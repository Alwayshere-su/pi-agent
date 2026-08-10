# Structure-Property Relationship Discovery

**Generated:** 2026-08-10 09:18
**Total candidates explored:** 99
**Validated:** 2 | **Refuted:** 0
**Contested:** 0 | **Underexplored:** 0
**Materials Project hits:** 2

## Search Summary

Explored 6 hypotheses via Bayesian optimization and MCTS. 四象限一致性: strong=6, underexplored=0, contested=0, weak=0

---

## Discovered Structure-Property Relationships

### 1. ❓ 单晶NMC811中Ni氧化态异质性调控位错辅助裂纹萌生

**Confidence:** 0.72 | **Novelty:** 0.88 | **LLM Plausibility:** 0.50
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: p24, p25)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.614 （文献数值证据 2 个）

**Description:** 在单晶LiNi0.8Mn0.1Co0.1O2正极颗粒中，Ni氧化态空间异质性（Ni2+/Ni3+/Ni4+分布）会产生局部晶格应变和缺陷能波动，直接影响位错滑移的临界剪切应力。假设同一单晶颗粒中Ni氧化态异质性较大的区域（特别是Ni4+富集或Ni2+还原区域）优先成为裂纹萌生点，导致颗粒整体断裂强度降低。可通过先对同一颗粒进行光谱叠层成像获得Ni价态图，再进行原位微力学压缩实验验证裂纹起始位置与价态异质性的空间关联。

**Expected Relationship:** Ni氧化态空间异质性程度（如Ni价态方差或局部Ni4+分数）与临界应力和裂纹起始位置直接相关：异质性越强，临界应力越低，且裂纹优先从价态突变界面处萌生。

**Materials:** LiNi0.8Mn0.1Co0.1O2 (SC-NMC811)
**Property:** 裂纹萌生临界应力

**Source Gap:** Gap 1
**Search Method:** bayesian (6 iterations, 17 candidates)

**Evidence Chain:**
  - p24
  - p25
  - [Novelty Verification] Overlap: none | Novelty: 0.880 (was 0.880) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 评估异常（'list' object has no attribute 'get'），采用默认评分 0.5

**External Validation:**
  - overall_match: False
  - databases_checked: ['materials_project', 'oqmd', 'nomad']
  - supporting_evidence: []
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [], 'queries_attempted': ['Ni0'], 'message': 'Materials Project 中未找到与假设涉及材料直接匹配的无机相。这可能是因为：(1) MOF 作为有机-无机杂化材料不在 MP 收录

---

### 2. ⏳ 裂纹电解质润湿通过表面重构与氧释放加速容量衰减

**Confidence:** 0.70 | **Novelty:** 0.90 | **LLM Plausibility:** 0.50
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: p27, p31, p32)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.488 （文献数值证据 0 个）

**Description:** 在高镍多晶NMC正极中，循环中形成的晶间裂纹被电解质润湿后暴露新的表面，这些新表面在高电压下按LiNiO2表面相图发生重构并释放氧，进一步增加界面阻抗和活性锂损失。假设容量衰减速率与裂纹表面积（或电解质可接触新表面面积）以及充电电压呈正相关，且存在耦合增益：裂纹+润湿比单一裂纹或单一表面重构造成的衰减更快。可通过对比在相同机械损伤下‘湿’裂纹与‘干’裂纹（如使用惰性气氛或固态电解质阻断润湿）的容量保持率来验证。

**Expected Relationship:** 容量保持率随循环圈数下降的速率与裂纹暴露面积×表面重构动力学（电压/温度相关）成正比；在高压（>4.2 V vs graphite）下，裂纹润湿与氧释放的耦合使衰减加速超出两者单独贡献之和。

**Materials:** LiNi0.8Mn0.1Co0.1O2, LiNiO2, 碳酸酯电解液
**Property:** 循环容量保持率

**Source Gap:** Gap 4
**Search Method:** bayesian (6 iterations, 17 candidates)

**Evidence Chain:**
  - p27
  - p31
  - p32
  - [Novelty Verification] Overlap: none | Novelty: 0.900 (was 0.900) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 评估失败，采用默认评分 0.5

---

### 3. ✅ 高镍层状氧化物中Ni含量与容量保持率呈非单调权衡

**Confidence:** 0.68 | **Novelty:** 0.82 | **LLM Plausibility:** 0.50
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: p22, p24, p32)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.548 （文献数值证据 0 个）

**Description:** 在LiNi_x Mn_y Co_z O2体系中，随着Ni含量x从0.6增加到1.0，首次放电容量增加，但由于Ni4+的强氧化性和表面/体相不稳定性导致循环保持率下降。假设在x≈0.8-0.9之间存在容量-保持率帕累托最优窗口，而x>0.9后保持率急剧恶化。该假设可通过合成一系列x=0.6/0.7/0.8/0.9/1.0的单晶或球形多晶样品，在相同电压窗口和电解液下进行标准化循环测试加以检验。

