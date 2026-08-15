# -*- coding: utf-8 -*-
"""
补齐正极（cathode）主题的定量核验产物 — 诚实版
================================================================
背景：正极主题 6 条假设中，仅假设 #2（hypo_3，Ni 含量-容量保持率）有可量化的
(x,y) 数据（knowledge_graph 表 3 的 6 个领域共识值），已生成
model_comparison_2.md / symbolic_2.md / quant_supplement_h2.md。

其余 5 条（hypo_1/2/4/5/6）为机制性/定性假设，支撑文献仅存摘要（无全文解析），
摘要中无可提取的 (x,y) 数值序列。本脚本为这 5 条假设生成"数据不足"的诚实
核验产物，明确：
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

HYP_PATH = "workspace/outputs/cathode/literature_survey/discovery/hypotheses.json"
OUT_DIR = "workspace/outputs/cathode/literature_survey/discovery"

# 每条"数据不足"假设的诚实补全说明（key = 0-indexed 假设序号）
INSUFFICIENT_RATIONALE = {
    0: {  # hypo_1 — Ni 氧化态异质性 → 裂纹萌生临界应力
        "x_label": "Ni 价态空间异质性程度（价态方差 / 局部 Ni4+ 分数）",
        "y_label": "裂纹萌生临界应力（GPa）/ 裂纹起始位置",
        "evidence": "p24（光谱叠层成像，Ni 价态图）、p25（原位微力学压缩）",
        "why": (
            "机制性假设：需要同一颗粒的逐像素价态分布与临界应力的空间关联数据。"
            "支撑文献 p24/p25 的摘要只给定性结论（价态异质性存在、位错滑移与裂纹关联），"
            "未提供可量化的 (价态方差, 临界应力) 数值对。"
        ),
        "needed": (
            "p24 价态图的逐像素 Ni 价态分布数值化（得到价态方差/局部 Ni4+ 分数），"
            "与 p25 的临界压缩应力实测值（GPa）配对，形成 ≥5 个颗粒的 (异质性, 临界应力) 数据对。"
        ),
    },
    1: {  # hypo_2 — 裂纹润湿 → 容量衰减
        "x_label": "裂纹暴露（润湿）表面积",
        "y_label": "循环容量衰减速率（%/圈）",
        "evidence": "p27（氧化诱导阳离子无序自由能模型）、p31（电-化-力耦合模型）、p32（LiNiO2 表面相图 DFT）",
        "why": (
            "理论/建模假设：p27/p31 为自由能/耦合模型，摘要给的是模型框架与对比结论"
            "（耦合 vs 均匀通量），无实验的 (裂纹面积, 衰减速率) 数值序列；"
            "p32 为表面相图计算，无循环衰减数据。"
        ),
        "needed": (
            "不同裂纹密度（或润湿/阻断润湿对照）样品的 (裂纹暴露表面积, 循环衰减速率) 实测数据对，"
            "并在 >4.2 V 与 ≤4.2 V 两组电压下各取 ≥4 点，以检验耦合增益项。"
        ),
    },
    3: {  # hypo_4 — 涂层 Li 电导率 → 界面阻抗帕累托
        "x_label": "涂层厚度 h（nm）",
        "y_label": "倍率容量保持率（%）/ 界面副反应阻抗",
        "evidence": "p39（涂层界面）、p42（5 种涂层 Li 扩散系数 DFT：α-AlF3/α-Al2O3/m-ZrO2/c-MgO/SiO2）",
        "why": (
            "定量标度律假设：需要各涂层 D_Li 数值与不同厚度下的倍率保持率。"
            "p42 摘要只给 5 涂层的定性排序，未列 D_Li（cm²/s）具体值；p39 无数值。"
        ),
        "needed": (
            "p42 全文的 5 涂层 D_Li 数值（cm²/s），配以每涂层 ≥3 个厚度的倍率保持率，"
            "形成 (厚度, 保持率) 系列，方可拟合 log(保持率) 随厚度的线性斜率并检验其与 log(D_Li) 的反比关系。"
        ),
    },
    4: {  # hypo_5 — Ni 氧化态 → 阳离子混排势垒
        "x_label": "Ni 平均价态（对应 Li 脱出量 / SOC）",
        "y_label": "Li/Ni 阳离子迁移势垒（eV）/ 混排度",
        "evidence": "p27（自由能模型）、p32（表面相图 DFT）、p24（价态成像）",
        "why": (
            "DFT/理论假设：需要不同 SOC（Ni 价态）下的阳离子迁移势垒数值。"
            "p27/p32 摘要未给势垒（eV）具体值，p24 为价态成像定性图。"
        ),
        "needed": (
            "p27/p32 全文的不同 Ni 价态（Li 脱出量）下的 Li/Ni 迁移势垒计算值（eV），"
            "形成 ≥4 个 (价态, 势垒) 数据对。"
        ),
    },
    5: {  # hypo_6 — 质子残留 → 容量衰减
        "x_label": "质子含量（ppm）",
        "y_label": "100 圈容量衰减速率 / 界面阻抗增长",
        "evidence": "p48（OEMS 质子残留）、p46（Zr 涂层）、p44（过锂化）",
        "why": (
            "定量剂量-响应假设：需要不同质子含量样品的衰减数据。"
            "p48 摘要为定性结论（衰减随质子含量上升），未给 (质子含量, 衰减速率) 数值对。"
        ),
        "needed": (
            "p48 全文的不同质子含量（ppm）样品的 100 圈衰减速率与界面阻抗实测值，"
            "形成 ≥4 个 (质子含量, 衰减速率) 数据对。"
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
- 数据可得性: 支撑文献仅存摘要（本项目正极主题为补跑主题，未做全文解析），摘要无可提取的定量序列。

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

    written = []
    for idx, hyp in enumerate(hyps):
        if idx == 2:  # hypo_3 已有完整产物，跳过
            continue
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
    print(f"\n共 {len(written)} 条 + 既有假设 #2（hypo_3）1 条 = 6 条全覆盖。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
