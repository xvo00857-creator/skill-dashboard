# Cloud SQL 订单服务 — 实现与改进报告

> 基于 Skill `cloud-sql-basics`（分类：自动化与工具）审阅并改进最小示例项目。
> 生成时间：2026-08-26
> 约束：不得访问生产凭据；所有验证在本地无凭据环境下完成。

---

## 一、执行摘要

原始示例项目（`package.json` / `app.js` / `test.js`）是一个与 Cloud SQL 无关的订单规范化函数，存在**导入路径错误**、**无断言测试**、**无数据库层**、**项目名与 Skill 不匹配**等问题。

本报告将其改进为一个**可重复验证的 Cloud SQL for PostgreSQL 订单服务**，覆盖以下核心改进：

1. **修复结构性 bug**：`test.js` 从 `./src/app.js` 导入但 `app.js` 在根目录，运行即 `ERR_MODULE_NOT_FOUND`。
2. **引入 Cloud SQL 连接层**：使用 `@google-cloud/cloud-sql-connector`（Skill 推荐的 Node.js Language Connector），以 IAM 数据库认证连接，禁止静态密码。
3. **领域逻辑与数据访问分离**：`normalizeOrder` 保持纯函数，`orderRepository` 通过依赖注入接收 `pg.Pool`，使单元测试在无真实数据库时即可运行。
4. **基础设施即代码**：提供 Terraform 配置，显式声明 edition、开启 IAM 认证标志、PITR、SSL 强制。
5. **可重复验证**：`scripts/verify.sh` 一键完成依赖安装 → 语法检查 → 10 个单元测试（全部 mock，无凭据）。

**验证结果**：10/10 单元测试通过，语法检查全部 OK。

---

## 二、原项目审阅

### 2.1 文件清单与问题

| 文件 | 问题 | 严重程度 |
|------|------|----------|
| `test.js` | 从 `./src/app.js` 导入，但 `app.js` 在项目根目录，不存在 `src/` 目录。运行 `npm test` 立即抛出 `ERR_MODULE_NOT_FOUND`。 | **阻断** |
| `test.js` | 仅调用 `console.log(normalizeOrder(...))`，无任何断言（`assert`），不是真正的测试，无法验证正确性。 | 高 |
| `app.js` | `normalizeOrder` 对 `amount` 不做 `Number.isFinite` 校验，传入 `"abc"` 会得到 `NaN` 而静默通过；无金额范围校验。 | 中 |
| `app.js` | 与 Cloud SQL 无任何关联，缺少数据库连接、数据访问层，无法体现 Skill 的核心能力。 | 中 |
| `package.json` | 项目名 `wechat-skill-eval-sample` 与 `cloud-sql-basics` Skill 无关；无任何依赖；无 `type: module` 声明（但代码使用 ESM `export`）。 | 低 |

### 2.2 原始 bug 复现

```
$ node test.js
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '.../src/app.js'
```

---

## 三、Skill 规则依据

### 3.1 实际读取的 Skill 文件相对路径

```
cloud-sql-basics/SKILL.md
cloud-sql-basics/references/core-concepts.md
cloud-sql-basics/references/cli-usage.md
cloud-sql-basics/references/client-library-usage.md
cloud-sql-basics/references/iac-usage.md
cloud-sql-basics/references/iam-security.md
cloud-sql-basics/references/dr-backups.md
cloud-sql-basics/references/mcp-usage.md
```

共 8 个文件，全部读取完毕。

### 3.2 确实影响结果的 SKILL.md 规则

**规则一：连接必须通过 Cloud SQL Auth Proxy 或 Language Connector，不得直接裸连。**

> SKILL.md Quick Start 步骤 5–6：先获取 `connectionName`，再启动 `./cloud-sql-proxy INSTANCE_CONNECTION_NAME`，最后通过 `127.0.0.1:5432` 连接。

**影响**：本项目的 `src/db.js` 没有使用普通 `pg.Pool` 直连 IP，而是使用 `@google-cloud/cloud-sql-connector` 的 `Connector.getOptions()` 获取加密套接字选项后再创建 `pg.Pool`。这是 Skill `references/client-library-usage.md` 明确推荐的 Node.js 方式，等价于内嵌 Auth Proxy，无需单独运行 proxy 进程，也无需配置 authorized networks。

**规则二：IAM 数据库认证需要 `cloudsql.iam_authentication=on` 数据库标志。**

> SKILL.md `references/iam-security.md`："IAM Database Authentication: Authenticate to the database using IAM users or service accounts instead of static passwords"；`references/iac-usage.md`："Enabling IAM Database Authentication requires setting the database flag `cloudsql.iam_authentication = "on"`"。

