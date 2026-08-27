#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_html.py - Markdown 内容 -> 平台 HTML / 复制预览 HTML

零外部依赖(Python 3.8+ 标准库)。可生成单个预览页，或在排版交付时生成干净页 + 复制预览页:
- 无 CDN / 无外部字体, 离线可用
- 顶部工具栏: 按发布平台复制富文本或纯文本 + 一键下载 HTML
- 自动按发布平台切换交付样式。公众号使用 gzh-design 风格的内联 HTML 主题。

用法:
    python build_html.py <正文.md> -o <输出.html> [-t 主题名] [--title "文章标题"]
    python build_html.py --list-themes
"""
import argparse
import html
import os
import random
import re
import subprocess
import sys

DEFAULT_THEME = "auto"
SPECIAL_THEMES = {"auto", "random"}

GZH_THEMES = {
    "moyu-green": "摸鱼绿 - 教程、测评、清单、工具盘点",
    "red-white": "红白色系 - 深度分析、观点、力量感话题",
    "graphite-minimal": "石墨极简风 - 设计、科技评论、专业观点",
    "zen-whitespace": "留白禅意风 - 随笔、极简生活、沉静表达",
    "moyu-ticket": "摸鱼票据风 - 工具对比、创意评测",
    "olive-journal": "橄榄手记 - 案例复盘、内刊手记、系统说明",
}

DELIVERY_STYLES = {
    "gzh-article": "公众号内联 HTML + 复制预览页",
    "article-html": "通用文章 HTML",
    "zhihu-answer": "知乎问答/专栏预览",
    "xhs-note": "小红书手机笔记卡片, 纯文本复制",
    "web-article": "官网/网页结构化文章",
    "blog-post": "个人博客长文",
}

SPECIAL_DELIVERY_STYLES = {"auto"}

PROCESS_LEAK_PATTERNS = (
    r"(抓取|爬取|采集)(到|自|于|时间|结果|数据|页面|信息)?",
    r"(检索|搜索|查询)(结果|显示|发现|到|出来)",
    r"(我|我们)?(通过|使用|借助).{0,12}(搜索引擎|爬虫|脚本|工具|模型|AI|大模型|提示词|prompt)",
    r"(由|通过).{0,12}(AI|模型|大模型|系统).{0,12}(生成|整理|撰写|输出)",
    r"(资料|数据|信息)(抓取|爬取|采集|清洗|抽取|汇总|整理)(时间|结果|口径)?",
    r"(本次|这次).{0,8}(整理|检索|搜索|抓取|采集).{0,12}(发现|得到|结果)",
    r"(截至|截止)\s*\d{4}\s*年\s*\d{1,2}\s*月\s*(抓取|爬取|采集|检索)",
    r"\d{4}\s*年\s*\d{1,2}\s*月\s*(抓取|爬取|采集|检索)",
)

COMMERCIAL_SOURCE_EXPOSURE = re.compile(
    r"(?:数据|资料|信息|内容).{0,24}(?:来自|来源于|据).{0,70}(?:51CTO|希赛网|(?<!相关)[\u4e00-\u9fffA-Za-z0-9]{2,16}(?:培训|网校|辅导|题库|课堂))",
    re.I,
)


def warn_process_leaks(text, label="正文"):
    hits = []
    for pattern in PROCESS_LEAK_PATTERNS:
        if re.search(pattern, text, re.I):
            hits.append(pattern)
    if hits:
        sys.stderr.write(
            "[警告] %s疑似暴露内容生产/资料处理过程；请改为“信息截至 YYYY-MM-DD”“据官网当前页面”“公开资料显示”等读者口径，避免抓取/爬取/采集/检索结果/AI 生成/提示词等词。\n"
            % label
        )


def warn_commercial_source_exposure(text, label="正文"):
    if COMMERCIAL_SOURCE_EXPOSURE.search(text):
        sys.stderr.write(
            "[警告] %s疑似把商业相关第三方机构写成资料背书；请优先使用官方来源，第三方仅作辅助核对时改为“相关机构公开汇总”。\n"
            % label
        )

# ---------------- Markdown 解析(轻量, 覆盖文章常用语法) ----------------

def render_inline(text):
    """行内元素: 转义后处理 加粗 / 斜体 / 行内代码 / 链接"""
    text = html.escape(text)
    text = text.replace("&lt;br&gt;", "<br>")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    return text


def render_image(alt, src):
    alt = html.escape(alt or "")
    src = html.escape(src or "")
    caption = '<figcaption>%s</figcaption>' % alt if alt else ""
    return '<figure><img src="%s" alt="%s" loading="lazy">%s</figure>' % (src, alt, caption)


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

        # 图片: 支持 http(s) 与相对路径，如 ![说明](assets/a.svg)
        m_img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if m_img:
            out.append(render_image(m_img.group(1).strip(), m_img.group(2).strip()))
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
.article figure{margin:24px 0;text-align:center;}
.article figure img{margin:0 auto 8px;}
.article figcaption{font-size:13px;line-height:1.6;color:#7a7f87;}
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

XHS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#f6f7f5">
<title>__TITLE__</title>
<style>
*{box-sizing:border-box;}
html{background:#eef1ed;}
body{margin:0;color:#212322;font:15px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
.toolbar{position:sticky;top:0;z-index:99;display:flex;gap:8px;align-items:center;min-height:48px;
  padding:8px max(14px,calc((100vw - 430px)/2));background:rgba(255,255,255,.94);
  border-bottom:1px solid rgba(30,40,34,.08);backdrop-filter:blur(10px);}
.toolbar .tip{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#59615b;font-size:13px;}
.toolbar button{border:1px solid rgba(30,40,34,.14);border-radius:999px;padding:7px 12px;background:#212322;color:#fff;
  font-size:13px;cursor:pointer;}
.toolbar button.ghost{background:#fff;color:#212322;}
.phone-shell{max-width:430px;margin:22px auto 46px;padding:0 14px;}
.note-card{min-height:720px;border-radius:28px;background:#fff;box-shadow:0 22px 60px rgba(28,34,30,.14);
  overflow:hidden;border:1px solid rgba(30,40,34,.08);}
.note-head{display:flex;align-items:center;gap:10px;padding:16px 18px;border-bottom:1px solid #f0f1ef;}
.avatar{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#dff7e8,#ffe9ef);}
.author{font-size:13px;font-weight:700;color:#252725;}
.meta{font-size:11px;color:#929891;}
.note-body{padding:18px 20px 22px;}
.note-body h1{margin:0 0 12px;font-size:23px;line-height:1.25;letter-spacing:0;font-weight:800;color:#1f2320;}
.note-body h2,.note-body h3{margin:20px 0 8px;font-size:16px;line-height:1.45;color:#1f2320;}
.note-body p{margin:0 0 12px;white-space:pre-wrap;}
.note-body ul,.note-body ol{margin:8px 0 14px;padding-left:1.25em;}
.note-body li{margin:5px 0;}
.note-body strong{font-weight:800;}
.note-body blockquote{margin:14px 0;padding:10px 12px;border-left:3px solid #83cfa3;background:#f6fbf7;border-radius:8px;color:#374039;}
.note-body code{padding:1px 5px;border-radius:5px;background:#f2f3f1;}
.note-actions{display:flex;gap:18px;padding:12px 20px 18px;border-top:1px solid #f0f1ef;color:#687069;font-size:13px;}
#plainText{display:none;}
@media (max-width:480px){
  .phone-shell{margin:12px auto 32px;padding:0 10px;}
  .note-card{border-radius:22px;min-height:calc(100vh - 78px);}
  .toolbar .tip{display:none;}
  .toolbar button{flex:1;min-height:36px;}
}
@media print{.toolbar{display:none}.phone-shell{max-width:100%;margin:0}.note-card{box-shadow:none;border:0}}
</style>
</head>
<body>
<div class="toolbar">
  <span class="tip">小红书笔记预览：复制为纯文本，可直接发布</span>
  <button type="button" title="复制小红书纯文本笔记" onclick="copyPlain()">&#128203; 复制笔记</button>
  <button class="ghost" type="button" title="下载当前 HTML" onclick="downloadHtml()">&#11015; 下载预览</button>
</div>
<main class="phone-shell">
  <article class="note-card">
    <header class="note-head">
      <div class="avatar" aria-hidden="true"></div>
      <div>
        <div class="author">Mr.Li Writer</div>
        <div class="meta">小红书笔记预览</div>
      </div>
    </header>
    <section class="note-body" id="article">
      __BODY__
    </section>
    <footer class="note-actions">
      <span>♡ 收藏</span><span>💬 评论</span><span>↗ 分享</span>
    </footer>
  </article>
</main>
<script type="text/plain" id="plainText">__PLAIN_TEXT__</script>
<script>
function copyPlain(){
  var text=document.getElementById('plainText').textContent;
  try{
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(function(){toast('已复制纯文本笔记');},function(){fallbackCopy(text);});
    }else{fallbackCopy(text);}
  }catch(e){fallbackCopy(text);}
}
function fallbackCopy(text){
  var ta=document.createElement('textarea');
  ta.value=text;ta.style.position='fixed';ta.style.left='-9999px';
  document.body.appendChild(ta);ta.focus();ta.select();
  var ok=document.execCommand('copy');ta.remove();
  toast(ok?'已复制纯文本笔记':'复制失败,请手动全选复制');
}
function downloadHtml(){
  try{
    var blob=new Blob(['<!DOCTYPE html>'+document.documentElement.outerHTML],{type:'text/html;charset=utf-8'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download=(document.title||'xhs-note')+'.html';a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);},1000);
  }catch(e){toast('下载失败,请使用浏览器另存为');}
}
function toast(msg){
  var t=document.createElement('div');
  t.textContent=msg;
  t.style.cssText='position:fixed;left:50%;bottom:36px;transform:translateX(-50%);'+
    'background:rgba(0,0,0,.82);color:#fff;padding:9px 18px;border-radius:999px;font-size:14px;z-index:999;';
  document.body.appendChild(t);setTimeout(function(){t.remove();},2000);
}
</script>
</body>
</html>
"""

