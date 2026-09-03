#!/usr/bin/env python3
"""
设计系统交付物验证脚本 — 零外部依赖，仅使用 Python 标准库。

验证内容：
  1. 文件完整性：所有预期文件存在且非空
  2. HTML 自包含性：无外部 <link>/<script src> 引用
  3. HTML 基本结构：doctype、charset、关键闭合标签
  4. CSS 令牌定义：design-tokens.css 包含核心令牌
  5. CSS 引用一致性：组件类名在页面中被使用
  6. Markdown 文档：包含必要章节
  7. 上传脚本：语法正确、参数完整
  8. 文件大小：在合理范围内（Stitch 上传无硬性限制，但过大不合理）

用法：
  python3 verify.py [项目根目录]
  默认项目根目录为脚本所在目录的上级目录。
"""

import pathlib
import re
import sys
import py_compile
import tempfile

# ---------- 配置 ----------

EXPECTED_FILES = [
    "tokens/design-tokens.css",
    "components/components.css",
    "pages/login.html",
    "pages/dashboard.html",
    "docs/component-mapping.md",
    "docs/page-structure.md",
    "docs/stitch-sync-plan.md",
]

# 核心设计令牌（必须在 design-tokens.css 中定义）
CORE_TOKENS = [
    "--color-primary-500",
    "--color-gray-0",
    "--color-gray-900",
    "--font-family-sans",
    "--font-size-base",
    "--space-4",
    "--radius-md",
    "--shadow-sm",
    "--sidebar-width",
    "--topbar-height",
]

# 核心组件类（必须在 components.css 中定义，且至少在一个页面中使用）
CORE_COMPONENTS = [
    ".btn",
    ".btn-primary",
    ".form-input",
    ".card",
    ".badge",
    ".avatar",
    ".sidebar",
    ".topbar",
    ".table",
    ".alert",
]

MAX_FILE_SIZE = 200 * 1024  # 200KB，单文件超过此值给出警告

# ---------- 工具 ----------

passed = 0
failed = 0
warnings = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  [PASS] {msg}")


def fail(msg):
    global failed
    failed += 1
    print(f"  [FAIL] {msg}")


