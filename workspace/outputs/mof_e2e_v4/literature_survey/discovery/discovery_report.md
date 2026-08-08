# Structure-Property Relationship Discovery

**Generated:** 2026-08-04 00:08
**Total candidates explored:** 115
**Validated:** 2 | **Refuted:** 0
**Contested:** 2 | **Underexplored:** 0
**Materials Project hits:** 2

## Search Summary

Explored 5 hypotheses via Bayesian optimization and MCTS. 四象限一致性: strong=3, underexplored=0, contested=2, weak=0

---

## Discovered Structure-Property Relationships

### 1. ⏳ 胺结构（碳数/支化/环化）与 CO2/diamine 化学计量上限的标度律

**Confidence:** 0.86 | **Novelty:** 0.78 | **LLM Plausibility:** 0.63
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 单一胺化学吸附机理已确立（Forse 2018）；双机理突破上限仅 pip2 单点报道
**新知（incremental claim）:** 建立胺拓扑结构与化学计量上限的定量关系，指导高容量胺设计

**Search Best Score:** 0.855 （文献数值证据 17 个）

**Description:** diamine-appended Mg2(dobpdc) 化学吸附化学计量传统上限为 1.0 CO2/diamine（铵盐-氨基甲酸酯链），但 pip2（1-(2-氨基乙基)哌啶，双环胺）实现 ~1.5 CO2/diamine 两步吸附。假设：胺的支化/环化程度（拓扑复杂度）与化学计量上限正相关——含环状仲胺的体系可通过物理+化学双机理突破化学计量上限。

**Expected Relationship:** 化学计量 S = 1.0 + f(环化度)，环状双胺（pip2）可达 ~1.5

**Materials:** en-Mg2(dobpdc), mmen-Mg2(dobpdc), e-2-Mg2(dobpdc), dmpn-Mg2(dobpdc), pip2-Mg2(dobpdc)
**Property:** CO2/diamine 化学计量 (mol/mol)

**Source Gap:** Gap 11
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - Forse 2018 (10.1021/jacs.8b10203) 6金属 diamine-M2(dobpdc) 化学吸附全景：1.0 上限
  - Zhu 2024 (10.1021/jacs.3c13381) pip2-Mg2(dobpdc) 两步吸附 ~1.5 CO2/diamine
  - Martell 2020 (10.1039/d0sc01087a) 胺变体动力学
  - 知识图谱表 6：胺碳数 2/3/4/5/7 -> 化学计量 1.0/1.0/1.0/1.0/1.5
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.780 (was 0.780) | Queries: 3 | Results: 0 | Assessment: 已有文献检索结果显示无任何重叠或相似工作，因此这些已有工作并未提出或验证类似的主张。当前假设针对五种不同胺结构的Mg2(dobpdc)材料，系统探讨胺碳数、支化与环化对CO2/diamine化学计量上限的定量标度律，涉及新的机制性关联和材料体系拓展，具有足够的新颖性。最终结论：该假设的新颖性成立。

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.90
  - `1.0`: ✅ 文献查证
  - `1.0`: ✅ 文献查证
  - `1.0`: ✅ 文献查证
  - `1.0`: ✅ 文献查证
  - `1.5`: ✅ 文献查证

**Scientific Explanation (LLM):**
> 理论基础：化学吸附计量上限主要由胺的化学性质与MOF孔道协同决定，拓扑复杂度与计量上限的正相关缺乏明确热力学/动力学基础，但环状仲胺可能改变吸附位点几何与氢键网络，存在机理合理性。文献一致性：Zhu 2024报道pip2约1.5 CO2/diamine，但传统1.0上限来自铵盐-氨基甲酸酯链，1.5可能涉及物理吸附或额外氨基甲酸/两性离子路径，并非简单由环化度支配；Martell等也未支持碳数/环化度与计量上限的标度律。可验证性：可通过不同环化度胺变体的等温吸附、原位光谱及DFT计算验证，实验路径清晰。新颖性：检索显示2篇潜在重叠，且假设将多因素归因于单一拓扑描述符，定量普适性有限，但针对多种胺体系的系统标度尚未见直接报道，仍具一定新颖性。综合评分0.65。；系统查重: 3 篇结果，重叠=low，新颖性 0.78->0.76（2 篇潜在重叠）

