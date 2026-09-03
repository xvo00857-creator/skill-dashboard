# 团队周报自动汇总（feishu-tools Skill 配套）

## 一、自动化场景

将团队每周重复的**周报汇总**工作自动化：

1. 从飞书多维表格读取本周任务记录
2. 按负责人、状态（已完成/进行中/阻塞/待开始）汇总
3. 生成 Markdown 周报
4. 通过 feishu-tools MCP 创建飞书文档并发送群通知

## 二、约束导致的方案变化

| 约束 | 对方案的影响 |
|------|-------------|
| 不新增非必要依赖 | 仅使用 Python 3.7+ 标准库（json/subprocess/argparse/logging/datetime/unittest），MCP 通信用标准库实现 JSON-RPC 2.0 over stdio，不引入 mcp-sdk 等第三方包 |
| 不改变无关文件 | 所有文件放在本目录 `feishu-weekly-report/` 下，不修改项目其他文件 |
| 本地可重复验证 | 提供 `--mode mock`（读本地 JSON 出 Markdown）和 `mock_mcp_server.py`（模拟 MCP server），无需飞书账号即可完整验证 |
| 外部账号只做模拟/确认前步骤 | `--mode live` 默认 dry-run，只打印将调用的工具和参数；必须显式加 `--execute` 才会实际写入 |
| 不得编造工具名（SKILL.md 规则） | live 模式启动后先调 MCP `tools/list` 获取当前暴露的工具，再按 Routing Hints 关键词匹配，不硬编码任何工具名 |

## 三、文件结构

```
feishu-weekly-report/
├── weekly_report.py        # 主脚本（mock + live 双模式）
├── mock_mcp_server.py      # 本地 MCP server 模拟器（验证用）
├── config.example.json     # 配置模板
├── config.json             # 当前配置（mock 数据路径）
├── config.mock_mcp.json    # 用 mock MCP server 的 live 模式配置
├── config.mock_partial.json# 模拟工具缺失场景的配置
├── mock_data/
│   └── tasks.json          # 模拟任务输入
├── examples/
│   ├── input_example.json  # 输入示例
│   └── output_example.md   # 输出示例
├── test_weekly_report.py   # 单元测试（18 项）
└── README.md
```

## 四、使用方法

### 4.1 本地模拟（无需飞书账号）

```bash
cd feishu-weekly-report
python3 weekly_report.py --mode mock --config config.json --output weekly_report.md
```

读取 `mock_data/tasks.json`，输出 `weekly_report.md`。

### 4.2 live 模式 dry-run（确认前步骤）

```bash
# 1. 复制配置模板并填入真实值
cp config.example.json config.json
# 编辑 config.json，填入 mcp.server_command 和飞书参数

# 2. dry-run：只打印将执行的工具调用，不写入
python3 weekly_report.py --mode live --config config.json
```

### 4.3 live 模式实际执行（需飞书插件已配置）

```bash
python3 weekly_report.py --mode live --config config.json --execute
```

### 4.4 用 mock MCP server 验证 live 全流程

```bash
python3 weekly_report.py --mode live --config config.mock_mcp.json          # dry-run
python3 weekly_report.py --mode live --config config.mock_mcp.json --execute # 实际调用 mock
```

## 五、可重复验证命令

```bash
# 1. 单元测试（18 项，覆盖状态归一化/校验/筛选/汇总/渲染/工具匹配/CLI 退出码）
python3 test_weekly_report.py

# 2. mock 模式端到端
python3 weekly_report.py --mode mock --config config.json --output /tmp/test_report.md
echo "退出码: $?"   # 应为 0
test -f /tmp/test_report.md && echo "输出文件存在"

# 3. live dry-run（mock MCP server）
python3 weekly_report.py --mode live --config config.mock_mcp.json
echo "退出码: $?"   # 应为 0

# 4. live 工具缺失场景
python3 weekly_report.py --mode live --config config.mock_partial.json
echo "退出码: $?"   # 应为 5（MCPToolNotFoundError）

# 5. 异常路径：配置文件不存在
python3 weekly_report.py --mode mock --config /nonexistent.json
echo "退出码: $?"   # 应为 2（ConfigError）
```

## 六、异常处理与退出码

| 退出码 | 异常类型 | 触发场景 |
|--------|---------|---------|
| 0 | 成功 | 正常完成 |
| 1 | WeeklyReportError | 其他业务错误 |
| 2 | ConfigError | 配置文件不存在、JSON 格式错误、缺少 mcp.server_command |
| 3 | DataValidationError | 任务数据不是列表、缺少 title/owner、记录非对象 |
| 4 | MCPAuthError | 飞书认证失败（按 SKILL.md 规则 7 提示检查 App ID/Secret/brand/preset） |
| 5 | MCPToolNotFoundError | 当前飞书预设缺少所需工具（按 SKILL.md 规则 6 说明差距） |
| 6 | MCPConnectionError | MCP server 启动失败、进程退出、通信超时 |
| 99 | 未预期异常 | 兜底捕获并记录堆栈 |
| 130 | KeyboardInterrupt | 用户中断 |

## 七、与 feishu-tools SKILL.md 的对应关系

- **规则 1（MCP 工具为主要操作面）**：live 模式通过 MCP 协议调用，不绕过插件
- **规则 2（以实际暴露工具为准）**：启动后调 `tools/list` 动态获取，不假设工具名
- **规则 4（从 URL 提取标识）**：配置中直接使用 app_token/table_id 等标识
- **规则 5（写操作确认）**：默认 dry-run，`--execute` 才实际写入
- **规则 6（无匹配工具时说明差距）**：工具缺失时退出码 5 并提示检查 preset
- **规则 7（认证错误指引）**：识别 auth/401/403 等错误，提示检查 App ID/Secret/brand/preset
- **Routing Hints**：`find_tool()` 按 doc/sheet/im 关键词在运行时匹配
- **Important Constraint**：不编造工具名，工具可用性以运行时 `tools/list` 为准

## 八、缺失项与已完成范围

### 已完成

- 可执行脚本 `weekly_report.py`（mock + live 双模式）
- 输入输出示例（`examples/`）
- 异常处理（8 种退出码，覆盖配置/数据/连接/认证/工具缺失）
- 本地验证记录（18 项单元测试 + 5 个端到端验证命令全部通过）
- mock MCP server 用于无账号环境验证

### 缺失项（当前环境限制）

1. **feishu-tools MCP 工具未在当前会话暴露**：`tool_search` 未找到任何 feishu-tools MCP 工具，SKILL.md 中的 Plugin id（`${OWNER_PLUGIN_ID}`）和 Plugin root（`${PLUGIN_ROOT}`）均为占位符，无法确定真实 MCP server 启动命令。因此 live 模式的真实飞书调用未在本环境执行，仅通过 mock MCP server 验证了调用逻辑。
2. **真实飞书账号/凭证未提供**：未执行真实的文档创建和群消息发送，符合"只做到安全的模拟或确认前步骤"的约束。
3. **MCP server 启动命令为示例值**：`config.example.json` 中的 `server_command` 需根据实际飞书插件配置填写。