**影响**：Terraform 配置 `infra/main.tf` 中显式设置了 `database_flags { name = "cloudsql.iam_authentication"; value = "on" }`，并创建 `type = "CLOUD_IAM_USER"` 的数据库用户，不创建任何静态密码用户。`src/db.js` 的 `authType` 默认设为 `"IAM"`。

---

## 四、改进方案

### 4.1 项目结构

```
cloud-sql-order-service/
├── package.json              # 依赖声明 + test script
├── src/
│   ├── app.js                # 纯函数：normalizeOrder（领域逻辑）
│   ├── db.js                 # Cloud SQL 连接工厂（Language Connector + IAM）
│   └── orderRepository.js    # 数据访问层（依赖注入 pg.Pool）
├── test/
│   ├── app.test.js           # normalizeOrder 单元测试（6 个用例）
│   └── orderRepository.test.js # 仓库层单元测试（4 个用例，mock pool）
├── infra/
│   └── main.tf               # Terraform：Cloud SQL 实例 + 数据库 + IAM 用户
├── scripts/
│   └── verify.sh             # 一键验证脚本
├── docker-compose.yml        # 本地 PostgreSQL（集成测试用，非生产凭据）
└── implementation-report.md  # 本报告
```

### 4.2 核心模块说明

#### `src/app.js` — 领域纯函数

`normalizeOrder(order)` 做了以下增强：
- 严格校验 `id`（`undefined` / `null` / 空字符串均拒绝）
- 金额经 `Number()` 转换后用 `Number.isFinite()` 拒绝 `NaN` / `Infinity`
- 金额范围校验 `[0, 1_000_000_000]`
- 默认币种 `CNY`，支持自定义
- 保持纯函数，无副作用，可独立测试

#### `src/db.js` — Cloud SQL 连接工厂

- 使用 `@google-cloud/cloud-sql-connector`（Skill 推荐的 Node.js Language Connector）
- 默认 `authType: "IAM"`（IAM 数据库认证，无静态密码）
- 连接参数全部从环境变量注入：`INSTANCE_CONNECTION_NAME` / `DB_NAME` / `DB_USER`
- 支持测试时注入自定义 `connector` / `pool` 工厂（依赖注入）
- 幂等 `getPool()` + 优雅关闭 `closePool()`

#### `src/orderRepository.js` — 数据访问层

- `upsertOrder(pool, order)`：先调用 `normalizeOrder` 校验，再执行 `INSERT ... ON CONFLICT DO UPDATE`
- `getOrder(pool, id)`：按主键查询
- `CREATE_ORDERS_TABLE_SQL`：幂等建表语句，含 `CHECK (amount >= 0)` 约束
- `pool` 通过参数注入，不直接 import `db.js`，使 mock 测试成为可能

#### `infra/main.tf` — Terraform 基础设施

- `POSTGRES_18`（Skill Quick Start 默认版本）
- `edition = "ENTERPRISE"`（显式声明，Skill 要求）
- `cloudsql.iam_authentication = on`（IAM 认证前置条件）
- `require_ssl = true` + `ipv4_enabled = true`（示例用公网；生产建议私网）
- `backup_configuration` 开启 automated backups + PITR（Skill `dr-backups.md` 推荐）
- `deletion_protection` 变量化（开发 `false` / 生产 `true`）
- 用户类型 `CLOUD_IAM_USER`，无静态密码

### 4.3 测试策略

| 层级 | 测试文件 | 用例数 | 是否需要真实 DB | 说明 |
|------|----------|--------|-----------------|------|
| 领域逻辑 | `test/app.test.js` | 6 | 否 | 纯函数，直接断言 |
| 数据访问 | `test/orderRepository.test.js` | 4 | 否 | mock `pg.Pool`，验证 SQL 文本和参数 |
| 集成 | （可选） | — | 本地 PostgreSQL | `docker-compose.yml` 提供，不依赖 Cloud SQL 凭据 |

---

## 五、两种约束与冲突分析

### 约束一：安全约束 — IAM 数据库认证 vs 静态密码

**冲突描述**：
- Skill `iam-security.md` 明确推荐使用 IAM Database Authentication 替代静态密码，并指出静态密码存在暴力破解风险（"Brute-Force Protection & Threat Detection" 章节）。
- 但 IAM 认证有前置条件：必须开启 `cloudsql.iam_authentication=on` 数据库标志（PostgreSQL），且应用服务账号必须被授予 `roles/cloudsql.instanceUser` 角色。这增加了配置复杂度。
- 此外，IAM 认证仅支持 MySQL 和 PostgreSQL，不支持 SQL Server（Skill `iam-security.md`："available for MySQL and PostgreSQL"）。

