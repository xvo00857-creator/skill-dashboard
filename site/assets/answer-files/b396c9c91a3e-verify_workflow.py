#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品图 ComfyUI 工作流验证脚本（零第三方依赖，仅使用 Python 标准库）。

功能：
  1. 校验 API 格式工作流 JSON 的结构完整性（节点引用、class_type、inputs）。
  2. 识别模板化节点与固定节点。
  3. 校验 output_node 是否为终端保存节点。
  4. 列出所需模型文件及目标目录。
  5. 若本地 ComfyUI 服务可用（默认 http://localhost:8188），执行健康检查并尝试提交任务。

用法：
  python3 verify_workflow.py                       # 仅静态校验
  python3 verify_workflow.py --submit              # 静态校验 + 尝试提交到本地 ComfyUI
  python3 verify_workflow.py --server http://host:8188 --submit
  python3 verify_workflow.py --workflow other.json # 指定工作流文件
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# 规则常量（与 SKILL.md 中的约定对齐）
# ---------------------------------------------------------------------------
TERMINAL_SAVER_CLASSES = {
    "SaveImage", "SaveVideo", "VHS_VideoCombine",
    "SaveAnimatedWEBP", "SaveImageWebsocket",
}
TEMPLATED_INPUT_KEYS = {
    "text", "seed", "width", "height", "batch_size",
    "steps", "cfg", "sampler_name", "scheduler", "denoise",
    "filename_prefix", "image", "video",
}
FIXED_LOADER_CLASSES = {
    "CheckpointLoaderSimple", "CheckpointLoader",
    "UNETLoader", "VAELoader", "CLIPLoader", "DualCLIPLoader",
    "LoraLoader", "LoraLoaderModelOnly",
    "ControlNetLoader", "StyleModelLoader",
}
MODEL_DIR_HINTS = {
    "CheckpointLoaderSimple": "models/checkpoints/",
    "CheckpointLoader": "models/checkpoints/",
    "UNETLoader": "models/diffusion_models/",
    "VAELoader": "models/vae/",
    "CLIPLoader": "models/text_encoders/",
    "DualCLIPLoader": "models/text_encoders/",
    "LoraLoader": "models/loras/",
    "LoraLoaderModelOnly": "models/loras/",
}

passed = 0
failed = 0
warnings = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  [通过] {msg}")


def fail(msg):
    global failed
    failed += 1
    print(f"  [失败] {msg}")


def warn(msg):
    global warnings
    warnings += 1
    print(f"  [警告] {msg}")