BASE_CSS_FALLBACK = """
body{margin:0;background:#f6f7f8;color:#232323;font:16px/1.9 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}
.article{max-width:720px;margin:0 auto;padding:34px 22px 68px;background:#fff;}
.article h1{font-size:30px;line-height:1.35;margin:0 0 26px;}
.article h2{font-size:22px;margin:36px 0 14px;padding-bottom:8px;border-bottom:1px solid #e5e7eb;}
.article h3{font-size:18px;margin:26px 0 12px;}
.article p{margin:0 0 18px;}
.article blockquote{margin:22px 0;padding:12px 16px;border-left:4px solid #9ca3af;background:#f8fafc;color:#4b5563;}
.article a{color:#2563eb;text-decoration:none;border-bottom:1px solid #bfdbfe;}
"""


def list_themes():
    print("可用公众号排版主题:")
    print("  %-18s %s" % ("auto", "按题材自动匹配；最终排版需加 --auto-theme-ok 表示用户已授权"))
    print("  %-18s %s" % ("random", "从 6 套公众号主题中随机选择；最终排版需加 --auto-theme-ok 表示用户已授权"))
    for name, desc in GZH_THEMES.items():
        print("  %-18s %s" % (name, desc))


def list_delivery_styles():
    print("可用交付样式:")
    print("  %-15s %s" % ("auto", "按发布平台和内容目标自动选择(默认)"))
    for name, desc in DELIVERY_STYLES.items():
        print("  %-15s %s" % (name, desc))


