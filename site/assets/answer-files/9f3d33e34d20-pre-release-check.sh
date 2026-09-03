#!/usr/bin/env bash
# prepare-release 预检与受约束执行脚本
# 严格遵循 prepare-release/SKILL.md，加入预检、幂等、重试、人工确认点。
# 用法:
#   ./pre-release-check.sh [patch|minor|major|x.y.z|x.y.z-pre.N] [--dry-run]
# 默认 patch；--dry-run 仅预览，不创建分支/PR，不修改文件。

set -euo pipefail

# ---------- 工具函数 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[通过]${NC} $1"; }
warn() { echo -e "${YELLOW}[警告]${NC} $1"; }
fail() { echo -e "${RED}[失败]${NC} $1"; FAILURES=$((FAILURES+1)); }
info() { echo -e "[信息] $1"; }
FAILURES=0

# 带重试的命令执行（幂等网络操作）
retry() {
  local max_attempts=${RETRY_MAX:-3}
  local delay=${RETRY_DELAY:-2}
  local attempt=1
  while (( attempt <= max_attempts )); do
    if "$@"; then return 0; fi
    warn "命令失败（第 ${attempt}/${max_attempts} 次）: $*"
    (( attempt < max_attempts )) && sleep "$delay"
    attempt=$((attempt+1))
  done
  return 1
}

# ---------- 参数解析 ----------
VERSION_ARG="patch"
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    patch|minor|major) VERSION_ARG="$arg" ;;
    *) VERSION_ARG="$arg" ;;
  esac
done

echo "========================================"
echo " prepare-release 预检"
echo " 时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo " 参数: version=$VERSION_ARG dry-run=$DRY_RUN"
echo "========================================"

# ---------- Step 0: 预检 ----------
echo ""
echo "### Step 0: 环境预检"

# 0.1 必须在 git 仓库内
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REPO_ROOT=$(git rev-parse --show-toplevel)
  ok "位于 git 仓库: $REPO_ROOT"
else
  fail "当前目录不是 git 仓库（也不在父目录中）。SKILL.md Step 1/2/6 依赖 git。"
  REPO_ROOT=""
fi

# 0.2 必要命令
for cmd in git node pnpm; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "命令可用: $cmd ($($cmd --version 2>&1 | head -1))"
  else
    fail "缺少必要命令: $cmd"
  fi
done
# gh 用于创建 PR（Step 6），缺失时降级为提示而非硬失败
if command -v gh >/dev/null 2>&1; then
  ok "命令可用: gh ($(gh --version 2>&1 | head -1))"
  GH_OK=1
else
  warn "未找到 gh CLI；Step 6 创建 PR 需手动按 .agents/skills/gh-create-pr/SKILL.md 操作或安装 gh。"
  GH_OK=0
fi

# 若连 git 仓库都不是，后续文件检查无意义，直接汇总退出
if [[ -z "$REPO_ROOT" ]]; then
  echo ""
  echo "### 预检汇总"
  fail "预检未通过：缺少 git 仓库。无法继续任何发布步骤。"
  echo ""
  echo "请在 Cherry Studio 代码库根目录重新运行本脚本。"
  exit 1
fi

cd "$REPO_ROOT"

# 0.3 必要文件
for f in package.json electron-builder.yml; do
  if [[ -f "$f" ]]; then ok "文件存在: $f"; else fail "缺少必要文件: $f"; fi
done

# 0.4 工作区必须干净（幂等：避免覆盖未提交改动）
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  fail "工作区有未提交改动。请先提交或 stash，再运行发布流程（幂等保护）。"
  git status --short
else
  ok "工作区干净"
fi

# 0.5 远程与网络（带重试的只读探测）
if git remote get-url origin >/dev/null 2>&1; then
  ok "远程 origin 配置: $(git remote get-url origin)"
  if retry git fetch --tags --dry-run >/dev/null 2>&1; then
    ok "远程 tags 可访问（fetch 探测成功）"
  else
    warn "无法 fetch 远程 tags（可能无网络或无权限）；将仅使用本地 tags。"
  fi
else
  warn "未配置远程 origin；Step 6 推送分支将不可用。"
fi

# ---------- Step 1: 确定版本 ----------
echo ""
echo "### Step 1: 确定版本"

