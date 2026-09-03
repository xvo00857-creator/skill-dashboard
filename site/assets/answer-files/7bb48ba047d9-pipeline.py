#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
input_pipeline.py — 只读预演版输入清单处理流水线（最小可用版本）

流程：读取输入清单 -> 字段校验 -> 风险分级 -> 生成待确认结果 -> 人工确认门禁 -> 提交

安全设计原则：
1. 默认 dry-run（只读预演），不产生任何外部副作用；
2. 未核实事实、个人敏感信息、不可逆操作三类风险分别识别并拦截；
3. 真正提交需要显式 --execute、--confirm-token 与 --config 指定的凭据，缺一不可；
4. 本版本未内置任何真实提交端点/凭据，submit 阶段仅记录意图并输出审计日志，
   不会访问网络、数据库或生产系统；接入真实系统前必须补齐授权与回滚方案。

仅依赖 Python 3 标准库。
"""

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# 0. 常量与规则
# ---------------------------------------------------------------------------

VERSION = "0.1.0-dryrun"

# 输入清单必需字段（可按实际业务扩展）
REQUIRED_FIELDS = ["id", "action", "target", "payload", "verified"]

# 不可逆操作关键词（命中即默认拦截，需逐行人工授权）
IRREVERSIBLE_KEYWORDS = [
    "delete", "drop", "truncate", "purge", "destroy", "rm -rf",
    "永久删除", "清空", "销毁", "注销账户", "解散", "封禁永久",
    "force push", "hard delete", "terminate", "deactivate",
    "批量发送", "打款", "转账", "退款", "发放", "下发通知",
]

# 个人敏感信息正则（命中即标记，默认脱敏，不进入提交）
PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone_cn": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "id_cn": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "bank_card": re.compile(r"(?<!\d)\d{16,19}(?!\d)"),
}

# 风险等级
RISK_BLOCK = "BLOCK"          # 拦截：不得提交
RISK_REVIEW = "REVIEW"        # 待审：需人工确认
RISK_OK = "OK"                # 通过：可提交（仍需整体确认门禁）

logger = logging.getLogger("pipeline")


# ---------------------------------------------------------------------------
# 1. 读取输入清单
# ---------------------------------------------------------------------------

def load_input(path: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """读取 CSV 输入清单，返回 (行列表, 错误列表)。"""
    rows: List[Dict[str, str]] = []
    errors: List[str] = []
    if not os.path.isfile(path):
        errors.append(f"输入文件不存在: {path}")
        return rows, errors
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_FIELDS if c not in header]
        if missing:
            errors.append(f"缺少必需列: {missing}；现有列: {header}")
            return rows, errors
        for i, row in enumerate(reader, start=2):  # 行号从 2 起（含表头）
            row["_line"] = str(i)
            rows.append(row)
    return rows, errors


# ---------------------------------------------------------------------------
# 2. 字段校验与风险识别
# ---------------------------------------------------------------------------

def detect_pii(text: str) -> List[str]:
    """返回文本中命中的敏感信息类型列表。"""
    hits = []
    for name, pat in PII_PATTERNS.items():
        if pat.search(text or ""):
            hits.append(name)
    return hits


def is_irreversible(action: str, payload: str) -> bool:
    """判断是否为不可逆操作。"""
    blob = f"{action} {payload}".lower()
    return any(kw in blob for kw in IRREVERSIBLE_KEYWORDS)


def validate_row(row: Dict[str, str]) -> Dict[str, Any]:
    """
    校验单行，返回结构化结果：
      id, line, risk, reasons[], pii_types[], unverified, irreversible, raw
    """
    rid = row.get("id", "").strip()
    action = row.get("action", "").strip()
    target = row.get("target", "").strip()
    payload = row.get("payload", "").strip()
    verified = row.get("verified", "").strip().lower()

    reasons: List[str] = []
    risk = RISK_OK

    # 2.1 必填值
    if not rid:
        reasons.append("id 为空")
        risk = RISK_BLOCK
    if not action:
        reasons.append("action 为空")
        risk = RISK_BLOCK
    if not target:
        reasons.append("target 为空")
        risk = RISK_REVIEW if risk == RISK_OK else risk

    # 2.2 未核实事实
    unverified = verified not in ("true", "1", "yes", "已核实")
    if unverified:
        reasons.append("verified 非真：事实未核实，不得自动提交")
        risk = RISK_REVIEW if risk == RISK_OK else risk

    # 2.3 个人敏感信息
    pii_types = detect_pii(f"{target} {payload}")
    if pii_types:
        reasons.append(f"命中个人敏感信息: {pii_types}（默认脱敏并拦截）")
        risk = RISK_BLOCK

    # 2.4 不可逆操作
    irreversible = is_irreversible(action, payload)
    if irreversible:
        reasons.append("命中不可逆操作关键词：默认拦截，需逐行书面授权与回滚方案")
        risk = RISK_BLOCK

    return {
        "id": rid,
        "line": row.get("_line"),
        "action": action,
        "target": target,
        "risk": risk,
        "reasons": reasons,
        "pii_types": pii_types,
        "unverified": unverified,
        "irreversible": irreversible,
        # 注意：原始 payload 不写入日志/报告，避免敏感信息扩散
        "payload_preview": _redact(payload)[:80],
    }


def _redact(text: str) -> str:
    """对敏感信息做脱敏替换。"""
    out = text or ""
    for name, pat in PII_PATTERNS.items():
        out = pat.sub(f"[REDACTED:{name}]", out)
    return out


# ---------------------------------------------------------------------------
# 3. 生成结果（预演报告）
# ---------------------------------------------------------------------------

def generate_results(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    return [validate_row(r) for r in rows]


def build_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        "total": len(results),
        "block": sum(1 for r in results if r["risk"] == RISK_BLOCK),
        "review": sum(1 for r in results if r["risk"] == RISK_REVIEW),
        "ok": sum(1 for r in results if r["risk"] == RISK_OK),
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "version": VERSION,
        "mode": "DRY-RUN（只读预演，未提交任何内容）",
        "summary": summary,
        "items": results,
    }


# ---------------------------------------------------------------------------
# 4. 人工确认门禁
# ---------------------------------------------------------------------------

def human_gate(results: List[Dict[str, Any]], assume_yes: bool) -> Tuple[bool, List[str]]:
    """
    人工确认门禁。
    返回 (是否允许进入提交阶段, 放行的 id 列表)。
    BLOCK 项永不放行；REVIEW 项需逐项确认；OK 项需整体确认。
    """
    approved_ids: List[str] = []
    block_count = sum(1 for r in results if r["risk"] == RISK_BLOCK)
    if block_count > 0:
        logger.warning("存在 %d 条 BLOCK 记录，提交阶段已被门禁拒绝。", block_count)
        return False, []

    review_items = [r for r in results if r["risk"] == RISK_REVIEW]
    ok_items = [r for r in results if r["risk"] == RISK_OK]

    if not assume_yes:
        print("\n===== 人工确认门禁 =====")
        print(f"待审 {len(review_items)} 条，可直接提交 {len(ok_items)} 条。")
        for r in review_items:
            ans = input(f"  放行 id={r['id']}（原因: {'; '.join(r['reasons'])}）? [y/N]: ").strip().lower()
            if ans != "y":
                logger.info("id=%s 被人工驳回。", r["id"])
                continue
            approved_ids.append(r["id"])
        overall = input(f"  确认提交全部 {len(ok_items)} 条 OK 记录? [y/N]: ").strip().lower()
        if overall != "y":
            logger.info("整体确认未通过，终止提交。")
            return False, approved_ids
    else:
        # 非交互环境：仅放行 OK 项；REVIEW 项必须在真实交互中确认
        approved_ids = [r["id"] for r in ok_items]
        if review_items:
            logger.warning("非交互模式下 %d 条 REVIEW 记录不会自动放行。", len(review_items))

    approved_ids.extend(r["id"] for r in ok_items if r["id"] not in approved_ids)
    return True, approved_ids


# ---------------------------------------------------------------------------
# 5. 提交（占位实现：只记录意图，不产生外部副作用）
# ---------------------------------------------------------------------------

def submit(results: List[Dict[str, Any]], approved_ids: List[str], config_path: str) -> Dict[str, Any]:
    """
    提交阶段占位实现。
    真实环境中此处应：
      - 从 config 读取端点与凭据（本版本不接受明文凭据）；
      - 在事务/幂等键保护下逐条提交；
      - 记录 before-state 以支持回滚。
    本版本仅写审计日志，不访问网络/数据库/生产系统。
    """
    if not config_path:
        raise RuntimeError("提交需要 --config 指定凭据配置；当前未提供，已拒绝提交。")
    if not os.path.isfile(config_path):
        raise RuntimeError(f"凭据配置文件不存在: {config_path}")

    approved_set = set(approved_ids)
    to_submit = [r for r in results if r["id"] in approved_set and r["risk"] == RISK_OK]
    receipt = {
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "STUB（占位提交：仅记录，未访问任何外部系统）",
        "count": len(to_submit),
        "ids": [r["id"] for r in to_submit],
        "warning": "此为占位实现。接入真实提交前必须补齐授权范围、生产凭据、回滚方案与人工复核。",
    }
    return receipt


# ---------------------------------------------------------------------------
# 6. 审计日志
# ---------------------------------------------------------------------------

def write_audit(report: Dict[str, Any], receipt: Dict[str, Any] = None, path: str = None) -> str:
    """将报告与回执写入审计日志文件，返回路径。"""
    if path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"audit_{ts}.jsonl")
    entries = [{"type": "report", **report}]
    if receipt:
        entries.append({"type": "receipt", **receipt})
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# 7. 主入口
# ---------------------------------------------------------------------------

def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(
        description="输入清单处理流水线（默认只读预演，不提交）"
    )
    parser.add_argument("--input", "-i", required=True, help="输入 CSV 清单路径")
    parser.add_argument("--execute", action="store_true",
                        help="真正进入提交阶段（默认关闭；仍需 --confirm-token 与 --config）")
    parser.add_argument("--confirm-token", default=None,
                        help="提交确认令牌，需与本次预演报告指纹匹配")
    parser.add_argument("--config", default=None, help="凭据配置文件路径（真实提交时必需）")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="非交互模式：仅放行 OK 项，REVIEW 项不放行")
    parser.add_argument("--report", default=None, help="报告输出路径（默认打印到屏幕）")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    # 7.1 读取
    rows, errors = load_input(args.input)
    if errors:
        for e in errors:
            logger.error(e)
        return 2

    # 7.2 校验 + 生成结果
    results = generate_results(rows)
    report = build_report(results)

    # 7.3 输出预演报告
    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report_text)
        logger.info("预演报告已写入: %s", args.report)
    else:
        print(report_text)

    # 7.4 计算报告指纹，作为提交令牌的绑定依据
    fingerprint = hashlib.sha256(
        json.dumps(report["summary"], sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    logger.info("本次预演报告指纹: %s", fingerprint)

    # 7.5 默认 dry-run：到此为止
    if not args.execute:
        audit_path = write_audit(report)
        logger.info("当前为 DRY-RUN，未提交任何内容。审计日志: %s", audit_path)
        logger.info("如需提交，请审阅报告后使用 --execute --confirm-token %s --config <凭据文件>", fingerprint)
        return 0

    # 7.6 提交路径：多重门禁
    if args.confirm_token != fingerprint:
        logger.error("确认令牌不匹配或缺失，拒绝提交。期望令牌: %s", fingerprint)
        return 3
    if not args.config:
        logger.error("缺少 --config 凭据配置，拒绝提交。")
        return 3

    allowed, approved_ids = human_gate(results, assume_yes=args.yes)
    if not allowed:
        logger.error("人工门禁未通过，终止提交。")
        audit_path = write_audit(report)
        logger.info("审计日志: %s", audit_path)
        return 4

    try:
        receipt = submit(results, approved_ids, args.config)
    except RuntimeError as e:
        logger.error("提交失败: %s", e)
        return 5

    audit_path = write_audit(report, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    logger.info("提交（占位）完成。审计日志: %s", audit_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
