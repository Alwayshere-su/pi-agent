# -*- coding: utf-8 -*-
"""为 gap_report.md 中缺少 DOI 的 p# 引用补注可靠 DOI（来自 knowledge_graph 同体系映射）。

规则（红线安全）：
- 仅补 knowledge_graph.md 中与 gap_report 同编号体系的 p#(DOI)（已交叉核验）；
- 某 p# 出现处已含 DOI（后 30 字符内有 10.xxx）→ 跳过；
- 该 p# 无可靠 DOI → 跳过（保持原样，索引表已标注待人工）；
- 补注格式：p# 后已有中文括号 → 在括号开头插「DOI: xxx；」；
  无括号 → 追加「（DOI: xxx）」。
"""
import io
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAP = ROOT / 'workspace/outputs/literature_survey/gap_report.md'

# knowledge_graph 同体系 p#(DOI)（完整 DOI）
kg = io.open(ROOT / 'workspace/outputs/literature_survey/knowledge_graph.md', encoding='utf-8').read()
kg_map = {}
for m in re.finditer(r'p(\d+)\s*\(?(10\.\d{4,}[^\s)）\]\)]*)', kg):
    kg_map.setdefault(m.group(1), m.group(2))

text = io.open(GAP, encoding='utf-8').read()
backup = str(GAP) + '.pid_bak'
shutil.copy2(GAP, backup)
print('[备份] ->', backup)


def annotate(m):
    pid = m.group(1)
    tail = text[m.end():m.end() + 30]
    if re.search(r'10\.\d{4,}', tail):
        return m.group(0)  # 已带 DOI，跳过
    doi = kg_map.get(pid)
    if not doi:
        return m.group(0)  # 无可靠 DOI，跳过
    # 统一追加独立 DOI 括号（不侵入原文已有括号，避免结构破坏）
    return m.group(0) + '（DOI: %s）' % doi


new_text, n = re.subn(r'\bp(\d+)\b', annotate, text)
io.open(GAP, 'w', encoding='utf-8').write(new_text)

# 统计结果
pids_after = re.findall(r'\bp(\d+)\b', new_text)
with_doi = sum(1 for mm in re.finditer(r'\bp(\d+)\b', new_text)
               if re.search(r'10\.\d{4,}', new_text[mm.end():mm.end() + 40]))
print('补注完成: 处理 %d 处 | 补注后带 DOI 的 p# 出现: %d/%d' % (n, with_doi, len(pids_after)))
