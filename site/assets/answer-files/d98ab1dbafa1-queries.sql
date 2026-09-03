-- =============================================================================
-- 可复用查询：订单与退款分析（AlloyDB for PostgreSQL / 标准 PostgreSQL）
-- 设计目标：业务方可直接基于视图取数，避免重复写 JOIN 与口径不一致。
-- 金额口径：orders.total_amount 为订单应付金额快照；refunds.refund_amount 为退款金额。
-- 退款率口径：退款金额 / 已完成或已支付订单金额（见各视图定义注释）。
-- =============================================================================

-- 1. 每日成交与订单量（仅统计 paid/completed，排除 cancelled/pending） ---------
CREATE OR REPLACE VIEW v_daily_orders AS
SELECT date_trunc('day', created_at)::date  AS stat_date,
       count(*)                              AS order_cnt,
       count(DISTINCT customer_id)           AS paying_customer_cnt,
       sum(total_amount)                     AS gmv_amount
FROM   orders
WHERE  status IN ('paid','completed')
GROUP  BY date_trunc('day', created_at);

COMMENT ON VIEW v_daily_orders IS '每日成交：订单数、付费客户数、GMV；口径=paid+completed';

-- 2. 每日退款汇总 -------------------------------------------------------------
CREATE OR REPLACE VIEW v_daily_refunds AS
SELECT date_trunc('day', requested_at)::date AS stat_date,
       count(*)                               AS refund_cnt,
       sum(refund_amount)                     AS refund_amount,
       count(*) FILTER (WHERE status = 'processed') AS processed_cnt,
       sum(refund_amount) FILTER (WHERE status = 'processed') AS processed_amount
FROM   refunds
GROUP  BY date_trunc('day', requested_at);

COMMENT ON VIEW v_daily_refunds IS '每日退款申请：申请笔数/金额、已处理笔数/金额';

-- 3. 每日退款率（核心可复用口径） ---------------------------------------------
-- 退款率 = 当日申请退款金额 / 当日成交订单金额(paid+completed)
CREATE OR REPLACE VIEW v_daily_refund_rate AS
SELECT o.stat_date,
       o.order_cnt,
       o.gmv_amount,
       coalesce(r.refund_cnt, 0)        AS refund_cnt,
       coalesce(r.refund_amount, 0)     AS refund_amount,
       CASE WHEN o.gmv_amount > 0
            THEN round(coalesce(r.refund_amount, 0) / o.gmv_amount, 6)
            ELSE 0 END                   AS refund_rate
FROM   v_daily_orders o
LEFT   JOIN v_daily_refunds r ON r.stat_date = o.stat_date;

COMMENT ON VIEW v_daily_refund_rate IS '每日退款率=退款金额/GMV(paid+completed)；GMV 为 0 时记 0';

-- 4. 退款时效分桶（未结清退款的账龄，用于运营跟进） ---------------------------
CREATE OR REPLACE VIEW v_refund_aging AS
SELECT refund_id,
       order_id,
       status,
       refund_amount,
       requested_at,
       now() - requested_at AS age_interval,
       CASE
         WHEN now() - requested_at < interval '1 day'  THEN '0-1天'
         WHEN now() - requested_at < interval '3 days' THEN '1-3天'
         WHEN now() - requested_at < interval '7 days' THEN '3-7天'
         ELSE '7天以上'
       END AS age_bucket
FROM   refunds
WHERE  status IN ('requested','approved');  -- 尚未 processed/rejected

COMMENT ON VIEW v_refund_aging IS '未结清退款账龄分桶；now() 为执行时刻，结果随时间变化';

-- 5. 可复用函数：任意时间段退款率 ---------------------------------------------
CREATE OR REPLACE FUNCTION fn_refund_rate(
    p_start date,
    p_end   date
) RETURNS TABLE(
    order_cnt     bigint,
    gmv_amount    numeric,
    refund_cnt    bigint,
    refund_amount numeric,
    refund_rate   numeric
) LANGUAGE sql STABLE AS $$
    SELECT count(*) FILTER (WHERE o.stat_date IS NOT NULL),
           coalesce(sum(o.gmv_amount),0),
           count(r.*),
           coalesce(sum(r.refund_amount),0),
           CASE WHEN coalesce(sum(o.gmv_amount),0) > 0
                THEN round(coalesce(sum(r.refund_amount),0) / sum(o.gmv_amount), 6)
                ELSE 0 END
    FROM   v_daily_orders o
    FULL   JOIN v_daily_refunds r ON r.stat_date = o.stat_date
    WHERE  coalesce(o.stat_date, r.stat_date) BETWEEN p_start AND p_end;
$$;

COMMENT ON FUNCTION fn_refund_rate IS '区间退款率；用法 SELECT * FROM fn_refund_rate(''2026-08-01'',''2026-08-31'');';

-- 6. 月度汇总（基于日视图，口径一致） -----------------------------------------
CREATE OR REPLACE VIEW v_monthly_summary AS
SELECT date_trunc('month', stat_date)::date AS stat_month,
       sum(order_cnt)                        AS order_cnt,
       sum(gmv_amount)                       AS gmv_amount,
       sum(refund_cnt)                       AS refund_cnt,
       sum(refund_amount)                    AS refund_amount,
       CASE WHEN sum(gmv_amount) > 0
            THEN round(sum(refund_amount) / sum(gmv_amount), 6)
            ELSE 0 END                       AS refund_rate
FROM   v_daily_refund_rate
GROUP  BY date_trunc('month', stat_date);

COMMENT ON VIEW v_monthly_summary IS '月度汇总，复用 v_daily_refund_rate 口径';
