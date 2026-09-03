# -*- coding: utf-8 -*-
"""
group-by-analysis Skill 主处理脚本
=================================
严格遵循 SKILL.md 四步流程：
  Step1 数据清洗与预处理（合并单元格 ffill / 正则清洗 / 分类映射）
  Step2 分组统计（count / sum / 占比 / 总计行）
  Step3 可视化柱状图（中文字体 / 数值标签 / 网格）
  Step4 openpyxl 生成带样式与条件格式的 Excel 报告

在 Skill 能力边界内，针对题目所述数据质量问题做如下落实：
  - 门店名称不一致 -> 正则清洗 + 分类映射（map_categories），未匹配归 Others
  - 缺失值        -> 不补零；金额缺失仅在 sum 中跳过、订单仍计入 count；
                     门店缺失单独成组「未知/缺失」，不丢弃不补零
  - 重复订单      -> 去重并记录数量与样例（SKILL.md 正文未含去重，属数据清洗扩展，已标注）

description 提及但正文未给代码的能力一并实现为可扩展步骤：
  - 多 Sheet 行数统计
  - 大文件 Parquet 转换预处理（pyarrow 可用时执行，否则降级跳过并提示）

用法：
  python3 group_by_analysis.py --input <file.xlsx> [--sheet 订单明细] \
      --group-col store_name --value-col amount --output-dir output
若不传 --input，则使用内置合成演示数据（见 make_demo_data.py）。
"""

import argparse
import os
import re
import sys
from datetime import datetime

import pandas as pd

# ----------------------------------------------------------------------
# 0. 通用配置
# ----------------------------------------------------------------------
UNKNOWN_GROUP = "未知/缺失"   # 缺失门店名的分组（不补零、不丢弃）
OTHERS_GROUP = "Others"       # SKILL.md map_categories 默认归宿：有值但未在映射表中

# 门店名称标准化映射表（key 为「正则清洗后」的名称）
# 实际使用时可替换为从数据库/字典表加载，此处为可扩展骨架
STORE_MAPPING = {
    "北京朝阳店": "北京朝阳店", "北京朝阳分店": "北京朝阳店", "朝阳店北京": "北京朝阳店",
    "北京海淀店": "北京海淀店", "海淀分店": "北京海淀店",
    "上海浦东店": "上海浦东店", "上海浦东分店": "上海浦东店", "浦东店上海": "上海浦东店",
    "上海徐汇店": "上海徐汇店", "徐汇分店": "上海徐汇店",
    "广州天河店": "广州天河店", "广州天河分店": "广州天河店", "天河店广州": "广州天河店",
    "深圳南山店": "深圳南山店", "南山分店": "深圳南山店",
    "成都锦江店": "成都锦江店", "锦江分店": "成都锦江店",
    "杭州西湖店": "杭州西湖店", "西湖分店": "杭州西湖店",
}


# ----------------------------------------------------------------------
# Step1 数据清洗与预处理
# ----------------------------------------------------------------------
def clean_text(text):
    """SKILL.md 原文：去标点并 strip；NaN 原样返回（不补零、不转空串）。"""
    if pd.isna(text):
        return text
    return re.sub(r'[^\w\s]', '', str(text)).strip()


def map_categories(value):
    """SKILL.md 分类映射骨架：命中映射表返回标准名，否则归 Others；
    缺失值（NaN/空串）单独归「未知/缺失」，不补零。"""
    if pd.isna(value) or str(value).strip() == "":
        return UNKNOWN_GROUP
    return STORE_MAPPING.get(str(value), OTHERS_GROUP)


def count_sheets(input_path):
    """多 Sheet 行数统计（description 能力）。"""
    xls = pd.ExcelFile(input_path)
    rows = {}
    for name in xls.sheet_names:
        df = pd.read_excel(input_path, sheet_name=name)
        rows[name] = len(df)
    return rows


