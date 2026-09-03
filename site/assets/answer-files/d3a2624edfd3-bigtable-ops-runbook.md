# Bigtable 基础设施配置、运维与故障排查方案

> 本方案严格依据 `bigtable-basics` Skill 的 SKILL.md 及其 references 编写，所有命令与模式均来自 Skill 文档，未引入文档之外的工具或流程。

---

## 一、能力边界与题目假设的冲突说明

| 题目表述 | Skill 实际边界 | 处理方式 |
|---|---|---|
| "云端基础设施配置、运维与故障排查"（广义） | Skill 仅覆盖 **Google Cloud Bigtable** 的实例/集群/表/列族/GC 策略/备份/IAM（控制面）与数据读写（数据面），以及热点诊断；明确声明"不用于通用 Cloud SQL 管理" | 本方案只覆盖 Bigtable 范围内的配置、运维与排障，不扩展到 VPC、GKE、Cloud SQL 等其他云资源 |
| "同一项目必须兼容既有接口和目录结构" | 工作目录中除 Skill 文件外**不存在既有应用项目或代码**，无法验证接口/目录兼容性 | 标注为待确认项；方案以"不改动既有代码、仅提供命令与配置"为原则 |
| "不能随意升级主版本或引入未经批准的新依赖" | Skill 不涉及依赖管理；所引用的客户端库为 Google 官方 Bigtable 客户端（Java/Go/Python），无新增第三方依赖 | 不引入任何新依赖；如需客户端代码，沿用官方库既有版本 |

---

## 二、当前环境状态（已核实，非假设）

- **gcloud CLI**：未安装
- **cbt CLI**：未安装
- **GCP 项目/实例/集群**：未提供任何项目 ID、实例 ID、区域、节点数等信息
- **既有项目代码**：工作目录中不存在（仅有 Skill 压缩包及解压文件）
- **认证状态**：无法验证（gcloud 未安装）

> 因此，本方案提供的是**可直接审阅、待确认后执行**的命令与流程，不包含任何已执行的操作或虚构的运行结果。

---

## 三、最小改动方案

### 3.1 工具准备（前置，仅安装不改动数据库）

```bash
# 安装 Google Cloud SDK（含 gcloud），具体方式依操作系统而定
# macOS 示例：
brew install --cask google-cloud-sdk

# 安装 cbt 组件
gcloud components install cbt

# 认证
gcloud auth login
gcloud config set project ${BIGTABLE_PROJECT}
```

> **安全规则（SKILL.md 明确要求）**：在对非模拟器的数据库做任何变更前，必须获得用户明确确认。以下所有标记为【需确认】的命令，在您确认前不会执行。

### 3.2 控制面：实例与集群（gcloud）

#### 3.2.1 查看现状（只读，安全）

```bash
# 列出现有实例
gcloud bigtable instances list

# 查看实例详情
gcloud bigtable instances describe ${BIGTABLE_INSTANCE}

# 列出集群
gcloud bigtable clusters list --instance=${BIGTABLE_INSTANCE}
```

#### 3.2.2 创建实例（仅在确认需要新建时）【需确认】

```bash
gcloud bigtable instances create ${BIGTABLE_INSTANCE} \
    --project=${BIGTABLE_PROJECT} \
    --display-name="${DISPLAY_NAME}" \
    --cluster-config=id=${BIGTABLE_CLUSTER},zone=${ZONE},nodes=${NUM_NODES}
```

**最小改动原则**：若实例已存在，不重建；仅通过 `clusters create` 按需添加集群。

#### 3.2.3 添加集群（如需多集群/高可用）【需确认】

```bash
gcloud bigtable clusters create ${NEW_CLUSTER} \
    --instance=${BIGTABLE_INSTANCE} \
    --zone=${NEW_ZONE} \
    --nodes=${NUM_NODES}
```

> **注意（来自 client_libraries.md）**：若应用使用 ReadModifyWrite（计数器/追加）或 CheckAndMutateRow（条件更新），多集群路由下这些操作会失败，必须使用**单集群路由**的 App Profile。

### 3.3 控制面：表与 Schema（gcloud DDL）

> SQL API 不支持 DDL。建表/删表/改表必须通过 gcloud（SKILL.md 第 65-69 行）。

#### 3.3.1 建表前先检查（只读）

