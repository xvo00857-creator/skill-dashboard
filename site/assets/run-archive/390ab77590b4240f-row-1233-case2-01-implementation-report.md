# 实现报告：Agent Platform 调优任务管理 —— 最小示例项目审阅与改进

## 一、结论概述

本项目对随消息上传的最小示例（`package.json` / `app.js` / `test.js`）进行了审阅和改进，并严格依据 Skill `agent-platform-tuning-management` 的 `SKILL.md` 扩展了调优任务管理模块。

**核心结论：**

1. **原示例存在 3 个可阻断运行的缺陷**：导入路径不匹配（`test.js` 引用 `./src/app.js` 但文件在根目录）、缺少 ESM 声明（`package.json` 无 `"type": "module"` 但 `app.js` 使用 `export`）、测试仅做 `console.log` 无断言。均已修复。
2. **Skill 领域与示例项目领域不匹配**：Skill 管理 Google Cloud Vertex AI 的 GenAI 调优任务（Python SDK），示例是 Node.js 订单归一化工具。本报告将两者整合：保留订单模块作为业务逻辑示例，新增调优管理模块严格遵循 Skill 规则。
3. **因无 GCP 生产凭据，采用 Mock 客户端实现可重复本地验证**。真实 `PythonSdkClient` 已按 Skill 示例代码实现，待凭据就绪即可切换，无需修改上层逻辑。
4. **全部 22 项自动化测试通过**，覆盖订单归一化、安全分级、工作流决策树、资源校验四大场景。

---

## 二、实际读取的 Skill 文件

| 相对路径 | 说明 |
|---|---|
| `agent-platform-tuning-management/SKILL.md` | Skill 主文件，含安全分级、环境初始化、工作流决策树、Python SDK 三段示例 |

ZIP 包内仅含此一个文件，无其他资产（无脚本、无模板、无参考配置）。

---

## 三、确实影响结果的 SKILL.md 规则

以下规则直接决定了实现方案的选择，而非可有可无的建议：

### 规则 1：Tier D 取消操作必须获得显式确认，且严禁在同一轮中同时输出确认提示和执行代码

> 原文："NEVER pre-emptively provide or execute any cancellation code before receiving the user's response in a new turn. Asking for confirmation and providing the code in a single parallel turn is a severe safety violation."

**影响**：`TuningManager` 将取消拆分为 `requestCancel()`（仅返回确认提示）和 `confirmCancel(jobId, confirmation)`（校验确认短语后才执行）两个独立方法。测试中专门验证了无效确认短语会被拒绝。这不是设计偏好，而是 Skill 的强制安全约束。

### 规则 2：环境初始化不得创建虚拟环境，必须先探测再按需安装

> 原文："Do not create a virtual environment — it starts empty and hides packages the environment already provides, forcing a redundant install. Probe, and install only what is missing."

**影响**：`scripts/probe_env.py` 使用 `importlib.util.find_spec` 探测 `vertexai`，仅输出安装建议而不自动执行 `pip install`。本报告的验证环境中探测结果为 `vertexai_installed: false`、`adc_configured: false`，正确退出码为 1，未尝试创建 venv 或安装。

### 规则 3：资源错误（403/404/INVALID_ARGUMENT）必须立即停止，不得重试

> 原文："you MUST inform the user that the project or tuning job does not exist or cannot be accessed... Do NOT retry or loop, do NOT assume the resource is valid."

**影响**：`tuning-client.js` 导出 `isResourceError()` 识别错误码，`TuningManager._handleResourceError()` 在捕获到此类错误时标记 `err.blocking = true` 并附加 `userAction` 提示。测试验证了 403 和 404 均被正确标记，上层不得循环重试。

---

## 四、原示例项目的缺陷

| # | 缺陷 | 位置 | 后果 |
|---|---|---|---|
| 1 | `test.js` 导入 `./src/app.js`，但 `app.js` 在项目根目录 | `test.js` 第 1 行 | `Error: Cannot find module` |
| 2 | `package.json` 无 `"type": "module"`，但 `app.js` 使用 ESM `export` | `package.json` | `SyntaxError: Unexpected token 'export'` |
| 3 | 测试仅 `console.log` 输出，无断言、无退出码 | `test.js` | 无法作为自动化验证手段 |
| 4 | `normalizeOrder` 对负金额、非数字金额、超大金额无防御 | `app.js` | 非法数据可进入下游 |
| 5 | 无批量处理能力，单条异常会中断整批 | `app.js` | 不满足真实业务批处理场景 |

