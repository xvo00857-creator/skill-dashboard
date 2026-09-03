# browser-act-skill-forge 受约束执行方案与演示结果

> 生成时间：2026-08-12 08:30 (UTC+8)
> 执行环境：macOS，当前会话无沙箱，有风险操作由系统弹窗确认
> 核心约束：browser-act 工具不可用；仅使用现有权限和已提供数据；不静默创建/删除/覆盖外部资源

---

## 一、预检结果（Phase 0）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| browser-act Skill 是否安装 | 未安装 | 所有 skill 根目录下无 browser-act；仅有 browser-task（不同工具） |
| browser-act CLI 是否在 PATH | 否 | `which browser-act` 无结果 |
| npm 全局包 | 未安装 | `npm list -g browser-act` 为空 |
| npm registry 是否存在 | 不存在 | `npm view browser-act` 返回 404 |
| pip 包 | 未安装 | `pip3 show browser-act` 无结果 |
| 网络访问 | 有限 | curl 可访问公开网站；web.fetch 对部分域名被安全策略拦截 |
| Python3 | 可用 | 用于运行 wrapper 脚本 |
| Node.js | 可用 | 用于 JS 语法检查和离线 mock 验证 |

**结论**：browser-act 是本 Skill 的核心依赖（Phase 2 网络流量检查、浏览器内 JS eval、HAR 录制、`wait stable` 等均依赖它），当前环境无法满足。按 SKILL.md Phase 0 规定，应"follow its guidance to resolve then retry"，但该工具在 npm registry 上不存在，无法通过常规方式安装。

**处理方式**：不伪造 browser-act 执行结果，不跳过预检。在约束下用现有工具（curl 获取 HTML、Python/Node 离线验证）完成可验证部分，并明确标注未验证项。

---

## 二、受约束流程方案

### 2.1 总体流程

```
预检（工具/权限/网络）
  → 需求确认（目标网站、能力拆分、输出目录）【人工确认点 1】
  → 站点探索（API 优先 → UI 触发+网络捕获 → DOM 提取）
  → 能力验证（fetch 复现 / 选择器三层验证 / 分页验证）
  → Skill 生成（Python wrapper + SKILL.md）
  → 封装验证（Python 输出 JS → 浏览器 eval → 错误场景）【人工确认点 2】
  → 自动化测试（Sub-Agent 执行）
  → 安装 Skill【人工确认点 3】
  → 批量执行（如有执行意图）
```

### 2.2 预检点

每个阶段开始前执行以下检查，任一失败则暂停并报告：

1. **工具就绪检查**：browser-act 是否可调用；API Key 是否已配置（如不可用，记录降级方案）
2. **目标可达性检查**：目标网站是否可访问；是否需要登录；当前登录状态是否有效
3. **输出目录检查**：`output/{skill-name}/` 是否已存在；若存在，检查是否为同一 Skill 的旧版本，避免覆盖未备份的工作
4. **权限边界检查**：确认操作仅读取页面已显示数据，不调用官方开放平台 API，不使用第三方代理/抓取服务
5. **磁盘空间检查**：确认 `tmp/` 和 `output/` 所在磁盘有足够空间

### 2.3 幂等设计

| 环节 | 幂等措施 |
|------|----------|
| 目录创建 | `mkdir -p`，已存在不报错；生成前检查是否已有同名 Skill，存在则询问而非覆盖 |
| 探索记录 | HAR 文件和临时 HTML 以时间戳命名，不覆盖已有记录 |
| 数据提取 | 批量执行时按 `id` 去重；重复运行同一页只追加新 id，已存在的跳过 |
| 分页遍历 | 记录已完成的页码，中断后从最后成功页的下一页恢复，不从头开始 |
| 文件写入 | Python wrapper 生成时先写临时文件再原子替换，避免半写文件 |
| Skill 安装 | 安装前检查目标位置是否已有同名 Skill，已有则提示版本差异 |

### 2.4 重试策略

按 SKILL.md 规定：