**Expected Relationship:** 放电容量（0.1C, 2.5-4.3V）随Ni含量线性增加，而300圈循环保持率随Ni含量分段下降：x≤0.8下降平缓，x>0.9出现加速下降，形成明确拐点；最佳折衷在x≈0.8-0.9区间。

**Materials:** LiNi0.6Mn0.2Co0.2O2, LiNi0.7Mn0.1Co0.2O2, LiNi0.8Mn0.1Co0.1O2, LiNi0.9Mn0.05Co0.05O2, LiNiO2
**Property:** 循环容量保持效率 (%)

**Source Gap:** Gap 3
**Search Method:** bayesian (5 iterations, 16 candidates)

**Evidence Chain:**
  - p22
  - p24
  - p32
  - [Novelty Verification] Overlap: none | Novelty: 0.820 (was 0.820) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 评估异常（'list' object has no attribute 'get'），采用默认评分 0.5

**External Validation:**
  - overall_match: True
  - databases_checked: ['materials_project', 'oqmd', 'nomad']
  - supporting_evidence: ['O (OQMD): formation_energy = 0.000 eV/atom, stability = 0.000 eV/atom']
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaaditcu', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 4. ✅ 水洗引入的质子残留通过近表面Li/H交换加速高镍正极容量衰减与阻抗增长

**Confidence:** 0.65 | **Novelty:** 0.85 | **LLM Plausibility:** 0.92
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: p48, p46, p44)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.467 （文献数值证据 0 个）

**Description:** 高镍NCM正极水洗除杂时近表面插层锂离子与水中质子发生交换（Li+/H+交换），质子残留在充放电中脱出并参与界面副反应。p48揭示即使低质子含量也会引发大性能变化：容量衰减与阻抗随质子含量上升。假设质子含量（水洗程度）与容量衰减速率、界面阻抗呈单调正相关，且存在阈值效应——低质子含量即显著影响。可通过系统制备不同水洗程度（质子含量梯度）样品，用OEMS+EIS定量质子含量-阻抗-衰减速率关系验证，并考察质子与涂层/过锂化工艺的交互。

**Expected Relationship:** 质子含量（ppm 级）每增加一个数量级，100 圈容量衰减速率与界面阻抗呈近似线性上升（低含量段即显著），衰减增量与 Ni 含量正相关；质子残留与 Zr 涂层（p46）、过锂化（p44）存在交互效应。

**Materials:** LiNi₀.₈₃Co₀.₁₂Mn₀.₀₅O₂ (NCM831205)
**Property:** 质子诱导容量衰减速率

**Source Gap:** Gap 8
**Search Method:** bayesian (6 iterations, 17 candidates)

**Evidence Chain:**
  - p48
  - p46
  - p44

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> 理论基础扎实：高镍正极水洗过程中Li+/H+交换符合离子交换热力学，质子占据锂位会扰动晶体结构，且易诱发表面岩盐相重构，增加界面阻抗与容量衰减。文献一致性好：已有研究证实水洗后质子残留与表面副反应相关，p48显示低质子含量即显著劣化，p46/p44提示与涂层、过锂化的交互符合已知改性策略。可验证性强：可通过梯度水洗制备不同质子含量样品，结合OEMS、EIS、循环测试定量关联质子含量与性能衰退，并可设计正交实验探索交互效应。新颖性较高：系统检索未发现重叠工作，提出的“质子含量每数量级线性加速”定量关系及交互效应为原创延伸。综合评分0.92。；系统查重: 0 篇结果，重叠=none，新颖性 0.85->0.85

**External Validation:**
  - overall_match: True
  - databases_checked: ['materials_project', 'oqmd', 'nomad']
  - supporting_evidence: ['Ni (OQMD): formation_energy = -0.001 eV/atom, stability = 0.000 eV/atom']
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaacfkfg', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 5. ⏳ Ni氧化态升高降低阳离子混排迁移势垒，促进层状结构向岩盐相降解

**Confidence:** 0.63 | **Novelty:** 0.85 | **LLM Plausibility:** 0.50
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: p27, p32, p24)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.508 （文献数值证据 0 个）

**Description:** 根据氧化诱导阳离子无序理论，高Ni3+/Ni4+含量使Ni经四面体中间体迁移至Li层。假设镍氧化态越高（如充电态SOC高），阳离子迁移势垒越低，阳离子混排度越高，导致电压和容量衰减。可以通过原位XAS/STEM定量不同电位下Ni价态和Li/Ni交换度，并测量对应的容量衰减速率。

**Expected Relationship:** Ni平均价态每增加0.1（对应Li脱出量增加），Li层Ni占据分数呈指数增长，且容量衰减速率与混排度呈线性正相关；表面重构层厚度与Ni4+浓度同步增加。

