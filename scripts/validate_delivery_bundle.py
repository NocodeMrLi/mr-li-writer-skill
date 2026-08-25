#!/usr/bin/env python3
"""Validate the mandatory delivery artifacts for a publishing platform."""

import argparse
import pathlib
import re
import sys


def first_match(files, predicate):
    return next((path for path in files if predicate(path)), None)


def validate_wechat_bundle(directory):
    files = sorted(path for path in directory.iterdir() if path.is_file())
    markdown = [path for path in files if path.suffix.lower() == ".md"]
    html = [path for path in files if path.suffix.lower() in {".html", ".htm"}]

    title_strategy = first_match(
        markdown,
        lambda path: "标题策略" in path.stem or "title-strategy" in path.stem.lower(),
    )
    article_source = first_match(
        markdown,
        lambda path: (
            path != title_strategy
            and (
                path.stem in {"正文", "文章原文"}
                or path.stem.lower() in {"article-source", "article", "source"}
                or "正文" in path.stem
            )
        ),
    )
    preview = first_match(
        html,
        lambda path: "preview" in path.stem.lower() or "预览" in path.stem,
    )
    clean_html = first_match(html, lambda path: path != preview)

    roles = {
        "标题策略 Markdown": title_strategy,
        "正文 Markdown": article_source,
        "公众号正文 HTML": clean_html,
        "复制预览 HTML": preview,
    }
    errors = []
    for role, path in roles.items():
        if path is None:
            errors.append("缺少%s" % role)
        elif path.stat().st_size == 0:
            errors.append("%s为空文件: %s" % (role, path.name))

    if title_strategy and title_strategy.stat().st_size:
        text = title_strategy.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"推荐标题|主标题", text):
            errors.append("标题策略 Markdown 缺少推荐标题/主标题")
        if not re.search(r"备选标题", text):
            errors.append("标题策略 Markdown 缺少备选标题")

    if preview and preview.stat().st_size:
        text = preview.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"复制到公众号|gzhCopy|clipboard", text, re.I):
            errors.append("复制预览 HTML 缺少可识别的复制功能")

    return roles, errors


def main():
    parser = argparse.ArgumentParser(description="发布交付物完整性校验")
    parser.add_argument("directory", help="交付目录")
    parser.add_argument("--platform", default="公众号", help="发布平台，默认公众号")
    args = parser.parse_args()

    directory = pathlib.Path(args.directory).expanduser().resolve()
    if not directory.is_dir():
        print("[错误] 交付目录不存在: %s" % directory)
        return 1

    if args.platform not in {"公众号", "wechat", "gzh"}:
        print("[跳过] 当前仅对公众号执行四件套校验: %s" % args.platform)
        return 0

    roles, errors = validate_wechat_bundle(directory)
    print("公众号交付四件套校验: %s" % directory)
    for role, path in roles.items():
        print("- %s: %s" % (role, path.name if path else "缺失"))
    for error in errors:
        print("[错误] %s" % error)
    if errors:
        return 1
    print("[通过] 四件套真实存在、非空，标题策略与复制预览具备必要内容")
    return 0


if __name__ == "__main__":
    sys.exit(main())
