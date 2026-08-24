#!/usr/bin/env python3
"""组件库源头检查器 —— 可验证循环的第一道关。

扫描 references/ 下所有组件库 .md 里的 ```html 代码块，检测会导致
排版问题的反模式。只看真实组件 HTML，不被说明文字干扰（grep 做不到）。

与 validate_gzh_html.py 配合构成闭环：
  改组件库 → component_lint.py 扫源头 → 生成产物 → validate_gzh_html.py 扫产物 → 修 → 重复

用法：
    component_lint.py [skill-dir]   # 默认当前目录
退出码：1 = 有 ERROR，0 = 通过。
"""

import glob
import os
import re
import sys

CJK = re.compile(r"[一-鿿㐀-䶿]")

# (正则, 级别, 说明) —— 在每个 ```html 组件块内检查
CHECKS = [
    (re.compile(r"white-space\s*:\s*pre", re.I), "ERROR",
     "用了 white-space:pre —— 会把 HTML 源码缩进/换行渲染成大左缩进+空行；"
     "代码块改成每行一个 <p style=\"margin:0\">，缩进用全角空格"),
    (re.compile(r"</?div[\s>]", re.I), "ERROR", "出现 <div>，应用 <section>"),
    (re.compile(r"\sclass\s*=", re.I), "ERROR", "出现 class 属性（会被公众号剥离）"),
    (re.compile(r"\sid\s*=", re.I), "ERROR", "出现 id 属性"),
    (re.compile(r"<style[\s>]", re.I), "ERROR", "出现 <style> 标签"),
    (re.compile(r"position\s*:\s*(fixed|absolute|sticky)", re.I), "ERROR",
     "position fixed/absolute/sticky 不被支持"),
    (re.compile(r"display\s*:\s*grid", re.I), "ERROR", "display:grid 不被支持"),
    (re.compile(r"var\s*\(\s*--", re.I), "ERROR", "用了 CSS 变量 var(--x)"),
    (re.compile(r"@(media|keyframes|import)", re.I), "ERROR", "@media/@keyframes/@import 不被支持"),
]

# 四周虚线框：border: ... dashed（不含方向，如 border-left dashed 不算）
FOURSIDE_DASHED = re.compile(r"border\s*:\s*[^;{}]*dashed", re.I)
CENTERED = re.compile(r"text-align\s*:\s*center", re.I)
COMPONENT_BLOCK = re.compile(
    r"^##\s+组件\s+\d+\s+(.+?)\n(.*?)(?=^##\s+组件\s+\d+\s+|^##\s+完整文章模板骨架|\Z)",
    re.M | re.S,
)
PUBLIC_PROCESS_LABEL = re.compile(r"公众号排版|深度文章|中文内容创作\s*Skill", re.I)
NARROW_FIXED_CARD = re.compile(r"width\s*:\s*(?:[6-9]\d|1[01]\d|120)px", re.I)
ADAPTIVE_CARD_COMPONENT = re.compile(
    r"数据|要点卡|对比|布局组件|flow-cards|three-col|ticket-cover|票据封面",
    re.I,
)


def lint_file(path):
    with open(path, encoding="utf-8", errors="replace") as source:
        text = source.read()
    name = os.path.basename(path).replace("公众号排版组件库 —— ", "").replace(".md", "")
    found = []  # (level, msg)
    seen = set()

    def add(level, msg):
        if msg not in seen:
            seen.add(msg)
            found.append((level, msg))

    for m in re.finditer(r"```html\s*\n(.*?)```", text, re.S):
        html = m.group(1)
        for rx, level, msg in CHECKS:
            if rx.search(html):
                add(level, msg)
        # 原 gzh-design 主题中部分引用框、亮点卡和素材占位会刻意使用
        # 四周虚线作为设计语言；这里不把 dashed 本身视为源头问题。

    for match in COMPONENT_BLOCK.finditer(text):
        title, body = match.group(1), match.group(2)
        snippets = re.findall(r"```html\s*\n(.*?)```", body, re.S)
        html = "\n".join(snippets)
        if re.search(r"章节标题|section-title|chapter-title", title, re.I):
            if "{{编号}}" not in html:
                add("ERROR", "章节标题组件未使用 {{编号}} 动态占位，容易让所有章节都保留 01")
        if re.search(r"目录|导读|toc", title, re.I):
            if NARROW_FIXED_CARD.search(html) and "overflow-wrap:anywhere" not in html:
                add("ERROR", "目录/导读含窄固定宽度卡片但没有长文本换行兜底")
        if ADAPTIVE_CARD_COMPONENT.search(title) and "flex:1" in html:
            if "min-width:0" not in html or "overflow-wrap:anywhere" not in html:
                add("ERROR", "多列卡片缺少 min-width:0 或 overflow-wrap:anywhere，长文本可能溢出")
        if PUBLIC_PROCESS_LABEL.search(html):
            add("ERROR", "组件可见文本含公众号排版/深度文章/内容创作 Skill 等生产标签")
    return name, found


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    candidate_dirs = [
        os.path.join(root, "assets", "gzh-design", "references"),
        os.path.join(root, "references"),
    ]
    ref_dir = next((d for d in candidate_dirs if os.path.isdir(d)), candidate_dirs[0])
    refs = sorted(
        p for p in glob.glob(os.path.join(ref_dir, "*.md"))
        if os.path.basename(p).startswith("theme-")
        and os.path.basename(p) not in {"theme-index.md", "theme-generator.md"}
    )
    if not refs:
        print(f"未找到公众号主题组件库: {ref_dir}/*.md")
        sys.exit(1)

    total_err = total_warn = clean = 0
    print(f"📐 组件库源头检查：{len(refs)} 个库\n")
    for path in refs:
        name, found = lint_file(path)
        if not found:
            clean += 1
            continue
        errs = [m for lv, m in found if lv == "ERROR"]
        warns = [m for lv, m in found if lv == "WARN"]
        total_err += len(errs)
        total_warn += len(warns)
        print(f"── {name} ──")
        for m in errs:
            print(f"   ❌ {m}")
        for m in warns:
            print(f"   ⚠️  {m}")

    print(f"\n汇总：{clean}/{len(refs)} 个库干净，ERROR×{total_err}，WARN×{total_warn}")
    if total_err == 0 and total_warn == 0:
        print("✅ 全部组件库源头无反模式")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