- **确定性失败**（明确错误码、结构不匹配、404、选择器命中 0 个元素）：不重试，立即切换到下一种手段（API → UI 触发+网络捕获 → DOM → AI Workflow）
- **瞬时失败**（超时、连接断开）：仅重试 1 次，不超过 1 次
- **探索手段切换顺序**：API 验证失败 → UI 触发+网络捕获 → DOM 提取 → AI Workflow → 报告障碍
- **探索上限**：100 个工具调用步骤，超出后报告已知障碍并询问下一步
- **批量执行**：单条失败不终止整批，记录失败项继续；整批结束后报告失败清单；支持从断点恢复
- **反爬限制**：串行执行，页间加 1-2 秒延迟；被限流时暂停并通知用户，不自动切换代理

### 2.5 人工确认点

| 确认点 | 时机 | 确认内容 |
|--------|------|----------|
| 确认点 1 | Phase 1 结束，探索开始前 | 目标网站 URL、能力拆分、输出目录、是否需要立即执行批量任务 |
| 确认点 2 | Phase 3b 封装验证后 | 验证结果是否接受；是否有未覆盖字段需要补充探索 |
| 确认点 3 | 安装 Skill 前 | 安装位置；是否覆盖已有同名 Skill |
| 确认点 4（操作类能力） | 提交类操作前 | 离线 HAR 验证通过后，实际在线执行前必须人工确认（本次演示为提取类，不涉及） |

---

## 三、演示执行记录

### 3.1 目标选择

- **网站**：Hacker News（https://news.ycombinator.com/）
- **选择理由**：公开无需登录、SSR 结构简单稳定、适合 DOM 提取路径演示
- **能力拆分**：1 个提取能力——首页故事列表提取（含 URL 分页）
- **输出目录**：`output/hackernews-stories/ycombinator-front-stories/`

### 3.2 探索方式（受限）

由于 browser-act 不可用，采用以下替代探索方式：

| SKILL.md 规定步骤 | 本次执行方式 | 差异说明 |
|-------------------|-------------|----------|
| `navigate` + `wait stable` | curl 获取页面 HTML | 非浏览器环境，无 JS 渲染；HN 为 SSR，HTML 含完整数据 |
| `network requests` 检查 API | 检查 HTML 中是否有内联 JSON / API 调用 | HN 首页为纯 SSR，无前端 API 调用，走 DOM 路径 |
| `eval` 验证选择器 | Python HTMLParser 解析真实 HTML 验证选择器匹配 | 非浏览器内验证，但用真实页面数据确认了选择器命中 |
| 分页验证 | curl 获取第 2 页 HTML，对比 id 和 rank | 确认两页无重叠、rank 连续 |

### 3.3 验证结果

**1. Python wrapper 输出验证（Phase 3b 第 1 步）**

```
python3 scripts/extract-stories.py        → 输出合法 JS 字符串，node --check 通过
python3 scripts/get-next-page.py          → 输出合法 JS 字符串，node --check 通过
python3 scripts/extract-stories.py --limit 1 → 参数化正确
```

**2. 离线 mock DOM 逻辑验证（替代 Phase 3b 第 2 步）**

使用 Node.js 构造 mock DOM，执行生成的 JS，5 项测试全部通过：

| 测试 | 结果 |
|------|------|
| 正常提取 2 条故事（含完整字段） | 通过：id/rank/title/url/site/score/user/age/comments 均正确 |
| 空页面错误处理 | 通过：返回 `{"error":true,"message":"..."}` |
| 有下一页链接 | 通过：`hasNext:true, nextUrl:"news?p=2"` |
| 无下一页链接 | 通过：`hasNext:false` |
| --limit 参数 | 通过：只返回 1 条 |

**3. 真实页面数据验证**

用 curl 获取真实 HN 首页 HTML（34,650 字节），Python 解析确认：
- 故事数：30 条
- 核心字段（id/rank/title/url）非空率：100%
- 分页链接：`?p=2`
- 第 2 页（30 条）与第 1 页 ID 重叠：0
- rank 连续性：第 1 页 1-30，第 2 页 31-60

### 3.4 未验证项（明确标注）

