# Google Cloud 解决方案架构：智能随行杯新品上市跨云智能分析平台

> 本文档基于 Skill `google-cloud-solution-agentic-analytics-spark-knowledge-catalog` 的四阶段工作流生成。
> 输出文件名按任务要求为 `skill-delivery.md`（Skill 模板原命名为 `solution-architecture-guide.md`，此处为显式偏差，结构仍遵循 `assets/output-template.md`）。
> 生成时间基准：2026-08-26。

---

## 0. 输入、范围与执行说明

### 0.1 输入文件
- `product_brief.md`：智能随行杯新品任务简报（目标用户、核心卖点、建议零售价、已确认素材、禁止编造项、不完整信息）。

### 0.2 Skill 能力边界
本 Skill 用于设计和部署**跨 Google Cloud、其他云厂商及本地环境的、受治理且安全的智能分析（agentic analytics）管道**，覆盖结构化与非结构化数据，通过 Apache Iceberg、零拷贝 ETL、远程查询下推等联邦机制访问外部数据。**不负责**：产品工业设计、电商前端开发、营销文案创作、实际销量预测建模执行。

### 0.3 执行偏差与限制声明（结论与假设分开）
| 项目 | Skill 原始要求 | 实际执行 | 原因 |
|---|---|---|---|
| Phase 1 逐题澄清 | 一次问一个问题，用户回答后再继续 | 基于 `product_brief.md` 自动补全合理业务假设并标注，未发起交互式问答 | 任务执行规则要求低风险选项自动选择、不停留澄清 |
| Phase 2 实时 grounding | 调用 Google Developer Knowledge MCP server、官方文档实时检索 | 仅使用 Skill 内置参考文件（`references/` 下三份）grounding；未调用外部 MCP | 无外部 MCP 访问凭据与网络授权；不得编造未读取的官方文档内容 |
| Phase 3 验证执行 | 生成脚本并经用户授权后实际运行 | 仅生成验证计划与 `curl`/`gcloud` 脚本，未实际执行 | 无 Google Cloud 项目、计费账号、服务账号密钥；不得伪造执行结果 |
| Phase 4 代码文件写入 | 经用户许可后写入工作区代码文件 | 未写入 Terraform/Python 代码文件，仅在部署指南中给出命令级指引 | 无 GCP 项目上下文，写入不可执行代码无价值且增加风险 |

---

## 1. 执行摘要与工作负载概述

### 1.1 业务背景
某消费品公司（以下简称"公司"）计划推出**智能随行杯**新品（建议零售价 199 元，核心卖点：12 小时保温、280g 轻量化、可拆洗杯盖，目标用户为一二线城市通勤人群）。新品上市期间，市场、供应链、产品、客服团队需要一个**自然语言驱动的跨系统智能分析平台**，用于：
- 需求预测与库存调拨（跨电商平台、官网、线下门店）
- 营销活动 ROI 实时分析（多渠道投放效果归因）
- 用户反馈与售后工单洞察（评论、客服会话、退货原因）
- 产品质量指标追踪（保温性能抽检、杯盖拆洗故障率）

### 1.2 数据分布现状（假设，基于业务合理性推导）
| 数据域 | 存储位置 | 数据类型 | 说明 |
|---|---|---|---|
| 官网电商订单与历史销售 | Google Cloud BigQuery | 结构化 | 已在 GCP 上 |
| 产品素材（白底图、规格书 PDF、营销视频） | Google Cloud Storage | 非结构化 | 已确认素材 |
| 第三方电商平台（天猫/京东）订单与评论导出 | AWS S3 | 结构化 + 非结构化（评论文本） | 平台定期导出至 S3 |
| ERP 库存、供应链、财务 | 本地 Oracle 数据库 | 结构化 | 含供应商 PII 与财务敏感数据 |
| CRM 与客服工单 | Salesforce | 结构化 + 非结构化 | 云 SaaS |
| 线下门店 POS | 本地 MySQL | 结构化 | 门店局域网 |

### 1.3 高层方案概述
采用 **Knowledge Catalog + Managed Service for Apache Spark（Lightning Engine）+ Lakehouse for Apache Iceberg** 为核心的零拷贝联邦分析架构：
- **用户交互层**：Antigravity IDE / VS Code + Google Cloud Data Agent Kit，数据分析师与业务 agent 用自然语言提问。
- **Grounding 与可信数据层**：Gemini 基础模型 + MCP servers + BigQuery，所有回答基于 Knowledge Catalog 中已认证的可信数据。
- **元数据治理层**：Knowledge Catalog 统一扫描跨源元数据，建立业务术语表、敏感数据分类、数据血缘。
- **数据处理与分析层**：Managed Service for Apache Spark 通过 Iceberg REST Catalog 零拷贝查询 AWS S3 数据；通过 Cross-Cloud Interconnect / Cloud Interconnect 访问本地 ERP；BigQuery Omni 处理 AWS 侧热数据。

---

## 2. 需求、依赖与当前状态

### 2.1 功能需求

**业务流程**：
1. 新品上市前：数据团队将各数据源接入元数据目录，定义业务术语（如"首周销量""退货率""保温达标率"），标记敏感字段。
2. 上市期间：市场/供应链/产品团队在 IDE 中用自然语言提问（如"对比天猫和京东近 7 天随行杯销量趋势"），agent 自动生成 SQL/Spark 作业并返回结果与可视化。
3. 日常运营：定时需求预测作业运行，库存预警自动推送到供应链团队；客服评论情感分析每日更新。

**关键活动与用例**：
- 跨云销售数据联邦查询（BigQuery + AWS S3 + 本地 ERP）
- 非结构化评论/工单的文本分析与主题聚类
- 需求预测模型训练与推理（基于历史销售 + 营销活动日历 + 季节性特征）
- 数据血缘追踪与影响分析（上游 schema 变更对下游报表的影响）
- PII 数据泄漏路径审计

### 2.2 非功能需求

**安全、隐私与合规**：
- 本地 ERP 中的供应商 PII（姓名、银行账号、联系方式）与财务数据**不得复制出本地域**（公司数据合规政策，假设项）。
- 用户评论中的个人信息需在分析前脱敏。
- 遵循《个人信息保护法》（PIPL）数据最小化原则。
- 所有跨云传输加密（TLS 1.2+），静态数据加密（CMEK）。

**可靠性**：
- 分析平台查询可用性 SLA：99.9%（假设项）。
- RTO ≤ 4 小时，RPO ≤ 1 小时（元数据层，假设项）。
- 跨云网络链路冗余，避免单点网络故障导致联邦查询中断。

