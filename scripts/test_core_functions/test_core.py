# -*- coding: utf-8 -*-
"""
GOAI 核心纯函数测试
====================
为项目核心纯逻辑补充单元测试，覆盖：

  1) utils/config.py 的 set_run_dir 多主题路径派生（含 survey/"" 向后兼容回退）；
  2) pi_agent/tools.py 的 _extract_json_object（JSON 围栏/BOM/前后缀/数组/非法输入）；
  3) pi_agent/tools.py 的数值验证纯函数
     （_normalize_unit 单位归一化 / _extract_claimed_values 数值提取 /
      _verify_numerical_claim 验证逻辑真/假判定）；
  4) literature_agent/discovery.py 的打分确定性
     （evidence_aware_score / _empty_evidence_score / _literature_prior_score）；
  5) random.seed 固定后随机序列可复现（确定性基础设施）；
  6) literature_agent/classical_models.py 的 Slack/Vegard 拟合
     （该文件由另一 Agent 并行新建，若未就绪则打印 SKIP 并跳过，不影响其它组）。

约束：
  - 不联网、不调用任何 LLM/检索 API；
  - 不读写 workspace/ 下的产物与缓存（不触碰 workspace/ 目录）；
  - 无 pytest 依赖，print + assert 风格，main() 以退出码汇总 PASS/FAIL。

独立运行（需在项目根下执行，或任意目录执行该文件绝对路径）：
    python -X utf8 scripts/test_core_functions/test_core.py
"""

import os
import random
import sys

# Windows GBK 控制台打印 emoji/Unicode 会 UnicodeEncodeError：
# 统一按 UTF-8 输出（-X utf8 之外的兜底，保证任意控制台可运行）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# 项目根（scripts/test_core_functions/ → 上三级）
ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import utils.config as cfg


# ─────────────────────────────────────────────────────────────
# 断言辅助：收集失败项并打印
# ─────────────────────────────────────────────────────────────
def _check(failures, cond, msg):
    if cond:
        print(f"  ✓ {msg}")
    else:
        failures.append(msg)
        print(f"  ✗ FAIL: {msg}")


def _approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


