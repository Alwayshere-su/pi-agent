# -*- coding: utf-8 -*-
"""核验 p188 新候选 Peh 2022 (10.1016/j.ces.2021.117399)：元数据 + OpenAlex 摘要"""
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}
DOI = "10.1016/j.ces.2021.117399"

r = requests.get(f"https://api.openalex.org/works/doi:{DOI}", headers=HEADERS, timeout=30)
print("OpenAlex HTTP", r.status_code)
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
    auth = d.get("authorships") or []
    print("title:", d.get("title"))
    print("year:", d.get("publication_year"), "| first:", auth[0]["author"]["display_name"] if auth else "")
    print("venue:", (d.get("primary_location") or {}).get("source", {}).get("display_name", ""))
    print("abstract(%d): %s" % (len(ab), ab[:400]))
    low = ab.lower()
    print("关键词: MOF=%s TSA=%s temperature swing=%s CO2=%s" % (
        "metal-organic" in low or "mof" in low, "tsa" in low, "temperature swing" in low, "co2" in low or "carbon dioxide" in low))
