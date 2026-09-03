# 本地测试站点浏览器验收流程（browser-cdp Skill）

本目录是一个**最小可用、默认只读预演**的浏览器验收框架，覆盖登录、表单校验、错误状态和截图证据。
基于随消息提供的 `browser-cdp` Skill 构建，严格遵循其启动流程与安全约束。

---

## 一、风险与事实核查（执行前必读）

### 1.1 已核实事实（来自实际探测，非推断）

| 项 | 实际结果 | 来源 |
|----|----------|------|
| 操作系统 | macOS（darwin） | 环境探测 |
| Node 版本 | v20.19.2（满足 Skill 要求的 20+） | `node --version` |
| Google Chrome | 已安装，版本 147.0.7727.56 | `/Applications/Google Chrome.app` |
| `agent-browser` | **未安装**（Skill 必需依赖缺失） | `which agent-browser` |
| CDP 端口 9222 | 已就绪，但应答者是 **HeadlessChrome**（无界面、无打开页面、无登录态） | `curl /json/version`、`/json/list` |
| 用户常规 Chrome | 检测到 **19 个进程**在运行 | `setup-cdp-chrome.js --dry-run` |
| 被测站点地址 | **未提供** | 用户输入中无 URL |
| 测试账号/密码 | **未提供** | 用户输入中无凭据 |
| 页面选择器/表单结构 | **未提供** | 用户输入中无 DOM 信息 |

### 1.2 未核实前提（用户输入中隐含但未确认）

- "有一个本地测试站点"——未给出地址、端口、技术栈，无法确认其存在或可达。
- "需要登录"——未给出登录入口、字段名、测试账号。
- "有表单校验和错误状态"——未给出具体表单、校验规则、预期错误文案。
- 9222 端口上的 HeadlessChrome 归属不明：可能是其他任务遗留，也可能是某个服务在用。
  本流程**不会**关闭它（Skill 规定 `CDP_STATUS=ready` 时直接复用，不运行 setup）。

### 1.3 识别到的风险点

1. **不可逆操作 A：kill 用户常规 Chrome。**
   Skill 的启动脚本在需要重建调试环境时会执行 `pkill -9 -x 'Google Chrome'`，
   当前有 19 个 Chrome 进程，可能导致未保存的标签页、草稿、表单输入丢失。
   Skill 明确要求：非 TTY 环境下检测到 Chrome 在跑而未传 `--yes` 会以退出码 3 中止；
   **必须先征得用户同意**才能带 `--yes`。本验收脚本不会自动执行该操作。

2. **不可逆操作 B：`--reset` 删除调试 profile。**
   `setup-cdp-chrome.js --reset` 会递归删除 `~/chrome-debug-profile`。
   该操作需 `--yes`，且仅在登录态失效时使用。本流程默认不触发。

3. **敏感信息泄露风险：提取 token/cookie。**
   Skill 文档演示了 `localStorage.getItem("token") || document.cookie`。
   本验收流程**不执行任何 token/cookie 提取**，仅对页面可见元素做断言，
   且增加了"错误页不泄露 password/token/secret/堆栈"的检查。

4. **生产环境误伤风险。**
   用户未提供授权范围。脚本默认指向 `127.0.0.1`，且所有凭据由本地 `.env.acceptance` 注入，
   不内置任何真实账号；但在你填写配置前，仍需确认目标确实是本地测试站点而非生产环境。

5. **依赖缺失。**
   `agent-browser` 未安装，`--run` 模式无法执行。安装属于系统级变更（`npm install -g`），
   需你确认后自行执行。

### 1.4 事实 / 推断 / 待确认 区分

- **事实**：上表 1.1 中所有项，均有命令输出为证。
- **推断**：9222 上的 HeadlessChrome 可能是其他任务遗留（无直接证据，仅因无页面且为 headless）。
- **待你确认**：被测站点 URL、测试账号、页面选择器、是否允许安装 agent-browser、
  是否允许在必要时重启 Chrome（会关闭现有 19 个进程）。

---

## 二、交付物清单

