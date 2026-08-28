#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Mr.Li Writer task intake confirmations before formal actions."""

import argparse
import json
import pathlib
import re
import sys


REQUIRED_FIELDS = (
    ("platform", "发布平台"),
    ("content_goal", "内容目标"),
    ("writing_direction", "创作方向"),
    ("delivery_style", "平台交付样式"),
)

CONDITIONAL_FIELDS = (
    ("reader_scene", "目标读者/阅读场景"),
    ("stance_boundary", "立场边界"),
    ("time_cutoff", "时效口径"),
    ("source_boundary", "来源边界"),
    ("delivery_format", "交付格式"),
    ("depth", "篇幅深度"),
)

TRUSTED_SOURCES = {"user", "user_confirmed", "auto_authorized"}
AUTO_AUTH_SOURCES = {"auto_authorized"}
RESUME_RE = re.compile(r"(继续完成任务|继续|接着做|恢复任务|按刚才的来|continue|resume)", re.I)
AUTO_RE = re.compile(r"(自动匹配|不用问|不要询问|直接处理|直接排|你看着办)")
MEMORY_AUTH_RE = re.compile(
    r"(长期偏好|长期记忆|历史偏好|历史默认|上次|之前偏好|standing instruction|memory|other skill|其他\s*skill|A\s*技能|旧技能)",
    re.I,
)

STYLE_OPTIONS = {
    "公众号": "摸鱼绿、红白色系、石墨极简风、留白禅意风、摸鱼票据风、橄榄手记、自动匹配",
    "知乎": "回答、专栏、回答 + HTML 预览、专栏 + HTML 预览、自动匹配",
    "小红书": "清爽纯文本笔记、手机卡片预览、偏种草、偏避坑、偏收藏清单、自动匹配",
    "官网/网页": "普通网页文章、SEO-GEO 结构化样式、转化落地页、专业报告页、CMS/模板适配、自动匹配",
    "个人博客": "Markdown、CMS 富文本、静态 HTML、作者随笔、技术长文、观点札记、自动匹配",
    "未知平台": "纯文本、Markdown、富文本、HTML、带复制预览 HTML、自动匹配",
}

STYLE_ALIASES = {
    "公众号": {
        "moyu-green",
        "摸鱼绿",
        "red-white",
        "红白色系",
        "graphite-minimal",
        "石墨极简风",
        "zen-whitespace",
        "留白禅意风",
        "moyu-ticket",
        "摸鱼票据风",
        "olive-journal",
        "橄榄手记",
        "auto",
        "自动匹配",
    },
    "知乎": {"回答", "专栏", "回答 + HTML 预览", "专栏 + HTML 预览", "auto", "自动匹配"},
    "小红书": {"清爽纯文本笔记", "手机卡片预览", "偏种草", "偏避坑", "偏收藏清单", "xhs-note", "auto", "自动匹配"},
    "官网/网页": {
        "普通网页文章",
        "SEO-GEO 结构化样式",
        "转化落地页",
        "专业报告页",
        "CMS/模板适配",
        "web-article",
        "auto",
        "自动匹配",
    },
    "个人博客": {"Markdown", "CMS 富文本", "静态 HTML", "作者随笔", "技术长文", "观点札记", "blog-post", "auto", "自动匹配"},
    "未知平台": {"纯文本", "Markdown", "富文本", "HTML", "带复制预览 HTML", "auto", "自动匹配"},
}

STYLE_CANONICAL = {
    "moyu-green": "moyu-green",
    "摸鱼绿": "moyu-green",
    "red-white": "red-white",
    "红白色系": "red-white",
    "graphite-minimal": "graphite-minimal",
    "石墨极简风": "graphite-minimal",
    "zen-whitespace": "zen-whitespace",
    "留白禅意风": "zen-whitespace",
    "moyu-ticket": "moyu-ticket",
    "摸鱼票据风": "moyu-ticket",
    "olive-journal": "olive-journal",
    "橄榄手记": "olive-journal",
    "回答": "zhihu-answer",
    "zhihu-answer": "zhihu-answer",
    "专栏": "zhihu-column",
    "回答 + HTML 预览": "zhihu-answer-html",
    "专栏 + HTML 预览": "zhihu-column-html",
    "清爽纯文本笔记": "xhs-plain",
    "手机卡片预览": "xhs-card",
    "偏种草": "xhs-seeding",
    "偏避坑": "xhs-avoid-pitfall",
    "偏收藏清单": "xhs-checklist",
    "xhs-note": "xhs-card",
    "普通网页文章": "web-article",
    "web-article": "web-article",
    "SEO-GEO 结构化样式": "web-seo-geo",
    "转化落地页": "web-conversion",
    "专业报告页": "web-report",
    "CMS/模板适配": "web-cms",
    "Markdown": "blog-markdown",
    "CMS 富文本": "blog-cms",
    "静态 HTML": "blog-static-html",
    "作者随笔": "blog-essay",
    "技术长文": "blog-tech",
    "观点札记": "blog-opinion",
    "blog-post": "blog-post",
    "auto": "auto",
    "自动匹配": "auto",
}