```bash
# 列出已有表
cbt ls

# 查看目标表的列族与 GC 策略（Schema 演进前必须先查）
cbt ls ${TABLE_NAME}
```

#### 3.3.2 建表（仅新建场景）【需确认】

```bash
# 单列表族
gcloud bigtable instances tables create ${TABLE_NAME} \
    --instance=${BIGTABLE_INSTANCE} \
    --column-families=${FAMILY_NAME}

# 多列族 + GC 策略
gcloud bigtable instances tables create ${TABLE_NAME} \
    --instance=${BIGTABLE_INSTANCE} \
    --column-families="family1:maxage=10d,family2:maxversions=5"
```

#### 3.3.3 Schema 演进（最小改动：只增不删）

依据 SKILL.md "Schema Evolution (DevOps)" 章节，生产环境**优先使用 Terraform** 管理 schema 以防误删；手动 cbt 变更前必须先查现状。

```bash
# 1. 先查现状（已在 3.3.1 执行）
cbt ls ${TABLE_NAME}

# 2. 新增列族（ additive，不影响现有数据）【需确认】
cbt createfamily ${TABLE_NAME} ${NEW_FAMILY}

# 3. 设置/更新 GC 策略【需确认】
cbt setgcpolicy ${TABLE_NAME} ${NEW_FAMILY} "maxversions=5 AND maxage=30d"
```

**不建议的操作（破坏性）**：
- `cbt deletefamily` 会删除该列族全部数据——除非有备份且明确要求，否则不执行。
- `cbt deletetable` 会删除整张表——同上。

#### 3.3.4 结构化行键（Structured Row Keys）

若需要通过 SQL 按行键分段名查询，使用 Skill 附带的模板 `assets/row_key_schema.yaml` 定义：

```bash
gcloud bigtable instances tables update ${TABLE_NAME} \
    --instance=${BIGTABLE_INSTANCE} \
    --row-key-schema-definition-file=row_key_schema.yaml
```

模板内容（来自 Skill assets）：
```yaml
encoding:
  delimitedBytes:
    delimiter: '#'
fields:
- fieldName: field1
  type:
    bytesType:
      encoding:
        raw: {}
- fieldName: field2
  type:
    bytesType:
      encoding:
        raw: {}
```

> 实际使用时需将 `field1`/`field2` 替换为真实分段名（如 `tenant_id`、`entity_type`）。

### 3.4 数据面：日常运维（cbt）

#### 3.4.1 配置 cbt

```bash
echo project = ${BIGTABLE_PROJECT} > ~/.cbtrc
echo instance = ${BIGTABLE_INSTANCE} >> ~/.cbtrc
```

#### 3.4.2 读取数据（排障/验证用）

```bash
# 单行点查（最高效，优先使用）
cbt lookup ${TABLE_NAME} ${ROW_KEY}

# 读前 N 行
cbt read ${TABLE_NAME} count=${N}

# 范围读（start 含，end 不含）
cbt read ${TABLE_NAME} start=${START_KEY} end=${END_KEY}

# SQL 查询（复杂聚合）
cbt sql "SELECT * FROM ${TABLE_NAME} WHERE _key = '${ROW_KEY}'"

# 带统计信息的慢查询诊断
cbt read ${TABLE_NAME} ${ROW_KEY} include-stats=full
```

> **全表扫描警告（SKILL.md 核心原则）**：`cbt count ${TABLE_NAME}` 会触发全表扫描，应避免。行数估算请用：
> ```bash
> gcloud bigtable instances tables describe ${TABLE_ID} \
>     --instance=${BIGTABLE_INSTANCE} --view stats
> ```

#### 3.4.3 写入/删除数据

```bash
# 写单元格【需确认】
cbt set ${TABLE_NAME} ${ROW_KEY} ${FAMILY}:${COLUMN}=${VALUE}

# 删除行【需确认】
cbt deleterow ${TABLE_NAME} ${ROW_KEY}
```

### 3.5 备份与恢复

