# Mr.Li Writer

> A topic-driven Chinese long-form writing skill that researches and verifies facts, designs novel angles, writes in a humanized (anti-AI) voice, and delivers single-file HTML in 6 themes.

一个面向中文深度内容创作的 AI Skill。给它一个主题（或你的一段核心想法），它会自动完成素材提取、全网检索与事实验证、新颖角度设计、去 AI 化写作、爆款标题生成，并输出单文件排版 HTML。

## 核心特性

- **事实可验证**：关键数据 / 政策经多源交叉验证，文末附带带原始 URL 的参考资料
- **角度新颖且有据**：拒绝套路化叙事，每个非主流观点都有证据和透明推理兜底，不为了新奇编证据
- **去 AI 化**：内置中文 AI 腔黑名单 + AI 味自评打分，专治"赋能 / 综上所述 / 结论前置 / 数据轰炸开头 / 结构高度规整"
- **干净无广告（双红线）**：屏蔽品牌词、公司名、产品名，也屏蔽素材里夹带的个人 IP / 博主名，适合直接对外发布
- **6 套排版主题**：黑白金极简 / 商务深蓝 / 暖色杂志 / 清新绿 / 水墨学者 / 卡片现代
- **迭代式创作**：大纲确认 → 正文确认 → 排版确认，每步用交互弹窗，不一步到位
- **用户想法落地**：你抛出的核心想法（含天马行空的推演）照单全收，AI 负责搜证，可支撑的放大、无依据的诚实标注

## 目录结构

```
mr-li-writer/
├── SKILL.md                    # 工作流编排（触发条件 + 7 步流程）
├── scripts/
│   ├── extract_seed.py         # 种子文档提取：docx 文字 + 图片 OCR，自动去人名
│   └── build_html.py           # 零依赖 Markdown→单文件 HTML（一键复制/下载，6 主题）
├── references/
│   ├── research-protocol.md    # 检索与事实验证、素材适配自分析、去个人 IP、文末引用规范
│   ├── writing-rules.md        # 深度写作、开头铁律、结构反套路、情感与声音、新颖角度
│   ├── humanize-rules.md       # 去 AI 化写作规则 + AI 味自评打分
│   └── title-rules.md          # 爆款标题创作规则
└── assets/themes/              # 6 套 HTML 排版主题 CSS
```

## 安装

把整个 `mr-li-writer/` 目录放到你的 Skills 目录下：

- 用户级：`~/.workbuddy/skills/mr-li-writer/`
- 项目级：`.workbuddy/skills/mr-li-writer/`

放入后，在对话中输入 `/mr-li-writer 你的主题` 即可调用。

## 使用

直接给它一个主题，例如：

```
/mr-li-writer 小白如何从 0 开始学习 AI？
```

技能会依次：确认需求 → 检索验证 → 设计角度并展示大纲（弹窗确认）→ 写正文 → 给爆款标题 → 选主题排版交付。

你也可以：

- 附上 docx / 图片素材，让它先提取再融合写作
- 直接抛出你的核心想法（哪怕天马行空），由它搜证落地

## 可调项

- 想换排版风格：编辑 `assets/themes/` 下任一 CSS，或在 `build_html.py` 的 `THEMES` 字典注册新主题
- 想改写作风格：直接改 `references/` 下对应规范文件

## License

MIT
