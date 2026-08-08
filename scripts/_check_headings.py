# -*- coding: utf-8 -*-
"""检查新生成文档的标题格式一致性"""
import os
import sys

import docx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = [
    f
    for f in os.listdir(".")
    if f.endswith(".docx")
    and not f.startswith("~$")
    and "reserach" not in f
    and "模板填写" not in f
][0]
print("CHECKING:", path)
d = docx.Document(path)

empty = []
for p in d.paragraphs:
    if p.style and p.style.name.startswith("Heading"):
        if not p.text.strip():
            empty.append((p.style.name, len(p.runs)))
        else:
            runs = []
            for r in p.runs:
                rPr = r._r.rPr
                ea = None
                if rPr is not None and rPr.rFonts is not None:
                    ea = rPr.rFonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia")
                col = None
                try:
                    col = r.font.color.rgb if r.font.color and r.font.color.type is not None else None
                except Exception:
                    pass
                runs.append(
                    (r.font.name, ea, r.font.size.pt if r.font.size else None, r.font.bold, str(col))
                )
            print(f"[{p.style.name}] {p.text.strip()[:26]!r} -> {runs}")
print("EMPTY HEADINGS:", empty if empty else "none")