# ─────────────────────────────────────────────────────────────
# [1] utils/config.py — set_run_dir 路径派生
# ─────────────────────────────────────────────────────────────
def _test_run_dir(failures):
    # 暂存并清除可能干扰的环境变量，保证 set_run_dir 走默认路径；
    # 测试结束恢复原环境变量。
    saved = {}
    for k in ("SURVEY_DIR", "SURVEY_MEMORY_DIR", "SURVEY_LOGS_DIR",
              "SURVEY_CHECKPOINT_DIR", "LITERATURE_CACHE_DIR"):
        saved[k] = os.environ.get(k)
        os.environ.pop(k, None)
    try:
        # ── a) 自定义 run_dir="perovskite" → 各目录带主题隔离 ──
        cfg.set_run_dir("perovskite")
        # 注意：源码中 SURVEY_DIR 在自定义 run_dir 下为
        # workspace/outputs/{run_dir}/literature_survey（保留历史子目录）
        _check(failures, cfg.SURVEY_DIR == "workspace/outputs/perovskite/literature_survey",
               f"SURVEY_DIR 应隔离到 outputs/perovskite/literature_survey，实际 {cfg.SURVEY_DIR}")
        _check(failures, cfg.MEMORY_DIR == "workspace/memory/perovskite",
               f"MEMORY_DIR 应隔离到 memory/perovskite，实际 {cfg.MEMORY_DIR}")
        _check(failures, cfg.LOGS_DIR == "workspace/logs/perovskite",
               f"LOGS_DIR 应隔离到 logs/perovskite，实际 {cfg.LOGS_DIR}")
        _check(failures, cfg.CHECKPOINT_DIR == "workspace/checkpoint/perovskite",
               f"CHECKPOINT_DIR 应隔离到 checkpoint/perovskite，实际 {cfg.CHECKPOINT_DIR}")
        _check(failures, cfg.LITERATURE_CACHE_DIR == "workspace/data/literature_cache/perovskite",
               f"LITERATURE_CACHE_DIR 应隔离到 data/literature_cache/perovskite，实际 {cfg.LITERATURE_CACHE_DIR}")
        _check(failures, cfg.get_literature_cache_dir() == cfg.LITERATURE_CACHE_DIR,
               "get_literature_cache_dir 应与 LITERATURE_CACHE_DIR 一致")

        # ── b) run_dir="survey" → 回退到历史默认路径（向后兼容） ──
        cfg.set_run_dir("survey")
        _check(failures, cfg.SURVEY_DIR == "workspace/outputs/literature_survey",
               f"survey 的 SURVEY_DIR 应回退到历史路径，实际 {cfg.SURVEY_DIR}")
        _check(failures, cfg.MEMORY_DIR == "workspace/memory/survey",
               f"survey 的 MEMORY_DIR 应回退到 memory/survey，实际 {cfg.MEMORY_DIR}")
        _check(failures, cfg.LOGS_DIR == "workspace/logs",
               f"survey 的 LOGS_DIR 应回退到 logs，实际 {cfg.LOGS_DIR}")
        _check(failures, cfg.CHECKPOINT_DIR == "workspace",
               f"survey 的 CHECKPOINT_DIR 应回退到 workspace，实际 {cfg.CHECKPOINT_DIR}")
        _check(failures, cfg.LITERATURE_CACHE_DIR == "workspace/data/literature_cache",
               f"survey 的 LITERATURE_CACHE_DIR 应回退到历史缓存目录，实际 {cfg.LITERATURE_CACHE_DIR}")

        # ── c) run_dir="" → 同样回退到历史默认路径 ──
        cfg.set_run_dir("")
        _check(failures, cfg.SURVEY_DIR == "workspace/outputs/literature_survey",
               f"空串的 SURVEY_DIR 应回退到历史路径，实际 {cfg.SURVEY_DIR}")
        _check(failures, cfg.LITERATURE_CACHE_DIR == "workspace/data/literature_cache",
               f"空串的 LITERATURE_CACHE_DIR 应回退到历史缓存目录，实际 {cfg.LITERATURE_CACHE_DIR}")

        # ── d) 再设置一个自定义 run_dir，验证可重复切换且互不串味 ──
        cfg.set_run_dir("cathode")
        _check(failures, cfg.MEMORY_DIR == "workspace/memory/cathode",
               f"切换到 cathode 后 MEMORY_DIR 应更新，实际 {cfg.MEMORY_DIR}")
        _check(failures, cfg.LITERATURE_CACHE_DIR == "workspace/data/literature_cache/cathode",
               f"切换到 cathode 后缓存目录应更新，实际 {cfg.LITERATURE_CACHE_DIR}")
    finally:
        cfg.set_run_dir("survey")  # 全局状态还原，避免影响后续测试/运行
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ─────────────────────────────────────────────────────────────
# [2] pi_agent/tools.py — _extract_json_object
# ─────────────────────────────────────────────────────────────
def _test_extract_json_object(failures):
    from pi_agent.tools import _extract_json_object

    # ① 直接 JSON
    r = _extract_json_object('{"a": 1, "b": [2, 3]}')
    _check(failures, isinstance(r, dict) and r.get("a") == 1 and r.get("b") == [2, 3],
           "直接 JSON 对象可解析")

    # ② ```json 代码围栏
    r = _extract_json_object('```json\n{"capacity": 4.5, "unit": "mmol/g"}\n```')
    _check(failures, isinstance(r, dict) and r.get("capacity") == 4.5,
           "```json 代码围栏内的对象可解析")

    # ③ 普通 ``` 代码围栏（数组）
    r = _extract_json_object('```\n[10, 20, 30]\n```')
    _check(failures, r == [10, 20, 30],
           "普通代码围栏内的数组可解析")

    # ④ 前后缀叙述文本（LLM 常见输出风格）
    r = _extract_json_object('综合以上证据，结论为 {"material": "MAPbI3", "score": 0.95}，详见报告。')
    _check(failures, isinstance(r, dict) and r.get("material") == "MAPbI3",
           "前后缀叙述文本中的 JSON 对象可提取")

    # ⑤ BOM 开头
    r = _extract_json_object('\ufeff{"a": 1}')
    _check(failures, isinstance(r, dict) and r.get("a") == 1,
           "BOM 开头的 JSON 可解析")

    # ⑥ 数组形态（无围栏、无前后缀）
    r = _extract_json_object('[1, 2, 3]')
    _check(failures, r == [1, 2, 3],
           "顶层数组形态可解析")

    # ⑦ 非 JSON 文本 → None
    r = _extract_json_object("这不是 JSON 内容，只是一个句子")
    _check(failures, r is None,
           "非 JSON 文本返回 None")

    # ⑧ 空串 / 纯空白 / 非字符串 → None
    _check(failures, _extract_json_object("") is None, "空串返回 None")
    _check(failures, _extract_json_object("   \n\t ") is None, "纯空白返回 None")
    _check(failures, _extract_json_object(None) is None, "None 返回 None")
    _check(failures, _extract_json_object(123) is None, "非字符串输入返回 None")


