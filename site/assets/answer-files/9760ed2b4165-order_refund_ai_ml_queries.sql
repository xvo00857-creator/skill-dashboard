-- ============================================================================
-- 订单与退款数据：可复用查询与数据管理方案
-- 适用 Skill: bigquery-ai-ml
-- 说明：本文件中的 AI/ML 函数语法严格依据 Skill 参考文档编写。
--       普通建表 DDL 不属于该 Skill 范围（SKILL.md 明确排除），
--       以标准 BigQuery DDL 提供，标注为【非 Skill 能力】。
-- ============================================================================


-- ============================================================================
-- 第一部分：基础建表 DDL【非 Skill 能力 — SKILL.md 明确排除表管理】
-- 以下 DDL 为标准 BigQuery 语法，不来自 bigquery-ai-ml Skill。
-- 分区/聚簇设计依据 Google Cloud 官方成本优化最佳实践。
-- ============================================================================

-- 订单明细表
-- 分区键：order_date（按天分区，减少查询扫描量）
-- 聚簇键：region, channel, product_category（常用过滤维度）
CREATE TABLE IF NOT EXISTS `your-project.your_dataset.orders` (
  order_id          STRING      NOT NULL,
  customer_id       STRING      NOT NULL,
  order_date        TIMESTAMP   NOT NULL,
  product_id        STRING      NOT NULL,
  product_category  STRING,
  quantity          INT64,
  order_amount      NUMERIC,
  region            STRING,
  channel           STRING,
  order_status      STRING
)
PARTITION BY DATE(order_date)
CLUSTER BY region, channel, product_category
OPTIONS(
  description = '订单明细表，按 order_date 天分区',
  partition_expiration_days = NULL
);

-- 退款明细表
-- 分区键：refund_date（按天分区）
-- 聚簇键：region, channel, product_category
CREATE TABLE IF NOT EXISTS `your-project.your_dataset.refunds` (
  refund_id         STRING      NOT NULL,
  order_id          STRING      NOT NULL,
  refund_date       TIMESTAMP   NOT NULL,
  refund_amount     NUMERIC,
  refund_reason     STRING,
  refund_status     STRING,
  product_category  STRING,
  region            STRING,
  channel           STRING
)
PARTITION BY DATE(refund_date)
CLUSTER BY region, channel, product_category
OPTIONS(
  description = '退款明细表，按 refund_date 天分区'
);

-- 日汇总视图（供 AI.FORECAST / AI.DETECT_ANOMALIES 使用）
-- AI 函数要求输入为表或子查询，视图可直接作为 TABLE 传入
CREATE VIEW IF NOT EXISTS `your-project.your_dataset.v_daily_metrics` AS
SELECT
  DATE(o.order_date) AS metric_date,
  o.region,
  o.channel,
  COUNT(DISTINCT o.order_id) AS daily_order_count,
  SUM(o.order_amount) AS daily_order_amount,
  COUNT(DISTINCT r.refund_id) AS daily_refund_count,
  IFNULL(SUM(r.refund_amount), 0) AS daily_refund_amount,
  SAFE_DIVIDE(IFNULL(SUM(r.refund_amount), 0), SUM(o.order_amount)) AS daily_refund_rate
FROM `your-project.your_dataset.orders` o
LEFT JOIN `your-project.your_dataset.refunds` r
  ON o.order_id = r.order_id
WHERE o.order_status = 'completed'
GROUP BY metric_date, o.region, o.channel;


-- ============================================================================
-- 第二部分：远程模型创建（AI.GENERATE / AI.CLASSIFY 等需要）
-- 语法依据：references/remote_models.md
-- 可用端点：gemini-2.5-pro, gemini-2.5-flash
--           text-embedding-005, text-multilingual-embedding-002, gemini-embedding-001
-- ============================================================================

-- 创建 Gemini 远程模型（供 AI.GENERATE_TABLE / AI.GENERATE_EMBEDDING 使用）
-- 注意：AI.CLASSIFY 和 AI.GENERATE 通过 connection_id + endpoint 直接调用，
--       不引用此模型；但仍需先创建 Cloud Resource Connection。
-- 注意：需要先创建 Cloud Resource Connection 并授予服务账号 Vertex AI User 角色
-- 依据：references/remote_models.md
CREATE OR REPLACE MODEL `your-project.your_dataset.gemini_flash_model`
REMOTE WITH CONNECTION DEFAULT
OPTIONS(ENDPOINT = 'gemini-2.5-flash');


