#!/usr/bin/env node
/**
 * cdp-screenshot.js
 * 通过 CDP（Chrome DevTools Protocol）对当前页面截图，保存为 PNG。
 * 不依赖任何第三方包：仅使用 Node 20 内置的全局 WebSocket 与 http。
 *
 * 用途：为浏览器验收流程留存证据。只读操作——只调用 Page.captureScreenshot，
 * 不点击、不输入、不读取 localStorage / cookie，不提取任何令牌。
 *
 * 用法：
 *   node cdp-screenshot.js --port 9222 --out ./screenshots/01-login.png [--timeout 15000]
 *
 * 退出码：0 成功 / 1 参数或环境错误 / 2 连接或截图失败
 */

"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const args = { port: 9222, out: null, timeoutMs: 15000 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--port") args.port = parseInt(argv[++i], 10);
    else if (a === "--out") args.out = argv[++i];
    else if (a === "--timeout") args.timeoutMs = parseInt(argv[++i], 10);
  }
  return args;
}

function httpGetJson(url, timeoutMs) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: timeoutMs, agent: false }, (res) => {
      let body = "";
      res.on("data", (c) => (body += c));
      res.on("end", () => {
        if (res.statusCode >= 400) return reject(new Error(`HTTP ${res.statusCode}`));
        try { resolve(JSON.parse(body)); } catch (e) { reject(new Error("返回内容不是合法 JSON")); }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("请求超时")); });
  });
}

function cdpCapture(wsUrl, timeoutMs) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    const id = 1;
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try { ws.close(); } catch {}
      reject(new Error(`CDP 截图超时（${timeoutMs}ms）`));
    }, timeoutMs);

    ws.addEventListener("open", () => {
      // 先启用 Page 域，再截图
      ws.send(JSON.stringify({ id, method: "Page.enable" }));
    });

    ws.addEventListener("message", (event) => {
      let msg;
      try { msg = JSON.parse(event.data); } catch { return; }
      if (msg.id !== id) return; // 只处理我们这一轮

      if (msg.error) {
        settled = true; clearTimeout(timer);
        try { ws.close(); } catch {}
        return reject(new Error("CDP 返回错误: " + JSON.stringify(msg.error)));
      }

      // Page.enable 的应答：接着发截图请求
      if (msg.result && !msg.result.data) {
        ws.send(JSON.stringify({
          id: id + 1,
          method: "Page.captureScreenshot",
          params: { format: "png" },
        }));
        return;
      }

      // 截图应答
      if (msg.result && msg.result.data) {
        settled = true; clearTimeout(timer);
        try { ws.close(); } catch {}
        resolve(msg.result.data);
      }
    });

    ws.addEventListener("error", (e) => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      reject(new Error("WebSocket 连接失败: " + (e.message || e)));
    });
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.out) {
    console.error("用法: node cdp-screenshot.js --port 9222 --out <输出路径>");
    process.exit(1);
  }

  // 1. 取页面目标列表（只读）
  let targets;
  try {
    targets = await httpGetJson(`http://127.0.0.1:${args.port}/json/list`, 5000);
  } catch (e) {
    console.error(`无法连接 CDP 端口 ${args.port}：${e.message}`);
    console.error("请先确认调试 Chrome 已启动（见 README 的启动流程）。");
    process.exit(2);
  }

  if (!Array.isArray(targets) || targets.length === 0) {
    console.error("CDP 已连接，但没有打开的页面标签。请先用 agent-browser open <URL> 打开被测站点。");
    process.exit(2);
  }

  // 优先选 page 类型目标；若有多个，取最后激活的一个（数组末尾通常是最近的）
  const pages = targets.filter((t) => t.type === "page");
  const target = pages[pages.length - 1] || targets[targets.length - 1];
  if (!target.webSocketDebuggerUrl) {
    console.error("目标标签没有 webSocketDebuggerUrl，无法截图。");
    process.exit(2);
  }

  // 2. 截图
  const base64 = await cdpCapture(target.webSocketDebuggerUrl, args.timeoutMs);

  // 3. 写文件
  const outPath = path.resolve(args.out);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, Buffer.from(base64, "base64"));
  console.log(`截图已保存: ${outPath}`);
}

main().catch((e) => {
  console.error("截图失败: " + e.message);
  process.exit(2);
});
