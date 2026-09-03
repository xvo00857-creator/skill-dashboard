# smart-explore 交付说明

## 一、Skill 概述

`smart-explore` 是一个基于 tree-sitter AST 解析的 Token 优化代码结构搜索 MCP 服务器。
核心原则：**先获取代码地图，再按需加载实现细节**（Index first, fetch on demand）。

提供三个 MCP 工具：

| 工具 | 作用 |
|------|------|
| `smart_search` | 跨目录发现文件和符号，返回排序匹配 + 折叠文件视图 |
| `smart_outline` | 单文件结构骨架（函数、类、方法、属性、import），约 1-2k tokens |
| `smart_unfold` | 指定符号的完整源码（含 JSDoc、装饰器、完整实现） |

## 二、最小改动方案

### 背景

SKILL.md 明确声明：*"This skill only loads instructions. You must call the MCP tools yourself."*
即 Skill 包本身只包含使用说明，三个 MCP 工具需要由运行环境另行提供。
经检查，当前环境中未安装 `smart_search` / `smart_outline` / `smart_unfold` 这三个 MCP 工具，
因此本次交付的核心工作是**实现这三个工具对应的 MCP 服务器**，使 Skill 可以实际使用。

### 改动内容

在 Skill 目录 `smart-explore/` 下新增以下文件（不修改原有 `SKILL.md`）：

```
smart-explore/
├── SKILL.md              # 原有文件，未修改
├── package.json          # 更新：main/bin/scripts 字段，声明依赖
├── package-lock.json     # npm install 生成
├── src/
│   ├── index.js          # MCP 服务器入口（stdio 传输，注册三个工具）
│   ├── languages.js      # 内置语言配置（扩展名→tree-sitter 包、AST 节点类型映射）
│   ├── parser.js         # Parser 实例缓存与解析封装
│   ├── symbols.js        # AST 遍历与符号提取核心逻辑
│   ├── search.js         # smart_search 实现（评分排序、折叠视图）
│   ├── outline.js        # smart_outline 实现
│   ├── unfold.js         # smart_unfold 实现
│   ├── markdown.js       # Markdown 特殊处理（标题树、frontmatter、节展开）
│   ├── config.js         # .claude-mem.json 自定义语法加载
│   └── fileutil.js       # 目录遍历、文件读取、忽略规则
└── test/
    ├── run-tests.js      # 24 个测试用例
    └── fixtures/         # TS/Python/Go/Markdown 测试样本
```

### 依赖选择（约束影响）

| 依赖 | 版本 | 选择理由 |
|------|------|----------|
| tree-sitter | 0.22.4 | 未使用 0.25.x：该版本与部分语言包存在 peer dependency 冲突，0.22.4 与所有语言包兼容 |
| tree-sitter-typescript | 0.23.2 | 同时提供 typescript 和 tsx 两个 language |
| tree-sitter-javascript | 0.23.1 | JS/JSX 支持 |
| tree-sitter-python | 0.23.6 | Python 支持 |
| tree-sitter-go | 0.23.4 | Go 支持 |
| tree-sitter-rust | 0.24.0 | Rust 支持 |
| tree-sitter-ruby | 0.23.1 | Ruby 支持 |
| tree-sitter-java | 0.23.5 | Java 支持 |
| tree-sitter-c | 0.24.1 | C 支持 |
| tree-sitter-cpp | 0.23.4 | C++ 支持 |
| @modelcontextprotocol/sdk | ^1.30.0 | MCP 协议 SDK，提供 McpServer / StdioServerTransport |

依赖版本均为各语言包与 tree-sitter 核心兼容的稳定版本，使用 `--legacy-peer-deps` 安装。
未引入任何未经批准的新依赖——所有依赖均为 SKILL.md 列出的语言支持所必需。

### 接口兼容性

三个工具的参数名、类型、默认值严格遵循 SKILL.md：

- `smart_search(query, path?, max_results?, file_pattern?)` — max_results 默认 20，上限 50
- `smart_outline(file_path)`
- `smart_unfold(file_path, symbol_name)`

输出格式遵循 SKILL.md 描述：
- search 返回 `-- Matching Symbols --` + 符号列表（含签名、行号、匹配原因）+ `-- Folded File Views --`
- outline 返回约 1-2k tokens 的结构骨架
- unfold 返回完整源码，AST 节点边界保证完整性，包含前置 JSDoc/装饰器

## 三、回滚办法

本次改动全部位于 `smart-explore/` 目录内，不影响项目其他文件。