def resolve_delivery_style(delivery_style, platform="", mode="", content_goal=""):
    if delivery_style != "auto":
        return delivery_style, "manual"
    platform_text = platform.lower()
    mode_text = mode.lower()
    goal_text = content_goal.lower()
    if "公众号" in platform or "微信" in platform:
        return "gzh-article", "auto:platform"
    if "小红书" in platform or "xiaohongshu" in platform_text or "xhs" in platform_text or mode_text == "xiaohongshu-note":
        return "xhs-note", "auto:platform"
    if "知乎" in platform:
        return "zhihu-answer", "auto:platform"
    if "官网" in platform or "网页" in platform or "seo" in goal_text or "geo" in goal_text:
        return "web-article", "auto:platform/content-goal"
    if "博客" in platform:
        return "blog-post", "auto:platform"
    return "article-html", "auto:platform"


def run_gzh_builder(args):
    builder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_gzh_html.py")
    cmd = [sys.executable, builder, args.md, "--theme", args.theme]
    if args.auto_theme_ok:
        cmd.append("--auto-theme-ok")
    if args.theme_confirmed:
        cmd.append("--theme-confirmed")
    if args.output:
        cmd.extend(["-o", args.output])
    if args.title:
        cmd.extend(["--title", args.title])
    return subprocess.call(cmd)


def escape_script_text(text):
    return text.replace("</script", "<\\/script")


def clean_page_from_preview(page):
    """Remove preview controls while retaining the platform-styled article."""
    page = re.sub(r'<div class="reading-progress".*?</div>\s*', "", page, flags=re.S)
    page = re.sub(r'<div class="toolbar">.*?</div>\s*', "", page, count=1, flags=re.S)
    page = re.sub(r'<script(?:\s+type="text/plain")?.*?</script>\s*', "", page, flags=re.S)
    return page


def preview_path_for(output_path):
    stem, suffix = os.path.splitext(output_path)
    return stem + "-preview" + (suffix or ".html")