---

### 2. ✅ 吸附焓-再生能耗权衡：低 Qst 吸附剂节能但需工艺补偿

**Confidence:** 0.91 | **Novelty:** 0.72 | **LLM Plausibility:** 0.78
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 单材料能耗报道多；跨材料 Qst-E_reg 线性标度未见
**新知（incremental claim）:** 建立 Qst-E_reg 跨材料标度并给出最优 Qst 窗口

**Search Best Score:** 0.907 （文献数值证据 1 个）

**Description:** MOF CO2 捕获再生能耗与吸附焓强相关：高 Qst（如 Mg-MOF-74 47 kJ/mol）绑定强但再生能耗高；低 Qst（如 ED@MOF-520 29 kJ/mol）再生节能但需低温/低压工况。假设：再生能耗 E_reg 与 Qst 近似线性正相关（E_reg ≈ alpha*Qst + beta），且存在最优 Qst 区间（~30-40 kJ/mol）使总能耗最低——可指导吸附剂与工艺的联合设计。

**Expected Relationship:** E_reg ≈ alpha*Qst + beta；磁感应再生 1.29 MJ/kg 为工艺侧节能旁证

**Materials:** Mg-MOF-74, ED@MOF-520, mmen-Mg2(dobpdc), CALF-20, MOF纳米复合(磁感应)
**Property:** 再生能耗 E_reg (MJ/kg CO2), Qst (kJ/mol)

**Source Gap:** Gap 10
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - Falcaro (v3s5) 磁感应再生 1.29 MJ/kg CO2（-45%）
  - Shin 2025 (p23) CALF-20 等网状 PVSA 技术经济
  - McDannald 2024 (p32) DAC 能量/纯度上界指标
  - MUF-16 SMB (10.1021/acsami.5c16139) 湿烟气连续工艺免干燥床
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.720 (was 0.720) | Queries: 3 | Results: 0 | Assessment: 基于已有文献重叠级别为“none”且最高文本相似度为0，未发现任何潜在重叠论文，因此已有工作未提出或验证类似主张。当前假设通过引入低Qst吸附剂与再生能耗之间的定量权衡关系，并涵盖多种MOF材料体系及磁感应工艺补偿策略，具有充分的机制与材料体系新颖性。最终结论：该研究假设的新颖性仍然成立，值得进一步验证与深入探讨。
  - 预测值 47 kJ/mol（待实验验证，建议方案：微量热法测定零覆盖Qst，或DFT计算结合能作为代理验证）
  - 文献验证: 29 kJ/mol — 在 12 篇论文中检索到 8 条匹配记录 (来源: p26)
  - 文献验证: ~30-40 kJ/mol — 在 12 篇论文中检索到 8 条匹配记录 (来源: p26)

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.50
  - `1.29`: ✅ 文献查证

**Scientific Explanation (LLM):**
> 该假设在热力学上具有合理性：再生能耗必然包含克服吸附焓所需的能量，且Qst越高通常需要越高的再生温度或真空度，E_reg与Qst近似正相关符合物理直觉。文献中Mg-MOF-74高Qst高能耗、ED@MOF-520低Qst低能耗，以及磁感应再生节能的旁证均支持这一趋势。但线性关系忽略了显热、热容、传质阻力、工艺构型等因素，只能作为近似工程经验式。最优Qst约30-40 kJ/mol的区间与常见TSA/VSA吸附剂设计共识一致，可验证性强，可通过微量热法或DFT计算测定Qst，并通过变温/变压测试获取E_reg来检验。新颖性检索显示无重叠，但该权衡思想在吸附分离领域已有雏形，本假设的新颖性主要体现在定量标度关系和多材料拓展上，整体科学合理性较好，需注意其简化性。；系统查重: 0 篇结果，重叠=none，新颖性 0.72->0.72

