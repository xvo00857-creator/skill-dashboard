# -*- coding: utf-8 -*-
"""
dummy-dataset 技能交付物：门店订单模拟数据生成脚本
遵循 SKILL.md 的 "Template: Python Script Output" 结构。

用途：生成一份带真实数据质量问题的门店订单模拟数据集，用于测试清洗与分析流程。
数据为人工模拟（dummy），不代表任何真实业务。

数据质量问题（可控注入，固定随机种子保证可复现）：
  1. 门店名称不一致：同一门店存在多种写法
  2. 缺失值：member_id（非会员，业务上允许缺失）、amount、unit_price（异常缺失）
  3. 重复订单：完全重复行
  4. 异常值：负数量、零金额
"""

import csv
import random
from datetime import datetime, timedelta

# ============================================================
# Configuration（对应 SKILL.md 模板中的 Configuration 段）
# ============================================================
ROWS = 8000                     # 基础行数（重复行在此之外追加）
FILENAME = "data/store_orders_raw.csv"
RANDOM_SEED = 20260812
START_DATE = datetime(2026, 5, 1)
END_DATE = datetime(2026, 7, 31)

# ============================================================
# Column definitions with realistic value generators
# （对应 SKILL.md 模板中的 columns 定义）
# ============================================================

# 8 家标准门店，每家门店配若干"脏写法"
STORE_VARIANTS = {
    "星巴克-国贸店": ["星巴克(国贸店)", "星巴克咖啡-国贸", "Starbucks 国贸店", "星巴克 国贸"],
    "瑞幸咖啡-中关村店": ["瑞幸咖啡(中关村店)", "luckin coffee 中关村", "瑞幸-中关村店"],
    "喜茶-人民广场店": ["喜茶(人民广场店)", "HEYTEA 人民广场", "喜茶人民广场店"],
    "蜜雪冰城-西湖店": ["蜜雪冰城(西湖店)", "蜜雪 西湖店", "MXBC 西湖"],
    "奈雪的茶-福田店": ["奈雪的茶(福田店)", "奈雪 福田店", "奈雪茶 福田"],
    "茶百道-天河店": ["茶百道(天河店)", "茶百道 天河", "茶百道天河北路店"],
    "星巴克-陆家嘴店": ["星巴克(陆家嘴店)", "Starbucks 陆家嘴", "星巴克咖啡-陆家嘴"],
    "瑞幸咖啡-滨江店": ["瑞幸(滨江店)", "luckin 滨江店", "瑞幸咖啡 滨江"],
}

STORE_CITY = {
    "星巴克-国贸店": "北京",
    "瑞幸咖啡-中关村店": "北京",
    "喜茶-人民广场店": "上海",
    "蜜雪冰城-西湖店": "杭州",
    "奈雪的茶-福田店": "深圳",
    "茶百道-天河店": "广州",
    "星巴克-陆家嘴店": "上海",
    "瑞幸咖啡-滨江店": "杭州",
}

# 商品与单价（元）
PRODUCTS = [
    ("咖啡", "美式咖啡", 25),
    ("咖啡", "拿铁", 30),
    ("咖啡", "卡布奇诺", 28),
    ("咖啡", "摩卡", 32),
    ("茶饮", "珍珠奶茶", 18),
    ("茶饮", "芋泥啵啵奶绿", 22),
    ("茶饮", "杨枝甘露", 25),
    ("茶饮", "柠檬茶", 15),
    ("烘焙", "黄油可颂", 15),
    ("烘焙", "芝士贝果", 12),
    ("烘焙", "提拉米苏", 32),
]

PAYMENT_METHODS = ["微信支付", "支付宝", "现金", "银行卡"]

# 缺失率与异常率
MISSING_MEMBER_RATE = 0.25     # 非会员订单，业务上允许缺失
MISSING_AMOUNT_RATE = 0.03     # 金额缺失（异常）
MISSING_PRICE_RATE = 0.02      # 单价缺失（异常）
DUPLICATE_RATE = 0.02          # 完全重复行比例
NEG_QTY_RATE = 0.005           # 负数量（退货/录入异常）
ZERO_AMOUNT_RATE = 0.003       # 零金额（异常）
DIRTY_STORE_NAME_RATE = 0.30   # 使用非标准门店名的比例


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta),
                             hours=random.randint(7, 22),
                             minutes=random.randint(0, 59))


def generate_dataset():
    """Generate realistic dummy dataset（对应 SKILL.md 模板中的 generate_dataset）"""
    random.seed(RANDOM_SEED)
    canonical_stores = list(STORE_VARIANTS.keys())
    data = []

    for i in range(1, ROWS + 1):
        canonical = random.choice(canonical_stores)
        # 门店名称：30% 概率使用脏写法
        if random.random() < DIRTY_STORE_NAME_RATE:
            store_name = random.choice(STORE_VARIANTS[canonical])
        else:
            store_name = canonical

        category, product, price = random.choice(PRODUCTS)
        quantity = random.randint(1, 5)

        # 负数量异常
        if random.random() < NEG_QTY_RATE:
            quantity = -abs(quantity)

        unit_price = price
        amount = round(unit_price * quantity, 2)

        # 零金额异常（把金额置 0，数量与单价保留）
        if random.random() < ZERO_AMOUNT_RATE:
            amount = 0.0

        order_date = _random_date(START_DATE, END_DATE).strftime("%Y-%m-%d %H:%M:%S")
        payment = random.choice(PAYMENT_METHODS)

        # 会员号：25% 缺失（非会员）
        member_id = "" if random.random() < MISSING_MEMBER_RATE else f"M{random.randint(100000, 999999)}"

        # 单价缺失（异常）
        if random.random() < MISSING_PRICE_RATE:
            unit_price = None

        # 金额缺失（异常）—— 不补零，留空
        if random.random() < MISSING_AMOUNT_RATE:
            amount = None

        record = {
            "order_id": f"ORD{i:06d}",
            "store_name": store_name,
            "city": STORE_CITY[canonical],
            "product_category": category,
            "product_name": product,
            "quantity": quantity,
            "unit_price": unit_price if unit_price is not None else "",
            "amount": amount if amount is not None else "",
            "order_date": order_date,
            "payment_method": payment,
            "member_id": member_id,
        }
        data.append(record)

    # 注入完全重复行（复制已有记录，order_id 也相同，模拟系统重复提交）
    n_dup = int(ROWS * DUPLICATE_RATE)
    dup_rows = random.sample(data, n_dup)
    data.extend(dup_rows)

    random.shuffle(data)
    return data


def save_as_csv(data, filename):
    """Save dataset as CSV（对应 SKILL.md 模板中的 save_as_csv）"""
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)


if __name__ == "__main__":
    dataset = generate_dataset()
    save_as_csv(dataset, FILENAME)
    print(f"Generated {len(dataset)} records in {FILENAME}")
