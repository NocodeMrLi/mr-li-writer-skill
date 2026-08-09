#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build WeChat Official Account HTML snippets from Markdown.

The 6 built-in styles are adapted from gzh-design-skill (AGPL-3.0):
Moyu Green, Red & White, Graphite Minimal, Zen Whitespace, Moyu Ticket,
and Olive Journal.

The full gzh-design component libraries are vendored under
assets/gzh-design/references/. This script is a deterministic CLI renderer and
quick preview helper; agent-driven final layout should read the selected theme
library and assemble richer article-specific components from that source.
"""

import argparse
import html
import os
import random
import re
import subprocess
import sys


THEMES = {
    "moyu-green": {
        "name": "摸鱼绿",
        "desc": "教程、测评、清单、工具盘点",
        "main": "#059669",
        "deep": "#065F46",
        "light": "#ECFDF5",
        "lighter": "#D1FAE5",
        "mark": "#A7F3D0",
        "title": "#111827",
        "text": "#374151",
        "muted": "#9CA3AF",
        "line": "#D1D5DB",
        "surface": "#FFFFFF",
        "radius": "12px",
        "shadow": "0 8px 24px -12px rgba(5,150,105,0.38)",
        "mode": "rich-card",
    },
    "red-white": {
        "name": "红白色系",
        "desc": "深度分析、观点、力量感话题",
        "main": "#DC2626",
        "deep": "#991B1B",
        "light": "#FEF2F2",
        "lighter": "#FEE2E2",
        "mark": "#FECACA",
        "title": "#1C1917",
        "text": "#374151",
        "muted": "#9CA3AF",
        "line": "#E5E7EB",
        "surface": "#FFFFFF",
        "radius": "12px",
        "shadow": "0 4px 24px -4px rgba(220,38,38,0.15)",
        "mode": "editorial",
    },
    "graphite-minimal": {
        "name": "石墨极简风",
        "desc": "设计、科技评论、专业观点、高端品牌",
        "main": "#52525B",
        "deep": "#27272A",
        "light": "#F4F4F5",
        "lighter": "#E4E4E7",
        "mark": "#A1A1AA",
        "title": "#18181B",
        "text": "#3F3F46",
        "muted": "#A1A1AA",
        "line": "#E4E4E7",
        "surface": "#FFFFFF",
        "radius": "4px",
        "shadow": "none",
        "mode": "minimal",
    },
    "zen-whitespace": {
        "name": "留白禅意风",
        "desc": "禅意冥想、极简生活、深度随笔、艺术留白",
        "main": "#4A5D52",
        "deep": "#3D5046",
        "light": "#EEF3F0",
        "lighter": "#F7FAF8",
        "mark": "#B5C8BC",
        "title": "#2B2B2B",
        "text": "#525252",
        "muted": "#A3A3A3",
        "line": "#E8E8E8",
        "surface": "#FFFFFF",
        "radius": "0",
        "shadow": "none",
        "mode": "zen",
    },
    "moyu-ticket": {
        "name": "摸鱼票据风",
        "desc": "工具对比、创意评测、票据/门票视觉隐喻",
        "main": "#059669",
        "deep": "#064E3B",
        "light": "#ECFDF5",
        "lighter": "#D1FAE5",
        "mark": "#A7F3D0",
        "title": "#111827",
        "text": "#374151",
        "muted": "#6B7280",
        "line": "#10B981",
        "surface": "#FFFCF3",
        "radius": "3px",
        "shadow": "6px 6px 0 rgba(5,150,105,0.18)",
        "mode": "ticket",
    },
    "olive-journal": {
        "name": "橄榄手记",
        "desc": "内刊手记、深度评测、案例复盘、系统性说明",
        "main": "#ED7B2F",
        "deep": "#1E1F23",
        "light": "#FFF4E8",
        "lighter": "#F8E7D2",
        "mark": "#ED7B2F",
        "title": "#1E1F23",
        "text": "#3F3F38",
        "muted": "#8C877B",
        "line": "#D8D1C4",
        "surface": "#FBF8EF",
        "radius": "10px",
        "shadow": "0 8px 24px -16px rgba(30,31,35,0.35)",
        "mode": "journal",
    },
}

SPECIAL_THEMES = {"auto", "random"}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
GZH_REF_DIR = os.path.join(ROOT_DIR, "assets", "gzh-design", "references")
COMPONENT_HEADING_RE = re.compile(r"^##\s+组件\s+\d+\s+(.+)$", re.M)


def leaf(text):
    return '<span leaf="">%s</span>' % html.escape(normalize_cn_punctuation(text))


def normalize_cn_punctuation(text):
    text = text.replace("，", "，")
    table = str.maketrans({
        ",": "，",
        ";": "；",
        "!": "！",
        "?": "？",
        ":": "：",
        "(": "（",
        ")": "）",
    })
    text = CJK_ASCII_PUNCT.sub(lambda m: m.group(0).translate(table), text)
    text = text.replace('"', "”").replace("'", "’")
    return text


CJK_ASCII_PUNCT = re.compile(r"(?<=[一-鿿㐀-䶿])[,;!?:()]|[,;!?:()](?=[一-鿿㐀-䶿])")


def inline_html(text, theme):
    token_re = re.compile(r"(\*\*.+?\*\*|==.+?==|\+\+.+?\+\+|<u>.+?</u>|`.+?`)")
    out = []
    pos = 0
    for match in token_re.finditer(text):
        if match.start() > pos:
            out.append(leaf(text[pos:match.start()]))
        token = match.group(0)
        if token.startswith("**"):
            out.append('<strong style="color:%s;font-weight:800;">%s</strong>' % (theme["deep"], leaf(token[2:-2])))
        elif token.startswith("=="):
            out.append('<span style="border-bottom:2px solid %s;font-weight:600;">%s</span>' % (theme["mark"], leaf(token[2:-2])))
        elif token.startswith("++"):
            out.append('<span style="border-bottom:2px solid %s;font-weight:600;">%s</span>' % (theme["mark"], leaf(token[2:-2])))
        elif token.startswith("<u>"):
            out.append('<span style="border-bottom:2px solid %s;font-weight:600;">%s</span>' % (theme["mark"], leaf(token[3:-4])))
        elif token.startswith("`"):
            out.append(
                '<span style="background:#F1F5F9;color:%s;padding:1px 6px;border-radius:4px;font-family:Consolas,Monaco,monospace;font-size:14px;">%s</span>'
                % (theme["main"], leaf(token[1:-1]))
            )
        pos = match.end()
    if pos < len(text):
        out.append(leaf(text[pos:]))
    return "".join(out)


def parse_blocks(md_text):
    lines = md_text.replace("\r\n", "\n").split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            lang = stripped.strip("`").strip() or "code"
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", lang, "\n".join(code)))
            continue

        m_img = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if m_img:
            blocks.append(("image", m_img.group(1).strip(), m_img.group(2).strip()))
            i += 1
            continue

        m_head = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m_head:
            blocks.append(("heading", len(m_head.group(1)), m_head.group(2).strip()))
            i += 1
            continue

        if stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(("quote", " ".join(quote)))
            continue

        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            blocks.append(("list", items))
            continue

        if re.match(r"^\d+[.、)]\s*", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+[.、)]\s*", lines[i].strip()):
                items.append(re.sub(r"^\d+[.、)]\s*", "", lines[i].strip()))
                i += 1
            blocks.append(("olist", items))
            continue

        if re.match(r"^(-{3,}|\*{3,}|={3,})$", stripped):
            blocks.append(("hr",))
            i += 1
            continue

        para = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,6}\s|[-*]\s|\d+[.、)]\s*|>|```|!\[|---|\*\*\*)",
            lines[i].strip(),
        ):
            para.append(lines[i].strip())
            i += 1
        blocks.append(("paragraph", " ".join(para)))
    return blocks


def infer_theme(md_text, title=""):
    text = (title + "\n" + md_text[:5000]).lower()
    scores = {k: 0 for k in THEMES}
    rules = [
        ("moyu-green", ["教程", "清单", "工具", "盘点", "步骤", "方法", "指南", "避坑"]),
        ("red-white", ["观点", "深度", "分析", "争议", "为什么", "评论", "真相"]),
        ("graphite-minimal", ["科技", "ai", "设计", "专业", "品牌", "产品"]),
        ("zen-whitespace", ["随笔", "生活", "关系", "情感", "冥想", "极简", "思考"]),
        ("moyu-ticket", ["测评", "对比", "评测", "选择", "评分"]),
        ("olive-journal", ["复盘", "案例", "内刊", "系统", "报告", "实战"]),
    ]
    for theme, keywords in rules:
        if any(k.lower() in text for k in keywords):
            scores[theme] += 2
    return max(scores.items(), key=lambda item: item[1])[0] if max(scores.values()) else "moyu-green"


def resolve_theme(theme, md_text, title=""):
    if theme == "random":
        return random.choice(list(THEMES)), "random"
    if theme == "auto":
        selected = infer_theme(md_text, title)
        return selected, "auto"
    if theme not in THEMES:
        raise ValueError("未知公众号主题: %s" % theme)
    return theme, "manual"


def style_attr(value):
    return value.replace("\n", "").strip()


def container_start(theme):
    bg = theme["surface"]
    return (
        '<section style="%s">'
        % style_attr(
            "max-width:677px;margin:0 auto;background:%s;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:%s;line-height:1.8;letter-spacing:0.4px;overflow-x:hidden;padding:10px 0 22px;"
            % (bg, theme["text"])
        )
    )


def hero(title, theme):
    if theme["mode"] == "zen":
        return """
