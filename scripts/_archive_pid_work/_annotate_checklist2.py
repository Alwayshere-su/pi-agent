# -*- coding: utf-8 -*-
"""把三步深核验（doi.org 解析 / Crossref 重检索 / p118 冲突）结果写回清单"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"workspace/_pids_final_checklist.md"
txt = open(path, encoding="utf-8").read()

REPL = {
    "p128": (
        "✅存在·弱吻合｜候选主题为 CeO2 吸附 CO2，与 MOF 水-CO₂ 衰减语境偏差大，建议重新检索",
        "✅存在·❌不匹配｜doi.org 确认为 CeO2 体系（TTU 仓储）；已换更优候选 10.3389/fmats.2022.825592（水导致柔性 MOF CO2 容量下降机理, Watanabe 2022, 强吻合）",
    ),
    "p52": (
        "✅存在·弱吻合｜flue gas impurities+VSA；非直接‘压缩能耗’，需确认",
        "✅存在·弱吻合｜doi.org 落地正常（Elsevier）；建议改用 10.1021/acs.iecr.5c04931（PSA 捕集技术经济+能耗, Karimi）或 10.1021/acsami.3c04079（湿烟气 MOF 高通量, 2023）",
    ),
    "p188": (
        "✅存在·弱吻合｜PTSA 天然气脱水建模，非 MOF CO₂ TSA；需确认或重新检索",
        "✅存在·弱吻合｜doi.org 落地正常（Springer）；建议改用 10.1021/acs.iecr.5b03727（TSA 后燃烧捕集多柱实验, Marx 2016）或 10.1021/acs.iecr.6b03887（TVSA DAC 系统设计, Sinha 2017）",
    ),
    "p139": (
        "✅存在·中吻合｜water co-adsorption 主题吻合，但体系为甲醛(Fe-HHTP-MOF)，CO₂ 语境需确认",
        "✅存在·中吻合｜doi.org 落地正常（ACS）；体系为甲醛(Fe-HHTP-MOF)，CO₂‘无竞争’语境仍待确认，如需更贴合候选建议按 water co-adsorption+CO2+MOF 再检索",
    ),
    "p118": (
        "✅存在·⚠冲突｜该 DOI 在 gap_report 已内联为 p27；需确认 p118 与 p27 是否同篇，避免重复引用",
        "✅存在·⚠冲突｜与 p27 同 DOI（MOF-74(Ni) Qst 调控, Lei 2022, JCIS）；疑似同篇，建议合并为一条引用，并人工确认‘29 甜点’与‘25–40 窗口’两值是否同出自此文",
    ),
}

for pid, (old, new) in REPL.items():
    if old in txt:
        txt = txt.replace(old, new)
    else:
        print("WARN 未找到替换目标:", pid)

deep = """

---

### 深核验结论（doi.org 实际解析 + Crossref 重检索，2026-08）

**步骤1 · doi.org 解析（15/15 全部可落地）**：p20/p52/p54/p55/p62/p118/p128/p185/p188 返回 200 且落地页标题可读；
p16/p60/p129/p139/p168/p169 返回 403（ACS/MDPI 反爬拦截），但落地 URL 均正确指向出版商页面，DOI 有效。

**步骤2 · 4 条弱匹配重检索**：
- p128 原候选（CeO2）确认不匹配，**更优候选** `10.3389/fmats.2022.825592`（水导致柔性 MOF CO2 容量下降机理，Watanabe 2022，强吻合）；
- p52 更优候选 `10.1021/acs.iecr.5c04931`（PSA 捕集技术经济与能耗，Karimi）；
- p188 更优候选 `10.1021/acs.iecr.5b03727`（TSA 后燃烧捕集多柱实验，Marx 2016）或 `10.1021/acs.iecr.6b03887`（TVSA DAC 系统设计，Sinha 2017）；
- p139 仍未命中强候选，建议按 `water co-adsorption CO2 MOF` 再检索或人工按 gap 语境定位。

**步骤3 · p118/p27 冲突**：两处引用指向同一篇论文（Lei 2022, JCIS, MOF-74(Ni) Qst 调控）——
疑似同一来源被引用两次（p27=29 kJ/mol 甜点，p118=25–40 kJ/mol 窗口），**建议合并为一条引用**
（或标注“同 p27（DOI: 10.1016/j.jcis.2021.12.163）”），并人工打开原文确认两个数值是否同出自此文。

> 红线不变：以上所有 DOI 均经 Crossref/DataCite/doi.org 核验真实存在，但“当初引用的就是它”仍须
> 人工打开原文确认后回填 gap_report（格式 `p#（DOI: xxx）`）；未确认前禁止当已确认引用。
"""

txt = txt.rstrip() + deep
open(path, "w", encoding="utf-8").write(txt)
print("已更新:", path)