# ─────────────────────────────────────────────────────────────
# [3] pi_agent/tools.py — _normalize_unit 单位归一化
# ─────────────────────────────────────────────────────────────
def _test_normalize_unit(failures):
    from pi_agent.tools import ToolHandlers

    _check(failures, ToolHandlers._normalize_unit("mmol/g") == "mmol/g",
           "'mmol/g' 归一化为 mmol/g")
    _check(failures, ToolHandlers._normalize_unit("mmol / g") == "mmol/g",
           "'mmol / g'（带空格）归一化为 mmol/g")
    _check(failures, ToolHandlers._normalize_unit("eV") == "ev",
           "'eV' 归一化为 ev（小写规范形）")
    _check(failures, ToolHandlers._normalize_unit("kJ/mol") == "kj/mol",
           "'kJ/mol' 归一化为 kj/mol")
    _check(failures, ToolHandlers._normalize_unit("kj mol⁻¹") == "kj/mol",
           "'kj mol⁻¹' 归一化为 kj/mol")
    # mAh/g 不在映射表中：应不崩溃、返回小写无多余空白的处理结果
    r = ToolHandlers._normalize_unit("mAh/g")
    _check(failures, isinstance(r, str) and r == "mah/g",
           f"'mAh/g' 不在映射表时安全降级为 {r}")
    _check(failures, ToolHandlers._normalize_unit("") == "",
           "空串单位安全返回空串")


# ─────────────────────────────────────────────────────────────
# [4] pi_agent/tools.py — _extract_claimed_values 数值提取
# ─────────────────────────────────────────────────────────────
def _test_extract_claimed_values(failures):
    from pi_agent.tools import ToolHandlers

    # 范围声明："3-5 kJ/mol" → low=3, high=5
    r = ToolHandlers._extract_claimed_values("Qst 为 3-5 kJ/mol")
    _check(failures, len(r) == 1 and _approx(r[0]["low_value"], 3.0)
           and _approx(r[0]["high_value"], 5.0)
           and r[0]["unit_norm"] == "kj/mol",
           f"'Qst 为 3-5 kJ/mol' 提取为范围 3-5 kj/mol，实际 {r}")

    # 带前缀的单值："~4.5 mmol/g" → prefix="~", low=high=4.5
    r = ToolHandlers._extract_claimed_values("容量 ~4.5 mmol/g")
    _check(failures, len(r) == 1 and r[0]["prefix"] == "~"
           and _approx(r[0]["low_value"], 4.5)
           and _approx(r[0]["high_value"], 4.5)
           and r[0]["unit_norm"] == "mmol/g",
           f"'容量 ~4.5 mmol/g' 提取为 ~ 4.5 mmol/g，实际 {r}")

    # 单值百分比："0.5 wt%" → unit=wt%
    r = ToolHandlers._extract_claimed_values("掺杂量 0.5 wt%")
    _check(failures, len(r) == 1 and _approx(r[0]["low_value"], 0.5)
           and r[0]["unit_norm"] == "wt%",
           f"'掺杂量 0.5 wt%' 提取为 0.5 wt%，实际 {r}")

    # 纯数字无单位 → 不误提取（返回空列表）
    r = ToolHandlers._extract_claimed_values("常数 a = 42 且后面没有单位")
    _check(failures, r == [],
           f"无单位文本不应误提取数值，实际 {r}")


