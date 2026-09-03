#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dask 门店订单数据清洗与分析管道
================================
严格遵循 dask Skill (SKILL.md) 规则：
  1. 使用 dd.read_csv() 直接读取多文件，不先用 pandas 全量加载
  2. 使用 map_partitions 进行分区级清洗（非逐行 apply）
  3. 惰性求值，所有聚合结果通过一次 dask.compute() 批量计算
  4. 清洗后的数据用 persist() 驻留以供多次聚合复用
  5. 指定合理 blocksize 控制分区大小
  6. map_partitions 指定 meta 以避免类型推断开销

数据问题处理原则：
  - 门店名称不一致：规则归一化 + 变体映射表
  - 缺失值：不随意补零；可推导的（数量×单价=金额）才推导，不可推导的保留 NaN 并标记
  - 重复订单：全行精确去重，记录去重数量
  - 金额不一致：以数量×单价为基准校正，记录校正明细
"""
import os
import json
import dask
import dask.dataframe as dd
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# ============================================================
# 配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_GLOB = os.path.join(BASE_DIR, "raw_data", "orders_2025_*.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
PARQUET_DIR = os.path.join(OUTPUT_DIR, "cleaned_parquet")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 门店名称归一化映射（从数据中发现的变体 → 标准名）
# 实际生产中此表可由数据探查自动生成，这里用规则+映射表
STORE_NORMALIZATION = {
    # 北京朝阳店 变体
    "北京朝阳店": "北京朝阳店", "北京市朝阳店": "北京朝阳店",
    "北京朝阳门店": "北京朝阳店", "北京 朝阳店": "北京朝阳店",
    "朝阳店(北京)": "北京朝阳店",
    # 上海浦东店 变体
    "上海浦东店": "上海浦东店", "上海市浦东店": "上海浦东店",
    "上海浦东分店": "上海浦东店", "上海 浦东店": "上海浦东店",
    "浦东店(上海)": "上海浦东店",
    # 广州天河店 变体
    "广州天河店": "广州天河店", "广州市天河店": "广州天河店",
    "广州天河门店": "广州天河店", "广州 天河店": "广州天河店",
    "天河店(广州)": "广州天河店",
    # 深圳南山店 变体
    "深圳南山店": "深圳南山店", "深圳市南山店": "深圳南山店",
    "深圳南山分店": "深圳南山店", "深圳 南山店": "深圳南山店",
    "南山店(深圳)": "深圳南山店",
    # 杭州西湖店 变体
    "杭州西湖店": "杭州西湖店", "杭州市西湖店": "杭州西湖店",
    "杭州西湖门店": "杭州西湖店", "杭州 西湖店": "杭州西湖店",
    "西湖店(杭州)": "杭州西湖店",
}

# 金额容差（元）
AMOUNT_TOLERANCE = 0.02


# ============================================================
# 分区级清洗函数（通过 map_partitions 并行执行）
# ============================================================
def clean_partition(pdf: pd.DataFrame) -> pd.DataFrame:
    """对单个 pandas DataFrame 分区执行清洗，返回带标记列的 DataFrame。"""
    df = pdf.copy()

    # --- 1. 门店名称归一化 ---
    df["store_raw"] = df["store_name"].astype(str).str.strip()
    df["store_name"] = df["store_raw"].map(STORE_NORMALIZATION).fillna(df["store_raw"])
    # 未能映射的标记为"未知门店"（不丢弃，保留以便人工核查）
    unmapped = ~df["store_raw"].isin(STORE_NORMALIZATION.keys())
    df.loc[unmapped, "store_name"] = "未知门店"

    # --- 2. 会员号处理：NaN/空 视为非会员（合法空值，非异常） ---
    df["member_id"] = df["member_id"].fillna("").astype(str)
    df["is_member"] = df["member_id"].str.len() > 0

    # --- 3. 支付方式缺失：标记为"未知"（分类值，不是数值零） ---
    df["payment_was_missing"] = df["payment_method"].isna()
    df["payment_method"] = df["payment_method"].fillna("未知")

    # --- 4. 数值列缺失与金额校验 ---
    # 记录原始缺失状态
    df["qty_was_missing"] = df["quantity"].isna()
    df["price_was_missing"] = df["unit_price"].isna()
    df["amount_was_missing"] = df["amount"].isna()

    # 数量和单价存在时，计算期望金额
    has_both = df["quantity"].notna() & df["unit_price"].notna()
    df["expected_amount"] = np.nan
    df.loc[has_both, "expected_amount"] = (
        df.loc[has_both, "quantity"] * df.loc[has_both, "unit_price"]
    ).round(2)

    # 金额缺失但数量和单价都在 → 推导金额（可推导，不补零）
    can_derive = df["amount_was_missing"] & has_both
    df.loc[can_derive, "amount"] = df.loc[can_derive, "expected_amount"]
    df["amount_derived"] = can_derive

    # 金额不一致检测（数量和单价都在时）
    df["amount_mismatch"] = False
    mismatch_mask = (
        has_both & ~df["amount_was_missing"] &
        (df["amount"] - df["expected_amount"]).abs() > AMOUNT_TOLERANCE
    )
    df.loc[mismatch_mask, "amount_mismatch"] = True
    # 以数量×单价为准校正
    df["amount_original"] = df["amount"]
    df.loc[mismatch_mask, "amount"] = df.loc[mismatch_mask, "expected_amount"]

    # 不可解析的缺失：数量或单价缺失且金额也缺失 → 保留 NaN，不补零
    df["unresolvable_missing"] = (
        (df["quantity"].isna() | df["unit_price"].isna()) & df["amount"].isna()
    )

    # --- 5. 日期解析 ---
    df["order_datetime"] = pd.to_datetime(df["order_datetime"], errors="coerce")
    df["order_month"] = df["order_datetime"].dt.to_period("M").astype(str)

    # --- 6. 清理辅助列 ---
    df = df.drop(columns=["expected_amount"])

    return df


# 清洗后的 meta（供 map_partitions 类型推断）
CLEAN_META = pd.DataFrame({
    "order_id": pd.Series(dtype="object"),
    "order_datetime": pd.Series(dtype="datetime64[ns]"),
    "store_name": pd.Series(dtype="object"),
    "region": pd.Series(dtype="object"),
    "product_category": pd.Series(dtype="object"),
    "product_name": pd.Series(dtype="object"),
    "quantity": pd.Series(dtype="float64"),
    "unit_price": pd.Series(dtype="float64"),
    "amount": pd.Series(dtype="float64"),
    "payment_method": pd.Series(dtype="object"),
    "member_id": pd.Series(dtype="object"),
    "store_raw": pd.Series(dtype="object"),
    "is_member": pd.Series(dtype="bool"),
    "payment_was_missing": pd.Series(dtype="bool"),
    "qty_was_missing": pd.Series(dtype="bool"),
    "price_was_missing": pd.Series(dtype="bool"),
    "amount_was_missing": pd.Series(dtype="bool"),
    "amount_derived": pd.Series(dtype="bool"),
    "amount_mismatch": pd.Series(dtype="bool"),
    "amount_original": pd.Series(dtype="float64"),
    "unresolvable_missing": pd.Series(dtype="bool"),
    "order_month": pd.Series(dtype="object"),
})


def main():
    print("=" * 60)
    print("Dask 门店订单清洗分析管道")
    print("=" * 60)

    # ----------------------------------------------------------
    # 步骤 1：用 dask.dataframe 直接读取多文件（不先用 pandas 加载）
    # ----------------------------------------------------------
    print("\n[1] 读取原始 CSV（dd.read_csv，blocksize=16MB）...")
    ddf_raw = dd.read_csv(
        RAW_GLOB,
        blocksize="16MB",
        dtype={
            "order_id": "string",
            "store_name": "string",
            "region": "string",
            "product_category": "string",
            "product_name": "string",
            "quantity": "float64",   # 含空值，必须用 float（NaN 无法用 int64 表示）
            "unit_price": "float64",
            "amount": "float64",
            "payment_method": "string",
            "member_id": "string",
        },
    )
    npartitions = ddf_raw.npartitions
    print(f"    分区数: {npartitions}")

    # ----------------------------------------------------------
    # 步骤 2：分区级清洗（map_partitions，惰性）
    # ----------------------------------------------------------
    print("[2] 应用 map_partitions 清洗（门店归一化/缺失值/金额校验）...")
    ddf_clean = ddf_raw.map_partitions(clean_partition, meta=CLEAN_META)

    # ----------------------------------------------------------
    # 步骤 3：全行精确去重（跨分区，惰性）
    # ----------------------------------------------------------
    print("[3] 全行精确去重...")
    ddf_dedup = ddf_clean.drop_duplicates()

    # ----------------------------------------------------------
    # 步骤 4：persist 驻留清洗结果（后续多次聚合复用，避免重复计算）
    # ----------------------------------------------------------
    print("[4] persist 清洗后数据到内存...")
    ddf = ddf_dedup.persist()

    # ----------------------------------------------------------
    # 步骤 5：构建所有统计与聚合（全部惰性，最后一次 compute）
    # ----------------------------------------------------------
    print("[5] 构建统计与聚合任务图...")

    # 5a. 行数统计
    raw_count = ddf_raw.shape[0]
    clean_count = ddf.shape[0]

    # 5b. 门店变体映射（原始值 → 标准名）
    store_variants = (
        ddf_raw.assign(store_raw=ddf_raw["store_name"].str.strip())
        .groupby("store_raw")
        .agg(cnt=("order_id", "count"))
        .reset_index()
    )

    # 5c. 各列缺失统计（清洗前，基于原始数据）
    missing_stats = ddf_raw.count()
    raw_total = ddf_raw.shape[0]

    # 5d. 异常标记统计（清洗后）—— 各标量单独定义，统一传入 compute
    a_payment_missing = ddf["payment_was_missing"].sum()
    a_qty_missing = ddf["qty_was_missing"].sum()
    a_price_missing = ddf["price_was_missing"].sum()
    a_amount_missing_orig = ddf["amount_was_missing"].sum()
    a_amount_derived = ddf["amount_derived"].sum()
    a_amount_mismatch = ddf["amount_mismatch"].sum()
    a_unresolvable = ddf["unresolvable_missing"].sum()
    a_unmapped = (ddf["store_name"] == "未知门店").sum()

    # 5e. 按门店汇总
    by_store = (
        ddf.groupby("store_name")
        .agg(
            订单数=("order_id", "count"),
            总金额=("amount", "sum"),
            平均金额=("amount", "mean"),
            总数量=("quantity", "sum"),
            会员订单数=("is_member", "sum"),
        )
        .reset_index()
        .sort_values("总金额", ascending=False)
    )

    # 5f. 按品类汇总
    by_category = (
        ddf.groupby("product_category")
        .agg(
            订单数=("order_id", "count"),
            总金额=("amount", "sum"),
            平均金额=("amount", "mean"),
        )
        .reset_index()
        .sort_values("总金额", ascending=False)
    )

    # 5g. 按月汇总
    by_month = (
        ddf.groupby("order_month")
        .agg(
            订单数=("order_id", "count"),
            总金额=("amount", "sum"),
            平均金额=("amount", "mean"),
        )
        .reset_index()
        .sort_values("order_month")
    )

    # 5h. 按支付方式汇总
    by_payment = (
        ddf.groupby("payment_method")
        .agg(
            订单数=("order_id", "count"),
            总金额=("amount", "sum"),
        )
        .reset_index()
        .sort_values("订单数", ascending=False)
    )

    # 5i. 按区域汇总
    by_region = (
        ddf.groupby("region")
        .agg(
            订单数=("order_id", "count"),
            总金额=("amount", "sum"),
        )
        .reset_index()
        .sort_values("总金额", ascending=False)
    )

    # 5j. 抽样核对记录
    # 用 dask 直接 take 抽样（随机取分区内样本）
    def sample_partition(pdf, n=5):
        return pdf.sample(n=min(n, len(pdf)), random_state=42)

    sample_missing = ddf[
        ddf["amount_derived"] | ddf["unresolvable_missing"] | ddf["payment_was_missing"]
    ][["order_id", "store_name", "quantity", "unit_price", "amount",
       "payment_method", "amount_derived", "unresolvable_missing", "payment_was_missing"]]

    sample_mismatch = ddf[ddf["amount_mismatch"]][
        ["order_id", "store_name", "quantity", "unit_price", "amount_original", "amount"]
    ]

    sample_unmapped = ddf[ddf["store_name"] == "未知门店"][
        ["order_id", "store_raw", "store_name"]
    ]

    # 去重抽样：先在主 compute 中算出重复 order_id 列表（小结果），
    # 再用具体 ID 集合做小范围抽样（避免在 merge 结果上直接 .head() 触发规划器错误）
    dup_counts = (
        ddf_raw.groupby("order_id")
        .agg(cnt=("order_id", "count"))
        .reset_index()
    )
    dup_ids_lazy = dup_counts[dup_counts["cnt"] > 1][["order_id"]]

    # ----------------------------------------------------------
    # 步骤 6：一次 compute() 批量计算所有结果
    # ----------------------------------------------------------
    print("[6] 执行 dask.compute()（一次性计算所有结果）...")
    (
        raw_n, clean_n,
        store_var_df,
        missing_counts,
        v_pay_miss, v_qty_miss, v_price_miss, v_amt_miss_orig,
        v_amt_derived, v_amt_mismatch, v_unresolvable, v_unmapped,
        df_store, df_category, df_month, df_payment, df_region,
        df_sample_missing, df_sample_mismatch, df_sample_unmapped,
        df_dup_ids,
    ) = dask.compute(
        raw_count, clean_count,
        store_variants,
        missing_stats,
        a_payment_missing, a_qty_missing, a_price_missing, a_amount_missing_orig,
        a_amount_derived, a_amount_mismatch, a_unresolvable, a_unmapped,
        by_store, by_category, by_month, by_payment, by_region,
        sample_missing.map_partitions(sample_partition, n=3),
        sample_mismatch.map_partitions(sample_partition, n=3),
        sample_unmapped.map_partitions(sample_partition, n=3),
        dup_ids_lazy,
        scheduler="threads",
    )

    # 组装异常统计 Series
    anomaly_s = pd.Series({
        "payment_missing": v_pay_miss,
        "qty_missing": v_qty_miss,
        "price_missing": v_price_miss,
        "amount_missing_original": v_amt_miss_orig,
        "amount_derived": v_amt_derived,
        "amount_mismatch_corrected": v_amt_mismatch,
        "unresolvable_missing": v_unresolvable,
        "unmapped_store": v_unmapped,
    })

    # 抽样结果取前 30 条（pandas 层操作）
    df_sample_missing = df_sample_missing.head(30)
    df_sample_mismatch = df_sample_mismatch.head(30)
    df_sample_unmapped = df_sample_unmapped.head(20)

    # 用已算出的重复 ID 集合做小范围抽样（小结果，单独一次 compute）
    dup_id_set = set(df_dup_ids["order_id"].head(20).tolist())
    df_sample_dup = (
        ddf_raw[ddf_raw["order_id"].isin(dup_id_set)]
        [["order_id", "store_name", "amount"]]
        .compute()
        .head(40)
    )

    dup_count = raw_n - clean_n

    # ----------------------------------------------------------
    # 步骤 7：输出结果
    # ----------------------------------------------------------
    print("[7] 写出结果文件...")

    # 7a. 异常统计
    missing_report = {}
    for col in ddf_raw.columns:
        col_missing = raw_n - int(missing_counts[col])
        missing_report[col] = {
            "缺失数": int(col_missing),
            "缺失率": f"{col_missing / raw_n * 100:.2f}%",
        }

    anomaly_report = {
        "原始总行数": int(raw_n),
        "精确重复行数": int(dup_count),
        "重复率": f"{dup_count / raw_n * 100:.2f}%",
        "去重后行数": int(clean_n),
        "支付方式缺失(标记为未知)": int(anomaly_s["payment_missing"]),
        "数量缺失": int(anomaly_s["qty_missing"]),
        "单价缺失": int(anomaly_s["price_missing"]),
        "金额原始缺失": int(anomaly_s["amount_missing_original"]),
        "金额由数量×单价推导": int(anomaly_s["amount_derived"]),
        "金额不一致已校正": int(anomaly_s["amount_mismatch_corrected"]),
        "不可解析缺失(保留NaN未补零)": int(anomaly_s["unresolvable_missing"]),
        "未映射门店": int(anomaly_s["unmapped_store"]),
        "分区数": npartitions,
    }

    with open(os.path.join(OUTPUT_DIR, "anomaly_report.json"), "w", encoding="utf-8") as f:
        json.dump(anomaly_report, f, ensure_ascii=False, indent=2)

    # 7b. 门店变体映射
    store_var_df = store_var_df.copy()
    store_var_df["标准门店名"] = store_var_df["store_raw"].map(STORE_NORMALIZATION).fillna("未知门店")
    store_var_df = store_var_df.sort_values(["标准门店名", "store_raw"])
    store_var_df.to_csv(os.path.join(OUTPUT_DIR, "store_name_mapping.csv"),
                        index=False, encoding="utf-8-sig")

    # 7c. 各结果表
    df_store.to_csv(os.path.join(OUTPUT_DIR, "result_by_store.csv"),
                    index=False, encoding="utf-8-sig")
    df_category.to_csv(os.path.join(OUTPUT_DIR, "result_by_category.csv"),
                       index=False, encoding="utf-8-sig")
    df_month.to_csv(os.path.join(OUTPUT_DIR, "result_by_month.csv"),
                    index=False, encoding="utf-8-sig")
    df_payment.to_csv(os.path.join(OUTPUT_DIR, "result_by_payment.csv"),
                      index=False, encoding="utf-8-sig")
    df_region.to_csv(os.path.join(OUTPUT_DIR, "result_by_region.csv"),
                     index=False, encoding="utf-8-sig")

    # 7d. 抽样核对记录
    with pd.ExcelWriter(os.path.join(OUTPUT_DIR, "sampling_verification.xlsx"),
                        engine="openpyxl") as writer:
        df_sample_missing.to_excel(writer, sheet_name="缺失值处理抽样", index=False)
        df_sample_mismatch.to_excel(writer, sheet_name="金额校正抽样", index=False)
        df_sample_dup.to_excel(writer, sheet_name="重复订单抽样", index=False)
        if len(df_sample_unmapped) > 0:
            df_sample_unmapped.to_excel(writer, sheet_name="未映射门店抽样", index=False)
        store_var_df.to_excel(writer, sheet_name="门店名称映射", index=False)

    # 7e. 清洗后数据写 Parquet（列式、压缩、可并行回读）
    print("    写出清洗后 Parquet...")
    # 显式将 object 列转为 string，避免 pyarrow 类型推断失败
    obj_cols = [c for c in CLEAN_META.columns if CLEAN_META[c].dtype == object]
    for col in obj_cols:
        ddf[col] = ddf[col].astype("string[pyarrow]")
    ddf.to_parquet(PARQUET_DIR, write_index=False, overwrite=True)

    # ----------------------------------------------------------
    # 步骤 8：打印摘要
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("异常统计摘要")
    print("=" * 60)
    for k, v in anomaly_report.items():
        print(f"  {k}: {v}")

    print("\n各列缺失统计:")
    for col, info in missing_report.items():
        if info["缺失数"] > 0:
            print(f"  {col}: {info['缺失数']} ({info['缺失率']})")

    print("\n门店汇总（前5）:")
    print(df_store.head().to_string(index=False))

    print("\n品类汇总:")
    print(df_category.to_string(index=False))

    print("\n月度汇总:")
    print(df_month.to_string(index=False))

    print(f"\n结果文件已输出到: {OUTPUT_DIR}")
    print(f"清洗后 Parquet: {PARQUET_DIR}")


if __name__ == "__main__":
    main()
