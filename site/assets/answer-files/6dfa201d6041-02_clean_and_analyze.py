# -*- coding: utf-8 -*-
"""
门店订单数据清洗与分析管线（可扩展）

输入：data/store_orders_raw.csv
输出：
  output/anomaly_report.csv        异常统计
  output/result_by_store.csv       按标准门店汇总的结果表
  output/sample_verification.csv   抽样核对记录
  output/cleaned_store_orders.csv  清洗后明细（含标记列，不丢行）
  output/run_log.txt               运行日志

核心原则：
  - 缺失值不补零：amount/unit_price 缺失时标记并排除出金额汇总，单独统计
  - 重复行不静默删除：标记 is_duplicate，结果汇总时剔除并记录
  - 门店名称标准化：基于显式映射表，无法匹配的标记为"未识别"，不猜测
  - 所有处理步骤可复现、可追溯
"""

import os
import sys
import hashlib
from datetime import datetime

import pandas as pd

# ============================================================
# 配置
# ============================================================
INPUT_PATH = "data/store_orders_raw.csv"
OUTPUT_DIR = "output"

# 门店名称标准化映射表（可扩展：新增门店只需在此追加）
# key 为标准门店名，value 为该门店所有已知写法（含标准名本身）
STORE_MAPPING = {
    "星巴克-国贸店": ["星巴克-国贸店", "星巴克(国贸店)", "星巴克咖啡-国贸",
                       "Starbucks 国贸店", "星巴克 国贸"],
    "瑞幸咖啡-中关村店": ["瑞幸咖啡-中关村店", "瑞幸咖啡(中关村店)",
                          "luckin coffee 中关村", "瑞幸-中关村店"],
    "喜茶-人民广场店": ["喜茶-人民广场店", "喜茶(人民广场店)",
                        "HEYTEA 人民广场", "喜茶人民广场店"],
    "蜜雪冰城-西湖店": ["蜜雪冰城-西湖店", "蜜雪冰城(西湖店)", "蜜雪 西湖店", "MXBC 西湖"],
    "奈雪的茶-福田店": ["奈雪的茶-福田店", "奈雪的茶(福田店)", "奈雪 福田店", "奈雪茶 福田"],
    "茶百道-天河店": ["茶百道-天河店", "茶百道(天河店)", "茶百道 天河", "茶百道天河北路店"],
    "星巴克-陆家嘴店": ["星巴克-陆家嘴店", "星巴克(陆家嘴店)", "Starbucks 陆家嘴",
                        "星巴克咖啡-陆家嘴"],
    "瑞幸咖啡-滨江店": ["瑞幸咖啡-滨江店", "瑞幸(滨江店)", "luckin 滨江店", "瑞幸咖啡 滨江"],
}

# 抽样核对的种子与数量
SAMPLE_SEED = 42
SAMPLE_N = 20


