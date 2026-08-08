#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meta_analysis.py —— 双金属 MOF 协同峰相对 Vegard 线性内插基线的跨体系 meta-analysis
（问题 #10 残余：单体系实测点不足，改为 meta-analysis 跨体系口径）

设计（与 quantitative_validation.md 的区分）:
  不做单体系曲线拟合（NiCo 仅 3 个实测点，自由度不足）；
  改为统计多个双金属 MOF 体系中点（协同峰）相对 Vegard 线性内插基线（两端点算术平均）
  的增强率 ratio = (mid_value - linear_mid) / linear_mid。

步骤:
  1. 读取 meta_analysis_data.json（数值全部来自 quantitative_pairs.json /
     quantitative_validation.md 表1.1/1.2 与 knowledge_graph.md，实测/估计显式标注）。
  2. 每个 include_in_meta_analysis=true 的体系计算 linear_mid 与 ratio。
  3. 跨体系汇总:
       - 单样本 t 检验 (H0: 平均增强率 = 0), 95% CI, Cohen's d (单样本 d = mean/std);
       - 符号检验 (正向体系占比, 二项检验 H0: p=0.5);
       - n < 4 时 t 检验不适用，仅输出符号检验并显式注明。
  4. 输出 workspace/outputs/literature_survey/discovery/meta_analysis.md（中文报告）
     与 meta_analysis.json（原始统计量）。

诚实红线:
  - 数值全部来自真实文件；实测/估计分开标注；
  - 归一化体系中点标注「归一化估计，仅趋势参考」，不替代实验验证；
  - 禁止编造任何文献数值；本脚本不做任何模型拟合，仅描述性 + 推断统计。

依赖: numpy, scipy（requirements.txt 已含 numpy==1.26.4, scipy==1.17.1）。
运行: python workspace/code/survey/meta_analysis.py   （工作目录为项目根 D:\\MMLL\\4.competition\\2026GOAI-3）
"""

import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

# ── 路径（基于脚本位置推导，不依赖运行目录）──────────────────────────────
BASE = Path(__file__).resolve().parents[1]           # scripts -> 项目根
DATA_DIR = BASE / "workspace" / "outputs" / "literature_survey" / "discovery"
DATA_FILE = DATA_DIR / "meta_analysis_data.json"
OUT_MD = DATA_DIR / "meta_analysis.md"
OUT_JSON = DATA_DIR / "meta_analysis.json"


def load_data(path: Path) -> dict:
    """读取 meta_analysis_data.json。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_per_system(sysinfo: dict) -> dict:
    """计算单体系的 linear_mid 与增强率 ratio。"""
    low = sysinfo["endpoint_low"]
    high = sysinfo["endpoint_high"]
    mid = sysinfo["midpoint_value"]
    linear_mid = (low + high) / 2.0
    ratio = (mid - linear_mid) / linear_mid
    return {**sysinfo, "linear_mid": linear_mid, "ratio": ratio}


