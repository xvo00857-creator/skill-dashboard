# 原生数据获取（Expo Networking）受约束流程方案

> 依据 Skill：`native-data-fetching`（Expo 官方 networking skill，`risk: critical`）
> 适用范围：Expo / React Native 应用中的网络请求、数据获取、缓存、鉴权、离线与 Expo Router loader。
> 本方案在题目约束下编写：仅使用现有权限与已提供数据，不静默创建/删除/覆盖外部资源，加入预检、幂等、重试与人工确认点。

## 0. 能力边界（先于一切）

- 本 Skill 的真实职责是 **Expo/React Native 网络层**：`fetch` 封装、React Query/SWR、错误处理、重试、取消、鉴权 token、离线、`EXPO_PUBLIC_` 环境变量、Expo Router loader（web，SDK 55+）。
- "目录发现"不是网络请求本身，而是实施前的**只读预检**：确认是否存在项目、依赖与配置，不做任何写入。
- 题目未提供真实 Expo 项目、后端 API 或凭证；因此本方案**不声称**已在真实项目中接入，也不伪造接口返回。真实接入需在具备项目与环境后按本方案执行并补充环境测试。

## 1. 预检（Pre-checks，只读，先于任何请求）

| 预检项 | 检查内容 | 不通过时处理 | 依据 |
|---|---|---|---|
| 运行时能力 | 全局 `fetch` 是否存在（Node 18+ / RN 自带） | 阻断并提示升级运行时 | SKILL.md §1 |
| API 地址配置 | `EXPO_PUBLIC_API_URL` 是否已定义 | 直接抛错，不发请求 | SKILL.md §6：`if (!BASE_URL) throw new Error(...)` |
| 密钥放置 | 客户端只用 `EXPO_PUBLIC_` 变量；服务端密钥用无前缀变量（loader/API 路由内） | 阻断写入型密钥进客户端包 | SKILL.md §6 / loaders 参考：secrets 用非前缀变量 |
| 网络状态 | 先查连通性（`@react-native-community/netinfo`；web/Node 用轻量探测） | 离线时挂起查询，不盲目重试 | SKILL.md §5 |
| loader 前置条件 | 若用 Expo Router loader：确认 SDK 55+、web output 已配置、`unstable_useServerDataLoaders` 开启 | 不满足则回退到客户端 fetch/React Query | loaders 参考 Configuration 节 |
| 目标目录 | 确认要写入/修改的项目路径存在且为预期项目，避免覆盖无关工程 | 路径不符则停止并请人工确认 | 题目约束 + Limitations |

预检全部通过后才进入请求阶段；任一项不通过即停止，不"带病"发请求。

## 2. 请求与错误处理（必做基线）

- 使用全局 `fetch`（**避免 axios，优先 expo/fetch**——SKILL.md Preferences）。
- 每次响应必须检查 `response.ok`，非 2xx 解析响应体并抛出**类型化错误** `ApiError(message, status, code)`；网络层异常（断网、超时、DNS）统一归为 `code: 'NETWORK_ERROR'`；`AbortError` 单独保留为 `code: 'ABORT_ERR'`。
- 禁止裸写 `await fetch(url).then(r => r.json())`（SKILL.md Common Mistakes 明确列为反例）。

## 3. 重试（Retry）

- 采用 SKILL.md §3 的指数退避：第 i 次失败后等待 `2^i * 1000ms`，默认最多 3 次。
- **不重试**：4xx 业务错误（除 408/429）、`AbortError`（取消应立即生效）、人工确认未通过。
- React Query 场景按 SKILL.md §2 设 `retry: 2`、`staleTime: 5min`。
- 演示中为缩短耗时把退避基数调小为 30ms，生产值仍为 1000ms（已在脚本注释标注）。

## 4. 幂等与去重（Idempotency）

- GET/HEAD 等只读请求天然幂等：以 `method + path + query` 为 key 做 **in-flight 去重**，并发相同请求复用同一个 Promise（对应 React Query 的 dedup 能力）。
- 写操作（POST/PUT/PATCH/DELETE）不做静默去重；需要幂等性时由调用方提供幂等键并经人工确认（见第 5 节）。
- 组件卸载或查询失效时用 `AbortController` 取消在途请求，避免"已离开页面仍写状态"。

## 5. 人工确认点（Human-in-the-loop）

以下操作在执行前必须取得明确人工确认，不得自动执行：

1. 任何写/变更类请求（POST/PUT/PATCH/DELETE）作用于真实数据时；
2. 修改 `.env` / `.env.production` 或切换 API base URL 时；
3. 安装依赖、升级 Expo SDK、修改 `app.json` 插件配置时；
4. 部署、发布、或可能产生费用/配额影响的操作（依据 SKILL.md Limitations："user approval for destructive or costly actions"）。

未确认时直接抛 `CONFIRMATION_REQUIRED`，不发请求。

## 6. 离线与取消

- 用 NetInfo 监听连通性并同步给 React Query `onlineManager`；离线时查询挂起、恢复后自动继续。
- 每个可取消请求持有 `AbortController`，在 effect cleanup 中 `abort()`。

## 7. 演示与可核验性

- 演示脚本：`native-fetch-demo.mjs`，仅用 Node 内置模块（`node:http` + 全局 `fetch`），在 `127.0.0.1` 回环地址起本地 mock 服务，**不访问任何外部网络**。
- 覆盖场景：预检拦截、正常 GET、404 类型化错误、500 指数退避重试后成功、并发 GET in-flight 去重、AbortController 取消、写操作人工确认拦截/放行。
- 每个场景打印 `通过/失败`，脚本退出码反映结果，可重复运行（幂等：每次起新端口、进程结束即清理，不写磁盘、不改外部资源）。

## 8. 仍需确认的假设与不可访问项

- **假设**：生产目标为 Expo SDK 55+ 项目；若 SDK 低于 55，loader 不可用，native 端一律用 React Query/fetch（loaders 参考明确"Loaders are web-only"）。
- **不可访问**：题目未提供真实后端、凭证、Expo 项目与 Expo CLI；本方案不联网安装 Expo、不调用任何真实 API，相关集成结果待真实环境补齐后验证。
- 本方案中的代码片段以 SKILL.md 示例为准；命令、API 行为、配额与部署影响在真实改动前需对照最新官方文档复核（SKILL.md Limitations）。
