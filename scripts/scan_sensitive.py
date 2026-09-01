#!/usr/bin/env python3
"""Fail when tracked text files contain high-confidence credential material."""

import pathlib
import re
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SELF = pathlib.Path(__file__).resolve()
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("OpenAI-style key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("Tencent SecretId", re.compile(r"AKID[A-Za-z0-9]{13,40}")),
)


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    for raw in result.stdout.split(b"\0"):
        if raw:
            yield ROOT / raw.decode("utf-8", errors="surrogateescape")


def main():
    findings = []
    for path in tracked_files():
        if path.resolve() == SELF or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append("%s:%d: %s" % (path.relative_to(ROOT), line, label))

    if findings:
        print("[阻断] 待纳入版本控制的文件中发现疑似敏感凭据：")
        for finding in findings:
            print("- %s" % finding)
        return 1
    print("[通过] 待纳入版本控制的文本文件未发现高置信度敏感凭据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
