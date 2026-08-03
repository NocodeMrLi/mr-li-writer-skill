# Mr.Li Writer

面向中文内容创作的研究、策划、写作、SEO 标题运营和单文件 HTML 排版 skill。

## 能做什么

- 根据主题、用户想法或种子素材建立内容 brief
- 按搜索意图和内容目标组织检索
- 区分事实、推理、假设和观点
- 以去 AI 味为最高优先级完成正文
- 用 SEO 与内容运营方法设计标题，不直接凭感觉批量生成
- 生成 SEO Title、H1、社交分发标题、Meta Description 和文章摘要
- 输出 Markdown、平台适配版本和单文件 HTML

## 安装

将整个目录放入 Codex 可发现的 skills 目录，例如：

```text
~/.codex/skills/mr-li-writer/
```

项目内使用时，也可以放在项目的 skills 目录中。

## 使用

直接说明目标即可，例如：

```text
使用 $mr-li-writer，写一篇给职场新人看的“如何判断一个证书是否值得考”的知乎文章。
目标：自然、有观点、不要 AI 腔；需要检索、SEO 标题策略和单文件 HTML。
```

建议同时提供：

- 目标读者和发布平台
- 想解决的问题或希望读者采取的行动
- 已有的核心观点、素材文件或参考链接
- 是否允许出现品牌、公司、产品和人物名称

## 目录

```text
SKILL.md
agents/openai.yaml
references/
  humanize-rules.md
  research-protocol.md
  title-rules.md
  writing-rules.md
scripts/
  build_html.py
  extract_seed.py
  lint_article.py
assets/themes/
```

## 脚本

```bash
python scripts/extract_seed.py <file.docx|file.pdf|image.png>
python scripts/extract_seed.py <file.docx> --redact-term "需要隐藏的词"
python scripts/lint_article.py <article.md> --require-sources
python scripts/build_html.py <article.md> --list-themes
python scripts/build_html.py <article.md> -t minimal-gold -o article.html --title "文章标题"
```

素材提取按文件类型按需安装依赖：

```bash
python -m pip install python-docx pypdf rapidocr_onnxruntime
```

`build_html.py` 和 `lint_article.py` 只使用 Python 标准库。

## 设计取向

标题先做搜索意图、用户阶段、内容承诺和平台适配分析，再生成候选并相对评分。SEO 不能牺牲自然表达，排版也保持克制、清楚和适合长时间阅读。
