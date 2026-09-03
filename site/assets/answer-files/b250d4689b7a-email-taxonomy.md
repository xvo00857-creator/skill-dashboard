# Email Taxonomy

> 本文件为收件箱分类体系。分类数控制在 5 类以内（原方案 5–7 类压缩），便于接手同事快速记忆与维护。
> 维护人：原负责人 → 接手同事（交接日起）

## Categories

### 1. 需立即行动 (Action Required)
- Signals: 含"请确认/请审批/请回复/截止/deadline/ASAP/紧急"等触发词；来自直接上级、核心项目相关人；主题含"评审/排期/上线/故障"
- Default action: classify + draft-reply（优先处理，24h 内回复）
- Typical volume: ~25% of inbox
- 交接备注: 周三评审会相关邮件归入此类，评审前 24h 内必须清零

### 2. 活跃对话 (Active Conversations)
- Signals: 正在进行的线程（Re:/Fwd: 多次往返）；项目讨论、方案对齐、跨团队协作
- Default action: classify（按需回复，不强制每封都回，跟进关键节点）
- Typical volume: ~30% of inbox
- 交接备注: 接手同事只需关注被 @ 或直接提问的邮件，其余可标记已读

### 3. 信息周知 (Informational)
- Signals: 含"FYI/周知/周报/月报/通知/公告/Recorded/分享"；群发邮件、非直接收件人（CC）
- Default action: skip（快速浏览标题，有需要再点开，不回复）
- Typical volume: ~30% of inbox
- 交接备注: 此类邮件不处理不影响交付，时间紧张时直接全部标记已读

### 4. 个人/重要 (Important/Personal)
- Signals: 来自 HR、行政、IT、财务；含"合同/薪资/报销/权限/账号/密码"；1:1 直接发送且非项目类
- Default action: flag-for-review（人工确认，不可自动跳过）
- Typical volume: ~10% of inbox
- 交接备注: 涉及个人隐私或权限的邮件不自动处理，转交原负责人或按公司流程操作

### 5. 低优先级/忽略 (Ignore/Low Priority)
- Signals: 含"unsubscribe/退订/营销/推广/活动邀请/调查问卷"；newsletter、digest
- Default action: skip（自动归档，不进收件箱视图）
- Typical volume: ~5% of inbox
- 交接备注: 由 blocklist.md 自动拦截，无需人工介入

## Report Preferences

- Delivery format: file-in-workspace（写入 Email/triage-log/ 目录，便于接手同事查阅历史）
- Detail level: 30-second-scan（时间减半，只看摘要；需要时展开）
- Always-shown-first: overdue items（tracker.md 中的逾期项）；周三评审会相关待办；直接上级邮件
