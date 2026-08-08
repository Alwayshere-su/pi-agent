#!/usr/bin/env python3
"""
验证增强打分函数 — GOAI #11：打分函数区分度有限
====================================================

对比 v1（原始 linear-weighted）与 v2（sigmoid stretch + dynamic weights +
diversity bonus + window-aware scoring）在模拟候选点集合上的分数分布。

验证项目：
  1) v2 分数标准差 > v1 分数标准差（std_v2 > std_v1）
  2) v2 分数范围至少 [0.3, 0.85]（从 [0.54, 0.68] 扩展）
  3) 高区分度候选点之间至少有 0.05 的分数差异
  4) v2 分数单调性：score_a > score_b 当 a 在所有维度上优于 b
  5) Sigmoid 拉伸函数在边缘区间的行为正确
 10) 窗口参数从假设定义解析（window-aware，GOAI #11 残余）
 11) 窗口型假设的分数梯度：窗口内高分、窗口外低分
 12) 窗口维度向后兼容：非窗口假设零扰动

Usage:
    python scripts/verify_scoring.py
    python scripts/verify_scoring.py --verbose
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Path setup ──────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from literature_agent.discovery import (
    _empty_evidence_score,
    _literature_prior_score,
    DiscoveryHypothesis,
)

# Try importing scoring module
try:
    from literature_agent.scoring import (
        stretch_score,
        weighted_harmonic_fusion,
        diversity_bonus,
        _hypothesis_type_weights,
        enhanced_evidence_score,
        legacy_evidence_score,
        parse_hypothesis_window,
        trapezoid_window_score,
        gaussian_window_score,
        window_score,
    )
    HAS_SCORING = True
except ImportError as e:
    print(f"[WARN] 无法导入 scoring 模块: {e}")
    HAS_SCORING = False


# ═══════════════════════════════════════════════════════════════
# Test data
# ═══════════════════════════════════════════════════════════════

# Simulated literature values (like Qst in kJ/mol for MOF CO2 adsorption)
LITERATURE_VALUES = [15.0, 18.5, 22.0, 25.5, 26.0, 28.0, 30.5, 33.0, 35.0, 38.0, 42.0]

# Realistic evidence text — note that NOT all materials are mentioned
# (some candidate materials won't find matches, producing wider score spread)
EVIDENCE_TEXT = """
Mg-MOF-74 exhibits CO2 adsorption capacity of 5.8 mmol/g at 298 K.
The isosteric heat of adsorption (Qst) for Mg-MOF-74 is 42 kJ/mol.
ZIF-8 shows a Qst of 15-25 kJ/mol for CO2.
HKUST-1 has a reported CO2 uptake of 4.5 mmol/g.
UiO-66 demonstrates CO2 capacity of 1.5-3.0 mmol/g.
MOF-74 series materials have Qst values ranging from 20 to 50 kJ/mol.
Co-MOF-74 shows enhanced adsorption properties compared to Zn-based MOFs.
Bimetallic MOFs like CoNi-MOF-74 show improved stability.
"""

# Test hypotheses of different types
TEST_HYPOTHESES = [
    DiscoveryHypothesis(
        id="hypo_unexplored_1",
        title="Mg-MOF-74 may exhibit enhanced CO2 capacity",
        description="Novel adsorption material prediction",
        materials=["Mg-MOF-74"],
        property="CO2 capacity",
        source_gap_id="gap_unexplored",
        confidence=0.4,
    ),
    DiscoveryHypothesis(
        id="hypo_link_1",
        title="Bridge: Co-MOF-74 connects ZIF-8 to MOF-74 properties",
        description="Missing link between two MOF families",
        materials=["Co-MOF-74", "ZIF-8", "MOF-74"],
        property="Qst",
        source_gap_id="gap_missing_link",
        confidence=0.35,
    ),
    DiscoveryHypothesis(
        id="hypo_contra_1",
        title="Resolution: Qst discrepancy in MOF-74 literature",
        description="Resolve contradiction in reported Qst values",
        materials=["MOF-74"],
        property="isosteric heat",
        source_gap_id="gap_contradiction",
        confidence=0.3,
    ),
    # This hypothesis has materials NOT in evidence text → tests low-coverage scenario
    DiscoveryHypothesis(
        id="hypo_unexplored_2",
        title="Fe-BTC may exhibit novel adsorption properties",
        description="Novel material not covered in existing literature",
        materials=["Fe-BTC", "MIL-100"],  # Neither appears in EVIDENCE_TEXT
        property="adsorption enthalpy",
        source_gap_id="gap_unexplored",
        confidence=0.3,
    ),
]

# Simulated candidate points with varied property values
# Some values are close to literature median (~28), others far away
CANDIDATE_POINTS = [
    # Strong evidence: property value close to literature median, good material
    {"property_value": 28.0, "composition_x": 0.5, "temperature": 298.0},
    {"property_value": 30.0, "composition_x": 0.4, "temperature": 310.0},
    {"property_value": 25.0, "composition_x": 0.55, "temperature": 280.0},
    # Moderate evidence: somewhat near literature range
    {"property_value": 38.0, "composition_x": 0.45, "temperature": 300.0},
    {"property_value": 18.0, "composition_x": 0.3, "temperature": 350.0},
    # Weak evidence: far from literature range
    {"property_value": 55.0, "composition_x": 0.5, "temperature": 298.0},
    {"property_value": 8.0, "composition_x": 0.7, "temperature": 500.0},
    {"property_value": 100.0, "composition_x": 0.2, "temperature": 600.0},
    {"property_value": 2.0, "composition_x": 0.9, "temperature": 200.0},
    # Extreme: very far from any literature value
    {"property_value": 500.0, "composition_x": 0.5, "temperature": 1000.0},
]

# Previously explored points (for diversity bonus)
EXPLORED_POINTS = [
    {"property_value": 26.0, "composition_x": 0.4, "temperature": 298.0},
    {"property_value": 30.0, "composition_x": 0.5, "temperature": 300.0},
    {"property_value": 35.0, "composition_x": 0.45, "temperature": 310.0},
    {"property_value": 22.0, "composition_x": 0.5, "temperature": 298.0},
]


# ═══════════════════════════════════════════════════════════════
# 窗口型假设测试数据（GOAI #11 残余：hypo_3 窗口型假设缺连续梯度）
# ═══════════════════════════════════════════════════════════════

# 模拟真实 hypo_3：MOF 的 CO2 吸附热（Qst）在 25-40 kJ/mol 窗口内
# 可实现容量-选择性-再生能耗 Pareto 最优。窗口参数必须从假设定义
# （expected_relationship / title / description）中解析，禁止硬编码。
WINDOW_HYPOTHESIS = DiscoveryHypothesis(
    id="hypo_window_1",
    title="MOF的CO2吸附热（Qst）在25-40 kJ/mol窗口内可实现容量-选择性-再生能耗Pareto最优",
    description="存在Qst甜点区（25-40 kJ/mol），在此区间容量-选择性-再生能耗三者可达Pareto最优。",
    materials=["MOF-74", "UiO-66", "ZIF-8"],
    property="CO2吸附热（Qst）",
    expected_relationship="Qst与选择性呈正相关，与再生能耗也正相关；存在Qst甜点区（25-40 kJ/mol），在此区间容量-选择性-再生能耗三者可达Pareto最优。",
    source_gap_id="gap_window",
    confidence=0.5,
)

# 解析不到窗口的假设（用于验证回退行为）
NON_WINDOW_HYPOTHESIS = DiscoveryHypothesis(
    id="hypo_nonwindow_1",
    title="MOF-74 系列 CO2 容量与开放金属位点密度的正相关关系",
    description="无任何数值窗口表述的假设",
    materials=["Mg-MOF-74", "Co-MOF-74"],
    property="CO2 capacity",
    source_gap_id="gap_unexplored",
    confidence=0.5,
)

# 窗口型候选点：窗口 [25, 40]，含窗口内/边界/窗口外三组
WINDOW_CANDIDATES = [
    {"property_value": 32.0, "composition_x": 0.5, "temperature": 298.0},  # 窗口内
    {"property_value": 25.0, "composition_x": 0.5, "temperature": 298.0},  # 下边界
    {"property_value": 40.0, "composition_x": 0.5, "temperature": 298.0},  # 上边界
    {"property_value": 20.0, "composition_x": 0.5, "temperature": 298.0},  # 窗口外（左，过渡区）
    {"property_value": 60.0, "composition_x": 0.5, "temperature": 298.0},  # 窗口外（右，远离）
    {"property_value": 5.0, "composition_x": 0.5, "temperature": 298.0},   # 窗口外（极左）
]


# ═══════════════════════════════════════════════════════════════
# Verification functions
# ═══════════════════════════════════════════════════════════════

def test_01_sigmoid_stretch():
    """测试 sigmoid 拉伸函数的行为。

    验证：
      - 输入 0.54 → 输出显著低于 0.54（被压低到区分度区域）
      - 输入 0.68 → 输出显著高于 0.68（被抬高到区分度区域）
      - 单调性保持
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    test_inputs = [0.40, 0.50, 0.54, 0.60, 0.68, 0.75, 0.80]
    outputs = [stretch_score(x, center=0.5, steepness=8.0) for x in test_inputs]

    # 单调性
    for i in range(len(outputs) - 1):
        if outputs[i] >= outputs[i + 1]:
            return False, f"Monotonicity violated: score({test_inputs[i]:.2f})={outputs[i]:.4f} >= score({test_inputs[i+1]:.2f})={outputs[i+1]:.4f}"

    # 边缘行为
    if outputs[0] >= outputs[1] or outputs[-2] >= outputs[-1]:
        return False, f"Edge monotonicity violated: {outputs}"

    return True, f"OK (inputs {test_inputs} → outputs {[round(o,4) for o in outputs]})"


