# -*- coding: utf-8 -*-
"""核验 15 个候选 DOI：Crossref works 优先，DataCite 兜底；输出元数据与标题吻合度
运行：python scripts/_verify_dois.py（需要网络）
"""
import json
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DOIS = [
    "10.1021/acsestengg.4c00503",     # p16
    "10.61511/eam.v2i2.2024.1431",    # p20
    "10.1016/j.egypro.2009.01.147",   # p52
    "10.1016/j.energy.2025.135505",   # p55
    "10.48448/dcn4-gz78",             # p54
    "10.3390/su17156796",             # p60
    "10.1016/j.efmat.2023.01.002",    # p62
    "10.1016/j.jcis.2021.12.163",     # p118
    "10.32865/2346/108905",           # p128
    "10.3390/jcs5040102",             # p129
    "10.1021/acsomega.4c06322",       # p139
    "10.1021/acsearthspacechem.7b00142",  # p168
    "10.1021/acs.jpcc.6b11719",       # p169
    "10.46690/capi.2023.01.02",       # p185
    "10.1007/s10450-017-9924-z",      # p188
]

HEADERS = {
    "User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)",
}


def get_json(url, timeout=30):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    if r.status_code == 200:
        try:
            return r.json(), r.status_code
        except Exception:
            return None, r.status_code
    return None, r.status_code


def crossref(doi):
    d, code = get_json(f"https://api.crossref.org/works/{requests.utils.quote(doi)}")
    if code != 200 or not d:
        return None, code
    m = d.get("message", {})
    title = (m.get("title") or [""])[0]
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        if m.get(k, {}).get("date-parts"):
            year = m[k]["date-parts"][0][0]
            break
    auth = m.get("author") or []
    first = auth[0].get("family", "") if auth else ""
    container = (m.get("container-title") or [""])[0]
    return {
        "agency": "crossref",
        "title": title,
        "year": year,
        "first_author": first,
        "container": container,
        "url": m.get("URL"),
    }, code


def datacite(doi):
    d, code = get_json(f"https://api.datacite.org/dois/{requests.utils.quote(doi)}")
    if code != 200 or not d:
        return None, code
    a = d.get("data", {}).get("attributes", {})
    title = (a.get("titles") or [{}])[0].get("title", "")
    year = a.get("publicationYear")
    creators = a.get("creators") or []
    first = (creators[0].get("name") or "") if creators else ""
    return {
        "agency": "datacite",
        "title": title,
        "year": year,
        "first_author": first,
        "container": (a.get("publisher") or ""),
        "url": a.get("url"),
    }, code


def tokens(s):
    return set(re.findall(r"[a-z0-9]{3,}", (s or "").lower()))


results = []
for i, doi in enumerate(DOIS):
    meta, code = crossref(doi)
    src = "crossref"
    if meta is None:
        meta, code2 = datacite(doi)
        src = "datacite"
        code = code2
    if meta:
        results.append({"p_idx": i + 1, "doi": doi, "status": "found", "source": src, **meta})
        t = meta["title"]
        print(f"[{i+1:2d}] OK  {doi}  ({src})")
        print(f"      title : {t[:110]}")
        print(f"      year  : {meta['year']} | author: {meta['first_author']} | venue: {meta['container'][:60]}")
    else:
        results.append({"p_idx": i + 1, "doi": doi, "status": f"not_found({code})", "source": src})
        print(f"[{i+1:2d}] FAIL {doi}  ({src}, HTTP {code})")
    time.sleep(0.4)

with open(r"workspace/_doi_verify_results.json", "w", encoding="utf-8") as fh:
    json.dump(results, fh, ensure_ascii=False, indent=2)
print()
print("已写入 workspace/_doi_verify_results.json")
