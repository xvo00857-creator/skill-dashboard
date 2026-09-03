-- =============================================================================
-- 权限边界（数据库内 roles and privileges）
-- 依据：iam-security.md——对象访问使用“标准 PostgreSQL roles and privileges”
--       通过 GRANT/REVOKE 控制；连接优先 IAM 数据库认证与 alloydbiamuser 角色。
-- 原则：最小权限。应用读写分离，分析只读；不用超级用户跑业务。
-- =============================================================================

-- 1. 应用读写角色（订单服务）：可写订单/明细，可插入退款、更新退款状态 ----------
CREATE ROLE app_rw NOLOGIN;
GRANT USAGE ON SCHEMA public TO app_rw;
GRANT INSERT, SELECT, UPDATE ON orders, order_items TO app_rw;
GRANT INSERT, SELECT, UPDATE ON refunds TO app_rw;
-- 序列权限（IDENTITY 列底层序列）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_rw;

-- 2. 退款服务角色：仅能创建/推进退款，不能改订单金额 --------------------------
CREATE ROLE refund_svc NOLOGIN;
GRANT USAGE ON SCHEMA public TO refund_svc;
GRANT SELECT ON orders, order_items TO refund_svc;
GRANT INSERT, SELECT, UPDATE ON refunds TO refund_svc;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO refund_svc;
-- 显式禁止修改订单金额（列级回收）
REVOKE UPDATE(total_amount) ON orders FROM refund_svc;

-- 3. 分析只读角色：只能读分析视图，不能直接读基表 PII（如 customer_id） -------
CREATE ROLE analyst_ro NOLOGIN;
GRANT USAGE ON SCHEMA public TO analyst_ro;
GRANT SELECT ON v_daily_orders, v_daily_refunds,
             v_daily_refund_rate, v_refund_aging, v_monthly_summary TO analyst_ro;
REVOKE SELECT ON orders, order_items, refunds FROM analyst_ro;

-- 4. 函数执行权限 -------------------------------------------------------------
GRANT EXECUTE ON FUNCTION fn_refund_rate(date, date) TO analyst_ro, app_rw;

-- 5. 默认权限：未来新建表/视图自动按上述角色授权（避免遗漏） ------------------
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT INSERT, SELECT, UPDATE ON TABLES TO app_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO analyst_ro;
-- 未来新建表的 IDENTITY 序列自动授权（避免新表插入时报权限错误）
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_rw, refund_svc;

-- 6. IAM 数据库认证用户绑定（控制平面注册后，在库内授权） ---------------------
-- 注意（依据 iam-security.md 第85-88行）：IAM 数据库用户不能仅用标准 SQL 创建，
-- 必须先经控制平面（Console/gcloud/API）注册，再在库内 GRANT alloydbiamuser。
-- 下面的 SQL 仅在对应用户已通过 gcloud alloydb users create 注册后执行：
--
--   GRANT alloydbiamuser TO "app-sa@PROJECT_ID.iam.gserviceaccount.com";
--   GRANT app_rw     TO "app-sa@PROJECT_ID.iam.gserviceaccount.com";
--   GRANT analyst_ro TO "analyst@EXAMPLE.com";