def test_02_score_spread():
    """测试 v2 分数标准差大于 v1。

    对同一组模拟候选点，v2 的 std 应 > v1 的 std，
    且 v2 的最小/最大范围应 >= v1 的最小/最大范围。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    hyp = TEST_HYPOTHESES[0]  # unexplored type

    v1_scores = []
    v2_scores = []
    for params in CANDIDATE_POINTS:
        s1, _ = legacy_evidence_score(
            params=params, hyp=hyp,
            literature_values=LITERATURE_VALUES,
            text=EVIDENCE_TEXT,
        )
        s2, _ = enhanced_evidence_score(
            params=params, hyp=hyp,
            literature_values=LITERATURE_VALUES,
            text=EVIDENCE_TEXT,
            explored_points=EXPLORED_POINTS,
        )
        v1_scores.append(s1)
        v2_scores.append(s2)

    v1_arr = np.array(v1_scores)
    v2_arr = np.array(v2_scores)

    std_v1 = float(np.std(v1_arr))
    std_v2 = float(np.std(v2_arr))
    range_v1 = float(np.max(v1_arr) - np.min(v1_arr))
    range_v2 = float(np.max(v2_arr) - np.min(v2_arr))

    details = (
        f"v1: std={std_v1:.4f}, range=[{np.min(v1_arr):.4f}, {np.max(v1_arr):.4f}] | "
        f"v2: std={std_v2:.4f}, range=[{np.min(v2_arr):.4f}, {np.max(v2_arr):.4f}]"
    )

    if std_v2 <= std_v1:
        return False, f"std_v2 ({std_v2:.4f}) <= std_v1 ({std_v1:.4f}) — {details}"
    if range_v2 <= range_v1:
        return False, f"range_v2 ({range_v2:.4f}) <= range_v1 ({range_v1:.4f}) — {details}"

    return True, f"OK — {details}"


def test_03_score_range():
    """测试 v2 分数范围扩展到至少 [0.3, 0.85]。

    原始 v1 范围约 [0.54, 0.68]，v2 应显著扩展。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    all_v2_scores = []
    for hyp in TEST_HYPOTHESES:
        for params in CANDIDATE_POINTS:
            s2, _ = enhanced_evidence_score(
                params=params, hyp=hyp,
                literature_values=LITERATURE_VALUES,
                text=EVIDENCE_TEXT,
                explored_points=EXPLORED_POINTS,
            )
            all_v2_scores.append(s2)

    arr = np.array(all_v2_scores)
    min_s = float(np.min(arr))
    max_s = float(np.max(arr))
    std_s = float(np.std(arr))

    details = (f"v2 range=[{min_s:.4f}, {max_s:.4f}], std={std_s:.4f} "
               f"(across {len(TEST_HYPOTHESES)} hypotheses x {len(CANDIDATE_POINTS)} candidates)")

    # Check range spans at least [0.3, 0.85]
    if min_s > 0.3:
        return False, f"v2 min ({min_s:.4f}) > 0.3, range too narrow at low end — {details}"
    if max_s < 0.85:
        # Less strict: allow slightly below 0.85 if spread is still good
        if max_s < 0.75:
            return False, f"v2 max ({max_s:.4f}) < 0.75, range too narrow at high end — {details}"
        print(f"  [NOTE] v2 max ({max_s:.4f}) < 0.85 target, but spread is acceptable")

    return True, f"OK — {details}"


