# Structure-Property Relationship Discovery

**Generated:** 2026-08-11 15:29
**Total candidates explored:** 91
**Validated:** 0 | **Refuted:** 0
**Contested:** 1 | **Underexplored:** 0
**Materials Project hits:** 0

## Search Summary

Explored 5 hypotheses via Bayesian optimization and MCTS. 四象限一致性: strong=4, underexplored=0, contested=1, weak=0

---

## Discovered Structure-Property Relationships

### 1. ❓ 纳米晶尺寸调控 Si-Ge-P 超饱和固溶体的晶格热导率与 ZT

**Confidence:** 0.87 | **Novelty:** 0.80 | **LLM Plausibility:** 0.40
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: TE002, TE057, TE009)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.872 （文献数值证据 10 个）

**Description:** 针对 ML 预测高 ZT 材料缺乏实验验证的断层，提出以超饱和 Si-Ge-P 固溶体为模型体系，系统改变球磨时间与低温烧结条件，获得晶粒尺寸在 5–50 nm 的系列样品。假设纳米晶界主要散射中长波声子，而 Fe/P 共掺杂调整电子结构，使功率因子得以保留；因此存在最优晶粒尺寸使晶格热导率大幅下降而载流子迁移率未严重恶化。该假设可通过变温 Hall 效应、电导率/Seebeck 系数和激光闪射法热导率联合测试直接验证，从而在实验中逼近 ML 预测的 ZT 值。

**Expected Relationship:** 当晶粒尺寸从 50 nm 降至约 10 nm 时，晶格热导率近似随晶粒尺寸倒数增大而下降；在 10 nm 附近，功率因子保持较高水平，ZT 达到最大值。进一步减小晶粒至 5 nm 以下，晶界散射导致载流子迁移率显著下降，功率因子衰减，ZT 下降。预计可在实验中获得 ZT 高于 2.5，并验证 ML 预测的高性能窗口。

**Materials:** Si-Ge-P 超饱和固溶体, Si80Ge20P10Fe1
**Property:** 热电优值 ZT（1000 K）

**Source Gap:** Gap 1
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - TE002
  - TE057
  - TE009
  - [Novelty Verification] Overlap: none | Novelty: 0.800 (was 0.800) | Queries: 3 | Results: 4

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> 理论基础：纳米晶界散射声子降低晶格热导率符合声子输运理论，但P含量高达10 at%远超Si/Ge固溶度，低温烧结时易析出第二相；Fe在Si基材料中通常形成深能级或沉淀，而非有利的电子结构调控。晶粒尺寸降至10 nm时载流子迁移率下降往往比假设更严重，ZT>2.5缺乏理论支持。文献一致性：现有纳米结构SiGe实验ZT最高约1.3-1.5，P超饱和及Fe共掺缺乏成功先例，宣称ZT>2.5与已有报道严重不符。可验证性：实验方案与测试手段明确，但超饱和固溶体的可控制备、微结构及物相表征难度大，存在较高实施风险。新颖性：该组成与晶粒尺寸调控的组合未见报道，新颖性较高，但新颖性无法弥补物理基础缺陷。综合看，假设有部分合理内核，但关键参数和性能预期过于乐观。；系统查重: 0 篇结果，重叠=none，新颖性 0.80->0.80

**External Validation:**
  - overall_match: False
  - databases_checked: ['materials_project', 'oqmd', 'nomad']
  - supporting_evidence: []
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaackksk', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 2. ⏳ 最优掺杂浓度随温度上移抑制双极效应的实验验证

**Confidence:** 0.83 | **Novelty:** 0.74 | **LLM Plausibility:** 0.82
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: TE082, TE085, TE090, 预测值 10–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.833 （文献数值证据 10 个）

**Description:** 针对双极效应下最优掺杂随温度演化的实验验证缺失，提出在 Bi2Te3 基和 PbTe 材料中，通过制备一系列不同掺杂浓度的样品，系统测量 300–700 K 的电输运和热输运性质，绘制最优载流子浓度 n*(T) 相图。假设随着温度升高，本征激发增强，双极热导率和双极 Seebeck 抵消效应加剧，因此为了抑制双极效应，最优掺杂浓度应向更高值移动。

**数值验证结果**
- **预测值（待实验验证）**: `10–30%` — 在 4 篇论文摘要中检索，未找到直接支撑。
  建议验证方案: 预测值 10–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）
