# -*- coding: utf-8 -*-
"""build_bib.py — 从主题证据池生成 references.bib

@external: utils/resource_registry.py → "Crossref API"
  来源: https://api.crossref.org (免费 API, 实时, 2026-08)
  用途: DOI → 标准 BibTeX 条目（含 HTML 实体/月份/上下标清理）
  降级: 无 DOI 的论文使用 @misc 占位（零虚构）

链路（主案例，有 paper_register）：
  paper_register.md / papers_pid_index.json / gap_report.md / paper_summaries.md
    --> Crossref API (有 DOI) + @misc (无 DOI) --> references.bib

链路（其他主题，无 paper_register）：
  paper_summaries.md + gap_report.md + survey_report.md
    --> @misc only（无 Crossref，因为无 DOI） --> references.bib

key 统一为正文引用标识（p{N} / TE{N} / r{...}），与 \\cite 一一对应。
零虚构：不编造作者/期刊/年份。

用法：
  python scripts/build_bib.py                                    # 主案例
  python scripts/build_bib.py --theme perovskite                 # 其他主题
  python scripts/build_bib.py --theme perovskite --offline       # 跳过 Crossref
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), '..', 'workspace', 'outputs')
CROSSREF_UA = 'lit-survey-agent/1.0 (mailto:research@example.org)'


# ---------- 路径工具 ----------

def theme_base(theme: str) -> str:
    """解析主题目录。
    主案例: workspace/outputs/literature_survey/（theme='literature_survey'）
    其他:   workspace/outputs/{theme}/literature_survey/（theme='perovskite' 等）
    """
    if theme == 'literature_survey':
        return os.path.join(ROOT, 'literature_survey')
    return os.path.join(ROOT, theme, 'literature_survey')


def has_index(theme: str) -> bool:
    return os.path.exists(os.path.join(theme_base(theme), 'papers_pid_index.json'))


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
        except Exception as e:
            last = e
            time.sleep(0.6 * (i + 1))
    raise RuntimeError(f'Crossref failed for {doi}: {last}')


def esc_title(s):
    """清理标题里的 LaTeX 敏感字符。
    保护 $...$ 数学模式内的内容不被转义（化学式如 Cs$_2$InAgCl$_6$）。"""
    if not s:
        return ''
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('\\n', ' ')
    s = re.sub(r'</?(sub|sup|i|b|em|strong)>', '', s)
    s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

    # 保护 $...$ 数学模式，避免内部 _ 被转义
    math_spans = []
    def _save_math(m):
        math_spans.append(m.group(0))
        return f'@@MATH{len(math_spans) - 1}@@'
    s = re.sub(r'\$[^$]*\$', _save_math, s)

    s = s.replace('&', r'\&').replace('%', r'\%').replace('#', r'\#')
    s = s.replace('_', r'\_')

    # 恢复数学模式
    for i, span in enumerate(math_spans):
        s = s.replace(f'@@MATH{i}@@', span)
    return s


def clean_bibtex(bib: str) -> str:
    """清理 Crossref 返回的 BibTeX 文本中 LaTeX 不兼容的内容。"""
    bib = bib.strip()
    # HTML 实体
    bib = bib.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    bib = bib.replace('&', r'\&')
    # title 内 HTML 标签
    bib = re.sub(r'</?(sub|sup|i|b|em|strong)>', '', bib)
    bib = re.sub(r'\\n', ' ', bib)
    # 删除 month 字段（Crossref 返回 month={March} 或 month=Apr，BibTeX 与 biblatex 对此处理不一致）
    bib = re.sub(r',\s*month\s*=\s*\{[^}]*\}', '', bib)
    bib = re.sub(r',\s*month\s*=\s*[A-Za-z]+', '', bib)
    bib = re.sub(r',\s*month\s*=\s*"[^"]*"', '', bib)
    return bib


# ---------- 数据加载：主案例（有 paper_register）----------

def load_index(base: str):
    with open(os.path.join(base, 'papers_pid_index.json'), encoding='utf-8') as f:
        return json.load(f)


def load_r_meta(base: str):
    """paper_summaries.md: 46 条 ID -> {title, venue, doi}"""
    path = os.path.join(base, 'paper_summaries.md')
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
            if venue:
                venue = re.split(r'\s+Abstract:', venue, flags=re.I)[0].strip()
            out[mi.group(1).strip()] = {
                'title': mt.group(1).strip(),
                'venue': venue,
                'doi': norm_doi(md.group(1)) if md else None,
            }
    return out


def load_p_over_180_dois(base: str):
    """从 gap_report.md 提取 p>180 编号的 DOI。"""
    path = os.path.join(base, 'gap_report.md')
    t = open(path, encoding='utf-8').read()
    pairs = {}
    for m in re.finditer(r'p(\d+)\s*[（(]\s*(?:DOI:\s*)?(10\.\S+?)\s*[）)]', t):
        n = int(m.group(1))
        if n > 180:
            pairs[n] = norm_doi(m.group(2))
    return pairs


def load_gap_ref_lines(base: str):
    """survey_report.md 末尾参考文献节选中的描述。"""
    path = os.path.join(base, 'survey_report.md')
    t = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'^\s*\d+\.\s+\*\*p(\d+)\*\*\s*--\s*(.+)$', t, re.M):
        out[int(m.group(1))] = m.group(2).strip()
    return out


# ---------- 数据加载：其他主题（无 paper_register）----------

def load_summaries_meta(base: str) -> dict[str, dict]:
    """从 paper_summaries.md 提取所有条目的 {id: {title, year, venue}}。
    支持多种 ID 格式：p1 / p01 / TE001 等。
    支持两种条目格式：
      - 干净格式：### N. Title: Actual Title
      - Dict 格式：### N. {'title': '...', 'authors': '...', 'abstract': '...'}
    """
    path = os.path.join(base, 'paper_summaries.md')
    if not os.path.exists(path):
        return {}
    t = open(path, encoding='utf-8').read()
    tick = chr(96)
    out = {}
    # 按 ### N. 分割条目
    blocks = re.split(r'\n(?=### \d+\.)', t)
    for b in blocks:
        # ID
        mi = re.search(r'\*\*ID:\*\*\s*' + tick + r'([^' + tick + r']+)' + tick, b)
        if not mi:
            mi = re.search(r'\*\*ID:\*\*\s*`?(\S+)`?', b)
        if not mi:
            continue
        rid = mi.group(1).strip()

        title = None
        year = None
        doi = None

        # 格式 A：### N. {'title': '...', 'authors': ...}（perovskite 等 dict repr 格式）
        # dict 可能跨行/不完整（title 闭合引号缺失），用 regex 比 ast.literal_eval 更稳健
        dict_m = re.match(r'### \d+\.\s*(\{.*)', b)
        if dict_m and 'title' in dict_m.group(1):
            raw_dict = dict_m.group(1)
            tm = re.search(r"['\"]title['\"]\s*:\s*['\"](.+?)['\"]", raw_dict)
            if tm:
                title = tm.group(1)
            else:
                # title 因截断没有闭合引号 — 贪婪匹配到行尾
                tm = re.search(r"['\"]title['\"]\s*:\s*['\"](.+)", raw_dict)
                if tm:
                    title = tm.group(1).rstrip()
            ym = re.search(r"['\"]year['\"]\s*:\s*(\d{4})", raw_dict)
            if ym:
                year = ym.group(1)

        # 格式 B：### N. Title: ...（主案例等）
        if not title:
            mt = re.search(r'(?:### \d+\.\s*(?:Title:\s*)?|Title:\s*)(.+?)(?:\n|$)', b)
            if mt:
                raw = mt.group(1).strip()
                # 如果以 { 开头，可能是 dict 格式没在格式 A 中匹配到
                if raw.startswith('{'):
                    tm = re.search(r"['\"]title['\"]\s*:\s*['\"](.+?)['\"]", raw)
                    if not tm:
                        # 截断无闭合引号
                        tm = re.search(r"['\"]title['\"]\s*:\s*['\"](.+)", raw)
                    if tm:
                        title = tm.group(1).rstrip()
                    ym = re.search(r"['\"]year['\"]\s*:\s*(\d{4})", raw)
                    if ym:
                        year = ym.group(1)
                    if not title:
                        title = raw
                else:
                    title = raw

        # Year（独立字段）
        if not year:
            my = re.search(r'\*\*Year:\*\*\s*(\d{4})', b)
            if my:
                year = my.group(1)

        # DOI
        md = re.search(r'(?:DOI|doi)\s*[::]?\s*(10\.\S+)', b, re.I)
        if md:
            doi = norm_doi(md.group(1))

        out[rid] = {'title': title, 'year': year, 'doi': doi}
    return out


# ---------- 条目生成 ----------

def make_article(doi, key, fallback_title=None):
    """有 DOI：Crossref 拉 BibTeX，替换 key 返回。"""
    bib = clean_bibtex(crossref_bibtex(doi))
    # 替换 entry key
    bib = re.sub(r'^(@\w+)\{[^,]+', rf'\g<1>{{{key}', bib, count=1, flags=re.M)
    if 'title=' not in bib and fallback_title:
        bib = bib.rstrip()
        bib = bib[:-1] + f',\n  title = {{{esc_title(fallback_title)}}}\n' + '}'
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
    ap.add_argument('--theme', default='literature_survey',
                    help='主题目录名（默认 literature_survey）')
    ap.add_argument('--offline', action='store_true', help='不调 Crossref，全部降级 @misc')
    ap.add_argument('--out', default=None, help='输出路径（默认 workspace/outputs/{theme}/literature_survey/latex/references.bib）')
    args = ap.parse_args()

    base = theme_base(args.theme)
    out = args.out or os.path.join(base, 'latex', 'references.bib')

    survey_path = os.path.join(base, 'survey_report.md')
    gap_path = os.path.join(base, 'gap_report.md')

    if not os.path.exists(survey_path):
        print(f'ERROR: survey_report.md not found at {survey_path}', file=sys.stderr)
        sys.exit(1)

    survey = open(survey_path, encoding='utf-8').read()
    gap = open(gap_path, encoding='utf-8').read() if os.path.exists(gap_path) else ''
    all_text = survey + '\n' + gap

    # 提取引用 key 全集
    p_refs = sorted(set(int(m) for m in re.findall(r'\bp(\d+)\b', all_text) if len(m) <= 5))
    te_refs = sorted(set(re.findall(r'\bTE\d+\b', all_text)))
    r_refs = sorted(set(re.findall(r'\br(?:10|11)s\d+_[0-9a-f]{12}\b', all_text)))

    entries = {}
    stats = {'doi_ok': 0, 'doi_fail': 0, 'misc': 0}

    # ── 路径 A：有 papers_pid_index.json → Crossref 主链路 ──
    if has_index(args.theme) and not args.offline:
        idx = load_index(base)
        r_meta = load_r_meta(base)
        p_over = load_p_over_180_dois(base)
        gap_lines = load_gap_ref_lines(base)

        # r10s* 别名映射
        r_alias = {}
        for rid in r_refs:
            if rid not in r_meta:
                suffix = rid.split('_', 1)[1]
                for cand in r_meta:
                    if cand.split('_', 1)[1] == suffix:
                        r_alias[rid] = cand
                        break

        # p1-p180
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
            if doi:
                try:
                    entries[key] = make_article(doi, key, fallback_title=title)
                    stats['doi_ok'] += 1
                    continue
                except Exception:
                    stats['doi_fail'] += 1
            entries[key] = make_misc(key, title, note='来源：papers_pid_index.json（无 DOI）')
            stats['misc'] += 1

        # p>180
        for n in p_refs:
            if n <= 180:
                continue
            key = f'p{n}'
            doi = p_over.get(n)
            if doi:
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

        # r#
        for rid in r_refs:
            meta = r_meta.get(rid) or r_meta.get(r_alias.get(rid))
            if meta and meta.get('doi'):
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
            note = '来源：paper_summaries.md' if meta else '编号来自调研报告正文引用；无独立元数据'
            if venue and 'arxiv' not in venue.lower():
                note += f'；Venue: {venue}'
            entries[rid] = make_misc(rid, title, note=note)
            stats['misc'] += 1

    # ── 路径 B：无 papers_pid_index.json → @misc only ──
    else:
        if args.offline:
            print('[offline mode]')
        else:
            print(f'[{args.theme}] 无 papers_pid_index.json，全部降级 @misc')

        meta = load_summaries_meta(base)

        # p# 引用
        for n in p_refs:
            key = f'p{n}'
            rec = meta.get(key) or meta.get(f'p{n:02d}')  # p06 格式
            if rec and rec.get('title'):
                note_parts = ['来源：paper_summaries.md']
                if rec.get('year'):
                    note_parts.append(f'Year: {rec["year"]}')
                entries[key] = make_misc(key, rec['title'], note='；'.join(note_parts))
            else:
                entries[key] = make_misc(key, f'（引用键 {key}，未在 paper_summaries 中找到标题）',
                                         note='请核对 survey_report.md 正文引用')
            stats['misc'] += 1

        # TE# 引用（热电主题专用）
        for rid in te_refs:
            rec = meta.get(rid)
            if rec and rec.get('title'):
                note_parts = ['来源：paper_summaries.md']
                if rec.get('year'):
                    note_parts.append(f'Year: {rec["year"]}')
                entries[rid] = make_misc(rid, rec['title'], note='；'.join(note_parts))
            else:
                entries[rid] = make_misc(rid, f'（引用键 {rid}，未在 paper_summaries 中找到标题）',
                                         note='请核对 survey_report.md 正文引用')
            stats['misc'] += 1

        # r# 引用
        for rid in r_refs:
            rec = meta.get(rid)
            title = rec['title'] if rec else None
            if not title:
                title = f'（引用键 {rid}，无关联摘要）'
            entries[rid] = make_misc(rid, title, note='编号来自调研报告正文引用')
            stats['misc'] += 1

    # 写出
    os.makedirs(os.path.dirname(out), exist_ok=True)
    header = (
        f'% references.bib — 由 scripts/build_bib.py 自动生成（主题: {args.theme}）\n'
        f'% key 规则：与报告正文引用一一对应\n'
        f'% 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n\n'
    )
    body = '\n\n'.join(entries[k] for k in sorted(entries))
    with open(out, 'w', encoding='utf-8') as f:
        f.write(header + body + '\n')

    # 统计
    all_keys = [f'p{n}' for n in p_refs] + te_refs + r_refs
    missing = [k for k in all_keys if k not in entries]

    print(f'theme: {args.theme}')
    print(f'entries total: {len(entries)}')
    if has_index(args.theme):
        print(f'  doi_ok={stats["doi_ok"]}  doi_fail={stats["doi_fail"]}  misc={stats["misc"]}')
    else:
        print(f'  all @misc: {stats["misc"]}')
    print(f'p_refs: {len(p_refs)}  te_refs: {len(te_refs)}  r_refs: {len(r_refs)}')
    print('missing keys:', missing if missing else 'NONE')
    print('out:', out)


if __name__ == '__main__':
    main()
