#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_html.py - Markdown 文章 -> 单文件排版 HTML

零外部依赖(Python 3.8+ 标准库)。产物为单个 HTML 文件:
- 无 CDN / 无外部字体, 离线可用
- 顶部工具栏: 一键复制正文(富文本, 粘贴到公众号编辑器保留格式) + 一键下载 HTML
- 多套排版主题, CSS 存于 ../assets/themes/

用法:
    python build_html.py <正文.md> -o <输出.html> [-t 主题名] [--title "文章标题"]
    python build_html.py --list-themes

新增主题: 在 ../assets/themes/ 添加一个 .css 文件, 并在下方 THEMES 中注册即可。
"""
import argparse
import html
import os
import re
import sys

THEMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "themes")

# 主题注册表: 名称 -> (css 文件名, 一句话说明)
THEMES = {
    "minimal-gold": ("minimal-gold.css", "黑白金极简风(默认, 公众号深度文)"),
    "business-blue": ("business-blue.css", "商务深蓝报告风(政策解读/行业分析)"),
    "magazine-warm": ("magazine-warm.css", "暖色杂志风(故事性/人物稿)"),
    "fresh-green": ("fresh-green.css", "清新绿(小红书/知乎/轻阅读)"),
    "ink-scholar": ("ink-scholar.css", "水墨学者风(知乎深度/文化类, 衬线留白)"),
    "card-modern": ("card-modern.css", "卡片现代风(圆角卡片, 小红书/产品文)"),
}

DEFAULT_THEME = "minimal-gold"


# ---------------- Markdown 解析(轻量, 覆盖文章常用语法) ----------------

def render_inline(text):
    """行内元素: 转义后处理 加粗 / 斜体 / 行内代码 / 链接"""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(
        r"!\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<img src="\2" alt="\1" loading="lazy">',
        text,
    )
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    return text


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", line)) and "-" in line


def split_table_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def md_to_html(md_text):
    lines = md_text.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)
    in_code = False
    code_lines = []
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # 围栏代码块
        if stripped.startswith("```"):
            if in_code:
                out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(code_lines)))
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # 空行
        if not stripped:
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (level, render_inline(m.group(2)), level))
            i += 1
            continue

        # 分隔线: --- 或 ===== (3 个及以上)
        if re.match(r"^(-{3,}|={3,}|\*{3,})$", stripped):
            out.append("<hr>")
            i += 1
            continue

        # 引用块
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote><p>%s</p></blockquote>" % render_inline("<br>".join(buf)))
            continue

        # 表格: 当前行含 | 且下一行是分隔行
        if "|" in stripped and i + 1 < n and is_table_sep(lines[i + 1]):
            header = split_table_row(stripped)
            i += 2
            rows = []
            while i < n and "|" in lines[i].strip() and lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1
            t = ["<table><thead><tr>"]
            t += ["<th>%s</th>" % render_inline(c) for c in header]
            t.append("</tr></thead><tbody>")
            for row in rows:
                t.append("<tr>")
                t += ["<td>%s</td>" % render_inline(c) for c in row]
                t.append("</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue

        # 无序列表
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>" + "".join("<li>%s</li>" % render_inline(x) for x in items) + "</ul>")
            continue

        # 有序列表
        if re.match(r"^\d+[.、)]\s*", stripped):
            items = []
            while i < n and re.match(r"^\d+[.、)]\s*", lines[i].strip()):
                items.append(re.sub(r"^\d+[.、)]\s*", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join("<li>%s</li>" % render_inline(x) for x in items) + "</ol>")
            continue

        # 普通段落(合并连续行)
        buf = [stripped]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not re.match(r"^(#{1,6}\s|[-*]\s|\d+[.、)]\s*|>|-{3,}$|={3,}$)", lines[i].strip())
            and "|" not in lines[i]
        ):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % render_inline("<br>".join(buf)))

    if in_code:
        out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(code_lines)))
    return "\n".join(out)


# ---------------- HTML 组装 ----------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#232323">
<title>__TITLE__</title>
<style>
__CSS__
/* 阅读层：保持克制，但补足长文阅读的层级、反馈和移动端表现 */
*{box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
.reading-progress{position:fixed;top:0;left:0;z-index:110;width:0;height:3px;
  background:#b8860b;transition:width .12s linear;}
.toolbar{position:sticky;top:0;z-index:99;display:flex;gap:8px;align-items:center;
  min-height:48px;padding:8px max(16px,calc((100vw - 760px)/2));
  background:rgba(35,35,35,.96);color:#eee;font:13px/1.5 -apple-system,"Microsoft YaHei",sans-serif;
  box-shadow:0 1px 0 rgba(255,255,255,.08);}
.toolbar .tip{opacity:.75;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.toolbar button{border:1px solid rgba(255,255,255,.22);border-radius:5px;padding:7px 11px;
  font-size:13px;cursor:pointer;background:#b8860b;color:#fff;transition:background .15s,transform .15s;}
.toolbar button:hover{background:#d09b22;}
.toolbar button.ghost{background:transparent;color:#eee;}
.toolbar button.ghost:hover{background:rgba(255,255,255,.1);}
.toolbar button:active{transform:scale(.97);}
.article img{display:block;max-width:100%;height:auto;margin:24px auto;border-radius:6px;}
.article pre{overflow:auto;margin:24px 0;padding:16px;border-radius:6px;background:#202124;color:#f3f3f3;
  font:13px/1.65 Consolas,Menlo,monospace;}
.article table{display:block;overflow-x:auto;}
@media (max-width:680px){
  .toolbar{padding-left:12px;padding-right:12px;}
  .toolbar .tip{display:none;}
  .toolbar button{flex:1;min-height:38px;}
}
@media print{.toolbar,.reading-progress{display:none;}}
</style>
</head>
<body>
<div class="reading-progress" id="readingProgress" aria-hidden="true"></div>
<div class="toolbar">
  <span class="tip">__TITLE__</span>
  <button type="button" title="复制正文" onclick="copyArticle()">&#128203; 复制正文</button>
  <button class="ghost" type="button" title="下载当前 HTML" onclick="downloadHtml()">&#11015; 下载 HTML</button>
</div>
<main class="article" id="article">
<h1 class="article-title">__TITLE__</h1>
__BODY__
</main>
<script>
function copyArticle(){
  var el=document.getElementById('article');
  var done=function(ok){toast(ok?'已复制,可直接粘贴到编辑器':'复制失败,请手动全选复制');};
  try{
    if(navigator.clipboard&&window.ClipboardItem){
      var blob=new Blob([el.innerHTML],{type:'text/html'});
      var item=new ClipboardItem({'text/html':blob,'text/plain':new Blob([el.innerText],{type:'text/plain'})});
      navigator.clipboard.write([item]).then(function(){done(true);},function(){fallbackCopy(el);});
    }else{fallbackCopy(el);}
  }catch(e){fallbackCopy(el);}
}
function fallbackCopy(el){
  try{
    var range=document.createRange();range.selectNodeContents(el);
    var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);
    var ok=document.execCommand('copy');sel.removeAllRanges();
    toast(ok?'已复制(纯文本)':'复制失败,请手动全选复制');
  }catch(e){toast('复制失败,请手动全选复制');}
}
function downloadHtml(){
  try{
    var blob=new Blob(['<!DOCTYPE html>'+document.documentElement.outerHTML],{type:'text/html;charset=utf-8'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download=(document.title||'article')+'.html';a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);},1000);
  }catch(e){toast('下载失败,请使用浏览器另存为');}
}
function updateReadingProgress(){
  var doc=document.documentElement;
  var max=doc.scrollHeight-doc.clientHeight;
  var value=max>0?(doc.scrollTop/max)*100:0;
  document.getElementById('readingProgress').style.width=value+'%';
}
window.addEventListener('scroll',updateReadingProgress,{passive:true});
updateReadingProgress();
function toast(msg){
  var t=document.createElement('div');
  t.textContent=msg;
  t.style.cssText='position:fixed;left:50%;bottom:40px;transform:translateX(-50%);'+
    'background:rgba(0,0,0,.8);color:#fff;padding:10px 20px;border-radius:20px;font-size:14px;z-index:999;';
  document.body.appendChild(t);setTimeout(function(){t.remove();},2200);
}
</script>
</body>
</html>
"""

