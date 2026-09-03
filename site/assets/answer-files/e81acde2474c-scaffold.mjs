// lib/scaffold.mjs
// DOM 组件脚手架：按 SKILL.md 规则生成新组件文件。
// 幂等：文件已存在时拒绝覆盖，除非 --force 且经人工确认。

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  precheckExpoProject,
  precheckComponentName,
  assertPathInside,
  writeFileWithRetry,
  confirm,
  fileExists,
} from "./utils.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE_PATH = path.join(__dirname, "..", "templates", "component.tsx.tpl");

/**
 * 生成 DOM 组件。
 * @param {object} opts
 * @param {string} opts.projectRoot - 项目根目录
 * @param {string} opts.name - 组件名（PascalCase）
 * @param {string} [opts.componentsDir] - 组件目录（相对项目根，默认 components）
 * @param {boolean} [opts.force] - 允许覆盖已存在文件
 * @param {boolean} [opts.yes] - 跳过人工确认
 * @param {boolean} [opts.dryRun] - 只打印不写文件
 */
export async function scaffold({
  projectRoot,
  name,
  componentsDir = "components",
  force = false,
  yes = false,
  dryRun = false,
}) {
  const steps = [];

  // ---- 预检 1：Expo 项目 ----
  const expoCheck = await precheckExpoProject(projectRoot);
  steps.push({ check: "Expo 项目检查", ok: expoCheck.ok, detail: expoCheck.ok ? `expo ${expoCheck.expoVersion}` : expoCheck.reason });
  if (!expoCheck.ok) {
    return { success: false, steps, error: expoCheck.reason };
  }

  // ---- 预检 2：组件名 ----
  const nameCheck = precheckComponentName(name);
  steps.push({ check: "组件名检查", ok: nameCheck.ok, detail: nameCheck.ok ? name : nameCheck.reason });
  if (!nameCheck.ok) {
    return { success: false, steps, error: nameCheck.reason };
  }

  // ---- 预检 3：目标路径安全 ----
  const targetDir = path.resolve(projectRoot, componentsDir);
  const fileName = `${name}.tsx`;
  const targetFile = path.join(targetDir, fileName);
  try {
    assertPathInside(projectRoot, targetDir);
    assertPathInside(projectRoot, targetFile);
    steps.push({ check: "路径安全检查", ok: true, detail: targetFile });
  } catch (err) {
    steps.push({ check: "路径安全检查", ok: false, detail: err.message });
    return { success: false, steps, error: err.message };
  }

  // ---- 幂等检查：文件是否已存在 ----
  const exists = await fileExists(targetFile);
  if (exists && !force) {
    const msg = `文件已存在：${targetFile}（幂等保护，拒绝静默覆盖。使用 --force 可覆盖，但仍需确认）`;
    steps.push({ check: "幂等检查", ok: false, detail: msg });
    return { success: false, steps, error: msg };
  }

  // ---- 读取模板 ----
  let template;
  try {
    template = await fs.readFile(TEMPLATE_PATH, "utf-8");
    steps.push({ check: "模板读取", ok: true, detail: TEMPLATE_PATH });
  } catch (err) {
    steps.push({ check: "模板读取", ok: false, detail: err.message });
    return { success: false, steps, error: `模板读取失败：${err.message}` };
  }

  const content = template.replaceAll("{{COMPONENT_NAME}}", name);

  // ---- dry-run ----
  if (dryRun) {
    steps.push({ check: "Dry Run", ok: true, detail: "未写入任何文件" });
    return { success: true, steps, dryRun: true, targetFile, content };
  }

  // ---- 人工确认点：覆盖已存在文件 ----
  if (exists && force) {
    const ok = await confirm(`将覆盖已存在的文件 ${targetFile}，是否继续？`, { yes });
    if (!ok) {
      steps.push({ check: "人工确认", ok: false, detail: "用户取消覆盖" });
      return { success: false, steps, error: "用户取消操作" };
    }
    steps.push({ check: "人工确认", ok: true, detail: "用户确认覆盖" });
  }

  // ---- 人工确认点：新建文件（展示计划） ----
  const planOk = await confirm(`将创建 DOM 组件：${targetFile}，是否继续？`, { yes, defaultYes: true });
  if (!planOk) {
    steps.push({ check: "人工确认", ok: false, detail: "用户取消创建" });
    return { success: false, steps, error: "用户取消操作" };
  }

  // ---- 确保目录存在 ----
  await fs.mkdir(targetDir, { recursive: true });

  // ---- 写入文件（带重试）----
  try {
    if (exists && force) {
      // 覆盖模式：先用临时文件写入再 rename，避免半写状态
      const tmpFile = `${targetFile}.tmp-${process.pid}`;
      await writeFileWithRetry(tmpFile, content, { flag: "w" });
      await fs.rename(tmpFile, targetFile);
      steps.push({ check: "文件写入", ok: true, detail: `已覆盖 ${targetFile}` });
    } else {
      await writeFileWithRetry(targetFile, content);
      steps.push({ check: "文件写入", ok: true, detail: `已创建 ${targetFile}` });
    }
  } catch (err) {
    steps.push({ check: "文件写入", ok: false, detail: err.message });
    return { success: false, steps, error: `写入失败：${err.message}` };
  }

  return { success: true, steps, targetFile, content };
}