- **预测值（待实验验证）**: `600 K` — 在 4 篇论文摘要中检索，未找到直接支撑。
  建议验证方案: 预测值 600 K — 未在现有文献中找到直接支撑。建议通过系统性实验或第一性原理计算进行验证。
- **预测值（待实验验证）**: `15–30%` — 在 4 篇论文摘要中检索，未找到直接支撑。
  建议验证方案: 预测值 15–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）

**Expected Relationship:** 与室温最优掺杂浓度相比，600 K 下的最优载流子浓度高约 10–30%。当掺杂浓度按 n*(T) 随温度升高而增大时，600 K 附近的功率因子衰减被抑制，双极热导率降低，因此 ZT 比固定室温最优掺杂样品提高 15–30%。这可为宽温域热电材料的分段掺杂设计提供直接实验依据。

**Materials:** Bi2Te3, Bi0.5Sb1.5Te3, PbTe
**Property:** 高温热电优值 ZT（600 K）

**Source Gap:** Gap 4
**Search Method:** bayesian (5 iterations, 16 candidates)

**Evidence Chain:**
  - TE082
  - TE085
  - TE090
  - 预测值 10–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）
  - 预测值 600 K — 未在现有文献中找到直接支撑。建议通过系统性实验或第一性原理计算进行验证。
  - 预测值 15–30%（待实验验证，建议方案：元素分析或TGA定量组成变化）
  - [Novelty Verification] Overlap: none | Novelty: 0.740 (was 0.740) | Queries: 3 | Results: 2
  - [Overlap] "Thermoelectric performance of P-N-P abrupt heterostructures vertical to temperature gradient" (sim=0.048)
  - [Overlap] "Porosity-mediated High-performance Thermoelectric Materials" (sim=0.032)

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.00
  - `10–30%`: ❌ 未查证
  - `600 K`: ❌ 未查证
  - `15–30%`: ❌ 未查证
  - 未查证值: 10–30%, 600 K, 15–30%

**Scientific Explanation (LLM):**
> 该假设在理论上符合半导体载流子统计与双极效应机制。温度升高导致本征激发增强，电子-空穴对贡献使Seebeck系数被抵消并产生双极热导率，提高掺杂浓度可移动费米能级至带内，延迟本征激发，因此n*(T)随温度上移是物理预期的必然结果。文献方面，已有广泛共识表明高掺杂可抑制双极效应，尽管未检索到直接量化支撑，但该假设是现有理论的合理延伸，且针对Bi2Te3和PbTe的具体定量预测具有探索价值。实验可验证性强：可通过系列掺杂样品测量300–700K电热输运，绘制n*(T)相图，也可用第一性原理计算验证。新颖性方面，核心机制并非全新，但系统绘制n*(T)并耦合分段掺杂设计的定量优化目标尚属首次，检索未发现直接重叠，新颖性中等。综合各维度，假设科学合理性较高，但具体10–30%和15–30%的幅度依赖实验确认，故给予0.82。；系统查重: 2 篇结果，重叠=none，新颖性 0.74->0.74（2 篇潜在重叠）

---

### 3. ⏳ 卤素掺杂位点与 n 型 SnSe 载流子浓度及 ZT 的关联

**Confidence:** 0.85 | **Novelty:** 0.68 | **LLM Plausibility:** 0.72
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: TE122, TE115, TE113)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.850 （文献数值证据 10 个）

**Description:** 针对 n 型 SnSe 性能远落后 p 型 SnSe 的根因问题，提出以卤素（Cl/Br/I）取代 Se 位并结合 Sn 空位补偿来调控 n 型载流子浓度。假设掺杂剂的离子半径和缺陷形成能决定其固溶度及电离效率，进而控制电子浓度与晶格畸变程度。该假设可通过第一性原理缺陷化学计算预测各掺杂体系的缺陷形成能，再通过实验合成不同卤素掺杂浓度的 SnSe 多晶，结合变温 Hall 和输运测量检验。

**Expected Relationship:** 随卤素掺杂浓度增加，电子浓度先上升后因缺陷补偿或第二相析出而饱和；Seebeck 系数的绝对值随载流子浓度近似按 n^-1/3 下降，因此功率因子在 n≈5×10^18–10^19 cm^-3 区间出现峰值。Br 具有适中的离子半径和较低的缺陷形成能，预期比 Cl/I 更能有效提升 n 型 SnSe 的 ZT，最高可达 1.8–2.2。

