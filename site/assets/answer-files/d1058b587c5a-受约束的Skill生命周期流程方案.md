# skill-lifecycle 受约束生命周期流程方案

> 依据随附 `skill-lifecycle/SKILL.md` 制定。本方案不臆造该 Skill 未声明的能力。

## 一、能力边界声明（与题目假设的差异）

题目要求"完成 Skill 的创建、安装、评估或生命周期管理"。经读取 SKILL.md，该 Skill 的真实定位是：

- **权威状态模型参考**：定义 Skill 容器状态、版本状态、审核任务状态、可见性模型、`latestVersionId` 指针规则、合法状态迁移、权限边界、领域事件与常见陷阱。
- **用途**：约束代理在修改发布/审核/下架流程、状态字段、搜索/详情/列表页、治理动作时，不引入非法状态或迁移。
- **它不是**：可执行的安装器、发布 CLI、评估器，也不提供任何外部 API、平台凭据或真实资源操作入口。

因此本次交付的"生命周期管理"是：**以 SKILL.md 为唯一事实来源的受约束流程方案 + 本地可核验的状态机演示**。未获得平台地址、凭据与明确授权前，不静默创建、安装、发布、删除任何真实 Skill 或外部资源。

## 二、受约束的生命周期流程

所有动作统一经过"预检 → 幂等判定 → 权限校验 → 人工确认（如适用）→ 执行 → 后置处理"六步。

### 1. 预检（preflight）

| 动作 | 预检条件（源自 SKILL.md） |
|------|---------------------------|
| 首次上传/发布 | 容器为 `ACTIVE`（`ARCHIVED` 不可发新版本）；角色为命名空间成员或 `SUPER_ADMIN`；发布警告已通过 `confirmWarnings` 两步确认 |
| 审核通过/驳回 | 版本处于 `PENDING_REVIEW` |
| 撤回审核 | 版本处于 `PENDING_REVIEW`；请求人为提交者本人 |
| Yank | 版本处于 `PUBLISHED`；请求人为平台治理角色 |
| Hide/Restore | 请求人为平台治理角色；操作 `skill.hidden` 布尔字段，**禁止**写 `SkillStatus.HIDDEN` 枚举 |
| Archive/Unarchive | 容器分别为 `ACTIVE`/`ARCHIVED`；请求人为 Owner 或命名空间管理员 |
| 删除版本 | 版本状态 ∈ {`DRAFT`,`REJECTED`,`SCAN_FAILED`,`UPLOADED`}；不是最后一个版本；请求人为 Owner 或命名空间管理员 |
| 可见性分流 | `PUBLIC`/`NAMESPACE_ONLY` → `PENDING_REVIEW` + 审核任务 + 安全扫描；`PRIVATE` → `UPLOADED`，不建审核任务；`SUPER_ADMIN` → 直接 `PUBLISHED` |

### 2. 幂等（idempotency）

- 执行前先比对目标状态：若版本已处于目标状态（如重复 approve、重复 yank、重复 archive），直接返回成功并标记 `idempotent=true`，不重复产生副作用、不重复发领域事件。
- 新发布时若已存在 `PENDING_REVIEW` 版本，按 SKILL.md 自动撤回旧待审版本并删除其待办审核任务，再进入新流程，避免重复审核任务。

### 3. 重试（retry）

- 仅对 SKILL.md 明确的"事务提交后存储删除"环节做有限次重试（演示默认 2 次）。
- 重试全部失败时**不静默吞错**，写入补偿记录（待人工/定时任务清理存储键与扫描记录），与 SKILL.md "compensation recording" 一致。
- 状态迁移本身不做盲目重试：非法状态/权限/确认缺失属于确定性失败，直接拒绝，不重试。

### 4. 人工确认点（human-in-the-loop）

以下治理/破坏性动作必须携带显式确认令牌 `confirmed=true`，否则预检阶段即拒绝：

- `yank_version`、`hide_skill`、`unhide_skill`、`archive_skill`、`delete_version`。
- 此外发布流程的 `confirmWarnings` 警告确认作为第二道人工确认点。
- 真实接入时，确认令牌应来自交互界面的显式点击/审批，而非程序默认填充。

### 5. 后置一致性