**性能**：
- 营销实时看板查询延迟 P95 ≤ 10 秒（热数据，假设项）。
- 大规模历史数据联邦查询（TB 级）P95 ≤ 5 分钟（假设项）。
- 自然语言到查询的生成响应 ≤ 3 秒（假设项）。

**运维**：
- 统一监控：查询性能、数据质量、资源利用率、成本异常。
- 数据质量扫描：每日自动检测空值率、schema 漂移、新鲜度。
- 审计日志：所有查询与数据访问记录保留 ≥ 180 天（假设项）。

**成本与可持续性**：
- 跨云数据出口费用（egress）需控制在月度预算内（具体金额待补，product_brief 未提供）。
- 优先采用零拷贝架构避免重复存储多 PB 级数据集。
- 采用 Serverless + Lightning Engine 减少计算资源浪费。

### 2.3 当前状态
- **现有基础设施**：公司已有 GCP 项目（BigQuery、Cloud Storage），AWS S3 用于电商平台数据导出，本地数据中心运行 Oracle ERP 与 MySQL POS，Salesforce 用于 CRM。
- **痛点与迁移/重设计动因**：
  1. 数据分散在 5+ 系统，分析师需手动导出 CSV 拼接，耗时且易出错。
  2. 无统一元数据治理，指标口径不一致（"销量"在不同团队定义不同）。
  3. 跨云数据复制成本高，且存在 PII 合规风险。
  4. 新品上市周期短，传统数仓开发跟不上业务节奏。

### 2.4 依赖
**内部依赖**：
- 公司 IT 部门提供本地 ERP 与 POS 的数据库连接信息与只读账号。
- 电商运营团队提供 AWS S3 桶的访问权限与数据导出频率说明。
- 法务/合规团队确认 PII 数据驻留政策与跨域传输审批流程。
- 数据团队定义业务术语表与指标口径。

**外部依赖**：
- Google Cloud 服务可用性（BigQuery、Knowledge Catalog、Managed Service for Apache Spark、Cloud Interconnect）。
- AWS S3 与 Cross-Cloud Interconnect 对接的网络配置。
- Salesforce API 配额与连接方式（需评估是否通过联邦查询或批量导入）。
- Data Agent Kit 扩展与 Antigravity IDE 的兼容性。

---

## 3. Phase 1：需求发现中的矛盾识别与消解

> **SKILL.md 规则（确实影响结果）**：Phase 1 Step 5 明确规定——识别到歧义或矛盾后，必须先描述矛盾、询问用户如何解决；**在所有矛盾消解之前，不得推荐或生成任何架构设计、技术分解或产品推荐**。Step 6 重申"若 Step 5 有未解决矛盾，不得开始本步"。
>
> 以下矛盾均已按"最低风险自动选择"原则给出消解建议并记录，视同用户已授权（任务执行规则：低风险选项自动选择、不停留澄清）。

### 矛盾一：零拷贝联邦查询 vs. PII 数据驻留合规

**描述**：Skill 的核心能力是零拷贝联邦查询（Spark REST Catalog、BigQuery Omni、远程查询下推），即不复制数据、在数据源侧执行查询后只回传结果。但公司合规政策要求本地 ERP 中的供应商 PII 与财务敏感数据"不得出域"。零拷贝虽然不复制原始数据，但**查询结果本身可能包含聚合后的敏感信息**（如"某供应商的订单总额"可反推出商业敏感信息），且查询执行过程中中间结果可能经过 GCP 内存。这构成"零拷贝不出域"与"查询结果可能含敏感信息"之间的矛盾。

**消解方案**（自动选择，最低风险）：
- 采用**零拷贝 + 行级/列级安全策略**双层防护：Knowledge Catalog 中对 ERP 敏感表标记 `pii_restricted` aspect，Spark REST Catalog 查询时自动应用列级掩码（column-level masking）与行级安全策略（row-level security），只允许聚合后的非敏感结果（如"总采购额"而非"按供应商拆分的采购额"）回传 GCP。
- 对含 PII 的原始字段，**永远不回传**，仅在本地侧完成脱敏/聚合后再回传统计值。
- 在 Knowledge Catalog 中建立 PII 数据血缘追踪，审计所有跨域查询的字段访问路径。

**关键取舍**：牺牲了"按供应商维度下钻分析"的灵活性，换取合规确定性。若业务确需供应商维度分析，需走本地侧报表流程，不纳入本平台。

### 矛盾二：营销实时低延迟 vs. 跨云出口成本

**描述**：市场团队要求营销效果看板 P95 ≤ 10 秒（热数据，近 7 天），但 AWS S3 中的电商订单数据若每次都通过跨云联邦查询实时拉取，将产生持续的数据出口费用（egress fee），且跨云网络延迟可能无法稳定满足 10 秒 SLA。这构成"实时性"与"成本控制"之间的矛盾。

**消解方案**（自动选择，最低风险）：
- **热数据（近 7 天）**：采用 **BigQuery Omni** 在 AWS 侧本地查询 S3 数据，查询结果（仅聚合结果，非原始数据）回传 BigQuery 区域，避免大规模原始数据跨云传输。同时在 BigQuery 中建立**物化视图**预计算常用营销指标（按日、按渠道、按 SKU），看板查询直接命中物化视图，P95 延迟可控。
- **冷数据（7 天以上）**：采用 Managed Service for Apache Spark + Iceberg REST Catalog 零拷贝查询，不设严格延迟 SLA，用于深度分析与模型训练。
- **数据新鲜度**：S3 数据为 T+1 批量导出（电商平台限制，假设项），实时看板的"实时"定义为"截至昨日数据"，而非秒级实时。若需秒级，需电商平台开放流式 API（待补依赖）。

**关键取舍**：接受 T+1 数据新鲜度而非秒级实时，换取成本可控与延迟稳定。物化视图增加存储成本但大幅降低重复查询计算成本。

### 矛盾三：新品数据缺失 vs. 分析平台完整性

**描述**：`product_brief.md` 明确**禁止编造**第三方检测结论、销量、用户评价、竞品价格；且**不完整信息**包括首发日期未定、防水等级与食品接触材料报告未提供。新品上市初期，这些维度数据为空，但分析平台需要完整的维度建模才能支持业务查询。若强行填充将违反"禁止编造"规则；若留空则平台初期可用性低。

