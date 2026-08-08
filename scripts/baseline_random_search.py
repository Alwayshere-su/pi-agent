#!/usr/bin/env python3
"""
Baseline Random Search -- 同预算公平对比参照系
==================================================

在同一证据索引 (knowledge_graph.md / paper_summaries.md) 上，以相同评估预算
（默认 40 次 = 10 初始随机 + 30 轮 UCB 采集）公平对比两类策略：
  复现 Agent 的贝叶斯搜索 vs 同预算随机均匀采样
跨 10 个种子比较每假设最优打分中位数。

Usage:
    python scripts/baseline_random_search.py --iterations 40 --seeds 10
    python scripts/baseline_random_search.py --iterations 10 --seeds 2 --hypothesis 0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Windows console compatibility: force UTF-8 for stdout ──────
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Path setup: make project root importable ──────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from literature_agent.discovery import BayesianOptimizer, DiscoveryHypothesis

# Enhanced scoring module (#11: 打分函数区分度有限)
try:
    from literature_agent.scoring import enhanced_evidence_score as _v2_score_fn
    from literature_agent.scoring import legacy_evidence_score as _v1_score_fn
    from literature_agent.scoring import parse_hypothesis_window as _parse_window_fn
    from literature_agent.scoring import window_score as _window_score_fn
    _HAS_SCORING_V2 = True
except ImportError:
    _HAS_SCORING_V2 = False
    _v2_score_fn = None  # type: ignore
    _v1_score_fn = None  # type: ignore
    _parse_window_fn = None  # type: ignore
    _window_score_fn = None  # type: ignore


# ═══════════════════════════════════════════════════════════════
# Constants (replicated from pi_agent.tools.ToolHandlers)
# ═══════════════════════════════════════════════════════════════

_PROPERTY_KEYWORD_MAP: Dict[str, List[str]] = {
    "选择性": ["selectivity", "separation factor"],
    "容量": ["capacity", "uptake", "loading"],
    "吸附": ["adsorption", "uptake", "capture"],
    "焓": ["isosteric heat", "qst", "enthalpy"],
    "再生": ["regeneration", "working capacity", "energy"],
    "稳定性": ["stability", "degradation", "cyclability"],
    "扩散": ["diffusion", "kinetics"],
    "催化": ["catalysis", "tof", "conversion", "activity"],
    "效率": ["efficiency"],
    "能耗": ["energy penalty", "regeneration energy"],
    "循环": ["cyclability", "cycle"],
}

_VALUE_UNIT_RE: re.Pattern = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mmol/g|mol/kg|mmol/cm3|mg/g|kJ/mol|wt%|m2/g|bar|K|%|h|min|eV)",
    re.IGNORECASE,
)

_PROPERTY_UNIT_BUCKETS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (("mmol/g", "mol/kg", "mmol/cm3", "mg/g", "wt%"),
     ("容量", "capacity", "uptake", "loading", "吸附", "capture", "adsorption")),
    (("kj/mol",),
     ("焓", "qst", "enthalpy", "等量吸附热", "吸附热")),
    (("m2/g",),
     ("bet", "surface area", "比表面积", "表面积")),
    (("bar",),
     ("压力", "pressure")),
    (("k",),
     ("温度", "temperature")),
    (("%", "wt%"),
     ("效率", "efficiency")),
)

# Material-name pattern: chemical formulas and MOF family names
_MATERIAL_RE: re.Pattern = re.compile(
    r"\b(?:[A-Z][a-z]?\d+[A-Za-z0-9]*(?:-[A-Za-z0-9]+)*"
    r"|ZIF-\d+|UiO-\d+|MIL-\d+|HKUST-\d+|IRMOF-\d+|MOF-\d+)\b",
)

# Possible knowledge-source paths (ordered by priority)
# 多主题支持：路径从 utils.config.SURVEY_DIR 派生（main.py --run-dir 或 --survey-dir 覆盖）
from utils.config import SURVEY_DIR  # noqa: E402

_KNOWLEDGE_SOURCE_CANDIDATES: List[str] = [
    f"{SURVEY_DIR}/knowledge_graph.md",
    f"{SURVEY_DIR}/paper_summaries.md",
]

# Default output path
_DEFAULT_OUTPUT: str = f"{SURVEY_DIR}/discovery/baseline_random.json"

# Default hypotheses path
_DEFAULT_HYPOTHESES: str = f"{SURVEY_DIR}/discovery/hypotheses.json"


# ═══════════════════════════════════════════════════════════════
# Standalone helpers (adapted from ToolHandlers)
# ═══════════════════════════════════════════════════════════════

def load_knowledge_source(search_paths: Optional[List[str]] = None) -> Optional[str]:
    """Load the knowledge-source Markdown text.

    Tries each candidate in order; returns the first successfully read text,
    or None if no source exists.
    """
    if search_paths is None:
        search_paths = _KNOWLEDGE_SOURCE_CANDIDATES

    for cand in search_paths:
        p = _PROJECT_ROOT / cand
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return None


def property_keywords(property_name: str) -> List[str]:
    """Map a hypothesis property name (Chinese / mixed) to literature search keywords."""
    kws: set = set()
    text = (property_name or "").lower()
    for zh, en_list in _PROPERTY_KEYWORD_MAP.items():
        if zh in text:
            kws.update(en_list)
    for tok in re.findall(r"[a-z][a-z0-9\-]{1,20}", text):
        if len(tok) >= 2:
            kws.add(tok)
    return sorted(kws) or ["adsorption", "capacity", "selectivity"]


def unit_filter(property_name: str) -> Optional[set]:
    """Return accepted unit set given a property name, or None (= no filtering)."""
    text = (property_name or "").lower()
    matched: set = set()
    for units, kws in _PROPERTY_UNIT_BUCKETS:
        if any(k in text for k in kws):
            matched.update(units)
    return matched or None


def build_evidence_index(source_text: str, hyp: DiscoveryHypothesis) -> dict:
    """Build evidence index from knowledge-source Markdown.

    Returns a dict with keys: blocks, material_tokens, prop_keywords, values.
    """
    # Split on Markdown headings for block-level granularity
    blocks = [b.strip() for b in re.split(r"\n(?=#{1,3} )", source_text) if len(b.strip()) > 60]
    if not blocks:
        blocks = [source_text]

    # Material tokens: from hypothesis materials + regex on source text
    material_tokens: set = set()
    for m in (hyp.materials or []):
        for part in re.split(r"[/\s,，、]+", m):
            part = part.strip()
            if len(part) >= 3 and not part.isdigit():
                material_tokens.add(part.lower())
    material_tokens.update(m.lower() for m in _MATERIAL_RE.findall(source_text))

    prop_kws = property_keywords(hyp.property)
    ufilt = unit_filter(hyp.property)
    values: List[float] = []
    for block in blocks:
        lower = block.lower()
        for kw in prop_kws:
            for m in re.finditer(re.escape(kw), lower):
                window = lower[max(0, m.start() - 120) : m.end() + 160]
                for vm in _VALUE_UNIT_RE.finditer(window):
                    unit = (vm.group(2) or "").lower()
                    if ufilt is not None and unit not in ufilt:
                        continue
                    v = float(vm.group(1))
                    if 0 < v < 1e6:
                        values.append(v)
    values = sorted(set(round(v, 4) for v in values))[:500]

    return {
        "blocks": blocks,
        "material_tokens": sorted(material_tokens),
        "prop_keywords": prop_kws,
        "values": values,
    }


def search_space_from_evidence(evid: dict, hyp: DiscoveryHypothesis = None) -> Dict[str, Tuple[float, float]]:
    """Define Bayesian search space from literature values (IQR robust interval).

    Uses Tukey fences (1.5 * IQR) with median-ratio fallback to avoid outliers
    blowing up the search range, EXACTLY matching the ToolHandlers._search_space logic.

    #11 窗口感知收缩：若假设解析到物理窗口（如 hypo_3 Qst∈[25,40]），
    将 property_value 搜索空间收窄到窗口附近物理合理区间 [0.5*lo, 1.5*hi]。
    原因：hypo_3 的证据索引混入无关文献值（CO2 容量 1.49-9.5 mmol/g 与
    Qst 42/47 kJ/mol 并存），Tukey 外推撑出 [0.001, 96.3] 的巨空间，
    窗口 [25,40] 仅占 15.6%——bayesian 的 GP 在多峰巨空间难以学习窗口地形，
    random 反而靠均匀采样碰窗口。收窄后窗口占比 ≈32%，GP 可学。
    """
    values = sorted(evid.get("values") or [])
    if values:
        n = len(values)
        q1 = values[max(0, n // 4)]
        q3 = values[min(n - 1, 3 * n // 4)]
        median = values[n // 2]
        iqr = max(q3 - q1, 1e-9)
        lo = max(0.001, q1 - 1.5 * iqr)
        hi = q3 + 1.5 * iqr
        # Median-ratio floor: ensures searchable space when IQR is near-zero
        lo = min(lo, median * 0.5)
        hi = max(hi, median * 2.0)
    else:
        lo, hi = 0.1, 100.0

    # ── 窗口感知收缩（#11 hypo_3）──
    if hyp is not None and _HAS_SCORING_V2 and _parse_window_fn is not None:
        try:
            _win = _parse_window_fn(hyp)
            if _win is not None:
                lo_w, hi_w = _win
                lo = max(0.001, 0.5 * lo_w)
                hi = 1.5 * hi_w
        except Exception:
            pass

    return {
        "property_value": (float(lo), float(hi)),
        "composition_x": (0.0, 1.0),
        "temperature": (300.0, 1500.0),
    }


def evidence_score(params: dict, hyp: DiscoveryHypothesis, evid: dict,
                   llm_plausibility: float = None,
                   scoring_version: str = "v1") -> float:
    """Literature evidence scoring function — synced with discovery.py text_score_fn.

    Supports two scoring versions:
      - "v1" (legacy): original linear-weighted composite score
      - "v2" (enhanced): sigmoid-stretched + dynamic harmonic weights + diversity bonus
        (#11: 打分函数区分度有限)

    Args:
        params: candidate parameter dict
        hyp: target hypothesis
        evid: evidence index dict (from build_evidence_index)
        llm_plausibility: optional LLM scientific plausibility score [0, 1]
        scoring_version: "v1" (legacy) or "v2" (enhanced, default since #11)
    """
    # ── v2 增强打分通道 ──
    if scoring_version == "v2" and _HAS_SCORING_V2 and _v2_score_fn is not None:
        # Reconstruct text from evidence blocks for v2 scoring
        text = "\n\n".join(evid["blocks"])
        v2_score, _meta = _v2_score_fn(
            params=params,
            hyp=hyp,
            literature_values=evid["values"],
            text=text,
            llm_plausibility=llm_plausibility,
            explored_points=None,
        )
        return float(v2_score)

    # ── v1 原始打分通道（向后兼容）──
    blocks: list = evid["blocks"]
    total = len(blocks)
    if total == 0:
        raw = 0.15
        if llm_plausibility is not None and llm_plausibility > 0:
            return raw * 0.65 + llm_plausibility * 0.35
        return raw

    cand_mats = params.get("materials") or params.get("material") or (hyp.materials or [])
    if isinstance(cand_mats, str):
        cand_mats = [cand_mats]
    cand_mats = [str(m).lower() for m in cand_mats]
    mats: list = evid["material_tokens"]
    kws: list = evid["prop_keywords"]
    values: list = evid["values"]

    # Priority: match against hypothesis materials; fallback to generic tokens
    if cand_mats:
        mat_blocks = [b for b in blocks if any(m in b.lower() for m in cand_mats)]
        if not mat_blocks:
            mat_blocks = [b for b in blocks if any(t in b.lower() for t in mats)]
    else:
        mat_blocks = [b for b in blocks if any(t in b.lower() for t in mats)]

    raw = 0.15  # base score
    if mat_blocks:
        raw += 0.20 * len(mat_blocks) / total  # material coverage
        co = sum(1 for b in mat_blocks if any(k in b.lower() for k in kws))
        raw += 0.15 * co / max(len(mat_blocks), 1)  # property co-occurrence
        cv = params.get("property_value") or params.get("value") or 0
        if values and cv:
            sims = sorted(1.0 / (1.0 + abs(cv - v) / max(v, 1e-6)) for v in values)
            best = sum(sims[-3:]) / max(len(sims[-3:]), 1)
            raw += 0.25 * best  # numerical proximity

    # ── composition_x 奖励（倒 U 型）：双金属/掺杂假设的组分比例 ──
    is_bimetallic = False
    if hyp.materials and len(hyp.materials) >= 2:
        is_bimetallic = True
    if not is_bimetallic and hyp.title:
        title_lower = hyp.title
        if any(kw in title_lower for kw in ["双金属", "掺杂", "比例"]):
            is_bimetallic = True
    if is_bimetallic:
        cx = params.get("composition_x", None)
        if cx is not None and 0.3 <= cx <= 0.7:
            comp_bonus = 0.05 + 0.05 * max(0.0, 1.0 - ((cx - 0.5) / 0.2) ** 2)
            raw += comp_bonus

    # ── temperature 奖励：常见实验温度范围 ──
    temp = params.get("temperature", None)
    if temp is not None:
        if 273 <= temp <= 373:
            raw += 0.05
        elif 373 < temp <= 500:
            raw += 0.02

    raw = min(raw, 1.0)

    # ── v1 窗口算术混合（与 v2 对齐：#11 hypo_3 窗口型假设）──
    # 窗口型假设（如 hypo_3 Qst∈[25,40]）下，窗口得分以 30% 权重混入：
    #   raw = 0.70*raw + 0.30*window_val
    # 使 bayesian 能学到「靠近窗口分数更高」的连续梯度（v2 同理）。
    if _HAS_SCORING_V2 and _parse_window_fn is not None and _window_score_fn is not None:
        try:
            _win = _parse_window_fn(hyp)
            if _win is not None:
                _wv, _ = _window_score_fn(params, hyp)
                raw = 0.70 * raw + 0.30 * _wv
        except Exception:
            pass

    # ── LLM plausibility blend (0.35 weight) ──
    # When available, LLM scientific judgment differentiates Bayesian from random:
    # - High LLM plausibility + strong evidence → boosted
    # - Low LLM plausibility + strong evidence → penalized (data-match but science questionable)
    if llm_plausibility is not None and llm_plausibility > 0:
        return raw * 0.65 + llm_plausibility * 0.35

    return raw


def safe_hypothesis(data: dict) -> DiscoveryHypothesis:
    """Construct a DiscoveryHypothesis from a dict, dropping unknown keys."""
    valid_fields = DiscoveryHypothesis.__dataclass_fields__
    return DiscoveryHypothesis(**{k: v for k, v in data.items() if k in valid_fields})


# ═══════════════════════════════════════════════════════════════
# Search strategies
# ═══════════════════════════════════════════════════════════════

def run_bayesian_search(
    hyp: DiscoveryHypothesis,
    evid: dict,
    total_budget: int,
    seed: int,
    n_initial: int = 10,
    scoring_version: str = "v1",
) -> Tuple[float, List[float]]:
    """Run one Bayesian-optimisation run and return (best_score, all_log_scores).

    Uses `n_initial` random samples + `total_budget - n_initial` UCB rounds.
    LLM plausibility is blended into the objective function (weight 0.35),
    reflecting the Agent's actual LLM-guided search behavior.

    Args:
        scoring_version: "v1" (legacy) or "v2" (enhanced, #11)
    """
    np.random.seed(seed)

    param_space = search_space_from_evidence(evid, hyp)
    n_iterations = total_budget - n_initial
    if n_iterations < 0:
        n_iterations = 0
        n_initial = total_budget

    # Use LLM plausibility if available (matches Agent's actual scoring logic)
    llm_plaus = hyp.llm_plausibility_score if hyp.llm_plausibility_score > 0 else None

    optimizer = BayesianOptimizer()

    _, best_score, log = optimizer.optimize(
        hyp,
        param_space,
        objective_fn=lambda p: evidence_score(
            p, hyp, evid, llm_plausibility=llm_plaus,
            scoring_version=scoring_version,
        ),
        n_iterations=n_iterations,
        n_initial=n_initial,
    )

    # Collect all per-candidate scores from the log
    all_scores: List[float] = []
    for entry in log:
        if "score" in entry:
            all_scores.append(float(entry["score"]))
        if "best_score" in entry:
            all_scores.append(float(entry["best_score"]))

    return float(best_score), all_scores


def run_random_search(
    hyp: DiscoveryHypothesis,
    evid: dict,
    total_budget: int,
    seed: int,
    scoring_version: str = "v1",
) -> Tuple[float, List[float]]:
    """Run one pure-random uniform sampling run and return (best_score, all_scores).

    Samples `total_budget` points uniformly from the same search space used by
    the Bayesian strategy. Random search does NOT use LLM guidance — this is
    the key differentiator: Bayesian exploits LLM-guided regions while random
    just samples uniformly over the raw evidence landscape.

    Args:
        scoring_version: "v1" (legacy) or "v2" (enhanced, #11)
    """
    np.random.seed(seed)

    param_space = search_space_from_evidence(evid, hyp)
    param_names = list(param_space.keys())
    bounds = np.array([[lo, hi] for lo, hi in param_space.values()])

    X = np.random.uniform(bounds[:, 0], bounds[:, 1], size=(total_budget, len(param_names)))

    # 与 bayesian 通道使用同一 llm_plausibility（公平对比：同一打分函数下
    # 比较两种搜索策略）。修复 #11 不公平对比：此前 random 不混合 LLM，
    # 而 bayesian 混合——当假设 llm_plausibility_score 偏低（如 hypo_2=0.5）时
    # bayesian 被 0.65*raw+0.35*0.5 压到天花板以下，random 却可达 raw 全值，
    # 导致「搜索算法优劣」被 LLM 分混淆。
    llm_plaus = hyp.llm_plausibility_score if hyp.llm_plausibility_score > 0 else None

    best_score = -1.0
    all_scores: List[float] = []
    for row in X:
        params = {n: float(v) for n, v in zip(param_names, row)}
        # Random search: same objective as Bayesian (fair comparison)
        score = evidence_score(
            params, hyp, evid,
            llm_plausibility=llm_plaus,
            scoring_version=scoring_version,
        )
        all_scores.append(score)
        if score > best_score:
            best_score = score

    return float(best_score), all_scores


# ═══════════════════════════════════════════════════════════════
# Analysis helpers
# ═══════════════════════════════════════════════════════════════

def compute_verdict(
    bayesian_median: float,
    random_median: float,
    diff: float,
    bayesian_scores: List[float],
    random_scores: List[float],
) -> str:
    """Determine verdict comparing Bayesian vs Random.

    Rules:
      |diff| <= 0.003  ->  parity (no meaningful difference)
      diff > 0.008 AND bayesian higher  ->  bayesian_wins
      diff < -0.008 AND random higher   ->  random_wins
      otherwise                         ->  marginal (slight difference, inconclusive)

    Thresholds lowered from 0.01 because LLM plausibility blending
    (weight 0.35) creates score spread typically in the 0.005-0.05 range.
    """
    if diff > 0.008:
        return "bayesian_wins"
    elif diff < -0.008:
        return "random_wins"
    elif abs(diff) <= 0.003:
        return "parity"
    else:
        return "marginal"


def median_iqr(values: List[float]) -> Tuple[float, float, float]:
    """Return (median, q1, q3) for a list of floats."""
    arr = np.array(sorted(values))
    median = float(np.median(arr))
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    return median, q1, q3


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baseline Random Search -- fair-comparison reference for Bayesian discovery",
    )
    parser.add_argument(
        "--iterations", type=int, default=40,
        help="Total evaluation budget per seed (default: 40 = 10 initial + 30 UCB rounds)",
    )
    parser.add_argument(
        "--seeds", type=int, default=10,
        help="Number of random seeds to average over (default: 10)",
    )
    parser.add_argument(
        "--hypothesis", type=str, default="all",
        help="Hypothesis index to test (0-based), or 'all' (default: all)",
    )
    parser.add_argument(
        "--survey-dir", type=str, default=None,
        help="主题运行目录名（与 main.py --run-dir 一致），自动定位该主题的 "
             "knowledge_graph.md / hypotheses.json / baseline_random.json",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help=f"Output JSON path (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--hypotheses-path", type=str, default=None,
        help=f"Path to hypotheses.json (default: {_DEFAULT_HYPOTHESES})",
    )
    parser.add_argument(
        "--knowledge-source", type=str, default=None,
        help="Override knowledge-source path (default: auto-detect knowledge_graph.md / paper_summaries.md)",
    )
    parser.add_argument(
        "--n-initial", type=int, default=10,
        help="Initial random samples for Bayesian optimizer (default: 10)",
    )
    parser.add_argument(
        "--scoring", type=str, default="v1", choices=["v1", "v2"],
        help="Scoring function version (default: v1). "
             "v2 = enhanced score with sigmoid stretching + dynamic weights + diversity bonus "
             "+ window-aware scoring for window-type hypotheses (e.g. hypo_3 Qst∈[25,40]) "
             "(#11: 打分函数区分度有限). "
             "Set SCORING_V2=true env var to make v2 the default.",
    )
    args = parser.parse_args()

    # 多主题支持：--survey-dir 与 main.py --run-dir 一致，自动定位该主题产物
    if args.survey_dir:
        import utils.config as _cfg
        _cfg.set_run_dir(args.survey_dir)
        globals()["_KNOWLEDGE_SOURCE_CANDIDATES"] = [
            f"{_cfg.SURVEY_DIR}/knowledge_graph.md",
            f"{_cfg.SURVEY_DIR}/paper_summaries.md",
        ]
        globals()["_DEFAULT_OUTPUT"] = f"{_cfg.SURVEY_DIR}/discovery/baseline_random.json"
        globals()["_DEFAULT_HYPOTHESES"] = f"{_cfg.SURVEY_DIR}/discovery/hypotheses.json"
    args.output = args.output or _DEFAULT_OUTPUT
    args.hypotheses_path = args.hypotheses_path or _DEFAULT_HYPOTHESES

    # ── 0. Check prerequisites ──────────────────────────────────
    hypotheses_path = _PROJECT_ROOT / args.hypotheses_path
    if not hypotheses_path.exists():
        print(f"[FAIL] Hypotheses file not found: {hypotheses_path}")
        print("  Expected path: workspace/outputs/literature_survey/discovery/hypotheses.json")
        print("  Run the main Agent first to generate hypotheses, or specify --hypotheses-path.")
        sys.exit(1)

    kw_sources = (
        [args.knowledge_source] if args.knowledge_source else _KNOWLEDGE_SOURCE_CANDIDATES
    )
    source_text = load_knowledge_source(kw_sources)
    if source_text is None:
        searched = args.knowledge_source or ", ".join(_KNOWLEDGE_SOURCE_CANDIDATES)
        print(f"[FAIL] Knowledge source not found. Looked in: {searched}")
        print("  At least one of knowledge_graph.md or paper_summaries.md must exist.")
        print("  Run extract_knowledge then write knowledge_graph.md first.")
        sys.exit(1)

    # Determine which source file we actually loaded
    actual_source = "unknown"
    for cand in kw_sources:
        if (_PROJECT_ROOT / cand).exists():
            actual_source = cand
            break

    # ── 1. Load hypotheses ──────────────────────────────────────
    try:
        hypotheses_data = json.loads(hypotheses_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[FAIL] Failed to parse hypotheses.json: {e}")
        sys.exit(1)

    if not isinstance(hypotheses_data, list) or len(hypotheses_data) == 0:
        print("[FAIL] hypotheses.json is empty or not a list.")
        sys.exit(1)

    # Select hypotheses to test
    if args.hypothesis.lower() == "all":
        indices = list(range(len(hypotheses_data)))
    else:
        try:
            idx = int(args.hypothesis)
        except ValueError:
            print(f"[FAIL] Invalid --hypothesis value: {args.hypothesis}. Use integer index or 'all'.")
            sys.exit(1)
        if idx < 0 or idx >= len(hypotheses_data):
            print(f"[FAIL] Hypothesis index {idx} out of range [0, {len(hypotheses_data) - 1}].")
            sys.exit(1)
        indices = [idx]

    # ── 2. Run comparison ───────────────────────────────────────
    total_budget = args.iterations
    n_seeds = args.seeds
    n_initial = args.n_initial

    print(f"\n{'=' * 72}")
    print(f"  Baseline Random Search -- Fair Comparison")
    print(f"{'=' * 72}")
    print(f"  Knowledge source : {actual_source} ({len(source_text):,} chars)")
    print(f"  Scoring version  : {args.scoring} {'(enhanced: piecewise-linear stretch + dynamic weights + window-aware + diversity bonus)' if args.scoring == 'v2' else '(legacy linear-weighted composite)'}")
    print(f"  Total budget     : {total_budget} evals/seed (Bayesian: {n_initial} init + {total_budget - n_initial} UCB)")
    print(f"  Seeds            : {n_seeds}")
    print(f"  Hypotheses tested: {len(indices)} / {len(hypotheses_data)} total")
    print(f"  Output           : {args.output}")
    print(f"{'=' * 72}\n")

    t_start = time.time()
    results_per_hypothesis: Dict[str, dict] = {}

    for h_idx in indices:
        h_data = hypotheses_data[h_idx]
        try:
            hyp = safe_hypothesis(h_data)
        except Exception as e:
            print(f"  [SKIP] Skipping hypothesis {h_idx}: failed to construct -- {e}")
            continue

        hyp_label = hyp.id if hyp.id else f"hypo_{h_idx}"

        print(f"[hypo {h_idx}] {hyp.title[:70]}...")
        # 窗口型假设诊断（GOAI #11 残余）：hypo_3 等窗口型假设在 v2 打分中
        # 依赖 window 维度提供连续梯度，这里打印解析状态便于定位问题。
        if _HAS_SCORING_V2 and _parse_window_fn is not None:
            _win = _parse_window_fn(hyp)
            if _win is not None:
                print(f"  [window] 检测到窗口型假设: property_value ∈ [{_win[0]}, {_win[1]}] → v2 打分启用 window 维度")
            else:
                print(f"  [window] 未解析到窗口 → window 维度中性（保持现有三维打分）")
        print(f"  Building evidence index ... ", end="", flush=True)
        t0 = time.time()
        evid = build_evidence_index(source_text, hyp)
        print(f"done ({time.time() - t0:.1f}s) -- "
              f"{len(evid['blocks'])} blocks, "
              f"{len(evid['material_tokens'])} materials, "
              f"{len(evid['values'])} literature values")

        bayesian_bests: List[float] = []
        random_bests: List[float] = []
        bayesian_all: List[float] = []
        random_all: List[float] = []

        for seed in range(n_seeds):
            # Bayesian search
            b_best, b_all = run_bayesian_search(
                hyp, evid, total_budget, seed=seed, n_initial=n_initial,
                scoring_version=args.scoring,
            )
            bayesian_bests.append(b_best)
            bayesian_all.extend(b_all)

            # Random search (offset seed to avoid correlated random streams)
            r_best, r_all = run_random_search(
                hyp, evid, total_budget, seed=seed + 10000,
                scoring_version=args.scoring,
            )
            random_bests.append(r_best)
            random_all.extend(r_all)

            print(f"  seed={seed:2d} | bayesian_best={b_best:.4f}  random_best={r_best:.4f}")

        # ── Compute statistics ──
        b_med, b_q1, b_q3 = median_iqr(bayesian_bests)
        r_med, r_q1, r_q3 = median_iqr(random_bests)
        diff = b_med - r_med

        verdict = compute_verdict(b_med, r_med, diff, bayesian_bests, random_bests)

        results_per_hypothesis[hyp_label] = {
            "bayesian_median": round(b_med, 6),
            "random_median": round(r_med, 6),
            "diff_median": round(diff, 6),
            "bayesian_iqr": [round(b_q1, 6), round(b_q3, 6)],
            "random_iqr": [round(r_q1, 6), round(r_q3, 6)],
            "verdict": verdict,
            "bayesian_all_scores": [round(s, 6) for s in bayesian_bests],
            "random_all_scores": [round(s, 6) for s in random_bests],
        }

        verdict_label = {
            "bayesian_wins": "BAYESIAN_WINS",
            "random_wins": "RANDOM_WINS",
            "parity": "PARITY",
        }.get(verdict, verdict)

        print(f"  --> bayesian_median={b_med:.4f}  random_median={r_med:.4f}  "
              f"diff={diff:+.4f}  [{verdict_label}]\n")

    # ── 3. Summary ──────────────────────────────────────────────
    n_total = len(results_per_hypothesis)
    n_bayesian_wins = sum(1 for v in results_per_hypothesis.values() if v["verdict"] == "bayesian_wins")
    n_random_wins = sum(1 for v in results_per_hypothesis.values() if v["verdict"] == "random_wins")
    n_parity = sum(1 for v in results_per_hypothesis.values() if v["verdict"] == "parity")

    output = {
        "baseline_type": "random_uniform_sampling",
        "scoring_version": args.scoring,
        "total_budget": total_budget,
        "n_seeds": n_seeds,
        "knowledge_source": actual_source,
        "results_per_hypothesis": results_per_hypothesis,
        "summary": {
            "total_hypotheses": n_total,
            "bayesian_wins": n_bayesian_wins,
            "parity": n_parity,
            "random_wins": n_random_wins,
        },
    }

    # ── 4. Save ─────────────────────────────────────────────────
    output_path = _PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - t_start

    # ── 5. Print final table ────────────────────────────────────
    print(f"{'=' * 72}")
    print(f"  Summary")
    print(f"{'=' * 72}")
    print(f"  {'Hypothesis':<16} {'Bayesian':>10} {'Random':>10} {'Diff':>10}  Verdict")
    print(f"  {'-' * 64}")
    for key, r in results_per_hypothesis.items():
        label = key[:16]
        print(f"  {label:<16} {r['bayesian_median']:10.4f} {r['random_median']:10.4f} "
              f"{r['diff_median']:+10.4f}  {r['verdict']}")

    print(f"  {'-' * 64}")
    print(f"  Total: {n_total} hypotheses  |  "
          f"Bayesian wins: {n_bayesian_wins}  |  "
          f"Parity: {n_parity}  |  "
          f"Random wins: {n_random_wins}")
    print(f"\n  Elapsed: {elapsed:.1f}s")
    print(f"  Output:  {output_path}")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    main()
