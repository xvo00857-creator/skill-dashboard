#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
invalid-data-cleaning Skill 执行脚本
严格遵循 SKILL.md 中的三步流程：
  Step1: 读取 Excel（所有工作表），按总行数判断是否转 Parquet，再读取数据
  Step2: 对目标文本列使用正则仅保留中文字符
  Step3: 保存清洗后的数据为 .xlsx 并生成本地下载链接

用法:
  python3 clean_data.py <输入Excel路径> [目标文本列名]

示例:
  python3 clean_data.py input_data.xlsx 备注
"""

import sys
import os
import re
import pandas as pd

# ============================================================
# 配置区
# ============================================================
# 行数阈值：超过此值时先转 Parquet 再读取（SKILL.md Step1 的判断条件）
# SKILL.md 未给出具体阈值数字，此处设为 100000 行作为"数据量过大"的判断标准
ROW_THRESHOLD = 100_000

# 默认目标文本列名（SKILL.md Step2 中的 target_column）
# 若命令行未指定，则使用此默认值
DEFAULT_TARGET_COL = "target_column"


def step1_read_excel(file_path: str, parquet_path: str = "temp_data.parquet") -> pd.DataFrame:
    """
    SKILL.md Step1:
      读取 Excel 文件所有工作表 → 合并 → 若总行数超过阈值则写 Parquet → 再读取。
    """
    print(f"[Step1] 正在读取 Excel: {file_path}")
    xls = pd.ExcelFile(file_path)
    print(f"[Step1] 发现工作表: {xls.sheet_names}")

    dfs = []
    for sheet in xls.sheet_names:
        df_sheet = pd.read_excel(xls, sheet_name=sheet)
        print(f"[Step1]   工作表 '{sheet}': {len(df_sheet)} 行, {len(df_sheet.columns)} 列")
        dfs.append(df_sheet)

    if not dfs:
        raise ValueError("Excel 文件中没有任何工作表数据")

    # 合并所有 sheet 数据（与 SKILL.md 一致，使用 concat + ignore_index）
    df_all = pd.concat(dfs, ignore_index=True)
    total_rows = len(df_all)
    print(f"[Step1] 合并后总行数: {total_rows}")

    # 根据总行数判断是否数据量过大
    if total_rows > ROW_THRESHOLD:
        print(f"[Step1] 总行数 {total_rows} > 阈值 {ROW_THRESHOLD}，转换为 Parquet 以提升读写效率")
        df_all.to_parquet(parquet_path, engine="pyarrow", index=False)
        print(f"[Step1] Parquet 已写入: {parquet_path}")
        df = pd.read_parquet(parquet_path)
        print(f"[Step1] 已从 Parquet 重新读取: {len(df)} 行")
    else:
        print(f"[Step1] 总行数 {total_rows} <= 阈值 {ROW_THRESHOLD}，直接使用内存数据，无需 Parquet")
        df = df_all

    return df


def step2_clean_chinese_text(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """
    SKILL.md Step2:
      对目标文本字段中的特殊字符（#、-、数字等）进行清洗，
      使用正则表达式仅保留中文字符（Unicode 范围 [一-鿿]）。
    """
    print(f"[Step2] 目标清洗列: '{target_col}'")

    if target_col not in df.columns:
        print(f"[Step2] 警告: 列 '{target_col}' 不存在于数据中，跳过文本清洗")
        print(f"[Step2] 可用列: {list(df.columns)}")
        return df

    # 定义清洗函数（与 SKILL.md 完全一致）
    def clean_chinese_text(text):
        if pd.isna(text):
            return text
        s = str(text)
        # 提取所有中文字符（Unicode 范围：[一-鿿]）
        chinese_chars = re.findall(r'[一-鿿]', s)
        cleaned = ''.join(chinese_chars)
        return cleaned if cleaned else ''

    # 记录清洗前的非空样本数
    non_null_before = df[target_col].notna().sum()
    print(f"[Step2] 清洗前非空值数: {non_null_before}")

    # 应用清洗函数
    df[target_col] = df[target_col].apply(clean_chinese_text)

    # 清洗后空字符串数（原本有内容但清洗后无中文字符的情况）
    empty_after = (df[target_col] == '').sum()
    print(f"[Step2] 清洗后变为空字符串的记录数: {empty_after}")
    print(f"[Step2] 文本清洗完成（仅保留中文字符，移除 #、-、数字及其他非中文字符）")

    return df


def step3_save_excel(df: pd.DataFrame, output_path: str = "cleaned_data.xlsx") -> str:
    """
    SKILL.md Step3:
      将清洗后的数据保存为 .xlsx 文件，并生成本地下载链接。
    """
    df.to_excel(output_path, index=False)
    abs_path = os.path.abspath(output_path)
    print(f"[Step3] 清洗后的数据已保存至: {abs_path}")
    print(f"[Step3] 下载链接: file://{abs_path}")
    return abs_path


def main():
    if len(sys.argv) < 2:
        print("用法: python3 clean_data.py <输入Excel路径> [目标文本列名]")
        print("示例: python3 clean_data.py input_data.xlsx 备注")
        sys.exit(1)

    file_path = sys.argv[1]
    target_col = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TARGET_COL

    if not os.path.exists(file_path):
        print(f"错误: 输入文件不存在: {file_path}")
        sys.exit(1)

    # 严格按 SKILL.md 三步执行
    df = step1_read_excel(file_path)
    df = step2_clean_chinese_text(df, target_col)
    output_path = step3_save_excel(df)

    print("\n===== 执行完成 =====")
    print(f"输出文件: {output_path}")


if __name__ == "__main__":
    main()
