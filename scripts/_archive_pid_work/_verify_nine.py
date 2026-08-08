# -*- coding: utf-8 -*-
"""替用户查验 9 条 p#：DOI 落地 + Crossref 元数据 + Semantic Scholar 摘要关键数值预筛"""
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

ITEMS = [
    ("p20", "10.61511/eam.v2i2.2024.1431", ["8.29", "capacity", "ni-dobdc", "ni-mof-74"]),
    ("p52", "10.1021/acs.iecr.5c04931", ["pressure swing", "psa", "energy", "techno-economic"]),
    ("p54", "10.48448/dcn4-gz78", ["amine", "oxide", "direct air capture", "dac", "sba"]),
    ("p55", "10.1016/j.energy.2025.135505", ["energy penalty", "low co2", "low concentration"]),
    ("p62", "10.1016/j.efmat.2023.01.002", ["nico", "bimetallic", "microwave", "8.30", "3.99", "5.03"]),
    ("p128", "10.3389/fmats.2022.825592", ["water", "capacity reduction", "flexible", "decreas"]),
    ("p129", "10.3390/jcs5040102", ["sba-15", "isosteric", "enthalpy", "qst"]),
    ("p185", "10.46690/capi.2023.01.02", ["m-mof-74", "molecular simulation", "adsorption"]),
    ("p188", "10.1021/acs.iecr.5b03727", ["temperature swing", "co2", "column", "postcombustion"]),
]


def crossref(doi):
    try:
        r = requests.get(f"https://api.crossref.org/works/{requests.utils.quote(doi)}",
                         headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        m = r.json().get("message", {})
        title = (m.get("title") or [""])[0]
        year = None
        for k in ("published-print", "published-online", "issued", "created"):
            if m.get(k, {}).get("date-parts"):
                year = m[k]["date-parts"][0][0]
                break
        auth = m.get("author") or []
        first = auth[0].get("family", "") if auth else ""
        return {"title": title, "year": year, "first": first,
                "venue": (m.get("container-title") or [""])[0], "abstract": m.get("abstract", "")}
    except Exception as e:
        return {"err": str(e)}


def s2_abstract(doi):
    try:
        r = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            params={"fields": "title,abstract,year,venue,authors"},
            headers=HEADERS,
            timeout=30,
        )
        if r.status_code != 200:
            return None
        d = r.json()
        return d.get("abstract") or ""
    except Exception:
        return None


for pid, doi, kws in ITEMS:
    cr = crossref(doi)
    print("=" * 66)
    if not cr:
        print(f"[{pid}] Crossref 查询失败 {doi}")
        time.sleep(0.4)
        continue
    ab = s2_abstract(doi)
    if ab is None:
        ab = re.sub(r"<[^>]+>", " ", cr.get("abstract", "")) or ""
    src = "semanticscholar" if ab else "crossref(无摘要)"
    print(f"[{pid}] {doi}")
    print(f"  标题 : {cr.get('title','')[:100]}")
    print(f"  作者/年/刊: {cr.get('first','')} | {cr.get('year')} | {cr.get('venue','')[:55]}")
    ab_l = ab.lower()
    hits = [k for k in kws if k.lower() in ab_l]
    print(f"  摘要: {'有' if ab else '无'}（{len(ab)} 字）")
    print(f"  关键命中: {hits if hits else '无'}")
    # 关键数值（8.29/8.30/3.99/5.03 等）
    nums = re.findall(r"\b8\.29\b|\b8\.30\b|\b3\.99\b|\b5\.03\b", ab)
    if nums:
        print(f"  数值命中: {nums}")
    verdict = "✅ 通过（标题+摘要关键吻合）" if hits else "⚠️ 摘要未命中关键值，需打开全文复核"
    print(f"  结论: {verdict}")
    time.sleep(1.2)
