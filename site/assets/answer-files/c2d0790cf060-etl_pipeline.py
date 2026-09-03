# -*- coding: utf-8 -*-
"""
门店订单 ETL 与聚合（可扩展分块处理）。

职责划分（严格遵守 chroma Skill 能力边界）：
  - chroma（StoreNameResolver）：仅负责门店名变体 -> 规范门店的语义匹配；
  - 本模块（pandas）：分块读取、重复订单检测、缺失值统计、聚合、抽样核对。

关键数据质量原则（按题目要求）：
  1. 缺失金额绝不补 0：聚合时缺失金额行不计入销售额，单独计数；
  2. 重复订单不静默合并：标记并统计，默认保留首条参与聚合，重复行单独列出；
  3. 门店名无法解析时不强行归并：标记 UNRESOLVED，进入人工复核清单；
  4. 全流程可复现：抽样核对使用固定随机种子。
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from store_name_resolver import StoreNameResolver, ResolveResult


# 视为缺失的字符串标记
NULL_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-", "--", "未知"}


@dataclass
class AnomalyStats:
    total_rows: int = 0
    duplicate_order_rows: int = 0
    duplicate_order_ids: int = 0
    missing_by_column: dict = field(default_factory=dict)
    unresolved_store_rows: int = 0
    unresolved_store_names: list = field(default_factory=list)
    negative_amount_rows: int = 0

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "duplicate_order_rows": self.duplicate_order_rows,
            "duplicate_order_ids": self.duplicate_order_ids,
            "missing_by_column": self.missing_by_column,
            "unresolved_store_rows": self.unresolved_store_rows,
            "unresolved_store_names": sorted(set(self.unresolved_store_names)),
            "negative_amount_rows": self.negative_amount_rows,
        }


def _is_missing(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    if isinstance(v, str) and v.strip().lower() in NULL_TOKENS:
        return True
    return False


def run_pipeline(
    input_path: str,
    store_master_path: str,
    output_dir: str,
    chunksize: int = 100_000,
    distance_threshold: float = 0.75,
    sample_size: int = 20,
    sample_seed: int = 42,
    chroma_persist_dir: str = "./chroma_store_db",
    reset_chroma: bool = True,
) -> dict:
    """
    运行完整 ETL。

    输入 CSV 期望列（顺序无关）：
      order_id, store_name, amount, order_time（可选）
    门店主数据 CSV 期望列：
      canonical_id, canonical_name, brand(可选), city(可选), area(可选)

    输出文件（写入 output_dir）：
      result_by_store.csv      按规范门店聚合的结果表
      anomalies.json           异常统计
      duplicate_orders.csv     重复订单明细
      unresolved_stores.csv    未解析门店清单（人工复核）
      sample_verification.csv  抽样核对记录
      pipeline_summary.txt     运行摘要
    """
    os.makedirs(output_dir, exist_ok=True)

    # ---- 1. 加载门店主数据并构建 chroma 索引 ----
    master = pd.read_csv(store_master_path, dtype=str)
    resolver = StoreNameResolver(
        persist_dir=chroma_persist_dir,
        distance_threshold=distance_threshold,
        reset=reset_chroma,
    )
    indexed = resolver.build_index(master.to_dict("records"))

    # ---- 2. 分块处理订单 ----
    stats = AnomalyStats()
    seen_order_ids: set[str] = set()
    duplicate_records: list[dict] = []

    # 聚合器：canonical_id -> 指标
    agg: dict[str, dict] = defaultdict(
        lambda: {
            "canonical_name": "",
            "order_count": 0,        # 去重后参与聚合的订单数
            "valid_amount_count": 0, # 金额非空的订单数
            "total_amount": 0.0,     # 仅累加非空金额
            "missing_amount_count": 0,
            "unresolved_rows": 0,
        }
    )

    sample_rows: list[dict] = []

    reader = pd.read_csv(
        input_path, dtype=str, chunksize=chunksize, keep_default_na=False
    )
    for chunk in reader:
        # 缺失值统计（按列）
        for col in chunk.columns:
            miss = int(chunk[col].apply(_is_missing).sum())
            stats.missing_by_column[col] = stats.missing_by_column.get(col, 0) + miss

        for _, row in chunk.iterrows():
            stats.total_rows += 1
            order_id = row.get("order_id")
            raw_store = row.get("store_name")
            amount_raw = row.get("amount")

            # 重复订单检测（按 order_id）
            is_dup = False
            if not _is_missing(order_id):
                oid = str(order_id).strip()
                if oid in seen_order_ids:
                    is_dup = True
                    stats.duplicate_order_rows += 1
                    duplicate_records.append(
                        {"order_id": oid, "raw_store": raw_store, "amount": amount_raw}
                    )
                else:
                    seen_order_ids.add(oid)

            # 解析门店名（重复行也解析，便于核对，但默认不参与聚合）
            res: ResolveResult = resolver.resolve_one(raw_store)

            # 金额解析：缺失不补 0
            amount_val: Optional[float] = None
            if not _is_missing(amount_raw):
                try:
                    amount_val = float(str(amount_raw).strip())
                except ValueError:
                    amount_val = None  # 非法金额按缺失处理，不补 0
                if amount_val is not None and amount_val < 0:
                    stats.negative_amount_rows += 1

            if not res.resolved:
                stats.unresolved_store_rows += 1
                stats.unresolved_store_names.append(raw_store if raw_store is not None else "")

            # 聚合：重复行不参与
            if not is_dup:
                key = res.canonical_id if res.resolved else "UNRESOLVED"
                bucket = agg[key]
                if res.resolved:
                    bucket["canonical_name"] = res.canonical_name
                else:
                    bucket["canonical_name"] = "UNRESOLVED（待人工复核）"
                bucket["order_count"] += 1
                if amount_val is None:
                    bucket["missing_amount_count"] += 1
                else:
                    bucket["valid_amount_count"] += 1
                    bucket["total_amount"] += amount_val
                if not res.resolved:
                    bucket["unresolved_rows"] += 1

            # 收集抽样候选（含原始字段与解析结果）
            sample_rows.append(
                {
                    "order_id": "" if _is_missing(order_id) else str(order_id).strip(),
                    "raw_store": "" if raw_store is None else str(raw_store),
                    "amount_raw": "" if _is_missing(amount_raw) else str(amount_raw),
                    "is_duplicate": is_dup,
                    "canonical_id": res.canonical_id or "",
                    "canonical_name": res.canonical_name or "",
                    "match_type": res.match_type,
                    "distance": "" if res.distance is None else round(res.distance, 4),
                    "resolved": res.resolved,
                    "amount_used_in_sum": amount_val if amount_val is not None else "",
                }
            )

    stats.duplicate_order_ids = len({r["order_id"] for r in duplicate_records})

    # ---- 3. 结果表 ----
    result_rows = []
    for cid, b in agg.items():
        result_rows.append(
            {
                "canonical_id": cid,
                "canonical_name": b["canonical_name"],
                "order_count_dedup": b["order_count"],
                "valid_amount_orders": b["valid_amount_count"],
                "total_amount": round(b["total_amount"], 2),
                "missing_amount_orders": b["missing_amount_count"],
                "unresolved_store_rows": b["unresolved_rows"],
            }
        )
    result_df = pd.DataFrame(result_rows).sort_values(
        "total_amount", ascending=False
    )
    result_path = os.path.join(output_dir, "result_by_store.csv")
    result_df.to_csv(result_path, index=False, encoding="utf-8-sig")

    # ---- 4. 异常统计 ----
    anomalies_path = os.path.join(output_dir, "anomalies.json")
    with open(anomalies_path, "w", encoding="utf-8") as f:
        json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)

    # ---- 5. 重复订单明细 ----
    dup_path = os.path.join(output_dir, "duplicate_orders.csv")
    pd.DataFrame(duplicate_records).to_csv(
        dup_path, index=False, encoding="utf-8-sig"
    )

    # ---- 6. 未解析门店清单 ----
    unres = pd.DataFrame(
        sorted(set(stats.unresolved_store_names)), columns=["raw_store_name"]
    )
    unres_path = os.path.join(output_dir, "unresolved_stores.csv")
    unres.to_csv(unres_path, index=False, encoding="utf-8-sig")

    # ---- 7. 抽样核对记录（可复现） ----
    sample_df = pd.DataFrame(sample_rows)
    if len(sample_df) > sample_size:
        sample_df = sample_df.sample(
            n=sample_size, random_state=sample_seed
        ).sort_index()
    sample_path = os.path.join(output_dir, "sample_verification.csv")
    sample_df.to_csv(sample_path, index=False, encoding="utf-8-sig")

    # ---- 8. 运行摘要 ----
    summary_path = os.path.join(output_dir, "pipeline_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("门店订单 ETL 运行摘要\n")
        f.write("=" * 40 + "\n")
        f.write(f"输入文件: {input_path}\n")
        f.write(f"门店主数据: {store_master_path}\n")
        f.write(f"chroma 主数据索引条数: {indexed}\n")
        f.write(f"分块大小: {chunksize}\n")
        f.write(f"语义匹配距离阈值: {distance_threshold}\n")
        f.write(f"总行数: {stats.total_rows}\n")
        f.write(f"重复订单行数(不参与聚合): {stats.duplicate_order_rows}\n")
        f.write(f"涉及重复的 order_id 数: {stats.duplicate_order_ids}\n")
        f.write(f"未解析门店行数: {stats.unresolved_store_rows}\n")
        f.write(f"负金额行数: {stats.negative_amount_rows}\n")
        f.write("缺失值按列统计:\n")
        for k, v in stats.missing_by_column.items():
            f.write(f"  {k}: {v}\n")
        f.write(f"结果表: {result_path}\n")
        f.write(f"抽样核对: {sample_path}\n")

    return {
        "result_path": result_path,
        "anomalies_path": anomalies_path,
        "duplicate_path": dup_path,
        "unresolved_path": unres_path,
        "sample_path": sample_path,
        "summary_path": summary_path,
        "indexed_stores": indexed,
        "stats": stats.to_dict(),
    }
