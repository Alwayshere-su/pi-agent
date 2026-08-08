# -*- coding: utf-8 -*-
"""批量核验 p# 候选 DOI：调 Crossref API 取真实元数据，与上下文关键词比对匹配置信度。

输入候选（_pids_candidates.md 语义候选 + 人工提示候选）：
    p62  -> 10.1016/j.efmat.2023.01.002
    p52  -> 10.1016/j.fuel.2017.03.079 ; 10.1016/j.ijggc.2016.04.023
    p54  -> 10.48448/dcn4-gz78
    p60  -> 10.1016/j.ces.2022.118390
    p188 -> 10.1016/j.ces.2022.118390
输出：workspace/_pids_verified.md（每行：p# / DOI / 真实标题 / 年份·期刊 / 与上下文匹配判定 / 状态）
"""
import io
import re
import time
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT / 'workspace/outputs/literature_survey'

# p# -> 候选 DOI（来自 _pids_candidates.md 语义命中 + 人工提示）
candidates = {
    '20':  ['10.1016/j.efmat.2023.01.002'],          # 索引候选（需复核：p20 是 Ni 8.29 矛盾，此候选为 NiCo 微波，仅低置信）
    '60':  ['10.1007/s13369-020-04946-0', '10.36561/ing.28.16'],
    '62':  ['10.1016/j.efmat.2023.01.002'],
    '129': ['10.3390/jcs5040102'],
    '52':  ['10.1016/j.fuel.2017.03.079', '10.1016/j.ijggc.2016.04.023'],
    '55':  ['10.1016/j.fuel.2017.03.079', '10.1016/j.ijggc.2016.04.023'],
    '54':  ['10.48448/dcn4-gz78'],
    '60b': ['10.1016/j.ces.2022.118390'],            # p60/p188 工艺动态候选
    '188': ['10.1016/j.ces.2022.118390'],
}

# 每个 p# 的上下文关键词（人工从 gap/memory 提炼，用于匹配判定）
ctx_kw = {
    '20':  ['ni-mof', 'synthesis', 'condition'],
    '60':  ['tvsa', 'temperature swing', 'co2'],
    '62':  ['nico', 'mof-74', 'microwave'],
    '129': ['sba', 'qst', 'amine'],
    '52':  ['co2', 'compression', 'energy', 'impurity'],
    '55':  ['co2', 'compression', 'energy'],
    '54':  ['sba-15', 'pei', 'dac'],
    '188': ['tsa', 'dynamic', 'mof'],
}

HEADERS = {'User-Agent': 'PiAgent-verification/1.0 (mailto:goai@example.com)'}


def crossref(doi):
    url = 'https://api.crossref.org/works/' + doi
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None, 'Crossref HTTP %d' % r.status_code
        m = r.json()['message']
        title = (m.get('title') or [''])[0]
        year = ''
        for k in ('published-print', 'published-online', 'issued'):
            if m.get(k, {}).get('date-parts'):
                year = m[k]['date-parts'][0][0]
                break
        journal = (m.get('container-title') or [''])[0]
        authors = ', '.join('%s %s' % (a.get('given', ''), a.get('family', '')) for a in m.get('author', [])[:3])
        return {'title': title, 'year': year, 'journal': journal, 'authors': authors}, None
    except Exception as e:
        return None, str(e)[:120]


def match_score(title, kws):
    t = title.lower()
    return sum(1 for kw in kws if kw in t)


out = ['# p# 候选 DOI 核验表（Crossref 元数据 + 匹配判定）',
       '',
       '> 生成：2026-08 ｜ 方法：Crossref API 取真实元数据；匹配 = 标题命中上下文关键词数。',
       '> **状态语义**：高置信=标题与上下文强吻合（仍需打开原文最终确认）；待核验=存在但主题匹配弱/存疑；',
       '> 无记录=Crossref 查不到（可能为 DataCite/Figshare 或 DOI 有误，需 doi.org 或人工再查）。',
       '']

for pid, dois in candidates.items():
    out.append('## p%s' % pid)
    out.append('上下文关键词: %s' % ' '.join(ctx_kw.get(pid, [])))
    for doi in dois:
        meta, err = crossref(doi)
        if meta is None:
            out.append('- DOI `%s` → **无记录/查询失败**（%s）【待人工核验】' % (doi, err))
            continue
        score = match_score(meta['title'], ctx_kw.get(pid, []))
        if score >= 2:
            st = '高置信候选'
        elif score == 1:
            st = '弱匹配候选'
        else:
            st = '主题存疑'
        out.append('- DOI `%s` → %s｜%s（%s, %s, %s）｜标题命中 %d/关键词 → **%s**' % (
            doi, meta['title'][:80], meta['journal'][:40], meta['year'], meta['authors'][:40], st, score, st))
    out.append('')
    time.sleep(0.5)

dst = ROOT / 'workspace/_pids_verified.md'
dst.write_text('\n'.join(out), encoding='utf-8')
print('[OK] 已生成 %s' % dst)
