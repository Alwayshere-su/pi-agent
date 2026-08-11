# 文献调研报告：热电材料 ZT 优化——从材料体系到构效关系的系统综述

> **2026-08-11 量化验证补充**：本报告为阶段一（文献调研）产物。阶段二（构效关系发现）
> 的量化验证结果见 `discovery/discovery_report.md`（量化验证结果汇总章节）与
> `discovery/model_comparison_0/1/2/4.md`、`discovery/symbolic_0/1/2/4.md`、
> `discovery/cross_theme_connections.md`。核心结论：跨材料温度-ZT 单变量建模
> 无显著标度（负结果，强化 Gap 1），ZT 预测需多描述符（带隙/有效质量/声速）。

**主题**: Thermoelectric Materials ZT Optimization
**文献规模**: 209 篇（arxiv 160 + semantic_scholar 49）
**日期**: 2026-08-02

---

## 1. 执行摘要

热电材料实现热-电直接转换，ZT = S²σT/(κₑ+κₗ) 是核心性能指标。本调研覆盖 209 篇文献，系统梳理了室温（Bi₂Te₃）、中温（PbTe、方钴矿）、高温（SnSe、half-Heusler、GeTe）及新兴二维体系的热电材料研究进展。**核心发现**：

1. **实验 ZT 纪录**：p 型 SnSe 单晶 ZT≈2.6（923 K）为实验最高；Yb/In 填充方钴矿 ZT≈1.72（773 K）；共振掺杂 half-Heusler ZT≈1.5（980 K）
2. **四条优化主线**：能带工程（收敛/共振掺杂）、声子工程（rattling/纳米结构/软晶格）、双极抑制（带隙工程）、数据驱动（ML/ab initio 输运）
3. **六大研究空白**：ML 预测-实验断层（置信度 0.92）、n 型 SnSe 落后（0.88）、方钴矿复现性（0.75）、双极掺杂温度演化（0.80）、散射相图普适性（0.72）、共振掺杂定量标度（0.70）

## 2. 文献综述

### 2.1 Bi₂Te₃ 基（室温经典）
Bi₂Te₃ 是室温热电基准材料，面临两大本征挑战：强各向异性与高温双极激发（TE065）。优化策略包括点缺陷工程、织构取向、能带隙增大、溶液法/球磨/甩带纳米结构降热导（TE065）。低维化（原子五重层薄膜、拓扑绝缘体薄膜）理论预测 ZT 可达 2.0–7.2（TE062/TE063），但均未实验验证。n 型 Bi₂Te₃ 通过 Se 掺杂实现高性能（TE070）。

### 2.2 PbTe 基（中温）
PbTe 是研究最深入的中温体系。**关键机制**：PbTe 带隙随温度显著增大，且实际带隙在 300–900 K 贴合最优带隙，是 n 型 PbTe 高 ZT 的本质原因（TE085）；温度诱导能带收敛+谷间散射主导 p 型输运（TE090）；Sr/Na 共掺实验验证能带收敛（TE105）。合金化（Ⅱ族）有效降热导（TE098）；PbTe 的巨非谐声子散射（TE097）与铁电软模附近宽带声子散射（TE109）是其本征低热导根源。

### 2.3 SnSe 基（高温纪录）
SnSe 单晶自 2014 年报道 ZT=2.6 以来成为研究热点（TE110 综述）。本征超低热导（0.08 W/mK，TE126）源于晶格软化+纳米级 Sn 偏心位移（TE124/TE133）+强非谐性。**核心瓶颈**：n 型 SnSe 远落后 p 型（TE122），受限于本征 Sn 空位缺陷化学（天然 p 型）与掺杂剂选择；电弧熔炼 n 型多晶已达 ZT=1.8（TE115），但 n 型单晶 Pb 掺杂仅 PF=1.2（TE119）。应变工程与织构化是新兴调控手段（TE120）。

