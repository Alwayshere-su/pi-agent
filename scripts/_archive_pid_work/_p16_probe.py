# -*- coding: utf-8 -*-
"""核验 p16 两个备选 DOI + 挖 memory 中 p16/p139 的体系/年份线索。"""
import io
import re
import glob
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'User-Agent': 'PiAgent-verify/1.0 (mailto:goai@example.com)'}

print('=== p16 备选核验 ===')
for doi in ['10.1021/acs.langmuir.1c01149', '10.1021/acsami.5c19588']:
    r = requests.get('https://api.crossref.org/works/' + doi, headers=HEADERS, timeout=20)
    if r.status_code == 200:
        m = r.json()['message']
        year = ''
        for k in ('published-print', 'published-online', 'issued'):
            if m.get(k, {}).get('date-parts'):
                year = m[k]['date-parts'][0][0]
                break
        print('  %s → %s（%s, %s, %s）' % (doi, (m.get('title') or [''])[0][:70],
                                          (m.get('container-title') or [''])[0][:30], year,
                                          ', '.join('%s %s' % (a.get('given', ''), a.get('family', '')) for a in m.get('author', [])[:2])))
    else:
        print('  %s → HTTP %d' % (doi, r.status_code))

print()
print('=== memory 中"水促进/水桥/湿度增强"相关段落（p16 线索）===')
for f in sorted(glob.glob(str(ROOT / 'workspace/memory/survey/*.md'))):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'.{0,50}(?:水促进|水桥|湿度.*增强|低湿度.*反升|p16).{0,70}', t):
        print(' ', f.split('\\')[-1], ':', m.group(0).replace('\n', ' ')[:110])

print()
print('=== memory 中 p139 相关（无竞争）===')
for f in sorted(glob.glob(str(ROOT / 'workspace/memory/survey/*.md'))):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'.{0,50}(?:无竞争|p139|水.*无.*影响|水不影响).{0,70}', t):
        print(' ', f.split('\\')[-1], ':', m.group(0).replace('\n', ' ')[:110])
