#!/usr/bin/env python
"""把 PDF 各页渲染为 PNG（默认 2x 缩放 ≈ 200 DPI）。

用法:
    python pdf_to_pages.py <pdf路径> [输出目录] [--scale 2.0] [--pages 1-10,15,20]

输出目录策略（按优先级）:
    1. 显式指定 out_dir           → 用指定目录
    2. 未指定 out_dir（默认）     → <PDF文件名去扩展名>/pdf_pages/
       例如 "示例讲座.pdf"       → "示例讲座/pdf_pages/"
       这样多个讲座的截图互不干扰。

依赖:
    pip install PyMuPDF
"""
import argparse
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF 未安装。请运行: pip install PyMuPDF")


def parse_pages(pages_str, total):
    """解析 '1-10,15,20' 格式的页码字符串，返回 0-indexed 页码列表"""
    if not pages_str:
        return list(range(total))
    result = []
    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            result.extend(range(int(start) - 1, int(end)))
        else:
            result.append(int(part) - 1)
    return sorted(set(result))


def default_out_dir(pdf_path):
    """基于 PDF 文件名生成默认输出目录：<文件名>/pdf_pages/"""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    # 去掉文件名中常见的版本号后缀，如 "(1)"、" V2"、"-final"
    import re
    pdf_name = re.sub(r'\s*\(\d+\)\s*$', '', pdf_name)
    return os.path.join(pdf_name, 'pdf_pages')


def main():
    parser = argparse.ArgumentParser(description='PDF 转 PNG 页面截图')
    parser.add_argument('pdf', help='PDF 文件路径')
    parser.add_argument('out_dir', nargs='?', default=None,
                        help='输出目录（默认 <PDF文件名>/pdf_pages/）')
    parser.add_argument('--scale', type=float, default=2.0,
                        help='缩放倍数（默认 2.0 ≈ 200 DPI）')
    parser.add_argument('--pages', help='指定页码，如 "1-10,15,20"，默认全部')
    args = parser.parse_args()

    out_dir = args.out_dir if args.out_dir else default_out_dir(args.pdf)

    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(args.pdf)
    total = len(doc)
    print(f'PDF 共 {total} 页，输出到 {out_dir}/，缩放 {args.scale}x')

    page_indices = parse_pages(args.pages, total)
    for idx in page_indices:
        if idx >= total:
            print(f'⚠️ 跳过第 {idx+1} 页（超出总页数）')
            continue
        page = doc[idx]
        mat = fitz.Matrix(args.scale, args.scale)
        pix = page.get_pixmap(matrix=mat)
        out = os.path.join(out_dir, f'page_{idx+1:03d}.png')
        pix.save(out)
        sz_kb = os.path.getsize(out) // 1024
        print(f'  第 {idx+1:>3} 页 → {out}  ({sz_kb} KB)')

    doc.close()
    print(f'\n完成。共生成 {len(page_indices)} 张页面截图')
    print(f'笔记中引用时使用相对路径：{os.path.relpath(out_dir, os.path.dirname(args.pdf) or ".")}/page_X.png')


if __name__ == '__main__':
    main()