### 2.4 Half-Heusler（高温稳定）
Half-Heusler 以高热稳定性、无毒著称，主流 ZT≈1（TE138/TE143）。**突破**：Hf₀.₃Zr₀.₇CoSn₀.₃Sb₀.₇ 经 <1at% Al 共振掺杂，PF ↑65%、κ ↓13%，ZT 0.8→1.5 @980K（TE146）；ZrNiSn 基建立了载流子散射相图——化学掺杂同时屏蔽电离杂质/晶界/极性光学声子散射，但对 κₗ 影响可忽略（TE136）；FeNb₀.₈Ti₀.₂Sb 的高性能源于本征电子结构（TE200）。

### 2.5 填充方钴矿（中温工程典范）
方钴矿通过填充原子降低晶格热导。**2026 年突破**：Yb 填充+In 填充+Te 掺杂实现双带优化+缺陷工程协同，ZT≈1.72 @773K（PF=5.63 mW/mK²，κ=2.23 W/mK），7 对单级器件转换效率 8.2%@ΔT=380K（TE040）。Yb 填充+CoSi₂ 纳米颗粒达 ZT=1.43（TE039）。**机制修正**：X 射线动力学衍射表明 rattling 实为填充物-笼系统整体振动动力学，而非独立低频振动（TE188）。**挑战**：p 型复现性差（ZT 0.67–0.89 波动，TE048），Yb 溶解度温度依赖性复杂（TE035）。

### 2.6 GeTe / 新兴二维体系
GeTe 通过功函数+声阻抗失配界面协同散射达 ZT≈1.93（TE165）；极性畸变导致负热膨胀与软声子（TE163）。二维体系（Graphdiyne ZT=3.0、Janus ISbTe 应变 ZT=1.31、β-PdXY ZT=0.68、PbSe/PbTe 单层 ZT=5.3）均为理论预测，代表未验证空间。

### 2.7 数据驱动与计算
- **ML 预测**：已有 R²=0.90–0.98 的 ZT/热导预测模型（TE011/TE057），但预测-实验断层显著（TE057）
- **ab initio 输运**：从电子-声子散射率→BTE→Monte Carlo 纳米结构模拟的完整流程（TE026）
- **品质因子方法**：区分本征材料属性与载流子浓度优化的有效质量模型（TE025）
- **LLM 数据库**：大语言模型驱动的热电材料数据库（TE017）

## 3. 关键材料与性质对比

| 材料 | 类型 | ZT（实验） | 温度 | PF (mW/mK²) | κ (W/mK) | 主要机制 | 证据 |
|------|------|-----------|------|-------------|----------|---------|------|
| SnSe 单晶 (p) | 实验 | 2.6 | 923 K | — | 0.08 | 晶格软化+超低热导 | TE113/126 |
| n 型 SnSe 多晶 | 实验 | 1.8 | 773 K | — | — | 电弧熔炼+织构 | TE115 |
| Yb/In 方钴矿 | 实验 | 1.72 | 773 K | 5.63 | 2.23 | 双带优化+缺陷工程 | TE040 |
| HfZrCoSnSb+Al | 实验 | 1.5 | 980 K | ↑65% | ↓13% | 共振掺杂 | TE146 |
| Yb 方钴矿+CoSi₂ | 实验 | 1.43 | ~800 K | — | — | 纳米颗粒 | TE039 |
| (Hf,Zr)NiSn | 实验 | 1.2 | ~900 K | — | — | 合金化 | TE007 |
| GeTe 基 | 实验 | 1.93 | — | — | — | 界面声阻抗失配 | TE165 |
| Bi₂Te₃ (经典) | 实验 | ~1.0 | 300-500 K | — | — | 点缺陷+织构 | TE065 |

**理论预测 ZT（未验证）**：Bi₂Te₃ 薄膜 7.2（TE062）、PbSe/PbTe 单层 5.3（TE096）、Si-Ge-P 3.6（TE002）、Graphdiyne 3.0（TE009）、(PbTe)₂ 层 2.9（TE100）。

## 4. 研究空白与未来方向

