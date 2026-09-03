#!/usr/bin/env node
/**
 * verify-config.mjs —— Linear 渠道最小配置校验（零依赖，仅用 Node 内置模块）
 *
 * 用法：
 *   node verify-config.mjs                # 校验同目录 .env
 *   node verify-config.mjs .env.linear    # 校验指定文件
 *
 * 校验项（对应 SKILL.md Credentials 与适配器要求）：
 *   1. 必填项：LINEAR_WEBHOOK_SECRET、LINEAR_TEAM_KEY、LINEAR_BOT_USERNAME
 *   2. 认证方式：OAuth（CLIENT_ID+CLIENT_SECRET）或 API_KEY 至少配一种
 *   3. TEAM_KEY 格式：大写字母，1-10 位（Linear team key 规范）
 *   4. 非空值不能是占位符
 */

import { readFileSync } from "node:fs";
import { resolve, basename } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const envFile = process.argv[2] || ".env";
const envPath = resolve(__dirname, envFile);

const results = [];
function check(name, pass, detail) {
  results.push({ name, pass, detail });
}

// ---- 读取并解析 .env（简单解析，不引入 dotenv） ----
let raw;
try {
  raw = readFileSync(envPath, "utf8");
} catch (e) {
  console.error(`✗ 无法读取配置文件: ${envPath}\n  ${e.message}`);
  process.exit(1);
}

const env = {};
for (const line of raw.split("\n")) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) continue;
  const eq = trimmed.indexOf("=");
  if (eq === -1) continue;
  const key = trimmed.slice(0, eq).trim();
  const val = trimmed.slice(eq + 1).trim();
  env[key] = val;
}

const PLACEHOLDERS = new Set(["", "your-...", "changeme", "xxx", "todo"]);
function isReal(v) {
  return v !== undefined && !PLACEHOLDERS.has(v.toLowerCase());
}

// ---- 1. 必填项 ----
check(
  "LINEAR_WEBHOOK_SECRET 已设置",
  isReal(env.LINEAR_WEBHOOK_SECRET),
  isReal(env.LINEAR_WEBHOOK_SECRET) ? "已配置" : "缺失或为占位符（webhook 签名验证必需）"
);
check(
  "LINEAR_TEAM_KEY 已设置",
  isReal(env.LINEAR_TEAM_KEY),
  isReal(env.LINEAR_TEAM_KEY) ? `值为 ${env.LINEAR_TEAM_KEY}` : "缺失（如 ENG、NAN）"
);
check(
  "LINEAR_BOT_USERNAME 已设置",
  isReal(env.LINEAR_BOT_USERNAME),
  isReal(env.LINEAR_BOT_USERNAME) ? `值为 ${env.LINEAR_BOT_USERNAME}` : "缺失"
);

// ---- 2. 认证方式 ----
const hasOAuth = isReal(env.LINEAR_CLIENT_ID) && isReal(env.LINEAR_CLIENT_SECRET);
const hasApiKey = isReal(env.LINEAR_API_KEY);
check(
  "至少一种认证方式（OAuth 或 API Key）",
  hasOAuth || hasApiKey,
  hasOAuth
    ? "OAuth Client Credentials（推荐）"
    : hasApiKey
    ? "Personal API Key（本人评论会被过滤）"
    : "LINEAR_CLIENT_ID+SECRET 与 LINEAR_API_KEY 均未配置"
);
if (hasOAuth) {
  check(
    "OAuth Client ID 与 Secret 成对出现",
    isReal(env.LINEAR_CLIENT_ID) && isReal(env.LINEAR_CLIENT_SECRET),
    "ID 和 Secret 均已填写"
  );
}

// ---- 3. TEAM_KEY 格式 ----
const teamKeyOk = env.LINEAR_TEAM_KEY && /^[A-Z]{1,10}$/.test(env.LINEAR_TEAM_KEY);
check(
  "LINEAR_TEAM_KEY 格式正确（1-10 位大写字母）",
  !!teamKeyOk,
  teamKeyOk ? "符合" : `当前值 "${env.LINEAR_TEAM_KEY ?? ""}" 不符合 Linear team key 规范`
);

// ---- 4. 模拟值检测（提醒） ----
const fakeMarkers = ["fake", "example", "dummy", "test-", "your-"];
const looksFake = Object.entries(env).some(([k, v]) =>
  ["LINEAR_CLIENT_SECRET", "LINEAR_WEBHOOK_SECRET", "LINEAR_API_KEY"].includes(k) &&
  fakeMarkers.some((m) => v.toLowerCase().includes(m))
);
check(
  "凭证为真实值（非模拟值）",
  !looksFake,
  looksFake
    ? "检测到 fake/example 等标记——仅可用于本地验证，不可连接真实 Linear"
    : "未检测到模拟值标记"
);

// ---- 输出 ----
console.log(`\n=== Linear 渠道配置校验: ${basename(envPath)} ===\n`);
let failed = 0;
for (const r of results) {
  const icon = r.pass ? "✓" : "✗";
  console.log(`  ${icon} ${r.name}`);
  console.log(`      ${r.detail}`);
  if (!r.pass) failed++;
}
console.log(`\n  结果: ${results.length - failed}/${results.length} 通过`);
if (looksFake) {
  console.log("  注意: 当前为模拟凭证，验证脚本可通过，但不会连接真实 Linear 工作区。");
}
process.exit(failed > 0 ? 1 : 0);
