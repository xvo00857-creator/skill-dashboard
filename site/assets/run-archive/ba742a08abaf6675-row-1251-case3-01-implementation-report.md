# 实现报告：最小示例项目审阅与改进

> 执行依据：Skill `gke-ai-troubleshooting-jobset-interruption`（分类：Containers / 自动化与工具）
> 报告生成时间：2026-08-26
> 所有验证均在本地沙箱完成，未访问任何生产凭据或外部集群。

---

## 一、实际读取的 Skill 文件清单

| 相对路径 | 作用 |
|---|---|
| `gke-ai-troubleshooting-jobset-interruption/SKILL.md` | 主技能文档：诊断工作流、查询模板、沙箱规则、解决方案 |
| `gke-ai-troubleshooting-jobset-interruption/references/failure_signatures.md` | 失败签名参考：抢占事件、主机硬件故障、NCCL 超时、不可调度示例 |
| `gke-ai-troubleshooting-jobset-interruption/scripts/validate_queries.sh` | LQL/PromQL 查询校验脚本（依赖 gcloud 与 GMS 访问令牌） |

---

## 二、影响结果的 SKILL.md 关键规则

### 规则 1：Autonomous & Sandbox Execution Rule（确实影响执行路径）

> 原文：If API queries, tools, or commands encounter `403 Permission Denied`, authentication errors, or network isolation, **do NOT enter authentication or credential troubleshooting loops**. Populate the query templates with the acquired variables, inspect any locally staged telemetry or mock data files if available, and complete the diagnostic workflow and resolution recommendations autonomously.

**对本题的影响**：本环境无 GCP 项目凭据、无 `gcloud` 认证、无集群访问权限。按此规则，不进入凭据排障循环，而是：
- 不运行 `scripts/validate_queries.sh`（它依赖 `gcloud auth print-access-token`，会触发 401/403）；
- 将诊断方法论（先整体健康后深入细节、证据分级、低风险/高风险动作区分）迁移应用到本地 Node.js 项目审阅；
- 所有结论基于本地文件的实际读取与可复现运行结果。

### 规则 2：Step 4 Required Execution Order（确实影响分析顺序）

> 原文：You MUST analyze pod status phases (Section A) and unschedulable pod metrics (Section B) to assess overall workload health before inspecting specific worker container logs (Section C).

**对本题的影响**：迁移为"先检查项目整体可运行性，再深入函数级缺陷"。实际顺序：
1. **整体健康**：`npm test` 能否运行？→ 发现路径不匹配 + ESM 类型缺失，项目完全无法启动；
2. **深入诊断**：在项目可运行后，再检查 `normalizeOrder` 的 NaN、负值、对象 id、公式注入等字段级缺陷。

若跳过整体健康直接改函数，会遗漏"项目根本跑不起来"这一最严重问题。

### 规则 3：Resolution Risk Level 区分

> 原文将解决方案分为 `[Low Risk]`（如切换按需虚拟机）和 `[High Risk]`（如隔离故障主机、删除 GCE 实例）。

**对本题的影响**：改进措施按风险分级：
- **低风险（已实施）**：补 `"type":"module"`、创建 `src/` 目录对齐导入路径、增加 NaN/负值/公式注入校验、CSV 审计；
- **高风险（未实施，仅建议）**：修改原始 `app.js` 在根目录的位置（可能影响其他依赖方）、引入第三方 CSV 解析库（增加依赖）。

---

## 三、原始项目缺陷诊断

### 3.1 整体健康检查（项目无法运行）

| 编号 | 缺陷 | 证据 | 严重度 |
|---|---|---|---|
| D1 | `test.js` 从 `./src/app.js` 导入，但 `app.js` 在项目根目录 | 运行 `node test.js` 报 `ERR_MODULE_NOT_FOUND: Cannot find module '/.../src/app.js'` | 致命 |
| D2 | `package.json` 缺少 `"type": "module"` | Node.js 输出 `MODULE_TYPELESS_PACKAGE_JSON` 警告，ESM 语法需重解析 | 高 |

**复现命令**：
```bash
cd <原始项目目录> && node test.js
# Error [ERR_MODULE_NOT_FOUND]: Cannot find module '.../src/app.js'
```

### 3.2 深入诊断（函数级缺陷）

对原始 `app.js` 的 `normalizeOrder` 逐项测试：