**本项目的取舍**：
- 选择 **IAM 数据库认证**，因为订单服务涉及金额数据，安全优先级高于配置简便性。
- Terraform 中显式开启 `cloudsql.iam_authentication=on`，创建 `CLOUD_IAM_USER` 类型用户。
- `src/db.js` 默认 `authType: "IAM"`，但保留 `DB_IAM_AUTH` 环境变量开关，便于在不支持 IAM 的引擎（如 SQL Server）上回退到密码模式——此时密码也必须从 Secret Manager 注入，严禁硬编码。

**残留风险**：
- IAM 令牌有有效期（通常 15 分钟），长连接场景需要 Connector 库自动刷新令牌。`@google-cloud/cloud-sql-connector` 已内置刷新逻辑，但需确认版本 >= 1.0。
- 若服务账号未授予 `roles/cloudsql.instanceUser`，连接会在认证阶段失败，且错误信息可能不直观。部署时需在 IAM 绑定步骤中验证。

### 约束二：连接方式约束 — 公网 IP + Language Connector vs 私网 IP

**冲突描述**：
- Skill `core-concepts.md` 指出 Cloud SQL 支持公网 IP（需 authorized networks 或 Auth Proxy）和私网 IP（VPC peering / Private Services Access / PSC）。
- Skill `iam-security.md` 推荐使用 Cloud SQL Auth Proxy / Language Connector 提供端到端加密，"without requiring SSL/TLS certificates or authorized networks"。
- 私网 IP 更安全（数据库不暴露在公网），但需要 VPC 对等连接或 PSC 配置，且开发机无法直接连接（需通过堡垒机或 VPC 内的开发环境）。
- 公网 IP + Language Connector 配置简单，开发机可直接连接，但实例本身暴露在公网（虽有 IAM 认证和加密，仍面临扫描和爆破面）。

**本项目的取舍**：
- 示例/开发环境使用 **公网 IP + Language Connector**（`ipType: "PUBLIC"`），因为这是 Skill Quick Start 的标准路径，且在无 VPC 配置的环境下可复现。
- Terraform 中预留了私网配置注释（`private_network`），生产环境应取消注释并设 `ipv4_enabled = false`。
- `src/db.js` 的 `ipType` 可通过环境变量扩展（当前硬编码 `PUBLIC`，生产部署时应改为 `PRIVATE` 并确保应用运行在 VPC 内）。

**残留风险**：
- 公网 IP 模式下，即使有 IAM 认证，实例仍会被互联网扫描。建议配合 `ssl-mode=ENCRYPTED_ONLY`（Terraform 中 `require_ssl = true`）和 VPC Service Controls 建立安全边界。
- Language Connector 的 `PUBLIC` 模式需要实例开启公网 IP；若组织策略强制禁止公网 IP（`constraints/sql.restrictPublicIp`），则必须使用私网模式。

---

## 六、关键取舍、依赖与风险汇总

### 6.1 关键取舍

| 决策点 | 选择 | 替代方案 | 取舍理由 |
|--------|------|----------|----------|
| 认证方式 | IAM 数据库认证 | 静态密码 | 安全优先；消除静态凭据爆破面 |
| 连接方式 | Language Connector（内嵌 proxy） | 独立 cloud-sql-proxy 进程 | 无需额外进程管理；Node.js 原生集成 |
| 测试策略 | 单元测试 + mock pool | 集成测试 + 真实 Cloud SQL | 不得访问生产凭据；mock 可在任意环境复现 |
| 实例 edition | Enterprise | Enterprise Plus | 示例场景无需 Read Pools / Advanced DR；成本更低 |
| 公网/私网 | 公网（示例） | 私网（生产） | 示例需可复现；生产应切换私网 |
| 测试框架 | Node.js 内置 `node:test` | Jest / Mocha | 零额外依赖；Node >= 18 内置 |

### 6.2 依赖清单

| 依赖 | 版本 | 用途 | 来源依据 |
|------|------|------|----------|
| `@google-cloud/cloud-sql-connector` | ^1.4.0 | Cloud SQL Language Connector，提供 IAM 认证 + 加密隧道 | Skill `client-library-usage.md` |
| `pg` | ^8.13.0 | PostgreSQL Node.js 驱动 | 标准 PostgreSQL 客户端 |
| Node.js | >= 18.0.0 | 内置 `node:test` 和 ESM 支持 | 运行时要求 |
| Terraform | ~> 6.0 (google provider) | 基础设施编排 | Skill `iac-usage.md` |

