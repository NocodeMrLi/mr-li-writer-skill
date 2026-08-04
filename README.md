# Mr.Li Writer

Mr.Li Writer 是一个面向中文内容创作的 Agent Skill，用来把一个标题、核心想法、参考资料或模糊灵感，转化为一篇更值得写、更有判断、更自然、更适合平台发布的文章。

它不是简单的“AI 代写模板”。它会先判断选题是否值得写，再做检索、立意升级、体裁识别、证据密度控制、正文写作、去 AI 味编辑、SEO 标题策划和 HTML 排版交付。

## 适合谁

- 公众号、知乎、小红书、SEO 长文和个人 IP 内容创作者
- 需要把零散想法整理成完整文章的人
- 希望文章自然、有判断、不像 AI 生成稿的人
- 想节省资料检索、选题判断和标题策划时间的人
- 需要把 DOCX、PDF、图片或链接素材整理成可发布内容的人

## 核心能力

### 1. 选题诊断与立意升级

用户可以只提供一个标题、一句话想法或一些参考资料。Skill 会先做两轮检索判断：

1. 竞争语境扫描：看市面上已有内容、常见标题、主流观点和重复风险。
2. 差异化校准：换人群、场景、时间尺度、反方问题和关键词，寻找更好的切口。

如果原方向不值得写，Skill 会主动纠偏，给出更清楚、更有新意、更能兑现的方向。用户坚持原方向时，也会通过缩小范围、降低结论强度和补充边界来优化。

### 2. 体裁、结构和证据密度控制

不同文章不应该套同一种结构。Skill 会先识别文章体裁，再决定结构和证据密度。

例如：

- 政策、行业、金融、医疗、法律类文章需要高证据密度和可靠来源。
- 工具、职场、教育、产品类文章需要数据、案例、反方和执行建议搭配。
- 情感、关系、生活、故事、随笔类文章默认低证据或极低证据，重点是场景、动作、心理和克制判断。

这可以避免所有文章都变成“数据/专家 + 三点原因 + 三点建议”的报告腔。

### 3. 高完成度增强

重要平台文章会进一步做：

- 主题升维：把表层问题推进到更有价值的一层，但不拔高成口号。
- 记忆点设计：让读者带走一句判断、一个画面、一个场景或一个可转述表达。
- 开头结尾专项打磨：避免机械导入和机械总结。
- 反平庸检查：检查文章是否只是正确但普通。
- 审美编辑：让文章更清楚、更有质感，但不文学化。

边界很明确：高完成度不等于文学化。文章必须清楚、好读、可转述，普通目标读者愿意看。

### 4. 去 AI 味写作

Skill 会避免：

- 模板化开头和总结
- 空洞大词和机械排比
- 虚构第一人称经历、采访和数据
- 所有段落都使用相同论证结构
- 为了显得专业而强塞数据、报告和专家
- 为了显得高级而过度文学化、散文化和抽象化

目标不是“骗过检测器”，而是让文章像一个认真思考的人写出来：具体、诚实、有边界、有判断。

### 5. SEO 与内容运营标题策划

标题不会直接批量生成。Skill 会先分析：

- 主搜索词和次级搜索词
- 搜索意图和用户阶段
- 内容承诺和平台限制
- 标题能否被正文兑现
- 搜索标题、正文 H1、社交分发标题和 Meta Description 是否需要区分

标题不编造搜索量、排名概率、保证结果或无法兑现的承诺。

### 6. 单文件 HTML 排版

Skill 自带 Markdown 到单文件 HTML 渲染器，支持复制正文、下载 HTML 和多套本地 CSS 主题。

默认使用 `auto` 主题选择：根据文章模式、发布平台、标题和正文关键词匹配候选主题，再随机选择一个。这样每次交付不固定为同一种视觉，但仍尽量匹配文章气质。

内置主题：

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

## 安装

将整个目录放入 Codex 可发现的 skills 目录，例如：

```text
~/.codex/skills/mr-li-writer/
```

项目内使用时，也可以放在项目的 skills 目录中。

## 使用示例

### 从一个模糊想法开始

```text
使用 $mr-li-writer，我想写“AI 会不会取代写作”，先帮我判断这个方向值不值得写，再给我更好的立意。
```

### 写公众号深度文

```text
使用 $mr-li-writer，写一篇公众号文章，主题是“为什么很多人越努力越焦虑”。
要求：先做选题诊断和检索，文章要自然、有判断、有记忆点，不要 AI 腔，最后生成 HTML。
```

