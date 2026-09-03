# -*- coding: utf-8 -*-
"""
冒烟测试：用合成的小样本验证整条流程可运行、结果可核对。

注意：以下数据为**合成冒烟测试数据**，不是用户真实业务数据。
其作用是验证：
  - chroma 语义匹配能否识别门店名变体；
  - 重复订单是否被标记且不参与聚合；
  - 缺失金额是否不补 0、不计入销售额；
  - 未知门店是否进入 UNRESOLVED 人工复核；
  - 抽样核对记录是否可复现。
"""

import os
import sys
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from etl_pipeline import run_pipeline  # noqa: E402


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    data_dir = os.path.join(HERE, "smoke_data")
    out_dir = os.path.join(HERE, "output")
    os.makedirs(data_dir, exist_ok=True)

    # 门店主数据（规范门店）
    master_rows = [
        ["S001", "星巴克咖啡（国贸店）", "星巴克", "北京", "国贸"],
        ["S002", "瑞幸咖啡（望京店）", "瑞幸", "北京", "望京"],
        ["S003", "麦当劳（中关村店）", "麦当劳", "北京", "中关村"],
        ["S004", "海底捞火锅（西单店）", "海底捞", "北京", "西单"],
    ]
    master_path = os.path.join(data_dir, "store_master.csv")
    write_csv(
        master_path,
        ["canonical_id", "canonical_name", "brand", "city", "area"],
        master_rows,
    )

    # 订单数据（含各类异常）
    order_rows = [
        # 1) 同店不同写法：括号/空格差异 -> 规范化精确匹配
        ["O001", "星巴克咖啡(国贸店)", "35.0", "2026-08-01 09:10"],
        ["O002", " 星巴克咖啡（国贸店） ", "42.5", "2026-08-01 10:20"],
        # 2) 英文品牌名 + 中文地名：Starbucks 国贸 -> 语义匹配（默认模型可能匹配不上，
        #    会进入 UNRESOLVED，用于暴露默认英文模型的局限）
        ["O003", "Starbucks 国贸店", "38.0", "2026-08-01 11:00"],
        # 3) 瑞幸变体
        ["O004", "瑞幸咖啡望京店", "18.9", "2026-08-01 12:00"],
        ["O005", "luckin coffee 望京店", "22.0", "2026-08-01 12:30"],
        # 4) 重复订单 O001（重复行，不参与聚合）
        ["O001", "星巴克咖啡(国贸店)", "35.0", "2026-08-01 09:10"],
        # 5) 缺失金额：不补 0，不计入销售额
        ["O006", "麦当劳（中关村店）", "", "2026-08-01 13:00"],
        ["O007", "麦当劳(中关村店)", "55.0", "2026-08-01 13:30"],
        # 6) 缺失门店名
        ["O008", "", "29.9", "2026-08-01 14:00"],
        # 7) 未知门店（主数据中不存在）
        ["O009", "喜茶（三里屯店）", "33.0", "2026-08-01 15:00"],
        # 8) 海底捞
        ["O010", "海底捞火锅(西单店)", "288.0", "2026-08-01 18:00"],
        # 9) 负金额（异常）
        ["O011", "瑞幸咖啡(望京店)", "-5.0", "2026-08-01 19:00"],
        # 10) 缺失 order_id
        ["", "星巴克咖啡(国贸店)", "40.0", "2026-08-01 20:00"],
    ]
    orders_path = os.path.join(data_dir, "orders.csv")
    write_csv(
        orders_path,
        ["order_id", "store_name", "amount", "order_time"],
        order_rows,
    )

    result = run_pipeline(
        input_path=orders_path,
        store_master_path=master_path,
        output_dir=out_dir,
        chunksize=500,
        distance_threshold=0.75,
        sample_size=10,
        sample_seed=42,
        chroma_persist_dir=os.path.join(HERE, "chroma_smoke_db"),
        reset_chroma=True,
    )

    print("=== 冒烟测试完成 ===")
    print("主数据索引条数:", result["indexed_stores"])
    print("异常统计:")
    for k, v in result["stats"].items():
        if k != "unresolved_store_names":
            print(f"  {k}: {v}")
    print("  unresolved_store_names:", result["stats"]["unresolved_store_names"])
    print("输出目录:", out_dir)


if __name__ == "__main__":
    main()
