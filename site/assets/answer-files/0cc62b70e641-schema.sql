-- =============================================================================
-- 订单与退款数据模型（AlloyDB for PostgreSQL）
-- 数据库类型依据：SKILL.md 第15-16行——AlloyDB 为 PostgreSQL 兼容托管数据库，
-- 因此以下使用标准 PostgreSQL 语法（未使用 AlloyDB 专有扩展）。
-- 对象访问控制遵循“标准 PostgreSQL roles and privileges”（iam-security.md 第74行）。
-- =============================================================================

-- 0. 枚举类型 ----------------------------------------------------------------
CREATE TYPE order_status  AS ENUM ('pending','paid','shipped','completed','cancelled');
CREATE TYPE refund_status AS ENUM ('requested','approved','rejected','processed');

-- 1. 订单主表（按月范围分区，适合订单类时序大数据） ---------------------------
CREATE TABLE orders (
    order_id     bigint GENERATED ALWAYS AS IDENTITY,
    customer_id  bigint        NOT NULL,
    status       order_status  NOT NULL DEFAULT 'pending',
    total_amount numeric(12,2) NOT NULL,
    currency     char(3)       NOT NULL DEFAULT 'CNY',
    created_at   timestamptz   NOT NULL DEFAULT now(),
    updated_at   timestamptz   NOT NULL DEFAULT now(),
    CONSTRAINT pk_orders PRIMARY KEY (order_id, created_at),
    CONSTRAINT chk_orders_total_amount_nonneg CHECK (total_amount >= 0)
) PARTITION BY RANGE (created_at);

COMMENT ON TABLE  orders IS '订单主表，按 created_at 月分区';
COMMENT ON COLUMN orders.total_amount IS '订单应付总金额快照，单位元；非负约束 chk_orders_total_amount_nonneg';

-- 2. 订单明细表（普通表，外键引用分区表 orders，需带被引用表分区键） ----------
CREATE TABLE order_items (
    order_item_id  bigint GENERATED ALWAYS AS IDENTITY,
    order_id       bigint        NOT NULL,
    order_created_at timestamptz NOT NULL,   -- 冗余 orders.created_at，外键所需
    sku            varchar(64)   NOT NULL,
    quantity       integer       NOT NULL,
    unit_price     numeric(12,2) NOT NULL,
    created_at     timestamptz   NOT NULL DEFAULT now(),
    CONSTRAINT pk_order_items PRIMARY KEY (order_item_id),
    CONSTRAINT fk_items_order FOREIGN KEY (order_id, order_created_at)
        REFERENCES orders (order_id, created_at),
    CONSTRAINT chk_items_qty_pos   CHECK (quantity > 0),
    CONSTRAINT chk_items_price_nonneg CHECK (unit_price >= 0)
);

COMMENT ON TABLE order_items IS '订单明细；order_created_at 为外键冗余字段，应与 orders.created_at 一致';

-- 3. 退款表（按月范围分区） ---------------------------------------------------
CREATE TABLE refunds (
    refund_id     bigint GENERATED ALWAYS AS IDENTITY,
    order_id      bigint        NOT NULL,
    order_created_at timestamptz NOT NULL,  -- 冗余 orders.created_at，外键所需
    status        refund_status NOT NULL DEFAULT 'requested',
    refund_amount numeric(12,2) NOT NULL,
    reason        varchar(256),
    requested_at  timestamptz   NOT NULL DEFAULT now(),
    processed_at  timestamptz,
    created_at    timestamptz   NOT NULL DEFAULT now(),
    CONSTRAINT pk_refunds PRIMARY KEY (refund_id, created_at),
    CONSTRAINT fk_refunds_order FOREIGN KEY (order_id, order_created_at)
        REFERENCES orders (order_id, created_at),
    CONSTRAINT chk_refunds_amount_pos CHECK (refund_amount > 0),
    CONSTRAINT chk_refunds_processed_time CHECK (processed_at IS NULL OR processed_at >= requested_at)
) PARTITION BY RANGE (created_at);

COMMENT ON TABLE refunds IS '退款单，按 created_at 月分区；退款金额必须为正';

-- 4. 索引 ---------------------------------------------------------------------
CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at DESC);
CREATE INDEX idx_orders_status           ON orders (status);
CREATE INDEX idx_items_order             ON order_items (order_id);
CREATE INDEX idx_items_sku               ON order_items (sku);
CREATE INDEX idx_refunds_order           ON refunds (order_id);
CREATE INDEX idx_refunds_status_req      ON refunds (status, requested_at);

-- 5. updated_at 自动维护触发器 ------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_orders_updated
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 6. 示例分区（生产中应通过定时任务/pg_partman 预创建） -----------------------
CREATE TABLE orders_2026_08 PARTITION OF orders
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE orders_2026_09 PARTITION OF orders
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE orders_default PARTITION OF orders DEFAULT;

CREATE TABLE refunds_2026_08 PARTITION OF refunds
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE refunds_2026_09 PARTITION OF refunds
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE refunds_default PARTITION OF refunds DEFAULT;
