# -*- coding: utf-8 -*-
"""
回归诊断与稳健性验证 — Regression Diagnostics for GOAI 文献调研 Agent
======================================================================
落实 1.md（teacherB#6）的"对 H0 进行真正的模型验证"建议。文献提取的
数据点少、且常来自同一篇论文（同源相关点），普通随机划分会数据泄漏。
本模块提供一套不依赖第三方统计库的稳健性指标，供 `run_model_comparison`
等工具调用：

  - adjusted_r2        : 调整 R²（惩罚参数数 k）
  - mae                : 平均绝对误差
  - bootstrap_ci       : 自助法区间（R²/RMSE/MAE/斜率，对任意拟合函数）
  - leave_one_out_cv   : 逐点留一交叉验证（OOF 预测）
  - group_cv           : 按组留一交叉验证（leave-one-group-out，
                         近似 leave-one-paper-out：组=文献块/论文来源）
  - cooks_distance     : 线性拟合的 Cook's distance（高杠杆/强影响点诊断）
  - regression_diagnostics : 汇总入口，一次给出全部指标

fit_fn 约定（bootstrap / CV 通用）：
    fit_fn(X_train, y_train) -> callable(X_test) -> y_pred
内置工厂 make_poly_fit(deg) 提供多项式拟合；也可传入自定义拟合器
（如符号回归或贝叶斯回归的拟合-预测闭包）。

依赖策略：仅标准库 + numpy（bootstrap 用 numpy 随机数，seed 可复现）。
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np


__all__ = [
    "adjusted_r2",
    "mae",
    "make_poly_fit",
    "bootstrap_ci",
    "leave_one_out_cv",
    "group_cv",
    "cooks_distance",
    "regression_diagnostics",
    "_self_check",
]


def _as_1d(values: Any, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        raise ValueError(f"{name} 为空")
    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError(f"{name} 包含 NaN/Inf")
    return arr


def _r2(y: np.ndarray, y_pred: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot < 1e-15:
        return 1.0 if ss_res < 1e-15 else 0.0
    return 1.0 - ss_res / ss_tot


def _rmse(y: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - np.asarray(y_pred)) ** 2)))


# ═══════════════════════════════════════════════════════════════
# 基础统计量
# ═══════════════════════════════════════════════════════════════

def adjusted_r2(r2: float, n: int, k: int) -> float:
    """调整 R²：1 − (1−R²)·(n−1)/(n−k−1)；惩罚参数数，小样本下防过拟合假象。

    n − k − 1 ≤ 0 时返回 NaN（无意义）。
    """
    denom = n - k - 1
    if denom <= 0:
        return float("nan")
    return float(1.0 - (1.0 - r2) * (n - 1) / denom)


def mae(y, y_pred) -> float:
    """平均绝对误差。"""
    y = np.asarray(y, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if y.size != y_pred.size:
        raise ValueError("y 与 y_pred 长度必须一致")
    return float(np.mean(np.abs(y - y_pred)))


# ═══════════════════════════════════════════════════════════════
# 拟合器工厂
# ═══════════════════════════════════════════════════════════════

def make_poly_fit(deg: int) -> Callable:
    """多项式拟合器工厂：返回 fit_fn(X_train, y_train) -> predict_fn(X_test)。

    用 numpy.polyfit（deg 阶），退化数据自动失败返回 None 的 predict。
    """
    def fit_fn(x_train, y_train):
        x_train = np.asarray(x_train, dtype=float)
        y_train = np.asarray(y_train, dtype=float)
        try:
            coef = np.polyfit(x_train, y_train, deg)
        except Exception:
            return None
        def predict_fn(x_test):
            return np.polyval(coef, np.asarray(x_test, dtype=float))
        return predict_fn
    return fit_fn


# ═══════════════════════════════════════════════════════════════
# 自助法区间
# ═══════════════════════════════════════════════════════════════

def bootstrap_ci(x, y, fit_fn: Callable, n_boot: int = 500,
                 alpha: float = 0.05, seed: int = 42,
                 metrics: Sequence[str] = ("r2", "rmse", "mae"),
                 slope_from_coef: bool = True) -> Dict[str, Any]:
    """bootstrap 区间：对 (x, y) 有放回重采样，反复拟合-评估。

    参数:
        fit_fn: 拟合器，约定见模块 docstring
        n_boot: 重采样次数（小样本建议 ≥ 500）
        alpha: 双侧分位（默认 0.05 → 95% 区间）
        metrics: 需要输出区间的指标（r2 / rmse / mae / slope）
        slope_from_coef: 线性拟合时额外输出斜率 bootstrap 区间
            （通过 polyfit 一阶系数估计，不要求 fit_fn 返回系数）

    返回 dict:
        {metric: {mean, std, ci_low, ci_high}, n_boot, n_ok,
         n_failed, seed, approximation}
    """
    x = _as_1d(x, "x")
    y = _as_1d(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    n = x.size
    if n < 3:
        raise ValueError("bootstrap 至少需要 3 个数据点")
    rng = np.random.default_rng(seed)

    out: Dict[str, List[float]] = {m: [] for m in metrics}
    if slope_from_coef:
        out["slope"] = []
    n_ok = 0

    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        # 有放回采样后去重——保留重复以反映采样分布；但若 x 退化则跳过
        xb = x[idx]
        yb = y[idx]
        if len(np.unique(xb)) < 2:
            continue
        predict = None
        try:
            predict = fit_fn(xb, yb)
        except Exception:
            predict = None
        if predict is None:
            continue
        try:
            y_pred = np.asarray(predict(x), dtype=float)
        except Exception:
            continue
        if y_pred.shape != y.shape or not np.all(np.isfinite(y_pred)):
            continue
        n_ok += 1
        if "r2" in out:
            out["r2"].append(_r2(y, y_pred))
        if "rmse" in out:
            out["rmse"].append(_rmse(y, y_pred))
        if "mae" in out:
            out["mae"].append(mae(y, y_pred))
        if "slope" in out:
            try:
                coef = np.polyfit(xb, yb, 1)
                out["slope"].append(float(coef[0]))
            except Exception:
                pass

    if n_ok < max(20, int(n_boot * 0.5)):
        raise ValueError(
            f"bootstrap 有效重采样仅 {n_ok}/{n_boot} 次，拟合器退化严重，"
            "请检查数据或拟合器"
        )

    lo_q = alpha / 2.0
    hi_q = 1.0 - alpha / 2.0
    result: Dict[str, Any] = {
        "n_boot": int(n_boot),
        "n_ok": n_ok,
        "seed": int(seed),
        "approximation": False,
    }
    for m, vals in out.items():
        if not vals:
            continue
        arr = np.asarray(vals, dtype=float)
        result[m] = {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "ci_low": float(np.quantile(arr, lo_q)),
            "ci_high": float(np.quantile(arr, hi_q)),
        }
    return result


# ═══════════════════════════════════════════════════════════════
# 交叉验证
# ═══════════════════════════════════════════════════════════════

def leave_one_out_cv(x, y, fit_fn: Callable) -> Dict[str, Any]:
    """逐点 LOOCV：每次留一个点，其余训练，OOF 预测。

    注意：文献数据点常同源（同一篇论文/同一块），逐点 LOOCV 仍有
    数据泄漏，仅作参考；同源场景应优先使用 group_cv。
    """
    x = _as_1d(x, "x")
    y = _as_1d(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    n = x.size
    if n < 4:
        return {"valid": False, "reason": f"LOOCV 至少需要 4 个点（当前 n={n}）"}
    oof = np.full(n, np.nan, dtype=float)
    n_ok = 0
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        try:
            predict = fit_fn(x[mask], y[mask])
            if predict is None:
                continue
            oof[i] = float(predict(np.array([x[i]]))[0])
            if np.isfinite(oof[i]):
                n_ok += 1
        except Exception:
            continue
    if n_ok < 2:
        return {"valid": False, "reason": f"LOOCV 有效折数不足（{n_ok}/{n}）"}
    valid = np.isfinite(oof)
    yv = y[valid]
    ov = oof[valid]
    return {
        "valid": True,
        "method": "leave_one_out",
        "n_folds": int(n),
        "n_ok": int(n_ok),
        "oof_r2": _r2(yv, ov),
        "oof_rmse": _rmse(yv, ov),
        "oof_mae": float(np.mean(np.abs(yv - ov))),
        "note": "逐点留一（同源点仍可能泄漏，建议结合 group_cv 看）",
    }


def group_cv(x, y, groups, fit_fn: Callable) -> Dict[str, Any]:
    """按组留一交叉验证（leave-one-group-out）。

    组 = 数据点来源（论文/文献块），同一组内的点不跨折泄漏，
    是 teacherB 建议的 leave-one-paper-out CV 的近似实现。

    参数:
        groups: 与 x/y 等长的组标签序列（str/int/...）

    返回 dict:
        {valid, n_groups, n_folds, oof_r2, oof_rmse, oof_mae, per_fold}
    """
    x = _as_1d(x, "x")
    y = _as_1d(y, "y")
    groups = list(groups)
    if len(groups) != x.size:
        raise ValueError("groups 长度必须与 x/y 一致")
    unique_groups = sorted(set(groups), key=lambda g: str(g))
    if len(unique_groups) < 2:
        return {"valid": False,
                "reason": f"只有 {len(unique_groups)} 个组，无法做分组 CV"}
    oof = np.full(x.size, np.nan, dtype=float)
    per_fold: List[Dict[str, Any]] = []
    for g in unique_groups:
        test_mask = np.asarray([gr == g for gr in groups], dtype=bool)
        train_mask = ~test_mask
        if train_mask.sum() < 3 or test_mask.sum() < 1:
            continue
        if len(np.unique(x[train_mask])) < 2:
            continue
        try:
            predict = fit_fn(x[train_mask], y[train_mask])
        except Exception:
            predict = None
        if predict is None:
            continue
        try:
            oof[test_mask] = np.asarray(predict(x[test_mask]), dtype=float)
        except Exception:
            continue
        if np.all(np.isfinite(oof[test_mask])):
            per_fold.append({
                "group": str(g),
                "n_train": int(train_mask.sum()),
                "n_test": int(test_mask.sum()),
            })
    valid = np.isfinite(oof)
    if valid.sum() < 2:
        return {"valid": False,
                "reason": f"分组 CV 有效预测点不足（{int(valid.sum())}/{x.size}）"}
    yv = y[valid]
    ov = oof[valid]
    return {
        "valid": True,
        "method": "leave_one_group_out",
        "n_groups": int(len(unique_groups)),
        "n_folds": int(len(per_fold)),
        "n_predicted": int(valid.sum()),
        "oof_r2": _r2(yv, ov),
        "oof_rmse": _rmse(yv, ov),
        "oof_mae": float(np.mean(np.abs(yv - ov))),
        "per_fold": per_fold,
        "note": "组=数据点来源（近似 leave-one-paper-out，同组不跨折泄漏）",
    }


# ═══════════════════════════════════════════════════════════════
# 影响点诊断（线性拟合）
# ═══════════════════════════════════════════════════════════════

def cooks_distance(x, y) -> Dict[str, Any]:
    """线性拟合的 Cook's distance：识别高杠杆/强影响点。

    Cook's distance 阈值经验取 4/n；返回最大 Cook 值、超过阈值的点索引、
    以及杠杆值 h_ii（帽子矩阵对角元）。

    要求 x 至少 3 个不同取值。
    """
    x = _as_1d(x, "x")
    y = _as_1d(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    n = x.size
    if n < 4 or len(np.unique(x)) < 3:
        return {"valid": False, "reason": "Cook's distance 至少需要 4 个点且 3 个不同 x"}
    A = np.column_stack([x, np.ones(n)])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    # 帽子矩阵 H = A (AᵀA)⁻¹ Aᵀ；杠杆 h_ii = 对角元
    try:
        ATA_inv = np.linalg.inv(A.T @ A)
        h = np.einsum("ij,jk,ik->i", A, ATA_inv, A)
    except Exception:
        h = np.full(n, 2.0 / n)
    sse = float(np.sum(resid ** 2))
    if sse <= 0 or n <= 2:
        p = 2
        mse = 1.0
    else:
        p = 2
        mse = sse / (n - p)
    cooks = resid ** 2 / (p * mse) * h / (1.0 - h + 1e-12)
    threshold = 4.0 / n
    idx = np.where(cooks > threshold)[0]
    return {
        "valid": True,
        "n": int(n),
        "max_cooks": float(np.max(cooks)) if cooks.size else 0.0,
        "max_cooks_index": int(np.argmax(cooks)) if cooks.size else -1,
        "threshold": float(threshold),
        "high_influence_indices": [int(i) for i in idx],
        "high_influence_count": int(idx.size),
        "leverage_max": float(np.max(h)) if h.size else 0.0,
        "note": "阈值经验取 4/n；高影响点可能主导线性回归，需检查其来源",
    }


# ═══════════════════════════════════════════════════════════════
# 汇总入口
# ═══════════════════════════════════════════════════════════════

def regression_diagnostics(x, y, groups: Optional[Sequence] = None,
                           fit_fn: Optional[Callable] = None,
                           n_boot: int = 500, seed: int = 42,
                           deg: int = 1) -> Dict[str, Any]:
    """回归稳健性验证汇总：一次给出全部 teacherB#6 指标。

    参数:
        groups: 可选组标签（论文/文献块来源），给则跑 group_cv
        fit_fn: 可选拟合器；缺省用 make_poly_fit(deg)（deg=1 线性）
        n_boot: bootstrap 次数
        deg: 缺省拟合器多项式阶数

    返回 dict：{n, fit, ols{...}, adjusted, bootstrap, loocv,
                group_cv(若 groups), cooks(若可用)}
    """
    x = _as_1d(x, "x")
    y = _as_1d(y, "y")
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致")
    n = x.size
    fit_fn = fit_fn or make_poly_fit(deg)

    # OLS 参考（线性）
    ols = {}
    if n >= 3 and len(np.unique(x)) >= 2:
        coef, *_ = np.linalg.lstsq(np.column_stack([x, np.ones(n)]), y, rcond=None)
        y_pred = coef[0] * x + coef[1]
        r2_ols = _r2(y, y_pred)
        ols = {
            "r2": r2_ols,
            "adjusted_r2": adjusted_r2(r2_ols, n, 2),
            "rmse": _rmse(y, y_pred),
            "mae": mae(y, y_pred),
            "slope": float(coef[0]),
            "intercept": float(coef[1]),
        }

    result: Dict[str, Any] = {
        "n": int(n),
        "fit": f"poly{deg}",
        "ols": ols,
    }

    # bootstrap（n>=3 且至少 2 个不同 x 才可做）
    if n >= 3 and len(np.unique(x)) >= 2:
        try:
            result["bootstrap"] = bootstrap_ci(
                x, y, fit_fn, n_boot=n_boot, seed=seed)
        except ValueError as e:
            result["bootstrap"] = {"valid": False, "reason": str(e)}

    # LOOCV
    result["loocv"] = leave_one_out_cv(x, y, fit_fn)

    # 分组 CV（若提供 groups）
    if groups is not None:
        result["group_cv"] = group_cv(x, y, groups, fit_fn)
    else:
        result["group_cv"] = {"valid": False,
                              "reason": "未提供数据点来源分组，跳过（同源数据建议提供）"}

    # Cook's distance
    result["cooks"] = cooks_distance(x, y)
    return result


# ═══════════════════════════════════════════════════════════════
# 合成数据自检
# ═══════════════════════════════════════════════════════════════

def _self_check() -> int:
    """用已知参数的合成数据验证诊断指标，返回进程退出码（0 成功 / 1 失败）。"""
    rng = np.random.default_rng(7)
    failures: list = []

    def _check(cond, msg):
        if cond:
            print(f"  ✓ {msg}")
        else:
            failures.append(msg)
            print(f"  ✗ FAIL: {msg}")

    # ── 1. 基础统计量 ──
    n = 12
    x = np.linspace(0.0, 10.0, n)
    y = 1.0 + 2.0 * x + rng.normal(0.0, 0.5, n)
    y_pred = 1.0 + 2.0 * x
    r2_lin = _r2(y, y_pred)
    ar2 = adjusted_r2(r2_lin, n, 2)
    print(f"[self-check] 合成: R²={r2_lin:.4f}, adjusted R²={ar2:.4f}, "
          f"MAE={mae(y, y_pred):.4f}")
    _check(ar2 <= r2_lin + 1e-12, "adjusted R² ≤ R²（参数惩罚生效）")
    _check(0.0 < mae(y, y_pred) < 0.5, "MAE 落在合理范围（噪声水平内）")

    # ── 2. bootstrap 区间覆盖真值 ──
    fit_lin = make_poly_fit(1)
    bt = bootstrap_ci(x, y, fit_lin, n_boot=300, seed=42)
    slope_lo, slope_hi = bt["slope"]["ci_low"], bt["slope"]["ci_high"]
    r2_lo, r2_hi = bt["r2"]["ci_low"], bt["r2"]["ci_high"]
    print(f"[self-check] bootstrap: slope 95% CI=[{slope_lo:.3f},{slope_hi:.3f}] "
          f"(真值 2.0), R² 95% CI=[{r2_lo:.3f},{r2_hi:.3f}]")
    _check(slope_lo <= 2.0 <= slope_hi, "bootstrap 斜率 95% 区间覆盖真值 2.0")
    _check(r2_lo > 0.5, "bootstrap R² 95% 区间下界 > 0.5（线性关系显著）")

    # ── 3. LOOCV / 分组 CV ──
    groups = [f"p{i % 3}" for i in range(n)]  # 3 组，同组点共享"论文"
    gc = group_cv(x, y, groups, fit_lin)
    lc = leave_one_out_cv(x, y, fit_lin)
    print(f"[self-check] LOOCV: oof R²={lc.get('oof_r2', float('nan')):.3f}; "
          f"groupCV: {gc.get('n_folds', 0)} 折, oof R²={gc.get('oof_r2', float('nan')):.3f}")
    _check(gc.get("valid") and gc["oof_r2"] > 0.5, "分组 CV OOF R² > 0.5")
    _check(lc.get("valid") and lc["oof_r2"] > 0.5, "LOOCV OOF R² > 0.5")

    # ── 4. Cook's distance 能识别离群点 ──
    x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    y2 = 1.0 + 2.0 * x2
    y2 = y2 + rng.normal(0.0, 0.1, x2.size)
    y2[9] = 30.0  # 人为高杠杆离群点（x 最大处 y 大幅偏离）
    cd = cooks_distance(x2, y2)
    print(f"[self-check] Cook's distance: max={cd.get('max_cooks', 0):.2f} "
          f"@idx={cd.get('max_cooks_index')}, 高影响点={cd.get('high_influence_indices')}")
    _check(cd.get("valid") and cd["high_influence_count"] >= 1,
           "Cook's distance 检出至少 1 个高影响点")
    _check(cd["max_cooks_index"] == 9, "最大 Cook's distance 落在人为离群点（idx=9）")

    # ── 5. 汇总入口 ──
    diag = regression_diagnostics(x, y, groups=groups, n_boot=200, seed=1)
    _check("bootstrap" in diag and "group_cv" in diag and "loocv" in diag
           and "cooks" in diag and "ols" in diag,
           "regression_diagnostics 汇总包含全部子模块")

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("PASS: adjusted R² / MAE / bootstrap / LOOCV / 分组 CV / Cook's distance 全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(_self_check())
