#!/usr/bin/env bash
# story-setup generic 部署独立验证脚本
# 严格按 SKILL.md Phase 3 验证清单 + 边界场景测试
# 用法: ./verify-deploy.sh <skill源目录> <目标项目目录>
set -uo pipefail

SKILL_SRC="${1:?用法: $0 <skill源目录> <目标项目目录>}"
PROJECT_DIR="${2:?缺少目标项目目录}"

PASS=0
FAIL=0
SKIP=0

ok()   { printf '  [PASS] %s\n' "$1"; PASS=$((PASS+1)); }
no()   { printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL+1)); }
skip() { printf '  [SKIP] %s\n' "$1"; SKIP=$((SKIP+1)); }

section() { printf '\n=== %s ===\n' "$1"; }

# ============================================================
section "一、SKILL.md Phase 3 验证（generic 目标）"
# ============================================================

AGENTS="$PROJECT_DIR/AGENTS.md"
SENTINEL="$PROJECT_DIR/.story-deployed"
SKILLS_DIR="$PROJECT_DIR/skills"
REF_DST="$SKILLS_DIR/story-setup/references/agent-references"
REF_SRC="$SKILL_SRC/references/agent-references"

# 1. 关键文件存在性
[ -f "$AGENTS" ] && ok "AGENTS.md 存在" || no "AGENTS.md 不存在"
[ -f "$SENTINEL" ] && ok ".story-deployed 存在" || no ".story-deployed 不存在"
[ -f "$SKILLS_DIR/story-setup/SKILL.md" ] && ok "skills/story-setup/SKILL.md 存在" || no "skills/story-setup/SKILL.md 不存在"

# 2. .story-deployed 字段
grep -q '^agents_version: 24$' "$SENTINEL" && ok "agents_version: 24" || no "agents_version 字段错误"
grep -q '^setup_skill_version: 1\.2\.7$' "$SENTINEL" && ok "setup_skill_version: 1.2.7" || no "setup_skill_version 字段错误"
grep -q '^target_cli: generic$' "$SENTINEL" && ok "target_cli: generic" || no "target_cli 字段错误"
grep -q '^resolver_strategy: project-local-skill-reference$' "$SENTINEL" && ok "resolver_strategy 正确" || no "resolver_strategy 字段错误"
grep -q '^references_dir: skills/story-setup/references/agent-references$' "$SENTINEL" && ok "references_dir 正确" || no "references_dir 字段错误"
grep -qE '^deployed_at: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' "$SENTINEL" && ok "deployed_at 为 UTC ISO 8601" || no "deployed_at 格式错误"

# 3. AGENTS.md 内容
grep -q '网文写作工具集（通用 Agent / Web AI）' "$AGENTS" && ok "AGENTS.md 含通用路由标题" || no "AGENTS.md 缺少通用路由标题"
grep -q '## Skill 路由表' "$AGENTS" && ok "AGENTS.md 含 Skill 路由表" || no "AGENTS.md 缺少 Skill 路由表"
grep -q 'story-setup' "$AGENTS" && ok "AGENTS.md 提及 story-setup" || no "AGENTS.md 未提及 story-setup"
grep -q '去AI味自锁' "$AGENTS" && ok "AGENTS.md 含去AI味自锁约定" || no "AGENTS.md 缺少去AI味自锁"
grep -q 'solo/direct' "$AGENTS" && ok "AGENTS.md 含 solo/direct 降级说明" || no "AGENTS.md 缺少降级说明"
! grep -q '{项目名}' "$AGENTS" && ok "无残留 {项目名} 占位符" || no "存在残留 {项目名} 占位符"
! grep -q '{书名}' "$AGENTS" && ok "无残留 {书名} 占位符" || no "存在残留 {书名} 占位符"

# 4. agent-references 完整性
src_count=$(find "$REF_SRC" -name '*.md' | wc -l | tr -d ' ')
dst_count=$(find "$REF_DST" -name '*.md' | wc -l | tr -d ' ')
[ "$src_count" = "$dst_count" ] && ok "agent-references 文件数一致（$dst_count 个）" || no "agent-references 文件数不一致（源 $src_count / 目标 ${dst_count}）"

# 验证关键参考文件存在
for ref in anti-ai-writing.md banned-words.md quality-checklist.md genre-catalog.md; do
  [ -f "$REF_DST/$ref" ] && ok "agent-references/$ref 存在" || no "agent-references/$ref 缺失"