def preprocess(df, group_col, value_col, ffill_col=None):
    """Step1：去完全重复 -> 合并单元格 ffill -> 正则清洗 -> 分类映射 -> 同ID去重。

    顺序说明：完全重复行必须在 ffill 之前判定，否则追加到末尾的重复行会因
    ffill 来源不同而变得「不完全相同」，导致漏判。
    返回: (clean_df, anomaly_stats_dict, sampling_records_df)
    """
    anomaly = {}
    n0 = len(df)
    anomaly["原始行数"] = n0

    # 1.0 先去完全重复行（SKILL.md 正文未含去重，属题目要求的扩展；在任何变换前判定）
    full_dup = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    # 1.1 合并单元格向前填充（SKILL.md Step1 第1点）
    if ffill_col and ffill_col in df.columns:
        before_na = int(df[ffill_col].isna().sum())
        df[ffill_col] = df[ffill_col].ffill()
        after_na = int(df[ffill_col].isna().sum())
        anomaly[f"合并单元格填充_{ffill_col}_填充空值数"] = before_na - after_na
        anomaly[f"合并单元格填充_{ffill_col}_剩余空值数"] = after_na

    # 1.2 正则清洗门店名称（SKILL.md Step1 第2点）
    df["_store_raw"] = df[group_col]
    df[group_col] = df[group_col].apply(clean_text)

    # 1.3 分类映射（SKILL.md Step1 第3点）——未匹配归 Others，缺失归「未知/缺失」
    df["group_tag"] = df[group_col].apply(map_categories)

    # 1.4 同 order_id 去重与冲突检测（扩展步骤）
    conflict_rows = 0
    conflict_samples = pd.DataFrame()
    if "order_id" in df.columns:
        oid_dup = int(df.duplicated(subset=["order_id"], keep=False).sum())
        nun = df.groupby("order_id")[[value_col, "group_tag"]].nunique(dropna=False)
        conflict_ids = nun[(nun[value_col] > 1) | (nun["group_tag"] > 1)].index.tolist()
        conflict_rows = int(df["order_id"].isin(conflict_ids).sum())
        if conflict_ids:
            conflict_samples = df[df["order_id"].isin(conflict_ids[:20])].copy()
        df = df.drop_duplicates(subset=["order_id"], keep="first").copy()
        anomaly["同order_id重复涉及行数(去完全重复后)"] = oid_dup
        anomaly["冲突订单行数(同ID金额/门店不一致)"] = conflict_rows
    anomaly["完全重复行数"] = full_dup
    anomaly["去重后行数"] = len(df)
    anomaly["净删除行数"] = n0 - len(df)

    # 1.5 异常采集：缺失值与未识别写法（在最终去重后统计，与分组结果口径一致；不补零）
    anomaly["门店名称缺失行数"] = int((df["group_tag"] == UNKNOWN_GROUP).sum())
    if value_col in df.columns:
        anomaly["金额缺失行数"] = int(df[value_col].isna().sum())
    else:
        anomaly["金额缺失行数"] = "值列不存在"
    others_mask = df["group_tag"] == OTHERS_GROUP
    others_raw = df.loc[others_mask, "_store_raw"].dropna().astype(str).unique().tolist()
    anomaly["未识别门店写法数"] = len(others_raw)
    anomaly["未识别门店写法样例"] = " | ".join(others_raw[:10])

    # 1.7 抽样核对记录：抽取各类异常样例，便于人工复核
    def _v(r, k):
        val = r.get(k, "")
        if pd.isna(val) or val == "":
            return "(空)"
        return val
    samples = []
    for tag, sub in [("缺失门店", df[df["group_tag"] == UNKNOWN_GROUP]),
                     ("未识别门店(Others)", df[df["group_tag"] == OTHERS_GROUP]),
                     ("金额缺失", df[df[value_col].isna() if value_col in df.columns else []])]:
        for _, r in sub.head(10).iterrows():
            samples.append({"核对类型": tag,
                            "order_id": _v(r, "order_id"),
                            "原始门店名": _v(r, "_store_raw"),
                            "清洗后门店名": _v(r, group_col),
                            "映射分组": _v(r, "group_tag"),
                            "金额": _v(r, value_col),
                            "日期": _v(r, "order_date")})
    if not conflict_samples.empty:
        for _, r in conflict_samples.head(10).iterrows():
            samples.append({"核对类型": "冲突订单",
                            "order_id": _v(r, "order_id"),
                            "原始门店名": _v(r, "_store_raw"),
                            "清洗后门店名": _v(r, group_col),
                            "映射分组": _v(r, "group_tag"),
                            "金额": _v(r, value_col),
                            "日期": _v(r, "order_date")})
    sampling_df = pd.DataFrame(samples)

    return df, anomaly, sampling_df