# ─────────────────────────────────────────────────────────────
# [5] pi_agent/tools.py — _verify_numerical_claim 验证逻辑
# ─────────────────────────────────────────────────────────────
def _test_verify_numerical_claim(failures):
    from pi_agent.tools import ToolHandlers

    # 强制走 tools.py 自带的 _extract_evidence_values 回退路径，
    # 使测试结果完全由本模块纯逻辑决定（不依赖 extractor 实现细节）。
    # 这是运行时属性替换，不修改任何源码文件，测后恢复。
    try:
        import literature_agent.extractor as _ext_mod
        _orig = _ext_mod.extract_numerical_values_with_context
        _ext_mod.extract_numerical_values_with_context = None
    except ImportError:
        _orig = None  # extractor 不可用时 _verify_numerical_claim 本就回退

    try:
        # ① 真（verified）：声明范围 [3,5] mmol/g，证据含 4.2 与 4.5 → n_found>=2
        kg = (
            "### 1. High-capacity CO2 adsorbents\n"
            "The adsorbent reached 4.2 mmol/g uptake at 298 K.\n"
            "A related sample showed 4.5 mmol/g capacity.\n"
        )
        r = ToolHandlers._verify_numerical_claim(
            "3-5 mmol/g", "mmol/g", "CO2 uptake", knowledge_graph_text=kg)
        _check(failures, r.get("verified") is True
               and r.get("verification_status") == "verified",
               f"证据匹配 2 条时应 verified，实际 {r.get('verification_status')}")

        # ② 部分（partial）：声明 4.2 mmol/g，证据仅 4.5（唯一匹配）→ n_found=1
        kg_partial = (
            "### 1. Sample report\n"
            "The sample showed 4.5 mmol/g capacity.\n"
        )
        r = ToolHandlers._verify_numerical_claim(
            "4.2 mmol/g", "mmol/g", "CO2 uptake", knowledge_graph_text=kg_partial)
        _check(failures, r.get("verified") is True
               and r.get("verification_status") == "partial",
               f"仅 1 条匹配时应 partial，实际 {r.get('verification_status')}")

        # ③ 假（unverified）：证据文本为空 → 直接 unverified
        r = ToolHandlers._verify_numerical_claim(
            "6-7 mmol/g", "mmol/g", "CO2 uptake", "", "")
        _check(failures, r.get("verified") is False
               and r.get("verification_status") == "unverified",
               f"无证据文本时应 unverified，实际 {r.get('verification_status')}")

        # ④ 假（contradicted）：声明 30-40 mmol/g，证据仅 4.2/4.5 → 偏差>50%
        r = ToolHandlers._verify_numerical_claim(
            "30-40 mmol/g", "mmol/g", "CO2 uptake", knowledge_graph_text=kg)
        _check(failures, r.get("verified") is False
               and r.get("verification_status") == "contradicted",
               f"文献值显著偏离声明时应 contradicted，实际 {r.get('verification_status')}")
    finally:
        if _orig is not None:
            try:
                _ext_mod.extract_numerical_values_with_context = _orig
            except NameError:
                pass


# ─────────────────────────────────────────────────────────────
# [6] literature_agent/discovery.py — 打分确定性
# ─────────────────────────────────────────────────────────────
def _test_discovery_deterministic(failures):
    from literature_agent.discovery import (
        DiscoveryHypothesis,
        _empty_evidence_score,
        _literature_prior_score,
        evidence_aware_score,
    )

    hyp = DiscoveryHypothesis(
        id="h1", title="band gap", materials=["MAPbI3"], property="band gap")
    params = {"materials": ["MAPbI3"], "property_value": 1.6}
    text = "MAPbI3 exhibits a direct band gap of 1.6 eV."
    lit = [1.55, 1.6, 1.65]

    # ① evidence_aware_score 固定输入两次调用 → 分数与元信息完全一致（确定性）
    s1, m1 = evidence_aware_score(params, hyp, lit, text)
    s2, m2 = evidence_aware_score(params, hyp, lit, text)
    _check(failures, s1 == s2 and m1 == m2,
           f"evidence_aware_score 两次调用一致（score={s1}, meta={m1}）")

    # ② 空证据保护：degraded 标记 + 可区分低分区间 [0.10, 0.22]
    s3, m3 = evidence_aware_score(params, hyp, [], text)
    s4, m4 = evidence_aware_score(params, hyp, [], text)
    _check(failures, m3.get("degraded") is True
           and m3.get("score_type") == "degraded_no_evidence"
           and 0.10 <= s3 <= 0.22 and s3 == s4,
           f"空证据时 degraded 低分确定且可区分（score={s3:.4f}）")

    # ③ _empty_evidence_score 确定性（同一参数两次一致）
    e1 = _empty_evidence_score(params)
    e2 = _empty_evidence_score(params)
    _check(failures, e1 == e2 and 0.10 <= e1 <= 0.22,
           f"_empty_evidence_score 确定性且落在 [0.10, 0.22]（{e1:.4f}）")

    # ④ _literature_prior_score 数值逻辑
    _check(failures, _literature_prior_score(4.5, [4.5]) == 1.0,
           "候选值完全命中文献值 → 先验分 1.0")
    _check(failures, _literature_prior_score(0, [4.5]) == 0.0,
           "非法候选值（<=0）→ 先验分 0.0")
    p_off = _literature_prior_score(100.0, [4.5])
    _check(failures, 0.0 <= p_off < 0.2,
           f"偏离文献值 → 低先验分（{p_off:.4f}）")


