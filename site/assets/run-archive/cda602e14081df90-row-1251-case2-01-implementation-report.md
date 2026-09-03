# GKE JobSet 中断诊断工具 — 实现报告

> Skill：`gke-ai-troubleshooting-jobset-interruption`（分类：自动化与工具）
> 依据：随消息上传的 Skill ZIP 中 `SKILL.md` 为唯一执行标准
> 产物目录：`jobset-diagnostic/`

---

## 一、原始项目问题审阅

上传的最小示例项目包含三个文件，经实际运行（`node test.js`）确认存在以下缺陷：

| 文件 | 问题 | 实际报错 / 现象 |
|------|------|-----------------|
| `test.js` | 导入路径 `./src/app.js`，但 `app.js` 位于项目根目录，`src/` 不存在 | `ERR_MODULE_NOT_FOUND: Cannot find module '.../src/app.js'` |
| `package.json` | 缺少 `"type": "module"`，而 `app.js` 使用 ESM `export` 语法 | 即使路径修复，Node 也会按 CommonJS 解析导致语法错误 |
| `app.js` | 仅含一个与 Skill 领域无关的 `normalizeOrder` 占位函数，无任何诊断逻辑 | 无法体现 JobSet 中断排查能力 |
| `test.js` | 仅做 `console.log`，不是断言式测试，`npm test` 无 pass/fail 语义 | 无法作为可重复验证的回归保障 |
| `package.json` | `scripts.test` 直接调用 `node test.js`，未使用测试框架 | 无测试统计、无失败退出码 |

**结论**：原始项目是一个无法运行的占位脚手架，需重构为符合 Skill 领域的可验证实现。

---

## 二、改进后的实现方案

### 2.1 项目结构

```
jobset-diagnostic/
├── package.json              # 修复：type=module, node --test, engines>=18
├── src/
│   ├── app.js                # 诊断编排主模块（4 步工作流 + 沙箱自治 + Step4 强制顺序）
│   ├── queries.js            # MQL / PromQL / LQL 查询模板（严格对应 SKILL.md Step1-4）
│   ├── timewindow.js         # 时间窗口计算（issue_time ± 30m，相对时间解析）
│   ├── failure_signatures.js # 4 类故障签名匹配 + 修复方案映射
│   └── cli.js                # CLI 入口（离线生成报告 / 查询包）
└── test.js                   # 21 个断言式测试，7 个测试套件
```

### 2.2 核心模块说明

**`src/queries.js`** — 将 SKILL.md 中 Step 1–4 的全部查询规范（MQL 6 条、PromQL 5 条、LQL 3 条）编码为模板常量，提供 `fillTemplate()` 和 `buildStepQueries()` 做变量替换。未提供的变量保留 `{placeholder}`，符合沙箱规则。

**`src/timewindow.js`** — 实现 SKILL.md "Time Handling Rules"：精确时间戳取 ±30 分钟窗口；相对时间（如 `"30 minutes ago"`）先解析再计算；无时间时基于当前时间。

**`src/failure_signatures.js`** — 将 `references/failure_signatures.md` 中的 4 类故障（Spot 抢占、宿主机硬件故障、NCCL 超时、Pod 不可调度）编码为正则签名，输出风险等级和对应修复方案 ID。

**`src/app.js`** — 编排器 `diagnose()` 依次执行 Step 0→1→2→3→4，每步自动推进（SKILL.md 各步均标注 "Proceed to next step automatically"）。支持沙箱模式（无凭据时基于 mock 日志做签名推理）和在线模式占位。

**`src/cli.js`** — 命令行入口，支持 `--cluster`、`--workload`、`--issue-time`、`--mock-logs-file`、`--queries-only` 参数，输出 JSON 报告。

---

## 三、覆盖的两种约束与冲突

### 约束一：自治与沙箱执行规则（无生产凭据）

**冲突**：SKILL.md 诊断工作流依赖 Cloud Logging / Cloud Monitoring 的真实 API 查询，但本环境无 GCP 凭据、无网络访问生产项目。若按常规思路进入"排查 gcloud auth / 获取 access_token"循环，将违反 SKILL.md 明确禁止的行为。

**SKILL.md 原文规则**：
> If API queries, tools, or commands encounter `403 Permission Denied`, authentication errors, or network isolation, **do NOT enter authentication or credential troubleshooting loops**. Populate the query templates with the acquired variables, inspect any locally staged telemetry or mock data files if available, and complete the diagnostic workflow and resolution recommendations autonomously.

**实现方式**：
- `diagnose()` 默认 `sandbox=true`，所有查询以已填充模板形式输出，不发起网络请求。
- 若提供 `mock_logs`（本地文件或字符串），则对其做故障签名匹配，输出诊断结论和修复建议。
- 报告中显式标注 `mode: "sandbox-offline"` 并附带警告，说明结论依据。
- 测试用例 `沙箱模式下不应抛出认证错误，应输出模板与警告` 验证此约束。

**取舍**：放弃实时遥测的精确性，换取完全离线、可重复、零凭据依赖的可验证性。查询模板本身可直接复制到有凭据环境执行，实现"一次编写、两处可用"。

### 约束二：Step 4 强制执行顺序（Pod 阶段 → 不可调度 → Worker 日志）

**冲突**：排查者的直觉是直接看 Worker 容器日志找 NCCL 报错，但 SKILL.md 强制要求先评估整体负载健康度（Pod 生命周期阶段 + 不可调度 Pod 数），再深入具体日志。跳过 A/B 可能导致误判（例如把资源不足导致的 Pending 误判为应用崩溃）。

**SKILL.md 原文规则**：
> **Required Execution Order**: You MUST analyze pod status phases (Section A) and unschedulable pod metrics (Section B) to assess overall workload health before inspecting specific worker container logs (Section C).