# ----------------------------------------------------------------------
# Step2 分组统计
# ----------------------------------------------------------------------
def group_summary(df, group_col="group_tag", value_col="amount"):
    """SKILL.md Step2：count / sum / 占比 / 总计行。

    注意：订单数用 size（含金额缺失订单，因为订单真实存在）；
    有金额订单数用 count（非空）；sum 对金额缺失自动跳过（skipna=True），
    不把未知补成零。三者一次 named agg 完成，避免多次 groupby 顺序错位。
    """
    summary = df.groupby(group_col, dropna=False).agg(
        订单数=(value_col, "size"),
        金额合计=(value_col, "sum"),
        有金额订单数=(value_col, "count"),
    ).reset_index()
    summary["缺失金额订单数"] = summary["订单数"] - summary["有金额订单数"]

    total_sum = summary["金额合计"].sum()
    summary["金额占比"] = (summary["金额合计"] / total_sum).map(
        lambda x: f"{x:.2%}" if pd.notna(x) else "0.00%")

    total_row = pd.DataFrame({
        group_col: ["Total"],
        "订单数": [summary["订单数"].sum()],
        "金额合计": [total_sum],
        "有金额订单数": [summary["有金额订单数"].sum()],
        "缺失金额订单数": [summary["缺失金额订单数"].sum()],
        "金额占比": ["100.00%"],
    })
    summary = summary.sort_values("金额合计", ascending=False, na_position="last")
    return pd.concat([summary, total_row], ignore_index=True)


