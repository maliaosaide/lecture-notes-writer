#!/usr/bin/env python
"""讲座笔记自动化审查脚本。

检查项:
1. 主观人称残留（X 教授、他指出、他承认等）
2. 图片引用路径是否存在
3. 孤立的图片文件（在 pdf_pages/ 但笔记未引用）
4. 引用的页面截图是否真的存在于 pdf_pages/
5. 论文引用块格式（> **参考论文**：...）
6. 附录完整性（核心论文索引、关键数据速查表）
7. 数字一致性（粗略：笔记中出现的数字是否在讲稿 markdown 中存在）

用法:
    python audit_notes.py <笔记.md> [--content-list <content_list.json>] [--lecturer <讲者姓名>]

退出码:
    0 = 通过审查
    1 = 有警告（建议人工确认）
    2 = 有错误（必须修正）
"""
import argparse
import json
import re
import sys
from pathlib import Path


# 主观人称模式（默认匹配"教授/老师/讲者"等 + 常见动词）
SUBJECTIVE_PATTERNS = [
    (r'\b\w+教授\b', '出现"X 教授"称谓'),
    (r'\b\w+老师\b', '出现"X 老师"称谓'),
    (r'讲者(指出|承认|提出|强调|直言|坦承|回忆|估计|援引|判断|据此|进一步|用一个|读博|现场)', '"讲者+动词"主观表述'),
    (r'他(指出|承认|提出|强调|直言|坦承|回忆|估计|援引|判断|据此|进一步|用一个|读博|现场|早期|最后)', '"他+动词"主观表述'),
]


def check_subjective(md_text, lecturer_name=None):
    """检查主观人称残留"""
    issues = []
    patterns = list(SUBJECTIVE_PATTERNS)
    # 如果用户提供了讲者姓名，特别检查
    if lecturer_name:
        patterns.append((rf'{lecturer_name}(指出|承认|提出|强调|直言|坦承|回忆|估计|援引|判断|据此|进一步)', f'"{lecturer_name}+动词"主观表述'))

    for pattern, desc in patterns:
        for m in re.finditer(pattern, md_text):
            line_no = md_text[:m.start()].count('\n') + 1
            issues.append({
                'level': 'error',
                'category': '主观人称',
                'desc': desc,
                'match': m.group(),
                'line': line_no,
            })
    return issues


def check_image_paths(md_text, notes_path):
    """检查图片引用路径是否存在"""
    issues = []
    notes_dir = Path(notes_path).parent
    for m in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', md_text):
        img_path = m.group(1)
        line_no = md_text[:m.start()].count('\n') + 1
        full_path = notes_dir / img_path
        if not full_path.exists():
            issues.append({
                'level': 'error',
                'category': '图片路径',
                'desc': f'引用的图片不存在: {img_path}',
                'match': m.group()[:60],
                'line': line_no,
            })
    return issues


def check_orphan_images(md_text, notes_path):
    """检查 pdf_pages/ 中的孤立图片（笔记未引用）"""
    issues = []
    notes_dir = Path(notes_path).parent
    pdf_pages_dir = notes_dir / 'pdf_pages'
    if not pdf_pages_dir.is_dir():
        return issues

    referenced = set(re.findall(r'pdf_pages/(page_\d+\.png)', md_text))
    actual = set(f.name for f in pdf_pages_dir.glob('page_*.png'))
    orphans = actual - referenced
    for orphan in sorted(orphans):
        issues.append({
            'level': 'warn',
            'category': '孤立图片',
            'desc': f'pdf_pages/ 中存在但笔记未引用: {orphan}',
            'match': orphan,
            'line': '-',
        })
    return issues


def check_paper_citations(md_text):
    """检查论文引用块格式"""
    issues = []
    # 找到所有"参考论文："引导的引用块（跨行匹配）
    # 用 DOTALL 让 . 匹配换行
    citations = re.findall(r'>\s*\*\*参考论文\*\*[：:]\s*(.+?)(?=\n\n|\n>|\Z)',
                           md_text, re.DOTALL)
    for c in citations:
        c_clean = c.strip()
        # 跳过空内容（可能是模板）
        if not c_clean:
            continue
        # 检查格式：应有 *"标题"* 标记
        if '*"' not in c_clean and '"*' not in c_clean:
            issues.append({
                'level': 'warn',
                'category': '论文引用格式',
                'desc': f'引用缺标题引号: {c_clean[:60]}',
                'match': c_clean[:60],
                'line': '-',
            })
    return issues