```bash
# 创建备份（变更前的安全网）【需确认】
gcloud bigtable backups create ${BACKUP_ID} \
    --instance=${BIGTABLE_INSTANCE} \
    --cluster=${BIGTABLE_CLUSTER} \
    --table=${TABLE_ID} \
    --retention-period=7d

# 从备份恢复到新表（不覆盖原表）
gcloud bigtable instances tables restore \
    --source=projects/${PROJECT_ID}/instances/${BIGTABLE_INSTANCE}/clusters/${BIGTABLE_CLUSTER}/backups/${BACKUP_ID} \
    --destination=${NEW_TABLE_ID} \
    --destination-instance=${BIGTABLE_INSTANCE} \
    --project=${BIGTABLE_PROJECT} \
    --async
```

---

## 四、故障排查流程

依据 SKILL.md "Observability" 核心原则，诊断性能/热点问题时**必须按以下顺序**：

### 4.1 第一步：Key Visualizer（主要诊断工具）

在 Google Cloud Console 中打开 Key Visualizer，查看行键访问模式热力图。这是 SKILL.md 明确要求的首要工具，提供最细粒度的访问分布视图。

### 4.2 第二步：热点 Tablet 列表（gcloud）

```bash
gcloud bigtable hot-tablets list ${BIGTABLE_CLUSTER} --instance=${BIGTABLE_INSTANCE}
```

识别 CPU 使用率高的具体 tablet。

### 4.3 第三步：慢查询统计（cbt）

```bash
cbt read ${TABLE_NAME} include-stats=full
```

### 4.4 常见问题与处置

| 现象 | 可能原因 | 处置方向（依据 Skill） |
|---|---|---|
| 写入热点，单节点 CPU 高 | 行键以时间戳/自增序列开头 | 改用高基数前缀或反转时间戳，如 `tenantID#reversedTimestamp#objectID`；低基数前缀加 salt：`salt = hash(original_key) % num_nodes` |
| 读取延迟高 | 全表扫描或大范围扫描 | 改用点查（`_key =`）、前缀扫描（`STARTS_WITH`）或范围扫描（`_key BETWEEN`）；用户面/低延迟场景用连续物化视图；低频批量场景用 Bigtable Data Boost |
| ReadModifyWrite/CheckAndMutateRow 失败 | 多集群路由 App Profile | 改用单集群路由 App Profile（client_libraries.md 明确要求） |
| SQL 点查写法报错 | 使用了点号语法 `cf.col` | 必须用方括号 `cf['col']`（sql_guide.md） |
| 模拟器上 SQL 不工作 | 模拟器不支持 GoogleSQL | 在真实实例上测试 SQL（infrastructure_management.md 末尾注释） |

### 4.5 行键设计验证清单（来自 schema_design.md）

- [ ] 行键 < 4KB（理想 10–100 字节）
- [ ] 全局唯一（重复键会覆盖数据）
- [ ] 字符集 `^[a-zA-Z0-9\-_#]+$`，数字零填充以保证字符串排序正确
- [ ] 列限定符 < 16KB
- [ ] 列族数量 < 100，名称简短
- [ ] 单元格值 < 10MB（硬限制 100MB）
- [ ] 行大小 < 100MB（读取时硬限制 256MB）
- [ ] 时间戳：毫秒精度 × 1000 转微秒（client_libraries.md 实现规则）

---

## 五、回滚办法

| 变更类型 | 回滚方式 |
|---|---|
| 新增列族 | `cbt deletefamily ${TABLE_NAME} ${FAMILY}` 【需确认，破坏性】；或保留空列族不影响数据 |
| GC 策略变更 | `cbt setgcpolicy` 重新设回原值（已被 GC 清理的数据无法恢复） |
| 表结构/数据误操作 | 从 3.5 节创建的备份恢复到新表，验证后再切换 |
| 新建实例/集群 | `gcloud bigtable instances delete` 或删除集群【需确认，破坏性】 |
| 行键 schema 定义更新 | 重新 `gcloud bigtable instances tables update` 传回旧定义文件 |

> **关键前提**：任何变更前先创建备份（3.5 节）。GC 策略收紧后，超出新策略的旧版本会被异步清理，无法通过回滚 GC 策略找回，因此 GC 变更需格外谨慎。

---

## 六、测试清单

### 6.1 本地模拟器测试（无风险，可先行）

```bash
# 启动模拟器
gcloud beta emulators bigtable start --host-port=localhost:8086

# 指向模拟器
export BIGTABLE_EMULATOR_HOST=localhost:8086

# 在模拟器上验证建表、列族、读写流程
cbt createtable test_table
cbt createfamily test_table test_family
cbt set test_table row1 test_family:col1=value1
cbt lookup test_table row1
```