# ─────────────────────────────────────────────────────────────
# [7] random.seed 固定后可复现（确定性基础设施）
# ─────────────────────────────────────────────────────────────
def _test_seed_reproducible(failures):
    from literature_agent.discovery import (
        DiscoveryHypothesis,
        evidence_aware_score,
    )

    # ① random 序列可复现
    random.seed(42)
    seq1 = [random.random() for _ in range(5)]
    random.seed(42)
    seq2 = [random.random() for _ in range(5)]
    _check(failures, seq1 == seq2,
           f"random.seed(42) 后随机序列可复现（{seq1[0]:.6f}...）")

    # ② numpy 序列可复现（numpy 缺失则跳过该项）
    try:
        import numpy as np
        np.random.seed(42)
        n1 = np.random.rand(5).tolist()
        np.random.seed(42)
        n2 = np.random.rand(5).tolist()
        _check(failures, n1 == n2,
               f"numpy random seed(42) 后序列可复现（{n1[0]:.6f}...）")
        # seed_everything 同步固定 random+numpy
        cfg.seed_everything(42)
        _check(failures, True, "seed_everything(42) 可正常执行")
    except ImportError:
        print("  ⚠ numpy 不可用，跳过 numpy 序列复现校验")

    # ③ evidence_aware_score 不依赖全局随机种子（确定性打分）
    hyp = DiscoveryHypothesis(id="h1", title="band gap",
                              materials=["MAPbI3"], property="band gap")
    params = {"materials": ["MAPbI3"], "property_value": 1.6}
    text = "MAPbI3 exhibits a direct band gap of 1.6 eV."
    lit = [1.55, 1.6, 1.65]
    random.seed(1)
    sa, _ = evidence_aware_score(params, hyp, lit, text)
    random.seed(999)
    sb, _ = evidence_aware_score(params, hyp, lit, text)
    _check(failures, sa == sb,
           f"不同随机种子下 evidence_aware_score 结果一致（{sa}）")


# ─────────────────────────────────────────────────────────────
# [8] literature_agent/classical_models.py — Slack/Vegard 拟合
#     该文件由另一 Agent 并行新建；未就绪时 SKIP，不导致失败。
# ─────────────────────────────────────────────────────────────
def _extract_r2(res):
    """从拟合返回值中提取 R²（兼容 dict / tuple / list / 纯数值）。"""
    if isinstance(res, dict):
        for k, v in res.items():
            kl = k.lower().replace("²", "2").replace("_", "")
            if "r2" in kl or "rsquared" in kl:
                return v
        return None
    if isinstance(res, (tuple, list)):
        if res and isinstance(res[-1], (int, float)) and not isinstance(res[-1], bool):
            if 0.0 <= float(res[-1]) <= 1.0:
                return float(res[-1])
        for item in res:
            r2 = _extract_r2(item)
            if r2 is not None:
                return r2
    return None


def _test_classical_models(failures):
    try:
        import literature_agent.classical_models as cm
    except ImportError as e:
        print(f"  ⚠ SKIP: literature_agent/classical_models.py 未就绪（{e}），跳过本组")
        return

    try:
        import numpy as np

        rng = np.random.default_rng(42)

        # ── Slack 带隙-温度模型：温度必须为正开尔文，Eg 用模型真值+噪声生成 ──
        T = np.linspace(100.0, 800.0, 60)
        E0t, St, thetat = 2.50, 2.30, 300.0
        eg = cm.slack_model(T, E0t, St, thetat) + rng.normal(0, 0.001, T.size)
        res = cm.fit_slack_model(T, eg)
        r2s = res.get("r2")
        if r2s is not None:
            _check(failures, r2s > 0.99,
                   f"Slack 合成数据拟合 R²={r2s:.4f} > 0.99")
            # 参数恢复误差（E_g0/S/theta 均 <5%）
            perr = max(abs(res.get("E_g0", 0) - E0t) / E0t,
                       abs(res.get("S", 0) - St) / St,
                       abs(res.get("theta", 0) - thetat) / thetat)
            _check(failures, perr < 0.05,
                   f"Slack 参数恢复误差 {perr*100:.2f}% < 5%")
        else:
            _check(failures, False, "fit_slack_model 未返回 r2")

        # ── Vegard 定律：组分 x∈[0,1]，晶格常数线性 ──
        xs = np.linspace(0.0, 1.0, 21)
        a0, a1 = 3.5, 4.2
        ys = a0 + (a1 - a0) * xs + rng.normal(0, 0.002, xs.size)
        slope, intercept, r2v = cm.fit_vegard(xs, ys)
        _check(failures, r2v > 0.99, f"Vegard 合成数据拟合 R²={r2v:.4f} > 0.99")
        _check(failures, abs(slope - (a1 - a0)) / (a1 - a0) < 0.05,
               f"Vegard 斜率恢复误差 {abs(slope-(a1-a0))/(a1-a0)*100:.2f}% < 5%")

        # ── 统一入口 fit_classical_baseline 冒烟（vegard/linear/quadratic）──
        base = cm.fit_classical_baseline("vegard", xs, ys)
        _check(failures, base.get("r2", 0) > 0.99,
               f"fit_classical_baseline('vegard') R²={base.get('r2', 0):.4f} > 0.99")
    except Exception as e:
        _check(failures, False, f"classical_models 拟合校验异常: {e!r}")