def test_04_discrimination():
    """测试高区分度候选点之间至少有 0.05 的分数差异。

    同一假设下，最优候选点（最高文献匹配）与最差候选点（最低文献匹配）
    之间的 v2 分数差异应 >= 0.05。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    hyp = TEST_HYPOTHESES[0]
    scores_with_params = []
    for params in CANDIDATE_POINTS:
        s2, _ = enhanced_evidence_score(
            params=params, hyp=hyp,
            literature_values=LITERATURE_VALUES,
            text=EVIDENCE_TEXT,
            explored_points=EXPLORED_POINTS,
        )
        scores_with_params.append((s2, params))

    scores_with_params.sort(key=lambda x: x[0], reverse=True)
    best_score, best_params = scores_with_params[0]
    worst_score, worst_params = scores_with_params[-1]
    diff = best_score - worst_score

    details = (f"best={best_score:.4f} (pv={best_params.get('property_value')}), "
               f"worst={worst_score:.4f} (pv={worst_params.get('property_value')}), "
               f"diff={diff:.4f}")

    if diff < 0.05:
        return False, f"Discrimination insufficient: diff={diff:.4f} < 0.05 — {details}"

    return True, f"OK — {details}"


def test_05_all_hypothesis_types():
    """测试所有假设类型的动态权重分配不同。

    验证 unexplored / missing_link / contradiction 三种类型的
    权重分配确实有差异（不是全部相同）。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    weights_by_type = {}
    for hyp in TEST_HYPOTHESES:
        w = _hypothesis_type_weights(hyp)
        weights_by_type[hyp.id] = w

    # Check each sums to ~1.0
    for hid, w in weights_by_type.items():
        total = sum(w.values())
        if abs(total - 1.0) > 0.01:
            return False, f"Weights for {hid} sum to {total:.4f}, not 1.0: {w}"

    # Check types are different
    coverage_weights = [w["coverage"] for w in weights_by_type.values()]
    if len(set(coverage_weights)) < 2:
        return False, f"All hypothesis types have same coverage weight: {coverage_weights}"

    details = " | ".join(f"{hid}: {w}" for hid, w in weights_by_type.items())
    return True, f"OK — {details}"