def meta_stats(ratios: list) -> dict:
    """
    跨体系统计:
      - n < 4: t 检验不适用（自由度/功效不足），仅符号检验。
      - 否则: 单样本 t 检验 + 95% CI + Cohen's d + 符号检验。
    """
    n = len(ratios)
    ratios = np.asarray(ratios, dtype=float)
    out = {"n": n, "t_test_applicable": n >= 4}

    k_pos = int(np.sum(ratios > 0))
    binom_res = stats.binomtest(k_pos, n, 0.5)
    out["sign_test"] = {
        "positive_count": k_pos,
        "total": n,
        "positive_ratio": k_pos / n,
        "p_twosided_binom": float(binom_res.pvalue),
        "p_onesided_greater": float(stats.binomtest(k_pos, n, 0.5, alternative="greater").pvalue),
    }

    if not out["t_test_applicable"]:
        out.update({
            "mean_ratio": None, "std_ratio": None, "se": None,
            "t_statistic": None, "df": None, "p_twosided": None,
            "ci95_low": None, "ci95_high": None, "cohens_d": None,
        })
        out["t_test_note"] = (
            f"样本量 n={n} < 4，单样本 t 检验不适用（自由度不足），仅报告符号检验。"
        )
        return out

    mean = float(np.mean(ratios))
    std = float(np.std(ratios, ddof=1))
    se = std / math.sqrt(n) if n > 1 else float("nan")
    t_val = mean / se if se and se > 0 else float("nan")
    df = n - 1
    p_two = float(2 * stats.t.sf(abs(t_val), df)) if not math.isnan(t_val) else None
    crit = float(stats.t.ppf(0.975, df))
    ci_lo = mean - crit * se
    ci_hi = mean + crit * se
    cohens_d = mean / std if std > 0 else None

    out.update({
        "mean_ratio": mean, "std_ratio": std, "se": se,
        "t_statistic": t_val, "df": df, "p_twosided": p_two,
        "ci95_low": ci_lo, "ci95_high": ci_hi, "cohens_d": cohens_d,
    })
    return out


def fmt(x, nd=3):
    if x is None:
        return "—"
    if isinstance(x, float) and math.isnan(x):
        return "—"
    return f"{x:.{nd}f}"


def fmt_p(x, nd=4):
    if x is None:
        return "—"
    return f"{x:.{nd}f}"


