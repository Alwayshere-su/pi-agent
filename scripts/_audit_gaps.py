# -*- coding: utf-8 -*-
"""核验 gap_report.md 各 Gap 的置信度与证据标识数"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"workspace/outputs/literature_survey/gap_report.md"
txt = open(path, encoding="utf-8").read()

sections = re.split(r"\n(?=## Gap )", txt)
pat = re.compile(r"p\d+|r\d+s\d+_\w+|scv:[\w]+|10\.\d{4}/[\w./\-]+")

print("=== 各 Gap 段落的置信度行与证据标识数 ===")
total_refs = 0
per_gap = []
for sec in sections:
    if not sec.startswith("## Gap"):
        continue
    title = sec.split("\n", 1)[0].replace("## ", "")[:40]
    body = sec
    confs = []
    for m in re.finditer(r"置信度[：:]([^\n｜|]*)", body):
        confs.append(m.group(1).strip()[:40])
    refs = set(pat.findall(body))
    per_gap.append(len(refs))
    total_refs += len(refs)
    print(f"{title:44s} conf={confs} refs={len(refs)}")

if per_gap:
    s = sorted(per_gap)
    n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    print()
    print("Gap 数:", n, "| 每 Gap refs:", per_gap)
    print("min:", min(per_gap), "| max:", max(per_gap), "| median:", med, "| total:", total_refs, "| mean:", round(total_refs / n, 2))

print()
print("=== 优先级排序表（文件后半部分）置信度 ===")
for m in re.finditer(r"\| (\d+) \| ([^|]+?) \| (高|中|低|中→高|中 → 高) \| ([\d.]+)", txt):
    print(f"  rank {m.group(1)}: {m.group(2).strip()[:24]} | {m.group(3)} | {m.group(4)}")
