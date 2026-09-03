#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLB 独立验证脚本
================
独立回读 robotic_arm.glb，验证 glTF 2.0 二进制结构完整性，
不依赖生成器内部状态，仅使用 Python 标准库。

检查项：
  1. GLB 文件头（magic / version / 总长度）
  2. Chunk 结构（JSON chunk + BIN chunk，类型与长度）
  3. JSON 合法性与 glTF 2.0 必需字段
  4. buffer / bufferView / accessor 边界一致性
  5. 索引不越界（indices < 顶点数）
  6. POSITION accessor min/max 与实际数据一致
  7. 法线为单位向量
  8. 节点引用合法性（mesh / children 索引存在）
  9. 材质合法性
  10. Skill 性能阈值（文件 <5MB，三角形 <100K）
  11. 场景节点树可遍历、无环

用法：
  python3 validate_glb.py [glb路径]
退出码：0 全部通过；1 存在失败项。
"""

import struct
import json
import sys
import os
import math


def fail(results, severity, msg):
    results.append((severity, False, msg))


def ok(results, msg):
    results.append(("PASS", True, msg))


def validate_glb(path):
    results = []
    with open(path, "rb") as f:
        data = f.read()
    file_size = len(data)

    # ---- 1. 文件头 ----
    if file_size < 12:
        fail(results, "FAIL", f"文件过小 ({file_size} 字节)，不足 GLB 头")
        return results
    magic, version, total_len = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:
        fail(results, "FAIL", f"magic 错误: 0x{magic:08X}，期望 0x46546C67 ('glTF')")
    else:
        ok(results, "GLB magic = 'glTF'")
    if version != 2:
        fail(results, "FAIL", f"version = {version}，期望 2")
    else:
        ok(results, "glTF version = 2")
    if total_len != file_size:
        fail(results, "FAIL", f"头中总长度 {total_len} != 实际文件大小 {file_size}")
    else:
        ok(results, f"总长度一致 ({total_len} 字节)")

    # ---- 2. Chunk 结构 ----
    offset = 12
    chunks = []
    while offset < file_size:
        if offset + 8 > file_size:
            fail(results, "FAIL", f"偏移 {offset}: chunk 头不完整")
            break
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        if offset + chunk_len > file_size:
            fail(results, "FAIL", f"chunk 数据越界: 需要 {chunk_len}，剩余 {file_size - offset}")
            break
        chunk_data = data[offset:offset + chunk_len]
        chunks.append((chunk_type, chunk_data))
        offset += chunk_len

    if len(chunks) < 1:
        fail(results, "FAIL", "没有 JSON chunk")
        return results
    if chunks[0][0] != 0x4E4F534A:
        fail(results, "FAIL", f"第一个 chunk 类型 0x{chunks[0][0]:08X}，期望 JSON (0x4E4F534A)")
    else:
        ok(results, "第一个 chunk 为 JSON")
    if len(chunks) >= 2:
        if chunks[1][0] != 0x004E4942:
            fail(results, "FAIL", f"第二个 chunk 类型 0x{chunks[1][0]:08X}，期望 BIN (0x004E4942)")
        else:
            ok(results, "第二个 chunk 为 BIN")
    else:
        fail(results, "WARN", "没有 BIN chunk（本模型应有几何数据）")

    # ---- 3. JSON 解析 ----
    try:
        json_str = chunks[0][1].rstrip(b" \t\r\n\x00").decode("utf-8")
        gltf = json.loads(json_str)
        ok(results, "JSON chunk 合法解析")
    except Exception as e:
        fail(results, "FAIL", f"JSON 解析失败: {e}")
        return results

    for key in ("asset", "scenes", "nodes", "meshes", "accessors", "bufferViews", "buffers"):
        if key not in gltf:
            fail(results, "FAIL", f"缺少必需顶层字段: {key}")
        else:
            ok(results, f"包含必需字段: {key}")
    if gltf.get("asset", {}).get("version") != "2.0":
        fail(results, "FAIL", "asset.version != '2.0'")
    else:
        ok(results, "asset.version = '2.0'")

    bin_data = chunks[1][1] if len(chunks) >= 2 else b""

    # ---- 4. buffer / bufferView / accessor 边界 ----
    buffers = gltf.get("buffers", [])
    buffer_views = gltf.get("bufferViews", [])
    accessors = gltf.get("accessors", [])

    for i, buf in enumerate(buffers):
        if buf["byteLength"] != len(bin_data):
            fail(results, "FAIL", f"buffer[{i}] byteLength {buf['byteLength']} != BIN chunk 长度 {len(bin_data)}")
        else:
            ok(results, f"buffer[{i}] byteLength 与 BIN chunk 一致 ({len(bin_data)})")

    for i, bv in enumerate(buffer_views):
        end = bv.get("byteOffset", 0) + bv["byteLength"]
        if end > len(bin_data):
            fail(results, "FAIL", f"bufferView[{i}] 越界: 结束 {end} > buffer {len(bin_data)}")
    ok(results, f"全部 {len(buffer_views)} 个 bufferView 在 buffer 范围内")

    comp_sizes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    type_counts = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
                   "MAT2": 4, "MAT3": 9, "MAT4": 16}

    total_tris = 0
    total_verts = 0

    for i, acc in enumerate(accessors):
        bv = buffer_views[acc["bufferView"]]
        cs = comp_sizes.get(acc["componentType"])
        nc = type_counts.get(acc["type"])
        if cs is None or nc is None:
            fail(results, "FAIL", f"accessor[{i}] componentType/type 非法")
            continue
        # 检查 accessor 计数不超过 bufferView 容量
        stride = bv.get("byteStride", cs * nc)
        available = bv["byteLength"] // stride
        if acc["count"] > available:
            fail(results, "FAIL", f"accessor[{i}] count {acc['count']} > bufferView 容量 {available}")

    ok(results, f"全部 {len(accessors)} 个 accessor 计数在 bufferView 容量内")

    # ---- 5/6/7. 逐 mesh 验证几何 ----
    meshes = gltf.get("meshes", [])
    nodes = gltf.get("nodes", [])
    materials = gltf.get("materials", [])

    for mi, mesh in enumerate(meshes):
        for pi, prim in enumerate(mesh.get("primitives", [])):
            attrs = prim.get("attributes", {})
            pos_acc_idx = attrs.get("POSITION")
            nrm_acc_idx = attrs.get("NORMAL")
            idx_acc_idx = prim.get("indices")

            if pos_acc_idx is None:
                fail(results, "FAIL", f"mesh[{mi}].prim[{pi}] 无 POSITION")
                continue
            pos_acc = accessors[pos_acc_idx]
            vcount = pos_acc["count"]
            total_verts += vcount

            # 读取位置数据
            pos_bv = buffer_views[pos_acc["bufferView"]]
            pos_off = pos_bv.get("byteOffset", 0) + pos_acc.get("byteOffset", 0)
            pos_floats = struct.unpack_from("<%df" % (vcount * 3), bin_data, pos_off)

            # 验证 min/max
            if "min" in pos_acc and "max" in pos_acc:
                for axis in range(3):
                    vals = pos_floats[axis::3]
                    mn, mx = min(vals), max(vals)
                    if abs(mn - pos_acc["min"][axis]) > 1e-5:
                        fail(results, "FAIL", f"mesh[{mi}] POSITION min[{axis}] 不匹配: {mn} vs {pos_acc['min'][axis]}")
                    if abs(mx - pos_acc["max"][axis]) > 1e-5:
                        fail(results, "FAIL", f"mesh[{mi}] POSITION max[{axis}] 不匹配: {mx} vs {pos_acc['max'][axis]}")

            # 验证法线
            if nrm_acc_idx is not None:
                nrm_acc = accessors[nrm_acc_idx]
                nrm_bv = buffer_views[nrm_acc["bufferView"]]
                nrm_off = nrm_bv.get("byteOffset", 0) + nrm_acc.get("byteOffset", 0)
                nrm_floats = struct.unpack_from("<%df" % (vcount * 3), bin_data, nrm_off)
                bad_n = 0
                for vi in range(vcount):
                    nx, ny, nz = nrm_floats[vi*3], nrm_floats[vi*3+1], nrm_floats[vi*3+2]
                    ln = math.sqrt(nx*nx + ny*ny + nz*nz)
                    if abs(ln - 1.0) > 0.05:
                        bad_n += 1
                if bad_n:
                    fail(results, "WARN", f"mesh[{mi}] 有 {bad_n} 个法线非单位向量")

            # 验证索引
            if idx_acc_idx is not None:
                idx_acc = accessors[idx_acc_idx]
                idx_bv = buffer_views[idx_acc["bufferView"]]
                idx_off = idx_bv.get("byteOffset", 0) + idx_acc.get("byteOffset", 0)
                icount = idx_acc["count"]
                if idx_acc["componentType"] == 5123:
                    indices = struct.unpack_from("<%dH" % icount, bin_data, idx_off)
                else:
                    indices = struct.unpack_from("<%dI" % icount, bin_data, idx_off)
                max_idx = max(indices)
                if max_idx >= vcount:
                    fail(results, "FAIL", f"mesh[{mi}] 索引越界: max {max_idx} >= 顶点数 {vcount}")
                tris = icount // 3
                total_tris += tris
                if prim.get("mode", 4) == 4:
                    ok(results, f"mesh[{mi}] '{mesh.get('name','')}' : {vcount} 顶点 / {tris} 三角形 / 索引合法")
            else:
                total_tris += vcount // 3

    # ---- 8. 节点引用 ----
    for ni, node in enumerate(nodes):
        if "mesh" in node:
            if not (0 <= node["mesh"] < len(meshes)):
                fail(results, "FAIL", f"node[{ni}] mesh 索引 {node['mesh']} 越界")
        if "children" in node:
            for ci in node["children"]:
                if not (0 <= ci < len(nodes)):
                    fail(results, "FAIL", f"node[{ni}] child {ci} 越界")
                if ci == ni:
                    fail(results, "FAIL", f"node[{ni}] 自引用")
        if "material" in node:
            if not (0 <= node["material"] < len(materials)):
                fail(results, "FAIL", f"node[{ni}] material 索引越界")
    ok(results, f"全部 {len(nodes)} 个节点引用合法")

    # 检查节点树无环（从场景根 DFS）
    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    visited = set()
    def dfs(ni, stack):
        if ni in stack:
            fail(results, "FAIL", f"节点树存在环 (node[{ni}])")
            return
        if ni in visited:
            return
        visited.add(ni)
        stack.add(ni)
        for ci in nodes[ni].get("children", []):
            dfs(ci, stack)
        stack.discard(ni)
    for root in scene.get("nodes", []):
        dfs(root, set())
    ok(results, f"场景节点树无环，可达 {len(visited)} 个节点")

    # ---- 9. 材质 ----
    for i, mat in enumerate(materials):
        pbr = mat.get("pbrMetallicRoughness", {})
        color = pbr.get("baseColorFactor", [1, 1, 1, 1])
        if len(color) != 4 or not all(0 <= c <= 1 for c in color):
            fail(results, "FAIL", f"material[{i}] baseColorFactor 非法: {color}")
    ok(results, f"全部 {len(materials)} 个材质颜色合法")

    # ---- 10. Skill 性能阈值 ----
    if file_size < 5 * 1024 * 1024:
        ok(results, f"文件大小 {file_size:,} 字节 < 5MB (Skill 阈值)")
    else:
        fail(results, "FAIL", f"文件大小 {file_size:,} >= 5MB")
    if total_tris < 100000:
        ok(results, f"总三角形 {total_tris:,} < 100K (Skill web 阈值)")
    else:
        fail(results, "FAIL", f"总三角形 {total_tris:,} >= 100K")
    if total_tris < 500000:
        ok(results, f"总三角形 {total_tris:,} < 500K (Skill 桌面端阈值)")

    # ---- 11. 包围盒合理性 ----
    # 汇总所有 POSITION 的世界近似范围（本地坐标）
    all_min = [float("inf")] * 3
    all_max = [float("-inf")] * 3
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            pa = accessors[prim["attributes"]["POSITION"]]
            for a in range(3):
                all_min[a] = min(all_min[a], pa["min"][a])
                all_max[a] = max(all_max[a], pa["max"][a])
    dims = [all_max[a] - all_min[a] for a in range(3)]
    ok(results, f"模型本地包围盒: X[{all_min[0]:.3f},{all_max[0]:.3f}] Y[{all_min[1]:.3f},{all_max[1]:.3f}] Z[{all_min[2]:.3f},{all_max[2]:.3f}]")
    ok(results, f"模型本地尺寸: {dims[0]:.3f} x {dims[1]:.3f} x {dims[2]:.3f} m")

    return results


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "robotic_arm.glb")

    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        sys.exit(1)

    print("=" * 64)
    print(f"独立验证: {path}")
    print("=" * 64)

    results = validate_glb(path)
    n_pass = sum(1 for _, okv, _ in results if okv)
    n_fail = sum(1 for _, okv, _ in results if not okv)

    for severity, okv, msg in results:
        tag = "PASS" if okv else severity
        symbol = "✓" if okv else ("✗" if severity == "FAIL" else "!")
        print(f"  [{symbol} {tag:4s}] {msg}")

    print("-" * 64)
    print(f"通过 {n_pass} 项，失败 {n_fail} 项")
    print("=" * 64)
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