> 模拟器限制：不支持 Bigtable GoogleSQL，SQL 相关测试需在真实实例的测试环境中进行。

### 6.2 变更前验证

- [ ] `cbt ls ${TABLE_NAME}` 确认当前列族与 GC 策略已记录
- [ ] 备份已创建且 `gcloud bigtable backups describe` 状态为 ready
- [ ] 待执行命令已在文档中审阅
- [ ] 已获得用户明确确认（SKILL.md 安全规则）

### 6.3 变更后验证

- [ ] `cbt ls ${TABLE_NAME}` 确认列族/GC 策略符合预期
- [ ] `cbt lookup` 抽样验证既有数据可读
- [ ] 应用侧冒烟测试通过
- [ ] Key Visualizer 观察 15–30 分钟，无新热点
- [ ] `gcloud bigtable hot-tablets list` 无异常高 CPU tablet

---

## 七、仍待确认项

以下信息缺失，在您提供前无法执行任何真实操作：

1. **GCP 项目 ID**（`${BIGTABLE_PROJECT}`）
2. **Bigtable 实例 ID**（`${BIGTABLE_INSTANCE}`）——是新建还是使用已有实例？
3. **集群 ID、区域/可用区、节点数**
4. **表名、列族名、GC 策略需求**
5. **具体故障现象**（如有）：延迟指标、错误日志、热点表现
6. **App Profile 路由策略**：单集群还是多集群？是否使用 ReadModifyWrite/CheckAndMutateRow？
7. **既有项目代码位置**：当前工作目录中未发现应用代码，如需兼容既有接口/目录结构，请提供项目路径
8. **是否允许安装 gcloud/cbt**（当前环境未安装）
9. **Terraform 使用情况**：Skill 建议生产 schema 变更优先用 Terraform，需确认现有 IaC 仓库与流程

---

## 八、约束如何改变了实现选择

1. **SKILL.md 安全规则（第 34-37 行）**：要求对非模拟器数据库变更必须获得用户明确确认。因此本方案只提供命令文档，不直接执行任何 `gcloud`/`cbt` 写操作；所有写命令均标注【需确认】。
2. **控制面/数据面分离原则**：建表/DDL 一律用 `gcloud`，列族/数据操作用 `cbt`，未混用。
3. **"优先 Terraform"与"先查后改"**：Schema 演进部分先 `cbt ls` 查现状，且只做 additive 变更（新增列族），不做破坏性删除。
4. **可观测性强制顺序**：排障流程严格按 Key Visualizer → hot-tablets → include-stats 的顺序，未跳过 Key Visualizer 直接给命令。
5. **不编造运行结果**：gcloud/cbt 未安装、无项目信息，因此未声称任何命令已执行成功，所有输出均为待验证。
6. **不扩展 Skill 职责**：题目广义的"云端基础设施"被收敛到 Bigtable 范围，未提供 VPC/网络/IAM 全局配置等 Skill 未覆盖的内容。
7. **客户端语言选择**：遵循 Skill 建议，生产场景优先 Java/Go，Python 仅用于脚本/数据科学。

---

## 九、实际读取的 Skill 文件（相对路径）

- `bigtable-basics/SKILL.md`
- `bigtable-basics/references/infrastructure_management.md`
- `bigtable-basics/references/cli_data_access.md`
- `bigtable-basics/references/schema_design.md`
- `bigtable-basics/references/sql_guide.md`
- `bigtable-basics/references/client_libraries.md`
- `bigtable-basics/references/dataplex.md`
- `bigtable-basics/assets/row_key_schema.yaml`

（以上路径相对于解压目录 `bigtable-basics/bigtable-basics/`）

---

## 十、实际影响交付结果的 SKILL.md 规则

**安全规则（SKILL.md 第 34-37 行）**：

> "You MUST obtain explicit user confirmation before making non-emulator database changes. You MUST mention this safety requirement when providing commands or instructions that modify the database structure or data."

这条规则直接决定了本方案的交付形态：我提供了完整的命令与流程，但**没有执行任何写操作**，并在每条结构/数据变更命令上标注了【需确认】。如果没有这条规则，方案可能会直接尝试运行 gcloud/cbt 命令——但在当前环境（工具未安装、项目未配置）下那样做既不可行也不安全。
