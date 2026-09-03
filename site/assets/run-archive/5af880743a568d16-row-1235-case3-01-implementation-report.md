# 实现报告：cloud-sql-basics Skill 评测 — 最小示例项目审阅与改进

> 生成时间：2026-08-26  
> 评测 Skill：`cloud-sql-basics`（分类：自动化与工具）  
> 输入文件：`package.json`、`app.js`、`test.js`、`edge_cases.csv`  
> 工作目录：`cloud-sql-eval/`

---

## 一、结论概述

原始最小示例项目存在 **3 类阻断性缺陷** 和 **4 类输入安全隐患**，均已在本地零凭据环境下完成修复与验证。改进后项目包含 18 项自动化测试，全部通过（退出码 0）。

与 Cloud SQL 的集成部分（创建实例、配置 IAM、执行 SQL 等）因缺少 Google Cloud 项目凭据和 `roles/cloudsql.admin` 权限而 **无法实际执行**，已给出降级方案与复测方法，未假装成功。

---

## 二、原始项目缺陷识别

### 2.1 阻断性缺陷（导致测试无法运行）

| 编号 | 缺陷 | 位置 | 影响 |
|------|------|------|------|
| B1 | 导入路径错误：`test.js` 引用 `./src/app.js`，但 `app.js` 在项目根目录 | `test.js` 第 1 行 | `ERR_MODULE_NOT_FOUND`，测试完全无法运行 |
| B2 | ESM/CJS 配置缺失：`app.js` 使用 `export` 语法，但 `package.json` 无 `"type": "module"` | `package.json` | Node.js 模块解析行为不确定 |
| B3 | `normalizeOrder` 校验不足：`Number(order.amount \|\| 0)` 对 `"abc"` 返回 `NaN` 而不报错，对负值静默接受 | `app.js` | 异常数据可穿透到下游，导致数据库写入脏数据 |

### 2.2 输入安全隐患（对齐 cloud-sql-basics IAM & Security 理念）

| 编号 | 隐患 | 位置 | 风险 |
|------|------|------|------|
| S1 | `id` 未做 `trim()`，纯空白字符串可通过 `!order.id` 检查（空串被拦截，但 `"   "` 不被拦截） | `app.js` | 写入空白主键，破坏数据唯一性 |
| S2 | `amount` 可为 `Infinity` / `NaN`，`Number.isFinite` 未校验 | `app.js` | 数据库数值字段写入非法值 |
| S3 | `amount` 可为负值，无业务规则校验 | `app.js` | 异常负值（如 edge_cases.csv 中 -999）静默入库 |
| S4 | `edge_cases.csv` 中 `record_id=5` 的 value 为 `=HYPERLINK(...)` 公式注入文本，无检测 | `edge_cases.csv` | 若导出到 Excel/Google Sheets 可能触发公式执行；写入数据库前应作为纯文本处理 |

---

## 三、已完成的改进

### 3.1 文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `package.json` | 已修改 | 添加 `"type": "module"` |
| `app.js` | 已重写 | 增强 `normalizeOrder` 输入校验 |
| `test.js` | 已重写 | 修正导入路径，扩展为 18 项完整测试套件 |
| `csv-validator.js` | 新增 | CSV 边界数据校验模块（零依赖） |
| `edge_cases.csv` | 未修改 | 原始数据保留，仅做读取分析 |

### 3.2 `normalizeOrder` 改进要点

1. **非对象输入拦截**：`null` / `undefined` / 原始类型直接抛出 `invalid order: expected a non-null object`
2. **id 严格校验**：`undefined` / `null` → `missing order id`；`trim()` 后为空 → `invalid order id: empty string after trim`
3. **金额有限性校验**：`Number.isFinite()` 拦截 `NaN` / `Infinity` / 非数字字符串
4. **负值拦截**：`amount < 0` → `invalid amount: negative value not allowed`
5. **安全上限**：超过 `Number.MAX_SAFE_INTEGER` 抛出异常
6. **缺失金额默认 0**：`amount === undefined` 时默认 0，但 `null` 走 `Number(null) === 0`

### 3.3 `csv-validator.js` 功能

