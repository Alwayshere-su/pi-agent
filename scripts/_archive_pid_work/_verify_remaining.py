# -*- coding: utf-8 -*-
"""独立复核 p60/p118/p168/p169：Crossref 元数据 + OpenAlex 摘要 + Semantic Scholar 兜底"""
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

ITEMS = [
    ("p60", "10.3390/su17156796",
     ["temperature vacuum swing", "t-vsa", "direct air capture", "dac", "parametr", "optimiz"]),
    ("p118", "10.1016/j.jcis.2021.12.163",
     ["isosteric", "heat", "mof-74", "qst", "nickel"]),
    ("p168", "10.1021/acsearthspacechem.7b00142",
     ["water", "proton", "dissociation", "hydrolysis"]),
    ("p169", "10.1021/acs.jpcc.6b11719",
     ["mixed", "mof-74", "metal distribution", "water adsorption", "mg", "ni"]),
]


def get(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            return r
        except Exception as e:
            print(f"   [重试 {i+1}/{tries}] {type(e).__name__}")
            time.sleep(3)
    return None


def crossref(doi):
    r = get(f"https://api.crossref.org/works/{requests.utils.quote(doi)}")
    if r is None:
        return None
    if r.status_code != 200:
        return None
    m = r.json().get("message", {})
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        if m.get(k, {}).get("date-parts"):
            year = m[k]["date-parts"][0][0]
            break
    auth = m.get("author") or []
    return {"title": (m.get("title") or [""])[0], "year": year,
            "first": auth[0].get("family", "") if auth else "",
            "venue": (m.get("container-title") or [""])[0]}


def openalex_ab(doi):
    r = get(f"https://api.openalex.org/works/doi:{doi}")
    if r is None:
        return ""
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
        r = get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                params={"fields": "abstract"})
        if r is None:
            return ""
        return (r.json().get("abstract") or "") if r.status_code == 200 else ""
    except Exception:
        return ""


for pid, doi, kws in ITEMS:
    print("=" * 66)
    cr = crossref(doi)
    if not cr:
        print(f"[{pid}] Crossref 失败 {doi}")
        continue
    ab = openalex_ab(doi) or s2_ab(doi)
    print(f"[{pid}] {doi}")
    print(f"  标题: {cr['title'][:110]}")
    print(f"  作者/年/刊: {cr['first']} | {cr['year']} | {cr['venue'][:50]}")
    low = ab.lower()
    hits = [k for k in kws if k.lower() in low]
    print(f"  摘要({len(ab)}字): {ab[:240]}")
    print(f"  关键命中: {hits if hits else '无'}")
    # p118 关注 Qst 数值
    if pid == "p118":
        nums = re.findall(r"\b(?:27|29|25|40|52)\b(?=[^\d]*kJ)", ab) or re.findall(r"\b(?:27|29|25|40|52)\s*(?:kJ|k.J)", ab)
        print(f"  Qst 数值线索: {nums if nums else '摘要未见 27/29/25/40/52 kJ'}")
    # p168 关注体系（Al³⁺ 水溶液?）
    if pid == "p168":
        print(f"  体系线索: Al/铝={'aluminum' in low or ' al3' in low or 'al(' in low} | 水溶液={'aqueous' in low} | MOF={'mof' in low or 'metal-organic' in low}")
    print(f"  结论: {'✅ 摘要关键命中' if hits else '⚠️ 摘要未命中/无摘要'}")
    time.sleep(1.0)