**消解方案**（自动选择，最低风险）：
- 架构设计为**渐进式数据接入（progressive data onboarding）**：为所有缺失维度（防水等级、材料认证、首发日期、竞品数据）预留 schema 与元数据条目，在 Knowledge Catalog 中标记为 `data_status: pending` aspect。
- 分析 agent 在查询到缺失维度时，**主动提示"该数据尚未接入，当前结果不含此维度"**，而非用默认值或估算值填充。
- 建立数据接入检查清单（onboarding checklist），每收到一份外部报告（如食品接触材料检测报告），按流程更新元数据并触发数据质量扫描。
- 竞品价格数据因"禁止编造"且无合法数据源，**本期不纳入**，列为待补项（需公司采购竞品数据服务或人工录入）。

**关键取舍**：平台初期分析维度受限，但保证所有输出数据均可溯源、无编造。竞品分析功能延后至数据合法接入后启用。

---

## 4. 技术分解（四层架构）

> 基于 SKILL.md Phase 1 Step 6 要求，技术分解必须组织在以下四层之下，并覆盖角色安全与凭据。

### 4.1 用户交互层（IDE）
- **组件**：Antigravity IDE 或 VS Code + Google Cloud Data Agent Kit 扩展。
- **能力**：数据分析师与业务 agent 在 IDE 中用自然语言提问，Data Agent Kit 提供 IDE 内 grounding，自动生成 BigQuery SQL / Spark 笔记本 / Dataflow 管道，执行并返回结果。
- **角色安全**：
  - 分析师角色：只读查询权限，可访问已认证数据。
  - 数据工程师角色：可创建/修改 Spark 会话模板、调度作业。
  - 业务 agent 角色：受限查询，仅可访问经 Knowledge Catalog 标记为 `certified` 的数据集。

### 4.2 Grounding 与可信数据层
- **组件**：Gemini 基础模型 + MCP servers（Knowledge Catalog MCP、BigQuery MCP）+ BigQuery 数据仓库。
- **能力**：所有自然语言查询的回答必须基于 Knowledge Catalog 中已认证的可信数据；MCP server 提供工具调用（搜索文档、获取表元数据、执行查询）；BigQuery 存储已治理的结构化数据与物化视图。
- **角色安全**：
  - Gemini 服务账号：仅可调用已授权的 MCP 工具，不可直接访问原始存储。
  - BigQuery 查询账号：按数据集级别授权，敏感数据集需额外审批。

### 4.3 元数据治理层
- **组件**：Knowledge Catalog（原 Dataplex）+ 元数据扫描器 + 业务术语表 + 数据血缘。
- **能力**：
  - 自动扫描 BigQuery、Cloud Storage、AWS S3（通过自定义源接入）、本地 ERP（通过自定义源接入）的元数据。
  - 建立业务术语表（"首周销量""退货率""保温达标率"等统一定义）。
  - 自定义 Aspect 类型：`pii_restricted`、`data_status`（certified/pending/deprecated）、`data_domain`（sales/inventory/marketing/quality）。
  - 数据血缘追踪：从源系统到 BigQuery 物化视图到分析报表的完整链路。
  - PII 泄漏路径审计：基于血缘识别敏感字段的下游传播。
- **角色安全**：
  - 数据治理管理员：可创建/修改 Aspect 类型、业务术语、数据分类规则。
  - 数据所有者：可认证（certify）自己负责的数据集。
  - 普通用户：只读查看元数据与血缘。

### 4.4 数据处理与分析层
- **组件**：
  - **Managed Service for Apache Spark（原 Dataproc Serverless）+ Lightning Engine**：通过 Iceberg REST Catalog 零拷贝查询 AWS S3 数据，执行大规模 ETL、特征工程、预测模型训练。
  - **Lakehouse for Apache Iceberg（原 BigLake）**：统一表格式，支持跨云零拷贝访问。
  - **BigQuery + BigQuery Omni**：GCP 侧数据仓库与 AWS 侧联邦查询。
  - **AlloyDB for PostgreSQL**：运营数据存储（库存实时状态、门店 POS 聚合），支持列缓存向量加速。
  - **Cross-Cloud Interconnect**：GCP ↔ AWS 专用网络链路。
  - **Cloud Interconnect**：GCP ↔ 本地数据中心专用网络链路。
  - **Cloud Storage**：原始非结构化数据（产品图片、PDF 规格书、营销视频）。
- **能力**：
  - Spark 作业通过 REST Catalog 直接查询 S3 上的 Iceberg 表，不复制数据。
  - Lightning Engine 原生运行时加速 Spark 作业。
  - BigQuery Omni 在 AWS 侧查询 S3 热数据，聚合结果回传。
  - AlloyDB 提供低延迟运营查询（如实时库存查询）。
- **角色安全**：
  - Spark 服务账号：通过 Secret Manager 存储 AWS S3 访问凭据（token federation），最小权限只读。
  - BigQuery Omni 服务账号：AWS 侧角色仅可访问指定 S3 桶与前缀。
  - AlloyDB 数据库账号：按 schema 授权，敏感表启用行级安全。

---

## 5. 方案架构

### 5.1 Google Cloud 产品与功能映射

> 基于 `references/product-selection-guidance.md` 的产品推荐。所有产品名称使用最新命名（旧名映射见该文件）。

