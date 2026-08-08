# -*- coding: utf-8 -*-
"""按行更新 v2 清单中 p52/p55/p62/p185/p188 的核验记录列"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"workspace/_pids_final_checklist.md"
txt = open(path, encoding="utf-8").read()

REC = {
    "p52": "✅OpenAlex 摘要命中 VPSA/能耗/技术经济（MOF MIL-160(Al)，Karimi 2026）→可回填",
    "p55": "⚠️OpenAlex/EuropePMC 均无摘要，需人工打开全文复核",
    "p62": "✅✅OpenAlex 摘要数值命中 8.30/3.99/5.03（Chen 2022）→确认回填",
    "p185": "✅OpenAlex 摘要命中 M-MOF-74 分子模拟/OMS（Deng 2023）→可回填",
    "p188": "⚠️摘要明写 zeolite 13X（非 MOF），与 Gap7 Mg-MOF-74 TSA 语境不符→建议换候选/降级",
}

lines = txt.split("\n")
out = []
for ln in lines:
    m = re.match(r"(\| ☐ 待确认 \| (p\d+) \| `[^`]+` \| [^|]* \| [^|]* \| )([^|]*)( \|)$", ln)
    if m and m.group(2) in REC:
        ln = m.group(1) + REC[m.group(2)] + m.group(4)
    out.append(ln)

open(path, "w", encoding="utf-8").write("\n".join(out))
print("已更新 5 行核验记录")