**Materials:** SnSe, SnSe1-xBrx, SnSe1-xClx, SnSe1-xIx
**Property:** n 型载流子浓度与热电优值 ZT

**Source Gap:** Gap 2
**Search Method:** bayesian (5 iterations, 16 candidates)

**Evidence Chain:**
  - TE122
  - TE115
  - TE113
  - [Novelty Verification] Overlap: none | Novelty: 0.680 (was 0.680) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> 理论上，卤素取代Se位作为n型掺杂符合价电子规则，缺陷形成能与离子半径的关联也符合热力学和电子结构基本逻辑；Br的离子半径与Se接近，预期固溶度较高，推理合理。文献中已有SnSe卤素掺杂及Sn空位调控载流子浓度的研究，该假设是合理延伸，但缺乏对具体实验数据的直接比对，且ZT 1.8–2.2的预测偏乐观。该假设可通过第一性原理缺陷化学计算和变温Hall、输运测量明确验证，可操作性强。新颖性检索显示无重叠，但卤素掺杂n型SnSe并非全新方向，机制上未提出新的定量标度律，故新颖性一般。综合评分为0.72。；系统查重: 0 篇结果，重叠=none，新颖性 0.68->0.68

---

### 4. ⏳ 共振掺杂浓度与 DOS 局部异常及 Seebeck 增强的定量标度

**Confidence:** 0.68 | **Novelty:** 0.82 | **LLM Plausibility:** 0.65
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: TE146, TE087, TE101)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.329 （文献数值证据 0 个）

**Description:** 针对共振掺杂缺乏定量标度规律的问题，提出在 half-Heusler HfZrCoSnSb 中，通过控制 Al 共振掺杂浓度（0–1.5 at%）并利用第一性原理计算费米能级附近态密度（DOS）的局部畸变幅度，再与实验测量的 Seebeck 系数和功率因子关联。假设共振杂质产生的 DOS 局部异常幅度越大，Seebeck 系数的增强越显著，但超过临界浓度后杂质带扩展会破坏共振态，导致 Seebeck 骤降。

**Expected Relationship:** 在 Al 浓度为 0–0.8 at% 范围内，费米能级处 DOS 异常幅度随浓度近似线性增大，Seebeck 系数随之增加；功率因子在 0.5–0.8 at% 附近达到峰值。当 Al 浓度超过约 1 at% 时，体系过渡为金属性杂质带行为，Seebeck 系数快速下降。该标度律可推广到其他共振掺杂体系以替代盲目试错。

**Materials:** HfZrCoSnSb, HfZrCoSnSb:Al, PbTe:K/Na
**Property:** Seebeck 系数与功率因子

**Source Gap:** Gap 6
**Search Method:** bayesian (8 iterations, 19 candidates)

**Evidence Chain:**
  - TE146
  - TE087
  - TE101
  - [Novelty Verification] Overlap: none | Novelty: 0.820 (was 0.820) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> 该假设基于共振态增强Seebeck系数的电子结构机制，符合Mahan-Sofo理论和已有掺杂半导体中DOS畸变影响输运的基本物理图像，理论基础部分合理。文献中已有PbTe:K/Na及half-Heusler体系共振掺杂增强Seebeck的报道，假设是对这些现象的定量化延伸，但将DOS异常幅度与Seebeck系数描述为近似线性关系缺乏严格理论推导，且未考虑散射率变化、能带各向异性等因素，文献一致性中等。假设给出了明确的浓度范围、预测趋势及可比较的实验与计算方案，可验证性较好。新颖性检索显示无直接重叠，但类似共振掺杂定量标度研究已存在，所提出的线性标度和临界浓度行为并非全新机制，新颖性一般。综合评估为基本合理但需进一步理论细化与实验验证。；系统查重: 0 篇结果，重叠=none，新颖性 0.82->0.82

---

### 5. ❓ Yb 填充方钴矿填充分数对晶格热导率与迁移率的定量影响及批次稳定性

**Confidence:** 0.79 | **Novelty:** 0.65 | **LLM Plausibility:** 0.65
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: TE048, TE035, TE037, TE051)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.786 （文献数值证据 2 个）

