# -*- coding: utf-8 -*-
"""
主分析脚本。
严格遵循 Skill (numeric-extraction-and-distribution-analysis) 的三步流程：
  Step1 从带单位字符串提取数值并清洗
  Step2 直方图 + 均值/中位数参考线
  Step3 2x2 综合分布面板（直方图/饼图/条形图/累积分布图），保存 300dpi
并完成变化任务新增要求：多表读取、去重、按渠道/用户状态分组对比、输出明细与汇总。

依赖仅使用 Skill 规定的 pandas / numpy / matplotlib（读 xlsx 用已安装的 openpyxl，
未新增任何非必要依赖）。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 无显示环境下保存图片
import matplotlib.pyplot as plt

# ============================================================
# 字体配置：Skill 写的是 ['SimHei', 'DejaVu Sans']，
# 但 macOS 无 SimHei，改用系统已装中文字体，避免中文乱码。
# 这是平台适配，不改变 Skill 逻辑，不引入新依赖。
# ============================================================
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Heiti TC", "Songti SC",
                                   "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 0. 变化任务新增：读取多表数据
# ============================================================
INPUT_FILE = "raw_data.xlsx"
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

xls = pd.ExcelFile(INPUT_FILE, engine="openpyxl")
print(f"[读取] 发现 sheet: {xls.sheet_names}")
frames = []
for sn in xls.sheet_names:
    tmp = pd.read_excel(xls, sheet_name=sn, dtype=str)
    tmp["来源表"] = sn
    frames.append(tmp)
df = pd.concat(frames, ignore_index=True)
print(f"[读取] 合并后原始行数: {len(df)}")

# 统一日期格式（变化任务新增：日期列规范化，便于后续按日期分组）
def norm_date(s):
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip().replace("/", "-")
    return pd.to_datetime(s, errors="coerce")

df["日期"] = df["日期"].apply(norm_date)

# ============================================================
# Step1（Skill 规定）：提取目标列，清理无效和空值，带单位字符串转数值
# ============================================================
item_col = "项目名称"
value_col = "会话时长"
numeric_col = "提取数值"
unit_str = "s"

def extract_numeric_value(val_str):
    """从带单位的字符串中提取数值（严格按 Skill 实现）"""
    if pd.isna(val_str):
        return None
    try:
        return float(str(val_str).replace(unit_str, "").strip())
    except ValueError:
        return None

n_before = len(df)
# 清理缺失值与异常占位符
df_clean = df.dropna(subset=[item_col, value_col]).copy()
df_clean = df_clean[df_clean[item_col] != "..."]
# 应用提取函数并过滤转换失败的行
df_clean[numeric_col] = df_clean[value_col].apply(extract_numeric_value)
df_clean = df_clean.dropna(subset=[numeric_col])
n_after_step1 = len(df_clean)
print(f"[Step1] 清洗前 {n_before} 行 -> 清洗后 {n_after_step1} 行 "
      f"(剔除空值/占位符/非法数值 {n_before - n_after_step1} 行)")

# ============================================================
# 变化任务新增：去重（表内 + 跨表）
# 业务键：日期 + 渠道 + 用户状态 + 项目名称 + 原始会话时长字符串
# ============================================================
dup_mask = df_clean.duplicated(subset=["日期", "渠道", "用户状态",
                                       "项目名称", value_col], keep="first")
n_dup = int(dup_mask.sum())
df_clean = df_clean[~dup_mask].copy()
print(f"[去重] 剔除完全重复行 {n_dup} 行，去重后 {len(df_clean)} 行")

# 渠道为空的行在去重后仍保留为“未知渠道”，不强行删除（避免丢失样本）
df_clean["渠道"] = df_clean["渠道"].fillna("未知渠道")

# 保存清洗后明细
detail_path = os.path.join(OUT_DIR, "cleaned_detail.csv")
df_clean.to_csv(detail_path, index=False, encoding="utf-8-sig")
print(f"[输出] 清洗明细: {detail_path} ({len(df_clean)} 行)")

# ============================================================
# Step2（Skill 规定）：基础分布直方图 + 均值/中位数参考线
# ============================================================
plt.figure(figsize=(12, 8))
plt.hist(df_clean[numeric_col], bins=10, alpha=0.7, color="skyblue", edgecolor="black")
mean_val = df_clean[numeric_col].mean()
median_val = df_clean[numeric_col].median()
plt.axvline(mean_val, color="red", linestyle="--", linewidth=2,
            label=f"平均值: {mean_val:.2f}")
plt.axvline(median_val, color="green", linestyle="--", linewidth=2,
            label=f"中位数: {median_val:.2f}")
plt.xlabel(f"{numeric_col}（{unit_str}）", fontsize=12)
plt.ylabel("频数", fontsize=12)
plt.title(f"{numeric_col}分布直方图", fontsize=14, fontweight="bold")
plt.legend()
plt.grid(True, alpha=0.3)
hist_path = os.path.join(OUT_DIR, "histogram_basic.png")
plt.savefig(hist_path, dpi=300, bbox_inches="tight")
plt.close()
print(f"[Step2] 直方图已保存: {hist_path}")

# ============================================================
# Step3（Skill 规定）：2x2 综合分析面板
# ============================================================
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# 1. 直方图
ax1.hist(df_clean[numeric_col], bins=8, alpha=0.7, color="lightblue",
         edgecolor="black", rwidth=0.8)
ax1.set_xlabel(f"{numeric_col}（{unit_str}）", fontsize=12)
ax1.set_ylabel("频数", fontsize=12)
ax1.set_title(f"{numeric_col}分布直方图", fontsize=14, fontweight="bold")
ax1.grid(True, alpha=0.3)

# 2. 饼图（基于 value_counts 统计占比）
val_counts = df_clean[numeric_col].value_counts().sort_index()
colors = plt.cm.Set3(np.linspace(0, 1, len(val_counts)))
ax2.pie(val_counts.values, labels=[f"{x}" for x in val_counts.index],
        autopct="%1.1f%%", colors=colors, startangle=90)
ax2.set_title(f"{numeric_col}占比分布", fontsize=14, fontweight="bold")

# 3. 条形图
val_counts.plot(kind="bar", ax=ax3, color="lightcoral", alpha=0.8)
ax3.set_xlabel(f"{numeric_col}（{unit_str}）", fontsize=12)
ax3.set_ylabel("数量", fontsize=12)
ax3.set_title(f"各{numeric_col}对应的数量", fontsize=14, fontweight="bold")
ax3.tick_params(axis="x", rotation=45)
ax3.grid(True, alpha=0.3)

# 4. 累积分布图
sorted_values = np.sort(df_clean[numeric_col])
cumulative_freq = np.arange(1, len(sorted_values) + 1) / len(sorted_values) * 100
ax4.plot(sorted_values, cumulative_freq, marker="o", linewidth=2,
         markersize=6, color="darkgreen")
ax4.set_xlabel(f"{numeric_col}（{unit_str}）", fontsize=12)
ax4.set_ylabel("累积百分比 (%)", fontsize=12)
ax4.set_title(f"{numeric_col}累积分布", fontsize=14, fontweight="bold")
ax4.grid(True, alpha=0.3)

plt.tight_layout()
dashboard_path = os.path.join(OUT_DIR, "distribution_dashboard.png")
plt.savefig(dashboard_path, dpi=300, bbox_inches="tight")
plt.close()
print(f"[Step3] 综合面板已保存: {dashboard_path}")

# ============================================================
# 变化任务新增：按渠道、用户状态分组对比 + 可视化
# ============================================================
def group_summary(col):
    g = df_clean.groupby(col)[numeric_col].agg(
        样本数="count", 均值="mean", 中位数="median",
        最小值="min", 最大值="max", 标准差="std"
    ).round(2).sort_values("样本数", ascending=False)
    return g

sum_channel = group_summary("渠道")
sum_status = group_summary("用户状态")
sum_channel.to_csv(os.path.join(OUT_DIR, "summary_by_channel.csv"), encoding="utf-8-sig")
sum_status.to_csv(os.path.join(OUT_DIR, "summary_by_status.csv"), encoding="utf-8-sig")
print("[分组] 按渠道汇总:")
print(sum_channel.to_string())
print("[分组] 按用户状态汇总:")
print(sum_status.to_string())

# 分组对比图：各渠道/状态的均值与中位数条形图
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
x = np.arange(len(sum_channel))
w = 0.38
ax1.bar(x - w/2, sum_channel["均值"], w, label="均值", color="#4C72B0")
ax1.bar(x + w/2, sum_channel["中位数"], w, label="中位数", color="#55A868")
ax1.set_xticks(x)
ax1.set_xticklabels(sum_channel.index, rotation=20)
ax1.set_ylabel(f"{numeric_col}（{unit_str}）")
ax1.set_title("各渠道会话时长：均值 vs 中位数", fontweight="bold")
ax1.legend()
ax1.grid(True, alpha=0.3, axis="y")

x2 = np.arange(len(sum_status))
ax2.bar(x2 - w/2, sum_status["均值"], w, label="均值", color="#4C72B0")
ax2.bar(x2 + w/2, sum_status["中位数"], w, label="中位数", color="#55A868")
ax2.set_xticks(x2)
ax2.set_xticklabels(sum_status.index, rotation=20)
ax2.set_ylabel(f"{numeric_col}（{unit_str}）")
ax2.set_title("各用户状态会话时长：均值 vs 中位数", fontweight="bold")
ax2.legend()
ax2.grid(True, alpha=0.3, axis="y")

plt.tight_layout()
group_path = os.path.join(OUT_DIR, "group_comparison.png")
plt.savefig(group_path, dpi=300, bbox_inches="tight")
plt.close()
print(f"[分组] 对比图已保存: {group_path}")

# ============================================================
# 摘要文本
# ============================================================
summary_lines = [
    "=== 数据清洗与分布分析摘要 ===",
    f"输入文件: {INPUT_FILE}（模拟数据，非真实业务数据）",
    f"原始合并行数: {n_before}",
    f"Step1 清洗后行数: {n_after_step1}（剔除空值/占位符/非法数值 {n_before - n_after_step1} 行）",
    f"去重剔除行数: {n_dup}",
    f"最终有效行数: {len(df_clean)}",
    f"数值列: {numeric_col}（单位 {unit_str}）",
    f"均值: {mean_val:.2f}  中位数: {median_val:.2f}",
    f"最小值: {df_clean[numeric_col].min():.2f}  最大值: {df_clean[numeric_col].max():.2f}",
    "",
    "--- 按渠道汇总 ---",
    sum_channel.to_string(),
    "",
    "--- 按用户状态汇总 ---",
    sum_status.to_string(),
    "",
    "输出文件:",
    f"  {detail_path}",
    f"  {os.path.join(OUT_DIR, 'summary_by_channel.csv')}",
    f"  {os.path.join(OUT_DIR, 'summary_by_status.csv')}",
    f"  {hist_path}",
    f"  {dashboard_path}",
    f"  {group_path}",
]
summary_path = os.path.join(OUT_DIR, "summary.txt")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("\n".join(summary_lines))
print(f"[输出] 摘要: {summary_path}")
print("\n".join(summary_lines))
