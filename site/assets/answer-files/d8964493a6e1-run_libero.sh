#!/usr/bin/env bash
# Cosmos Policy LIBERO 评估封装脚本。
#
# 严格对应 SKILL.md Workflow 1 的官方命令，所有固定参数保持与文档一致，
# 仅将 task_suite_name / num_trials_per_task / run_id_note 参数化，
# 以减少复制长命令时的漏参风险。固定参数不得随意改动（SKILL.md
# 「Run comparability」：跨重复运行保持任务名、seed、trial 数等固定）。
#
# 用法:
#   bash scripts/run_libero.sh                         # smoke: libero_10, 1 trial
#   bash scripts/run_libero.sh -s libero_spatial -n 50 # full: 指定套件 50 trials
#   bash scripts/run_libero.sh -s libero_10 -n 50 -r full --gpu 1
#   bash scripts/run_libero.sh --skip-preflight        # 跳过预检
#
# 需在 cosmos-policy 仓库根目录执行；依赖 uv 与官方 Python 3.10 环境。
set -euo pipefail

# ---- 可参数化项（默认值对应 SKILL.md smoke 评估） ----
SUITE="libero_10"
TRIALS=1
RUN_NOTE="smoke"
GPU_ID="0"
SKIP_PREFLIGHT=0
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
用法: run_libero.sh [选项] [-- 透传给 run_libero_eval 的额外参数]
  -s, --suite NAME       LIBERO 任务套件 (libero_spatial/libero_object/libero_goal/libero_10)
                         默认: libero_10
  -n, --trials NUM       每任务 trial 数，smoke=1，full=50 (默认: 1)
  -r, --run-note TEXT    run_id_note 标记 (默认: smoke)
  -g, --gpu ID           GPU 编号，同时设置 CUDA_VISIBLE_DEVICES 与 MUJOCO_EGL_DEVICE_ID
                         (默认: 0；若已在环境中设置则沿用环境值)
      --skip-preflight   跳过 scripts/preflight_check.py
  -h, --help             显示本帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--suite)       SUITE="$2"; shift 2 ;;
    -n|--trials)      TRIALS="$2"; shift 2 ;;
    -r|--run-note)    RUN_NOTE="$2"; shift 2 ;;
    -g|--gpu)         GPU_ID="$2"; shift 2 ;;
    --skip-preflight) SKIP_PREFLIGHT=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    --)               shift; EXTRA_ARGS=("$@"); break ;;
    *)                echo "未知参数: $1" >&2; usage; exit 2 ;;
  esac
done

# ---- EGL 环境变量（SKILL.md「EGL alignment」：四个必须一起设置） ----
# 已在环境中设置的值优先，保证多卡场景不被脚本覆盖。
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-$GPU_ID}"
export MUJOCO_EGL_DEVICE_ID="${MUJOCO_EGL_DEVICE_ID:-$GPU_ID}"
export MUJOCO_GL="${MUJOCO_GL:-egl}"
export PYOPENGL_PLATFORM="${PYOPENGL_PLATFORM:-egl}"
# 缓存一致性（SKILL.md「Cache consistency」）
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$SKIP_PREFLIGHT" -eq 0 ]]; then
  echo ">> 运行预检..."
  python3 "$SCRIPT_DIR/preflight_check.py" --benchmark libero --gpu "$CUDA_VISIBLE_DEVICES"
fi

echo ">> LIBERO 评估: suite=$SUITE trials=$TRIALS run_note=$RUN_NOTE gpu=$CUDA_VISIBLE_DEVICES"

# ---- 以下固定参数逐字对应 SKILL.md Workflow 1 Step 3，不得增删改 ----
uv run --extra cu128 --group libero --python 3.10 \
  python -m cosmos_policy.experiments.robot.libero.run_libero_eval \
    --config cosmos_predict2_2b_480p_libero__inference_only \
    --ckpt_path nvidia/Cosmos-Policy-LIBERO-Predict2-2B \
    --config_file cosmos_policy/config/config.py \
    --use_wrist_image True \
    --use_proprio True \
    --normalize_proprio True \
    --unnormalize_actions True \
    --dataset_stats_path nvidia/Cosmos-Policy-LIBERO-Predict2-2B/libero_dataset_statistics.json \
    --t5_text_embeddings_path nvidia/Cosmos-Policy-LIBERO-Predict2-2B/libero_t5_embeddings.pkl \
    --trained_with_image_aug True \
    --chunk_size 16 \
    --num_open_loop_steps 16 \
    --task_suite_name "$SUITE" \
    --num_trials_per_task "$TRIALS" \
    --local_log_dir cosmos_policy/experiments/robot/libero/logs/ \
    --seed 195 \
    --randomize_seed False \
    --deterministic True \
    --run_id_note "$RUN_NOTE" \
    --ar_future_prediction False \
    --ar_value_prediction False \
    --use_jpeg_compression True \
    --flip_images True \
    --num_denoising_steps_action 5 \
    --num_denoising_steps_future_state 1 \
    --num_denoising_steps_value 1 \
    --data_collection False \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
