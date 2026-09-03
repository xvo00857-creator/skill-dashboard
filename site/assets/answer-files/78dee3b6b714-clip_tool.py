#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clip_tool.py — 受约束的 CLIP 命令行工具（零样本分类 / 语义图搜 / 图像去重）

设计原则（依据 clip Skill 的 SKILL.md）：
  - 默认模型 ViT-B/32（SKILL.md 推荐：Good balance）
  - 嵌入向量一律 L2 归一化后再算余弦相似度（SKILL.md：Required for cosine similarity）
  - 标签使用描述性写法 "a photo of ..."（SKILL.md：Better zero-shot performance）
  - 批处理、缓存嵌入（SKILL.md：More efficient / Expensive to recompute）
  - 不做细粒度识别、不输出边界框、不做位置/计数判断（SKILL.md Limitations）

安全与约束：
  - 默认只读取指定图片、只写入项目本地缓存目录与输出文件，不触碰外部资源
  - 首次下载模型权重（约 338MB，来自 OpenAI）需显式 --accept-model-download 确认
  - 去重默认只报告不删除；删除需同时传 --apply 与 --i-understand-delete
  - 所有破坏性/外发动作都有开关，缺省拒绝
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# ----------------------------- 预检：依赖 -----------------------------
_MISSING = []
try:
    import torch
except ImportError:
    _MISSING.append("torch")
try:
    import clip
except ImportError:
    _MISSING.append("clip (pip install git+https://github.com/openai/CLIP.git)")
try:
    from PIL import Image
except ImportError:
    _MISSING.append("pillow")
try:
    import numpy as np
except ImportError:
    _MISSING.append("numpy")

VALID_MODELS = ["RN50", "RN101", "ViT-B/32", "ViT-B/16", "ViT-L/14"]
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}


def ep(msg):
    print(msg, file=sys.stderr, flush=True)


# ----------------------------- 重试装饰器 -----------------------------
def retry(fn, attempts=3, base_delay=1.5, desc="操作"):
    """对瞬时失败（网络/IO）做指数退避重试；最后一次仍失败则抛出。"""
    last = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if i == attempts:
                break
            delay = base_delay * (2 ** (i - 1))
            ep(f"[重试] {desc}第 {i} 次失败：{e}；{delay:.1f}s 后重试…")
            time.sleep(delay)
    raise last


