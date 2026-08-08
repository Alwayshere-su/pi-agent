# -*- coding: utf-8 -*-
"""把机器核验结论（DOI 存在 + 主题吻合度）写回 _pids_final_checklist.md"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"workspace/_pids_final_checklist.md"
txt = open(path, encoding="utf-8").read()

# p# -> (机器核验判定, 备注)
VERDICT = {
    "p16": ("✅存在·中吻合", "2025 新文献（Humidity+Amine+DAC）；是否即‘水促进’所引需打开确认"),
    "p20": ("✅存在·高吻合", "Ni-DOBDC(=Ni-MOF-74) CO2 容量；需核对 8.29 数值是否出自该文"),
    "p52": ("✅存在·弱吻合", "flue gas impurities+VSA；非直接‘压缩能耗’，需确认"),
    "p55": ("✅存在·中吻合", "energy penalty+low CO2 content；2025 新，需确认"),
    "p54": ("✅存在·弱吻合", "DataCite 会议视频（Underline MH21），非期刊论文；SBA-15+PEI 需确认"),
    "p60": ("✅存在·高吻合", "Dynamic Temperature–Vacuum Swing Adsorption for DAC"),
    "p62": ("✅存在·高吻合", "NiCo-MOF-74 微波合成+CO2（与 v3s0/Chen 2023 同源）"),
    "p118": ("✅存在·⚠冲突", "该 DOI 在 gap_report 已内联为 p27；需确认 p118 与 p27 是否同篇，避免重复引用"),
    "p128": ("✅存在·弱吻合", "候选主题为 CeO2 吸附 CO2，与 MOF 水-CO₂ 衰减语境偏差大，建议重新检索"),
    "p129": ("✅存在·高吻合", "SBA-15 + isosteric enthalpy；与 gap_report 内联同 DOI 一致"),
    "p139": ("✅存在·中吻合", "water co-adsorption 主题吻合，但体系为甲醛(Fe-HHTP-MOF)，CO₂ 语境需确认"),
    "p168": ("✅存在·中吻合", "水辅助质子解离 DFT 机理，体系需打开核验"),
    "p169": ("✅存在·高吻合", "Mixed-Metal MOF-74 金属分布+水吸附，对应‘混合金属偏好+水稳’"),
    "p185": ("✅存在·高吻合", "M-MOF-74 分子模拟 CO2 吸附分离"),
    "p188": ("✅存在·弱吻合", "PTSA 天然气脱水建模，非 MOF CO₂ TSA；需确认或重新检索"),
}

header = "| 状态 | p# | gap 上下文 | 候选 DOI（已核验存在） | 判定 | 机器核验（本次） | 确认后回填? |"
sep = "|------|----|-----------|----------------------|------|-----------------|------------|"

lines = txt.split("\n")
out = []
in_table = False
for ln in lines:
    if ln.startswith("| 状态 | p#"):
        in_table = True
        out.append(header)
        continue
    if in_table and ln.startswith("|---"):
        out.append(sep)
        continue
    if in_table:
        m = re.match(r"\| ☐ 待确认 \| (p\d+) \| ([^|]*) \| `([^`]+)` \| ([^|]*) \| ([^|]*) \|", ln)
        if m:
            pid, ctx, doi, judge, backfill = m.groups()
            v, note = VERDICT.get(pid, ("?", ""))
            out.append(f"| ☐ 待确认 | {pid} | {ctx} | `{doi}` | {judge} | {v}｜{note} | {backfill} |")
            continue
        # 表格结束
        if not ln.strip().startswith("|"):
            in_table = False
    out.append(ln)

open(path, "w", encoding="utf-8").write("\n".join(out))
print("已更新:", path)
