# -*- coding: utf-8 -*-
"""compile_route_a_pdf.py — 将 Route A Markdown 文档编译为 PDF

链路：Markdown → pandoc → Jinja2 模板 → .tex → tectonic → .pdf
"""

import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
PANDOC = os.path.join(ROOT, 'vendor', 'pandoc', 'pandoc-3.10.1', 'pandoc.exe')
TECTONIC = os.path.join(ROOT, 'vendor', 'tectonic', 'tectonic.exe')
TEMPLATE = os.path.join(ROOT, 'scripts', 'templates', 'route_a.tex.j2')
OUTPUTS = os.path.join(ROOT, 'workspace', 'outputs')
DATE = '2026-08'


def preprocess_md(text: str) -> str:
    """Markdown 预处理。"""
    # --- 在表格后的空行间被 pandoc 误解析为表格分隔符 → 换成 ***
    text = re.sub(r'\n\n---\n', r'\n\n***\n', text)
    return text


def run_pandoc(md_path: str) -> str:
    """pandoc markdown → latex body。"""
    raw = open(md_path, encoding='utf-8').read()
    raw = preprocess_md(raw)
    cmd = [PANDOC, '-f', 'markdown-yaml_metadata_block', '-t', 'latex', '--wrap=none']
    r = subprocess.run(cmd, input=raw, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError(f'pandoc failed: {r.stderr[:500]}')
    return r.stdout


def cleanup_route_a(latex: str) -> str:
    """Route A 专用 LaTeX 后处理。"""
    # 删除 pandoc 插入的 \begin{titlepage}...\end{titlepage}（我们用模板的 title）
    latex = re.sub(r'\\begin\{titlepage\}.*?\\end\{titlepage\}', '', latex, flags=re.DOTALL)
    # 删除 pandoc 生成的 \hypertarget 锚点（空标签）
    latex = re.sub(r'\\hypertarget\{[^}]*\}\{\}', '', latex)
    # \\[...\\] 内联 display math → 保持
    # 压缩空行
    latex = re.sub(r'\n{3,}', '\n\n', latex)
    return latex.strip()


def build_tex(body: str, title: str) -> str:
    """将 body 填入模板。"""
    template = open(TEMPLATE, encoding='utf-8').read()
    tex = template.replace('{{ title }}', title).replace('{{ date }}', DATE).replace('{{ body }}', body)
    return tex


def compile_pdf(tex_path: str) -> bool:
    """tectonic 编译 PDF。在 .tex 所在目录运行以解决相对路径问题。"""
    cwd = os.path.dirname(tex_path)
    tex_name = os.path.basename(tex_path)
    cmd = [TECTONIC, '-Z', 'search-path=.', tex_name]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        # 打印最后 20 行错误
        lines = r.stderr.strip().split('\n')
        print('  Tectonic errors (last 20):', file=sys.stderr)
        for line in lines[-20:]:
            print(f'    {line}', file=sys.stderr)
        return False
    return True


def main():
    docs = [
        {
            'md': os.path.join(OUTPUTS, 'ROUTE_A_SP_LIST.md'),
            'title': '路线 A：构效关系清单（SPR Inventory）',
        },
        {
            'md': os.path.join(OUTPUTS, 'ROUTE_A_EXPLANATION.md'),
            'title': '路线 A：构效关系解释文档（Scientific Explanation）',
        },
    ]

    for doc in docs:
        md_path = doc['md']
        if not os.path.exists(md_path):
            print(f'SKIP: {md_path} not found', file=sys.stderr)
            continue

        basename = os.path.splitext(os.path.basename(md_path))[0]
        print(f'Processing: {basename} ...')

        # 1. pandoc
        try:
            latex_body = run_pandoc(md_path)
        except RuntimeError as e:
            print(f'  ERROR (pandoc): {e}', file=sys.stderr)
            continue

        # 2. cleanup
        latex_body = cleanup_route_a(latex_body)

        # 3. template
        tex = build_tex(latex_body, doc['title'])

        # 4. write .tex to same dir as .md
        tex_path = os.path.join(OUTPUTS, f'{basename}.tex')
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(tex)
        print(f'  .tex written: {tex_path} ({len(tex)} bytes)')

        # 5. compile
        ok = compile_pdf(tex_path)
        if ok:
            pdf_path = tex_path.replace('.tex', '.pdf')
            print(f'  PDF compiled: {pdf_path}')
        else:
            print(f'  PDF compilation FAILED for {basename}', file=sys.stderr)

    print('Done.')


if __name__ == '__main__':
    main()
