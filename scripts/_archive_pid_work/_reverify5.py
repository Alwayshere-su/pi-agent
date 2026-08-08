# -*- coding: utf-8 -*-
"""复核 p52/p55/p62/p185/p188：OpenAlex 摘要重建 + Europe PMC 兜底"""
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

ITEMS = [
    ("p52", "10.1021/acs.iecr.5c04931", ["pressure swing", "psa", "energy", "techno-economic", "cost"]),
    ("p55", "10.1016/j.energy.2025.135505", ["energy penalty", "low co2", "low concentration", "absorption", "capture"]),
    ("p62", "10.1016/j.efmat.2023.01.002", ["nico", "bimetallic", "microwave", "capacity", "co2", "8.30", "3.99", "5.03"]),
    ("p185", "10.46690/capi.2023.01.02", ["m-mof-74", "molecular simulation", "adsorption", "oms", "metal"]),
    ("p188", "10.1021/acs.iecr.5b03727", ["temperature swing", "co2", "column", "postcombustion", "mof", "zeolite", "amine"]),
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
        first = auth[0].get("author", {}).get("display_name", "") if auth else ""
        return {
            "title": d.get("title", ""),
            "year": d.get("publication_year"),
            "first": first,
            "venue": (d.get("primary_location") or {}).get("source", {}).get("display_name", ""),
            "abstract": ab,
        }
    except Exception as e:
        return {"err": str(e)}


def europepmc(doi):
    try:
        r = requests.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query": f'DOI:"{doi}"', "resultType": "core", "format": "json"},
            headers=HEADERS,
            timeout=30,
        )
        res = r.json().get("resultList", {}).get("result", [])
        if res:
            return res[0].get("abstractText", "")
        return None
    except Exception:
        return None


for pid, doi, kws in ITEMS:
    print("=" * 66)
    oa = openalex(doi)
    ab = (oa or {}).get("abstract", "") if oa else ""
    src = "openalex"
    if not ab:
        ab = europepmc(doi) or ""
        src = "europepmc"
    if oa:
        print(f"[{pid}] {doi}")
        print(f"  标题: {(oa.get('title') or '')[:100]}")
        print(f"  作者/年/刊: {oa.get('first','')} | {oa.get('year')} | {(oa.get('venue') or '')[:55]}")
    print(f"  摘要来源: {src} | 长度 {len(ab)}")
    if ab:
        print(f"  摘要前 260 字: {ab[:260]}")
    ab_l = ab.lower()
    hits = [k for k in kws if k.lower() in ab_l]
    print(f"  关键命中: {hits if hits else '无'}")
    nums = re.findall(r"\b8\.29\b|\b8\.30\b|\b3\.99\b|\b5\.03\b", ab)
    if nums:
        print(f"  数值命中: {nums}")
    print(f"  结论: {'✅ 摘要关键命中' if hits else '⚠️ 仍无摘要/未命中，需人工打开'}")
    time.sleep(1.0)
