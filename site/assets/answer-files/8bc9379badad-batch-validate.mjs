#!/usr/bin/env node
/**
 * EAS Workflows 批量校验器
 * 复用 expo-cicd-workflows Skill 的 fetchCached（ETag 缓存）与 ajv/js-yaml 依赖，
 * 在 validate.js 同等逻辑上增加：预检、幂等、重试、人工确认点、可恢复批处理。
 *
 * 用法：
 *   node batch-validate.mjs [选项] <file1.yml> [file2.yml ...]
 *   node batch-validate.mjs --resume [选项]   # 从状态文件恢复，跳过已通过文件
 *
 * 选项：
 *   --yes, -y        跳过人工确认点（非交互模式）
 *   --resume         可恢复模式：跳过上次已通过的文件
 *   --skip-valid     若状态文件中已记录通过则跳过（幂等）
 *   --state <path>   状态文件路径（默认 .batch-validate-state.json）
 *   --report <path>  报告输出路径（默认 reports/validate-report-<时间戳>.json）
 *   --max-retries N  schema 获取重试次数（默认 3）
 *   --help, -h       显示帮助
 */

import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, basename } from 'node:path';
import process from 'node:process';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

// ---- 路径配置 ----
const WORK_DIR = resolve('.');
const SKILL_DIR = resolve(WORK_DIR, 'expo-cicd-workflows/expo-cicd-workflows');
const SKILL_SCRIPTS = resolve(SKILL_DIR, 'scripts');
const SCHEMA_URL = 'https://api.expo.dev/v2/workflows/schema';

// ---- 解析参数 ----
const args = process.argv.slice(2);
const opts = {
  yes: args.includes('--yes') || args.includes('-y'),
  resume: args.includes('--resume'),
  skipValid: args.includes('--skip-valid'),
  files: args.filter(a => !a.startsWith('-')),
  maxRetries: 3,
  statePath: resolve(WORK_DIR, '.batch-validate-state.json'),
  reportPath: null,
};
const stateIdx = args.indexOf('--state');
if (stateIdx >= 0) opts.statePath = resolve(args[stateIdx + 1]);
const reportIdx = args.indexOf('--report');
if (reportIdx >= 0) opts.reportPath = resolve(args[reportIdx + 1]);
const retriesIdx = args.indexOf('--max-retries');
if (retriesIdx >= 0) opts.maxRetries = parseInt(args[retriesIdx + 1], 10);

if (args.includes('--help') || args.includes('-h') || (opts.files.length === 0 && !opts.resume)) {
  console.log(`EAS Workflows 批量校验器
用法: node batch-validate.mjs [选项] <file1.yml> [file2.yml ...]

选项:
  -y, --yes          跳过人工确认点
  --resume           从状态文件恢复，跳过已通过文件
  --skip-valid       状态文件中已通过的文件跳过（幂等）
  --state <path>     状态文件路径
  --report <path>    报告输出路径
  --max-retries N    schema 获取重试次数（默认 3）
  -h, --help         显示帮助`);
  process.exit(args.includes('--help') ? 0 : 1);
}

// ---- 工具函数 ----
function log(level, msg) {
  const prefix = { info: 'ℹ', ok: '✓', warn: '⚠', err: '✗', ask: '?' }[level] || '·';
  console.log(`${prefix} ${msg}`);
}

async function confirm(question) {
  if (opts.yes) {
    log('info', `${question} [自动确认: 是]`);
    return true;
  }
  const rl = createInterface({ input, output });
  const answer = await rl.question(`? ${question} (y/N) `);
  rl.close();
  return /^[yY]/.test(answer);
}

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// 带指数退避的重试
async function withRetry(fn, label, maxRetries) {
  let lastErr;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (e) {
      lastErr = e;
      if (attempt < maxRetries) {
        const delay = Math.min(1000 * 2 ** (attempt - 1), 8000);
        log('warn', `${label} 失败（第 ${attempt}/${maxRetries} 次）: ${e.message}，${delay}ms 后重试...`);
        await sleep(delay);
      }
    }
  }
  throw lastErr;
}