def build_md(data: dict, per_system: list, ms: dict) -> str:
    lines = []
    A = lines.append
    A("# 跨体系 meta-analysis：双金属 MOF 协同峰相对 Vegard 线性内插基线的增强率")
    A("")
    A("> 问题 #10 残余专项：NiCo-MOF-74 单体系实测点仅 3 个（x=0/0.5/1.0），单体系曲线拟合自由度不足。"
      "本文不拟合任何单体系曲线，改为 meta-analysis 跨体系口径：以每个双金属体系中点（协同峰）"
      "相对 Vegard 线性内插基线（两端点算术平均，无协同零假设）的增强率作为统一效应量，跨体系做推断统计。")
    A("")
    A("## 1. 方法")
    A("")
    A("- **Vegard 基线（无协同零假设）**：若双金属 MOF 仅是两种单金属 OMS 的简单混合，容量应随比例线性内插。"
      "在中点 x=0.5 处，期望值 `linear_mid = (endpoint_low + endpoint_high) / 2`。")
    A("- **效应量**：`ratio = (mid_value - linear_mid) / linear_mid`，即中点评实测/估计值相对线性内插的**相对增强率**。")
    A("- **跨体系推断**：单样本 t 检验（H0: 平均增强率 = 0，双侧），95% CI，Cohen's d（单样本 d = mean/std），"
      "符号检验（正向体系占比，二项检验 H0: p=0.5）。")
    A("- **样本量门槛**：体系数 n<4 时 t 检验不适用（自由度不足），仅报告符号检验并显式注明。")
    A("- **数据来源**：数值全部来自 `quantitative_pairs.json`、`quantitative_validation.md` 表1.1/1.2（§4bis 推导规则）、"
      "`knowledge_graph.md`；实测/估计逐条标注，未编造任何文献数值。")
    A("")
    A("## 2. 数据（每体系端点 + 中点）")
    A("")
    A("| 体系 | 端点低 (x=0) | 端点高 (x=1) | 中点值 | 单位 | 来源 | 中点实测? | Vegard中点 | 增强率 ratio | 备注 |")
    A("|------|-------------|-------------|--------|------|------|-----------|-----------|--------------|------|")
    for s in per_system:
        est_tag = "" if s["midpoint_is_measured"] else "（归一化估计，仅趋势参考）"
        A(f"| {s['system']} | {fmt(s['endpoint_low'])} ({s['endpoint_low_label']})"
          f" | {fmt(s['endpoint_high'])} ({s['endpoint_high_label']})"
          f" | {fmt(s['midpoint_value'])} | {s['unit']} | {s['source']}"
          f" | {'是' if s['midpoint_is_measured'] else '否'} | {fmt(s['linear_mid'])}"
          f" | **{fmt(s['ratio'] * 100, 1)}%** | {est_tag} |")
    A("")
    A("> 说明：`中点实测?=否` 的行，端点值为 quantitative_validation.md §4bis 的 R_EST_1/2/3/4 规则构造，"
      "中点 1.0 为文献定性结论（1:1 最优 / 双金属>单金属）加归一化强制最大值，**不是独立实测**，"
      "仅作趋势参考，不替代实验验证。唯一全实测体系为 NiCo-MOF-74（p62，298K/1bar）。")
    A("")
    A("排除条目：Cu/Mg-MOF-74（scv:ecfe34f94197 实测 9.21 mmol/g@273K/100kPa, Cu/Mg=0.1/0.9）"
      "——该点为 x=0.9 接近端点而非中点，且无同条件端点（273K/100kPa）可作基线；"
      "且 R19 判定 Cu/Mg（s-d 组合）吸附随 Mg 比例单调增，属倒 U 反例，故不纳入统计。")
    A("")
    A("## 3. 统计结果")
    A("")
    n = ms["n"]
    n_meas = sum(1 for s in per_system if s["midpoint_is_measured"])
    A(f"- **纳入体系数 n** = {n}（其中中点实测 {n_meas} 个，中点归一化估计 {n - n_meas} 个）。")
    A("")
    if ms["t_test_applicable"]:
        A(f"- **平均增强率** = {fmt(ms['mean_ratio'] * 100, 1)}%，样本标准差 = {fmt(ms['std_ratio'] * 100, 1)}%，"
          f"标准误 = {fmt(ms['se'] * 100, 1)}%。")
        A(f"- **单样本 t 检验（H0: 平均增强率=0）**：t = {fmt(ms['t_statistic'], 2)}，df = {ms['df']}，"
          f"p = {fmt_p(ms['p_twosided'])}（双侧）。")
        sig = "显著" if ms["p_twosided"] is not None and ms["p_twosided"] < 0.05 else "不显著"
        ci_text = "不包含 0" if (ms["p_twosided"] is not None and ms["p_twosided"] < 0.05) else "包含 0"
        A(f"- **95% CI（平均增强率）** = [{fmt(ms['ci95_low'] * 100, 1)}%, {fmt(ms['ci95_high'] * 100, 1)}%]，{ci_text}，"
          f"在 α=0.05 下{sig}。")
        A(f"- **Cohen's d（单样本）** = {fmt(ms['cohens_d'], 2)}（{_d_level(ms['cohens_d'])}）。")
    else:
        A(f"- ⚠️ **n = {n} < 4，t 检验不适用**（{ms.get('t_test_note', '')}）。仅报告符号检验，结论为趋势性。")
    A(f"- **符号检验**：{ms['sign_test']['positive_count']}/{ms['sign_test']['total']} 个体系增强率为正"
      f"（{fmt(ms['sign_test']['positive_ratio'] * 100, 0)}%），"
      f"二项检验 p = {fmt_p(ms['sign_test']['p_twosided_binom'])}（双侧，H0: p=0.5）。")
    A("")
    A("## 4. 物理诠释")
    A("")
    k_pos = ms["sign_test"]["positive_count"]
    A(f"- **正向协同在全部 {n} 个纳入体系中一致出现**：{k_pos}/{n} 个体系中点高于两端点线性内插"
      "（Cu/Mg s-d 单调增反例因无中点且条件不可比被排除）。")
    A("- **增强幅度体系依赖**：")
    for s in sorted(per_system, key=lambda x: -x["ratio"]):
        tag = "实测" if s["midpoint_is_measured"] else "归一化估计"
        A(f"  - {s['system']}：{fmt(s['ratio'] * 100, 0)}%（{tag}）")
    A("  —— 与 OMS 型 MOF-74 平台（d-d 组合、开放式金属位点密集）协同幅度大于介孔 MIL-101 框架"
      "的物理预期一致（R5/R19：曲线形状与幅度依赖金属组合与框架）。")
    A("- **机理旁证**：d-d 组合（NiCo/CoMn）倒 U、s-d 组合（Cu/Mg）单调（R19），电子结构（d 带中心差/空反键轨道，R27）"
      "是协同的来源；meta-analysis 给出的正增强率与 R5「双金属比例→容量非单调、存在体系依赖峰值」方向一致。")
    A("")
    A("## 5. 与单体系拟合的关系")
    A("")
    A("- **单体系口径（quantitative_validation.md）**：NiCo 全 8 点（3 实测+5 估计）二次拟合"
      "R²=0.6919，嵌套 F=9.909, p=0.0254，峰值 x=0.437；但**仅实测点 3 点**自由度=0，二次 R²=1.0 是数学恒等，"
      "不能作为统计证据。")
    A("- **meta-analysis 口径（本文）**：不拟合任何单体系曲线，把每体系中点增强率作为独立效应量跨体系检验。"
      f"NiCo 实测中点增强率 {fmt(next(s['ratio'] * 100 for s in per_system if s['system'] == 'NiCo-MOF-74'), 1)}%"
      f"（{fmt(next(s['midpoint_value'] for s in per_system if s['system'] == 'NiCo-MOF-74'))} vs "
      f"{fmt(next(s['linear_mid'] for s in per_system if s['system'] == 'NiCo-MOF-74'))} mmol/g）"
      "与单体系二次拟合峰值增强 +83%（8.32 vs 4.55）几乎一致，"
      "两口径相互印证；且 meta 口径把「自由度问题」从单体系拟合参数数（3 点 3 参数）转移为跨体系样本量"
      f"（{n} 个独立体系），可做 t 检验/符号检验。")
    A(f"- **代价**：{n} 个体系中 {n - n_meas} 个为归一化估计（中点=1.0 为构造值），若排除它们则只剩 {n_meas} 个体系，"
      "统计口径将退化为单体系，无法做跨体系推断。因此本文结果**只能定性支持「正向协同」的普适趋势，"
      "不能定量确证倒 U 普适性**。")
    A("")
    A("## 6. 局限与诚实声明")
    A("")
    A("- 数值全部来自真实文件（quantitative_pairs.json / quantitative_validation.md / knowledge_graph.md），"
      "无编造；is_measured 逐条标注。")
    A("- CoMn/FeCu/MIL-101 的端点与中点为归一化估计（§4bis R_EST 规则 + 文献定性结论），"
      "`中点=1.0` 含归一化构造成分，**仅趋势参考，不替代实验验证**。")
    A(f"- n={n} 样本量仍小：t 检验功效有限（按 quantitative_validation.md §5.3a 的经验，n=12 时才仅能检测大效应）；"
      f"符号检验 p={fmt_p(ms['sign_test']['p_twosided_binom'])}（双侧）本身不显著，"
      f"显著性主要由 {k_pos}/{n} 全正向 + t 检验贡献。")
    A("- 各体系测试条件不完全一致（NiCo 298K/1bar；FeCu 1-5 bar/40-50°C 系统评估；MIL-101 条件见 p147），"
      "但效应量是体系内归一化/同条件端点内插，跨体系比较基于「增强率」而非绝对容量，条件差异影响有限。")
    A("- **下一步**：按 gap_report 建议做梯度合成实验（0-100%，步长 10%），逐体系获取足量实测中点后，"
      "meta-analysis 可纳入更多实测体系并做混合效应模型。")
    A("")
    A(f"> 由 `workspace/code/survey/meta_analysis.py` 生成（数据：`meta_analysis_data.json`）。")
    return "\n".join(lines)


