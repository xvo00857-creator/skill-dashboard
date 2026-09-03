#!/usr/bin/env bash
# eBay 已售出商品采集编排脚本（受约束版）
# 基于 ebay-sold-listings-search Skill
# 用法: bash collect.sh <keyword> [keyword2 ...]
# 环境变量:
#   EBAY_SITE       默认 ebay.com
#   MAX_ITEMS       每个关键词最大条数，默认 60
#   ITEM_CONDITION  默认 any（可选 new/used 或数字 ID）
#   MIN_PRICE       默认空
#   MAX_PRICE       默认空
#   OUTPUT_DIR      默认 ./output
#   DRY_RUN         设为 1 时只构建 URL 不调用 browser-act（预检演示用）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SCRIPTS="${SCRIPT_DIR}/../ebay-sold-listings-search/ebay-sold-listings-search/scripts"
EBAY_SITE="${EBAY_SITE:-ebay.com}"
MAX_ITEMS="${MAX_ITEMS:-60}"
ITEM_CONDITION="${ITEM_CONDITION:-any}"
MIN_PRICE="${MIN_PRICE:-}"
MAX_PRICE="${MAX_PRICE:-}"
OUTPUT_DIR="${OUTPUT_DIR:-${SCRIPT_DIR}/output}"
DRY_RUN="${DRY_RUN:-0}"