// ---- 预检 ----
async function preflight() {
  log('info', '=== 预检开始 ===');
  const checks = [];

  // 1. Node 版本 >= 18（需要内置 fetch 和 ESM）
  const nodeMajor = parseInt(process.versions.node.split('.')[0], 10);
  checks.push({
    name: `Node.js 版本 >= 18（当前 ${process.version}）`,
    pass: nodeMajor >= 18,
  });

  // 2. Skill 脚本存在
  const fetchScript = resolve(SKILL_SCRIPTS, 'fetch.js');
  checks.push({
    name: `Skill fetch.js 存在`,
    pass: existsSync(fetchScript),
  });

  // 3. 依赖已安装
  const ajvPath = resolve(SKILL_SCRIPTS, 'node_modules/ajv/dist/2020.js');
  const yamlPath = resolve(SKILL_SCRIPTS, 'node_modules/js-yaml/index.js');
  checks.push({
    name: `校验依赖已安装（ajv, js-yaml）`,
    pass: existsSync(ajvPath) && existsSync(yamlPath),
  });

  // 4. 待校验文件存在
  for (const f of opts.files) {
    const abs = resolve(WORK_DIR, f);
    checks.push({
      name: `文件存在: ${f}`,
      pass: existsSync(abs),
    });
  }

  let allPass = true;
  for (const c of checks) {
    log(c.pass ? 'ok' : 'err', `${c.name}: ${c.pass ? '通过' : '失败'}`);
    if (!c.pass) allPass = false;
  }

  if (!allPass) {
    throw new Error('预检未通过，请修复上述问题后重试');
  }
  log('ok', '=== 预检全部通过 ===');
}

// ---- 加载状态（可恢复/幂等） ----
async function loadState() {
  try {
    const raw = await readFile(opts.statePath, 'utf8');
    return JSON.parse(raw);
  } catch {
    return { files: {} };
  }
}

async function saveState(state) {
  await writeFile(opts.statePath, JSON.stringify(state, null, 2));
}

// ---- 语义检查（SKILL.md 第 3、4 条） ----
function semanticCheck(doc) {
  const warnings = [];
  if (!doc.jobs || typeof doc.jobs !== 'object') return warnings;
  const jobNames = Object.keys(doc.jobs);
  for (const [name, job] of Object.entries(doc.jobs)) {
    if (Array.isArray(job.needs)) {
      for (const dep of job.needs) {
        if (!jobNames.includes(dep)) {
          warnings.push(`job "${name}" 的 needs 引用了不存在的 job: "${dep}"`);
        }
      }
    }
    if (Array.isArray(job.after)) {
      for (const dep of job.after) {
        if (!jobNames.includes(dep)) {
          warnings.push(`job "${name}" 的 after 引用了不存在的 job: "${dep}"`);
        }
      }
    }
  }
  return warnings;
}

