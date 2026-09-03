# configure-auth Skill 审查报告

## 一、能力边界声明（题目假设与 SKILL.md 的冲突说明）

本题将 `configure-auth` 归类为"安全与合规"并要求执行"安全审计、风险确认与防御性修复"。经阅读 SKILL.md，该 Skill 的真实能力边界为：

- **实际用途**：为 Blazor Web App 添加认证与授权配置，涵盖 `[Authorize]`、`AuthorizeView`、角色/策略访问、Identity 登录页、`AuthenticationStateProvider`，以及不同渲染模式（静态 SSR / 交互式 Server / WebAssembly / Auto）下的认证状态处理。
- **不是**：通用漏洞扫描器、渗透测试工具、依赖项审计工具或生产环境安全评估工具。它不包含扫描逻辑、不连接任何外部服务、不执行任何探测命令。

因此，本报告严格以 SKILL.md 记载的配置规则和"常见错误"表为依据，将其转化为一份**防御性认证配置审查清单**。任何超出该 Skill 范围的安全审计项（如依赖漏洞、网络暴露、密钥管理等）均不在本次交付范围内，需使用对应专业工具另行处理。

## 二、审查范围与前提

| 项目 | 状态 |
|------|------|
| 待审查 Blazor 项目代码 | **不存在**。工作区仅含 `configure-auth/SKILL.md`，无 `Program.cs`、`App.razor`、`Routes.razor`、`.razor` 页面、`.csproj` 或 `AGENTS.md`。 |
| AGENTS.md（Skill Step 1 要求读取） | **未找到**。无法确认项目的交互模式（全局交互 vs 逐页交互）和作用域。 |
| 扫描器/工具输出 | 无。本 Skill 不调用扫描器，也未收到任何扫描器提示。 |
| 生产服务 | 未访问、未连接、未中断。全程仅使用只读文件检查。 |

**结论**：由于缺少目标项目，本次无法确认任何具体问题。以下所有条目均为**待验证项**，需在提供实际项目代码后逐项核对。报告不包含任何已证实问题。

## 三、防御性认证配置审查清单（基于 SKILL.md）

以下清单逐条对应 SKILL.md 中的配置步骤和"常见错误"表。每项标注了风险等级、验证方法和防御性修复方案。

### A. 服务注册层（对应 Step 2、Step 6）

| 编号 | 待验证项 | 风险 | 验证方法（只读） | 防御性修复（若确认存在） |
|------|----------|------|------------------|--------------------------|
| A1 | `Program.cs` 是否调用 `AddCascadingAuthenticationState()` | 高：缺失会导致 `Task<AuthenticationState>` 为 null，授权组件无法获取用户状态 | 检查 server 项目 `Program.cs` 是否包含该调用 | 添加 `builder.Services.AddCascadingAuthenticationState();` |
| A2 | `Program.cs` 是否调用 `AddAuthorization()` | 高：缺失则 `[Authorize]` 和策略不生效 | 同上 | 添加 `builder.Services.AddAuthorization();` |
| A3 | 使用 Identity 时是否完整注册 `AddAuthentication` + `AddIdentityCookies` + `AddIdentityCore`（含 Roles、EntityFrameworkStores、SignInManager、DefaultTokenProviders） | 高：注册不完整会导致登录/角色/外部登录失败 | 检查 `Program.cs` 中 Identity 相关服务注册链 | 按 SKILL.md Step 2 代码块补全 |
| A4 | WebAssembly / Auto 模式下，server `Program.cs` 是否调用 `AddAuthenticationStateSerialization()` | 高：缺失会导致 WASM 接管后认证状态变为匿名用户 | 检查 server 端 `Program.cs` | 添加 `builder.Services.AddAuthenticationStateSerialization();`（可配置 `SerializeAllClaims = true`） |
| A5 | WebAssembly / Auto 模式下，client `Program.cs` 是否调用 `AddAuthenticationStateDeserialization()` | 高：与 A4 配对，缺失则客户端无法反序列化认证状态 | 检查 `.Client/Program.cs` | 添加 `builder.Services.AddAuthenticationStateDeserialization();` |

### B. 路由与根组件层（对应 Step 3）

