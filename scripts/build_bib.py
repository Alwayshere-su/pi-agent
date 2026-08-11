# -*- coding: utf-8 -*-
"""build_bib.py — 从 paper_register 证据池生成 references.bib

链路：paper_register.md / papers_pid_index.json / gap_report.md / paper_summaries.md
      --> references.bib（key 统一为 p{N} 或 r{...}，与正文 \cite 一一对应）

- 有 DOI：调用 Crossref API 拉取标准 BibTeX（免费、无需 key）
- 无 DOI：用已知标题/语境生成 @misc 条目（零虚构：不编造作者/期刊/年份）

用法：python scripts/build_bib.py [--out <references.bib>] [--offline]
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.join(os.path.dirname(__file__), '..', 'workspace', 'outputs', 'literature_survey')
DEFAULT_OUT = os.path.join(BASE, 'latex', 'references.bib')
CROSSREF_UA = 'lit-survey-agent/1.0 (mailto:research@example.org)'

# ---------- 工具 ----------

def norm_doi(d):
    if not d:
        return None
    d = str(d).strip()
    d = re.sub(r'^https?://(dx\.)?doi\.org/', '', d, flags=re.I)
    if d in ('', '—', '-', 'None', 'N/A'):
        return None
    return d.lower()


def crossref_bibtex(doi, timeout=25, retries=2):
    """Crossref transform 端点直接返回 BibTeX 文本。"""
    url = 'https://api.crossref.org/works/' + urllib.parse.quote(doi) + '/transform/application/x-bibtex'
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': CROSSREF_UA, 'Accept': 'application/x-bibtex'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.6 * (i + 1))
    raise RuntimeError(f'Crossref failed for {doi}: {last}')


def esc_title(s):
    """清理标题里的 LaTeX 敏感字符（保留基础转义）。"""
    if not s:
        return ''
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('\\n', ' ')  # 字面 \n 序列
    s = re.sub(r'</?(sub|sup|i|b|em|strong)>', '', s)  # 剥离 HTML 上下标/格式标签
    s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    s = s.replace('&', r'\&').replace('%', r'\%').replace('#', r'\#')
    s = s.replace('_', r'\_')
    return s


# ---------- 数据加载 ----------

def load_index():
    with open(os.path.join(BASE, 'papers_pid_index.json'), encoding='utf-8') as f:
        return json.load(f)


def load_r_meta():
    """paper_summaries.md: 46 条 ID -> {title, venue, doi}"""
    path = os.path.join(BASE, 'paper_summaries.md')
    t = open(path, encoding='utf-8').read()
    entries = re.split(r'\n(?=### \d+\. Title:)', t)
    tick = chr(96)
    out = {}
    for e in entries:
        mt = re.search(r'### \d+\. Title:\s*(.+?)\n', e, re.S)
        mi = re.search(r'\*\*ID:\*\*\s*' + tick + r'([^' + tick + r']+)' + tick, e)
        mv = re.search(r'Venue:\s*(.+?)(?:\n|$)', e)
        md = re.search(r'(?:DOI|doi)\s*[::]?\s*(10\.\S+)', e, re.I)
        if mt and mi:
            venue = mv.group(1).strip() if mv else None
            # venue 行可能混入后续 Abstract: 片段，截断
            if venue:
                venue = re.split(r'\s+Abstract:', venue, flags=re.I)[0].strip()
            out[mi.group(1).strip()] = {
                'title': mt.group(1).strip(),
                'venue': venue,
                'doi': norm_doi(md.group(1)) if md else None,
            }
    return out


def load_p_over_180_dois():
    """从 gap_report.md 提取 p>180 编号的 DOI。"""
    path = os.path.join(BASE, 'gap_report.md')
    t = open(path, encoding='utf-8').read()
    pairs = {}
    for m in re.finditer(r'p(\d+)\s*[（(]\s*(?:DOI:\s*)?(10\.\S+?)\s*[）)]', t):
        n = int(m.group(1))
        if n > 180:
            pairs[n] = norm_doi(m.group(2))
    return pairs


def load_gap_ref_lines():
    """survey_report.md 末尾参考文献节选中的描述（给无 DOI 的 p>180 提供语境）。"""
    path = os.path.join(BASE, 'survey_report.md')
    t = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'^\s*\d+\.\s+\*\*p(\d+)\*\*\s*--\s*(.+)$', t, re.M):
        out[int(m.group(1))] = m.group(2).strip()
    return out


# ---------- 条目生成 ----------

def make_article(doi, key, fallback_title=None):
    """有 DOI：Crossref 拉 BibTeX，替换 key 返回；缺 title 时回退 fallback_title。"""
    bib = crossref_bibtex(doi)
    bib = bib.strip()
    # 清理 HTML 实体（Crossref BibTeX 中 title/journal 常含 &amp;）
    # 注意顺序：先统一 HTML 实体为裸 &，最后一次性转义 &
    bib = bib.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    bib = bib.replace('&', r'\&')
    # 替换 entry key（第一行 @type{oldkey,）
    bib = re.sub(r'^(@\w+)\{[^,]+', rf'\g<1>{{{key}', bib, count=1, flags=re.M)
    if 'title=' not in bib and fallback_title:
        bib = bib.rstrip()
        bib = bib[:-1] + f',\n  title = {{{esc_title(fallback_title)}}}\n' + '}'
    # title 字段内 HTML 实体/换行清理（Crossref 数据常见）
    bib = re.sub(r'</?(sub|sup|i|b|em|strong)>', '', bib)
    bib = re.sub(r'\\n', ' ', bib)
    bib = re.sub(r'\n', ' ', bib)
    # month=March 等非标准宏会触发 BibTeX 警告：直接删除 month 字段（年份已足够）
    bib = re.sub(r',\s*month=\{[^}]*\}', '', bib)
    return bib


def make_misc(key, title, note=None):
    parts = [f'@misc{{{key},', f'  title = {{{esc_title(title)}}},']
    if note:
        parts.append(f'  note = {{{esc_title(note)}}},')
    parts.append('}')
    return '\n'.join(parts)


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--offline', action='store_true', help='不调 Crossref，全部降级 @misc')
    args = ap.parse_args()

    idx = load_index()
    r_meta = load_r_meta()
    p_over = load_p_over_180_dois()
    gap_lines = load_gap_ref_lines()

    # 需要覆盖的 key 全集：正文引用的 p#（1..224）+ r#
    survey = open(os.path.join(BASE, 'survey_report.md'), encoding='utf-8').read()
    gap = open(os.path.join(BASE, 'gap_report.md'), encoding='utf-8').read()
    all_text = survey + '\n' + gap
    p_refs = sorted(set(int(m) for m in re.findall(r'\bp(\d+)\b', all_text)))
    r_refs = sorted(set(re.findall(r'\br(?:10|11)s\d+_[0-9a-f]{12}\b', all_text)))

    # r10s* 别名 -> r11s*（同后缀同一篇）
    r_alias = {}
    for rid in r_refs:
        if rid not in r_meta:
            suffix = rid.split('_', 1)[1]
            for cand in r_meta:
                if cand.split('_', 1)[1] == suffix:
                    r_alias[rid] = cand
                    break

    entries = {}
    stats = {'doi_ok': 0, 'doi_fail': 0, 'misc': 0}

    # 1) p1-p180
    for n in p_refs:
        if n < 1 or n > 180:
            continue
        key = f'p{n}'
        rec = idx.get(key)
        if not rec:
            entries[key] = make_misc(key, f'（登记表编号 {key}，未在索引中找到）')
            stats['misc'] += 1
            continue
        doi = norm_doi(rec.get('doi'))
        title = rec.get('title') or f'（编号 {key} 的文献）'
        if doi and not args.offline:
            try:
                entries[key] = make_article(doi, key, fallback_title=title)
                stats['doi_ok'] += 1
                continue
            except Exception:
                stats['doi_fail'] += 1
        entries[key] = make_misc(key, title, note=f'来源：papers_pid_index.json（无 DOI）')
        stats['misc'] += 1

    # 2) p>180
    for n in p_refs:
        if n <= 180:
            continue
        key = f'p{n}'
        doi = p_over.get(n)
        if doi and not args.offline:
            try:
                entries[key] = make_article(doi, key)
                stats['doi_ok'] += 1
                continue
            except Exception:
                stats['doi_fail'] += 1
        desc = gap_lines.get(n)
        title = desc if desc else f'（报告引用编号 {key} 的文献）'
        entries[key] = make_misc(key, title, note='编号来自调研报告正文引用；无 DOI/独立元数据')
        stats['misc'] += 1

    # 3) r#
    for rid in r_refs:
        meta = r_meta.get(rid) or r_meta.get(r_alias.get(rid))
        if meta and meta.get('doi') and not args.offline:
            try:
                entries[rid] = make_article(meta['doi'], rid)
                stats['doi_ok'] += 1
                continue
            except Exception:
                stats['doi_fail'] += 1
        title = meta['title'] if meta else None
        venue = meta['venue'] if meta else None
        if not title:
            title = f'（报告引用编号 {rid} 的文献）'
        note = f'来源：paper_summaries.md' if meta else '编号来自调研报告正文引用；无独立元数据'
        if venue and 'arxiv' not in venue.lower():
            note += f'；Venue: {venue}'
        entries[rid] = make_misc(rid, title, note=note)
        stats['misc'] += 1

    # 写出
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    header = (
        '% references.bib — 由 scripts/build_bib.py 自动生成\n'
        '% 数据源：papers_pid_index.json / gap_report.md / paper_summaries.md / Crossref API\n'
        '% key 规则：p{N}（登记表编号）、r{...}（最终收录摘要编号），与报告正文引用一一对应\n'
        '% 生成时间: ' + time.strftime('%Y-%m-%d %H:%M:%S') + '\n\n'
    )
    body = '\n\n'.join(entries[k] for k in sorted(entries))
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(header + body + '\n')

    print(f'entries total: {len(entries)}')
    print(f'  doi_ok={stats["doi_ok"]}  doi_fail={stats["doi_fail"]}  misc={stats["misc"]}')
    print(f'p_refs covered: {len([k for k in entries if k.startswith("p")])} / {len(p_refs)}')
    print(f'r_refs covered: {len([k for k in entries if k.startswith("r")])} / {len(r_refs)}')
    need = [f'p{n}' for n in p_refs] + list(r_refs)
    missing = [k for k in need if k not in entries]
    print('missing keys:', missing if missing else 'NONE')
    print('out:', args.out)


if __name__ == '__main__':
    main()
