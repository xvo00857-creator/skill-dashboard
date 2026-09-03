#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cohort_analysis_pipeline.py
-------------------------------------------------
依据 cohort-analysis Skill（SKILL.md）五步流程编写的留存/分群分析模板。
本脚本不包含任何数据或结果；必须在提供真实数据文件后运行。

对应 SKILL.md 步骤：
  Step 1 读取与校验数据（第13-17行）
  Step 2 量化分析：留存率、参与度趋势、功能采用率、环比（第19-24行）
  Step 3 可视化：留存热力图、分群折线图、采用对比图（第26-31行）
  Step 4 识别模式与异常（第33-40行）
  Step 5 后续研究建议（第42-49行）

新增约束（本次评测）：
  - 只使用可追溯输入；每个数字注明来源表/字段或计算口径
  - 事实 / 假设 / 建议 三分开输出
  - 不编造数据、链接或已完成状态

使用方式：
  1) 将真实数据文件放入 ./data/ 目录（支持 csv/xlsx/json，可多表）
  2) 按下文“配置区”修改字段映射
  3) python3 cohort_analysis_pipeline.py
  4) 结果输出到 ./output/ 目录
"""

import os
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 无显示环境下输出静态图片
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
# 配置区：需根据真实数据的实际字段名修改
# ============================================================
DATA_DIR = Path("./data")          # 真实数据目录（当前不存在，需用户提供）
OUTPUT_DIR = Path("./output")      # 结果输出目录

# 字段映射 —— 任务要求含“日期、渠道、用户状态”的多表数据
FIELD_MAP = {
    "user_id":   "user_id",     # 用户唯一标识
    "date":      "event_date",  # 行为/记录日期
    "channel":   "channel",     # 渠道，如 organic / paid / referral
    "status":    "status",      # 用户状态，如 active / churned / new
    # 可选：cohort 标识若不存在，将用 user_id 首次出现月份自动生成
    "cohort":    None,
}

# 留存口径：以“首次出现月”为队列，观察后续第 N 月是否仍有记录
RETENTION_WINDOWS = [0, 1, 2, 3, 6]  # 月

# ============================================================
# Step 1：读取与校验
# ============================================================
def load_tables(data_dir: Path) -> dict:
    """读取目录下所有 csv/xlsx/json，返回 {表名: DataFrame}。"""
    if not data_dir.exists():
        raise FileNotFoundError(
            f"数据目录 {data_dir.resolve()} 不存在。"
            f"请提供含日期、渠道、用户状态的多表数据后再运行。"
        )
    tables = {}
    for p in sorted(data_dir.iterdir()):
        if p.suffix.lower() == ".csv":
            tables[p.stem] = pd.read_csv(p)
        elif p.suffix.lower() in (".xlsx", ".xls"):
            xls = pd.ExcelFile(p)
            for sheet in xls.sheet_names:
                tables[f"{p.stem}__{sheet}"] = pd.read_excel(p, sheet_name=sheet)
        elif p.suffix.lower() == ".json":
            tables[p.stem] = pd.read_json(p)
    if not tables:
        raise ValueError(f"{data_dir} 中未找到 csv/xlsx/json 数据文件。")
    return tables


def validate_and_clean(df: pd.DataFrame, fm: dict) -> pd.DataFrame:
    """校验结构、缺失值、日期解析；返回清洗后 DataFrame。"""
    required = ["user_id", "date", "channel", "status"]
    missing_cols = [c for c in required if fm[c] not in df.columns]
    if missing_cols:
        raise ValueError(f"缺少必要字段: {missing_cols}；现有字段: {list(df.columns)}")

    df = df.rename(columns={fm[c]: c for c in required if fm[c] in df.columns})
    before = len(df)

    # 日期解析（无法解析的记为缺失，后续剔除）
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # 渠道/状态规范化：去空格、小写
    df["channel"] = df["channel"].astype(str).str.strip().str.lower()
    df["status"] = df["status"].astype(str).str.strip().str.lower()
    # 剔除关键字段缺失
    df = df.dropna(subset=["user_id", "date"])
    after = len(df)

    print(f"  [清洗] 原始 {before} 行 -> 有效 {after} 行（剔除 {before-after} 行缺失/无效日期）")
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """按 user_id + date + channel + status 去重，保留首条。"""
    before = len(df)
    df = df.drop_duplicates(subset=["user_id", "date", "channel", "status"], keep="first")
    after = len(df)
    print(f"  [去重] {before} 行 -> {after} 行（移除 {before-after} 条重复）")
    return df

# ============================================================
# Step 2：量化分析
# ============================================================
def build_cohorts(df: pd.DataFrame) -> pd.DataFrame:
    """以每个 user_id 首次出现月为队列；计算相对月份。"""
    first_seen = df.groupby("user_id")["date"].min().rename("cohort_date")
    df = df.merge(first_seen, on="user_id", how="left")
    df["cohort_month"] = df["cohort_date"].dt.to_period("M")
    df["event_month"] = df["date"].dt.to_period("M")
    # 相对月份（以月为单位）
    df["periods_since_cohort"] = (
        (df["event_month"] - df["cohort_month"]).apply(lambda x: x.n if hasattr(x, "n") else x)
    )
    return df


def retention_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """留存矩阵：行=队列月，列=第N月，值=留存率。"""
    cohort_sizes = df.groupby("cohort_month")["user_id"].nunique()
    active = (
        df.groupby(["cohort_month", "periods_since_cohort"])["user_id"]
        .nunique()
        .reset_index()
    )
    pivot = active.pivot(index="cohort_month", columns="periods_since_cohort", values="user_id")
    retention = pivot.divide(cohort_sizes, axis=0)
    return retention, cohort_sizes


def channel_status_summary(df: pd.DataFrame) -> pd.DataFrame:
    """按渠道×状态分组：用户数、占比（口径：该渠道内去重用户数）。"""
    g = df.groupby(["channel", "status"])["user_id"].nunique().reset_index(name="users")
    channel_total = g.groupby("channel")["users"].transform("sum")
    g["share_in_channel"] = (g["users"] / channel_total).round(4)
    return g.sort_values(["channel", "users"], ascending=[True, False])

# ============================================================
# Step 3：可视化
# ============================================================
def plot_retention_heatmap(retention: pd.DataFrame, out: Path):
    plt.figure(figsize=(10, 6))
    sns.heatmap(retention, annot=True, fmt=".0%", cmap="YlGnBu",
                cbar_kws={"label": "留存率"})
    plt.title("队列留存热力图（口径：首次出现月为队列，第N月仍有记录的用户占比）")
    plt.xlabel("距队列月数")
    plt.ylabel("队列月")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_cohort_lines(retention: pd.DataFrame, out: Path):
    plt.figure(figsize=(10, 6))
    for cohort, row in retention.iterrows():
        plt.plot(row.index, row.values, marker="o", label=str(cohort))
    plt.title("各队列留存曲线")
    plt.xlabel("距队列月数")
    plt.ylabel("留存率")
    plt.legend(title="队列月", fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_channel_status(summary: pd.DataFrame, out: Path):
    pivot = summary.pivot(index="channel", columns="status", values="users").fillna(0)
    pivot.plot(kind="bar", stacked=True, figsize=(10, 6))
    plt.title("各渠道用户状态分布（口径：去重用户数）")
    plt.xlabel("渠道")
    plt.ylabel("去重用户数")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()

# ============================================================
# 主流程
# ============================================================
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("=== Step 1 读取与校验 ===")
    tables = load_tables(DATA_DIR)
    print(f"发现 {len(tables)} 张表: {list(tables.keys())}")

    # 合并多表（纵向拼接；若表结构不同，此处需按实际情况调整关联逻辑）
    cleaned = []
    for name, df in tables.items():
        print(f"-- 处理表: {name}（{len(df)} 行）")
        df = validate_and_clean(df, FIELD_MAP)
        df["source_table"] = name  # 保留来源，便于追溯
        cleaned.append(df)
    all_df = pd.concat(cleaned, ignore_index=True)
    all_df = deduplicate(all_df)

    # 数据质量摘要（事实，可追溯）
    quality = {
        "输入表数量": len(tables),
        "输入表清单": list(tables.keys()),
        "清洗去重后总行数": int(len(all_df)),
        "去重用户数": int(all_df["user_id"].nunique()),
        "日期范围": [str(all_df["date"].min().date()), str(all_df["date"].max().date())],
        "渠道取值": sorted(all_df["channel"].unique().tolist()),
        "状态取值": sorted(all_df["status"].unique().tolist()),
    }

    print("=== Step 2 量化分析 ===")
    all_df = build_cohorts(all_df)
    retention, sizes = retention_matrix(all_df)
    ch_summary = channel_status_summary(all_df)

    print("=== Step 3 可视化 ===")
    plot_retention_heatmap(retention, OUTPUT_DIR / "retention_heatmap.png")
    plot_cohort_lines(retention, OUTPUT_DIR / "retention_curves.png")
    plot_channel_status(ch_summary, OUTPUT_DIR / "channel_status.png")

    print("=== 写出明细 ===")
    retention.to_csv(OUTPUT_DIR / "retention_matrix.csv", encoding="utf-8-sig")
    sizes.to_csv(OUTPUT_DIR / "cohort_sizes.csv", encoding="utf-8-sig")
    ch_summary.to_csv(OUTPUT_DIR / "channel_status_summary.csv", index=False, encoding="utf-8-sig")
    with open(OUTPUT_DIR / "data_quality.json", "w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print("完成。结果在:", OUTPUT_DIR.resolve())
    print("注意：Step 4 模式识别与 Step 5 研究建议需基于真实输出数字撰写，")
    print("      且须区分事实/假设/建议，本模板不预生成结论。")


if __name__ == "__main__":
    main()
