#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static checks for a Markdown article before delivery."""

import argparse
import re
import sys
from pathlib import Path


AI_PHRASES = (
    "总而言之",
    "综上所述",
    "由此可见",
    "值得注意的是",
    "在当今时代",
    "希望对你有所帮助",
    "让我们一起",
    "未来可期",
    "拭目以待",
)


def parse_args():
    parser = argparse.ArgumentParser(description="检查文章结构、引用和常见 AI 腔")
    parser.add_argument("markdown", help="Markdown 文件")
    parser.add_argument("--mode", default="research-explainer", help="内容模式")
    parser.add_argument("--title", default="", help="可选标题，用于长度检查")
    parser.add_argument(
        "--require-sources",
        action="store_true",
        help="要求文章包含参考资料和至少一个 URL",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.markdown)
    if not path.is_file():
        print("[错误] 文件不存在: %s" % path, file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    warnings = []
    errors = []

    if not re.search(r"^#\s+\S+", text, re.M):
        warnings.append("缺少一级标题，HTML 可能只能使用命令行传入的标题。")

    if re.search(r"^(根据|数据显示|报告显示)", text.lstrip()):
        warnings.append("开头直接进入来源或数据，检查是否缺少场景、问题或读者入口。")

    for phrase in AI_PHRASES:
        count = text.count(phrase)
        if count:
            warnings.append("发现疑似模板化表达“%s” %d 次。" % (phrase, count))

    if re.search(r"我亲自|我亲身|我翻了[一二三四五六七八九十0-9]+份|我采访过", text):
        warnings.append("发现可能未经证实的第一人称经历或采访表达，请核对来源。")

    if args.title:
        title_length = len(args.title.strip())
        if title_length < 8:
            warnings.append("标题少于 8 个字符，检查主题识别度。")
        if title_length > 60:
            warnings.append("标题超过 60 个字符，检查搜索结果和移动端展示。")

    if args.require_sources:
        if not re.search(r"^##\s+(参考资料|References)\s*$", text, re.M):
            errors.append("缺少“## 参考资料”或“## References”章节。")
        if not re.search(r"https?://\S+", text):
            errors.append("参考资料章节中没有可验证的 URL。")

    if re.search(r"\b\d{2,3}%\b", text) and not re.search(r"https?://\S+", text):
        warnings.append("正文包含百分比数据，但未发现 URL；请补充来源或删除数字。")

    for warning in warnings:
        print("[警告] %s" % warning)
    for error in errors:
        print("[错误] %s" % error)

    if errors:
        return 1
    print("[通过] %s (%s)" % (path, args.mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
