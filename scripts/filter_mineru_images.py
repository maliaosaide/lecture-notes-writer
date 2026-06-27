#!/usr/bin/env python
"""评估 MinerU 提取的散图质量，标记图标/装饰图。

MinerU 会把 PDF 中所有图片元素提取到 images/，但其中很多是
图标、Logo、装饰图，没有信息量。本脚本通过像素尺寸和文件大小筛选。

用法:
    python filter_mineru_images.py <images目录> [--threshold 500]

判定标准（经验值）:
- 像素 < 300x300  → 几乎肯定是图标
- 文件 < 5KB      → 几乎肯定是图标
- 像素 300-500    → 可疑，需人工确认
- 像素 > 500      → 一般是有信息量的图
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow 未安装。请运行: pip install Pillow")


def main():
    parser = argparse.ArgumentParser(description='筛选 MinerU 散图')
    parser.add_argument('images_dir', help='MinerU images 目录路径')
    parser.add_argument('--threshold', type=int, default=500,
                        help='像素阈值，小于此值视为可疑（默认 500）')
    parser.add_argument('--size-kb', type=int, default=5,
                        help='文件大小阈值 KB，小于此值视为可疑（默认 5KB）')
    args = parser.parse_args()

    if not os.path.isdir(args.images_dir):
        sys.exit(f'目录不存在: {args.images_dir}')

    files = sorted([f for f in os.listdir(args.images_dir)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f'共 {len(files)} 张图片\n')

    suspicious, ok = [], []
    for f in files:
        path = os.path.join(args.images_dir, f)
        sz_kb = os.path.getsize(path) // 1024
        try:
            with Image.open(path) as im:
                w, h = im.size
                # 颜色丰富度
                colors = im.convert('RGB').getcolors(maxcolors=1000000)
                color_count = len(colors) if colors else 999999
        except Exception as e:
            print(f'⚠️ 无法读取 {f}: {e}')
            continue

        min_dim = min(w, h)
        flag = ''
        if min_dim < args.threshold or sz_kb < args.size_kb:
            flag = '⚠️ 疑似图标'
            suspicious.append((f, w, h, sz_kb, color_count))
        else:
            flag = '✓'
            ok.append((f, w, h, sz_kb, color_count))

        print(f'  {w:>5}x{h:<5}  {sz_kb:>5}KB  colors={color_count:>6}  {flag}  {f[:20]}')

    print(f'\n=== 汇总 ===')
    print(f'✓ 有信息量: {len(ok)} 张')
    print(f'⚠️ 疑似图标: {len(suspicious)} 张')
    print(f'\n建议: 疑似图标的图片可考虑删除，或改用 PDF 完整页面截图替代。')


if __name__ == '__main__':
    main()
