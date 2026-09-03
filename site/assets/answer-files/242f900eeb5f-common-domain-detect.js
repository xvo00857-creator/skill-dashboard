#!/usr/bin/env node
/**
 * common-domain-detect.js
 * 基于 component-common-domain-detection Skill 的五阶段方法论实现：
 *   1. 命名空间叶子节点模式扫描
 *   2. 跨组件共享文件/类检测
 *   3. 功能相似度分析（基于导入与文件结构）
 *   4. 耦合影响评估（传入耦合 CA）
 *   5. 合并方式建议（共享服务 / 共享库 / 组件合并）
 *
 * 零外部依赖，仅使用 Node.js 内置模块。
 * 用法：node common-domain-detect.js <仓库根目录> [--json]
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------- 配置：来自 SKILL.md 的模式定义 ----------

// 高优先级合并候选（领域功能）
const DOMAIN_LEAF_PATTERNS = [
  'notification', 'notify', 'email',
  'audit', 'auditing',
  'validation', 'validate', 'validator',
  'format', 'formatter', 'formatting',
  'report', 'reporting',
];

// 基础设施模式（不在本 Skill 合并范围内）
const INFRA_LEAF_PATTERNS = ['util', 'utils', 'helper', 'helpers', 'common', 'lib', 'libs', 'vendor'];

// 基础设施导入（排除出共享类统计）
const INFRA_IMPORT_PATTERNS = [
  /^react$/i, /^react-dom/i, /^vue$/i, /^angular/i, /^svelte/i,
  /^express$/i, /^koa$/i, /^fastify$/i, /^hapi$/i, /^nestjs/i,
  /^axios$/i, /^lodash/i, /^underscore/i, /^ramda$/i,
  /^dayjs$/i, /^moment$/i, /^date-fns/i,
  /^winston$/i, /^log4js/i, /^pino$/i, /^debug$/i,
  /^dotenv$/i, /^config$/i, /^joi$/i, /^zod$/i, /^yup$/i,
  /^jest$/i, /^mocha$/i, /^vitest$/i, /^chai$/i,
  /^webpack$/i, /^vite$/i, /^babel/i, /^eslint/i, /^typescript$/i,
  /^@types\//i, /^node:/i,
];

// 视为组件根的目录名（保留用于参考；当前发现逻辑以"直接含代码文件的目录"为组件）
const COMPONENT_ROOTS = new Set([
  'src', 'lib', 'packages', 'apps', 'services', 'components',
  'pages', 'views', 'modules', 'features', 'api', 'controllers',
  'routes', 'hooks', 'store', 'stores', 'utils', 'common', 'shared',
]);
void COMPONENT_ROOTS; // 显式标记为保留配置，避免未使用告警

const CODE_EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx', '.vue', '.mjs', '.cjs']);
const SKIP_DIRS = new Set([
  'node_modules', '.git', 'dist', 'build', '.next', 'coverage',
  '.nuxt', 'output', 'target', '__pycache__', '.cache',
]);

// ---------- 阶段 0：发现组件 ----------

function walk(dir, acc) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (e) {
    return acc;
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    acc.push(full);
    walk(full, acc);
  }
  return acc;
}

function hasCodeFilesDirectly(dir) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (e) {
    return false;
  }
  return entries.some((e) => e.isFile() && CODE_EXTENSIONS.has(path.extname(e.name)));
}

/**
 * 组件定义：任何直接包含代码文件的目录（仓库根除外）。
 * 例如 src/components/Button、src/api/user、src/services/notification、src/utils。
 * 文件归属时取最长匹配路径，因此嵌套目录不会重复计数。
 */
function discoverComponents(rootDir) {
  const allDirs = walk(rootDir, []);
  const components = [];
  const rootResolved = path.resolve(rootDir);

  for (const dir of allDirs) {
    if (path.resolve(dir) === rootResolved) continue;
    if (!hasCodeFilesDirectly(dir)) continue;
    const rel = path.relative(rootDir, dir);
    const parts = rel.split(path.sep);
    components.push({
      name: parts[parts.length - 1],
      relPath: rel,
      absPath: dir,
      leaf: parts[parts.length - 1],
    });
  }

  // 去重
  const seen = new Set();
  return components.filter((c) => {
    if (seen.has(c.relPath)) return false;
    seen.add(c.relPath);
    return true;
  });
}

