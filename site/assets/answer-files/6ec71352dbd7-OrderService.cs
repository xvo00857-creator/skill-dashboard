using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace OtelDemo.Api.Services;

// Step 4：为业务操作创建自定义 span。
// ActivitySource 名称必须与 Program.cs 中 .AddSource("MyApp.Orders") 完全一致，
// 否则 StartActivity 会静默返回 null（SKILL.md 标注的头号排障点）。
public class OrderService
{
    private static readonly ActivitySource ActivitySource = new("MyApp.Orders");
    private readonly ILogger<OrderService> _logger;

    public OrderService(ILogger<OrderService> logger) => _logger = logger;

    public async Task<Order> ProcessOrderAsync(CreateOrderRequest request)
    {
        // 开启一个新的 span。
        using var activity = ActivitySource.StartActivity("ProcessOrder");

        // 为 span 添加属性（tag）。
        activity?.SetTag("order.customer_id", request.CustomerId);
        activity?.SetTag("order.item_count", request.Items.Count);

        try
        {
            // 校验子 span。
            using (var validationActivity = ActivitySource.StartActivity("ValidateOrder"))
            {
                await ValidateOrderAsync(request);
                validationActivity?.SetTag("validation.result", "passed");
            }

            // 支付子 span：Client 表示出站调用。
            using (var paymentActivity = ActivitySource.StartActivity("ProcessPayment",
                ActivityKind.Client))
            {
                paymentActivity?.SetTag("payment.method", request.PaymentMethod);
                await ProcessPaymentAsync(request);
            }

            var order = new Order(Guid.NewGuid(), request.CustomerId, "Completed");

            activity?.SetTag("order.status", "completed");
            activity?.SetStatus(ActivityStatusCode.Ok);

            return order;
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            // 通过 ILogger 记录异常——OpenTelemetry 会以 trace 关联方式采集。
            // 优先用日志而非 activity.RecordException()：OTel 正弃用 span event 记录异常，
            // 转向基于日志的异常记录。
            _logger.LogError(ex, "Order processing failed for customer {CustomerId}", request.CustomerId);
            throw;
        }
    }

    private static Task ValidateOrderAsync(CreateOrderRequest request)
    {
        if (request.Items is null || request.Items.Count == 0)
        {
            throw new ArgumentException("Order must contain at least one item.", nameof(request));
        }
        return Task.CompletedTask;
    }

    private static Task ProcessPaymentAsync(CreateOrderRequest request)
    {
        // 示例：真实支付调用应通过 IHttpClientFactory 发起，
        // AddHttpClientInstrumentation 会自动创建出站 HTTP span 并传播上下文。
        if (string.IsNullOrWhiteSpace(request.PaymentMethod))
        {
            throw new InvalidOperationException("Payment method is required.");
        }
        return Task.CompletedTask;
    }
}
