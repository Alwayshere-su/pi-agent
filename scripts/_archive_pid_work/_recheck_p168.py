# -*- coding: utf-8 -*-
"""重试获取 p168/p169 摘要（OpenAlex+S2，多次重试）"""
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HEADERS = {"User-Agent": "PiAgent-PID-Verify/1.0 (mailto:team@example.com)"}


def get(url, params=None, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                return r
            return None
        except Exception as e:
            time.sleep(2.5)
    return None


def fetch_ab(doi):
    r = get(f"https://api.openalex.org/works/doi:{doi}")
    if r:
        inv = r.json().get("abstract_inverted_index")
        if inv:
            pos = {}
            for w, idxs in inv.items():
                for i in idxs:
                    pos[i] = w
            return "openalex", " ".join(pos[i] for i in sorted(pos))
    r = get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}", params={"fields": "abstract"})
    if r and r.json().get("abstract"):
        return "semanticscholar", r.json()["abstract"]
    return None, ""


for pid, doi in [("p168", "10.1021/acsearthspacechem.7b00142"),
                 ("p169", "10.1021/acs.jpcc.6b11719")]:
    src, ab = fetch_ab(doi)
    print("=" * 60)
    print(f"[{pid}] {doi} | 摘要来源: {src or '无'} | 长度 {len(ab)}")
    if ab:
        print("  ", ab[:400])
        low = ab.lower()
        print("  体系线索: Al/铝=", "aluminum" in low or " al" in low, "| 水溶液=", "aqueous" in low,
              "| MOF=", "mof" in low or "metal-organic" in low,
              "| 混合金属=", "mixed-metal" in low or "mixed metal" in low,
              "| 水吸附=", "water adsorption" in low)
    else:
        print("  摘要仍不可得（网络/无收录）")
