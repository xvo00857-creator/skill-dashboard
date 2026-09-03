#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KubeSphere 持续交付配置本地验证脚本
仅依赖 Python3 + PyYAML, 无需 kubectl / 集群 / 外部账号。

验证项:
  1. 所有 YAML 文件语法合法
  2. Pipeline CRD 结构完整 (apiVersion/kind/metadata/spec)
  3. creator 注解存在 (SKILL.md 要求)
  4. Jenkinsfile 包含必要阶段和关键步骤
  5. 凭证引用一致性 (Jenkinsfile 引用的凭证 ID 在 credentials.yaml 中定义)
  6. PipelineRun 参数与 Pipeline 定义的参数匹配
  7. RBAC 配置完整 (ServiceAccount/Role/RoleBinding)
  8. Deployment/Service 结构合法
  9. 无硬编码真实密钥 (仅允许 PLACEHOLDER 占位符)
 10. 不使用已废弃的 v1alpha2 API (扫描例外除外)

用法: python3 validate.py
退出码: 0=全部通过, 1=存在失败项
"""
import sys
import os
import re
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

passed = 0
failed = 0
warnings = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  [PASS] {msg}")


def fail(msg):
    global failed
    failed += 1
    print(f"  [FAIL] {msg}")


def warn(msg):
    global warnings
    warnings += 1
    print(f"  [WARN] {msg}")


def load_yaml_docs(filename):
    """加载多文档 YAML, 返回文档列表"""
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    return [d for d in docs if d is not None]


def section(title):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# 1. YAML 语法验证
# ---------------------------------------------------------------------------
section("1. YAML 语法验证")
yaml_files = ["pipeline.yaml", "pipelinerun.yaml", "credentials.yaml",
              "rbac.yaml", "deployment.yaml"]
all_docs = {}
for fn in yaml_files:
    try:
        docs = load_yaml_docs(fn)
        all_docs[fn] = docs
        ok(f"{fn}: 语法合法, 包含 {len(docs)} 个文档")
    except yaml.YAMLError as e:
        fail(f"{fn}: YAML 语法错误 - {e}")
        all_docs[fn] = []

# ---------------------------------------------------------------------------
# 2. Pipeline CRD 结构验证
# ---------------------------------------------------------------------------
section("2. Pipeline CRD 结构验证")
pipeline_docs = [d for d in all_docs.get("pipeline.yaml", [])
                 if d.get("kind") == "Pipeline"]
if len(pipeline_docs) == 1:
    p = pipeline_docs[0]
    if p.get("apiVersion") == "devops.kubesphere.io/v1alpha3":
        ok("apiVersion = devops.kubesphere.io/v1alpha3")
    else:
        fail(f"apiVersion 错误: {p.get('apiVersion')}")

    meta = p.get("metadata", {})
    if meta.get("name") == "demo-go-http-cd":
        ok("metadata.name = demo-go-http-cd")
    else:
        fail(f"metadata.name 错误: {meta.get('name')}")

    if meta.get("namespace") == "demo-project":
        ok("metadata.namespace = demo-project")
    else:
        fail(f"metadata.namespace 错误: {meta.get('namespace')}")

    # creator 注解 (SKILL.md CRITICAL)
    creator = meta.get("annotations", {}).get("kubesphere.io/creator")
    if creator:
        ok(f"kubesphere.io/creator 注解存在: {creator}")
    else:
        fail("缺少 kubesphere.io/creator 注解 (SKILL.md 要求)")

    spec = p.get("spec", {})
    if spec.get("type") == "pipeline":
        ok("spec.type = pipeline (普通流水线)")
    else:
        fail(f"spec.type 错误: {spec.get('type')}")

    jenkinsfile = spec.get("pipeline", {}).get("jenkinsfile", "")
    if jenkinsfile:
        ok("Jenkinsfile 已内联在 spec.pipeline.jenkinsfile")
    else:
        fail("Jenkinsfile 为空")

    # 保存 jenkinsfile 供后续验证
    pipeline_jenkinsfile = jenkinsfile
else:
    fail(f"期望 1 个 Pipeline 文档, 实际 {len(pipeline_docs)} 个")
    pipeline_jenkinsfile = ""

# ---------------------------------------------------------------------------
# 3. Jenkinsfile 内容验证
# ---------------------------------------------------------------------------
section("3. Jenkinsfile 内容验证")
if pipeline_jenkinsfile:
    required_stages = [
        "Checkout and Test",
        "Build and Push Image",
        "Deploy",
        "Verify Deployment",
        "Manual Rollback",
    ]
    for stage in required_stages:
        if f"stage('{stage}')" in pipeline_jenkinsfile:
            ok(f"包含阶段: {stage}")
        else:
            fail(f"缺少阶段: {stage}")

    # SKILL.md 要点: archiveArtifacts 与构建同 stage
    if "archiveArtifacts" in pipeline_jenkinsfile:
        ok("包含 archiveArtifacts 步骤")
    else:
        fail("缺少 archiveArtifacts 步骤")

    # SKILL.md 要点: container 名称与 pod yaml 匹配
    containers_in_pod = re.findall(r"- name: (\w+)", pipeline_jenkinsfile)
    container_calls = re.findall(r"container\('(\w+)'\)", pipeline_jenkinsfile)
    for cc in container_calls:
        if cc in containers_in_pod:
            ok(f"container('{cc}') 与 Pod 定义匹配")
        else:
            fail(f"container('{cc}') 在 Pod 定义中未找到")

    # 检查不使用 \$class 转义 (SKILL.md Common Mistakes)
    if "\\$class" not in pipeline_jenkinsfile:
        ok("未使用 \\$class 转义 (SKILL.md 建议)")
    else:
        fail("使用了 \\$class 转义 (SKILL.md 指出这是常见错误)")

    # 检查使用 withCredentials 而非硬编码
    if "withCredentials" in pipeline_jenkinsfile:
        ok("使用 withCredentials 引用凭证 (未硬编码)")
    else:
        fail("未使用 withCredentials 引用凭证")

    # 检查 post.failure 回滚
    if "post {" in pipeline_jenkinsfile and "failure {" in pipeline_jenkinsfile:
        ok("包含 post.failure 自动回滚逻辑")
    else:
        warn("未找到 post.failure 块")

    # 检查 rollout undo
    if "rollout undo" in pipeline_jenkinsfile:
        ok("包含 kubectl rollout undo 回滚命令")
    else:
        fail("缺少回滚命令 rollout undo")

    # 检查 rollout status 验证
    if "rollout status" in pipeline_jenkinsfile:
        ok("包含 kubectl rollout status 部署验证")
    else:
        fail("缺少部署验证 rollout status")

    # 检查参数定义
    if "parameters {" in pipeline_jenkinsfile:
        ok("Jenkinsfile 定义了 parameters 块")
    else:
        fail("Jenkinsfile 未定义 parameters 块")

    # 提取参数名
    jf_params = re.findall(r"\w+\(name:\s*'(\w+)'", pipeline_jenkinsfile)
    print(f"     Jenkinsfile 参数: {jf_params}")

# ---------------------------------------------------------------------------
# 4. 凭证引用一致性
# ---------------------------------------------------------------------------
section("4. 凭证引用一致性")
cred_docs = [d for d in all_docs.get("credentials.yaml", [])
             if d.get("kind") == "Secret"]
cred_ids = set()
for c in cred_docs:
    cname = c.get("metadata", {}).get("name")
    ctype = c.get("metadata", {}).get("annotations", {}).get(
        "credential.devops.kubesphere.io/type")
    cred_ids.add(cname)
    if ctype == "basic-auth":
        ok(f"凭证 {cname}: 类型 basic-auth")
    else:
        fail(f"凭证 {cname}: 类型异常 - {ctype}")

    # 检查 creator 注解
    if c.get("metadata", {}).get("annotations", {}).get("kubesphere.io/creator"):
        ok(f"凭证 {cname}: 包含 creator 注解")
    else:
        fail(f"凭证 {cname}: 缺少 creator 注解")

# 检查 Jenkinsfile 引用的凭证 ID 是否都有定义
referenced_creds = re.findall(r"credentialsId:\s*'(\w+)'", pipeline_jenkinsfile)
for rc in referenced_creds:
    if rc in cred_ids:
        ok(f"Jenkinsfile 引用的凭证 '{rc}' 在 credentials.yaml 中已定义")
    else:
        fail(f"Jenkinsfile 引用的凭证 '{rc}' 未在 credentials.yaml 中定义")

# ---------------------------------------------------------------------------
# 5. PipelineRun 验证
# ---------------------------------------------------------------------------
section("5. PipelineRun 验证")
pr_docs = [d for d in all_docs.get("pipelinerun.yaml", [])
           if d.get("kind") == "PipelineRun"]
if len(pr_docs) >= 2:
    ok(f"定义了 {len(pr_docs)} 个 PipelineRun (正常构建 + 回滚)")
else:
    fail(f"期望至少 2 个 PipelineRun, 实际 {len(pr_docs)}")

for pr in pr_docs:
    pr_name = pr.get("metadata", {}).get("name")
    if pr.get("apiVersion") == "devops.kubesphere.io/v1alpha3":
        ok(f"{pr_name}: apiVersion 正确")
    else:
        fail(f"{pr_name}: apiVersion 错误")

    ref = pr.get("spec", {}).get("pipelineRef", {}).get("name")
    if ref == "demo-go-http-cd":
        ok(f"{pr_name}: pipelineRef 指向 demo-go-http-cd")
    else:
        fail(f"{pr_name}: pipelineRef 错误 - {ref}")

    params = pr.get("spec", {}).get("parameters", [])
    param_names = {p["name"]: p["value"] for p in params}
    # 参数名必须与 Jenkinsfile 定义一致
    for pname in param_names:
        if pname in jf_params:
            ok(f"{pr_name}: 参数 '{pname}' 与 Jenkinsfile 定义匹配")
        else:
            fail(f"{pr_name}: 参数 '{pname}' 在 Jenkinsfile 中未定义")
    # 布尔值必须是字符串
    if "MANUAL_ROLLBACK" in param_names:
        val = param_names["MANUAL_ROLLBACK"]
        if isinstance(val, str) and val in ("true", "false"):
            ok(f"{pr_name}: MANUAL_ROLLBACK 布尔值为字符串 '{val}'")
        else:
            fail(f"{pr_name}: MANUAL_ROLLBACK 必须是字符串 'true'/'false', 实际 {val!r}")

# ---------------------------------------------------------------------------
# 6. RBAC 验证
# ---------------------------------------------------------------------------
section("6. RBAC 配置验证")
rbac_docs = all_docs.get("rbac.yaml", [])
kinds = {d.get("kind") for d in rbac_docs}
for kind in ["ServiceAccount", "Role", "RoleBinding"]:
    if kind in kinds:
        ok(f"包含 {kind}")
    else:
        fail(f"缺少 {kind}")

sa_docs = [d for d in rbac_docs if d.get("kind") == "ServiceAccount"]
if sa_docs and sa_docs[0].get("metadata", {}).get("name") == "demo-deployer":
    ok("ServiceAccount 名称 = demo-deployer")
else:
    fail("ServiceAccount 名称错误")

# Jenkinsfile 中引用的 serviceAccountName 必须存在
sa_in_jf = re.search(r'serviceAccountName:\s*([\w-]+)', pipeline_jenkinsfile)
if sa_in_jf:
    sa_name = sa_in_jf.group(1)
    if any(d.get("metadata", {}).get("name") == sa_name for d in sa_docs):
        ok(f"Jenkinsfile 中 serviceAccountName '{sa_name}' 在 rbac.yaml 中已定义")
    else:
        fail(f"Jenkinsfile 中 serviceAccountName '{sa_name}' 未定义")

# Role 不应包含集群级权限
role_docs = [d for d in rbac_docs if d.get("kind") == "Role"]
for r in role_docs:
    for rule in r.get("rules", []):
        for v in rule.get("verbs", []):
            if v == "*":
                fail(f"Role {r['metadata']['name']} 使用通配符动词 '*' (违反最小权限)")
    ok(f"Role {r['metadata']['name']}: 未使用通配符权限")

# ---------------------------------------------------------------------------
# 7. Deployment / Service 验证
# ---------------------------------------------------------------------------
section("7. Deployment / Service 验证")
deploy_docs = all_docs.get("deployment.yaml", [])
for d in deploy_docs:
    kind = d.get("kind")
    name = d.get("metadata", {}).get("name")
    if kind == "Deployment":
        if d.get("apiVersion") == "apps/v1":
            ok(f"Deployment {name}: apiVersion = apps/v1")
        if d.get("spec", {}).get("replicas", 0) >= 2:
            ok(f"Deployment {name}: replicas >= 2 (高可用)")
        containers = d.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        for c in containers:
            if "readinessProbe" in c:
                ok(f"Deployment {name}: 容器 {c['name']} 配置了 readinessProbe")
            else:
                fail(f"Deployment {name}: 容器 {c['name']} 缺少 readinessProbe")
            if "livenessProbe" in c:
                ok(f"Deployment {name}: 容器 {c['name']} 配置了 livenessProbe")
            else:
                fail(f"Deployment {name}: 容器 {c['name']} 缺少 livenessProbe")
            if c.get("image") == "IMAGE_PLACEHOLDER":
                ok(f"Deployment {name}: 镜像使用占位符 (由流水线注入)")
            else:
                warn(f"Deployment {name}: 镜像非占位符: {c.get('image')}")
    elif kind == "Service":
        ok(f"Service {name}: 已定义")

# ---------------------------------------------------------------------------
# 8. 安全检查: 无硬编码密钥
# ---------------------------------------------------------------------------
section("8. 安全检查: 无硬编码真实密钥")
secret_patterns = [
    (r"ghp_[A-Za-z0-9]{20,}", "GitHub PAT"),
    (r"xox[baprs]-[A-Za-z0-9-]+", "Slack Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
]
for fn in yaml_files:
    path = os.path.join(BASE_DIR, fn)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for pattern, label in secret_patterns:
        matches = re.findall(pattern, content)
        if matches:
            fail(f"{fn}: 发现疑似硬编码 {label}: {matches}")
    # 检查 PLACEHOLDER 占位符 (允许)
    if "PLACEHOLDER" in content:
        ok(f"{fn}: 敏感值使用 PLACEHOLDER 占位符")

# 检查 Jenkinsfile 中不直接使用 GITHUB_ 环境变量 (SKILL.md 要求)
if re.search(r"\bGITHUB_[A-Z_]+\b", pipeline_jenkinsfile):
    fail("Jenkinsfile 中直接使用了 GITHUB_ 环境变量 (SKILL.md 禁止)")
else:
    ok("Jenkinsfile 未直接使用 GITHUB_ 环境变量 (SKILL.md 要求)")

# ---------------------------------------------------------------------------
# 9. API 版本检查 (避免已废弃 v1alpha2 用于核心操作)
# ---------------------------------------------------------------------------
section("9. API 版本检查")
for fn in yaml_files:
    path = os.path.join(BASE_DIR, fn)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "devops.kubesphere.io/v1alpha2" in content:
        fail(f"{fn}: 使用了已废弃的 v1alpha2 API (SKILL.md 建议优先 v1alpha3)")
    elif "devops.kubesphere.io/v1alpha3" in content:
        ok(f"{fn}: 使用 v1alpha3 API")

# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print(f"验证完成: {passed} 通过, {failed} 失败, {warnings} 警告")
print("=" * 60)
sys.exit(1 if failed > 0 else 0)