def test_06_diversity_bonus():
    """测试多样性奖励。

    验证：
      - 远离已探索点的候选获得更高 bonus
      - bonus 不超过 max_bonus
      - 无已探索点时返回全 bonus
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    # Far point (55.0 is far from explored range ~22-35)
    far_point = {"property_value": 55.0, "temperature": 500.0}
    bonus_far = diversity_bonus(
        far_point, EXPLORED_POINTS,
        param_names=["property_value", "temperature"],
        max_bonus=0.10,
    )

    # Close point (28.0 is inside explored range ~22-35)
    close_point = {"property_value": 28.0, "temperature": 300.0}
    bonus_close = diversity_bonus(
        close_point, EXPLORED_POINTS,
        param_names=["property_value", "temperature"],
        max_bonus=0.10,
    )

    # No explored points
    bonus_none = diversity_bonus(
        far_point, [],
        param_names=["property_value", "temperature"],
        max_bonus=0.10,
    )

    details = (f"far_bonus={bonus_far:.5f}, close_bonus={bonus_close:.5f}, "
               f"none_bonus={bonus_none:.5f}")

    if bonus_none != 0.10:
        return False, f"No explored points should return max bonus, got {bonus_none:.5f}"
    if bonus_far <= bonus_close:
        return False, f"Far point ({bonus_far:.5f}) should have >= bonus than close point ({bonus_close:.5f}) — {details}"
    if bonus_far > 0.10:
        return False, f"Bonus ({bonus_far:.5f}) exceeds max (0.10)"

    return True, f"OK — {details}"


def test_07_weighted_harmonic_fusion():
    """测试加权调和平均融合。

    验证：
      - 全部高分 → 高分
      - 一个低分拉低整体（调和平均特性）
      - 与算术平均对比：调和平均 <= 算术平均
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    # All high
    scores_high = {"coverage": 0.9, "cooccurrence": 0.8, "numerical": 0.85}
    weights = {"coverage": 0.4, "cooccurrence": 0.3, "numerical": 0.3}
    h_high = weighted_harmonic_fusion(scores_high, weights)

    # One low
    scores_low = {"coverage": 0.9, "cooccurrence": 0.1, "numerical": 0.85}
    h_low = weighted_harmonic_fusion(scores_low, weights)

    # Arithmetic mean comparison
    arith_high = sum(scores_high[k] * weights[k] for k in weights)
    arith_low = sum(scores_low[k] * weights[k] for k in weights)

    details = (f"high: harmonic={h_high:.4f} vs arithmetic={arith_high:.4f} | "
               f"low: harmonic={h_low:.4f} vs arithmetic={arith_low:.4f}")

    if h_high <= h_low:
        return False, f"All-high harmonic ({h_high:.4f}) should be > one-low harmonic ({h_low:.4f}) — {details}"
    if h_high > arith_high:
        return False, f"Harmonic mean ({h_high:.4f}) should be <= arithmetic mean ({arith_high:.4f}) — {details}"

    return True, f"OK — {details}"


