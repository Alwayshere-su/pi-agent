# -*- coding: utf-8 -*-
"""为无候选 p# 生成 Sciverse/Crossref 检索式建议（基于 memory 描述 + gap 上下文）。"""
import io
import re
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT / 'workspace/outputs/literature_survey'

# memory 描述
mem = {}
for f in sorted(glob.glob(str(ROOT / 'workspace/memory/survey/*.md'))):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'\bp(\d+)\b([^\n]{0,80})', t):
        pid = m.group(1)
        ctx = m.group(2).strip()
        if pid not in mem or len(ctx) > len(mem[pid]):
            mem[pid] = ctx

# gap 上下文
gap = io.open(SURVEY / 'gap_report.md', encoding='utf-8').read()
no_cand = ['16', '52', '55', '118', '128', '139', '168', '169', '185', '20']
# 20 有候选（质量差），仍给检索式

queries = {
    '16': '"water" CO2 uptake amine functionalized MOF humidity enhancement',
    '20': 'Ni-MOF-74 CO2 adsorption 8.29 mmol/g synthesis condition',
    '52': 'CO2 compression energy penalty low purity flue gas amine',
    '55': 'CO2 capture compression energy impurity gas MOF',
    '118': 'MOF Qst 25-40 kJ/mol CO2 adsorption heat Pareto',
    '128': 'water vapor CO2 adsorption MOF degradation humidity decay',
    '139': 'MOF CO2 adsorption water no competition co-adsorption',
    '168': 'water dissociation open metal site MOF hydrolysis mechanism',
    '169': 'bimetallic MOF thermodynamic preference mixed metal stability',
    '185': 'M-MOF-74 molecular simulation OMS density Qst',
}

out = ['# 需外部检索的 p# 检索式建议（Sciverse / Crossref）',
       '',
       '> 每条：memory/gap 线索 → 建议检索式。检索后**打开原文核验 DOI 再回填**，全部【待核验】。',
       '']
for pid in ['16', '20', '52', '55', '118', '128', '139', '168', '169', '185']:
    mctx = mem.get(pid, '(无 memory 线索)')
    gctx = ''
    mm = re.search(r'\bp' + pid + r'\b[^\n]{0,90}', gap)
    if mm:
        gctx = mm.group(0)
    out.append('## p%s' % pid)
    out.append('- memory: %s' % mctx[:90])
    out.append('- gap 上下文: %s' % gctx[:90])
    out.append('- 检索式: `%s`' % queries.get(pid, ''))
    out.append('')

dst = ROOT / 'workspace/_pids_queries.md'
dst.write_text('\n'.join(out), encoding='utf-8')
print('[OK] 已生成 %s' % dst)
