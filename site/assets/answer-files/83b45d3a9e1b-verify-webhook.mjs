#!/usr/bin/env node
/**
 * verify-webhook.mjs —— Linear Webhook 签名机制本地模拟验证（零依赖）
 *
 * 复现 @linear/sdk/webhooks 的签名与校验逻辑（从 SDK 源码确认）：
 *   - 签名头: linear-signature
 *   - 时间戳头: linear-timestamp
 *   - 算法: HMAC-SHA256(rawBody, webhookSecret).digest("hex")
 *   - 比较: crypto.timingSafeEqual（长度一致后常量时间比较）
 *   - 时间戳容差: 60 秒
 *
 * 用法：
 *   node verify-webhook.mjs                # 使用 .env.linear 中的假密钥
 *   node verify-webhook.mjs <secret>       # 指定密钥
 *
 * 本脚本不发起任何网络请求，仅在本地构造模拟 Comment 事件并验证签名链路。
 */

import { createHmac, timingSafeEqual } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

// ---- 读取密钥（与 verify-config.mjs 相同的简易 .env 解析） ----
function loadSecret() {
  if (process.argv[2]) return process.argv[2];
  try {
    const raw = readFileSync(resolve(__dirname, ".env.linear"), "utf8");
    for (const line of raw.split("\n")) {
      const m = line.match(/^LINEAR_WEBHOOK_SECRET=(.+)$/);
      if (m) return m[1].trim();
    }
  } catch {
    /* fall through */
  }
  return "fake-webhook-secret";
}

const SECRET = loadSecret();
const TIMESTAMP_TOLERANCE_MS = 60_000; // SDK 中为 1e3 * 60

// ---- 签名（模拟 Linear 服务端签名） ----
function sign(rawBody, secret) {
  return createHmac("sha256", secret).update(rawBody).digest("hex");
}

// ---- 验签（复刻 LinearWebhookClient.verify 逻辑） ----
function verify(rawBody, signature, timestamp) {
  const expected = Buffer.from(createHmac("sha256", SECRET).update(rawBody).digest("hex"));
  const actual = Buffer.from(signature);
  if (expected.length !== actual.length) return { ok: false, reason: "签名长度不匹配" };
  if (!timingSafeEqual(expected, actual)) return { ok: false, reason: "签名不匹配" };
  if (timestamp !== undefined && timestamp !== null) {
    const ts = typeof timestamp === "string" ? parseInt(timestamp, 10) : timestamp;
    if (Number.isNaN(ts)) return { ok: false, reason: `时间戳无法解析: ${timestamp}` };
    if (Math.abs(Date.now() - ts) > TIMESTAMP_TOLERANCE_MS)
      return { ok: false, reason: "时间戳超出 60 秒容差（可能为重放攻击）" };
  }
  return { ok: true };
}

// ---- 构造模拟 Linear Comment webhook 负载 ----
function makeCommentPayload(action = "create") {
  return {
    action,
    type: "Comment",
    data: {
      id: "fake-comment-uuid-0001",
      body: "请帮我看一下这个 issue 的优先级",
      issueId: "fake-issue-uuid-abcd",
      userId: "fake-user-uuid-5678",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    organizationId: "fake-org-uuid",
    webhookTimestamp: Date.now(),
    webhookId: "fake-webhook-delivery-uuid",
  };
}

// ---- 测试用例 ----
const cases = [];
function test(name, fn) {
  cases.push({ name, fn });
}

test("正常 Comment 事件签名验证通过", () => {
  const body = JSON.stringify(makeCommentPayload("create"));
  const sig = sign(body, SECRET);
  const ts = String(Date.now());
  const r = verify(body, sig, ts);
  return r.ok ? { pass: true } : { pass: false, detail: r.reason };
});

test("篡改 body 后签名验证失败", () => {
  const body = JSON.stringify(makeCommentPayload("create"));
  const sig = sign(body, SECRET);
  const tampered = body.replace("优先级", "描述"); // 篡改内容
  const r = verify(tampered, sig, String(Date.now()));
  return !r.ok && r.reason === "签名不匹配"
    ? { pass: true, detail: "篡改被正确拒绝" }
    : { pass: false, detail: `应拒绝但得到: ${JSON.stringify(r)}` };
});

test("错误密钥签名验证失败", () => {
  const body = JSON.stringify(makeCommentPayload("create"));
  const wrongSig = sign(body, "wrong-secret");
  const r = verify(body, wrongSig, String(Date.now()));
  return !r.ok
    ? { pass: true, detail: "错误密钥被正确拒绝" }
    : { pass: false, detail: "错误密钥不应通过" };
});

test("过期时间戳（超过 60 秒）验证失败", () => {
  const body = JSON.stringify(makeCommentPayload("create"));
  const sig = sign(body, SECRET);
  const oldTs = String(Date.now() - 120_000); // 2 分钟前
  const r = verify(body, sig, oldTs);
  return !r.ok && r.reason.includes("时间戳")
    ? { pass: true, detail: "过期时间戳被正确拒绝" }
    : { pass: false, detail: `应拒绝但得到: ${JSON.stringify(r)}` };
});

test("签名长度不一致验证失败", () => {
  const body = JSON.stringify(makeCommentPayload("create"));
  const r = verify(body, "abc", String(Date.now()));
  return !r.ok
    ? { pass: true, detail: "短签名被正确拒绝" }
    : { pass: false, detail: "短签名不应通过" };
});

test("action=remove 事件不触发回复逻辑（仅验签通过）", () => {
  // 适配器只处理 action=create；此处验证验签本身对非 create 事件同样生效
  const body = JSON.stringify(makeCommentPayload("remove"));
  const sig = sign(body, SECRET);
  const r = verify(body, sig, String(Date.now()));
  return r.ok
    ? { pass: true, detail: "验签通过；业务层应忽略非 create 事件" }
    : { pass: false, detail: r.reason };
});

// ---- 执行 ----
console.log(`\n=== Linear Webhook 签名模拟验证（密钥: ${SECRET.slice(0, 4)}***） ===\n`);
let passed = 0;
for (const c of cases) {
  let result;
  try {
    result = c.fn();
  } catch (e) {
    result = { pass: false, detail: `异常: ${e.message}` };
  }
  const icon = result.pass ? "✓" : "✗";
  console.log(`  ${icon} ${c.name}`);
  if (result.detail) console.log(`      ${result.detail}`);
  if (result.pass) passed++;
}
console.log(`\n  结果: ${passed}/${cases.length} 通过`);
process.exit(passed === cases.length ? 0 : 1);