<section style="margin:32px 16px 48px;padding:40px 24px;border-top:1px solid {line};border-bottom:1px solid {line};text-align:center;">
  <p style="font-family:Georgia,'Times New Roman',serif;font-size:23px;font-weight:700;color:{title_color};margin:0;line-height:1.65;letter-spacing:0.8px;">{title}</p>
</section>""".format(line=theme["line"], title_color=theme["title"], title=leaf(title))
    if theme["mode"] == "ticket":
        return """
<section style="margin:10px 10px 34px;background:{surface};border:2px solid {main};border-radius:3px;padding:26px 22px;box-shadow:{shadow};">
  <p style="font-size:12px;color:{deep};font-weight:800;margin:0 0 10px;letter-spacing:2px;">{label}</p>
  <p style="font-size:22px;font-weight:900;color:{title_color};margin:0;line-height:1.55;">{title}</p>
</section>""".format(surface=theme["surface"], main=theme["main"], deep=theme["deep"], shadow=theme["shadow"], title_color=theme["title"], label=leaf("FEATURE TICKET"), title=leaf(title))
    return """
<section style="margin:10px 10px 32px;background:{surface};border-radius:{radius};box-shadow:{shadow};padding:28px 24px 24px;overflow:hidden;border:1px solid {line};">
  <p style="font-size:12px;color:{main};font-weight:800;margin:0 0 10px;letter-spacing:2px;">{label}</p>
  <p style="font-size:23px;font-weight:900;color:{title_color};margin:0;line-height:1.55;">{title}</p>
