<p align="center">
  <img src="./assets/readme-banner.svg" alt="Mr.Li Writer - 写作.Skill，让想法变成文章">
</p>

# Mr.Li Writer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![WeChat Layout: AGPL-3.0](https://img.shields.io/badge/WeChat%20Layout-AGPL--3.0-blue.svg)](assets/gzh-design/LICENSE)

一项去 AI 味的中文内容创作 Skill。  
从一个标题、想法或素材开始，先判断值不值得写，再生成适合公众号、知乎、小红书、官网/网页和个人博客的平台原生内容。

> It evaluates whether your idea is worth writing, upgrades the angle, then creates platform-native Chinese drafts for WeChat, Zhihu, Xiaohongshu, websites, or blogs.

它不是简单的"AI 代写模板"，也不是把一篇长文缩短后分发到所有平台，而是把选题诊断、开头设计、标题策划、平台原生写作和去 AI 味表达整合成一个完整的工作流。

---

## 适合谁

- 公众号、知乎、小红书、官网/网页、个人博客和个人 IP 内容创作者
- 需要把零散想法整理成完整文章的人
- 希望文章自然、有判断、不像 AI 生成稿的人
- 想节省资料检索、选题判断和标题策划时间的人
- 需要把 DOCX、PDF、图片或链接素材整理成可发布内容的人

---

## 能做什么

- **选题诊断**：先判断方向值不值得写，避免同质化，帮你找到更好的立意角度
- **开头设计**：拒绝"后台有人问""随着……发展"等模板化开头，为每篇文章设计专属入口
- **标题策划**：基于搜索意图和平台特性策划标题，不编造数据、不做标题党
- **平台原生写作**：公众号写成文章，知乎写成回答/专栏，小红书写成原生笔记，官网/网页写成结构化网页内容
- **去 AI 味写作**：文章像认真思考的人写出来的，具体、诚实、有判断，没有空洞排比和虚构经历
- **多体裁覆盖**：支持公众号深度文、知乎回答、小红书笔记、行业解读、实用指南、情感生活等
- **平台化交付**：公众号使用完整组件库式内联 HTML 排版，小红书使用手机笔记卡片，官网/网页和博客使用对应预览

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

### 写小红书笔记

```text
使用 $mr-li-writer，写一篇小红书笔记，主题是"新手第一次买空气炸锅怎么选"。
要求：不要写公众号长文，要像小红书原生笔记，有短标题、短段落、emoji 提示、适合谁/不适合谁、避坑清单和 6-10 个话题标签。
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
- 内容目标：普通传播、GEO、SEO、转化销售或专业报告
- 想解决的问题或希望读者采取的行动
- 已有的核心观点、素材文件或参考链接
- 希望的文章气质：稳妥清晰、观点锋利、故事感更强、平台传播、高完成度深度
- 对开头风格的偏好（如直接、场景感、判断感）
- 标题的使用场景（如搜索、社交分发、公众号推送、小红书笔记标题）
- 是否允许出现品牌、公司、产品和人物名称
- 是否需要 Markdown、平台纯文本、SEO/GEO 元数据或单文件 HTML

---

## 发布平台与内容目标

推荐把“发在哪里”和“想达成什么”分开说：

发布平台：

- 公众号
- 知乎
- 小红书
- 官网/网页
- 个人博客

内容目标：

- 普通传播
- GEO / 生成式搜索优化
- SEO / 搜索引擎优化
- 转化销售
- 专业报告

例如：“发布平台：官网/网页；内容目标：SEO”比“写一篇 SEO 平台文章”更清楚。

---

## 平台交付样式

| 发布平台 | 默认交付样式 |
|---|---|
| 公众号 | 内联 HTML 排版主题 + 复制预览页 |
| 知乎 | 问答/专栏样式 |
| 小红书 | 手机笔记卡片 / 清爽纯文本笔记 |
| 官网/网页 | 网页文章 / SEO-GEO 结构化样式 |
| 个人博客 | 博客长文样式 |

用户没有指定交付样式时会自动匹配；用户手动指定时会尊重选择。

---

## 公众号排版主题

公众号排版风格来自 `gzh-design-skill` 的 6 套主题。项目已内置主题索引、公共组件和完整主题组件库，生成的是可粘贴到公众号编辑器的内联 HTML，并会同时生成带“复制到公众号”按钮的预览页。

| 主题标识 | 中文名 | 适合内容 |
|---|---|
| `moyu-green` | 摸鱼绿 | 教程、测评、清单、工具盘点 |
| `red-white` | 红白色系 | 深度分析、观点、力量感话题 |
| `graphite-minimal` | 石墨极简风 | 设计、科技评论、专业观点 |
| `zen-whitespace` | 留白禅意风 | 随笔、极简生活、沉静表达 |
| `moyu-ticket` | 摸鱼票据风 | 工具对比、创意评测 |
| `olive-journal` | 橄榄手记 | 案例复盘、内刊手记、系统说明 |

如果用户没有指定主题，系统会先推荐适合的公众号主题；用户明确说“直接排”“不用问”时会自动匹配。

公众号主题组件库位于：

```text
assets/gzh-design/references/
```

组件库覆盖封面、目录、章节标题、正文段落、引用、提示卡、标签、列表、数据/要点卡、图片、FAQ、时间线、作者签名和结尾互动等常用公众号排版区块。正式精排时会按文章类型选择对应主题和组件组合，而不是只做颜色替换。

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
python3 scripts/lint_article.py <note.md> --platform 小红书 --mode xiaohongshu-note --genre platform-native --evidence-density low --impact-check
```

### 生成 HTML

```bash
python3 scripts/build_html.py <article.md> --list-themes
python3 scripts/build_html.py <article.md> --list-delivery-styles
python3 scripts/build_html.py <article.md> -o article.html --title "文章标题" --mode opinion-analysis --platform 公众号
python3 scripts/build_html.py <article.md> -o article.html --title "文章标题" --platform 公众号 -t red-white
python3 scripts/build_gzh_html.py <article.md> -o article_gzh.html --title "文章标题" -t moyu-green
python3 scripts/build_html.py <note.md> -o note.html --title "笔记标题" --mode xiaohongshu-note --platform 小红书
python3 scripts/build_html.py <web.md> -o web.html --title "网页标题" --platform 官网/网页 --content-goal SEO
```

公众号排版会输出两份文件：

- 干净正文片段：用于校验和手动粘贴兜底
- 复制预览页：浏览器打开后点击“复制到公众号”，再粘贴到公众号编辑器

公众号组件库检查：

```bash
python3 scripts/gzh_component_inventory.py .
python3 scripts/component_lint.py .
python3 scripts/validate_gzh_html.py article_gzh.html
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
│   ├── build_html.py
│   ├── build_gzh_html.py
│   ├── validate_gzh_html.py
│   ├── component_lint.py
│   ├── gzh_component_inventory.py
│   └── wrap_gzh_preview.py
└── assets/
    ├── readme-banner.svg
    └── gzh-design/
        ├── LICENSE
        ├── NOTICE.md
        ├── assets/
        │   └── preview-template.html
        └── references/  # gzh-design-skill 主题索引、公共组件和完整主题组件库
```

---

## License

项目原创部分采用 [MIT](LICENSE) © 2026 NocodeMrLi。

公众号排版主题与组件库来自 [gzh-design-skill](https://github.com/isjiamu/gzh-design-skill)，相关排版代码和派生部分遵循 [GNU AGPL-3.0](assets/gzh-design/LICENSE)，来源说明见 [assets/gzh-design/NOTICE.md](assets/gzh-design/NOTICE.md)。