- 零依赖 CSV 解析（支持双引号包裹、字段内转义引号）
- 检测四类问题：重复记录、缺失字段、异常负值、公式注入文本
- 返回结构化报告，包含 `validRecords`（完全无问题的记录）
- 重复 ID 的所有出现（含首次）均排除出有效记录

---

## 四、edge_cases.csv 边界分析结果

原始数据共 6 行（不含表头），分析结果：

| record_id | 行号 | 问题分类 | 详情 |
|-----------|------|----------|------|
| 1 | 2 | 有效 | 正常记录，status=ok, value=120 |
| 2 | 3 | 重复 | 与第 4 行 record_id 完全相同 |
| 2 | 4 | 重复 | 重复记录（首次出现也排除出有效集） |
| 3 | 5 | 缺失字段 | status 和 value 均为空 |
| 4 | 6 | 异常负值 | value=-999，status=error |
| 5 | 7 | 公式注入 | value=`=HYPERLINK("https://example.invalid","do not execute")`，以等号开头 |

**有效记录仅 1 条**（record_id=1），有效率 16.7%。

---

## 五、Cloud SQL Skill 关联与阻断说明

### 5.1 Skill 实际读取的文件（相对路径）

```
cloud-sql-basics/SKILL.md
cloud-sql-basics/references/core-concepts.md
cloud-sql-basics/references/cli-usage.md
cloud-sql-basics/references/client-library-usage.md
cloud-sql-basics/references/iam-security.md
cloud-sql-basics/references/dr-backups.md
cloud-sql-basics/references/iac-usage.md
cloud-sql-basics/references/mcp-usage.md
```

共 1 个 SKILL.md + 7 个参考文档，全部已读取。

### 5.2 确实影响结果的 SKILL.md 规则

**规则一：前置 IAM 权限要求（SKILL.md "Prerequisites" 节）**

> "Ensure you have the necessary IAM permissions to create and manage Cloud SQL instances. The **Cloud SQL Admin** (`roles/cloudsql.admin`) role provides full access to Cloud SQL resources."

**影响**：SKILL.md 中所有 Quick Start 命令（`gcloud sql instances create`、`gcloud sql users set-password`、`gcloud sql databases create` 等）均需已认证的 `gcloud` CLI 和 `roles/cloudsql.admin` 权限。当前环境无 Google Cloud 项目凭据，因此 **无法创建任何 Cloud SQL 实例或执行任何写操作**。本报告的数据校验部分可在本地完成，但数据库集成部分被此规则阻断。

**规则二：安全连接要求（iam-security.md "Secure Connectivity" 节）**

> "Use **`ENCRYPTED_ONLY`** or **`TRUSTED_CLIENT_CERTIFICATE_REQUIRED`** to prevent transmission of credentials in clear text."
> "Recommended: Use IAM Database Authentication or the Cloud SQL Auth Proxy to bypass database passwords entirely and eliminate static credential brute-force vectors."

**影响**：若后续集成 Cloud SQL，连接层必须使用 `--ssl-mode=ENCRYPTED_ONLY` 和 Cloud SQL Auth Proxy，不得在连接字符串中明文传递密码（SKILL.md Quick Start 第 6 步的 `psql` 示例中 `password=PASSWORD sslmode=disable` 仅为本地代理场景，不适用于生产）。此规则直接决定了数据库连接模块的设计方向。

### 5.3 阻断项与降级方案

