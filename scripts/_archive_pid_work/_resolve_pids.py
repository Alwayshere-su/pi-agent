# -*- coding: utf-8 -*-
"""提取断链 p# 的上下文，并从 papers_pid_index.json 生成候选匹配（只读，不猜测）
输出：workspace/_pids_worksheet.md
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGETS = [16, 20, 52, 54, 55, 60, 62, 118, 128, 129, 139, 168, 169, 185, 188]

gap = open(r"workspace/outputs/literature_survey/gap_report.md", encoding="utf-8").read()
ctx = {t: [] for t in TARGETS}

# gap_report 中每个 p# 的上下文（所在 Gap 段 + 所在行）
sec_title = ""
for line in gap.split("\n"):
    if line.startswith("## "):
        sec_title = line[3:].strip()[:30]
    for t in TARGETS:
        if re.search(rf"\bp{t}\b", line):
            ctx[t].append(f"[{sec_title}] {line.strip()[:160]}")

# memory/survey 中的上下文
import glob

for f in glob.glob(r"workspace/memory/survey/*.md"):
    for line in open(f, encoding="utf-8").read().split("\n"):
        for t in TARGETS:
            if re.search(rf"\bp{t}\b", line):
                ctx[t].append(f"[memory:{f.split(chr(92))[-1]}] {line.strip()[:160]}")

idx = json.load(open(r"workspace/outputs/literature_survey/papers_pid_index.json", encoding="utf-8"))

out = []
out.append("# p# 断链补全工作底稿（候选=需人工核验，禁止直接引用）")
out.append("")
for t in TARGETS:
    out.append(f"## p{t}")
    out.append("### 上下文")
    for c in ctx[t][:6]:
        out.append(f"- {c}")
    if not ctx[t]:
        out.append("- （仓库内无上下文，需按 Gap 语境人工检索）")
    out.append("### 候选（来自 papers_pid_index.json，编号体系不同，按标题/摘要语义匹配）")
    out.append("- （待人工用上下文关键词在此索引中匹配，见下）")
    out.append("")

open(r"workspace/_pids_worksheet.md", "w", encoding="utf-8").write("\n".join(out))

# 同时输出索引中可能相关的条目（按目标词弱匹配，仅作人工筛选提示）
kw = ["molecular simulation", "TSA", "breakthrough", "water", "VPSA", "regeneration",
      "DAC", "direct air capture", "Qst", "isosteric", "NO2", "SO2", "stability",
      "dynamic", "adsorption", "humidity", "M-MOF-74"]
print("索引中与目标主题相关的条目（人工筛选用）：")
for k, v in idx.items():
    blob = (v.get("title", "") + " " + v.get("abstract", "")).lower()
    hits = [w for w in kw if w.lower() in blob]
    if len(hits) >= 2:
        print(f"  {k} | doi={v.get('doi')} | title={v.get('title')[:80]}")

print()
print("工作底稿已写入 workspace/_pids_worksheet.md")
