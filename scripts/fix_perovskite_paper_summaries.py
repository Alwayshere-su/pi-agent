# -*- coding: utf-8 -*-
"""fix_perovskite_paper_summaries.py — 重建 perovskite paper_summaries.md（W-5 P1-2）

现状（已核实）：文件 71 个条目均以被截断的 Python dict 原文（`### N. {'title': ...}`）
呈现，评审无法直接阅读。完整数据存在于
`workspace/data/literature_cache/perovskite/papers_merged.json`（71 条，键 p1..p71，
与文件 `**ID:**` 顺序完全一致）。

本脚本以 papers_merged.json 为唯一数据源重建规范 markdown（零虚构）：
  ### N. Title: <title>
  **ID:** `pN`
  **Authors:** <authors>（若存在）
  **DOI:** <doi>（若存在）
  **Abstract:** <abstract，保留前 800 字符>

用法：
  python scripts/fix_perovskite_paper_summaries.py            # dry-run
  python scripts/fix_perovskite_paper_summaries.py --apply    # 写回
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PATH = os.path.join(ROOT, 'workspace', 'outputs', 'perovskite', 'literature_survey',
                    'paper_summaries.md')
SRC = os.path.join(ROOT, 'workspace', 'data', 'literature_cache', 'perovskite',
                   'papers_merged.json')


def main():
    dry = '--apply' not in sys.argv
    data = json.load(open(SRC, encoding='utf-8'))
    keys = list(data.keys())
    out = []
    out.append('# Literature Survey — Paper Summaries')
    out.append('')
    out.append(f'**Total papers:** {len(keys)}')
    out.append('**Generated:** 2026-08-10（条目数据源：`papers_merged.json`，'
               '2026-08-16 由 fix_perovskite_paper_summaries.py 重建清洗）')
    out.append('')
    out.append('---')
    out.append('')
    out.append('**Sources:** arxiv + semantic_scholar 混合（DOI 见各条目）')
    out.append('')
    out.append('---')
    out.append('')
    for i, k in enumerate(keys, 1):
        it = data[k]
        title = str(it.get('title', '')).strip()
        authors = str(it.get('authors', '')).strip()
        abstract = str(it.get('abstract', '')).strip()
        doi = str(it.get('doi', '')).strip()
        out.append(f'### {i}. Title: {title}')
        out.append(f'**ID:** `{k}`')
        if authors and authors != 'N/A':
            out.append(f'**Authors:** {authors}')
        if doi and doi != 'N/A':
            out.append(f'**DOI:** {doi}')
        if abstract:
            ab = abstract[:800] + ('…' if len(abstract) > 800 else '')
            out.append(f'**Abstract:** {ab}')
        out.append('')
    if not dry:
        open(PATH, 'w', encoding='utf-8', newline='').write('\n'.join(out))
    print(f'{PATH}')
    print(f'  重建 {len(keys)} 条（源 papers_merged.json）')
    print('  （dry-run，加 --apply 写回）' if dry else '  已写回')


if __name__ == '__main__':
    main()
