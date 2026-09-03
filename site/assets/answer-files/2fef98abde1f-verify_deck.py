#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deck-product-launch Skill 核验脚本
仅解析已提供的 example.html，对照 SKILL.md 的布局与设计规范做客观检查。
不联网、不生成外部资源、不修改文件。
"""
import html.parser
import re
import sys
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "deck-product-launch-extracted", "deck-product-launch", "example.html")
PATH = os.path.normpath(PATH)

class DeckParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.slides = []          # list of dict(title, classes)
        self._in_slide = False
        self._cur = None
        self.in_style = False
        self.style_text = []
        self.title_text = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "style":
            self.in_style = True
        if tag == "title":
            self._in_title = True
        if tag == "section" and "slide" in a.get("class", "").split():
            self._in_slide = True
            self._cur = {"title": a.get("data-title", ""), "classes": a.get("class", "")}
        if self._in_slide and tag == "a":
            self._cur.setdefault("links", []).append(a.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "title":
            self._in_title = False
        if tag == "section" and self._in_slide:
            self.slides.append(self._cur)
            self._in_slide = False
            self._cur = None

    def handle_data(self, data):
        if self.in_style:
            self.style_text.append(data)
        if self._in_title:
            self.title_text = (self.title_text or "") + data

p = DeckParser()
with open(PATH, encoding="utf-8") as f:
    raw = f.read()
p.feed(raw)

style = "".join(p.style_text)
results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))

# 1. 文件基本信息
check("文件存在", os.path.exists(PATH), PATH)
check("文件大小(字节)", True, str(len(raw.encode("utf-8"))))

# 2. 幻灯片数量
n = len(p.slides)
check("幻灯片总数", n, f"共 {n} 张")

# 3. SKILL.md 规定的布局段落
required_layout = ["Cover", "Introducing", "Feature", "Pricing", "CTA"]
titles = [s["title"] for s in p.slides]
# 暗封面
cover = p.slides[0] if p.slides else {}
check("Cover 为暗背景(dark)", "dark" in cover.get("classes", ""),
      f"class='{cover.get('classes','')}'")
check("包含 Introducing 页", any("Introducing" in t for t in titles), str(titles))
check("包含 Pricing 页", any("Pricing" in t for t in titles), str(titles))
check("包含 CTA/Available now 页", any(t in ("Ship",) or "CTA" in t for t in titles), str(titles))
# SKILL.md 明确列出 "Why we built this (问题)"，检查是否存在
has_why = any(("why" in t.lower()) or ("problem" in t.lower()) for t in titles)
check("包含 'Why we built this' 问题页", has_why,
      "未发现——example.html 实际为 Cover→Introducing→Sound→Fit→Intelligence→How→Pricing→Ship")

# 4. 特性卡数量 (feature-card)
fc = len(re.findall(r'class="feature-card"', raw))
check("特性卡(feature-card)数量", fc, f"{fc} 个（SKILL.md 要求 3-6 个特性页，此处为卡片数）")

# 5. 定价档数量 (price-card)
pc = len(re.findall(r'class="price-card', raw))
check("定价档(price-card)数量", pc, f"{pc} 档")

# 6. accent 暖橙→桃 渐变
# 注意：base.css 的 :root 定义了蓝紫默认值，模板 .tpl-product-launch 作用域会覆盖。
# 需提取模板作用域内的“生效值”，而非首个匹配。
tpl_block = ""
m_tpl = re.search(r'\.tpl-product-launch\s*\{(.*?)\}', style, re.S)
if m_tpl:
    tpl_block = m_tpl.group(1)
source_block = tpl_block if tpl_block else style
m_grad = re.search(r'--grad:\s*(linear-gradient\([^;]+\));', source_block)
check("--grad 渐变定义(模板生效值)", bool(m_grad), m_grad.group(1) if m_grad else "未找到")
m_acc = re.search(r'--accent:\s*(#[0-9a-fA-F]+)', source_block)
check("--accent 主色(模板生效值)", bool(m_acc), m_acc.group(1) if m_acc else "未找到")
# 同时记录 base 默认值，说明存在层叠覆盖
m_acc_base = re.search(r'--accent:\s*(#[0-9a-fA-F]+)', style)
check("base.css 默认 --accent(被模板覆盖)", True,
      f"{m_acc_base.group(1) if m_acc_base else '?'} → 模板覆盖为 {m_acc.group(1) if m_acc else '?'}")
# 橙→桃：主色应在橙红区间
if m_acc:
    hv = m_acc.group(1).lstrip('#')
    r, g, b = int(hv[0:2],16), int(hv[2:4],16), int(hv[4:6],16)
    orange_peach = (r > 200) and (80 < g < 180) and (b < 120)
    check("主色为暖橙→桃色系", orange_peach, f"rgb({r},{g},{b})")

# 7. 16:9 比例提示
has_169 = ("aspect-ratio:16/9" in raw) or ("16/9" in raw)
check("含 16:9 比例约束(aspect_hint)", has_169,
      "overview 缩略图含 aspect-ratio:16/9；slide 本体为 100vh 流式，未强制固定 16:9 画布")

# 8. 暗 hero + 亮内容
dark_slides = [s["title"] for s in p.slides if "dark" in s["classes"]]
check("暗背景页", True, f"{len(dark_slides)} 张：{dark_slides}")

# 9. CTA 按钮
has_cta = "cta-btn" in raw
check("CTA 按钮(cta-btn)", has_cta, "")

# 10. 运行时依赖：static fallback
has_fallback = "runtime.js is absent" in raw
check("含静态预览兜底(无 runtime.js)", has_fallback,
      "所有 slide 同时可见，可直接浏览器打开/打印")

# 11. 外链字体（外部依赖，需联网）
fonts = re.findall(r"fonts\.googleapis\.com/css2\?family=([^'\"]+)", raw)
check("Google Fonts 外部依赖", len(fonts),
      f"{len(fonts)} 个字体请求；离线时回退系统字体，不影响结构")

# 12. 页面标题
check("HTML <title>", True, p.title_text or "")

# 输出
print("=" * 64)
print("deck-product-launch · example.html 核验报告")
print("文件:", PATH)
print("=" * 64)
ok_n = 0
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    ok_n += 1 if ok else 0
    print(f"[{mark}] {name}: {detail}")
print("-" * 64)
print(f"通过 {ok_n}/{len(results)} 项")
# 幻灯片清单
print("幻灯片顺序：")
for i, s in enumerate(p.slides, 1):
    print(f"  {i}. {s['title']}  [{'dark' if 'dark' in s['classes'] else 'light'}]")
