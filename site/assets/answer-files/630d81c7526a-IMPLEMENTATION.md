# OpenTelemetry .NET 接入实现说明

本工程按随附 Skill `configuring-opentelemetry-dotnet` 的 SKILL.md 落地，在 ASP.NET Core 8 中接入
Traces / Metrics / Logs 三信号，统一通过 OTLP 导出。

## 一、前提与重要说明

- 本次消息只上传了 Skill 压缩包，**未提供既有业务项目**。因此新建了最小可编译参考工程
  `OtelDemo.Api`（`dotnet new web`，net8.0）来落实配置。接入既有项目时，只需把
  “Program.cs 中的 OpenTelemetry 配置块”和“自定义 ActivitySource / Meter 代码”平移过去，
  无需照搬示例端点。
- 本机 .NET SDK：`8.0.424`（`~/.dotnet/dotnet`）。目标框架 `net8.0`，未升级主版本。
- NuGet 实际还原版本均为 **1.17.0**（当前 1.x 最新稳定版），未引入 Skill 清单外的任何直接依赖。

## 二、最小改动方案

### 1. 新增的直接依赖（仅 4 个，严格对应 SKILL.md Step 1）

| 包 | 版本 | 用途 |
|----|------|------|
| OpenTelemetry.Extensions.Hosting | 1.17.0 | DI 集成（`AddOpenTelemetry`） |
| OpenTelemetry.Instrumentation.AspNetCore | 1.17.0 | 入站 HTTP 自动埋点 |
| OpenTelemetry.Instrumentation.Http | 1.17.0 | 出站 HTTP 自动埋点 + 上下文传播 |
| OpenTelemetry.Exporter.OpenTelemetryProtocol | 1.17.0 | 三信号统一 OTLP 导出 |

未引入：`OpenTelemetry` 单独包（SKILL.md 明确禁止）、`OpenTelemetry.Exporter.Console`
（SKILL.md 标注仅限本地调试、不得进生产）、SqlClient/EF Core/gRPC/Runtime 等可选 instrumentation
（本工程未使用对应库，按“只装匹配项”原则不加）。

传递依赖 `System.Diagnostics.DiagnosticSource 10.0.0` 由 NuGet 自动解析，非手工指定。

### 2. 代码改动

- `Program.cs`：新增 `AddOpenTelemetry()` 配置块（Resource / Tracing / Metrics / Logging / OTLP），
  注册 `AddHttpClient()`、`OrderService`、`OrderMetrics`，新增 `/healthz` 与示例 `/orders` 端点。
- `Services/OrderService.cs`：按 Step 4 用静态 `ActivitySource("MyApp.Orders")` 创建业务 span，
  异常经 `ILogger.LogError` 记录（而非 `RecordException`）。
- `Services/OrderMetrics.cs`：按 Step 5 通过 DI 注入的 `IMeterFactory` 创建 `Meter("MyApp.Metrics")`，
  定义 Counter / Histogram / UpDownCounter。

### 3. 与 SKILL.md 示例的一处必要偏差（已核实）

SKILL.md Step 2 写法：

```csharp
.WithLogging(logging => { logging.IncludeScopes = true; })
```

在实际还原的 **1.17.0** 中编译失败：`WithLogging` 的单参数重载回调类型是
`LoggerProviderBuilder`，而 `IncludeScopes` 位于 `OpenTelemetryLoggerOptions`。
1.17.0 需使用双参数重载：

```csharp
.WithLogging(
    configureBuilder: _ => { },
    configureOptions: options => options.IncludeScopes = true)
```

语义与 SKILL.md 完全一致（开启 scopes、OTLP 导出对日志生效），仅适配 1.17.0 的真实 API 签名。
此外 `UseOtlpExporter()` 位于 `OpenTelemetry` 命名空间，需 `using OpenTelemetry;`。

## 三、约束如何改变了实现选择

- **“不随意升级主版本 / 不引入未经批准的新依赖”**：目标框架保持 net8.0；OTel 包全部锁定 1.x 最新稳定版
  1.17.0，未引入任何 Skill 清单外的直接包；可选 instrumentation 一律不加。
- **“兼容既有接口和目录结构”**：因无既有项目，采用最小 API（`dotnet new web`）而非 Web API 模板
  （后者会自带 Swashbuckle 等额外依赖），把侵入面降到最低；自定义类型集中在 `Services/`，
  并在注释中标注真实项目应放回既有 `Models/` 目录。
- **“最小改动”**：三信号在同一个 `AddOpenTelemetry()` 链式调用中配置，一个 OTLP exporter 覆盖全部信号，
  不拆分多套 exporter、不引入额外配置文件。
- **“不编造运行结果”**：所有结论均来自实际 `dotnet build` 与 `dotnet run` + curl 的真实输出；
  未连接真实 OTLP 后端，因此“链路在后端可见”这一项只列入测试清单，未声称已验证。

## 四、回滚办法

