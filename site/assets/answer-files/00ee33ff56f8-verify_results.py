#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""独立交叉核对脚本：回读 Parquet 验证清洗结果的正确性。"""
import os
import dask.dataframe as dd
import pandas as pd
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_DIR = os.path.join(BASE_DIR, "output", "cleaned_parquet")

print("=" * 60)
print("独立交叉核对")
print("=" * 60)

# 1. 回读 Parquet（用 dask，不一次性加载到内存）
ddf = dd.read_parquet(PARQUET_DIR)
total = ddf.shape[0].compute()
print(f"\n[1] Parquet 回读行数: {total}")
assert total == 3_000_000, f"行数不符: {total}"
print("    ✓ 与去重后行数一致 (3,000,000)")

# 2. 验证门店名称全部归一化（无原始变体残留）
unique_stores = ddf["store_name"].unique().compute()
print(f"\n[2] 归一化后门店列表: {sorted(unique_stores)}")
expected = {"北京朝阳店", "上海浦东店", "广州天河店", "深圳南山店", "杭州西湖店"}
assert set(unique_stores) == expected, f"门店名未完全归一化: {set(unique_stores)}"
print("    ✓ 所有门店名已归一化为 5 个标准名")

# 3. 验证未把未知值补零：不可解析的行 amount 仍为 NaN
nan_amount = int(ddf["amount"].isna().sum().compute())
unresolvable = int(ddf["unresolvable_missing"].sum().compute())
print(f"\n[3] amount 为 NaN 的行数: {nan_amount}")
print(f"    标记为不可解析缺失的行数: {unresolvable}")
assert nan_amount == unresolvable, "NaN 行数与不可解析标记数不一致"
print("    ✓ 不可解析的缺失值保留为 NaN，未被补零")

# 4. 验证金额推导和校正逻辑
# 对于 quantity 和 unit_price 都存在的行，amount 应等于 quantity*unit_price
has_both = ~ddf["quantity"].isna() & ~ddf["unit_price"].isna()
check_df = ddf[has_both].copy()
check_df["recalc"] = (check_df["quantity"] * check_df["unit_price"]).round(2)
check_df["diff"] = (check_df["amount"] - check_df["recalc"]).abs()
max_diff = float(check_df["diff"].max().compute())
mismatch_after = int((check_df["diff"] > 0.02).sum().compute())
print(f"\n[4] 数量×单价可校验行数: {int(has_both.sum().compute())}")
print(f"    清洗后金额与数量×单价最大偏差: {max_diff}")
print(f"    清洗后仍不一致行数: {mismatch_after}")
assert mismatch_after == 0, f"仍有 {mismatch_after} 行金额不一致"
print("    ✓ 所有可校验行的金额均与数量×单价一致")

# 5. 验证无重复行
dup_check = int(ddf.groupby(list(ddf.columns)).size().compute().gt(1).sum())
# 用 order_id 检查更高效
oid_counts = ddf.groupby("order_id").size().compute()
dup_oids = int((oid_counts > 1).sum())
print(f"\n[5] order_id 重复数: {dup_oids}")
assert dup_oids == 0, "仍有重复 order_id"
print("    ✓ 无重复订单")

# 6. 验证异常报告数字
with open(os.path.join(BASE_DIR, "output", "anomaly_report.json"), encoding="utf-8") as f:
    report = json.load(f)
print(f"\n[6] 异常报告核对:")
print(f"    原始行数: {report['原始总行数']} (数据生成器预期 3,149,908)")
print(f"    重复行数: {report['精确重复行数']}")
print(f"    去重后行数: {report['去重后行数']}")
assert report["原始总行数"] - report["精确重复行数"] == report["去重后行数"]
print("    ✓ 原始行数 - 重复行数 = 去重后行数")

# 7. 抽样核对 Excel
xl = pd.ExcelFile(os.path.join(BASE_DIR, "output", "sampling_verification.xlsx"))
print(f"\n[7] 抽样核对工作簿包含 {len(xl.sheet_names)} 个 sheet:")
for sheet in xl.sheet_names:
    df_s = xl.parse(sheet)
    print(f"    - {sheet}: {len(df_s)} 行 × {len(df_s.columns)} 列")

print("\n" + "=" * 60)
print("全部核对通过 ✓")
print("=" * 60)
