#!/usr/bin/env bash
# story-setup generic 部署脚本
# 严格按 SKILL.md 的「通用 Web AI / 其他 Agent 部署算法」实现
# 用法: ./deploy-generic.sh <skill源目录> <目标项目目录> [项目名] [书名] [目标平台] [作者名]
set -euo pipefail

# ---------- 参数解析 ----------
SKILL_SRC="${1:?用法: $0 <skill源目录> <目标项目目录> [项目名] [书名] [目标平台] [作者名]}"
PROJECT_DIR="${2:?缺少目标项目目录}"
PROJECT_NAME="${3:-$(basename "$PROJECT_DIR")}"
BOOK_NAME="${4:-$PROJECT_NAME}"
TARGET_PLATFORM="${5:-}"
AUTHOR_NAME="${6:-作者}"

# SKILL.md 规定的版本号
AGENTS_VERSION=24
SETUP_SKILL_VERSION="1.2.7"

# ---------- 工具函数 ----------
log()  { printf '[story-setup] %s\n' "$*"; }
warn() { printf '[story-setup][WARN] %s\n' "$*" >&2; }
err()  { printf '[story-setup][ERROR] %s\n' "$*" >&2; }

# ---------- Phase 1: 检测项目状态 ----------
log "Phase 1: 检测项目状态"

# 1a. 自检参考目录（SKILL.md 铁律：8 个子目录 + scripts/merge-codex-hooks.py）
log "自检 skill 参考目录..."
REQUIRED_DIRS=(agent-references templates opencode codex zcode openclaw reasonix generic)
missing_dirs=()
empty_dirs=()
for d in "${REQUIRED_DIRS[@]}"; do
  dir_path="$SKILL_SRC/references/$d"
  if [ ! -d "$dir_path" ]; then
    missing_dirs+=("$d")
  elif [ -z "$(ls -A "$dir_path" 2>/dev/null)" ]; then
    empty_dirs+=("$d")
  fi
done
if [ ! -f "$SKILL_SRC/scripts/merge-codex-hooks.py" ]; then
  missing_dirs+=("scripts/merge-codex-hooks.py")