| 编号 | 待验证项 | 风险 | 验证方法（只读） | 防御性修复（若确认存在） |
|------|----------|------|------------------|--------------------------|
| B1 | `Routes.razor`（或路由组件）是否使用 `AuthorizeRouteView` 而非普通 `RouteView` | 高：使用普通 `RouteView` 则 `[Authorize]` 特性不会在路由层强制执行 | 检查路由组件中 `<Found>` 内的组件类型 | 替换为 `AuthorizeRouteView`，并配置 `<NotAuthorized>` 模板 |
| B2 | `App.razor` 是否通过 `AcceptsInteractiveRouting()` 条件设置渲染模式 | 高：全局交互应用若无条件设置，Identity 页面会尝试交互式渲染导致崩溃 | 检查 `App.razor` 中 `RenderModeForPage` 属性逻辑 | 按 SKILL.md Step 3 添加 `HttpContext.AcceptsInteractiveRouting()` 判断，对排除页面返回 null |
| B3 | `<NotAuthorized>` 模板是否区分"未认证"与"已认证但无权限"两种情况 | 中：不区分会导致未认证用户看到"无权限"而非跳转登录 | 检查 `<NotAuthorized>` 内是否判断 `context.User.Identity?.IsAuthenticated` | 未认证时渲染 `<RedirectToLogin />`，已认证无权限时显示提示 |

### C. 页面与组件保护层（对应 Step 4、Step 5）

| 编号 | 待验证项 | 风险 | 验证方法（只读） | 防御性修复（若确认存在） |
|------|----------|------|------------------|--------------------------|
| C1 | 需要保护的页面是否标注 `@attribute [Authorize]` | 高：未标注则匿名用户可访问受限页面 | 搜索所有 `@page` 组件，检查敏感页面（如 `/admin`）是否有 `[Authorize]` | 在需保护页面添加 `@attribute [Authorize]`，按需指定 Roles 或 Policy |
| C2 | 交互式组件中是否直接使用 `HttpContext.User` | 高：交互式 Server / WASM 组件中 `HttpContext` 不可用，会得到 null 或过期声明 | 搜索交互式组件中的 `HttpContext` 引用 | 改用 `[CascadingParameter] Task<AuthenticationState>` 并在 `OnInitializedAsync` 中 await 获取 |
| C3 | 交互式组件中是否直接注入/使用 `SignInManager` 或 `UserManager` | 高：这些服务内部依赖 `HttpContext`，在交互式组件中会抛出 `InvalidOperationException` | 搜索交互式组件中的 `SignInManager` / `UserManager` 注入 | 将登录/注册/管理页面移至静态 SSR，并标注 `[ExcludeFromInteractiveRouting]` |
| C4 | 全局交互应用中，Identity 页面（Login/Register/Manage）是否标注 `[ExcludeFromInteractiveRouting]` | 高：未标注则这些页面仍在交互式 circuit 中渲染，`SignInManager` 抛异常 | 检查 Identity 页面是否有该特性；同时确认 B2 已配置 | 添加 `@attribute [ExcludeFromInteractiveRouting]` |
| C5 | 逐页交互应用中，Identity 页面是否误加了 `@rendermode` 指令 | 中：逐页模式下 Identity 页面默认静态 SSR 即可，加 `@rendermode` 反而引入 C3 问题 | 检查 Identity 页面是否有 `@rendermode` | 移除 Identity 页面上的 `@rendermode` 指令（逐页模式下不需要 `[ExcludeFromInteractiveRouting]`） |

### D. 静态 SSR 重定向层（对应 Render Mode × Auth Matrix）

| 编号 | 待验证项 | 风险 | 验证方法（只读） | 防御性修复（若确认存在） |
|------|----------|------|------------------|--------------------------|
| D1 | 是否误以为静态 SSR 下 `<NotAuthorized>` 会自动渲染内容 | 中：静态 SSR 使用中间件管道，`<NotAuthorized>` 内容不会显示，需通过中间件重定向 | 确认应用渲染模式；检查 cookie 认证事件的 `LoginPath` 配置或 `RedirectToLogin` 组件 | 配置 `LoginPath` 或使用 `RedirectToLogin` 组件进行重定向，不要依赖 `<NotAuthorized>` 模板 |

## 四、问题分类汇总

| 分类 | 数量 | 说明 |
|------|------|------|
| 已证实问题 | 0 | 无目标项目代码，无法证实任何问题。 |
| 待验证项（疑似） | 13 | 即第三节 A1–D1，均为 SKILL.md 明确记载的常见错误模式，需在实际项目中核对。 |
| 误报/场景依赖项 | 见下 | 以下情况在特定渲染模式下不是问题，不应误报： |

**不应误报的场景依赖项：**

1. **逐页交互应用中 Identity 页面缺少 `[ExcludeFromInteractiveRouting]`** —— 不是问题。SKILL.md Step 5 明确说明逐页模式下 Identity 页面默认静态 SSR，不需要该特性。
2. **静态 SSR 组件中使用 `HttpContext.User`** —— 不是问题。`HttpContext` 在静态 SSR 管道中可用。仅在交互式组件中才是问题（C2）。
3. **缺少 `AddAuthenticationStateSerialization`** —— 仅在 WebAssembly / Auto 模式下是问题。纯静态 SSR 或纯交互式 Server 应用不需要。
4. **`<NotAuthorized>` 不渲染** —— 在静态 SSR 下是框架设计行为（中间件管道处理），不是 bug；但需确认有替代重定向机制（D1）。

