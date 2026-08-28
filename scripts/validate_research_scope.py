#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate source expansion before drafting or delivering hard-info articles."""

import argparse
import json
import pathlib
import re
import sys


URL_RE = re.compile(r"https?://\S+")
HARD_INFO_RE = re.compile(
    r"(政策|法律|医疗|金融|价格|报名|考试|资格|证书|认证|补贴|费用|时间|截止|开通|更新|版本|榜单|通知|公告|监管|官方|202\d|20\d{2})"
)
TIME_SENSITIVE_RE = re.compile(
    r"(最新|今天|昨日|明天|今年|本月|下半年|上半年|截止|开通|报名|考试|价格|费用|政策|通知|公告|更新|版本|202\d|20\d{2})"
)
SOURCE_FILE_RE = re.compile(r"\.(docx|pdf|md|txt|png|jpe?g|webp)\b", re.I)
SEED_ONLY_RE = re.compile(r"(只基于|仅基于|不要外查|不再外查|不用外查|不要联网|不联网|只用我给|仅用我给|只看我给|仅看我给)")


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


def field_value(state, key):
    value = state.get(key)
    if isinstance(value, dict):
        return str(value.get("value", "")).strip()
    return str(value or "").strip()


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def has_truthy(scope, key):
    value = scope.get(key)
    if isinstance(value, dict):
        return bool(value.get("checked") or value.get("confirmed") or value.get("done") or value.get("value"))
    return bool(value)


def prompt_seed_sources(prompt):
    prompt = str(prompt or "")
    sources = URL_RE.findall(prompt)
    if SOURCE_FILE_RE.search(prompt):
        sources.append("file")
    return sources


def seed_sources(state, scope):
    sources = []
    for key in ("user_seed_sources", "seed_sources", "user_sources", "provided_sources", "reference_links"):
        sources.extend(as_list(scope.get(key)))
        sources.extend(as_list(state.get(key)))
    sources.extend(prompt_seed_sources(state.get("original_prompt", "")))
    seen = []
    for source in sources:
        if source not in seen:
            seen.append(source)
    return seen


def risk_requires_external_research(state, scope, seeds):
    if has_truthy(scope, "requires_external_research"):
        return True
    if not seeds:
        return False
    text = " ".join(
        [
            str(state.get("original_prompt", "")),
            str(scope.get("risk", "")),
            str(scope.get("topic_risk", "")),
            field_value(state, "content_goal"),
            field_value(state, "writing_direction"),
            field_value(state, "platform"),
            str(state.get("genre", "")),
            str(state.get("evidence_density", "")),
        ]
    )
    if re.search(r"(high|高|policy|industry|research|专业报告|SEO|GEO|转化|time_sensitive|hard_info)", text, re.I):
        return True
    return bool(HARD_INFO_RE.search(text))


def risk_requires_freshness(state, scope):
    text = " ".join(
        [
            str(state.get("original_prompt", "")),
            str(scope.get("risk", "")),
            str(scope.get("topic_risk", "")),
            field_value(state, "writing_direction"),
            str(state.get("genre", "")),
        ]
    )
    return bool(TIME_SENSITIVE_RE.search(text))


def external_sources(scope):
    sources = []
    for key in ("external_sources", "official_sources", "authority_sources", "independent_sources", "crosscheck_sources"):
        sources.extend(as_list(scope.get(key)))
    return sources


def explicit_seed_only_authorized(state, scope):
    candidates = [
        state.get("original_prompt", ""),
        state.get("last_user", ""),
        state.get("source_boundary", ""),
        scope.get("source_boundary", ""),
        scope.get("user_quote", ""),
        scope.get("authorization_quote", ""),
    ]
    for record_key in ("source_boundary", "research_boundary"):
        record = state.get(record_key)
        if isinstance(record, dict):
            candidates.extend([record.get("value", ""), record.get("user_quote", ""), record.get("authorization_quote", "")])
    for text in candidates:
        if SEED_ONLY_RE.search(str(text or "")):
            return True
    return has_truthy(scope, "seed_only_confirmed") or has_truthy(scope, "no_external_search_confirmed")


def validate_research_scope(state, phase="draft"):
    if phase == "task-list":
        return []
    scope = state.get("research_scope")
    if scope is None:
        scope = {}
    if not isinstance(scope, dict):
        return ["资料搜集：research_scope 必须是 JSON object。"]

    seeds = seed_sources(state, scope)
    if not seeds:
        return []

    if explicit_seed_only_authorized(state, scope):
        return []

    errors = []
    requires_external = risk_requires_external_research(state, scope, seeds)
    requires_freshness = risk_requires_freshness(state, scope)

    if requires_external:
        if not has_truthy(scope, "external_search_done") and not external_sources(scope):
            errors.append("资料搜集：种子资料不是完整资料搜集，不能只解析用户提供的链接/文件；必须继续检索主题相关的最新、权威、最匹配资料。")
        if not has_truthy(scope, "official_sources_checked") and not as_list(scope.get("official_sources")):
            errors.append("资料搜集：缺少官方/权威来源核验记录；高时效或硬信息不能只依据用户提供资料改写。")
        if not has_truthy(scope, "independent_crosscheck_checked") and not as_list(scope.get("independent_sources")):
            errors.append("资料搜集：缺少独立交叉核对记录；至少说明除用户资料外还核对了哪些可靠来源。")

    if requires_freshness and not has_truthy(scope, "freshness_checked"):
        errors.append("资料搜集：缺少最新核验或信息截至时间记录；动态信息必须确认当前有效口径。")

    if requires_external and not str(scope.get("source_mix", "")).strip():
        errors.append("资料搜集：缺少来源组合说明；需要记录用户种子资料、官方/权威资料和交叉核对资料如何共同支撑正文。")

    return errors


def print_report(errors):
    if not errors:
        print("[通过] 资料搜集范围已覆盖用户种子资料、外部扩展和必要核验。")
        return
    print("[阻断] 当前不能进入写作、排版或交付。")
    print("缺少或不可信的资料搜集动作：")
    for error in errors:
        print("- %s" % error)
    print("")
    print("执行要求：用户提供的链接、文件或截图只算种子资料；所有智能体和模型都不能只解析用户资料后直接写作。")


def main():
    parser = argparse.ArgumentParser(description="Mr.Li Writer 资料搜集范围硬门禁")
    parser.add_argument("state", help="任务状态 JSON 文件")
    parser.add_argument(
        "--phase",
        default="draft",
        choices=("draft", "layout", "delivery", "task-list"),
        help="即将进入的阶段",
    )
    args = parser.parse_args()

    try:
        state = load_state(pathlib.Path(args.state).expanduser())
    except ValueError as exc:
        print("[阻断] %s" % exc)
        return 2

    errors = validate_research_scope(state, phase=args.phase)
    print_report(errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
