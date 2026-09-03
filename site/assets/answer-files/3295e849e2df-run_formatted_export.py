#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
formatted-export Skill 执行脚本
严格遵循 SKILL.md 两步：
  Step1 扫描所有 sheet，模糊匹配目标列，筛选空值/无效字符记录
  Step2 导出 Excel，整行标红

场景：源资料含多个工作表、字段命名不一致、部分金额为空。
目标列：金额类字段（通过模糊关键词匹配，见下方常量）。
"""

import sys
import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# ========== 清洗口径（可复核） ==========
# 第一级模糊匹配：列名（小写）包含以下任一关键词即认定为金额类目标列
PRIMARY_KEYWORDS = [
    '金额', 'amount', 'money', '费用', '支出', '收入',
    '价格', '价款', '合计', '总价', '单价', '报销', '成本'
]
# 第二级次级推断：列名同时包含以下成对关键词（如"费用额""价金"等不规范命名）
SECONDARY_PAIRS = [('费', '额'), ('价', '金'), ('收', '入'), ('支', '出')]

# 无效值判定（严格对应 SKILL.md 的 mask 逻辑）：
#   1) pandas 判定为空值 isna()
#   2) 转字符串去首尾空格后为空串 ''
#   3) 转字符串去首尾空格后为 'nan'（不区分大小写）
def is_invalid_value(val) -> bool:
    if pd.isna(val):
        return True
    s = str(val).strip()
    if s == '':
        return True
    if s.lower() == 'nan':
        return True
    return False


def find_target_column(columns):
    """按 SKILL.md 两级逻辑定位目标列，返回列名或 None。"""
    # 第一级
    for col in columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in PRIMARY_KEYWORDS):
            return col
    # 第二级（次级推断）
    for col in columns:
        col_str = str(col)
        for k1, k2 in SECONDARY_PAIRS:
            if k1 in col_str and k2 in col_str:
                return col
    return None


def run(source_path: str, output_path: str = "filtered_results_highlighted.xlsx"):
    if not os.path.exists(source_path):
        print(f"[错误] 源文件不存在: {source_path}")
        return 1

    print(f"[Step1] 读取源文件: {source_path}")
    all_sheets = pd.read_excel(source_path, sheet_name=None)
    print(f"        共 {len(all_sheets)} 个工作表: {list(all_sheets.keys())}")

    empty_target_rows = []
    stats = []  # (sheet, 命中列, 异常行数, 总行数)

    for sheet_name, sheet_df in all_sheets.items():
        target_col = find_target_column(sheet_df.columns)
        if target_col is None:
            print(f"  [{sheet_name}] 未匹配到金额类目标列，跳过")
            stats.append((sheet_name, None, 0, len(sheet_df)))
            continue

        # 严格对应 SKILL.md 的 mask
        mask = (
            sheet_df[target_col].isna()
            | (sheet_df[target_col].astype(str).str.strip() == '')
            | (sheet_df[target_col].astype(str).str.strip().str.lower() == 'nan')
        )
        empty_rows = sheet_df[mask].copy()
        print(f"  [{sheet_name}] 目标列='{target_col}'  异常 {len(empty_rows)}/{len(sheet_df)} 行")
        stats.append((sheet_name, target_col, len(empty_rows), len(sheet_df)))

        if len(empty_rows) > 0:
            empty_rows.insert(0, '来源Sheet', sheet_name)
            empty_target_rows.append(empty_rows)

    result_df = pd.concat(empty_target_rows, ignore_index=True) if empty_target_rows else pd.DataFrame()

    # ========== Step2 导出并整行标红 ==========
    if not result_df.empty:
        result_df.to_excel(output_path, index=False)
        wb = load_workbook(output_path)
        ws = wb.active
        red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
        for row in range(2, ws.max_row + 1):
            for col in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col).fill = red_fill
        wb.save(output_path)
        print(f"\n[Step2] 结果文件已保存: {output_path}")
        print(f"        异常记录总数: {len(result_df)}")
    else:
        print("\n[Step2] 未找到符合条件的记录，无需导出。")

    print("\n===== 各工作表复核统计 =====")
    for sheet_name, col, bad, total in stats:
        col_disp = col if col is not None else '(无匹配列)'
        print(f"  {sheet_name:<12} 命中列: {col_disp:<14} 异常: {bad}/{total}")
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 run_formatted_export.py <源Excel路径> [输出Excel路径]")
        print("示例: python3 run_formatted_export.py 源资料.xlsx filtered_results_highlighted.xlsx")
        sys.exit(0)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "filtered_results_highlighted.xlsx"
    sys.exit(run(src, out))