def load_workflow(path):
    if not os.path.isfile(path):
        fail(f"工作流文件不存在: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            wf = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"JSON 解析失败: {e}")
        return None
    if not isinstance(wf, dict):
        fail("工作流根节点必须是对象(dict)，API 格式应为 {node_id: {...}}")
        return None
    return wf


def validate_structure(wf):
    print("\n== 1. 结构校验 ==")
    all_ids = set(wf.keys())
    referenced = set()

    for nid, node in wf.items():
        if not isinstance(node, dict):
            fail(f"节点 {nid} 不是对象")
            continue
        ct = node.get("class_type")
        if not ct:
            fail(f"节点 {nid} 缺少 class_type")
            continue
        inputs = node.get("inputs")
        if inputs is None:
            fail(f"节点 {nid} ({ct}) 缺少 inputs")
            continue
        if not isinstance(inputs, dict):
            fail(f"节点 {nid} ({ct}) 的 inputs 不是对象")
            continue

        for key, val in inputs.items():
            # 连接引用形如 ["4", 0]
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
                ref_id = val[0]
                referenced.add(ref_id)
                if ref_id not in all_ids:
                    fail(f"节点 {nid}.{key} 引用了不存在的节点 {ref_id}")

    # 检查是否有未被任何节点引用的孤立节点（允许有，仅警告）
    orphans = all_ids - referenced - {nid for nid in wf
                                      if wf[nid].get("class_type") in TERMINAL_SAVER_CLASSES}
    # 反向检查：被引用但不存在的已在上面处理
    ok(f"共 {len(all_ids)} 个节点，{len(referenced)} 个被引用")
    if orphans:
        warn(f"可能的孤立节点（未被引用且非保存节点）: {sorted(orphans)}")
    else:
        ok("无孤立节点")

    if failed == 0:
        ok("所有节点引用均可解析")


def classify_nodes(wf):
    print("\n== 2. 模板化节点 / 固定节点识别 ==")
    templated = []
    fixed = []
    for nid, node in sorted(wf.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
        ct = node.get("class_type", "")
        inputs = node.get("inputs", {})
        t_keys = [k for k in inputs if k in TEMPLATED_INPUT_KEYS]
        if ct in FIXED_LOADER_CLASSES:
            fixed.append((nid, ct))
            print(f"  节点 {nid:>4} | {ct:<24} | 固定（加载器/模型）")
        elif t_keys:
            templated.append((nid, ct, t_keys))
            print(f"  节点 {nid:>4} | {ct:<24} | 模板化参数: {', '.join(t_keys)}")
        else:
            print(f"  节点 {nid:>4} | {ct:<24} | 固定（图结构/连线）")
    print(f"  小结: 模板化节点 {len(templated)} 个，固定加载器 {len(fixed)} 个")
    return templated, fixed


def validate_output_node(wf, output_node):
    print(f"\n== 3. output_node 校验 (output_node=\"{output_node}\") ==")
    if output_node not in wf:
        fail(f"output_node {output_node} 不在工作流中")
        return
    node = wf[output_node]
    ct = node.get("class_type", "")
    if ct in TERMINAL_SAVER_CLASSES:
        ok(f"output_node {output_node} 是终端保存节点: {ct}")
    else:
        fail(f"output_node {output_node} 的 class_type 为 {ct}，"
             f"应为 {sorted(TERMINAL_SAVER_CLASSES)} 之一")
    # 检查它是否有图片输入连接
    images_input = node.get("inputs", {}).get("images")
    if isinstance(images_input, list) and images_input[0] in wf:
        ok(f"输出图片来自节点 {images_input[0]}")
    else:
        warn("未检测到 images 输入连接，请确认该节点能产出最终文件")


def collect_models(wf):
    print("\n== 4. 模型依赖 ==")
    models = []
    for nid, node in wf.items():
        ct = node.get("class_type", "")
        if ct in MODEL_DIR_HINTS:
            inputs = node.get("inputs", {})
            # 常见模型文件字段名
            for field in ("ckpt_name", "unet_name", "vae_name",
                          "clip_name", "lora_name", "control_net_name"):
                if field in inputs and isinstance(inputs[field], str):
                    dest = MODEL_DIR_HINTS[ct]
                    models.append((nid, ct, inputs[field], dest))
                    print(f"  节点 {nid} ({ct}): {inputs[field]} -> ComfyUI/{dest}")
    if not models:
        warn("未发现模型加载节点，工作流可能无法独立运行")
    return models


def check_server(server):
    print(f"\n== 5. ComfyUI 服务检查 ({server}) ==")
    url = f"{server.rstrip('/')}/system_stats"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ok("服务在线")
        sys_info = data.get("system", {})
        dev_info = data.get("devices", [{}])[0] if data.get("devices") else {}
        print(f"    系统: {sys_info.get('os', '?')}")
        if dev_info:
            print(f"    GPU : {dev_info.get('name', '?')}, "
                  f"显存: {dev_info.get('vram_total', 0) // (1024**2)} MB")
        return True
    except urllib.error.URLError as e:
        warn(f"服务不可达: {e.reason}")
        print("    这是预期情况——若尚未启动 ComfyUI，请先启动后再用 --submit 提交。")
        return False
    except Exception as e:
        warn(f"健康检查异常: {e}")
        return False


def submit_workflow(server, workflow_path, output_node):
    print(f"\n== 6. 提交任务到 {server} ==")
    with open(workflow_path, "r", encoding="utf-8") as f:
        wf = json.load(f)
    payload = json.dumps({"prompt": wf, "client_id": "verify_script"}).encode("utf-8")
    url = f"{server.rstrip('/')}/prompt"
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        pid = result.get("prompt_id")
        if pid:
            ok(f"任务已提交, prompt_id={pid}")
            print(f"    可通过 GET {server.rstrip('/')}/history/{pid} 查询结果")
        else:
            fail(f"提交返回异常: {result}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        fail(f"提交失败 HTTP {e.code}: {body[:500]}")
    except Exception as e:
        fail(f"提交异常: {e}")


def main():
    parser = argparse.ArgumentParser(description="商品图 ComfyUI 工作流验证脚本")
    parser.add_argument("--workflow", default="product_image_workflow_api.json",
                        help="工作流 JSON 文件路径")
    parser.add_argument("--output-node", default="9",
                        help="终端保存节点 ID（字符串）")
    parser.add_argument("--server",
                        default=os.environ.get("COMFYUI_SERVER_URL",
                                               "http://localhost:8188"),
                        help="ComfyUI 服务地址")
    parser.add_argument("--submit", action="store_true",
                        help="校验通过后尝试提交任务到 ComfyUI")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    wf_path = args.workflow
    if not os.path.isabs(wf_path):
        wf_path = os.path.join(base_dir, wf_path)

    print("=" * 60)
    print("商品图 ComfyUI 工作流验证")
    print(f"工作流文件: {wf_path}")
    print("=" * 60)

    wf = load_workflow(wf_path)
    if wf is None:
        print("\n验证中止：无法加载工作流。")
        sys.exit(1)

    validate_structure(wf)
    classify_nodes(wf)
    validate_output_node(wf, args.output_node)
    collect_models(wf)

    server_ok = check_server(args.server)
    if args.submit:
        if server_ok:
            submit_workflow(args.server, wf_path, args.output_node)
        else:
            print("\n服务不可达，跳过提交。启动 ComfyUI 后可重新运行:")
            print(f"  python3 verify_workflow.py --submit --server {args.server}")
    else:
        print("\n（未指定 --submit，仅做静态校验。）")

    print("\n" + "=" * 60)
    print(f"结果: 通过 {passed}, 失败 {failed}, 警告 {warnings}")
    print("=" * 60)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
