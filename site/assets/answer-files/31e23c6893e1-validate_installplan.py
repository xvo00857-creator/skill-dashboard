#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InstallPlan 静态校验脚本（不依赖 kubectl / 集群）。
依据 kubesphere-extension-management SKILL.md 的 CRITICAL 规则与最佳实践：
  - metadata.name 必须等于 spec.extension.name
  - spec.extension.version 必须为精确版本（禁止 latest / recommendedVersion）
  - enabled 必须为 true
  - upgradeStrategy 必须为 Manual（生产环境）
  - 默认配置时不得包含 spec.config
  - clusterScheduling 仅在 Multicluster 模式下出现，且需含 placement.clusters
  - kind/apiVersion 正确
用法: python3 validate_installplan.py <installplan.yaml>
退出码: 0 全部通过; 1 存在失败项
"""
import sys
import yaml

PSEUDO_VERSIONS = {"latest", "recommendedversion", "recommended", "stable"}

def fail(msg, errs):
    errs.append(msg)
    print(f"  [FAIL] {msg}")

def ok(msg):
    print(f"  [PASS] {msg}")

def main():
    if len(sys.argv) != 2:
        print("用法: python3 validate_installplan.py <installplan.yaml>")
        sys.exit(2)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    errs = []
    print(f"校验文件: {path}\n")

    # 1. kind / apiVersion
    if doc.get("kind") != "InstallPlan":
        fail(f"kind 应为 InstallPlan，实际为 {doc.get('kind')!r}", errs)
    else:
        ok("kind: InstallPlan")

    if doc.get("apiVersion") != "kubesphere.io/v1alpha1":
        fail(f"apiVersion 应为 kubesphere.io/v1alpha1，实际为 {doc.get('apiVersion')!r}", errs)
    else:
        ok("apiVersion: kubesphere.io/v1alpha1")

    metadata = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    ext = spec.get("extension") or {}

    # 2. metadata.name 存在
    meta_name = metadata.get("name")
    if not meta_name:
        fail("metadata.name 缺失", errs)
    else:
        ok(f"metadata.name: {meta_name}")

    # 3. spec.extension.name 存在且与 metadata.name 一致（CRITICAL）
    ext_name = ext.get("name")
    if not ext_name:
        fail("spec.extension.name 缺失", errs)
    elif meta_name and ext_name != meta_name:
        fail(f"metadata.name({meta_name}) 与 spec.extension.name({ext_name}) 不一致（CRITICAL）", errs)
    else:
        ok(f"metadata.name == spec.extension.name: {ext_name}")

    # 4. spec.extension.version 为精确版本（CRITICAL）
    version = ext.get("version")
    if not version:
        fail("spec.extension.version 缺失", errs)
    elif str(version).strip().lower() in PSEUDO_VERSIONS:
        fail(f"version 必须为精确版本，禁止使用 {version!r}（CRITICAL）", errs)
    else:
        ok(f"spec.extension.version: {version}（精确版本）")

    # 5. enabled: true
    if spec.get("enabled") is not True:
        fail(f"spec.enabled 应为 true，实际为 {spec.get('enabled')!r}", errs)
    else:
        ok("spec.enabled: true")

    # 6. upgradeStrategy: Manual
    if spec.get("upgradeStrategy") != "Manual":
        fail(f"spec.upgradeStrategy 应为 Manual，实际为 {spec.get('upgradeStrategy')!r}", errs)
    else:
        ok("spec.upgradeStrategy: Manual")

    # 7. 默认配置：不应出现 spec.config
    if "config" in spec:
        fail("默认配置场景不应包含 spec.config（如需自定义请显式说明）", errs)
    else:
        ok("默认配置：未包含 spec.config")

    # 8. clusterScheduling 结构（若存在）
    cs = spec.get("clusterScheduling")
    if cs is not None:
        placement = cs.get("placement") or {}
        clusters = placement.get("clusters")
        if not clusters or not isinstance(clusters, list) or len(clusters) == 0:
            fail("clusterScheduling.placement.clusters 必须为非空列表", errs)
        else:
            ok(f"clusterScheduling.placement.clusters: {clusters}")
    else:
        ok("未设置 clusterScheduling（单集群 / HostOnly 模式）")

    print()
    if errs:
        print(f"结果: 失败 {len(errs)} 项")
        sys.exit(1)
    print("结果: 全部通过")
    sys.exit(0)

if __name__ == "__main__":
    main()
