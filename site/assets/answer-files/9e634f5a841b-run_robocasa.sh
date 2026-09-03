#!/usr/bin/env bash
# Cosmos Policy RoboCasa 评估封装脚本。
#
# 严格对应 SKILL.md Workflow 2 的官方命令，所有固定参数保持与文档一致，
# 仅将 task_name / obj_instance_split / num_trials_per_task / run_id_note
# 参数化。SKILL.md「Run comparability」要求跨重复运行保持 task name、
# object split、seed、trial 数固定，因此修改这些参数时请显式传入。
#
# 用法:
#   bash scripts/run_robocasa.sh                              # smoke: TurnOffMicrowave, split A, 2 trials
#   bash scripts/run_robocasa.sh -t TurnOnSink -n 50 -r full  # full: 指定任务 50 trials
#   bash scripts/run_robocasa.sh -t TurnOffMicrowave -s A -n 2 --gpu 0
#   bash scripts/run_robocasa.sh --skip-preflight
#
# 需在 cosmos-policy 仓库根目录执行；依赖 uv、官方 Python 3.10 环境与
# 已安装的 cosmos-compatible robocasa 分支及 kitchen 资产。
set -euo pipefail

# ---- 可参数化项（默认值对应 SKILL.md smoke 评估） ----
TASK_NAME="TurnOffMicrowave"
OBJ_SPLIT="A"
TRIALS=2
RUN_NOTE="smoke"
GPU_ID="0"
SKIP_PREFLIGHT=0
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
用法: run_robocasa.sh [选项] [-- 透传给 run_robocasa_eval 的额外参数]
  -t, --task NAME      RoboCasa 任务名 (默认: TurnOffMicrowave)
  -s, --split LABEL    obj_instance_split，跨重复运行保持固定 (默认: A)
  -n, --trials NUM     每任务 trial 数，smoke=2，full=50 (默认: 2)
  -r, --run-note TEXT  run_id_note 标记 (默认: smoke)
  -g, --gpu ID         GPU 编号，同时设置 CUDA_VISIBLE_DEVICES 与 MUJOCO_EGL_DEVICE_ID
                       (默认: 0；若已在环境中设置则沿用环境值)
      --skip-preflight 跳过 scripts/preflight_check.py
  -h, --help           显示本帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--task)        TASK_NAME="$2"; shift 2 ;;
    -s|--split)       OBJ_SPLIT="$2"; shift 2 ;;
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
  python3 "$SCRIPT_DIR/preflight_check.py" --benchmark robocasa --gpu "$CUDA_VISIBLE_DEVICES"
fi

echo ">> RoboCasa 评估: task=$TASK_NAME split=$OBJ_SPLIT trials=$TRIALS run_note=$RUN_NOTE gpu=$CUDA_VISIBLE_DEVICES"

# ---- 以下固定参数逐字对应 SKILL.md Workflow 2 Step 2，不得增删改 ----
uv run --extra cu128 --group robocasa --python 3.10 \
  python -m cosmos_policy.experiments.robot.robocasa.run_robocasa_eval \
    --config cosmos_predict2_2b_480p_robocasa_50_demos_per_task__inference \
    --ckpt_path nvidia/Cosmos-Policy-RoboCasa-Predict2-2B \
    --config_file cosmos_policy/config/config.py \
    --use_wrist_image True \
    --num_wrist_images 1 \
    --use_proprio True \
    --normalize_proprio True \
    --unnormalize_actions True \
    --dataset_stats_path nvidia/Cosmos-Policy-RoboCasa-Predict2-2B/robocasa_dataset_statistics.json \
    --t5_text_embeddings_path nvidia/Cosmos-Policy-RoboCasa-Predict2-2B/robocasa_t5_embeddings.pkl \
    --trained_with_image_aug True \
    --chunk_size 32 \
    --num_open_loop_steps 16 \
    --task_name "$TASK_NAME" \
    --obj_instance_split "$OBJ_SPLIT" \
    --num_trials_per_task "$TRIALS" \
    --local_log_dir cosmos_policy/experiments/robot/robocasa/logs/ \
    --seed 195 \
    --randomize_seed False \
    --deterministic True \
    --run_id_note "$RUN_NOTE" \
    --use_variance_scale False \
    --use_jpeg_compression True \
    --flip_images True \
    --num_denoising_steps_action 5 \
    --num_denoising_steps_future_state 1 \
    --num_denoising_steps_value 1 \
    --data_collection False \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
