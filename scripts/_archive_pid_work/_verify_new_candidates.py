# -*- coding: utf-8 -*-
"""核验步骤2提出的新候选 DOI 存在性与元数据"""
import json
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CAND = {
    "p128_new": "10.3389/fmats.2022.825592",
    "p52_new": "10.1021/acs.iecr.5c04931",
    "p52_alt": "10.1021/acsami.3c04079",
    "p188_new": "10.1021/acs.iecr.5b03727",
    "p188_alt": "10.1021/acs.iecr.6b03887",
}
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}

for tag, doi in CAND.items():
    r = requests.get(
        f"https://api.crossref.org/works/{requests.utils.quote(doi)}",
        headers=HEADERS,
        timeout=30,
    )
    if r.status_code != 200:
        print(f"[{tag}] FAIL HTTP {r.status_code} {doi}")
        continue
    m = r.json().get("message", {})
    title = (m.get("title") or [""])[0]
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        if m.get(k, {}).get("date-parts"):
            year = m[k]["date-parts"][0][0]
            break
    auth = m.get("author") or []
    first = auth[0].get("family", "") if auth else ""
    cont = (m.get("container-title") or [""])[0]
    print(f"[{tag}] OK {doi}")
    print(f"        {title[:100]} | {year} | {first} | {cont[:50]}")
    time.sleep(0.4)
