# -*- coding: utf-8 -*-
"""查验 p60 / p118 / p168 / p169：Crossref 元数据 + OpenAlex 摘要（S2 兜底）+ 关键信息"""
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

ITEMS = [
    ("p60", "10.3390/su17156796",
     ["temperature", "vacuum", "swing", "direct air capture", "dac", "parametric", "co2"]),
    ("p118", "10.1016/j.jcis.2021.12.163",
     ["isosteric", "qst", "enthalpy", "mof-74", "nickel", "kj/mol", "29", "25"]),
    ("p168", "10.1021/acsearthspacechem.7b00142",
     ["water", "proton", "dissociation", "hydrolysis", "dft", "mechanism"]),
    ("p169", "10.1021/acs.jpcc.6b11719",
     ["mixed-metal", "mof-74", "metal distribution", "water adsorption", "structure"]),
]


def openalex(doi):
    try:
        r = requests.get(f"https://api.openalex.org/works/doi:{doi}", headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        d = r.json()
        inv = d.get("abstract_inverted_index")
        ab = ""
        if inv:
            pos = {}
            for w, idxs in inv.items():
                for i in idxs:
                    pos[i] = w
            ab = " ".join(pos[i] for i in sorted(pos))
        auth = d.get("authorships") or []
        return {"title": d.get("title", ""), "year": d.get("publication_year"),
                "first": auth[0]["author"]["display_name"] if auth else "",
                "venue": (d.get("primary_location") or {}).get("source", {}).get("display_name", ""),
                "abstract": ab}
    except Exception as e:
        return {"err": str(e)}


def s2(doi):
    try:
        r = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                         params={"fields": "abstract"}, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return (r.json().get("abstract") or "")
    except Exception:
        pass
    return ""


for pid, doi, kws in ITEMS:
    print("=" * 66)
    oa = openalex(doi)
    ab = (oa or {}).get("abstract", "") if oa else ""
    src = "openalex"
    if not ab:
        ab = s2(doi)
        src = "semanticscholar"
    if oa:
        print(f"[{pid}] {doi}")
        print(f"  标题: {(oa.get('title') or '')[:110]}")
        print(f"  作者/年/刊: {oa.get('first','')} | {oa.get('year')} | {(oa.get('venue') or '')[:55]}")
    print(f"  摘要来源: {src} | 长度 {len(ab)}")
    if ab:
        print(f"  摘要前 300 字: {ab[:300]}")
    ab_l = ab.lower()
    hits = [k for k in kws if k.lower() in ab_l]
    print(f"  关键命中: {hits if hits else '无'}")
    # p118 特定：找 kJ/mol 数值
    if pid == "p118":
        nums = re.findall(r"\b\d+(?:\.\d+)?\s*kJ/mol\b", ab)
        print(f"  kJ/mol 数值: {nums if nums else '未在摘要出现'}")
    print(f"  结论: {'✅ 摘要关键命中' if hits else '⚠️ 无摘要/未命中，按标题级'}")
    time.sleep(1.2)