/**
 * 阶段 1 补充：检测文件名即领域模式的情况（对应 SKILL.md Node.js 示例：
 * services/CustomerService/notification.js ← Common pattern）。
 * 返回 { pattern, files: [{file, component}] }
 */
function detectFilenamePatterns(components, rootDir) {
  const groups = {};
  for (const comp of components) {
    const files = listCodeFiles(comp.absPath);
    for (const f of files) {
      const base = path.basename(f, path.extname(f)).toLowerCase();
      if (DOMAIN_LEAF_PATTERNS.includes(base)) {
        if (!groups[base]) groups[base] = [];
        groups[base].push({ file: path.relative(rootDir, f), component: comp.relPath });
      }
    }
  }
  return Object.entries(groups)
    .filter(([, items]) => items.length >= 2)
    .map(([pattern, items]) => ({ pattern, items }));
}

// ---------- 阶段 1：命名空间叶子节点模式 ----------

function groupByLeafNode(components) {
  const groups = {};
  for (const comp of components) {
    const leaf = comp.leaf.toLowerCase();
    if (!groups[leaf]) groups[leaf] = [];
    groups[leaf].push(comp);
  }
  return groups;
}

function classifyLeaf(leaf) {
  if (DOMAIN_LEAF_PATTERNS.includes(leaf)) return 'domain';
  if (INFRA_LEAF_PATTERNS.includes(leaf)) return 'infrastructure';
  return 'other';
}

// ---------- 阶段 2：共享文件/类检测 ----------

const IMPORT_RE = [
  /require\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
  /import\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]/g,
  /export\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]/g,
  /import\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
];

function extractImports(filePath) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (e) {
    return [];
  }
  const imports = new Set();
  for (const re of IMPORT_RE) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(content)) !== null) {
      imports.add(m[1]);
    }
  }
  return [...imports];
}

function listCodeFiles(dir) {
  const result = [];
  function dfs(d) {
    let entries;
    try {
      entries = fs.readdirSync(d, { withFileTypes: true });
    } catch (e) {
      return;
    }
    for (const e of entries) {
      if (e.isDirectory()) {
        if (!SKIP_DIRS.has(e.name)) dfs(path.join(d, e.name));
      } else if (e.isFile() && CODE_EXTENSIONS.has(path.extname(e.name))) {
        result.push(path.join(d, e.name));
      }
    }
  }
  dfs(dir);
  return result;
}

function isExternalImport(spec) {
  if (spec.startsWith('.') || spec.startsWith('/')) return false;
  return true;
}

function isInfraImport(spec) {
  return INFRA_IMPORT_PATTERNS.some((re) => re.test(spec));
}

/**
 * 解析相对导入到绝对路径（尝试常见扩展名与 index 文件）
 */
function resolveImport(spec, fromFile, rootDir) {
  if (!spec.startsWith('.')) return null;
  const base = path.resolve(path.dirname(fromFile), spec);
  const candidates = [
    base,
    ...[...CODE_EXTENSIONS].map((ext) => base + ext),
    ...[...CODE_EXTENSIONS].map((ext) => path.join(base, 'index' + ext)),
  ];
  for (const c of candidates) {
    try {
      if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
    } catch (e) { /* ignore */ }
  }
  return null;
}

function findComponentForFile(absFile, components) {
  let best = null;
  let bestLen = -1;
  for (const comp of components) {
    if (absFile.startsWith(comp.absPath + path.sep) || absFile === comp.absPath) {
      if (comp.absPath.length > bestLen) {
        best = comp;
        bestLen = comp.absPath.length;
      }
    }
  }
  return best;
}