| 组件 | 推荐 Google Cloud 产品/功能 | 选择理由与依据 | 考虑过的替代方案 | 替代方案优劣 |
|---|---|---|---|---|
| 中央元数据与数据治理 | **Knowledge Catalog**（集成 Lakehouse for Apache Iceberg） | 捕获业务术语表、列描述、自定义元数据 Aspect 类型；支持数据血缘与 PII 泄漏追踪；为 agentic 分析提供 grounding 层。依据：`product-selection-guidance.md` 中央元数据推荐项。 | Data Catalog（旧版） | 已被 Knowledge Catalog 取代，不推荐。 |
| 处理引擎 | **Managed Service for Apache Spark + Lightning Engine**（配置 Iceberg REST Catalog） | 零拷贝查询 AWS S3 Iceberg 表；Lightning Engine 原生运行时加速；Serverless 免运维。依据：`product-selection-guidance.md` 处理引擎推荐项。 | BigQuery | **优**：直接用标准 SQL 查询外部 BigLake 表，学习成本低。**劣**：对非 Iceberg 格式的外部数据与复杂 ETL/ML 工作流支持不如 Spark 灵活。 |
| 原始数据存储 | **Cloud Storage** | 适合非结构化文件（PDF 规格书、产品图片、营销视频）的原始 blob 存储。依据：`product-selection-guidance.md` 原始数据存储推荐项。 | BigQuery | **劣**：非结构化 blob 存储非 BigQuery 设计目标。 |
| 跨云连接 | **Cross-Cloud Interconnect** | GCP ↔ AWS 专用高带宽低延迟链路，避免公网传输的不稳定性与安全风险。依据：`product-selection-guidance.md` 跨云连接推荐项。 | 公网 VPN | **优**：成本低、配置快。**劣**：延迟高、不稳定、安全性弱，不适合大规模联邦查询。 |
| 本地连接 | **Cloud Interconnect** | GCP ↔ 本地数据中心专用链路，支持混合云联邦查询。依据：`product-selection-guidance.md` 本地连接推荐项。 | 公网 VPN | 同上。 |
| 运营数据存储 | **AlloyDB for PostgreSQL** | 支持列缓存向量加速，适合实时运营查询（库存、门店聚合）的快速 join。依据：`product-selection-guidance.md` 运营数据存储推荐项。 | Cloud SQL for PostgreSQL | **优**：简单小型关系型工作负载成本低。**劣**：缺乏列缓存向量加速，复杂 join 性能不足。 |
| 用户与 agent 交互 | **Antigravity IDE 或 VS Code + Google Cloud Data Agent Kit** | 提供 IDE 内 grounding，支持自然语言生成 SQL/Spark 笔记本/数据管道。依据：`product-selection-guidance.md` 用户交互推荐项。 | 自建 Web 分析前端 | **优**：可定制 UI。**劣**：开发成本高，无内置 agentic 能力与 grounding。 |
| 数据仓库 | **BigQuery + BigQuery Omni** | 无服务器数据仓库，支持物化视图预计算；BigQuery Omni 在 AWS 侧查询 S3 热数据。 | — | — |
| 密钥管理 | **Secret Manager** | 存储 AWS S3 访问凭据、本地数据库连接字符串，支持 token federation。 | — | — |

### 5.2 架构图（Mermaid）

```mermaid
graph TD
    subgraph 用户交互层
        Analyst([数据分析师/业务团队])
        Agent([业务 Agent])
        IDE[Antigravity IDE / VS Code<br/>+ Data Agent Kit]
        Analyst --> IDE
        Agent --> IDE
    end

    subgraph Grounding与可信数据层
        Gemini[Gemini 基础模型]
        MCP[MCP Servers<br/>Knowledge Catalog / BigQuery]
        BQ[(BigQuery<br/>+ 物化视图)]
        IDE -->|自然语言查询| Gemini
        Gemini -->|工具调用| MCP
        MCP -->|查询| BQ
    end

    subgraph 元数据治理层
        KC[Knowledge Catalog<br/>业务术语表 + Aspect + 血缘]
        Scanner[元数据扫描器]
        MCP -->|元数据检索| KC
        Scanner -->|扫描| KC
    end

    subgraph 数据处理与分析层
        Spark[Managed Service for Apache Spark<br/>+ Lightning Engine + Iceberg REST Catalog]
        BQOmni[BigQuery Omni<br/>AWS 侧查询]
        AlloyDB[(AlloyDB for PostgreSQL<br/>运营数据)]
        GCS[(Cloud Storage<br/>非结构化原始数据)]
        Spark -->|零拷贝查询| S3
        BQOmni -->|查询| S3
        Spark -->|写入| BQ
        AlloyDB -->|联邦| BQ
        GCS -->|元数据| Scanner
    end

    subgraph 外部与本地数据源
        S3[(AWS S3<br/>电商订单+评论)]
        ERP[(本地 Oracle ERP<br/>库存+财务+PII)]
        POS[(本地 MySQL POS<br/>门店销售)]
        SF[Salesforce CRM<br/>客户+工单]
    end

    %% 网络连接
    Spark -.->|Cross-Cloud Interconnect| S3
    BQOmni -.->|AWS 本地| S3
    Spark -.->|Cloud Interconnect| ERP
    Spark -.->|Cloud Interconnect| POS
    ERP -->|自定义源元数据| Scanner
    POS -->|自定义源元数据| Scanner
    S3 -->|自定义源元数据| Scanner
    SF -->|API/批量| GCS
    SF -->|元数据| Scanner

    %% 安全与凭据
    SM[Secret Manager<br/>AWS 凭据 + DB 连接串]
    Spark -->|读取凭据| SM
    BQOmni -->|AWS IAM 角色| S3
```

### 5.3 架构描述

**数据流**：
1. **元数据采集**：Knowledge Catalog 元数据扫描器定期扫描 BigQuery 数据集、Cloud Storage 桶、AWS S3 桶（通过自定义源接入）、本地 Oracle ERP 与 MySQL POS（通过自定义源接入），将表/列/文件元数据统一收录。数据治理管理员为每张表分配 `data_domain`、`pii_restricted`、`data_status` 等 Aspect，数据所有者认证可信数据集。
2. **热数据查询（营销看板）**：用户在 IDE 中提问"近 7 天各渠道随行杯销量趋势"。Data Agent Kit 将自然语言转为 BigQuery SQL，优先命中 BigQuery 中的物化视图（已预计算）。若物化视图未覆盖，BigQuery Omni 在 AWS 侧查询 S3 热数据，仅聚合结果回传。
3. **冷数据深度分析**：用户提问"对比过去 6 个月各电商平台评论中的负面主题分布"。Managed Service for Apache Spark 通过 Iceberg REST Catalog 零拷贝读取 S3 上的历史评论数据，执行文本分析与主题聚类，结果写入 BigQuery。
4. **本地 ERP 联邦查询**：用户提问"当前各仓库随行杯库存总量"。Spark 通过 Cloud Interconnect 连接本地 Oracle ERP，应用行级安全策略后执行聚合查询，仅回传非敏感聚合结果。
5. **非结构化数据处理**：Cloud Storage 中的产品规格书 PDF 与评论数据通过 Spark 进行文本提取与向量化，元数据录入 Knowledge Catalog。

**任务/控制流**：
1. 用户/Agent 在 IDE 发起自然语言查询 → Data Agent Kit 解析意图 → 调用 Knowledge Catalog MCP 检索相关表与元数据 → 生成 SQL/Spark 代码 → 用户确认后执行。
2. 定时调度：需求预测 Spark 作业每日运行，数据质量扫描每日运行，元数据扫描每 6 小时运行。
3. 异常处理：查询失败时自动重试（指数退避），超过阈值告警；数据质量不达标时标记对应数据集 `data_status: deprecated` 并通知数据所有者。

