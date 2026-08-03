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

EVIDENCE_PHRASES = (
    "数据显示",
    "报告显示",
    "研究表明",
    "研究发现",
    "专家指出",
    "专家表示",
    "调查显示",
    "根据调查",
    "根据研究",
    "公开资料显示",
)

OVER_LITERARY_PHRASES = (
    "命运的齿轮",
    "时代的洪流",
    "灵魂深处",
    "生命的底色",
    "岁月长河",
    "人间烟火",
    "诗意地",
    "在时光里",
    "内心深处",
    "精神旷野",
)

ABSTRACT_PHRASES = (
    "意义",
    "价值",
    "本质",
    "底层逻辑",
    "时代",
    "命运",
    "灵魂",
    "内核",
)

LOW_EVIDENCE_GENRES = {
    "relationship-life",
    "story-profile",
    "personal-essay",
    "platform-light",
}

HIGH_RISK_MODES = {
    "research-explainer",
}


def parse_args():
    parser = argparse.ArgumentParser(description="检查文章结构、引用和常见 AI 腔")
    parser.add_argument("markdown", help="Markdown 文件")
    parser.add_argument("--mode", default="research-explainer", help="内容模式")
    parser.add_argument("--genre", default="", help="文章体裁，如 relationship-life/policy-industry/product-tool")
    parser.add_argument(
        "--evidence-density",
        default="",
        choices=("", "high", "medium", "low", "minimal", "高", "中", "低", "极低"),
        help="证据密度: high/medium/low/minimal 或 高/中/低/极低",
    )
    parser.add_argument("--title", default="", help="可选标题，用于长度检查")
    parser.add_argument(
        "--require-sources",
        action="store_true",
        help="要求文章包含参考资料和至少一个 URL",
    )
    parser.add_argument(
        "--impact-check",
        action="store_true",
        help="检查高完成度增强是否走向过度文学化、抽象化或缺少记忆点",
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

    evidence_hits = sum(text.count(phrase) for phrase in EVIDENCE_PHRASES)
    density = args.evidence_density
    is_low_density = density in {"low", "minimal", "低", "极低"}
    if args.genre in LOW_EVIDENCE_GENRES or is_low_density:
        if evidence_hits >= 3:
            warnings.append(
                "低证据体裁/密度中出现数据、研究或专家话术 %d 次；检查是否喧宾夺主。"
                % evidence_hits
            )
        if len(re.findall(r"\b\d{2,3}%\b", text)) >= 2:
            warnings.append("低证据文章包含多个百分比数字；检查是否把生活/关系内容写成报告。")
        if args.require_sources and not re.search(r"^##\s+(参考资料|References)\s*$", text, re.M):
            warnings.append("低证据文章未列参考资料可以接受，但请确认正文没有硬事实承诺。")

    if args.mode in HIGH_RISK_MODES and density in {"", "low", "minimal", "低", "极低"}:
        warnings.append("研究解释类文章使用低证据密度；请确认主题不是政策、价格、医疗、法律、金融等高风险硬信息。")

    if args.impact_check:
        literary_hits = sum(text.count(phrase) for phrase in OVER_LITERARY_PHRASES)
        if literary_hits >= 2:
            warnings.append("发现过度文学化表达 %d 次；检查是否影响平台读者理解和转述。" % literary_hits)

        abstract_hits = sum(text.count(phrase) for phrase in ABSTRACT_PHRASES)
        concrete_markers = len(re.findall(r"(早上|晚上|那天|一次|门口|桌上|手机|消息|说|问|看见|走|坐|放下|打开)", text))
        if abstract_hits >= 10 and concrete_markers < 3:
            warnings.append("抽象词较多但具体场景/动作较少；检查主题升维是否太飘。")

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        long_paragraphs = [p for p in paragraphs if len(re.sub(r"\s+", "", p)) > 260]
        if len(long_paragraphs) >= 3:
            warnings.append("长段落较多；检查平台阅读是否吃力。")

        if not re.search(r"(不是.+而是|真正|关键|核心|换句话说|说到底|更准确地说)", text):
            warnings.append("未发现清晰的核心判断提示；检查文章是否缺少可转述记忆点。")

    for warning in warnings:
        print("[警告] %s" % warning)
    for error in errors:
        print("[错误] %s" % error)

    if errors:
        return 1
    suffix = args.mode
    if args.genre:
        suffix += "/%s" % args.genre
    if args.evidence_density:
        suffix += "/%s" % args.evidence_density
    print("[通过] %s (%s)" % (path, suffix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
