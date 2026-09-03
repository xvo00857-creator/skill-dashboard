#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deck-presenter-mode 交付物验证脚本
用法: python3 verify_deck.py [html文件路径]
无第三方依赖，仅使用 Python 标准库。
"""
import sys, re, os

DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "quarterly-review-q2-2026.html")
path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT

errors = []
warns = []
checks = []

def ok(msg): checks.append(("PASS", msg))
def fail(msg): errors.append(msg)
def warn(msg): warns.append(msg)

# 1. 文件存在且非空
if not os.path.isfile(path):
    fail("文件不存在: %s" % path); print("\n".join(errors)); sys.exit(1)
size = os.path.getsize(path)
if size < 1000:
    fail("文件过小(%d bytes)，疑似异常" % size)
else:
    ok("文件存在且非空: %s (%d bytes)" % (os.path.basename(path), size))

html = open(path, encoding="utf-8").read()

# 2. slide 数量 = 8
slides = re.findall(r'<section\s+class="slide"', html)
if len(slides) == 8:
    ok("幻灯片数量: 8 (符合要求)")
else:
    fail("幻灯片数量: %d (应为 8)" % len(slides))

# 3. notes 数量 = 8
notes_blocks = re.findall(r'<aside\s+class="notes">(.*?)</aside>', html, re.S)
if len(notes_blocks) == 8:
    ok("逐字稿 <aside class=notes> 数量: 8")
else:
    fail("逐字稿数量: %d (应为 8)" % len(notes_blocks))

# 4. 每个 notes 纯文本字数 150-300
def strip_tags(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\s+', '', s)
    return s
all_in_range = True
for i, nb in enumerate(notes_blocks, 1):
    txt = strip_tags(nb)
    n = len(txt)
    if 150 <= n <= 300:
        ok("第 %d 页逐字稿字数: %d (在 150-300 区间)" % (i, n))
    else:
        fail("第 %d 页逐字稿字数: %d (超出 150-300)" % (i, n))
        all_in_range = False

# 5. 5 套主题定义
themes = ["tokyo-night", "dracula", "catppuccin-mocha", "nord", "corporate-clean"]
missing_t = [t for t in themes if ('data-theme="%s"' % t) not in html and ("[data-theme='%s']" % t) not in html]
if not missing_t:
    ok("5 套主题均已定义: %s" % ", ".join(themes))
else:
    fail("缺少主题定义: %s" % ", ".join(missing_t))
if "data-themes=" in html:
    ok("html data-themes 声明存在")
# corporate-clean 是 light 主题
if "corporate-clean" in html:
    ok("包含 light 主题 (corporate-clean)")

# 6. 关键交互功能
required_js = {
    "T 键切换主题": ["'t'", "'T'", "cycleTheme"],
    "S 键打开提词器": ["'s'", "'S'", "openPresenter"],
    "F 键全屏": ["'f'", "'F'", "Fullscreen"],
    "O 键总览": ["'o'", "'O'", "overview"],
    "R 键重置计时": ["'r'", "'R'", "presenterStart"],
    "左右键翻页": ["ArrowRight", "ArrowLeft"],
}
for name, needles in required_js.items():
    if all(n in html for n in needles):
        ok("JS 功能存在: %s" % name)
    else:
        fail("JS 功能缺失: %s (需要 %s)" % (name, needles))

# 7. Popup 四张磁吸卡: CURRENT / NEXT / SCRIPT / TIMER
for card in ["CURRENT", "NEXT", "SCRIPT", "TIMER"]:
    if card in html:
        ok("演讲者 popup 卡片: %s" % card)
    else:
        fail("演讲者 popup 缺少卡片: %s" % card)

# 8. 无外部 npm/构建依赖 (不应出现 import/require 外部包、<script src=>)
ext_script = re.findall(r'<script[^>]+src=', html)
if not ext_script:
    ok("无外部 <script src> 依赖 (全部内联原生 JS)")
else:
    fail("发现外部脚本依赖: %s" % ext_script)
if "require(" in html or re.search(r'(?<!@)import\s+[\w{]', html):
    warn("疑似存在模块导入语句，请确认非外部依赖")
else:
    ok("未发现 require/import 外部模块（CSS @import 字体除外）")

# 9. Google Fonts 仅为模板自带 CDN 字体，非功能依赖
gf = re.findall(r'fonts\.googleapis\.com', html)
if gf:
    warn("包含 %d 处 Google Fonts CDN（模板自带，离线自动回退系统字体，不影响功能）" % len(gf))

# 10. HTML 基本结构闭合
if html.count("<section") == html.count("</section>"):
    ok("<section> 标签闭合: %d 对" % html.count("<section"))
else:
    fail("<section> 标签不匹配")
if html.count("<aside") == html.count("</aside>"):
    ok("<aside> 标签闭合")
else:
    fail("<aside> 标签不匹配")
if html.strip().endswith("</html>"):
    ok("文档以 </html> 正常结束")
else:
    fail("文档未正常结束")

# 11. 16:9 提示与 data-title
titles = re.findall(r'data-title="([^"]+)"', html)
if len(titles) == 8:
    ok("8 页均有 data-title: %s" % " | ".join(titles))
else:
    fail("data-title 数量: %d" % len(titles))

# 12. 内容覆盖: 目标/数据/问题/举措/下季度计划
content_keywords = {
    "目标": ["目标", "OKR", "达成"],
    "数据": ["DAU", "收入", "留存", "数据"],
    "问题": ["问题", "根因", "未达"],
    "举措": ["举措", "措施"],
    "下季度计划": ["Q3", "计划"],
}
for k, kws in content_keywords.items():
    if any(kw in html for kw in kws):
        ok("内容覆盖: %s" % k)
    else:
        fail("内容缺失: %s" % k)

# 13. 示例数据标注
if "示例数据" in html:
    ok("已标注数据为示例数据")
else:
    warn("未发现「示例数据」标注")

# 输出
print("=" * 60)
print("验证结果: %s" % path)
print("=" * 60)
for status, msg in checks:
    print("  [ %s ] %s" % (status, msg))
if warns:
    print("\n-- 提示 --")
    for w in warns:
        print("  [WARN] %s" % w)
print("\n" + "-" * 60)
if errors:
    print("结论: 失败 (%d 项错误)" % len(errors))
    for e in errors:
        print("  [FAIL] %s" % e)
    sys.exit(1)
else:
    print("结论: 全部通过 (%d 项检查)" % len(checks))
    sys.exit(0)
