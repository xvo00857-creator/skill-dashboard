# Stitch 同步方案

> 本文档说明如何将本设计系统的页面和文档上传到 Google Stitch 项目。
> 上传使用 `upload-to-stitch` Skill 提供的 Python 脚本，该脚本绕过 MCP 工具的 base64 输出令牌限制，直接通过 HTTP 发送文件。

## 前置条件

| 条件 | 状态 | 说明 |
|:---|:---|:---|
| Python 3.11+ | 已满足 | 系统默认 python3 为 3.9.6（不支持脚本中的 `str \| None` 语法），需使用 `python3.11`（已验证可用） |
| certifi | 已满足 | 已安装，用于 SSL 证书验证 |
| Stitch API Key | **缺失** | 需从 MCP 配置文件提取或由用户提供 |
| Stitch Project ID | **缺失** | 需通过 `list_projects` MCP 工具获取 |
| 待上传文件 | 已就绪 | 见下方清单 |

## 待上传文件清单

以下文件均位于 `stitch-design-system/` 目录，支持 Stitch 上传的文件类型（`.html`、`.md`）：

| 序号 | 文件路径 | MIME 类型 | 建议 Stitch 标题 | 说明 |
|:---|:---|:---|:---|:---|
| 1 | `pages/login.html` | text/html | `/login` | 登录页（自包含） |
| 2 | `pages/dashboard.html` | text/html | `/dashboard` | 仪表盘页（自包含） |
| 3 | `docs/component-mapping.md` | text/markdown | 组件映射表 | 组件清单与页面映射 |
| 4 | `docs/page-structure.md` | text/markdown | 页面结构说明 | 页面 DOM 结构与响应式 |
| 5 | `docs/stitch-sync-plan.md` | text/markdown | Stitch 同步方案 | 本文件 |

> 注意：`tokens/design-tokens.css` 和 `components/components.css` 为开发时引用的源文件，
> 其内容已内联到两个 HTML 页面中，无需单独上传。Stitch 不支持 `.css` 文件类型。

## 上传步骤

### 步骤 1：获取 Project ID

使用 Stitch MCP 工具 `list_projects` 列出项目，找到目标项目的 `projectId`。

### 步骤 2：获取 API Key

从以下位置之一查找 Stitch API Key（`X-Goog-Api-Key`）：

- Antigravity：`.gemini/antigravity/mcp_config.json` 或 `.gemini/jetski/mcp_config.json`
- Gemini CLI：`~/.gemini/settings.json` 或 `~/.gemini/extensions/Stitch/gemini-extension.json`
- Claude Code：`~/.claude.json`

若以上位置均未找到，**必须**向用户索取 API Key，不得在无密钥情况下继续。

### 步骤 3：用户确认（Checkpoint）

上传前必须向用户展示待上传文件列表（路径、大小、类型），等待明确批准后方可执行。

### 步骤 4：执行上传

脚本路径：`upload-to-stitch/scripts/upload_to_stitch.py`（相对于 Skill 目录）。
**注意**：脚本使用 Python 3.10+ 联合类型语法（`str | None`），需用 `python3.11` 运行，系统默认的 `python3`（3.9.6）会报错。

```bash
# 设置变量（替换为实际值）
SKILL_DIR="upload-to-stitch-extracted/upload-to-stitch"
PROJECT_ID="<你的项目ID>"
API_KEY="<你的API密钥>"
BASE="stitch-design-system"
PY=python3.11

# 上传登录页
"$PY" "$SKILL_DIR/scripts/upload_to_stitch.py" \
  --project-id "$PROJECT_ID" \
  --file-path "$BASE/pages/login.html" \
  --api-key "$API_KEY" \
  --title "/login" \
  --generated-by "upload-to-stitch-skill"

# 上传仪表盘页
"$PY" "$SKILL_DIR/scripts/upload_to_stitch.py" \
  --project-id "$PROJECT_ID" \
  --file-path "$BASE/pages/dashboard.html" \
  --api-key "$API_KEY" \
  --title "/dashboard" \
  --generated-by "upload-to-stitch-skill"

# 上传组件映射文档
"$PY" "$SKILL_DIR/scripts/upload_to_stitch.py" \
  --project-id "$PROJECT_ID" \
  --file-path "$BASE/docs/component-mapping.md" \
  --api-key "$API_KEY" \
  --title "组件映射表" \
  --generated-by "upload-to-stitch-skill"

# 上传页面结构文档
"$PY" "$SKILL_DIR/scripts/upload_to_stitch.py" \
  --project-id "$PROJECT_ID" \
  --file-path "$BASE/docs/page-structure.md" \
  --api-key "$API_KEY" \
  --title "页面结构说明" \
  --generated-by "upload-to-stitch-skill"
```

### SSL 问题排查

若遇到 `SSLCertVerificationError`，使用以下方式运行：

```bash
SSL_CERT_FILE=$("$PY" -c "import certifi; print(certifi.where())") \
  "$PY" "$SKILL_DIR/scripts/upload_to_stitch.py" ...
```

## 当前状态

由于当前环境中未找到 Stitch API Key 和 Project ID，上传操作**尚未执行**。
所有文件已在本地准备就绪并通过验证。提供凭据后，可按上述步骤立即上传。

## 安全说明

- API Key 仅在命令行参数中传递给脚本，不会写入任何文件。
- 脚本直接调用 `https://stitch.googleapis.com`，不经过第三方服务器。
- 上传前必须经过用户确认（Skill 强制要求的 Checkpoint）。
