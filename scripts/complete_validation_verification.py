# -*- coding: utf-8 -*-
"""
补齐固态电解质（validation）主题的定量核验产物 — 诚实版
================================================================
背景：validation 主题 5 条假设（卤化物 Br 取代、O/Mo-O 双掺杂、高熵 S_cfg、
Lewis 酸基团、Ag/LiF 双层界面）均为机制性/定性假设。知识图谱用项目自带
extract_xy_pairs_from_markdown 提取到 0 组 (x,y) 数值配对——支撑文献仅有
摘要级证据（无全文解析），图谱中相关数值均为单点（Mo-O 掺杂 3.97 mS/cm、
O2 处理降 H2S 66%、Ag@CNTs 界面电阻 0.25 Ω cm² 等），不构成可回归的
定量序列。

本脚本为 5 条假设生成"数据不足"的诚实核验产物，明确：
  - 拟验证的定量关系（x → y）；
  - 证据链与数据可得性；
  - 为什么当前数据不足以做回归；
  - 补全所需的具体数据。

原则：绝不虚构数值 —— 与整个项目"严谨一致、不要出岔子"的要求一致。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

HYP_PATH = "workspace/outputs/validation/literature_survey/discovery/hypotheses.json"
OUT_DIR = "workspace/outputs/validation/literature_survey/discovery"

# 每条"数据不足"假设的诚实补全说明（key = hypotheses.json 列表下标）
INSUFFICIENT_RATIONALE = {
    0: {  # hypo_1 — 卤化物 Br 取代量 → 电导率/湿度稳定性
        "x_label": "Br 取代量 x（Li3YCl6-xBrx）",
        "y_label": "室温离子电导率 σ (S/cm) 与 H2O 暴露后电导率保持率",
        "evidence": "P040（卤化物热导率 0.45–0.70 W/mK）、P070（CHGNet 微调 ML 预测 LYCB 结构与电导）、P006（混合阴离子/反钙钛矿综述）",
        "why": (
            "机制性假设：需要 Li3YCl6-xBrx 系列在不同 x 下的室温电导率实测/计算值。"
            "支撑文献 P040/P070/P006 的摘要只给出定性结论（卤化物 SSE 覆盖薄弱、"
            "ML 可预测结构与电导），未提供 (x, σ) 数值序列；知识图谱中卤化物体系"
            "仅 P040/P070 直接相关，无成系列电导率数据。"
        ),
        "needed": (
            "合成/计算 Li3YCl6-xBrx（x = 0, 0.5, 1.0, 1.5, 2.0, 3.0 等）系列，"
            "逐点测量室温电导率 σ 与湿度暴露后的电导率保持率，形成 ≥6 个 "
            "(x, σ) 与 (x, 保持率) 数据对，方可拟合火山型曲线并定位最优 x。"
        ),
    },
    1: {  # hypo_2 — O/Mo-O 双掺杂 → 电导率 & H2S 释放
        "x_label": "O 含量（Li6PS5Cl1-xOx 的 x，0–0.3）",
        "y_label": "室温离子电导率 σ (S/cm) 与 H2S 生成速率",
        "evidence": "P024（Mo-O 双掺杂 3.97 mS/cm 冷压单点）、P031（O2 处理降 H2S 66%）、P027（隔膜水解）、P023（拉曼水解路径）",
        "why": (
            "定量剂量-响应假设：需要不同 O/Mo-O 掺杂浓度下的 (电导率, H2S 释放) 配对。"
            "P024 只有 Mo-O 双掺杂单一组成点（3.97 mS/cm），P031 的 66% 是单一 O2 "
            "处理条件的结果，均非 O 含量 x 的系列扫描；P027/P023 只给水解机理，无定量。"
        ),
        "needed": (
            "系统合成 Li6PS5Cl1-xOx（x = 0, 0.05, 0.1, 0.2, 0.3 等）系列并测量 "
            "(x, σ) 与 (x, H2S 释放量)，同时制备单一 O 掺杂与 Mo-O 共掺杂对照，"
            "形成 ≥5 组双目标数据对，方可验证双目标优化窗口。"
        ),
    },
    2: {  # hypo_3 — 高熵 S_cfg → 电导率火山型
        "x_label": "构型熵 S_cfg（阳离子无序度）",
        "y_label": "室温离子电导率 σ (S/cm)",
        "evidence": "P068（ML 预测 SSE 电导框架）、P080（OBELiX ~600 实验电导数据集）、P079（20,237 种 Li 材料高通量筛选）、P074（MD 方法对比）",
        "why": (
            "理论/建模假设：需要同一框架下不同 S_cfg 组成的电导率数值。"
            "P068/P080/P079 摘要给的是 ML 框架与数据集规模（OBELiX ~600 样本、"
            "20,237 筛选池），未按 S_cfg 值列出电导率序列；P074 为方法对比综述。"
        ),
        "needed": (
            "从 P080 OBELiX 数据集按化学组成计算各候选的构型熵 S_cfg 并与实验 σ "
            "配对（≥10 个 (S_cfg, σ) 数据点），或用 P079 高通量数据补足，"
            "方可检验火山型关系与最优 S_cfg。"
        ),
    },
    3: {  # hypo_4 — Lewis 酸浓度 → t+/σ 权衡
        "x_label": "Lewis 酸性基团浓度",
        "y_label": "锂离子迁移数 t+ 与离子电导率 σ",
        "evidence": "P038（PEO+TFSI 弱配位阴离子，Li+ 扩散慢于 TFSI-）、P039（Lewis 酸性聚合物反转扩散关系）、P059/P001（聚合物界面工程）",
        "why": (
            "定量剂量-响应假设：需要不同 Lewis 酸基团浓度下的 (t+, σ) 配对。"
            "P038/P039 摘要只给定性结论（弱配位阴离子低 t+、Lewis 酸性可反转"
            "扩散关系），未给出不同浓度下的 t+/σ 数值序列。"
        ),
        "needed": (
            "在 PEO-LiTFSI 基体中系统引入不同浓度（如 0/1/3/5/10 wt%）的 Lewis 酸"
            "基团，逐点测量 t+ 与 σ，形成 ≥5 组 (浓度, t+, σ) 数据对，"
            "方可验证 t+ 单调上升而 σ 先升后降的非单调权衡。"
        ),
    },
    4: {  # hypo_5 — Ag/LiF 双层界面 → 界面电阻
        "x_label": "界面设计（单层 vs Ag/LiF 双层）与 SSE 阴离子种类",
        "y_label": "Li/SSE 界面电阻（Ω cm²）",
        "evidence": "P047（Ag@COOH-CNTs 0.25 Ω cm² 单点）、P017（LiF 富集 SEI）、P060（LiCux 三维网络）、P058（DFT 界面稳定性）、P046（硫化物界面策略）",
        "why": (
            "机制性/普适性假设：需要跨多种 SSE 的界面电阻系统对比。"
            "P047 只有 Ag 键合界面的单一超低值 0.25 Ω cm²，P017/P060/P046 为各自"
            "独立策略的定性报道，无「双层设计」在不同 SSE（硫化物/氧化物/卤化物）"
            "上的统一 (设计, 电阻) 数值表。"
        ),
        "needed": (
            "在 Li6PS5Cl、LLZO、Li3YCl6 上分别制备裸界面 / 单层（Ag 或 LiF）/ "
            "Ag/LiF 双层三类样品，逐类测量界面电阻（每类 ≥3 个样品），"
            "形成跨 3 种 SSE × 3 种设计的系统数据表，方可验证普适降低效应。"
        ),
    },
}


def _mk_insufficient_model_comparison(hyp: dict, rationale: dict, idx: int) -> str:
    title = hyp.get("title", "")
    desc = hyp.get("description", "")
    prop = hyp.get("property", "")
    mats = "、".join(hyp.get("materials", []))
    rel = hyp.get("expected_relationship", "")
    conf = hyp.get("confidence", "")
    gap = hyp.get("source_gap_id", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""# 模型对比报告 — 假设 #{idx}

> 生成时间: {now}
> 工具: run_model_comparison（经典模型对比，赛题硬性验证标准）
> 状态: 数据不足（insufficient_data）— 如实记录，未虚构数值

## 假设
- 标题: {title}
- 来源 Gap: {gap}
- 目标性质: {prop}
- 涉及材料: {mats}
- 置信度: {conf}
- 预期关系: {rel}

## 拟验证的定量关系（x → y）
- x: {rationale["x_label"]}
- y: {rationale["y_label"]}

## 文献数据点
- 点数: 0（无可用 (x,y) 数值对）
- 证据链: {rationale["evidence"]}
- 数据可得性: 支撑文献仅存摘要（本项目固态电解质主题为补充验证主题，未做全文解析），
  摘要无可提取的定量序列；知识图谱中相关数值均为单点报道，不构成可回归的序列。

## 候选模型 / 经典模型
无法执行：数据不足，线性 / 二次 / Vegard / 幂律 / Slack 等任何模型均无数据可拟合。

## 规则化统计判定（路线 A 验证标准）
- **verdict = insufficient_data**（数据不足，非"被否证"亦非"通过"）
- 原因: {rationale["why"]}

## 补全所需数据
{rationale["needed"]}

## 结论
本假设为机制性/理论性假设，现有摘要级证据不足以做定量回归验证。定量核验需在上述数据补全后重新运行 `run_model_comparison`。
"""