| 编号 | 缺陷 | 输入 | 原始输出 | 期望行为 |
|---|---|---|---|---|
| D3 | 非数字金额静默产生 `NaN` | `{id:1, amount:"abc"}` | `{id:"1", amount:null}`（JSON 序列化 NaN 为 null） | 应抛出 `invalid amount` |
| D4 | `NaN` 金额被 falsy 逻辑吞掉 | `{id:1, amount:NaN}` | `{id:"1", amount:0}` | 应抛出或标记警告 |
| D5 | 对象 id 静默转为 `"[object Object]"` | `{id:{a:1}}` | `{id:"[object Object]", amount:0}` | 应抛出 `order id must be a primitive` |
| D6 | 不检测负值 | `{id:1, amount:-50}` | `{id:"1", amount:-50}` 无警告 | 应标记 `negative amount` 警告 |
| D7 | 不检测公式注入 | `{id:1, amount:"=HYPERLINK(...)"}` | `Number("=HYPERLINK(...)")` = NaN，静默 | 应检测并拒绝 |

**复现命令**：
```bash
node --input-type=module -e '
import { normalizeOrder } from "./app.js";
console.log(JSON.stringify(normalizeOrder({id:1, amount:"abc"})));
console.log(JSON.stringify(normalizeOrder({id:{a:1}})));
'
```

### 3.3 edge_cases.csv 边界场景审计

原始项目无任何 CSV 处理能力。对 `edge_cases.csv`（6 条数据行）人工审计发现：

| record_id | 行号 | 问题类型 | 详情 |
|---|---|---|---|
| 2 | 3, 4 | **重复** | record_id=2 出现两次（第 3 行和第 4 行完全相同） |
| 3 | 5 | **缺失** | status 为空、value 为空 |
| 4 | 6 | **异常** | status=error，value=-999（负值） |
| 5 | 7 | **不安全** | value=`=HYPERLINK("https://example.invalid","do not execute")`（CSV 公式注入） |
| 1 | 2 | 正常 | 无问题 |

---

## 四、改进方案与实施

### 4.1 项目结构修正

```
project_improved/
├── package.json          # 增加 "type": "module"，版本升至 1.1.0
├── src/
│   └── app.js            # 对齐 test.js 的导入路径 ./src/app.js
├── test.js               # 零依赖测试套件（node:assert）
└── edge_cases.csv        # 输入数据（原样保留）
```

### 4.2 package.json 修正

```json
{
  "name": "wechat-skill-eval-sample",
  "version": "1.1.0",
  "private": true,
  "type": "module",
  "scripts": { "test": "node test.js" }
}
```

变更点：新增 `"type": "module"`（修复 D2），版本号升至 1.1.0。

### 4.3 src/app.js 改进

`normalizeOrder` 改进要点：

1. **整体健康检查前置**：先校验订单对象是否存在且为非数组对象，再校验 id 存在且为原始类型（修复 D5）；
2. **金额严格校验**：空值默认 0 并警告；非数字抛出 `invalid amount`（修复 D3、D4）；
3. **公式注入检测**：字符串金额以 `= + - @` 开头时标记为潜在注入并拒绝（修复 D7）；
4. **负值降级处理**：负值不阻断但返回 `warnings: ["negative amount"]`，由上层决定拒收或放行（修复 D6）；
5. **返回结构化结果**：`{ id, amount, warnings }`，warnings 数组承载可恢复异常。

新增 `parseCSVLine`：兼容标准 RFC 4180（`""` 转义）和反斜杠转义（`\"`，与实际 edge_cases.csv 一致），正确处理引号内逗号。

新增 `auditEdgeCases`：对 CSV 做四类审计——重复（按 record_id）、缺失（status/value 空值）、异常（负值）、不安全（公式注入），返回结构化 `{ records, issues }`。

### 4.4 test.js 改进

从零依赖 `node:assert/strict` 构建 18 项测试，覆盖：
- `normalizeOrder`：正常用例 + 9 项边界（缺失对象、缺失 id、对象 id、金额缺失、非数字金额、负值、公式注入、金额为 0）；
- `parseCSVLine`：普通行、反斜杠转义引号、标准双引号转义；
- `auditEdgeCases`：基于真实 edge_cases.csv 的 6 项断言（行数、重复、缺失、异常、不安全、四类全覆盖）。

---

## 五、验证结果

### 5.1 改进项目测试

```
$ cd project_improved && node test.js

== normalizeOrder 测试 ==
  ✓ 正常订单：数字 id 与字符串金额
  ✓ 缺失订单对象 → 抛出
  ✓ 缺失 order id → 抛出
  ✓ id 为对象 → 抛出
  ✓ 金额缺失 → 默认 0 并警告
  ✓ 金额为非数字字符串 → 抛出 invalid amount
  ✓ 金额为负值 → 不阻断但警告
  ✓ 金额为公式注入字符串 → 抛出 invalid amount 并警告
  ✓ 金额为 0 → 正常（不被 falsy 误判为缺失）

== parseCSVLine 测试 ==
  ✓ 普通行解析
  ✓ 带引号且含逗号的字段（反斜杠转义，与实际 edge_cases.csv 一致）
  ✓ 带引号且含逗号的字段（标准 RFC 4180 双引号转义）

== auditEdgeCases 测试（基于 edge_cases.csv） ==
  ✓ CSV 解析出 6 条数据行
  ✓ 检测到重复 record_id=2
  ✓ 检测到 record_id=3 缺失 status 和 value
  ✓ 检测到 record_id=4 异常负值
  ✓ 检测到 record_id=5 公式注入（unsafe）
  ✓ issue 类型覆盖 duplicate/missing/abnormal/unsafe 四类

== 结果：18 passed, 0 failed ==
```

