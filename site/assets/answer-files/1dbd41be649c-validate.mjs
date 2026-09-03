// lib/validate.mjs
// DOM 组件静态校验器：对照 SKILL.md 规则检查 .tsx/.ts 文件。
// 只做静态文本检查，不执行代码，不修改任何文件。

import fs from "node:fs/promises";
import path from "node:path";

/**
 * 校验规则（对应 SKILL.md "Rules for DOM Components" 及其他章节）：
 *  R1  文件顶部必须有 "use dom" 指令
 *  R2  必须有且仅有一个默认导出
 *  R3  文件名不能是 _layout（SKILL.md: _layout files cannot be DOM components）
 *  R4  props 类型中不应包含函数/类实例等不可序列化类型（仅警告）
 *  R5  dom 属性应使用 import("expo/dom").DOMProps 类型
 *  R6  不应在 DOM 组件内直接使用需要原生路由状态的 hooks（警告）
 *  R7  外部 CSS 导入应使用相对路径（SKILL.md: CSS imports must be in the DOM component file）
 */

const ROUTER_HOOKS_NEEDING_PROPS = [
  "useLocalSearchParams",
  "useGlobalSearchParams",
  "usePathname",
  "useSegments",
  "useRootNavigation",
  "useRootNavigationState",
];

/**
 * @param {string} filePath - 待校验文件路径
 * @returns {Promise<{filePath: string, passed: boolean, errors: Array, warnings: Array}>}
 */
export async function validate(filePath) {
  const errors = [];
  const warnings = [];
  const resolved = path.resolve(filePath);

  let source;
  try {
    source = await fs.readFile(resolved, "utf-8");
  } catch (err) {
    return {
      filePath: resolved,
      passed: false,
      errors: [{ rule: "FILE", message: `无法读取文件：${err.message}` }],
      warnings: [],
    };
  }

  const basename = path.basename(resolved);
  const ext = path.extname(resolved);

  // R3: _layout 文件不能是 DOM 组件
  if (basename.toLowerCase().startsWith("_layout")) {
    errors.push({ rule: "R3", message: "SKILL.md 规定 _layout 文件不能是 DOM 组件" });
  }

  // R1: 顶部必须有 "use dom" 指令（允许前导注释/空行）
  const lines = source.split(/\r?\n/);
  let foundUseDom = false;
  for (let i = 0; i < Math.min(lines.length, 20); i++) {
    const trimmed = lines[i].trim();
    if (trimmed === "") continue;
    if (trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*")) continue;
    if (/^["']use dom["'];?$/.test(trimmed)) {
      foundUseDom = true;
    }
    break;
  }
  if (!foundUseDom) {
    errors.push({ rule: "R1", message: '文件顶部缺少 "use dom"; 指令' });
  }

  // R2: 默认导出检查
  const defaultExportMatches = source.match(/export\s+default\s+(function|class|const|let|var|\{|\()/g) || [];
  if (defaultExportMatches.length === 0) {
    errors.push({ rule: "R2", message: "缺少默认导出（每个 DOM 组件应有一个 default export）" });
  } else if (defaultExportMatches.length > 1) {
    warnings.push({ rule: "R2", message: `发现 ${defaultExportMatches.length} 个默认导出，建议每个文件只保留一个` });
  }

  // R5: dom 属性类型（匹配 dom: 或 dom?: 两种写法）
  if (!/dom\??\s*:\s*import\(["']expo\/dom["']\)\.DOMProps/.test(source)) {
    warnings.push({ rule: "R5", message: '建议为 dom 属性声明类型：dom?: import("expo/dom").DOMProps' });
  }

  // R4: 不可序列化 props 检查（在 interface/type Props 块中查找函数类型）
  const propsBlockMatch = source.match(/(?:interface|type)\s+\w*Props?\s*\{([\s\S]*?)\}/);
  if (propsBlockMatch) {
    const propsBlock = propsBlockMatch[1];
    // 查找箭头函数类型或 Function 类型
    const funcPropRegex = /^\s*\w+\s*[?:]\s*(\([^)]*\)\s*=>|Function\b)/gm;
    let m;
    while ((m = funcPropRegex.exec(propsBlock)) !== null) {
      warnings.push({
        rule: "R4",
        message: `props 中包含函数类型，SKILL.md 要求 props 仅可序列化；若需暴露原生方法，请通过 async 函数 props 传递（参考 SKILL.md "Exposing Native Actions"）`,
      });
    }
  }

  // R6: 路由 hooks 检查
  for (const hook of ROUTER_HOOKS_NEEDING_PROPS) {
    const re = new RegExp(`\\b${hook}\\s*\\(`);
    if (re.test(source)) {
      warnings.push({
        rule: "R6",
        message: `在 DOM 组件中直接使用 ${hook}() 可能无法获取同步路由状态，SKILL.md 建议在原生父组件中读取后通过 props 传入`,
      });
    }
  }

  // R7: CSS 导入检查
  const cssImports = source.match(/import\s+["'][^"']+\.css["']/g) || [];
  for (const imp of cssImports) {
    const importPath = imp.match(/["']([^"']+)["']/)[1];
    if (!importPath.startsWith(".") && !importPath.startsWith("@/")) {
      warnings.push({
        rule: "R7",
        message: `CSS 导入 "${importPath}" 不是相对路径；SKILL.md 要求 CSS 在 DOM 组件文件内（隔离上下文），建议使用相对路径或内联样式`,
      });
    }
  }

  // 额外：检查是否导入了 react-native（DOM 组件中不应直接用 RN 组件）
  if (/from\s+["']react-native["']/.test(source)) {
    warnings.push({
      rule: "RN",
      message: "DOM 组件运行在 Web 环境中，不应直接导入 react-native；请使用 HTML 元素",
    });
  }

  return {
    filePath: resolved,
    passed: errors.length === 0,
    errors,
    warnings,
  };
}
