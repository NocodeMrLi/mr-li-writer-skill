import contextlib
import html
import importlib.util
import io
import pathlib
import re
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


class DeliveryProtocolTests(unittest.TestCase):
    def test_skill_requires_native_file_attachments(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("原生附件", text)
        self.assertNotIn("`[用途名](绝对路径) — 一句话用途`", text)

    def test_research_protocol_covers_commercial_source_conflicts(self):
        text = (ROOT / "references/research-protocol.md").read_text(encoding="utf-8")
        self.assertIn("直接商业利益", text)
        self.assertIn("相关机构公开汇总", text)


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

    def test_moyu_toc_supports_long_titles_without_overflow(self):
        rendered = build_gzh.build_component_section(SAMPLE_MD, "测试文章", "moyu-green")
        self.assertIn("overflow-wrap:anywhere", rendered)
        self.assertIn("min-width:140px", rendered)
        self.assertNotIn("width:110px", rendered)

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