BASE_CSS_FALLBACK = """
body{margin:0;background:#f5f5f5;color:#222;font:16px/1.9 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}
.article{max-width:680px;margin:0 auto;padding:32px 20px 64px;background:#fff;}
"""


def list_themes():
    print("可用主题:")
    for name, (css, desc) in THEMES.items():
        exists = os.path.isfile(os.path.join(THEMES_DIR, css))
        mark = "" if exists else "  [缺少 CSS 文件!]"
        print("  %-15s %s%s" % (name, desc, mark))


def main():
    parser = argparse.ArgumentParser(description="Markdown -> 单文件排版 HTML")
    parser.add_argument("md", nargs="?", help="Markdown 正文文件路径")
    parser.add_argument("-o", "--output", help="输出 HTML 路径(默认: 与 md 同目录同名 .html)")
    parser.add_argument("-t", "--theme", default=DEFAULT_THEME, help="主题名(默认 %s)" % DEFAULT_THEME)
    parser.add_argument("--title", default="", help="文章标题(默认取 md 文件名)")
    parser.add_argument("--list-themes", action="store_true", help="列出可用主题")
    args = parser.parse_args()

    if args.list_themes:
        list_themes()
        return

    if not args.md:
        parser.error("缺少 Markdown 文件路径(或用 --list-themes 查看主题)")

    md_path = os.path.abspath(args.md)
    if not os.path.isfile(md_path):
        sys.stderr.write("[错误] 文件不存在: %s\n" % md_path)
        sys.exit(1)

    if args.theme not in THEMES:
        sys.stderr.write("[错误] 未知主题 '%s'\n" % args.theme)
        list_themes()
        sys.exit(1)

    css_file = os.path.join(THEMES_DIR, THEMES[args.theme][0])
    if os.path.isfile(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            css = f.read()
    else:
        sys.stderr.write("[警告] 主题 CSS 缺失, 使用内置基础样式: %s\n" % css_file)
        css = BASE_CSS_FALLBACK

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    title = args.title or os.path.splitext(os.path.basename(md_path))[0]
    body = md_to_html(md_text)

    out_path = args.output or os.path.splitext(md_path)[0] + ".html"
    out_path = os.path.abspath(out_path)

    page = (HTML_TEMPLATE
            .replace("__TITLE__", html.escape(title))
            .replace("__CSS__", css)
            .replace("__BODY__", body))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)

    print("[完成] 主题=%s" % args.theme)
    print("[输出] %s" % out_path)


if __name__ == "__main__":
    main()