---

## 6. 设计与配置建议

> 基于 `references/design-recommendations.md`，结合本工作负载的功能与非功能需求。

### 6.1 安全、隐私与合规
- **访问控制**：
  - 遵循最小权限原则，为每个服务账号分配精确的 IAM 角色（如 `roles/dataproc.editor` 仅限 Spark 运维人员）。
  - Knowledge Catalog 中建立 Aspect 类型 `pii_restricted`，对含 PII 的表/列自动应用列级掩码。
  - BigQuery 启用行级安全策略（row-level security），按用户部门限制可查询的数据范围。
- **数据保护**：
  - 静态加密使用客户管理加密密钥（CMEK，Cloud KMS）。
  - 传输加密强制 TLS 1.2+。
  - Secret Manager 存储 AWS S3 访问凭据与本地数据库连接字符串，配置 token federation 使 Spark REST Catalog 可安全认证远程 AWS S3 / Azure 存储。
- **网络安全**：
  - Cross-Cloud Interconnect 与 Cloud Interconnect 均配置冗余链路（分属不同物理域），避免单点故障。
  - VPC Service Controls 限制 BigQuery 与 Cloud Storage 的数据导出边界。
  - Knowledge Catalog 数据血缘追踪用于识别 PII 数据泄漏路径，定期审计。

### 6.2 可靠性
- **冗余部署**：
  - BigQuery 为多区域高可用服务，无需额外配置。
  - Knowledge Catalog 元数据存储为区域级，选择支持多区域复制的区域（如 `us-central1` 或 `asia-east1`，待根据公司区域策略确认）。
  - Cross-Cloud Interconnect 配置冗余链路（separate domains），防止大规模查询期间网络中断。
- **备份与灾备**：
  - Knowledge Catalog 元数据定期导出至 Cloud Storage（跨区域复制）。
  - BigQuery 物化视图可通过查询历史重建，无需单独备份。
  - RTO ≤ 4 小时，RPO ≤ 1 小时（元数据层，假设项）。

### 6.3 运维卓越
- **监控与日志**：
  - Cloud Logging 收集所有查询日志、Spark 作业日志、元数据扫描日志。
  - Cloud Monitoring 建立仪表盘：查询延迟 P50/P95/P99、Spark 作业成功率、数据质量扫描通过率、跨云网络带宽利用率、月度成本趋势。
  - 告警规则：查询失败率 > 1%、数据新鲜度延迟 > 24 小时、成本异常增长 > 20% MoM。
- **基础设施即代码（IaC）**：
  - 推荐使用 Terraform 管理所有 GCP 资源（BigQuery 数据集、Knowledge Catalog 条目、Spark 会话模板、Interconnect 配置、IAM 策略）。
  - 代码纳入版本控制（Cloud Source Repositories 或公司 Git），CI/CD 流水线执行 `terraform plan` 审批后 `apply`。
- **Spark 会话管理**：
  - 在 Managed Service for Apache Spark 中部署可复用会话模板（`template.yaml`），按工作负载类型（ETL / ML / 交互查询）分别配置。
  - Knowledge Catalog 数据血缘用于上游 schema 变更的影响分析，变更前自动评估下游报表与作业影响。

### 6.4 成本优化
- **零拷贝架构**：
  - 运行零拷贝 Spark REST Catalog 查询 AWS S3，而非通过公网端点传输文件，消除网络出口费用。
  - 使用 BigQuery Omni 在 AWS 侧查询热数据，仅聚合结果回传。
- **资源 sizing 与伸缩**：
  - Managed Service for Apache Spark Serverless 自动伸缩，按实际使用计费。
  - 交互查询使用较小 Spark 会话模板，批处理 ETL/ML 使用较大模板。
  - BigQuery 采用按需计费 + 预留容量（flat-rate）混合模式：稳定报表负载用预留容量，临时分析用按需。
- **存储优化**：
  - Knowledge Catalog 血缘成本优化工具识别并清理孤立表（orphaned tables）。
  - BigQuery 分区表 + 聚簇索引，减少扫描数据量。
  - Cloud Storage 非结构化数据采用生命周期规则：30 天后转 Nearline，90 天后转 Coldline。

### 6.5 性能效率
- **Spark 性能配置**（依据 `design-recommendations.md`）：
  - 启用 Lightning Engine 原生运行时：`spark.dataproc.lightningEngine.runtime=native`。
  - 计算层级设为 premium：`dataproc.tier=premium`（在 Spark 会话模板中配置）。
  - 配置堆外内存：`spark.memory.offHeap.size=1g`，加速向量运算。
- **区域选择**：
  - 选择与 AWS S3 桶所在区域邻近的 Google Cloud 区域，最小化地理延迟（如 AWS `ap-northeast-1` 对应 GCP `asia-northeast1`）。
- **数据库与查询优化**：
  - BigQuery 物化视图预计算常用营销指标，自动刷新。
  - AlloyDB 列缓存（columnar engine）加速运营数据的复杂 join 查询。
  - Iceberg 表启用分区裁剪与统计信息，加速 Spark 查询。

### 6.6 可持续性
- 采用 Managed Service for Apache Spark Serverless + Lightning Engine，在内存中完成运算，减少服务器计算浪费。
- 零拷贝架构（BigQuery Omni / Spark REST Catalog）避免存储多 PB 级重复数据集。
- 非活跃数据自动转冷存储层级，减少存储碳足迹。
- 定期审查资源利用率，关停未使用的 Spark 会话与 BigQuery 预留容量。

---

## 7. 部署指南

> 以下为命令级部署指引，未提供完整 Terraform 代码文件（原因见 0.3 执行偏差声明）。所有命令需在具备 GCP 项目与计费账号的环境中执行。

### 7.1 部署前置条件
1. **Google Cloud 项目**：创建或选择一个项目，启用计费（需公司财务审批，待补）。
2. **启用 API**：
   ```bash
   gcloud services enable \
     bigquery.googleapis.com \
     dataplex.googleapis.com \
     dataproc.googleapis.com \
     storage.googleapis.com \
     alloydb.googleapis.com \
     secretmanager.googleapis.com \
     cloudkms.googleapis.com \
     monitoring.googleapis.com \
     logging.googleapis.com
   ```
