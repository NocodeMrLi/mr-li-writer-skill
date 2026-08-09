#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List the WeChat layout components vendored from gzh-design-skill."""

import os
import re
import sys


THEME_HEADING = re.compile(r"^#\s+公众号排版组件库\s+——\s+(.+)$", re.M)
COMPONENT_HEADING = re.compile(r"^##\s+组件\s+\d+\s+(.+)$", re.M)


def references_dir(root):
    candidates = [
        os.path.join(root, "assets", "gzh-design", "references"),
        os.path.join(root, "references"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    ref_dir = references_dir(root)
    if not os.path.isdir(ref_dir):
        print("未找到公众号组件库目录: %s" % ref_dir, file=sys.stderr)
        return 1

    files = sorted(
        name for name in os.listdir(ref_dir)
        if name.startswith("theme-")
        and name.endswith(".md")
        and name not in {"theme-index.md", "theme-generator.md"}
    )
    if not files:
        print("未找到公众号主题组件库: %s" % ref_dir, file=sys.stderr)
        return 1

    total = 0
    print("公众号组件库清单: %s" % ref_dir)
    for name in files:
        path = os.path.join(ref_dir, name)
        text = open(path, encoding="utf-8", errors="replace").read()
        theme_match = THEME_HEADING.search(text)
        theme_name = theme_match.group(1).strip() if theme_match else name
        components = COMPONENT_HEADING.findall(text)
        total += len(components)
        print("\n%s (%s): %d 个组件" % (theme_name, name, len(components)))
        for item in components:
            print("  - %s" % item.strip())

    print("\n总计: %d 套主题, %d 个组件" % (len(files), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