### 写知乎回答

```text
使用 $mr-li-writer，写一篇知乎回答：如何判断一个证书是否值得考？
目标读者：职场新人。
要求：有检索、有反方、有选择标准，不要标题党。
```

### 写情感生活类文章

```text
使用 $mr-li-writer，写一篇“夫妻之间的保鲜剂”。
要求：不要大篇幅数据和专家，重点写具体生活场景、关系判断和可执行的小动作。
```

### 基于素材二次创作

```text
使用 $mr-li-writer，基于我提供的 DOCX 和参考链接，整理成一篇公众号文章。
要求：保留必要事实，去掉宣传腔，重新设计标题和 HTML 排版。
```

## 建议提供的信息

越明确，输出越贴近你的目标：

- 目标读者和发布平台
- 想解决的问题或希望读者采取的行动
- 已有的核心观点、素材文件或参考链接
- 希望的文章气质：稳妥清晰、观点锋利、故事感更强、平台传播、高完成度深度
- 是否允许出现品牌、公司、产品和人物名称
- 是否需要 Markdown、平台改写、SEO 元数据或单文件 HTML

信息不足时，Skill 会使用合理默认值并标注假设，不会停在空泛提问。

## 工作流程

1. 选题诊断与立意升级
2. 建立内容 brief
3. 识别体裁、结构和证据密度
4. 高完成度增强
5. 提取和整理素材
6. 研究与证据整理
7. 设计观点和大纲
8. 撰写和自检正文
9. SEO 与内容运营标题策划
10. 交付 Markdown、平台版本或单文件 HTML

## 目录结构

```text
SKILL.md
agents/
  openai.yaml
references/
  ideation-protocol.md
  genre-structure-protocol.md
  high-impact-writing-protocol.md
  humanize-rules.md
  research-protocol.md
  title-rules.md
  writing-rules.md
scripts/
  build_html.py
  extract_seed.py
  lint_article.py
assets/themes/
  business-blue.css
  calm-cyan.css
  card-modern.css
  editorial-red.css
  fresh-green.css
  ink-scholar.css
  magazine-warm.css
  minimal-gold.css
  mono-lab.css
  note-paper.css
```

## 脚本说明

### 提取素材

```bash
python3 scripts/extract_seed.py <file.docx|file.pdf|image.png>
python3 scripts/extract_seed.py <file.docx> --redact-term "需要隐藏的词"
```

素材提取按文件类型可能需要安装依赖：

```bash
python3 -m pip install python-docx pypdf rapidocr_onnxruntime
```

`DOCX`、可提取文本的 `PDF` 和常见图片格式可用；扫描版 PDF 需要 OCR 能力支持。

### 检查正文

```bash
python3 scripts/lint_article.py <article.md> --genre relationship-life --evidence-density low --impact-check
python3 scripts/lint_article.py <article.md> --genre policy-industry --evidence-density high --require-sources --impact-check
```

`lint_article.py` 会检查：

- 常见 AI 腔和模板化表达
- 虚构第一人称经历风险
- 低证据文章中数据、研究和专家话术是否过多
- 高证据文章是否缺少参考资料和 URL
- 高完成度增强是否走向过度文学化、抽象化或缺少记忆点

在 skill 工作流里，检查结果不是最终交付给用户的待办清单；它们用于交付前自动修正。发现明显 AI 味时，应直接重写并复检，直到没有明显 AI 味再交付。

### 生成 HTML

```bash
python3 scripts/build_html.py <article.md> --list-themes
python3 scripts/build_html.py <article.md> -o article.html --title "文章标题" --mode opinion-analysis --platform 公众号
python3 scripts/build_html.py <article.md> -t note-paper -o article.html --title "文章标题"
python3 scripts/build_html.py <article.md> -t random -o article.html --title "文章标题"
```

`build_html.py` 只使用 Python 标准库，生成单文件 HTML，适合本地预览、归档或继续编辑。

## 设计边界

- 不伪造事实、经历、采访、数据和来源。
- 不把搜索结果数量、关键词热度或标题常见程度伪装成真实搜索量。
- 不为了 SEO 牺牲自然表达。
- 不为了“高完成度”把平台文章写成普通人不愿意看的文学作品。
- 不默认删除品牌、公司、人物和产品名；是否脱敏由任务模式决定。
- 不用低质量资料硬撑刺激观点；资料不足时降低结论强度或换角度。

## License

MIT
