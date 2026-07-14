#!/usr/bin/env python
"""从笔记中提取所有论文/学术工作引用，输出待验证清单。

不自动调用 grok-search，只输出"建议验证项"由人决定。
理由：grok-search 偶尔返回错误，自动改写笔记风险高。

提取的引用类型：
1. 引用块: `> **参考论文**：作者. *"标题"*. 期刊.`
2. 行内引用: `**论文名**（作者 et al., 年份）` 或 `**论文名** (作者 et al., 年份)`
3. 索引表行: 表格中包含论文名的行

用法:
    python verify_citations.py <笔记.md>
"""
import argparse
import re
import sys
from pathlib import Path


# 行内引用模式：**论文名**（作者 et al., 年份） 或 **论文名** (Yao et al., 2022)
# 也匹配 **SWE-Agent**（Yang et al., Princeton, NeurIPS 2024）
INLINE_PATTERN = re.compile(
    r'\*\*([^*]{2,80})\*\*\s*[（(]\s*([^)）]{3,100})\s*[)）]'
)

# 引用块模式: > **参考论文**：...
CITATION_BLOCK_PATTERN = re.compile(
    r'>\s*\*\*参考论文\*\*[：:]\s*(.+?)(?=\n\n|\n>|\Z)',
    re.DOTALL
)

# 学术工作常见关键词（用于过滤误报）
ACADEMIC_KEYWORDS = [
    'et al', 'arxiv', 'ICLR', 'NeurIPS', 'ICML', 'ACL', 'EMNLP',
    'CVPR', 'USENIX', 'ISSTA', 'FSE', 'TSE', 'TOSEM', 'TACL',
    '20', '21', '22', '23', '24', '25', '26',  # 年份
    'Princeton', 'Stanford', 'MIT', 'Berkeley', 'CMU', 'Meta',
    'Google', 'Microsoft', 'OpenAI', 'Anthropic', 'NVIDIA',
]


def is_likely_academic(text):
    """判断文本是否看起来像学术引用"""
    return any(kw.lower() in text.lower() for kw in ACADEMIC_KEYWORDS)


def extract_citations(md_text):
    """提取所有引用"""
    citations = []

    # 1. 引用块
    for m in CITATION_BLOCK_PATTERN.finditer(md_text):
        line_no = md_text[:m.start()].count('\n') + 1
        citations.append({
            'type': '引用块',
            'name': m.group(1).strip()[:80],
            'full': m.group(0).strip()[:200],
            'line': line_no,
        })

    # 2. 行内引用
    for m in INLINE_PATTERN.finditer(md_text):
        name = m.group(1).strip()
        meta = m.group(2).strip()
        # 过滤掉非学术引用（如产品配置、章节编号）
        if not is_likely_academic(meta) and not is_likely_academic(name):
            continue
        # 过滤明显的非论文名（如"步骤 1"、"核心观点"）
        if len(name) < 3 or name.startswith(('步骤', '核心', '关键', '第')):
            continue
        line_no = md_text[:m.start()].count('\n') + 1
        citations.append({
            'type': '行内',
            'name': name,
            'meta': meta,
            'full': m.group(0).strip()[:200],
            'line': line_no,
        })

    return citations


def deduplicate(citations):
    """按论文名去重，保留首次出现"""
    seen = {}
    for c in citations:
        name = c['name']
        if name not in seen:
            seen[name] = {**c, 'count': 1}
        else:
            seen[name]['count'] += 1
    return list(seen.values())


def main():
    parser = argparse.ArgumentParser(description='提取笔记中的论文引用')
    parser.add_argument('notes', help='笔记 markdown 路径')
    parser.add_argument('--output', '-o', help='输出清单到文件（默认 stdout）')
    args = parser.parse_args()

    md_text = Path(args.notes).read_text(encoding='utf-8')
    citations = extract_citations(md_text)
    unique = deduplicate(citations)

    out_lines = []
    out_lines.append(f'# 论文引用验证清单\n')
    out_lines.append(f'来源: {args.notes}')
    out_lines.append(f'共发现 {len(citations)} 处引用，去重后 {len(unique)} 个独立工作\n')
    out_lines.append('## 分级建议\n')
    out_lines.append('请人工标记每个引用的优先级：')
    out_lines.append('- **必做**: 讲者展开讲过的（核心章节、ablation、关键数据）')
    out_lines.append('- **可选**: 评估基准、简单提及')
    out_lines.append('- **不做**: 讲者未展开、纯工具/项目名\n')
    out_lines.append('## 引用清单\n')
    out_lines.append('| # | 论文/工作 | 元信息 | 类型 | 出现次数 | 首次行号 | 优先级 |')
    out_lines.append('|---|---------|--------|------|---------|---------|--------|')
    for i, c in enumerate(unique, 1):
        meta = c.get('meta', c.get('full', ''))[:60].replace('|', '\\|').replace('\n', ' ')
        name = c['name'][:40].replace('|', '\\|')
        out_lines.append(f'| {i} | {name} | {meta} | {c["type"]} | {c["count"]} | {c["line"]} | _____ |')

    output = '\n'.join(out_lines)
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f'已输出到 {args.output}')
    else:
        print(output)

    print(f'\n=== 总结 ===', file=sys.stderr)
    print(f'共 {len(unique)} 个独立学术工作需人工分级', file=sys.stderr)
    print(f'建议：必做项用 grok-search 验证（每次 ~30-60 秒）', file=sys.stderr)
    print(f'验证后按 citation-verification.md 的规则补充题外话', file=sys.stderr)


if __name__ == '__main__':
    main()
