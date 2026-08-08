# -*- coding: utf-8 -*-
"""查验 p60/p118/p168/p169：Crossref 元数据 + OpenAlex/S2 摘要 + 关键词；p118 合并佐证（含 memory 上下文）"""
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

ITEMS = [
    ("p60", "10.3390/su17156796", ["temperature", "vacuum swing", "dac", "direct air capture", "co2", "parametr"]),
    ("p118", "10.1016/j.jcis.2021.12.163", ["isosteric", "qst", "kj/mol", "nickel", "mof-74"]),
    ("p168", "10.1021/acsearthspacechem.7b00142", ["water", "proton", "dissociation", "hydrolysis", "mof"]),
    ("p169", "10.1021/acs.jpcc.6b11719", ["mixed-metal", "metal distribution", "water adsorption", "mof-74"]),
]


def crossref(doi):
    r = requests.get(f"https://api.crossref.org/works/{requests.utils.quote(doi)}",
                     headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return None
    m = r.json().get("message", {})
    return {
        "title": (m.get("title") or [""])[0],
        "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
        "first": (m.get("author") or [{}])[0].get("family", ""),
        "venue": (m.get("container-title") or [""])[0],
        "abstract": m.get("abstract", ""),
    }


def openalex_ab(doi):
    r = requests.get(f"https://api.openalex.org/works/doi:{doi}", headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return ""
    inv = r.json().get("abstract_inverted_index")
    if not inv:
        return ""
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def s2_ab(doi):
    try:
        r = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                         params={"fields": "abstract"}, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.json().get("abstract") or ""
    except Exception:
        pass
    return ""


for pid, doi, kws in ITEMS:
    print("=" * 66)
    cr = crossref(doi)
    ab = openalex_ab(doi) or s2_ab(doi) or ""
    src = "openalex/s2" if ab else "无摘要"
    if cr:
        print(f"[{pid}] {doi}")
        print(f"  标题: {cr['title'][:110]}")
        print(f"  作者/年/刊: {cr['first']} | {cr['year']} | {cr['venue'][:50]}")
    print(f"  摘要来源: {src} | 长度 {len(ab)}")
    if ab:
        print(f"  摘要前 240 字: {ab[:240]}")
    low = ab.lower()
    hits = [k for k in kws if k.lower() in low]
    print(f"  关键命中: {hits if hits else '无'}")
    if pid == "p118":
        for pat in [r"29", r"25", r"40", r"kj/mol", r"qst", r"isosteric"]:
            m = re.findall(r".{20}" + pat + r".{20}", ab, re.I)
            if m:
                print(f"  p118 数值片段 {pat!r}: {m[:2]}")
    print(f"  结论: {'✅ 摘要关键命中' if hits else '⚠️ 无摘要/未命中，标题级待确认'}")
    time.sleep(1.0)

# p118 合并佐证：memory 中 p27/p118 上下文
print()
print("=== p118/p27 memory 上下文（合并佐证） ===")
for f in [r"workspace/memory/survey/survey-0801-mof-co2.md",
          r"workspace/outputs/literature_survey/gap_report.md"]:
    try:
        for ln in open(f, encoding="utf-8"):
            if re.search(r"\bp27\b|\bp118\b", ln):
                print(f"  [{f.split('/')[-1]}] {ln.strip()[:150]}")
    except Exception as e:
        print("  读取失败", f, e)
