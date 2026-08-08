# -*- coding: utf-8 -*-
"""增强打分函数 — GOAI #11：提升贝叶斯 vs 随机对比区分度
================================================================

问题背景：
  当前打分函数的三维证据信号（材料覆盖率、材料x性质共现、数值接近度）通过
  简单线性加权组合，分数集中在 [0.54, 0.68] 窄区间，贝叶斯 vs 随机对比结果
  为 3:2（diff_median ~ -0.050 ~ +0.088），区分度不足。

增强方案（保持向后兼容）：
  a) 非线性打分变换 —— 将窄区间分数通过 sigmoid 拉伸到 [0.2, 0.9]
  b) 加权调和平均 —— 三维信号根据假设类型动态调整权重，替代简单算术平均
  c) 多样性奖励 —— 候选点与已探索点的最小欧氏距离越大，额外加分越多
  d) 窗口型打分维度（window-aware）—— 对「窗口型假设」（如 hypo_3：
     Qst 应落在 [25,40] kJ/mol 窗口内）自动解析窗口参数，property_value
     落在窗口内给高分、越远离窗口惩罚越大（梯形/高斯窗口函数）。
     解析不到窗口的假设回退到现有三维行为（window 维度权重为 0），
     保证 v1/v2 现有打分结果完全不受影响（GOAI #11 残余：hypo_3 贝叶斯
     输给 random 的根因是窗口型假设缺乏连续梯度）。

用法：
  from literature_agent.scoring import enhanced_evidence_score, legacy_evidence_score

  # v2（增强，默认启用）
  score = enhanced_evidence_score(params, hyp, literature_values, text=text)

  # v1（原始，向后兼容）
  score = legacy_evidence_score(params, hyp, literature_values, text=text)

配置开关：
  环境变量 SCORING_V2=true  启用增强打分（默认 true）
  环境变量 SCORING_V2=false 回退到原始打分
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

def _is_scoring_v2() -> bool:
    """检查是否启用增强打分 v2。

    优先级：
      1) 环境变量 SCORING_V2（"true"/"1" → True, "false"/"0" → False）
      2) 默认 True（v2 是新默认）
    """
    val = os.environ.get("SCORING_V2", "true").strip().lower()
    if val in ("false", "0", "no", "off"):
        return False
    return True


# ═══════════════════════════════════════════════════════════════
# 匹配归一化辅助 — 修复知识图谱写法差异导致的信号失效
# ═══════════════════════════════════════════════════════════════

def _norm_key(s: str) -> str:
    """归一化匹配键：小写 + 移除空格/连字符/斜杠/括号/标点差异。

    背景：知识图谱中材料与属性的写法与 hypotheses.json 不一致——
      "NiCu-MOF-74" vs "Ni-Cu-MOF-74"（连字符位置）
      "CO2 吸附容量"   vs "CO2吸附容量"（空格）
      "缺陷 MOF-74"    vs "缺陷MOF-74(Co)"（空格/括号）
      "Fe/Cu-MOF"      vs "FeCu-MOF-74"（斜杠）
    这些差异会导致 v2 的精确子串匹配全部失效，coverage/cooccurrence
    信号恒为 0，从而削弱打分区分度。归一化后按紧凑小写键匹配可恢复信号。

    Args:
        s: 原始字符串（材料名/属性名/文本片段）

    Returns:
        紧凑小写键；非法输入返回 ""（避免空键误匹配）
    """
    if not s:
        return ""
    return re.sub(r"[\s\-_/()（）\[\].,，、:：;；]+", "", s.lower())


def _matches_any(cand_keys: List[str], target: str) -> bool:
    """cand_keys 中任一归一化键是 target（已归一化）的子串。

    Args:
        cand_keys: 候选的归一化键列表（非空）
        target: 已归一化的目标文本

    Returns:
        True 当任一候选键出现在目标文本中
    """
    return any(k and k in target for k in cand_keys)


# 材料名变体：对含括号后缀的材料（如 "缺陷MOF-74(Co)"、"MIL-101(Cr,Mg)"），
# 生成剥离括号内容后的家族键（"缺陷MOF-74"），以匹配知识图谱中不带
# 金属后缀写法（"缺陷 MOF-74"）的文本。
def _material_keys(m: str) -> List[str]:
    """生成材料名的候选归一化键（完整 + 括号剥离变体）。

    Args:
        m: 材料名，如 "缺陷MOF-74(Co)" / "NiCu-MOF-74"

    Returns:
        候选键列表（非空键）
    """
    keys = [_norm_key(m)]
    stripped = re.sub(r"\([^)]*\)", "", m)          # 去掉 (…)
    if stripped != m:
        keys.append(_norm_key(stripped))
    stripped2 = re.sub(r"[（(][^）)]*[）)]", "", m)  # 兼容中文全角/半角括号
    if stripped2 != m:
        keys.append(_norm_key(stripped2))
    return [k for k in keys if k]


# 属性中文关键词 → 英文/同义词关键词映射（与 baseline_random_search 的
# property_keywords 对齐，解决 hypotheses 属性名与知识图谱属性写法不一致：
#   "CO2吸附热（Qst）" vs 知识图谱 "等量吸附热 Qst"
#   "湿态CO2吸附容量"  vs 知识图谱 "水蒸气 → 胺型 MOF 容量"
# )
_PROPERTY_EN_KEYWORDS: Dict[str, List[str]] = {
    "选择性": ["selectivity", "separation factor", "选择性"],
    "容量": ["capacity", "uptake", "loading", "容量"],
    "吸附": ["adsorption", "uptake", "capture", "吸附"],
    "焓": ["isosteric heat", "qst", "enthalpy", "吸附热", "等量吸附热"],
    "热": ["qst", "enthalpy", "heat", "吸附热"],
    "再生": ["regeneration", "working capacity", "energy", "再生"],
    "稳定性": ["stability", "degradation", "cyclability", "稳定"],
    "扩散": ["diffusion", "kinetics", "扩散"],
    "催化": ["catalysis", "tof", "conversion", "activity", "催化"],
    "效率": ["efficiency", "效率"],
    "能耗": ["energy penalty", "regeneration energy", "能耗"],
    "循环": ["cyclability", "cycle", "循环"],
    "湿态": ["humid", "humidity", "water", "rh", "湿度", "湿"],
    "保持率": ["retention", "keep", "retain", "保持率", "衰减"],
    "密度": ["density", "浓度", "密度"],
    "oms": ["oms", "open metal site", "open metal", "金属位点", "配位不饱和"],
    "缺陷": ["defect", "缺陷"],
    "杂质": ["impurity", "no2", "so2", "杂质"],
    "no2": ["no2", "nitrogen dioxide"],
    "so2": ["so2", "sulfur dioxide"],
}


def _property_keys(prop: str) -> List[str]:
    """生成属性的候选匹配键：归一化原文 + 中文关键词映射的英文同义词。

    Args:
        prop: 假设的 property 字段（中文/混合）

    Returns:
        候选键列表（归一化、小写、非空）
    """
    keys: List[str] = []
    pnorm = _norm_key(prop)
    if pnorm:
        keys.append(pnorm)
    text = (prop or "").lower()
    for zh, en_list in _PROPERTY_EN_KEYWORDS.items():
        if zh.lower() in text:
            keys.extend(_norm_key(e) for e in en_list)
    # 过滤空键并去重（保持顺序）
    out: List[str] = []
    seen: set = set()
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


# ═══════════════════════════════════════════════════════════════
# a) 非线性打分变换 — Sigmoid-based score stretching
# ═══════════════════════════════════════════════════════════════

def stretch_score(score: float, center: float = 0.5, steepness: float = 8.0) -> float:
    """分段式分数拉伸，用于提升打分区分度（GOAI #11 修复：sigmoid 高段饱和）。

    原实现为纯 sigmoid：sigmoid 在两端饱和，高分段（>=0.85）差异被压扁——
    输入 0.90 → 0.982、0.95 → 0.989，高分候选几乎无法区分，导致
    hypo_4 等高分假设 bayesian vs random 仅差 0.004（marginal）。

    本实现改为**分段线性拉伸**（锚点插值，全程单调连续）：
      - 低段 (0.0–0.30)：压缩无证据/弱证据分数（0.0→0.02, 0.30→0.22）
      - 中段 (0.30–0.65)：线性拉开（斜率 ≈1.3），窄区间分数得到放大
      - 高段 (0.65–1.00)：保留区分度（斜率 ≈0.7–1.1），
        0.85→0.875、0.95→0.965，高分差异不再被 sigmoid 压扁

    锚点（raw, final）：
      (0.00,0.02) (0.30,0.22) (0.50,0.42) (0.65,0.62) (0.80,0.82) (0.90,0.93) (1.00,1.00)

    Args:
        score: 原始分数，期望在 [0, 1]
        center / steepness: 保留参数以兼容旧调用（分段线性映射不再使用，
            但仍接受并忽略这两个参数，保证向后兼容）

    Returns:
        拉伸后的分数，大致映射到 [0.02, 1.0]，中段与高段均保留区分度
    """
    if score is None or not isinstance(score, (int, float)):
        return 0.02
    s = float(score)
    if s <= 0.0:
        return 0.02
    if s >= 1.0:
        return 1.0
    anchors = (
        (0.00, 0.02),
        (0.30, 0.22),
        (0.50, 0.42),
        (0.65, 0.62),
        (0.80, 0.82),
        (0.90, 0.93),
        (1.00, 1.00),
    )
    for i in range(1, len(anchors)):
        x0, y0 = anchors[i - 1]
        x1, y1 = anchors[i]
        if s <= x1:
            return y0 + (s - x0) * (y1 - y0) / max(x1 - x0, 1e-12)
    return 1.0


# ═══════════════════════════════════════════════════════════════
# b) 加权证据融合 — 动态权重调和平均
# ═══════════════════════════════════════════════════════════════

def _hypothesis_type_weights(hyp: Any) -> Dict[str, float]:
    """根据假设类型返回三维信号的自适应权重。

    不同类型的假设对三维证据信号的依赖程度不同：
      - 新型材料预测（unexplored）：材料覆盖率权重更高（缺乏现有材料数据）
      - 机制桥接（missing_link）：材料x性质共现权重更高（需要证明桥接关系）
      - 矛盾解决（contradiction）：数值接近度权重更高（需要精确数据支持）

    默认权重（简单平均回退）：{"coverage": 1/3, "cooccurrence": 1/3, "numerical": 1/3}

    窗口型假设（window-aware，GOAI #11 残余）：
      若从假设定义解析到窗口（parse_hypothesis_window 成功），则动态挂载
      "window" 维度，权重为 0.30，其余三维按比例缩放（总和保持 1.0）。
      注意：window 权重的实际生效路径是 enhanced_evidence_score 中的
      **乘性门控**（fused * (0.6 + 0.4*window_val)），而非调和平均——
      调和平均会把 window=0 剔除、却让 window∈(0,1) 过渡项显著拉低总分，
      产生「远离窗口反而比靠近边界分高」的非单调响应。此处的 window
      权重保留用于 meta 展示与未来调和平均扩展。
      解析不到窗口的假设，"window" 权重为 0.0——维度不参与融合，
      与未引入窗口维度前的打分结果完全一致（向后兼容保证）。

    Args:
        hyp: DiscoveryHypothesis 或兼容对象（有 id / source_gap_id / title 等属性）

    Returns:
        {"coverage": w1, "cooccurrence": w2, "numerical": w3, "window": w4}，
        四者和为 1.0（window 权重可能为 0）
    """
    # 从假设中推断类型（通过 id 或 title）
    hypo_id = (getattr(hyp, "id", "") or "").lower()
    title = (getattr(hyp, "title", "") or "").lower()
    source_gap = (getattr(hyp, "source_gap_id", "") or "").lower()

    # 启发式类型检测
    if "unexplored" in hypo_id or "unexplored" in source_gap:
        # 未探索：更依赖材料覆盖率（新材料在文献中出现越多，越可信）
        # 原因：未探索空间缺乏已有研究，材料的基础覆盖是主要信号
        w = {"coverage": 0.45, "cooccurrence": 0.30, "numerical": 0.25}
    elif "link" in hypo_id or "missing" in hypo_id or "missing_link" in source_gap:
        # 缺失连接：更依赖材料x性质共现（需要证明中间材料桥接关系）
        # 原因：桥接假说需要材料与性质在文献中共现作为连接证据
        w = {"coverage": 0.25, "cooccurrence": 0.45, "numerical": 0.30}
    elif "contra" in hypo_id or "contradiction" in source_gap:
        # 矛盾解决：更依赖数值接近度（需要精确数据区分不同文献的矛盾）
        # 原因：矛盾场景中，数值精度是区分哪一方结论更可信的关键
        w = {"coverage": 0.20, "cooccurrence": 0.30, "numerical": 0.50}
    else:
        # 默认均衡权重
        w = {"coverage": 1.0 / 3, "cooccurrence": 1.0 / 3, "numerical": 1.0 / 3}

    # ── 窗口型假设：解析到窗口 → 挂载 window 维度（权重 0.30）──
    # 其余三维按 (1 - 0.30) 比例缩放，保证权重总和仍为 1.0。
    if parse_hypothesis_window(hyp) is not None:
        w_window = 0.30
        scale = 1.0 - w_window
        return {
            "coverage": w["coverage"] * scale,
            "cooccurrence": w["cooccurrence"] * scale,
            "numerical": w["numerical"] * scale,
            "window": w_window,
        }

    # ── 非窗口假设：window 权重为 0，维度中性 ──
    return {"coverage": w["coverage"], "cooccurrence": w["cooccurrence"],
            "numerical": w["numerical"], "window": 0.0}


def weighted_harmonic_fusion(scores: Dict[str, float],
                              weights: Dict[str, float]) -> float:
    """加权调和平均融合三维证据信号。

    使用调和平均而非算术平均的原因：
      - 调和平均对低分信号更敏感（一个信号很弱会显著拉低总分）
      - 防止某一维信号"过拟合"掩盖其他维度的不足
      - 更保守的融合策略，要求三个维度都有一定水平的证据

    公式：
      H = 1 / sum(w_i / s_i)  for s_i > 0
      若任一 s_i <= 0，则该项权重转移到其他维度（保守处理）

    若所有权重对应的分数都为 0，回退到加权算术平均。

    Args:
        scores: {"coverage": s1, "cooccurrence": s2, "numerical": s3}
        weights: {"coverage": w1, "cooccurrence": w2, "numerical": w3}

    Returns:
        [0, 1] 融合分数
    """
    if not scores or not weights:
        return 0.0

    # 过滤有效分数（> 0 且对应权重大于 0）
    effective: Dict[str, Tuple[float, float]] = {}
    total_weight = 0.0
    for key, w in weights.items():
        s = scores.get(key, 0.0)
        if w > 0 and s > 1e-9:
            effective[key] = (s, w)
            total_weight += w

    if not effective:
        # 全部无效 → 回退到加权算术平均
        if total_weight > 0:
            return sum(scores.get(k, 0.0) * weights.get(k, 0.0) for k in weights) / total_weight
        return 0.0

    # 加权调和平均：H = 1 / sum(w_i / s_i)
    # 注意：被过滤维度（s_i<=0）的权重必须从分母中剔除并重新归一化，
    # 否则 H 会系统性偏高（>1），经 sigmoid 拉伸后分数聚集在高位，
    # 严重损害区分度（GOAI #11 静态分析发现）。
    denom = sum(w / s for s, w in effective.values())
    if denom <= 1e-9:
        return 0.0
    return float(total_weight / denom)


# ═══════════════════════════════════════════════════════════════
# c) 多样性奖励 — 鼓励探索未覆盖区域
# ═══════════════════════════════════════════════════════════════

def diversity_bonus(params: Dict,
                    explored_points: List[Dict],
                    param_names: Optional[List[str]] = None,
                    max_bonus: float = 0.10) -> float:
    """基于欧氏距离的多样性奖励。

    若候选点与已探索点的最小归一化欧氏距离较大，说明该区域未被充分探索，
    给予额外加分以鼓励 exploration。

    奖励函数：bonus = max_bonus * min(1.0, min_dist / threshold)

    其中 threshold = 0.3（归一化空间中中等距离阈值），
    当 min_dist >= 0.3 时获得全 bonus，线性衰减至 0。

    动机：
      - UCB 仅在工作空间（均值+不确定度）中平衡 exploration/exploitation
      - 但单纯依赖 GP 后验方差可能不足以覆盖参数空间的结构化空洞
      - 多样性奖励直接作用于打分函数，补充 UCB 的探索性不足

    Args:
        params: 候选参数字典
        explored_points: 已探索点列表（同结构字典）
        param_names: 用于距离计算的参数名列表，默认取 params 所有数值键
        max_bonus: 最大额外加分，默认 0.10

    Returns:
        [0, max_bonus] 多样性奖励
    """
    if not explored_points:
        return max_bonus  # 无已探索点 → 全 bonus

    # 确定用于距离计算的参数名
    if param_names is None:
        param_names = [k for k, v in params.items()
                       if isinstance(v, (int, float)) and k != "composition_x"]

    if not param_names:
        return 0.0

    # 提取当前候选点的数值向量
    cand_vec = np.array([float(params.get(k, 0.0)) for k in param_names])

    # 归一化：用已探索点的范围做 min-max 归一化
    all_vals = {k: [] for k in param_names}
    for ep in explored_points:
        for k in param_names:
            v = ep.get(k)
            if isinstance(v, (int, float)):
                all_vals[k].append(float(v))

    mins = np.array([min(all_vals[k]) if all_vals[k] else 0.0 for k in param_names])
    maxs = np.array([max(all_vals[k]) if all_vals[k] else 1.0 for k in param_names])
    ranges = np.maximum(maxs - mins, 1e-12)

    # 归一化候选点
    cand_norm = (cand_vec - mins) / ranges

    # 归一化已探索点
    explored_vecs = []
    for ep in explored_points:
        vec = np.array([float(ep.get(k, 0.0)) for k in param_names])
        explored_vecs.append((vec - mins) / ranges)

    if not explored_vecs:
        return max_bonus

    explored_norm = np.array(explored_vecs)

    # 计算最小欧氏距离
    dists = np.sqrt(np.sum((explored_norm - cand_norm) ** 2, axis=1))
    min_dist = float(np.min(dists))

    # 线性奖励：min_dist 越大 bonus 越高
    threshold = 0.3  # 归一化空间中中等距离阈值
    bonus = max_bonus * min(1.0, min_dist / threshold)

    return bonus


# ═══════════════════════════════════════════════════════════════
# d) 窗口型打分维度 — window-aware scoring
# ═══════════════════════════════════════════════════════════════
# 背景（GOAI #11 残余）：
#   部分假设是「窗口型」——property_value 应落在某个数值窗口内才算符合
#   假设（如 hypo_3：MOF 的 CO2 吸附热 Qst 应落在 25-40 kJ/mol 窗口内才
#   能实现容量-选择性-再生能耗 Pareto 最优）。现有三维信号
#   （coverage / cooccurrence / numerical）都是「与文献离散数值的接近度」
#   型，对窗口型假设没有连续梯度——候选值越接近窗口边界（或窗口内任意
#   位置）在数值接近度维度上没有区分，导致贝叶斯与随机无差别（hypo_3
#   在 v1/v2 下均输给 random）。
#
# 本区块提供：
#   1) parse_hypothesis_window —— 从假设定义（expected_relationship /
#      title / description）中解析窗口参数（如 [25, 40]），禁止硬编码。
#   2) trapezoid_window_score / gaussian_window_score —— 窗口打分函数：
#      落在窗口内给高分（梯形窗内为 1.0），越远离窗口惩罚越大。
#   3) window_score —— 综合入口，解析失败返回 (0.0, None)（维度中性）。
#
# 向后兼容：解析不到窗口的假设，window 维度权重为 0，不参与融合，
#   与未加本维度前的打分结果完全一致。

# 窗口模式匹配：`数字 分隔符 数字 单位`（如 "25-40 kJ/mol"、"25–40 kJ/mol"）
_WINDOW_UNIT_RE = r"(?:kJ/mol|kj/mol|kJ mol|kJ·mol|kJ\.mol|kcal/mol|J/mol|kWh/kg|mmol/g|mmol/cm3|mol/kg|mg/g|wt%|m2/g|bar|kPa|MPa|K|%|eV|h|min)"
_WINDOW_DASH_RE = r"[-–—~～至到]"

_WINDOW_SEP_PATTERN = re.compile(
    rf"(?P<lo>\d+(?:\.\d+)?)\s*{_WINDOW_DASH_RE}\s*(?P<hi>\d+(?:\.\d+)?)\s*"
    rf"(?:{_WINDOW_UNIT_RE})",
    re.IGNORECASE,
)

# 回退模式：无单位但紧跟窗口语义词（"25-40 窗口/区间/甜点区/range"）
_WINDOW_SEMANTIC_PATTERN = re.compile(
    rf"(?P<lo>\d+(?:\.\d+)?)\s*{_WINDOW_DASH_RE}\s*(?P<hi>\d+(?:\.\d+)?)\s*"
    r"(?=窗口|区间|范围|甜点|window|range|sweet)",
    re.IGNORECASE,
)

# 窗口乘性门控下界：窗口型假设在 fused 融合后乘
#   gate = _WINDOW_GATE_MIN + (1 - _WINDOW_GATE_MIN) * window_val
# 窗口内（window_val=1）→ gate=1.0（无惩罚）；极远（window_val=0）
# → gate=0.6（fused 打 6 折）。保证单调：越远离窗口惩罚越大。
_WINDOW_GATE_MIN = 0.6


def _is_plausible_window(lo: float, hi: float) -> bool:
    """窗口合理性校验：排除年份/编号区间与明显非物理区间。

    规则：
      - 0 <= lo < hi；
      - 排除 4 位整数形态（如 2016-2020，文献年份/编号）；
      - 上界不超过 100000（避免把编号段当作物理窗口）。
    """
    if not (0.0 <= lo < hi):
        return False
    if lo >= 1000 and hi <= 9999 and float(lo).is_integer() and float(hi).is_integer():
        return False  # 4 位整数字段（年份/编号）
    if hi > 100000.0:
        return False
    return True


def parse_hypothesis_window(hyp: Any) -> Optional[Tuple[float, float]]:
    """从假设定义中解析窗口区间（如 "25-40 kJ/mol" → (25.0, 40.0)）。

    解析来源（按优先级）：
      1) expected_relationship —— 最定量化的描述；
      2) title —— 简洁明确的窗口表述；
      3) description —— 详述（注意可能含多个区间，取首个合理窗口）。

    匹配规则：
      - 主模式要求区间紧跟单位（kJ/mol 等），最可靠；
      - 回退模式允许无单位但邻近「窗口/区间/甜点区」等语义词；
      - 排除年份/编号形态（2016-2020）与明显非物理区间。

    Args:
        hyp: DiscoveryHypothesis 或兼容对象（有 title / description /
             expected_relationship 属性）

    Returns:
        (lo, hi) 元组；解析不到返回 None
    """
    if hyp is None:
        return None
    texts: List[str] = []
    for attr in ("expected_relationship", "title", "description"):
        t = getattr(hyp, attr, None)
        if isinstance(t, str) and t.strip():
            texts.append(t)
    if not texts:
        return None

    for text in texts:
        for pat in (_WINDOW_SEP_PATTERN, _WINDOW_SEMANTIC_PATTERN):
            for m in pat.finditer(text):
                lo, hi = float(m.group("lo")), float(m.group("hi"))
                if _is_plausible_window(lo, hi):
                    return (lo, hi)
    return None


def trapezoid_window_score(value: Any,
                           lo: float,
                           hi: float,
                           width_frac: float = 0.5) -> float:
    """梯形窗口函数：窗口内平顶 = 1.0，窗口外线性衰减、越远越低。

    Args:
        value: 候选 property_value
        lo / hi: 窗口下/上界
        width_frac: 单侧过渡区宽度 = 窗口宽度的倍数（默认 0.5）

    Returns:
        [0, 1] 窗口得分；value 非法时返回 0.0

    示例（lo=25, hi=40, width_frac=0.5, tw=7.5）：
      value=32      → 1.0   （窗口内）
      value=20      → 1 - 5/7.5 ≈ 0.333
      value=17.5    → 0.0   （超过过渡区）
      value=60      → 0.0   （远离窗口，惩罚最大）
    """
    if value is None or not isinstance(value, (int, float)):
        return 0.0
    v = float(value)
    if lo <= v <= hi:
        return 1.0
    tw = max((hi - lo) * width_frac, 1e-9)
    if v < lo:
        return max(0.0, 1.0 - (lo - v) / tw)
    return max(0.0, 1.0 - (v - hi) / tw)


def gaussian_window_score(value: Any,
                          lo: float,
                          hi: float,
                          sigma_frac: float = 0.5) -> float:
    """高斯窗口函数：窗口中心峰值 = 1.0，两侧按高斯衰减。

    Args:
        value: 候选 property_value
        lo / hi: 窗口下/上界
        sigma_frac: sigma = 窗口宽度 * sigma_frac（默认 0.5）

    Returns:
        (0, 1] 窗口得分；value 非法时返回 0.0
    """
    if value is None or not isinstance(value, (int, float)):
        return 0.0
    center = 0.5 * (lo + hi)
    sigma = max((hi - lo) * sigma_frac, 1e-9)
    return float(math.exp(-0.5 * ((float(value) - center) / sigma) ** 2))


def window_score(params: Dict,
                 hyp: Any,
                 window: Optional[Tuple[float, float]] = None,
                 mode: str = "trapezoid") -> Tuple[float, Optional[Tuple[float, float]]]:
    """窗口维度综合入口：解析窗口并计算 property_value 的窗口得分。

    Args:
        params: 候选参数字典（property_value / value 键）
        hyp: 目标假设（用于解析窗口；window 已给出时可传 None）
        window: 可选显式窗口 (lo, hi)；为 None 时从 hyp 解析
        mode: "trapezoid"（默认，窗口内平顶=1）或 "gaussian"

    Returns:
        (window_score, window_bounds)
        - 解析不到窗口：返回 (0.0, None)——维度中性，不影响现有打分；
        - property_value 缺失/非正：返回 (0.0, window)。
    """
    if window is None:
        window = parse_hypothesis_window(hyp)
    if window is None:
        return 0.0, None
    lo, hi = window
    cv = params.get("property_value") or params.get("value") or 0
    if not isinstance(cv, (int, float)) or cv <= 0:
        return 0.0, window
    if mode == "gaussian":
        return gaussian_window_score(cv, lo, hi), window
    return trapezoid_window_score(cv, lo, hi), window


# ═══════════════════════════════════════════════════════════════
# 核心：增强打分函数
# ═══════════════════════════════════════════════════════════════

# ── 导入原始 _literature_prior_score 和 _empty_evidence_score ──
# （从 discovery.py 延迟导入，避免循环依赖）
_literature_prior_score_ref: Optional[Callable] = None


def _get_literature_prior_score() -> Callable:
    """延迟获取 _literature_prior_score 引用（避免循环导入）。"""
    global _literature_prior_score_ref
    if _literature_prior_score_ref is None:
        from literature_agent.discovery import _literature_prior_score
        _literature_prior_score_ref = _literature_prior_score
    return _literature_prior_score_ref


def _get_empty_evidence_score() -> Callable:
    """延迟获取 _empty_evidence_score 引用（避免循环导入）。"""
    from literature_agent.discovery import _empty_evidence_score
    return _empty_evidence_score


def enhanced_evidence_score(params: Dict,
                            hyp: Any,
                            literature_values: List[float],
                            text: str = "",
                            llm_plausibility: Optional[float] = None,
                            explored_points: Optional[List[Dict]] = None,
                            enable_stretch: bool = True) -> Tuple[float, Dict]:
    """增强版文献证据打分函数（v2 默认）。

    相比 legacy_evidence_aware_score() 的改进：
      1) 非线性拉伸：sigmoid 将窄区间分数映射到更宽范围
      2) 动态权重：根据假设类型（unexplored/missing_link/contradiction）调整三维信号权重
      3) 加权调和平均融合：对低分信号更敏感，防止单维过拟合
      4) 多样性奖励：候选点远离已探索区域时额外加分

    调用者无需关心内部实现——只需传入与 legacy 版本相同的参数，
    额外可传入 explored_points 以启用多样性奖励。

    Args:
        params: 候选参数字典
        hyp: 目标假设（DiscoveryHypothesis 或兼容对象）
        literature_values: 文献数值列表
        text: 可选证据文本
        llm_plausibility: 可选 LLM 科学合理性评分 [0, 1]
        explored_points: 可选已探索点列表（用于多样性奖励）
        enable_stretch: 是否启用 sigmoid 拉伸（默认 True）

    Returns:
        (score: float, meta: Dict)
        meta 包含 score_type, degraded, reason, evidence_count, prior_breakdown 等
    """
    # ── 空证据保护：与 legacy 保持一致 ──
    if not literature_values:
        empty_score_fn = _get_empty_evidence_score()
        base = empty_score_fn(params)
        if llm_plausibility is not None:
            base = base * 0.65 + float(llm_plausibility) * 0.35
        return float(min(base, 1.0)), {
            "score_type": "degraded_no_evidence",
            "degraded": True,
            "reason": "证据数值为空，打分无区分度（未利用文献数值先验）",
            "evidence_count": 0,
            "literature_prior": 0.0,
            "score_version": "v2",
        }

    # ── 提取候选参数 ──
    cand_mats = params.get("materials") or params.get("material") or (
        getattr(hyp, "materials", None) or [])
    if isinstance(cand_mats, str):
        cand_mats = [cand_mats]
    cand_mats = [str(m).lower() for m in cand_mats]

    cand_prop = getattr(hyp, "property", "") or ""
    text_lower = (text or "").lower()

    # ── 三维证据信号计算 ──
    # 信号 1: 材料覆盖率 (0-1)
    # 候选材料在证据文本中出现的比例 — 材料出现越多，该假设越可靠
    # 注意：使用归一化键匹配（_material_keys），修复知识图谱中
    #   "NiCu-MOF-74" vs "Ni-Cu-MOF-74"、"缺陷MOF-74(Co)" vs "缺陷 MOF-74"
    #   "CO2 吸附容量" vs "CO2吸附容量" 等写法差异导致的信号失效。
    coverage = 0.0
    if text_lower and cand_mats:
        text_norm = _norm_key(text)
        mat_hits = 0
        for m in cand_mats:
            m_keys = _material_keys(m)
            if any(
                (m.lower() in text_lower) or (k and k in text_norm)
                for k in m_keys
            ):
                mat_hits += 1
        coverage = mat_hits / max(len(cand_mats), 1)

    # 信号 2: 材料x性质共现 (0-1)
    # 在包含材料的段落中，同时出现目标性质的比例
    # 段落级检查比全文检查更细粒度——共现频次影响分数
    # 同样使用归一化匹配 + 属性关键词映射（"等量吸附热 Qst" vs
    # "CO2吸附热（Qst）"、"水蒸气→胺型MOF容量" vs "湿态CO2吸附容量"）。
    cooccurrence = 0.0
    if text_lower and cand_mats and cand_prop:
        # 按段落切分（以空行/标题为界）
        paragraphs = [p.strip() for p in (text or "").split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text or ""]

        prop_keys = _property_keys(cand_prop)

        mat_paragraphs = []
        for para in paragraphs:
            para_lower = para.lower()
            para_norm = _norm_key(para)
            if any(
                (m.lower() in para_lower) or (k and k in para_norm)
                for m in cand_mats for k in _material_keys(m)
            ):
                mat_paragraphs.append((para_lower, para_norm))

        if mat_paragraphs:
            # 计算：同时包含材料+性质的段落比例
            co_occur_count = 0
            for para_lower, para_norm in mat_paragraphs:
                if any(
                    (cand_prop.lower() in para_lower) or (k and k in para_norm)
                    for k in prop_keys
                ):
                    co_occur_count += 1
            cooccurrence = co_occur_count / max(len(mat_paragraphs), 1)
        else:
            # 材料完全未出现 → 共现为 0
            cooccurrence = 0.0

    # 信号 3: 数值接近度 (0-1)
    # 候选 property_value 距离文献数值分布的远近
    cv = params.get("property_value") or params.get("value") or 0
    prior_fn = _get_literature_prior_score()
    numerical = prior_fn(cv, literature_values)

    # ── 动态权重（窗口型假设自动挂载 window 维度）──
    weights = _hypothesis_type_weights(hyp)

    # ── 窗口型维度（window-aware）：从假设解析窗口并计算窗口得分 ──
    # 解析不到窗口时 window_score 返回 (0.0, None)，权重为 0，
    # 完全不影响现有三维融合结果（向后兼容）。
    window_val, window_bounds = window_score(params, hyp)

    # ── 加权调和平均融合（三维基础信号）──
    # 注意：window 维度不进入调和平均——调和平均会把 window=0 的项
    # 「剔除」（不拉低总分）却让 window∈(0,1) 的过渡项显著拉低总分，
    # 造成「远离窗口反而比靠近窗口边界分高」的非单调响应，破坏
    # 「越远离窗口惩罚越大」的语义。因此 window 维度改用乘性门控。
    signal_scores_3d = {
        "coverage": coverage,
        "cooccurrence": cooccurrence,
        "numerical": numerical,
    }
    weights_3d = {k: v for k, v in weights.items() if k != "window"}
    fused = weighted_harmonic_fusion(signal_scores_3d, weights_3d)

    # ── window 维度：算术加权混合（仅窗口型假设）──
    # fused = 0.60 * fused_3d + 0.40 * window_val
    # 相比乘性门控（_WINDOW_GATE_MIN=0.6，窗口外仅打 6 折，梯度弱、区分度不足），
    # 算术混合让窗口直接贡献 40% 分数：窗口内（window_val=1）多 0.40、
    # 窗口外（window_val=0）少 0.40，差异稳定可学习（GP/UCB 可强导向窗口）。
    # 权重 0.30 → 0.40（GOAI #11：hypo_3 窗口型假设在 v2 下仍输给 random，
    # 窗口 30% 权重不足以覆盖三维证据信号的噪声，40% 后窗口成为主导维度）。
    # 算术线性混合严格单调，无调和平均「剔除 0 项 / 过渡项拉低总分」的
    # 非单调问题（见上 751-755 注释）。
    if window_bounds is not None:
        fused = 0.60 * fused + 0.40 * window_val

    # ── 常识奖励（与 v1 对齐，v2 曾缺失的重要区分信号）──
    # 1) composition_x 倒 U 型奖励：双金属/掺杂假设的组分比例接近 0.5 加分
    #    （知识图谱 R5/R19 支持"1:1 最优"，对 hypo_1 双金属倒U 假设至关重要）
    # 2) temperature 奖励：常见实验温度区间（273-373K）加分
    common_bonus = 0.0
    _hyp_mats = getattr(hyp, "materials", None) or []
    is_bimetallic = bool(_hyp_mats and len(_hyp_mats) >= 2)
    if not is_bimetallic and getattr(hyp, "title", ""):
        _tl = (getattr(hyp, "title", "") or "").lower()
        if any(kw in _tl for kw in ["双金属", "掺杂", "比例"]):
            is_bimetallic = True
    if is_bimetallic:
        cx = params.get("composition_x", None)
        if cx is not None and 0.3 <= cx <= 0.7:
            common_bonus += 0.05 + 0.05 * max(
                0.0, 1.0 - ((cx - 0.5) / 0.2) ** 2
            )
    temp = params.get("temperature", None)
    if temp is not None:
        if 273 <= temp <= 373:
            common_bonus += 0.05
        elif 373 < temp <= 500:
            common_bonus += 0.02

    # ── 线性映射 fused [0, 1] → score [0.05, 0.90] ──
    # 相比 v1 的固定基分 0.15 + 窄范围加成，v2 使用更宽的映射区间：
    #   fused=0.0（无证据）→ 0.05（极低分，几乎无证据支撑）
    #   fused=0.5（混合证据）→ 0.475（中等，有部分证据）
    #   fused=1.0（强证据）→ 0.90（高分，三维证据全匹配）
    # 这比 legacy 的 0.15 + narrow additions 有更大的动态范围。
    raw_score = 0.05 + 0.85 * fused + common_bonus

    # ── 多样性奖励（在 sigmoid 前加入，保持线性区域）──
    div_bonus = 0.0
    if explored_points:
        div_bonus = diversity_bonus(params, explored_points)
        raw_score += div_bonus

    raw_score = float(min(raw_score, 1.0))

    # ── LLM plausibility 混合 ──
    if llm_plausibility is not None:
        raw_score = min(raw_score * 0.65 + float(llm_plausibility) * 0.35, 1.0)

    # ── 分段拉伸（原 sigmoid 拉伸，GOAI #11 修复高段饱和）──
    # 使用 stretch_score 的分段线性映射：
    #   中段将中等分数拉开，高段保留区分度（不再被 sigmoid 压扁）：
    #     输入 0.30 → 0.22
    #     输入 0.50 → 0.42
    #     输入 0.65 → 0.62
    #     输入 0.80 → 0.82
    #     输入 0.90 → 0.93
    # 目标：将 v1 窄区间 [0.54, 0.68] 映射到宽区间 [0.42, 0.75]，
    # 且高分（0.8+）候选之间仍保持可区分梯度。
    if enable_stretch:
        final_score = stretch_score(raw_score, center=0.5, steepness=10.0)
    else:
        final_score = raw_score

    meta = {
        "score_type": "prior_based",
        "score_version": "v2",
        "degraded": False,
        "reason": "",
        "evidence_count": len(literature_values),
        "literature_prior": round(numerical, 4),
        "fused_score": round(fused, 4),
        "raw_score": round(raw_score, 4),
        "common_bonus": round(common_bonus, 5),
        "diversity_bonus": round(div_bonus, 5),
        "window": {
            "parsed": window_bounds is not None,
            "bounds": [round(window_bounds[0], 4), round(window_bounds[1], 4)]
            if window_bounds is not None else None,
            "score": round(window_val, 4),
            "mode": "trapezoid",
        },
        "signal_breakdown": {
            "coverage": round(coverage, 4),
            "cooccurrence": round(cooccurrence, 4),
            "numerical": round(numerical, 4),
            "window": round(window_val, 4),
        },
        "weights": {k: round(v, 4) for k, v in weights.items()},
    }
    return float(final_score), meta


def legacy_evidence_score(params: Dict,
                          hyp: Any,
                          literature_values: List[float],
                          text: str = "",
                          llm_plausibility: Optional[float] = None) -> Tuple[float, Dict]:
    """原始文献证据打分函数（v1，向后兼容通道）。

    直接委托给 discovery.evidence_aware_score() 以保持完全一致的行为。
    此函数存在的目的是为调用者提供一个统一的入口——通过同一个接口
    （enhanced_evidence_score / legacy_evidence_score）即可切换新旧打分。
    """
    from literature_agent.discovery import evidence_aware_score
    score, meta = evidence_aware_score(
        params=params,
        hyp=hyp,
        literature_values=literature_values,
        text=text,
        llm_plausibility=llm_plausibility,
    )
    meta["score_version"] = "v1"
    return score, meta


# ═══════════════════════════════════════════════════════════════
# 统一入口：自动根据 SCORING_V2 选择版本
# ═══════════════════════════════════════════════════════════════

def auto_evidence_score(params: Dict,
                        hyp: Any,
                        literature_values: List[float],
                        text: str = "",
                        llm_plausibility: Optional[float] = None,
                        explored_points: Optional[List[Dict]] = None,
                        force_v2: Optional[bool] = None) -> Tuple[float, Dict]:
    """自动选择打分版本（支持显式覆盖与默认环境变量）。

    当 force_v2=True 时强制使用 v2，force_v2=False 时强制使用 v1，
    未指定时读取 SCORING_V2 环境变量（默认 true）。

    Args:
        params: 候选参数字典
        hyp: 目标假设
        literature_values: 文献数值列表
        text: 可选证据文本
        llm_plausibility: 可选 LLM 科学合理性评分
        explored_points: 可选已探索点列表（仅 v2 使用）
        force_v2: 显式覆盖版本选择

    Returns:
        (score: float, meta: Dict)
    """
    use_v2 = force_v2 if force_v2 is not None else _is_scoring_v2()

    if use_v2:
        return enhanced_evidence_score(
            params=params,
            hyp=hyp,
            literature_values=literature_values,
            text=text,
            llm_plausibility=llm_plausibility,
            explored_points=explored_points,
        )
    else:
        return legacy_evidence_score(
            params=params,
            hyp=hyp,
            literature_values=literature_values,
            text=text,
            llm_plausibility=llm_plausibility,
        )
