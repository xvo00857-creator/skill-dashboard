#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
门店订单批处理流水线（可扩展 / 可恢复）

设计原则：
  1. 分块读取，支持大文件；每块处理完落 checkpoint，中断后可从断点续跑。
  2. 缺失值绝不补 0：数值列保留 NaN，聚合时 skipna；分类列保留空/标记"未知"，
     并在异常统计中逐列计数。
  3. 重复订单：按订单号去重，保留首条；重复条目全部记入审计日志；若同订单号
     存在字段冲突，标记 conflict 供人工核对，不静默覆盖。
  4. 门店名称不一致：先做规则归一化（去空白/全半角/常见后缀），再按映射表对齐；
     映射表未命中且模糊匹配置信度不足时，标记 NEEDS_REVIEW，不自动改名。
  5. 产出：清洗后结果表、异常统计、抽样核对记录。

用法：
  python3 order_pipeline.py --input <csv> --outdir <dir> [--chunksize 50000]
  （重跑时自动读取 outdir/checkpoint.json 续跑；加 --restart 从头开始）

注意：本脚本不依赖 terminal_pty_* 工具。按 SKILL.md 指引，非交互式批处理应使用
普通执行（terminal_exec / Bash），PTY 会话仅用于需要跨调用状态或交互式提示的场景。
"""

import argparse
import csv
import json
import os
import random
import re
import sys
from collections import defaultdict
from datetime import datetime

# ----------------------------- 门店名称归一化 -----------------------------

# 已知门店标准名 -> 别名/历史名（按需扩充；真实环境应从主数据加载）
STORE_ALIAS_MAP = {
    "北京朝阳店": ["朝阳店", "北京朝阳分店", "朝阳旗舰店", "北京朝陽店"],
    "北京海淀店": ["海淀店", "北京海淀分店", "海淀旗舰店"],
    "上海浦东店": ["浦东店", "上海浦东分店", "浦東店"],
    "上海徐汇店": ["徐汇店", "上海徐汇分店", "徐匯店"],
    "杭州西湖店": ["西湖店", "杭州西湖分店", "西湖旗舰店"],
    "广州天河店": ["天河店", "广州天河分店", "天河旗舰店"],
}

# 反向索引：归一化别名 -> 标准名
_ALIAS_INDEX = {}
for _std, _aliases in STORE_ALIAS_MAP.items():
    _ALIAS_INDEX[_std] = _std
    for _a in _aliases:
        _ALIAS_INDEX[_a] = _std

# 名称中需剥离的常见后缀/装饰词
_NAME_SUFFIXES = [
    "旗舰店", "直营店", "专卖店", "分店", "门店", "店",
    "有限责任公司", "有限公司", "公司",
]


def _norm_text(s: str) -> str:
    """基础文本归一化：去空白、全角转半角、统一大小写、去常见标点。"""
    if s is None:
        return ""
    s = str(s).strip()
    # 全角转半角
    out = []
    for ch in s:
        code = ord(ch)
        if code == 0x3000:
            code = 0x20
        elif 0xFF01 <= code <= 0xFF5E:
            code -= 0xFEE0
        out.append(chr(code))
    s = "".join(out)
    s = re.sub(r"\s+", "", s)
    s = s.replace("(", "").replace(")", "").replace("（", "").replace("）", "")
    s = s.replace("-", "").replace("_", "").replace("·", "")
    return s.lower()


def _strip_suffixes(name: str) -> str:
    for suf in _NAME_SUFFIXES:
        if name.endswith(suf):
            name = name[: -len(suf)]
    return name


def normalize_store(raw_name):
    """
    返回 (standard_name, status)
      status: OK              映射表命中
              UNKNOWN_NULL    原始为空
              NEEDS_REVIEW    未能可靠匹配，保留原值并标记
    """
    if raw_name is None or str(raw_name).strip() == "":
        return None, "UNKNOWN_NULL"

    norm = _norm_text(raw_name)
    # 1) 直接查别名索引（含标准名自身）
    if norm in _ALIAS_INDEX:
        return _ALIAS_INDEX[norm], "OK"
    # 2) 去后缀后再查
    stripped = _strip_suffixes(norm)
    if stripped in _ALIAS_INDEX:
        return _ALIAS_INDEX[stripped], "OK"
    # 3) 去后缀后做包含匹配（置信度有限，仅在唯一命中时接受）
    candidates = set()
    for alias, std in _ALIAS_INDEX.items():
        a = _strip_suffixes(alias)
        if a and (a in stripped or stripped in a):
            candidates.add(std)
    if len(candidates) == 1:
        return next(iter(candidates)), "OK"
    # 4) 无法可靠匹配
    return str(raw_name).strip(), "NEEDS_REVIEW"


# ----------------------------- 数值解析 -----------------------------

def parse_amount(v):
    """
    解析金额。空串/None -> (None, 'MISSING')；
    非数字 -> (None, 'INVALID')；合法 -> (float, 'OK')。
    绝不把缺失补成 0。
    """
    if v is None:
        return None, "MISSING"
    s = str(v).strip()
    if s == "":
        return None, "MISSING"
    s2 = s.replace(",", "").replace("￥", "").replace("¥", "").replace("$", "")
    try:
        return float(s2), "OK"
    except ValueError:
        return None, "INVALID"


def parse_int(v):
    if v is None:
        return None, "MISSING"
    s = str(v).strip()
    if s == "":
        return None, "MISSING"
    try:
        return int(float(s)), "OK"
    except ValueError:
        return None, "INVALID"


# ----------------------------- 流水线 -----------------------------

REQUIRED_COLS = ["order_id", "store_name", "amount", "qty"]


class Pipeline:
    def __init__(self, input_path, outdir, chunksize=50000, sample_n=20, seed=42):
        self.input_path = input_path
        self.outdir = outdir
        self.chunksize = chunksize
        self.sample_n = sample_n
        self.rng = random.Random(seed)

        self.clean_path = os.path.join(outdir, "cleaned_orders.csv")
        self.audit_path = os.path.join(outdir, "duplicate_audit.csv")
        self.review_path = os.path.join(outdir, "store_review.csv")
        self.stats_path = os.path.join(outdir, "exception_stats.json")
        self.sample_path = os.path.join(outdir, "sample_check.csv")
        self.checkpoint_path = os.path.join(outdir, "checkpoint.json")

        self.seen_orders = {}          # order_id -> 首条记录的关键字段指纹
        self.dup_count = 0
        self.conflict_count = 0
        self.missing = defaultdict(int)
        self.invalid = defaultdict(int)
        self.store_status = defaultdict(int)
        self.total_in = 0
        self.total_out = 0
        self.samples = []              # 抽样核对记录
        self.chunk_idx = 0

    # ---------- checkpoint ----------
    def _load_checkpoint(self):
        if os.path.exists(self.checkpoint_path):
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_checkpoint(self, done=False):
        ck = {
            "chunk_idx": self.chunk_idx,
            "total_in": self.total_in,
            "total_out": self.total_out,
            "dup_count": self.dup_count,
            "conflict_count": self.conflict_count,
            "missing": dict(self.missing),
            "invalid": dict(self.invalid),
            "store_status": dict(self.store_status),
            "done": done,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(ck, f, ensure_ascii=False, indent=2)

    # ---------- 主流程 ----------
    def run(self, restart=False):
        os.makedirs(self.outdir, exist_ok=True)
        ck = None if restart else self._load_checkpoint()
        resume = ck is not None
        to_skip = 0
        if resume:
            if ck.get("done"):
                print("[resume] 该任务已完成（checkpoint 标记 done）。如需重跑请加 --restart。")
                return
            self.chunk_idx = ck["chunk_idx"]
            self.total_in = ck["total_in"]
            self.total_out = ck["total_out"]
            self.dup_count = ck["dup_count"]
            self.conflict_count = ck["conflict_count"]
            for k, v in ck.get("missing", {}).items():
                self.missing[k] = v
            for k, v in ck.get("invalid", {}).items():
                self.invalid[k] = v
            for k, v in ck.get("store_status", {}).items():
                self.store_status[k] = v
            to_skip = ck["total_in"]
            # 从已落盘的清洗结果重建 seen_orders，保证跨 checkpoint 的重复订单仍能识别
            if os.path.exists(self.clean_path):
                with open(self.clean_path, "r", encoding="utf-8-sig", newline="") as f_seen:
                    for r in csv.DictReader(f_seen):
                        oid = r.get("order_id", "").strip()
                        if oid:
                            self.seen_orders[oid] = (
                                r.get("store_standard") or None,
                                float(r["amount"]) if r.get("amount") not in ("", None) else None,
                                int(r["qty"]) if r.get("qty") not in ("", None) else None,
                            )
            print(f"[resume] 从 chunk {self.chunk_idx} 续跑（跳过前 {to_skip} 行，"
                  f"已重建 {len(self.seen_orders)} 个订单号）")

        # 输出文件：续跑时追加；新跑时写表头
        mode = "a" if resume else "w"
        f_clean = open(self.clean_path, mode, encoding="utf-8-sig", newline="")
        f_audit = open(self.audit_path, mode, encoding="utf-8-sig", newline="")
        f_review_fh = open(self.review_path, mode, encoding="utf-8-sig", newline="")

        w_clean = csv.writer(f_clean)
        w_audit = csv.writer(f_audit)
        w_rev = csv.writer(f_review_fh)
        if not resume:
            w_clean.writerow([
                "order_id", "store_raw", "store_standard", "store_status",
                "amount", "qty", "amount_status", "qty_status", "row_flag",
            ])
            w_audit.writerow(["order_id", "dup_count", "conflict_fields", "raw_row"])
            w_rev.writerow(["store_raw", "store_kept", "reason"])

        try:
            with open(self.input_path, "r", encoding="utf-8-sig", newline="") as f_in:
                reader = csv.DictReader(f_in)
                missing_cols = [c for c in REQUIRED_COLS if c not in (reader.fieldnames or [])]
                if missing_cols:
                    raise ValueError(f"输入缺少必要列: {missing_cols}；实际列: {reader.fieldnames}")

                chunk = []
                for row in reader:
                    # 续跑：跳过已处理的行
                    if to_skip > 0:
                        to_skip -= 1
                        continue
                    chunk.append(row)
                    if len(chunk) >= self.chunksize:
                        self._process_chunk(chunk, w_clean, w_audit, w_rev)
                        chunk = []
                        self.chunk_idx += 1
                        self._save_checkpoint()
                        print(f"[chunk {self.chunk_idx}] 累计读入 {self.total_in}，输出 {self.total_out}")
                if chunk:
                    self._process_chunk(chunk, w_clean, w_audit, w_rev)
                    self.chunk_idx += 1
                    self._save_checkpoint()
        finally:
            f_clean.close()
            f_audit.close()
            f_review_fh.close()

        self._write_stats()
        self._write_sample()
        self._save_checkpoint(done=True)
        print("[done] 完成")

    def _process_chunk(self, chunk, w_clean, w_audit, w_rev):
        for row in chunk:
            self.total_in += 1
            order_id = (row.get("order_id") or "").strip()
            store_raw = (row.get("store_name") or "").strip()
            amount, amt_status = parse_amount(row.get("amount"))
            qty, qty_status = parse_int(row.get("qty"))

            # 缺失/非法计数
            if order_id == "":
                self.missing["order_id"] += 1
            if amt_status == "MISSING":
                self.missing["amount"] += 1
            elif amt_status == "INVALID":
                self.invalid["amount"] += 1
            if qty_status == "MISSING":
                self.missing["qty"] += 1
            elif qty_status == "INVALID":
                self.invalid["qty"] += 1

            # 门店归一化
            store_std, store_status = normalize_store(store_raw)
            self.store_status[store_status] += 1
            if store_status == "UNKNOWN_NULL":
                self.missing["store_name"] += 1
            if store_status == "NEEDS_REVIEW":
                w_rev.writerow([store_raw, store_std, "未能可靠匹配，需人工确认"])

            row_flag = "OK"
            if order_id == "":
                row_flag = "MISSING_ORDER_ID"

            # 重复订单判定
            if order_id and order_id in self.seen_orders:
                self.dup_count += 1
                prev = self.seen_orders[order_id]
                cur_fp = (store_std, amount, qty)
                conflict_fields = []
                if prev[0] != cur_fp[0]:
                    conflict_fields.append("store")
                if prev[1] != cur_fp[1]:
                    conflict_fields.append("amount")
                if prev[2] != cur_fp[2]:
                    conflict_fields.append("qty")
                if conflict_fields:
                    self.conflict_count += 1
                    w_audit.writerow([
                        order_id, ">=2", ";".join(conflict_fields),
                        json.dumps(row, ensure_ascii=False),
                    ])
                    row_flag = "DUP_CONFLICT"
                else:
                    w_audit.writerow([
                        order_id, ">=2", "", json.dumps(row, ensure_ascii=False),
                    ])
                    row_flag = "DUP_EXACT"
                # 重复行不写入清洗结果（保留首条）
                continue

            if order_id:
                self.seen_orders[order_id] = (store_std, amount, qty)

            w_clean.writerow([
                order_id,
                store_raw,
                store_std if store_std is not None else "",
                store_status,
                "" if amount is None else amount,
                "" if qty is None else qty,
                amt_status,
                qty_status,
                row_flag,
            ])
            self.total_out += 1

    def _write_stats(self):
        # 汇总金额/数量：缺失值不参与（skipna 语义），绝不按 0 计
        amt_sum = 0.0
        amt_n = 0
        qty_sum = 0
        qty_n = 0
        with open(self.clean_path, "r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for rrow in r:
                if rrow["amount_status"] == "OK" and rrow["amount"] != "":
                    amt_sum += float(rrow["amount"])
                    amt_n += 1
                if rrow["qty_status"] == "OK" and rrow["qty"] != "":
                    qty_sum += int(rrow["qty"])
                    qty_n += 1

        stats = {
            "input_path": self.input_path,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_rows_read": self.total_in,
            "total_rows_after_dedup": self.total_out,
            "duplicate_rows_removed": self.dup_count,
            "duplicate_conflict_rows": self.conflict_count,
            "missing_counts_by_column": dict(self.missing),
            "invalid_counts_by_column": dict(self.invalid),
            "store_name_status": dict(self.store_status),
            "amount_sum_excluding_missing": round(amt_sum, 2),
            "amount_non_missing_count": amt_n,
            "qty_sum_excluding_missing": qty_sum,
            "qty_non_missing_count": qty_n,
            "note": "缺失值未补0；金额/数量合计仅基于非缺失合法值。",
        }
        with open(self.stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    def _write_sample(self):
        """从完整清洗结果做蓄水池抽样，覆盖续跑前后的所有行。"""
        reservoir = []
        n = 0
        with open(self.clean_path, "r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for rrow in r:
                n += 1
                record = [
                    rrow.get("order_id", ""),
                    rrow.get("store_raw", ""),
                    rrow.get("amount", ""),
                    rrow.get("qty", ""),
                    rrow.get("store_standard", ""),
                    rrow.get("store_status", ""),
                    rrow.get("amount_status", ""),
                    rrow.get("qty_status", ""),
                    rrow.get("row_flag", ""),
                ]
                if len(reservoir) < self.sample_n:
                    reservoir.append(record)
                else:
                    j = self.rng.randint(0, n - 1)
                    if j < self.sample_n:
                        reservoir[j] = record
        with open(self.sample_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "order_id", "原始store_name", "清洗后amount", "清洗后qty",
                "清洗后store_standard", "门店状态", "金额状态", "数量状态", "行标记",
            ])
            w.writerows(reservoir)


def main():
    ap = argparse.ArgumentParser(description="门店订单批处理流水线")
    ap.add_argument("--input", required=True, help="输入 CSV 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    ap.add_argument("--chunksize", type=int, default=50000)
    ap.add_argument("--sample-n", type=int, default=20)
    ap.add_argument("--restart", action="store_true", help="忽略 checkpoint 从头跑")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"[error] 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    p = Pipeline(args.input, args.outdir, chunksize=args.chunksize, sample_n=args.sample_n)
    p.run(restart=args.restart)


if __name__ == "__main__":
    main()
