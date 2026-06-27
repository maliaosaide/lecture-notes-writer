#!/usr/bin/env python
"""验证笔记中插入的 PDF 页面截图与所在章节内容是否一致。

读取笔记 markdown，找出所有 pdf_pages/ 引用，对照 MinerU
content_list.json 中该页的标题，判断插入位置是否合理。

用法:
    python verify_image_consistency.py <笔记.md> <content_list.json>
"""
import argparse
import json
import re
import sys
from pathlib import Path


def extract_used_pages(md_text):
    """提取笔记中所有引用的 PDF 页码"""
    return sorted(set(int(m) for m in re.findall(r'page_(\d+)\.png', md_text)))


def find_image_context(md_text):
    """找出每张图片引用所在的最接近的章节标题（## 或 ### 行）"""
    lines = md_text.split('\n')
    current_heading = '(开头)'
    results = []
    for line in lines:
        if line.startswith('## ') or line.startswith('### '):
            current_heading = line.lstrip('#').strip()
        m = re.search(r'page_(\d+)\.png', line)
        if m:
            page = int(m.group(1))
            results.append((page, current_heading))
    return results


def build_page_headings(content_list_path):
    """构建 page_idx -> [headings] 映射"""
    with open(content_list_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    mapping = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get('type') != 'text':
            continue
        if item.get('text_level'):
            page = item.get('page_idx', -1) + 1
            mapping.setdefault(page, []).append(item.get('text', '').strip())
    return mapping


def main():
    parser = argparse.ArgumentParser(description='验证图片-内容一致性')
    parser.add_argument('notes', help='笔记 markdown 路径')
    parser.add_argument('content_list', help='MinerU content_list.json 路径')
    args = parser.parse_args()

    md_text = Path(args.notes).read_text(encoding='utf-8')
    page_headings = build_page_headings(args.content_list)
    image_contexts = find_image_context(md_text)
    used_pages = extract_used_pages(md_text)

    print(f'笔记共引用 {len(used_pages)} 张 PDF 页面截图\n')
    print(f'{"页码":>4}  {"笔记章节":<40}  PDF 该页标题')
    print('-' * 100)
    for page, heading in image_contexts:
        pdf_titles = page_headings.get(page, ['(无标题)'])
        print(f'  P{page:<3}  {heading[:38]:<40}  {" / ".join(pdf_titles)[:50]}')

    # 校验是否有重复或孤立页
    print(f'\n=== 校验 ===')
    if len(image_contexts) != len(used_pages):
        print(f'⚠️ 引用次数 {len(image_contexts)} 与唯一页数 {len(used_pages)} 不一致（可能重复）')
    else:
        print('✓ 无重复引用')
    print(f'✓ 所有页码范围: {min(used_pages)} - {max(used_pages)}')


if __name__ == '__main__':
    main()