| 文件 | 说明 |
|------|------|
| `acceptance-test.sh` | 主验收脚本，默认 dry-run，`--run` 才操作浏览器 |
| `cdp-screenshot.js` | CDP 截图助手（Node 20 内置 WebSocket，无第三方依赖） |
| `.env.acceptance.example` | 配置模板，复制为 `.env.acceptance` 后填写 |
| `README.md` | 本文件（风险分析、授权、停止条件、回滚、排查） |
| `screenshots/<run_id>/` | 每次 `--run` 的截图证据目录（dry-run 不产生图片） |
| `run-<run_id>.log` | 每次运行的完整日志 |

### 已实际执行的只读预演记录

- `node setup-cdp-chrome.js 9222 --detect-only` → `CDP_STATUS=ready`（退出码 0）
- `node setup-cdp-chrome.js 9222 --dry-run` → 预演成功，显示若重建将 kill 19 个 Chrome 进程
- `curl http://127.0.0.1:9222/json/version` → HeadlessChrome/147.0.7727.56
- `curl http://127.0.0.1:9222/json/list` → 空数组（无打开页面）
- `./acceptance-test.sh`（dry-run）→ 12 项断言全部预演通过，未操作浏览器
- `node cdp-screenshot.js`（无页面时）→ 友好报错退出码 2

**未执行的操作**：未安装 agent-browser、未 kill 任何 Chrome 进程、未打开任何页面、
未输入任何凭据、未读取任何 token/cookie、未删除任何文件。

---

## 三、用例与截图清单

| 序号 | 用例 | 截图文件 | 断言要点 |
|------|------|----------|----------|
| 01 | 打开登录页 | `01-login-page.png` | 提交按钮存在 |
| 02 | 登录空提交 | `02-login-empty-submit.png` | 出现必填错误提示 |
| 03 | 错误凭据登录 | `03-login-bad-cred.png` | 出现登录失败提示 |
| 04 | 正确凭据登录 | `04-login-success.png` | URL 离开登录页或出现成功标识 |
| 05 | 登录后状态 | `05-after-login.png` | 页面可见元素正常 |
| 06 | 打开表单页 | `06-form-page.png` | 表单已加载 |
| 07 | 表单空提交 | `07-form-empty.png` | 必填校验提示 |
| 08 | 非法邮箱 | `08-form-bad-email.png` | 格式校验提示 |
| 09 | 合法提交 | `09-form-success.png` | 成功提示 |
| 10 | 404 错误页 | `10-error-404.png` | 错误页可见且不泄露敏感信息 |

失败时额外生成 `FAIL-*.png` 截图。

---

## 四、使用方法

### 4.1 安装依赖（需你确认后执行）

```bash
npm install -g agent-browser
```

> 这是系统级安装。Skill 前置条件要求 Node 20+（已满足）。

### 4.2 填写配置

```bash
cd acceptance
cp .env.acceptance.example .env.acceptance
# 编辑 .env.acceptance，填入测试站点地址、测试账号、真实选择器
```

`.env.acceptance` 含凭据，**不要提交到版本库**（建议加入 `.gitignore`）。

### 4.3 预演（不操作浏览器，推荐先跑）

```bash
./acceptance-test.sh
```

### 4.4 正式执行

```bash
./acceptance-test.sh --run            # 全部用例
./acceptance-test.sh --run --case login   # 只跑登录
./acceptance-test.sh --run --case form    # 只跑表单
./acceptance-test.sh --run --case error   # 只跑错误状态
```

### 4.5 启动调试 Chrome（仅当 CDP 未就绪时）

脚本前置检查会告诉你 CDP 状态：
- 若 `CDP_STATUS=ready`：直接用，不要启动。
- 若 `needs-setup` 且无 Chrome 运行：`node ../browser-cdp-extracted/browser-cdp/scripts/setup-cdp-chrome.js 9222`
- 若 `needs-setup` 且有 Chrome 运行：**先保存工作**，确认可关闭后：
  `node ../browser-cdp-extracted/browser-cdp/scripts/setup-cdp-chrome.js 9222 --yes`

---

