#!/usr/bin/env python
"""检查笔记对录音转文字的覆盖率。

输入：
    - 笔记 markdown
    - 录音转文字（可以是 .txt 或 .md；若是讯飞听见导出的"洞察"格式会自动识别）

输出：
    - 录音中每条洞察/段落在笔记中的覆盖情况
    - 未覆盖的洞察列表（由人工确认是否补充）
    - 总体覆盖率统计

用法:
    python coverage_check.py <笔记.md> <录音转文字.txt>
"""
import argparse
import re
import sys
from pathlib import Path


def extract_insights(text):
    """从录音转文字中提取"洞察"段落。

    支持两种格式：
    1. 讯飞听见 AI 智能纪要：识别"洞察"标题后的内容段落
    2. 普通文本：按空行分割段落
    """
    insights = []

    # 模式 1：讯飞听见格式（"洞察"标题 + 空行 + 内容段落）
    # 匹配 "洞察\n\n<内容>" 或 "建议 · xxx\n\n<内容>"
    pattern = re.compile(
        r'(?:洞察|建议\s*·\s*\w+|风险)\s*\n\s*\n\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\n\s*(?:洞察|建议|风险|\d{2}:\d{2}|\Z))',
        re.MULTILINE
    )
    for m in pattern.finditer(text):
        content = m.group(1).strip()
        if len(content) > 10:  # 过滤太短的
            insights.append(content)

    # 如果没匹配到洞察格式，按段落分割
    if not insights:
        paragraphs = re.split(r'\n\s*\n', text)
        for p in paragraphs:
            p = p.strip()
            # 跳过导航/广告/标题类内容
            if (len(p) > 30 and
                not any(skip in p for skip in ['切片', 'logo', 'Base64', 'shareaudio', 'iflyrec', '编组', 'Created with'])):
                insights.append(p)

    return insights


def check_coverage(insight, notes_text):
    """检查一条洞察是否在笔记中被覆盖。

    策略：提取洞察中的关键名词短语（4+ 字符），看是否在笔记中出现。
    """
    # 提取关键短语（中文 4+ 字符的连续词组、英文 4+ 字符的单词、数字）
    keywords = set()

    # 中文关键词（4-15 字符）
    cn_patterns = re.findall(r'[一-鿿]{4,15}', insight)
    keywords.update(cn_patterns)

    # 英文关键词（4+ 字符）
    en_patterns = re.findall(r'[A-Za-z][A-Za-z0-9]{3,}', insight)
    keywords.update(en_patterns)

    # 数字
    num_patterns = re.findall(r'\d+\.?\d*[%亿万亿]?', insight)
    keywords.update(num_patterns)

    if not keywords:
        return True, []  # 无法判断，默认覆盖

    # 过滤常见停用词
    stopwords = {'所示', '可以', '通过', '进行', '以及', '一个', '这种', '这种', '目前',
                 '需要', '能够', '同时', '如果', '因此', '以及', '虽然', '但是', '已经',
                 '正在', '应该', '可能', '由于', '其中', '这些', '那些', '这样', '那样',
                 '不是', '不能', '不会', '没有', '什么', '怎么', '为什么', '怎么样',
                 'them', 'their', 'this', 'that', 'with', 'from', 'have', 'been'}
    keywords = {k for k in keywords if k.lower() not in stopwords and len(k) >= 4}

    if not keywords:
        return True, []

    # 检查覆盖：至少 30% 的关键词在笔记中出现
    matched = sum(1 for kw in keywords if kw in notes_text)
    ratio = matched / len(keywords) if keywords else 1

    return ratio >= 0.3, [kw for kw in keywords if kw not in notes_text]


def main():
    parser = argparse.ArgumentParser(description='检查笔记对录音的覆盖率')
    parser.add_argument('notes', help='笔记 markdown 路径')
    parser.add_argument('transcript', help='录音转文字文件路径')
    args = parser.parse_args()

    notes_text = Path(args.notes).read_text(encoding='utf-8')
    transcript_text = Path(args.transcript).read_text(encoding='utf-8')

    insights = extract_insights(transcript_text)
    print(f'📝 笔记: {args.notes} ({len(notes_text)} 字符)')
    print(f'🎙️  录音: {args.transcript}')
    print(f'📊 提取到 {len(insights)} 条洞察/段落\n')

    if not insights:
        print('⚠️ 未识别到洞察格式，请检查录音转文字格式')
        return 1

    covered = 0
    uncovered = []
    for i, insight in enumerate(insights, 1):
        is_covered, missing_kws = check_coverage(insight, notes_text)
        if is_covered:
            covered += 1
        else:
            # 截取前 80 字符作为预览
            preview = insight[:80].replace('\n', ' ')
            uncovered.append({
                'id': i,
                'preview': preview,
                'missing_kws': missing_kws[:5],  # 只显示前 5 个缺失关键词
            })

    coverage_rate = covered / len(insights) * 100
    print(f'=== 覆盖率统计 ===')
    print(f'✅ 已覆盖: {covered} / {len(insights)} ({coverage_rate:.1f}%)')
    print(f'❌ 未覆盖: {len(uncovered)} 条\n')

    if coverage_rate >= 90:
        print(f'🎉 覆盖率优秀（≥90%）')
    elif coverage_rate >= 75:
        print(f'⚠️  覆盖率良好但可改进（75-90%），建议补充未覆盖的洞察')
    else:
        print(f'❌ 覆盖率不足（<75%），必须补充')

    if uncovered:
        print(f'\n=== 未覆盖的洞察（前 20 条） ===')
        for u in uncovered[:20]:
            print(f'\n#{u["id"]} {u["preview"]}...')
            print(f'   缺失关键词: {", ".join(u["missing_kws"])}')

    return 0 if coverage_rate >= 75 else 2


if __name__ == '__main__':
    sys.exit(main())
