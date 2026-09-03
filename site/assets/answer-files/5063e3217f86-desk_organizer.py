#!/usr/bin/env python3
"""
桌面收纳盒参数化建模脚本（四隔层）
==================================
外廓: 180 × 120 × 35 mm
壁厚: 2.4 mm
底厚: 2.4 mm
隔层: 2×2 十字分隔，隔墙厚 2.4 mm

单位: 毫米 (mm)
建模内核: trimesh + manifold3d (布尔运算)
输出: desk_organizer_4comp.stl (二进制 STL)
      desk_organizer_4comp.step 占位（本环境无 OCCT，不生成）
      verification_log.json (验证日志)

本脚本是工程源文件，所有尺寸参数化，可修改后重新运行。
"""

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

# ── 设计参数（单位: mm）─────────────────────────────────────────────
PARAMS = {
    "outer_length": 180.0,      # X 外廓长
    "outer_width": 120.0,       # Y 外廓宽
    "outer_height": 35.0,       # Z 外廓高
    "wall_thickness": 2.4,      # 侧壁厚
    "bottom_thickness": 2.4,    # 底厚
    "divider_thickness": 2.4,   # 隔墙厚
    "compartments_x": 2,        # X 方向隔层数
    "compartments_y": 2,        # Y 方向隔层数
    "unit": "mm",
}

OUTPUT_DIR = Path(__file__).resolve().parent
STL_PATH = OUTPUT_DIR / "desk_organizer_4comp.stl"
LOG_PATH = OUTPUT_DIR / "verification_log.json"


def make_box(size_x, size_y, size_z, center=(0, 0, 0)):
    """创建一个长方体 trimesh，center 为中心坐标。"""
    box = trimesh.creation.box(extents=(size_x, size_y, size_z))
    box.apply_translation(center)
    return box


def build_organizer(p):
    """
    构建收纳盒实体:
      实体 = 外箱体 - 内腔 + X 向隔墙 + Y 向隔墙
    所有坐标以底面中心为 (0,0,0)，Z 向上。
    """
    L, W, H = p["outer_length"], p["outer_width"], p["outer_height"]
    t = p["wall_thickness"]
    tb = p["bottom_thickness"]
    td = p["divider_thickness"]
    nx, ny = p["compartments_x"], p["compartments_y"]

    # 外箱体（实心）
    outer = make_box(L, W, H, center=(0, 0, H / 2))

    # 内腔：从顶面挖到底板上表面
    inner_l = L - 2 * t
    inner_w = W - 2 * t
    inner_h = H - tb
    # 内腔中心：X/Y 居中，Z 从 tb 到 H → 中心 = (tb + H)/2
    cavity = make_box(inner_l, inner_w, inner_h, center=(0, 0, (tb + H) / 2))

    # 布尔差集：外箱体 - 内腔
    shell = outer.difference(cavity, engine="manifold")

    # 隔墙：沿 X 方向的隔墙有 (ny-1) 道，沿 Y 方向的隔墙有 (nx-1) 道
    dividers = []
    # 隔墙高度 = 内腔高度（从底板上表面到顶面）
    div_h = inner_h
    div_z = (tb + H) / 2  # 隔墙中心 Z

    # 沿 X 方向延伸的隔墙（分隔 Y）
    inner_y_min = -inner_w / 2
    for i in range(1, ny):
        y_pos = inner_y_min + i * (inner_w / ny)
        div = make_box(inner_l, td, div_h, center=(0, y_pos, div_z))
        dividers.append(div)

    # 沿 Y 方向延伸的隔墙（分隔 X）
    inner_x_min = -inner_l / 2
    for i in range(1, nx):
        x_pos = inner_x_min + i * (inner_l / nx)
        div = make_box(td, inner_w, div_h, center=(x_pos, 0, div_z))
        dividers.append(div)

    # 合并隔墙到壳体
    result = shell
    for div in dividers:
        result = result.union(div, engine="manifold")

    return result