**退出码：0**

### 5.2 原始项目对比验证

```
$ node test.js（原始项目）
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '.../src/app.js'
# 退出码：1
```

```
$ node --input-type=module -e '...原始 normalizeOrder...'
amount=abc => {"id":"1","amount":null}     # NaN 静默
id=object => {"id":"[object Object]","amount":0}  # 静默 corruption
# 退出码：0（无任何报错）
```

---

## 六、阻断项与降级方案

### 6.1 无法完成的事项及原因

| 事项 | 阻断原因 | 证据 |
|---|---|---|
| 运行 `scripts/validate_queries.sh` | 依赖 `gcloud auth print-access-token` 与 GMS API，本环境无 GCP 凭据、无网络到 `monitoring.googleapis.com` | 脚本内含 `gcloud logging read` 和 `curl ... monitoring.googleapis.com`，未认证时返回 401/403 |
| 执行 SKILL.md 中的 MQL/PromQL/LQL 查询 | 无目标 GKE 集群、无 `{project_id}`/`{cluster_name}`/`{workload_name}` 实际值 | 本任务输入为 Node.js 项目文件，非 GKE 遥测数据 |
| 隔离故障主机 VM（Resolution 2） | 属于 `[High Risk]` 操作，需要 GCE 实例删除权限，且本环境无对应主机 | SKILL.md 明确标记为 High Risk |

### 6.2 降级方案

1. **查询校验降级**：不运行 `validate_queries.sh`，但人工核对 SKILL.md 中所有 LQL filter 语法（`resource.type`、`resource.labels.cluster_name`、`timestamp` 范围）与 PromQL 指标名，确认模板变量占位符 `{cluster_name}` 等格式正确；
2. **诊断方法论迁移**：将 Skill 的"先整体后局部、证据分级、风险分级"框架应用于 Node.js 项目审阅，确保分析过程可复现；
3. **GKE 诊断复测方法**：若后续获得 GCP 凭据，按以下步骤复测——
   ```bash
   export PROJECT_ID=<你的项目>
   export CLUSTER_NAME=<集群名>
   export WORKLOAD_NAME=<JobSet名>
   # 1. 校验 LQL 查询
   bash scripts/validate_queries.sh
   # 2. 按 SKILL.md Step 1-4 依次执行 MQL/PromQL/LQL 查询
   # 3. 将查询结果与 failure_signatures.md 中的签名比对
   ```

---

## 七、复测方法（改进项目）

```bash
# 1. 进入改进项目目录
cd project_improved

# 2. 运行全部测试（零依赖，仅需 Node.js >= 18）
node test.js
# 预期：18 passed, 0 failed，退出码 0

# 3. 单独验证 normalizeOrder
node --input-type=module -e '
import { normalizeOrder } from "./src/app.js";
console.log(normalizeOrder({ id: 42, amount: "19.9" }));
// { id: "42", amount: 19.9, warnings: [] }
'

# 4. 单独验证 CSV 审计
node --input-type=module -e '
import { readFileSync } from "fs";
import { auditEdgeCases } from "./src/app.js";
const { issues } = auditEdgeCases(readFileSync("./edge_cases.csv", "utf-8"));
console.log(JSON.stringify(issues, null, 2));
'
```

---

## 八、结论

1. **原始项目无法运行**：`test.js` 导入路径与 `app.js` 实际位置不匹配（D1），且 `package.json` 缺 ESM 声明（D2），`npm test` 直接崩溃。
2. **原始 `normalizeOrder` 存在 5 项函数级缺陷**：NaN 静默（D3/D4）、对象 id 静默 corruption（D5）、负值无告警（D6）、公式注入无检测（D7）。
3. **edge_cases.csv 含 4 类边界问题**：重复（record_id=2）、缺失（record_id=3）、异常负值（record_id=4）、公式注入（record_id=5）。原始项目无 CSV 处理能力。
4. **改进项目已全部修复并通过 18 项测试**：零依赖、纯本地可复现、退出码 0。
5. **GKE 相关查询因无凭据未执行**：按 SKILL.md 的 Autonomous & Sandbox Execution Rule，未进入凭据排障循环，改为方法论迁移 + 人工语法核对 + 提供复测方法。
