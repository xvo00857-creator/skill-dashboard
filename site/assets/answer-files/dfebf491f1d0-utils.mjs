// lib/utils.mjs
// 共享工具：预检、重试、人工确认、路径安全检查
// 所有文件操作均限制在当前工作目录内，不静默覆盖外部资源。

import fs from "node:fs/promises";
import path from "node:path";
import readline from "node:readline";

/**
 * 预检：确认当前目录看起来是一个 Expo 项目。
 * 检查 package.json 是否存在且依赖中包含 expo。
 * @param {string} projectRoot - 项目根目录
 * @returns {Promise<{ok: boolean, reason?: string, expoVersion?: string}>}
 */
export async function precheckExpoProject(projectRoot) {
  const pkgPath = path.join(projectRoot, "package.json");
  try {
    const raw = await fs.readFile(pkgPath, "utf-8");
    const pkg = JSON.parse(raw);
    const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
    if (!deps.expo) {
      return { ok: false, reason: "package.json 中未找到 expo 依赖，可能不是 Expo 项目" };
    }
    return { ok: true, expoVersion: deps.expo };
  } catch (err) {
    if (err.code === "ENOENT") {
      return { ok: false, reason: `未找到 package.json（${pkgPath}），请在 Expo 项目根目录运行` };
    }
    if (err instanceof SyntaxError) {
      return { ok: false, reason: "package.json 解析失败：JSON 格式错误" };
    }
    return { ok: false, reason: `读取 package.json 失败：${err.message}` };
  }
}

/**
 * 预检：组件名合法性。
 * 必须是 PascalCase 标识符，且不能是 _layout（SKILL.md 明确禁止）。
 */
export function precheckComponentName(name) {
  if (!name || typeof name !== "string") {
    return { ok: false, reason: "组件名不能为空" };
  }
  if (name.toLowerCase() === "_layout" || name.startsWith("_layout")) {
    return { ok: false, reason: "SKILL.md 规定 _layout 文件不能是 DOM 组件" };
  }
  if (!/^[A-Z][A-Za-z0-9]*$/.test(name)) {
    return { ok: false, reason: "组件名必须是 PascalCase（如 MyChart），仅含字母数字且以大写字母开头" };
  }
  return { ok: true };
}

/**
 * 确保目标路径在项目根目录内，防止路径穿越。
 */
export function assertPathInside(root, target) {
  const resolvedRoot = path.resolve(root);
  const resolvedTarget = path.resolve(target);
  if (!resolvedTarget.startsWith(resolvedRoot + path.sep) && resolvedTarget !== resolvedRoot) {
    throw new Error(`安全拦截：目标路径 ${resolvedTarget} 不在项目根目录 ${resolvedRoot} 内`);
  }
}

/**
 * 带重试的文件写入。最多重试 3 次，指数退避。
 * 仅对临时错误（EBUSY/EPERM/ENOSPC 等）重试，不对 EEXIST 等业务错误重试。
 */
export async function writeFileWithRetry(filePath, content, options = {}) {
  const maxRetries = options.maxRetries ?? 3;
  const flag = options.flag ?? "wx"; // 默认 wx：独占创建，不覆盖已有文件
  let lastErr;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      await fs.writeFile(filePath, content, { encoding: "utf-8", flag });
      return { attempted: attempt, overwrote: false };
    } catch (err) {
      lastErr = err;
      // EEXIST 是业务逻辑错误（文件已存在），不重试，交给调用方处理
      if (err.code === "EEXIST") throw err;
      if (attempt < maxRetries) {
        const delay = 200 * Math.pow(2, attempt - 1); // 200ms, 400ms, 800ms
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }
  throw lastErr;
}

/**
 * 交互式人工确认（在 TTY 环境下）。
 * 非 TTY 或传入 yes=true 时自动通过（用于 CI/自动化场景，但调用方应显式传入）。
 */
export async function confirm(question, { yes = false, defaultYes = false } = {}) {
  if (yes) return true;
  if (!process.stdin.isTTY) {
    // 非交互环境：没有显式 --yes 时，默认拒绝，避免静默执行
    console.log(`[需确认] ${question}（非交互环境，未指定 --yes，默认拒绝）`);
    return false;
  }
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    const hint = defaultYes ? " [Y/n] " : " [y/N] ";
    rl.question(question + hint, (answer) => {
      rl.close();
      const a = answer.trim().toLowerCase();
      if (a === "") resolve(defaultYes);
      else resolve(a === "y" || a === "yes");
    });
  });
}

/**
 * 检查文件是否存在。
 */
export async function fileExists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}
