# -*- coding: utf-8 -*-
"""生成 p# 证据索引表 pid_evidence_index.md（GOAI 证据链断链补救）。

数据源：
  - workspace/outputs/literature_survey/papers_pid_index.json（zip 恢复，180 篇 p# 元数据）
  - knowledge_graph.md（p#(DOI) 映射）
  - memory/survey/*.md（p# 主题描述）
  - gap_report.md（p# 所属 Gap 与引用上下文）

输出：workspace/outputs/literature_survey/discovery/pid_evidence_index.md
"""
import io
import json
import re
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT / 'workspace' / 'outputs' / 'literature_survey'
OUT = SURVEY / 'discovery' / 'pid_evidence_index.md'

# 1) papers_pid_index.json —— ⚠️ 仅作候选检索池，不按 p# 直接映射
# 该文件来自早期 Prospector 归档（180 篇论文），其 p# 编号与当前项目
# （knowledge_graph / gap_report）**不是同一编号体系**（已核实：p65 在 zip 为
# UiO-66@IL 合成 10.1016/j.chemosphere.2022.135122，而 knowledge_graph/gap_report
# 中 p65 为 CoMn 1:1 废水吸附 10.3390/su17073060）。故 zip 论文只能用于按
# 标题/主题人工匹配候选，禁止按 p# 直接对应 DOI。
pid_index = json.load(io.open(SURVEY / 'papers_pid_index.json', encoding='utf-8'))
zip_pool = []
for k, v in pid_index.items():
    m = re.match(r'p(\d+)$', k)
    if m and isinstance(v, dict):
        doi = v.get('doi', '') if isinstance(v.get('doi'), str) else ''
        if not doi:
            doi = re.search(r'10\.\d{4,}[^\s"\'\\]*', json.dumps(v, ensure_ascii=False))
            doi = doi.group(0) if doi else ''
        zip_pool.append({'pid': m.group(1), 'title': v.get('title', ''), 'doi': doi})

# 2) knowledge_graph p#->DOI（取完整 DOI，含 / 后续路径）
kg = io.open(SURVEY / 'knowledge_graph.md', encoding='utf-8').read()
kg_map = {}
for m in re.finditer(r'p(\d+)\s*\(?(10\.\d{4,}[^\s)）\]\)]*)', kg):
    kg_map.setdefault(m.group(1), m.group(2))

# 3) memory 描述
mem_desc = {}
for f in sorted(glob.glob(str(ROOT / 'workspace/memory/survey/*.md'))):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'\bp(\d+)\b([^\n]{0,70})', t):
        if m.group(1) not in mem_desc:
            mem_desc[m.group(1)] = (Path(f).name, m.group(2).strip()[:60])

# 4) gap_report：40 个 p# 及其 Gap 上下文
g = io.open(SURVEY / 'gap_report.md', encoding='utf-8').read()
gpids = sorted(set(re.findall(r'\bp(\d+)\b', g)), key=int)
sections = re.split(r'\n## ', g)[1:]
gap_of = {}
pid_ctx = {}
for sec in sections:
    name = sec.split('\n')[0][:50]
    # 上下文抓取跨行：p# 后最多 160 字符（含换行折叠）
    for m in re.finditer(r'\bp(\d+)\b', sec):
        pid = m.group(1)
        ctx = sec[m.end():m.end() + 160].replace('\n', ' ').strip()[:110]
        gap_of.setdefault(pid, set()).add(name)
        if pid not in pid_ctx or len(ctx) > len(pid_ctx[pid]):
            pid_ctx[pid] = ctx


def ctx_doi(ctx):
    """从 Gap 引用上下文中提取完整 DOI（排除中英文括号/空白/引号）。"""
    m = re.search(r'10\.\d{4,}[^\s)）(\]\x27]*', ctx or '')
    return m.group(0) if m else ''

lines = [
    '# p# 论文证据索引表（GOAI 证据链断链补救）',
    '',
    '> 生成时间：2026-08 ｜ 用途：为 `gap_report.md` 中的历史轮次论文编号 p# 提供可解析的',
    '> DOI/标题/摘要定位，恢复「Gap → 论文 → 摘要 → 检索日志 → API 调用」四层追溯链。',
    '> ⚠️ **编号体系说明**：本表 DOI 仅采自信誉来源——`knowledge_graph.md`（与 gap_report 同一',
    '> 编号体系，已交叉核验）与 gap_report 引用上下文。`papers_pid_index.json`（zip 归档恢复的',
    '> 180 篇历史论文）编号体系与当前项目**不同**（已核实 p65 等错配），只能作为人工按标题/主题',
    '> 检索的候选池，**禁止按 p# 直接取用其 DOI**（避免指错文献）。',
    '> 其余来源：`workspace/memory/survey/`（各轮主题描述）、`gap_report.md`（引用上下文）。',
    '',
    '| p# | 状态 | DOI | 标题/线索 | 可解析位置 |',
    '|----|------|-----|-----------|-----------|',
]

for pid in gpids:
    kgd = kg_map.get(pid)
    mem = mem_desc.get(pid)
    gctx = pid_ctx.get(pid, '')
    gdoi = ctx_doi(gctx)
    if kgd:
        status = '已解析(KG)'
        doi = kgd
        title = gctx[:70] if gctx else '—'
        loc = '`knowledge_graph.md`'
    elif gdoi:
        status = '已解析(上下文DOI)'
        doi = gdoi
        title = gctx[:70]
        loc = '`gap_report.md` 引用上下文'
    elif mem:
        status = '待人工补DOI'
        doi = '—'
        title = 'memory 描述: ' + mem[1][:60]
        loc = '`memory/%s`' % mem[0]
    else:
        status = '⚠️ 待人工定位'
        doi = '—'
        title = 'Gap 上下文: ' + (gctx[:70] if gctx else '无')
        loc = '—'
    gaps = '; '.join(sorted(gap_of.get(pid, set())))[:45]
    lines.append('| p%s | %s | %s | %s | %s |' % (pid, status, doi, title.replace('|', '\\|'), loc))

# 汇总（仅统计可靠来源：knowledge_graph + gap 上下文 + memory）
n_ok = sum(1 for p in gpids if (p in kg_map or ctx_doi(pid_ctx.get(p, ''))))
n_part = sum(1 for p in gpids if not (p in kg_map or ctx_doi(pid_ctx.get(p, ''))) and p in mem_desc)
n_no = len(gpids) - n_ok - n_part

lines += [
    '',
    '### 汇总',
    '',
    '- 40 个 p# 中：**已解析 %d**（含 DOI）｜ **待人工补 DOI %d**（有 memory 描述）｜ **待人工定位 %d**（无任何线索）' % (n_ok, n_part, n_no),
    '- 已解析 p# 的 DOI 可直接在 `gap_report.md` 证据行内联查证（`p#（DOI: ...）`）；',
    '- `papers_pid_index.json` 为早期归档候选池（编号体系不同），仅用于按标题/主题人工匹配，勿按 p# 直接取用。',
    '- 待人工定位 p# 的引用上下文见 `gap_report.md` 对应 Gap；建议在复赛前凭上下文检索补齐，**禁止凭空填写 DOI**。',
    '',
]

OUT.write_text('\n'.join(lines), encoding='utf-8')
print('[OK] 已生成 %s' % OUT)
print('  已解析: %d | 待人工补DOI: %d | 待人工定位: %d' % (n_ok, n_part, n_no))
