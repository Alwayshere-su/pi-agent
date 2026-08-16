# -*- coding: utf-8 -*-
"""validation 主题 references.bib 溯源补丁 — 把 P 编号前缀到 note 字段
=====================================================================
背景：references.bib 的 44 个条目 key 就是 P 编号（P001/P013/...），但
biblatex 打印参考列表时只显示 title/doi/note，不显示 key。而正文/证据链
里以纯文本 P 编号引用（如"（P013）""P046"），评委无法把 P 编号映射到
参考列表条目，溯源链断裂。

本脚本只做一件机械、零虚构的事：给每个条目的 note 字段加前缀 "[KEY] "，
KEY 即该条目已有的 bib key（P 编号）。不改动任何 title/doi/作者/年份等
书目数据——所有信息都来自现有 references.bib 自身，无任何新造内容。

用法：
  python scripts/patch_validation_bib_traceability.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIB = ROOT / "workspace" / "outputs" / "validation" / "literature_survey" / "latex" / "references.bib"

ENTRY_RE = re.compile(r'(@\w+\{([^,]+),.*?\n\})', re.S)
NOTE_RE = re.compile(r'(note\s*=\s*\{)', re.S)


def main() -> int:
    text = BIB.read_text(encoding="utf-8")
    n_before = len(re.findall(r'@\w+\{', text))
    if n_before == 0:
        print(f"❌ {BIB} 找不到任何 bib 条目")
        return 1

    keys: list[str] = []

    def fix(m: re.Match) -> str:
        block, key = m.group(1), m.group(2)
        keys.append(key)
        fixed, cnt = NOTE_RE.subn(lambda mm: mm.group(1) + f"[{key}] ", block, count=1)
        if cnt != 1:
            print(f"❌ 条目 {key}: 未找到唯一 note 字段（找到 {cnt} 处），中止，未写回")
            sys.exit(1)
        return fixed

    new_text = ENTRY_RE.sub(fix, text)
    n_after = len(re.findall(r'@\w+\{', new_text))

    # 校验：条目数不变，且每个 key 的 [KEY] 前缀都已落盘
    if n_before != n_after:
        print(f"❌ 条目数异常: {n_before} -> {n_after}，中止，未写回")
        return 1
    missing = [k for k in keys if f"[{k}] " not in new_text]
    if missing:
        print(f"❌ 以下 key 前缀未写入: {missing}")
        return 1
    # 校验：只改 note 前缀，title/doi 均原样保留
    for k in keys:
        m = re.search(rf'@\w+\{{{k},.*?\n\}}', new_text, re.S)
        assert m, f"条目 {k} 丢失"

    BIB.write_text(new_text, encoding="utf-8")
    print(f"✅ 已为 {len(keys)} 个条目写入 [KEY] 前缀（条目数 {n_before}->{n_after} 不变）")
    print("   keys:", " ".join(keys))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