## 五、授权清单（执行 `--run` 前请逐项确认）

- [ ] 目标地址确认为**本地测试站点**（127.0.0.1 / localhost），非生产环境
- [ ] 使用的是**专用测试账号**，非个人或生产账号
- [ ] 已阅读 `.env.acceptance` 中的选择器，与被测站点实际 DOM 一致
- [ ] 已知晓：若 CDP 未就绪且 Chrome 在运行，启动调试 Chrome 会**关闭所有常规 Chrome 窗口**
- [ ] 已保存常规 Chrome 中未保存的工作（标签页、草稿、表单）
- [ ] 同意安装 `agent-browser`（若尚未安装）
- [ ] 同意脚本在测试站点上执行登录、表单提交等操作（会产生测试数据）
- [ ] 已知晓脚本**不会**读取 token/cookie，也**不会**执行 `--reset`

---

## 六、停止条件

脚本在以下情况**自动停止**：

1. 前置检查发现 CDP 未就绪且需要 kill Chrome 时——停止，等待你手动启动。
2. `--run` 模式下缺少 `agent-browser` 或必填配置——停止。
3. 任一断言失败——立即停止（设置 `CONTINUE_ON_FAIL=1` 可继续跑完）。
4. 单条 CDP 命令超过 30 秒——`timeout` 终止该命令。
5. 截图失败——记录警告但不中断（证据缺失不阻塞用例）。

你可以随时按 `Ctrl+C` 手动停止。

---

## 七、回滚方案

| 场景 | 回滚动作 |
|------|----------|
| 验收过程中浏览器状态异常 | 关闭调试 Chrome 窗口即可；它使用独立的 `~/chrome-debug-profile`，不影响你的常规 Chrome |
| 调试 Chrome 无响应 | 按 Skill 规定：`pgrep -af chrome-debug-profile` 找到调试实例 PID，`kill -9 <PID>`；**禁止**按 Chrome 可执行名批量杀进程 |
| 登录态被污染 | `node setup-cdp-chrome.js 9222 --reset --yes`（会删除 `~/chrome-debug-profile` 并重新复制；需先确认关闭 Chrome） |
| 测试产生了脏数据 | 使用测试账号在站点内手动清理，或重置测试数据库（站点侧操作，本脚本不涉及） |
| 想恢复到执行前状态 | 本脚本不修改系统配置、不写浏览器 profile、不安装东西（除你主动 `npm install -g`）；删除 `acceptance/` 目录即可完全移除 |

---

## 八、人工复核点

以下节点建议人工介入确认，不要全自动放行：

1. **首次 `--run` 前**：人工打开被测站点，确认选择器和登录流程与脚本假设一致。
2. **登录成功后（05 截图）**：人工查看截图，确认确实进入了登录后页面而非停留在错误页。
3. **表单合法提交（09 截图）**：确认提交没有产生非预期的真实数据（如发邮件、下单）。
4. **错误页检查（10 截图）**：人工目检是否有堆栈、SQL、内部 IP 等敏感信息泄露。
5. **全部跑完后**：查看 `run-<id>.log` 和截图目录，确认无异常请求或跳转。

---

## 九、失败排查指南

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `未找到 agent-browser` | 依赖未装 | `npm install -g agent-browser` |
| `CDP 未就绪且检测到 N 个 Chrome 进程` | 调试 Chrome 未启动且常规 Chrome 在跑 | 保存工作后手动执行带 `--yes` 的 setup 命令 |
| `NEEDS_CONSENT` 退出码 3 | 非 TTY 下 setup 检测到 Chrome 在跑且未传 `--yes` | 这是 Skill 的安全闸门；先问用户再带 `--yes`，不要盲目加参数 |
| `CDP 端口仍被占用` | 端口被其他进程占着 | 脚本会打印占用者；结束占用进程或换端口（如 `9223`） |
| `没有打开的页面标签`（截图） | 未先 `open` 页面或页面已关闭 | 确认 `agent-browser open` 成功；用 `curl /json/list` 查看 |
| 断言一直失败 | 选择器与站点实际 DOM 不符 | 用 `agent-browser snapshot -i` 查看交互元素引用，更新 `.env.acceptance` |
| `eval 返回 null` | JS 选择器写错或 localStorage key 不对 | 复杂 JS 用 `eval -b <base64>` 或 `eval --stdin`（见 Skill 文档） |
| CDP 命令挂起 | 页面加载慢或网络挂起 | 脚本已包 30s `timeout`；重试一次；持续挂起则检查站点可达性 |
| 登录后仍在登录页 | 测试账号错误或验证码/二次验证 | 确认账号有效；若有验证码，本脚本不处理，需人工介入 |
| Chrome 启动 30s 超时 | profile 损坏或端口冲突 | 试 `--reset`；检查端口；查看 `~/chrome-debug-profile/` |
| 截图全黑/空白 | headless 模式下页面未渲染完 | 增大 `wait` 时间；确认页面不是纯前端路由需要额外等待 |