详见 `gap_report.md`（Gap 1–6）。核心优先方向：
1. **Gap 1（高）**：弥合 ML 预测-实验断层——主动学习+相稳定性筛选闭环（TE057）
2. **Gap 2（高）**：n 型 SnSe 缺陷化学-掺杂-织构协同优化（TE122）
3. **Gap 6（中）**：共振掺杂 DOS 异常-塞贝克增强定量标度律（TE146）
4. **Gap 4（中）**：双极最优掺杂随温度演化的实验验证（TE082）
5. **Gap 3（中）**：方钴矿批次复现性标准协议（TE048）
6. **Gap 5（中）**：载流子散射相图跨体系普适性验证（TE136）

## 5. 参考文献（代表性，含 DOI）

| ID | 论文 | DOI |
|----|------|-----|
| TE065 | Hong et al., "Fundamental and Progress of Bi2Te3-based Thermoelectric Materials", 2018 | 10.1088/1674-1056/27/4/048403 |
| TE085 | Cao et al., "Thermally induced band gap increase and high thermoelectric figure of merit of n-type PbTe", 2019 | 10.1016/j.mtphys.2019.100172 |
| TE110 | Chen et al., "High-performance SnSe thermoelectric materials: Progress and future challenge", 2018 | 10.1016/J.PMATSCI.2018.04.005 |
| TE136 | Ren et al., "Establishing the carrier scattering phase diagram for ZrNiSn-based half-Heusler thermoelectric materials", 2020 | 10.1038/s41467-020-16913-2 |
| TE040 | Rao et al., "Dual Band Optimization and Defect Engineering Enable Ultrahigh Thermoelectric Performance in Filled Skutterudites", 2026 | 10.1002/aenm.202506357 |
| TE146 | Mitra et al., "Conventional Half-Heusler Alloys Advance State-of-the-Art Thermoelectric Properties", 2022 | — |
| TE057 | Athar & Jund, "Beyond Predicted ZT: Machine Learning Strategies for the Experimental Discovery of Thermoelectric Materials", 2026 | 10.1016/j.aichem.2026.100113 |
| TE122 | Abbas et al., "Challenges and strategies in developing high-performance n-type polycrystalline SnSe thermoelectric materials", 2025 | 10.1016/j.isci.2025.114025 |
| TE188 | Valério et al., "Phonon Scattering Mechanism in Thermoelectric Materials Revised via Resonant X-ray Dynamical Diffraction", 2020 | 10.1557/mrc.2020.37 |
| TE025 | Kang & Snyder, "Transport property analysis method for thermoelectric materials: material quality factor and the effective mass model", 2017 | — |

*完整 209 篇文献清单见 `paper_summaries.md` 与 `papers_te.json`。*

## 证据链

> 本章节由 `scripts/inject_evidence_chain.py` 依据 discovery 产物自动生成，保证赛题红线 1「每个结论都能指回具体文献或数据库记录」在基本任务报告层闭环。
> 生成时间：2026-08-03 18:14｜假设总数：5｜证据条目总数：27
> 数据源：discovery/hypotheses.json（必需）、discovery/discovery_report.json（可选）
> 回查路径：survey_report.md → discovery/hypotheses.json（evidence_chain）→ discovery/discovery_report.md（Evidence Chain）→ 检索缓存 search_results.json / 人工核实。
> 状态说明：「✅ 已溯源」= 编号证据在 discovery 产物中存在且未被引用审计标记；「⚠ 需人工核对」= reference_audit 标记该编号不可追溯，须人工确认。

---

### 假设 1｜纳米晶尺寸调控 Si-Ge-P 超饱和固溶体的晶格热导率与 ZT（hypo_1）

**结论简述**：针对 ML 预测高 ZT 材料缺乏实验验证的断层，提出以超饱和 Si-Ge-P 固溶体为模型体系，系统改变球磨时间与低温烧结条件，获得晶粒尺寸在 5–50 nm 的系列样品。假设纳米晶界主要散射中长波声子，而 Fe/P 共掺杂调整电子结构，使功率因子得以保留；因此存在最优晶粒尺寸使晶格热导率大幅下降而载流子迁移率未严重恶化。该假设可通过变温 Hall 效应、电导率/Seebeck 系数和激光闪射法热导率联合测试直接验证，从而在实验中逼近 ML 预测的 ZT 值。