-- ============================================================================
-- 第三部分：可复用 AI/ML 查询
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 查询 1：订单量与退款金额预测（AI.FORECAST）
-- 依据：references/ai_forecast.md
-- 模型：TimesFM 2.0（内置预训练模型，无需训练）
-- 输入要求：至少 3 个数据点；data_col 为数值列，timestamp_col 为日期/时间列
-- ----------------------------------------------------------------------------
SELECT *
FROM AI.FORECAST(
  (
    SELECT
      metric_date,
      region,
      channel,
      daily_refund_amount
    FROM `your-project.your_dataset.v_daily_metrics`
    WHERE metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
  ),
  data_col => 'daily_refund_amount',
  timestamp_col => 'metric_date',
  id_cols => ['region', 'channel'],
  horizon => 30,
  confidence_level => 0.95,
  output_historical_time_series => TRUE
);

-- ----------------------------------------------------------------------------
-- 查询 2：退款异常检测（AI.DETECT_ANOMALIES）
-- 依据：references/ai_detect_anomalies.md
-- 模型：TimesFM 2.0（内置）
-- 用途：检测每日退款金额的异常波动（潜在欺诈或系统性问题）
-- 输入要求：historical_data 和 target_data 两个输入，至少 3 个数据点
-- ----------------------------------------------------------------------------
SELECT *
FROM AI.DETECT_ANOMALIES(
  -- 历史数据（训练上下文）：过去 180 天
  (
    SELECT
      metric_date,
      region,
      daily_refund_amount
    FROM `your-project.your_dataset.v_daily_metrics`
    WHERE metric_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 210 DAY)
                          AND DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  ),
  -- 目标数据（待检测）：最近 30 天
  (
    SELECT
      metric_date,
      region,
      daily_refund_amount
    FROM `your-project.your_dataset.v_daily_metrics`
    WHERE metric_date > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  ),
  data_col => 'daily_refund_amount',
  timestamp_col => 'metric_date',
  id_cols => ['region'],
  anomaly_prob_threshold => 0.95
);

-- ----------------------------------------------------------------------------
-- 查询 3：退款变动关键维度归因（AI.KEY_DRIVERS）
-- 依据：references/ai_key_drivers.md
-- 用途：识别哪些维度组合（地区/渠道/品类）导致了退款金额的变化
-- 输入要求：metric_col 为数值列；interest_label_col 为布尔列
--           dimension_cols 为 1-12 个维度列
-- ----------------------------------------------------------------------------
SELECT *
FROM AI.KEY_DRIVERS(
  (
    SELECT
      r.refund_amount,
      r.region,
      r.channel,
      r.product_category,
      -- 兴趣组：最近 30 天；参照组：之前 30 天
      (DATE(r.refund_date) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) AS is_recent
    FROM `your-project.your_dataset.refunds` r
    WHERE r.refund_status = 'completed'
      AND r.refund_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
  ),
  metric_col => 'refund_amount',
  dimension_cols => ['region', 'channel', 'product_category'],
  interest_label_col => 'is_recent',
  top_k => 10
);

-- ----------------------------------------------------------------------------
-- 查询 4：退款原因文本分类（AI.CLASSIFY）
-- 依据：references/ai_classify.md
-- 用途：将非结构化的退款原因文本自动归类
-- 注意：需要远程模型连接（connection_id），会产生 Vertex AI 调用费用
-- ----------------------------------------------------------------------------
SELECT
  refund_id,
  order_id,
  refund_reason,
  AI.CLASSIFY(
    refund_reason,
    categories => [
      ('quality_issue', '商品质量问题或损坏'),
      ('wrong_item', '发错货或商品与描述不符'),
      ('logistics', '物流延迟或包裹丢失'),
      ('customer_mind', '客户不想要了/尺码不合适'),
      ('fraud', '疑似欺诈或恶意退款'),
      ('other', '其他原因')
    ],
    connection_id => 'your-project.us.your-connection',
    endpoint => 'gemini-2.5-flash'
  ) AS refund_category
FROM `your-project.your_dataset.refunds`
WHERE refund_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND refund_reason IS NOT NULL
LIMIT 1000;

