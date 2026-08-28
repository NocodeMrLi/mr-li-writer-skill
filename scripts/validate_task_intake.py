#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate Mr.Li Writer task intake confirmations before formal actions."""

import argparse
import importlib.util
import json
import pathlib
import re
import sys


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent


def load_research_scope_validator():
    module_path = SCRIPT_DIR / "validate_research_scope.py"
    if not module_path.is_file():
        raise RuntimeError("缺少资料搜集范围校验脚本: %s" % module_path)
    spec = importlib.util.spec_from_file_location("mr_li_validate_research_scope", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载资料搜集范围校验脚本: %s" % module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "validate_research_scope", None)
    if not callable(validator):
        raise RuntimeError("资料搜集范围校验脚本缺少 validate_research_scope")
    return validator


validate_research_scope = load_research_scope_validator()


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
RESUME_RE = re.compile(
    r"^\s*(?:请)?(?:继续(?:完成)?(?:未完成的)?任务|继续|接着做|恢复任务|按刚才的来|continue|resume|continue\s+(?:the\s+)?(?:unfinished\s+)?task|resume\s+(?:the\s+)?task)\s*[。.!！]*\s*$",
    re.I,
)
DIRECT_AUTO_RE = re.compile(r"(不用问|不要询问|直接处理)")
YOU_DECIDE_RE = re.compile(r"你看着办")
AUTO_MATCH_RE = re.compile(r"自动匹配")
LOCAL_SCOPE_RE = re.compile(r"(公众号)?主题|排版主题|样式|交付样式|标题|题目|主标题|封面标题|标签|目录|大纲|小标题|直接排")
GLOBAL_SCOPE_RE = re.compile(r"(全部|所有|本次|整体|整篇|全流程|平台|内容目标|创作方向|交付样式|都|全都)")
MEMORY_AUTH_RE = re.compile(
    r"(长期偏好|长期记忆|用户偏好|历史偏好|历史默认|上次|之前偏好|习惯推断|standing instruction|memory|craft mode|other skill|其他\s*skill|A\s*技能|旧技能|排版\s*(由\s*AI\s*)?自行决定)",
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

PLATFORM_OPTIONS_TEXT = "公众号 / 小红书 / 知乎 / 官网/网页 / 个人博客"
CONTENT_GOAL_OPTIONS_TEXT = "普通传播 / GEO 生成式搜索优化 / SEO 搜索引擎优化 / 转化销售 / 专业报告"
GENERIC_DELIVERY_OPTIONS_TEXT = {
    "公众号": "公众号排版主题：摸鱼绿 / 红白色系 / 石墨极简风 / 留白禅意风 / 摸鱼票据风 / 橄榄手记 / 自动匹配",
    "知乎": "回答 / 专栏 / 回答 + HTML 预览 / 专栏 + HTML 预览 / 自动匹配",
    "小红书": "清爽纯文本笔记 / 手机卡片预览 / 偏种草 / 偏避坑 / 偏收藏清单 / 自动匹配",
    "官网/网页": "普通网页文章 / SEO-GEO 结构化样式 / 转化落地页 / 专业报告页 / CMS/模板适配 / 自动匹配",
    "个人博客": "Markdown / CMS 富文本 / 静态 HTML / 作者随笔 / 技术长文 / 观点札记 / 自动匹配",
    "未知平台": "先确认发布平台，再确认该平台的交付样式；不要把公众号排版主题写进发布平台选项",
}

DELIVERY_STYLE_MARKERS = {
    "摸鱼绿",
    "红白色系",
    "石墨极简风",
    "留白禅意风",
    "摸鱼票据风",
    "橄榄手记",
    "moyu-green",
    "red-white",
    "graphite-minimal",
    "zen-whitespace",
    "moyu-ticket",
    "olive-journal",
    "回答",
    "专栏",
    "HTML 预览",
    "手机卡片预览",
    "清爽纯文本笔记",
    "偏种草",
    "偏避坑",
    "偏收藏清单",
    "普通网页文章",
    "SEO-GEO 结构化样式",
    "转化落地页",
    "专业报告页",
    "CMS/模板适配",
    "Markdown",
    "CMS 富文本",
    "静态 HTML",
}

TASK_CONTEXT_FIELDS = (
    "original_prompt",
    "topic",
    "title",
    "brief",
    "source_summary",
)


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


def has_task_level_auto_authorization(text):
    text = str(text or "")
    for match in DIRECT_AUTO_RE.finditer(text):
        window = text[max(0, match.start() - 8) : match.end() + 8]
        local_scope = LOCAL_SCOPE_RE.search(window)
        global_scope = GLOBAL_SCOPE_RE.search(window)
        if local_scope and not global_scope:
            continue
        return True
    for match in YOU_DECIDE_RE.finditer(text):
        window = text[max(0, match.start() - 8) : match.end() + 8]
        local_scope = LOCAL_SCOPE_RE.search(window)
        global_scope = GLOBAL_SCOPE_RE.search(window)
        if local_scope and not global_scope:
            continue
        return True
    if re.search(r"(全部|所有|全都|本次|整体|整篇|全流程).{0,12}自动匹配|自动匹配.{0,12}(全部|所有|全都|本次|整体|整篇|全流程)", text):
        return True
    for match in AUTO_MATCH_RE.finditer(text):
        window = text[max(0, match.start() - 8) : match.end() + 8]
        local_scope = LOCAL_SCOPE_RE.search(window)
        global_scope = GLOBAL_SCOPE_RE.search(window)
        if local_scope and not global_scope:
            continue
        return True
    return False


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
    if str(record.get("source", "")).strip().lower() in AUTO_AUTH_SOURCES and not has_task_level_auto_authorization(quote):
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
    source = "auto_authorized" if has_task_level_auto_authorization(text) and not memory_based else "prompt_detected"
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
            "confirmed": True,
            "source": "user",
            "user_quote": platform,
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


def platform_mixes_delivery_style(value):
    text = str(value or "").strip()
    if not text:
        return False
    if text in STYLE_OPTIONS or text in {"wechat", "gzh", "微信", "微信公众号", "zhihu", "xhs", "xiaohongshu", "web", "website", "blog"}:
        return False
    resolved = platform_key(text)
    if resolved == "未知平台":
        return False
    if re.search(r"[（(].+[）)]", text):
        return True
    return any(marker in text and marker != resolved for marker in DELIVERY_STYLE_MARKERS)


def validate(state, phase="draft", platform=None, last_user="", expected_style=""):
    errors = []
    platform_record = field_record(state, "platform")
    state_platform = str(platform_record.get("value", "")).strip()
    if platform and state_platform and platform_key(platform) != platform_key(state_platform):
        errors.append(("发布平台", "命令平台与任务状态不一致: %s != %s" % (platform, state_platform)))
    if platform_mixes_delivery_style(state_platform):
        errors.append(("发布平台", "发布平台不能混入排版主题或交付样式；请先只确认平台，再单独确认平台交付样式"))

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

    if phase in {"draft", "layout", "delivery"}:
        if not any(str(state.get(key, "")).strip() for key in TASK_CONTEXT_FIELDS):
            errors.append(
                (
                    "资料搜集",
                    "任务状态缺少 original_prompt/topic/brief，无法判断用户是否提供资料链接或文件；不能绕过资料搜集范围校验",
                )
            )
        for reason in validate_research_scope(state, phase=phase):
            errors.append(("资料搜集", reason))

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
    print("请先向用户合并确认缺失项；如果用户要省略询问，必须明确回复“自动匹配 / 不用问 / 直接处理 / 本次全部你看着办”。")
    print("当前平台可选交付样式：%s" % STYLE_OPTIONS.get(platform, STYLE_OPTIONS["未知平台"]))


def print_new_task_hint():
    print("新任务尚未形成任务状态，必须先完成最低必要询问，再抓取、检索、读取链接、生成任务列表、写正文或排版。")


def print_question_card(platform):
    delivery_options = GENERIC_DELIVERY_OPTIONS_TEXT.get(platform, GENERIC_DELIVERY_OPTIONS_TEXT["未知平台"])
    print("")
    print("请先确认以下信息（可直接按序号回复；有特殊要求写在“补充说明/自行输入”）：")
    print("1. 发布平台：%s" % PLATFORM_OPTIONS_TEXT)
    print("   注意：公众号排版主题不是发布平台，不能把平台和主题合并成一个选项。")
    print("2. 内容目标：%s" % CONTENT_GOAL_OPTIONS_TEXT)
    print("3. 创作方向：")
    print("   A. [最推荐] 读者最需要解决的现实问题/行动清单")
    print("   B. [次推荐] 关键变化的深度解读/判断标准")
    print("   C. 平台原生传播角度：更适合转发、收藏或评论讨论")
    print("   D. 转化销售角度：突出信任、异议处理和下一步行动")
    print("   E. 专业报告角度：强调来源、框架、边界和结论可靠性")
    print("4. 平台交付样式：%s" % delivery_options)
    print("补充说明/自行输入：可以写目标读者、阅读场景、立场边界、时效口径、来源边界、篇幅深度或你自己的表达偏好；也可以留空。")


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
    parser.add_argument("--emit-question-card", action="store_true", help="阻断时输出标准化问题卡，供智能体直接询问用户")
    args = parser.parse_args()

    if args.from_prompt and args.state:
        print("[阻断] 不能同时使用任务状态文件和 --from-prompt。")
        print("新任务入口只用 --from-prompt；正式写作、排版和交付阶段只用任务状态文件。")
        return 2

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
    if errors and (args.emit_question_card or from_prompt):
        print_question_card(platform)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