---

## 五、改进内容

### 5.1 项目结构

```
agent-platform-tuning-project/
├── package.json              # 新增 type:module、scripts
├── test.js                   # 22 项断言测试，零外部依赖
├── src/
│   ├── app.js                # 修复并增强的订单归一化
│   ├── tuning-client.js      # 客户端抽象（Mock + PythonSdk）
│   └── tuning-manager.js     # 调优管理器（安全分级/决策树/资源校验）
└── scripts/
    └── probe_env.py          # Python 环境探测（不建 venv）
```

### 5.2 订单归一化增强（`src/app.js`）

- 保留原始函数签名 `normalizeOrder(order)`，向后兼容
- 新增输入类型校验（非对象、空 ID）
- 新增金额校验（非数字、负数、超大值）
- 金额保留两位小数（`Math.round(amount * 100) / 100`）
- ID 自动 `trim()`
- 新增 `normalizeOrders()` 批量方法，成功/错误分离，单条失败不阻断整批

### 5.3 调优管理模块（`src/tuning-manager.js` + `src/tuning-client.js`）

**客户端抽象层**：
- `MockTuningClient`：纯内存实现，支持注入任务、模拟 403 权限错误，用于本地无凭据验证
- `PythonSdkClient`：通过 `node:child_process` 调用 `python3 -c`，生成的 Python 代码严格对应 SKILL.md 中的三段示例（list / get / cancel），不做任何超出 Skill 范围的扩展

**管理器安全分级**：

| 操作 | 分级 | 确认要求 | 方法 |
|---|---|---|---|
| 列出任务 | Tier R | 无需 | `listJobs()` |
| 获取任务详情 | Tier R | 无需 | `getJob(jobId)` |
| 请求取消 | Tier D | 返回确认提示 | `requestCancel(jobId)` |
| 确认取消 | Tier D | 校验 "I confirm" / "Yes, cancel it" | `confirmCancel(jobId, confirmation)` |

**工作流决策树**：`checkContext()` 校验 `projectId` 和 `region`，缺失时抛出明确错误，不自行猜测区域。

**资源校验**：`isResourceError()` 识别 `403` / `404` / `PERMISSION_DENIED` / `NOT_FOUND` / `INVALID_ARGUMENT`，命中后标记 `blocking` 并附加用户操作建议。

### 5.4 环境探测（`scripts/probe_env.py`）

- 探测 `vertexai` / `google.cloud.aiplatform` 可导入性（兼容父包缺失时的异常）
- 探测 `gcloud` CLI 可用性
- 探测 ADC 凭据文件（含 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量）
- 输出 JSON，退出码：0=就绪，1=缺依赖，2=缺凭据
- **不创建 venv，不自动安装**，仅输出建议命令

---

## 六、覆盖的约束与冲突（至少两种）

### 冲突一：Skill 领域（Python/GCP 调优管理）vs 示例项目领域（Node.js 订单归一化）

**表现**：Skill 的全部代码示例是 Python + `google.cloud.aiplatform_v1`，而示例项目是 Node.js ESM。两者无直接交集。

**取舍**：不强行将订单逻辑改写为 Python（会丢失示例项目的原始意图），也不忽略 Skill（会偏离任务要求）。采用**双模块共存**方案：订单模块保留为业务逻辑示例，调优管理模块作为 Skill 规则的实现载体。两者通过同一项目的测试套件统一验证。

**风险**：双模块增加了项目的认知负担。缓解：`package.json` 的 `description` 明确标注了双重定位，文档中分区说明。

### 冲突二：Skill 要求 GCP 凭据 vs 任务约束"不得访问生产凭据"

**表现**：Skill Phase 0 要求 `gcloud auth login` 和 `gcloud auth application-default login`，但任务明确禁止访问生产凭据，且当前环境无 `gcloud` CLI。

**取舍**：实现 `MockTuningClient` 使全部安全逻辑可在本地无凭据环境下重复验证；同时保留 `PythonSdkClient` 作为生产环境的即插即用实现。`probe_env.py` 正确报告环境未就绪（退出码 1），不假装成功。

**风险**：Mock 客户端无法验证真实 GCP API 的响应格式差异。缓解：`PythonSdkClient` 生成的 Python 代码与 SKILL.md 示例逐行对应，输出解析器针对 Skill 示例中的 `print` 格式编写；切换到真实环境后可通过 `listJobs()` 的首次调用快速验证。