3. **安装工具**：Google Cloud SDK（`gcloud`）、Terraform ≥ 1.5、kubectl（如需 GKE）。
4. **网络前置**：
   - Cross-Cloud Interconnect：需与 AWS 侧协同配置，预计周期 2-4 周（待补）。
   - Cloud Interconnect：需与本地数据中心网络团队协同，预计周期 4-8 周（待补）。
5. **凭据前置**：
   - AWS IAM 角色（用于 BigQuery Omni 与 Spark REST Catalog 访问 S3）。
   - 本地 Oracle ERP 与 MySQL POS 的只读数据库账号。
   - Salesforce API 连接凭据（如采用 API 接入）。

### 7.2 分步部署指引

**步骤 1：认证与项目设置**
```bash
gcloud auth login
gcloud config set project PROJECT_ID
gcloud config set compute/region REGION
```

**步骤 2：创建 Cloud Storage 桶（非结构化原始数据）**
```bash
gsutil mb -l REGION -c standard gs://BUCKET_NAME
gsutil versioning set on gs://BUCKET_NAME
```

**步骤 3：创建 BigQuery 数据集与物化视图**
```bash
bq --location=REGION mk \
  --dataset \
  --default_table_expiration 31536000 \
  PROJECT_ID:smart_mug_analytics
```
（物化视图 SQL 需根据实际表结构编写，此处略。）

**步骤 4：配置 Knowledge Catalog**
- 创建业务术语表（business glossary）：定义"首周销量""退货率""保温达标率"等术语。
- 创建自定义 Aspect 类型：`pii_restricted`、`data_status`、`data_domain`。
- 配置元数据扫描：BigQuery 数据集、Cloud Storage 桶。
- 配置自定义源接入：AWS S3、本地 Oracle ERP、本地 MySQL POS（参考 `references/knowledge-catalog-documentation.md` 中 `ingest-custom-sources` 指南）。

**步骤 5：配置 Secret Manager 凭据**
```bash
echo -n "AWS_ACCESS_KEY_ID" | gcloud secrets create aws-access-key-id --data-file=-
echo -n "AWS_SECRET_ACCESS_KEY" | gcloud secrets create aws-secret-access-key --data-file=-
echo -n "oracle://user:pass@host:1521/db" | gcloud secrets create erp-connection --data-file=-
```

**步骤 6：创建 Spark 会话模板**
创建 `template.yaml`（关键配置）：
```yaml
sparkConfig:
  spark.dataproc.lightningEngine.runtime: native
  dataproc.tier: premium
  spark.memory.offHeap.enabled: "true"
  spark.memory.offHeap.size: 1g
  spark.sql.catalog.aws_iceberg: org.apache.iceberg.spark.SparkCatalog
  spark.sql.catalog.aws_iceberg.catalog-impl: org.apache.iceberg.rest.RESTCatalog
  spark.sql.catalog.aws_iceberg.uri: https://ICEBERG_REST_CATALOG_ENDPOINT
```
提交模板：
```bash
gcloud dataproc sessions create spark-interactive TEMPLATE_NAME \
  --region=REGION \
  --session-template=template.yaml
```

**步骤 7：配置 BigQuery Omni（AWS 侧）**
- 在 AWS 侧创建 IAM 角色，授权 BigQuery Omni 服务账号访问指定 S3 桶。
- 在 BigQuery 中创建 AWS 外部连接与外部表。
（具体步骤参考 BigQuery Omni 官方文档，待 grounding 补全。）

**步骤 8：配置 Cross-Cloud Interconnect 与 Cloud Interconnect**
- 需与网络团队协同，通过 Google Cloud Console 或 Terraform 配置。
- 配置冗余链路（separate domains）。

**步骤 9：部署 AlloyDB 实例**
```bash
gcloud alloydb clusters create CLUSTER_NAME \
  --region=REGION \
  --network=VPC_NAME
gcloud alloydb instances create INSTANCE_NAME \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --instance-type=PRIMARY \
  --cpu-count=4
```

**步骤 10：配置监控与告警**
- 在 Cloud Monitoring 中创建仪表盘与告警策略。
- 配置 Cloud Logging 日志路由与保留策略。

---

## 8. 验证计划

> 基于 SKILL.md Phase 3。以下为验证计划与脚本，**未实际执行**（无 GCP 项目与凭据，见 0.3）。执行前需用户授权并具备有效 GCP 环境。

### 8.1 验证目标
验证所设计的架构是否满足功能与非功能需求，重点验证：
1. 跨云零拷贝联邦查询可用性
2. PII 数据不泄漏（安全策略有效性）
3. 营销看板查询延迟 SLA
4. 元数据治理与血缘追踪完整性
5. 故障恢复能力（RTO/RPO）

### 8.2 验证步骤与脚本

**验证项 1：BigQuery 数据集与物化视图可用性**
```bash
# 检查数据集存在
bq show PROJECT_ID:smart_mug_analytics
# 执行测试查询
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM \`PROJECT_ID.smart_mug_analytics.daily_sales_mv\`'
```
**预期结果**：数据集存在，物化视图返回非零行数。

**验证项 2：Knowledge Catalog 元数据扫描**
```bash
# 列出 Knowledge Catalog 条目（使用 Dataplex API，旧 API 名）
curl -X GET \
  "https://dataplex.googleapis.com/v1/projects/PROJECT_ID/locations/REGION/entryGroups?pageSize=10" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)"
```
**预期结果**：返回包含 BigQuery、Cloud Storage、AWS S3（自定义源）、本地 ERP（自定义源）的元数据条目。

**验证项 3：Spark 零拷贝查询 AWS S3**
```bash
# 提交 Spark 作业测试 Iceberg REST Catalog 连接
gcloud dataproc batches submit spark \
  --region=REGION \
  --batch=BATCH_ID \
  --jar=gs://BUCKET_NAME/jars/iceberg-spark-runtime.jar \
  --properties="spark.sql.catalog.aws_iceberg.catalog-impl=org.apache.iceberg.rest.RESTCatalog,spark.sql.catalog.aws_iceberg.uri=REST_CATALOG_URI" \
  -- "SELECT count(*) FROM aws_iceberg.daily_orders WHERE dt >= '2026-08-01'"
```
**预期结果**：作业成功完成，返回 S3 上订单表的记录数，且未在 GCP 侧产生数据复制。

**验证项 4：PII 安全策略验证**
```bash
# 以普通分析师身份尝试查询含 PII 的 ERP 表
bq query --use_legacy_sql=false \
  'SELECT supplier_name, bank_account FROM \`PROJECT_ID.erp_federated.suppliers\` LIMIT 5'
```
**预期结果**：查询被拒绝或返回掩码值（`supplier_name` 显示为 `***`，`bank_account` 不可访问），证明列级安全策略生效。

