# -*- coding: utf-8 -*-
"""
生成多表模拟数据（明确标注为模拟数据，非真实业务数据）。
因随附 ZIP 中仅含 SKILL.md、未提供输入数据，本脚本用于演示 Skill 流程。
包含：两个 sheet、日期/渠道/用户状态/项目名称/带单位数值列，
      并故意混入重复行、空值、占位符"..."、非法数值、日期格式不一致等脏数据。
固定随机种子，可重复生成。
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta

rng = np.random.default_rng(42)

channels = ["自然流量", "付费广告", "社交媒体", "邮件营销"]
statuses = ["新用户", "活跃用户", "流失用户", "回流用户"]
items = ["首页浏览", "搜索功能", "详情页", "下单流程", "个人中心"]
unit = "s"

start = date(2026, 7, 1)
rows = []
for i in range(90):
    d = start + timedelta(days=int(rng.integers(0, 28)))
    ch = rng.choice(channels)
    st = rng.choice(statuses)
    it = rng.choice(items)
    # 会话时长：对数正态分布，单位 s
    dur = rng.lognormal(mean=4.2, sigma=0.7)
    dur = round(float(dur), 1)
    rows.append([d.isoformat(), ch, st, it, f"{dur}{unit}"])

df1 = pd.DataFrame(rows, columns=["日期", "渠道", "用户状态", "项目名称", "会话时长"])

# --- 注入脏数据 ---
# 1) 完全重复行（表内）
dup_rows = df1.sample(8, random_state=1).copy()
df1 = pd.concat([df1, dup_rows], ignore_index=True)

# 2) 关键字段空值
for idx in [3, 17, 40]:
    df1.loc[idx, "渠道"] = np.nan
for idx in [5, 22]:
    df1.loc[idx, "会话时长"] = np.nan
for idx in [11]:
    df1.loc[idx, "项目名称"] = np.nan

# 3) 占位符 "..."
for idx in [33, 55]:
    df1.loc[idx, "项目名称"] = "..."

# 4) 非法数值
bad_vals = ["未知", "N/A", "", "  ", "abc123s", "120秒"]  # 最后一个单位不一致
for i, idx in enumerate([66, 67, 68, 69, 70, 71]):
    df1.loc[idx, "会话时长"] = bad_vals[i]

# 5) 日期格式不一致
for idx in [8, 29, 50]:
    parts = df1.loc[idx, "日期"].split("-")
    df1.loc[idx, "日期"] = f"{parts[0]}/{int(parts[1])}/{int(parts[2])}"

# 6) 数值带前后空格
for idx in [14, 31]:
    df1.loc[idx, "会话时长"] = "  " + str(df1.loc[idx, "会话时长"]) + "  "

# --- 第二个 sheet：补充明细，部分与表1重复（跨表去重），部分新增 ---
extra_rows = []
for i in range(25):
    d = start + timedelta(days=int(rng.integers(0, 28)))
    ch = rng.choice(channels)
    st = rng.choice(statuses)
    it = rng.choice(items)
    dur = round(float(rng.lognormal(mean=4.0, sigma=0.8)), 1)
    extra_rows.append([d.isoformat(), ch, st, it, f"{dur}{unit}"])
df2_new = pd.DataFrame(extra_rows, columns=df1.columns)
# 从表1取 10 行作为跨表重复
df2_dup = df1.dropna(subset=["渠道", "会话时长"]).sample(10, random_state=3)
df2 = pd.concat([df2_new, df2_dup], ignore_index=True)
# 表2也混入少量脏数据
df2.loc[0, "会话时长"] = "无效"
df2.loc[1, "项目名称"] = "..."
df2.loc[2, "渠道"] = np.nan

out = "raw_data.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as w:
    df1.to_excel(w, sheet_name="行为明细", index=False)
    df2.to_excel(w, sheet_name="补充明细", index=False)

print(f"已生成模拟数据文件: {out}")
print(f"  行为明细: {len(df1)} 行")
print(f"  补充明细: {len(df2)} 行")
print(f"  列: {list(df1.columns)}")
print(f"  数值列单位: {unit}")
print("注意：本数据为程序生成的模拟数据，非真实业务数据。")