**证据编号列表**：
- `TE002`（论文编号）
- `TE057`（论文编号）
- `TE009`（论文编号）
- `[Novelty Verification] Overlap: none | Novelty: 0.800 (was 0.800) | Queries: 3 | Results: 4`（新颖性查重）

**来源归属**：
- 论文证据：`TE002`、`TE057`、`TE009`（源自 hypotheses.json → evidence_chain）
- 新颖性查重：新颖性 0.800；查询 3 次；结果 4 条
- 数据库记录：无（hypotheses.json 中 external_validation 为空）

**可追溯状态**：✅ 已溯源 —— 证据编号在 discovery 产物（hypotheses.json → evidence_chain、discovery_report.md → Evidence Chain）中可逐层回查，且未被引用审计标记；论文编号对应的真实文献最终确认请回查检索缓存或人工复核。

---

### 假设 2｜卤素掺杂位点与 n 型 SnSe 载流子浓度及 ZT 的关联（hypo_2）

**结论简述**：针对 n 型 SnSe 性能远落后 p 型 SnSe 的根因问题，提出以卤素（Cl/Br/I）取代 Se 位并结合 Sn 空位补偿来调控 n 型载流子浓度。假设掺杂剂的离子半径和缺陷形成能决定其固溶度及电离效率，进而控制电子浓度与晶格畸变程度。该假设可通过第一性原理缺陷化学计算预测各掺杂体系的缺陷形成能，再通过实验合成不同卤素掺杂浓度的 SnSe 多晶，结合变温 Hall 和输运测量检验。

**证据编号列表**：
- `TE122`（论文编号）
- `TE115`（论文编号）
- `TE113`（论文编号）
- `[Novelty Verification] Overlap: none | Novelty: 0.680 (was 0.680) | Queries: 3 | Results: 0`（新颖性查重）

**来源归属**：
- 论文证据：`TE122`、`TE115`、`TE113`（源自 hypotheses.json → evidence_chain）
- 新颖性查重：新颖性 0.680；查询 3 次；结果 0 条
- 数据库记录：无（hypotheses.json 中 external_validation 为空）

**可追溯状态**：✅ 已溯源 —— 证据编号在 discovery 产物（hypotheses.json → evidence_chain、discovery_report.md → Evidence Chain）中可逐层回查，且未被引用审计标记；论文编号对应的真实文献最终确认请回查检索缓存或人工复核。

---

### 假设 3｜最优掺杂浓度随温度上移抑制双极效应的实验验证（hypo_3）

**结论简述**：针对双极效应下最优掺杂随温度演化的实验验证缺失，提出在 Bi2Te3 基和 PbTe 材料中，通过制备一系列不同掺杂浓度的样品，系统测量 300–700 K 的电输运和热输运性质，绘制最优载流子浓度 n*(T) 相图。假设随着温度升高，本征激发增强，双极热导率和双极 Seebeck 抵消效应加剧，因此为了抑制双极效应，最优掺杂浓度应向更高值移动。  **数值验证结果** - **预测值（待实验验证）**: `10–30%` — 在 4 篇论文摘要中检索，未找到直接支撑。  …

**证据编号列表**：
- `TE082`（论文编号）
- `TE085`（论文编号）
- `TE090`（论文编号）
- `[Novelty Verification] Overlap: none | Novelty: 0.740 (was 0.740) | Queries: 3 | Results: 2`（新颖性查重）
- `预测值 10–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）`
- `预测值 600 K — 未在现有文献中找到直接支撑。建议通过系统性实验或第一性原理计算进行验证。`
- `预测值 15–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）`
- `[Overlap] "Thermoelectric performance of P-N-P abrupt heterostructures vertical to temperature gradient" (sim=0.048)`
- `[Overlap] "Porosity-mediated High-performance Thermoelectric Materials" (sim=0.032)`