def build_variant_lookup(mapping):
    """构造 变体写法 -> 标准门店名 的反查表"""
    lookup = {}
    for canonical, variants in mapping.items():
        for v in variants:
            lookup[v.strip()] = canonical
    return lookup


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_lines = []

    def log(msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line)
        log_lines.append(line)

    # --------------------------------------------------------
    # 0. 读取
    # --------------------------------------------------------
    log(f"读取文件: {INPUT_PATH}")
    log(f"文件 MD5: {file_md5(INPUT_PATH)}")
    df = pd.read_csv(INPUT_PATH, dtype=str, encoding="utf-8-sig")
    # 空字符串视为缺失
    df = df.replace({"": pd.NA})
    n_raw = len(df)
    log(f"原始行数: {n_raw}，列: {list(df.columns)}")

    # 数值列转换（不强制，无法转换的记为 NaN）
    df["quantity_num"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price_num"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["amount_num"] = pd.to_numeric(df["amount"], errors="coerce")

    # --------------------------------------------------------
    # 1. 缺失值统计（不补零）
    # --------------------------------------------------------
    log("步骤1: 缺失值统计")
    missing_counts = df.isna().sum()
    missing_report = pd.DataFrame({
        "列名": missing_counts.index,
        "缺失行数": missing_counts.values,
        "缺失率%": (missing_counts.values / n_raw * 100).round(2),
    })
    log("\n" + missing_report.to_string(index=False))

    # --------------------------------------------------------
    # 2. 重复订单检测
    # --------------------------------------------------------
    log("步骤2: 重复订单检测")
    # 2a. 完全重复行（所有业务列一致）
    business_cols = ["order_id", "store_name", "city", "product_category",
                     "product_name", "quantity", "unit_price", "amount",
                     "order_date", "payment_method", "member_id"]
    df["is_exact_dup"] = df.duplicated(subset=business_cols, keep="first")
    n_exact_dup = int(df["is_exact_dup"].sum())
    log(f"完全重复行数（保留首条，其余标记）: {n_exact_dup}")

    # 2b. 同 order_id 出现多次（含非完全重复）
    oid_counts = df.groupby("order_id").size()
    dup_oids = oid_counts[oid_counts > 1].index.tolist()
    n_dup_oid_rows = int(df["order_id"].isin(dup_oids).sum())
    log(f"重复 order_id 个数: {len(dup_oids)}，涉及行数: {n_dup_oid_rows}")

    # --------------------------------------------------------
    # 3. 门店名称标准化
    # --------------------------------------------------------
    log("步骤3: 门店名称标准化")
    lookup = build_variant_lookup(STORE_MAPPING)
    df["store_canonical"] = df["store_name"].str.strip().map(lookup)
    n_unmapped = int(df["store_canonical"].isna().sum())
    if n_unmapped > 0:
        unmapped_names = df.loc[df["store_canonical"].isna(), "store_name"].unique().tolist()
        log(f"未识别门店名称行数: {n_unmapped}，写法: {unmapped_names}")
        df["store_canonical"] = df["store_canonical"].fillna("未识别门店")
    else:
        log("所有门店名称均已匹配到标准名")

    # 名称变体统计
    variant_stats = (df.groupby(["store_canonical", "store_name"]).size()
                     .reset_index(name="行数").sort_values(["store_canonical", "行数"],
                                                           ascending=[True, False]))
    variant_stats.to_csv(f"{OUTPUT_DIR}/store_name_variants.csv", index=False, encoding="utf-8-sig")
    log(f"门店名称变体对照表已保存: {OUTPUT_DIR}/store_name_variants.csv")

    # --------------------------------------------------------
    # 4. 异常值检测
    # --------------------------------------------------------
    log("步骤4: 异常值检测")
    # 4a. 负数量
    df["flag_neg_qty"] = df["quantity_num"] < 0
    # 4b. 零金额（非缺失的 0）
    df["flag_zero_amount"] = (df["amount_num"].notna()) & (df["amount_num"] == 0)
    # 4c. 金额缺失（不补零）
    df["flag_missing_amount"] = df["amount_num"].isna()
    # 4d. 单价缺失
    df["flag_missing_price"] = df["unit_price_num"].isna()
    # 4e. 金额与 数量×单价 不一致（仅在三者均非空时校验）
    mask_check = (df["quantity_num"].notna() & df["unit_price_num"].notna()
                  & df["amount_num"].notna() & ~df["flag_zero_amount"])
    df["expected_amount"] = (df["quantity_num"] * df["unit_price_num"]).round(2)
    df["amount_diff"] = (df["amount_num"] - df["expected_amount"]).round(2)
    df["flag_amount_mismatch"] = False
    df.loc[mask_check & (df["amount_diff"].abs() > 0.01), "flag_amount_mismatch"] = True

    anomaly_items = [
        ("完全重复行", n_exact_dup),
        ("重复order_id涉及行", n_dup_oid_rows),
        ("未识别门店名称", n_unmapped),
        ("member_id缺失", int(missing_counts.get("member_id", 0))),
        ("amount缺失(不补零)", int(df["flag_missing_amount"].sum())),
        ("unit_price缺失", int(df["flag_missing_price"].sum())),
        ("负数量", int(df["flag_neg_qty"].sum())),
        ("零金额", int(df["flag_zero_amount"].sum())),
        ("金额与数量×单价不一致", int(df["flag_amount_mismatch"].sum())),
    ]
    anomaly_df = pd.DataFrame(anomaly_items, columns=["异常类型", "行数"])
    anomaly_df["占比%"] = (anomaly_df["行数"] / n_raw * 100).round(2)
    anomaly_df.to_csv(f"{OUTPUT_DIR}/anomaly_report.csv", index=False, encoding="utf-8-sig")
    log("\n" + anomaly_df.to_string(index=False))

    # --------------------------------------------------------
    # 5. 结果表：按标准门店汇总
    # --------------------------------------------------------
    log("步骤5: 按标准门店汇总")
    # 有效行：非完全重复、门店已识别、金额非缺失非零、数量非负
    df["valid_for_revenue"] = (~df["is_exact_dup"]
                               & (df["store_canonical"] != "未识别门店")
                               & df["amount_num"].notna()
                               & ~df["flag_zero_amount"]
                               & ~df["flag_neg_qty"])

    grp = df.groupby("store_canonical")
    result = grp.agg(
        **{
            "订单数(去重后)": ("is_exact_dup", lambda s: int((~s).sum())),
            "有效计费订单数": ("valid_for_revenue", lambda s: int(s.sum())),
            "有效销售额(元)": ("amount_num", lambda s: round(
                s[df.loc[s.index, "valid_for_revenue"]].sum(), 2)),
            "缺失金额行数": ("flag_missing_amount", lambda s: int(s.sum())),
            "零金额行数": ("flag_zero_amount", lambda s: int(s.sum())),
            "负数量行数": ("flag_neg_qty", lambda s: int(s.sum())),
            "重复行数": ("is_exact_dup", lambda s: int(s.sum())),
        }
    ).reset_index().rename(columns={"store_canonical": "标准门店名"})

    # 合计行
    total = pd.DataFrame([{
        "标准门店名": "合计",
        "订单数(去重后)": int((~df["is_exact_dup"]).sum()),
        "有效计费订单数": int(df["valid_for_revenue"].sum()),
        "有效销售额(元)": round(df.loc[df["valid_for_revenue"], "amount_num"].sum(), 2),
        "缺失金额行数": int(df["flag_missing_amount"].sum()),
        "零金额行数": int(df["flag_zero_amount"].sum()),
        "负数量行数": int(df["flag_neg_qty"].sum()),
        "重复行数": int(df["is_exact_dup"].sum()),
    }])
    result = pd.concat([result, total], ignore_index=True)
    result.to_csv(f"{OUTPUT_DIR}/result_by_store.csv", index=False, encoding="utf-8-sig")
    log("\n" + result.to_string(index=False))

    # --------------------------------------------------------
    # 6. 抽样核对记录
    # --------------------------------------------------------
    log("步骤6: 抽样核对")
    # 分层抽样：随机抽 10 条正常行 + 10 条有标记的异常行
    normal_pool = df[df["valid_for_revenue"]].sample(n=min(10, int(df["valid_for_revenue"].sum())),
                                                     random_state=SAMPLE_SEED)
    anomaly_pool = df[~df["valid_for_revenue"]].sample(n=min(10, int((~df["valid_for_revenue"]).sum())),
                                                       random_state=SAMPLE_SEED)
    sample = pd.concat([normal_pool, anomaly_pool])

    verify_rows = []
    for _, r in sample.iterrows():
        flags = []
        if r["is_exact_dup"]:
            flags.append("完全重复")
        if r["store_canonical"] == "未识别门店":
            flags.append("门店未识别")
        if r["flag_missing_amount"]:
            flags.append("金额缺失(未补零)")
        if r["flag_missing_price"]:
            flags.append("单价缺失")
        if r["flag_neg_qty"]:
            flags.append("负数量")
        if r["flag_zero_amount"]:
            flags.append("零金额")
        if r["flag_amount_mismatch"]:
            flags.append("金额不一致")
        if not flags:
            flags.append("正常")

        verify_rows.append({
            "order_id": r["order_id"],
            "原始门店名": r["store_name"],
            "标准门店名": r["store_canonical"],
            "商品": r["product_name"],
            "数量": r["quantity"],
            "单价": r["unit_price"],
            "原始金额": r["amount"],
            "数量×单价": r["expected_amount"] if pd.notna(r["expected_amount"]) else "",
            "金额差异": r["amount_diff"] if pd.notna(r["amount_diff"]) else "",
            "是否计入有效销售额": "是" if r["valid_for_revenue"] else "否",
            "核对标记": "；".join(flags),
        })
    verify_df = pd.DataFrame(verify_rows)
    verify_df.to_csv(f"{OUTPUT_DIR}/sample_verification.csv", index=False, encoding="utf-8-sig")
    log(f"抽样核对 {len(verify_df)} 条已保存")

    # --------------------------------------------------------
    # 7. 保存清洗后明细（保留全部行与标记列）
    # --------------------------------------------------------
    df.to_csv(f"{OUTPUT_DIR}/cleaned_store_orders.csv", index=False, encoding="utf-8-sig")
    log(f"清洗后明细已保存: {OUTPUT_DIR}/cleaned_store_orders.csv")

    # --------------------------------------------------------
    # 8. 运行日志
    # --------------------------------------------------------
    with open(f"{OUTPUT_DIR}/run_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    log("完成。")


if __name__ == "__main__":
    main()