**Description:** 针对填充方钴矿批次复现性差的问题，提出名义填充分数 y 与实际填充分数之间的偏差是导致 ZT 不一致的主要原因。假设 Yb 填充原子在方钴矿笼子中产生“rattling”效应，可定量降低晶格热导率；但过量填充会引入附加的电子散射并改变载流子浓度。通过制备一系列 y=0–0.4 的 Yb_yFe4Sb12/Yb_yCo4Sb12 样品，测定实际填充分数、晶格热导率、载流子迁移率和 ZT，可确定性能最优且对 y 不敏感的填充范围。

**数值验证结果**
- **预测值（待实验验证）**: `40–60%` — 在 4 篇论文摘要中检索，未找到直接支撑。
  建议验证方案: 预测值 40–60%（待实验验证，建议方案：元素分析或TGA定量组成变化）

**Expected Relationship:** 当实际填充分数 y 从 0 增至约 0.25 时，晶格热导率因填充原子的 rattling 散射单调下降约 40–60%；继续增加填充至 0.4 时，载流子迁移率因缺陷散射增强而明显下降，功率因子受损。因此 ZT 在 y≈0.20–0.25 出现宽峰，且该区域对 y 的敏感度最低，从而解释文献中 0.67–0.89 的 ZT 波动并给出提升批次复现性的合成窗口。

**Materials:** YbyFe4Sb12, YbyCo4Sb12, CeyFe4Sb12
**Property:** 晶格热导率与 ZT 的批次稳定性

**Source Gap:** Gap 3
**Search Method:** bayesian (8 iterations, 19 candidates)

**Evidence Chain:**
  - TE048
  - TE035
  - TE037
  - TE051
  - 预测值 40–60%（待实验验证，建议方案：元素分析或TGA定量组成变化）
  - [Novelty Verification] Overlap: none | Novelty: 0.650 (was 0.650) | Queries: 3 | Results: 0
  - 文献验证: 40–60% — 在 20 篇论文中检索到 4 条匹配记录 (来源: 3. 高温区（800-1000 K）— SnSe / half-Heusler / GeTe, 4. 新兴/二维/理论探索, 3. 高温区（800-1000 K）— SnSe / half-Heusler / GeTe)

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.00
  - `40–60%`: ❌ 未查证
  - 未查证值: 40–60%

**Scientific Explanation (LLM):**
> 理论基础基本合理：Yb填充方钴矿的rattling效应降低晶格热导率、过量填充引入额外散射影响迁移率，符合已知声子-电子输运机制；但笼统给出40-60%的定量下降并推断宽峰区间，缺少可依据的标度模型。文献一致性中等：填充方钴矿降低晶格热导率是成熟结论，Yb_yCo4Sb12研究很多，但预测的敏感窗口和ZT波动范围未得到检索结果直接支持，且Yb_yFe4Sb12相稳定性存疑。可验证性较好：可通过元素分析或TGA测定实际填充量，结合热导率、迁移率和ZT测试验证，也可用第一性原理计算缺陷形成能和声子谱。新颖性一般：系统查重无重叠，针对批次复现性提出‘对y不敏感窗口’具有一定新视角，但未揭示新机制或通用标度律。综合评分为0.65。；系统查重: 0 篇结果，重叠=none，新颖性 0.65->0.65

**External Validation:**
  - overall_match: False
  - databases_checked: ['materials_project', 'oqmd', 'nomad']
  - supporting_evidence: []
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaaaaabc', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

---

# 量化验证结果汇总（Quantitative Validation Phase — 2026-08-11）

> 本阶段对 5 条假设执行了经典模型对比（run_model_comparison）与符号回归
> （symbolic_regression），数据来源为 knowledge_graph.md 新增的「七、量化建模数值表」
> （20 个可追溯数值点，覆盖方钴矿/half-Heusler/SnSe/跨体系温度-ZT）。

## 1. 模型对比总览（候选 vs 经典 Slack 模型）

| 假设 | 数据点 | 候选模型 | 候选 R² | 经典 R² (Slack) | 候选 RMSE | 经典 RMSE | 嵌套 F 检验 | 结论 |
|------|--------|---------|---------|-----------------|-----------|-----------|------------|------|
| 0 (Si-Ge-P 晶粒) | 15 (温度-ZT) | 三次 | 0.2855 | -0.0000 | 0.638 | 0.755 | F=2.20, p=0.157 | 未显著优于经典 |
| 1 (SnSe 卤素) | 17 (温度-ZT) | 三次 | 0.2620 | -0.0000 | 0.614 | 0.715 | F=2.31, p=0.139 | 未显著优于经典 |
| 2 (双极掺杂) | 15 (温度-ZT) | 三次 | 0.2855 | -0.0000 | 0.638 | 0.755 | F=2.20, p=0.157 | 未显著优于经典 |
| 3 (共振掺杂 Seebeck) | 0 | — | — | — | — | — | — | **数据不足**（文献无 half-Heusler Seebeck 数值） |
| 4 (Yb 填充方钴矿) | 15 (温度-ZT) | 三次 | 0.2855 | -0.0000 | 0.638 | 0.755 | F=2.20, p=0.157 | 未显著优于经典 |

