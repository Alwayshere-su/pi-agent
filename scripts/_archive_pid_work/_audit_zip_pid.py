# -*- coding: utf-8 -*-
"""验证 zip 内 papers.json 对 gap_report 40 个 p# 的覆盖。"""
import zipfile
import io
import re
import json

z = zipfile.ZipFile('GOAI_初赛_Prospector.zip')
data = json.loads(z.read('submission_initial/evidence/mof/papers.json').decode('utf-8', errors='ignore'))

pid_map = {}
for k, v in data.items():
    m = re.match(r'p(\d+)$', k)
    if m and isinstance(v, dict):
        pid = m.group(1)
        doi = v.get('doi', '') if isinstance(v.get('doi'), str) else ''
        if not doi:
            doi = re.search(r'10\.\d{4,}[^\s"\'\\]*', json.dumps(v, ensure_ascii=False))
            doi = doi.group(0) if doi else ''
        pid_map[pid] = {'title': v.get('title', '')[:90], 'doi': doi}

print('papers.json 中 p# 条目数:', len(pid_map))
print('p# 范围: p%s - p%s' % (min(pid_map, key=int), max(pid_map, key=int)))
print('含 DOI 的条目:', sum(1 for v in pid_map.values() if v['doi']))

g = io.open('workspace/outputs/literature_survey/gap_report.md', encoding='utf-8').read()
gpids = sorted(set(re.findall(r'\bp(\d+)\b', g)), key=int)
found = [p for p in gpids if p in pid_map]
missing = [p for p in gpids if p not in pid_map]
print()
print('=== gap_report 40 个 p# 覆盖: %d/%d ===' % (len(found), len(gpids)))
print('仍缺失:', missing)

none17 = ['20', '50', '52', '54', '55', '60', '116', '117', '118', '128', '129', '139', '178', '182', '185', '188', '191', '224']
print()
print('=== 之前"完全无线索"的 18 个 p# 在 zip 中的情况 ===')
for p in none17:
    if p in pid_map:
        info = pid_map[p]
        print('  p%s: 已找到 | %s | DOI: %s' % (p, info['title'][:55], info['doi'][:45] or '(无DOI字段)'))
    else:
        print('  p%s: 仍缺失' % p)
