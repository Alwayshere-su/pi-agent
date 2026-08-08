# -*- coding: utf-8 -*-
"""
经典模型拟合模块 — Classical Model Fitting for GOAI 文献调研 Agent
====================================================================
为路线 A（构效关系发现）提供"前人 / 经典公式"的可复现基线拟合，
供 `run_model_comparison` 工具（另一 Agent）import 调用：新发现的规律
必须在统计指标上优于这些经典模型（更高 R² / 更低 RMSE），并能解释
旧模型为何失效。本模块即负责给出经典基线本身。

与赛题要求的关系（补充.md 路线 A 验证标准）：
  - "新生成的规律必须在统计指标上优于前人成果（例如更高的 R² 或更低的
    MSE），且能解释为何旧模型会失效。"
  - Slack Model 是 70 年代提出的带隙-温度经验公式（Einstein 声子模型），
    仅适用高温、简单晶体等场景。本模块把 Slack 公式拟合回真实数据，
    得到经典基线 {R², RMSE}，供新模型做统计对比。
  - Vegard 定律（晶格常数随组分线性变化）是 1921 年经验法则，合金常因
    bowing 效应偏离线性；本模块给出线性基线，用于量化偏差。

模型公式（Slack / Varshni-Einstein）：
    E_g(T) = E_g0 - S * theta * [coth(theta / (2T)) - 1]
    其中 hbar_omega = k_B * theta（theta 为爱因斯坦温度，单位 K，T 为开尔文），
    S 为无量纲耦合常数，E_g0 为 0K 外推带隙（单位与 Eg 输入一致，通常 eV）。
    数值等价形式：coth(theta/(2T)) - 1 = 2 / (exp(theta/T) - 1)，
    本实现用 expm1 保证小 T / 大 theta 下的数值稳定。

依赖策略：仅强制要求标准库 + numpy；scipy.optimize.curve_fit 为可选增强
（requirements.txt 已含 scipy>=1.9）。若 scipy import 失败，自动退化为
纯 numpy 网格搜索兜底，保证功能可用。
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional, Tuple

import numpy as np

# 玻尔兹曼常数（eV/K）：Slack 模型中把爱因斯坦温度 theta(K) 换算为能量的系数
_K_B_EV = 8.617333262e-5

try:  # scipy 为可选增强；失败则走纯 numpy 网格搜索兜底
    from scipy.optimize import curve_fit as _curve_fit
    _HAS_SCIPY = True
except Exception:  # pragma: no cover - 环境无 scipy 时的兜底路径
    _curve_fit = None
    _HAS_SCIPY = False


__all__ = [
    "slack_model",
    "fit_slack_model",
    "fit_vegard",
    "fit_linear",
    "fit_quadratic",
    "fit_power",
    "fit_classical_baseline",
]

# curve_fit 多起点初始化（S0, theta0），提高非凸拟合收敛概率
_SLACK_STARTS: Tuple[Tuple[float, float], ...] = (
    (3.0, 300.0),
    (2.0, 200.0),
    (4.5, 500.0),
    (1.2, 120.0),
    (2.5, 800.0),
)


# ═══════════════════════════════════════════════════════════════
# 内部工具：R² / RMSE
# ═══════════════════════════════════════════════════════════════

def _r2(y: np.ndarray, y_pred: np.ndarray) -> float:
    """决定系数 R² = 1 - SS_res/SS_tot；y 恒定时退化处理。"""
    y = np.asarray(y, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot < 1e-15:
        return 1.0 if ss_res < 1e-15 else 0.0
    return 1.0 - ss_res / ss_tot


def _rmse(y: np.ndarray, y_pred: np.ndarray) -> float:
    """均方根误差 RMSE。"""
    y = np.asarray(y, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y - y_pred) ** 2)))


def _as_1d_array(values: Any, name: str) -> np.ndarray:
    """把输入转成 float 一维数组，并做基本合法性检查。"""
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        raise ValueError(f"{name} 为空")
    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError(f"{name} 包含 NaN/Inf")
    return arr


# ═══════════════════════════════════════════════════════════════
# 1. Slack 带隙-温度模型
# ═══════════════════════════════════════════════════════════════

def _slack_coth_term(theta: float, T: np.ndarray) -> np.ndarray:
    """数值稳定的 coth(theta/(2T)) - 1 = 2 / (exp(theta/T) - 1)。

    推导：coth(x)-1 = (e^{2x}+1)/(e^{2x}-1) - 1 = 2/(e^{2x}-1)，
    令 x = theta/(2T) 即得 2/(exp(theta/T)-1)。
    expm1 在 theta/T -> 0（高温）时给出精确小量，避免舍入误差；
    theta/T 过大时结果物理上为 0，直接截断避免 exp 溢出。
    """
    z = theta / np.asarray(T, dtype=float)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        term = np.where(z < 700.0, 2.0 / np.expm1(z), 0.0)
    return term


def slack_model(T, E_g0: float, S: float, theta: float) -> np.ndarray:
    """Slack 带隙-温度模型：E_g(T) = E_g0 - S*ħω*[coth(ħω/(2k_B·T)) - 1]。

    参数：
      E_g0  — 0K 外推带隙（eV，与输入 Eg 同单位）
      S     — 无量纲耦合常数（Slack 参数）
      theta — 爱因斯坦温度（K），满足 ħω = k_B·theta
    实现：coth(ħω/(2k_B·T))-1 = coth(theta/(2T))-1 = 2/(exp(theta/T)-1)，
    因此 E_g(T) = E_g0 - S·k_B·theta·[2/(exp(theta/T)-1)]，
    其中 k_B = 8.617333262e-5 eV/K（把 theta 从 K 换算为能量）。
    渐近行为：T->0 时 E_g -> E_g0；高温时 E_g -> E_g0 - 2·S·k_B·T + S·k_B·theta（线性衰减）。
    """
    T = np.asarray(T, dtype=float)
    return E_g0 - S * _K_B_EV * theta * _slack_coth_term(theta, T)


def _slack_grid_fit(T: np.ndarray, Eg: np.ndarray) -> Dict[str, Any]:
    """纯 numpy 网格搜索兜底：遍历 (S, theta)，E_g0 解析最优。"""
    theta_grid = np.logspace(np.log10(10.0), np.log10(5000.0), 120)
    S_grid = np.linspace(0.1, 20.0, 120)
    best: Optional[Tuple[float, float, float, float]] = None
    for S in S_grid:
        for th in theta_grid:
            d = _slack_coth_term(th, T)
            E0 = float(np.mean(Eg + S * _K_B_EV * th * d))  # E_g0 闭式最优
            sse = float(np.sum((Eg - (E0 - S * _K_B_EV * th * d)) ** 2))
            if best is None or sse < best[0]:
                best = (sse, E0, S, th)
    assert best is not None
    _sse, E0, S, th = best
    y_pred = E0 - S * _K_B_EV * th * _slack_coth_term(th, T)
    return {
        "E_g0": E0,
        "S": S,
        "theta": th,
        "r2": _r2(Eg, y_pred),
        "rmse": _rmse(Eg, y_pred),
        "converged": False,
        "method": "numpy 网格搜索（scipy 不可用或 curve_fit 失败）",
    }


def fit_slack_model(T_points, Eg_points) -> Dict[str, Any]:
    """拟合 Slack 带隙-温度模型，返回参数 + R²/RMSE + 收敛标志。

    优先使用 scipy.optimize.curve_fit（多起点，取 SSE 最小解）；
    若 scipy 不可用或全部起点失败，退化为纯 numpy 网格搜索。
    T 必须为开尔文（正数）。

    返回 dict：
      {E_g0, S, theta, r2, rmse, converged, method}
    """
    T = _as_1d_array(T_points, "T")
    Eg = _as_1d_array(Eg_points, "Eg")
    if T.size != Eg.size:
        raise ValueError("T 与 Eg 长度必须一致")
    if T.size < 4:
        raise ValueError("Slack 模型拟合至少需要 4 个数据点")
    if np.any(T <= 0):
        raise ValueError("T 必须为正（单位：开尔文）")

    E_g0_est = float(np.max(Eg))
    lower = (0.0, 1e-9, 5.0)
    upper = (max(50.0, 10.0 * E_g0_est), 100.0, 10000.0)

    if _HAS_SCIPY and _curve_fit is not None:
        best: Optional[Dict[str, Any]] = None
        best_sse = float("inf")
        for S0, theta0 in _SLACK_STARTS:
            try:
                popt, _ = _curve_fit(
                    slack_model, T, Eg,
                    p0=(E_g0_est, S0, theta0),
                    bounds=(lower, upper),
                    maxfev=20000,
                )
                E_g0, S, theta = (float(v) for v in popt)
                if not (np.isfinite(E_g0) and S > 0 and theta > 0):
                    continue
                y_pred = slack_model(T, E_g0, S, theta)
                sse = float(np.sum((Eg - y_pred) ** 2))
                if sse < best_sse:
                    best_sse = sse
                    best = {
                        "E_g0": E_g0,
                        "S": S,
                        "theta": theta,
                        "r2": _r2(Eg, y_pred),
                        "rmse": _rmse(Eg, y_pred),
                        "converged": True,
                        "method": "scipy.optimize.curve_fit（多起点，最优解）",
                    }
            except Exception:
                continue  # 该起点失败，尝试下一个
        if best is not None:
            return best

    # 兜底：纯 numpy 网格搜索
    return _slack_grid_fit(T, Eg)


# ═══════════════════════════════════════════════════════════════
# 2. Vegard 定律 / 通用线性、二次、幂律拟合
# ═══════════════════════════════════════════════════════════════

def fit_linear(x, y) -> Tuple[float, float, float]:
    """最小二乘线性拟合 y = intercept + slope*x，返回 (slope, intercept, R²)。"""
    x = _as_1d_array(x, "x")
    y = _as_1d_array(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    if x.size < 2:
        raise ValueError("线性拟合至少需要 2 个数据点")
    A = np.vstack([x, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    slope, intercept = float(coef[0]), float(coef[1])
    y_pred = intercept + slope * x
    return slope, intercept, _r2(y, y_pred)


def fit_vegard(x, y) -> Tuple[float, float, float]:
    """Vegard 定律拟合：晶格常数 a(x) = a0 + k*x（x 为组分，0~1）。

    返回 (slope, intercept, R²)。Vegard 定律（1921 年经验法则）假定合金
    晶格常数随组分线性内插；真实合金常有 bowing（二次）偏离，此时 R² 会
    显著低于 1，正是"旧模型失效"的量化证据。
    """
    return fit_linear(x, y)


def fit_quadratic(x, y) -> Tuple[Dict[str, float], float, float]:
    """二次多项式拟合 y = a + b*x + c*x²，返回 (params, R², RMSE)。"""
    x = _as_1d_array(x, "x")
    y = _as_1d_array(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    if x.size < 3:
        raise ValueError("二次拟合至少需要 3 个数据点")
    A = np.vstack([x ** 2, x, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    c, b, a = (float(v) for v in coef)
    y_pred = a + b * x + c * x ** 2
    return {"a": a, "b": b, "c": c}, _r2(y, y_pred), _rmse(y, y_pred)


def fit_power(x, y) -> Tuple[Dict[str, float], float, float, float]:
    """幂律拟合 y = a*x^b（log-log 线性回归）。

    返回 (params, R²_original, RMSE_original, R²_loglog)：
    主报告指标（R²/RMSE）在原始空间计算，与其它模型公平对比；
    R²_loglog 反映 log-log 空间线性拟合质量。
    要求 x>0 且 y>0（物理上幂律常见于尺寸-性能关系，如强度-晶粒尺寸）。
    """
    x = _as_1d_array(x, "x")
    y = _as_1d_array(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    if np.any(x <= 0) or np.any(y <= 0):
        raise ValueError("power 模型要求 x>0 且 y>0（需做 log-log 变换）")
    slope, intercept, r2_log = fit_linear(np.log(x), np.log(y))
    a, b = float(np.exp(intercept)), slope
    y_pred = a * x ** b
    return (
        {"a": a, "b": b},
        _r2(y, y_pred),
        _rmse(y, y_pred),
        r2_log,
    )


# ═══════════════════════════════════════════════════════════════
# 3. 统一经典基线入口
# ═══════════════════════════════════════════════════════════════

def fit_classical_baseline(model_name: str, X, y) -> Dict[str, Any]:
    """统一经典模型拟合入口，返回统一 dict。

    支持 model_name：
      "slack"     — E_g = E_g0 - S*theta*[coth(theta/(2T)) - 1]（X = T 开尔文，y = 带隙）
      "vegard"    — 线性 y = intercept + slope*x（X = 组分，y = 晶格常数）
      "linear"    — 通用线性 y = intercept + slope*x
      "quadratic" — 二次 y = a + b*x + c*x²
      "power"     — 幂律 y = a*x^b（log-log 线性拟合）

    返回 dict：{model, params, r2, rmse, n, notes}
    """
    model = str(model_name).strip().lower()
    X = _as_1d_array(X, "X")
    y = _as_1d_array(y, "y")
    if X.size != y.size:
        raise ValueError("X 与 y 长度必须一致")
    n = X.size

    if model == "slack":
        res = fit_slack_model(X, y)
        params: Dict[str, Any] = {
            "E_g0": res["E_g0"],   # 0K 外推带隙（eV）
            "S": res["S"],         # 无量纲耦合常数
            "theta": res["theta"], # 爱因斯坦温度（K），hbar_omega = k_B*theta
            "converged": res["converged"],
            "method": res["method"],
        }
        notes = (
            "Slack/Varshni-Einstein 经验模型（70 年代）：E_g(T)=E_g0-S*theta*[coth(theta/(2T))-1]。"
            "局限：假设单一 Einstein 声子模，通常仅高温/简单晶体适用；"
            "若对非谐声子、多支声子或低温数据拟合失败，即为旧模型失效场景，"
            "可与新规律做统计对比（R²/RMSE）。T 单位为开尔文。"
        )
        return {"model": model, "params": params, "r2": res["r2"],
                "rmse": res["rmse"], "n": n, "notes": notes}

    if model in ("vegard", "linear"):
        slope, intercept, r2 = fit_linear(X, y)
        y_pred = intercept + slope * X
        params = {"slope": slope, "intercept": intercept}
        if model == "vegard":
            notes = (
                "Vegard 定律（1921 年经验法则）：合金晶格常数随组分 x 线性内插 "
                "a(x)=a0+k*x。真实合金常因 bowing 效应二次偏离，R²<1 即为失效证据；"
                "bowing 参数可由 quadratic 拟合的 c 系数给出（-4*c 为 bowing 系数）。"
            )
        else:
            notes = "通用最小二乘线性模型 y = intercept + slope*x。"
        return {"model": model, "params": params, "r2": r2,
                "rmse": _rmse(y, y_pred), "n": n, "notes": notes}

    if model == "quadratic":
        params, r2, rmse = fit_quadratic(X, y)
        notes = (
            "二次多项式 y = a + b*x + c*x²（如 Vegard 定律的 bowing 修正，"
            "bowing 系数 = -4c）。仅当残差显著低于线性模型时，才能说明组分非线性效应存在。"
        )
        return {"model": model, "params": params, "r2": r2,
                "rmse": rmse, "n": n, "notes": notes}

    if model == "power":
        params, r2, rmse, r2_log = fit_power(X, y)
        notes = (
            f"幂律 y = a*x^b（log-log 线性回归）；log-log 空间 R²={r2_log:.4f}，"
            "主报告 R²/RMSE 在原始空间计算以与其他模型公平对比。"
        )
        return {"model": model, "params": params, "r2": r2,
                "rmse": rmse, "n": n, "notes": notes}

    raise ValueError(
        f"未知模型 '{model_name}'，支持：slack / vegard / linear / quadratic / power"
    )


# ═══════════════════════════════════════════════════════════════
# 4. 合成数据自检
# ═══════════════════════════════════════════════════════════════

def _self_check() -> int:
    """用已知参数的合成数据验证拟合，返回进程退出码（0 成功 / 1 失败）。"""
    rng = np.random.default_rng(42)
    failures: list = []

    # ── Slack 自检 ──
    T = np.linspace(100.0, 800.0, 60)          # 开尔文
    E_g0_true, S_true, theta_true = 2.50, 2.30, 300.0
    Eg = slack_model(T, E_g0_true, S_true, theta_true) + rng.normal(0.0, 0.001, T.size)
    res = fit_slack_model(T, Eg)
    err_E_g0 = abs(res["E_g0"] - E_g0_true) / E_g0_true
    err_S = abs(res["S"] - S_true) / S_true
    err_theta = abs(res["theta"] - theta_true) / theta_true
    print(f"[self-check] Slack: method={res['method']}, R²={res['r2']:.6f}, "
          f"ΔE_g0={err_E_g0 * 100:.2f}%, ΔS={err_S * 100:.2f}%, "
          f"Δtheta={err_theta * 100:.2f}%")
    ok_slack = (res["r2"] > 0.99 and err_E_g0 < 0.05 and err_S < 0.05
                and err_theta < 0.05)
    if not ok_slack:
        failures.append("Slack 参数恢复失败或 R² 不达标")

    # ── Vegard 自检 ──
    x = np.linspace(0.0, 1.0, 11)              # 组分
    slope_true, intercept_true = -0.20, 5.50   # 如 GaAs-InAs 合金晶格常数
    y = intercept_true + slope_true * x + rng.normal(0.0, 0.001, x.size)
    slope, intercept, r2 = fit_vegard(x, y)
    err_slope = abs(slope - slope_true) / abs(slope_true)
    err_intercept = abs(intercept - intercept_true) / abs(intercept_true)
    print(f"[self-check] Vegard: R²={r2:.6f}, slope={slope:.4f} (真值 {slope_true}), "
          f"intercept={intercept:.4f} (真值 {intercept_true})")
    ok_vegard = (r2 > 0.99 and err_slope < 0.05 and err_intercept < 0.05)
    if not ok_vegard:
        failures.append("Vegard 参数恢复失败或 R² 不达标")

    # ── 统一入口冒烟测试（quadratic / power）──
    try:
        q = fit_classical_baseline("quadratic", x, y)
        p = fit_classical_baseline("power", np.linspace(1.0, 5.0, 20),
                                   3.0 * np.linspace(1.0, 5.0, 20) ** 0.7)
        if q["r2"] < 0.99 or p["r2"] < 0.99:
            failures.append("quadratic/power 统一入口冒烟测试 R² 不达标")
    except Exception as exc:  # pragma: no cover
        failures.append(f"统一入口冒烟测试异常: {exc!r}")

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("PASS: Slack 与 Vegard 参数恢复（误差<5%）且 R²>0.99；quadratic/power 冒烟通过。")
    return 0


if __name__ == "__main__":
    # Windows GBK 控制台打印 ²/°C 等 Unicode 会 UnicodeEncodeError：统一 UTF-8 输出
    # （复现命令可跨平台运行，README 附录 B 自检命令依赖此兜底）
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    sys.exit(_self_check())
