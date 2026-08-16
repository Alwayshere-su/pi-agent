# -*- coding: utf-8 -*-
"""fix_explanation_mc_summary.py — 把 EXPLANATION 里 5 处裸 dict 的「统计验证」改成中文一句话

根因（见 HARNESS_FIX_FRAMEWORK.md W-2c）：
  model_comparison.json 的 verdict 字段是嵌套 dict {'verdict':..., 'reason':...}；
  旧生成器 format_mc_summary 直接 str(verdict) 泄出裸 dict，如
  {'verdict': 'insufficient', 'reason': '候选或经典 R² 缺失，无法判定', ...}。
  本脚本把裸 dict 替换为「中文判定标签：reason」一句话。零虚构——reason 文本
  与 delta_r2/f_supported 等全部取自 hypotheses.json 里已存在的字段。

用法：
  python scripts/fix_explanation_mc_summary.py                 # dry-run
  python scripts/fix_explanation_mc_summary.py --apply PATH...  # 写回（可传多份 .md）
"""
import argparse
import os
import sys

# 精确的裸 dict → 中文一句话（两条 distinct 文本，共 5 处）
REPLACEMENTS = {
    "{'verdict': 'insufficient', 'reason': '候选或经典 R² 缺失，无法判定', 'delta_r2': None, 'f_supported': False, 'ci_supported': False}":
        '无法判定：候选或经典 R² 缺失，无法判定',
    "{'verdict': 'no_improvement', 'reason': '候选 R²=0.0214 与经典 R²=-0.0000 差距不足（ΔR²=+0.0214，<0.05 阈值），无显著提升', 'delta_r2': 0.0214, 'f_supported': False, 'ci_supported': False}":
        '无显著提升：候选 R²=0.0214 与经典 R²=-0.0000 差距不足（ΔR²=+0.0214，<0.05 阈值）',
}


def apply_to_md(md_path: str, dry_run: bool) -> int:
    with open(md_path, encoding='utf-8') as f:
        raw = f.read()
    changed = 0
    for old, new in REPLACEMENTS.items():
        n = raw.count(old)
        if n:
            changed += n
            raw = raw.replace(old, new)
    if not dry_run and changed:
        with open(md_path, 'w', encoding='utf-8', newline='') as f:
            f.write(raw)
    return changed


def main():
    ap = argparse.ArgumentParser(description='格式化 EXPLANATION 的裸 dict 统计验证')
    ap.add_argument('--apply', nargs='+', metavar='PATH',
                    help='写回指定 EXPLANATION .md（默认 dry-run）')
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    expl = os.path.join(root, 'workspace', 'outputs', 'ROUTE_A_EXPLANATION.md')

    if not args.apply:
        n = apply_to_md(expl, dry_run=True)
        print(f'dry-run: {expl} 可替换 {n} 处裸 dict')
        for old, new in REPLACEMENTS.items():
            print(f'  {old[:60]}... -> {new}')
        print('（加 --apply PATH... 落盘）')
        return

    for p in args.apply:
        if not os.path.exists(p):
            print(f'[missing] {p}', file=sys.stderr)
            continue
        n = apply_to_md(p, dry_run=False)
        print(f'{p}: 替换 {n} 处裸 dict')


if __name__ == '__main__':
    main()
