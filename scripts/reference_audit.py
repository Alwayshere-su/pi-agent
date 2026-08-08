# -*- coding: utf-8 -*-
"""
引用真实性回查 — Reference Audit for GOAI 文献调研 Agent
========================================================
赛题红线 4「零虚假引用」的自动化防线：扫描调研报告 / 知识图谱 / Gap 报告 /
发现报告中的所有引用（DOI / paper_id / 作者-年份），与真实检索结果
（search_results.json）逐条对账，输出「不可追溯引用」清单。

用法（项目根目录执行）：
    python scripts/reference_audit.py                 # 默认 run-dir=survey
    python scripts/reference_audit.py --run-dir mof_rerun

输出：
    - 控制台摘要 + 退出码（0=审计完成；存在高风险不可追溯引用时退出码 1）
    - workspace/outputs/<run-dir>/literature_survey/discovery/reference_audit.md

两类对账结果严格区分：
  - HIGH RISK：DOI / paper_id 形式引用但检索结果中无匹配（红线 4 高危，疑似编造）
  - WARNING  ：作者-年份形式无法匹配（可能来自领域常识/未检索文献，需人工确认）

约束：不联网、不调用 LLM；只读产物与缓存；纯标准库。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# 项目根（scripts/ → 上两级）
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.config import SURVEY_DIR  # noqa: E402  默认输出根


# ═══════════════════════════════════════════════════════════════
# 引用提取
# ═══════════════════════════════════════════════════════════════

_DOI_RE = re.compile(
    r"(?:doi\s*:\s*|doi\.org/|dx\.doi\.org/)(10\.\d{4,9}/[^\s\)\],;|]+)",
    re.IGNORECASE)
_PAPER_ID_RE = re.compile(r"\b(p\d{1,3})\b", re.IGNORECASE)
_AUTHOR_YEAR_RE = re.compile(r"\b([A-Z][a-zA-Z\-]{1,30})(?:\s+et\s+al\.?)?\s+(19\d{2}|20[0-2]\d)\b")


def _normalize_doi(raw: str) -> str:
    # 去掉 markdown 反引号/星号/引号等装饰符，再清理首尾标点
    for ch in "`'\"*_#|":
        raw = raw.replace(ch, "")
    return raw.strip().strip(".,;:()").rstrip(".").lower()


def extract_references(text: str) -> dict:
    """从文本提取引用。返回 {"dois": [...], "paper_ids": [...], "author_years": [...]}。"""
    dois = [_normalize_doi(m.group(1)) for m in _DOI_RE.finditer(text)]
    paper_ids = [m.group(1).lower() for m in _PAPER_ID_RE.finditer(text)]
    author_years = [(m.group(1), int(m.group(2))) for m in _AUTHOR_YEAR_RE.finditer(text)]
    return {"dois": dois, "paper_ids": paper_ids, "author_years": author_years}


# ═══════════════════════════════════════════════════════════════
# 检索结果索引
# ═══════════════════════════════════════════════════════════════

def load_papers(run_dir: str) -> list:
    """加载 search_results.json（支持 run_dir 隔离目录与根缓存目录）。"""
    candidates = [
        ROOT / "workspace" / "data" / "literature_cache" / run_dir / "search_results.json",
        ROOT / "workspace" / "data" / "literature_cache" / "search_results.json",
        ROOT / "workspace" / "data" / "literature_cache" / run_dir / "search_log.jsonl",
    ]
    for path in candidates:
        if not path.exists():
            continue
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
                for v in data.values():
                    if isinstance(v, list) and v:
                        return v
            except Exception as e:
                print(f"  ⚠️ 无法解析 {path}: {e}", file=sys.stderr)
        elif path.suffix == ".jsonl":
            papers = []
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    papers.append(json.loads(line))
                except Exception:
                    continue
            if papers:
                return papers
    return []


def build_paper_index(papers: list) -> dict:
    """构造检索结果索引：by_doi / by_paper_id / by_author_year / by_first_author_year。"""
    idx = {"by_doi": {}, "by_paper_id": {}, "by_author_year": defaultdict(list),
           "by_first_author_year": defaultdict(list)}
    for p in papers:
        if not isinstance(p, dict):
            continue
        doi = _normalize_doi(str(p.get("doi") or ""))
        if doi:
            idx["by_doi"][doi] = p
        pid = str(p.get("paper_id") or "").lower()
        if pid:
            idx["by_paper_id"][pid] = p
        year = p.get("year")
        authors = p.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]
        if year:
            for a in authors:
                surname = str(a).strip().split()[-1] if str(a).strip() else ""
                if surname:
                    idx["by_author_year"][(surname.lower(), str(year))].append(p)
            first_author = str(authors[0]).strip().split()[-1] if authors else ""
            if first_author:
                idx["by_first_author_year"][(first_author.lower(), str(year))].append(p)
    return idx


def trace_doi(doi: str, idx: dict) -> bool:
    return doi in idx["by_doi"]


def trace_paper_id(pid: str, idx: dict) -> bool:
    return pid in idx["by_paper_id"]


def trace_author_year(author: str, year: int, idx: dict) -> bool:
    key = (author.lower(), str(year))
    return bool(idx["by_author_year"].get(key) or idx["by_first_author_year"].get(key))


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def audit_file(path: Path, idx: dict) -> dict:
    """审计单个文件，返回 {"path", "dois", "paper_ids", "author_years",
    "high_risk": [...], "warnings": [...]}。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    refs = extract_references(text)
    high_risk = []
    warnings = []
    for doi in refs["dois"]:
        if not trace_doi(doi, idx):
            high_risk.append({"type": "doi", "value": doi})
    for pid in refs["paper_ids"]:
        if not trace_paper_id(pid, idx):
            high_risk.append({"type": "paper_id", "value": pid})
    for author, year in refs["author_years"]:
        if not trace_author_year(author, year, idx):
            warnings.append({"type": "author_year", "value": f"{author} {year}"})
    return {
        "path": str(path.resolve().relative_to(ROOT)),
        "dois": refs["dois"], "paper_ids": refs["paper_ids"],
        "author_years": [f"{a} {y}" for a, y in refs["author_years"]],
        "high_risk": high_risk,
        "warnings": warnings,
    }


