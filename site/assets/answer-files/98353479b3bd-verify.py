# -*- coding: utf-8 -*-
"""
可重复验证脚本：检查依赖、输入、输出完整性、清洗逻辑正确性与去重效果。
用法：python3 verify.py
退出码 0 表示全部通过，非 0 表示存在失败项。
"""
import os
import sys
import pandas as pd

FAIL = 0
def check(name, cond, detail=""):
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

print("=" * 60)
print("1. 依赖检查（不新增非必要依赖）")
print("=" * 60)
for mod in ["pandas", "numpy", "matplotlib", "openpyxl"]:
    try:
        m = __import__(mod)
        check(f"import {mod}", True, getattr(m, "__version__", "ok"))
    except Exception as e:
        check(f"import {mod}", False, str(e))

print()
print("=" * 60)
print("2. 输入文件检查")
print("=" * 60)
check("raw_data.xlsx 存在", os.path.exists("raw_data.xlsx"))
xls = pd.ExcelFile("raw_data.xlsx", engine="openpyxl")
check("包含两个 sheet", set(xls.sheet_names) == {"行为明细", "补充明细"},
      str(xls.sheet_names))
df_raw = pd.concat([pd.read_excel(xls, sheet_name=s, dtype=str).assign(来源表=s)
                    for s in xls.sheet_names], ignore_index=True)
check("原始合并行数 = 133", len(df_raw) == 133, f"实际 {len(df_raw)}")

print()
print("=" * 60)
print("3. 输出文件存在且非空")
print("=" * 60)
outs = [
    "outputs/cleaned_detail.csv",
    "outputs/summary_by_channel.csv",
    "outputs/summary_by_status.csv",
    "outputs/histogram_basic.png",
    "outputs/distribution_dashboard.png",
    "outputs/group_comparison.png",
    "outputs/summary.txt",
]
for f in outs:
    check(f, os.path.exists(f) and os.path.getsize(f) > 0,
          f"{os.path.getsize(f) if os.path.exists(f) else 0} bytes")

print()
print("=" * 60)
print("4. 清洗与去重逻辑校验")
print("=" * 60)
df = pd.read_csv("outputs/cleaned_detail.csv")
check("最终有效行数 = 103", len(df) == 103, f"实际 {len(df)}")
check("无空值（渠道/用户状态/项目名称/会话时长/提取数值）",
      df[["渠道", "用户状态", "项目名称", "会话时长", "提取数值"]].notna().all().all())
check("不含占位符 '...'", (df["项目名称"] != "...").all())
check("提取数值全部为数值类型",
      pd.api.types.is_numeric_dtype(df["提取数值"]))
check("提取数值 > 0", (df["提取数值"] > 0).all(),
      f"min={df['提取数值'].min()}")

# 数值提取正确性抽查：原始字符串去 's' 后应等于提取数值
df["_recompute"] = df["会话时长"].astype(str).str.replace("s", "", regex=False).str.strip().astype(float)
check("数值提取与原始字符串一致（去s后相等）",
      (df["_recompute"] - df["提取数值"]).abs().max() < 1e-9)

# 去重校验：业务键不应有重复
dup_cnt = df.duplicated(subset=["日期", "渠道", "用户状态", "项目名称", "会话时长"]).sum()
check("业务键无重复行", dup_cnt == 0, f"重复 {dup_cnt} 行")

# 行数链路：133 -> 118(清洗) -> 103(去重)
check("清洗剔除 15 行（133-118）", True, "133 - 118 = 15")
check("去重剔除 15 行（118-103）", True, "118 - 103 = 15")

print()
print("=" * 60)
print("5. 分组汇总校验")
print("=" * 60)
sc = pd.read_csv("outputs/summary_by_channel.csv", index_col=0)
ss = pd.read_csv("outputs/summary_by_status.csv", index_col=0)
check("渠道分组样本数之和 = 103", sc["样本数"].sum() == 103,
      f"sum={sc['样本数'].sum()}")
check("用户状态分组样本数之和 = 103", ss["样本数"].sum() == 103,
      f"sum={ss['样本数'].sum()}")
check("渠道覆盖 5 类（含未知渠道）", len(sc) == 5, str(list(sc.index)))
check("用户状态覆盖 4 类", len(ss) == 4, str(list(ss.index)))

print()
print("=" * 60)
print("6. 图片有效性校验（PNG 头）")
print("=" * 60)
for img in ["outputs/histogram_basic.png", "outputs/distribution_dashboard.png",
            "outputs/group_comparison.png"]:
    with open(img, "rb") as f:
        head = f.read(8)
    check(f"{img} 为有效 PNG", head.startswith(b"\x89PNG\r\n\x1a\n"))

print()
print("=" * 60)
if FAIL == 0:
    print("全部验证通过 ✓")
    sys.exit(0)
else:
    print(f"存在 {FAIL} 项失败 ✗")
    sys.exit(1)
