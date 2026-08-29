# Mr.Li Writer README Promo Video Design Spec

## Mode
video-shotcraft autonomous free creation. Iteration 2 (2026-08-29) on the same generator pipeline (`scripts/generate-promo-video.js`, SVG → sharp → PNG → ffmpeg), same visual system, no re-skin.

## Iteration 2 Rationale
Two independent inputs triggered this iteration:

1. Visual audit of the shipped cut found 5 failing frames (24 sampled):
   - 19.0-20.0s: `sources.log` card tucked under the hero lockup's bottom-right corner on the held final frame.
   - 17.9s: fully blank canvas at the platforms→outro cut.
   - 13.0s: anti-AI shot opens ~85% empty with an orphan gold dash.
   - Borderline sparse build-in beats at 5.3s and 15.5s; residual skeleton bars at 4.5s; scan-line stubs at 8.5-10.3s.
2. Coverage gap: commits after 2026-08-26 hardened intake and delivery gates (validate_task_intake.py, memory firewall, resume re-check, platform delivery-style confirmation, research scope). None appeared in the video.

Constraints kept: 20 s / 600 frames / 1920x1080 / silent (README copy references "20 秒"), one headline per shot, no element stacking growth.

## Product Brief
Mr.Li Writer is a Chinese writing Skill that turns ideas, titles, scattered materials, files, and references into platform-native publishable content. It is positioned as an editorial judgment and delivery system, not a prompt bundle.

## Visual Direction
Paper editorial system meets launch-film interface.

Tokens:
- Background: graphite ink `#101113`, paper `#f6f3ed`, warm paper `#e9e0d2`.
- Primary text: ink `#101113`, white `#fffdf8`.
- Accents: olive `#2f7d5c`, cinnabar `#d45546`, blue `#406d9f`, amber `#c19a5b`.
- Typography: system sans for UI and Chinese text; Georgia-style serif for stamped hero words.
- Motion: low-energy letterpress opening, accelerating card motions, stable document read moments, high-energy launch outro.

## Feature Compression
At most eight product features are made explicit to avoid overstacking:

1. Intake hard gate: standard question card, must-ask items, memory firewall, confirmation from user's own words.
2. Editorial routing: reader task first.
3. Minimum necessary innovation: innovation has cost and stop conditions.
4. Reliable current sources: seed materials are only the start; official/primary sources, information-as-of date, no fabrication.
5. Title and opening design: click contract and non-template entry.
6. Anti-AI rewrite: two direct revision passes and human voice boundaries.
7. Platform-native delivery: WeChat, Zhihu, Xiaohongshu, web/blog are distinct, and the per-platform delivery style is confirmed before writing.
8. Validated real files: title strategy, source, HTML, preview, validator.

## Feature-to-Shot Mapping (Iteration 2, 600 frames)

| # | Frames | Feature | Motion Source | Main Visual | Caption |
|---|---:|---|---|---|---|
| 1 | 0-70 | Brand and promise | brand-ink-open | Wordmark letterpress on dense paper/ink field | 写作 Skill，让想法变成可信内容 |
| 2 | 70-126 | Intake hard gate (NEW) | question-card build / stamp pop | Standard question card with four must-ask rows, 必问 seal, user-quote bubble, memory-firewall footer | 先确认，再动笔 |
| 3 | 126-186 | Editorial routing | row-embed / scan focus | Reader-task chips embed into an editor console; skeleton fully fades as YAML types | 先判断读者任务，再决定怎么写 |
| 4 | 186-242 | Minimum necessary innovation | deck-deal / step cards | Four innovation levels, first card front-loaded, only the needed level unlocks | 创新有成本，也有停止条件 |
| 5 | 242-324 | Reliable current sources | terminal-3d / verification HUD | Official source cards, date stamp 2026-08-29, no-fabrication gate; scan line removed | 资料真实可靠，种子资料只作起点 |
| 6 | 324-384 | Title and opening | paper-title-card | Click contract and template opening rejection | 标题和开头，先做编辑决策 |
| 7 | 384-454 | Anti-AI rewrite | document-typewriter-reveal | Rewrite rows enter from t=4; orphan gold dash replaced by headline underline | 去 AI 味不是伪装，是直接改写 |
| 8 | 454-518 | Platform-native delivery + style confirmation | card deal / carousel | Platform cards with per-platform delivery-style subtitles | 交付样式逐平台确认，再写原生内容 |
| 9 | 518-600 | Validated delivery and outro | outro-group-photo-launch + 14f crossfade | Platform scene dissolves while file ring flies in; ring radius 560x305, hero 680x260, zero clearance violations; caption dropped to y=940 | 从判断、核验、写作到真实交付 |

## Defect Fixes (must hold in QA)
- Outro: no file card may intersect the hero rect (620..1300 x 375..635 final, overshoot-inclusive) or sibling cards; caption clear of the ring.
- No frame between 518 and 600 may be empty: crossfade covers the shot change.
- Humanize opening frame must contain headline + at least the first rewrite row.
- Routing skeleton bars fade to zero once YAML rows land (no ghost bars).
- No scan line stubs beside the terminal in the sources shot.

## Readability Rules
- One headline per shot.
- Supporting copy uses at most one short line.
- Any detail appears as labels, stamps, files, or check marks rather than paragraphs.
- Text intended to be read uses at least 56 px effective height.
- No large blank paper fields; every scene has texture, document shapes, cards, or motion lines.

## Data Safety
All visible article examples are fictional. The reliable-current-source shot shows the protocol and date-stamping behavior, not real mutable facts that could become stale.