</section>""".format(surface=theme["surface"], radius=theme["radius"], shadow=theme["shadow"], line=theme["line"], main=theme["main"], title_color=theme["title"], label=leaf("MR.LI WRITER"), title=leaf(title))


def toc(headings, theme):
    selected = [h for h in headings if h[0] == 2][:3]
    if len(selected) < 2:
        return ""
    items = []
    for idx, (_, text) in enumerate(selected, 1):
        items.append(
            '<section style="flex:1;background:%s;border-radius:%s;padding:15px 10px;margin-right:%s;text-align:center;border:1px solid %s;">'
            '<p style="display:inline-block;background:%s;color:#FFFFFF;font-size:12px;font-weight:800;padding:2px 9px;border-radius:4px;margin:0 0 8px;">%s</p>'
            '<p style="font-size:13px;font-weight:700;color:%s;margin:0;line-height:1.5;">%s</p></section>'
            % (
                theme["light"],
                theme["radius"],
                "8px" if idx < len(selected) else "0",
                theme["lighter"],
                theme["main"],
                leaf("%02d" % idx),
                theme["title"],
                leaf(text),
            )
        )
    return '<section style="padding:0 10px 30px;"><p style="font-size:14px;color:%s;margin:0 0 14px;letter-spacing:1px;">%s</p><section style="display:flex;justify-content:space-between;">%s</section></section>' % (theme["muted"], leaf("本文看点"), "".join(items))


def section_title(text, number, theme, ending=False):
    label = "∞" if ending else "%02d" % number
    if theme["mode"] == "zen":
        return """