**完全回滚：**
```bash
rm -rf smart-explore/src smart-explore/test smart-explore/node_modules
rm smart-explore/package.json smart-explore/package-lock.json
```
执行后目录恢复为仅有原始 `SKILL.md` 的状态。

**仅回滚依赖：**
```bash
rm -rf smart-explore/node_modules smart-explore/package-lock.json
```

## 四、测试清单

### 自动化测试（24 项，全部通过）

```
cd smart-explore && npm test
```

| 分类 | 测试项 |
|------|--------|
| smart_search (9) | TS 类方法搜索、Python 类搜索、Go 结构体搜索、Go 方法搜索、max_results 限制、file_pattern 过滤、Markdown 标题搜索、无匹配优雅返回、精确匹配排序优先 |
| smart_outline (5) | TS 文件结构（类/方法/接口/import/函数）、Python 类与函数、Go 结构体与方法、Markdown 标题与 frontmatter、不存在文件报错 |
| smart_unfold (8) | TS 方法完整实现、TS JSDoc 包含、Python 方法完整实现、Go 方法完整实现、ClassName.method 格式、Markdown 节展开、不存在符号报错并列出可用符号、缺少参数报错 |
| 语言支持 (2) | TS interface 提取、Go type 提取 |

### MCP 协议验证

- stdio 传输启动正常
- `initialize` 握手返回 serverInfo: smart-explore 1.0.0
- `tools/list` 返回三个工具
- `tools/call` 调用 smart_outline 返回正确结果

### 支持的语言

JavaScript (.js/.mjs/.cjs)、TypeScript (.ts)、TSX/JSX (.tsx/.jsx)、
Python (.py/.pyw)、Go (.go)、Rust (.rs)、Ruby (.rb)、Java (.java)、
C (.c/.h)、C++ (.cpp/.cc/.cxx/.hpp/.hh)、Markdown (.md/.mdx)。

不支持的扩展名回退为纯文本搜索。

## 五、仍待确认项

1. **MCP 客户端配置**：需在 MCP 客户端配置文件中添加本服务器，例如：
   ```json
   {
     "mcpServers": {
       "smart-explore": {
         "command": "node",
         "args": ["/path/to/smart-explore/src/index.js"]
       }
     }
   }
   ```
   具体配置路径取决于使用的 MCP 客户端（Claude Desktop / Cursor / 其他）。

2. **自定义语法 query 文件**：SKILL.md 提到通过 `.claude-mem.json` 配置自定义 tree-sitter 语法，
   并支持 `.scm` query 文件。已实现加载逻辑，但未对所有可能的自定义语言编写 query 做端到端验证。
   SKILL.md 指出"most languages require a custom query"，通用降级模式仅能提取基础结构。

3. **Ruby/Java/C/C++/Rust 的深度测试**：当前测试覆盖了 TS/Python/Go/Markdown，
   其他语言的 AST 节点类型映射已按 tree-sitter 语法定义配置，但未在真实项目中验证。
   如遇提取遗漏，需在 `src/languages.js` 的 `nodeTypes` 中补充节点类型。

4. **tree-sitter 版本升级**：当前锁定 0.22.4 以保证兼容性。
   若未来所有语言包发布支持 0.25.x 的版本，可考虑升级，但需重新验证 peer dependencies。

## 六、实际读取的 Skill 文件

- `smart-explore/SKILL.md`（相对路径）

## 七、影响交付结果的 SKILL.md 规则

1. **"This skill only loads instructions. You must call the MCP tools yourself."**
   —— 这条规则直接决定了本次交付的核心工作：Skill 包不包含可执行代码，
   三个 MCP 工具在当前环境中不存在，因此必须实现 MCP 服务器才能让 Skill 生效。

2. **语言支持列表**（JavaScript/TypeScript/Python/Go/Rust/Ruby/Java/C/C++）
   —— 决定了需要安装哪些 tree-sitter 语言包，以及版本兼容性约束。

3. **.claude-mem.json 自定义语法配置**
   —— 决定了 `src/config.js` 的实现：从项目根目录读取配置，从 node_modules 加载语法包，
   支持可选的 .scm query 文件，包未安装时静默降级。

4. **Markdown 特殊处理**（标题作为符号树、frontmatter 作为合成符号、unfold 展开到同级标题）
   —— 决定了 `src/markdown.js` 的独立实现，而非走 tree-sitter 解析路径。

5. **"Index first, fetch on demand"** 原则
   —— 决定了三个工具的分工：search 返回折叠视图而非完整代码，outline 只给骨架，
   unfold 才加载完整实现，避免一次性加载过多 token。