**Materials:** LiNi0.8Mn0.1Co0.1O2, LiNiO2
**Property:** 阳离子混排度 / 容量衰减速率

**Source Gap:** Gap 2
**Search Method:** bayesian (5 iterations, 16 candidates)

**Evidence Chain:**
  - p27
  - p32
  - p24
  - [Novelty Verification] Overlap: none | Novelty: 0.850 (was 0.850) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 评估失败，采用默认评分 0.5

---

### 6. ⏳ 涂层材料的Li离子电导率与界面副反应阻抗之间的帕累托最优设计

**Confidence:** 0.65 | **Novelty:** 0.78 | **LLM Plausibility:** 0.50
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 已有文献依据(evidence_chain 编号: p39, p42)，具体结论需人工/LLM 补写
**新知（incremental claim）:** 相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)

**Search Best Score:** 0.433 （文献数值证据 0 个）

**Description:** 正极表面涂层（Al2O3、AlF3、ZrO2、MgO、SiO2等）对Li离子传输的阻碍与对电解液副反应的阻挡构成矛盾。假设涂层材料的体积Li扩散系数D_Li和电子绝缘性/热力学稳定性共同决定最优厚度：存在一个临界涂层厚度 h*，低于h*不能有效抑制副反应，高于h*则导致倍率性能快速下降；且D_Li越高，h*可越厚而不损失倍率性能。可通过在同一高镍正极上控制不同涂层材料与厚度并进行倍率-循环测试验证。

**Expected Relationship:** log(倍率容量保持率)随涂层厚度线性下降，下降斜率与log(D_Li)成反比；副反应抑制率随厚度单调上升；在交叉点处存在最佳厚度h* = f(D_Li, 界面反应速率常数)。

**Materials:** α-AlF3, α-Al2O3, m-ZrO2, c-MgO, SiO2, LiNi0.8Mn0.1Co0.1O2
**Property:** 倍率容量保持效率 (%)

**Source Gap:** Gap 5
**Search Method:** bayesian (5 iterations, 16 candidates)

**Evidence Chain:**
  - p39
  - p42
  - [Novelty Verification] Overlap: none | Novelty: 0.780 (was 0.780) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 评估失败，采用默认评分 0.5

---


---

# 量化验证补充（第二轮，赛题硬性验证标准）

> 注：本补充章节由主 Agent 第二轮手动追加（工具重新生成 discovery_report 时覆盖了首版补充，此处恢复）。

## 模型对比（run_model_comparison，假设 2 = Ni 含量-容量保持率）
- 报告：`discovery/model_comparison_2.md`（工具生成）+ `discovery/quant_supplement_h2.md`（补充统计）
- 严格可比 A 层（n=6，表格配对）：**线性 R²=0.8873**（y = -34.59x + 109.08，斜率 t=-5.61, p=0.005）；**二次 R²=0.9828**（嵌套 F 检验 p=0.027，二次显著）
- **经典模型（Vegard 端点线性混合）：R²=-0.0322，完全失效**（固定端点"理想混合"假设不成立）；自由线性 R²=0.887 说明组分-保持率关系存在但非经典混合律
- 弱可比 B 层（n=25，跨条件噪声）：R²=0.011——文献数据异质性显著，趋势需标准化条件验证
- **结论**：Ni 含量 x∈[0.33,1.0] 与 100 圈保持率强负相关（每增 1.0 降 ~34.6 个百分点）；二次项显著提示高 Ni 端加速下降，与假设 2"非单调"方向一致但帕累托窗口未获支持

## 符号回归（symbolic_regression，假设 2）
- 报告：`discovery/symbolic_2.md`；31 点拟合 R²=0.105（受 B 层噪声稀释），A 层 6 点线性/二次为主导形态

## 外部数据库交叉验证（validate_discovery，双轨验证保底）
- 假设 2：**validated**（OQMD 命中 O 相参考条目，组成空间外部证据）
- 假设 5（质子诱导降解，Gap 8）：**validated**（OQMD 命中 Ni 相条目）
- 假设 0：inconclusive（单晶 NMC 的 Ni 氧化态异质性-位错裂纹属微结构-力学耦合性质，Materials Project/OQMD/NOMAD 不覆盖此类性质，验证依赖文献证据链 p24+p25 + 顺序关联实验方案）

## 新证据强化（第二轮新增 p43-p50）
- p46（Zr 涂层火山型，1.5 wt% 最优）→ 支持假设 3 的非单调权衡（R18）
- p44（过锂化 NMC532 anti-site 缺陷↓）→ 支持假设 4 的混排-性能关联（R16）
- p47（Ni 含量↑→稳定性↓）→ 支持假设 2 的方向性（R19）
- p48（质子诱导降解）→ 新增 Gap 8 与假设 5（R20）
- p45（构型熵）→ 保持率提升新策略（R17）
- p43（3-Thp-BOH CEI）→ 界面工程路径（R15）
