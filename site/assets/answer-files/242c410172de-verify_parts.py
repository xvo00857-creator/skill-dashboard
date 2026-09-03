#!/usr/bin/env python3
"""可重复的 STEP 零件校验脚本：从 api.step.parts 拉取记录，比对本地文件 SHA-256 与 STEP 文件头。

仅依赖 Python 3 标准库，无需安装任何第三方包。

用法：
    python3 verify_parts.py                # 校验同目录下所有 .step 文件
    python3 verify_parts.py <目录>         # 校验指定目录
    python3 verify_parts.py --offline      # 使用同目录 manifest.json 离线校验（不联网）

校验逻辑：
    1. 按零件 ID 从 API 获取记录（在线模式）或读取 manifest.json（离线模式）
    2. 计算本地 .step 文件 SHA-256，与记录中的 sha256 比对
    3. 检查文件头是否为 ISO-10303-21（合法 STEP 文件）
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

API_ORIGIN = "https://api.step.parts"
USER_AGENT = "step-parts-skill/1.0"
TIMEOUT = 30.0

# 本次小型传送机构选用的零件 ID
PART_IDS = [
    "bearing_608zz",
    "iso4762_socket_head_cap_screw_m3x12",
    "iso4032_hex_nut_m3",
    "din125_flat_washer_m3",
    "din913_set_screw_m3x4",
    "hex_standoff_m3_12mm_male_female",
    "gt2_pulley_16t_bore5_w6",
    "gt2_pulley_20t_bore8_w6",
    "stepper_motor_nema17_l0040_single_shaft",
    "nema17_l_bracket",
    "z_axis_coupling_5x8mm",
    "sk8_sc8uu_8mm_linear_rail_shaft_support",
]


def fetch_record(part_id: str) -> dict:
    url = f"{API_ORIGIN}/v1/parts/{part_id}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_step_file(path: Path) -> bool:
    try:
        with path.open("r", errors="replace") as f:
            return f.readline().strip().startswith("ISO-10303-21")
    except OSError:
        return False


def main() -> int:
    offline = "--offline" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--offline"]
    target_dir = Path(args[0]) if args else Path(__file__).resolve().parent
    if not target_dir.is_dir():
        print(f"目录不存在: {target_dir}")
        return 2

    manifest_path = target_dir / "manifest.json"
    manifest: dict[str, dict] = {}

    if offline:
        if not manifest_path.exists():
            print(f"离线模式需要 {manifest_path}，请先在线运行一次生成清单。")
            return 2
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        print(f"离线校验模式，使用清单: {manifest_path}")
    else:
        print(f"在线校验模式，API: {API_ORIGIN}")

    results = []
    all_ok = True

    for part_id in PART_IDS:
        path = target_dir / f"{part_id}.step"
        row: dict = {"id": part_id, "file": path.name}

        if not path.exists():
            row.update(status="缺失", checksum_ok=False, header_ok=False)
            all_ok = False
            results.append(row)
            continue

        local_hash = sha256_file(path)
        header_ok = is_step_file(path)

        if offline:
            rec = manifest.get(part_id, {})
            expected_hash = rec.get("sha256")
            name = rec.get("name", "")
            page_url = rec.get("pageUrl", "")
        else:
            try:
                rec = fetch_record(part_id)
                expected_hash = rec.get("sha256")
                name = rec.get("name", "")
                page_url = rec.get("pageUrl", "")
                manifest[part_id] = {
                    "name": name,
                    "sha256": expected_hash,
                    "pageUrl": page_url,
                    "apiUrl": rec.get("apiUrl"),
                    "stepUrl": rec.get("stepUrl"),
                    "byteSize": rec.get("byteSize"),
                }
            except Exception as exc:  # noqa: BLE001
                row.update(status=f"API错误({exc})", checksum_ok=False, header_ok=header_ok)
                all_ok = False
                results.append(row)
                continue

        checksum_ok = expected_hash == local_hash
        ok = checksum_ok and header_ok
        if not ok:
            all_ok = False

        row.update(
            status="通过" if ok else "失败",
            name=name,
            size_bytes=path.stat().st_size,
            local_sha256=local_hash,
            expected_sha256=expected_hash,
            checksum_ok=checksum_ok,
            header_ok=header_ok,
            page_url=page_url,
        )
        results.append(row)

    if not offline:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"已写入清单: {manifest_path}")

    print()
    for r in results:
        print(f"[{r['status']}] {r['id']}  {r.get('name', '')}")
        print(f"    文件: {r['file']}  ({r.get('size_bytes', '?')} 字节)")
        print(f"    STEP 文件头: {'OK' if r['header_ok'] else '异常'}")
        print(f"    SHA-256 校验: {'OK' if r['checksum_ok'] else '不匹配'}")
        if r.get("page_url"):
            print(f"    来源页面: {r['page_url']}")

    print()
    print(f"总计 {len(results)} 个零件，全部通过: {all_ok}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