- 审核通过、Yank、删除指针版本后，必须按 SKILL.md 规则重算 `latestVersionId`：仅指向 `PUBLISHED` 版本；排序按 `publishedAt DESC, createdAt DESC, id DESC`；无已发布版本时为 `null`。
- 按迁移发出对应领域事件（`SkillPublishedEvent`、`ReviewSubmittedEvent`、`SkillVersionYankedEvent`、`SkillStatusChangedEvent`），演示中仅记录不外发。

## 三、不可访问资源与待确认假设

1. **平台/API 不可访问**：未提供 Skill 平台地址、凭据与命名空间，因此无法真实创建、安装、发布或评估任何 Skill；本次不尝试连接。
2. **SKILL.md 内部一处不一致 [需确认]**：迁移表称 `PRIVATE` 首次上传会"更新 `latestVersionId`"，但指针规则明确"`latestVersionId` 只能指向 `PUBLISHED` 版本"。本方案保守遵循指针规则：`PRIVATE` → `UPLOADED` 时 `latestVersionId` 保持 `null`。此处理需与代码/设计文档确认。
3. **Hide/Restore、Yank 权限**：SKILL.md 注明代码中"无权限检查"，本方案在流程层主动加平台治理角色校验 + 人工确认，属增强约束，落地前需与治理方确认。
4. **存储与扫描后端**：演示中以内存对象模拟；真实存储键删除、安全扫描记录清理需对接实际后端，重试与补偿策略参数需按后端 SLA 调整。
5. **`confirmWarnings` 的具体警告项**：SKILL.md 只声明两步流程，未列举警告内容；演示以"存在发布警告"占位，真实警告清单需由发布服务提供。

## 四、可核验演示结果

演示脚本：`lifecycle_guard.py`（纯本地、无网络、无外部写入）。运行方式：

```bash
python3 lifecycle_guard.py
```

本次实际运行退出码 `0`，7 个场景全部通过，关键可核验点：

1. 未确认 `confirmWarnings` 的发布被预检拒绝；确认后 `PUBLIC` 上传进入 `PENDING_REVIEW` 并创建审核任务与扫描记录；审核通过后 `latestVersionId` 指向该版本。
2. 重复 `approve` 幂等返回；`DRAFT` 直接审核通过被拒绝；普通成员 Yank 被拒绝；Yank 缺少人工确认令牌被拒绝。
3. 新版本发布自动撤回旧 `PENDING_REVIEW`；Yank 当前最新版本后，`latestVersionId` 按规则回退到次新 `PUBLISHED` 版本（v3 → v1）。
4. `PRIVATE` 上传进入 `UPLOADED` 且不创建审核任务；Hide 只置 `hidden=true`，容器状态仍为 `ACTIVE`（未使用 `HIDDEN` 枚举）。
5. 删除 `PUBLISHED` 版本被拒绝；删除最后一个版本被拒绝；删除 `REJECTED` 版本成功并清理存储键与扫描记录。
6. 存储删除持续失败时，按重试次数重试，耗尽后写入补偿记录（演示输出："版本 vf 存储删除在 1 次重试后仍失败……待人工/定时任务补偿清理"）。
7. `ARCHIVED` 容器发布新版本被拒绝；Unarchive 后恢复。

## 五、实际读取的 Skill 文件（相对路径）

- `skill-lifecycle/SKILL.md`（ZIP 内唯一文件，已完整读取）

## 六、实际影响交付结果的 SKILL.md 规则（至少一条）

**规则：`HIDDEN` 不应作为容器生命周期枚举状态，新代码应使用 `skill.hidden` 布尔覆盖层。**

该规则直接改变了本方案的数据模型与演示：
- 状态机中容器状态只保留 `ACTIVE`/`ARCHIVED`，另设独立的 `hidden: bool` 字段；
- Hide/Restore 动作只切换布尔值，不触发 `SkillStatusChangedEvent`，也不改变版本发布能力；
- 演示场景四专门验证"Hide 后容器仍为 `ACTIVE`"。

若忽略该规则而沿用 `SkillStatus.HIDDEN`，将与设计文档冲突并导致列表/详情页投影、权限判断与归档逻辑出错。

其他同样落地的规则：`latestVersionId` 仅指向 `PUBLISHED` 且 Yank/删除后重算；`PRIVATE` 跳过审核任务；删除版本仅限四种非发布状态且保护最后版本；治理动作纳入人工确认。
