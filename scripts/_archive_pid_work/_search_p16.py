# -*- coding: utf-8 -*-
"""为 p16（水促进·胺型，早期引用）检索 2010s 早期候选"""
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

QUERIES = [
    "water enhances CO2 adsorption amine functionalized metal organic framework",
    "humidity improves CO2 uptake metal organic framework",
    "water vapor promotes CO2 capture metal organic framework",
    "water beneficial CO2 adsorption amine MOF humidity",
]


def search(q, rows=6):
    r = requests.get(
        "https://api.crossref.org/works",
        params={"query.bibliographic": q, "rows": rows,
                "select": "DOI,title,author,issued,container-title", "mailto": "team@example.com"},
        headers=HEADERS,
        timeout=30,
    )
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
        out.append((it.get("DOI"), (it.get("title") or [""])[0][:90], year, first,
                    (it.get("container-title") or [""])[0][:45]))
    return out


seen = set()
for q in QUERIES:
    print(f"\n=== {q} ===")
    for doi, t, y, a, c in search(q):
        if doi in seen:
            continue
        seen.add(doi)
        tag = "←早期" if (y and y <= 2020) else ""
        print(f"  - {doi} | {t} | {y} | {a} | {c} {tag}")
    time.sleep(0.6)