**验证项 5：营销看板延迟测试**
```bash
# 连续执行 20 次看板查询，记录延迟
for i in $(seq 1 20); do
  start=$(date +%s%N)
  bq query --use_legacy_sql=false --format=none \
    'SELECT * FROM \`PROJECT_ID.smart_mug_analytics.marketing_dashboard_mv\` WHERE dt = CURRENT_DATE() - 1'
  end=$(date +%s%N)
  echo "Query $i: $(( (end - start) / 1000000 )) ms"
done
```
**预期结果**：P95 延迟 ≤ 10 秒（热数据命中物化视图）。

**验证项 6：数据血缘验证**
```bash
# 查询 Knowledge Catalog 血缘（Dataplex API）
curl -X GET \
  "https://dataplex.googleapis.com/v1/projects/PROJECT_ID/locations/REGION/entryGroups/@dataplex/entries/TABLE_ENTRY_ID/lineage" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)"
```
**预期结果**：返回从源表（S3 订单表）到目标表（BigQuery 物化视图）的完整血缘链路。

**验证项 7：故障恢复测试**
- 手动断开一条 Cross-Cloud Interconnect 链路，验证联邦查询通过冗余链路继续可用。
- 恢复 Knowledge Catalog 元数据从 Cloud Storage 备份，验证 RTO ≤ 4 小时。
（此验证项需在维护窗口执行，需网络团队协同。）

### 8.3 验证验收标准
| 验证项 | 通过标准 |
|---|---|
| BigQuery 可用性 | 数据集与物化视图存在，查询成功 |
| 元数据扫描 | 所有数据源元数据已收录，Aspect 标记正确 |
| Spark 零拷贝查询 | 作业成功，无数据复制至 GCP 存储 |
| PII 安全 | 普通用户无法访问原始 PII 字段 |
| 营销看板延迟 | P95 ≤ 10 秒（热数据） |
| 数据血缘 | 端到端血缘链路完整 |
| 故障恢复 | 单链路故障不中断服务，RTO 达标 |

---

## 9. 风险、依赖与待补项

### 9.1 关键风险
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| Cross-Cloud Interconnect / Cloud Interconnect 部署周期长（2-8 周） | 项目延期 | 高 | 提前启动网络配置流程；过渡期可用公网 VPN + 加密隧道（仅用于非敏感数据测试） |
| 本地 ERP PII 合规审批未通过 | 无法接入 ERP 数据，库存分析功能缺失 | 中 | 提前与法务/合规团队沟通；准备替代方案（ERP 侧定期导出脱敏聚合数据至 GCS） |
| AWS S3 数据为 T+1 批量导出，无法满足实时需求 | 营销看板新鲜度不足 | 中 | 与电商平台沟通开放流式 API；或接受 T+1 并在产品中明确标注数据时间 |
| Knowledge Catalog 自定义源接入复杂度高 | 元数据收录不完整 | 中 | 参考 `ingest-custom-sources` 指南分阶段接入；优先接入 BigQuery/GCS，再接入 S3，最后接入本地源 |
| 新品数据缺失导致平台初期价值低 | 业务方满意度低 | 高 | 采用渐进式接入策略；优先上线已有数据（历史销售、产品素材）的分析功能；缺失数据明确标注为待补 |
| BigQuery Omni 区域可用性限制 | 无法在目标区域部署 | 低 | 提前确认 BigQuery Omni 支持的 AWS 区域；备选方案为 Spark REST Catalog 全量查询 |
| Lightning Engine premium 层级成本超预期 | 月度成本超预算 | 中 | 先以非 premium 层级测试，评估性能提升与成本增量后再决定；设置预算告警 |

### 9.2 关键依赖
1. **网络依赖**：Cross-Cloud Interconnect 与 Cloud Interconnect 的物理链路部署，依赖网络服务商与公司 IT 团队。
2. **凭据依赖**：AWS IAM 角色、本地数据库账号、Salesforce API 凭据，需各系统管理员提供。
3. **合规依赖**：PII 数据跨域传输审批，需法务/合规团队签字。
4. **数据依赖**：
   - 首发日期（product_brief 不完整信息）→ 影响营销日历与需求预测时间轴。
   - 防水等级与食品接触材料报告（product_brief 不完整信息）→ 影响产品质量维度分析。
   - 竞品价格数据（product_brief 禁止编造）→ 竞品分析功能待合法数据源接入后启用。
5. **人员依赖**：数据治理管理员配置业务术语表与 Aspect；数据所有者认证数据集。

### 9.3 待补项清单（不得编造）
| 待补项 | 来源 | 影响 | 补齐方式 |
|---|---|---|---|
| 首发日期 | product_brief 不完整信息 | 营销日历、需求预测时间轴 | 产品团队确认后更新元数据 |
| 防水等级 | product_brief 不完整信息 | 产品质量分析维度 | 收到检测报告后录入 |
| 食品接触材料报告 | product_brief 不完整信息 | 合规与质量分析 | 收到第三方报告后录入 |
| 第三方检测结论 | product_brief 禁止编造 | 产品卖点验证 | 收到合法检测报告后录入 |
| 销量数据 | product_brief 禁止编造 | 需求预测与销售分析 | 上市后实际数据接入 |
| 用户评价 | product_brief 禁止编造 | 情感分析与产品改进 | 电商平台评论数据接入 |
| 竞品价格 | product_brief 禁止编造 | 竞品分析与定价策略 | 采购竞品数据服务或人工录入 |
| GCP 项目 ID 与计费账号 | 执行环境缺失 | 全部部署与验证 | 公司 IT 提供 |
| AWS S3 桶名与 IAM 角色 | 执行环境缺失 | 跨云联邦查询 | 电商运营团队提供 |
| 本地 ERP/POS 连接信息 | 执行环境缺失 | 本地数据联邦查询 | IT 部门提供 |
| BigQuery Omni 官方文档实时 grounding | 无 MCP 访问 | 部署步骤精确性 | 具备网络授权后调用 Google Developer Knowledge MCP 补全 |

---

## 10. 结论

