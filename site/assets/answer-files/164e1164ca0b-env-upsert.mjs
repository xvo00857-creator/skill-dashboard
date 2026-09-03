#!/usr/bin/env node
// env-upsert.mjs
// 幂等写入 .env 的 KEY=VALUE：存在则原地更新，不存在则追加。
// 用法: node env-upsert.mjs <path-to-.env> <KEY> <VALUE>
// 仅更新以 KEY= 开头的行；注释行（# KEY=...）不动。
import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const [, , envPath, key, value] = process.argv;
if (!envPath || !key || value === undefined) {
  console.error('用法: env-upsert.mjs <.env路径> <KEY> <VALUE>');
  process.exit(1);
}

const line = `${key}=${value}`;
let lines = existsSync(envPath) ? readFileSync(envPath, 'utf8').split('\n') : [];
// 去掉因结尾换行产生的尾部空字符串
while (lines.length > 0 && lines[lines.length - 1] === '') lines.pop();

const re = new RegExp(`^${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}=`);
let found = false;
lines = lines.map((l) => {
  if (!found && re.test(l)) { found = true; return line; }
  return l;
});
if (!found) lines.push(line);

writeFileSync(envPath, lines.join('\n') + '\n', { mode: 0o600 });
const secret = key.includes('PASSWORD') || key.includes('TOKEN') || key.includes('SECRET');
console.log(`.env upsert: ${key}=${secret ? '***' : value}`);
