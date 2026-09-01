# 宣传视频复现

本目录可以从已纳入版本控制的生成器源码，重新生成 README 使用的 20 秒无声宣传片。

## 环境

- Node.js 20.9 或更高版本
- npm
- FFmpeg（同时提供 `ffmpeg` 与 `ffprobe`）

## 构建与核验

```bash
cd promo-video
npm ci
npm audit --omit=dev --audit-level=high --registry=https://registry.npmjs.org
npm run build
npm run inspect
```

输出文件为 `out/mr-li-writer-promo-silent.mp4`。预期规格：H.264、1920×1080、30fps、约 20 秒、无声。确认画面后，可将它复制到仓库的 `assets/mr-li-writer-promo-silent.mp4`；该复制动作不会由构建脚本自动执行，避免意外覆盖已发布素材。

逐帧 PNG 和质检抽帧都位于 `out/`，该目录已被 Git 忽略。视觉设计与上次人工验收记录分别见 `design-spec.md` 和 `final-review.md`。
