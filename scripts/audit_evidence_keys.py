# -*- coding: utf-8 -*-
"""audit_evidence_keys.py — 证据链 p#/TE#/P#/v#/r#/DOI 与 references.bib 的四层追溯审计

对应 HARNESS_FIX_FRAMEWORK.md W-3 Step 1：
  1. 缺失表：证据链使用的引用键在 references.bib 中不存在；
  2. 重复表：bib 内标题（归一化）哈希相同的多键条目；
  3. 语义表：每条假设的 expected_relationship 关键词 × 证据链各键的 bib 标题，
     供人工/LLM 判读「支持 / 中性 / 错位」。

用法：
  python scripts/audit_evidence_keys.py            # 输出三张表
  python scripts/audit_evidence_keys.py --json     # 同时输出机器可读 JSON
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WORKSPACE = os.path.join(ROOT, 'workspace', 'outputs')
SURVEY_DIR = os.path.join(ROOT, '文献调研报告')

# 主题 → (discovery 目录相对 workspace, 文献调研报告子目录)
THEMES = {
    'literature_survey': ('literature_survey/discovery', '主案例_MOF-CO2'),
    'mof_e2e_v4':        ('mof_e2e_v4/literature_survey/discovery', 'mof_e2e_v4'),
    'perovskite':        ('perovskite/literature_survey/discovery', 'perovskite_钙钛矿'),
    'thermoelectric':    ('thermoelectric/literature_survey/discovery', 'thermoelectric_热电'),
    'cathode':           ('cathode/literature_survey/discovery', 'cathode_高镍正极'),
    'validation':        ('validation/literature_survey/discovery', 'validation_固态电解质'),
}

# 已知且已披露的例外键（COMPLIANCE.md §11.1）：mof_e2e_v4 的 v3s#/DOI 形式证据链引用
# 未落入其 references.bib（bib 以诚实占位条目标注），DOI 可经 Crossref 独立核验。
KNOWN_EXCEPTIONS = {
    'mof_e2e_v4': {
        '10.1021/acsami.5c16139', '10.1021/jacs.3c13381', '10.1021/jacs.8b10203',
        '10.1039/d0sc01087a', 'v3s0_c795f15f9d35', 'v3s1', 'v3s3', 'v3s5',
    },
}

# 与 build_route_a_docs.py 保持一致的引用键解析
_KEY_RE = re.compile(
    r'\b(?:p\d+|TE\d+|P\d+|v\d+s\d+(?:_[0-9a-f]+)?|r\d+s\d+(?:_[0-9a-f]+)?|10\.\d{4,}/[^\s()]+)\b'
)
_KEY_FULL = re.compile(
    r'^(?:p\d+|TE\d+|P\d+|v\d+s\d+(?:_[0-9a-f]+)?|r\d+s\d+(?:_[0-9a-f]+)?|10\.\d{4,}/[^\s()]+)$'
)
_SKIP = ('Novelty', 'Overlap', 'LLM', 'Assessment')


def extract_evidence_keys(hyps: list) -> list[str]:
    keys: list[str] = []
    for h in hyps:
        ec = h.get('evidence_chain') or []
        if isinstance(ec, dict):
            ec = list(ec.values())
        for e in ec:
            eid = e.get('id', e.get('ref', e.get('paper_id', ''))) if isinstance(e, dict) else str(e)
            eid = str(eid).strip()
            if not eid or any(t in eid for t in _SKIP):
                continue
            if _KEY_FULL.match(eid):
                keys.append(eid)
            else:
                keys.extend(_KEY_RE.findall(eid))
    return keys


def load_bib(bib_path: str) -> tuple[dict, dict]:
    """返回 (key → {title, doi, authors, year, journal}), (归一化标题 → [keys])。"""
    if not os.path.exists(bib_path):
        return {}, {}
    raw = open(bib_path, encoding='utf-8').read()
    entries: dict = {}
    by_title: dict[str, list[str]] = defaultdict(list)
    # 按 @type{key, 定位，用括号配平截取条目体（bib 的 } 常内联，不能用 \n} 匹配）
    pos = 0
    while True:
        m = re.search(r'@\w+\{\s*([^,\s]+)\s*,', raw[pos:])
        if not m:
            break
        key = m.group(1)
        start = pos + m.end()
        depth = 1
        i = start
        while i < len(raw) and depth > 0:
            if raw[i] == '{':
                depth += 1
            elif raw[i] == '}':
                depth -= 1
            i += 1
        body = raw[start:i - 1] if depth == 0 else raw[start:]

        def field(name: str) -> str:
            fm = re.search(r'\b' + name + r'\s*=\s*\{([^}]*)\}', body, re.I)
            return fm.group(1).strip() if fm else ''

        title = field('title')
        entries[key] = {
            'title': title,
            'doi': field('doi'),
            'authors': field('author'),
            'year': field('year'),
            'journal': field('journal'),
        }
        norm = re.sub(r'[^a-z0-9]', '', title.lower())
        if norm:
            by_title[norm].append(key)
        pos = i  # i 为绝对位置（条目结束的 } 之后）
    return entries, by_title


def audit_theme(name: str, disc_rel: str, survey_sub: str) -> dict:
    hp_path = os.path.join(WORKSPACE, disc_rel, 'hypotheses.json')
    bib_path = os.path.join(SURVEY_DIR, survey_sub, 'references.bib')
    result = {'theme': name, 'missing': [], 'duplicates': {}, 'semantic': [], 'hypo_count': 0}
    if not os.path.exists(hp_path):
        result['error'] = f'no hypotheses.json at {hp_path}'
        return result
    data = json.load(open(hp_path, encoding='utf-8'))
    hyps = data.get('hypotheses', data) if isinstance(data, dict) else data
    result['hypo_count'] = len(hyps)
    entries, by_title = load_bib(bib_path)
    result['bib_count'] = len(entries)

    # 1. 缺失表
    used = set(extract_evidence_keys(hyps))
    for k in sorted(used):
        if k not in entries and k not in KNOWN_EXCEPTIONS.get(name, set()):
            result['missing'].append(k)

    # 2. 重复表（bib 内部）
    for norm, keys in by_title.items():
        if len(keys) > 1:
            result['duplicates'][norm] = keys

    # 3. 语义表（假设 expected_relationship × 证据键 bib 标题）
    for h in hyps:
        rel = (h.get('expected_relationship') or '')[:120]
        row = {'id': h.get('id'), 'expected_relationship': rel, 'refs': []}
        ec = h.get('evidence_chain') or []
        if isinstance(ec, dict):
            ec = list(ec.values())
        for e in ec:
            eid = e.get('id', e.get('ref', e.get('paper_id', ''))) if isinstance(e, dict) else str(e)
            eid = str(eid).strip()
            if not eid or any(t in eid for t in _SKIP):
                continue
            for k in ([eid] if _KEY_FULL.match(eid) else _KEY_RE.findall(eid)):
                if k in entries:
                    row['refs'].append({
                        'key': k,
                        'title': entries[k]['title'][:130],
                        'year': entries[k]['year'],
                    })
                else:
                    row['refs'].append({'key': k, 'title': '<<不在 bib 中>>', 'year': ''})
        result['semantic'].append(row)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true', help='同时输出 machine-readable JSON')
    args = ap.parse_args()

    all_results = []
    for name, (disc_rel, survey_sub) in THEMES.items():
        r = audit_theme(name, disc_rel, survey_sub)
        all_results.append(r)
        print(f'\n=== {name} （bib {r.get("bib_count", 0)} 条 / {r.get("hypo_count", 0)} 假设） ===')
        print(f'  缺失键: {r["missing"] if r["missing"] else "无"}')
        if r.get('duplicates'):
            for norm, keys in r['duplicates'].items():
                print(f'  重复条目: {keys}')
        else:
            print('  重复条目: 无')
        for row in r['semantic']:
            print(f'  {row["id"]}: {row["expected_relationship"][:50]}')
            for ref in row['refs']:
                print(f'      {ref["key"]:20s} {ref["year"]:4s} {ref["title"][:70]}')

    if args.json:
        out = os.path.join(WORKSPACE, 'audit_evidence_keys.json')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=1)
        print(f'\nJSON 写出: {out}')

    # 汇总退出码：主案例缺失键 > 0 时非零（fail-fast）
    missing_total = sum(len(r['missing']) for r in all_results)
    dup_total = sum(len(v) for r in all_results for v in r.get('duplicates', {}).values())
    print(f'\n汇总: 缺失键 {missing_total} 个 | 重复条目 {dup_total} 个')
    sys.exit(1 if (missing_total or dup_total) else 0)


if __name__ == '__main__':
    main()
