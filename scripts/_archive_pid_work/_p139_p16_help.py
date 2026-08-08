# -*- coding: utf-8 -*-
"""p139/p16 辅助核验：memory 上下文挖掘 + 新检索式 + 候选年代核对。"""
import io
import re
import time
import glob
import json
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'User-Agent': 'PiAgent-verify/1.0 (mailto:goai@example.com)'}

# 1) memory 中 p139/p16 的全部上下文
print('=== memory 中 p139 出现 ===')
for f in sorted(glob.glob(str(ROOT / 'workspace/memory/survey/*.md'))):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'p139\b[^\n]{0,90}', t):
        print(' ', f.split('\\')[-1], ':', m.group(0)[:95])
print()
print('=== memory 中 p16 出现 ===')
for f in sorted(glob.glob(str(ROOT / 'workspace/memory/survey/*.md'))):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'\bp16\b[^\n]{0,90}', t):
        print(' ', f.split('\\')[-1], ':', m.group(0)[:95])


def search(query, rows=5):
    r = requests.get('https://api.crossref.org/works',
                     params={'query': query, 'rows': rows, 'select': 'DOI,title,container-title,issued'},
                     headers=HEADERS, timeout=20)
    items = []
    for it in r.json()['message']['items']:
        title = (it.get('title') or [''])[0]
        if not title:
            continue
        year = ''
        for k in ('published-print', 'published-online', 'issued'):
            if it.get(k, {}).get('date-parts'):
                year = it[k]['date-parts'][0][0]
                break
        items.append({'doi': it['DOI'], 'title': title, 'year': year,
                      'journal': (it.get('container-title') or [''])[0]})
    return items


print()
print('=== p139 新检索（水无竞争/不影响 CO2）===')
for q in ['water vapor does not affect CO2 adsorption metal-organic framework',
          'CO2 uptake unaffected by humidity metal organic framework',
          'water co-adsorption negligible CO2 metal organic framework']:
    print('检索式:', q)
    try:
        for it in search(q, 4):
            print('  - %s | %s（%s, %s）' % (it['doi'], it['title'][:68], it['journal'][:22], it['year']))
    except Exception as e:
        print('  检索失败:', e)
    time.sleep(0.8)

print()
print('=== p16 候选年份核对 ===')
r = requests.get('https://api.crossref.org/works/10.1021/acsestengg.4c00503', headers=HEADERS, timeout=20)
if r.status_code == 200:
    m = r.json()['message']
    print('10.1021/acsestengg.4c00503 →', (m.get('title') or [''])[0][:70])
    print('  年份:', m.get('issued', {}).get('date-parts'))
    print('  期刊:', (m.get('container-title') or [''])[0])
