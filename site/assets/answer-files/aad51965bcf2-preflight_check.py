#!/usr/bin/env python3
"""Cosmos Policy 评估环境预检脚本。

依据 SKILL.md「Non-negotiable rules」与「Common issues」章节，在运行
LIBERO / RoboCasa 评估前检查 headless EGL 渲染环境、缓存一致性、运行时
依赖与仓库结构。仅使用 Python 标准库，不引入任何新依赖。

用法:
    python scripts/preflight_check.py                # 检查 LIBERO 评估环境
    python scripts/preflight_check.py --benchmark robocasa
    python scripts/preflight_check.py --gpu 1        # 指定期望的 GPU 编号
    python scripts/preflight_check.py --skip-gpu     # 无 GPU 机器上跳过 nvidia-smi 检查

退出码:
    0  全部硬性检查通过（警告不影响退出码）
    1  存在硬性检查失败
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 四个必须同时设置的 EGL 相关环境变量（SKILL.md「EGL alignment」规则）
EGL_ENV_VARS = [
    "CUDA_VISIBLE_DEVICES",
    "MUJOCO_EGL_DEVICE_ID",
    "MUJOCO_GL",
    "PYOPENGL_PLATFORM",
]
EXPECTED_RENDER_BACKEND = "egl"
EXPECTED_PYTHON_MAJOR_MINOR = (3, 10)


def _ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def check_egl_env(expected_gpu: str | None) -> list[str]:
    """检查 EGL 四个环境变量是否齐全且 GPU 编号一致。"""
    failures: list[str] = []

    missing = [v for v in EGL_ENV_VARS if not os.environ.get(v)]
    if missing:
        failures.append(
            "缺少 EGL 环境变量: " + ", ".join(missing) + "。请同时设置 "
            "CUDA_VISIBLE_DEVICES / MUJOCO_EGL_DEVICE_ID / MUJOCO_GL=egl / "
            "PYOPENGL_PLATFORM=egl（SKILL.md「EGL alignment」）。"
        )
        return failures

    cuda_dev = os.environ["CUDA_VISIBLE_DEVICES"]
    egl_dev = os.environ["MUJOCO_EGL_DEVICE_ID"]
    if cuda_dev != egl_dev:
        failures.append(
            f"GPU 编号不一致: CUDA_VISIBLE_DEVICES={cuda_dev} 而 "
            f"MUJOCO_EGL_DEVICE_ID={egl_dev}，二者必须指向同一块 GPU。"
        )
    else:
        _ok(f"EGL GPU 编号一致: {cuda_dev}")

    if os.environ["MUJOCO_GL"] != EXPECTED_RENDER_BACKEND:
        failures.append(
            f"MUJOCO_GL={os.environ['MUJOCO_GL']}，应为 egl。"
        )
    if os.environ["PYOPENGL_PLATFORM"] != EXPECTED_RENDER_BACKEND:
        failures.append(
            f"PYOPENGL_PLATFORM={os.environ['PYOPENGL_PLATFORM']}，应为 egl。"
        )
    if not failures:
        _ok("MUJOCO_GL=egl 且 PYOPENGL_PLATFORM=egl")

    if expected_gpu is not None and cuda_dev != expected_gpu:
        _warn(
            f"CUDA_VISIBLE_DEVICES={cuda_dev} 与命令行指定的 --gpu {expected_gpu} "
            "不一致；如非多卡刻意安排，请确认。"
        )

    return failures


def check_cache_consistency() -> None:
    """检查 HF_HOME 与 TRANSFORMERS_CACHE 缓存目录一致性（SKILL.md「Cache consistency」）。"""
    hf_home = os.environ.get("HF_HOME")
    transformers_cache = os.environ.get("TRANSFORMERS_CACHE")

    if not hf_home and not transformers_cache:
        _warn(
            "未设置 HF_HOME / TRANSFORMERS_CACHE；SKILL.md 建议在 setup 与 eval 间"
            "复用同一缓存目录，避免重复下载 Hugging Face 产物。"
        )
        return

    if hf_home and transformers_cache:
        try:
            same = Path(hf_home).resolve() == Path(transformers_cache).resolve()
        except OSError:
            same = hf_home == transformers_cache
        if same:
            _ok(f"缓存目录一致: {hf_home}")
        else:
            _warn(
                f"HF_HOME={hf_home} 与 TRANSFORMERS_CACHE={transformers_cache} "
                "指向不同目录，可能导致缓存无法复用。"
            )
    else:
        _warn(
            "仅设置了 HF_HOME 或 TRANSFORMERS_CACHE 之一；建议二者指向同一目录。"
        )


def check_uv() -> list[str]:
    """检查 uv 是否可用（SKILL.md 所有评估命令均通过 uv run 执行）。"""
    if shutil.which("uv"):
        _ok("uv 已安装")
        return []
    return ["未找到 uv；SKILL.md 的安装与评估命令均依赖 uv（uv sync / uv run）。"]


def check_python_version() -> list[str]:
    """检查当前 Python 主次版本是否为 3.10（SKILL.md 命令固定 --python 3.10）。"""
    cur = sys.version_info[:2]
    if cur == EXPECTED_PYTHON_MAJOR_MINOR:
        _ok(f"Python 版本: {cur[0]}.{cur[1]}")
        return []
    # 注意：uv run --python 3.10 会自行拉起 3.10，因此宿主机版本不符只警告
    _warn(
        f"当前 Python 为 {cur[0]}.{cur[1]}，SKILL.md 命令固定 --python 3.10；"
        "uv 会自动获取 3.10，但若 uv 无法下载请在官方容器中运行。"
    )
    return []


def check_repo_root() -> list[str]:
    """检查是否在 cosmos-policy 仓库根目录（存在 pyproject.toml 与 config 模块）。"""
    failures: list[str] = []
    cwd = Path.cwd()

    pyproject = cwd / "pyproject.toml"
    if not pyproject.is_file():
        failures.append(
            f"当前目录 {cwd} 下未找到 pyproject.toml；请在 cosmos-policy 仓库根目录"
            "运行本脚本（SKILL.md: git clone 后 cd cosmos-policy）。"
        )
    else:
        _ok("找到 pyproject.toml")

    config_py = cwd / "cosmos_policy" / "config" / "config.py"
    if not config_py.is_file():
        failures.append(
            "未找到 cosmos_policy/config/config.py；评估命令的 --config_file 指向"
            "该相对路径，缺失会导致启动失败。"
        )
    else:
        _ok("找到 cosmos_policy/config/config.py")

    return failures


def check_gpu(skip: bool) -> list[str]:
    """检查 nvidia-smi 是否可见 GPU（headless GPU 节点硬性要求）。"""
    if skip:
        _warn("已按 --skip-gpu 跳过 GPU 可见性检查。")
        return []

    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return [
            "未找到 nvidia-smi；headless GPU 评估需要可见的 NVIDIA GPU。"
            "若在无 GPU 机器上做预检请加 --skip-gpu。"
        ]
    try:
        proc = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return [f"nvidia-smi 执行失败: {exc}"]

    if proc.returncode != 0:
        return [f"nvidia-smi 返回非零退出码 {proc.returncode}: {proc.stderr.strip()}"]

    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return ["nvidia-smi 未列出任何 GPU。"]
    _ok(f"可见 {len(lines)} 块 GPU: {lines[0]}")
    return []


def check_robocasa_assets() -> list[str]:
    """RoboCasa 专项检查：macros_private.py 与 kitchen 资产是否就绪。"""
    failures: list[str] = []

    # SKILL.md Workflow 2 Step 1: 验证 macros_private.py 存在且路径正确
    macros_candidates = []
    try:
        import robocasa  # type: ignore

        pkg_dir = Path(robocasa.__file__).resolve().parent
        macros_candidates.append(pkg_dir / "macros_private.py")
    except ImportError:
        _warn(
            "无法 import robocasa；若尚未安装 cosmos-compatible 分支，请执行 "
            "uv pip install -e robocasa-cosmos-policy 后再运行 RoboCasa 评估。"
        )

    # 也检查用户目录下的 robocasa 配置位置
    macros_candidates.append(Path.home() / ".robocasa" / "macros_private.py")

    found_macros = [p for p in macros_candidates if p.is_file()]
    if found_macros:
        _ok(f"找到 macros_private.py: {found_macros[0]}")
    else:
        failures.append(
            "未找到 macros_private.py；请先运行 "
            "python -m robocasa.scripts.setup_macros 并确认路径正确。"
        )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Cosmos Policy 评估环境预检")
    parser.add_argument(
        "--benchmark",
        choices=["libero", "robocasa"],
        default="libero",
        help="评估目标，影响专项检查项（默认 libero）",
    )
    parser.add_argument(
        "--gpu",
        default=None,
        help="期望的 GPU 编号，与 CUDA_VISIBLE_DEVICES 比对（可选）",
    )
    parser.add_argument(
        "--skip-gpu",
        action="store_true",
        help="跳过 nvidia-smi GPU 可见性检查（用于无 GPU 机器）",
    )
    args = parser.parse_args()

    print(f"== Cosmos Policy 预检 (benchmark={args.benchmark}) ==")
    print(f"工作目录: {Path.cwd()}")
    print()

    failures: list[str] = []

    # 1. EGL 环境（硬性）
    print("-- EGL 渲染环境 --")
    failures.extend(check_egl_env(args.gpu))
    print()

    # 2. 缓存一致性（警告级）
    print("-- 缓存一致性 --")
    check_cache_consistency()
    print()

    # 3. uv / Python / 仓库结构
    print("-- 运行时与仓库 --")
    failures.extend(check_uv())
    failures.extend(check_python_version())
    failures.extend(check_repo_root())
    print()

    # 4. GPU
    print("-- GPU --")
    failures.extend(check_gpu(args.skip_gpu))
    print()

    # 5. RoboCasa 专项
    if args.benchmark == "robocasa":
        print("-- RoboCasa 资产 --")
        failures.extend(check_robocasa_assets())
        print()

    print("=" * 48)
    if failures:
        print(f"预检未通过，共 {len(failures)} 项硬性问题：")
        for i, f in enumerate(failures, 1):
            print(f"  {i}. {f}")
        return 1

    print("预检通过。可按 SKILL.md 工作流运行评估。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