**来源归属**：
- 论文证据：`TE082`、`TE085`、`TE090`（源自 hypotheses.json → evidence_chain）
- 新颖性查重：新颖性 0.740；查询 3 次；结果 2 条
- 其他证据：预测值 10–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）
- 其他证据：预测值 600 K — 未在现有文献中找到直接支撑。建议通过系统性实验或第一性原理计算进行验证。
- 其他证据：预测值 15–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）
- 其他证据：[Overlap] "Thermoelectric performance of P-N-P abrupt heterostructures vertical to temperature gradient" (sim=0.048)
- 其他证据：[Overlap] "Porosity-mediated High-performance Thermoelectric Materials" (sim=0.032)
- 数据库记录：无（hypotheses.json 中 external_validation 为空）

**可追溯状态**：✅ 已溯源 —— 证据编号在 discovery 产物（hypotheses.json → evidence_chain、discovery_report.md → Evidence Chain）中可逐层回查，且未被引用审计标记；论文编号对应的真实文献最终确认请回查检索缓存或人工复核。

---

### 假设 4｜共振掺杂浓度与 DOS 局部异常及 Seebeck 增强的定量标度（hypo_4）

**结论简述**：针对共振掺杂缺乏定量标度规律的问题，提出在 half-Heusler HfZrCoSnSb 中，通过控制 Al 共振掺杂浓度（0–1.5 at%）并利用第一性原理计算费米能级附近态密度（DOS）的局部畸变幅度，再与实验测量的 Seebeck 系数和功率因子关联。假设共振杂质产生的 DOS 局部异常幅度越大，Seebeck 系数的增强越显著，但超过临界浓度后杂质带扩展会破坏共振态，导致 Seebeck 骤降。

**证据编号列表**：
- `TE146`（论文编号）
- `TE087`（论文编号）
- `TE101`（论文编号）
- `[Novelty Verification] Overlap: none | Novelty: 0.820 (was 0.820) | Queries: 3 | Results: 0`（新颖性查重）

**来源归属**：
- 论文证据：`TE146`、`TE087`、`TE101`（源自 hypotheses.json → evidence_chain）
- 新颖性查重：新颖性 0.820；查询 3 次；结果 0 条
- 数据库记录：无（hypotheses.json 中 external_validation 为空）

**可追溯状态**：✅ 已溯源 —— 证据编号在 discovery 产物（hypotheses.json → evidence_chain、discovery_report.md → Evidence Chain）中可逐层回查，且未被引用审计标记；论文编号对应的真实文献最终确认请回查检索缓存或人工复核。

---

### 假设 5｜Yb 填充方钴矿填充分数对晶格热导率与迁移率的定量影响及批次稳定性（hypo_5）

**结论简述**：针对填充方钴矿批次复现性差的问题，提出名义填充分数 y 与实际填充分数之间的偏差是导致 ZT 不一致的主要原因。假设 Yb 填充原子在方钴矿笼子中产生“rattling”效应，可定量降低晶格热导率；但过量填充会引入附加的电子散射并改变载流子浓度。通过制备一系列 y=0–0.4 的 Yb_yFe4Sb12/Yb_yCo4Sb12 样品，测定实际填充分数、晶格热导率、载流子迁移率和 ZT，可确定性能最优且对 y 不敏感的填充范围。  **数值验证结果** - **预测值（待实验…

**证据编号列表**：
- `TE048`（论文编号）
- `TE035`（论文编号）
- `TE037`（论文编号）
- `TE051`（论文编号）
- `[Novelty Verification] Overlap: none | Novelty: 0.650 (was 0.650) | Queries: 3 | Results: 0`（新颖性查重）
- `预测值 40–60%（待实验验证，建议方案：元素分析或TGA定量组成变化）`

**来源归属**：
- 论文证据：`TE048`、`TE035`、`TE037`、`TE051`（源自 hypotheses.json → evidence_chain）
- 新颖性查重：新颖性 0.650；查询 3 次；结果 0 条
- 其他证据：预测值 40–60%（待实验验证，建议方案：元素分析或TGA定量组成变化）
- 数据库记录：无（hypotheses.json 中 external_validation 为空）

**可追溯状态**：✅ 已溯源 —— 证据编号在 discovery 产物（hypotheses.json → evidence_chain、discovery_report.md → Evidence Chain）中可逐层回查，且未被引用审计标记；论文编号对应的真实文献最终确认请回查检索缓存或人工复核。
