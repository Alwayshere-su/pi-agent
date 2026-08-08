# -*- coding: utf-8 -*-
"""多通道复核 p55 = 10.1016/j.energy.2025.135505（Verhaeghe 2025, Energy）"""
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}
DOI = "10.1016/j.energy.2025.135505"
TITLE = "Absorption-based carbon capture energy penalty reduction for low CO2 content applications"


def show(tag, d):
    print(f"[{tag}]")
    if not d:
        print("   无结果")
        return
    print(f"   title: {d.get('title','')[:110]}")
    print(f"   year : {d.get('year')} | first: {d.get('first')} | venue: {d.get('venue','')[:50]}")
    ab = d.get("abstract") or ""
    print(f"   abstract({len(ab)}): {ab[:220]}")


# 1) OpenAlex by DOI（含 has_abstract）
r = requests.get(f"https://api.openalex.org/works/doi:{DOI}", headers=HEADERS, timeout=30)
if r.status_code == 200:
    d = r.json()
    inv = d.get("abstract_inverted_index")
    ab = ""
    if inv:
        pos = {}
        for w, idxs in inv.items():
            for i in idxs:
                pos[i] = w
        ab = " ".join(pos[i] for i in sorted(pos))
    auth = (d.get("authorships") or [])
    show("OpenAlex-DOI", {"title": d.get("title"), "year": d.get("publication_year"),
                          "first": auth[0]["author"]["display_name"] if auth else "",
                          "venue": (d.get("primary_location") or {}).get("source", {}).get("display_name", ""),
                          "abstract": ab})
else:
    print(f"[OpenAlex-DOI] HTTP {r.status_code}")

# 2) OpenAlex 按标题检索
try:
    r = requests.get("https://api.openalex.org/works", params={"search": TITLE, "per-page": 3},
                     headers=HEADERS, timeout=30)
    items = r.json().get("results", []) if r.status_code == 200 else []
    for it in items[:2]:
        inv = it.get("abstract_inverted_index")
        ab = ""
        if inv:
            pos = {}
            for w, idxs in inv.items():
                for i in idxs:
                    pos[i] = w
            ab = " ".join(pos[i] for i in sorted(pos))
        auth = (it.get("authorships") or [])
        show("OpenAlex-标题检索", {"title": it.get("title"), "year": it.get("publication_year"),
                                  "first": auth[0]["author"]["display_name"] if auth else "",
                                  "venue": (it.get("primary_location") or {}).get("source", {}).get("display_name", ""),
                                  "abstract": ab})
except Exception as e:
    print("[OpenAlex-标题检索] ERR", e)

# 3) Semantic Scholar 重试（3 次）
for attempt in range(3):
    try:
        r = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{DOI}",
                         params={"fields": "title,abstract,year,venue,authors"},
                         headers=HEADERS, timeout=30)
        if r.status_code == 200:
            d = r.json()
            auth = d.get("authors") or []
            show("SemanticScholar", {"title": d.get("title"), "year": d.get("year"),
                                     "first": auth[0]["name"] if auth else "",
                                     "venue": d.get("venue"), "abstract": d.get("abstract") or ""})
            break
        print(f"[SemanticScholar] HTTP {r.status_code}（第{attempt+1}次）")
        time.sleep(3)
    except Exception as e:
        print(f"[SemanticScholar] ERR {e}")
        time.sleep(3)

# 4) Europe PMC 按标题
try:
    r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                     params={"query": TITLE[:80], "resultType": "core", "format": "json"},
                     headers=HEADERS, timeout=30)
    res = r.json().get("resultList", {}).get("result", [])
    for it in res[:2]:
        show("EuropePMC-标题", {"title": it.get("title"), "year": it.get("pubYear"),
                                "first": (it.get("authorString") or "").split(",")[0],
                                "venue": it.get("journalInfo", {}).get("journal", {}).get("title", ""),
                                "abstract": it.get("abstractText") or ""})
except Exception as e:
    print("[EuropePMC-标题] ERR", e)

# 5) Unpaywall OA 状态
try:
    r = requests.get(f"https://api.unpaywall.org/v2/{DOI}",
                     params={"email": "team@example.com"}, headers=HEADERS, timeout=30)
    if r.status_code == 200:
        d = r.json()
        loc = d.get("best_oa_location") or {}
        print(f"[Unpaywall] is_oa={d.get('is_oa')} | 标题={d.get('title','')[:80]}")
        print(f"   OA 链接: {loc.get('url_for_pdf') or loc.get('url') or '无'}")
    else:
        print(f"[Unpaywall] HTTP {r.status_code}")
except Exception as e:
    print("[Unpaywall] ERR", e)

# 6) Crossref 复核 + link 字段
try:
    r = requests.get(f"https://api.crossref.org/works/{requests.utils.quote(DOI)}",
                     headers=HEADERS, timeout=30)
    m = r.json().get("message", {})
    print(f"[Crossref] title={ (m.get('title') or [''])[0][:100] }")
    print(f"   abstract 有无: {bool(m.get('abstract'))} | link 字段: {[l.get('URL') for l in (m.get('link') or [])][:2]}")
except Exception as e:
    print("[Crossref] ERR", e)
