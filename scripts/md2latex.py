# -*- coding: utf-8 -*-
"""md2latex.py — 将 survey_report.md + gap_report.md 转换为 report.tex

链路：Markdown 报告 --> pandoc 结构转换 --> Python 后处理（引用/转义/删节）--> 模板 --> report.tex

后处理要点：
1. 引用转换：p{N} -> \\cite{pN}，r{...} -> \\cite{r...}（处理 pandoc 对下划线的 \\_ 转义）
2. 表格保留 longtable（pandoc 已输出）
3. 参考文献节选删除（由 \\printbibliography 统一输出，避免重复）
4. scv: 缓存编号保留为文本（非正式文献编号，不转 \\cite）

用法：python scripts/md2latex.py [--out <report.tex>]
"""
import argparse
import os
import re
import subprocess
import sys

BASE = os.path.join(os.path.dirname(__file__), '..', 'workspace', 'outputs', 'literature_survey')
PANDOC = os.path.join(os.path.dirname(__file__), '..', 'vendor', 'pandoc', 'pandoc-3.10.1', 'pandoc.exe')
TEMPLATE = os.path.join(os.path.dirname(__file__), 'templates', 'report.tex.j2')
DEFAULT_OUT = os.path.join(BASE, 'latex', 'report.tex')

TITLE = '金属有机框架（MOF）用于 CO2 捕集：材料-性质-构效关系系统综述'
DATE = '2026-08'


def run_pandoc(md_path):
    """pandoc markdown -> latex body（返回 latex 字符串）。"""
    cmd = [PANDOC, '-f', 'markdown', '-t', 'latex', '--wrap=none', md_path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError(f'pandoc failed: {r.stderr[:500]}')
    return r.stdout


def convert_refs(latex):
    """p# / r# 引用 -> \\cite。

    规则：
    - p\\d+ 独立出现 -> \\cite{pN}
    - r(10|11)s\\d+_[0-9a-f]{12}（含 pandoc 转义的 \\_）-> \\cite{r...}
    - 排除已在 \\cite{...} 中的；scv: 编号不转。
    """
    protected = {}
    def _protect(m):
        k = f'@@CITE{len(protected)}@@'
        protected[k] = m.group(0)
        return k
    latex = re.sub(r'\\cite\{[^}]*\}', _protect, latex)

    # p#：前后非字母数字/下划线/反斜杠，数字后不跟字母/点
    latex = re.sub(r'(?<![A-Za-z0-9_\\])p(\d+)(?![A-Za-z0-9_.])',
                   lambda m: f'\\cite{{p{m.group(1)}}}', latex)

    # r#：pandoc 把 _ 转义为 \\_，两种形态都匹配；转成标准 key（还原下划线）
    def _r(m):
        return f'\\cite{{{m.group(0).replace(chr(92), "")}}}'
    latex = re.sub(r'(?<![A-Za-z0-9_\\])r(?:10|11)s\d+\\?_[0-9a-f]{12}(?![A-Za-z0-9_])', _r, latex)

    for k, v in protected.items():
        latex = latex.replace(k, v)
    return latex


def cleanup(latex):
    """删节与清理。"""
    # 删除参考文献节选：定位"七、参考文献"标题，删除到"证据链"标题前
    # pandoc 会把含特殊字符的标题包成 \texorpdfstring{...}
    m_ref = re.search(r'\\subsection\{[^}]*七、参考文献', latex)
    m_ev = re.search(r'\\subsection\{[^}]*证据链', latex)
    if m_ref:
        end = m_ev.start() if m_ev else len(latex)
        latex = latex[:m_ref.start()] + latex[end:]
    # 行内 (DOI: 10.xxx) 片段删除（DOI 已在 .bib 中）
    latex = re.sub(r'[（(]\s*(?:DOI|doi)\s*[:：]\s*10\.[0-9a-zA-Z./()\-]+[)）]', '', latex)
    latex = re.sub(r'\.\s*doi:\s*10\.[0-9a-zA-Z./()\-]+', '', latex)
    # 删除残留的 "**p65** -- ..." 式参考文献行（若节选删除未覆盖）
    latex = re.sub(r'^\s*\\textbf\{[pr]\S*\} -- .*$', '', latex, flags=re.M)
    # 压缩空行
    latex = re.sub(r'\n{3,}', '\n\n', latex)
    return latex.strip()


def build_tex(survey_body, gap_body):
    template = open(TEMPLATE, encoding='utf-8').read()
    # gap 报告的 label 加前缀，避免与 survey 中同名小节（Gap 1 等）冲突
    gap_body = re.sub(r'\\label\{', r'\\label{gap:', gap_body)
    body = survey_body + '\n\n' + gap_body
    tex = template.replace('{{ title }}', TITLE).replace('{{ date }}', DATE).replace('{{ body }}', body)
    return tex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=DEFAULT_OUT)
    args = ap.parse_args()

    survey_body = cleanup(convert_refs(run_pandoc(os.path.join(BASE, 'survey_report.md'))))
    gap_body = cleanup(convert_refs(run_pandoc(os.path.join(BASE, 'gap_report.md'))))

    tex = build_tex(survey_body, gap_body)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(tex)
    print('report.tex written:', args.out, f'({len(tex)} bytes)')

    cites = re.findall(r'\\cite\{([^}]+)\}', tex)
    keys = set()
    for c in cites:
        for k in c.split(','):
            k = k.strip()
            if k:
                keys.add(k)
    print('distinct cite keys:', len(keys), '| p:', len([k for k in keys if k.startswith('p')]),
          '| r:', len([k for k in keys if k.startswith('r')]))


if __name__ == '__main__':
    main()