# ----------------------------- 缓存（幂等） -----------------------------
class EmbeddingCache:
    """
    以 (模型名, 文件内容 sha256) 为键缓存图像嵌入；以 (模型名, 文本集合 sha256) 缓存文本嵌入。
    文件未变化则命中，不重复编码（幂等）。
    """

    def __init__(self, cache_dir: Path, model_name: str):
        self.cache_dir = Path(cache_dir)
        self.model_name = model_name
        self.safe_model = model_name.replace("/", "_")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _sha256_bytes(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()

    def _img_cache_path(self, path: Path) -> Path:
        key = self._sha256_file(path)
        return self.cache_dir / f"img_{self.safe_model}_{key}.npy"

    def _text_cache_path(self, labels) -> Path:
        raw = "\x1f".join(labels).encode("utf-8")
        key = self._sha256_bytes(raw)
        return self.cache_dir / f"txt_{self.safe_model}_{key}.npy"

    def get_image(self, path: Path):
        p = self._img_cache_path(path)
        if p.exists():
            return np.load(p)
        return None

    def put_image(self, path: Path, vec: np.ndarray):
        np.save(self._img_cache_path(path), vec)

    def get_text(self, labels):
        p = self._text_cache_path(labels)
        if p.exists():
            return np.load(p)
        return None

    def put_text(self, labels, vec: np.ndarray):
        np.save(self._text_cache_path(labels), vec)


# ----------------------------- 模型加载（含下载确认门） -----------------------------
def _model_checkpoint_path(model_name: str) -> Path:
    # clip 内部把权重下载到 ~/.cache/clip/<safe>.pt
    safe = model_name.replace("/", "-")
    return Path.home() / ".cache" / "clip" / f"{safe}.pt"


def load_model(model_name: str, accept_download: bool, device_override=None):
    if model_name not in VALID_MODELS:
        raise ValueError(f"不支持的模型 {model_name}，可选：{VALID_MODELS}")

    ckpt = _model_checkpoint_path(model_name)
    if not ckpt.exists():
        size_note = "ViT-L/14 约 890MB" if model_name == "ViT-L/14" else "约 338-350MB"
        msg = (
            f"[人工确认点] 模型权重 {model_name} 不在本地（期望路径 {ckpt}）。\n"
            f"  首次运行需从 OpenAI 下载，{size_note}，将写入 {ckpt.parent}。\n"
            f"  如同意下载并写入该缓存目录，请加 --accept-model-download 重新运行。"
        )
        if not accept_download:
            ep(msg)
            sys.exit(3)
        ep(f"[确认] 已获授权，开始下载模型权重 {model_name} …")

    if device_override:
        device = device_override
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        ep("[预检] 未检测到 GPU，使用 CPU 运行（按 SKILL.md 性能表，编码约慢 10 倍，结果一致）。")

    # clip.load 内部自带下载；包一层重试以应对网络抖动
    model, preprocess = retry(
        lambda: clip.load(model_name, device=device),
        attempts=3, base_delay=2.0, desc="模型加载/下载",
    )
    model.eval()
    return model, preprocess, device


# ----------------------------- 图像收集与编码 -----------------------------
def collect_images(inputs):
    files = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            for f in sorted(p.iterdir()):
                if f.suffix.lower() in IMG_EXTS:
                    files.append(f)
        elif p.is_file() and p.suffix.lower() in IMG_EXTS:
            files.append(p)
        else:
            ep(f"[预检] 跳过不可用路径：{item}")
    return files


def encode_images(model, preprocess, device, paths, cache: EmbeddingCache, batch_size=8):
    """对图片编码，命中缓存则跳过；坏图跳过并记录。返回 (path->vec 字典, 坏图列表)。"""
    result = {}
    bad = []
    to_encode = []
    for p in paths:
        cached = cache.get_image(p)
        if cached is not None:
            result[str(p)] = cached
        else:
            to_encode.append(p)

    for start in range(0, len(to_encode), batch_size):
        batch_paths = to_encode[start:start + batch_size]
        tensors = []
        ok_paths = []
        for p in batch_paths:
            try:
                with Image.open(p) as im:
                    im = im.convert("RGB")
                    tensors.append(preprocess(im))
                ok_paths.append(p)
            except Exception as e:  # noqa: BLE001
                ep(f"[跳过] 无法读取图片 {p}：{e}")
                bad.append({"path": str(p), "error": str(e)})
        if not tensors:
            continue
        batch = torch.stack(tensors).to(device)
        with torch.no_grad():
            feats = model.encode_image(batch)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        feats_np = feats.cpu().numpy().astype("float32")
        for p, vec in zip(ok_paths, feats_np):
            cache.put_image(p, vec)
            result[str(p)] = vec
    return result, bad


def encode_texts(model, device, labels, cache: EmbeddingCache):
    cached = cache.get_text(labels)
    if cached is not None:
        return cached
    tokens = clip.tokenize(labels).to(device)
    with torch.no_grad():
        feats = model.encode_text(tokens)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    vec = feats.cpu().numpy().astype("float32")
    cache.put_text(labels, vec)
    return vec


# ----------------------------- 子命令：classify -----------------------------
def cmd_classify(args):
    files = collect_images(args.images)
    if not files:
        ep("[预检] 没有可用图片。"); sys.exit(2)
    labels = list(args.labels)
    if args.describe:
        labels = [f"a photo of {l}" for l in labels]
    ep(f"[预检] 图片 {len(files)} 张，标签 {len(labels)} 个：{labels}")

    model, preprocess, device = load_model(args.model, args.accept_model_download, args.device)
    cache = EmbeddingCache(Path(args.cache_dir), args.model)
    img_vecs, bad = encode_images(model, preprocess, device, files, cache, args.batch_size)
    txt_vecs = encode_texts(model, device, labels, cache)

    import numpy as _np
    results = []
    for path, vec in img_vecs.items():
        sims = vec @ txt_vecs.T  # 余弦相似度（已归一化）
        # CLIP 标准做法：softmax(logits)，这里用 100*sims 作为 logits 温度
        logits = sims * 100.0
        probs = _np.exp(logits) / _np.exp(logits).sum(axis=-1, keepdims=True)
        order = probs.argsort()[::-1]
        results.append({
            "image": path,
            "predicted": labels[int(order[0])],
            "confidence": float(probs[order[0]]),
            "scores": {labels[i]: float(probs[i]) for i in order},
        })

    out = {
        "command": "classify", "model": args.model, "device": device,
        "labels": labels, "results": results, "bad_images": bad,
        "cached_image_count": len(files) - len(bad),
    }
    _emit(out, args.out)
    return 0 if not bad or args.allow_bad else 1


# ----------------------------- 子命令：search -----------------------------
def cmd_search(args):
    files = collect_images(args.images)
    if not files:
        ep("[预检] 没有可用图片。"); sys.exit(2)
    query = args.query.strip()
    if not query:
        ep("[预检] 查询文本为空。"); sys.exit(2)
    queries = [query]
    if args.describe:
        queries = [f"a photo of {query}"]
    ep(f"[预检] 图片 {len(files)} 张，查询：{queries[0]}")

    model, preprocess, device = load_model(args.model, args.accept_model_download, args.device)
    cache = EmbeddingCache(Path(args.cache_dir), args.model)
    img_vecs, bad = encode_images(model, preprocess, device, files, cache, args.batch_size)
    qvec = encode_texts(model, device, queries, cache)[0]

    scored = []
    for path, vec in img_vecs.items():
        scored.append({"image": path, "similarity": float(vec @ qvec)})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top = scored[: args.top_k]

    out = {
        "command": "search", "model": args.model, "device": device,
        "query": queries[0], "top_k": args.top_k, "results": top,
        "bad_images": bad,
    }
    _emit(out, args.out)
    return 0 if not bad or args.allow_bad else 1


# ----------------------------- 子命令：dedup（默认只报告） -----------------------------
def cmd_dedup(args):
    files = collect_images(args.images)
    if len(files) < 2:
        ep("[预检] 去重至少需要 2 张图片。"); sys.exit(2)
    ep(f"[预检] 图片 {len(files)} 张，阈值 {args.threshold}")

    model, preprocess, device = load_model(args.model, args.accept_model_download, args.device)
    cache = EmbeddingCache(Path(args.cache_dir), args.model)
    img_vecs, bad = encode_images(model, preprocess, device, files, cache, args.batch_size)

    import numpy as _np
    paths = list(img_vecs.keys())
    mat = _np.stack([img_vecs[p] for p in paths])
    sims = mat @ mat.T
    pairs = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            s = float(sims[i, j])
            if s >= args.threshold:
                pairs.append({"image_a": paths[i], "image_b": paths[j], "similarity": s})
    pairs.sort(key=lambda x: x["similarity"], reverse=True)

    deleted = []
    if pairs and args.apply:
        if not args.i_understand_delete:
            ep("[人工确认点] 检测到 --apply 但未提供 --i-understand-delete，拒绝删除。仅输出报告。")
        else:
            # 保守策略：每对中删除排序靠后者（后者更可能是后加入的副本）
            seen_keep = set()
            for pair in pairs:
                a, b = pair["image_a"], pair["image_b"]
                # 若 a 已被删，则保留 b
                keeper, victim = (b, a) if a in seen_keep else (a, b)
                seen_keep.add(keeper)
                if victim in seen_keep:
                    continue
                try:
                    os.remove(victim)  # 唯一的删除动作，受双重开关保护
                    deleted.append(victim)
                    seen_keep.add(victim)
                    ep(f"[删除] {victim}（与 {keeper} 相似度 {pair['similarity']:.3f}）")
                except OSError as e:
                    ep(f"[删除失败] {victim}：{e}")
    elif pairs:
        ep("[人工确认点] 默认 dry-run，仅列出疑似重复对，不删除任何文件。"
           "确认要删除需加 --apply --i-understand-delete。")

    out = {
        "command": "dedup", "model": args.model, "device": device,
        "threshold": args.threshold, "pairs": pairs, "deleted": deleted,
        "bad_images": bad, "dry_run": not (args.apply and args.i_understand_delete),
    }
    _emit(out, args.out)
    return 0


# ----------------------------- 子命令：preflight（不加载模型） -----------------------------
def cmd_preflight(args):
    info = {
        "python": sys.version.split()[0],
        "torch": getattr(torch, "__version__", "missing") if "torch" in sys.modules else "missing",
        "clip": "ok" if "clip" in sys.modules else "missing",
        "pillow": "ok" if "PIL" in sys.modules else "missing",
        "numpy": "ok" if "numpy" in sys.modules else "missing",
        "cuda_available": bool(torch.cuda.is_available()) if "torch" in sys.modules else False,
        "model": args.model,
        "checkpoint_exists": _model_checkpoint_path(args.model).exists(),
        "cache_dir": str(Path(args.cache_dir).resolve()),
        "cache_dir_writable": os.access(Path(args.cache_dir).resolve() if Path(args.cache_dir).exists()
                                        else Path(args.cache_dir).resolve().parent, os.W_OK),
    }
    if _MISSING:
        info["missing_dependencies"] = _MISSING
    files = collect_images(args.images) if args.images else []
    info["images_found"] = len(files)
    info["images"] = [str(f) for f in files]
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if not _MISSING else 1


# ----------------------------- 输出 -----------------------------
def _emit(obj, out_path):
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
        ep(f"[输出] 结果已写入 {out_path}")
    print(text)


# ----------------------------- CLI -----------------------------
def build_parser():
    p = argparse.ArgumentParser(description="受约束的 CLIP 工具：零样本分类 / 语义图搜 / 图像去重")
    p.add_argument("--model", default="ViT-B/32", choices=VALID_MODELS, help="模型（默认 ViT-B/32）")
    p.add_argument("--cache-dir", default=".clip_cache", help="嵌入缓存目录（默认项目本地 .clip_cache）")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--device", default=None, help="强制设备 cpu/cuda，默认自动")
    p.add_argument("--accept-model-download", action="store_true",
                   help="人工确认：允许首次从 OpenAI 下载模型权重")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("classify", help="零样本图像分类")
    pc.add_argument("--images", nargs="+", required=True, help="图片文件或目录")
    pc.add_argument("--labels", nargs="+", required=True, help="候选类别文本")
    pc.add_argument("--describe", action="store_true", help='自动给标签加 "a photo of " 前缀')
    pc.add_argument("--out", default=None)
    pc.add_argument("--allow-bad", action="store_true", help="存在坏图时仍返回 0")
    pc.set_defaults(func=cmd_classify)

    ps = sub.add_parser("search", help="语义图搜：文本查询找最相似图片")
    ps.add_argument("--images", nargs="+", required=True)
    ps.add_argument("--query", required=True)
    ps.add_argument("--describe", action="store_true")
    ps.add_argument("--top-k", type=int, default=3)
    ps.add_argument("--out", default=None)
    ps.add_argument("--allow-bad", action="store_true")
    ps.set_defaults(func=cmd_search)

    pd = sub.add_parser("dedup", help="图像去重（默认 dry-run 不删除）")
    pd.add_argument("--images", nargs="+", required=True)
    pd.add_argument("--threshold", type=float, default=0.95)
    pd.add_argument("--apply", action="store_true", help="真正执行删除（需配合 --i-understand-delete）")
    pd.add_argument("--i-understand-delete", action="store_true")
    pd.add_argument("--out", default=None)
    pd.set_defaults(func=cmd_dedup)

    pp = sub.add_parser("preflight", help="只做预检，不加载模型")
    pp.add_argument("--images", nargs="*", default=[])
    pp.set_defaults(func=cmd_preflight)
    return p


def main():
    if _MISSING:
        ep(f"[预检失败] 缺少依赖：{_MISSING}")
        ep("请在虚拟环境中安装：pip install ftfy regex tqdm git+https://github.com/openai/CLIP.git")
        if "--help" not in sys.argv and "preflight" not in sys.argv:
            sys.exit(2)
    args = build_parser().parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
