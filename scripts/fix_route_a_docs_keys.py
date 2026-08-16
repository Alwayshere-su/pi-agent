# -*- coding: utf-8 -*-
"""fix_route_a_docs_keys.py — 同步主案例证据链键变更到 ROUTE_A_SP_LIST.md / ROUTE_A_EXPLANATION.md

W-3 完成后的事实源变更：
  1. 证据链键合并：p210 -> p116（MOF@MOF 核壳，同一篇论文，保留 p116）；
  2. 证据链键移除：p9（主案例 bib 中不存在、正文未引用，无法定位真实文献）；
  3. 已知工作文本更新：hypo_1 / hypo_3 的 known_prior_work 随 bib 键映射修复同步改写。

本脚本只做精确替换，不重排其它任何内容（保留两份文档的 curated 表述）。
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TARGETS = [
    os.path.join(ROOT, 'workspace', 'outputs', 'ROUTE_A_SP_LIST.md'),
    os.path.join(ROOT, 'workspace', 'outputs', 'ROUTE_A_EXPLANATION.md'),
    os.path.join(ROOT, '路线A_构效关系清单与解释文档', 'ROUTE_A_SP_LIST.md'),
    os.path.join(ROOT, '路线A_构效关系清单与解释文档', 'ROUTE_A_EXPLANATION.md'),
]

# (旧, 新) 精确替换对
REPLACEMENTS = [
    # 证据链键：p210 -> p116
    ('p210, p224, p201, p186, p182', 'p116, p224, p201, p186, p182'),
    ('p210, p224, p201, p186, p182,', 'p116, p224, p201, p186, p182,'),
    ('（p224/p210/p201）', '（p224/p116/p201）'),
    # 证据链键：移除 p9（精确到 "p9, " 与 ", p9"）
    ('p13, p7, p192, p9, r10s1_a9ed68d1734e', 'p13, p7, p192, r10s1_a9ed68d1734e'),
    ('p13, p7, p192, p9,', 'p13, p7, p192,'),
    # hypo_1 已知工作（SP_LIST 单元格 / EXPLANATION 段落）
    (
        '已有文献确立开放金属位点（OMS）密度与 CO₂ 容量/选择性正相关（p22 钴基 MOF 吡啶位点+OMS、p24 ZIF-8@Zn-MOF-74 核壳），离子液体复合与膜分离可调 CO₂/N₂ 选择性（p65、p67），TSA 循环给出工艺侧权衡（p147）',
        '已有文献确立开放金属位点（OMS）密度与 CO₂ 容量/选择性正相关（p2 ZIF-8@Zn-MOF-74 核壳、p24 NiCo-MOF-74 微波合成 OMS 增强），双金属体系实验验证组分协同：CoMn-MOF-74 1:1 最佳（p65）、Fe/Cu-MOF 双金属优于单金属（p67）、Ni-Cu-MOF-74 MMM 高选择性（p22）、MIL-101(Cr,Mg) 双金属高容量高选择性（p147）',
    ),
    # hypo_3 已知工作
    (
        '已有文献确立 Qst 与选择性/再生能耗同向权衡的方向（p27 等温吸附热计算方法、p129 DAC 挑战综述），缺陷/核壳工程可调节 Qst（p117、p116）',
        '已有文献确立 Qst 与选择性/再生能耗同向权衡的方向（p27 MOF-74(Ni) Qst 调控、p129 SBA-15 等量吸附焓），Qst 计算方法成熟（p117），核壳工程可调节 Qst（p116）',
    ),
]


def main():
    dry = '--apply' not in sys.argv
    for path in TARGETS:
        if not os.path.exists(path):
            print(f'[skip] {path} 不存在')
            continue
        raw = open(path, encoding='utf-8').read()
        total = 0
        for old, new in REPLACEMENTS:
            n = raw.count(old)
            if n:
                raw = raw.replace(old, new)
                total += n
                print(f'  {os.path.basename(path)}: {n} 处替换 -> {old[:40]}...')
        if not dry and total:
            open(path, 'w', encoding='utf-8', newline='').write(raw)
            print(f'[written] {path}')
        else:
            print(f'[dry-run] {path}: 共 {total} 处待替换')
    print('（加 --apply 写回）' if dry else '完成')


if __name__ == '__main__':
    main()
