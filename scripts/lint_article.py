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

SEMANTIC_REVERSAL_PATTERNS = (
    r"你以为.{2,80}(其实|实际|真正)",
    r"看似.{2,80}(其实|实际|实则)",
    r"表面上?.{2,80}(其实|实际|实则)",
    r"不是.{2,80}而是",
    r"并非.{2,80}而是",
    r"不在于.{2,80}而在于",
    r"(?:并不|不只|不再)是.{2,80}(?:而是|真正)",
)

NOMINALIZATION_PATTERNS = (
    r"进行(?:了|一次|着)?.{0,12}(?:调整|优化|分析|讨论|梳理|复盘|探索|思考)",
    r"实现(?:了)?.{0,16}(?:提升|增长|转变|突破)",
    r"完成(?:了)?对.{0,20}的",
    r"起到(?:了)?.{0,12}作用",
)

INSIGHT_ROAD_SIGNS = (
    "更深一层",
    "真正的问题是",
    "更本质的是",
    "还有一层",
    "只说对了一半",
    "答案恰恰相反",
)

CONJUNCTIONS = (
    "因为",
    "所以",
    "但是",
    "然而",
    "同时",
    "此外",
    "因此",
    "不仅",
    "并且",
)

VIRTUAL_OPENING_PATTERNS = (
    r"后台.*(有人|总有人|很多人|问)",
    r"群里.*(有人|总有人|很多人|问)",
    r"网上.*(有人|很多人|都在).*(问|讨论)",
    r"评论区.*(经常|常常|总是|有人)",
    r"有朋友问我",
    r"最近.*很多人.*问",
    r"每到.*(时候|季|季节|年底|年初|开学|报名).*(有人|很多人|问)",
)

GENERIC_OPENING_PATTERNS = (
    (r"随着.{0,20}(发展|普及|变化|到来)", "开头疑似使用“随着……”宏大背景套话。"),
    (r"在(当今|现代|如今).{0,12}(社会|时代|背景)", "开头疑似使用宏大背景开场。"),
    (r"(你是否也曾|你有没有发现|有没有发现|不知道你有没有)", "开头疑似使用空泛设问。"),
    (r"所谓.{1,20}(就是|指的是)", "开头疑似使用定义式套话。"),
    (r"(朋友|同事|读者|学员)小[A-ZＡ-Ｚ一二三四五六七八九十]", "开头疑似使用无真实素材支撑的假人物场景。"),
    (r"最近.{0,20}(很火|刷屏|爆了|全网都在)", "开头疑似使用热点套话。"),
    (r"每到.{0,12}(年底|年初|开学|报名|考试|毕业|换季|节假日)", "开头疑似使用泛季节/时间套话。"),
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

PROCESS_LEAK_PATTERNS = (
    (r"(抓取|爬取|采集)(到|自|于|时间|结果|数据|页面|信息)?", "出现“抓取/爬取/采集”等后台采集动作词"),
    (r"(检索|搜索|查询)(结果|显示|发现|到|出来)", "出现“检索/搜索结果”等生产过程表述"),
    (r"(我|我们)?(通过|使用|借助).{0,12}(搜索引擎|爬虫|脚本|工具|模型|AI|大模型|提示词|prompt)", "暴露搜索、工具、模型或提示词过程"),
    (r"(由|通过).{0,12}(AI|模型|大模型|系统).{0,12}(生成|整理|撰写|输出)", "暴露 AI/模型生成过程"),
    (r"(本文|本篇|文章)?(?:为|是)?\s*(二创|二次创作|二创整理|基于原文改写|基于链接改写|基于素材改写)", "把内部改写/二创口径写进读者端正文"),
    (r"(资料|数据|信息)(抓取|爬取|采集|清洗|抽取|汇总|整理)(时间|结果|口径)?", "把内部资料处理动作写进了正文"),
    (r"(本次|这次).{0,8}(整理|检索|搜索|抓取|采集).{0,12}(发现|得到|结果)", "出现任务执行过程口吻"),
    (r"(截至|截止)\s*\d{4}\s*年\s*\d{1,2}\s*月\s*(抓取|爬取|采集|检索)", "时间备注使用了后台动作词"),
    (r"\d{4}\s*年\s*\d{1,2}\s*月\s*(抓取|爬取|采集|检索)", "时间备注使用了后台动作词"),
)

COMMERCIAL_SOURCE_EXPOSURE_PATTERNS = (
    r"(?:数据|资料|信息|内容).{0,24}(?:来自|来源于|据).{0,70}(?<!相关)[\u4e00-\u9fffA-Za-z0-9]{2,16}(?:培训|网校|辅导|题库|课堂)",
)


def configured_commercial_source_patterns():
    path = Path(__file__).resolve().parents[1] / "references" / "commercial-source-terms.txt"
    try:
        terms = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except FileNotFoundError:
        terms = []
    if not terms:
        return ()
    names = "|".join(re.escape(term) for term in terms)
    return (
        r"(?:数据|资料|信息|内容).{0,24}(?:来自|来源于|据).{0,70}(?:%s)" % names,
        r"(?:%s).{0,30}(?:公开汇总|数据|资料|统计|显示)" % names,
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
    "platform-native",
}

HIGH_RISK_MODES = {
    "research-explainer",
}

XHS_MODULE_PATTERNS = (
    r"适合(谁|人群|你)",
    r"不适合(谁|人群|你)",
    r"避坑",
    r"判断标准",
    r"可收藏|收藏清单|建议收藏",
)

XHS_LONGFORM_PATTERNS = (
    r"本文将从",
    r"接下来.{0,12}(展开|分析|讨论)",
    r"从以下.{0,8}(方面|维度)",
    r"随着.{0,20}(发展|普及|变化|到来)",
    r"在(当今|现代|如今).{0,12}(社会|时代|背景)",
    r"综上所述",
    r"总而言之",
)

EMOJI_OR_SYMBOL_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF]|[✅⚠️📌✨🔥💡🌟👉❗️❤️⭐️]"
)