// ---- 主流程 ----
async function main() {
  await preflight();

  // 人工确认点 1：确认待校验文件清单
  log('info', `待校验文件（${opts.files.length} 个）:`);
  opts.files.forEach((f, i) => log('info', `  ${i + 1}. ${f}`));
  if (!(await confirm('确认开始批量校验？'))) {
    log('warn', '用户取消，退出。');
    process.exit(0);
  }

  // 加载 Skill 模块
  const { fetchCached } = await import(resolve(SKILL_SCRIPTS, 'fetch.js'));
  const Ajv2020 = (await import(resolve(SKILL_SCRIPTS, 'node_modules/ajv/dist/2020.js'))).default;
  const addFormats = (await import(resolve(SKILL_SCRIPTS, 'node_modules/ajv-formats/dist/index.js'))).default;
  const yaml = (await import(resolve(SKILL_SCRIPTS, 'node_modules/js-yaml/index.js'))).default;

  // 获取 schema（带重试，fetchCached 自带 ETag 幂等缓存）
  log('info', '获取官方 JSON Schema（带 ETag 缓存与重试）...');
  const schemaData = await withRetry(
    async () => {
      const raw = await fetchCached(SCHEMA_URL);
      return JSON.parse(raw).data;
    },
    '获取 schema',
    opts.maxRetries
  );
  log('ok', `Schema 已加载（$id: ${schemaData.$id || 'n/a'}）`);

  const ajv = new Ajv2020({ allErrors: true, strict: true });
  addFormats(ajv);
  const validator = ajv.compile(schemaData);

  // 加载状态（幂等/可恢复）
  const state = await loadState();
  const results = [];
  let passed = 0, failed = 0, skipped = 0;

  for (const file of opts.files) {
    const absPath = resolve(WORK_DIR, file);

    // 幂等：跳过已通过文件
    if ((opts.skipValid || opts.resume) && state.files[absPath]?.status === 'valid') {
      log('ok', `${file} — 已在状态文件中记录为通过，跳过（幂等）`);
      skipped++;
      results.push({ file, status: 'skipped', reason: 'previously-valid' });
      continue;
    }

    log('info', `校验: ${file}`);
    let content, doc;
    try {
      content = await readFile(absPath, 'utf8');
    } catch (e) {
      log('err', `${file} — 读取失败: ${e.message}`);
      failed++;
      results.push({ file, status: 'invalid', errors: [`读取失败: ${e.message}`] });
      state.files[absPath] = { status: 'invalid', errors: [`读取失败: ${e.message}`], at: new Date().toISOString() };
      continue;
    }

    try {
      doc = yaml.load(content);
    } catch (e) {
      log('err', `${file} — YAML 解析错误: ${e.message}`);
      failed++;
      results.push({ file, status: 'invalid', errors: [`YAML 解析错误: ${e.message}`] });
      state.files[absPath] = { status: 'invalid', errors: [`YAML 解析错误: ${e.message}`], at: new Date().toISOString() };
      continue;
    }

    const errors = [];
    const valid = validator(doc);
    if (!valid) {
      for (const e of validator.errors) {
        const path = e.instancePath || '(root)';
        const allowed = e.params?.allowedValues?.join(', ');
        errors.push(`${path}: ${e.message}${allowed ? ` (allowed: ${allowed})` : ''}`);
      }
    }

    // 语义检查
    const warnings = semanticCheck(doc);

    if (!valid) {
      log('err', `${file} — Schema 校验失败:`);
      errors.forEach(e => console.log(`    ${e}`));
      failed++;
      results.push({ file, status: 'invalid', errors, warnings });
      state.files[absPath] = { status: 'invalid', errors, warnings, at: new Date().toISOString() };
    } else if (warnings.length > 0) {
      log('warn', `${file} — Schema 通过，但有语义警告:`);
      warnings.forEach(w => console.log(`    ${w}`));
      passed++;
      results.push({ file, status: 'valid-with-warnings', warnings });
      state.files[absPath] = { status: 'valid', warnings, at: new Date().toISOString() };
    } else {
      log('ok', `${file} — 校验通过`);
      passed++;
      results.push({ file, status: 'valid' });
      state.files[absPath] = { status: 'valid', at: new Date().toISOString() };
    }

    await saveState(state);
  }

  // 人工确认点 2：校验完成后确认是否生成报告
  log('info', `汇总: 通过 ${passed}, 失败 ${failed}, 跳过 ${skipped}`);
  if (failed > 0) {
    log('warn', '存在校验失败的文件。报告将记录详细错误。');
  }

  const reportDir = resolve(WORK_DIR, 'reports');
  await mkdir(reportDir, { recursive: true });
  const reportPath = opts.reportPath || resolve(reportDir, `validate-report-${Date.now()}.json`);
  const report = {
    timestamp: new Date().toISOString(),
    schema_url: SCHEMA_URL,
    skill_dir: SKILL_DIR,
    summary: { total: opts.files.length, passed, failed, skipped },
    results,
  };
  await writeFile(reportPath, JSON.stringify(report, null, 2));
  log('ok', `报告已写入: ${reportPath}`);
  await saveState(state);

  process.exit(failed > 0 ? 1 : 0);
}

main().catch(e => {
  log('err', `致命错误: ${e.message}`);
  console.error(e.stack);
  process.exit(2);
});