<section style="margin-top:64px;margin-bottom:32px;padding:0 16px;">
  <p style="font-size:10px;color:{main};font-weight:600;letter-spacing:4px;margin:0 0 10px;text-transform:uppercase;">{label}</p>
  <h3 style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:700;color:{title_color};margin:0 0 16px;letter-spacing:0.5px;line-height:1.4;">{text}</h3>
  <section style="width:40px;height:2px;background:{main};"><span leaf=""><br></span></section>
</section>""".format(main=theme["main"], title_color=theme["title"], label=leaf("%s · CHAPTER" % label), text=leaf(text))
    return """
<section style="margin-top:46px;margin-bottom:26px;padding:0 10px;">
  <section style="display:flex;align-items:center;margin-bottom:18px;padding-bottom:14px;border-bottom:3px solid {main};">
    <span style="display:inline-block;background:{main};color:#FFFFFF;font-size:17px;font-weight:900;padding:4px 13px;border-radius:6px;margin-right:14px;line-height:1.3;">{label}</span>
    <section>
      <p style="font-size:10px;color:{main};font-weight:700;letter-spacing:3px;margin:0 0 2px;text-transform:uppercase;">{en}</p>
      <h3 style="font-size:18px;font-weight:800;color:{title_color};margin:0;letter-spacing:0.5px;">{text}</h3>
    </section>
  </section>
