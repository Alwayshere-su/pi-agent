# -*- coding: utf-8 -*-
"""全面核验 15 个待补 p#：Crossref works 检索（真实学术库）+ 元数据匹配判定；p54 走 DataCite。

每个 p# 输出 Top 5 检索结果（DOI/标题/年份/期刊）+ 上下文关键词命中分 + 判定。
全部【候选，须打开原文最终确认】——机器只做存在性与主题吻合核验，不做身份拍板。
"""
import io
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'User-Agent': 'PiAgent-verify/1.0 (mailto:goai@example.com)'}

# p# -> 检索式（材料+性质+方法）
QUERIES = {
    '16':  'water vapor CO2 uptake amine functionalized MOF humidity enhancement',
    '20':  'Ni-MOF-74 CO2 adsorption capacity 8.29 synthesis condition effect',
    '52':  'CO2 capture compression energy penalty low purity flue gas impurities MOF',
    '55':  'CO2 capture energy penalty impurity gas low purity stream',
    '54':  'SBA-15 PEI amine impregnated CO2 capture direct air',
    '60':  'temperature swing adsorption TVSA MOF CO2 high purity',
    '62':  'NiCo-MOF-74 bimetallic microwave synthesis CO2 capture open metal site',
    '118': 'MOF CO2 isosteric heat Qst 25-40 kJ/mol adsorption',
    '128': 'water vapor effect MOF CO2 adsorption capacity degradation',
    '129': 'amine functionalized SBA-15 CO2 isosteric heat Qst',
    '139': 'MOF CO2 adsorption water co-adsorption no competition effect',
    '168': 'water dissociation open metal site MOF-74 hydrolysis degradation mechanism',
    '169': 'bimetallic MOF mixed metal thermodynamic preference water stability',
    '185': 'M-MOF-74 molecular simulation open metal site density CO2 adsorption',
    '188': 'temperature swing adsorption dynamic MOF process modeling',
}

CTX_KW = {
    '16':  ['water', 'amine', 'mof', 'humidity', 'co2'],
    '20':  ['ni', 'mof', 'co2', 'adsorption', 'synthesis'],
    '52':  ['co2', 'compression', 'energy', 'impurity'],
    '55':  ['co2', 'compression', 'energy', 'impurity'],
    '54':  ['sba', 'pei', 'co2', 'capture'],
    '60':  ['tvsa', 'temperature', 'swing', 'co2'],
    '62':  ['nico', 'mof-74', 'microwave', 'co2'],
    '118': ['mof', 'qst', 'adsorption', 'heat'],
    '128': ['water', 'mof', 'co2', 'adsorption', 'degradation'],
    '129': ['sba', 'amine', 'qst', 'co2'],
    '139': ['mof', 'co2', 'water', 'co-adsorption'],
    '168': ['water', 'dissociation', 'mof', 'hydrolysis'],
    '169': ['bimetallic', 'mof', 'metal', 'stability'],
    '185': ['mof-74', 'molecular', 'simulation', 'oms'],
    '188': ['tsa', 'temperature', 'swing', 'mof'],
}


def crossref_search(query, rows=5):
    url = 'https://api.crossref.org/works'
    params = {'query': query, 'rows': rows, 'select': 'DOI,title,container-title,issued,author'}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None, 'HTTP %d' % r.status_code
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
            journal = (it.get('container-title') or [''])[0]
            authors = ', '.join('%s %s' % (a.get('given', ''), a.get('family', '')) for a in it.get('author', [])[:2])
            items.append({'doi': it['DOI'], 'title': title, 'year': year, 'journal': journal, 'authors': authors})
        return items, None
    except Exception as e:
        return None, str(e)[:100]


def datacite(doi):
    """DataCite 核验（figshare 等 10.48448 前缀）。"""
    url = 'https://api.datacite.org/dois/' + doi
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None, 'DataCite HTTP %d' % r.status_code
        a = r.json()['data']['attributes']
        return {'title': (a.get('titles') or [{}])[0].get('title', ''),
                'year': (a.get('publicationYear') or ''),
                'journal': (a.get('publisher') or ''), 'authors': ''}, None
    except Exception as e:
        return None, str(e)[:100]


def match(title, kws):
    t = title.lower()
    return sum(1 for kw in kws if kw in t)


out = ['# p# 全面核验表（Crossref 检索 + DataCite，机器核验存在性与主题吻合）',
       '',
       '> 生成：2026-08 ｜ 对每个待补 p# 用检索式调 Crossref works（真实学术库）取 Top 5，',
       '> 命中分 = 上下文关键词在标题中的命中数。**全部为候选：DOI 真实存在且主题吻合 ≠ 确认就是当初引用的那篇**，',
       '> 仍需打开原文最终确认（红线：身份对应无法由机器证明）。',
       '']

for pid in ['16', '20', '52', '55', '54', '60', '62', '118', '128', '129', '139', '168', '169', '185', '188']:
    out.append('## p%s' % pid)
    out.append('检索式: `%s`' % QUERIES[pid])
    kws = CTX_KW.get(pid, [])
    if pid == '54':
        # p54 用 DataCite（10.48448 figshare）
        meta, err = datacite('10.48448/dcn4-gz78')
        if meta and meta['title']:
            sc = match(meta['title'], kws)
            out.append('- DataCite `10.48448/dcn4-gz78` → %s（%s, %s）｜命中 %d → %s' % (
                meta['title'][:80], meta['journal'][:40], meta['year'], sc, '高置信' if sc >= 2 else ('弱匹配' if sc == 1 else '存疑')))
        else:
            out.append('- DataCite `10.48448/dcn4-gz78` → 查询失败（%s）【需 doi.org 人工】' % err)
        out.append('')
        time.sleep(0.5)
        continue
    items, err = crossref_search(QUERIES[pid])
    if items is None:
        out.append('- Crossref 检索失败: %s' % err)
        out.append('')
        continue
    for it in items:
        sc = match(it['title'], kws)
        verdict = '高置信' if sc >= 2 else ('弱匹配' if sc == 1 else '主题存疑')
        out.append('- `%s` → %s（%s, %s, %s）｜命中 %d → %s' % (
            it['doi'], it['title'][:80], it['journal'][:35], it['year'], it['authors'][:35], sc, verdict))
    out.append('')
    time.sleep(0.8)

dst = ROOT / 'workspace/_pids_crossref_verified.md'
dst.write_text('\n'.join(out), encoding='utf-8')
print('[OK] 已生成 %s' % dst)