function detectSharedFiles(components, rootDir) {
  // fileAbsPath -> Set(component relPath)
  const fileUsage = new Map();
  // componentRel -> Set(other componentRel)  它依赖了谁
  const compDeps = new Map(components.map((c) => [c.relPath, new Set()]));
  // 外部包使用
  const externalUsage = new Map();

  for (const comp of components) {
    const files = listCodeFiles(comp.absPath);
    for (const file of files) {
      const imports = extractImports(file);
      for (const spec of imports) {
        if (isExternalImport(spec)) {
          if (!isInfraImport(spec)) {
            if (!externalUsage.has(spec)) externalUsage.set(spec, new Set());
            externalUsage.get(spec).add(comp.relPath);
          }
          continue;
        }
        const resolved = resolveImport(spec, file, rootDir);
        if (!resolved) continue;
        const owner = findComponentForFile(resolved, components);
        if (!owner) continue;
        if (owner.relPath === comp.relPath) continue; // 自引用
        compDeps.get(comp.relPath).add(owner.relPath);
        if (!fileUsage.has(resolved)) fileUsage.set(resolved, new Set());
        fileUsage.get(resolved).add(comp.relPath);
      }
    }
  }

  const sharedFiles = [];
  for (const [absFile, users] of fileUsage.entries()) {
    if (users.size >= 2) {
      const owner = findComponentForFile(absFile, components);
      sharedFiles.push({
        file: path.relative(rootDir, absFile),
        owner: owner ? owner.relPath : '(unknown)',
        usedBy: [...users],
      });
    }
  }

  const sharedExternal = [];
  for (const [pkg, users] of externalUsage.entries()) {
    if (users.size >= 2) {
      sharedExternal.push({ pkg, usedBy: [...users] });
    }
  }

  return { sharedFiles, sharedExternal, compDeps };
}

// ---------- 阶段 4：耦合影响评估 ----------

function computeCoupling(components, compDeps) {
  // CA (afferent coupling): 有多少其他组件依赖本组件
  const ca = {};
  for (const comp of components) ca[comp.relPath] = 0;
  for (const [from, deps] of compDeps.entries()) {
    for (const to of deps) {
      if (to in ca) ca[to]++;
    }
  }
  return ca;
}

/**
 * 估算合并后的 CA：合并一组组件后，新组件的 CA =
 * 依赖其中任一旧组件的不同外部组件数量。
 */
function estimateConsolidatedCA(groupRelPaths, compDeps) {
  const dependents = new Set();
  for (const [from, deps] of compDeps.entries()) {
    if (groupRelPaths.includes(from)) continue; // 组内互依赖不计
    for (const to of deps) {
      if (groupRelPaths.includes(to)) dependents.add(from);
    }
  }
  return dependents.size;
}

// ---------- 阶段 3：功能相似度（轻量文本指纹） ----------