**实现方式**：
- `app.js` 中 Step 4 被拆为 `sections.A`（order=1）、`sections.B`（order=2）、`sections.C`（order=3）。
- 每步执行后校验 `execution_order_valid = (A.order===1 && B.order===2 && C.order===3)`。
- 测试用例 `Step 4 应包含 A、B、C 三个子步骤且顺序为 1→2→3` 和端到端场景二验证此约束。

**取舍**：增加了编排器的结构复杂度，但确保诊断逻辑不会因"跳步"而产生假阳性结论。

---

## 四、关键取舍、依赖与风险

### 4.1 取舍

| 取舍点 | 选择 | 理由 |
|--------|------|------|
| 测试框架 | Node.js 内置 `node:test` | 零外部依赖，`npm install` 即可运行，符合"最小示例"定位 |
| 模块系统 | ESM (`"type": "module"`) | 与原始 `app.js` 的 `export` 语法一致，修复而非推翻 |
| 故障匹配 | 正则签名 vs LLM 推理 | 正则确定性高、可测试、离线可用；LLM 推理需外部依赖且不可重复 |
| 在线模式 | 仅占位不实现 | SKILL.md 禁止在无凭据时进入认证循环；在线执行需用户自行提供凭据 |
| 原始 `normalizeOrder` | 移除 | 与 Skill 领域无关，保留会造成职责混乱 |

### 4.2 依赖

- **运行时**：Node.js >= 18（使用 `node:test`、顶层 await）
- **零 npm 依赖**：全部使用 Node.js 内置模块（`fs`、`test`、`assert`）
- **Skill 资产**：查询模板和故障签名均来自 Skill ZIP 内文件，无外部数据源

### 4.3 风险

1. **正则签名漏报**：故障日志格式可能随 GKE 版本变化，当前签名基于 `failure_signatures.md` 中的示例，实际生产中可能出现未覆盖的变体。缓解：签名库可扩展，新增 pattern 无需改动编排逻辑。
2. **沙箱结论的局限性**：无真实遥测时，诊断结论仅基于 mock 日志文本，无法确认指标趋势（如重启频率是否递增）。缓解：报告中明确标注模式和数据来源。
3. **高风险操作未自动化**：Resolution 2（隔离故障宿主机）涉及 cordon/drain/删除 VM，属于不可逆操作，本工具仅输出建议不自动执行。这符合 SKILL.md 将其标注为 `[High Risk]` 的定位。
4. **查询模板与实际 API 的兼容性**：MQL/PromQL/LQL 模板严格抄录自 SKILL.md，若 GKE 监控指标名称变更需同步更新。

---

## 五、验证结果

### 5.1 测试执行

```
$ node --test test.js
# tests 21
# suites 7
# pass 21
# fail 0
# duration_ms 490
```

7 个测试套件覆盖：查询模板填充（3）、时间窗口计算（4）、故障签名匹配（6）、沙箱自治规则（3）、Step4 强制顺序（2）、查询包生成（1）、端到端约束场景（2）。

### 5.2 CLI 冒烟测试

无 mock 日志时输出 4 步查询模板 + 通用修复建议；有 mock 日志（含 4 类故障签名）时正确识别全部 4 类故障、输出对应修复方案（resolution_1 + resolution_2）、Step4 顺序校验通过。

### 5.3 原始项目对比

| 维度 | 原始项目 | 改进后 |
|------|----------|--------|
| 能否运行 | 否（路径错误） | 是 |
| 测试 | 无断言 | 21 个断言，全通过 |
| 领域逻辑 | 无（占位函数） | 完整 4 步诊断工作流 |
| 凭据依赖 | 不适用 | 零依赖（沙箱模式） |
| 可重复性 | 无 | 离线可重复 |

---

## 六、实际读取的 Skill 文件相对路径

以下文件均已实际读取并作为实现依据：

1. `gke-ai-troubleshooting-jobset-interruption/SKILL.md` — 主工作流定义（2732 tokens）
2. `gke-ai-troubleshooting-jobset-interruption/references/failure_signatures.md` — 4 类故障签名示例（646 tokens）
3. `gke-ai-troubleshooting-jobset-interruption/scripts/validate_queries.sh` — LQL/PromQL 校验脚本参考（923 tokens）

---

## 七、确实影响结果的 SKILL.md 规则

**自治与沙箱执行规则（Autonomous & Sandbox Execution Rule）** 是对实现结果影响最大的规则：

- 它直接决定了本工具**不实现**真实 GCP API 调用层，而是采用"模板输出 + 本地签名推理"的离线架构。
- 它禁止进入凭据排查循环，因此 `diagnose()` 在无凭据时不会尝试 `gcloud auth` 或获取 access_token，而是直接填充模板并完成诊断。
- 它影响了测试设计：核心测试套件全部在沙箱模式下运行，验证工具在零凭据环境中仍能产出有意义的诊断结论。

若没有这条规则，实现路径可能是构建一个依赖 `@google-cloud/monitoring` 和 `@google-cloud/logging` 的在线客户端，这将引入外部依赖、凭据管理和网络需求，与本任务"不得访问生产凭据"的约束直接冲突。

---

## 八、复测方法

```bash
cd jobset-diagnostic
npm test                  # 运行 21 个测试
node src/cli.js --cluster my-cluster --workload my-jobset --issue-time "2026-05-20T08:15:00Z"
node src/cli.js --cluster my-cluster --workload my-jobset --mock-logs-file /path/to/logs.txt
node src/cli.js --cluster my-cluster --workload my-jobset --queries-only
```

所有命令均为一次性执行，不启动持续运行的服务，无网络请求，无凭据要求。
