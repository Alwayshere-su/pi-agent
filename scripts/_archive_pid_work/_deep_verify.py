# -*- coding: utf-8 -*-
"""三步深核验：1) doi.org 解析 15 个 DOI  2) 4 条弱匹配 p# Crossref 重检索  3) p118/p27 冲突核对
运行：python scripts/_deep_verify.py（需要网络）
"""
import json
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}
DOIS = {
    "p16": "10.1021/acsestengg.4c00503",
    "p20": "10.61511/eam.v2i2.2024.1431",
    "p52": "10.1016/j.egypro.2009.01.147",
    "p55": "10.1016/j.energy.2025.135505",
    "p54": "10.48448/dcn4-gz78",
    "p60": "10.3390/su17156796",
    "p62": "10.1016/j.efmat.2023.01.002",
    "p118": "10.1016/j.jcis.2021.12.163",
    "p128": "10.32865/2346/108905",
    "p129": "10.3390/jcs5040102",
    "p139": "10.1021/acsomega.4c06322",
    "p168": "10.1021/acsearthspacechem.7b00142",
    "p169": "10.1021/acs.jpcc.6b11719",
    "p185": "10.46690/capi.2023.01.02",
    "p188": "10.1007/s10450-017-9924-z",
}


def resolve_doi(doi):
    try:
        r = requests.get(
            f"https://doi.org/{requests.utils.quote(doi)}",
            headers=HEADERS,
            allow_redirects=True,
            timeout=30,
        )
        final = r.url
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()[:100]
        return r.status_code, final[:120], title
    except Exception as e:
        return "ERR", str(e)[:80], ""


def crossref_search(query, rows=5):
    try:
        r = requests.get(
            "https://api.crossref.org/works",
            params={
                "query.bibliographic": query,
                "rows": rows,
                "select": "DOI,title,author,issued,container-title",
                "mailto": "team@example.com",
            },
            headers=HEADERS,
            timeout=30,
        )
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("message", {}).get("items", []):
            title = (it.get("title") or [""])[0]
            year = None
            for k in ("published-print", "published-online", "issued", "created"):
                if it.get(k, {}).get("date-parts"):
                    year = it[k]["date-parts"][0][0]
                    break
            auth = it.get("author") or []
            first = auth[0].get("family", "") if auth else ""
            cont = (it.get("container-title") or [""])[0]
            out.append((it.get("DOI"), title[:90], year, first, cont[:50]))
        return out
    except Exception as e:
        return [("ERR", str(e)[:80], None, "", "")]


print("=" * 70)
print("步骤1：doi.org 解析核验（状态码 + 落地页 URL + 页面标题）")
print("=" * 70)
step1 = {}
for pid, doi in DOIS.items():
    code, final, title = resolve_doi(doi)
    step1[pid] = {"doi": doi, "status": code, "url": final, "title": title}
    print(f"[{pid}] HTTP {code} | {doi}")
    print(f"        -> {final}")
    if title:
        print(f"        页题: {title}")
    time.sleep(0.5)

print()
print("=" * 70)
print("步骤2：4 条弱匹配 p# Crossref 重检索（更优候选 Top5）")
print("=" * 70)
QUERIES = {
    "p52": "CO2 capture energy penalty low purity flue gas compression MOF",
    "p128": "water vapor effect CO2 adsorption capacity decline metal organic framework",
    "p139": "water co-adsorption CO2 metal organic framework no competition",
    "p188": "temperature swing adsorption dynamic simulation CO2 capture MOF",
}
step2 = {}
for pid, q in QUERIES.items():
    print(f"\n[{pid}] 检索式: {q}")
    res = crossref_search(q)
    step2[pid] = res
    for doi, t, y, a, c in res:
        print(f"  - {doi} | {t} | {y} | {a} | {c}")
    time.sleep(0.6)

print()
print("=" * 70)
print("步骤3：p118/p27 冲突核对（同一 DOI 10.1016/j.jcis.2021.12.163）")
print("=" * 70)
try:
    r = requests.get(
        "https://api.crossref.org/works/10.1016%2Fj.jcis.2021.12.163",
        headers=HEADERS,
        timeout=30,
    )
    m = r.json().get("message", {})
    print("title:", (m.get("title") or [""])[0])
    print("authors:", ", ".join(a.get("family", "") for a in (m.get("author") or []))[:120])
    print("year:", m.get("issued", {}).get("date-parts"))
    print("abstract 前 400 字:", (m.get("abstract") or "（Crossref 无摘要）")[:400])
    step3 = m
except Exception as e:
    print("ERR", e)
    step3 = {"err": str(e)}

with open(r"workspace/_deep_verify_results.json", "w", encoding="utf-8") as fh:
    json.dump({"step1": step1, "step2": step2, "step3_abstract": str(step3)[:2000]}, fh, ensure_ascii=False, indent=2)
print()
print("结果已写入 workspace/_deep_verify_results.json")
