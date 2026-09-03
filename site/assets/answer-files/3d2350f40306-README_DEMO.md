# 操作说明 — weekly_todo_summary 自动化流程

## 文件清单
| 文件 | 用途 |
|------|------|
| weekly_todo_summary.py | 主脚本 |
| todos.json | 待办数据（模拟） |
| summary_output.md | 生成的摘要（执行后产生） |
| PERMISSIONS.md | 权限清单 |
| ROLLBACK.md | 回滚方案 |
| README_DEMO.md | 本说明 |

## 快速开始

### 1. 预览（dry-run，不做任何变更）
```bash
python3 weekly_todo_summary.py --dry-run
```
输出摘要预览到终端，不写入文件。借鉴 release-skills 的 --dry-run 选项。

### 2. 执行（含人工确认）
```bash
python3 weekly_todo_summary.py
```
脚本会：
1. 加载 todos.json
2. 筛选逾期项（due < 今天 且 status != done）
3. 生成摘要
4. **暂停并展示确认信息**（借鉴 Step 8 User Confirmation）
5. 用户输入 1 确认后才写入文件

### 3. 非交互执行（CI/定时任务）
```bash
DEMO_AUTO_CONFIRM=1 python3 weekly_todo_summary.py
```
跳过交互式确认，直接执行。适用于 cron 定时任务。

## 如何替换为真实数据

### 方式一：替换 todos.json
将 todos.json 替换为从真实任务系统导出的数据，保持相同 JSON 结构：
```json
{
  "team": "团队名",
  "week": "周期",
  "members": [{"id":1, "name":"姓名", "role":"角色"}],
  "todos": [{"id":"T-001", "assignee":1, "title":"标题", "due":"YYYY-MM-DD", "status":"done|in_progress|todo", "priority":"high|medium|low"}]
}
```

### 方式二：对接飞书任务/多维表格（需开发）
在脚本中替换 load_todos() 函数，调用飞书 API 获取真实待办：
- 飞书任务 API: <LARK_TASK_API_URL>（占位符）
- 多维表格 API: <LARK_BITABLE_API_URL>（占位符）
- 需要配置 <LARK_APP_ID> 和 <LARK_APP_SECRET>

### 方式三：对接真实发送渠道
当前"发送"=写本地文件。要发送到飞书群/邮件：
1. 配置 webhook URL（<FEISHU_WEBHOOK_URL>）
2. 在脚本末尾添加 HTTP POST 请求发送摘要内容
3. 保留 Step 8 确认环节，发送前仍需人工确认

## 与 release-skills 的关系

| 方面 | release-skills | 本脚本 |
|------|---------------|--------|
| 用途 | 软件版本发布 | 周待办摘要 |
| --dry-run | 有（第38行） | 借鉴实现 |
| 执行前确认 | Step 8 三问确认 | 借鉴实现 |
| 无内容时停止 | "stop rather than creating"（第325行） | 用户选取消即停止 |
| 多语言changelog | 有（Step 4） | 不适用 |
| git tag/Release | 有（Step 9-10） | 不适用 |
| 版本号递增 | 有（Step 3） | 不适用 |

## 注意事项
1. 所有团队成员姓名均为模拟，标注"（模拟）"
2. "今天"日期硬编码为 2026-08-10 以保证演示可复现；真实使用时改为 date.today()
3. 外部 API 地址均为占位符，未实际调用
4. 脚本不修改 todos.json，只读取
