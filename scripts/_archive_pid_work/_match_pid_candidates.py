# -*- coding: utf-8 -*-
"""为 gap_report 待补 p# 生成候选 DOI（papers_pid_index.json 语义匹配）。

规则（红线安全）：
- papers_pid_index.json 编号体系与当前项目不同，结果仅作**候选**，
  任何 DOI 在打开原始来源核验前一律视为【待核验】，禁止直接引用；
- 候选打分：上下文关键词在候选论文 title（+2/词）与 abstract（+1/词）中的命中；
- 输出 Top 3 候选到 workspace/_pids_candidates.md。
"""
import io
import json
import re
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT / 'workspace/outputs/literature_survey'

# 1) papers_pid_index.json 候选池
pool = json.load(io.open(SURVEY / 'papers_pid_index.json', encoding='utf-8'))
papers = []
for k, v in pool.items():
    m = re.match(r'p(\d+)$', k)
    if m and isinstance(v, dict):
        papers.append({
            'pid': m.group(1),
            'title': (v.get('title') or '').lower(),
            'abstract': (v.get('abstract') or '').lower(),
            'doi': (v.get('doi') or '') if isinstance(v.get('doi'), str) else '',
        })

# 2) 待补 p# 及上下文（gap_report 中 p# 后 120 字符 + memory 描述）
gap = io.open(SURVEY / 'gap_report.md', encoding='utf-8').read()
targets = ['16', '20', '52', '54', '55', '60', '62', '118', '128', '129', '139', '168', '169', '185', '188']
ctx_map = {}
for pid in targets:
    ctxs = [m.group(0) for m in re.finditer(r'\bp' + pid + r'\b[^\n]{0,110}', gap)]
    ctx = ' '.join(ctxs)[:400]
    ctx_map[pid] = ctx

STOP = set('the a an of in on for and or with from by to at as is are was were be been being this that these those due via vs under over between among using use used shows shown data paper result results material materials mof mofs co2 carbon dioxide capture adsorption capacity capacities 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 20 25 30 40 50 100 400 546 10. p# gap'.split())


def keywords(pid, ctx):
    """从上下文提取检索关键词（词长>=4、去停用、去 p#/DOI/数字）。"""
    ctx = re.sub(r'10\.\d{4,}[^\s]*', ' ', ctx)
    ctx = re.sub(r'p\d+', ' ', ctx)
    words = re.findall(r'[a-zA-Z][a-zA-Z\-]{3,}', ctx.lower())
    return [w for w in words if w not in STOP]


def score(p, kws):
    s = 0
    for kw in kws:
        if kw in p['title']:
            s += 2
        elif kw in p['abstract']:
            s += 1
    return s


out = ['# p# 候选 DOI 匹配表（papers_pid_index.json 语义候选，全部【待核验】）',
       '',
       '> 生成：2026-08 ｜ 规则：候选来自早期归档索引（编号体系与当前项目不同），',
       '> **任何 DOI 在打开原始来源（DOI 解析页/原文）核验前一律视为待核验**，禁止直接引用。',
       '> 打分：上下文关键词在候选论文 title(+2)/abstract(+1) 的命中加权。',
       '']

matched_any = 0
for pid in targets:
    ctx = ctx_map.get(pid, '')
    kws = keywords(pid, ctx)
    scored = [(score(p, kws), p) for p in papers]
    scored.sort(key=lambda x: -x[0])
    top = [p for s, p in scored if s > 0][:3]
    out.append('## p%s' % pid)
    out.append('')
    out.append('上下文关键词: %s' % ' '.join(kws[:15]))
    out.append('上下文: %s' % ctx[:150])
    out.append('')
    if top:
        matched_any += 1
        for p in top:
            out.append('- 候选 `%s`（索引 p%s，得分，标题：%s，DOI：%s）【待核验】' % (
                p['pid'], p['pid'], p['title'][:70], p['doi'][:45] or '(无DOI)'))
    else:
        out.append('- （索引中无命中候选，需 Sciverse/Crossref 定向检索）')
    out.append('')

out.append('---')
out.append('摘要：%d/15 个 p# 在索引中获得候选（余下需外部检索）' % matched_any)

dst = ROOT / 'workspace/_pids_candidates.md'
dst.write_text('\n'.join(out), encoding='utf-8')
print('[OK] 已生成 %s（%d/15 个 p# 获得候选）' % (dst, matched_any))
