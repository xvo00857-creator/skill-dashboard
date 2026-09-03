using OpenTelemetry;
using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using OtelDemo.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// 用于出站 HTTP 调用的生命周期管理；AddHttpClientInstrumentation 会自动为其传播 trace context。
builder.Services.AddHttpClient();

// 注册自定义指标（Step 5：通过 IMeterFactory 创建 Meter，保证生命周期与可测试性）。
builder.Services.AddSingleton<OrderMetrics>();
builder.Services.AddSingleton<OrderService>();

// Step 2：在一处配置 Traces / Metrics / Logs 三个信号，统一走 OTLP 导出。
builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource
        .AddService(serviceName: builder.Environment.ApplicationName))
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation(options =>
        {
            // 健康检查端点不进链路，避免噪声。
            options.Filter = httpContext =>
                !httpContext.Request.Path.StartsWithSegments("/healthz");
        })
        .AddHttpClientInstrumentation(options =>
        {
            options.RecordException = true;
        })
        // 自定义 ActivitySource 名称必须与代码中 new ActivitySource("...") 完全一致。
        .AddSource("MyApp.Orders"))
    .WithMetrics(metrics => metrics
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        // 自定义 Meter 名称必须与 meterFactory.Create("...") 完全一致。
        .AddMeter("MyApp.Metrics"))
    .WithLogging(
        configureBuilder: _ => { },
        configureOptions: options =>
        {
            options.IncludeScopes = true;
            // options.IncludeFormattedMessage = true;  // 如需导出格式化后的消息文本再开启
        })
    // 单一 OTLP 导出器同时导出 traces/metrics/logs。
    // 默认读取 OTEL_EXPORTER_OTLP_ENDPOINT（gRPC 默认 http://localhost:4317）。
    .UseOtlpExporter();

var app = builder.Build();

// 健康检查：被 AspNetCore instrumentation 的 Filter 排除，不产生 span。
app.MapGet("/healthz", () => Results.Ok(new { status = "healthy" }));

// 示例业务端点：触发自定义 span、自定义指标与日志-trace 关联。
app.MapPost("/orders", async (OrderService orderService, OrderMetrics orderMetrics, CreateOrderRequest request) =>
{
    var sw = System.Diagnostics.Stopwatch.StartNew();
    var order = await orderService.ProcessOrderAsync(request);
    sw.Stop();

    orderMetrics.RecordOrderProcessed(request.Region ?? "unknown", sw.Elapsed.TotalMilliseconds);
    return Results.Ok(order);
});

app.Run();

// 仅用于示例端点的请求/响应模型；真实项目中应放在既有 Models 目录以兼容既有结构。
public record CreateOrderRequest(string CustomerId, string PaymentMethod, string? Region, List<string> Items);
public record Order(Guid Id, string CustomerId, string Status);