if [[ -f package.json ]]; then
  CUR_VER=$(node -p "require('./package.json').version" 2>/dev/null || echo "")
  if [[ -n "$CUR_VER" ]]; then ok "package.json 当前版本: $CUR_VER"; else fail "无法从 package.json 读取 version"; fi
else
  CUR_VER=""
fi

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -n "$LAST_TAG" ]]; then ok "最新 tag: $LAST_TAG"; else warn "未找到任何 tag；将以 package.json 版本为基准。"; fi

# 计算目标版本（仅当基准版本可读时）
NEW_VER=""
if [[ -n "$CUR_VER" ]]; then
  BASE=${LAST_TAG#v}
  if [[ -z "$BASE" ]]; then BASE="$CUR_VER"; fi
  IFS='.' read -r MAJ MIN PAT <<<"$BASE"
  case "$VERSION_ARG" in
    patch) NEW_VER="${MAJ}.${MIN}.$((PAT+1))" ;;
    minor) NEW_VER="${MAJ}.$((MIN+1)).0" ;;
    major) NEW_VER="$((MAJ+1)).0.0" ;;
    *)
      if [[ "$VERSION_ARG" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
        NEW_VER="$VERSION_ARG"
      else
        fail "无效版本号: $VERSION_ARG"
      fi
      ;;
  esac
fi

if [[ -n "$NEW_VER" ]]; then
  ok "解析目标版本: $NEW_VER (输入: $VERSION_ARG)"
else
  fail "无法确定目标版本"
fi

# ---------- Step 2: 收集 commits ----------
echo ""
echo "### Step 2: 收集 commits"
COMMIT_COUNT=0
if [[ -n "$LAST_TAG" ]]; then
  COMMITS=$(git log "${LAST_TAG}..HEAD" --format="%H %s" --no-merges 2>/dev/null || echo "")
  COMMIT_COUNT=$(echo -n "$COMMITS" | grep -c . || true)
  ok "自 ${LAST_TAG} 以来的提交数（不含 merge）: $COMMIT_COUNT"
  # 展示前 10 条供人工核对
  if [[ "$COMMIT_COUNT" -gt 0 ]]; then
    echo "  提交列表（前 10 条）:"
    echo "$COMMITS" | head -10 | while read -r h s; do
      echo "    - ${h:0:8} $s"
    done
  fi
else
  warn "无 tag，无法界定提交范围；Step 2 将跳过。"
fi

# ---------- 幂等检查：目标分支/版本是否已存在 ----------
echo ""
echo "### 幂等检查"
if [[ -n "$NEW_VER" ]]; then
  BRANCH="release/v${NEW_VER}"
  if git show-ref --verify --quiet "refs/heads/${BRANCH}" 2>/dev/null; then
    fail "本地分支已存在: ${BRANCH}（重复运行保护；如需重建请先删除该分支）"
  else
    ok "本地分支不存在: ${BRANCH}"
  fi
  if git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
    fail "远程分支已存在: origin/${BRANCH}（可能已有进行中的发布）"
  else
    ok "远程分支不存在: origin/${BRANCH}"
  fi
  if git rev-parse "v${NEW_VER}" >/dev/null 2>&1; then
    fail "tag v${NEW_VER} 已存在"
  else
    ok "tag v${NEW_VER} 不存在"
  fi
fi

# ---------- 汇总 ----------
echo ""
echo "========================================"
echo " 预检汇总: ${FAILURES} 个失败项"
echo "========================================"
if [[ "$FAILURES" -gt 0 ]]; then
  echo -e "${RED}预检未通过。未修改任何文件，未创建任何分支或 PR。${NC}"
  echo "请修复上述问题后重新运行。"
  exit 1
fi

echo -e "${GREEN}预检通过。${NC}"
echo ""
if [[ "$DRY_RUN" -eq 1 ]]; then
  info "--dry-run 模式：下一步将生成发布说明并更新文件，但不创建分支/PR。"
else
  info "下一步将生成发布说明并更新 package.json / electron-builder.yml。"
  info "按 SKILL.md Step 5，文件修改后会暂停等待人工确认，再进入 Step 6（创建分支+PR）。"
fi
echo ""
echo "目标版本: ${NEW_VER:-<未知>}"
echo "dry-run : $DRY_RUN"
echo ""
echo "注意：本脚本仅完成预检与版本解析。发布说明生成与文件更新需在 Cherry Studio"
echo "代码库内、具备 electron-builder.yml 等文件时继续执行。"