done
[ -d "$REF_DST/genre-prose-cards" ] && ok "genre-prose-cards 目录存在" || no "genre-prose-cards 目录缺失"

# 5. generic 不应部署的文件
[ ! -d "$PROJECT_DIR/.claude" ] && ok "generic 未创建 .claude/" || no "generic 不应创建 .claude/"
[ ! -f "$PROJECT_DIR/.agents-pending-restart" ] && ok "generic 未创建 .agents-pending-restart" || no "generic 不应创建 .agents-pending-restart"

# 6. 用户已有文件不被覆盖
[ -f "$PROJECT_DIR/《雾港迷踪》/设定/题材定位.md" ] && ok "用户文件 设定/题材定位.md 保留" || no "用户文件 设定/题材定位.md 丢失"
[ -f "$PROJECT_DIR/《雾港迷踪》/大纲/小节大纲.md" ] && ok "用户文件 大纲/小节大纲.md 保留" || no "用户文件 大纲/小节大纲.md 丢失"

# ============================================================
section "二、边界场景测试"
# ============================================================

TESTDIR=$(mktemp -d)
trap 'rm -rf "$TESTDIR"' EXIT
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="$SCRIPT_DIR/deploy-generic.sh"

# 场景 1: 已有 AGENTS.md（含 story-setup 标记块）—— 应替换块内内容，保留用户内容
section "场景 1: 已有 AGENTS.md 含标记块（块替换）"
mkdir -p "$TESTDIR/p1"
cat > "$TESTDIR/p1/AGENTS.md" << 'EOF'
# 我的项目
这是用户自定义内容，必须保留。
<!-- story-setup:begin -->
旧的 story-setup 内容
<!-- story-setup:end -->
用户尾部内容。
EOF
if "$DEPLOY" "$SKILL_SRC" "$TESTDIR/p1" "测试项目" "测试书" "" "测试作者" >/dev/null 2>&1; then
  grep -q '这是用户自定义内容，必须保留' "$TESTDIR/p1/AGENTS.md" && ok "标记块前用户内容保留" || no "标记块前用户内容丢失"
  grep -q '用户尾部内容' "$TESTDIR/p1/AGENTS.md" && ok "标记块后用户内容保留" || no "标记块后用户内容丢失"
  ! grep -q '旧的 story-setup 内容' "$TESTDIR/p1/AGENTS.md" && ok "旧块内容已替换" || no "旧块内容未替换"
  grep -q '网文写作工具集' "$TESTDIR/p1/AGENTS.md" && ok "新块内容已写入" || no "新块内容未写入"
  # 验证只有一对标记
  begin_count=$(grep -c 'story-setup:begin' "$TESTDIR/p1/AGENTS.md")
  end_count=$(grep -c 'story-setup:end' "$TESTDIR/p1/AGENTS.md")
  [ "$begin_count" = "1" ] && [ "$end_count" = "1" ] && ok "标记块唯一（begin=$begin_count, end=${end_count}）" || no "标记块不唯一（begin=$begin_count, end=${end_count}）"
else
  no "部署脚本执行失败"
fi

# 场景 2: 已有 AGENTS.md（无标记块）—— 应追加标记块，保留全部用户内容
section "场景 2: 已有 AGENTS.md 无标记块（追加合并）"
mkdir -p "$TESTDIR/p2"
cat > "$TESTDIR/p2/AGENTS.md" << 'EOF'
# 纯用户项目
这是完全自定义的 AGENTS.md，没有任何 story-setup 标记。
## 用户自定义节
用户的内容。
EOF
if "$DEPLOY" "$SKILL_SRC" "$TESTDIR/p2" "测试项目2" "测试书2" "" "作者2" >/dev/null 2>&1; then
  grep -q '纯用户项目' "$TESTDIR/p2/AGENTS.md" && ok "用户原有标题保留" || no "用户原有标题丢失"
  grep -q '用户自定义节' "$TESTDIR/p2/AGENTS.md" && ok "用户自定义节保留" || no "用户自定义节丢失"
  grep -q 'story-setup:begin' "$TESTDIR/p2/AGENTS.md" && ok "已追加标记块" || no "未追加标记块"
  grep -q '网文写作工具集' "$TESTDIR/p2/AGENTS.md" && ok "模板内容已追加" || no "模板内容未追加"