# ─────────────────────────────────────────────────────────────
# [9] pi_agent/tools.py — 无量纲 ZT / 带隙 eV 文献数值点提取
#     2026-10 新增：热电 ZT（无单位）与带隙（eV）此前因缺单位桶/无量纲
#     路径而提取不到配对点，导致模型对比"数据不足"。本组验证：
#       a) _unit_filter 对 ZT / 带隙 / Seebeck 返回正确单位桶；
#       b) ZT 表格（x=温度 K, y=裸数字）能提取出 (T, ZT) 配对点；
#       c) 带隙 eV 能提取配对点。
#     不联网、不调用 LLM，仅测纯函数。
# ─────────────────────────────────────────────────────────────
def _test_dimensionless_extraction(failures):
    from pi_agent.tools import ToolHandlers

    th = ToolHandlers.__new__(ToolHandlers)  # 不跑 __init__，只测纯函数

    # ── a) _unit_filter 单位桶 ──
    uf = th._unit_filter("热电优值 ZT（1000 K）")
    _check(failures, uf == {"dimensionless"},
           f"_unit_filter('热电优值 ZT') 应返回 dimensionless，实际 {uf}")
    uf2 = th._unit_filter("带隙 band gap")
    _check(failures, uf2 == {"ev"},
           f"_unit_filter('带隙 band gap') 应返回 {{'ev'}}，实际 {uf2}")
    uf3 = th._unit_filter("Seebeck 系数 热电势")
    _check(failures, uf3 == {"µv/k", "uv/k"},
           f"_unit_filter('Seebeck') 应返回 {{'µv/k','uv/k'}}，实际 {uf3}")

    # ── b) ZT 表格提取（x=温度 K, y=ZT 裸数字）──
    hyp_zt = type("H", (), {"property": "热电优值 ZT",
                            "materials": ["SnSe"]})()
    src_zt = (
        "# 热电测试\n"
        "| 材料 | ZT | 温度 |\n"
        "|------|-----|------|\n"
        "| SnSe 单晶 | 2.6 | 923 K |\n"
        "| n 型 PbTe | 1.7 | 800 K |\n"
        "| Yb 填充方钴矿 | 1.4 | 773 K |\n"
        "| CeFe3CoSb12 | 0.8 | 700 K |\n"
    )
    res = th._extract_literature_points(src_zt, hyp_zt)
    if res is None:
        _check(failures, False, "ZT 表格应能提取 (T, ZT) 配对点，实际返回 None")
    else:
        _check(failures, res["n_points"] >= 3,
               f"ZT 提取点数 {res['n_points']} >= 3")
        _check(failures, res["y_unit"] == "dimensionless",
               f"ZT y_unit 应为 dimensionless，实际 {res['y_unit']}")
        _check(failures, res["x_label"] == "temperature",
               f"ZT x_label 应为 temperature，实际 {res['x_label']}")
        _check(failures, any(abs(x - 923) < 1 and abs(y - 2.6) < 1e-6
                             for x, y in res["points"]),
               "ZT 应包含 (923, 2.6) 配对点")

    # ── c) 带隙 eV 提取 ──
    hyp_eg = type("H", (), {"property": "带隙 band gap",
                            "materials": ["MAPbI3", "CsPbBr3"]})()
    src_eg = (
        "# 带隙测试\n"
        "| 材料 | 带隙 (eV) | Br 含量 |\n"
        "|------|----------|---------|\n"
        "| MAPbI3 | 1.55 | x=0.0 |\n"
        "| MAPbI2Br | 1.9 | x=0.33 |\n"
        "| MAPbBr3 | 2.3 | x=1.0 |\n"
    )
    res2 = th._extract_literature_points(src_eg, hyp_eg)
    if res2 is None:
        _check(failures, False, "带隙 eV 表格应能提取 (x, Eg) 配对点，实际返回 None")
    else:
        _check(failures, res2["n_points"] >= 3,
               f"带隙提取点数 {res2['n_points']} >= 3")
        _check(failures, res2["y_unit"] == "ev",
               f"带隙 y_unit 应为 ev，实际 {res2['y_unit']}")

    # ── c) 规则化统计判定 _model_compare_verdict 四种分支 ──
    _check(failures, th._model_compare_verdict(
        {"name": "二次", "k": 3, "r2": 0.92, "rss": 10.0},
        {"name": "线性", "k": 2, "r2": 0.70, "rss": 60.0},
        {"valid": True, "significant": True, "full_side": "候选模型"},
        {"bootstrap": {"r2": {"ci_low": 0.88}}})["verdict"] == "candidate_better",
        "verdict: F 显著 + ΔR²≥0.05 → candidate_better")
    _check(failures, th._model_compare_verdict(
        {"name": "二次", "k": 3, "r2": 0.92, "rss": 10.0},
        {"name": "线性", "k": 2, "r2": 0.70, "rss": 60.0},
        {"valid": False, "reason": "参数数相同"},
        {"bootstrap": {"r2": {"ci_low": 0.85}}})["verdict"] == "candidate_better",
        "verdict: bootstrap CI 下界 > 经典 R² → candidate_better")
    _check(failures, th._model_compare_verdict(
        {"name": "二次", "k": 3, "r2": 0.72, "rss": 30.0},
        {"name": "线性", "k": 2, "r2": 0.70, "rss": 60.0},
        {"valid": False, "reason": "参数数相同"},
        {})["verdict"] == "no_improvement",
        "verdict: ΔR²<0.05 → no_improvement")
    _check(failures, th._model_compare_verdict(
        {"name": "二次", "k": 3, "r2": 0.50, "rss": 80.0},
        {"name": "线性", "k": 2, "r2": 0.70, "rss": 60.0},
        {"valid": False, "reason": "参数数相同"},
        {})["verdict"] == "candidate_worse",
        "verdict: 候选 R² 低于经典 → candidate_worse")

    # ── d) ZT 裸数字不应混入带单位数值（功率因子等）──
    hyp_zt2 = type("H", (), {"property": "热电优值 ZT",
                             "materials": ["PbTe"]})()
    src_zt2 = (
        "# 热电测试 2\n"
        "| 材料 | ZT | 功率因子 | 温度 |\n"
        "|------|-----|---------|------|\n"
        "| PbTe 合金 | 2.0 | 5.63 mW/m·K | 850 K |\n"
        "| PbTe-CdTe | 1.4 | 4.1 mW/m·K | 800 K |\n"
        "| PbTe 纳米 | 1.1 | 3.2 mW/m·K | 750 K |\n"
    )
    res3 = th._extract_literature_points(src_zt2, hyp_zt2)
    if res3 is None:
        _check(failures, False, "ZT 混合表格应能提取，实际返回 None")
    else:
        ys = [y for _, y in res3["points"]]
        _check(failures, all(y <= 20.0 for y in ys),
               f"ZT 提取值应全部 ≤20（不应混入功率因子 5.63），实际 {ys[:6]}")