def parse_args():
    parser = argparse.ArgumentParser(description="检查文章结构、引用和常见 AI 腔")
    parser.add_argument("markdown", help="Markdown 文件")
    parser.add_argument("--mode", default="research-explainer", help="内容模式")
    parser.add_argument("--platform", default="", help="发布平台，如 公众号/知乎/小红书/官网/网页/个人博客")
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
        help="检查高完成度增强是否走向过度文学化、抽象化或阅读负担过重",
    )
    parser.add_argument(
        "--allow-commercial-source-names",
        action="store_true",
        help="文章本身在评测/介绍相关商业机构时，允许正文显名并要求说明利益关系",
    )
    return parser.parse_args()


def han_count(text):
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def sentence_length_cv(text):
    lengths = [
        han_count(match.group())
        for match in re.finditer(r"[^。！？!?\n]+[。！？!?]", text)
        if han_count(match.group()) >= 4
    ]
    if len(lengths) < 12:
        return None
    mean = sum(lengths) / len(lengths)
    if not mean:
        return None
    variance = sum((length - mean) ** 2 for length in lengths) / len(lengths)
    return (variance ** 0.5) / mean, len(lengths)


def main():
    args = parse_args()
    path = Path(args.markdown)
    if not path.is_file():
        print("[错误] 文件不存在: %s" % path, file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    warnings = []
    errors = []
    platform = args.platform.strip().lower()

    if not re.search(r"^#\s+\S+", text, re.M):
        warnings.append("缺少一级标题，HTML 可能只能使用命令行传入的标题。")

    body_start = re.sub(r"^#.*\n+", "", text.lstrip(), count=1)
    opening_sample = body_start[:220]

    if re.search(r"^(根据|数据显示|报告显示)", body_start.lstrip()):
        warnings.append("开头直接进入来源或数据，检查是否缺少场景、问题或读者入口。")

    for pattern in VIRTUAL_OPENING_PATTERNS:
        if re.search(pattern, opening_sample):
            warnings.append("开头疑似使用虚拟来源套话；请确认是否有真实读者提问，否则重写开头。")
            break

    for pattern, message in GENERIC_OPENING_PATTERNS:
        if re.search(pattern, opening_sample):
            warnings.append(message)
            break

    for phrase in AI_PHRASES:
        count = text.count(phrase)
        if count:
            warnings.append("发现疑似模板化表达“%s” %d 次。" % (phrase, count))

    reversal_hits = []
    for pattern in SEMANTIC_REVERSAL_PATTERNS:
        reversal_hits.extend(re.findall(pattern, text, re.S))
    if reversal_hits:
        warnings.append(
            "发现疑似翻案修辞动作 %d 处；检查是否先替读者虚构误解再宣布洞察。真实的认识变化可以保留，换皮套路应改为直接判断和依据。"
            % len(reversal_hits)
        )

    nominalization_hits = sum(
        len(re.findall(pattern, text)) for pattern in NOMINALIZATION_PATTERNS
    )
    if nominalization_hits >= 2:
        warnings.append(
            "发现动词名词化表达 %d 处；检查能否还原成谁做了什么、改变了什么。"
            % nominalization_hits
        )

    road_sign_hits = sum(text.count(phrase) for phrase in INSIGHT_ROAD_SIGNS)
    if road_sign_hits >= 2:
        warnings.append(
            "洞察路标出现 %d 次；不要靠“更深一层/真正的问题”给段落排队，让材料和因果承担推进。"
            % road_sign_hits
        )

    total_han = han_count(text)
    conjunction_hits = sum(text.count(word) for word in CONJUNCTIONS)
    if total_han >= 600 and conjunction_hits * 1000 / total_han > 9:
        warnings.append(
            "连词密度偏高；检查是否每段都靠因为/所以/然而等路标连接，能由语序和事理自然衔接的可删减。"
        )

    cv_result = sentence_length_cv(text)
    if cv_result and cv_result[0] < 0.38:
        warnings.append(
            "全文 %d 个句子的长度过于接近；检查是否形成统一节拍。只在内容需要时调整长短，不要机械打散。"
            % cv_result[1]
        )

    process_leaks = []
    for pattern, message in PROCESS_LEAK_PATTERNS:
        matches = re.findall(pattern, text, re.I)
        if matches:
            process_leaks.append(message)
    if process_leaks:
        warnings.append(
            "正文疑似暴露内容生产/资料处理过程：%s。请改为读者可接受的来源口径，如“信息截至 YYYY-MM-DD”“据官网当前页面”“公开资料显示”，不要出现抓取、爬取、采集、检索结果、AI 生成、提示词等后台动作。"
            % "；".join(dict.fromkeys(process_leaks))
        )

    commercial_patterns = COMMERCIAL_SOURCE_EXPOSURE_PATTERNS + configured_commercial_source_patterns()
    if not args.allow_commercial_source_names and any(re.search(pattern, text, re.I) for pattern in commercial_patterns):
        warnings.append(
            "正文疑似把商业相关第三方机构写成资料背书。硬信息应优先使用官方来源；第三方仅作辅助核对时，请改为“相关机构公开汇总”，不要在正文显名宣传。"
        )

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
            warnings.append("抽象词较多但具体场景/动作较少；检查内容是否为了显得深刻而变飘。")

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        long_paragraphs = [p for p in paragraphs if len(re.sub(r"\s+", "", p)) > 260]
        if len(long_paragraphs) >= 3:
            warnings.append("长段落较多；检查平台阅读是否吃力。")

        # 判断可以由事实、动作和完整推理自然落下，不要求出现“真正/核心”等提示词。

    is_xhs = (
        "小红书" in args.platform
        or "xiaohongshu" in platform
        or "xhs" in platform
        or args.mode == "xiaohongshu-note"
    )
    if is_xhs:
        heading_match = re.search(r"^#\s+(.+)$", text, re.M)
        if heading_match:
            title = heading_match.group(1).strip()
            if len(title) > 32:
                warnings.append("小红书标题偏长；检查是否仍是 SEO/公众号长标题。")
        else:
            warnings.append("小红书笔记缺少一级标题。")

        emoji_hits = len(EMOJI_OR_SYMBOL_PATTERN.findall(text))
        if emoji_hits < 3:
            warnings.append("小红书笔记少于 3 个 emoji 或符号化段落提示。")
        if emoji_hits > 18:
            warnings.append("小红书笔记 emoji/符号较多；检查是否满屏表情影响阅读。")

        tags = re.findall(r"(?<!\S)#([A-Za-z0-9_\-\u4e00-\u9fff]+)", text)
        if len(tags) < 6 or len(tags) > 10:
            warnings.append("小红书标签数量应为 6-10 个，当前为 %d 个。" % len(tags))

        module_hits = sum(1 for pattern in XHS_MODULE_PATTERNS if re.search(pattern, text))
        if module_hits < 2:
            warnings.append("小红书笔记缺少适合谁/不适合谁/避坑/判断标准/可收藏清单中的至少两个模块。")

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        body_paragraphs = [p for p in paragraphs if not p.startswith("#") and not p.startswith("标签")]
        long_xhs_paragraphs = [
            p for p in body_paragraphs
            if len(re.sub(r"\s+", "", p)) > 120 and not re.search(r"^[-*]\s+", p)
        ]
        if len(long_xhs_paragraphs) >= 2:
            warnings.append("小红书笔记存在多个过长段落；检查是否仍是公众号长文节奏。")

        section_like_headings = len(re.findall(r"^#{2,3}\s+", text, re.M))
        if section_like_headings >= 3:
            warnings.append("小红书笔记出现较多长文小标题层级；检查是否像公众号/知乎结构。")

        for pattern in XHS_LONGFORM_PATTERNS:
            if re.search(pattern, text):
                warnings.append("小红书笔记疑似出现公众号腔、长文铺垫或报告腔。")
                break

        if len(text) > 3200:
            warnings.append("小红书笔记全文较长；检查是否只是把长文缩短而非原生笔记。")

        if not re.search(r"标签\s*\n", text):
            warnings.append("小红书笔记末尾建议使用“标签”区域集中放置话题标签。")

    for warning in warnings:
        print("[警告] %s" % warning)
    for error in errors:
        print("[错误] %s" % error)

    if errors:
        return 1
    suffix = args.mode
    if args.platform:
        suffix += "/%s" % args.platform
    if args.genre:
        suffix += "/%s" % args.genre
    if args.evidence_density:
        suffix += "/%s" % args.evidence_density
    print("[通过] %s (%s)" % (path, suffix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
