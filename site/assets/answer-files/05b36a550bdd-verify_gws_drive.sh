#!/usr/bin/env bash
# gws-drive Skill 本地可重复验证脚本
# 用途：在不依赖外部账号、不安装新依赖的前提下，验证输入文件完整性与前置条件状态
# 用法：bash verify_gws_drive.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_FILE="${SCRIPT_DIR}/gws-drive.zip"
EXTRACT_DIR="${SCRIPT_DIR}/gws-drive-extracted"
SKILL_MD="${EXTRACT_DIR}/gws-drive/SKILL.md"

PASS=0; FAIL=0
ok()   { echo "[通过] $1"; PASS=$((PASS+1)); }
fail() { echo "[缺失] $1"; FAIL=$((FAIL+1)); }

echo "========== 1. 输入文件完整性 =========="
if [ -f "$ZIP_FILE" ]; then
  ok "ZIP 文件存在: $ZIP_FILE"
  if unzip -t "$ZIP_FILE" >/dev/null 2>&1; then
    ok "ZIP 压缩数据完整性测试通过 (unzip -t)"
  else
    fail "ZIP 文件损坏"
  fi
  echo "--- ZIP 内容 ---"
  unzip -l "$ZIP_FILE"
  echo "--- SHA256 ---"
  shasum -a 256 "$ZIP_FILE"
else
  fail "ZIP 文件不存在: $ZIP_FILE"
fi

echo ""
echo "========== 2. SKILL.md 可读性 =========="
if [ -f "$SKILL_MD" ]; then
  ok "SKILL.md 存在: $SKILL_MD"
  echo "--- SHA256 ---"
  shasum -a 256 "$SKILL_MD"
  echo "--- 行数/大小 ---"
  wc -l "$SKILL_MD"
  if head -12 "$SKILL_MD" | grep -q "name: gws-drive"; then
    ok "SKILL.md frontmatter 中 name 字段为 gws-drive"
  else
    fail "SKILL.md frontmatter 中未找到 name: gws-drive"
  fi
else
  fail "SKILL.md 不存在"
fi

echo ""
echo "========== 3. Skill 声明的依赖检查 =========="
# SKILL.md metadata.requires.bins: [gws]
if command -v gws >/dev/null 2>&1; then
  ok "gws 二进制已安装: $(command -v gws)"
  echo "--- gws --version ---"; gws --version 2>&1 || true
  echo "--- gws drive --help (前20行) ---"; gws drive --help 2>&1 | head -20 || true
else
  fail "gws 二进制未安装 (SKILL.md 声明 requires.bins: [gws])"
fi

# SKILL.md 第16行 PREREQUISITE: ../gws-shared/SKILL.md
SHARED_MD="${EXTRACT_DIR}/gws-shared/SKILL.md"
if [ -f "$SHARED_MD" ]; then
  ok "前置 Skill 存在: gws-shared/SKILL.md"
else
  fail "前置 Skill 缺失: gws-shared/SKILL.md (SKILL.md 第16行要求先读)"
fi

# SKILL.md 第26行 Helper: ../gws-drive-upload/SKILL.md
UPLOAD_MD="${EXTRACT_DIR}/gws-drive-upload/SKILL.md"
if [ -f "$UPLOAD_MD" ]; then
  ok "上传 Helper Skill 存在: gws-drive-upload/SKILL.md"
else
  fail "上传 Helper Skill 缺失: gws-drive-upload/SKILL.md (+upload 命令文档)"
fi

echo ""
echo "========== 4. 外部账号/凭据检查 =========="
if [ -d "$HOME/.config/gws" ] || [ -d "$HOME/.gws" ]; then
  ok "发现 gws 配置目录"
else
  fail "未发现 gws 配置目录 (~/.config/gws 或 ~/.gws)"
fi
if command -v gcloud >/dev/null 2>&1; then
  ok "gcloud 已安装"
else
  fail "gcloud 未安装 (无法用其完成 Google OAuth 凭据)"
fi
if env | grep -qiE "GOOGLE_APPLICATION_CREDENTIALS|GOOGLE_SERVICE_ACCOUNT"; then
  ok "发现 Google 凭据相关环境变量"
else
  fail "未发现 Google 凭据环境变量"
fi

echo ""
echo "========== 5. 汇总 =========="
echo "通过: $PASS  缺失/失败: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "结论：前置条件不满足，无法执行真实上传。以上缺失项需补齐后方可继续。"
  exit 1
else
  echo "结论：所有前置条件满足，可继续执行 gws drive 上传流程。"
fi