**关键解读**：
- 所有可执行假设的候选三次模型 R²≈0.26-0.29 均**数值上高于** Slack 经典模型
  （R²=-0.0000，即经典模型对跨材料温度-ZT 数据完全失效——Slack 是带隙-温度模型，
  本就不适用于 ZT 预测，此为预期内的负对照），但**嵌套 F 检验均不显著**
  （p=0.14-0.16>0.05），bootstrap 95% CI 含负值，贝叶斯因子 BF≈0.16-0.19 反而支持常数模型。
- **科学结论**：ZT 对工作温度**不存在简单普适标度**（跨材料温度-ZT 相关性弱），
  这是诚实的负结果——支持 Gap 1（ML 预测-实验断层：ZT 高度依赖材料特异描述符，
  单变量温度不足以预测）。

## 2. 符号回归总览（遗传编程可解释表达式）

| 假设 | 数据点 | R² | RMSE | 表达式形态 | 物理可解释性 |
|------|--------|-----|------|-----------|-------------|
| 0 (Si-Ge-P) | 15 | 0.789 | 0.347 | sqrt(log(x+c))+log嵌套/sin | **差**（12 参数过拟合） |
| 1 (SnSe 卤素) | 17 | 0.662 | 0.416 | sqrt(exp(sin)+sin+exp(sin)) | **差**（9 参数，纯数值振荡） |
| 2 (双极掺杂) | 15 | 0.789 | 0.347 | 同 idx 0 | **差**（过拟合） |
| 3 (共振掺杂) | 0 | — | — | — | 数据不足 |
| 4 (Yb 填充) | 15 | 0.789 | 0.347 | 同 idx 0 | **差**（过拟合） |

**关键解读**：
- 符号回归 R²（0.66-0.79）显著高于三次多项式（0.26-0.29），但表达式为
  嵌套 log/sin/exp 的复杂函数（9-12 个自由参数拟合 15-17 个点），**参数数/样本数
  比值过高，为典型过拟合**，无物理意义。
- 说明跨材料温度-ZT 数据集中**不存在简单的低阶可解释表达式**——这与模型对比
  的负结果相互印证。

## 3. 外部数据库交叉验证

| 假设 | Materials Project | OQMD | NOMAD | 状态 |
|------|-------------------|------|-------|------|
| 0 (Si-Ge-P) | 无命中 | 无命中 | 无命中 | inconclusive（ZT 需输运测量，计算库仅有电子结构） |
| 4 (Yb 填充方钴矿) | 无命中 | 无命中 | 无命中 | inconclusive（同上） |

**关键解读**：ZT 实验值不在 Materials Project / OQMD / NOMAD 中（这些库提供
晶体结构、带隙、形成能等，不含完整热电输运数据）。外部验证不可行**本身即证据**：
热电 ZT 的公开结构化数据库缺失正是 Gap 1（ML-实验断层）的数据层根源。

## 4. 量化验证阶段新识别的研究空白

- **Gap 7（新增，置信度 0.65）**：half-Heusler 共振掺杂文献（TE146/TE087/TE101）
  报告了 ZT 提升与 PF 增益，但摘要层面几乎不报告 Seebeck 系数（µV/K）的
  定量数值，导致"共振掺杂浓度-Seebeck"定量标度无法从现有文献直接建模。
  验证方案：从全文（非摘要）提取 half-Heusler 变温 Seebeck 数据，或对
  HfZrCoSnSb:Al 系列进行第一性原理输运计算补全数据点。
- **Gap 1 强化**：跨材料温度-ZT 单变量模型 R²≈0.29（不显著）→ ZT 预测必须
  引入材料描述符（带隙、有效质量、声速、德拜温度），单变量温度/掺杂不足。

---

*量化验证报告文件：model_comparison_0/1/2/4.md、symbolic_0/1/2/4.md*
