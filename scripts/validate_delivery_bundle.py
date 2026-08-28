#!/usr/bin/env python3
"""Validate platform-native source, title strategy, and optional layout artifacts."""

import argparse
import pathlib
import re
import subprocess
import sys


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
WECHAT_PLATFORMS = {"公众号", "wechat", "gzh", "微信", "微信公众号"}


def first_match(files, predicate):
    return next((path for path in files if predicate(path)), None)


def is_wechat(platform):
    return platform.strip().lower() in WECHAT_PLATFORMS


def is_web_platform(platform):
    value = platform.strip().lower()
    return "官网" in value or "网页" in value or value in {"web", "website"}


def find_bundle_roles(directory, platform, layout=False):
    files = sorted(path for path in directory.iterdir() if path.is_file())
    markdown = [path for path in files if path.suffix.lower() == ".md"]
    source_files = [path for path in files if path.suffix.lower() in {".md", ".txt"}]
    html_files = [path for path in files if path.suffix.lower() in {".html", ".htm"}]

    title_strategy = first_match(
        markdown,
        lambda path: "标题策略" in path.stem or "title-strategy" in path.stem.lower(),
    )
    source_names = {
        "正文",
        "文章原文",
        "笔记",
        "article-source",
        "article",
        "source",
        "note-source",
        "note",
    }
    platform_source = first_match(
        source_files,
        lambda path: (
            path != title_strategy
            and (
                path.stem.lower() in source_names
                or "正文" in path.stem
                or "原文" in path.stem
                or "笔记" in path.stem
                or "source" in path.stem.lower()
            )
        ),
    )

    roles = {
        "标题策略 Markdown": title_strategy,
        "平台原生正文": platform_source,
    }
    needs_layout = layout or is_wechat(platform) or is_web_platform(platform)
    if needs_layout:
        preview = first_match(
            html_files,
            lambda path: "preview" in path.stem.lower() or "预览" in path.stem,
        )
        clean_html = first_match(html_files, lambda path: path != preview)
        clean_label = "公众号正文 HTML" if is_wechat(platform) else "平台排版 HTML"
        roles[clean_label] = clean_html
        roles["复制预览 HTML"] = preview

    return roles, needs_layout


def validate_bundle(directory, platform, layout=False):
    roles, needs_layout = find_bundle_roles(directory, platform, layout=layout)
    errors = []
    for role, path in roles.items():
        if path is None:
            errors.append("缺少%s" % role)
        elif path.stat().st_size == 0:
            errors.append("%s为空文件: %s" % (role, path.name))

    title_strategy = roles.get("标题策略 Markdown")
    if title_strategy and title_strategy.stat().st_size:
        text = title_strategy.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"推荐标题|主标题", text):
            errors.append("标题策略 Markdown 缺少推荐标题/主标题")
        if not re.search(r"备选标题", text):
            errors.append("标题策略 Markdown 缺少备选标题")

    preview = roles.get("复制预览 HTML")
    if preview and preview.stat().st_size:
        text = preview.read_text(encoding="utf-8", errors="replace")
        if not re.search(
            r"复制(?:到公众号|正文|笔记|内容)|gzhCopy|copyArticle|copyPlain|clipboard",
            text,
            re.I,
        ):
            errors.append("复制预览 HTML 缺少可识别的复制功能")

    return roles, needs_layout, errors


def validate_wechat_bundle(directory):
    """Backward-compatible API for existing callers."""
    roles, _, errors = validate_bundle(directory, "公众号", layout=True)
    return roles, errors


def require_task_state(task_state, platform):
    if not task_state:
        print("[阻断] 交付校验前必须传入 --task-state，并通过 scripts/validate_task_intake.py 确认必问项。")
        return 2
    checker = SCRIPT_DIR / "validate_task_intake.py"
    return subprocess.call([sys.executable, str(checker), task_state, "--phase", "delivery", "--platform", platform])


def main():
    parser = argparse.ArgumentParser(description="发布交付物完整性校验")
    parser.add_argument("directory", help="交付目录")
    parser.add_argument("--platform", default="公众号", help="发布平台，默认公众号")
    parser.add_argument(
        "--layout",
        action="store_true",
        help="本次包含排版交付；除公众号外，启用后要求排版 HTML 和复制预览 HTML",
    )
    parser.add_argument("--task-state", default="", help="任务状态 JSON；交付前必须通过必问项/恢复任务门禁")
    args = parser.parse_args()

    directory = pathlib.Path(args.directory).expanduser().resolve()
    if not directory.is_dir():
        print("[错误] 交付目录不存在: %s" % directory)
        return 1

    intake_rc = require_task_state(args.task_state, args.platform)
    if intake_rc != 0:
        return intake_rc

    roles, needs_layout, errors = validate_bundle(
        directory,
        args.platform,
        layout=args.layout,
    )
    mode = "排版交付" if needs_layout else "原生内容交付"
    print("%s交付校验（%s）: %s" % (args.platform, mode, directory))
    for role, path in roles.items():
        print("- %s: %s" % (role, path.name if path else "缺失"))
    for error in errors:
        print("[错误] %s" % error)
    if errors:
        return 1

    if needs_layout:
        print("[通过] 标题、平台原生正文、排版 HTML 与复制预览均真实存在且非空")
    else:
        print("[通过] 标题策略与平台原生正文真实存在且非空；本次不机械要求 HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
