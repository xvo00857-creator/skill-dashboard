# -*- coding: utf-8 -*-
"""
生成合成演示数据 demo_data.xlsx（仅用于验证 group_by_analysis.py 可运行）
=====================================================================
【重要声明】本文件由脚本随机生成，是合成演示数据，不是真实业务数据。
随附 ZIP 包中仅含 SKILL.md，未提供任何真实数据文件；真实结果需在提供
真实 Excel 后运行 group_by_analysis.py --input <真实文件> 产出。

演示数据刻意包含题目所述数据质量问题：
  - 多 Sheet（订单明细 + 门店字典）
  - category 列模拟合并单元格（连续空值需 ffill）
  - 门店名称多种不一致写法
  - store_name 缺失、amount 缺失（不补零）
  - 完全重复行、同 order_id 但金额/门店不一致的冲突行
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RNG = np.random.default_rng(20260812)
N = 5000  # 数据量较大

# 标准门店与其多种写法
STORE_VARIANTS = {
    "北京朝阳店": ["北京朝阳店", "北京朝阳分店", "朝阳店（北京）"],
    "北京海淀店": ["北京海淀店", "海淀分店"],
    "上海浦东店": ["上海浦东店", "上海浦东分店", "浦东店(上海)"],
    "上海徐汇店": ["上海徐汇店", "徐汇分店"],
    "广州天河店": ["广州天河店", "广州天河分店", "天河店（广州）"],
    "深圳南山店": ["深圳南山店", "南山分店"],
    "成都锦江店": ["成都锦江店", "锦江分店"],
    "杭州西湖店": ["杭州西湖店", "西湖分店"],
}
# 未在映射表中的写法（将归 Others）
UNKNOWN_STORES = ["武汉光谷店", "南京新街口店", "西安钟楼店"]

CATEGORIES = ["电子产品", "家居日用", "食品饮料", "服饰鞋包", "美妆个护"]
start = datetime(2026, 7, 1)

rows = []
oid = 100000
for i in range(N):
    std_store = RNG.choice(list(STORE_VARIANTS.keys()))
    variant = RNG.choice(STORE_VARIANTS[std_store])
    # 5% 概率门店名缺失
    if RNG.random() < 0.05:
        variant = None
    # 3% 概率出现未识别门店写法
    elif RNG.random() < 0.03:
        variant = RNG.choice(UNKNOWN_STORES)

    # category 模拟合并单元格：每 8 行只在第 1 行填值，其余留空（需 ffill）
    cat = CATEGORIES[i % len(CATEGORIES)] if i % 8 == 0 else None

    amount = round(float(RNG.integers(20, 2000) + RNG.random()), 2)
    # 6% 概率金额缺失
    if RNG.random() < 0.06:
        amount = None

    d = start + timedelta(days=int(RNG.integers(0, 31)))
    rows.append({
        "order_id": f"OD{oid}",
        "store_name": variant,
        "category": cat,
        "amount": amount,
        "order_date": d.strftime("%Y-%m-%d"),
    })
    oid += 1

df = pd.DataFrame(rows)

# 注入完全重复行（复制 30 行）
dup_full = df.sample(30, random_state=1).copy()
df = pd.concat([df, dup_full], ignore_index=True)

# 注入同 order_id 冲突行：取 15 行，用相同 order_id 但金额/门店不同
conflict_src = df.sample(15, random_state=2).copy()
max_oid_num = int(df["order_id"].str[2:].astype(int).max())
for idx, (_, r) in enumerate(conflict_src.iterrows()):
    new_row = r.to_dict()
    new_row["order_id"] = r["order_id"]  # 相同 order_id
    if r["amount"] is not None:
        new_row["amount"] = round(float(r["amount"]) + 500, 2)  # 金额冲突
    new_row["store_name"] = RNG.choice(UNKNOWN_STORES)  # 门店也可能不同
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

# 门店字典 Sheet
store_dict = pd.DataFrame([
    {"标准门店名": k, "已知写法": "、".join(v)} for k, v in STORE_VARIANTS.items()
])

# 说明 Sheet
readme = pd.DataFrame({
    "说明": [
        "本文件为合成演示数据，非真实业务数据。",
        "ZIP 包中仅含 SKILL.md，未提供真实数据；请用真实 Excel 替换后重跑。",
        "数据包含：门店名不一致、门店名缺失、金额缺失、完全重复行、同ID冲突行、合并单元格。",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
})

out = "demo_data.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as w:
    df.to_excel(w, sheet_name="订单明细", index=False)
    store_dict.to_excel(w, sheet_name="门店字典", index=False)
    readme.to_excel(w, sheet_name="数据说明", index=False)

print(f"[OK] 已生成 {out}，订单明细共 {len(df)} 行（含注入的重复/冲突）")
print(f"     门店名缺失: {df['store_name'].isna().sum()} 行")
print(f"     金额缺失: {df['amount'].isna().sum()} 行")
