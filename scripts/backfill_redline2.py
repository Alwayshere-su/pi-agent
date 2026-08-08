# -*- coding: utf-8 -*-
"""红线2 字段回填脚本 — 为历史 hypotheses.json 补 known_prior_work / incremental_claim。

背景(2026-10 修复):dataclass 与 prompt 中已有这两个字段要求,但 8 个主题的
hypotheses.json 均无——LLM 输出缺字段时静默落盘。本脚本为历史产物补全:
  - 有值则保留;
  - 缺失时从 evidence_chain / description 派生占位说明,并标 redline2_complete=false
    (不伪造内容,如实标注待补写);
  - 同时做 UTF-8 编码修复:检测 GBK/乱码内容并重新以 UTF-8 落盘。

用法(项目根目录):
    python -X utf8 scripts/backfill_redline2.py                 # 回填全部主题
    python -X utf8 scripts/backfill_redline2.py --run-dir mof_rerun
    python -X utf8 scripts/backfill_redline2.py --dry-run       # 只报告不改写
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_hypotheses(path: Path):
    """读取 hypotheses.json,处理 GBK 乱码(常见历史产物)。"""
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            text = raw.decode(enc)
            return json.loads(text), enc
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return None, None


def _backfill_one(h: dict) -> bool:
    """为单条假设补齐红线2 字段,返回是否发生修改。"""
    changed = False
    if not h.get("known_prior_work"):
        chain = h.get("evidence_chain") or []
        real_refs = [c for c in chain
                     if not str(c).startswith("[") and not str(c).startswith("Novelty")]
        if real_refs:
            h["known_prior_work"] = (
                f"已有文献依据(evidence_chain 编号: {', '.join(str(r) for r in real_refs[:4])})，"
                "具体结论需人工/LLM 补写")
        else:
            h["known_prior_work"] = "本假设基于研究 Gap 分析提出，具体已知工作待补写"
        h["redline2_complete"] = False
        changed = True
    else:
        h.setdefault("redline2_complete", True)
    if not h.get("incremental_claim"):
        h["incremental_claim"] = (
            "相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)")
        h["redline2_complete"] = False
        changed = True
    else:
        h.setdefault("redline2_complete", True)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="红线2 字段历史产物回填")
    parser.add_argument("--run-dir", default=None,
                        help="只处理指定主题;默认扫描 workspace/outputs/*")
    parser.add_argument("--dry-run", action="store_true",
                        help="只报告不改写")
    args = parser.parse_args()

    if args.run_dir:
        targets = [Path(f"workspace/outputs/{args.run_dir}/literature_survey/discovery/hypotheses.json")]
    else:
        targets = sorted(Path("workspace/outputs").glob(
            "*/literature_survey/discovery/hypotheses.json"))
        # 顶层主输出目录(literature_survey 本身)不在 glob 模式内,单独追加
        top = Path("workspace/outputs/literature_survey/discovery/hypotheses.json")
        if top.exists() and top not in targets:
            targets.append(top)

    total_fixed = 0
    for path in targets:
        if not path.exists():
            print(f"[skip] 不存在: {path}")
            continue
        data, enc = _load_hypotheses(path)
        if data is None:
            print(f"[warn] 无法解析(编码/JSON 均失败): {path}")
            continue
        hyps = data if isinstance(data, list) else data.get("hypotheses", [])
        n_changed = 0
        for h in hyps:
            if isinstance(h, dict) and _backfill_one(h):
                n_changed += 1
        total_fixed += n_changed
        has_redline2 = all(h.get("known_prior_work") and h.get("incremental_claim")
                           for h in hyps if isinstance(h, dict))
        if args.dry_run:
            print(f"[dry-run] {path}: {n_changed} 条假设补齐红线2, 现全部含字段={has_redline2} (编码={enc})")
            continue
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print(f"[ok] {path}: {n_changed} 条假设补齐红线2, 现全部含字段={has_redline2} (原编码={enc}, 已重写为 UTF-8)")
        except OSError as e:
            print(f"[error] 写回失败 {path}: {e}")

    print(f"\n合计: {total_fixed} 条假设补齐红线2 字段")
    return 0


if __name__ == "__main__":
    sys.exit(main())
