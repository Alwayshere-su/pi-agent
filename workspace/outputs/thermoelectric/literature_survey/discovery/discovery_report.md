# Structure-Property Relationship Discovery

**Generated:** 2026-08-02 19:32
**Total candidates explored:** 53
**Validated:** 0 | **Refuted:** 0
**Contested:** 1 | **Underexplored:** 0
**Materials Project hits:** 0

## Search Summary

Explored 5 hypotheses via Bayesian optimization and MCTS. 四象限一致性: strong=4, underexplored=0, contested=1, weak=0

---

## Discovered Structure-Property Relationships

### 1. ⏳ 纳米晶尺寸调控 Si-Ge-P 超饱和固溶体的晶格热导率与 ZT

**Confidence:** 0.87 | **Novelty:** 0.80 | **LLM Plausibility:** 0.45
**Consistency:** contested (争议 — 数据匹配但科学存疑)

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
> 理论基础方面，纳米晶界散射中长波声子降低晶格热导率符合声子输运理论，但Fe/P共掺杂调整电子结构的描述缺乏支撑，Fe在SiGe中易形成深能级，不利于载流子迁移；超饱和固溶体热力学稳定性存疑。文献一致性上，SiGe基热电材料实验ZT通常低于1.5，预期ZT>2.5过于乐观，与现有数据不符。可验证性良好，变温Hall与激光闪射等测试可明确验证。新颖性较高，查重无重叠，成分组合与超饱和策略有一定新意。综合而言，假设逻辑部分合理，但关键预期过于理想，材料选择存在潜在问题，评分中等偏低。；系统查重: 4 篇结果，重叠=none，新颖性 0.80->0.80

---

### 2. ⏳ 最优掺杂浓度随温度上移抑制双极效应的实验验证

**Confidence:** 0.83 | **Novelty:** 0.74 | **LLM Plausibility:** 0.82
**Consistency:** strong (强 — LLM与搜索一致高分)

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

#### 新颖性验证 (Novelty Verification)

**重叠评估:** none
**原始新颖性分数:** 0.820
**调整后新颖性分数:** 0.820

**检索查询:**
  1. `共振掺杂浓度与 共振掺杂浓度 但超过临界浓度后杂质带扩展会破坏共振态`
  2. `HfZrCoSnSb HfZrCoSnSb:Al`
  3. `HfZrCoSnSb HfZrCoSnSb:Al PbTe:K/Na contradictory evidence`

**检索结果总数:** 0

**潜在重叠论文:** 无

**评估说明:** 根据已有文献重叠级别为“none”且最高文本相似度为0，现有工作并未提出或验证类似的主张。该假设首次将共振掺杂浓度与DOS局部异常及Seebeck增强建立定量标度，并具体应用于HfZrCoSnSb及PbTe:K/Na体系，涉及新的定量关系和材料组合，具有足够的新颖性。因此，该研究假设的新颖性仍然成立。


**Confidence:** 0.68 | **Novelty:** 0.82 | **LLM Plausibility:** 0.65
**Consistency:** strong (强 — LLM与搜索一致高分)

**Search Best Score:** N/A（无搜索记录）

**Description:** 针对共振掺杂缺乏定量标度规律的问题，提出在 half-Heusler HfZrCoSnSb 中，通过控制 Al 共振掺杂浓度（0–1.5 at%）并利用第一性原理计算费米能级附近态密度（DOS）的局部畸变幅度，再与实验测量的 Seebeck 系数和功率因子关联。假设共振杂质产生的 DOS 局部异常幅度越大，Seebeck 系数的增强越显著，但超过临界浓度后杂质带扩展会破坏共振态，导致 Seebeck 骤降。

**Expected Relationship:** 在 Al 浓度为 0–0.8 at% 范围内，费米能级处 DOS 异常幅度随浓度近似线性增大，Seebeck 系数随之增加；功率因子在 0.5–0.8 at% 附近达到峰值。当 Al 浓度超过约 1 at% 时，体系过渡为金属性杂质带行为，Seebeck 系数快速下降。该标度律可推广到其他共振掺杂体系以替代盲目试错。

**Materials:** HfZrCoSnSb, HfZrCoSnSb:Al, PbTe:K/Na
**Property:** Seebeck 系数与功率因子

**Source Gap:** Gap 6
**Search Method:** bayesian (0 iterations, 0 candidates)

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