以下 SKILL.md 要求的验证步骤因 browser-act 不可用而**未执行**，不声称已通过：

1. **浏览器内 eval 验证**（Phase 3b 第 2 步）：`eval "$(python scripts/xxx.py)"` 在真实浏览器中执行——未执行
2. **错误场景浏览器验证**（Phase 3b 第 3 步）：导航到错误页面/不存在 ID 时的浏览器行为——未执行
3. **Sub-Agent 自动化测试**（Delivery 第 1 步）：通过子 Agent 执行完整测试——未执行
4. **Skill 安装**（Delivery 第 2 步）：安装到 Skill 目录——未执行（需人工确认）
5. **选择器三层验证中的"真实页面刷新后稳定性"**：仅验证了单次获取的 HTML，未在浏览器中刷新对比
6. **反爬/限流行为**：未在浏览器中高频访问，未观察到限流响应

---

## 四、生成的 Skill 包

```
output/hackernews-stories/
├── demo_result.json                          # 真实页面提取的演示数据（30 条）
└── ycombinator-front-stories/
    ├── SKILL.md                              # 生成的 Skill 定义文件
    └── scripts/
        ├── extract-stories.py                # 故事列表提取 JS wrapper
        └── get-next-page.py                  # 下一页链接 JS wrapper
```

**实现方式**：DOM 提取（SSR 页面，无前端 API 端点）
**数据覆盖**：id、rank、title、url、site、score、user、age、comments（9 个字段）
**分页**：URL 分页，`a.morelink` 的 href 指向下一页（`?p=N`）

---

## 五、实际读取的 Skill 文件

以下为本次实际读取的文件（相对路径基于解压后的 Skill 根目录）：

1. `SKILL.md` — 主流程定义（Phase 0-3 + Delivery + 工具约束）
2. `references/exploration_extraction.md` — 提取类能力探索指南
3. `references/exploration_operation.md` — 操作类能力探索指南
4. `references/output_template.md` — 输出文件格式规范

---

## 六、影响交付结果的 SKILL.md 规则

**规则**（SKILL.md 第 277 行，Code Constraints）：
> "Must directly operate on target site: never obtain data through external services... never call the target site's official open platform API... Solutions must access the target site directly through the browser, using its frontend's internal endpoints or DOM data."

**对交付结果的影响**：
Hacker News 提供官方 Firebase API（`hacker-news.firebaseio.com`），使用该 API 可以更方便地获取数据。但该规则明确禁止调用目标网站的官方开放平台 API，要求通过浏览器直接访问目标站点的前端内部端点或 DOM 数据。因此本次生成的 Skill 采用 DOM 提取路径（从 `news.ycombinator.com` 的页面 DOM 中读取数据），而非调用 HN 官方 API。这直接决定了：
- 能力组件标记为 "DOM" 而非 "API"
- 分页方式为 URL 分页（跟随 "More" 链接）而非 API 分页参数
- 数据字段受限于页面 DOM 中实际显示的内容

**另一条关键规则**（SKILL.md 第 36 行，Phase 0）：
> "Invoke `browser-act` via Skill tool to load usage. If installation or configuration issues arise during loading, follow its guidance to resolve then retry."

**对交付结果的影响**：
browser-act 不可用导致 Phase 2 的浏览器内探索（网络流量检查、JS eval、HAR 录制）和 Phase 3b 的浏览器内验证无法按规定执行。这直接导致交付物中存在 6 项未验证步骤，演示结果降级为离线验证 + 真实 HTML 结构分析，而非完整的浏览器端到端验证。

---

## 七、后续建议

1. **安装 browser-act**：在具备 browser-act 的环境中重新执行 Phase 2 和 Phase 3b，完成浏览器内验证
2. **Sub-Agent 测试**：验证通过后按 Delivery 流程派发子 Agent 执行自动化测试
3. **人工确认安装**：测试通过后由用户确认安装到 Skill 目录
4. **扩展能力**：如需提取评论、用户信息等，可新增详情页提取能力（同一 Skill 包内追加能力目录）