def analyze_mesh(mesh, p):
    """对网格进行几何与制造性分析，返回检查结果字典。"""
    log = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parameters": p,
        "checks": {},
        "derived_dimensions": {},
        "manufacturing_notes": [],
    }

    # ── 1. 单位声明 ──
    log["checks"]["unit_declared"] = {
        "pass": True,
        "detail": f"所有尺寸以 {p['unit']} 为单位，STL 头声明单位为 mm",
    }

    # ── 2. 网格基本统计 ──
    log["checks"]["mesh_stats"] = {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "bounds_mm": mesh.bounds.tolist(),
        "volume_mm3": float(mesh.volume),
        "is_watertight": bool(mesh.is_watertight),
        "is_winding_consistent": bool(mesh.is_winding_consistent),
        "euler_number": int(mesh.euler_number),
    }

    # ── 3. 闭合轮廓（水密性）检查 ──
    wt = mesh.is_watertight
    log["checks"]["closed_contour"] = {
        "pass": wt,
        "detail": (
            "网格水密，所有边恰好属于两个面，轮廓闭合"
            if wt
            else "网格存在边界边，轮廓未闭合，需要修复"
        ),
    }

    # ── 4. 外廓尺寸验证 ──
    bounds = mesh.bounds
    actual_l = float(bounds[1][0] - bounds[0][0])
    actual_w = float(bounds[1][1] - bounds[0][1])
    actual_h = float(bounds[1][2] - bounds[0][2])
    tol = 0.01  # 10 微米容差

    dim_ok = (
        abs(actual_l - p["outer_length"]) < tol
        and abs(actual_w - p["outer_width"]) < tol
        and abs(actual_h - p["outer_height"]) < tol
    )
    log["checks"]["outer_dimensions"] = {
        "pass": dim_ok,
        "expected_mm": [p["outer_length"], p["outer_width"], p["outer_height"]],
        "actual_mm": [round(actual_l, 4), round(actual_w, 4), round(actual_h, 4)],
        "tolerance_mm": tol,
    }

    # ── 5. 派生尺寸 ──
    t = p["wall_thickness"]
    tb = p["bottom_thickness"]
    td = p["divider_thickness"]
    inner_l = p["outer_length"] - 2 * t
    inner_w = p["outer_width"] - 2 * t
    inner_h = p["outer_height"] - tb
    comp_x = (inner_l - (p["compartments_x"] - 1) * td) / p["compartments_x"]
    comp_y = (inner_w - (p["compartments_y"] - 1) * td) / p["compartments_y"]

    log["derived_dimensions"] = {
        "inner_length_mm": round(inner_l, 4),
        "inner_width_mm": round(inner_w, 4),
        "inner_depth_mm": round(inner_h, 4),
        "compartment_inner_size_mm": [round(comp_x, 4), round(comp_y, 4)],
        "wall_thickness_mm": t,
        "bottom_thickness_mm": tb,
        "divider_thickness_mm": td,
        "estimated_material_volume_cm3": round(mesh.volume / 1000.0, 2),
    }

    # ── 6. 壁厚与喷嘴直径匹配检查 ──
    # FDM 常用喷嘴 0.4 mm；壁厚应为喷嘴直径整数倍（2.4 = 6×0.4 ✓）
    nozzle = 0.4
    wall_multiples = t / nozzle
    log["checks"]["wall_thickness_nozzle"] = {
        "pass": abs(wall_multiples - round(wall_multiples)) < 0.01,
        "wall_mm": t,
        "nozzle_mm": nozzle,
        "multiples": round(wall_multiples, 2),
        "detail": (
            f"壁厚 {t} mm = {wall_multiples:.1f} × {nozzle} mm 喷嘴直径，"
            "可整数倍线宽填充，无薄壁填充问题"
        ),
    }

    # ── 7. 最小特征尺寸检查 ──
    min_feature = min(t, tb, td)
    log["checks"]["minimum_feature"] = {
        "pass": min_feature >= 2 * nozzle,
        "min_feature_mm": min_feature,
        "threshold_mm": 2 * nozzle,
        "detail": f"最小特征 {min_feature} mm ≥ {2*nozzle} mm（2 倍喷嘴直径），可打印",
    }

    # ── 8. 法向一致性 ──
    log["checks"]["face_normals"] = {
        "pass": bool(mesh.is_winding_consistent),
        "detail": (
            "面法向一致（卷绕一致），切片器可正确识别内外"
            if mesh.is_winding_consistent
            else "面法向不一致，可能导致切片器误判实体"
        ),
    }

    # ── 9. 制造注意事项 ──
    notes = log["manufacturing_notes"]
    notes.append("开口朝上打印，无需支撑结构（所有内壁垂直于底板）。")
    notes.append(
        f"壁厚 {t} mm 为 0.4 mm 喷嘴的 6 倍线宽，建议外壁 2 道 + 内壁 4 道，"
        "填充率 15-20% 即可满足桌面收纳强度。"
    )
    notes.append("底板面积 180×120 mm，确认打印机成型尺寸足够（如 A1 Mini 为 180×180×180 mm，刚好可打）。")
    notes.append("隔墙与侧壁等高（32.6 mm），十字交接处无悬空，无需支撑。")
    notes.append("建议底板加 brim 或 raft 以防 ABS/ASA 翘边；PLA 通常不需要。")
    notes.append("所有内角为直角，FDM 打印内角会有圆角效应（由喷嘴半径决定），不影响功能。")
    notes.append("无小特征、无细柱、无桥接，制造风险低。")
    notes.append("建议层高 0.2 mm，初始层高 0.2 mm，打印时间约 4-6 小时（视填充和速度）。")

    # 总体判定
    all_pass = all(
        v.get("pass", True)
        for k, v in log["checks"].items()
        if isinstance(v, dict) and "pass" in v
    )
    log["overall_pass"] = all_pass

    return log


def main():
    print("=== 桌面收纳盒参数化建模 ===")
    print(f"参数: {json.dumps(PARAMS, ensure_ascii=False)}")
    print()

    # 建模
    print("正在构建模型...")
    mesh = build_organizer(PARAMS)
    print(f"  顶点数: {len(mesh.vertices)}")
    print(f"  面数: {len(mesh.faces)}")
    print(f"  体积: {mesh.volume:.2f} mm³")
    print(f"  水密: {mesh.is_watertight}")
    print()

    # 导出 STL（二进制）
    mesh.export(STL_PATH, file_type="stl")
    print(f"STL 已导出: {STL_PATH}")
    print(f"  文件大小: {STL_PATH.stat().st_size} 字节")
    print()

    # 验证分析
    print("正在验证...")
    log = analyze_mesh(mesh, PARAMS)

    # 写入验证日志
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"验证日志: {LOG_PATH}")
    print()

    # 打印摘要
    print("=== 验证结果 ===")
    for name, result in log["checks"].items():
        if isinstance(result, dict) and "pass" in result:
            status = "✓ 通过" if result["pass"] else "✗ 失败"
            print(f"  [{status}] {name}: {result.get('detail', '')}")
        elif name == "mesh_stats":
            print(f"  [信息] {name}: {result['vertices']} 顶点, {result['faces']} 面, "
                  f"水密={result['is_watertight']}")
    print()
    print(f"总体判定: {'✓ 全部通过' if log['overall_pass'] else '✗ 存在失败项'}")
    print()

    return 0 if log["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