### 冲突三（附加）：Tier D 取消的安全确认 vs 自动化测试的可执行性

**表现**：Skill 要求取消操作必须等待用户在新的一轮中输入确认，但自动化测试需要在单次运行中完成验证。

**取舍**：将确认机制实现为纯函数 `isCancelConfirmed(input)` 和两步法 `requestCancel` / `confirmCancel`。测试直接调用 `confirmCancel` 并传入有效确认短语，模拟用户已完成确认的状态；同时单独测试无效确认被拒绝。这既遵守了 Skill 的安全规则（确认逻辑真实存在且被强制执行），又保证了测试的自动化。

---

## 七、依赖

| 依赖 | 用途 | 状态 |
|---|---|---|
| Node.js >= 18 | 运行 ESM 项目和测试 | 当前环境已满足 |
| Python 3 | 运行环境探测脚本和（生产环境）Python SDK | 当前环境已满足 |
| `google-cloud-aiplatform` (Python) | 生产环境调用 Vertex AI API | **未安装**，`probe_env.py` 已检测到 |
| `gcloud` CLI + ADC 凭据 | 生产环境认证 | **未配置**，`probe_env.py` 已检测到 |

项目运行时**零 Node.js 外部依赖**（仅用 `node:assert`、`node:child_process` 内置模块），降低了供应链风险。

---

## 八、风险

1. **凭据风险**：`PythonSdkClient` 通过子进程传递 `projectId` / `region` / `jobId`，当前未做 shell 注入防护（因使用 `spawn` 数组参数而非 `shell: true`，参数不经过 shell 解析，实际风险低）。若未来改为拼接命令字符串需引入白名单校验。
2. **Mock 与真实 API 偏差**：Mock 客户端的任务结构是简化对象，真实 `aiplatform_v1` 返回的是 protobuf 对象。切换生产环境后需确认字段名（`base_model`、`tuned_model_display_name` 等）与 Skill 示例一致。
3. **取消操作的幂等性**：Skill 未说明重复取消已取消任务的行为。当前实现对不存在的任务返回 404（标记为 blocking），对正在取消的任务会重复设置状态。生产环境中 `cancel_tuning_job` 对终态任务的返回需实测。
4. **金额精度**：使用 `Math.round(amount * 100) / 100` 处理浮点精度，对于极端值（如 `0.1 + 0.2` 类问题）在两位小数场景下足够，但如果业务要求精确到分且金额极大，应考虑整数分制或 `BigInt`。

---

## 九、验证方法（可重复）

```bash
cd agent-platform-tuning-project

# 1. 运行全部测试（22 项，零依赖）
node test.js
# 预期输出：22 passed, 0 failed，退出码 0

# 2. 运行环境探测（验证 GCP 环境状态，不执行任何安装）
python3 scripts/probe_env.py
# 当前环境预期：vertexai_installed: false, ready: false，退出码 1
# 生产环境预期：ready: true，退出码 0
```

**本次实际执行结果**：
- `node test.js`：22 passed, 0 failed
- `python3 scripts/probe_env.py`：正确检测到无 `vertexai`、无 `gcloud`、无 ADC，退出码 1

---

## 十、切换到生产环境的步骤

1. 安装依赖：`pip install google-cloud-aiplatform`
2. 配置凭据：`gcloud auth application-default login`
3. 运行探测确认就绪：`python3 scripts/probe_env.py`（退出码 0）
4. 在代码中将 `MockTuningClient` 替换为 `PythonSdkClient`：
   ```js
   import { PythonSdkClient, TuningManager } from "./src/tuning-manager.js";
   const manager = new TuningManager({
     client: new PythonSdkClient(),
     projectId: "your-project-id",
     region: "us-central1",
   });
   ```
5. Tier R 操作可直接调用；Tier D 取消操作必须先调用 `requestCancel()`，等待用户确认后再调用 `confirmCancel()`。

---

## 附录：Skill 元数据

- **名称**：`agent-platform-tuning-management`
- **分类（metadata.category）**：`AiAndMachineLearning`（注：任务描述中称分类为"自动化与工具"，以实际读取的 SKILL.md frontmatter 为准）
- **适用范围**：列出、获取、取消 GenAI 调优任务
- **不适用**：模型微调本身（用 `agent-platform-tuning`）、模型部署（用 `agent-platform-deploy`）、服务端点管理（用 `agent-platform-endpoint-management`）
