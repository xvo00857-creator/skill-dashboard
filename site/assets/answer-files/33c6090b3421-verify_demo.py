#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_demo.py — 对演示结果做确定性核验（不重新跑模型，只校验已保存的 JSON）。
用法：.venv/bin/python verify_demo.py
退出码 0 表示全部通过。
"""
import json, sys
from pathlib import Path

R = Path("results")
checks = []

def check(name, cond, detail=""):
    checks.append((name, bool(cond), detail))

# 1) 分类结果：每张图的预测标签与置信度
cls = json.loads((R / "classify.json").read_text(encoding="utf-8"))
expected = {
    "demo_images/dog.jpg": "a photo of dog",
    "demo_images/cat.jpg": "a photo of cat",
    "demo_images/car.jpg": "a photo of car",
    "demo_images/sunset.jpg": "a photo of sunset over the ocean",
}
pred = {r["image"]: r for r in cls["results"]}
for img, label in expected.items():
    check(f"分类正确[{img}]", pred.get(img, {}).get("predicted") == label,
          f"got={pred.get(img, {}).get('predicted')}")
    check(f"置信度>=0.9[{img}]", pred.get(img, {}).get("confidence", 0) >= 0.9,
          f"conf={pred.get(img, {}).get('confidence')}")
check("分类无坏图", cls["bad_images"] == [])
check("分类模型为 ViT-B/32", cls["model"] == "ViT-B/32")

# 2) 语义图搜：furry animal 查询应把狗/猫排在车/海前面
srch = json.loads((R / "search.json").read_text(encoding="utf-8"))
order = [Path(r["image"]).name for r in srch["results"]]
rank_dog = order.index("dog.jpg"); rank_cat = order.index("cat.jpg")
rank_car = order.index("car.jpg"); rank_sun = order.index("sunset.jpg")
check("图搜：狗/猫排在车之前", rank_dog < rank_car and rank_cat < rank_car, str(order))
check("图搜：狗/猫排在日落之前", rank_dog < rank_sun and rank_cat < rank_sun, str(order))

# 3) 去重 dry-run：未删除任何文件
dd = json.loads((R / "dedup.json").read_text(encoding="utf-8"))
check("去重为 dry_run", dd["dry_run"] is True)
check("去重未删除文件", dd["deleted"] == [])

# 4) 幂等：第二次分类结果与第一次一致
cls2 = json.loads((R / "classify2.json").read_text(encoding="utf-8"))
p1 = {r["image"]: r["predicted"] for r in cls["results"]}
p2 = {r["image"]: r["predicted"] for r in cls2["results"]}
check("幂等：两次分类预测一致", p1 == p2, f"{p1} vs {p2}")

# 5) 缓存文件存在
import os
cache_files = list(Path(".clip_cache").glob("*.npy"))
check("缓存目录有嵌入文件", len(cache_files) >= 4, f"{len(cache_files)} files")

# 输出
ok = 0
for name, passed, detail in checks:
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {name}" + (f"  ({detail})" if detail and not passed else ""))
    ok += passed
print(f"\n{ok}/{len(checks)} 项通过")
sys.exit(0 if ok == len(checks) else 1)
