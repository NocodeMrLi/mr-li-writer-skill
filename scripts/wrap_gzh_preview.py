#!/usr/bin/env python3
"""把已校验的公众号正文片段（纯 <section>）包成带「复制」按钮的浏览器预览页。

用户打开预览页 → 点右上角「复制到公众号」→ 按钮选中并复制里面渲染后的富文本
（等价手动 Ctrl+A/Ctrl+C，样式全保留）→ 到公众号编辑器 Ctrl+V 粘贴即可。

按钮和 JS 只存在于预览外壳里，**不在被复制的 section 内**，所以粘进公众号的
仍是干净合规的正文，不含 <script>/<button>。校验请对原始 section 文件跑
validate_gzh_html.py（本预览页含 script/style，不参与校验）。

用法:
    wrap_gzh_preview.py <section.html> [output.html] --task-state <任务状态.json>
    默认输出 <section去扩展名>-preview.html
"""

import argparse
import html
import os
import subprocess
import sys


def require_task_state(task_state):
    if not task_state:
        print("[错误] 生成公众号复制预览前必须传入 --task-state，并通过 scripts/validate_task_intake.py 确认必问项。", file=sys.stderr)
        return 2
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_task_intake.py")
    return subprocess.call([sys.executable, checker, task_state, "--phase", "layout", "--platform", "公众号"])


def parse_args():
    parser = argparse.ArgumentParser(description="把公众号正文片段包成带复制按钮的浏览器预览页")
    parser.add_argument("section", help="已校验的公众号正文片段 HTML")
    parser.add_argument("output", nargs="?", help="输出预览页路径，默认 <section>-preview.html")
    parser.add_argument("--task-state", required=True, help="任务状态 JSON；必须已确认必问项")
    return parser.parse_args()


def main():
    args = parse_args()
    src = args.section
    intake_rc = require_task_state(args.task_state)
    if intake_rc != 0:
        sys.exit(intake_rc)
    if not os.path.isfile(src):
        print(f"✗ 找不到文件: {src}")
        sys.exit(1)

    content = open(src, encoding="utf-8").read().strip()
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    candidates = [
        os.path.join(root, "assets", "gzh-design", "assets", "preview-template.html"),
        os.path.join(root, "assets", "preview-template.html"),
    ]
    tpl_path = next((p for p in candidates if os.path.isfile(p)), candidates[0])
    tpl = open(tpl_path, encoding="utf-8").read()

    title = os.path.splitext(os.path.basename(src))[0]
    out_html = tpl.replace("{{TITLE}}", html.escape(title)).replace("<!--GZH_CONTENT-->", content)

    out = args.output if args.output else os.path.splitext(src)[0] + "-preview.html"
    open(out, "w", encoding="utf-8").write(out_html)
    print(f"✓ 已生成带「复制」按钮的预览页: {out}")
    print("  用浏览器打开它，点右上角「复制到公众号」，再去公众号编辑器 Ctrl/⌘+V 粘贴。")


if __name__ == "__main__":
    main()