1. 删除 `Program.cs` 中 `AddOpenTelemetry()` 整块及 `using OpenTelemetry.*`、
   `using OtelDemo.Api.Services;`，移除 `AddHttpClient()` 与两个服务注册（若它们仅为示例而存在）。
2. 删除 `Services/OrderService.cs`、`Services/OrderMetrics.cs` 及示例端点、示例 record。
3. 卸载 4 个包：
   ```bash
   dotnet remove package OpenTelemetry.Extensions.Hosting
   dotnet remove package OpenTelemetry.Instrumentation.AspNetCore
   dotnet remove package OpenTelemetry.Instrumentation.Http
   dotnet remove package OpenTelemetry.Exporter.OpenTelemetryProtocol
   ```
4. 还原后执行 `dotnet build` 确认 0 错误。
   （若用版本控制，直接 revert 对应提交即可，以上为无 VCS 时的手工回滚。）

## 五、测试清单

### 已实际执行

- [x] `dotnet build -c Release`：**Build succeeded，0 Warning，0 Error**。
- [x] `dotnet run` 启动，`GET /healthz` → 200 `{"status":"healthy"}`。
- [x] `POST /orders`（合法请求）→ 200，返回订单 JSON，触发自定义 span 与指标记录。
- [x] `POST /orders`（空 items）→ 500，异常经 `ILogger.LogError` 输出到控制台
      （“Order processing failed for customer cust-2”），验证日志-异常路径。
- [x] OTLP 后端不可达（本机无 4317 监听）时应用**未崩溃**，健康检查仍 200。

### 需在目标环境验证（本次无法访问后端，未执行）

- [ ] 启动 OTLP collector / Jaeger / Aspire dashboard，设置 `OTEL_EXPORTER_OTLP_ENDPOINT`，
      确认 traces、metrics、logs 三信号均到达。
- [ ] 确认 HTTP 自动 span 含正确 verb / URL / 状态码。
- [ ] 确认 `/healthz` 被过滤、不产生 span。
- [ ] 确认日志条目带 TraceId / SpanId，可与 trace 关联。
- [ ] 确认自定义 span `ProcessOrder` / `ValidateOrder` / `ProcessPayment` 出现在后端，
      且错误 span 带异常状态。
- [ ] 确认指标 `orders.processed`、`orders.processing_duration`、`orders.active` 可按 `region` 维度查询。
- [ ] 若 collector 仅收 HTTP/protobuf，设置 `OtlpExportProtocol.HttpProtobuf` 并验证端口 4318。

## 六、仍待确认项

1. **既有项目代码**：本次未提供，需确认真实项目的目标框架、入口模型（最小 API / Controller）、
   现有 DI 与目录结构，再平移配置。
2. **观测后端与端点**：OTLP collector 地址、协议（gRPC 4317 / HTTP 4318）、是否需要 header/鉴权，
   当前使用默认 `http://localhost:4317`。
3. **服务名 / 资源属性**：当前用 `builder.Environment.ApplicationName`，是否需补充
   `service.version`、`deployment.environment` 等资源属性待确认。
4. **自定义 Source / Meter 命名**：示例用 `MyApp.Orders`、`MyApp.Metrics`，需按真实业务域统一命名。
5. **高基数标签**：示例仅用 `region`、`order.type` 低基数标签；真实业务需审核，禁止 userId / requestId / UUID。
6. **出站调用方式**：示例支付为占位；真实出站 HTTP 应经 `IHttpClientFactory` 发起以获得自动 span 与传播。
7. **日志格式化消息**：`IncludeFormattedMessage` 默认关闭，若后端需要消息文本需显式开启（有性能/隐私影响）。
8. **SQL / EF / gRPC / Runtime 等可选 instrumentation**：需确认项目是否使用对应库后再决定是否添加。

## 七、实际读取的 Skill 文件

- `configuring-opentelemetry-dotnet/configuring-opentelemetry-dotnet/SKILL.md`
  （压缩包内唯一文件，已完整读取）

## 八、实际影响交付结果的 SKILL.md 规则（至少一条）

- **Step 1 “Install exactly these / Do NOT install `OpenTelemetry` alone / Console exporter do NOT include in production”**
  直接决定了 csproj 只出现 4 个直接包、版本 1.17.0、且未加 Console 或任何可选 instrumentation，
  这是本次依赖清单的唯一依据。
- **Step 4 “Prefer logging over activity.RecordException()”** 决定了 `OrderService` 异常路径使用
  `ILogger.LogError` 而非 `RecordException`。
- **Step 5 “Use IMeterFactory (injected via DI) to create meters” + Common Pitfalls 中
  “ActivitySource should be static; create Meter via IMeterFactory”** 决定了
  `OrderMetrics` 通过 DI 注入 `IMeterFactory`、`ActivitySource` 为静态字段。
- **Common Pitfalls “ActivitySource.StartActivity returns null — names must match exactly”**
  决定了代码注释与测试清单中对名称一致性的强调。