def check_appendices(md_text):
    """检查附录完整性（模糊匹配）。

    论文索引用正则匹配：核心论文索引 / 论文索引 / 学术工作索引 / 研究索引 / 参考文献 等。
    数据速查用正则匹配：关键数据速查表 / 数据速查 / 关键数据 / 数据索引 等。
    """
    issues = []
    # 论文/学术工作索引（容忍多种命名）
    paper_patterns = [
        r'核心论文索引',
        r'论文索引',
        r'学术工作索引',
        r'学术.*索引',
        r'研究.*索引',
        r'参考文献',
        r'参考资料',
        r'References',
    ]
    if not any(re.search(p, md_text) for p in paper_patterns):
        issues.append({
            'level': 'warn',
            'category': '附录缺失',
            'desc': '缺少"核心论文索引"附录（或同义命名如"学术工作索引"/"参考文献"）',
            'match': '-',
            'line': '-',
        })
    # 数据速查表（容忍多种命名）
    data_patterns = [
        r'关键数据速查表',
        r'数据速查',
        r'关键数据',
        r'数据索引',
        r'核心数据',
        r'数据.*表',
    ]
    if not any(re.search(p, md_text) for p in data_patterns):
        issues.append({
            'level': 'warn',
            'category': '附录缺失',
            'desc': '缺少"关键数据速查表"附录（或同义命名如"数据索引"/"核心数据"）',
            'match': '-',
            'line': '-',
        })
    return issues


def check_numbers_consistency(md_text, content_list_path):
    """检查数字一致性：笔记中的关键百分比是否在讲稿中出现。

    content_list.json 包含了讲稿所有文本（含表格），从中提取所有数字。
    笔记中"独立出现的百分比"（前后非数字）若在讲稿中找不到，则警告。
    """
    if not content_list_path:
        return []
    try:
        with open(content_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []

    # 从 content_list.json 的所有 text 字段提取数字（包括表格）
    lecture_chunks = []
    for item in data:
        if isinstance(item, dict):
            text = item.get('text', '')
            if isinstance(text, str):
                lecture_chunks.append(text)
            # 表格的 cells 字段
            elif isinstance(text, list):
                lecture_chunks.extend(str(c) for c in text)
    lecture_text = ' '.join(lecture_chunks)
    lecture_numbers = set(re.findall(r'\d+\.?\d*%?', lecture_text))

    issues = []
    # 笔记中的百分比（前后非数字，避免抓到表格里的小数）
    note_percents = set(re.findall(r'(?<![\d.])\d+\.?\d*%(?!\d)', md_text))
    for p in note_percents:
        # 容忍 ±0.1 误差：笔记里写 45%，讲稿里可能是 44.67%
        try:
            p_val = float(p.rstrip('%'))
            # 检查讲稿里是否有相近数字（±5% 相对误差）
            found_close = False
            for ln in lecture_numbers:
                try:
                    ln_val = float(ln.rstrip('%'))
                    if ln_val > 0 and abs(ln_val - p_val) / max(ln_val, 1) < 0.05:
                        found_close = True
                        break
                except ValueError:
                    continue
            if not found_close:
                issues.append({
                    'level': 'warn',
                    'category': '数字一致性',
                    'desc': f'笔记中的 {p} 在讲稿中未找到相近数字（>5% 偏差）',
                    'match': p,
                    'line': '-',
                })
        except ValueError:
            continue
    return issues


def main():
    parser = argparse.ArgumentParser(description='讲座笔记自动化审查')
    parser.add_argument('notes', help='笔记 markdown 路径')
    parser.add_argument('--content-list', help='MinerU content_list.json（用于数字一致性检查）')
    parser.add_argument('--lecturer', help='讲者姓名（用于检测主观人称残留）')
    args = parser.parse_args()

    md_text = Path(args.notes).read_text(encoding='utf-8')
    all_issues = []

    print(f'🔍 审查笔记: {args.notes}\n')
    all_issues.extend(check_subjective(md_text, args.lecturer))
    all_issues.extend(check_image_paths(md_text, args.notes))
    all_issues.extend(check_orphan_images(md_text, args.notes))
    all_issues.extend(check_paper_citations(md_text))
    all_issues.extend(check_appendices(md_text))
    all_issues.extend(check_numbers_consistency(md_text, args.content_list))

    # 输出报告
    errors = [i for i in all_issues if i['level'] == 'error']
    warns = [i for i in all_issues if i['level'] == 'warn']

    if not all_issues:
        print('✅ 审查通过，未发现问题\n')
        return 0

    print(f'=== 审查结果：{len(errors)} 错误 + {len(warns)} 警告 ===\n')

    if errors:
        print('❌ 错误（必须修正）:')
        for i in errors:
            print(f'  [行{i["line"]}] {i["category"]}: {i["desc"]}')
            print(f'         匹配: {i["match"]}')
        print()

    if warns:
        print('⚠️  警告（建议人工确认）:')
        for i in warns:
            print(f'  [行{i["line"]}] {i["category"]}: {i["desc"]}')
        print()

    print(f'总结: {"❌ 必须修正" if errors else "⚠️  建议人工确认"}')
    return 2 if errors else 1


if __name__ == '__main__':
    sys.exit(main())
