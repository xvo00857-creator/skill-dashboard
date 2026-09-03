#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kpi_analysis.py
严格遵循 kpi-metric-analysis/SKILL.md（YAML name: large-file-kpi-analysis）的两步执行。

【重要边界声明】
- 本脚本核心计算（Step1 单位换算系数、容差、排序；Step2 输出优先级与单表 Excel）
  逐行对应 SKILL.md，未作改动。
- SKILL.md 第 8 行明确：读取/计数/Parquet 优化属于父工作流（parent workflow），
  不在本子 skill 职责内。本脚本中 load_and_merge / normalize_columns 两段标注为
  「前置适配层」，仅为让脚本能端到端运行而提供的最小实现，不属于 Skill 原生能力；
  其口径可独立调整，不影响 Step1/Step2 的核心结论。
- 不编造数据：若未通过 --input 提供真实数据文件，脚本直接退出，不产生任何结果表。
"""

import argparse
import os
import sys
import pandas as pd

# ============================================================
# 以下常量与计算逻辑严格对应 SKILL.md Step1，不得修改系数
# ============================================================
DENOMINATOR_FACTOR = 1e-6   # SKILL.md: den_converted = denominator * 1e-6
NUMERATOR_FACTOR = 1e3      # SKILL.md: num_converted = numerator * 1e3
PA_TO_MPA = 1e6             # SKILL.md: calc_result_mpa = calc_result_pa / 1e6
TOLERANCE = 1e-6            # SKILL.md: tolerance = 1e-6

# 列名映射：待数据接入后按真实表头填写；留 None 表示该组计算不启用。
# 单位一致性验证组（物理量）：
COL_NUMERATOR = None    # 例：'Mx (kN·m)'
COL_DENOMINATOR = None  # 例：'Wx (cm³)'
COL_TARGET = None       # 例：'sigma (MPa)'
# 核心业务指标排序组：
COL_GROUP = None        # 例：'开发区名称'
COL_METRIC = None       # 例：'实际到帐外资额'


# ------------------------------------------------------------
# 前置适配层（非 SKILL.md 原生，父工作流职责；最小实现）
# ------------------------------------------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """字段命名规范化：去首尾空白、全角括号/空格转半角。
    不做猜测性改名（避免把 A 列错配成 B 列）；真实列名映射通过上方常量显式指定。"""
    new_cols = []
    for c in df.columns:
        if isinstance(c, str):
            c = (c.strip()
                   .replace('（', '(').replace('）', ')')
                   .replace('　', '').replace(' ', ''))
        new_cols.append(c)
    df = df.copy()
    df.columns = new_cols
    return df


def load_and_merge(path: str) -> pd.DataFrame:
    """读取多工作表并纵向合并。
    SKILL.md 假设 data 已加载；此处为最小适配：
    - 每个 sheet 先规范化表头；
    - 仅在列集合一致时纵向拼接，列不一致时保留各 sheet 来源列 __sheet__，
      缺失列留空（NaN），不强行填充；
    - 空金额/空数值保持 NaN，不做 0 填充。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xlsx', '.xls'):
        sheets = pd.read_excel(path, sheet_name=None, engine='openpyxl')
    elif ext == '.csv':
        sheets = {'csv': pd.read_csv(path)}
    else:
        raise ValueError(f"不支持的文件类型: {ext}（SKILL.md 示例为 Excel）")

    frames = []
    for name, df in sheets.items():
        df = normalize_columns(df)
        df['__sheet__'] = name
        frames.append(df)
    merged = pd.concat(frames, ignore_index=True, sort=False)
    return merged


# ------------------------------------------------------------
# Step1：单位一致性验证 + 核心指标降序（严格对应 SKILL.md）
# ------------------------------------------------------------
def step1(data: pd.DataFrame):
    """返回 (result_df, data)。
    result_df 为排序结果；单位验证列写回 data（与 SKILL.md 一致）。"""
    col_numerator = COL_NUMERATOR
    col_denominator = COL_DENOMINATOR
    col_target = COL_TARGET

    # 1. 物理量/指标单位一致性验证与计算（保留公式结构，与 SKILL.md 一致）
    if col_numerator in data.columns and col_denominator in data.columns and col_target in data.columns:
        data['den_converted'] = data[col_denominator] * DENOMINATOR_FACTOR
        data['num_converted'] = data[col_numerator] * NUMERATOR_FACTOR
        data['calc_result_pa'] = data['num_converted'] / data['den_converted']
        data['calc_result_mpa'] = data['calc_result_pa'] / PA_TO_MPA

        # 容差验证
        data['is_valid'] = (data['calc_result_mpa'] - data[col_target]).abs() < TOLERANCE
        print("单位一致性验证通过率:", data['is_valid'].mean() * 100, "%")

    # 2. 提取关键指标并降序排列
    group_col = COL_GROUP
    metric_col = COL_METRIC

    result_df = pd.DataFrame()
    if group_col in data.columns and metric_col in data.columns:
        result_df = data[[group_col, metric_col]].copy()
        result_df = result_df.sort_values(metric_col, ascending=False).reset_index(drop=True)

    return result_df, data


# ------------------------------------------------------------
# Step2：整理结果、保存 Excel（严格对应 SKILL.md）
# ------------------------------------------------------------
def step2(result_df: pd.DataFrame, data: pd.DataFrame, output_path: str):
    # 确定最终输出的数据框（优先级与 SKILL.md 完全一致）
    if not result_df.empty:
        result_df_final = result_df
    elif 'calc_result_mpa' in data.columns:
        result_df_final = data[[COL_NUMERATOR, COL_DENOMINATOR, COL_TARGET,
                                'calc_result_mpa', 'is_valid']].copy()
        result_df_final.columns = ['分子指标', '分母指标', '目标比对值', '计算结果', '是否一致']
    else:
        result_df_final = data.head(100)  # 默认输出前100行作为示例

    # 保存为 Excel 文件
    result_df_final.to_excel(output_path, index=False, engine='openpyxl')
    print(f"分析结果已保存至: {output_path}")
    print(f"下载链接: [点击下载分析结果](./{output_path})")
    return result_df_final


def main():
    ap = argparse.ArgumentParser(description="KPI 单位一致性验证与排序（严格按 SKILL.md）")
    ap.add_argument('--input', '-i', required=True, help='待分析数据文件路径（xlsx/xls/csv）')
    ap.add_argument('--output', '-o', default='analysis_result.xlsx', help='输出 Excel 路径')
    args = ap.parse_args()

    data = load_and_merge(args.input)
    print(f"已读取数据: {len(data)} 行, {len(data.columns)} 列")
    print("列名:", list(data.columns))

    result_df, data = step1(data)
    final = step2(result_df, data, args.output)
    print(f"最终输出: {len(final)} 行, {len(final.columns)} 列")


if __name__ == '__main__':
    main()
