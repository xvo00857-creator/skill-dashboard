#!/usr/bin/env bash
# ============================================================================
# SwiftUI 演示组件类型检查验证脚本
#
# 受约束流程：
#   预检 → 清理（幂等）→ 类型检查（含重试）→ 报告结果
#
# 本脚本只做只读类型检查（-typecheck），不生成可执行文件，
# 不创建/删除项目目录之外的任何资源。
# ============================================================================
set -euo pipefail

# ---- 配置 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/.build-check"
SDK_PATH=""
TARGET="arm64-apple-macos14.0"
MAX_RETRIES=3
RETRY_DELAY=2

# 源文件（不含 #Preview 宏文件，因为宏插件需完整 Xcode）
SOURCE_FILES=(
    "${SCRIPT_DIR}/TaskModels.swift"
    "${SCRIPT_DIR}/TaskComponents.swift"
    "${SCRIPT_DIR}/TaskListView.swift"
    "${SCRIPT_DIR}/TaskPreviewVerification.swift"
)

# 宏预览文件（仅在完整 Xcode 中可编译，此处只检查文件存在）
MACRO_PREVIEW_FILE="${SCRIPT_DIR}/TaskPreviews.swift"

PASS=0
FAIL=0

# ---- 工具函数 ----
log()  { printf "[%s] %s\n" "$(date '+%H:%M:%S')" "$*"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
err()  { printf "  \033[31m✗\033[0m %s\n" "$*"; }

# ---- 预检 ----
preflight() {
    log "=== 预检开始 ==="

    # 1. 检查 swiftc
    if ! command -v swiftc &>/dev/null; then
        err "未找到 swiftc，请安装 Xcode Command Line Tools"
        exit 1
    fi
    ok "swiftc 可用：$(swiftc --version | head -1)"

    # 2. 检查 macOS SDK
    SDK_PATH="$(xcrun --sdk macosx --show-sdk-path 2>/dev/null || true)"
    if [[ -z "${SDK_PATH}" || ! -d "${SDK_PATH}" ]]; then
        err "未找到 macOS SDK"
        exit 1
    fi
    ok "macOS SDK：${SDK_PATH}"

    # 3. 检查 iOS SDK（标注为不可用，不阻断）
    if ! xcrun --sdk iphoneos --show-sdk-path &>/dev/null; then
        ok "iOS SDK：不可用（仅 Command Line Tools，iOS 目标需完整 Xcode）"
    else
        ok "iOS SDK：可用"
    fi

    # 4. 检查源文件
    for f in "${SOURCE_FILES[@]}"; do
        if [[ ! -f "$f" ]]; then
            err "源文件缺失：$f"
            exit 1
        fi
    done
    ok "源文件齐全（${#SOURCE_FILES[@]} 个）"

    if [[ -f "${MACRO_PREVIEW_FILE}" ]]; then
        ok "宏预览文件存在（#Preview 需完整 Xcode 编译，本次跳过类型检查）"
    fi

    log "=== 预检通过 ==="
}

# ---- 幂等清理 ----
cleanup() {
    log "=== 幂等清理 ==="
    if [[ -d "${BUILD_DIR}" ]]; then
        rm -rf "${BUILD_DIR}"
        ok "已清理旧的构建目录：${BUILD_DIR}"
    fi
    mkdir -p "${BUILD_DIR}"
    ok "构建目录就绪：${BUILD_DIR}"
}

# ---- 带重试的类型检查 ----
typecheck_with_retry() {
    local desc="$1"
    shift
    local attempt=1
    local rc=0

    while (( attempt <= MAX_RETRIES )); do
        log "类型检查 [${desc}]（第 ${attempt}/${MAX_RETRIES} 次）"
        if swiftc \
            -sdk "${SDK_PATH}" \
            -target "${TARGET}" \
            -parse-as-library \
            -typecheck \
            "$@" 2>&1; then
            ok "[${desc}] 类型检查通过"
            PASS=$((PASS + 1))
            return 0
        else
            rc=$?
            if (( attempt < MAX_RETRIES )); then
                log "类型检查失败，${RETRY_DELAY}s 后重试…"
                sleep "${RETRY_DELAY}"
            fi
        fi
        attempt=$((attempt + 1))
    done

    err "[${desc}] 类型检查在 ${MAX_RETRIES} 次尝试后仍失败"
    FAIL=$((FAIL + 1))
    return "${rc}"
}

# ---- 正确性规则静态扫描 ----
static_checks() {
    log "=== 正确性规则静态扫描 ==="
    local issues=0

    # 检查 @State 是否为 private（排除注释行）
    if grep -rn '@State\s\+var' "${SCRIPT_DIR}"/Task*.swift | grep -v 'private' | grep -v '_state' | grep -v 'PreviewProvider' | grep -v '^\s*//'; then
        err "发现非 private 的 @State 属性"
        issues=$((issues + 1))
    else
        ok "所有 @State 属性均为 private"
    fi

    # 检查 @FocusState 是否为 private
    if grep -rn '@FocusState\s\+var' "${SCRIPT_DIR}"/Task*.swift | grep -v 'private' | grep -v '^\s*//'; then
        err "发现非 private 的 @FocusState 属性"
        issues=$((issues + 1))
    else
        ok "所有 @FocusState 属性均为 private"
    fi

    # 检查是否使用了已废弃的 .animation() 无 value 参数
    if grep -rn '\.animation(\.' "${SCRIPT_DIR}"/Task*.swift | grep -v 'value:' | grep -v '^\s*//'; then
        err "发现未带 value 参数的 .animation() 调用"
        issues=$((issues + 1))
    else
        ok "所有 .animation() 调用均包含 value 参数"
    fi

    # 检查 ForEach 是否使用了 .indices（排除注释行）
    if grep -rn 'ForEach.*\.indices' "${SCRIPT_DIR}"/Task*.swift | grep -v '^\s*//'; then
        err "ForEach 使用了 .indices（不稳定身份）"
        issues=$((issues + 1))
    else
        ok "ForEach 未使用 .indices"
    fi

    # 检查是否使用了已废弃的 foregroundColor
    if grep -rn '\.foregroundColor(' "${SCRIPT_DIR}"/Task*.swift | grep -v '^\s*//'; then
        err "使用了已废弃的 .foregroundColor()，应改用 .foregroundStyle()"
        issues=$((issues + 1))
    else
        ok "未使用已废弃的 .foregroundColor()"
    fi

    # 检查是否使用了 onTapGesture 而非 Button
    if grep -rn 'onTapGesture' "${SCRIPT_DIR}"/Task*.swift | grep -v '^\s*//'; then
        err "使用了 onTapGesture，可点击元素应优先使用 Button"
        issues=$((issues + 1))
    else
        ok "可点击元素均使用 Button"
    fi

    if (( issues > 0 )); then
        err "静态扫描发现 ${issues} 个问题"
        FAIL=$((FAIL + 1))
    else
        ok "静态扫描全部通过"
        PASS=$((PASS + 1))
    fi
}

# ---- 主流程 ----
main() {
    log "SwiftUI 演示组件验证开始"
    log "工作目录：${SCRIPT_DIR}"

    preflight
    cleanup

    log "=== 类型检查 ==="
    typecheck_with_retry "全部源文件" "${SOURCE_FILES[@]}" || true

    static_checks

    log "=== 验证结果 ==="
    log "通过：${PASS}  失败：${FAIL}"

    if (( FAIL > 0 )); then
        err "验证未全部通过，请检查上方错误信息"
        exit 1
    fi
    ok "全部验证通过"
}

main "$@"