def _mk_insufficient_symbolic(hyp: dict, idx: int) -> str:
    title = hyp.get("title", "")
    prop = hyp.get("property", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""# 符号回归报告 — 假设 #{idx}

> 生成时间: {now}
> 工具: symbolic_regression（赛题推荐算法，遗传编程）
> 状态: 数据不足（insufficient_data）— 如实记录

## 假设
- 标题: {title}
- 目标性质: {prop}

## 数据
- 点数: 0（无可用 (x,y) 数值对）

## 拟合结果
无法执行：无 (x,y) 数据点，遗传编程无样本可搜索表达式，MSE/RMSE/R² 均无定义。

## 结论
数据不足。与 `model_comparison_{idx}.md` 一致：本假设需先补全定量 (x,y) 数据，方可执行符号回归。
"""


def main() -> int:
    with open(HYP_PATH, encoding="utf-8") as f:
        hyps = json.load(f)

    if len(hyps) != 5:
        print(f"警告: 预期 5 条假设，实际 {len(hyps)} 条", file=sys.stderr)

    written = []
    for idx, hyp in enumerate(hyps):
        rationale = INSUFFICIENT_RATIONALE[idx]
        mc_path = os.path.join(OUT_DIR, f"model_comparison_{idx}.md")
        sym_path = os.path.join(OUT_DIR, f"symbolic_{idx}.md")
        with open(mc_path, "w", encoding="utf-8") as f:
            f.write(_mk_insufficient_model_comparison(hyp, rationale, idx))
        with open(sym_path, "w", encoding="utf-8") as f:
            f.write(_mk_insufficient_symbolic(hyp, idx))
        written.append((idx, hyp["id"], hyp["title"]))

    print("已生成（数据不足，如实标注）：")
    for idx, hid, title in written:
        print(f"  #{idx} {hid}: {title}  -> model_comparison_{idx}.md + symbolic_{idx}.md")
    print(f"\n共 {len(written)} 条全覆盖。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
