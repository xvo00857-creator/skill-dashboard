#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
合成测试数据生成脚本
====================
本脚本生成用于演示 Dask 分布式清洗分析流程的门店订单数据。
数据特征（按题目描述构造）：
  - 数据量较大：约 300 万行，拆分为 6 个 CSV 文件
  - 门店名称不一致：同一门店存在多种写法（空格、市/区后缀、括号别名等）
  - 缺失值：quantity / unit_price / amount / payment_method / member_id 等列存在缺失
  - 重复订单：约 5% 的订单为完全重复行
  - 金额异常：部分 amount 与 quantity*unit_price 不一致
注意：本数据为程序化生成的测试数据，非真实业务数据。
"""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_data")
os.makedirs(OUT_DIR, exist_ok=True)

# 5 家标准门店及其名称变体（模拟门店名称不一致问题）
STORE_VARIANTS = {
    "北京朝阳店": ["北京朝阳店", "北京市朝阳店", "北京朝阳门店", "北京 朝阳店", "朝阳店(北京)"],
    "上海浦东店": ["上海浦东店", "上海市浦东店", "上海浦东分店", "上海 浦东店", "浦东店(上海)"],
    "广州天河店": ["广州天河店", "广州市天河店", "广州天河门店", "广州 天河店", "天河店(广州)"],
    "深圳南山店": ["深圳南山店", "深圳市南山店", "深圳南山分店", "深圳 南山店", "南山店(深圳)"],
    "杭州西湖店": ["杭州西湖店", "杭州市西湖店", "杭州西湖门店", "杭州 西湖店", "西湖店(杭州)"],
}

REGION_MAP = {
    "北京朝阳店": "华北",
    "上海浦东店": "华东",
    "广州天河店": "华南",
    "深圳南山店": "华南",
    "杭州西湖店": "华东",
}

PRODUCTS = [
    ("食品饮料", "矿泉水", 2.0),
    ("食品饮料", "方便面", 5.0),
    ("食品饮料", "牛奶", 8.5),
    ("食品饮料", "面包", 6.0),
    ("食品饮料", "巧克力", 12.0),
    ("日用百货", "纸巾", 15.0),
    ("日用百货", "洗衣液", 35.0),
    ("日用百货", "牙膏", 12.0),
    ("日用百货", "毛巾", 18.0),
    ("生鲜果蔬", "苹果", 9.0),
    ("生鲜果蔬", "香蕉", 5.0),
    ("生鲜果蔬", "西红柿", 6.0),
    ("生鲜果蔬", "鸡蛋", 12.0),
    ("烟酒粮油", "大米", 45.0),
    ("烟酒粮油", "食用油", 65.0),
    ("烟酒粮油", "啤酒", 6.0),
    ("个护美妆", "洗发水", 40.0),
    ("个护美妆", "沐浴露", 35.0),
]

PAYMENT_METHODS = ["微信支付", "支付宝", "现金", "银行卡", "会员储值"]

NUM_FILES = 6
ROWS_PER_FILE = 500_000  # 总计 300 万行
DUP_RATE = 0.05          # 约 5% 重复订单
MISSING_RATE = 0.04      # 各列约 4% 缺失（不同列独立）
AMOUNT_MISMATCH_RATE = 0.02  # 约 2% 金额与数量×单价不一致

def gen_order_id(seq):
    return f"ORD{seq:09d}"

def gen_datetime(file_idx, row_idx):
    # 每个文件覆盖一个月，2025-01 ~ 2025-06
    base = datetime(2025, 1 + file_idx, 1)
    day_offset = random.randint(0, 27)
    second_offset = random.randint(0, 86399)
    dt = base + timedelta(days=day_offset, seconds=second_offset)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def maybe_missing(value, rate=MISSING_RATE):
    return "" if random.random() < rate else value

def main():
    seq = 1
    total_written = 0
    for fi in range(NUM_FILES):
        path = os.path.join(OUT_DIR, f"orders_2025_{fi+1:02d}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "order_id", "order_datetime", "store_name", "region",
                "product_category", "product_name", "quantity",
                "unit_price", "amount", "payment_method", "member_id"
            ])
            rows_buffer = []
            for ri in range(ROWS_PER_FILE):
                std_store = random.choice(list(STORE_VARIANTS.keys()))
                store_name = random.choice(STORE_VARIANTS[std_store])
                region = REGION_MAP[std_store]
                cat, pname, base_price = random.choice(PRODUCTS)
                qty = random.randint(1, 20)
                price = round(base_price * random.uniform(0.9, 1.1), 2)
                amount = round(qty * price, 2)

                # 金额不一致：人为制造偏差
                if random.random() < AMOUNT_MISMATCH_RATE:
                    amount = round(amount + random.choice([-1, 1]) * random.uniform(1, 50), 2)

                payment = random.choice(PAYMENT_METHODS)
                is_member = random.random() < 0.6
                member_id = f"M{random.randint(100000, 999999)}" if is_member else ""

                row = [
                    gen_order_id(seq),
                    gen_datetime(fi, ri),
                    store_name,
                    region,
                    cat,
                    pname,
                    maybe_missing(qty),
                    maybe_missing(price),
                    maybe_missing(amount),
                    maybe_missing(payment),
                    member_id,  # 非会员本身就是空，不算缺失
                ]
                rows_buffer.append(row)
                seq += 1

                # 注入重复行：随机复制当前行
                if random.random() < DUP_RATE:
                    rows_buffer.append(row.copy())

                if len(rows_buffer) >= 10000:
                    writer.writerows(rows_buffer)
                    total_written += len(rows_buffer)
                    rows_buffer = []

            if rows_buffer:
                writer.writerows(rows_buffer)
                total_written += len(rows_buffer)

        print(f"已生成: {path}  (累计 {total_written} 行)")

    print(f"\n完成。共 {NUM_FILES} 个文件，总计约 {total_written} 行（含重复）。")
    print(f"输出目录: {OUT_DIR}")

if __name__ == "__main__":
    main()
