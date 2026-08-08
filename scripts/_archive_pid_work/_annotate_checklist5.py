# -*- coding: utf-8 -*-
"""更新 p60/p118/p168/p169 四条核验记录"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
path = r"workspace/_pids_final_checklist.md"
txt = open(path, encoding="utf-8").read()

REC = {
    "p60": "✅OpenAlex 摘要命中 TVSA/DAC/参数优化（Ghiri 2025）→可回填",
    "p118": "✅同篇坐实（Lei 2022，摘要 Qst 27–52 kJ/mol）；建议合并为一条引用并人工复核 29/25–40 具体出处",
    "p168": "⚠️摘要命中水解离机理，但体系为 Al³⁺ 水溶液（非 MOF）——接受为机理证据则回填并注明体系，否则降级",
    "p169": "✅OpenAlex 摘要命中 Mg–Ni/Cd-MOF-74 混合金属+水吸附（Howe 2016）→可回填",
}

lines = txt.split("\n")
out = []
for ln in lines:
    m = re.match(r"(\| ☐ 待确认 \| (p\d+) \| `[^`]+` \| [^|]* \| [^|]* \| )([^|]*)( \|)$", ln)
    if m and m.group(2) in REC:
        ln = m.group(1) + REC[m.group(2)] + m.group(4)
    out.append(ln)
open(path, "w", encoding="utf-8").write("\n".join(out))
print("已更新 4 行")