def warn(msg):
    global warnings
    warnings += 1
    print(f"  [WARN] {msg}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------- 验证函数 ----------

def verify_files(root: pathlib.Path):
    section("1. 文件完整性")
    for rel in EXPECTED_FILES:
        p = root / rel
        if not p.exists():
            fail(f"缺失文件: {rel}")
        elif p.stat().st_size == 0:
            fail(f"文件为空: {rel}")
        else:
            size = p.stat().st_size
            if size > MAX_FILE_SIZE:
                warn(f"文件较大 ({size} 字节): {rel}")
            ok(f"{rel} ({size} 字节)")


def verify_html(root: pathlib.Path, rel: str, required_components: list[str]):
    p = root / rel
    if not p.exists():
        return
    content = p.read_text(encoding="utf-8")

    # doctype
    if re.match(r"<!DOCTYPE html>", content, re.IGNORECASE):
        ok(f"{rel}: 包含 DOCTYPE 声明")
    else:
        fail(f"{rel}: 缺少 DOCTYPE 声明")

    # charset
    if 'charset="UTF-8"' in content or "charset='UTF-8'" in content:
        ok(f"{rel}: 包含 UTF-8 charset")
    else:
        fail(f"{rel}: 缺少 UTF-8 charset")

    # 自包含：无外部 link stylesheet
    ext_links = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', content, re.I)
    if not ext_links:
        ok(f"{rel}: 无外部 CSS 引用（自包含）")
    else:
        fail(f"{rel}: 发现外部 CSS 引用: {ext_links}")

    # 自包含：无外部 script src
    ext_scripts = re.findall(r'<script[^>]+src=["\'][^"\']+["\']', content, re.I)
    if not ext_scripts:
        ok(f"{rel}: 无外部 JS 引用（自包含）")
    else:
        fail(f"{rel}: 发现外部 JS 引用: {ext_scripts}")

    # 关键闭合标签
    for tag in ["</html>", "</head>", "</body>"]:
        if tag in content:
            ok(f"{rel}: 包含 {tag}")
        else:
            fail(f"{rel}: 缺少 {tag}")

    # 内联 <style>
    if "<style>" in content:
        ok(f"{rel}: 包含内联 <style>")
    else:
        fail(f"{rel}: 缺少内联 <style>（页面不自包含）")

    # 核心组件使用
    for cls in required_components:
        cls_name = cls.lstrip(".")
        if f'class="{cls_name}"' in content or f'class="' in content and cls_name in content:
            ok(f"{rel}: 使用组件 {cls}")
        else:
            warn(f"{rel}: 未发现组件 {cls}")


def verify_css_tokens(root: pathlib.Path):
    section("3. 设计令牌定义")
    p = root / "tokens/design-tokens.css"
    if not p.exists():
        fail("design-tokens.css 不存在，跳过令牌检查")
        return
    content = p.read_text(encoding="utf-8")
    for token in CORE_TOKENS:
        if token in content:
            ok(f"令牌已定义: {token}")
        else:
            fail(f"缺少令牌: {token}")

    # 检查 :root 选择器
    if ":root" in content:
        ok("令牌定义在 :root 选择器内")
    else:
        fail("未找到 :root 选择器")


def verify_components_css(root: pathlib.Path):
    section("4. 组件样式定义")
    p = root / "components/components.css"
    if not p.exists():
        fail("components.css 不存在，跳过组件检查")
        return set()
    content = p.read_text(encoding="utf-8")
    found = set()
    for cls in CORE_COMPONENTS:
        # 匹配 .btn { 或 .btn, 或 .btn:hover 等
        pattern = re.escape(cls) + r"[\s,:{]"
        if re.search(pattern, content):
            ok(f"组件已定义: {cls}")
            found.add(cls)
        else:
            fail(f"缺少组件定义: {cls}")
    return found


def verify_markdown(root: pathlib.Path, rel: str, required_sections: list[str]):
    section(f"5. Markdown 文档: {rel}")
    p = root / rel
    if not p.exists():
        fail(f"{rel} 不存在")
        return
    content = p.read_text(encoding="utf-8")
    for sec in required_sections:
        if sec in content:
            ok(f"包含章节: {sec}")
        else:
            fail(f"缺少章节: {sec}")


def verify_upload_script(root: pathlib.Path):
    section("6. 上传脚本语法检查")
    # 上传脚本在 Skill 解压目录中，路径相对于工作目录
    candidates = [
        root.parent / "upload-to-stitch-extracted" / "upload-to-stitch" / "scripts" / "upload_to_stitch.py",
        root / "scripts" / "upload_to_stitch.py",
    ]
    script = None
    for c in candidates:
        if c.exists():
            script = c
            break
    if script is None:
        warn("未找到 upload_to_stitch.py（不在本项目目录内，属正常）")
        return
    try:
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
            py_compile.compile(str(script), cfile=tmp.name, doraise=True)
        ok(f"上传脚本语法正确: {script.name}")
    except py_compile.PyCompileError as e:
        fail(f"上传脚本语法错误: {e}")

    # 检查必需参数
    content = script.read_text(encoding="utf-8")
    for arg in ["--project-id", "--file-path", "--api-key"]:
        if arg in content:
            ok(f"脚本包含参数: {arg}")
        else:
            fail(f"脚本缺少参数: {arg}")


def verify_no_external_deps(root: pathlib.Path):
    section("7. 零外部依赖检查")
    # 检查所有 HTML 和 CSS 文件中是否有外部 URL 引用（非 data: URI）
    external_patterns = [
        (r'<script[^>]+src=["\']https?://', "外部 JS CDN"),
        (r'<link[^>]+href=["\']https?://', "外部 CSS CDN"),
        (r'@import\s+["\']https?://', "CSS @import 外部"),
        (r'url\(["\']?https?://', "CSS url() 外部资源"),
    ]
    all_files = list((root / "pages").glob("*.html")) + \
                list((root / "tokens").glob("*.css")) + \
                list((root / "components").glob("*.css"))
    for f in all_files:
        content = f.read_text(encoding="utf-8")
        for pattern, desc in external_patterns:
            matches = re.findall(pattern, content, re.I)
            if matches:
                fail(f"{f.name}: 发现{desc} ({len(matches)} 处)")
            else:
                ok(f"{f.name}: 无{desc}")


# ---------- 主函数 ----------

def main():
    if len(sys.argv) > 1:
        root = pathlib.Path(sys.argv[1]).resolve()
    else:
        root = pathlib.Path(__file__).resolve().parent.parent

    print(f"项目根目录: {root}")
    print(f"Python: {sys.version.split()[0]}")

    if not root.is_dir():
        print(f"错误: 目录不存在: {root}")
        sys.exit(1)

    verify_files(root)
    verify_css_tokens(root)
    found_components = verify_components_css(root)

    section("2. HTML 页面验证")
    verify_html(root, "pages/login.html", [".btn", ".btn-primary", ".form-input", ".card", ".alert", ".form-check"])
    verify_html(root, "pages/dashboard.html", [".btn", ".btn-primary", ".sidebar", ".topbar", ".card", ".stat-card", ".table", ".badge", ".avatar"])

    verify_markdown(root, "docs/component-mapping.md", ["组件清单", "页面 × 组件映射", "设计令牌引用关系"])
    verify_markdown(root, "docs/page-structure.md", ["登录页", "仪表盘页", "文件组织", "技术约束"])
    verify_markdown(root, "docs/stitch-sync-plan.md", ["前置条件", "待上传文件", "上传步骤", "当前状态"])

    verify_upload_script(root)
    verify_no_external_deps(root)

    section("验证结果汇总")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  警告: {warnings}")
    if failed > 0:
        print("\n  存在失败项，请检查后重新验证。")
        sys.exit(1)
    else:
        print("\n  所有检查通过，交付物就绪。")
        sys.exit(0)


if __name__ == "__main__":
    main()
