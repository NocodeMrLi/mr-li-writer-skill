import contextlib
import html
import importlib.util
import io
import json
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
build_html = load_module("build_html", "scripts/build_html.py")
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
    def write_task_state(self, directory, **overrides):
        base = {
            "original_prompt": "写一篇公众号文章，主题是测试文章",
            "platform": {"value": "公众号", "confirmed": True, "source": "user", "user_quote": "公众号"},
            "content_goal": {"value": "普通传播", "confirmed": True, "source": "user", "user_quote": "普通传播"},
            "writing_direction": {"value": "实用指南", "confirmed": True, "source": "user", "user_quote": "写成实用指南"},
            "delivery_style": {"value": "moyu-green", "confirmed": True, "source": "user", "user_quote": "摸鱼绿"},
        }
        base.update(overrides)
        path = pathlib.Path(directory) / "task-state.json"
        path.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
        return path

    def test_task_intake_blocks_resume_when_required_confirmations_are_missing(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = pathlib.Path(tmp) / "task-state.json"
            state.write_text(
                json.dumps(
                    {
                        "platform": {
                            "value": "公众号",
                            "confirmed": True,
                            "source": "user",
                            "user_quote": "公众号",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    str(state),
                    "--phase",
                    "resume",
                    "--last-user",
                    "继续完成任务",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("不能把“继续完成任务”视为确认", result.stdout)
            self.assertIn("内容目标", result.stdout)
            self.assertIn("创作方向", result.stdout)
            self.assertIn("平台交付样式", result.stdout)

    def test_task_intake_rejects_model_inferred_confirmations(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                delivery_style={
                    "value": "graphite-minimal",
                    "confirmed": True,
                    "source": "model",
                    "user_quote": "模型推荐石墨极简",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "layout"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("平台交付样式", result.stdout)
            self.assertIn("不得用模型推断", result.stdout)

    def test_task_intake_rejects_cross_platform_delivery_style(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                platform={"value": "知乎", "confirmed": True, "source": "user", "user_quote": "知乎"},
                delivery_style={"value": "graphite-minimal", "confirmed": True, "source": "user", "user_quote": "石墨极简风"},
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "layout", "--platform", "知乎"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("不得把公众号主题或其他平台样式跨平台套用", result.stdout)
            self.assertIn("回答、专栏", result.stdout)

    def test_task_intake_accepts_user_confirmed_or_authorized_auto_match(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                delivery_style={
                    "value": "auto",
                    "confirmed": True,
                    "source": "auto_authorized",
                    "user_quote": "不用问，自动匹配",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "layout"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task_intake_rejects_memory_or_standing_instruction_as_authorization(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                delivery_style={
                    "value": "auto",
                    "confirmed": True,
                    "source": "auto_authorized",
                    "user_quote": "根据长期偏好：意图明确时直接执行、不询问、排版自行决定",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "layout"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("长期记忆", result.stdout)

    def test_task_intake_from_prompt_blocks_new_task_without_confirmations(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--from-prompt",
                "Meta AI 原生组织转型受挫，原文：https://example.com/article",
                "--phase",
                "task-list",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("新任务尚未形成任务状态", result.stdout)
        self.assertIn("发布平台", result.stdout)
        self.assertIn("内容目标", result.stdout)
        self.assertIn("创作方向", result.stdout)
        self.assertIn("平台交付样式", result.stdout)

    def test_task_intake_from_prompt_does_not_auto_authorize_from_memory_words(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--from-prompt",
                "根据长期偏好直接处理，写成公众号并自动匹配",
                "--phase",
                "task-list",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("发布平台", result.stdout)
        self.assertIn("当前平台可选交付样式", result.stdout)

    def test_task_intake_from_prompt_rejects_craft_mode_memory_authorization(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--from-prompt",
                "按 Craft mode 和用户偏好直接处理，这次排版由 AI 自行决定并自动匹配。",
                "--phase",
                "task-list",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("发布平台", result.stdout)
        self.assertIn("平台交付样式", result.stdout)
        self.assertIn("当前平台可选交付样式", result.stdout)

    def test_task_intake_rejects_platform_value_mixed_with_layout_theme(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                platform={
                    "value": "公众号（橄榄手记）",
                    "confirmed": True,
                    "source": "user",
                    "user_quote": "公众号",
                },
                delivery_style={
                    "value": "橄榄手记",
                    "confirmed": True,
                    "source": "user",
                    "user_quote": "橄榄手记",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "layout", "--platform", "公众号"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("发布平台不能混入排版主题", result.stdout)

    def test_task_intake_emit_question_card_separates_platform_and_layout_theme(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--from-prompt",
                "这篇 Gemini 3.5 Transcribe 的文章发到哪个平台？",
                "--phase",
                "task-list",
                "--emit-question-card",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("请先确认以下信息", result.stdout)
        self.assertIn("1. 发布平台", result.stdout)
        self.assertIn("公众号 / 小红书 / 知乎 / 官网/网页 / 个人博客", result.stdout)
        self.assertIn("2. 内容目标", result.stdout)
        self.assertIn("3. 创作方向", result.stdout)
        self.assertIn("4. 平台交付样式", result.stdout)
        self.assertIn("最推荐", result.stdout)
        self.assertIn("次推荐", result.stdout)
        self.assertIn("补充说明/自行输入", result.stdout)
        self.assertIn("公众号排版主题不是发布平台", result.stdout)
        self.assertNotIn("公众号（橄榄手记）", result.stdout)

    def test_task_intake_from_prompt_always_outputs_standard_question_card(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--from-prompt",
                "原文：https://example.com/article，帮我写一篇文章",
                "--phase",
                "task-list",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("请先确认以下信息", result.stdout)
        self.assertIn("1. 发布平台", result.stdout)
        self.assertIn("2. 内容目标", result.stdout)
        self.assertIn("3. 创作方向", result.stdout)
        self.assertIn("4. 平台交付样式", result.stdout)
        self.assertIn("补充说明/自行输入", result.stdout)

    def test_task_intake_from_prompt_does_not_treat_title_auto_match_as_global_authorization(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--from-prompt",
                "帮我写公众号文章，标题可以自动匹配，其他先问我。",
                "--phase",
                "task-list",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("内容目标", result.stdout)
        self.assertIn("创作方向", result.stdout)
        self.assertIn("平台交付样式", result.stdout)

    def test_research_scope_blocks_user_link_only_for_time_sensitive_hard_info(self):
        validator = ROOT / "scripts/validate_research_scope.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                original_prompt="https://mp.weixin.qq.com/s/example 2026 下半年软考报名要求",
                research_scope={
                    "user_seed_sources": ["https://mp.weixin.qq.com/s/example"],
                    "user_sources_checked": True,
                    "requires_external_research": True,
                    "risk": "time_sensitive_hard_info",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "draft"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("种子资料不是完整资料搜集", result.stdout)
            self.assertIn("官方/权威来源", result.stdout)
            self.assertIn("最新核验", result.stdout)

    def test_research_scope_accepts_seed_plus_official_fresh_crosscheck(self):
        validator = ROOT / "scripts/validate_research_scope.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                original_prompt="https://mp.weixin.qq.com/s/example 2026 下半年软考报名要求",
                research_scope={
                    "user_seed_sources": ["https://mp.weixin.qq.com/s/example"],
                    "user_sources_checked": True,
                    "external_search_done": True,
                    "official_sources_checked": True,
                    "freshness_checked": True,
                    "independent_crosscheck_checked": True,
                    "requires_external_research": True,
                    "risk": "time_sensitive_hard_info",
                    "source_mix": "用户种子资料 + 全国软考报名平台 + 各省软考办通知",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "draft"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_research_scope_allows_explicit_seed_only_boundary(self):
        validator = ROOT / "scripts/validate_research_scope.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                original_prompt="只基于我给的资料写，不再外查：https://mp.weixin.qq.com/s/example",
                research_scope={
                    "user_seed_sources": ["https://mp.weixin.qq.com/s/example"],
                    "user_sources_checked": True,
                    "requires_external_research": True,
                    "risk": "time_sensitive_hard_info",
                },
                source_boundary={
                    "value": "只基于用户给的资料，不再外查",
                    "confirmed": True,
                    "source": "user",
                    "user_quote": "只基于我给的资料写，不再外查",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "draft"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task_intake_requires_task_context_before_draft(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(tmp, original_prompt="")
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "draft"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("original_prompt/topic/brief", result.stdout)
            self.assertIn("不能绕过资料搜集范围校验", result.stdout)

    def test_task_intake_invokes_research_scope_before_draft(self):
        validator = ROOT / "scripts/validate_task_intake.py"
        with tempfile.TemporaryDirectory() as tmp:
            state = self.write_task_state(
                tmp,
                original_prompt="https://mp.weixin.qq.com/s/example 2026 下半年软考报名要求",
                research_scope={
                    "user_seed_sources": ["https://mp.weixin.qq.com/s/example"],
                    "requires_external_research": True,
                    "risk": "time_sensitive_hard_info",
                },
            )
            result = subprocess.run(
                [sys.executable, str(validator), str(state), "--phase", "draft"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("资料搜集", result.stdout)
            self.assertIn("不能只解析用户提供的链接", result.stdout)

    def test_documents_require_intake_check_before_fetching_or_task_list(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        for text in (skill, agent):
            self.assertIn("validate_task_intake.py", text)
            self.assertIn("--from-prompt", text)
            self.assertIn("--emit-question-card", text)
        self.assertIn("抓取、检索、读取链接、生成任务列表", skill)
        self.assertIn("before fetching source links", agent)

    def test_documents_require_seed_source_expansion_protocol(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        research = (ROOT / "references/research-protocol.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        for text in (skill, research, readme, agent):
            self.assertIn("种子资料", text)
            self.assertIn("validate_research_scope.py", text)
        for token in (
            "user_seed_sources",
            "external_search_done",
            "official_sources_checked",
            "freshness_checked",
            "source_mix",
        ):
            self.assertIn(token, skill + research + agent)
        self.assertIn("只基于我给的资料", skill + research + readme)
        self.assertIn("二创整理", skill + research + readme)

    def test_build_html_requires_task_state_before_formal_generation(self):
        builder = ROOT / "scripts/build_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            output = directory / "article.html"
            source.write_text(SAMPLE_MD, encoding="utf-8")
            missing_state = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "公众号",
                    "-t",
                    "moyu-green",
                    "--theme-confirmed",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing_state.returncode, 0)
            self.assertIn("--task-state", missing_state.stderr + missing_state.stdout)

            state = self.write_task_state(directory)
            complete = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "公众号",
                    "-t",
                    "moyu-green",
                    "--theme-confirmed",
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)

    def test_build_html_requires_task_state_for_every_platform(self):
        builder = ROOT / "scripts/build_html.py"
        platforms = ("知乎", "小红书", "官网/网页", "个人博客")
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            source.write_text(SAMPLE_MD, encoding="utf-8")
            for platform in platforms:
                output = directory / ("%s.html" % platform.replace("/", "-"))
                result = subprocess.run(
                    [
                        sys.executable,
                        str(builder),
                        str(source),
                        "-o",
                        str(output),
                        "--platform",
                        platform,
                    ],
                    capture_output=True,
                    text=True,
            )
            self.assertNotEqual(result.returncode, 0, platform)
            self.assertIn("--task-state", result.stderr + result.stdout)

    def test_non_wechat_html_deduplicates_page_title_and_markdown_h1(self):
        builder = ROOT / "scripts/build_html.py"
        title = "PMP 新考纲 12 月 5 日首考：第七版和第八版一张表对照，AI 题会怎么出"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "zhihu-source.md"
            output = directory / "zhihu.html"
            source.write_text("# %s\n\n正文第一段。\n" % title, encoding="utf-8")
            state = self.write_task_state(
                directory,
                platform={"value": "知乎", "confirmed": True, "source": "user", "user_quote": "知乎"},
                delivery_style={"value": "回答", "confirmed": True, "source": "user", "user_quote": "回答"},
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "知乎",
                    "--delivery-style",
                    "zhihu-answer",
                    "--title",
                    title,
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            html_text = output.read_text(encoding="utf-8")
            main = re.search(r'<main class="article" id="article">(.*?)</main>', html_text, re.S).group(1)
            body_text = html.unescape(re.sub(r"<[^>]+>", "", main))
            self.assertEqual(body_text.count(title), 1)
            self.assertEqual(len(re.findall(r"<h1", html_text)), 1)

    def test_build_html_rejects_theme_that_differs_from_task_state(self):
        builder = ROOT / "scripts/build_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            output = directory / "article.html"
            source.write_text(SAMPLE_MD, encoding="utf-8")
            state = self.write_task_state(
                directory,
                delivery_style={
                    "value": "moyu-green",
                    "confirmed": True,
                    "source": "user",
                    "user_quote": "摸鱼绿",
                },
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "公众号",
                    "-t",
                    "graphite-minimal",
                    "--theme-confirmed",
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("命令交付样式与任务状态不一致", result.stdout)

    def test_delivery_bundle_requires_task_state(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            delivery = pathlib.Path(tmp)
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "article-source.md").write_text("# 正文\n\n内容。", encoding="utf-8")
            (delivery / "article.html").write_text("<main>正文</main>", encoding="utf-8")
            (delivery / "article-preview.html").write_text(
                "<button>复制正文</button><script>function copyArticle(){}</script>",
                encoding="utf-8",
            )
            missing_state = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "公众号"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing_state.returncode, 0)
            self.assertIn("--task-state", missing_state.stdout + missing_state.stderr)

            state = self.write_task_state(delivery)
            complete = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    str(delivery),
                    "--platform",
                    "公众号",
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)

    def test_wrap_gzh_preview_requires_task_state(self):
        wrapper = ROOT / "scripts/wrap_gzh_preview.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article.html"
            output = directory / "article-preview.html"
            source.write_text("<section><p><span leaf=\"\">正文</span></p></section>", encoding="utf-8")

            missing_state = subprocess.run(
                [sys.executable, str(wrapper), str(source), str(output)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing_state.returncode, 0)
            self.assertIn("--task-state", missing_state.stderr + missing_state.stdout)

            state = self.write_task_state(directory)
            complete = subprocess.run(
                [sys.executable, str(wrapper), str(source), str(output), "--task-state", str(state)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)
            self.assertTrue(output.is_file())

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
            state = self.write_task_state(delivery)
            (delivery / "article-source.md").write_text("# 正文\n\n内容。", encoding="utf-8")
            (delivery / "article.html").write_text("<section>正文</section>", encoding="utf-8")
            (delivery / "article-preview.html").write_text(
                "<button>复制到公众号</button><script>function gzhCopy(){}</script>",
                encoding="utf-8",
            )
            missing = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "公众号", "--task-state", str(state)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing.returncode, 0)

            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            complete = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "公众号", "--task-state", str(state)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)

    def test_agent_entrypoint_repeats_wechat_delivery_guards(self):
        text = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("four real", text)
        self.assertIn("semantic", text)
        self.assertIn("validate_delivery_bundle.py", text)
        self.assertIn("--auto-theme-ok", text)
        self.assertIn("--theme-confirmed", text)
        self.assertIn("If the publishing platform is missing", text)
        self.assertIn("3-5 concrete options", text)

    def test_resume_requests_must_recheck_required_confirmations(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        platform_protocol = (ROOT / "references/platform-native-protocol.md").read_text(encoding="utf-8")
        for text in (skill, platform_protocol):
            self.assertIn("恢复任务防误判", text)
            self.assertIn("继续完成任务", text)
            self.assertIn("不得把“继续”理解为用户已确认缺失项", text)
            self.assertIn("发布平台、内容目标、创作方向、平台交付样式", text)

    def test_platform_delivery_style_confirmation_has_no_interpretation_gap(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        platform_protocol = (ROOT / "references/platform-native-protocol.md").read_text(encoding="utf-8")
        agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        for text in (skill, platform_protocol):
            self.assertIn("平台交付样式硬确认", text)
            self.assertIn("写正文、生成任务列表、创建正文文件、生成 HTML 或交付文件之前", text)
            self.assertIn("必须完整展示该平台的全部可选交付样式", text)
            self.assertIn("不得只展示推荐项", text)
            self.assertIn("公众号排版主题", text)
            for option in ("摸鱼绿", "红白色系", "石墨极简风", "留白禅意风", "摸鱼票据风", "橄榄手记", "自动匹配"):
                self.assertIn(option, text)
        for phrase in (
            "confirm the platform delivery style before drafting",
            "show the complete option set",
            "not only recommended options",
            "all six WeChat layout themes",
        ):
            self.assertIn(phrase, agent)

    def test_required_and_conditional_questions_are_hard_gates(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        platform_protocol = (ROOT / "references/platform-native-protocol.md").read_text(encoding="utf-8")
        agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for text in (skill, platform_protocol):
            self.assertIn("必问项与条件触发项硬门禁", text)
            self.assertIn("必问项缺失时不得写正文、生成任务列表、创建文件、排版或交付", text)
            self.assertIn("条件触发项一旦被触发，就临时升级为本任务的必确字段", text)
            self.assertIn("不得用模型推断、历史默认、平台默认或推荐项替代用户确认", text)
            for item in ("发布平台", "内容目标", "创作方向", "平台交付样式"):
                self.assertIn(item, text)
            for item in ("目标读者/阅读场景", "立场边界", "时效口径", "来源边界", "交付格式", "篇幅深度"):
                self.assertIn(item, text)
        for phrase in (
            "Required fields and triggered conditional fields are hard gates",
            "Do not draft, create tasks, create files, layout, or deliver",
            "Triggered conditional fields become required for that task",
        ):
            self.assertIn(phrase, agent)
        self.assertIn("必问项与条件触发项是硬门禁", readme)

    def test_wechat_builder_rejects_silent_auto_theme(self):
        builder = ROOT / "scripts/build_gzh_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            source.write_text(SAMPLE_MD, encoding="utf-8")
            state = self.write_task_state(directory)

            silent_auto = subprocess.run(
                [sys.executable, str(builder), str(source), "--no-preview", "--task-state", str(state)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(silent_auto.returncode, 0)
            self.assertIn("不能静默使用主题 auto", silent_auto.stderr)

            confirmed_theme = subprocess.run(
                [sys.executable, str(builder), str(source), "--no-preview", "-t", "moyu-green", "--task-state", str(state)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(confirmed_theme.returncode, 0)
            self.assertIn("不能由智能体静默指定主题", confirmed_theme.stderr)

            user_confirmed_theme = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "--no-preview",
                    "-t",
                    "moyu-green",
                    "--theme-confirmed",
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(user_confirmed_theme.returncode, 0, user_confirmed_theme.stdout + user_confirmed_theme.stderr)

    def test_wechat_builder_rejects_silent_specific_theme(self):
        builder = ROOT / "scripts/build_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            output = directory / "article.html"
            source.write_text(SAMPLE_MD, encoding="utf-8")
            state = self.write_task_state(
                directory,
                delivery_style={
                    "value": "graphite-minimal",
                    "confirmed": True,
                    "source": "user",
                    "user_quote": "石墨极简风",
                },
            )

            silent_specific = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "公众号",
                    "-t",
                    "graphite-minimal",
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(silent_specific.returncode, 0)
            self.assertIn("不能由智能体静默指定主题", silent_specific.stderr)

            confirmed_specific = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "公众号",
                    "-t",
                    "graphite-minimal",
                    "--theme-confirmed",
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(confirmed_specific.returncode, 0, confirmed_specific.stdout + confirmed_specific.stderr)
            self.assertTrue(output.is_file())

    def test_wechat_copy_preview_writes_rich_html_clipboard(self):
        builder = ROOT / "scripts/build_gzh_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            output = directory / "article.html"
            source.write_text(TABLE_MD, encoding="utf-8")
            state = self.write_task_state(
                directory,
                delivery_style={"value": "red-white", "confirmed": True, "source": "user", "user_quote": "红白色系"},
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "-t",
                    "red-white",
                    "--theme-confirmed",
                    "--task-state",
                    str(state),
                ],
                capture_output=True,
                text=True,
            )
            preview = directory / "article_preview.html"
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(preview.is_file())
            text = preview.read_text(encoding="utf-8")
            self.assertIn("ClipboardItem", text)
            self.assertIn("'text/html'", text)
            self.assertIn("'text/plain'", text)
            self.assertIn("navigator.clipboard.write", text)
            self.assertIn("gzhFallbackCopy", text)
            self.assertIn("<meta charset=\"utf-8\">", text)

    def test_skill_requires_multiple_direction_options_with_ranking(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for text in (skill, readme):
            self.assertIn("3-5", text)
            self.assertIn("最推荐", text)
            self.assertIn("次推荐", text)
        self.assertIn("用户只确认平台和方向，不等于确认平台交付样式", skill)
        self.assertIn("交付样式未确认前，任务列表不得出现", skill)

    def test_three_layer_confirmation_policy_is_documented(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        platform = (ROOT / "references/platform-native-protocol.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")

        for text in (skill, platform, readme):
            self.assertIn("必问", text)
            self.assertIn("条件问", text)
            self.assertIn("不默认问", text)
            for phrase in (
                "发布平台",
                "内容目标",
                "创作方向",
                "平台交付样式",
                "目标读者/阅读场景",
                "立场边界",
                "时效口径",
                "来源边界",
                "交付格式",
                "篇幅深度",
                "语气风格",
                "开头方式",
                "标题数量",
                "是否要金句",
                "是否要案例",
            ):
                self.assertIn(phrase, text)

        self.assertIn("three-layer confirmation", agent)
        self.assertIn("publishing platform, content goal", agent)
        self.assertIn("platform delivery style", agent)
        self.assertIn("do not ask by", agent)
        self.assertIn("default about tone", agent)

    def test_every_platform_has_delivery_style_confirmation(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        platform = (ROOT / "references/platform-native-protocol.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        delivery = (ROOT / "references/delivery-protocol.md").read_text(encoding="utf-8")

        for text in (skill, platform, readme):
            for phrase in (
                "平台交付样式",
                "回答 / 专栏",
                "手机卡片预览",
                "SEO-GEO 结构化",
                "静态 HTML",
            ):
                self.assertIn(phrase, text)

        for phrase in (
            "公众号确认排版主题",
            "知乎确认回答 / 专栏",
            "小红书确认纯文本笔记/手机卡片",
            "官网/网页确认网页结构",
            "个人博客确认 Markdown/CMS/静态 HTML",
        ):
            self.assertIn(phrase, delivery)

    def test_platform_builder_rejects_silent_wechat_auto_theme(self):
        builder = ROOT / "scripts/build_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            source = directory / "article-source.md"
            output = directory / "article.html"
            source.write_text(SAMPLE_MD, encoding="utf-8")
            auto_state = self.write_task_state(
                directory,
                delivery_style={
                    "value": "auto",
                    "confirmed": True,
                    "source": "auto_authorized",
                    "user_quote": "自动匹配",
                },
            )

            silent_auto = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "公众号",
                    "--task-state",
                    str(auto_state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(silent_auto.returncode, 0)
            self.assertIn("不能静默使用主题 auto", silent_auto.stderr)

            authorized_auto = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    str(source),
                    "-o",
                    str(output),
                    "--platform",
                    "公众号",
                    "--auto-theme-ok",
                    "--task-state",
                    str(auto_state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(authorized_auto.returncode, 0, authorized_auto.stdout + authorized_auto.stderr)
            self.assertTrue(output.is_file())

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
            "平台交付样式",
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
            state = self.write_task_state(
                delivery,
                platform={"value": "知乎", "confirmed": True, "source": "user", "user_quote": "知乎"},
                delivery_style={"value": "回答", "confirmed": True, "source": "user", "user_quote": "回答"},
            )
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "article-source.md").write_text("# 正文\n\n内容。", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "知乎", "--task-state", str(state)],
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
            state = self.write_task_state(
                delivery,
                platform={"value": "知乎", "confirmed": True, "source": "user", "user_quote": "知乎"},
                delivery_style={"value": "回答 + HTML 预览", "confirmed": True, "source": "user", "user_quote": "回答 + HTML 预览"},
            )
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "article-source.md").write_text("# 正文\n\n内容。", encoding="utf-8")
            missing = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "知乎", "--layout", "--task-state", str(state)],
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
                [sys.executable, str(validator), str(delivery), "--platform", "知乎", "--layout", "--task-state", str(state)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)

    def test_xiaohongshu_bundle_accepts_plain_text_native_source(self):
        validator = ROOT / "scripts/validate_delivery_bundle.py"
        with tempfile.TemporaryDirectory() as tmp:
            delivery = pathlib.Path(tmp)
            state = self.write_task_state(
                delivery,
                platform={"value": "小红书", "confirmed": True, "source": "user", "user_quote": "小红书"},
                delivery_style={"value": "清爽纯文本笔记", "confirmed": True, "source": "user", "user_quote": "清爽纯文本笔记"},
            )
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "note-source.txt").write_text("测试笔记\n\n#话题一 #话题二", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "小红书", "--task-state", str(state)],
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
            state = self.write_task_state(
                delivery,
                platform={"value": "官网/网页", "confirmed": True, "source": "user", "user_quote": "官网/网页"},
                delivery_style={"value": "普通网页文章", "confirmed": True, "source": "user", "user_quote": "普通网页文章"},
            )
            (delivery / "title-strategy.md").write_text(
                "# 标题策略\n\n## 主标题\n测试标题\n\n## 备选标题\n备选一、备选二。",
                encoding="utf-8",
            )
            (delivery / "web-source.md").write_text("# 网页正文\n\n内容。", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(validator), str(delivery), "--platform", "官网/网页", "--task-state", str(state)],
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
                [sys.executable, str(validator), str(delivery), "--platform", "官网/网页", "--task-state", str(state)],
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
            state = self.write_task_state(
                directory,
                platform={"value": "知乎", "confirmed": True, "source": "user", "user_quote": "知乎"},
                delivery_style={"value": "回答 + HTML 预览", "confirmed": True, "source": "user", "user_quote": "回答 + HTML 预览"},
            )
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
                    "--task-state",
                    str(state),
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

    def test_xiaohongshu_copy_text_is_plain_publishable_text(self):
        source = "# 这是一条笔记\n\n**适合谁**\n\n- 新手\n\n## 标签\n\n#话题一 #话题二"
        plain = build_html.markdown_to_plain_text(source)
        self.assertNotIn("# 这是一条笔记", plain)
        self.assertNotIn("**适合谁**", plain)
        self.assertNotIn("## 标签", plain)
        self.assertIn("这是一条笔记", plain)
        self.assertIn("适合谁", plain)
        self.assertIn("#话题一 #话题二", plain)

    def test_generic_article_tables_wrap_instead_of_horizontal_scroll(self):
        self.assertIn("table-layout:fixed", build_html.HTML_TEMPLATE)
        self.assertIn("overflow-wrap:anywhere", build_html.HTML_TEMPLATE)
        self.assertNotIn(".article table{display:block;overflow-x:auto;}", build_html.HTML_TEMPLATE)

    def test_backup_gzh_preview_template_writes_rich_and_plain_clipboard(self):
        template = (ROOT / "assets/gzh-design/assets/preview-template.html").read_text(encoding="utf-8")
        self.assertIn("ClipboardItem", template)
        self.assertIn("'text/html'", template)
        self.assertIn("'text/plain'", template)

    def test_component_subheading_number_resets_per_chapter(self):
        markdown = """# 标题

## 第一章

### 第一个点

### 第二个点

## 第二章

### 新章节第一点
"""
        calls = []
        original = build_gzh.component_subheading

        def spy(theme_key, components, text, number):
            calls.append((text, number))
            return original(theme_key, components, text, number)

        with mock.patch.object(build_gzh, "component_subheading", side_effect=spy):
            build_gzh.build_component_section(markdown, "标题", "graphite-minimal")

        self.assertEqual(calls, [("第一个点", 1), ("第二个点", 2), ("新章节第一点", 1)])


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

    def test_lint_warns_on_reader_facing_recreation_disclaimer(self):
        article = """# 软考报名要求

正文。

本文为二创整理，具体政策以官方最新通知为准。
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "article.md"
            path.write_text(article, encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["lint_article.py", str(path)]):
                with contextlib.redirect_stdout(output):
                    code = lint_article.main()
        self.assertEqual(code, 0)
        self.assertIn("二创", output.getvalue())

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
    LONG_PROSE_QUOTE_MD = """# AI 项目经理

> 学长说：这五项不需要你成为算法专家。需要的是你知道大模型能干什么、不能干什么、干起来要多久要多少钱。这个判断力，才是懂技术边界的真正含义。

## 第一部分：先判断边界

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

    def test_long_prose_quotes_are_left_aligned_not_centered(self):
        for theme in build_gzh.THEMES:
            with self.subTest(theme=theme):
                rendered = build_gzh.build_component_section(self.LONG_PROSE_QUOTE_MD, "AI 项目经理", theme)
                self.assertIn('data-balanced="prose-quote"', rendered)
                quote = re.search(r'<section data-balanced="prose-quote".*?</section>', rendered, re.S)
                self.assertIsNotNone(quote)
                self.assertIn("text-align:left", quote.group(0))
                self.assertNotIn("text-align:center", quote.group(0))

    def test_long_centered_emphasis_is_repaired_across_themes(self):
        sample = (
            '<p style="font-size:15px;margin:0 0 24px;text-align:center;color:#DC2626;'
            'font-weight:700;letter-spacing:1px;border-top:1px solid #FEE2E2;'
            'border-bottom:1px solid #FEE2E2;padding:14px 10px;">'
            '<span leaf="">报名截止 ≠ 缴费截止，但缴费截止才是真截止</span></p>'
        )
        repaired = build_gzh.repair_centered_text_orphans(sample)
        self.assertIn('data-balanced="center-text"', repaired)
        self.assertIn("text-align:left", repaired)
        self.assertNotIn("text-align:center", repaired)
        self.assertIn("overflow-wrap:anywhere", repaired)

    def test_short_centered_emphasis_can_stay_centered(self):
        sample = (
            '<p style="font-size:15px;text-align:center;font-weight:700;">'
            '<span leaf="">真正重要</span></p>'
        )
        repaired = build_gzh.repair_centered_text_orphans(sample)
        self.assertIn("text-align:center", repaired)
        self.assertNotIn('data-balanced="center-text"', repaired)

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
