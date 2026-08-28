#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate WeChat Official Account HTML snippets.

Adapted from gzh-design-skill (AGPL-3.0).
"""

import argparse
import re
import sys
from html.parser import HTMLParser


FORBIDDEN = [
    (re.compile(r"<style[\s>]", re.I), "ERROR", "<style> 标签会被过滤，样式必须内联"),
    (re.compile(r"<script[\s>]", re.I), "ERROR", "<script> 标签会被过滤"),
    (re.compile(r"</?div[\s>]", re.I), "ERROR", "<div> 会被改写，请用 <section>"),
    (re.compile(r"<link[\s>]", re.I), "ERROR", "外部 <link>（CSS/字体）会被过滤"),
    (re.compile(r"position\s*:\s*(fixed|absolute|sticky)", re.I), "ERROR", "position fixed/absolute/sticky 不被支持"),
    (re.compile(r"float\s*:", re.I), "ERROR", "float 不被支持"),
    (re.compile(r"@media", re.I), "ERROR", "@media 媒体查询不被支持"),
    (re.compile(r"@keyframes", re.I), "ERROR", "@keyframes 动画不被支持"),
    (re.compile(r"@import", re.I), "ERROR", "@import 不被支持"),
    (re.compile(r"display\s*:\s*grid", re.I), "ERROR", "display:grid 不被支持，请用 flex"),
    (re.compile(r"var\s*\(\s*--", re.I), "ERROR", "CSS 变量 var(--x) 不被支持，请写死值"),
    (re.compile(r"url\s*\(\s*['\"]?https?://[^)]*\.(woff2?|ttf|otf|eot)", re.I), "ERROR", "外部字体不被支持"),
    (re.compile(r"overflow-x\s*:\s*auto", re.I), "ERROR", "横向滚动在公众号发布后不稳定，请改为容器内自适应换行"),
    (re.compile(r"(?:width|min-width|max-width)\s*:\s*\d+(?:\.\d+)?vw", re.I), "ERROR", "vw 宽度在公众号 PC/手机端不稳定，请使用百分比或 flex 自适应"),
]

RAW_MARKDOWN_TABLE = re.compile(
    r"\|[^\n<>]+\|\s*(?:<[^>]+>\s*)*\|\s*:?-{3,}:?\s*\|",
    re.I,
)

HEADING_CONTEXT_RE = re.compile(r"(?P<context>(?:(?!<h[23]\b).){0,1200})<h[23]\b[^>]*>", re.I | re.S)
LEAF_TEXT_RE = re.compile(r"<span\s+leaf=\"\">\s*([^<]+?)\s*</span>", re.I)

FORBIDDEN_FRONT_BADGE = re.compile(
    r"<(?:span|section)\b[^>]*style=\"[^\"]*(?:border-radius|padding|background)[^\"]*\"[^>]*>\s*"
    r"(?:<span leaf=\"\">)?\s*(中立|客观中立|模型生成|AI\s*生成|提示词|Prompt|公众号排版|深度文章|内部标签)\s*"
    r"(?:</span>)?",
    re.I,
)

CJK = re.compile(r"[一-鿿㐀-䶿]")
SKIP_TAGS = {"head", "title", "style", "script"}
HALF_PUNCT = re.compile(r"[一-鿿㐀-䶿][,;!?]")
ASCII_QUOTE = re.compile(r"[\"']")
CODE_STYLE = re.compile(r"monospace|white-space\s*:\s*pre|courier|consolas|sf mono", re.I)


class LeafChecker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.leaf_depth = 0
        self.code_depth = 0
        self.span_leaf_count = 0
        self.unwrapped = []
        self.half_punct = []
        self.forbidden_attrs = []

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        for attr_name, _attr_value in attrs:
            if attr_name in {"class", "id"}:
                self.forbidden_attrs.append((tag, attr_name))
        is_leaf = tag == "span" and "leaf" in ad
        is_code = bool(CODE_STYLE.search(ad.get("style", "") or ""))
        if is_leaf:
            self.span_leaf_count += 1
            self.leaf_depth += 1
        if is_code:
            self.code_depth += 1
        self.stack.append((tag, is_leaf, is_code))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, was_leaf, was_code in self.stack[i:]:
                    if was_leaf:
                        self.leaf_depth -= 1
                    if was_code:
                        self.code_depth -= 1
                del self.stack[i:]
                break

    def handle_data(self, data):
        text = data.strip()
        if not text or not CJK.search(text):
            return
        if any(t in SKIP_TAGS for t, _, _ in self.stack):
            return
        if self.leaf_depth == 0:
            parent = self.stack[-1][0] if self.stack else "(root)"
            snippet = text[:24] + ("…" if len(text) > 24 else "")
            self.unwrapped.append((snippet, parent))
        if self.code_depth == 0 and (HALF_PUNCT.search(text) or ASCII_QUOTE.search(text)):
            snippet = text[:24] + ("…" if len(text) > 24 else "")
            self.half_punct.append(snippet)


def chapter_numbers(html):
    numbers = []
    for match in HEADING_CONTEXT_RE.finditer(html):
        context = match.group("context")
        labels = [item.strip() for item in LEAF_TEXT_RE.findall(context)]
        if not labels:
            continue
        has_chapter_marker = any(re.search(r"^(CHAPTER|PART|THE\b)", label, re.I) for label in labels)
        nums = [label for label in labels if re.fullmatch(r"\d{2}", label)]
        if has_chapter_marker and nums:
            numbers.append(nums[-1])
    return numbers


def validate(html, name="<input>"):
    errors, warnings = [], []
    for rx, level, msg in FORBIDDEN:
        hits = len(rx.findall(html))
        if hits:
            (errors if level == "ERROR" else warnings).append("%s（命中 %d 处）" % (msg, hits))
    if RAW_MARKDOWN_TABLE.search(html):
        errors.append("检测到未转换的 Markdown 表格；必须渲染为语义化 <table> 后再交付")
    if FORBIDDEN_FRONT_BADGE.search(html):
        errors.append("检测到不适合暴露给读者的前端标签词；请改为信息指南、判断参考、深度解读、避坑提醒等读者口径")

    checker = LeafChecker()
    try:
        checker.feed(html)
    except Exception as exc:
        warnings.append("HTML 解析中断: %s" % exc)

    attr_hits = [attr for _tag, attr in checker.forbidden_attrs]
    if "class" in attr_hits:
        errors.append("class 属性会被剥离，请用内联 style（命中 %d 处）" % attr_hits.count("class"))
    if "id" in attr_hits:
        errors.append("id 属性会被剥离（命中 %d 处）" % attr_hits.count("id"))

    numbers = chapter_numbers(html)
    if len(numbers) >= 2:
        expected = ["%02d" % index for index in range(1, len(numbers) + 1)]
        if numbers != expected:
            errors.append("章节编号不连续或重复；应为 %s，实际为 %s" % ("/".join(expected), "/".join(numbers)))

    has_cjk = bool(CJK.search(html))
    if has_cjk and checker.span_leaf_count == 0:
        errors.append("全文没有任何 <span leaf=\"\"> 包裹，粘贴到公众号后样式会大面积丢失")
    elif checker.unwrapped:
        sample = "；".join("「%s」(在 <%s> 内)" % (s, p) for s, p in checker.unwrapped[:5])
        warnings.append("%d 处中文文本未被 <span leaf> 包裹，样式可能丢失。例：%s" % (len(checker.unwrapped), sample))

    if checker.half_punct:
        sample = "；".join("「%s」" % s for s in checker.half_punct[:5])
        warnings.append("%d 处正文疑似半角标点/英文引号，应改中文全角。例：%s" % (len(checker.half_punct), sample))

    return errors, warnings, checker.span_leaf_count


def main():
    parser = argparse.ArgumentParser(description="公众号 HTML 合规校验")
    parser.add_argument("file", nargs="?", help="HTML 文件路径")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取")
    args = parser.parse_args()

    if args.stdin or not args.file:
        source = sys.stdin.read()
        name = "<stdin>"
    else:
        with open(args.file, encoding="utf-8", errors="replace") as f:
            source = f.read()
        name = args.file

    errors, warnings, leaf_n = validate(source, name)
    print("公众号 HTML 合规校验: %s" % name)
    print("span leaf 包裹: %d 处" % leaf_n)

    for error in errors:
        print("[错误] %s" % error)
    for warning in warnings:
        print("[警告] %s" % warning)

    if errors:
        return 1
    print("[通过] 无致命问题，可粘贴到公众号编辑器")
    return 0


if __name__ == "__main__":
    sys.exit(main())
