# accint-frames 受约束流程方案

> 本方案严格依据 `accint-frames/SKILL.md` 编写。该 Skill 的真实职责是：
> 通过 `acc frames`（只读 CLI）列出队列，并对每个 open/waiting 的 brain_frame
> 经 `acc_act(runtime="continue")` 提交 proposal_text 来排空 acc 的审议队列。
> Skill 自身只是两个 MCP 动词的路由层，不含业务逻辑。

## 一、与题目假设的冲突说明

题目中出现"音视频脚本、处理或生成流程"的表述，但 SKILL.md 全文未涉及任何
音视频/图片/媒体处理能力，其唯一动作是排空 acc 审议队列。按题目要求
"以该 Skill 的真实能力边界为准，不扩张职责；SKILL.md 与题目假设冲突时以文件规则为准"，
本方案不包含任何音视频生成或处理步骤，也不调用 Seedream 等生图工具——
因为该 Skill 的流程不需要它们。若确需音视频能力，应使用对应领域的 Skill，
而非本 Skill。

## 二、预检（Pre-checks）

| 编号 | 检查项 | 类型 | 失败处理 |
|------|--------|------|----------|
| P1 | `acc` CLI 在 PATH 中且可执行 | 只读 | 阻断，提示需人工确认后安装 |
| P2 | `acc_act` MCP 动词已注册可用 | 只读 | 阻断，提示需在 MCP 配置中启用 |
| P3 | acc 配置/认证目录存在且可读（如 `~/.acc`、`~/.config/acc`） | 只读 | 阻断，提示需人工配置认证 |
| P4 | `acc frames` 能成功列出队列（只读观察） | 只读 | 瞬时错误重试；认证错误上报人工 |
| P5 | 当前任务确实匹配 acc 上游来源与本地项目上下文（Limitations 第1条） | 人工判断 | 不匹配则不使用本 Skill |

预检全部通过前，不执行任何 submit 动作。

## 三、幂等设计（Idempotency）

- 依据 SKILL.md 第4条：相同的重复 submit 会重放缓存结果，重新提交是安全的。
- 本地维护 `drained_frames.tsv`（frame_id、submit_token、commitment_id、状态、时间戳），
  处理每个 frame 前先查是否已有成功 commitment，避免重复审议。
- 即使去重记录丢失，重放相同 payload 也只会返回缓存结果，不会产生重复副作用。
- 不删除、不覆盖队列中任何 frame；只读取并提交。

## 四、重试策略（Retry）

- `acc frames`（只读列表）：瞬时错误（网络超时、5xx）最多重试 3 次，
  指数退避（1s、2s、4s）；认证失败(401/403)、命令不存在不重试，直接上报。
- `acc_act` submit：因本身幂等，遇到超时或结果不确定时，用完全相同的
  `frame_id` + `submit_token` + `proposal_text` 重试，最多 2 次；
  返回明确业务错误（如 frame 已关闭）则不重试，记录并跳过。
- 所有重试写入日志，包含尝试次数、错误摘要。

## 五、人工确认点（Human Confirmation Gates）

| 编号 | 确认点 | 说明 |
|------|--------|------|
| H1 | 预检通过后、首次 submit 前 | 向人工展示队列全貌（frame 数量、各 frame 的 typed hole 摘要），确认后才继续 |
| H2 | 每个 frame 的 proposal_text 提交前 | 展示完整 proposal_text（含末尾 `PREDICT: <0.00-1.00> <why>` 行），人工审阅后提交 |
| H3 | 安装 acc CLI / 配置认证 / 启用 MCP 动词前 | 这些属于变更外部环境，须人工明确授权；本方案不静默安装 |
| H4 | 任何破坏性或高成本操作前 | 依据 Limitations 第3条及 risk: critical，须人工批准 |

## 六、标准执行流程

1. 运行预检脚本 `accint_frames_drain.sh --preflight`（只读）。
2. P5 人工确认任务匹配。
3. H1：展示 `acc frames` 输出的队列，人工确认开始排空。
4. 对每个 open/waiting frame：
   a. 读取 typed hole 与 retrieved context；
   b. 本地去重检查（幂等）；
   c. 审议并生成 proposal_text，末尾追加 `PREDICT: <置信度> <理由>`；
   d. H2：人工审阅 proposal_text；
   e. 调用 `acc_act(runtime="continue", input={frame_id, submit_token, proposal_text})`；
   f. 记录返回的 `commitment` id 与引用的 `[ids]` 到 `drained_frames.tsv`。
5. 队列排空后，汇总所有 commitment id 与 [ids]，输出报告。
6. 排空完成前不接新工作（SKILL.md 第5条）。

## 七、本次环境实际状态（2026-08-12 预检结果）

- P1：`acc` CLI 未找到（`which acc` 退出码 1）。
- P2：`acc_act` MCP 工具未注册（tool_search 无匹配）。
- P3：`~/.acc`、`~/.config/acc`、`~/.local/share/acc` 均不存在。
- P4：因 P1 失败，无法执行 `acc frames`，队列不可访问。
- 结论：流程在预检阶段安全停止，**未产生任何外部副作用**，
  未创建/删除/覆盖任何外部资源，未提交任何 frame。
- 需人工确认事项（H3）：是否安装 acc CLI、如何配置认证、如何启用 acc_act MCP 动词。
  在这些确认并完成前，无法进入实际排空阶段。