if [ $# -lt 1 ]; then
  echo "用法: bash collect.sh <keyword> [keyword2 ...]" >&2
  exit 1
fi

# ========== 阶段 0：预检 ==========
echo "=== 阶段 0：预检 ==="

# 0.1 Python
if ! command -v python3 &>/dev/null; then
  echo "[预检失败] python3 未找到" >&2; exit 1
fi
echo "[预检] python3: $(python3 --version)"

# 0.2 Skill 脚本存在性
for f in build-url.py extract-page.py enum-categories.py; do
  if [ ! -f "${SKILL_SCRIPTS}/${f}" ]; then
    echo "[预检失败] 缺少脚本: ${SKILL_SCRIPTS}/${f}" >&2; exit 1
  fi
done
echo "[预检] Skill 脚本目录: ${SKILL_SCRIPTS}"

# 0.3 browser-act（DRY_RUN 模式下仅警告）
if ! command -v browser-act &>/dev/null; then
  if [ "$DRY_RUN" = "1" ]; then
    echo "[预检-警告] browser-act 未安装；DRY_RUN=1，仅验证 URL 构建"
  else
    echo "[预检失败] browser-act 未找到。SKILL.md 要求此工具执行浏览器导航与 JS 提取。" >&2
    echo "  请安装/配置 browser-act 后重试，或以 DRY_RUN=1 运行仅验证 URL 构建。" >&2
    exit 1
  fi
else
  echo "[预检] browser-act: $(browser-act --version 2>/dev/null || echo available)"
fi

# 0.4 输出目录（幂等：不覆盖已有文件）
mkdir -p "$OUTPUT_DIR"
echo "[预检] 输出目录: ${OUTPUT_DIR}"

# 0.5 经验记忆文件
MEMORY_FILE="${SCRIPT_DIR}/browser-act-skill-forge-memories/ebay-sold-listings-search.memory.md"
if [ -f "$MEMORY_FILE" ]; then
  echo "[预检] 发现经验记忆文件，请先阅读: ${MEMORY_FILE}"
fi

# ========== 阶段 1-4：逐关键词采集 ==========
for KEYWORD in "$@"; do
  echo ""
  echo "=== 采集关键词: ${KEYWORD} ==="
  SAFE_NAME=$(echo "$KEYWORD" | tr ' /' '__')
  OUTFILE="${OUTPUT_DIR}/${SAFE_NAME}.jsonl"

  # 人工确认点 B：已有结果文件
  if [ -f "$OUTFILE" ]; then
    echo "[人工确认点 B] 结果文件已存在: ${OUTFILE}"
    echo "  将以追加模式写入（按 itemId 去重由后续合并步骤处理）。"
  fi

  PAGE=1
  COLLECTED=0

  while [ "$COLLECTED" -lt "$MAX_ITEMS" ]; do
    echo "--- 第 ${PAGE} 页 ---"

    # 阶段 1：构建 URL
    URL=$(python3 "${SKILL_SCRIPTS}/build-url.py" "$KEYWORD" \
      --ebaySite "$EBAY_SITE" \
      --sortOrder endedRecently \
      --itemCondition "$ITEM_CONDITION" \
      ${MIN_PRICE:+--minPrice "$MIN_PRICE"} \
      ${MAX_PRICE:+--maxPrice "$MAX_PRICE"} \
      --includeCompletedListings true \
      --ipg 60 --page "$PAGE")
    echo "[URL] ${URL}"

    if [ "$DRY_RUN" = "1" ]; then
      echo "[DRY_RUN] 跳过浏览器操作"
      break
    fi

    # 阶段 2：导航 + 等待（含重试）
    NAV_OK=0
    for ATTEMPT in 1 2; do
      browser-act navigate "$URL"
      if browser-act wait --selector "li.s-card" --state visible --timeout 30000; then
        NAV_OK=1; break
      fi
      echo "[重试] 第 ${ATTEMPT} 次导航/等待失败，10 秒后重试..."
      sleep 10
    done
    if [ "$NAV_OK" -ne 1 ]; then
      echo "[人工确认点 A] 页面持续无法加载（可能是验证码/登录墙）。"
      echo "  请在浏览器中手动完成验证后重新运行，或检查网络/代理。"
      break
    fi

    # 阶段 3：提取
    RESULT=$(browser-act eval "$(python3 "${SKILL_SCRIPTS}/extract-page.py" --keyword "$KEYWORD")")

    # 检查 error 字段（简单 grep，生产环境建议用 jq）
    if echo "$RESULT" | grep -q '"error":true'; then
      echo "[错误] 提取返回 error，10 秒后重试 1 次..."
      sleep 10
      RESULT=$(browser-act eval "$(python3 "${SKILL_SCRIPTS}/extract-page.py" --keyword "$KEYWORD")")
      if echo "$RESULT" | grep -q '"error":true'; then
        echo "[中止] 关键词 ${KEYWORD} 第 ${PAGE} 页提取持续失败"
        break
      fi
    fi

    # 阶段 3.5：解析并去重写入 JSONL（此处用 python 内联处理）
    PAGE_COUNT=$(COLLECTED="$COLLECTED" MAX_ITEMS="$MAX_ITEMS" OUTFILE="$OUTFILE" \
      python3 -c "
import json, sys, os
data = json.loads(sys.stdin.read())
collected = int(os.environ['COLLECTED'])
max_items = int(os.environ['MAX_ITEMS'])
outfile = os.environ['OUTFILE']
seen_path = outfile + '.seen'
seen = set()
if os.path.exists(seen_path):
    with open(seen_path) as f:
        seen = set(line.strip() for line in f if line.strip())
new_count = 0
with open(outfile, 'a', encoding='utf-8') as out, open(seen_path, 'a', encoding='utf-8') as seenf:
    for item in data.get('items', []):
        iid = item.get('itemId')
        if not iid or iid in seen:
            continue
        if collected + new_count >= max_items:
            break
        out.write(json.dumps(item, ensure_ascii=False) + '\n')
        seenf.write(iid + '\n')
        seen.add(iid)
        new_count += 1
has_next = data.get('hasNextPage', False)
print(f'{new_count}|{int(has_next)}')
" <<< "$RESULT")

    NEW_COUNT="${PAGE_COUNT%%|*}"
    HAS_NEXT="${PAGE_COUNT##*|}"
    COLLECTED=$((COLLECTED + NEW_COUNT))
    echo "[本页新增] ${NEW_COUNT} 条，累计 ${COLLECTED}/${MAX_ITEMS}"

    if [ "$HAS_NEXT" = "0" ] || [ "$COLLECTED" -ge "$MAX_ITEMS" ]; then
      echo "[完成] 关键词 ${KEYWORD} 采集结束"
      break
    fi

    # 阶段 4：页间退避 2-4 秒
    SLEEP_SEC=$((2 + RANDOM % 3))
    echo "[退避] ${SLEEP_SEC} 秒..."
    sleep "$SLEEP_SEC"
    PAGE=$((PAGE + 1))
  done
done

echo ""
echo "=== 采集结束 ==="
echo "结果目录: ${OUTPUT_DIR}"
echo "后续可用 jq 合并去重: cat ${OUTPUT_DIR}/*.jsonl | jq -s 'unique_by(.itemId)' > merged.json"
