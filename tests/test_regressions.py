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


class GzhThemeRegressionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
