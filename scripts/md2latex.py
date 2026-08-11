# -*- coding: utf-8 -*-
"""md2latex.py — 将 survey_report.md + gap_report.md 转换为 report.tex

链路：Markdown 报告 --> pandoc 结构转换 --> Python 后处理（引用/转义/删节）--> 模板 --> report.tex

后处理要点：
1. 引用转换：p{N} -> \\cite{pN}，TE{N} -> \\cite{TE{N}}，r{...} -> \\cite{r...}
2. 表格保留 longtable（pandoc 已输出）
3. 参考文献节选删除（由 \\printbibliography 统一输出，避免重复）

用法：
  python scripts/md2latex.py                                    # 主案例
  python scripts/md2latex.py --theme perovskite                 # 其他主题
  python scripts/md2latex.py --theme perovskite --title "..."   # 手动指定标题
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..', 'workspace', 'outputs')
PANDOC = os.path.join(os.path.dirname(__file__), '..', 'vendor', 'pandoc', 'pandoc-3.10.1', 'pandoc.exe')
TEMPLATE = os.path.join(os.path.dirname(__file__), 'templates', 'report.tex.j2')
DATE = '2026-08'


def theme_base(theme: str) -> str:
    """解析主题目录。"""
    if theme == 'literature_survey':
        return os.path.join(ROOT, 'literature_survey')
    return os.path.join(ROOT, theme, 'literature_survey')


def extract_title(survey_md_text: str) -> str:
    """从 survey_report.md 第一行提取标题。"""
    m = re.search(r'^#\s+(.+?)(?:\n|$)', survey_md_text, re.M)
    if m:
        return m.group(1).strip()
    return '文献调研报告'


def preprocess_md(text: str) -> str:
    """Markdown 正文预处理，解决 pandoc 解析歧义。"""
    # --- 在表格后的空行间被 pandoc 误解析为表格分隔符 → 换成 ***
    text = re.sub(r'\n\n---\n', r'\n\n***\n', text)
    return text


def run_pandoc(md_path):
    """pandoc markdown -> latex body。"""
    raw = open(md_path, encoding='utf-8').read()
    raw = preprocess_md(raw)
    # -yaml_metadata_block: 避免文档中的 --- 被误解析为 YAML front matter
    cmd = [PANDOC, '-f', 'markdown-yaml_metadata_block', '-t', 'latex', '--wrap=none']
    r = subprocess.run(cmd, input=raw, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError(f'pandoc failed: {r.stderr[:500]}')
    return r.stdout


def convert_refs(latex):
    """p# / TE# / r# 引用 -> \\cite。

    规则：
    - p\\d+ 独立出现 -> \\cite{pN}
    - TE\\d+ -> \\cite{TE{N}}
    - r(10|11)s\\d+_[0-9a-f]{12}（含 pandoc 转义的 \\_）-> \\cite{r...}
    - 排除已在 \\cite{...} 中的。
    - 排除 \\label{...}、\\ref{...} 内部的（避免 \\csname 错误）。
    """
    protected = {}
    def _protect(m):
        k = f'@@PROTECT{len(protected)}@@'
        protected[k] = m.group(0)
        return k
    # 保护已存在的 \\cite{}
    latex = re.sub(r'\\cite\{[^}]*\}', _protect, latex)
    # 保护 \\label{} 和 \\ref{} 内部（引用编号不能进入 label）
    latex = re.sub(r'\\(label|ref)\{[^}]*\}', _protect, latex)

    # p#：前后非字母数字/下划线/反斜杠，数字后不跟字母/点
    latex = re.sub(r'(?<![A-Za-z0-9_\\])p(\d+)(?![A-Za-z0-9_.])',
                   lambda m: f'\\cite{{p{m.group(1)}}}', latex)

    # TE#：热电主题引用
    latex = re.sub(r'(?<![A-Za-z0-9_\\])(TE\d+)(?![A-Za-z0-9_])',
                   lambda m: f'\\cite{{{m.group(1)}}}', latex)

    # r#：pandoc 把 _ 转义为 \\_，两种形态都匹配
    def _r(m):
        return f'\\cite{{{m.group(0).replace(chr(92), "")}}}'
    latex = re.sub(r'(?<![A-Za-z0-9_\\])r(?:10|11)s\d+\\?_[0-9a-f]{12}(?![A-Za-z0-9_])', _r, latex)

    for k, v in protected.items():
        latex = latex.replace(k, v)
    return latex


def cleanup(latex):
    """删节与清理。"""
    # 删除参考文献节选
    m_ref = re.search(r'\\subsection\{[^}]*[七八九]、参考文献', latex)
    m_ev = re.search(r'\\subsection\{[^}]*证据链', latex)
    if m_ref:
        end = m_ev.start() if m_ev else len(latex)
        latex = latex[:m_ref.start()] + latex[end:]
    # 行内 (DOI: 10.xxx) 删除
    latex = re.sub(r'[（(]\s*(?:DOI|doi)\s*[:：]\s*10\.[0-9a-zA-Z./()\-]+[)）]', '', latex)
    latex = re.sub(r'\.\s*doi:\s*10\.[0-9a-zA-Z./()\-]+', '', latex)
    # 残留参考文献行
    latex = re.sub(r'^\s*\\textbf\{[prTE0-9]*\} -- .*$', '', latex, flags=re.M)
    # 压缩空行
    latex = re.sub(r'\n{3,}', '\n\n', latex)
    return latex.strip()


def build_tex(survey_body, gap_body, title):
    template = open(TEMPLATE, encoding='utf-8').read()
    # gap 报告的 label 加前缀，避免同名小节冲突
    gap_body = re.sub(r'\\label\{', r'\\label{gap:', gap_body)
    body = survey_body + '\n\n' + gap_body
    tex = template.replace('{{ title }}', title).replace('{{ date }}', DATE).replace('{{ body }}', body)
    return tex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--theme', default='literature_survey', help='主题目录名')
    ap.add_argument('--title', default=None, help='报告标题（默认从 survey_report.md 提取）')
    ap.add_argument('--out', default=None, help='输出 .tex 路径')
    args = ap.parse_args()

    base = theme_base(args.theme)

    survey_path = os.path.join(base, 'survey_report.md')
    gap_path = os.path.join(base, 'gap_report.md')

    if not os.path.exists(survey_path):
        print(f'ERROR: survey_report.md not found at {survey_path}', file=sys.stderr)
        sys.exit(1)

    raw_survey = open(survey_path, encoding='utf-8').read()
    raw_gap = open(gap_path, encoding='utf-8').read() if os.path.exists(gap_path) else ''

    title = args.title or extract_title(raw_survey)

    survey_body = cleanup(convert_refs(run_pandoc(survey_path)))
    gap_body = cleanup(convert_refs(run_pandoc(gap_path))) if raw_gap else ''

    tex = build_tex(survey_body, gap_body, title)
    out = args.out or os.path.join(base, 'latex', 'report.tex')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(tex)
    print('report.tex written:', out, f'({len(tex)} bytes)')

    # 统计引用
    cites = re.findall(r'\\cite\{([^}]+)\}', tex)
    keys = set()
    for c in cites:
        for k in c.split(','):
            k = k.strip()
            if k:
                keys.add(k)
    p_keys = [k for k in keys if k.startswith('p')]
    te_keys = [k for k in keys if k.startswith('TE')]
    r_keys = [k for k in keys if k.startswith('r')]
    print(f'distinct cite keys: {len(keys)} | p: {len(p_keys)} | TE: {len(te_keys)} | r: {len(r_keys)}')


if __name__ == '__main__':
    main()
