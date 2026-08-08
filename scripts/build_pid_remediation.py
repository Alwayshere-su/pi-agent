# -*- coding: utf-8 -*-
"""为 gap_report.md 中无 DOI 的 p# 生成候选映射卡（候选全部来自仓库文件，禁止 AI 猜 DOI）"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"workspace/evidence/pids_remediation.md"

# p# -> (主题关键词，用于在仓库候选池中匹配；含中英文)
PID_KEYWORDS = {
    "p16": ["competitive", "cooperative", "co2-h2o", "water", "促进", "竞争", "水"],
    "p20": ["ni-mof-74", "nickel", "8.29", "synthesis", "capacity", "镍", "容量", "合成"],
    "p52": ["compression", "low purity", "energy", "co2 compression", "压缩", "能耗", "低纯度"],
    "p54": ["sba-15", "pei", "direct air capture", "amine", "dac", "浸渍", "胺"],
    "p55": ["compression", "low purity", "energy", "co2", "压缩", "能耗"],
    "p60": ["tvsa", "temperature vacuum swing", "high purity", "co2", "高纯", "变温"],
    "p62": ["nico-mof-74", "microwave", "bimetallic", "open metal site", "8.30", "微波", "双金属"],
    "p118": ["qst", "isosteric heat", "25-40", "adsorption heat", "吸附热", "窗口"],
    "p128": ["water", "decay", "capacity", "humidity", "衰减", "水", "容量"],
    "p129": ["water", "no effect", "co2", "水", "无影响"],
    "p139": ["water", "no competition", "co2", "水", "无竞争"],
    "p168": ["water dissociation", "mechanism", "mof-74", "水解离", "机理"],
    "p169": ["bimetallic", "mixed metal", "thermodynamic", "preference", "混合金属", "热力学"],
    "p185": ["m-mof-74", "molecular simulation", "binding", "potential", "分子模拟", "结合"],
    "p188": ["tsa", "temperature swing", "dynamics", "process", "变温", "动态"],
}

gap = open(r"workspace/outputs/literature_survey/gap_report.md", encoding="utf-8").read()

# 候选池 1：papers_pid_index.json（pid -> title/abstract，编号体系不同，仅作关键词池）
index = json.load(
    open(r"workspace/outputs/literature_survey/papers_pid_index.json", encoding="utf-8")
)
index_pool = [(pid, e.get("title", ""), e.get("abstract", "")) for pid, e in index.items()]

# 候选池 2：主案例检索缓存（title + doi + abstract）
cache = json.load(open(r"workspace/data/literature_cache/search_results.json", encoding="utf-8"))
cache_pool = [
    (r.get("title", ""), r.get("doi", ""), r.get("abstract", "") or "")
    for r in cache
    if r.get("title")
]

# 候选池 3：memory/survey 提及（直接线索，含标题/DOI 若同段落出现）
mem_pool = []
for f in sorted(glob.glob(r"workspace/memory/survey/*.md")):
    txt = open(f, encoding="utf-8").read()
    mem_pool.append((f.split("\\")[-1], txt))

# 候选池 4：knowledge_graph.md（p# 同行 DOI 共现）
kg = open(r"workspace/outputs/literature_survey/knowledge_graph.md", encoding="utf-8").read()


def norm(s):
    return s.lower()


def score(title, kws):
    t = norm(title)
    hits = [k for k in kws if k in t]
    return hits


lines = []
lines.append("# p# 待核验候选映射卡（gap_report.md 中无可靠 DOI 的引用）\n")
lines.append(
    "> 生成说明：候选**全部来自仓库现有文件**（papers_pid_index.json、检索缓存 search_results.json、"
    "memory/survey、knowledge_graph.md），**不含 AI 猜测的 DOI**。"
    "每条候选需人工在 Sciverse/arXiv 按标题核对确认后，再回填 gap_report.md 与 paper_summaries.md。\n"
)
lines.append("| p# | 所属 Gap | 上下文主题 | 仓库候选（标题 / DOI，来源） | 状态 |")
lines.append("|---|---|---|---|---|")

pids = list(PID_KEYWORDS.keys())
for pid in pids:
    kws = PID_KEYWORDS[pid]
    # 上下文：gap_report 中该 p# 所在句子
    m = re.search(rf"\b{pid}\b[^。\n]*", gap)
    ctx = (m.group(0).strip()[:80] if m else "") or ""
    # 所属 Gap
    sec = re.split(r"\n(?=## Gap )", gap)
    own_gap = ""
    for s in sec:
        if re.search(rf"\b{pid}\b", s):
            own_gap = s.split("\n", 1)[0].replace("## ", "").split("：")[0]
            break
    # 候选：cache 池
    cands = []
    seen = set()
    for title, doi, ab in cache_pool:
        hits = score(title, kws)
        if hits:
            key = (title[:40], doi)
            if key not in seen:
                seen.add(key)
                cands.append((len(hits), "检索缓存", title, doi, "/".join(hits)))
    for pid2, title, ab in index_pool:
        hits = score(title, kws)
        if hits:
            key = (title[:40], pid2)
            if key not in seen:
                seen.add(key)
                cands.append((len(hits), f"pid索引({pid2})", title, "", "/".join(hits)))
    cands.sort(key=lambda x: -x[0])
    # memory 线索
    mem_ctx = []
    for fname, txt in mem_pool:
        for mm in re.finditer(rf"\b{pid}\b[^\n]{0,60}", txt):
            mem_ctx.append(f"{fname}:{mm.group(0).strip()[:50]}")
    # knowledge_graph 同行 DOI
    kg_dois = []
    for line in kg.split("\n"):
        if re.search(rf"\b{pid}\b", line):
            doi = re.search(r"10\.\d{4,9}/[^\s)）|,；;]+", line)
            if doi:
                kg_dois.append(doi.group(0))

    if cands:
        top = cands[:3]
        cand_txt = "<br>".join(
            f"{t} / {d or '—'}（{src}，命中 {h}）" for h, src, t, d, _ in top
        )
    else:
        cand_txt = "仓库候选池无命中"
    if mem_ctx:
        cand_txt += "<br>【memory 线索】" + "<br>".join(mem_ctx[:2])
    if kg_dois:
        cand_txt += "<br>【图谱同行 DOI】" + "; ".join(kg_dois[:2])
    lines.append(
        f"| {pid} | {own_gap or '—'} | {ctx or '—'} | {cand_txt} | 待人工核验 |"
    )

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("written:", OUT)
print("p# 数:", len(pids))
