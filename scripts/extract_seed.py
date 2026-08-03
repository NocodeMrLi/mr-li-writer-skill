#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_seed.py - 种子文档提取工具

从 docx / 图片文件中提取文字素材，供文章二创使用：
- .docx: 提取段落文字 + 内嵌表格 + 内嵌图片(OCR)
- 图片(png/jpg/jpeg/bmp/webp): 直接 OCR

用法:
    python extract_seed.py <文件路径> [<文件路径2> ...]

依赖:
    python-docx            (仅处理 .docx 时需要)
    rapidocr_onnxruntime   (仅处理图片时需要)

安装(请安装到受管 venv，禁止全局安装):
    python -m pip install python-docx rapidocr_onnxruntime

输出: 结构化文本到 stdout，供后续整理为 Markdown(图片中的表格/榜单信息由调用方转写为表格)。
"""
import os
import sys
import tempfile

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def check_dep(module_name, pip_name, feature):
    try:
        return __import__(module_name)
    except ImportError:
        sys.stderr.write(
            "[缺少依赖] 功能 '%s' 需要 %s。\n"
            "请安装到受管环境后再运行，例如:\n"
            "  python -m pip install %s\n" % (feature, pip_name, pip_name)
        )
        sys.exit(2)


_ocr_engine = None


def get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        mod = check_dep("rapidocr_onnxruntime", "rapidocr_onnxruntime", "图片 OCR")
        _ocr_engine = mod.RapidOCR()
    return _ocr_engine


def ocr_image(image_path):
    engine = get_ocr()
    result, _ = engine(image_path)
    if not result:
        return ""
    return "\n".join(line[1] for line in result if line and len(line) > 1)


def extract_docx(path):
    docx = check_dep("docx", "python-docx", "docx 文字提取")
    doc = docx.Document(path)
    out = []

    # 按文档顺序遍历段落与表格
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = doc.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            p = Paragraph(child, doc)
            text = p.text.strip()
            if text:
                style = (p.style.name or "") if p.style else ""
                if style.startswith("Heading"):
                    try:
                        level = int(style.split()[-1])
                    except (ValueError, IndexError):
                        level = 2
                    out.append("#" * min(level + 1, 6) + " " + text)
                else:
                    out.append(text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, doc)
            rows = []
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                rows.append("| " + " | ".join(cells) + " |")
            if rows:
                header_sep = "|" + " --- |" * len(table.rows[0].cells)
                out.append(rows[0])
                out.append(header_sep)
                out.extend(rows[1:])

    # 提取内嵌图片并 OCR
    image_parts = [
        (rid, part)
        for rid, part in doc.part.related_parts.items()
        if "image" in str(part.content_type)
    ]
    if image_parts:
        out.append("\n[以下为文档内嵌图片的 OCR 结果]")
        tmpdir = tempfile.mkdtemp(prefix="mr_li_seed_")
        for idx, (rid, part) in enumerate(image_parts, 1):
            ext = os.path.splitext(part.partname)[1] or ".png"
            img_path = os.path.join(tmpdir, "img_%d%s" % (idx, ext))
            with open(img_path, "wb") as f:
                f.write(part.blob)
            text = ocr_image(img_path)
            out.append("\n--- 图片 %d ---" % idx)
            out.append(text if text else "(未识别到文字)")

    return "\n\n".join(out)


def extract_image(path):
    text = ocr_image(path)
    return text if text else "(未识别到文字)"


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(1)

    for path in sys.argv[1:]:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            sys.stderr.write("[警告] 文件不存在，已跳过: %s\n" % path)
            continue
        ext = os.path.splitext(path)[1].lower()
        print("=" * 20)
        print("[文件] %s" % path)
        print("=" * 20)
        try:
            if ext == ".docx":
                print(extract_docx(path))
            elif ext in IMAGE_EXTS:
                print(extract_image(path))
            else:
                sys.stderr.write("[警告] 不支持的格式 %s，已跳过: %s\n" % (ext, path))
                continue
        except SystemExit:
            raise
        except Exception as e:
            sys.stderr.write("[错误] 处理失败 %s: %s\n" % (path, e))
        print()


if __name__ == "__main__":
    main()
