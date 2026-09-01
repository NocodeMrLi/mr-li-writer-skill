import importlib.util
import json
from html.parser import HTMLParser
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_html = load_module("quality_gate_build_html", "scripts/build_html.py")
build_gzh = load_module("quality_gate_build_gzh", "scripts/build_gzh_html.py")


def confirmed_state(platform="公众号", delivery_style="moyu-green", original_prompt="写一篇测试文章"):
    return {
        "original_prompt": original_prompt,
        "platform": {"value": platform, "confirmed": True, "source": "user", "user_quote": platform},
        "content_goal": {"value": "专业报告", "confirmed": True, "source": "user", "user_quote": "专业报告"},
        "writing_direction": {"value": "政策解读", "confirmed": True, "source": "user", "user_quote": "政策解读"},
        "delivery_style": {
            "value": delivery_style,
            "confirmed": True,
            "source": "user",
            "user_quote": delivery_style,
        },
    }


class ScriptProbeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_depth = 0
        self.executable_probe_hits = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self.script_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.script_depth:
            self.script_depth -= 1

    def handle_data(self, data):
        if self.script_depth and "__mrli_xss_probe" in data:
            self.executable_probe_hits += 1


class IntakeAuthorizationQualityGateTests(unittest.TestCase):
    def test_negated_auto_authorization_phrases_never_bypass_intake(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        prompts = (
            "不要自动匹配，先问我。",
            "不要直接处理，所有选项都先问我。",
            "不能你看着办，必须让我确认。",
            "这次不自动匹配。",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = subprocess.run(
                    [sys.executable, str(validator), "--from-prompt", prompt, "--phase", "task-list"],
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("请先确认以下信息", result.stdout)


class ResearchBoundaryQualityGateTests(unittest.TestCase):
    def test_negated_seed_only_phrases_still_require_external_research(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        prompts = (
            "不要只基于我给的链接，必须外查并核对最新政策：https://example.com/policy",
            "不是只基于我给的资料，请继续外查最新政策：https://example.com/policy",
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            for index, prompt in enumerate(prompts):
                with self.subTest(prompt=prompt):
                    state_path = directory / ("state-%d.json" % index)
                    state_path.write_text(
                        json.dumps(confirmed_state(original_prompt=prompt), ensure_ascii=False),
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        [sys.executable, str(validator), str(state_path), "--phase", "draft"],
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("必须继续检索", result.stdout)

    def test_explicit_affirmative_seed_only_authorization_remains_supported(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        state = confirmed_state(
            original_prompt="只基于我给的链接整理，不要外查：https://example.com/policy"
        )
        with tempfile.TemporaryDirectory() as tmp:
            state_path = pathlib.Path(tmp) / "state.json"
            state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(state_path), "--phase", "draft"],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class XiaohongshuPreviewSecurityTests(unittest.TestCase):
    def test_mixed_case_script_end_tag_cannot_escape_plain_text_payload(self):
        payload = "# 标题\n\n</ScRiPt><script>window.__mrli_xss_probe=1</ScRiPt>\n"
        plain_text = build_html.markdown_to_plain_text(payload)
        preview = (
            build_html.XHS_HTML_TEMPLATE.replace("__TITLE__", "标题")
            .replace("__BODY__", build_html.md_to_html(payload))
            .replace("__PLAIN_TEXT__", build_html.embed_plain_text(plain_text))
        )
        parser = ScriptProbeParser()
        parser.feed(preview)
        self.assertEqual(parser.executable_probe_hits, 0)
        self.assertIn('<textarea id="plainText" hidden aria-hidden="true">', preview)


class FormalDeliveryContentGateTests(unittest.TestCase):
    def write_web_bundle(self, directory, article_text):
        state = confirmed_state(
            platform="官网/网页",
            delivery_style="普通网页文章",
            original_prompt="写一篇官网工具指南",
        )
        state["content_goal"] = {
            "value": "普通传播",
            "confirmed": True,
            "source": "user",
            "user_quote": "普通传播",
        }
        state_path = directory / "task-state.json"
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        (directory / "title-strategy.md").write_text(
            "# 标题策略\n\n## 推荐标题\n测试指南\n\n## 备选标题\n测试指南二",
            encoding="utf-8",
        )
        (directory / "article-source.md").write_text(article_text, encoding="utf-8")
        (directory / "article.html").write_text("<main>测试指南</main>", encoding="utf-8")
        (directory / "article-preview.html").write_text(
            "<button>复制正文</button><script>function copyArticle(){}</script>",
            encoding="utf-8",
        )
        return state_path

    def test_delivery_blocks_reader_facing_process_leaks(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            state_path = self.write_web_bundle(
                directory,
                "# 测试指南\n\n本次检索结果显示，这个工具已经完成更新。\n",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    str(directory),
                    "--platform",
                    "官网/网页",
                    "--task-state",
                    str(state_path),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("正文质量门禁", result.stdout)
        self.assertIn("检索/搜索结果", result.stdout)

    def test_delivery_allows_soft_style_warning_without_hard_policy_violation(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            state_path = self.write_web_bundle(
                directory,
                "# 测试指南\n\n随着行业发展，这里给出一份具体可执行的检查清单。\n",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    str(directory),
                    "--platform",
                    "官网/网页",
                    "--task-state",
                    str(state_path),
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("开头疑似", result.stdout)

    def test_professional_delivery_requires_verifiable_sources(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            state_path = self.write_web_bundle(
                directory,
                "# 政策分析\n\n这里给出一项需要核验的政策判断。\n",
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["content_goal"]["value"] = "专业报告"
            state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    str(directory),
                    "--platform",
                    "官网/网页",
                    "--task-state",
                    str(state_path),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("缺少“## 参考资料”", result.stdout)
        self.assertIn("没有可验证的 URL", result.stdout)

    def test_strict_lint_blocks_each_reader_facing_policy_violation(self):
        lint = ROOT / "scripts/lint_article.py"
        cases = (
            ("# 标题\n\n资料来自某某培训公开汇总。\n", "商业相关第三方机构"),
            ("# 标题\n\n我采访过十位读者，结论如下。\n", "第一人称经历"),
            ("# 标题\n\n调查显示，80% 的用户支持这一做法。\n", "百分比数据"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            for index, (article, expected) in enumerate(cases):
                with self.subTest(expected=expected):
                    source = directory / ("article-%d.md" % index)
                    source.write_text(article, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(lint), str(source), "--strict-delivery"],
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(expected, result.stdout)


class PreviewAccessibilityQualityTests(unittest.TestCase):
    def test_wechat_preview_templates_have_main_article_and_named_heading(self):
        asset_template = (
            ROOT / "assets/gzh-design/assets/preview-template.html"
        ).read_text(encoding="utf-8")
        for name, template in (
            ("asset", asset_template),
            ("builder", build_gzh.PREVIEW_TEMPLATE),
        ):
            with self.subTest(template=name):
                self.assertRegex(template, r"<main\b")
                self.assertRegex(template, r"<article\b[^>]*id=[\"']gzh-content[\"']")
                self.assertRegex(template, r"<h1\b")


class RepositoryAutomationQualityTests(unittest.TestCase):
    def test_ci_covers_python_components_secrets_and_promo_dependencies(self):
        workflow = (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8")
        required_markers = (
            "python -m unittest discover -s tests -v",
            "python scripts/component_lint.py .",
            "python scripts/scan_sensitive.py",
            "actions/setup-node@v4",
            'node-version: "20"',
            "working-directory: promo-video",
            "npm ci",
            "npm audit --omit=dev --audit-level=high --registry=https://registry.npmjs.org",
            "node --check scripts/generate-promo-video.js",
            'node -e "require(\'sharp\')"',
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, workflow)

    def test_readme_exposes_runnable_quality_and_reproduction_entrypoints(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        required_markers = (
            "npm --prefix promo-video ci",
            "npm --prefix promo-video audit --omit=dev --audit-level=high --registry=https://registry.npmjs.org",
            ".github/workflows/",
            "quality.yml",
            "scan_sensitive.py",
            "promo-video/README.md",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, readme)

    def test_promo_renderer_uses_security_fixed_sharp_line(self):
        package = json.loads((ROOT / "promo-video/package.json").read_text(encoding="utf-8"))
        version = tuple(int(part) for part in package["dependencies"]["sharp"].split("."))
        self.assertGreaterEqual(version, (0, 35, 0))
        self.assertEqual(package["engines"]["node"], ">=20.9.0")


if __name__ == "__main__":
    unittest.main()
