# -*- coding: utf-8 -*-
"""校验生成的《材料科学文献调研Agent_算法赛初赛方案.docx》"""
import glob
import os
import sys

import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

files = [
    f
    for f in os.listdir(".")
    if f.endswith(".docx") and not f.startswith("~$") and "reserach" not in f and "模板填写" not in f
]
path = files[0]
print("VERIFYING:", path)
d = docx.Document(path)


def iter_block_items(parent):
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


required = [
    "一、项目概述", "1.1 项目名称", "1.2 参赛方向", "1.3 方案概述",
    "二、科学问题理解", "2.1 科学问题与研究对象", "2.2 科学意义",
    "三、技术方案与预期方法路线", "3.1 技术方案", "3.2 预期方法路线",
    "3.3 数据来源、依赖工具与运行流程",
    "四、阶段性实验结果或可行性验证", "4.1 阶段性实验或可行性验证", "4.2 当前结果",
    "五、复现与开放计划", "5.1 复现方式", "5.2 开源计划", "5.3 依赖、数据来源与合规披露",
    "六、团队介绍", "6.1 成员背景", "6.2 团队分工", "6.3团队成果",
]
heads = [
    blk.text.strip()
    for blk in iter_block_items(d)
    if isinstance(blk, Paragraph) and blk.style and blk.style.name.startswith("Heading")
]
missing = [h for h in required if h not in heads]
print("MISSING HEADINGS:", missing if missing else "none")
print("HEADINGS COUNT:", len(heads))

leftover = [
    blk.text.strip()
    for blk in iter_block_items(d)
    if isinstance(blk, Paragraph) and ("应说明" in blk.text or "呈现建议" in blk.text)
]
print("LEFTOVER TEMPLATE PROMPTS:", leftover if leftover else "none")

n_tables = 0
for blk in iter_block_items(d):
    if isinstance(blk, Table):
        n_tables += 1
        widths = []
        for c in blk.rows[0].cells:
            try:
                widths.append(round(c.width.cm, 2))
            except Exception:
                widths.append(None)
        print(
            f"TABLE {n_tables}: {len(blk.rows)}x{len(blk.columns)} "
            f"widths_cm={widths} sum={sum(w for w in widths if w)}"
        )
print("TOTAL TABLES:", n_tables)

cjk = 0
for blk in iter_block_items(d):
    if isinstance(blk, Paragraph):
        if blk.style and blk.style.name.startswith("Heading"):
            continue
        cjk += sum(1 for ch in blk.text if "\u4e00" <= ch <= "\u9fff")
print("CJK chars in prose paragraphs:", cjk)

for sec in d.sections:
    for fp in sec.footer.paragraphs:
        if fp.text.strip():
            print("FOOTER:", fp.text.strip())

# ---- dump full body for review ----
out = []
for i, blk in enumerate(iter_block_items(d)):
    if isinstance(blk, Paragraph):
        st = blk.style.name if blk.style else "?"
        out.append(f"[{i}] {st} | {blk.text}")
    else:
        out.append(f"[{i}] TABLE {len(blk.rows)}x{len(blk.columns)}:")
        for r in blk.rows:
            out.append(
                "    | " + " || ".join(c.text.strip().replace(chr(10), " ")[:40] for c in r.cells)
            )
with open("_final_dump2.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("dump written to _final_dump2.txt")