-- ----------------------------------------------------------------------------
-- 查询 5：退款模式摘要（AI.GENERATE）
-- 依据：references/ai_generate.md
-- 用途：用 LLM 生成退款数据的自然语言摘要
-- 注意：需要远程模型，会产生 Vertex AI 调用费用
-- ----------------------------------------------------------------------------
SELECT
  AI.GENERATE(
    CONCAT(
      '以下是最近7天的退款数据汇总，请用中文生成一段简明摘要，指出主要退款原因和异常：',
      TO_JSON_STRING(
        (
          SELECT AS STRUCT
            region,
            product_category,
            COUNT(*) AS refund_count,
            SUM(refund_amount) AS total_refund
          FROM `your-project.your_dataset.refunds`
          WHERE refund_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
          GROUP BY region, product_category
          ORDER BY total_refund DESC
          LIMIT 20
        )
      )
    ),
    connection_id => 'your-project.us.your-connection',
    endpoint => 'gemini-2.5-flash'
  ) AS refund_summary;

-- ----------------------------------------------------------------------------
-- 查询 6：预测准确度回测（AI.EVALUATE）
-- 依据：references/ai_evaluate.md
-- 用途：用历史数据回测 TimesFM 预测准确度，输出 MAE/MSE/RMSE/MAPE/sMAPE
-- 输入要求：history_data（用于预测的历史）和 actual_data（实际值）
-- ----------------------------------------------------------------------------
SELECT *
FROM AI.EVALUATE(
  -- 历史数据：用 180 天前到 60 天前的数据
  (
    SELECT
      metric_date,
      region,
      daily_refund_amount
    FROM `your-project.your_dataset.v_daily_metrics`
    WHERE metric_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 240 DAY)
                          AND DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
  ),
  -- 实际数据：最近 60 天（作为真值对比）
  (
    SELECT
      metric_date,
      region,
      daily_refund_amount
    FROM `your-project.your_dataset.v_daily_metrics`
    WHERE metric_date > DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
  ),
  data_col => 'daily_refund_amount',
  timestamp_col => 'metric_date',
  id_cols => ['region'],
  horizon => 30
);

-- ----------------------------------------------------------------------------
-- 查询 7：贡献分析模型（ML.CONTRIBUTION_ANALYSIS）
-- 依据：references/ml_contribution_analysis.md
-- 用途：AI.KEY_DRIVERS 的替代方案，需要创建持久化模型实体
-- 注意：CREATE MODEL 按 $312.50/TiB 计费（on-demand），显著高于普通查询
-- ----------------------------------------------------------------------------

-- 7a. 创建贡献分析模型
CREATE OR REPLACE MODEL `your-project.your_dataset.refund_contribution_model`
OPTIONS(
  MODEL_TYPE = 'CONTRIBUTION_ANALYSIS',
  CONTRIBUTION_METRIC = 'SUM(refund_amount)',
  IS_TEST_COL = 'is_recent',
  DIMENSION_ID_COLS = ['region', 'channel', 'product_category'],
  TOP_K_INSIGHTS_BY_APRIORI_SUPPORT = 10
) AS
SELECT
  region,
  channel,
  product_category,
  refund_amount,
  (DATE(refund_date) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) AS is_recent
FROM `your-project.your_dataset.refunds`
WHERE refund_status = 'completed'
  AND refund_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY);

-- 7b. 查询洞察结果
SELECT *
FROM ML.GET_INSIGHTS(MODEL `your-project.your_dataset.refund_contribution_model`)
ORDER BY unexpected_difference DESC;


-- ============================================================================
-- 第四部分：成本控制查询
-- ============================================================================

-- 查询作业历史中的扫描字节量（用于估算成本）
-- 依据：BigQuery 标准 INFORMATION_SCHEMA 视图（非 AI/ML 函数）
SELECT
  job_id,
  creation_time,
  total_bytes_processed,
  ROUND(total_bytes_processed / POW(1024, 4), 4) AS tib_processed,
  ROUND(total_bytes_processed / POW(1024, 4) * 6.25, 4) AS estimated_cost_usd
FROM `your-project.region.INFORMATION_SCHEMA.JOBS`
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND job_type = 'QUERY'
ORDER BY total_bytes_processed DESC
LIMIT 50;

-- 使用最大字节限制防止意外高成本查询
-- 语法：BigQuery 标准查询参数（非 AI/ML 函数）
-- 设置后，超过限制的查询将直接失败而不产生费用
-- 示例：通过 bq 命令行或 API 设置 maximum_bytes_billed
-- bq query --maximum_bytes_billed=1000000000 "SELECT ..."
