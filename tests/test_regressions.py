import contextlib
import html
import importlib.util
import io
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_gzh = load_module("build_gzh_html", "scripts/build_gzh_html.py")
lint_article = load_module("lint_article", "scripts/lint_article.py")


SAMPLE_MD = """# 测试文章

开头说明。

## 第一部分：先判断问题

正文一。

## 第二部分：再给方法

正文二。

## 第三部分：完成交付

正文三。
"""

TABLE_MD = """# 报名状态

| 省份 | 报名开始 | 报名截止 | 备注 |
| --- | --- | --- | --- |
| 广东 | 8月17日 9:00 | 8月25日 17:00 | 今天需要完成缴费并确认报名状态 |
| 辽宁 | 8月19日 8:30 | 8月25日 16:00 | 不含大连，大连单独安排 |
"""


class DeliveryProtocolTests(unittest.TestCase):
    def test_skill_requires_native_file_attachments(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("原生附件", text)
        self.assertNotIn("`[用途名](绝对路径) — 一句话用途`", text)

    def test_research_protocol_covers_commercial_source_conflicts(self):
        text = (ROOT / "references/research-protocol.md").read_text(encoding="utf-8")
        self.assertIn("直接商业利益", text)
        self.assertIn("相关机构公开汇总", text)

    def test_wechat_delivery_requires_and_validates_four_artifacts(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        protocol = (ROOT / "references/delivery-protocol.md").read_text(encoding="utf-8")
        self.assertTrue(validator.exists(), "缺少公众号四件套交付校验器")
        for role in ("标题策略", "正文 Markdown", "公众号正文 HTML", "复制预览 HTML"):
            self.assertIn(role, protocol)

        with tempfile.TemporaryDirectory() as tmp:
            delivery = pathlib.Path(tmp)
            (delivery / "article-source.md").write_text("# 正文\n\n内容。", encoding="utf-8")
            (delivery / "article.html").write_text("<section>正文</section>", encoding="utf-8")
            (delivery / "article-preview.html").write_text(
                "<button>复制到公众号</button><script>function gzhCopy(){}</script>",
                encoding="utf-8",
            )
            missing = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "公众号"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing.returncode, 0)

            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            complete = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "公众号"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)

    def test_agent_entrypoint_repeats_wechat_delivery_guards(self):
        text = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("four real", text)
        self.assertIn("semantic", text)
        self.assertIn("validate_delivery_bundle.py", text)

    def test_agent_entrypoint_routes_reader_value_before_novelty(self):
        text = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("minimum necessary innovation", text)
        self.assertIn("reader job", text)
        self.assertIn("speaking position", text)

    def test_zhihu_and_xiaohongshu_require_layout_confirmation(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        platform = (ROOT / "references/platform-native-protocol.md").read_text(encoding="utf-8")
        agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        for text in (skill, platform):
            self.assertIn("是否需要 HTML 排版预览", text)
            self.assertIn("不要询问", text)
        self.assertIn("ask whether HTML layout preview is needed", agent)

    def test_platform_protocol_defines_minimum_necessary_confirmation_matrix(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        platform = (ROOT / "references/platform-native-protocol.md").read_text(encoding="utf-8")
        for phrase in (
            "最低必要询问",
            "公众号排版主题",
            "回答还是专栏",
            "内容目标",
            "发布环境",
            "Markdown / CMS 富文本 / 静态 HTML",
            "一次合并询问",
            "不重复询问",
        ):
            self.assertIn(phrase, platform)
        self.assertIn("必要询问矩阵", skill)
        self.assertIn("一次合并", skill)

    def test_non_layout_platform_bundle_requires_title_and_native_source_only(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            delivery = pathlib.Path(tmp)
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "article-source.md").write_text("# 正文\n\n内容。", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "知乎"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("平台原生正文", result.stdout)
            self.assertNotIn("跳过", result.stdout)

    def test_formatted_non_wechat_bundle_requires_clean_and_copy_html(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            delivery = pathlib.Path(tmp)
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "article-source.md").write_text("# 正文\n\n内容。", encoding="utf-8")
            missing = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "知乎", "--layout"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing.returncode, 0)

            (delivery / "article.html").write_text("<main>正文</main>", encoding="utf-8")
            (delivery / "article-preview.html").write_text(
                "<button>复制正文</button><script>navigator.clipboard.writeText('正文')</script>",
                encoding="utf-8",
            )
            complete = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "知乎", "--layout"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)

    def test_xiaohongshu_bundle_accepts_plain_text_native_source(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            delivery = pathlib.Path(tmp)
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "note-source.txt").write_text("测试笔记\n\n#话题一 #话题二", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "小红书"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("平台原生正文", result.stdout)
            self.assertNotIn("跳过", result.stdout)

    def test_website_platform_requires_html_pair_by_default(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            delivery = pathlib.Path(tmp)
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "web-source.md").write_text("# 网页正文\n\n内容。", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "官网/网页"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("平台排版 HTML", result.stdout)
            self.assertIn("复制预览 HTML", result.stdout)

            (delivery / "web.html").write_text("<main>网页正文</main>", encoding="utf-8")
            (delivery / "web-preview.html").write_text(
                "<button>复制正文</button><script>function copyArticle(){}</script>",
                encoding="utf-8",
            )
            complete = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "官网/网页"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)
            for role in ("标题策略 Markdown", "平台原生正文", "平台排版 HTML", "复制预览 HTML"):
                self.assertIn(role, complete.stdout)

    def test_generic_builder_can_emit_clean_and_copy_preview_html(self):
        builder = ROOT / "scripts/build_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            output = directory / "article.html"
            source.write_text("# 测试标题\n\n正文内容。", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "知乎",
                    "--emit-pair",
                ],
                capture_output=True,
                text=True,
            )
            preview = directory / "article-preview.html"
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            self.assertTrue(preview.is_file())
            self.assertNotIn("copyArticle", output.read_text(encoding="utf-8"))
            self.assertIn("copyArticle", preview.read_text(encoding="utf-8"))


class ReadmeDocumentationTests(unittest.TestCase):
    def test_markdown_table_separators_match_header_width(self):
        lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
        separator = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+$")
        for index, line in enumerate(lines):
            if separator.fullmatch(line):
                with self.subTest(line=index + 1):
                    self.assertGreater(index, 0)
                    self.assertEqual(lines[index - 1].count("|"), line.count("|"))

    def test_installation_is_runnable_from_the_public_repository(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "git clone https://github.com/NocodeMrLi/mr-li-writer-skill.git",
            text,
        )

    def test_directory_tree_mentions_delivery_protocol_and_tests(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("delivery-protocol.md", text)
        self.assertIn("├── tests/", text)
        self.assertIn("test_regressions.py", text)

    def test_readme_documents_four_artifacts_and_runnable_checks(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for artifact in ("title-strategy.md", "article-source.md", "article-gzh.html", "article-preview.html"):
            self.assertIn(artifact, text)
        self.assertIn("article-gzh_preview.html", text)
        self.assertIn("python3 -m unittest discover -s tests -v", text)
        self.assertIn("重要文章发布前", text)

    def test_readme_documents_adaptive_innovation_and_human_writing_inspiration(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in ("最低必要创新", "读者任务", "点击契约", "说话位置"):
            self.assertIn(phrase, text)
        self.assertIn("https://github.com/KKKKhazix/human-writing", text)

    def test_public_notices_do_not_expose_local_source_paths(self):
        notice = (ROOT / "assets/gzh-design/NOTICE.md").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", notice)

    def test_readme_explains_original_product_strengths_and_conditional_delivery(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in ("不是拼装式提示词", "编辑路由", "最低必要创新", "写作到交付闭环"):
            self.assertIn(phrase, text)
        self.assertIn("需要排版", text)
        self.assertIn("不需要排版", text)
        self.assertIn("不机械凑四件套", text)

    def test_readme_explains_zhihu_xiaohongshu_layout_confirmation(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("选择知乎或小红书后", text)
        self.assertIn("是否需要 HTML 排版预览", text)

    def test_readme_explains_platform_confirmation_points(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("执行中会确认什么", text)
        for platform in ("公众号", "知乎", "小红书", "官网/网页", "个人博客"):
            self.assertIn(platform, text)
        self.assertIn("一次合并询问", text)


class ArticleLintTests(unittest.TestCase):
    def test_lint_warns_when_training_vendors_are_named_as_sources(self):
        article = """# 软考报名时间

数据来自全国软考报名平台当前页面及 51CTO、希赛网公开汇总。
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "article.md"
            path.write_text(article, encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["lint_article.py", str(path)]):
                with contextlib.redirect_stdout(output):
                    code = lint_article.main()
        self.assertEqual(code, 0)
        self.assertIn("商业相关第三方机构", output.getvalue())
        self.assertIn("相关机构公开汇总", output.getvalue())

    def test_lint_accepts_generic_commercial_source_wording(self):
        article = """# 软考报名时间

数据来自全国软考报名平台当前页面及相关机构公开汇总。
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "article.md"
            path.write_text(article, encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["lint_article.py", str(path)]):
                with contextlib.redirect_stdout(output):
                    code = lint_article.main()
        self.assertEqual(code, 0)
        self.assertNotIn("商业相关第三方机构", output.getvalue())

    def test_impact_lint_does_not_require_formulaic_insight_markers(self):
        article = """# 普通工作日为什么更能检验健身计划

周二晚上六点，外面下着雨，人刚加完班。健身房还要坐四站地铁。

办卡只用一分钟，去一次却要换衣服、出门、训练、洗澡。计划能不能坚持，应该拿这样的普通一天来算。
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "article.md"
            path.write_text(article, encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["lint_article.py", str(path), "--impact-check", "--genre", "relationship-life"],
            ):
                with contextlib.redirect_stdout(output):
                    code = lint_article.main()
        self.assertEqual(code, 0)
        self.assertNotIn("未发现清晰的核心判断提示", output.getvalue())

    def test_lint_warns_on_semantic_reversal_posture(self):
        article = """# 为什么计划总会失败

你以为自己缺的是自律，其实真正的问题藏在时间安排里。

很多计划只写目标，没有给普通工作日留下执行空间。
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "article.md"
            path.write_text(article, encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["lint_article.py", str(path)]):
                with contextlib.redirect_stdout(output):
                    code = lint_article.main()
        self.assertEqual(code, 0)
        self.assertIn("翻案", output.getvalue())


class EditorialInnovationProtocolTests(unittest.TestCase):
    def test_skill_routes_editorial_value_before_innovation(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("editorial-routing-protocol.md", text)
        self.assertIn("最低必要创新", text)
        self.assertIn("读者任务", text)
        self.assertNotIn("保留完整创作流程：选题诊断、立意升级", text)

    def test_editorial_router_defines_four_innovation_levels(self):
        path = ROOT / "references/editorial-routing-protocol.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        for level in ("直给型", "微创新型", "视角转换型", "概念创新型"):
            self.assertIn(level, text)
        for reader_job in ("找答案", "做选择", "避风险", "被理解", "看故事"):
            self.assertIn(reader_job, text)
        self.assertIn("读者收益", text)
        self.assertIn("理解成本", text)

    def test_title_rules_use_click_contract_not_novelty_as_default(self):
        text = (ROOT / "references/title-rules.md").read_text(encoding="utf-8")
        self.assertIn("点击契约", text)
        self.assertIn("此刻相关性", text)
        self.assertIn("理解成本", text)
        self.assertIn("自然口语感", text)
        self.assertIn("熟悉的问题", text)
        self.assertIn("差异化不是必选项", text)

    def test_humanize_rules_define_positive_human_voice(self):
        text = (ROOT / "references/humanize-rules.md").read_text(encoding="utf-8")
        for phrase in ("说话位置", "选择性取舍", "每段新增", "承认不知道", "先写后审"):
            self.assertIn(phrase, text)

    def test_high_impact_protocol_has_optional_enhancement_levels(self):
        text = (ROOT / "references/high-impact-writing-protocol.md").read_text(encoding="utf-8")
        for level in ("基础发布", "编辑增强", "深度增强"):
            self.assertIn(level, text)
        self.assertIn("不需要升维", text)

    def test_editorial_benchmark_covers_twelve_cross_genre_cases(self):
        protocol = (ROOT / "references/editorial-evaluation-protocol.md").read_text(encoding="utf-8")
        cases = (ROOT / "tests/fixtures/editorial-routing-cases.md").read_text(encoding="utf-8")
        self.assertEqual(cases.count("## CASE-"), 12)
        for dimension in ("点击意愿", "理解成本", "可信度", "活人感", "平台原生度"):
            self.assertIn(dimension, protocol)
        self.assertIn("同题多跑", protocol)
        self.assertIn("盲评", protocol)


class GzhThemeRegressionTests(unittest.TestCase):
    LONG_QUOTE_MD = """# 软考含金量

> 含金量 = 证书权威性 × 用途契合度 × 环境认可度

## 第一部分：先判断证书

正文一。
"""

    def test_moyu_cover_renders_title_once_without_repeated_fragment(self):
        title = "一份不会把复杂问题写复杂的完整安装与避坑指南"
        rendered = build_gzh.build_component_section(SAMPLE_MD, title, "moyu-green")
        plain = html.unescape(re.sub(r"<[^>]+>", "", rendered))
        plain = re.sub(r"\s+", "", plain)
        self.assertEqual(plain.count(title), 1)

    def test_graphite_section_number_is_a_placeholder(self):
        text = (ROOT / "assets/gzh-design/references/theme-graphite-minimal.md").read_text(encoding="utf-8")
        component = text.split("## 组件 5 章节标题", 1)[1].split("## 组件 6", 1)[0]
        self.assertIn("{{编号}}", component)
        self.assertNotIn('<span leaf="">01</span>', component)

    def test_every_theme_section_template_uses_dynamic_numbering(self):
        sections = {
            "theme-moyu-green.md": ("## 组件 4 章节标题", "## 组件 5"),
            "theme-red-white.md": ("## 组件 5 章节标题", "## 组件 6"),
            "theme-graphite-minimal.md": ("## 组件 5 章节标题", "## 组件 6"),
            "theme-zen-whitespace.md": ("## 组件 5 章节标题", "## 组件 6"),
            "theme-moyu-ticket.md": ("## 组件 3 章节标题", "## 组件 4"),
            "theme-olive-journal.md": ("## 组件 3 章节标题", "## 组件 4"),
        }
        theme_dir = ROOT / "assets/gzh-design/references"
        for filename, (start, end) in sections.items():
            with self.subTest(theme=filename):
                text = (theme_dir / filename).read_text(encoding="utf-8")
                component = text.split(start, 1)[1].split(end, 1)[0]
                self.assertIn("{{编号}}", component)

    def test_renderer_applies_each_section_number_to_every_theme(self):
        for theme in build_gzh.THEMES:
            components = build_gzh.load_theme_components(theme)
            for number in (1, 2, 3):
                with self.subTest(theme=theme, number=number):
                    rendered = build_gzh.component_section_title(theme, components, "章节标题", number)
                    plain = html.unescape(re.sub(r"<[^>]+>", "", rendered))
                    plain = re.sub(r"\s+", "", plain)
                    self.assertIn("%02d" % number, plain)
                    if number > 1:
                        self.assertNotIn("01", plain)

    def test_all_generated_themes_hide_production_labels(self):
        forbidden = ("公众号排版", "深度文章", "中文内容创作 Skill")
        for theme in build_gzh.THEMES:
            with self.subTest(theme=theme):
                rendered = build_gzh.build_component_section(SAMPLE_MD, "测试文章", theme)
                for phrase in forbidden:
                    self.assertNotIn(phrase, rendered)

    def test_moyu_toc_binds_each_heading_once(self):
        rendered = build_gzh.build_component_section(SAMPLE_MD, "测试文章", "moyu-green")
        for heading in ("第一部分：先判断问题", "第二部分：再给方法", "第三部分：完成交付"):
            self.assertEqual(rendered.count(heading), 2, heading)

    def test_moyu_toc_is_publication_safe_without_horizontal_scroll(self):
        rendered = build_gzh.build_component_section(SAMPLE_MD, "测试文章", "moyu-green")
        self.assertIn("overflow-wrap:anywhere", rendered)
        self.assertNotIn("overflow-x:auto", rendered)
        self.assertNotRegex(rendered, r"width:\s*\d+(?:\.\d+)?vw")
        self.assertNotIn("white-space:nowrap", rendered)
        self.assertNotIn("滑动查看", rendered)

    def test_theme_source_toc_components_are_publication_safe(self):
        theme_dir = ROOT / "assets/gzh-design/references"
        for path in sorted(theme_dir.glob("theme-*.md")):
            if path.name in {"theme-index.md", "theme-generator.md"}:
                continue
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(
                r"^##\s+组件\s+\d+\s+([^\n]*(?:目录|导读|toc)[^\n]*)\n(.*?)(?=^##\s+组件\s+\d+|\Z)",
                text,
                re.I | re.M | re.S,
            ):
                with self.subTest(theme=path.name, component=match.group(1)):
                    component = match.group(2)
                    self.assertNotIn("overflow-x:auto", component)
                    self.assertNotRegex(component, r"width:\s*\d+(?:\.\d+)?vw")
                    self.assertNotIn("white-space:nowrap", component)

    def test_markdown_tables_render_as_semantic_responsive_tables_in_every_theme(self):
        blocks = build_gzh.parse_blocks(TABLE_MD)
        self.assertTrue(any(block[0] == "table" for block in blocks))
        for theme in build_gzh.THEMES:
            with self.subTest(theme=theme):
                rendered = build_gzh.build_component_section(TABLE_MD, "报名状态", theme)
                self.assertIn("<table", rendered)
                self.assertIn("table-layout:fixed", rendered)
                self.assertIn("overflow-wrap:anywhere", rendered)
                self.assertNotIn("| --- |", rendered)

    def test_generated_html_validator_rejects_raw_markdown_tables(self):
        validator = load_module("validate_gzh_html", "scripts/validate_gzh_html.py")
        source = '<section><p><span leaf="">| 省份 | 截止时间 |\n| --- | --- |</span></p></section>'
        errors, _, _ = validator.validate(source)
        self.assertTrue(any("Markdown 表格" in error for error in errors), errors)

    def test_multi_column_components_include_text_overflow_guards(self):
        checks = {
            "theme-graphite-minimal.md": ("## 组件 12 数据 / 要点卡片组", "## 组件 13"),
            "theme-red-white.md": ("## 组件 12 数据 / 要点卡片组", "## 组件 13"),
            "theme-moyu-green.md": ("## 组件 11 布局组件", "## 组件 12"),
            "theme-moyu-ticket.md": ("## 组件 2 票据封面", "## 组件 3"),
            "theme-olive-journal.md": ("## 组件 21 对比摘要卡", "## 组件 22"),
        }
        theme_dir = ROOT / "assets/gzh-design/references"
        for filename, (start, end) in checks.items():
            with self.subTest(theme=filename):
                text = (theme_dir / filename).read_text(encoding="utf-8")
                component = text.split(start, 1)[1].split(end, 1)[0]
                self.assertIn("min-width:0", component)
                self.assertIn("overflow-wrap:anywhere", component)

    def test_long_visual_quotes_are_balanced_before_wechat_wrapping(self):
        for theme in build_gzh.THEMES:
            with self.subTest(theme=theme):
                rendered = build_gzh.build_component_section(self.LONG_QUOTE_MD, "软考含金量", theme)
                self.assertIn('data-balanced="quote"', rendered)
                balanced = re.search(r'<section data-balanced="quote".*?</section>', rendered, re.S)
                self.assertIsNotNone(balanced)
                self.assertIn("<br>", balanced.group(0))

    def test_public_topic_tags_do_not_expose_editorial_posture_words(self):
        labels = build_gzh.public_topic_tags("软考含金量中立深度解读", [])
        self.assertNotIn("中立", labels)
        self.assertEqual(labels, ("深度解读", "判断参考"))

    def test_validator_rejects_forbidden_reader_facing_badges(self):
        validator = load_module("validate_gzh_html_front_badge", "scripts/validate_gzh_html.py")
        source = '<section><span style="padding:2px 8px;border-radius:4px;"><span leaf="">中立</span></span></section>'
        errors, _, _ = validator.validate(source)
        self.assertTrue(any("前端标签" in error for error in errors), errors)

    def test_skill_documents_frontend_badge_and_title_linebreak_guards(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "references/delivery-protocol.md").read_text(encoding="utf-8")
        for text in (skill, protocol):
            self.assertIn("前端标签白名单", text)
            self.assertIn("标题/金句换行", text)


if __name__ == "__main__":
    unittest.main()
