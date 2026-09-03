-- =============================================================================
-- 验证脚本（AlloyDB for PostgreSQL / 标准 PostgreSQL）
-- 用法：通过 AlloyDB Auth Proxy 或语言连接器连库后，用 psql 执行本文件。
-- 本脚本分两部分：
--   A. 结构与约束静态检查（不依赖业务数据）
--   B. 口径冒烟测试（在事务内插入样例数据并 ROLLBACK，不产生持久数据）
-- =============================================================================

-- A. 结构与约束检查 ----------------------------------------------------------

-- A1. 表与分区是否就位（应列出 orders 主表及其分区、refunds 主表及其分区）
SELECT inhparent::regclass AS parent,
       inhrelid::regclass  AS partition
FROM   pg_inherits
WHERE  inhparent IN ('orders'::regclass, 'refunds'::regclass)
ORDER  BY parent, partition;

-- A2. 是否存在违反约束的行（正常应返回 0 行；上线后可定期巡检）
SELECT 'orders_total_amount_neg' AS check_name, count(*) FROM orders WHERE total_amount < 0
UNION ALL
SELECT 'items_qty_not_pos',       count(*) FROM order_items WHERE quantity <= 0
UNION ALL
SELECT 'refunds_amount_not_pos',  count(*) FROM refunds WHERE refund_amount <= 0;

-- A3. 退款金额是否超过对应订单金额（业务一致性巡检；正常应 0 行）
SELECT r.refund_id, r.order_id, r.refund_amount, o.total_amount
FROM   refunds r
JOIN   orders  o ON o.order_id = r.order_id
WHERE  r.refund_amount > o.total_amount;

-- A4. 视图可查询性（应各自返回 0 行或统计行，不报错）
SELECT count(*) FROM v_daily_refund_rate;
SELECT count(*) FROM v_refund_aging;
SELECT count(*) FROM v_monthly_summary;

-- A5. 权限边界自检：analyst_ro 不应拥有基表 SELECT（以下查询应返回 0 行）
SELECT table_name
FROM   information_schema.role_table_grants
WHERE  grantee = 'analyst_ro'
  AND  table_name IN ('orders','order_items','refunds')
  AND  privilege_type = 'SELECT';

-- B. 口径冒烟测试（事务内造数，结束回滚，不污染库） ---------------------------
BEGIN;

INSERT INTO orders (order_id, customer_id, status, total_amount, created_at)
OVERRIDING SYSTEM VALUE VALUES
  (1001, 1, 'completed', 100.00, timestamptz '2026-08-10 10:00:00+00'),
  (1002, 2, 'paid',      200.00, timestamptz '2026-08-10 11:00:00+00'),
  (1003, 1, 'cancelled',  50.00, timestamptz '2026-08-10 12:00:00+00');
-- order_items.created_at 必须落在其所属 orders 分区键范围内（2026-08）
INSERT INTO order_items (order_id, order_created_at, sku, quantity, unit_price, created_at) VALUES
  (1001, timestamptz '2026-08-10 10:00:00+00', 'SKU-A', 1, 100.00, timestamptz '2026-08-10 10:05:00+00'),
  (1002, timestamptz '2026-08-10 11:00:00+00', 'SKU-B', 2, 100.00, timestamptz '2026-08-10 11:05:00+00');
INSERT INTO refunds (order_id, order_created_at, status, refund_amount, reason, requested_at, created_at) VALUES
  (1001, timestamptz '2026-08-10 10:00:00+00', 'processed', 30.00, '质量问题',
   timestamptz '2026-08-10 15:00:00+00', timestamptz '2026-08-10 15:00:00+00');

-- 预期：GMV=300（100+200，cancelled 不计），退款=30，退款率=0.1
SELECT stat_date, order_cnt, gmv_amount, refund_cnt, refund_amount, refund_rate
FROM   v_daily_refund_rate
WHERE  stat_date = '2026-08-10';
-- 预期：order_cnt=2, gmv_amount=300.00, refund_cnt=1, refund_amount=30.00, refund_rate=0.100000

-- 函数口径应与视图一致
SELECT * FROM fn_refund_rate('2026-08-10','2026-08-10');
-- 预期：order_cnt=2, gmv_amount=300.00, refund_cnt=1, refund_amount=30.00, refund_rate=0.100000

ROLLBACK;  -- 撤销全部造数
-- =============================================================================
