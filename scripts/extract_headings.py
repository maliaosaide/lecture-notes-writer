#!/usr/bin/env python
"""从 MinerU content_list.json 提取所有 heading 及其页码。

content_list.json 中每条 item 都有 page_idx 字段（0-indexed），
text_level 字段标识是否为标题。本脚本提取所有标题及其页码，
用于规划笔记章节与 PDF 页的对应关系。

用法:
    python extract_headings.py <content_list.json>
"""
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description='提取章节标题和页码')
    parser.add_argument('content_list', help='MinerU content_list.json 文件路径')
    parser.add_argument('--level', type=int, help='只显示指定级别标题（如 1=h1, 2=h2）')
    args = parser.parse_args()

    try:
        with open(args.content_list, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f'读取失败: {e}')

    print(f'{"页码":>6}  {"级别":<6}  标题')
    print('-' * 80)
    count = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get('type') != 'text':
            continue
        level = item.get('text_level')
        if not level:
            continue
        if args.level and level != args.level:
            continue
        page = item.get('page_idx', -1) + 1  # 转 1-indexed
        text = item.get('text', '').strip()
        print(f'  第{page:>3}页  [H{level}]  {text}')
        count += 1

    print(f'\n共 {count} 个标题')


if __name__ == '__main__':
    main()
