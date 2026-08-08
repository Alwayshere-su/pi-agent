# -*- coding: utf-8 -*-
"""
将《材料科学文献调研Agent_算法赛初赛方案.docx》渲染为逐页 PNG（供对话内预览）。
流程：Word COM 后台导出 PDF -> PyMuPDF 渲染 PNG（150 dpi）。
输出目录：可视化目录（Codex 桌面线程可写）。
运行：python scripts/_render_docx_pages.py
"""
import os
import sys

os.chdir(r"D:\MMLL\4.competition\2026GOAI-3")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_DIR = r"C:\Users\su\.codex\visualizations\2026\08\08\019fe087-6c63-7543-b4f7-79392388ad7b\docx_pages"
os.makedirs(OUT_DIR, exist_ok=True)

fname = [x for x in os.listdir(".") if x.endswith(".docx") and "reserach" not in x][0]
docx_path = os.path.abspath(fname)
pdf_path = os.path.join(OUT_DIR, "plan_preview.pdf")

import win32com.client  # noqa: E402

word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    doc = word.Documents.Open(docx_path, ReadOnly=True)
    doc.ExportAsFixedFormat(pdf_path, 17)  # wdExportFormatPDF
    doc.Close(False)
finally:
    word.Quit()

import fitz  # PyMuPDF  # noqa: E402

pdf = fitz.open(pdf_path)
print("pages:", pdf.page_count)
for i, page in enumerate(pdf):
    pix = page.get_pixmap(dpi=150)
    png = os.path.join(OUT_DIR, f"page-{i+1:02d}.png")
    pix.save(png)
    print("saved", png)