def main():
    parser = argparse.ArgumentParser(description="Markdown -> 平台 HTML / 复制预览 HTML")
    parser.add_argument("md", nargs="?", help="Markdown 正文文件路径")
    parser.add_argument("-o", "--output", help="输出 HTML 路径(默认: 与 md 同目录同名 .html)")
    parser.add_argument("-t", "--theme", default=DEFAULT_THEME, help="公众号主题名、auto 或 random(默认 %s)" % DEFAULT_THEME)
    parser.add_argument(
        "--auto-theme-ok",
        action="store_true",
        help="确认用户已授权系统自动/随机选择公众号主题；未授权时请用 -t 指定具体主题",
    )
    parser.add_argument(
        "--theme-confirmed",
        action="store_true",
        help="确认用户已选择当前公众号主题；具体主题最终排版必须带此参数",
    )
    parser.add_argument("--title", default="", help="文章标题(默认取 md 文件名)")
    parser.add_argument("--mode", default="", help="内容模式: research-explainer/practical-guide/opinion-analysis/story-profile/platform-native/xiaohongshu-note")
    parser.add_argument("--platform", default="", help="发布平台: 公众号/知乎/小红书/官网/网页/个人博客")
    parser.add_argument("--content-goal", default="", help="内容目标: 普通传播/GEO/SEO/转化销售/专业报告")
    parser.add_argument(
        "--delivery-style",
        default="auto",
        help="交付样式: auto/gzh-article/article-html/zhihu-answer/xhs-note/web-article/blog-post",
    )
    parser.add_argument("--list-themes", action="store_true", help="列出可用主题")
    parser.add_argument("--list-delivery-styles", action="store_true", help="列出可用交付样式")
    parser.add_argument(
        "--emit-pair",
        action="store_true",
        help="同时生成干净排版 HTML 和带复制功能的 -preview.html；用于非公众号排版交付",
    )
    args = parser.parse_args()

    if args.list_themes:
        list_themes()
        return
    if args.list_delivery_styles:
        list_delivery_styles()
        return

    if not args.md:
        parser.error("缺少 Markdown 文件路径(或用 --list-themes / --list-delivery-styles 查看选项)")

    md_path = os.path.abspath(args.md)
    if not os.path.isfile(md_path):
        sys.stderr.write("[错误] 文件不存在: %s\n" % md_path)
        sys.exit(1)

    if args.theme not in GZH_THEMES and args.theme not in SPECIAL_THEMES:
        sys.stderr.write("[错误] 未知公众号主题 '%s'\n" % args.theme)
        list_themes()
        sys.exit(1)

    if args.delivery_style not in DELIVERY_STYLES and args.delivery_style not in SPECIAL_DELIVERY_STYLES:
        sys.stderr.write("[错误] 未知交付样式 '%s'\n" % args.delivery_style)
        list_delivery_styles()
        sys.exit(1)

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    warn_process_leaks(md_text)
    warn_commercial_source_exposure(md_text)

    title = args.title or os.path.splitext(os.path.basename(md_path))[0]
    delivery_style, delivery_reason = resolve_delivery_style(
        args.delivery_style,
        platform=args.platform,
        mode=args.mode,
        content_goal=args.content_goal,
    )

    if delivery_style == "gzh-article":
        if args.theme in SPECIAL_THEMES and not args.auto_theme_ok:
            sys.stderr.write(
                "[错误] 公众号最终排版不能静默使用主题 %s；请先确认公众号主题，使用 -t <主题名>，或在用户明确授权自动匹配后添加 --auto-theme-ok。\n"
                % args.theme
            )
            sys.exit(2)
        if args.theme in GZH_THEMES and not args.theme_confirmed:
            sys.stderr.write(
                "[错误] 公众号最终排版不能由智能体静默指定主题 %s；请先让用户确认主题，再添加 --theme-confirmed。\n"
                % args.theme
            )
            sys.exit(2)
        return_code = run_gzh_builder(args)
        sys.exit(return_code)

    body = md_to_html(md_text)

    out_path = args.output or os.path.splitext(md_path)[0] + ".html"
    out_path = os.path.abspath(out_path)

    if delivery_style == "xhs-note":
        page = (XHS_HTML_TEMPLATE
                .replace("__TITLE__", html.escape(title))
                .replace("__BODY__", body)
                .replace("__PLAIN_TEXT__", escape_script_text(md_text)))
    else:
        page = (HTML_TEMPLATE
                .replace("__TITLE__", html.escape(title))
                .replace("__CSS__", BASE_CSS_FALLBACK)
                .replace("__BODY__", body))

    if args.emit_pair:
        preview_path = preview_path_for(out_path)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(clean_page_from_preview(page))
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(page)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)

    print("[完成] 交付样式=%s (%s)" % (delivery_style, delivery_reason))
    if args.theme != "auto":
        print("[提示] 非公众号平台未使用公众号主题=%s" % args.theme)
    print("[输出] %s" % out_path)
    if args.emit_pair:
        print("[复制预览] %s" % preview_path)


if __name__ == "__main__":
    main()