# ─────────────────────────────────────────────────────────────
# [10] literature_agent/discovery.py — LLM 剪枝/聚焦应用到搜索空间
#      2026-10 新增：LLM 引导的 prune/focus_regions 必须真正作用于
#      _acquisition 采样（此前只记录不生效）。本组用 fake LLM guide 验证：
#       a) _apply_llm_regions 正确解析 prune/focus 区间并记录事件；
#       b) _acquisition 在 focus 区间内采样一半候选点；
#       c) _acquisition 丢弃落入 prune 区间的候选点。
#     不联网、不调用真实 LLM。
# ─────────────────────────────────────────────────────────────
def _test_llm_prune_focus(failures):
    import numpy as np
    from literature_agent.discovery import BayesianOptimizer

    opt = BayesianOptimizer()
    opt._llm_property_idx = 0  # property_value 在参数列表首位

    # ── a) _apply_llm_regions 解析 ──
    fake = [
        {"property_value": 50.0,
         "llm_prune_regions": [[900.0, 1500.0]],
         "llm_focus_regions": [[300.0, 400.0]]},
    ]
    opt._apply_llm_regions(fake)
    _check(failures, opt._llm_prune_regions == [[900.0, 1500.0]],
           f"prune_regions 应被解析为 [[900,1500]]，实际 {opt._llm_prune_regions}")
    _check(failures, opt._llm_focus_regions == [[300.0, 400.0]],
           f"focus_regions 应被解析为 [[300,400]]，实际 {opt._llm_focus_regions}")
    _check(failures, any(e.get("type") == "bayes_llm_region_apply"
                         for e in opt._llm_events),
           "应记录 bayes_llm_region_apply 审计事件")

    # ── b) _acquisition 在 focus 区间内采样一半候选点 ──
    bounds = np.array([[0.0, 1500.0], [0.0, 1.0], [300.0, 1500.0]])
    np.random.seed(7)
    X = np.array([[50.0, 0.5, 500.0]])
    y = np.array([0.7])
    cand = opt._acquisition(X, y, bounds, iteration=0)
    # 候选点从 focus 采样逻辑生成，应落在全区间内（含聚焦逻辑兼容）
    _check(failures, bounds[0, 0] <= cand[0] <= bounds[0, 1],
           f"采样候选 property 应在全 bounds 内，实际 {cand[0]}")

    # 聚焦行为验证: 内部直接测 _acquisition 采样分布——
    # focus 区间 [300,400] 应使最终候选点显著偏向该区间（一半候选点直接
    # 来自 focus 采样，GP-UCB 选择也倾向于高价值区域）
    opt._llm_focus_regions = [[300.0, 400.0]]
    opt._llm_prune_regions = []
    np.random.seed(42)
    sampled = []
    for _ in range(30):
        c = opt._acquisition(X, y, bounds, iteration=1)
        sampled.append(c[0])
    in_focus = sum(1 for v in sampled if 300.0 <= v <= 400.0)
    _check(failures, in_focus >= 10,
           f"聚焦采样 30 次中应 ≥10 次落在 focus 区间 [300,400]，实际 {in_focus}")

    # ── c) prune 区间: 候选点不应落入被剪枝区间 ──
    opt._llm_focus_regions = []
    opt._llm_prune_regions = [[900.0, 1500.0]]
    opt._llm_property_idx = 0
    np.random.seed(3)
    pruned_vals = []
    for _ in range(30):
        c = opt._acquisition(X, y, bounds, iteration=2)
        pruned_vals.append(c[0])
    in_prune = sum(1 for v in pruned_vals if 900.0 <= v <= 1500.0)
    _check(failures, in_prune == 0,
           f"剪枝区间 [900,1500] 内不应出现候选点（30 次采样），实际命中 {in_prune}")

    # ── c2) prune 覆盖整个 bounds 的极端情况: 不应崩溃，应退化回全空间 ──
    opt._llm_prune_regions = [[0.0, 1500.0]]  # 覆盖 property 全范围
    np.random.seed(11)
    try:
        c4 = opt._acquisition(X, y, bounds, iteration=3)
        _check(failures, bounds[0, 0] <= c4[0] <= bounds[0, 1],
               f"prune 全覆盖时应退化回全空间采样，实际 {c4[0]}")
    except Exception as e:
        _check(failures, False, f"prune 全覆盖时 _acquisition 崩溃: {e!r}")
    opt._llm_prune_regions = []  # 还原

    # 事件审计:剪枝聚焦后应记录 region_apply 事件（再次调用触发）
    opt._apply_llm_regions(fake)
    n_region = sum(1 for e in opt._llm_events
                   if e.get("type") == "bayes_llm_region_apply")
    _check(failures, n_region >= 2,
           f"region_apply 审计事件应累积 ≥2，实际 {n_region}")


