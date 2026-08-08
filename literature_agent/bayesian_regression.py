# -*- coding: utf-8 -*-
"""
小样本贝叶斯线性回归 — Bayesian Linear Regression for GOAI 文献调研 Agent
==========================================================================
解决 1.md（teacherA#5）指出的核心瓶颈：文献提取的数据点常常只有 3~5 个，
普通 OLS 多项式回归在 n < k+2 时过拟合或无法给出可靠统计结论。本模块用
共轭先验（Normal-Inverse-Gamma）做贝叶斯线性回归，解析求解后验：

    模型:  y = X·β + ε,   ε ~ N(0, σ²·I)
    先验:  β | σ² ~ N(β₀, σ²·V₀),   σ² ~ InvGamma(a₀, b₀)
    后验:  Vₙ = (V₀⁻¹ + XᵀX)⁻¹
           βₙ = Vₙ·(V₀⁻¹·β₀ + Xᵀy)
           aₙ = a₀ + n/2
           bₙ = b₀ + ½·(yᵀy + β₀ᵀV₀⁻¹β₀ − βₙᵀVₙ⁻¹βₙ)
    β 边际后验:  多元 t 分布，νₙ = 2aₙ，位置 βₙ，尺度 (bₙ/aₙ)·Vₙ
    预测 y*|x*:  t 分布，νₙ，均值 x*ᵀβₙ，尺度 (bₙ/aₙ)·(1 + x*ᵀVₙx*)

能力：
  - 3~4 个数据点也能输出带不确定性的参数估计（斜率/截距后验均值 ± 95% 可信区间）；
  - 通过边际似然计算 Bayes Factor（BF₁₀ = 线性模型 vs 常数模型），
    提供"统计上优于'无关系'基线"的贝叶斯表述（teacherB 建议的 BF 对比）；
  - 后验预测区间直接反映小样本不确定性，天然比点估计更诚实。

依赖策略：仅强制标准库 + numpy；scipy.stats.t 用于精确 t 分位数，
若不可用则退化为正态近似（并在结果中标注 approximation=True）。

用法示例:
    from literature_agent.bayesian_regression import fit_bayesian_linear
    res = fit_bayesian_linear([300, 400, 500, 600], [5.0, 3.2, 2.1, 1.5])
    print(res["slope"], res["slope_ci"], res["bayes_factor_vs_constant"])
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:  # scipy 为可选增强；不可用时用正态近似替代 t 分布
    from scipy import stats as _stats
    _HAS_SCIPY = True
except Exception:  # pragma: no cover
    _stats = None
    _HAS_SCIPY = False


__all__ = [
    "fit_bayesian_linear",
    "bayes_factor_vs_constant",
    "_self_check",
]


# ═══════════════════════════════════════════════════════════════
# 内部工具
# ═══════════════════════════════════════════════════════════════

def _as_1d_array(values: Any, name: str) -> np.ndarray:
    """把输入转成 float 一维数组，并做基本合法性检查。"""
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        raise ValueError(f"{name} 为空")
    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError(f"{name} 包含 NaN/Inf")
    return arr


def _t_ppf(q: float, nu: float) -> Tuple[float, bool]:
    """t 分布分位数；scipy 不可用时退化为正态近似。返回 (值, 是否近似)。"""
    if _HAS_SCIPY and _stats is not None:
        try:
            return float(_stats.t.ppf(q, nu)), False
        except Exception:  # pragma: no cover
            pass
    # 正态近似：ν 越大越接近标准正态
    from math import sqrt
    z = 1.959963984540054  # Φ⁻¹(0.975)
    # 大 ν 直接用 z；小 ν 用经验收缩近似（t 比正态更胖尾）
    if nu >= 60:
        return z, True
    c = 1.0 + 1.3 / nu  # 经验修正，宽松覆盖 95% 分位
    return float(z * c if q >= 0.5 else -z * c), True


def _default_prior(x: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """默认弱信息先验（以数据尺度为参照，避免量纲敏感性）。

    - β₀ = [0, mean(y)]：斜率先验中心在 0（无关系），截距中心在 y 均值；
    - V₀ = diag((20·y_scale/x_scale)², (20·y_scale)²)：先验标准差为
      20 倍数据尺度，足够宽以不主导后验（"弱信息"而非"无信息"）；
    - a₀=2, b₀=0.5·y_scale²：σ² 先验均值 = b₀/(a₀−1) = 0.5·y_scale²。
    """
    x_scale = float(np.std(x)) or 1.0
    y_scale = float(np.std(y)) or 1.0
    beta0 = np.array([0.0, float(np.mean(y))], dtype=float)
    V0 = np.diag([
        (20.0 * y_scale / x_scale) ** 2,
        (20.0 * y_scale) ** 2,
    ])
    a0 = 2.0
    b0 = 0.5 * y_scale * y_scale
    return {"beta0": beta0, "V0": V0, "a0": a0, "b0": b0}


def _design_matrix(x: np.ndarray) -> np.ndarray:
    """设计矩阵 X = [x, 1]，列序 [slope, intercept]。"""
    n = x.size
    return np.column_stack([x, np.ones(n)])


def _log_marginal_likelihood(X: np.ndarray, y: np.ndarray,
                             prior: Dict[str, Any]) -> float:
    """解析边际似然 log p(y | X, M)（Normal-Inverse-Gamma 共轭）。

    ln p(y|X) = −n/2·ln(2π) + ½·ln|Vₙ|/|V₀| + a₀·ln b₀ − aₙ·ln bₙ
                + lnΓ(aₙ) − lnΓ(a₀)
    """
    k = X.shape[1]
    n = y.size
    V0 = np.asarray(prior["V0"], dtype=float)
    beta0 = np.asarray(prior["beta0"], dtype=float)
    a0 = float(prior["a0"])
    b0 = float(prior["b0"])
    if V0.shape != (k, k):
        raise ValueError(f"V0 形状 {V0.shape} 与设计矩阵列数 {k} 不符")
    if beta0.shape != (k,):
        raise ValueError(f"beta0 形状 {beta0.shape} 与设计矩阵列数 {k} 不符")

    V0_inv = np.linalg.inv(V0)
    XtX = X.T @ X
    Vn_inv = V0_inv + XtX
    Vn = np.linalg.inv(Vn_inv)
    beta_n = Vn @ (V0_inv @ beta0 + X.T @ y)
    an = a0 + n / 2.0
    quad = float(y.T @ y + beta0.T @ V0_inv @ beta0 - beta_n.T @ Vn_inv @ beta_n)
    bn = b0 + 0.5 * quad
    if bn <= 0 or not np.isfinite(bn):  # 数值保护
        bn = 1e-12

    from math import lgamma, log, pi
    sign_vn, logdet_vn = np.linalg.slogdet(Vn)
    sign_v0, logdet_v0 = np.linalg.slogdet(V0)
    if sign_vn <= 0 or sign_v0 <= 0:  # 防御：奇异先验/设计矩阵
        logdet_vn = 0.0
        logdet_v0 = 0.0
    log_ml = (
        -0.5 * n * log(2.0 * pi)
        + 0.5 * (logdet_vn - logdet_v0)
        + a0 * log(b0) - an * log(bn)
        + lgamma(an) - lgamma(a0)
    )
    return float(log_ml)


# ═══════════════════════════════════════════════════════════════
# 主入口：贝叶斯线性回归
# ═══════════════════════════════════════════════════════════════

def fit_bayesian_linear(x, y, prior: Optional[Dict[str, Any]] = None,
                        x_new: Optional[Any] = None) -> Dict[str, Any]:
    """贝叶斯线性回归 y = intercept + slope·x（共轭先验，解析后验）。

    参数:
        x: 自变量（一维）
        y: 因变量（一维，与 x 等长）
        prior: 可选先验 dict {beta0, V0, a0, b0}；缺省用弱信息先验
        x_new: 可选，预测点（标量或数组），输出后验预测区间

    返回 dict:
        n, slope{mean,std,ci_low,ci_high}, intercept{...}, sigma2{mean,std},
        r2, rmse, mae, bayes_factor_vs_constant, log_bf_vs_constant,
        prediction{mean,ci_low,ci_high}（若给 x_new）, approximation(bool),
        beta_mean, beta_cov, nu
    """
    x = _as_1d_array(x, "x")
    y = _as_1d_array(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    if x.size < 2:
        raise ValueError("贝叶斯线性回归至少需要 2 个数据点")
    if len(set(x.tolist())) < 2:
        raise ValueError("x 需要至少 2 个不同取值")

    prior = prior or _default_prior(x, y)
    X = _design_matrix(x)
    n = x.size

    # ── 后验参数 ──
    V0 = np.asarray(prior["V0"], dtype=float)
    beta0 = np.asarray(prior["beta0"], dtype=float)
    a0 = float(prior["a0"])
    b0 = float(prior["b0"])
    V0_inv = np.linalg.inv(V0)
    Vn_inv = V0_inv + X.T @ X
    Vn = np.linalg.inv(Vn_inv)
    beta_n = Vn @ (V0_inv @ beta0 + X.T @ y)
    an = a0 + n / 2.0
    quad = float(y.T @ y + beta0.T @ V0_inv @ beta0 - beta_n.T @ Vn_inv @ beta_n)
    bn = b0 + 0.5 * quad
    if bn <= 0 or not np.isfinite(bn):
        bn = 1e-12
    nu = 2.0 * an
    sigma2_mean = bn / (an - 1.0) if an > 1.0 else bn
    sigma2_var = (bn ** 2 / ((an - 1.0) ** 2 * (an - 2.0))
                  if an > 2.0 else float("nan"))

    # ── β 边际后验（多元 t）：尺度矩阵 (bn/an)·Vn ──
    scale_mat = (bn / an) * Vn
    slope_mean = float(beta_n[0])
    intercept_mean = float(beta_n[1])
    slope_scale = float(np.sqrt(scale_mat[0, 0]))
    intercept_scale = float(np.sqrt(scale_mat[1, 1]))

    # 95% 可信区间（t 分位数；scipy 不可用时近似）
    t975, approx = _t_ppf(0.975, nu)
    slope_ci = (slope_mean - t975 * slope_scale, slope_mean + t975 * slope_scale)
    intercept_ci = (intercept_mean - t975 * intercept_scale,
                    intercept_mean + t975 * intercept_scale)

    # ── 拟合质量（用后验均值预测）──
    y_pred = float(beta_n[0]) * x + float(beta_n[1])
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(ss_res / n))
    mae = float(np.mean(np.abs(y - y_pred)))

    # ── Bayes Factor vs 常数模型 ──
    bf_res = _bf_vs_constant_internal(X, y, prior, beta0, V0, a0, b0)

    result: Dict[str, Any] = {
        "n": int(n),
        "slope": {"mean": slope_mean, "std": slope_scale,
                  "ci_low": slope_ci[0], "ci_high": slope_ci[1]},
        "intercept": {"mean": intercept_mean, "std": intercept_scale,
                      "ci_low": intercept_ci[0], "ci_high": intercept_ci[1]},
        "sigma2": {"mean": sigma2_mean, "std": float(np.sqrt(sigma2_var))
                   if np.isfinite(sigma2_var) else None},
        "r2": r2, "rmse": rmse, "mae": mae,
        "nu": float(nu),
        "beta_mean": beta_n.tolist(),
        "beta_cov": scale_mat.tolist(),
        "approximation": bool(approx),
        **bf_res,
    }

    # ── 后验预测 ──
    if x_new is not None:
        x_new_arr = np.atleast_1d(np.asarray(x_new, dtype=float))
        pred_mean = x_new_arr * slope_mean + intercept_mean
        pred_scale = np.sqrt(
            (bn / an) * (1.0 + np.sum(x_new_arr ** 2) * Vn[0, 0]
                         + 2.0 * x_new_arr * Vn[0, 1] + Vn[1, 1])
        )
        lo = pred_mean - t975 * pred_scale
        hi = pred_mean + t975 * pred_scale
        result["prediction"] = {
            "x": x_new_arr.tolist(),
            "mean": pred_mean.tolist(),
            "ci_low": lo.tolist(),
            "ci_high": hi.tolist(),
        }
    return result


def _bf_vs_constant_internal(X, y, prior, beta0, V0, a0, b0) -> Dict[str, Any]:
    """线性模型 vs 常数模型的 Bayes Factor（内部实现）。"""
    n = y.size
    log_ml_linear = _log_marginal_likelihood(X, y, prior)
    # 常数模型：X0 = 1，先验截距 N(mean(y), σ²·(20·y_scale)²)
    y_scale = float(np.std(y)) or 1.0
    c_prior = {
        "beta0": np.array([float(np.mean(y))]),
        "V0": np.array([[float((20.0 * y_scale) ** 2)]]),
        "a0": a0,
        "b0": b0,
    }
    X0 = np.ones((n, 1))
    log_ml_const = _log_marginal_likelihood(X0, y, c_prior)
    log_bf = log_ml_linear - log_ml_const
    # 数值保护：BF 太大/太小直接饱和到表示范围
    if log_bf > 100:
        bf = float("inf")
    elif log_bf < -100:
        bf = 0.0
    else:
        bf = float(np.exp(log_bf))
    # 定性解释（Kass & Raftery 1995 的档位）
    if log_bf >= 0:
        if log_bf >= 3.0:
            evidence = "强支持线性关系（BF ≥ 20）"
        elif log_bf >= 1.0:
            evidence = "中等支持线性关系（3 ≤ BF < 20）"
        else:
            evidence = "弱支持线性关系（1 ≤ BF < 3）"
    else:
        if log_bf <= -3.0:
            evidence = "强支持常数模型（BF ≤ 1/20）"
        elif log_bf <= -1.0:
            evidence = "中等支持常数模型（BF ≤ 1/3）"
        else:
            evidence = "弱支持常数模型（BF < 1）"
    return {
        "bayes_factor_vs_constant": bf,
        "log_bf_vs_constant": float(log_bf),
        "bf_evidence": evidence,
    }


def bayes_factor_vs_constant(x, y,
                             prior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """公开入口：线性模型 vs 常数模型的 Bayes Factor。

    返回 {bayes_factor_vs_constant, log_bf_vs_constant, bf_evidence}。
    BF₁₀ > 1 表示数据支持"x 与 y 存在线性关系"；小样本下比
    单纯比较 R² 更稳健（不会因过拟合给出虚假高 R²）。
    """
    x = _as_1d_array(x, "x")
    y = _as_1d_array(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    if x.size < 2:
        raise ValueError("至少需要 2 个数据点")
    prior = prior or _default_prior(x, y)
    X = _design_matrix(x)
    return _bf_vs_constant_internal(
        X, y, prior,
        np.asarray(prior["beta0"], dtype=float),
        np.asarray(prior["V0"], dtype=float),
        float(prior["a0"]), float(prior["b0"]),
    )


# ═══════════════════════════════════════════════════════════════
# 合成数据自检
# ═══════════════════════════════════════════════════════════════

def _self_check() -> int:
    """用已知参数的合成数据验证贝叶斯后验，返回进程退出码（0 成功 / 1 失败）。"""
    rng = np.random.default_rng(42)
    failures: list = []

    def _check(cond, msg):
        if cond:
            print(f"  ✓ {msg}")
        else:
            failures.append(msg)
            print(f"  ✗ FAIL: {msg}")

    # ── 1. 中等样本：n=8，真值 slope=0.5, intercept=2.0 ──
    x8 = np.linspace(0.0, 10.0, 8)
    y8 = 2.0 + 0.5 * x8 + rng.normal(0.0, 0.8, x8.size)
    r8 = fit_bayesian_linear(x8, y8)
    slope_m, lo8, hi8 = (r8["slope"]["mean"],
                         r8["slope"]["ci_low"], r8["slope"]["ci_high"])
    print(f"[self-check] n=8: slope={slope_m:.4f} (95% CI [{lo8:.4f},{hi8:.4f}]), "
          f"BF={r8['bayes_factor_vs_constant']:.3g}")
    _check(abs(slope_m - 0.5) < 0.5, "n=8 斜率后验均值在真值 0.5 附近（±0.5）")
    _check(lo8 <= 0.5 <= hi8, "n=8 斜率 95% 可信区间覆盖真值 0.5")
    _check(r8["bayes_factor_vs_constant"] > 3.0,
           "n=8 线性关系的 Bayes Factor > 3（中等以上证据）")
    _check(0.0 <= r8["r2"] <= 1.0, "n=8 R² 落在 [0,1]")

    # ── 2. 小样本：n=3（OLS 二次不可行 / 过拟合场景）仍可运行 ──
    x3 = np.array([1.0, 3.0, 5.0])
    y3 = 2.0 + 0.5 * x3 + rng.normal(0.0, 0.8, 3)
    r3 = fit_bayesian_linear(x3, y3)
    print(f"[self-check] n=3: slope={r3['slope']['mean']:.4f} "
          f"(95% CI [{r3['slope']['ci_low']:.4f},{r3['slope']['ci_high']:.4f}]), "
          f"BF={r3['bayes_factor_vs_constant']:.3g}")
    _check(np.isfinite(r3["slope"]["mean"]) and
           np.isfinite(r3["slope"]["ci_low"]), "n=3 后验统计量全部有限")
    # 小样本不确定性应大于中等样本
    _check((r3["slope"]["ci_high"] - r3["slope"]["ci_low"]) >
           (r8["slope"]["ci_high"] - r8["slope"]["ci_low"]) * 0.9,
           "n=3 的斜率可信区间宽度 ≥ n=8 的 0.9 倍（小样本不确定性更大）")

    # ── 3. 预测区间：x_new 处预测均值接近真实函数 ──
    rp = fit_bayesian_linear(x8, y8, x_new=np.array([4.0]))
    pred_m = rp["prediction"]["mean"][0]
    pred_lo = rp["prediction"]["ci_low"][0]
    pred_hi = rp["prediction"]["ci_high"][0]
    print(f"[self-check] 预测 x=4.0: mean={pred_m:.4f} "
          f"(95% PI [{pred_lo:.4f},{pred_hi:.4f}]), 真值=4.0")
    _check(abs(pred_m - 4.0) < 1.0, "x=4.0 预测均值接近真值 4.0（±1）")
    _check(pred_lo <= 4.0 <= pred_hi, "x=4.0 95% 预测区间覆盖真值 4.0")

    # ── 4. 与 OLS 一致性：弱先验下后验均值 ≈ OLS 解 ──
    c = np.polyfit(x8, y8, 1)
    _check(abs(r8["slope"]["mean"] - c[0]) < 0.3 and
           abs(r8["intercept"]["mean"] - c[1]) < 0.5,
           "弱先验下贝叶斯斜率/截距后验均值与 OLS 解接近")

    # ── 5. 确定性：相同输入结果一致 ──
    r8b = fit_bayesian_linear(x8, y8)
    _check(r8b["slope"]["mean"] == r8["slope"]["mean"] and
           r8b["bayes_factor_vs_constant"] == r8["bayes_factor_vs_constant"],
           "确定性：相同输入给出相同后验结果")

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("PASS: 贝叶斯线性回归后验、可信区间、Bayes Factor、预测区间全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(_self_check())
