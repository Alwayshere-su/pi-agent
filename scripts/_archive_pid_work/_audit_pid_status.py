# -*- coding: utf-8 -*-
"""统计 gap_report 40 个 p# 的完整状态：DOI（knowledge_graph）/ 描述（memory）/ 无线索。"""
import io
import re
import glob

g = io.open('workspace/outputs/literature_survey/gap_report.md', encoding='utf-8').read()
kg = io.open('workspace/outputs/literature_survey/knowledge_graph.md', encoding='utf-8').read()

kg_map = {}
for m in re.finditer(r'p(\d+)\s*\(?(10\.\d{4,})', kg):
    kg_map.setdefault(m.group(1), m.group(2))

mem_desc = {}
for f in sorted(glob.glob('workspace/memory/survey/*.md')):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'\bp(\d+)\b([^\n]{0,60})', t):
        pid = m.group(1)
        if pid not in mem_desc:
            mem_desc[pid] = (f.split('\\')[-1], m.group(2).strip()[:55])

gap_of = {}
sections = re.split(r'\n## ', g)[1:]
for sec in sections:
    name = sec.split('\n')[0][:45]
    for m in re.finditer(r'\bp(\d+)\b', sec):
        gap_of.setdefault(m.group(1), set()).add(name)

all_pids = sorted(set(gap_of.keys()), key=int)
rows = []
for pid in all_pids:
    doi = kg_map.get(pid, '')
    mem = mem_desc.get(pid, '')
    status = 'OK-DOI' if doi else ('PART-DESC' if mem else 'NONE')
    rows.append((pid, status, doi, mem, '; '.join(sorted(gap_of[pid]))[:70]))

print('=== %d 个 p# 完整状态 ===' % len(rows))
for pid, st, doi, mem, gs in rows:
    detail = doi if doi else (mem if mem else '(无线索)')
    print('%5s | %-9s | %s | %s' % (pid, st, detail, gs))

print()
n_ok = sum(1 for r in rows if r[1] == 'OK-DOI')
n_part = sum(1 for r in rows if r[1] == 'PART-DESC')
n_no = sum(1 for r in rows if r[1] == 'NONE')
print('=== 汇总 ===')
print('总数: %d | 有DOI: %d | 仅描述: %d | 完全无线索: %d' % (len(rows), n_ok, n_part, n_no))
