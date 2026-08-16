# -*- coding: utf-8 -*-
"""fix_explanation_evidence_chains.py — 把 SP_LIST 的 curated 证据链同步进 EXPLANATION

根因（见 HARNESS_FIX_FRAMEWORK.md W-2b）：
  build_route_a_docs.py 的 format_evidence_list 正则只认 `p#/TE#/P#/r#` 键，
  不认 MOFv4/PVSK 的「作者 年份 (key) 一句话描述」证据链，于是输出
  「（证据链条目存在，但需清理格式）」占位符。SP_LIST 已手工填实（权威源），
  EXPLANATION 未同步 → 10 处占位。

修法（零虚构、零手抄）：
  从 ROUTE_A_SP_LIST.md 按 SPR-xxx 提取 `| **证据链** | X |` 单元格，
  映射到 ROUTE_A_EXPLANATION.md 同 SPR-xxx 小节下的
  `**关键文献证据**：（证据链条目存在，但需清理格式）`，替换为 X。
  不动 EXPLANATION 其它任何内容（科学解释/已知工作/增量贡献/统计验证）。

用法：
  python scripts/fix_explanation_evidence_chains.py                 # dry-run：报告映射与替换预览
  python scripts/fix_explanation_evidence_chains.py --apply PATH...  # 写回（可传多份 .md）
"""
import argparse
import os
import re
import sys

PLACEHOLDER = '**关键文献证据**：（证据链条目存在，但需清理格式）'

SP_LIST_HEAD = re.compile(r'^### (SPR-[A-Za-z0-9-]+) — ')
EXPL_HEAD = re.compile(r'^#### (SPR-[A-Za-z0-9-]+)：')
EVID_CELL = re.compile(r'^\| \*\*证据链\*\* \| (.+) \|$')


def extract_sp_evidence(sp_list_path: str) -> dict[str, str]:
    """从 SP_LIST 提取 SPR-xxx → 证据链文本（`| **证据链** | X |` 单元格内文）。"""
    mapping: dict[str, str] = {}
    with open(sp_list_path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    cur = None
    for line in lines:
        m = SP_LIST_HEAD.match(line)
        if m:
            cur = m.group(1)
            continue
        if cur:
            m2 = EVID_CELL.match(line)
            if m2:
                mapping[cur] = m2.group(1).strip()
    return mapping


def apply_to_md(md_path: str, mapping: dict[str, str], dry_run: bool) -> int:
    """在单个 EXPLANATION .md 上替换占位符，返回替换数。"""
    with open(md_path, encoding='utf-8') as f:
        raw = f.read()
    lines = raw.split('\n')

    cur = None
    changed = 0
    missing_ids = []
    out = []
    for line in lines:
        m = EXPL_HEAD.match(line)
        if m:
            cur = m.group(1)
            out.append(line)
            continue
        if cur and line == PLACEHOLDER:
            if cur in mapping:
                out.append(f'**关键文献证据**：{mapping[cur]}')
                changed += 1
            else:
                missing_ids.append(cur)
                out.append(line)
        else:
            out.append(line)

    if missing_ids:
        print(f'  [warn] {md_path}: 占位符存在但 SP_LIST 无对应证据链: {missing_ids}', file=sys.stderr)

    if not dry_run and changed:
        new_raw = '\n'.join(out)
        # 保留换行约定（LF/CRLF）与尾随换行状态
        had_trailing_nl = raw.endswith('\n')
        uses_crlf = raw.count('\r\n') >= (raw.count('\n') // 2) and '\r\n' in raw
        if uses_crlf:
            new_raw = new_raw.replace('\n', '\r\n')
        if had_trailing_nl and not new_raw.endswith('\n'):
            new_raw += '\r\n' if uses_crlf else '\n'
        with open(md_path, 'w', encoding='utf-8', newline='') as f:
            f.write(new_raw)
    return changed


def main():
    ap = argparse.ArgumentParser(description='同步 SP_LIST 证据链到 EXPLANATION')
    ap.add_argument('--apply', nargs='+', metavar='PATH',
                    help='写回指定 EXPLANATION .md（默认 dry-run）')
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sp_list = os.path.join(root, 'workspace', 'outputs', 'ROUTE_A_SP_LIST.md')
    mapping = extract_sp_evidence(sp_list)
    print(f'从 SP_LIST 提取 {len(mapping)} 条证据链')

    if not args.apply:
        # dry-run：只对 workspace 主文件预览
        expl = os.path.join(root, 'workspace', 'outputs', 'ROUTE_A_EXPLANATION.md')
        n = apply_to_md(expl, mapping, dry_run=True)
        print(f'dry-run: {expl} 可替换 {n} 处')
        for sid in sorted(mapping):
            print(f'  {sid}: {mapping[sid]}')
        print('（加 --apply PATH... 落盘）')
        return

    for p in args.apply:
        if not os.path.exists(p):
            print(f'[missing] {p}', file=sys.stderr)
            continue
        n = apply_to_md(p, mapping, dry_run=False)
        print(f'{p}: 替换 {n} 处证据链占位符')


if __name__ == '__main__':
    main()
