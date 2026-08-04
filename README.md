# Mr.Li Writer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> 一项去 AI 味的中文长篇写作技能。它先判断选题值不值得写、帮你找到差异化角度，再为每篇文章设计独特的开头和标题，最终以具体、有判断、人性化的语气完成正文，并交付可直接发布的多平台版本。

> An anti-AI-tone Chinese long-form writing skill. It first evaluates whether your idea is worth writing and helps you find a distinctive angle, then designs a unique opening and title for each piece, and delivers the final draft in a concrete, opinionated, humanized voice—ready to publish across platforms.

它不是简单的"AI 代写模板"，而是把选题诊断、开头设计、标题策划和去 AI 味写作整合成一个完整的工作流。

---

## 适合谁

- 公众号、知乎、小红书、SEO 长文和个人 IP 内容创作者
- 需要把零散想法整理成完整文章的人
- 希望文章自然、有判断、不像 AI 生成稿的人
- 想节省资料检索、选题判断和标题策划时间的人
- 需要把 DOCX、PDF、图片或链接素材整理成可发布内容的人

---

## 能做什么

- **选题诊断**：先判断方向值不值得写，避免同质化，帮你找到更好的立意角度
- **开头设计**：拒绝"后台有人问""随着……发展"等模板化开头，为每篇文章设计专属入口
- **标题策划**：基于搜索意图和平台特性策划标题，不编造数据、不做标题党
- **去 AI 味写作**：文章像认真思考的人写出来的，具体、诚实、有判断，没有空洞排比和虚构经历
- **多体裁覆盖**：支持公众号深度文、知乎回答、小红书长文、行业解读、实用指南、情感生活等
- **HTML 排版交付**：一键生成单文件 HTML，内置 10 套 CSS 主题，自动匹配文章气质

---

## 安装

将整个目录放入 Codex 可发现的 skills 目录：

```bash
cp -r mr-li-writer-skill-main ~/.codex/skills/mr-li-writer/
```

项目内使用时，也可以放在项目的 `skills` 目录中。

---

## 快速开始

```text
使用 $mr-li-writer，我想写"[你的主题]"，帮我判断这个方向值不值得写，再给我更好的立意。
```

---

## 使用示例

### 从一个模糊想法开始

```text
使用 $mr-li-writer，我想写"AI 会不会取代写作"，先帮我判断这个方向值不值得写，再给我更好的立意。
```

### 写公众号深度文

```text
使用 $mr-li-writer，写一篇公众号文章，主题是"为什么很多人越努力越焦虑"。
要求：先做选题诊断，设计一个不套模板的开头，标题要适合公众号推送，正文去 AI 味、有判断、有记忆点，最后生成 HTML。
```

### 写知乎回答

```text
使用 $mr-li-writer，写一篇知乎回答：如何判断一个证书是否值得考？
目标读者：职场新人。
要求：开头要有代入感不要模板化，有检索、有反方、有选择标准，标题不要标题党。
```

### 写情感生活类文章

```text
使用 $mr-li-writer，写一篇"夫妻之间的保鲜剂"。
要求：开头用真实生活场景切入不要套话，正文不要大篇幅数据和专家，重点写具体场景、关系判断和可执行的小动作，语气去 AI 味。
```

### 基于素材二次创作

```text
使用 $mr-li-writer，基于我提供的 DOCX 和参考链接，整理成一篇公众号文章。
要求：保留必要事实，去掉宣传腔，重新设计开头和标题，正文去 AI 味，最后生成 HTML 排版。
```

---

## 建议提供的信息

越明确，输出越贴近你的目标：

- 目标读者和发布平台
- 想解决的问题或希望读者采取的行动
- 已有的核心观点、素材文件或参考链接
- 希望的文章气质：稳妥清晰、观点锋利、故事感更强、平台传播、高完成度深度
- 对开头风格的偏好（如直接、场景感、判断感）
- 标题的使用场景（如 SEO 搜索、社交分发、公众号推送）
- 是否允许出现品牌、公司、产品和人物名称
- 是否需要 Markdown、平台改写、SEO 元数据或单文件 HTML

---

## HTML 排版主题

| 主题 | 适合内容 |
|---|---|
| `minimal-gold` | 公众号深度文、通用长文、稳重观点 |
| `business-blue` | 政策解读、行业分析、数据报告 |
| `magazine-warm` | 故事、人物、案例和长阅读 |
| `fresh-green` | 小红书、知乎轻阅读、生活和成长类 |
| `ink-scholar` | 知乎深度、文化、教育、思辨类 |
| `card-modern` | 产品文、小红书卡片感内容、轻量清单 |
| `editorial-red` | 评论、争议观点、社会议题和主张型文章 |
| `calm-cyan` | 科技、AI、工具、效率和方法论 |
| `note-paper` | 实用指南、步骤、清单、避坑和复盘 |
| `mono-lab` | 产品分析、技术说明、极简报告 |

---

## 脚本说明

### 素材提取

```bash
python3 scripts/extract_seed.py <file.docx|file.pdf|image.png>
python3 scripts/extract_seed.py <file.docx> --redact-term "需要隐藏的词"
```

依赖：`pip install python-docx pypdf rapidocr_onnxruntime`

### 正文质量检查

交付前自动检查：模板化表达、同质化开头、虚构第一人称、证据密度是否匹配文章类型、是否缺少引用来源等。

```bash
python3 scripts/lint_article.py <article.md> --genre relationship-life --evidence-density low --impact-check
python3 scripts/lint_article.py <article.md> --genre policy-industry --evidence-density high --require-sources --impact-check
```

### 生成 HTML

```bash
python3 scripts/build_html.py <article.md> --list-themes
python3 scripts/build_html.py <article.md> -o article.html --title "文章标题" --mode opinion-analysis --platform 公众号
python3 scripts/build_html.py <article.md> -t note-paper -o article.html --title "文章标题"
python3 scripts/build_html.py <article.md> -t random -o article.html --title "文章标题"
```

---

## 目录结构

```text
mr-li-writer-skill-main/
├── README.md
├── LICENSE
├── agents/
├── scripts/
│   ├── extract_seed.py
│   ├── lint_article.py
│   └── build_html.py
└── assets/
    └── themes/          # 10 套 CSS 排版主题
```

---

## License

[MIT](LICENSE) © 2026 NocodeMrLi