## 五、最小风险验证计划

以下计划全部使用**只读操作**，不修改任何文件、不重启服务、不连接生产环境。

### 阶段 1：环境确认（零风险）

1. 获取目标 Blazor 项目代码（只读副本或脱敏样本）。
2. 读取项目根目录 `AGENTS.md`（Skill Step 1 强制要求），确认：
   - 交互模式：全局交互（globally interactive）还是逐页交互（per-page）？
   - 渲染模式：静态 SSR / Interactive Server / WebAssembly / Auto？
3. 检查 `.csproj` 确认项目结构（是否有独立 `.Client` 项目）。

### 阶段 2：静态配置核对（只读，不运行代码）

4. 按第三节清单 A1–A5 检查 `Program.cs`（server 和 client）。
5. 按 B1–B3 检查 `App.razor` 和 `Routes.razor`。
6. 用文本搜索定位所有 `@page` 组件，核对 C1（敏感页面授权）。
7. 搜索交互式组件中的 `HttpContext`、`SignInManager`、`UserManager` 引用，核对 C2、C3。
8. 检查 Identity 页面目录（通常在 `/Areas/Identity/Pages/Account/`），核对 C4、C5。

### 阶段 3：本地构建验证（低风险，仅本地开发环境）

9. 在本地开发环境执行 `dotnet build` 确认编译通过（不连接生产数据库）。
10. 使用本地测试数据库运行应用，验证：
    - 未认证访问受保护页面是否跳转登录（而非崩溃或放行）；
    - 登录后认证状态是否保持（特别关注 WASM/Auto 模式接管后是否变匿名）；
    - 登录/登出页面是否正常渲染（无 `InvalidOperationException`）；
    - 角色/策略授权是否正确拒绝无权限用户。
11. 验证过程中不修改生产配置、不重启生产服务、不使用生产数据。

### 阶段 4：修复后复测

12. 对确认存在的问题，按第三节"防御性修复"列进行最小化修改。
13. 重复阶段 3 的验证项确认修复生效。
14. 修复仅涉及认证配置代码，不改动业务逻辑。

## 六、无法访问/待确认的资源与假设

| 项 | 状态 | 影响 |
|----|------|------|
| 目标 Blazor 项目代码 | 未提供 | 无法确认任何具体问题，所有审查项均为待验证 |
| `AGENTS.md` | 未找到 | 无法确认交互模式，导致 A4/A5/C4/C5 等渲染模式相关项无法判定是否适用 |
| 项目渲染模式 | 未知 | Render Mode × Auth Matrix 的适用行无法确定 |
| 是否使用 ASP.NET Core Identity | 未知 | A3 的 Identity 服务注册检查是否适用无法确定 |
| 生产环境访问 | 未访问 | 本报告不包含任何运行时验证结果 |

## 七、实际读取的 Skill 文件

| 相对路径 | 说明 |
|----------|------|
| `configure-auth/SKILL.md` | 唯一文件，已完整读取（206 行） |

ZIP 包内仅包含此一个文件，无其他脚本、模板或资源文件。

## 八、影响交付结果的 SKILL.md 规则

**规则**：SKILL.md "Common Mistakes" 表第 4 行——"`<NotAuthorized>` in static SSR layout → Content never shown → Static SSR uses middleware pipeline; redirect via `LoginPath` or `RedirectToLogin` component"，以及 Render Mode × Auth Matrix 中"Static SSR"行的"Use middleware for redirects, `<NotAuthorized>` does NOT render"。

**对交付结果的影响**：这条规则直接决定了本报告 D1 项的分类——它将"静态 SSR 下 `<NotAuthorized>` 不渲染"从一个看似的 bug 正确归类为**框架设计行为**，并指出真正需要验证的是"是否存在替代的中间件重定向机制"。如果忽略此规则，审查者很可能将其误报为漏洞并建议在静态 SSR 布局中"修复" `<NotAuthorized>` 模板，而正确的防御方向是配置 cookie 认证的 `LoginPath` 或使用 `RedirectToLogin` 组件。这体现了该 Skill 按渲染模式区分认证行为的核心原则，也直接支撑了第四节"误报/场景依赖项"的判定。

---

*本报告所有结论均基于 configure-auth/SKILL.md 的文本内容，未编造任何文件内容、扫描结果或运行时数据。提供实际项目代码后，可按第五节计划执行逐项验证。*