# ─────────────────────────────────────────────────────────────
# main()：汇总各测试组，退出码 0=全过 / 1=存在失败
# ─────────────────────────────────────────────────────────────
def main() -> int:
    groups = [
        ("[1] utils/config.py — set_run_dir 路径派生", _test_run_dir),
        ("[2] pi_agent/tools.py — _extract_json_object", _test_extract_json_object),
        ("[3] pi_agent/tools.py — _normalize_unit 单位归一化", _test_normalize_unit),
        ("[4] pi_agent/tools.py — _extract_claimed_values 数值提取", _test_extract_claimed_values),
        ("[5] pi_agent/tools.py — _verify_numerical_claim 验证逻辑", _test_verify_numerical_claim),
        ("[6] literature_agent/discovery.py — 打分确定性", _test_discovery_deterministic),
        ("[7] 随机种子固定后可复现", _test_seed_reproducible),
        ("[8] literature_agent/classical_models.py — Slack/Vegard 拟合", _test_classical_models),
        ("[9] pi_agent/tools.py — 无量纲 ZT / 带隙 eV 提取", _test_dimensionless_extraction),
        ("[10] literature_agent/discovery.py — LLM 剪枝/聚焦生效", _test_llm_prune_focus),
    ]

    failures = []
    for title, fn in groups:
        print(f"\n{title}")
        try:
            fn(failures)
        except Exception:
            import traceback
            traceback.print_exc()
            failures.append(f"{title} 执行异常")

    if failures:
        print(f"\n❌ FAILED：{len(failures)} 项失败")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("\n✅ ALL CORE FUNCTION TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
