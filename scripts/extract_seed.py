#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract DOCX, text-based PDF, and image seed materials.

The script keeps names and entities by default. Use --redact-term repeatedly
when a user explicitly wants exact terms removed from the extracted output.
Scanned PDFs still require an OCR-capable PDF workflow.
"""

import argparse
import os
import re
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
            "  python3 -m pip install %s\n" % (feature, pip_name, pip_name)
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
    return "\n".join(
        str(line[1]).strip()
        for line in result
        if line and len(line) > 1 and str(line[1]).strip()
    )


def escape_table_cell(value):
    return value.strip().replace("\n", " ").replace("|", "\\|")


def heading_level(style_name):
    match = re.search(r"(?:Heading|标题)\s*([1-6])", style_name or "", re.I)
    return int(match.group(1)) if match else None


def extract_docx(path):
    docx = check_dep("docx", "python-docx", "DOCX 文字提取")
    doc = docx.Document(path)
    out = []

    from docx.table import Table
    from docx.text.paragraph import Paragraph

    # Preserve paragraph/table order from the document body.
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, doc)
            text = paragraph.text.strip()
            if not text:
                continue
            level = heading_level(paragraph.style.name if paragraph.style else "")
            out.append("#" * (level or 0) + (" " if level else "") + text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, doc)
            rows = []
            for row in table.rows:
                cells = [escape_table_cell(cell.text) for cell in row.cells]
                rows.append("| " + " | ".join(cells) + " |")
            if rows and table.rows[0].cells:
                separator = "|" + " --- |" * len(table.rows[0].cells)
                out.extend([rows[0], separator, *rows[1:]])

    image_parts = [
        part
        for part in doc.part.related_parts.values()
        if "image" in str(part.content_type)
    ]
    if image_parts:
        out.append("\n[以下为文档内嵌图片的 OCR 结果，请人工核验]")
        with tempfile.TemporaryDirectory(prefix="mr_li_seed_") as tmpdir:
            for index, part in enumerate(image_parts, 1):
                ext = os.path.splitext(str(part.partname))[1] or ".png"
                image_path = os.path.join(tmpdir, "img_%d%s" % (index, ext))
                with open(image_path, "wb") as handle:
                    handle.write(part.blob)
                try:
                    text = ocr_image(image_path)
                except SystemExit as exc:
                    if int(exc.code or 0) == 2:
                        out.append("\n[图片 OCR 已跳过：缺少 OCR 依赖；上方 DOCX 文字已保留。]")
                        break
                    raise
                out.append("\n--- 图片 %d ---" % index)
                out.append(text if text else "(未识别到文字)")

    return "\n\n".join(out)


def extract_pdf(path):
    pypdf = check_dep("pypdf", "pypdf", "PDF 文字提取")
    reader = pypdf.PdfReader(path)
    pages = []
    for index, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        pages.append("### PDF 第 %d 页\n%s" % (index, text or "(未提取到文字，可能是扫描版)"))
    return "\n\n".join(pages)


def extract_image(path):
    text = ocr_image(path)
    return text if text else "(未识别到文字)"


def apply_redactions(text, terms):
    for term in terms:
        if term:
            text = text.replace(term, "[已按要求脱敏]")
    return text


def parse_args():
    parser = argparse.ArgumentParser(description="提取 DOCX、PDF 和图片种子素材")
    parser.add_argument("paths", nargs="+", help="待提取的文件路径")
    parser.add_argument(
        "--redact-term",
        action="append",
        default=[],
        help="精确脱敏一个词，可重复使用；默认不自动删除人名或实体",
    )
    return parser.parse_args()


def extract_path(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return extract_docx(path)
    if ext == ".pdf":
        return extract_pdf(path)
    if ext in IMAGE_EXTS:
        return extract_image(path)
    raise ValueError("不支持的格式 %s" % ext)


def main():
    args = parse_args()
    exit_code = 0
    for raw_path in args.paths:
        path = os.path.abspath(raw_path)
        if not os.path.isfile(path):
            sys.stderr.write("[警告] 文件不存在，已跳过: %s\n" % path)
            exit_code = 1
            continue
        print("=" * 20)
        print("[文件] %s" % path)
        print("=" * 20)
        try:
            text = apply_redactions(extract_path(path), args.redact_term)
            print(text)
        except SystemExit:
            raise
        except Exception as exc:
            sys.stderr.write("[错误] 处理失败 %s: %s\n" % (path, exc))
            exit_code = 1
        print()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
