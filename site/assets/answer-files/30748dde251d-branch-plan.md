// 分支与集成计划
// 依据：parallel-feature-development SKILL.md「Branch Management」与 merge-strategies.md

## 策略选择：多分支策略（Sub-Branch Integration）

选择理由：3 个实现者 + 1 个 lead，存在跨切片依赖（登录/注册依赖共享鉴权层），
需要显式评审关卡，符合 merge-strategies.md Pattern 2「4+ 人、需要 review gate」的判定。

## 分支拓扑

feature/auth                        （集成分支，lead 拥有合并权）
  ├── feature/auth-contract         （lead：契约 + barrel 文件）
  ├── feature/auth-login            （implementer-1：登录垂直切片）
  ├── feature/auth-register         （implementer-2：注册垂直切片）
  └── feature/auth-infra            （implementer-3：共享鉴权基础设施）

## 合并顺序（按依赖图：基础 → 依赖方 → 集成）

1. feature/auth-contract → feature/auth        （契约先行，所有人据此开发）
2. feature/auth-infra     → feature/auth        （中间件/JWT 工具）
3. feature/auth-login     → feature/auth        （登录切片）
4. feature/auth-register  → feature/auth        （注册切片）
5. lead 在 feature/auth 执行集成验证清单（见 integration-checklist.md）

## 冲突预防

- 契约文件 src/types/auth-contract.ts 只在 feature/auth-contract 分支修改，
  合并到 feature/auth 后对其余实现者只读。
- barrel 文件 src/api/auth/index.ts 由 lead 唯一拥有，实现者不得在自己的分支修改；
  需要导出新模块时向 lead 发变更请求，由 lead 串行应用。
- 若契约必须变更：lead 在 feature/auth-contract 修改 → 广播通知所有实现者 →
  实现者 rebase 后再继续。依据 SKILL.md Troubleshooting 契约漂移条款。