def audit_run(run_dir: str) -> dict:
    """审计一个 run_dir 的全部报告产物。"""
    out_root = ROOT / "workspace" / "outputs" / run_dir / "literature_survey"
    if not out_root.exists():
        out_root = Path(str(SURVEY_DIR))  # 回退默认
    papers = load_papers(run_dir)
    idx = build_paper_index(papers)

    targets = []
    for name in ("survey_report.md", "knowledge_graph.md", "gap_report.md",
                 "paper_summaries.md"):
        p = out_root / name
        if p.exists():
            targets.append(p)
    disc = out_root / "discovery"
    if disc.exists():
        # 排除审计报告自身（避免自引用污染）
        targets.extend(sorted(p for p in disc.glob("*.md")
                              if p.name != "reference_audit.md"))

    file_results = [audit_file(p, idx) for p in targets]
    total = {"dois": 0, "paper_ids": 0, "author_years": 0}
    high_risk_total = 0
    warning_total = 0
    for fr in file_results:
        total["dois"] += len(fr["dois"])
        total["paper_ids"] += len(fr["paper_ids"])
        total["author_years"] += len(fr["author_years"])
        high_risk_total += len(fr["high_risk"])
        warning_total += len(fr["warnings"])

    return {
        "run_dir": run_dir,
        "out_root": str(out_root),
        "n_papers": len(papers),
        "total_refs": total,
        "high_risk_total": high_risk_total,
        "warning_total": warning_total,
        "files": file_results,
    }


def write_report(result: dict) -> Path:
    """写审计报告 md，返回报告路径。"""
    out = ROOT / result["out_root"] / "discovery"
    out.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 引用真实性回查报告（Reference Audit）",
        "",
        f"> run-dir: `{result['run_dir']}` | 检索结果论文数: {result['n_papers']}",
        f"> 生成时间: {__import__('time').strftime('%Y-%m-%d %H:%M')}",
        f"> 工具: scripts/reference_audit.py（赛题红线4 零虚假引用的自动化防线）",
        "",
        "## 汇总",
        "",
        "| 指标 | 数量 |",
        "|------|------|",
        f"| DOI 引用 | {result['total_refs']['dois']} |",
        f"| paper_id 引用 | {result['total_refs']['paper_ids']} |",
        f"| 作者-年份引用 | {result['total_refs']['author_years']} |",
        f"| **高风险不可追溯引用（DOI/paper_id）** | **{result['high_risk_total']}** |",
        f"| 警告（作者-年份未匹配，可能来自领域常识） | {result['warning_total']} |",
        "",
        "> 高风险 = 报告中的 DOI / paper_id 在检索结果（search_results.json）中找不到，"
        "疑似编造引用（红线 4，需逐条人工核实）。",
        "> 警告 = 作者-年份形式无法匹配，可能是领域常识引用（如 Caskey 2008 属经典文献）"
        "或未检索到的文献，需人工确认后决定是否补充检索。",
        "",
        "## 逐文件明细",
        "",
    ]
    for fr in result["files"]:
        lines.append(f"### {fr['path']}")
        lines.append("")
        lines.append(f"- DOI: {len(fr['dois'])} | paper_id: {len(fr['paper_ids'])} | "
                     f"作者-年份: {len(fr['author_years'])}")
        if fr["high_risk"]:
            lines.append(f"- **高风险不可追溯: {len(fr['high_risk'])}**")
            for item in fr["high_risk"]:
                lines.append(f"  - `{item['value']}`（{item['type']}）")
        if fr["warnings"]:
            lines.append(f"- 警告未匹配: {len(fr['warnings'])}")
            for w in fr["warnings"][:20]:
                lines.append(f"  - `{w['value']}`")
            if len(fr["warnings"]) > 20:
                lines.append(f"  - … 共 {len(fr['warnings'])} 条")
        lines.append("")
    report_path = out / "reference_audit.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="引用真实性回查（红线4 防线）")
    parser.add_argument("--run-dir", default="survey", help="主题运行目录名（默认 survey）")
    args = parser.parse_args()

    result = audit_run(args.run_dir)
    report_path = write_report(result)

    print(f"引用回查完成 — run-dir: {result['run_dir']}")
    print(f"  检索结果论文: {result['n_papers']} 篇")
    print(f"  引用统计: DOI {result['total_refs']['dois']} | "
          f"paper_id {result['total_refs']['paper_ids']} | "
          f"作者-年份 {result['total_refs']['author_years']}")
    print(f"  ✅ 可追溯引用: "
          f"{result['total_refs']['dois'] + result['total_refs']['paper_ids'] - result['high_risk_total']}"
          f"（DOI/paper_id）")
    print(f"  ⚠️ 高风险不可追溯: {result['high_risk_total']}（需人工核实，红线4）")
    print(f"  ⚠️ 作者-年份未匹配警告: {result['warning_total']}")
    print(f"  报告: {report_path}")
    # 高风险存在时退出码 1（提示红线4 风险），无高风险退出码 0
    return 1 if result["high_risk_total"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