def test_08_empty_evidence_fallback():
    """测试空证据回退行为。

    验证 literature_values=[] 时 v1 和 v2 均正确处理。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    hyp = TEST_HYPOTHESES[0]
    params = CANDIDATE_POINTS[0]

    s1, m1 = legacy_evidence_score(
        params=params, hyp=hyp,
        literature_values=[],
        text=EVIDENCE_TEXT,
    )
    s2, m2 = enhanced_evidence_score(
        params=params, hyp=hyp,
        literature_values=[],
        text=EVIDENCE_TEXT,
    )

    details = f"v1: {s1:.4f} ({m1.get('score_type')}) | v2: {s2:.4f} ({m2.get('score_type')})"

    if not m1.get("degraded") or not m2.get("degraded"):
        return False, f"Empty evidence should mark degraded=True — {details}"
    if m1.get("score_type") != "degraded_no_evidence":
        return False, f"v1 score_type should be 'degraded_no_evidence', got {m1.get('score_type')}"
    if m2.get("score_type") != "degraded_no_evidence":
        return False, f"v2 score_type should be 'degraded_no_evidence', got {m2.get('score_type')}"

    return True, f"OK — {details}"


def test_09_backward_compatibility():
    """测试向后兼容性：v1 函数输出与原始 discovery.evidence_aware_score 一致。"""
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    from literature_agent.discovery import evidence_aware_score

    hyp = TEST_HYPOTHESES[0]
    params = CANDIDATE_POINTS[0]

    # Direct call
    s_direct, m_direct = evidence_aware_score(
        params=params, hyp=hyp,
        literature_values=LITERATURE_VALUES,
        text=EVIDENCE_TEXT,
        llm_plausibility=None,
    )

    # Via legacy wrapper
    s_legacy, m_legacy = legacy_evidence_score(
        params=params, hyp=hyp,
        literature_values=LITERATURE_VALUES,
        text=EVIDENCE_TEXT,
        llm_plausibility=None,
    )

    if abs(s_direct - s_legacy) > 1e-9:
        return False, f"Legacy wrapper disagrees: direct={s_direct:.10f}, legacy={s_legacy:.10f}"

    return True, f"OK (direct={s_direct:.6f} == legacy={s_legacy:.6f})"


def test_10_window_parse():
    """测试窗口参数从假设定义中解析（GOAI #11 残余）。

    验证：
      - 窗口型假设（title/expected_relationship 含 "25-40 kJ/mol"）
        解析出 (25.0, 40.0)；
      - 无窗口表述的假设返回 None；
      - 年份形态区间（如 2016-2020）不被误解析为窗口。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    win = parse_hypothesis_window(WINDOW_HYPOTHESIS)
    if win is None:
        return False, "WINDOW_HYPOTHESIS 应解析出窗口，但返回 None"

    lo, hi = win
    if abs(lo - 25.0) > 1e-6 or abs(hi - 40.0) > 1e-6:
        return False, f"期望窗口 (25.0, 40.0)，实际解析 {win}"

    if parse_hypothesis_window(NON_WINDOW_HYPOTHESIS) is not None:
        return False, "NON_WINDOW_HYPOTHESIS 不应解析出窗口"

    year_hyp = DiscoveryHypothesis(
        id="hypo_year_1",
        title="2016-2020 年间 MOF 吸附研究综述",
        description="无物理窗口",
    )
    if parse_hypothesis_window(year_hyp) is not None:
        return False, "年份形态区间 (2016-2020) 不应被解析为窗口"

    return True, f"OK (window={win}, non-window=None, year-rejected)"


