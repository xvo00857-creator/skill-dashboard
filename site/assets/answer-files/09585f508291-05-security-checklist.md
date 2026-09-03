# 安全检查报告

> 检查依据：csp-and-metadata.md 的 "Security Best Practices" 章节，以及通用安全实践。
> Skill 未覆盖的项已标注 [补充]。

## 检查结果

### 来自 csp-and-metadata.md 的规则

| # | 规则 | 状态 | 说明 |
|---|------|------|------|
| 1 | Specify exact domains (not wildcards) | 通过 | 配置中使用完整 URL，CSP connectDomains 要求精确域名 |
| 2 | Avoid wildcards | 通过 | 未使用通配符域名 |
| 3 | Never use 'unsafe-eval' | 通过 | 未引入 unsafe-eval |
| 4 | Test CSP in development | [需手动验证] | 在 Inspector (http://localhost:3000/inspector) 中验证 |
| 5 | Use HTTPS for all resources | 通过 | SUMMARY_API_BASE_URL 默认值为 https:// |

### 来自 server-and-widgets.md 的规则

| # | 规则 | 状态 | 说明 |
|---|------|------|------|
| 6 | Tool annotations 标记 readOnlyHint | 通过 | summarize-weather 设置 readOnlyHint: true |
| 7 | zod schema 验证输入 | 通过 | 所有入参通过 z.object() 验证 |
| 8 | 错误处理使用 ErrorBoundary | N/A | 本 tool 无 widget，不涉及 React ErrorBoundary |

### [补充] 通用安全实践（Skill 未明确规定）

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 9 | API 密钥不入库 | 通过 | .env 在 .gitignore 中；.env.example 仅含占位符 |
| 10 | 密钥通过 Authorization header 传递 | 通过 | 使用 Bearer token，不出现在 URL 或日志中 |
| 11 | 错误响应不泄露密钥 | 通过 | catch 块中错误消息不含 apiKey |
| 12 | 请求超时设置 | 通过 | AbortController + 10s 默认超时 |
| 13 | 输入消毒（zod 验证） | 通过 | city/model/language 均经 zod 验证 |
| 14 | 不修改现有 tool（向后兼容） | 通过 | get-weather schema 和行为未变 |
| 15 | 版本号小版本升级 | 通过 | 1.0.0 -> 1.1.0（新增功能，无 breaking change） |

## 需要手动验证的项

1. 在 MCP Inspector 中测试 summarize-weather tool，确认正常调用和错误场景
2. 确认 .env 文件实际存在于项目根目录且未被 git 追踪：`git status` 不应显示 .env
3. 确认部署环境（mcp-use deploy）中已配置 SUMMARY_API_BASE_URL 和 SUMMARY_API_KEY
4. 如使用 widget，需在 widgetMetadata.metadata.csp.connectDomains 中添加外部 API 域名
5. [补充] 运行契约测试：`node --test tests/`

## 发现的 Skill 限制

- Skill 无密钥管理最佳实践章节（仅 setup.md 一处 process.env 示例）
- Skill 无测试指导
- Skill 无 API 版本化/向后兼容策略指导
- Skill 无速率限制/重试/熔断等生产级可靠性指导