</section>""".format(main=theme["main"], title_color=theme["title"], label=leaf(label), en=leaf("CHAPTER"), text=leaf(text))


def paragraph(text, theme):
    return '<p style="margin:0 10px 20px;font-size:15px;line-height:1.8;text-align:justify;color:%s;">%s</p>' % (theme["text"], inline_html(text, theme))


def subheading(text, theme):
    return '<p style="font-size:15px;font-weight:800;color:%s;margin:28px 10px 14px;padding-left:10px;border-left:3px solid %s;line-height:1.4;">%s</p>' % (theme["title"], theme["main"], leaf(text))


def quote(text, theme):
    return '<section style="margin:0 10px 24px;background:%s;border-radius:0 10px 10px 0;border-left:4px solid %s;padding:16px 18px;"><p style="font-size:16px;font-weight:800;color:%s;margin:0;line-height:1.8;">%s</p></section>' % (theme["light"], theme["main"], theme["deep"], leaf("「%s」" % text.strip("「」")))


def list_block(items, theme, ordered=False):
    rows = []
    for idx, item in enumerate(items, 1):
        badge = "%02d" % idx if ordered else "•"
        rows.append('<p style="margin:0 0 12px;font-size:15px;line-height:1.75;color:%s;"><span style="display:inline-block;background:%s;color:%s;border-radius:5px;padding:1px 8px;margin-right:8px;font-weight:900;">%s</span>%s</p>' % (theme["text"], theme["lighter"], theme["deep"], leaf(badge), inline_html(item, theme)))
    return '<section style="margin:0 10px 22px;padding:16px 16px 4px;background:%s;border-radius:%s;border:1px solid %s;">%s</section>' % (theme["light"], theme["radius"], theme["lighter"], "".join(rows))


def code_block(code, lang, theme):
    rows = []
    for line in code.split("\n") or [""]:
        rows.append('<p style="margin:0;font-family:Consolas,Monaco,monospace;font-size:13px;line-height:1.6;color:#E2E8F0;">%s</p>' % leaf(line.replace("  ", "　　")))
    return '<section style="margin:0 10px 22px;border-radius:8px;overflow:hidden;background:#1E293B;box-shadow:0 4px 16px -8px rgba(15,23,42,0.4);"><section style="padding:8px 14px;background:#0F172A;"><span style="font-size:12px;color:#94A3B8;font-family:Consolas,Monaco,monospace;letter-spacing:1px;">%s</span></section><section style="padding:11px 14px;">%s</section></section>' % (leaf(lang), "".join(rows))


def image_block(alt, src, theme):
    caption = ""
    if alt:
        caption = '<p style="font-size:12px;color:%s;text-align:center;margin:0 10px 24px;">%s</p>' % (theme["muted"], leaf("— %s" % alt))
    return '<section style="background:#FFF;border-radius:12px;padding:6px;border:1px solid %s;box-shadow:0 4px 12px -2px rgba(0,0,0,0.08);margin:0 10px 8px;"><section style="margin:0;border-radius:8px;overflow:hidden;"><span leaf=""><img src="%s" style="max-width:100%%;height:auto;display:block;margin:0 auto;"></span></section></section>%s' % (theme["line"], html.escape(src), caption)


def hr(theme):
    return '<section style="padding:0 10px;"><section style="height:1px;background:linear-gradient(to right,transparent,%s,%s,%s,transparent);margin:36px 0;"><span leaf=""><br></span></section></section>' % (theme["mark"], theme["main"], theme["mark"])


def signature(theme):
    return '<section style="margin:44px 10px 10px;padding:22px 20px;background:%s;border-radius:%s;border:1px solid %s;text-align:center;"><p style="font-size:14px;color:%s;margin:0 0 8px;line-height:1.8;">%s</p><p style="font-size:12px;color:%s;margin:0;">%s</p></section>' % (theme["light"], theme["radius"], theme["lighter"], theme["text"], leaf("我是 {{作者名}}，{{一句话简介}}"), theme["muted"], leaf("如果你觉得今天这篇有收获，欢迎点赞、在看、转发，我们下篇见"))


def build_section(md_text, title, theme):
    blocks = parse_blocks(md_text)
    if not title:
        for block in blocks:
            if block[0] == "heading" and block[1] == 1:
                title = block[2]
                break
    title = title or "公众号文章"
    headings = [(b[1], b[2]) for b in blocks if b[0] == "heading"]
    parts = [container_start(theme), hero(title, theme), toc(headings, theme)]
    chapter = 0
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            level, text = block[1], block[2]
            if level == 1:
                continue
            if level == 2:
                chapter += 1
                ending = bool(re.search(r"(结语|总结|最后|尾声|写在最后)", text))
                parts.append(section_title(text, chapter, theme, ending=ending))
            else:
                parts.append(subheading(text, theme))
        elif kind == "paragraph":
            parts.append(paragraph(block[1], theme))
        elif kind == "quote":
            parts.append(quote(block[1], theme))
        elif kind == "list":
            parts.append(list_block(block[1], theme, ordered=False))
        elif kind == "olist":
            parts.append(list_block(block[1], theme, ordered=True))
        elif kind == "code":
            parts.append(code_block(block[2], block[1], theme))
        elif kind == "image":
            parts.append(image_block(block[1], block[2], theme))
        elif kind == "hr":
            parts.append(hr(theme))
    parts.append(signature(theme))
    parts.append("</section>")
    return "\n".join(p for p in parts if p)


PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · 公众号排版预览</title>
<style>
body{margin:0;background:#eef0f2;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;-webkit-text-size-adjust:100%;}
.gzh-toolbar{position:fixed;top:0;left:0;right:0;height:54px;background:#ffffff;box-shadow:0 1px 10px rgba(0,0,0,.08);display:flex;align-items:center;justify-content:space-between;padding:0 16px;z-index:99;}
.gzh-hint{font-size:13px;color:#6b7280;line-height:1.4;}
.gzh-hint b{color:#111827;}
.gzh-copy{background:__MAIN__;color:#fff;border:0;border-radius:9px;padding:10px 20px;font-size:14px;font-weight:700;cursor:pointer;box-shadow:0 3px 10px rgba(0,0,0,.16);white-space:nowrap;}
.gzh-toast{position:fixed;top:66px;left:50%;transform:translateX(-50%);background:#111827;color:#fff;padding:11px 20px;border-radius:10px;font-size:14px;font-weight:600;opacity:0;pointer-events:none;transition:opacity .25s;z-index:100;box-shadow:0 6px 20px rgba(0,0,0,.25);max-width:88vw;text-align:center;}
.gzh-toast.show{opacity:1;}
.gzh-stage{max-width:700px;margin:78px auto 64px;padding:0 8px;}
</style>
</head>
<body>
<section class="gzh-toolbar">
  <span class="gzh-hint">下方是排版效果 · 点右侧 <b>复制</b> 直接粘到公众号</span>
  <button class="gzh-copy" id="gzhCopyBtn" onclick="gzhCopy()">复制到公众号</button>
</section>
<section class="gzh-toast" id="gzhToast"></section>
<section class="gzh-stage"><section id="gzh-content">
__CONTENT__
</section></section>
<script>
function gzhShowToast(msg){var t=document.getElementById('gzhToast');t.textContent=msg;t.classList.add('show');clearTimeout(t._timer);t._timer=setTimeout(function(){t.classList.remove('show');},2800);}
function gzhCopy(){var el=document.getElementById('gzh-content');var range=document.createRange();range.selectNodeContents(el);var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);var ok=false;try{ok=document.execCommand('copy');}catch(e){ok=false;}sel.removeAllRanges();gzhShowToast(ok?'已复制，去公众号编辑器粘贴即可':'自动复制失败，请手动全选再复制');}
</script>
</body>
</html>
"""