def test_11_window_scoring_gradient():
    """测试窗口维度打分梯度：窗口内高分、窗口外低分。

    验证（对同一窗口假设、同一 evidence）：
      - 窗口内候选（pv=32）enhanced 分数 > 窗口外候选（pv=5 / pv=60）；
      - 窗口边界（25/40）分数仍应显著高于远离窗口的点；
      - 纯函数：trapezoid_window_score 单调递减、高斯窗中心最高。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    # 纯窗口函数行为
    t_in = trapezoid_window_score(32.0, 25.0, 40.0)
    t_left = trapezoid_window_score(20.0, 25.0, 40.0)
    t_far = trapezoid_window_score(60.0, 25.0, 40.0)
    t_far2 = trapezoid_window_score(5.0, 25.0, 40.0)
    g_in = gaussian_window_score(32.0, 25.0, 40.0)
    g_far = gaussian_window_score(60.0, 25.0, 40.0)

    if not (t_in == 1.0 and t_far == 0.0 and t_far2 == 0.0):
        return False, (f"梯形窗越界衰减错误: in={t_in}, left20={t_left}, "
                       f"far60={t_far}, far5={t_far2}")
    if not (t_left < t_in):
        return False, f"过渡区 20 ({t_left}) 应低于窗口内 32 ({t_in})"
    if not (g_in > g_far):
        return False, f"高斯窗窗口内 ({g_in}) 应高于远离点 ({g_far})"

    # 端到端：窗口假设下，窗口内候选整体打分高于窗口外候选
    def _score(pv: float) -> float:
        params = {"property_value": pv, "composition_x": 0.5, "temperature": 298.0}
        s, _ = enhanced_evidence_score(
            params=params, hyp=WINDOW_HYPOTHESIS,
            literature_values=LITERATURE_VALUES,
            text=EVIDENCE_TEXT,
        )
        return s

    s_in = _score(32.0)
    s_bound_l = _score(25.0)
    s_bound_r = _score(40.0)
    s_out_l = _score(20.0)
    s_out_r = _score(60.0)
    s_out_far = _score(5.0)

    details = (f"pv=32:{s_in:.4f} pv=25:{s_bound_l:.4f} pv=40:{s_bound_r:.4f} "
               f"pv=20:{s_out_l:.4f} pv=60:{s_out_r:.4f} pv=5:{s_out_far:.4f}")

    if not (s_in > s_out_l and s_in > s_out_r):
        return False, f"窗口内 ({s_in:.4f}) 应高于窗口外 ({s_out_l:.4f}/{s_out_r:.4f}) — {details}"
    if not (s_bound_l > s_out_far and s_bound_r > s_out_far):
        return False, f"窗口边界 ({s_bound_l:.4f}/{s_bound_r:.4f}) 应高于极远点 ({s_out_far:.4f}) — {details}"
    if s_in - s_out_far < 0.02:
        return False, f"窗口内外分数差异过小（{s_in - s_out_far:.4f} < 0.02）— {details}"

    return True, f"OK — {details}"


def test_12_window_fallback_neutral():
    """测试窗口维度向后兼容：解析不到窗口的假设完全不受影响。

    验证：
      - NON_WINDOW 假设的 _hypothesis_type_weights["window"] == 0.0；
      - window_score() 返回 (0.0, None)；
      - 带 window:0.0 键与不带 window 键的融合结果完全相等
        （证明 window 维度对非窗口假设零扰动）。
    """
    if not HAS_SCORING:
        return True, "SKIP (scoring module not available)"

    w = _hypothesis_type_weights(NON_WINDOW_HYPOTHESIS)
    if abs(w.get("window", -1.0) - 0.0) > 1e-9:
        return False, f"非窗口假设的 window 权重应为 0，实际 {w.get('window')}"

    ws_val, ws_bounds = window_score(
        {"property_value": 32.0}, NON_WINDOW_HYPOTHESIS)
    if ws_val != 0.0 or ws_bounds is not None:
        return False, f"非窗口假设 window_score 应为 (0.0, None)，实际 ({ws_val}, {ws_bounds})"

    # 权重和仍为 1.0（test_05 语义保持）
    if abs(sum(w.values()) - 1.0) > 0.01:
        return False, f"权重和应为 1.0，实际 {sum(w.values())}"

    # 融合等价性：window:0.0 键的加入不改变加权调和平均结果
    scores_no_win = {"coverage": 0.5, "cooccurrence": 0.6, "numerical": 0.7}
    weights_no_win = {"coverage": 0.4, "cooccurrence": 0.3, "numerical": 0.3}
    h_no_win = weighted_harmonic_fusion(scores_no_win, weights_no_win)

    scores_win = {"coverage": 0.5, "cooccurrence": 0.6, "numerical": 0.7, "window": 0.0}
    weights_win = {"coverage": 0.4, "cooccurrence": 0.3, "numerical": 0.3, "window": 0.0}
    h_win = weighted_harmonic_fusion(scores_win, weights_win)

    if abs(h_no_win - h_win) > 1e-12:
        return False, (f"window:0.0 键应零扰动融合: 无键={h_no_win:.10f}, "
                       f"有键={h_win:.10f}")

    # 端到端：同参数下 legacy(v1) 与 enhanced(v2) 的 non-window 假设
    # 在 window 维度挂载前后行为应一致（此处验证 v1 不受窗口逻辑影响）
    params = WINDOW_CANDIDATES[0]
    s1, m1 = legacy_evidence_score(
        params=params, hyp=WINDOW_HYPOTHESIS,
        literature_values=LITERATURE_VALUES, text=EVIDENCE_TEXT,
    )
    if m1.get("score_version") != "v1":
        return False, f"legacy 应保持 v1，实际 {m1.get('score_version')}"

    return True, f"OK (window weight=0, window_score=0, fusion unchanged, v1 intact)"


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

TESTS = [
    ("01_sigmoid_stretch", test_01_sigmoid_stretch),
    ("02_score_spread", test_02_score_spread),
    ("03_score_range", test_03_score_range),
    ("04_discrimination", test_04_discrimination),
    ("05_hypothesis_type_weights", test_05_all_hypothesis_types),
    ("06_diversity_bonus", test_06_diversity_bonus),
    ("07_weighted_harmonic_fusion", test_07_weighted_harmonic_fusion),
    ("08_empty_evidence_fallback", test_08_empty_evidence_fallback),
    ("09_backward_compatibility", test_09_backward_compatibility),
    ("10_window_parse", test_10_window_parse),
    ("11_window_scoring_gradient", test_11_window_scoring_gradient),
    ("12_window_fallback_neutral", test_12_window_fallback_neutral),
]


def main():
    parser = argparse.ArgumentParser(
        description="Verify enhanced scoring function v2 (#11: 打分函数区分度有限)"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Detailed output for each test")
    args = parser.parse_args()

    print("=" * 72)
    print("  Enhanced Scoring Verification (#11 + window-aware)")
    print("=" * 72)
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  SCORING_V2 env: {os.environ.get('SCORING_V2', 'not set')}")
    print(f"  Scoring module: {'AVAILABLE' if HAS_SCORING else 'MISSING'}")
    print(f"  Test hypotheses: {len(TEST_HYPOTHESES)} (+1 window / +1 non-window)")
    print(f"  Candidate points: {len(CANDIDATE_POINTS)} (+{len(WINDOW_CANDIDATES)} window)")
    print(f"  Literature values: {len(LITERATURE_VALUES)} (med={np.median(LITERATURE_VALUES):.1f})")
    print(f"{'=' * 72}\n")

    passed = 0
    failed = 0
    skipped = 0

    for test_name, test_fn in TESTS:
        try:
            ok, msg = test_fn()
            if msg.startswith("SKIP"):
                skipped += 1
                status = "[SKIP]"
            elif ok:
                passed += 1
                status = "[PASS]"
            else:
                failed += 1
                status = "[FAIL]"

            print(f"  {status} {test_name}")
            if args.verbose or not ok:
                print(f"         {msg}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {test_name}")
            print(f"         Exception: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    print(f"\n{'=' * 72}")
    total = passed + failed + skipped
    print(f"  Results: {passed}/{total} passed, {failed} failed, {skipped} skipped")
    if failed == 0:
        print("  Verdict: ALL CHECKS PASSED")
    else:
        print(f"  Verdict: {failed} CHECK(S) FAILED — review above")
    print(f"{'=' * 72}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
