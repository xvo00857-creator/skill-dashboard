#!/usr/bin/env node
// bin/dom-component.mjs
// use-dom Skill 配套 CLI：DOM 组件脚手架与校验器
// 用法：
//   dom-component scaffold <组件名> [--dir components] [--force] [--yes] [--dry-run]
//   dom-component validate <文件路径>
//   dom-component --help

import path from "node:path";
import { scaffold } from "../lib/scaffold.mjs";
import { validate } from "../lib/validate.mjs";

const args = process.argv.slice(2);
const command = args[0];

function parseFlags(argv) {
  const flags = { force: false, yes: false, dryRun: false, dir: "components" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--force") flags.force = true;
    else if (a === "--yes" || a === "-y") flags.yes = true;
    else if (a === "--dry-run") flags.dryRun = true;
    else if (a === "--dir") flags.dir = argv[++i];
  }
  return flags;
}

function printSteps(steps) {
  for (const s of steps) {
    const mark = s.ok ? "✓" : "✗";
    console.log(`  ${mark} [${s.check}] ${s.detail}`);
  }
}

function printResult(result) {
  console.log(result.passed ? "\n✓ 校验通过" : "\n✗ 校验未通过");
  if (result.errors.length) {
    console.log("\n错误：");
    for (const e of result.errors) console.log(`  ✗ [${e.rule}] ${e.message}`);
  }
  if (result.warnings.length) {
    console.log("\n警告：");
    for (const w of result.warnings) console.log(`  ⚠ [${w.rule}] ${w.message}`);
  }
}

const HELP = `use-dom Skill 配套工具

用法：
  dom-component scaffold <组件名>   创建新的 DOM 组件
  dom-component validate <文件>     校验已有 DOM 组件是否符合 SKILL.md 规则

scaffold 选项：
  --dir <目录>     组件目录（相对项目根，默认 components）
  --force          允许覆盖已存在文件（仍需确认）
  --yes, -y        跳过人工确认（用于自动化）
  --dry-run        只打印计划，不写文件

示例：
  dom-component scaffold WebChart
  dom-component scaffold CodeBlock --dir components/dom --dry-run
  dom-component validate components/WebChart.tsx
`;

if (!command || command === "--help" || command === "-h") {
  console.log(HELP);
  process.exit(0);
}

const projectRoot = process.cwd();

if (command === "scaffold") {
  const name = args[1];
  if (!name) {
    console.error("错误：请提供组件名，例如 dom-component scaffold WebChart");
    process.exit(1);
  }
  const flags = parseFlags(args.slice(2));
  const result = await scaffold({
    projectRoot,
    name,
    componentsDir: flags.dir,
    force: flags.force,
    yes: flags.yes,
    dryRun: flags.dryRun,
  });
  printSteps(result.steps);
  if (result.success) {
    if (result.dryRun) {
      console.log("\n[Dry Run] 以下内容将被写入：");
      console.log("--- " + result.targetFile + " ---");
      console.log(result.content);
    } else {
      console.log(`\n✓ 完成：${result.targetFile}`);
    }
    process.exit(0);
  } else {
    console.error(`\n✗ 失败：${result.error}`);
    process.exit(1);
  }
} else if (command === "validate") {
  const file = args[1];
  if (!file) {
    console.error("错误：请提供文件路径，例如 dom-component validate components/WebChart.tsx");
    process.exit(1);
  }
  const result = await validate(path.resolve(projectRoot, file));
  console.log(`校验文件：${result.filePath}`);
  printResult(result);
  process.exit(result.passed ? 0 : 1);
} else {
  console.error(`未知命令：${command}\n`);
  console.log(HELP);
  process.exit(1);
}