---

## 十、实际读取的 Skill 文件与影响本次结果的规则

### 读取的文件（ZIP 内相对路径）

1. `browser-cdp/SKILL.md`（完整读取，175 行）
2. `browser-cdp/scripts/setup-cdp-chrome.js`（完整读取，1002 行）

### 直接影响本次交付的具体规则

| 规则（出处） | 对本次结果的影响 |
|--------------|------------------|
| SKILL.md「启动流程」第一步必须 `--detect-only` 无副作用探测 | 我先执行了 detect-only，确认 `CDP_STATUS=ready`，因此**未运行 setup、未 kill Chrome** |
| SKILL.md：`CDP_STATUS=ready` 时直接复用，不要运行 setup | 脚本前置检查严格按此分支处理，不重复启动 |
| SKILL.md：Chrome 在跑时必须先用 AskUserQuestion 征得同意才能 `--yes` | 脚本检测到该情况时**停止并提示**，把决定权交给你，不自动传 `--yes` |
| SKILL.md：非 TTY 下缺 `--yes` 会退出码 3 `NEEDS_CONSENT`，"不应看到 3 就盲传 --yes" | 脚本和排查指南都把退出码 3 当作需人工确认的信号，不自动绕过 |
| SKILL.md「停止/清理」：手工清理不得按可执行名批量 kill，只杀 `chrome-debug-profile` 对应 PID | 回滚方案中明确写了 `pgrep -af chrome-debug-profile` 定位后只杀调试实例 |
| setup-cdp-chrome.js 的多重安全闸门（端口释放验证、实例身份比对、端口归属进程树验证） | 我信任这些闸门但不触发它们；dry-run 已展示其步骤，`--run` 时由脚本保证 |
| SKILL.md 前置条件：需 `agent-browser`、Node 20+、Chrome | 已核实 Node 和 Chrome 满足；`agent-browser` 缺失，如实标注为阻塞项 |
| SKILL.md 演示了 token 提取命令 | 我识别其为敏感能力，验收脚本**刻意不使用**，并增加错误页敏感信息检查 |
| SKILL.md 未提供截图命令 | 我自行编写了 `cdp-screenshot.js`，仅用 CDP `Page.captureScreenshot`，不引入额外依赖 |
| SKILL.md OpenCode 超时注意事项（30s 超时包装） | 脚本每条 CDP 命令都包了 `timeout 30` |

### 能力匹配说明

- Skill 的真实能力是：**通过 CDP 控制 Chrome、复用登录态、打开页面、执行 JS、快照、点击、输入、提取 token**。
- 它**不是**一个完整的测试框架——没有断言、没有测试用例组织、没有截图。
  我在其之上用 shell 封装了断言/用例/截图/日志，补齐了验收流程所需的最小能力。
- 截图能力 SKILL.md 未记录，我用 Node 20 内置 WebSocket 直连 CDP 实现，已在无页面场景下验证报错路径。
- 由于 `agent-browser` 未安装且无被测站点，`--run` 模式的真实浏览器操作**尚未执行**；
  当前交付的是可运行的脚本 + 已通过的 dry-run 预演，待你补齐配置和依赖后即可执行。
