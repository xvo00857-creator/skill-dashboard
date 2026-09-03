#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kubesphere-openkruise Skill 本地合规性校验脚本

依据 kubesphere-openkruise/SKILL.md 的硬性规则，对交付的 manifest 做离线校验。
不连接任何集群、不执行 kubectl，仅校验 YAML 语法与 Skill 规则。

用法：
    python3 validate_manifests.py [manifest_dir]
退出码：0 全部通过；1 存在失败项。
"""
import sys
import os
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = HERE

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    mark = "✓" if condition else "✗"
    line = f"[{mark}] {name}"
    if not condition and detail:
        line += f" —— {detail}"
    print(line)


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_installplan(doc):
    check("InstallPlan: apiVersion=kubesphere.io/v1alpha1",
          doc.get("apiVersion") == "kubesphere.io/v1alpha1",
          f"实际为 {doc.get('apiVersion')}")
    check("InstallPlan: kind=InstallPlan",
          doc.get("kind") == "InstallPlan",
          f"实际为 {doc.get('kind')}")

    metadata = doc.get("metadata", {}) or {}
    spec = doc.get("spec", {}) or {}
    extension = spec.get("extension", {}) or {}

    # SKILL.md 第40行：metadata.name MUST equal spec.extension.name
    check("InstallPlan: metadata.name == spec.extension.name",
          metadata.get("name") == extension.get("name"),
          f"metadata.name={metadata.get('name')}, extension.name={extension.get('name')}")
    check("InstallPlan: 扩展名为 openkruise",
          extension.get("name") == "openkruise",
          f"实际为 {extension.get('name')}")
    check("InstallPlan: 扩展版本为 1.0.3（本环境默认）",
          extension.get("version") == "1.0.3",
          f"实际为 {extension.get('version')}")
    check("InstallPlan: upgradeStrategy=Manual",
          spec.get("upgradeStrategy") == "Manual",
          f"实际为 {spec.get('upgradeStrategy')}")
    # SKILL.md 第41行：cluster-scoped，不加 namespace
    check("InstallPlan: 集群作用域，metadata.namespace 不存在",
          "namespace" not in metadata,
          f"namespace={metadata.get('namespace')}")
    check("InstallPlan: spec.enabled=true",
          spec.get("enabled") is True,
          f"实际为 {spec.get('enabled')}")
    clusters = (((spec.get("clusterScheduling") or {}).get("placement") or {}).get("clusters"))
    check("InstallPlan: clusterScheduling.placement.clusters 非空",
          isinstance(clusters, list) and len(clusters) > 0,
          f"实际为 {clusters}")
    # SKILL.md 第43行：省略可选字段而非猜测；本示例未要求自定义 config
    check("InstallPlan: 未臆造 spec.config（无自定义需求时省略）",
          "config" not in spec,
          "检测到 config 字段，需确认是否有 chart values 依据")


def validate_sidecarset(doc):
    check("SidecarSet: apiVersion=apps.kruise.io/v1alpha1",
          doc.get("apiVersion") == "apps.kruise.io/v1alpha1",
          f"实际为 {doc.get('apiVersion')}")
    check("SidecarSet: kind=SidecarSet",
          doc.get("kind") == "SidecarSet",
          f"实际为 {doc.get('kind')}")
    metadata = doc.get("metadata", {}) or {}
    spec = doc.get("spec", {}) or {}
    check("SidecarSet: metadata.name=log-agent",
          metadata.get("name") == "log-agent",
          f"实际为 {metadata.get('name')}")
    selector = ((spec.get("selector") or {}).get("matchLabels")) or {}
    check("SidecarSet: selector.matchLabels.app=demo",
          selector.get("app") == "demo",
          f"实际为 {selector.get('app')}")
    ns_selector = ((spec.get("namespaceSelector") or {}).get("matchLabels")) or {}
    check("SidecarSet: namespaceSelector.matchLabels 存在",
          len(ns_selector) > 0,
          f"实际为 {ns_selector}")
    containers = spec.get("containers") or []
    check("SidecarSet: 至少一个容器", len(containers) >= 1, f"容器数={len(containers)}")
    if containers:
        c0 = containers[0]
        check("SidecarSet: 容器镜像 fluent/fluent-bit:2.2",
              c0.get("image") == "fluent/fluent-bit:2.2",
              f"实际为 {c0.get('image')}")
    us = spec.get("updateStrategy") or {}
    check("SidecarSet: updateStrategy.type=RollingUpdate",
          us.get("type") == "RollingUpdate",
          f"实际为 {us.get('type')}")


def validate_cloneset(doc):
    check("CloneSet: apiVersion=apps.kruise.io/v1alpha1",
          doc.get("apiVersion") == "apps.kruise.io/v1alpha1",
          f"实际为 {doc.get('apiVersion')}")
    check("CloneSet: kind=CloneSet",
          doc.get("kind") == "CloneSet",
          f"实际为 {doc.get('kind')}")
    metadata = doc.get("metadata", {}) or {}
    spec = doc.get("spec", {}) or {}
    check("CloneSet: metadata.name=sample-app",
          metadata.get("name") == "sample-app",
          f"实际为 {metadata.get('name')}")
    check("CloneSet: namespace=demo-project",
          metadata.get("namespace") == "demo-project",
          f"实际为 {metadata.get('namespace')}")
    check("CloneSet: replicas=3",
          spec.get("replicas") == 3,
          f"实际为 {spec.get('replicas')}")
    selector = ((spec.get("selector") or {}).get("matchLabels")) or {}
    check("CloneSet: selector.matchLabels.app=sample-app",
          selector.get("app") == "sample-app",
          f"实际为 {selector.get('app')}")
    containers = (((spec.get("template") or {}).get("spec") or {}).get("containers")) or []
    check("CloneSet: 至少一个容器", len(containers) >= 1, f"容器数={len(containers)}")
    if containers:
        check("CloneSet: 容器镜像 nginx:1.25",
              containers[0].get("image") == "nginx:1.25",
              f"实际为 {containers[0].get('image')}")
    us = spec.get("updateStrategy") or {}
    check("CloneSet: updateStrategy.type=InPlaceIfPossible",
          us.get("type") == "InPlaceIfPossible",
          f"实际为 {us.get('type')}")
    check("CloneSet: updateStrategy.maxUnavailable=1",
          us.get("maxUnavailable") == 1,
          f"实际为 {us.get('maxUnavailable')}")


VALIDATORS = {
    "installplan-openkruise.yaml": validate_installplan,
    "sidecarset-log-agent.yaml": validate_sidecarset,
    "cloneset-sample-app.yaml": validate_cloneset,
}


def main():
    manifest_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    print(f"校验目录: {manifest_dir}\n")
    for fname, validator in VALIDATORS.items():
        path = os.path.join(manifest_dir, fname)
        print(f"=== {fname} ===")
        if not os.path.exists(path):
            check(f"{fname}: 文件存在", False, f"未找到 {path}")
            print()
            continue
        try:
            doc = load_yaml(path)
            check(f"{fname}: YAML 语法合法", True)
        except yaml.YAMLError as e:
            check(f"{fname}: YAML 语法合法", False, str(e))
            print()
            continue
        validator(doc)
        print()

    total = len(results)
    passed = sum(1 for r in results if r[0] == PASS)
    failed = total - passed
    print("=" * 48)
    print(f"合计: {total} 项, 通过 {passed}, 失败 {failed}")
    if failed:
        print("结果: 存在失败项")
        sys.exit(1)
    print("结果: 全部通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
