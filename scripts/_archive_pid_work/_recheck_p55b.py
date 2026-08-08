# -*- coding: utf-8 -*-
"""p55 最后两条通道：Elsevier API 链接 + Unpaywall(合法邮箱)"""
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:research@example.org)"}

# 1) Elsevier API 链接（Crossref link 字段，可能需 key）
url = "https://api.elsevier.com/content/article/PII:S0360544225011478?httpAccept=text/plain"
try:
    r = requests.get(url, headers=HEADERS, timeout=30)
    print(f"[Elsevier-API] HTTP {r.status_code}")
    if r.status_code == 200:
        txt = r.text
        print("  内容前 600 字:")
        print("  " + txt[:600].replace("\n", " "))
    else:
        print("  响应头提示:", r.headers.get("X-ELS-Status", ""), "| 体:", r.text[:120])
except Exception as e:
    print("[Elsevier-API] ERR", e)

# 2) Unpaywall（合法邮箱格式）
try:
    r = requests.get("https://api.unpaywall.org/v2/10.1016/j.energy.2025.135505",
                     params={"email": "research@example.org"}, headers=HEADERS, timeout=30)
    print(f"\n[Unpaywall] HTTP {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        loc = d.get("best_oa_location") or {}
        print(f"  is_oa={d.get('is_oa')} | title={d.get('title','')[:80]}")
        print(f"  OA: {loc.get('url_for_pdf') or loc.get('url') or '无'}")
    else:
        print("  体:", r.text[:150])
except Exception as e:
    print("[Unpaywall] ERR", e)