# ----------------------------------------------------------------------
# Step3 可视化
# ----------------------------------------------------------------------
def draw_chart(summary_df, group_col, value_col, chart_path):
    """SKILL.md Step3：中文字体 / 蓝色柱 / 数值标签 / 横向网格。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # 选中文字体（Arial Unicode MS 为 macOS 上 matplotlib 可直接识别的 .ttf；
    #   STHeiti/PingFang 为 .ttc，部分 matplotlib 版本未索引，故作回退）
    candidates = ["Arial Unicode MS", "STHeiti", "PingFang SC", "Heiti SC",
                  "Hiragino Sans GB", "SimHei", "Microsoft YaHei",
                  "WenQuanYi Zen Hei", "DejaVu Sans"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates if c in available), "DejaVu Sans")
    plt.rcParams["font.sans-serif"] = [chosen]
    plt.rcParams["axes.unicode_minus"] = False

    plot_df = summary_df[summary_df[group_col] != "Total"].copy()
    plot_df["金额合计"] = plot_df["金额合计"].fillna(0)  # 仅绘图时把 NaN 显示为 0，不改原数据

    plt.figure(figsize=(11, 6), dpi=120)
    bars = plt.bar(plot_df[group_col], plot_df["金额合计"], color="#4472C4")
    for bar in bars:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., h,
                 f"{h:,.0f}", ha="center", va="bottom", fontsize=9)
    plt.title("各门店订单金额分布", fontsize=14)
    plt.xlabel("门店分组")
    plt.ylabel("金额合计")
    plt.xticks(rotation=30, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    return chosen


# ----------------------------------------------------------------------
# Step4 Excel 报告
# ----------------------------------------------------------------------
def build_excel(summary_df, anomaly, sampling_df, sheet_rows, output_path,
                group_col, parquet_path=None, demo_note=None):
    """SKILL.md Step4：openpyxl 带样式 + 最大值行绿色标记；多 Sheet 组织。"""
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    wb = Workbook()
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center")
    green = PatternFill(start_color="00B050", end_color="00B050", fill_type="solid")
    yellow = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    def write_df(ws, df, highlight_max_col=None):
        # 表头
        for c, col in enumerate(df.columns, 1):
            cell = ws.cell(1, c, col)
            cell.fill = header_fill; cell.font = header_font
            cell.alignment = center; cell.border = border
        # 数据
        max_val = None
        if highlight_max_col and highlight_max_col in df.columns:
            # 排除 Total 行后取最大值（SKILL.md 示例未排除 Total，会导致总和行被标绿）
            non_total = df[df[df.columns[0]] != "Total"]
            vals = pd.to_numeric(non_total[highlight_max_col], errors="coerce")
            max_val = vals.max()
        for r, row in enumerate(df.itertuples(index=False), 2):
            for c, val in enumerate(row, 1):
                cell = ws.cell(r, c, val if not pd.isna(val) else None)
                cell.border = border
                if highlight_max_col and max_val is not None and c == list(df.columns).index(highlight_max_col) + 1:
                    try:
                        if float(val) == float(max_val):
                            cell.fill = green
                    except (TypeError, ValueError):
                        pass
                if str(row[0]) == "Total":
                    cell.font = Font(bold=True)
        for col in ws.columns:
            letter = col[0].column_letter
            width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
            ws.column_dimensions[letter].width = min(max(width + 2, 10), 40)

    # Sheet1 结果表
    ws1 = wb.active
    ws1.title = "分组结果"
    write_df(ws1, summary_df, highlight_max_col="金额合计")

    # Sheet2 异常统计
    ws2 = wb.create_sheet("异常统计")
    ws2.cell(1, 1, "指标").fill = header_fill
    ws2.cell(1, 1).font = header_font; ws2.cell(1, 1).border = border
    ws2.cell(1, 2, "值").fill = header_fill
    ws2.cell(1, 2).font = header_font; ws2.cell(1, 2).border = border
    r = 2
    for k, v in anomaly.items():
        ws2.cell(r, 1, k).border = border
        c = ws2.cell(r, 2, str(v)); c.border = border
        if any(w in k for w in ["缺失", "重复", "冲突", "未识别", "删除"]):
            c.fill = yellow
        r += 1
    ws2.column_dimensions["A"].width = 38
    ws2.column_dimensions["B"].width = 60

    # Sheet3 抽样核对
    ws3 = wb.create_sheet("抽样核对")
    if sampling_df is not None and len(sampling_df):
        write_df(ws3, sampling_df)
    else:
        ws3.cell(1, 1, "无异常样例")

    # Sheet4 多Sheet行数
    ws4 = wb.create_sheet("Sheet行数")
    ws4.cell(1, 1, "Sheet名").fill = header_fill; ws4.cell(1, 1).font = header_font
    ws4.cell(1, 2, "行数").fill = header_fill; ws4.cell(1, 2).font = header_font
    for i, (name, n) in enumerate(sheet_rows.items(), 2):
        ws4.cell(i, 1, name); ws4.cell(i, 2, n)
    ws4.column_dimensions["A"].width = 24

    # Sheet5 运行说明
    ws5 = wb.create_sheet("运行说明")
    notes = [
        "group-by-analysis Skill 分析报告",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "处理流程（严格对应 SKILL.md 四步）:",
        "  Step1 合并单元格ffill -> 正则清洗 -> 分类映射(未匹配归Others)",
        "  Step2 分组 count/sum/占比/总计行",
        "  Step3 matplotlib 中文字体柱状图",
        "  Step4 openpyxl 带样式Excel(最大值行绿色标记)",
        "",
        "数据质量处理原则:",
        "  - 门店名称不一致: 正则清洗后按映射表标准化, 未识别归 Others",
        "  - 缺失值: 不补零; 金额缺失在sum中跳过、订单仍计入count; 门店缺失单列「未知/缺失」",
        "  - 重复订单: 完全重复行去重; 同order_id保留第一条; 冲突订单记入异常统计",
        "  - 去重为 SKILL.md 正文未含的扩展步骤, 已在异常统计中留痕",
    ]
    if parquet_path:
        notes.append(f"Parquet 预处理文件: {parquet_path}")
    if demo_note:
        notes.append("")
        notes.append(demo_note)
    for i, line in enumerate(notes, 1):
        ws5.cell(i, 1, line)
    ws5.column_dimensions["A"].width = 80

    wb.save(output_path)


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------
def run(input_path, group_col, value_col, output_dir, sheet_name=0, ffill_col=None):
    os.makedirs(output_dir, exist_ok=True)

    # 多 Sheet 行数统计
    sheet_rows = count_sheets(input_path)

    # 大文件 Parquet 预处理（description 能力；pyarrow 缺失则降级）
    parquet_path = None
    try:
        df_all = pd.read_excel(input_path, sheet_name=None)
        for idx, (name, df) in enumerate(df_all.items()):
            pq = os.path.join(output_dir, f"parquet_sheet{idx}.parquet")
            df.to_parquet(pq, index=False)
        parquet_path = os.path.join(output_dir, "parquet_sheet*.parquet")
    except Exception as e:
        print(f"[WARN] Parquet 预处理跳过: {e}")

    df = pd.read_excel(input_path, sheet_name=sheet_name)
    print(f"[INFO] 读取 Sheet「{sheet_name}」共 {len(df)} 行")

    # Step1
    df_clean, anomaly, sampling_df = preprocess(df, group_col, value_col, ffill_col=ffill_col)
    # Step2
    summary = group_summary(df_clean, "group_tag", value_col)
    # Step3
    chart_path = os.path.join(output_dir, "analysis_chart.png")
    font_used = draw_chart(summary, "group_tag", value_col, chart_path)
    # Step4
    report_path = os.path.join(output_dir, "analysis_report.xlsx")
    build_excel(summary, anomaly, sampling_df, sheet_rows, report_path,
                "group_tag", parquet_path=parquet_path)

    # 控制台输出
    print("\n===== 分组结果 =====")
    print(summary.to_string(index=False))
    print("\n===== 异常统计 =====")
    for k, v in anomaly.items():
        print(f"  {k}: {v}")
    print(f"\n[OK] 图表(字体={font_used}): {chart_path}")
    print(f"[OK] Excel 报告: {report_path}")
    return summary, anomaly, sampling_df, report_path, chart_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="输入 Excel 路径；不传则使用演示数据")
    ap.add_argument("--sheet", default=0, help="数据所在 Sheet 名或序号")
    ap.add_argument("--group-col", default="store_name")
    ap.add_argument("--value-col", default="amount")
    ap.add_argument("--ffill-col", default="category", help="需 ffill 的合并单元格列")
    ap.add_argument("--output-dir", default="output")
    args = ap.parse_args()

    if args.input is None:
        print("[INFO] 未指定 --input，使用合成演示数据 demo_data.xlsx")
        args.input = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_data.xlsx")
        if not os.path.exists(args.input):
            print("[ERROR] 未找到 demo_data.xlsx，请先运行 make_demo_data.py")
            sys.exit(1)
    run(args.input, args.group_col, args.value_col, args.output_dir,
        sheet_name=args.sheet, ffill_col=args.ffill_col)
