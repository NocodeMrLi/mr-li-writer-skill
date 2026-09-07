#!/usr/bin/env python3
"""Shared source-role checks for article linting and HTML builders."""

import json
import re
from pathlib import Path


COMMERCIAL_ENTITY = (
    r"(?:培训(?:机构|学校|平台|公司|品牌|中心)?|网校|"
    r"辅导(?:机构|平台|公司|品牌|中心)?|题库(?:平台|公司|品牌)?|"
    r"考证(?:机构|平台|服务)?|课程(?:平台|公司|品牌|中心)|"
    r"教育(?:培训|咨询)(?:机构|公司|中心)?|咨询(?:机构|公司|平台|中心))"
)
SOURCE_ACTION = r"(?:发布|公布|放出|整理|汇总|统计|披露|表示|指出|显示|称)"
ENTITY_PREFIX = r"[\u4e00-\u9fffA-Za-z0-9·.-]{1,24}"

COMMERCIAL_SOURCE_EXPOSURE_PATTERNS = (
    r"(?:数据|资料|信息|内容).{0,24}?(?:来自|来源于|据).{0,70}?(?P<entity_a>%s%s)" % (ENTITY_PREFIX, COMMERCIAL_ENTITY),
    r"(?:据|来自|来源于|参考|援引).{0,40}?(?P<entity_b>%s%s)" % (ENTITY_PREFIX, COMMERCIAL_ENTITY),
    r"(?P<entity_c>%s%s)[^。！？\n]{0,30}%s" % (ENTITY_PREFIX, COMMERCIAL_ENTITY, SOURCE_ACTION),
)
COMMERCIAL_SOURCE_REGEXES = tuple(re.compile(pattern, re.I) for pattern in COMMERCIAL_SOURCE_EXPOSURE_PATTERNS)

BUILTIN_OFFICIAL_IDENTITY = re.compile(
    r"(?:工业和信息化部|工信部|教育部|人力资源和社会保障部|人社部|财政部|"
    r"国家市场监督管理总局|国家统计局|国务院|中国政府网|中国计算机技术职业资格网|"
    r"中国国际人才交流基金会|软考办|PMI(?:\s*中国)?|"
    r"[\u4e00-\u9fff]{1,16}(?:人民政府|主管部门|考试中心)|"
    r"(?:国家|省|市|区|县)[\u4e00-\u9fff]{1,16}(?:部|委|办|局|厅|署))",
    re.I,
)
SEPARATE_ENTITY_CUE = re.compile(r"(?:与|和|及|联合|会同|携手|授权|委托|指导|合作|主管|主办|所属|下属)")


def compile_named_source_regex(names):
    patterns = []
    for name in names:
        term = str(name or "").strip()
        if not term:
            continue
        escaped = re.escape(term)
        if len(term) <= 2 and re.fullmatch(r"[\u4e00-\u9fff]+", term):
            patterns.append(
                r"(?:据|来自|来源于|参考|援引).{0,40}%s|%s.{0,30}(?:刚(?:把)?|%s)"
                % (escaped, escaped, SOURCE_ACTION)
            )
        else:
            patterns.append(escaped)
    return re.compile(r"(?:%s)" % "|".join(patterns), re.I) if patterns else None


def source_role_names(task_state):
    if not task_state:
        return (), ()
    try:
        state = json.loads(Path(task_state).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return (), ()
    scope = state.get("research_scope", {})
    entities = scope.get("source_entities", []) if isinstance(scope, dict) else []
    restricted = []
    official = []
    for entity in entities if isinstance(entities, list) else []:
        if not isinstance(entity, dict):
            continue
        name = str(entity.get("name", "")).strip()
        role = str(entity.get("role", "")).strip().lower().replace("-", "_")
        visibility = str(entity.get("reader_visibility", "")).strip().lower()
        if not name:
            continue
        if role in {"official", "authoritative"}:
            official.append(name)
        if role in {"commercial_interested", "unknown"} or visibility in {"omit", "anonymous", "internal_only"}:
            restricted.append(name)
    return tuple(dict.fromkeys(restricted)), tuple(dict.fromkeys(official))


def entity_is_official_identity(entity_text, official_names=()):
    text = str(entity_text or "")
    commercial = re.search(COMMERCIAL_ENTITY, text, re.I)
    if not commercial:
        return False
    for name in official_names:
        for official in re.finditer(re.escape(name), text, re.I):
            if official.end() >= commercial.end():
                return True
            if official.end() <= commercial.start():
                between = text[official.end() : commercial.start()]
                if not SEPARATE_ENTITY_CUE.search(between):
                    return True
    for official in BUILTIN_OFFICIAL_IDENTITY.finditer(text):
        if official.end() > commercial.start():
            continue
        between = text[official.end() : commercial.start()]
        if not SEPARATE_ENTITY_CUE.search(between):
            return True
    return False


def has_commercial_source_exposure(text, configured_regex=None, official_names=()):
    body = str(text or "")
    if configured_regex and configured_regex.search(body):
        return True
    for regex in COMMERCIAL_SOURCE_REGEXES:
        for match in regex.finditer(body):
            entity = next((value for value in match.groupdict().values() if value), match.group(0))
            if not entity_is_official_identity(entity, official_names):
                return True
    return False


def has_restricted_source_mention(text, names):
    regex = compile_named_source_regex(names)
    return bool(regex and regex.search(str(text or "")))
