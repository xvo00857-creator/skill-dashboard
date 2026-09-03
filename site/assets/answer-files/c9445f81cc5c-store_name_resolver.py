# -*- coding: utf-8 -*-
"""
门店名称解析器（基于 chroma Skill）。

本模块严格使用 chroma Skill 的真实能力边界：
  - 向量嵌入 + 相似度检索（collection.query / collection.add）
  - 元数据过滤（where）
  - 持久化存储（PersistentClient）

chroma 在本方案中**只**承担一件事：把原始门店名（含中英文混写、
括号差异、空格差异等变体）通过语义相似度匹配到主数据中的规范门店。
它不负责去重、缺失值处理或数值聚合——那些由 pandas ETL 完成。

重要限制（实测）：
  chroma 默认嵌入模型为 all-MiniLM-L6-v2（见 SKILL.md "Default (Sentence
  Transformers)"），该模型以英文为主，对中文/英文品牌别名（如
  "Starbucks" vs "星巴克"）的语义对齐较弱。因此：
    1. 本解析器先做规范化精确匹配（去空格/括号/大小写），再回退到语义匹配；
    2. 语义匹配置信度不足时一律标记 UNRESOLVED 并进入人工复核，不强行归并；
    3. 生产环境建议按 SKILL.md "Custom embedding function" 一节接入
       多语言模型（如 paraphrase-multilingual-MiniLM-L12-v2）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable, Optional

import chromadb


# 距离阈值：chroma 默认返回 squared L2 distance，越小越相似。
# 该阈值需在真实主数据上抽样校准；此处给出保守默认值。
DEFAULT_DISTANCE_THRESHOLD = 0.75


def _normalize_name(name: Optional[str]) -> str:
    """规范化门店名：去空白、去常见标点/括号、转小写。仅用于精确匹配前置。"""
    if name is None:
        return ""
    s = str(name).strip().lower()
    # 去掉所有空白与常见括号/标点，保留中英文与数字
    s = re.sub(r"[\s\(\)（）\[\]【】\-—_·.,，。/\\]+", "", s)
    return s


@dataclass
class ResolveResult:
    raw_name: str
    canonical_id: Optional[str]      # None 表示未解析
    canonical_name: Optional[str]
    distance: Optional[float]        # None 表示走的精确匹配
    match_type: str                  # exact / semantic / unresolved
    resolved: bool


class StoreNameResolver:
    """对门店主数据建索引，并解析原始门店名。"""

    def __init__(
        self,
        persist_dir: str = "./chroma_store_db",
        collection_name: str = "store_master",
        distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
        reset: bool = False,
    ):
        # SKILL.md 最佳实践 1：使用 persistent client，重启不丢数据
        self._client = chromadb.PersistentClient(path=persist_dir)
        if reset:
            try:
                self._client.delete_collection(collection_name)
            except Exception:
                pass
        # SKILL.md：create_collection 不传 embedding_function 时使用默认
        # all-MiniLM-L6-v2（见 SKILL.md "Default (Sentence Transformers)"）
        self._col = self._client.get_or_create_collection(name=collection_name)
        self._threshold = distance_threshold
        # 规范化名 -> 规范门店信息，用于确定性精确匹配
        self._exact_index: dict[str, dict] = {}

    # ---------- 建索引 ----------

    def build_index(self, stores: Iterable[dict]) -> int:
        """
        stores: 可迭代对象，每个元素为 dict，至少包含：
            canonical_id, canonical_name
        可选：brand, city, area 等元数据字段。
        返回写入条数。
        """
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        count = 0
        for s in stores:
            cid = str(s["canonical_id"])
            cname = str(s["canonical_name"]).strip()
            if not cname:
                continue
            # SKILL.md 最佳实践 6：唯一 ID，避免冲突
            if cid in ids:
                continue
            ids.append(cid)
            documents.append(cname)
            meta = {"canonical_id": cid, "canonical_name": cname}
            for k in ("brand", "city", "area"):
                if s.get(k) is not None:
                    meta[k] = str(s[k])
            metadatas.append(meta)
            self._exact_index[_normalize_name(cname)] = {
                "canonical_id": cid,
                "canonical_name": cname,
            }
            count += 1

        if ids:
            # SKILL.md 最佳实践 3：批量写入
            # chroma 单次批量建议控制在几百条以内，此处按 500 切片
            for i in range(0, len(ids), 500):
                self._col.add(
                    ids=ids[i : i + 500],
                    documents=documents[i : i + 500],
                    metadatas=metadatas[i : i + 500],
                )
        return count

    # ---------- 解析 ----------

    def resolve_one(self, raw_name: Optional[str]) -> ResolveResult:
        if raw_name is None or str(raw_name).strip() == "":
            return ResolveResult(
                raw_name="" if raw_name is None else str(raw_name),
                canonical_id=None,
                canonical_name=None,
                distance=None,
                match_type="unresolved",
                resolved=False,
            )

        raw = str(raw_name).strip()
        norm = _normalize_name(raw)

        # 1) 规范化精确匹配（确定性优先，不依赖模型）
        if norm in self._exact_index:
            hit = self._exact_index[norm]
            return ResolveResult(
                raw_name=raw,
                canonical_id=hit["canonical_id"],
                canonical_name=hit["canonical_name"],
                distance=None,
                match_type="exact",
                resolved=True,
            )

        # 2) 语义相似度匹配（chroma 核心能力）
        res = self._col.query(query_texts=[raw], n_results=1)
        if not res["ids"] or not res["ids"][0]:
            return ResolveResult(raw, None, None, None, "unresolved", False)

        best_id = res["ids"][0][0]
        best_meta = res["metadatas"][0][0]
        best_dist = float(res["distances"][0][0])

        if best_dist <= self._threshold:
            return ResolveResult(
                raw_name=raw,
                canonical_id=best_meta["canonical_id"],
                canonical_name=best_meta["canonical_name"],
                distance=best_dist,
                match_type="semantic",
                resolved=True,
            )

        # 3) 置信度不足：不强行归并，进入人工复核
        return ResolveResult(
            raw_name=raw,
            canonical_id=None,
            canonical_name=None,
            distance=best_dist,
            match_type="unresolved",
            resolved=False,
        )

    def resolve_batch(self, raw_names: Iterable[Optional[str]]) -> list[ResolveResult]:
        return [self.resolve_one(n) for n in raw_names]

    def count(self) -> int:
        try:
            return self._col.count()
        except Exception:
            return 0


def result_to_dict(r: ResolveResult) -> dict:
    return asdict(r)