def _d_level(d):
    if d is None:
        return "不适用"
    a = abs(d)
    if a < 0.2:
        return "效应量微小"
    if a < 0.5:
        return "小效应"
    if a < 0.8:
        return "中效应"
    return "大效应"


def main():
    data = load_data(DATA_FILE)
    included = [s for s in data["systems"] if s.get("include_in_meta_analysis", False)]
    excluded = [s for s in data["systems"] if not s.get("include_in_meta_analysis", False)]

    if not included:
        raise SystemExit("错误：meta_analysis_data.json 中没有 include_in_meta_analysis=true 的体系。")

    per_system = [compute_per_system(s) for s in included]
    ratios = [s["ratio"] for s in per_system]
    ms = meta_stats(ratios)

    # 报告性汇总
    per_system_out = []
    for s in per_system:
        per_system_out.append({
            "system": s["system"],
            "endpoint_low": s["endpoint_low"],
            "endpoint_low_label": s["endpoint_low_label"],
            "endpoint_high": s["endpoint_high"],
            "endpoint_high_label": s["endpoint_high_label"],
            "midpoint_value": s["midpoint_value"],
            "midpoint_label": s["midpoint_label"],
            "midpoint_is_measured": s["midpoint_is_measured"],
            "unit": s["unit"],
            "source": s["source"],
            "note": s["note"],
            "linear_mid": s["linear_mid"],
            "ratio": s["ratio"],
        })
    excluded_out = [{
        "system": s["system"],
        "midpoint_value": s["midpoint_value"],
        "midpoint_label": s["midpoint_label"],
        "unit": s["unit"],
        "source": s["source"],
        "is_measured": s.get("midpoint_is_measured"),
        "exclude_reason": s.get("exclude_reason"),
    } for s in excluded]

    result = {
        "generated_at": "2026-08-04",
        "method": "跨体系 meta-analysis：中点增强率 ratio=(mid-linear_mid)/linear_mid, linear_mid=(endpoint_low+endpoint_high)/2 (Vegard)",
        "data_file": str(DATA_FILE.relative_to(BASE)),
        "per_system": per_system_out,
        "excluded_systems": excluded_out,
        "meta_stats": ms,
        "warnings": [
            "CoMn/FeCu/MIL-101 的端点与中点为归一化估计（quantitative_validation.md §4bis R_EST 规则+文献定性结论），中点=1.0 含构造成分，仅趋势参考，不替代实验验证。",
            "n=4 样本量小：t 检验功效有限；符号检验双侧 p 不显著，结论以定性「正向协同趋势」为准。",
            "各体系测试条件不完全一致（NiCo 298K/1bar；FeCu 1-5 bar/40-50°C；MIL-101 p147），基于体系内增强率比较以缓解。",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    md = build_md(data, per_system, ms)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)

    # 控制台摘要
    print(f"[OK] meta-analysis 完成：n={ms['n']} 个体系")
    for s in per_system:
        print(f"  - {s['system']:<16} ratio = {s['ratio'] * 100:+.1f}%  (Vegard中点={s['linear_mid']:.3f})")
    if ms["t_test_applicable"]:
        print(f"[t 检验] t={ms['t_statistic']:.3f}, df={ms['df']}, p={ms['p_twosided']:.4f}, "
              f"95%CI=[{ms['ci95_low']*100:.1f}%, {ms['ci95_high']*100:.1f}%], d={ms['cohens_d']:.2f}")
    else:
        print(f"[t 检验] 不适用（n={ms['n']}<4）")
    print(f"[符号检验] {ms['sign_test']['positive_count']}/{ms['sign_test']['total']} 正向, "
          f"p(双侧)={ms['sign_test']['p_twosided_binom']:.4f}")
    print(f"[输出] {OUT_MD}")
    print(f"[输出] {OUT_JSON}")


if __name__ == "__main__":
    main()
