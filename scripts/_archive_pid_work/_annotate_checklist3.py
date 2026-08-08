# -*- coding: utf-8 -*-
"""把 5 条复核结果写回清单（p52/p55/p62/p185/p188）"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"workspace/_pids_final_checklist.md"
txt = open(path, encoding="utf-8").read()

REPL = {
    "p52": (
        "✅存在·弱吻合｜doi.org 落地正常（Elsevier）；建议改用 10.1021/acs.iecr.5c04931（PSA 捕集技术经济+能耗, Karimi）或 10.1021/acsami.3c04079（湿烟气 MOF 高通量, 2023）",
        "✅复核通过（OpenAlex 摘要命中 VPSA/能耗/技术经济，体系为 MOF MIL-160(Al)，Karimi 2026）→ 可回填",
    ),
    "p55": (
        "✅存在·中吻合｜energy penalty+low CO2 content；2025 新，需确认",
        "⚠️标题吻合（低浓度 CO₂ 能耗降低, Verhaeghe 2025）；摘要仍不可得（OpenAlex/EuropePMC 均无），需人工打开全文复核",
    ),
    "p62": (
        "✅存在·高吻合｜NiCo-MOF-74 微波合成+CO2（与 v3s0/Chen 2023 同源）",
        "✅✅复核通过（OpenAlex 摘要数值命中 8.30/3.99/5.03，Chen 2022）→ 确认回填",
    ),
    "p185": (
        "✅存在·高吻合｜M-MOF-74 分子模拟 CO2 吸附分离",
        "✅复核通过（OpenAlex 摘要命中 M-MOF-74 分子模拟/OMS，Deng 2023）→ 可回填",
    ),
    "p188": (
        "✅存在·弱吻合｜doi.org 落地正常（Springer）；建议改用 10.1021/acs.iecr.5b03727（TSA 后燃烧捕集多柱实验, Marx 2016）或 10.1021/acs.iecr.6b03887（TVSA DAC 系统设计, Sinha 2017）",
        "⚠️复核发现体系为沸石 13X 非 MOF（Marx 2016，摘要明写 zeolite 13X）；与 Gap7 Mg-MOF-74 TSA 语境不符，建议换候选（如 TVSA DAC 的 Sinha 2017）或降级",
    ),
}

for pid, (old, new) in REPL.items():
    if old in txt:
        txt = txt.replace(old, new)
    else:
        print("WARN 未找到替换目标:", pid)

extra = """

**5 条复核（OpenAlex 摘要重建 + Europe PMC，2026-08）**：
- p62/p52/p185 摘要级确认（p62 含 8.30/3.99/5.03 数值）→ 可回填；
- p55 标题吻合但摘要不可得 → 唯一需人工打开全文复核；
- p188 复核发现体系为沸石 13X（非 MOF）→ 与 Gap7 语境不符，建议换候选或降级。
"""
txt = txt.rstrip() + extra
open(path, "w", encoding="utf-8").write(txt)
print("已更新:", path)
