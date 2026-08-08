# -*- coding: utf-8 -*-
"""向 survey_report.md 追加「证据链」章节 — GOAI 红线 1 报告层闭环。

用法（项目根目录执行，Windows 建议加 -X utf8）：
    python -X utf8 scripts/inject_evidence_chain.py --run-dir mof_rerun          # dry-run：只打印
    python -X utf8 scripts/inject_evidence_chain.py --run-dir mof_rerun --apply # 追加到 survey_report.md
    python -X utf8 scripts/inject_evidence_chain.py --self-check                # 用 mof_rerun 真实产物自检

默认 dry-run：把生成的「## 证据链」章节打印到 stdout，不写任何文件。
--apply：把章节追加到 {SURVEY_DIR}/survey_report.md；若文件已含 `## 证据链`
         章节则跳过（幂等），绝不重复追加。
--self-check：固定用 mof_rerun 产物跑一次 dry-run 并断言输出非空、假设数≥1。

运行目录约定与 main.py 对齐：调用 utils.config.set_run_dir(run_dir) 后取
cfg.SURVEY_DIR（默认 workspace/outputs/<run_dir>/literature_survey）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 项目根（scripts/ → 上两级），保证可被任意工作目录直接调用
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.config import set_run_dir  # noqa: E402
import utils.config as _cfg  # noqa: E402
from literature_agent.evidence_chain_report import (  # noqa: E402
    build_evidence_chain_section,
)

_HYPOTHESIS_HEAD_RE = re.compile(r"^### 假设 \d+｜", re.MULTILINE)
_EVIDENCE_CHAIN_HEAD_RE = re.compile(r"^##\s*证据链\b", re.MULTILINE)


def _count_hypotheses(section: str) -> int:
    return len(_HYPOTHESIS_HEAD_RE.findall(section))


def _apply_section(survey_dir: Path, section: str) -> str:
    """把证据链章节追加到 survey_report.md；幂等：已含「## 证据链」则跳过。

    Returns:
        动作说明文本（用于打印）。
    """
    report = survey_dir / "survey_report.md"
    if not report.exists():
        raise FileNotFoundError(
            f"survey_report.md 不存在：{report}。请先运行文献调研生成主报告。"
        )
    content = report.read_text(encoding="utf-8")
    if _EVIDENCE_CHAIN_HEAD_RE.search(content):
        return f"[skip] {report} 已包含 `## 证据链` 章节，未重复追加（幂等）。"
    if not content.endswith("\n"):
        content += "\n"
    with report.open("w", encoding="utf-8", newline="\n") as f:
        f.write(content + "\n" + section)
    return f"[ok] 已将「## 证据链」章节追加到 {report}"


def _run_self_check() -> int:
    """用 mof_rerun 真实产物验证生成链路（dry-run，不写文件）。"""
    set_run_dir("mof_rerun")
    survey_dir = Path(_cfg.SURVEY_DIR)
    print(f"[self-check] survey_dir = {survey_dir}")
    section = build_evidence_chain_section(survey_dir)
    n_hypo = _count_hypotheses(section)
    n_risk = section.count("⚠ 需人工核对")
    assert section.strip(), "生成的证据链章节为空"
    assert "## 证据链" in section, "章节缺少 `## 证据链` 标题"
    assert n_hypo >= 1, f"假设数 < 1（实际 {n_hypo}）"
    print(f"[self-check] 章节长度 {len(section)} 字符，假设 {n_hypo} 条，"
          f"需人工核对标记 {n_risk} 处")
    print("[self-check] PASS：非空章节 + 假设数≥1（mof_rerun 真实产物 dry-run）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="向 survey_report.md 追加证据链章节（红线 1 报告层闭环）"
    )
    parser.add_argument(
        "--run-dir", default="survey",
        help="主题运行目录名（默认 survey，与 main.py 对齐），如 mof_rerun"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="把生成的证据链章节追加到 {SURVEY_DIR}/survey_report.md（默认只打印，不写文件）"
    )
    parser.add_argument(
        "--self-check", action="store_true",
        help="用 mof_rerun 真实产物跑 dry-run 自检（忽略 --run-dir/--apply）"
    )
    args = parser.parse_args()

    if args.self_check:
        return _run_self_check()

    set_run_dir(args.run_dir)
    # 动态读取 set_run_dir 更新后的值（模块级 import 是快照，会拿到旧默认值）
    survey_dir = Path(_cfg.SURVEY_DIR)

    # ── 生成章节（只读产物，不写文件）──
    section = build_evidence_chain_section(survey_dir)

    if not args.apply:
        print(section, end="")
        print(f"\n[dry-run] 共 {_count_hypotheses(section)} 条假设证据链；"
              f"未写入任何文件。加 --apply 追加到 {survey_dir / 'survey_report.md'}")
        return 0

    # ── 幂等追加 ──
    action = _apply_section(survey_dir, section)
    print(action)
    return 0


if __name__ == "__main__":
    sys.exit(main())
