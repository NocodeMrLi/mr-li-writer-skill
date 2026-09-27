#!/usr/bin/env python3
"""Validate platform-native source, title strategy, and optional layout artifacts."""

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
WECHAT_PLATFORMS = {"公众号", "wechat", "gzh", "微信", "微信公众号"}
WECHAT_THEME_ALIASES = {
    "摸鱼绿": "moyu-green",
    "红白色系": "red-white",
    "石墨极简": "graphite-minimal",
    "石墨极简风": "graphite-minimal",
    "留白禅意风": "zen-whitespace",
    "留白禅意风（Zen）": "zen-whitespace",
    "摸鱼票据风": "moyu-ticket",
    "橄榄手记": "olive-journal",
}


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


def normalized_html(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def html_digest(text):
    return hashlib.sha256(normalized_html(text).encode("utf-8")).hexdigest()


def normalize_wechat_theme(value):
    value = str(value or "").strip()
    if value.lower() in {"auto", "random"} or value == "自动匹配":
        return ""
    return WECHAT_THEME_ALIASES.get(value, value)


def meta_content(source, name):
    match = re.search(
        r'<meta\s+name=["\']%s["\']\s+content=["\']([^"\']*)["\']\s*/?>'
        % re.escape(name),
        source,
        re.I,
    )
    return match.group(1).strip() if match else ""


def validate_wechat_layout(clean_path, preview_path, expected_theme=""):
    errors = []
    clean = clean_path.read_text(encoding="utf-8", errors="replace")
    preview = preview_path.read_text(encoding="utf-8", errors="replace")

    renderer = re.search(r'data-mr-li-writer-renderer=["\']component-library-v1["\']', clean, re.I)
    theme_match = re.search(r'data-mr-li-writer-theme=["\']([^"\']+)["\']', clean, re.I)
    actual_theme = theme_match.group(1).strip() if theme_match else ""
    if not renderer or not actual_theme:
        errors.append("公众号正文 HTML 未由完整组件库渲染器生成；禁止只按主题颜色手写简化页面")
    expected_theme = normalize_wechat_theme(expected_theme)
    if expected_theme and actual_theme and actual_theme != expected_theme:
        errors.append("公众号正文 HTML 主题与任务状态不一致：应为 %s，实际为 %s" % (expected_theme, actual_theme))

    if meta_content(preview, "mr-li-writer-template") != "gzh-preview-v2":
        errors.append("复制预览 HTML 不是受支持的公众号正式预览模板")
    preview_theme = meta_content(preview, "mr-li-writer-theme")
    if actual_theme and preview_theme != actual_theme:
        errors.append("复制预览 HTML 的主题标识与公众号正文 HTML 不一致")

    rich_clipboard = all(
        marker in preview
        for marker in ("ClipboardItem", "'text/html'", "'text/plain'", "navigator.clipboard.write([item])")
    )
    if not rich_clipboard or "navigator.clipboard.writeText" in preview:
        errors.append("公众号复制预览必须使用 text/html + text/plain 富文本剪贴板，禁止 writeText 复制 HTML 源码")

    article_match = re.search(
        r'<article\b[^>]*id=["\']gzh-content["\'][^>]*>(.*?)</article>',
        preview,
        re.I | re.S,
    )
    declared_digest = meta_content(preview, "mr-li-writer-content-sha256")
    clean_digest = html_digest(clean)
    embedded_digest = html_digest(article_match.group(1)) if article_match else ""
    if not re.fullmatch(r"[a-f0-9]{64}", declared_digest):
        errors.append("复制预览 HTML 缺少有效的正文一致性摘要")
    elif declared_digest != clean_digest or embedded_digest != clean_digest:
        errors.append("复制预览 HTML 内正文与公众号正文 HTML 不一致；必须由同一份已校验正文生成")
    return errors


def validate_bundle(directory, platform, layout=False, task_state=None):
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
    if is_wechat(platform):
        clean = roles.get("公众号正文 HTML")
        expected_theme = state_value(task_state or {}, "delivery_style")
        if clean and preview and clean.stat().st_size and preview.stat().st_size:
            errors.extend(validate_wechat_layout(clean, preview, expected_theme))

    return roles, needs_layout, errors


def validate_wechat_bundle(directory):
    """Backward-compatible API for existing callers."""
    roles, _, errors = validate_bundle(directory, "公众号", layout=True)
    return roles, errors


def attachment_order(roles):
    """Return validated artifacts in the order users should see as file cards."""
    priority = (
        "复制预览 HTML",
        "公众号正文 HTML",
        "平台排版 HTML",
        "平台原生正文",
        "标题策略 Markdown",
    )
    return [(role, roles[role]) for role in priority if roles.get(role)]


def require_task_state(task_state, platform):
    if not task_state:
        print("[阻断] 交付校验前必须传入 --task-state，并通过 scripts/validate_task_intake.py 确认必问项。")
        return 2
    checker = SCRIPT_DIR / "validate_task_intake.py"
    return subprocess.call([sys.executable, str(checker), task_state, "--phase", "delivery", "--platform", platform])


def state_value(state, key):
    value = state.get(key, "")
    if isinstance(value, dict):
        return str(value.get("value", "")).strip()
    return str(value).strip()


def load_task_state(task_state):
    try:
        return json.loads(pathlib.Path(task_state).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def task_requires_sources(state):
    direct = state.get("require_sources", False)
    if isinstance(direct, dict):
        direct = direct.get("value", False)
    if direct is True or str(direct).strip().lower() in {"1", "true", "yes", "是", "需要"}:
        return True

    density = state_value(state, "evidence_density").lower()
    if density in {"high", "medium", "高", "中"}:
        return True
    mode = state_value(state, "mode").lower()
    genre = state_value(state, "genre").lower()
    goal = state_value(state, "content_goal")
    return (
        mode in {"research-explainer", "policy-analysis"}
        or genre in {"policy-industry", "medical-health", "legal-finance"}
        or goal == "专业报告"
    )


def validate_content_quality(source, platform, task_state):
    state = load_task_state(task_state)
    command = [
        sys.executable,
        str(SCRIPT_DIR / "lint_article.py"),
        str(source),
        "--platform",
        platform,
        "--strict-delivery",
        "--task-state",
        task_state,
    ]
    for state_key, option in (
        ("mode", "--mode"),
        ("genre", "--genre"),
        ("evidence_density", "--evidence-density"),
    ):
        value = state_value(state, state_key)
        if value:
            command.extend([option, value])
    if task_requires_sources(state):
        command.append("--require-sources")

    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
    return result.returncode


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

    state = load_task_state(args.task_state)
    roles, needs_layout, errors = validate_bundle(
        directory,
        args.platform,
        layout=args.layout,
        task_state=state,
    )
    mode = "排版交付" if needs_layout else "原生内容交付"
    print("%s交付校验（%s）: %s" % (args.platform, mode, directory))
    for role, path in roles.items():
        print("- %s: %s" % (role, path.name if path else "缺失"))
    for error in errors:
        print("[错误] %s" % error)
    if errors:
        return 1

    source = roles.get("平台原生正文")
    quality_rc = validate_content_quality(source, args.platform, args.task_state)
    if quality_rc != 0:
        print("[错误] 正文质量门禁未通过；请修复阻断项后重新校验。")
        return 1

    if needs_layout:
        print("[通过] 标题、平台原生正文、排版 HTML 与复制预览均真实存在且非空")
    else:
        print("[通过] 标题策略与平台原生正文真实存在且非空；本次不机械要求 HTML")
    print("[待执行] 必须调用宿主原生附件/文件卡片能力附加以下文件；预览优先，不能用工作区路径代替：")
    for index, (role, path) in enumerate(attachment_order(roles), start=1):
        print("ATTACHMENT_REQUIRED\t%d\t%s\t%s" % (index, role, path.resolve()))
    print("[注意] 文件完整性校验通过不等于最终交付完成；只有附件工具返回成功后才能结束任务。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
