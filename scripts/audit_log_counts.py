# -*- coding: utf-8 -*-
"""audit_log_counts.py — 检索日志/入库摘要/文档声称篇数三列对齐审计（W-5 P1-2）

对 6 个主题输出：
  search_log.jsonl 行数 × paper_summaries 实际条目数 × gap_report/文档声称篇数，
三列并排，一眼看出口径差。只读，不修改任何文件。

用法：
  python scripts/audit_log_counts.py
"""
import glob
import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WS = os.path.join(ROOT, 'workspace')

THEMES = {
    'literature_survey': 'outputs/literature_survey',
    'mof_e2e_v4': 'outputs/mof_e2e_v4/literature_survey',
    'perovskite': 'outputs/perovskite/literature_survey',
    'thermoelectric': 'outputs/thermoelectric/literature_survey',
    'cathode': 'outputs/cathode/literature_survey',
    'validation': 'outputs/validation/literature_survey',
}


def count_lines(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        return sum(1 for _ in f)


def count_paper_summaries(theme: str) -> int:
    ps = os.path.join(WS, THEMES[theme], 'paper_summaries.md')
    if not os.path.exists(ps):
        return 0
    raw = open(ps, encoding='utf-8').read()
    m = re.search(r'\*\*Total papers:\*\*\s*(\d+)', raw)
    if m:
        return int(m.group(1))
    # 兜底：统计 '### N. Title:' 区块
    return len(re.findall(r'\n### \d+\. ', raw))


def claim_in_gap_report(theme: str) -> str:
    g = os.path.join(WS, THEMES[theme], 'gap_report.md')
    if not os.path.exists(g):
        return ''
    raw = open(g, encoding='utf-8').read()
    claims = []
    for m in re.finditer(r'(\d{2,})\s*(?:篇|papers?|篇次)', raw):
        claims.append(m.group(1))
    return ','.join(claims[:6]) if claims else ''


def main():
    print(f"{'主题':<18}{'search_log 行':>14}{'paper_summaries':>16}{'gap_report 声称':>20}")
    print('-' * 70)
    for theme in THEMES:
        base = os.path.join(WS, THEMES[theme])
        search_log = os.path.join(WS, 'data', 'literature_cache', theme, 'search_log.jsonl')
        if not os.path.exists(search_log):
            # 主案例（literature_survey）的日志在缓存根目录
            search_log = os.path.join(WS, 'data', 'literature_cache', 'search_log.jsonl')
        n_log = count_lines(search_log)
        n_ps = count_paper_summaries(theme)
        claim = claim_in_gap_report(theme)
        print(f'{theme:<18}{n_log:>14}{n_ps:>16}{claim:>20}')


if __name__ == '__main__':
    main()
