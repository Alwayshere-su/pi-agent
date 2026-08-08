# -*- coding: utf-8 -*-
"""复核用户新候选 + p139 再检索（Crossref）。"""
import io
import time
import requests
from pathlib import Path

HEADERS = {'User-Agent': 'PiAgent-verify/1.0 (mailto:goai@example.com)'}


def crossref(doi):
    r = requests.get('https://api.crossref.org/works/' + doi, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None, 'HTTP %d' % r.status_code
    m = r.json()['message']
    title = (m.get('title') or [''])[0]
    year = ''
    for k in ('published-print', 'published-online', 'issued'):
        if m.get(k, {}).get('date-parts'):
            year = m[k]['date-parts'][0][0]
            break
    journal = (m.get('container-title') or [''])[0]
    return {'title': title, 'year': year, 'journal': journal}, None


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


print('=== 用户新候选复核（Crossref）===')
new_cands = {
    'p128': ['10.3389/fmats.2022.825592'],
    'p52':  ['10.1021/acs.iecr.5c04931', '10.1021/acsami.3c04079'],
    'p188': ['10.1021/acs.iecr.5b03727', '10.1021/acs.iecr.6b03887'],
    'p139': ['10.1021/acsomega.4c06322'],
}
for pid, dois in new_cands.items():
    for doi in dois:
        meta, err = crossref(doi)
        if meta:
            print('%s %s → %s（%s, %s）' % (pid, doi, meta['title'][:75], meta['journal'][:30], meta['year']))
        else:
            print('%s %s → 查询失败(%s)' % (pid, doi, err))
        time.sleep(0.5)

print()
print('=== p139 再检索：water co-adsorption CO2 MOF ===')
for q in ['water co-adsorption CO2 metal-organic framework selectivity',
          'CO2 N2 adsorption water vapor MOF no effect capacity']:
    print('检索式:', q)
    for it in search(q, 4):
        print('  - %s | %s（%s, %s）' % (it['doi'], it['title'][:70], it['journal'][:25], it['year']))
    time.sleep(0.8)
