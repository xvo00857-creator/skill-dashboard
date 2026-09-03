#!/usr/bin/env node
/**
 * validate-ownership.js
 * 依据 parallel-feature-development SKILL.md 静态校验文件归属矩阵。
 *
 * 校验项：
 *   R1 「The Cardinal Rule」：一个文件只能有一个 owner
 *   R2 契约文件（contracts 列表）必须归 lead 所有，且对其余实现者只读
 *   R3 barrel/index 文件必须恰好有一个 owner（Troubleshooting: index.ts/__init__.py）
 *   R4 每个 owner 至少分配一个文件（避免空工作流）
 *   R5 跨集群依赖只能通过契约文件对接（crossClusterDependencies.via 必须是 contracts 中的文件）
 *
 * 设计约束：
 *   - 只读：脚本只读取 ownership-matrix.json，不创建/修改/删除任何文件（幂等，可重复运行）
 *   - 无外部依赖：仅使用 Node.js 内置模块
 *   - 退出码：0 = 全部通过；1 = 存在违规；2 = 用法/读取错误
 *
 * 用法：
 *   node validate-ownership.js                 # 校验同目录下的 ownership-matrix.json
 *   node validate-ownership.js --self-test     # 注入违规样例，验证检测器本身有效
 */

const fs = require("fs");
const path = require("path");

const SELF_TEST = process.argv.includes("--self-test");

function loadMatrix() {
  if (SELF_TEST) {
    // 故意构造违规矩阵，验证检测器能否抓到：
    //  - login.ts 同时分给 implementer-1 和 implementer-2（违反 R1）
    //  - 契约文件分给 implementer-1（违反 R2）
    //  - index.ts 同时分给 lead 和 implementer-3（违反 R3）
    //  - implementer-4 文件列表为空（违反 R4）
    //  - 跨集群依赖 via 指向非契约文件（违反 R5）
    return {
      feature: "自检：故意违规矩阵",
      owners: {
        lead: ["src/types/auth-contract.ts", "src/api/auth/index.ts"],
        "implementer-1": [
          "src/api/auth/login.ts",
          "src/types/auth-contract.ts", // R2 违规
        ],
        "implementer-2": ["src/api/auth/login.ts"], // R1 违规
        "implementer-3": ["src/middleware/auth.ts", "src/api/auth/index.ts"], // R3 违规
        "implementer-4": [], // R4 违规
      },
      contracts: ["src/types/auth-contract.ts"],
      barrelFiles: ["src/api/auth/index.ts"],
      crossClusterDependencies: [
        { from: "implementer-1", to: "implementer-3", via: "src/middleware/auth.ts" }, // R5 违规
      ],
    };
  }
  const matrixPath = path.join(__dirname, "ownership-matrix.json");
  const raw = fs.readFileSync(matrixPath, "utf-8");
  return JSON.parse(raw);
}

function normalize(p) {
  return p.trim().replace(/\\/g, "/").replace(/\/+$/, "");
}

function validate(matrix) {
  const errors = [];
  const owners = matrix.owners || {};
  const contracts = new Set((matrix.contracts || []).map(normalize));
  const barrels = new Set((matrix.barrelFiles || []).map(normalize));

  // R1: 一个文件一个 owner
  const fileToOwners = new Map();
  for (const [owner, files] of Object.entries(owners)) {
    if (!Array.isArray(files)) {
      errors.push(`[R4] owner "${owner}" 的文件列表不是数组`);
      continue;
    }
    for (const f of files.map(normalize)) {
      if (!f) continue;
      if (!fileToOwners.has(f)) fileToOwners.set(f, []);
      fileToOwners.get(f).push(owner);
    }
  }
  for (const [f, list] of fileToOwners) {
    if (list.length > 1) {
      errors.push(`[R1] 文件 "${f}" 被分配给多个 owner: ${list.join(", ")}（违反 Cardinal Rule）`);
    }
  }

  // R2: 契约文件必须归 lead
  for (const c of contracts) {
    const list = fileToOwners.get(c) || [];
    if (list.length !== 1 || list[0] !== "lead") {
      errors.push(`[R2] 契约文件 "${c}" 必须归 lead 所有，当前: ${list.join(", ") || "未分配"}`);
    }
  }

  // R3: barrel 文件恰好一个 owner
  for (const b of barrels) {
    const list = fileToOwners.get(b) || [];
    if (list.length !== 1) {
      errors.push(`[R3] barrel 文件 "${b}" 必须恰好有一个 owner，当前: ${list.join(", ") || "未分配"}`);
    }
  }

  // R4: 每个 owner 至少一个文件
  for (const [owner, files] of Object.entries(owners)) {
    if (Array.isArray(files) && files.length === 0) {
      errors.push(`[R4] owner "${owner}" 没有分配任何文件`);
    }
  }

  // R5: 跨集群依赖 via 必须是契约文件
  for (const dep of matrix.crossClusterDependencies || []) {
    const via = normalize(dep.via || "");
    if (via && !contracts.has(via)) {
      errors.push(
        `[R5] 跨集群依赖 ${dep.from} → ${dep.to} 通过 "${via}" 对接，但该文件不在契约列表中；` +
          `跨集群只能通过 lead 拥有的契约文件对接`
      );
    }
  }

  return errors;
}

function main() {
  let matrix;
  try {
    matrix = loadMatrix();
  } catch (e) {
    console.error("读取/解析 ownership-matrix.json 失败：", e.message);
    process.exit(2);
  }

  const errors = validate(matrix);
  const totalFiles = new Set(
    Object.values(matrix.owners || {})
      .flat()
      .map(normalize)
  ).size;

  console.log("=== 文件归属矩阵校验 ===");
  console.log(`特性：${matrix.feature || "(未命名)"}`);
  console.log(`owner 数：${Object.keys(matrix.owners || {}).length}，文件数：${totalFiles}`);
  console.log(`契约文件：${(matrix.contracts || []).join(", ") || "(无)"}`);
  console.log(`barrel 文件：${(matrix.barrelFiles || []).join(", ") || "(无)"}`);
  console.log("");

  if (SELF_TEST) {
    console.log("（自检模式：已注入 5 类违规，预期全部被检出）");
    console.log("");
  }

  if (errors.length === 0) {
    console.log("结果：通过 ✓");
    console.log(" - R1 Cardinal Rule：无文件被多 owner 共有");
    console.log(" - R2 契约文件：均归 lead 所有");
    console.log(" - R3 barrel 文件：均唯一 owner");
    console.log(" - R4 owner 分配：无空 owner");
    console.log(" - R5 跨集群依赖：均通过契约文件对接");
    process.exit(0);
  } else {
    console.log(`结果：失败 ✗（共 ${errors.length} 项违规）`);
    for (const e of errors) console.log("  " + e);
    process.exit(1);
  }
}

main();