else
  no "部署脚本执行失败"
fi

# 场景 3: 降级保护（agents_version > 24 应停止）
section "场景 3: 降级保护（agents_version > 24）"
mkdir -p "$TESTDIR/p3"
cat > "$TESTDIR/p3/.story-deployed" << 'EOF'
deployed_at: 2099-01-01T00:00:00Z
agents_version: 99
setup_skill_version: 9.9.9
target_cli: generic
EOF
if "$DEPLOY" "$SKILL_SRC" "$TESTDIR/p3" "降级测试" "降级书" "" "作者" >/dev/null 2>&1; then
  no "降级保护未触发（脚本应失败退出）"
else
  # 验证未覆盖已有文件
  grep -q 'agents_version: 99' "$TESTDIR/p3/.story-deployed" && ok "高版本 sentinel 未被覆盖" || no "高版本 sentinel 被修改"
  ok "降级保护正确触发（脚本退出码非 0）"
fi

# 场景 4: 幂等性（三次部署后文件一致）
section "场景 4: 三次部署幂等性"
mkdir -p "$TESTDIR/p4"
"$DEPLOY" "$SKILL_SRC" "$TESTDIR/p4" "幂等测试" "幂等书" "" "作者" >/dev/null 2>&1
snapshot4() {
  {
    find "$TESTDIR/p4/skills" -type f -exec md5 {} \;
    grep -v '^deployed_at:' "$TESTDIR/p4/.story-deployed"
    md5 "$TESTDIR/p4/AGENTS.md"
  } | sort | md5
}
H1=$(snapshot4)
STORY_SETUP_IDEMPOTENCY_REENTRY=1 "$DEPLOY" "$SKILL_SRC" "$TESTDIR/p4" "幂等测试" "幂等书" "" "作者" >/dev/null 2>&1
H2=$(snapshot4)
STORY_SETUP_IDEMPOTENCY_REENTRY=1 "$DEPLOY" "$SKILL_SRC" "$TESTDIR/p4" "幂等测试" "幂等书" "" "作者" >/dev/null 2>&1
H3=$(snapshot4)
if [ "$H1" = "$H2" ] && [ "$H2" = "$H3" ]; then
  ok "三次部署快照一致（${H1}）"
else
  no "三次部署快照不一致（H1=$H1 H2=$H2 H3=${H3}）"
fi

# 场景 5: 参考资料不完整时应拒绝部署
section "场景 5: 参考资料不完整时拒绝部署"
mkdir -p "$TESTDIR/p5"
BROKEN_SRC="$TESTDIR/broken-skill"
cp -R "$SKILL_SRC" "$BROKEN_SRC"
rm -rf "$BROKEN_SRC/references/generic"
if "$DEPLOY" "$BROKEN_SRC" "$TESTDIR/p5" "残缺测试" "残缺书" "" "作者" >/dev/null 2>&1; then
  no "不完整参考包未被拒绝"
else
  [ ! -f "$TESTDIR/p5/.story-deployed" ] && ok "不完整参考包未产生部署标记" || no "不完整参考包仍产生了部署标记"
  ok "不完整参考包正确拒绝"
fi
rm -rf "$BROKEN_SRC"

# 场景 6: 用户已有 .active-book 不被覆盖
section "场景 6: .active-book 用户状态文件保留"
mkdir -p "$TESTDIR/p6"
echo "用户的活跃书名" > "$TESTDIR/p6/.active-book"
"$DEPLOY" "$SKILL_SRC" "$TESTDIR/p6" "状态测试" "状态书" "" "作者" >/dev/null 2>&1
[ "$(cat "$TESTDIR/p6/.active-book")" = "用户的活跃书名" ] && ok ".active-book 未被修改" || no ".active-book 被覆盖"

# ============================================================
section "三、汇总"
# ============================================================
TOTAL=$((PASS+FAIL+SKIP))
echo "通过: $PASS / $TOTAL"
echo "失败: $FAIL / $TOTAL"
echo "跳过: $SKIP / $TOTAL"
if [ $FAIL -eq 0 ]; then
  echo "结论: 全部验证通过"
  exit 0
else
  echo "结论: 存在 $FAIL 项失败"
  exit 1
fi