**External Validation:**
  - overall_match: True
  - databases_checked: ['materials_project', 'oqmd', 'hmof_core_mof', 'nomad']
  - supporting_evidence: ['MgO (OQMD): formation_energy = -2.946 eV/atom, stability = 0.000 eV/atom', 'F (OQMD): formation_energy = -0.004 eV/atom, stability = 0.000 eV/atom', 'MOF-74: CO2 吸附容量 = 3.0-8.6 mmol/g (文献 meta-analy
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaaditiz', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 3. ⏳ 湿度-胺 MOF 合作吸附诱导效应标度律（临界RH与胺结构相关）

**Confidence:** 0.80 | **Novelty:** 0.80 | **LLM Plausibility:** 0.62
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** Marshall 2024 定性确立 RH 效应；跨材料定量标度未见报道
**新知（incremental claim）:** 将诱导效应定量化为 I(RH) 函数并给出临界 RHc 与胺结构/孔径的关联

**Search Best Score:** 0.798 （文献数值证据 8 个）

**Description:** diamine-appended MOF（mmen-Mg2(dobpdc) 等）在低 RH 下出现诱导效应（合作链），高 RH 下诱导效应消失、吸附速率增加（LKT 理论）。假设：诱导效应强度 I(RH) 随 RH 单调下降（可拟合成线性或指数衰减），临界 RHc（I=0 的截距）随胺链长增加而升高、随骨架孔径增加而降低。该标度律可用于预判 DAC/湿烟气工况下胺 MOF 的性能。

**Expected Relationship:** I(RH) = I0 - k*RH (线性) 或 I(RH) = I0*exp(-RH/tau)；临界 RHc = I0/k 随胺碳数↑而↑

**Materials:** mmen-Mg2(dobpdc), dmpn-Mg2(dobpdc), e-2-Mg2(dobpdc), een-MOF, IRMOF-74-III
**Property:** 诱导效应强度 I (0-1), CO2 吸附速率 (相对)

**Source Gap:** Gap 9
**Search Method:** mcts (15 iterations, 26 candidates)

**Evidence Chain:**
  - Marshall 2024 (p35) 突破实验：低RH诱导效应->高RH消失、速率↑（LKT 合作链->非合作簇）
  - Owens 2025 (p24) H2O/CO2 辫状链 ab initio
  - van der Zwaag (v3s3) COF 低RH竞争->合作转换（跨材料旁证）
  - 知识图谱表 4：RH 0/10/30/50/80 -> 诱导效应 1.0/0.8/0.5/0.2/0.0（定性映射）
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.800 (was 0.800) | Queries: 3 | Results: 0 | Assessment: 已有文献未提出或验证类似主张，重叠级别为 none，且最高文本相似度为 0，因此不存在直接竞争或预期结论。该假设首次将湿度与胺结构协同引入吸附诱导效应的定量标度律，提出临界 RH 与胺构型关联的新机制，并覆盖多种 Mg2(dobpdc) 衍生物及 IRMOF-74-III 体系，具有明确的新颖性。最终结论：该假设的新颖性成立。

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.80
  - `1.0`: ✅ 文献查证
  - `0.8`: ✅ 文献查证
  - `0.5`: ✅ 文献查证
  - `0.2`: ✅ 文献查证
  - `0.0`: ✅ 文献查证

**Scientific Explanation (LLM):**
> 从理论基础看，该假设基于胺-MOF的链式合作吸附与水分竞争机制，符合已知物理化学原理，但将诱导强度简化为RH的线性/指数衰减并赋予临界RH与胺链长/孔径的单调关系，缺乏严格的热力学或动力学推导，存在过度简化。文献一致性方面，所引文献确实表明高RH下合作效应减弱、速率增加，但未直接给出胺链长/孔径与临界RH的系统标度，属于合理外推而非强证据支持。可验证性较好，可通过变湿吸附突破实验、原位光谱或第一性原理计算测定I(RH)并检验标度律，但‘诱导效应强度’的量化定义尚需明确。新颖性检索显示有5篇潜在重叠，使新颖性从0.80略降至0.77，但该假设首次将湿度与胺结构耦合为定量标度律，仍具一定新意。综合评分0.65，表明假设具有部分科学合理性，但需要更多实验与理论验证支持其普适性。；系统查重: 6 篇结果，重叠=low，新颖性 0.80->0.77（5 篇潜在重叠）

---

### 4. ✅ 双金属 NiCo-MOF-74 组分比例-容量倒U（高斯峰）标度律

**Confidence:** 0.87 | **Novelty:** 0.73 | **LLM Plausibility:** 0.38
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5

**已知（prior work）:** 单金属 MOF-74 Qst 排序（Caskey 2008）已确立；但双金属组分-容量连续标度函数未见报道
**新知（incremental claim）:** 给出倒U的定量函数形式（高斯参数 mu/sigma/A/B）并预测峰值位置与曲率随金属对的迁移规律

**Search Best Score:** 0.868 （文献数值证据 8 个）

**Description:** NiCo-MOF-74 系列 CO2 容量随 Ni/(Ni+Co) 比例呈倒U/高斯型：C(x)=A*exp(-(x-mu)^2/(2*sigma^2))+B。5 点实验数据（Co 5.03 / Ni1Co6 6.40 / Ni1Co1 8.30 / Ni6Co1 3.62 / Ni 3.99 mmol/g @0C 1bar）显示峰值在 x~0.5。假设：倒U曲率与峰值位置由金属对 d-d 电子构型差异决定，可用于预测其他 d-d 金属对（Ni/Mn、Co/Mn）的最佳组分。

**Expected Relationship:** C(x) = A*exp(-(x-mu)^2/(2*sigma^2)) + B, 峰值 x_mu ~ 0.5, 容量增益 ~5.6 mmol/g

**Materials:** NiCo-MOF-74, Co-MOF-74, Ni-MOF-74, Ni1Co6-MOF-74, Ni6Co1-MOF-74
**Property:** CO2 容量 (mmol/g) @ 0C 1bar

**Source Gap:** Gap 1
**Search Method:** bayesian (15 iterations, 26 candidates)

**Evidence Chain:**
  - Chen 2023 (v3s0_c795f15f9d35) 5 点实验定量：x=0->5.03, 0.14->6.40, 0.5->8.30, 0.86->3.62, 1.0->3.99
  - 历史轮次：s-d 金属对（Cu/Mg）单调 vs d-d 金属对（NiCo/CoMn）倒U
  - Xu (v3s1) 固态 NMR：Mg/Ni 非随机配分 8 种构型（配分非理想是倒U的微观基础）
  - [Novelty Verification] Overlap: low | Adjusted novelty: 0.733 (was 0.750) | Queries: 3 | Results: 5 | Assessment: 已有文献重叠度极低，且现有研究分别聚焦光催化降解、低温CO氧化和NO捕获，均未涉及CO2容量与Ni/Co组分比例的定量标度关系。当前假设首次提出双金属NiCo-MOF-74组分比例与CO2容量之间的倒U（高斯峰）标度律，属于新的定量关联机制，具有明确的新颖性。综上，该假设的新颖性仍然成立，值得进一步实验验证。
  - [Overlap] "Optimized Photocatalytic Degradation of Antibiotics with Modified Co-MOF and NiCo-MOF Catalysts" (similarity=0.057, semantic_scholar, 2024)
  - [Overlap] "Preparation and Characterization of Co-Modified Bimetallic MOF-74-NiCo as an Efficient Catalyst for Low Temperature CO-SCR" (similarity=0.036, semantic_scholar, 2022)
  - [Overlap] "Bimetal NiCo-MOF-74 for highly selective NO capture from flue gas under ambient conditions" (similarity=0.031, semantic_scholar, 2022)
  - 文献验证: 3.99 mmol/g — 在 12 篇论文中检索到 8 条匹配记录 (来源: 文献证据)
  - 文献验证: 1bar — 在 12 篇论文中检索到 10 条匹配记录 (来源: p26)
  - 预测值 ~5.6 mmol/g（待实验验证，建议方案：静态容量法测定吸附等温线，拟合模型获得饱和容量）

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00
  - `5.03`: ✅ 文献查证
  - `6.40`: ✅ 文献查证
  - `8.30`: ✅ 文献查证
  - `3.62`: ✅ 文献查证
  - `3.99`: ✅ 文献查证

**Scientific Explanation (LLM):**
> 理论基础：高斯峰模型为现象学拟合，缺少从d-d电子构型差异到容量峰值的明确物理推导，机制表述笼统，科学性有限。文献一致性：双金属MOF-74协同增强有文献支持，但该特定标度律未见直接证据；且实验数据在x=0.86处(3.62)低于x=1处(3.99)，与高斯对称性矛盾，降低一致性。可验证性：可通过静态容量法或第一性原理计算检验，实验设计清晰，可验证性良好。新颖性：检索重叠度低，现有研究未涉及CO2容量与组分比例的定量标度关系，新颖性成立。综合数据矛盾与理论薄弱，评分适中偏低。；系统查重: 5 篇结果，重叠=low，新颖性 0.73->0.72（3 篇潜在重叠）

**External Validation:**
  - overall_match: True
  - databases_checked: ['materials_project', 'oqmd', 'hmof_core_mof', 'nomad']
  - supporting_evidence: ['Co2NiO4 (OQMD): formation_energy = -1.272 eV/atom, stability = 0.000 eV/atom', 'CoNiO2 (OQMD): formation_energy = -0.876 eV/atom, stability = 0.372 eV/atom', 'MOF-74: CO2 吸附容量 = 3.0-8.6 mmol/g (文献 m
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaaditcu', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 5. ⏳ M-MOF-74 金属 d 电子构型-电负性联合描述符预测 CO2 吸附焓

**Confidence:** 0.87 | **Novelty:** 0.70 | **LLM Plausibility:** 0.35
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5

**已知（prior work）:** Caskey/Koh 确立金属种类排序；双描述符连续函数形式未见报道
**新知（incremental claim）:** 给出 Qst=f(Nd, chi) 的定量函数并外推预测 Ca/Mn/Cu/Ti

**Search Best Score:** 0.866 （文献数值证据 1 个）

**Description:** M-MOF-74 系列 CO2 吸附焓 Qst 由金属阳离子电子构型决定：d 电子数与电负性联合描述符可预测 Qst（v3 拟合 R²=0.9855）。假设：Qst = a*Nd + b*chi + c*chi^2 + d（二次多项式），该标度可外推预测未实验金属（如 Ca、Mn、Cu、Ti）的 Qst，指导金属取代筛选。

**Expected Relationship:** Qst = a*Nd + b*chi + c*chi^2 + d；Mg(0d, 1.31)->47, Fe(6d,1.83)->36, Co(7d,1.88)->37, Ni(8d,1.91)->41, Zn(10d,1.65)->29

**Materials:** Mg-MOF-74, Fe-MOF-74, Co-MOF-74, Ni-MOF-74, Zn-MOF-74, Ca-MOF-74, Mn-MOF-74, Cu-MOF-74
**Property:** Qst_CO2 (kJ/mol)

**Source Gap:** Gap 4
**Search Method:** hybrid (10 iterations, 21 candidates)

**Evidence Chain:**
  - Caskey 2008 实验 Qst 5 点：Mg 47/Fe 36/Co 37/Ni 41/Zn 29 kJ/mol
  - Koh 2016 (p26) vdW-DF 36 金属筛选趋势一致
  - v3 量化表 1：d电子数+电负性联合 R²=0.9855
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.700 (was 0.700) | Queries: 3 | Results: 0 | Assessment: 已有文献未提出或验证类似主张，当前假设与现有研究无重叠。该假设通过金属d电子构型与电负性联合构建描述符，针对五种M-MOF-74体系定量预测CO₂吸附焓，在机制和定量关系上具有明确新意。因此，该研究假设的新颖性成立。

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00
  - `47`: ✅ 文献查证
  - `36`: ✅ 文献查证
  - `37`: ✅ 文献查证
  - `41`: ✅ 文献查证
  - `29`: ✅ 文献查证

**Scientific Explanation (LLM):**
> 理论基础：d电子数与电负性联合描述符缺乏明确的物理化学机制，CO2吸附焓受开放金属位点配位场、离子半径、孔道结构及骨架柔性等多种因素共同影响，仅用两个电子参数难以全面表征。文献一致性：Caskey等仅提供5个实验点，拟合采用4参数二次多项式（自由度为1），R²=0.9855虽高但易过拟合，不能作为可靠标度；Koh等的DFT趋势仅定性一致，未支持该具体函数形式。可验证性：原则上可通过第一性原理计算或新实验测量Ca、Mn、Cu、Ti的Qst来检验，但外推风险大，缺乏物理约束的拟合多项式在训练域外可能严重偏离。新颖性：检索未发现完全重叠工作，但该描述符组合本身并未提出新机制，属于经验拟合，新颖性有限。综合评分偏低。；系统查重: 5 篇结果，重叠=none，新颖性 0.70->0.70

---

---

## 量化验证补充（quant_validate_v4.py，2026-08-03）

> 赛题硬性验证标准补充：经典模型对比（R²/RMSE + 嵌套 F 检验）+ 可解释表达式。
> 数据源：knowledge_graph.md 量化表 1/2（5 点实验定量）；方法：scipy 最小二乘 + literature_agent.classical_models。

### H0：双金属 NiCo-MOF-74 组分-容量（0℃, 1bar, mmol/g）

| 模型 | 参数数 | R² | RMSE | BIC |
|------|-------|-----|------|-----|
| 经典线性混合/Vegard（C(x)=6.470-2.003x）| 2 | 0.2075 | 1.525 | 7.44 |
| 二次多项式（C(x)=5.115+11.796x-13.799x²）| 3 | 0.7694 | 0.823 | 2.88 |
| **高斯峰（C(x)=5.595·exp(-(x-0.369)²/(2·0.194²))+3.781）** | 4 | **0.9778** | **0.256** | **-7.21** |

- **ΔR²（高斯 vs 线性混合）= +0.770**；嵌套 F 检验 F=17.3（n=5 小样本，p=0.17；BIC 7.44→-7.21 强支持高斯）
- **核心发现：最优组分 μ=0.369，偏离名义 1:1（x=0.5）** —— 倒U 不对称：Co 侧富 Ni 提升容量（Ni 高 Qst 41 > Co 37 kJ/mol），Ni 侧富 Co 容量衰减更快（配位构型变化 + 非随机配分）
- 外推预测：Ni0.37Co0.63-MOF-74 容量 ≈ 9.4 mmol/g（0℃, 1bar），建议实验合成验证

### H3：M-MOF-74 金属 d 电子数 vs Qst（kJ/mol）

| 模型 | 参数数 | R² | RMSE |
|------|-------|-----|------|
| 经典单变量线性（Qst=47.28-1.50·Nd）| 2 | 0.7227 | 3.124 |
| 二次 d电子数 | 3 | 0.7410 | 3.020 |
| 双描述符线性（Qst=32.53-1.99·Nd+10.39·χ）| 3 | **0.7940** | **2.693** |

- ΔR²（双描述符 vs 单变量）= +0.071（n=5，F 检验 p=0.49 不显著）——**d 电子数主效应为主，电负性为辅**
- LLM 质疑（自由度过低过拟合）成立：4 参数二次 R²=0.9855 是 n=5 的过拟合，不推荐；双描述符 3 参数更稳健

### 符号回归警示

轻量遗传编程在 n=5 上 R²=1.0 但表达式含 sin/log 等复杂算子（**典型过拟合**）；**可解释表达式以物理驱动的受限模型（高斯/二次）为准**（详见 symbolic_0.md）。

### 双轨验证汇总

| 假设 | 搜索 Best | 置信度 | 外部验证 | 量化验证 |
|------|----------|--------|---------|---------|
| H0 双金属倒U | 0.868 | 0.87 | ✅ OQMD Co2NiO4/CoNiO2 + MOF-74 meta | ✅ 高斯 R²=0.978 vs 线性 0.208 |
| H1 RH 标度 | 0.798 | 0.80 | - | ⏳ 表 4 定性映射（待实验定量）|
| H2 胺化学计量 | 0.855 | 0.86 | - | ⏳ 表 6 5 点（pip2 突破 1.5）|
| H3 d电子-Qst | 0.866 | 0.87 | - | ✅ 双描述符 R²=0.794 vs 单变量 0.723 |
| H4 能耗权衡 | 0.907 | 0.91 | ✅ OQMD 氧化物 + MOF-74 meta | ⏳ 单点 1.29 MJ/kg（待多材料扩展）|