fi
if [ ${#missing_dirs[@]} -gt 0 ] || [ ${#empty_dirs[@]} -gt 0 ]; then
  err "story-setup 参考资料包不完整"
  [ ${#missing_dirs[@]} -gt 0 ] && err "  缺目录/文件: ${missing_dirs[*]}"
  [ ${#empty_dirs[@]} -gt 0 ] && err "  目录为空: ${empty_dirs[*]}"
  err "按你的安装方式重装 oh-story-claudecode，再执行 /story-setup"
  exit 1
fi
log "参考目录检查通过（8 个子目录均非空，scripts/merge-codex-hooks.py 存在）"

# 1b. 检查是否已部署过
SENTINEL="$PROJECT_DIR/.story-deployed"
if [ -f "$SENTINEL" ]; then
  log "检测到已有部署标记 $SENTINEL"
  existing_ver=$(grep -E '^agents_version:' "$SENTINEL" | head -1 | awk '{print $2}' || true)
  if [ -n "$existing_ver" ]; then
    if [ "$existing_ver" -gt "$AGENTS_VERSION" ] 2>/dev/null; then
      err "项目 agents_version=$existing_ver 大于当前 skill 版本 $AGENTS_VERSION"
      err "当前 story-setup 比项目部署旧，停止以避免降级覆盖。请先更新 oh-story-claudecode。"
      exit 1
    elif [ "$existing_ver" -eq "$AGENTS_VERSION" ] 2>/dev/null; then
      log "项目已部署 agents_version=${existing_ver}，将执行幂等重新部署"
    else
      log "项目 agents_version=${existing_ver} < ${AGENTS_VERSION}，标记为待更新"
    fi
  else
    log "项目 agents_version 缺失或非整数，标记为待更新"
  fi
  # 已部署项目以 sentinel 的 target_cli 为准
  existing_target=$(grep -E '^target_cli:' "$SENTINEL" | head -1 | sed 's/^target_cli:[[:space:]]*//' || true)
  if [ -n "$existing_target" ]; then
    TARGET_CLI="$existing_target"
    log "沿用 sentinel 中的 target_cli=$TARGET_CLI"
  else
    TARGET_CLI="generic"
  fi
else
  TARGET_CLI="generic"
  log "全新项目，target_cli=generic"
fi

# 1c. 检查项目状态文件（不覆盖用户内容）
[ -f "$PROJECT_DIR/.active-book" ] && log "检测到 .active-book（用户状态文件，不覆盖）"
[ -d "$PROJECT_DIR/.claude" ] && warn "检测到 .claude/ 目录，generic 部署不触碰"

# ---------- Phase 2: 部署基础设施 ----------
log "Phase 2: 部署基础设施（target_cli=${TARGET_CLI}）"

# 2a. 部署 skills 目录（generic 算法第 1 步）
# SKILL.md: 复制仓库 skills/ 下所有含 SKILL.md 的 story skill 目录
# 本包仅含 story-setup；其余 12 个 skill 不在包内，如实报告
log "部署 skills/ 目录..."
SKILLS_DEST="$PROJECT_DIR/skills"
mkdir -p "$SKILLS_DEST"

deployed_skills=0
missing_skills=()
# story-setup 是本包自带的（先删后复制，避免 macOS cp -R 在目标已存在时嵌套复制）
if [ -f "$SKILL_SRC/SKILL.md" ]; then
  rm -rf "$SKILLS_DEST/story-setup"
  cp -R "$SKILL_SRC" "$SKILLS_DEST/story-setup"
  deployed_skills=$((deployed_skills + 1))
  log "  已部署: story-setup"
else
  err "story-setup 源目录缺少 SKILL.md"
  exit 1
fi

# 检查其余 12 个预期 skill 是否在同级目录可用
EXPECTED_OTHER_SKILLS=(
  browser-cdp story-long-write story-short-write
  story-long-analyze story-short-analyze story-long-scan story-short-scan
  story-deslop story-cover story-review story-import story
)
SKILL_PARENT="$(dirname "$SKILL_SRC")"
for skill_name in "${EXPECTED_OTHER_SKILLS[@]}"; do
  if [ -f "$SKILL_PARENT/$skill_name/SKILL.md" ]; then
    rm -rf "$SKILLS_DEST/$skill_name"
    cp -R "$SKILL_PARENT/$skill_name" "$SKILLS_DEST/$skill_name"
    deployed_skills=$((deployed_skills + 1))
    log "  已部署: $skill_name"
  else
    missing_skills+=("$skill_name")
  fi
done
if [ ${#missing_skills[@]} -gt 0 ]; then
  warn "以下 ${#missing_skills[@]} 个 skill 不在本包内，未部署（需完整 oh-story-claudecode 仓库）:"
  warn "  ${missing_skills[*]}"
  warn "已部署 $deployed_skills 个 skill（story-setup 完整可用）"
fi

# 2b. 部署 agent-references（generic 算法第 3 步，确保参考路径可解析）
log "部署 agent-references..."
AGENT_REF_SRC="$SKILL_SRC/references/agent-references"
AGENT_REF_DEST="$SKILLS_DEST/story-setup/references/agent-references"
mkdir -p "$AGENT_REF_DEST"
cp -R "$AGENT_REF_SRC/"* "$AGENT_REF_DEST/"
ref_count=$(find "$AGENT_REF_DEST" -name '*.md' | wc -l | tr -d ' ')
log "  agent-references: $ref_count 个 .md 文件"

# 2c. 部署 AGENTS.md（generic 算法第 2 步，按合并策略）
log "部署 AGENTS.md..."
AGENTS_TMPL="$SKILL_SRC/references/generic/AGENTS.md.tmpl"
AGENTS_DEST="$PROJECT_DIR/AGENTS.md"

# 模板占位符替换
render_template() {
  local content
  content=$(cat "$AGENTS_TMPL")
  content="${content//\{项目名\}/$PROJECT_NAME}"
  content="${content//\{书名\}/$BOOK_NAME}"
  if [ -n "$TARGET_PLATFORM" ]; then
    content="${content//\{目标平台\}/$TARGET_PLATFORM}"
  fi
  content="${content//\{作者名\}/$AUTHOR_NAME}"
  # 命令替换会去掉尾部换行，这里补回，确保结束标记在独立行
  printf '%s\n' "$content"
}

# AGENTS.md 合并策略：marker/section merge
MERGE_MARKER_BEGIN="<!-- story-setup:begin -->"
MERGE_MARKER_END="<!-- story-setup:end -->"

if [ -f "$AGENTS_DEST" ]; then
  log "  检测到已有 AGENTS.md，执行 marker/section 合并"
  if grep -qF "$MERGE_MARKER_BEGIN" "$AGENTS_DEST" && grep -qF "$MERGE_MARKER_END" "$AGENTS_DEST"; then
    # 已有管理块：替换块内内容（用临时文件避免 awk -v 多行问题）
    tmp_block=$(mktemp)
    {
      printf '%s\n' "$MERGE_MARKER_BEGIN"
      render_template
      printf '%s\n' "$MERGE_MARKER_END"
    } > "$tmp_block"
    awk -v begin="$MERGE_MARKER_BEGIN" -v end="$MERGE_MARKER_END" -v blockfile="$tmp_block" '
      $0 == begin { in_block=1; while ((getline line < blockfile) > 0) print line; close(blockfile); next }
      $0 == end { in_block=0; next }
      !in_block { print }
    ' "$AGENTS_DEST" > "$AGENTS_DEST.tmp"
    rm -f "$tmp_block"
    mv "$AGENTS_DEST.tmp" "$AGENTS_DEST"
    log "  已替换 story-setup 管理块，用户内容保留"
  else
    # 无标记：按 ## 标题切分合并，模板标准 section 覆盖同名，用户独有 section 保留
    rendered=$(render_template)
    # 简单实现：将模板内容追加到用户内容之后（用户 section 在前，模板 section 在后）
    # 更精细的 section 级合并在有冲突时应询问用户；此处无标题冲突时追加
    user_sections=$(grep -c '^## ' "$AGENTS_DEST" || true)
    tmpl_sections=$(printf '%s' "$rendered" | grep -c '^## ' || true)
    log "  用户 AGENTS.md 有 $user_sections 个 section，模板有 $tmpl_sections 个 section"
    # 检查标题冲突
    conflict=0
    while IFS= read -r heading; do
      if grep -qF "$heading" "$AGENTS_DEST"; then
        conflict=1
        warn "  section 冲突: ${heading}（模板版本覆盖）"
      fi
    done < <(printf '%s' "$rendered" | grep '^## ' || true)
    {
      cat "$AGENTS_DEST"
      echo ""
      echo "$MERGE_MARKER_BEGIN"
      render_template
      echo "$MERGE_MARKER_END"
    } > "$AGENTS_DEST.tmp"
    mv "$AGENTS_DEST.tmp" "$AGENTS_DEST"
    log "  已合并（用户内容保留，模板内容以标记块追加）"
  fi
else
  # 全新文件：写入模板并包含标记块（使后续重部署走幂等的块替换路径）
  {
    printf '%s\n' "$MERGE_MARKER_BEGIN"
    render_template
    printf '%s\n' "$MERGE_MARKER_END"
  } > "$AGENTS_DEST"
  log "  已创建新 AGENTS.md（含管理块标记）"
fi

# 2d. 创建部署标记 .story-deployed（generic 算法第 4 步 + Step 7）
log "创建部署标记..."
DEPLOYED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$SENTINEL" <<EOF
deployed_at: $DEPLOYED_AT
agents_version: $AGENTS_VERSION
setup_skill_version: $SETUP_SKILL_VERSION
target_cli: generic
resolver_strategy: project-local-skill-reference
references_dir: skills/story-setup/references/agent-references
EOF
log "  .story-deployed 已写入（agents_version=${AGENTS_VERSION}, setup_skill_version=${SETUP_SKILL_VERSION}）"

# generic 不创建 .claude/.agents-pending-restart（仅 claude-code 需要）
log "generic 目标不部署平台专属 hooks/custom agents"

# ---------- Phase 3: 验证安装 ----------
log "Phase 3: 验证安装"
verification_passed=0
verification_failed=0

check() {
  local desc="$1" cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    log "  [PASS] $desc"
    verification_passed=$((verification_passed + 1))
  else
    err  "  [FAIL] $desc"
    verification_failed=$((verification_failed + 1))
  fi
}

# Phase 3 第 11 步：验证 generic 部署
check "AGENTS.md 含通用 story skill 路由" \
  "grep -q '网文写作工具集（通用 Agent / Web AI）' '$AGENTS_DEST'"
check "AGENTS.md 含 Skill 路由表" \
  "grep -q '## Skill 路由表' '$AGENTS_DEST'"
check "skills/story-setup/SKILL.md 存在" \
  "[ -f '$SKILLS_DEST/story-setup/SKILL.md' ]"
check "agent-references 文件完整（与源目录数量一致）" \
  "[ \$(find '$AGENT_REF_DEST' -name '*.md' | wc -l | tr -d ' ') -eq \$(find '$AGENT_REF_SRC' -name '*.md' | wc -l | tr -d ' ') ]"
check ".story-deployed 含 agents_version: 24" \
  "grep -q 'agents_version: 24' '$SENTINEL'"
check ".story-deployed 含 setup_skill_version: 1.2.7" \
  "grep -q 'setup_skill_version: 1.2.7' '$SENTINEL'"
check ".story-deployed 含 target_cli: generic" \
  "grep -q 'target_cli: generic' '$SENTINEL'"
check ".story-deployed 含 resolver_strategy" \
  "grep -q 'resolver_strategy: project-local-skill-reference' '$SENTINEL'"
check ".story-deployed 含 references_dir" \
  "grep -q 'references_dir: skills/story-setup/references/agent-references' '$SENTINEL'"
check "AGENTS.md 占位符已替换（无残留 {项目名}）" \
  "! grep -q '{项目名}' '$AGENTS_DEST'"

# 验证幂等性：再次部署不应改变结果（用环境变量防止递归调用无限循环）
# 注意：deployed_at 时间戳每次更新是预期行为，比较时排除该行
if [ -z "${STORY_SETUP_IDEMPOTENCY_REENTRY:-}" ]; then
  log "验证幂等性（二次部署）..."
  snapshot() {
    {
      find "$SKILLS_DEST" -type f -exec md5 {} \;
      grep -v '^deployed_at:' "$SENTINEL"
      md5 "$AGENTS_DEST"
    } | sort | md5
  }
  BEFORE_HASH=$(snapshot)
  STORY_SETUP_IDEMPOTENCY_REENTRY=1 "$0" "$SKILL_SRC" "$PROJECT_DIR" "$PROJECT_NAME" "$BOOK_NAME" "$TARGET_PLATFORM" "$AUTHOR_NAME" >/dev/null 2>&1
  AFTER_HASH=$(snapshot)
  if [ "$BEFORE_HASH" = "$AFTER_HASH" ]; then
    log "  [PASS] 幂等性验证通过（二次部署文件哈希一致，时间戳正常更新）"
    verification_passed=$((verification_passed + 1))
  else
    err "  [FAIL] 幂等性验证失败（二次部署后文件发生变化）"
    verification_failed=$((verification_failed + 1))
  fi
else
  log "幂等性重入：跳过二次部署验证"
fi

# ---------- 安装报告 ----------
echo ""
echo "=========================================="
echo " story-setup 安装报告（target_cli=generic）"
echo "=========================================="
echo ""
echo "已部署文件："
echo "  AGENTS.md"
echo "  skills/story-setup/（含 SKILL.md、references/、scripts/、UPGRADING.md）"
echo "  skills/story-setup/references/agent-references/（$ref_count 个 .md 文件）"
echo "  .story-deployed"
echo ""
echo "部署标记："
cat "$SENTINEL"
echo ""
if [ ${#missing_skills[@]} -gt 0 ]; then
  echo "注意事项："
  echo "  - 本包仅含 story-setup，其余 ${#missing_skills[@]} 个 skill 未部署："
  echo "    ${missing_skills[*]}"
  echo "  - 如需完整功能，请安装 oh-story-claudecode 完整仓库后重新部署"
fi
echo "  - generic 不部署平台专属 hooks/custom agents"
echo "  - 大纲守卫、commit 提醒、session/compact 注入等硬拦截按 skill 内软约束执行"
echo "  - 涉及专业 Agent 的 Skill 走 solo/direct fallback"
echo "  - 去AI味自锁：每章正文落盘后同轮自检（AGENTS.md 通用使用约定）"
echo ""
echo "验证结果：$verification_passed 通过, $verification_failed 失败"
if [ $verification_failed -eq 0 ]; then
  echo "状态：部署成功"
else
  echo "状态：部署存在验证失败项，请检查"
  exit 1
fi
