# -*- coding: utf-8 -*-
"""三层合并统计：zip papers.json ∪ knowledge_graph ∪ memory 对 gap_report 40 个 p# 的最终覆盖。"""
import zipfile
import io
import re
import json
import glob

# 1) zip papers.json
z = zipfile.ZipFile('GOAI_初赛_Prospector.zip')
data = json.loads(z.read('submission_initial/evidence/mof/papers.json').decode('utf-8', errors='ignore'))
zip_map = {}
for k, v in data.items():
    m = re.match(r'p(\d+)$', k)
    if m and isinstance(v, dict):
        pid = m.group(1)
        doi = v.get('doi', '') if isinstance(v.get('doi'), str) else ''
        if not doi:
            doi = re.search(r'10\.\d{4,}[^\s"\'\\]*', json.dumps(v, ensure_ascii=False))
            doi = doi.group(0) if doi else ''
        zip_map[pid] = {'title': v.get('title', '')[:80], 'doi': doi}

# 2) knowledge_graph p#->DOI
kg = io.open('workspace/outputs/literature_survey/knowledge_graph.md', encoding='utf-8').read()
kg_map = {}
for m in re.finditer(r'p(\d+)\s*\(?(10\.\d{4,})', kg):
    kg_map.setdefault(m.group(1), m.group(2))

# 3) memory 描述
mem_desc = {}
for f in sorted(glob.glob('workspace/memory/survey/*.md')):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'\bp(\d+)\b([^\n]{0,60})', t):
        if m.group(1) not in mem_desc:
            mem_desc[m.group(1)] = (f.split('\\')[-1], m.group(2).strip()[:50])

# 4) gap_report 40 个 p#
g = io.open('workspace/outputs/literature_survey/gap_report.md', encoding='utf-8').read()
gpids = sorted(set(re.findall(r'\bp(\d+)\b', g)), key=int)

print('=== 40 个 p# 最终状态（三层合并）===')
full_missing = []
for pid in gpids:
    zi = zip_map.get(pid)
    kgd = kg_map.get(pid)
    mem = mem_desc.get(pid)
    if zi and zi['doi']:
        print('  p%-4s | ZIP-DOI  %s | %s' % (pid, zi['doi'][:42], zi['title'][:50]))
    elif kgd:
        print('  p%-4s | KG-DOI   %s' % (pid, kgd))
    elif zi:
        print('  p%-4s | ZIP-无DOI %s' % (pid, zi['title'][:60]))
    elif mem:
        print('  p%-4s | MEM描述  [%s] %s' % (pid, mem[0], mem[1][:50]))
    else:
        full_missing.append(pid)
        print('  p%-4s | 完全无线索' % pid)

print()
print('=== 汇总 ===')
n_zip_doi = sum(1 for p in gpids if zip_map.get(p, {}).get('doi'))
n_kg = sum(1 for p in gpids if p in kg_map)
n_mem = sum(1 for p in gpids if p in mem_desc)
print('40 个 p# 中：ZIP 提供 DOI: %d | KG 提供 DOI: %d | MEM 提供描述: %d | 完全无线索: %d' % (
    n_zip_doi, n_kg, n_mem, len(full_missing)))
print('完全无线索列表:', full_missing)
