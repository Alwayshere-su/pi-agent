# -*- coding: utf-8 -*-
"""backfill_best_scores.py — 把 search_h*.json 的真实 best_score 回填到 hypotheses.json 与 SP 清单

根因（见 HARNESS_FIX_FRAMEWORK.md W-1 / P0-1）：
  h_run_discovery_search 只把分数写入 search_h{i}.json（含 hypothesis_index 字段），
  从未回填 hypotheses.json 的 best_score 字段；build_route_a_docs.py 只读后者，
  导致 SP 清单「Best Score」列全为 0.000，与报告/CROSS_THEME_REPORT 的真实分数矛盾。

事实源：search_h*.json 的 `hypothesis_index`（0 基）→ `best_score`。
        按 hypothesis_index 映射，**不按文件名顺序猜**。

用法：
  python scripts/backfill_best_scores.py                     # dry-run：逐主题报告 old→new
  python scripts/backfill_best_scores.py --apply             # 写回 hypotheses.json（6 主题）
  python scripts/backfill_best_scores.py --sync-md PATH [PATH ...]
      # 外科式更新 .md 的「Best Score」单元格（保留所有其他手工内容，如 [数值验证] 注解）
      # PATH 可传 workspace 与交付目录两份，逐个更新

零虚构：本脚本只搬运 search_h*.json 里已存在的真实分数，不生成任何数值。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_route_a_docs import THEMES, discovery_base  # 复用主题配置与路径工具


def load_search_scores(cfg) -> dict[int, float]:
    """读一个主题下所有 search_h*.json，返回 {hypothesis_index: best_score}。"""
    base = discovery_base(cfg)
    scores: dict[int, float] = {}
    if not os.path.isdir(base):
        return scores
    for fn in sorted(os.listdir(base)):
        if not re.match(r'search_h\d+\.json$', fn):
            continue
        path = os.path.join(base, fn)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'hypothesis_index' in data:
            scores[int(data['hypothesis_index'])] = float(data.get('best_score', 0.0))
    return scores


def load_hypotheses_raw(cfg):
    path = os.path.join(discovery_base(cfg), 'hypotheses.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def hypotheses_path(cfg) -> str:
    return os.path.join(discovery_base(cfg), 'hypotheses.json')


def _as_raw_list(data):
    """兼容 list 顶层与 dict（'hypotheses'/'results' 键）两种结构。"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('hypotheses', 'results'):
            if isinstance(data.get(key), list):
                return data[key]
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def backfill_theme(cfg, apply: bool) -> list[tuple]:
    """回填单主题；返回变更列表 [(hypo_id, old, new)]。"""
    scores = load_search_scores(cfg)
    if not scores:
        print(f'  [{cfg.key}] 无 search_h*.json，跳过', file=sys.stderr)
        return []
    data = load_hypotheses_raw(cfg)
    raw_list = _as_raw_list(data)
    changes = []
    for i, h in enumerate(raw_list):
        if i not in scores:
            continue
        old = h.get('best_score')
        new = scores[i]
        # 已有非零值 → 跳过并报告（不覆盖人工可能已回填的分数）
        if old is not None:
            try:
                if float(old) > 0:
                    print(f'  [skip] {cfg.key} #{i} 已是 {old}')
                    continue
            except (TypeError, ValueError):
                pass
        changes.append((h.get('id', f'hypo_{i + 1}'), old, new))
        if apply:
            h['best_score'] = new
    if apply and changes:
        path = hypotheses_path(cfg)
        # 读取原始字节，保留换行约定（LF/CRLF）与尾随换行状态，避免 diff 噪声
        with open(path, 'rb') as f:
            raw = f.read()
        had_trailing_nl = raw.endswith(b'\n')
        uses_crlf = raw.count(b'\r\n') >= (raw.count(b'\n') // 2) and b'\r\n' in raw
        out = json.dumps(data, ensure_ascii=False, indent=2)
        if uses_crlf:
            out = out.replace('\n', '\r\n')
        if had_trailing_nl:
            out += '\r\n' if uses_crlf else '\n'
        with open(path, 'wb') as f:
            f.write(out.encode('utf-8'))
        print(f'  [apply] {cfg.key}: {path}')
    return changes


def build_spr_score_map() -> dict[str, float]:
    """按 THEMES 顺序构建 SPR-{prefix}-{i+1:02d} → best_score 映射（与文档顺序一致）。"""
    spr_scores: dict[str, float] = {}
    for cfg in THEMES:
        scores = load_search_scores(cfg)
        for i in sorted(scores):
            spr = f'SPR-{cfg.prefix}-{i + 1:02d}'
            spr_scores[spr] = scores[i]
    return spr_scores


def sync_md(md_path: str) -> int:
    """外科式更新单个 .md 的 Best Score 单元格，返回修改行数。

    只改「| **Best Score** | X |」行，其余内容（含手工 [数值验证] 注解、已知工作、
    证据链等）逐字节保留。分段按「### SPR-xxx —」标题定位，避免跨段误替换。
    """
    spr_scores = build_spr_score_map()
    with open(md_path, encoding='utf-8') as f:
        lines = f.read().split('\n')

    current_spr = None
    changed = 0
    out = []
    for line in lines:
        m = re.match(r'^### (SPR-[A-Za-z0-9-]+) — ', line)
        if m:
            current_spr = m.group(1)
            out.append(line)
            continue
        if current_spr and line.startswith('| **Best Score** |') and current_spr in spr_scores:
            new = spr_scores[current_spr]
            line = f'| **Best Score** | {new:.3f} |'
            changed += 1
        out.append(line)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    return changed


def main():
    ap = argparse.ArgumentParser(description='回填 Best Score 到 hypotheses.json 与 SP 清单')
    ap.add_argument('--apply', action='store_true', help='写回 hypotheses.json（默认 dry-run）')
    ap.add_argument('--sync-md', nargs='+', metavar='PATH',
                    help='外科式更新指定 .md 的 Best Score 单元格（可多个路径）')
    args = ap.parse_args()

    if not args.sync_md:
        print('=== Best Score 回填（hypotheses.json）===')
        total = 0
        for cfg in THEMES:
            print(f'[{cfg.key}]')
            changes = backfill_theme(cfg, apply=args.apply)
            for hid, old, new in changes:
                old_s = '缺失' if old is None else f'{old}'
                print(f'  {hid}: {old_s} -> {new:.6f}')
            total += len(changes)
        print(f'\n共 {total} 条待回填' + ('（已 --apply 写回）' if args.apply else '（dry-run，未落盘；加 --apply 生效）'))

    if args.sync_md:
        print('=== 外科式更新 .md Best Score ===')
        for p in args.sync_md:
            if not os.path.exists(p):
                print(f'  [missing] {p}', file=sys.stderr)
                continue
            n = sync_md(p)
            print(f'  {p}: 更新 {n} 处 Best Score')


if __name__ == '__main__':
    main()