function functionFingerprint(comp) {
  const files = listCodeFiles(comp.absPath);
  const fnNames = new Set();
  const re = /(?:function\s+([A-Za-z_$][\w$]*)|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(|([A-Za-z_$][\w$]*)\s*[:=]\s*(?:async\s*)?function)/g;
  for (const f of files) {
    let content;
    try { content = fs.readFileSync(f, 'utf8'); } catch (e) { continue; }
    let m;
    while ((m = re.exec(content)) !== null) {
      const name = m[1] || m[2] || m[3];
      if (name && name.length > 2) fnNames.add(name.toLowerCase());
    }
  }
  return fnNames;
}

function jaccardSimilarity(setA, setB) {
  if (setA.size === 0 && setB.size === 0) return 0;
  let inter = 0;
  for (const x of setA) if (setB.has(x)) inter++;
  const union = setA.size + setB.size - inter;
  return union === 0 ? 0 : inter / union;
}

// ---------- 报告生成 ----------

function generateReport(rootDir, components, asJson) {
  const leafGroups = groupByLeafNode(components);
  const { sharedFiles, sharedExternal, compDeps } = detectSharedFiles(components, rootDir);
  const ca = computeCoupling(components, compDeps);
  const filenamePatterns = detectFilenamePatterns(components, rootDir);

  // 叶子节点重复组（2+ 组件同名叶子）
  const duplicateLeafGroups = [];
  for (const [leaf, comps] of Object.entries(leafGroups)) {
    if (comps.length >= 2) {
      const kind = classifyLeaf(leaf);
      const relPaths = comps.map((c) => c.relPath);
      const beforeCA = relPaths.reduce((s, p) => s + (ca[p] || 0), 0);
      const afterCA = estimateConsolidatedCA(relPaths, compDeps);
      // 功能相似度
      const fingerprints = comps.map((c) => functionFingerprint(c));
      let simSum = 0;
      let simCount = 0;
      for (let i = 0; i < fingerprints.length; i++) {
        for (let j = i + 1; j < fingerprints.length; j++) {
          simSum += jaccardSimilarity(fingerprints[i], fingerprints[j]);
          simCount++;
        }
      }
      const avgSimilarity = simCount > 0 ? simSum / simCount : 0;
      duplicateLeafGroups.push({
        leaf, kind, components: relPaths, beforeCA, afterCA, avgSimilarity,
      });
    }
  }

  // 排序：领域优先，其次相似度，其次 CA 不变
  duplicateLeafGroups.sort((a, b) => {
    const kindOrder = { domain: 0, other: 1, infrastructure: 2 };
    if (kindOrder[a.kind] !== kindOrder[b.kind]) return kindOrder[a.kind] - kindOrder[b.kind];
    if (a.afterCA <= a.beforeCA && b.afterCA > b.beforeCA) return -1;
    if (b.afterCA <= b.beforeCA && a.afterCA > a.beforeCA) return 1;
    return b.avgSimilarity - a.avgSimilarity;
  });

  const result = {
    rootDir: path.resolve(rootDir),
    componentCount: components.length,
    components: components.map((c) => ({ relPath: c.relPath, ca: ca[c.relPath] || 0 })),
    duplicateLeafGroups,
    filenamePatterns,
    sharedFiles: sharedFiles.sort((a, b) => b.usedBy.length - a.usedBy.length),
    sharedExternal: sharedExternal.sort((a, b) => b.usedBy.length - a.usedBy.length),
  };

  if (asJson) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  // Markdown 报告（遵循 SKILL.md 输出格式）
  const lines = [];
  lines.push('# 公共领域组件检测报告');
  lines.push('');
  lines.push(`- 扫描根目录：\`${result.rootDir}\``);
  lines.push(`- 发现组件数：${result.componentCount}`);
  lines.push(`- 同名叶子节点组（≥2）：${duplicateLeafGroups.length}`);
  lines.push(`- 同名领域文件组（≥2）：${filenamePatterns.length}`);
  lines.push(`- 跨组件共享文件（≥2 方使用）：${sharedFiles.length}`);
  lines.push('');

  lines.push('## 组件边界与传入耦合（CA）');
  lines.push('');
  lines.push('| 组件 | CA（被依赖数） |');
  lines.push('| --- | --- |');
  for (const c of result.components) {
    lines.push(`| \`${c.relPath}\` | ${c.ca} |`);
  }
  lines.push('');

  lines.push('## 同名叶子节点模式（阶段 1）');
  lines.push('');
  if (duplicateLeafGroups.length === 0) {
    lines.push('未发现同名叶子节点的重复组件。');
  } else {
    for (const g of duplicateLeafGroups) {
      const kindLabel = g.kind === 'domain' ? '领域功能（合并候选）'
        : g.kind === 'infrastructure' ? '基础设施（不在本 Skill 合并范围）'
        : '其他（需人工确认）';
      lines.push(`### 叶子节点：\`${g.leaf}\` — ${kindLabel}`);
      lines.push('');
      for (const p of g.components) lines.push(`- \`${p}\`（当前 CA=${ca[p] || 0}）`);
      lines.push('');
      lines.push(`- 合并前总 CA：${g.beforeCA}`);
      lines.push(`- 合并后估算 CA：${g.afterCA}`);
      const caDelta = g.afterCA - g.beforeCA;
      lines.push(`- CA 变化：${caDelta > 0 ? '+' + caDelta + '（需关注）' : caDelta === 0 ? '0（无增加，安全）' : caDelta + '（下降）'}`);
      lines.push(`- 函数名指纹平均相似度：${(g.avgSimilarity * 100).toFixed(1)}%`);
      lines.push('');
    }
  }

  lines.push('## 同名领域文件模式（阶段 1 补充）');
  lines.push('');
  lines.push('对应 SKILL.md Node.js 示例：不同组件目录下出现同名领域文件（如 notification.js / audit.js）。');
  lines.push('');
  if (filenamePatterns.length === 0) {
    lines.push('未发现跨组件同名领域文件。');
  } else {
    for (const fp of filenamePatterns) {
      lines.push(`### 文件模式：\`${fp.pattern}.*\`（${fp.items.length} 处）`);
      lines.push('');
      for (const it of fp.items) lines.push(`- \`${it.file}\`（所属组件 \`${it.component}\`）`);
      lines.push('');
    }
  }

  lines.push('## 跨组件共享文件（阶段 2）');
  lines.push('');
  if (sharedFiles.length === 0) {
    lines.push('未发现被 2 个及以上组件共同引用的内部文件。');
  } else {
    lines.push('| 共享文件 | 所属组件 | 使用方数 | 使用方 |');
    lines.push('| --- | --- | --- | --- |');
    for (const s of sharedFiles.slice(0, 50)) {
      lines.push(`| \`${s.file}\` | \`${s.owner}\` | ${s.usedBy.length} | ${s.usedBy.map((u) => '`' + u + '`').join('<br>')} |`);
    }
    if (sharedFiles.length > 50) lines.push(`\n> 仅展示前 50 项，共 ${sharedFiles.length} 项。`);
  }
  lines.push('');

  lines.push('## 合并机会汇总（阶段 5）');
  lines.push('');
  lines.push('| 公共功能 | 组件数 | 合并前 CA | 合并后 CA | 相似度 | 建议 |');
  lines.push('| --- | --- | --- | --- | --- | --- |');
  for (const g of duplicateLeafGroups) {
    let feasibility = '❌ 低';
    let recommendation = '不合并';
    if (g.kind === 'infrastructure') {
      feasibility = '—';
      recommendation = '基础设施，不在本 Skill 范围';
    } else if (g.avgSimilarity >= 0.15 && g.afterCA <= g.beforeCA + 2) {
      feasibility = '✅ 高';
      recommendation = g.leaf.match(/notif|email|audit|report/) ? '共享服务' : '共享库';
    } else if (g.afterCA <= g.beforeCA + 3) {
      feasibility = '⚠️ 中';
      recommendation = '可合并，监控耦合';
    }
    lines.push(`| ${g.leaf} | ${g.components.length} | ${g.beforeCA} | ${g.afterCA} | ${(g.avgSimilarity * 100).toFixed(0)}% | ${feasibility} / ${recommendation} |`);
  }
  lines.push('');

  console.log(lines.join('\n'));
}

// ---------- 主入口 ----------

function main() {
  const args = process.argv.slice(2);
  const asJson = args.includes('--json');
  const target = args.find((a) => !a.startsWith('--')) || process.cwd();

  if (!fs.existsSync(target)) {
    console.error(`错误：目标目录不存在：${target}`);
    process.exit(1);
  }
  const stat = fs.statSync(target);
  if (!stat.isDirectory()) {
    console.error(`错误：目标不是目录：${target}`);
    process.exit(1);
  }

  const components = discoverComponents(target);
  if (components.length === 0) {
    console.error('未发现组件（目标目录下没有直接包含 .js/.ts/.jsx/.tsx/.vue 等代码文件的子目录）。');
    console.error('请确认目标目录是一个前端/Node 仓库，且代码未被编译产物目录掩盖。');
    process.exit(2);
  }
  generateReport(target, components, asJson);
}

main();