| 阻断项 | 缺失条件 | 降级方案 | 复测方法 |
|--------|----------|----------|----------|
| 创建 Cloud SQL 实例 | Google Cloud 项目 ID、已认证 `gcloud`、`roles/cloudsql.admin` | 使用本地 SQLite 或内存数据库替代，验证数据模型和 SQL 语法；数据校验逻辑与数据库无关，已在本地完成 | 获得凭据后执行：`gcloud auth login && gcloud config set project PROJECT_ID && gcloud sql instances create test-instance --database-version=POSTGRES_18 --cpu=2 --memory=7680MiB --region=us-central1 --quiet` |
| 配置 IAM 数据库认证 | 项目级 IAM 权限、`cloudsql.iam_authentication` 数据库标志 | 使用本地静态密码用户，代码中预留 IAM 认证接口 | 获得权限后：`gcloud sql instances patch INSTANCE --database-flags=cloudsql.iam_authentication=on && gcloud sql users create USER_EMAIL --instance=INSTANCE --type=CLOUD_IAM_USER` |
| 执行 SQL 写入/查询 | 运行中的 Cloud SQL 实例、网络连通性、Auth Proxy | 本地验证 `normalizeOrder` 输出可直接用于参数化 SQL（`INSERT INTO orders (id, amount) VALUES ($1, $2)`），无 SQL 注入风险 | 启动代理：`./cloud-sql-proxy PROJECT:REGION:INSTANCE`，然后 `psql "host=127.0.0.1 port=5432 user=postgres dbname=DB sslmode=disable"` 执行验证 SQL |
| MCP 工具调用 | `roles/mcp.toolUser` 角色 + Cloud SQL 资源角色 | 不适用，MCP 为远程管理协议，无本地替代 | 获得角色后通过 `https://sqladmin.googleapis.com/mcp` 端点调用 `execute_sql_readonly` 验证只读查询 |

---

## 六、验证结果

### 6.1 原始测试（修复前）

```
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '.../src/app.js'
退出码: 1
```

### 6.2 改进后测试（修复后）

```
=== normalizeOrder 单元测试 ===
  PASS: 数字 id 转字符串、字符串金额转数字
  PASS: 金额为 0 时正常处理
  PASS: 缺失 amount 时默认为 0
  PASS: id 首尾空白被去除
  PASS: null 输入抛出异常
  PASS: undefined 输入抛出异常
  PASS: 缺失 id 抛出异常
  PASS: 空字符串 id 抛出异常
  PASS: 纯空白 id 抛出异常
  PASS: 非数字金额字符串抛出 NaN 异常
  PASS: Infinity 金额抛出异常
  PASS: 负金额抛出异常

=== edge_cases.csv 校验测试 ===
  PASS: CSV 共 6 行数据（实际 6）
  PASS: 检测到 record_id=2 的重复记录
  PASS: 检测到 record_id=3 缺失 status 和 value
  PASS: 检测到 record_id=4 的异常负值 -999
  PASS: 检测到 record_id=5 的公式注入文本 (=HYPERLINK)
  PASS: 仅 record_id=1 为完全有效记录

=== 测试结果: 18 通过, 0 失败 ===
退出码: 0
```

### 6.3 复现命令

```bash
cd cloud-sql-eval
node test.js
echo $?  # 预期输出 0
```

无需 `npm install`（零外部依赖），无需网络连接，无需任何凭据。

---

## 七、复测方法

1. **代码逻辑复测**：在任意 Node.js >= 18 环境中执行 `node test.js`，确认 18/18 通过
2. **CSV 数据复测**：修改 `edge_cases.csv` 添加新的边界行（如超大数值、Unicode id、嵌套引号），重新运行测试确认校验器行为
3. **Cloud SQL 集成复测**：获得 Google Cloud 项目凭据后，按 5.3 节降级方案中的命令逐步执行，确认实例创建、IAM 配置、SQL 执行均成功
4. **安全复测**：使用 `--ssl-mode=ENCRYPTED_ONLY` 创建实例后，尝试以明文方式连接，确认被拒绝；验证 `normalizeOrder` 输出用于参数化查询时无 SQL 注入

---

## 八、总结

- **已完成**：原始项目 3 个阻断性缺陷修复、4 类输入安全隐患加固、CSV 边界数据校验模块、18 项自动化测试全部通过
- **未完成（有明确阻断）**：Cloud SQL 实例创建、IAM 配置、SQL 执行等云端操作，因缺少 Google Cloud 项目凭据和 `roles/cloudsql.admin` 权限无法执行
- **关键 Skill 规则**：SKILL.md 前置 IAM 权限要求直接决定了云端操作不可执行；iam-security.md 的 `ENCRYPTED_ONLY` 和 IAM 数据库认证要求决定了连接层设计方向
- **零凭据保证**：所有已完成的工作均在本地无网络、无凭据环境下验证，未访问任何生产系统
