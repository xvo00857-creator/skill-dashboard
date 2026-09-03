using System.Diagnostics;
using System.Diagnostics.Metrics;

namespace OtelDemo.Api.Services;

// Step 5：创建自定义指标。
// 通过 DI 注入的 IMeterFactory 创建 Meter，保证生命周期管理与可测试性；
// Meter 名称必须与 Program.cs 中 .AddMeter("MyApp.Metrics") 完全一致。
public class OrderMetrics
{
    private readonly Counter<long> _ordersProcessed;
    private readonly Histogram<double> _orderProcessingDuration;
    private readonly UpDownCounter<int> _activeOrders;

    public OrderMetrics(IMeterFactory meterFactory)
    {
        var meter = meterFactory.Create("MyApp.Metrics");

        // Counter：只增不减。
        _ordersProcessed = meter.CreateCounter<long>(
            "orders.processed", "orders", "Total orders successfully processed");

        // Histogram：测量分布（延迟、大小）。
        _orderProcessingDuration = meter.CreateHistogram<double>(
            "orders.processing_duration", "ms", "Time to process an order");

        // UpDownCounter：可增可减。
        _activeOrders = meter.CreateUpDownCounter<int>(
            "orders.active", "orders", "Currently processing orders");
    }

    public void RecordOrderProcessed(string region, double durationMs)
    {
        // 标签支持维度过滤；注意不要用 userId/requestId/UUID 等高基数值作为标签，
        // 否则会撑爆指标存储（见 SKILL.md Common Pitfalls）。
        var tags = new TagList
        {
            { "region", region },
            { "order.type", "standard" }
        };

        _ordersProcessed.Add(1, tags);
        _orderProcessingDuration.Record(durationMs, tags);
    }
}
