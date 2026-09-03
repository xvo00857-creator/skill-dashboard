# 文件整理变更清单

> 基于 neat-freak Skill 规则执行的知识治理与工作区整理
> 整理日期：2026-08-07
> 路径模式：轻量路径（单人项目、无规则文件、文档量少）

---

## 一、整理原则

1. **分类优先**：按文件用途归入语义化目录，根目录不放裸文件
2. **命名规范**：统一使用 kebab-case，文件名包含日期/主题等可检索信息
3. **去重保守**：内容重复的文件只保留一个权威版本，其余移入删除候选区，**未确认前不删除**
4. **未知保留**：归属或用途无法判断的文件，移入 `_unclassified/` 保留，不做猜测性归类
5. **垃圾隔离**：系统生成的元数据文件（如 macOS `._` 文件）移入删除候选区
6. **可逆原则**：所有变更均可通过本清单回溯，原始文件未被物理删除

---

## 二、目录结构（整理后）

```
neat-freak-fixture-organized/
├── docs/
│   ├── contracts/          # 合同与法务文档
│   └── meetings/           # 会议纪要
├── finance/                # 财务单据与发票
├── assets/
│   └── brand/              # 品牌与设计资产
├── _unclassified/          # 归属暂不明确的文件（保留待确认）
├── _cleanup-candidate/     # 删除候选区（待用户确认后清理）
└── CHANGELOG.md            # 本变更清单
```

---

## 三、变更明细

### 3.1 分类 + 重命名（已执行）

| 原始路径 | 新路径 | 变更类型 | 理由 |
|---|---|---|---|
| `contract-draft.txt` | `docs/contracts/contract-draft.txt` | 分类 | 合同类文档归入法务目录 |
| `invoice-july.txt` | `finance/2026-07-invoice-supplier-a.txt` | 分类 + 重命名 | 财务单据归入 finance；补充年月与供应商信息，便于检索和排序 |
| `logo-old.txt` | `assets/brand/logo-legacy.txt` | 分类 + 重命名 | 品牌素材归入 assets/brand；"old"改为"legacy"更规范，明确标注为历史版本 |
| `meeting-notes-final-final.txt` | `docs/meetings/2026-07-18-project-kickoff-meeting-notes.txt` | 分类 + 重命名 | 会议纪要归入 docs/meetings；规范命名为「日期-主题-类型」格式，消除"final-final"冗余版本号 |

### 3.2 去重（移入删除候选区，未删除）

| 文件 | 移入路径 | 理由 |
|---|---|---|
| `meeting-notes-final-v2.txt` | `_cleanup-candidate/meeting-notes-final-v2.txt` | 与 `meeting-notes-final-final.txt` 内容**完全相同**（均为 2026-07-18 项目启动会记录）。保留命名更晚的 final-final 版本（已重命名为规范名称），v2 版列为删除候选 |

### 3.3 系统垃圾（移入删除候选区，未删除）

| 项目 | 移入路径 | 理由 |
|---|---|---|
| `__MACOSX/` 目录（含全部 `._*` 元数据文件） | `_cleanup-candidate/__MACOSX/` | macOS 压缩包自动生成的元数据垃圾，无业务价值 |

### 3.4 未分类（保留待确认）

| 文件 | 移入路径 | 理由 |
|---|---|---|
| `screenshot-001.txt` | `_unclassified/screenshot-001.txt` | 文件标注为"模拟截图占位文件，归属暂不明确"，无法判断应归入哪个业务目录。保留待用户补充信息后再归类 |

---

## 四、待用户确认事项

### 删除候选清单（确认后可安全删除）

1. `_cleanup-candidate/meeting-notes-final-v2.txt` — 重复会议纪要，内容与权威版完全一致
2. `_cleanup-candidate/__MACOSX/` — macOS 系统元数据，无业务价值

> **以上文件目前仅隔离，未物理删除。** 请确认后执行清理。

### 待裁决事项

1. `_unclassified/screenshot-001.txt` 的归属：属于哪个项目/功能的截图？应归入 docs、assets 还是其他目录？
2. `logo-legacy.txt`（旧版品牌素材）是否需要长期保留？还是归档后删除？
3. `contract-draft.txt` 是草稿状态，是否有正式版本需要替换？

---

## 五、事实面状态

| 事实面 | 状态 | 说明 |
|---|---|---|
| 代码 | not-applicable | 本项目无代码，为纯文档/资产集合 |
| 运行态 | not-applicable | 无可运行服务 |
| 文档 | changed | 已分类、规范命名、去重候选已隔离 |
| 规则 | pending | 项目尚无 CLAUDE.md / AGENTS.md 规则文件；如需要可创建最小规则文件 |
| 记忆 | not-applicable | 无 Agent 记忆系统 |
| 工作区 | changed-and-verified | 残留文件已隔离，目录结构已规范 |

---

## 六、Skill 规则引用

本整理依据 `neat-freak` Skill 的以下规则执行：
- 轻量路径五步盘点法（盘点 → 对齐事实 → 补规则 → 清点残留 → 汇报）
- 目录纪律：根目录不放裸文件
- 会话残留识别：`xxx_old`、版本号冗余文件列入删除候选
- 去重原则：同一事实只保留一个权威版本
- 保守删除：未确认前不删除，仅隔离到候选区
- 无法裁决保留：归属不明的文件不做猜测性归类
