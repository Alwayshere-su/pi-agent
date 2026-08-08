# -*- coding: utf-8 -*-
"""为 p188（Gap7 MOF TSA 动态）检索 MOF 体系的 TSA 候选，并核验 Sinha 2017 备选体系"""
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

QUERIES = [
    "temperature swing adsorption metal organic framework CO2 dynamic modeling",
    "Mg-MOF-74 temperature swing adsorption regeneration",
    "TSA simulation MOF CO2 capture regeneration energy",
]


def search(q, rows=6):
    r = requests.get(
        "https://api.crossref.org/works",
        params={"query.bibliographic": q, "rows": rows,
                "select": "DOI,title,author,issued,container-title", "mailto": "team@example.com"},
        headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return []
    out = []
    for it in r.json().get("message", {}).get("items", []):
        year = None
        for k in ("published-print", "published-online", "issued", "created"):
            if it.get(k, {}).get("date-parts"):
                year = it[k]["date-parts"][0][0]
                break
        auth = it.get("author") or []
        first = auth[0].get("family", "") if auth else ""
        out.append((it.get("DOI"), (it.get("title") or [""])[0][:95], year, first,
                    (it.get("container-title") or [""])[0][:45]))
    return out


def meta(doi):
    r = requests.get(f"https://api.crossref.org/works/{requests.utils.quote(doi)}",
                     headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return None
    return r.json().get("message", {})


seen = set()
for q in QUERIES:
    print(f"\n=== {q} ===")
    for doi, t, y, a, c in search(q):
        if doi in seen:
            continue
        seen.add(doi)
        tag = ""
        if "mof" in t.lower() or "metal-organic" in t.lower():
            tag = " ←MOF"
        print(f"  - {doi} | {t} | {y} | {a} | {c}{tag}")
    time.sleep(0.6)

# 核验备选 Sinha 2017 的体系
print("\n=== 备选 10.1021/acs.iecr.6b03887（Sinha 2017）元数据 ===")
m = meta("10.1021/acs.iecr.6b03887")
if m:
    print("  title:", (m.get("title") or [""])[0][:120])
    print("  authors:", ", ".join(a.get("family", "") for a in (m.get("author") or []))[:100])
    print("  year:", m.get("issued", {}).get("date-parts"))
    print("  abstract:", (m.get("abstract") or "（无）")[:260])
else:
    print("  查询失败")