def load_state(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError("任务状态文件不存在: %s" % path)
    except json.JSONDecodeError as exc:
        raise ValueError("任务状态文件不是合法 JSON: %s" % exc)
    if not isinstance(data, dict):
        raise ValueError("任务状态必须是 JSON object")
    return data


def field_record(state, key):
    value = state.get(key)
    if isinstance(value, dict):
        return value
    if value:
        return {"value": value, "confirmed": False, "source": "legacy"}
    return {}


def source_is_trusted(record):
    return str(record.get("source", "")).strip().lower() in TRUSTED_SOURCES


def has_user_quote(record):
    source = str(record.get("source", "")).strip().lower()
    if source in AUTO_AUTH_SOURCES:
        return bool(str(record.get("user_quote") or record.get("authorization_quote") or "").strip())
    return bool(str(record.get("user_quote") or "").strip())


def quote_text(record):
    return str(record.get("user_quote") or record.get("authorization_quote") or "").strip()


def missing_reason(record):
    if not str(record.get("value", "")).strip():
        return "缺少取值"
    if record.get("confirmed") is not True:
        return "未标记 confirmed:true"
    if not source_is_trusted(record):
        return "不得用模型推断、历史默认、平台默认、推荐项或 memory 代替用户确认"
    if not has_user_quote(record):
        return "缺少用户原话或自动匹配授权原话"
    quote = quote_text(record)
    if MEMORY_AUTH_RE.search(quote):
        return "长期记忆、历史偏好或其他 skill 的习惯不能代替当前任务用户确认"
    if str(record.get("source", "")).strip().lower() in AUTO_AUTH_SOURCES and not AUTO_RE.search(quote):
        return "自动匹配授权必须来自当前任务中的明确原话"
    return ""


def platform_key(value):
    value = str(value or "").strip()
    lower = value.lower()
    if value in STYLE_OPTIONS:
        return value
    if lower in {"wechat", "gzh", "微信", "微信公众号"} or "公众号" in value:
        return "公众号"
    if "知乎" in value or lower == "zhihu":
        return "知乎"
    if "小红书" in value or lower in {"xhs", "xiaohongshu"}:
        return "小红书"
    if "官网" in value or "网页" in value or lower in {"web", "website"}:
        return "官网/网页"
    if "博客" in value or lower == "blog":
        return "个人博客"
    return "未知平台"


def state_from_prompt(prompt):
    text = prompt or ""
    memory_based = bool(MEMORY_AUTH_RE.search(text))
    source = "auto_authorized" if AUTO_RE.search(text) and not memory_based else "prompt_detected"
    confirmed = source == "auto_authorized"
    quote = "自动匹配" if confirmed else ""
    state = {}
    platform = ""
    for candidate in ("公众号", "小红书", "知乎", "官网/网页", "个人博客"):
        if candidate in text or (candidate == "官网/网页" and ("官网" in text or "网页" in text)) or (candidate == "个人博客" and "博客" in text):
            platform = candidate
            break
    if platform:
        state["platform"] = {
            "value": platform,
            "confirmed": confirmed,
            "source": source,
            "user_quote": quote,
        }
    for key, label in REQUIRED_FIELDS:
        state.setdefault(
            key,
            {
                "value": "",
                "confirmed": False,
                "source": "missing",
                "user_quote": "",
            },
        )
    if confirmed:
        defaults = {
            "content_goal": "auto",
            "writing_direction": "auto",
            "delivery_style": "auto",
        }
        for key, value in defaults.items():
            state[key] = {
                "value": value,
                "confirmed": True,
                "source": "auto_authorized",
                "user_quote": quote,
            }
        if not platform:
            state["platform"] = {
                "value": "auto",
                "confirmed": True,
                "source": "auto_authorized",
                "user_quote": quote,
            }
    return state


def triggered_conditionals(state):
    triggered = []
    container = state.get("conditional_fields")
    if isinstance(container, dict):
        for key, label in CONDITIONAL_FIELDS:
            record = container.get(key)
            if isinstance(record, dict) and record.get("triggered"):
                triggered.append((key, label, record))
    for key, label in CONDITIONAL_FIELDS:
        record = state.get(key)
        if isinstance(record, dict) and record.get("triggered"):
            triggered.append((key, label, record))
    return triggered


def canonical_style(value):
    return STYLE_CANONICAL.get(str(value or "").strip(), str(value or "").strip())


def validate(state, phase="draft", platform=None, last_user="", expected_style=""):
    errors = []
    platform_record = field_record(state, "platform")
    state_platform = str(platform_record.get("value", "")).strip()
    if platform and state_platform and platform_key(platform) != platform_key(state_platform):
        errors.append(("发布平台", "命令平台与任务状态不一致: %s != %s" % (platform, state_platform)))

    for key, label in REQUIRED_FIELDS:
        reason = missing_reason(field_record(state, key))
        if reason:
            errors.append((label, reason))

    resolved_platform = platform_key(state_platform or platform)
    delivery_style = str(field_record(state, "delivery_style").get("value", "")).strip()
    if delivery_style and not any(label == "平台交付样式" for label, _ in errors):
        allowed = STYLE_ALIASES.get(resolved_platform, STYLE_ALIASES["未知平台"])
        if delivery_style not in allowed:
            errors.append(
                (
                    "平台交付样式",
                    "当前样式不属于%s可选项；不得把公众号主题或其他平台样式跨平台套用" % resolved_platform,
                )
            )
        elif expected_style and canonical_style(delivery_style) != "auto" and canonical_style(expected_style) != "auto":
            if canonical_style(delivery_style) != canonical_style(expected_style):
                errors.append(
                    (
                        "平台交付样式",
                        "命令交付样式与任务状态不一致: %s != %s" % (expected_style, delivery_style),
                    )
                )

    for _key, label, record in triggered_conditionals(state):
        reason = missing_reason(record)
        if reason:
            errors.append((label, "条件触发后必须确认: %s" % reason))

    resume_without_confirmation = phase == "resume" or bool(last_user and RESUME_RE.search(last_user))
    return errors, resume_without_confirmation, resolved_platform


def print_report(errors, resume_without_confirmation, platform):
    if not errors:
        print("[通过] 必问项与已触发条件项均有用户确认或明确自动匹配授权")
        return

    print("[阻断] 当前不能继续写作、生成任务列表、创建文件、排版或交付。")
    if resume_without_confirmation:
        print("前面任务可能被中断/恢复，不能把“继续完成任务”视为确认。")
    print("缺少或不可信的必要确认项：")
    for label, reason in errors:
        print("- %s：%s" % (label, reason))
    print("")
    print("请先向用户合并确认缺失项；如果用户要省略询问，必须明确回复“自动匹配 / 不用问 / 直接处理 / 直接排”。")
    print("当前平台可选交付样式：%s" % STYLE_OPTIONS.get(platform, STYLE_OPTIONS["未知平台"]))


def print_new_task_hint():
    print("新任务尚未形成任务状态，必须先完成最低必要询问，再抓取、检索、读取链接、生成任务列表、写正文或排版。")


def main():
    parser = argparse.ArgumentParser(description="Mr.Li Writer 任务询问与恢复状态硬门禁")
    parser.add_argument("state", nargs="?", help="任务状态 JSON 文件")
    parser.add_argument("--from-prompt", default="", help="从用户初始输入做新任务入口检查；不会把模型推断当确认")
    parser.add_argument(
        "--phase",
        default="draft",
        choices=("resume", "task-list", "draft", "layout", "delivery"),
        help="即将进入的阶段",
    )
    parser.add_argument("--platform", default="", help="命令正在处理的发布平台，用于和任务状态交叉校验")
    parser.add_argument("--expected-style", default="", help="命令即将使用的交付样式/公众号主题，用于和任务状态交叉校验")
    parser.add_argument("--last-user", default="", help="最近一条用户消息，用于识别继续/恢复任务场景")
    args = parser.parse_args()

    if args.from_prompt:
        state = state_from_prompt(args.from_prompt)
        from_prompt = True
    else:
        from_prompt = False
        if not args.state:
            print("[阻断] 缺少任务状态文件。")
            print("正式写作、排版和交付必须先生成并传入 --task-state。")
            return 2
        path = pathlib.Path(args.state).expanduser()
        try:
            state = load_state(path)
        except ValueError as exc:
            print("[阻断] %s" % exc)
            print("正式写作、排版和交付必须先生成并传入 --task-state。")
            return 2

    errors, resume_without_confirmation, platform = validate(
        state,
        phase=args.phase,
        platform=args.platform,
        last_user=args.last_user,
        expected_style=args.expected_style,
    )
    if from_prompt and errors:
        print_new_task_hint()
    print_report(errors, resume_without_confirmation, platform)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