def write_preview(section_html, out_path, title, theme):
    preview_path = os.path.splitext(out_path)[0] + "_preview.html"
    page = PREVIEW_TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__MAIN__", theme["main"]).replace("__CONTENT__", section_html)
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(page)
    return preview_path


def validate_file(path):
    validator = os.path.join(SCRIPT_DIR, "validate_gzh_html.py")
    if not os.path.isfile(validator):
        return 0
    return subprocess.call([sys.executable, validator, path])


def list_themes():
    print("可用公众号主题:")
    print("  %-18s %s" % ("auto", "按题材自动匹配，默认推荐摸鱼绿"))
    print("  %-18s %s" % ("random", "从 6 套公众号主题中随机选择"))
    for key, item in THEMES.items():
        print("  %-18s %s - %s" % (key, item["name"], item["desc"]))
    if os.path.isdir(GZH_REF_DIR):
        print("\n完整组件库: %s" % GZH_REF_DIR)
        print("查看组件清单: python3 scripts/gzh_component_inventory.py .")
    else:
        print("\n[提示] 未找到完整组件库目录: %s" % GZH_REF_DIR)


def list_components():
    if not os.path.isdir(GZH_REF_DIR):
        print("[错误] 未找到完整组件库目录: %s" % GZH_REF_DIR, file=sys.stderr)
        return 1
    total = 0
    for key in THEMES:
        path = os.path.join(GZH_REF_DIR, "theme-%s.md" % key)
        if not os.path.isfile(path):
            print("[缺失] %s -> %s" % (key, path))
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            components = COMPONENT_HEADING_RE.findall(f.read())
        total += len(components)
        print("%s/%s: %d 个组件" % (THEMES[key]["name"], key, len(components)))
        for item in components:
            print("  - %s" % item.strip())
    print("总计: %d 个主题组件" % total)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Markdown -> 公众号内联 HTML")
    parser.add_argument("md", nargs="?", help="Markdown 正文文件路径")
    parser.add_argument("-o", "--output", help="输出干净公众号 HTML 片段")
    parser.add_argument("-t", "--theme", default="auto", help="公众号主题: auto/random/%s" % "/".join(THEMES))
    parser.add_argument("--title", default="", help="文章标题")
    parser.add_argument("--no-preview", action="store_true", help="只生成干净 HTML，不生成复制预览页")
    parser.add_argument("--list-themes", action="store_true", help="列出公众号主题")
    parser.add_argument("--list-components", action="store_true", help="列出已接入的 gzh-design 完整组件库")
    args = parser.parse_args()

    if args.list_themes:
        list_themes()
        return 0
    if args.list_components:
        return list_components()
    if not args.md:
        parser.error("缺少 Markdown 文件路径")
    if args.theme not in THEMES and args.theme not in SPECIAL_THEMES:
        list_themes()
        parser.error("未知公众号主题: %s" % args.theme)

    md_path = os.path.abspath(args.md)
    if not os.path.isfile(md_path):
        print("[错误] 文件不存在: %s" % md_path, file=sys.stderr)
        return 1
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    title = args.title or os.path.splitext(os.path.basename(md_path))[0]
    theme_key, reason = resolve_theme(args.theme, md_text, title)
    theme = THEMES[theme_key]
    section = build_section(md_text, title, theme)

    out_path = os.path.abspath(args.output or os.path.splitext(md_path)[0] + "_gzh.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(section)

    rc = validate_file(out_path)
    if rc != 0:
        return rc

    preview = ""
    if not args.no_preview:
        preview = write_preview(section, out_path, title, theme)

    print("[完成] 公众号主题=%s/%s (%s)" % (theme["name"], theme_key, reason))
    print("[输出] 干净正文片段: %s" % out_path)
    if preview:
        print("[输出] 复制预览页: %s" % preview)
    return 0


if __name__ == "__main__":
    sys.exit(main())