### 6.3 风险清单

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| IAM 令牌过期导致长连接断开 | 中 | Connector 库内置自动刷新；应用层实现重试逻辑 |
| 公网 IP 暴露扫描面 | 中 | `require_ssl = true`；生产切换私网；VPC-SC 边界 |
| `cloudsql.iam_authentication` 标志未开启导致 IAM 用户无法登录 | 高 | Terraform 显式设置；部署后用 `gcloud sql instances describe` 验证 |
| 服务账号缺少 `roles/cloudsql.instanceUser` | 高 | Terraform 输出中提示需手动绑定；部署 checklist 包含 IAM 验证 |
| PITR 未开启导致无法时间点恢复 | 中 | Terraform `point_in_time_recovery_enabled = true`；定期验证恢复流程 |
| 单元测试 mock 与真实 PostgreSQL 行为差异（如 `NUMERIC` 精度） | 低 | 提供 `docker-compose.yml` 用于本地集成测试；CI 中可加集成测试阶段 |
| `deletion_protection = false` 在生产误设导致实例被删 | 高 | 变量化；生产环境通过 Terraform workspace 或 `tfvars` 强制 `true` |

---

## 七、可重复验证方案

### 7.1 一键验证（无凭据环境）

```bash
cd cloud-sql-order-service
bash scripts/verify.sh
```

脚本执行以下步骤：
1. 检查 Node.js 版本
2. 安装依赖（`npm install`）
3. 对所有 `.js` 文件执行 `node --check` 语法检查
4. 运行 `npm test`（10 个单元测试，全部 mock，无真实数据库）

### 7.2 实际验证结果

```
$ npm test
TAP version 13
ok 1 - 正常订单：数字 id 和字符串金额
ok 2 - 默认金额为 0
ok 3 - 自定义币种
ok 4 - 缺失 id 抛出错误
ok 5 - 非法金额（NaN / Infinity）抛出错误
ok 6 - 金额超出范围抛出错误
ok 7 - upsertOrder 调用 normalizeOrder 并执行 INSERT ... ON CONFLICT
ok 8 - upsertOrder 在输入非法时抛出，不执行 SQL
ok 9 - getOrder 执行 SELECT 并返回首行
ok 10 - getOrder 未找到时返回 null
1..10
# tests 10
# pass 10
# fail 0
```

### 7.3 可选：本地集成测试（Docker，非 Cloud SQL）

```bash
docker-compose up -d
# 等待健康检查通过后，使用标准 pg 连接运行集成测试
# 连接串：postgresql://testuser:testpass@localhost:5432/orders_test
```

此步骤不访问任何 Cloud SQL 生产凭据，仅用于验证 SQL 语法在真实 PostgreSQL 上的正确性。

### 7.4 可选：Terraform 计划验证（无凭据）

```bash
cd infra
terraform init
terraform plan -var="project_id=my-project" -var="iam_user_email=app-sa@my-project.iam.gserviceaccount.com"
```

`terraform plan` 不创建任何资源，仅验证配置语法和依赖关系，无需实际 GCP 凭据。

---

## 八、与原始项目的对比

| 维度 | 原始项目 | 改进后项目 |
|------|----------|------------|
| 测试可运行性 | `npm test` 立即 `ERR_MODULE_NOT_FOUND` | 10/10 测试通过 |
| 测试断言 | 无（仅 `console.log`） | `node:assert/strict` 全量断言 |
| 数据库 | 无 | Cloud SQL for PostgreSQL 连接层 + 仓库层 |
| 认证方式 | 不适用 | IAM 数据库认证（无静态密码） |
| 基础设施 | 无 | Terraform 完整配置 |
| 输入校验 | 仅检查 `id`，金额无校验 | id + 金额有限性 + 金额范围 + 币种 |
| 项目名 | `wechat-skill-eval-sample`（与 Skill 无关） | `cloud-sql-order-service` |
| 可重复性 | 无法运行 | `scripts/verify.sh` 一键验证 |

---

## 九、结论

1. **原始项目存在阻断性 bug**（导入路径错误），且测试无断言，无法作为可验证的示例。
2. **改进后项目严格遵循 `cloud-sql-basics` Skill 规则**：使用 Language Connector 连接、IAM 数据库认证、Terraform 显式 edition + IAM 标志 + PITR + SSL 强制。
3. **覆盖两种约束/冲突**：(1) IAM 认证 vs 静态密码的安全冲突；(2) 公网 IP + Connector vs 私网 IP 的连接方式冲突，并给出了取舍和残留风险。
4. **可重复验证**：在无任何生产凭据的环境下，`bash scripts/verify.sh` 可完成语法检查 + 10 个单元测试，全部通过。
5. **未假装访问生产环境**：所有 Cloud SQL 资源操作仅限于 Terraform 配置文本和 `terraform plan` 级别，未执行 `gcloud sql instances create` 或任何需要凭据的实际操作。

---

## 附录：文件清单

```
cloud-sql-order-service/
├── implementation-report.md    # 本报告（最终交付物）
├── package.json
├── docker-compose.yml
├── src/
│   ├── app.js
│   ├── db.js
│   └── orderRepository.js
├── test/
│   ├── app.test.js
│   └── orderRepository.test.js
├── infra/
│   └── main.tf
└── scripts/
    └── verify.sh
```