### 10.1 核心结论
1. **方案可行**：基于 Knowledge Catalog + Managed Service for Apache Spark（Lightning Engine）+ Lakehouse for Apache Iceberg 的零拷贝联邦分析架构，能够满足智能随行杯新品上市的跨系统智能分析需求。
2. **三大矛盾已消解**：
   - PII 数据驻留 vs. 零拷贝查询 → 零拷贝 + 行列级安全策略，仅聚合非敏感结果回传。
   - 实时低延迟 vs. 跨云成本 → 热数据用 BigQuery Omni + 物化视图，冷数据用 Spark 零拷贝，接受 T+1 新鲜度。
   - 数据缺失 vs. 平台完整性 → 渐进式接入，缺失维度标记 pending，agent 主动提示而非编造。
3. **核心约束**：本方案的所有设计与建议基于 Skill 内置参考文件 grounding，**未调用外部 Google Cloud MCP 或实时官方文档**，部署指南中的具体参数（如区域、实例规格）需在实际 GCP 环境中结合官方文档确认。
4. **验证未执行**：因无 GCP 项目与凭据，Phase 3 验证脚本未实际运行，所有验证结果为预期值而非实测值。

### 10.2 验收方法
1. **文档验收**：本文档覆盖 SKILL.md 要求的四阶段产出（需求发现、技术分解、产品映射、架构图、架构描述、设计建议、部署指南、验证计划），结构遵循 `assets/output-template.md`。
2. **技术验收**：在具备 GCP 环境后，按第 8 节验证计划逐项执行，7 项验证全部通过即为技术验收通过。
3. **业务验收**：
   - 分析师可在 IDE 中用自然语言查询跨系统销售数据并获得正确结果。
   - PII 数据不可被未授权用户访问。
   - 营销看板 P95 延迟 ≤ 10 秒。
   - 缺失数据维度不产生编造结果，agent 明确提示数据缺失。

---

## 11. 实际读取的 Skill 文件相对路径

以下为本次执行中**实际读取**的文件（相对于 Skill 根目录 `google-cloud-solution-agentic-analytics-spark-knowledge-catalog/`）：

1. `SKILL.md` — 主工作流定义（四阶段、严格阶段分离、矛盾消解规则、grounding 要求）
2. `assets/output-template.md` — 输出文档模板（8 节结构）
3. `references/product-selection-guidance.md` — 产品选择指南（新旧命名映射、推荐产品与替代方案）
4. `references/design-recommendations.md` — 设计建议（六大支柱的具体配置项）
5. `references/knowledge-catalog-documentation.md` — Knowledge Catalog 官方文档索引（12 篇文档链接）

**未读取/未调用**：
- Google Developer Knowledge MCP server（无访问凭据）
- `https://github.com/google/skills` 相关 skills（无网络授权）
- 所有 `https://docs.cloud.google.com/...` 实时官方文档（无网络授权，仅使用了 Skill 内置的文档索引链接作为参考）
- `google-cloud-waf-*` 系列安全/可靠性/成本等 skills（未安装，无访问路径）

---

## 12. 影响结果的 SKILL.md 规则

> 以下规则**确实影响了**本次交付的内容与形式：

**规则一（最关键）：Phase 1 Step 5——矛盾未消解前不得生成架构。**
SKILL.md 原文："Until all the ambiguities and contradictions that you identify are resolved... you must NOT recommend or generate any architecture design, technical decomposition, or Google Cloud product recommendations."
- **影响**：本文档在第 3 节专门列出并消解了三大矛盾（PII 驻留 vs. 零拷贝、实时性 vs. 成本、数据缺失 vs. 完整性），然后才在第 4-5 节给出技术分解与架构设计。若忽略此规则，将直接生成架构而不处理矛盾，导致方案存在合规与成本硬伤。

**规则二：Phase 2 "Ground all generated content"——必须基于 Google 官方资源 grounding。**
- **影响**：本文档明确声明仅使用 Skill 内置参考文件 grounding，未调用外部 MCP 与实时文档，并在待补项中列出需补全的 grounding。产品命名严格遵循 `product-selection-guidance.md` 的新旧映射（如使用 Knowledge Catalog 而非 Dataplex），设计建议中的 Spark 配置参数（`spark.dataproc.lightningEngine.runtime=native` 等）直接来自 `design-recommendations.md`。

**规则三：Phase 3 Step 6——需用户授权才能执行验证。**
- **影响**：本文档仅生成验证计划与脚本，未实际执行任何 `gcloud`/`curl` 命令，所有验证结果为预期值。这避免了在无 GCP 凭据情况下伪造执行结果的风险。

---

## 13. 参考资源

> 以下链接来自 Skill 内置文件，仅作索引参考，**未在本次执行中实际访问**。

- Knowledge Catalog AI 概览：https://docs.cloud.google.com/dataplex/docs/ai-overview.md.txt
- Knowledge Catalog 发现代理设置：https://docs.cloud.google.com/dataplex/docs/use-discovery-agent.md.txt
- 元数据自动丰富：https://docs.cloud.google.com/dataplex/docs/build-agent-to-enrich-metadata.md.txt
- 建立基础数据上下文（业务术语表 + Aspect）：https://docs.cloud.google.com/dataplex/docs/establish-foundational-data-context.md.txt
- 策略合规的湖仓访问控制：https://docs.cloud.google.com/dataplex/docs/enable-policy-compliant-lakehouse-access.md.txt
- 自定义源接入：https://docs.cloud.google.com/dataplex/docs/ingest-custom-sources.md.txt
- 数据质量扫描：https://docs.cloud.google.com/dataplex/docs/profile-ensure-data-quality.md.txt
- Gemini CLI 测试数据上下文：https://docs.cloud.google.com/dataplex/docs/use-gemini-cli-agent-to-test-data-context.md.txt
- 数据血缘影响分析：https://docs.cloud.google.com/dataplex/docs/lineage-use-cases-impact-analysis.md.txt
- PII 泄漏血缘追踪：https://docs.cloud.google.com/dataplex/docs/lineage-use-cases-pii-leakage.md.txt
- Lightning Engine 加速 Spark：https://docs.cloud.google.com/managed-spark/docs/guides/lightning-engine.md.txt
- BigQuery 使用 Knowledge Catalog：https://docs.cloud.google.com/bigquery/docs/use-knowledge-catalog.md.txt
- 跨云智能分析参考架构：https://docs.cloud.google.com/architecture/agentic-ai-cross-cloud-analytics.md.txt
- Data Agent Kit 扩展：https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/tree/main/skills
- 跨云数据拓扑分析 Codelab：https://codelabs.developers.google.com/next26/gen-keynote/raw-data-forecasting#0
- 治理上下文 Codelab：https://codelabs.developers.google.com/governance-context-part1#0