### 5. ⏳ Yb 填充方钴矿填充分数对晶格热导率与迁移率的定量影响及批次稳定性

#### 新颖性验证 (Novelty Verification)

**重叠评估:** none
**原始新颖性分数:** 0.650
**调整后新颖性分数:** 0.650

**检索查询:**
  1. `填充方钴矿填充分数对晶格热导率与迁移率的定量影响及批次稳定性 可定量降低晶格热导率 但过量填充会引入附加的电子散射并改变载流子浓度`
  2. `YbyFe4Sb12 YbyCo4Sb12`
  3. `YbyFe4Sb12 YbyCo4Sb12 CeyFe4Sb12 contradictory evidence`

**检索结果总数:** 0

**潜在重叠论文:** 无

**评估说明:** 根据已有文献重叠信息，未发现任何工作提出或验证过类似的主张，因此该假设在现有数据库中是空白点。当前假设聚焦于Yb填充分数对两种方钴矿材料晶格热导率与迁移率的定量影响，并结合批次稳定性评估，体现了明确的定量关系和材料体系层面的新颖性。综上，该研究假设的新颖性依然成立，值得进一步探索。


**Confidence:** 0.55 | **Novelty:** 0.65 | **LLM Plausibility:** 0.72
**Consistency:** strong (强 — LLM与搜索一致高分)

**Search Best Score:** N/A（无搜索记录）

**Description:** 针对填充方钴矿批次复现性差的问题，提出名义填充分数 y 与实际填充分数之间的偏差是导致 ZT 不一致的主要原因。假设 Yb 填充原子在方钴矿笼子中产生“rattling”效应，可定量降低晶格热导率；但过量填充会引入附加的电子散射并改变载流子浓度。通过制备一系列 y=0–0.4 的 Yb_yFe4Sb12/Yb_yCo4Sb12 样品，测定实际填充分数、晶格热导率、载流子迁移率和 ZT，可确定性能最优且对 y 不敏感的填充范围。

**数值验证结果**
- **预测值（待实验验证）**: `40–60%` — 在 4 篇论文摘要中检索，未找到直接支撑。
  建议验证方案: 预测值 40–60%（待实验验证，建议方案：元素分析或TGA定量组成变化）

**Expected Relationship:** 当实际填充分数 y 从 0 增至约 0.25 时，晶格热导率因填充原子的 rattling 散射单调下降约 40–60%；继续增加填充至 0.4 时，载流子迁移率因缺陷散射增强而明显下降，功率因子受损。因此 ZT 在 y≈0.20–0.25 出现宽峰，且该区域对 y 的敏感度最低，从而解释文献中 0.67–0.89 的 ZT 波动并给出提升批次复现性的合成窗口。

**Materials:** YbyFe4Sb12, YbyCo4Sb12, CeyFe4Sb12
**Property:** 晶格热导率与 ZT 的批次稳定性

**Source Gap:** Gap 3
**Search Method:** bayesian (0 iterations, 0 candidates)

**Evidence Chain:**
  - TE048
  - TE035
  - TE037
  - TE051
  - 预测值 40–60%（待实验验证，建议方案：元素分析或TGA定量组成变化）
  - [Novelty Verification] Overlap: none | Novelty: 0.650 (was 0.650) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.00
  - `40–60%`: ❌ 未查证
  - 未查证值: 40–60%

**Scientific Explanation (LLM):**
> 理论基础扎实：填充原子在笼中的rattling散射声子降低晶格热导率是公认机制，过量填充引入额外电子散射并改变载流子浓度也符合物理原理。文献总体一致：Yb填充CoSb3等体系已有大量报道显示晶格热导率随填充分数降低、ZT在y≈0.2附近出现峰值，但具体下降幅度因体系而异（部分报道达70%以上），故40–60%的定量预测需谨慎看待。可验证性强：可通过控制合成、元素分析测定实际填充分数，并结合热导率、迁移率及ZT测试验证，也可用第一性原理计算辅助。新颖性一般：填充-性能关系本身非新概念，但将名义/实际填充分数偏差与批次稳定性联系起来，并寻找对y不敏感的合成窗口，具有一定应用视角新意；系统检索未发现直接相似工作。综合认为假设合理但定量普适性有待实验确认。；系统查重: 0 篇结果，重叠=none，新颖性 0.65->0.65

---
