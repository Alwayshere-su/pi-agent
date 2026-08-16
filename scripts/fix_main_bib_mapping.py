# -*- coding: utf-8 -*-
"""fix_main_bib_mapping.py — 主案例 references.bib 键→论文映射修复（W-3 P0-3）

背景（已核实）：report.tex 正文的 DOI 标注（`\\cite{pN}（DOI）：描述`）定义了每个
引用键的"意图论文"，但 references.bib 的 16 个条目被错误填充为另一篇论文（系统性错位，
见 HARNESS_FIX_FRAMEWORK.md W-3 与 audit_evidence_keys.py 输出）。

本脚本依据 report.tex 自带标注 + workspace/data/literature_cache/papers.json 的
真实元数据，把这些键的 bib 条目替换为正确论文（DOI 全部真实可查），并把真正的重复
条目 p210 合并到 p116。

用法：
  python scripts/fix_main_bib_mapping.py            # dry-run：报告替换预览
  python scripts/fix_main_bib_mapping.py --apply    # 写回 references.bib + report.tex
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BIB = os.path.join(ROOT, '文献调研报告', '主案例_MOF-CO2', 'references.bib')
TEX = os.path.join(ROOT, '文献调研报告', '主案例_MOF-CO2', 'report.tex')
PAPERS = os.path.join(ROOT, 'workspace', 'data', 'literature_cache', 'papers.json')

# 键 → 正确 DOI（来源：report.tex 内联标注；p2/p30 来源为正文明确语境）
FIX = {
    'p65':  '10.3390/su17073060',            # CoMn-MOF-74 双金属 1:1
    'p67':  '10.9767/bcrec.20658',           # Fe/Cu-MOF 双金属
    'p147': '10.1016/j.ces.2016.03.035',     # MIL-101(Cr,Mg) 双金属
    'p176': '10.1016/j.enconman.2017.11.010',# Mg-MOF-74 TSA 工艺
    'p178': '10.1016/j.apenergy.2017.10.098',# Mg-MOF-74 VPSA CFD
    'p17':  '10.1021/acs.langmuir.5c04277',  # M-MOF-74 结合势能景观
    'p27':  '10.1016/j.jcis.2021.12.163',    # MOF-74(Ni) Qst 调控
    'p22':  '10.3390/membranes15120385',     # Ni-Cu-MOF-74 MMM
    'p24':  '10.1016/j.efmat.2023.01.002',   # NiCo-MOF-74 微波合成
    'p31':  '10.1016/j.envres.2024.119985',  # MOF DAC 综述
    'p35':  '10.1016/j.cej.2025.170309',     # MOF-碳纤维 DAC
    'p50':  '10.3390/molecules30143048',     # DAC 纳米材料综述
    'p129': '10.3390/jcs5040102',            # SBA-15 等量吸附焓
    'p117': '10.1039/d0dt01784a',            # Qst 计算指南
    'p2':   '10.1016/j.fuel.2023.127463',    # ZIF-8@Zn-MOF-74 核壳
    'p30':  '10.1007/s10450-025-00664-x',    # ZIF-8 GCMC
}

# 真重复：p210 与 p116 同为 MOF@MOF 核壳（ccst.2024.100356），保留 p116
MERGE = {'p210': 'p116'}


def bib_entries(raw: str) -> dict[str, str]:
    """解析 bib，返回 {key: 条目原文}（含 @type{...} 到配平 } 的完整块）。"""
    out = {}
    pos = 0
    while True:
        m = re.search(r'(@\w+\{\s*[^,\s]+)', raw[pos:])
        if not m:
            break
        start = pos + m.start()
        head = raw[pos + m.start(): pos + m.end()]
        km = re.search(r'\{([^,\s]+)', head)
        key = km.group(1)
        depth = 0
        i = start
        while i < len(raw):
            if raw[i] == '{':
                depth += 1
            elif raw[i] == '}':
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        out[key] = raw[start:i]
        pos = i
    return out


def build_entry(key: str, meta: dict) -> str:
    authors = ' and '.join(meta.get('authors', []))
    title = meta.get('title', '').strip().replace('\n', ' ')
    # 清理 HTML 残留（如 &amp; → &）
    title = re.sub(r'<[^>]+>', '', title)
    title = title.replace('&amp;', '&')
    title = re.sub(r'\s+', ' ', title).strip()
    journal = (meta.get('journal') or '').replace('&amp;', '&')
    # LaTeX 特殊字符转义（bib 由 biblatex/bibtex 直接读取）
    def esc(s: str) -> str:
        return (s.replace('\\', r'\textbackslash{}')
                 .replace('&', r'\&')
                 .replace('%', r'\%')
                 .replace('#', r'\#')
                 .replace('_', r'\_'))
    title = esc(title)
    journal = esc(journal)
    authors = esc(authors)
    parts = [f'@article{{{key}',
             f'title={{{title}}}']
    if meta.get('volume'):
        parts.append(f'volume={{{meta["volume"]}}}')
    if meta.get('pages'):
        parts.append(f'pages={{{meta["pages"]}}}')
    parts.append(f'journal={{{journal}}}')
    if authors:
        parts.append(f'author={{{authors}}}')
    if meta.get('year'):
        parts.append(f'year={{{meta["year"]}}}')
    parts.append(f'DOI={{{meta["doi"]}}}')
    parts.append(f'url={{https://doi.org/{meta["doi"]}}}')
    return ',\n  '.join(parts) + '\n}\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='写回（默认 dry-run）')
    args = ap.parse_args()

    papers = json.load(open(PAPERS, encoding='utf-8'))
    raw = open(BIB, encoding='utf-8').read()
    entries = bib_entries(raw)
    tex = open(TEX, encoding='utf-8').read()

    missing_meta = []
    for k, doi in FIX.items():
        meta = papers.get('doi:' + doi)
        if not meta:
            missing_meta.append((k, doi))
            print(f'[MISSING META] {k} {doi}')
            continue
        new_entry = build_entry(k, meta)
        old = entries.get(k)
        if not old:
            print(f'[NO OLD ENTRY] {k}（无法替换，跳过）')
            continue
        print(f'== {k}: {doi}')
        print(f'   OLD: {old[:120]}...')
        print(f'   NEW: {new_entry[:120]}...')
        if args.apply:
            raw = raw.replace(old, new_entry, 1)

    if missing_meta:
        print(f'警告：{len(missing_meta)} 个键在 papers.json 中无元数据，未处理。')

    # 合并 p210 → p116
    if 'p210' in entries and args.apply:
        raw = raw.replace(entries['p210'], '', 1)
    tex_new = tex
    for old_k, new_k in MERGE.items():
        n = len(re.findall(r'\\cite\{' + old_k + r'\}', tex_new))
        tex_new = re.sub(r'\\cite\{' + old_k + r'\}', r'\\cite{' + new_k + '}', tex_new)
        print(f'[MERGE] tex \\cite{{{old_k}}} -> \\cite{{{new_k}}}：{n} 处')

    # 补 r10s1_a9ed68d1734e 占位条目（与其他 r10s 键一致，诚实标注无独立元数据）
    if 'r10s1_a9ed68d1734e' not in entries:
        placeholder = ('@misc{r10s1_a9ed68d1734e,\n'
                       '  title = {（报告引用编号 r10s1\\_a9ed68d1734e 的文献）},\n'
                       '  note = {编号来自调研报告正文引用；无独立元数据}\n'
                       '}\n')
        print('[ADD] r10s1_a9ed68d1734e 占位条目')
        if args.apply:
            raw = raw.rstrip() + '\n\n' + placeholder

    if args.apply:
        open(BIB, 'w', encoding='utf-8', newline='').write(raw)
        open(TEX, 'w', encoding='utf-8', newline='').write(tex_new)
        print('\n已写回 references.bib 与 report.tex')
    else:
        print('\n（dry-run，加 --apply 写回）')


if __name__ == '__main__':
    main()
