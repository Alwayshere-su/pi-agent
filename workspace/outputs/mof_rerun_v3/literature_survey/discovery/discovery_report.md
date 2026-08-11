# Structure-Property Relationship Discovery

**Generated:** 2026-08-11 21:30
**Total candidates explored:** 105
**Validated:** 1 | **Refuted:** 0
**Contested:** 2 | **Underexplored:** 0
**Materials Project hits:** 1

## Search Summary

Explored 5 hypotheses via Bayesian optimization and MCTS. 四象限一致性: strong=3, underexplored=0, contested=2, weak=0

---

## Discovered Structure-Property Relationships

### 1. ✅ Qst–容量非单调权衡：低压容量存在最优 Qst 窗口（火山型），高压容量随 Qst 饱和

**Confidence:** 0.87 | **Novelty:** 0.70 | **LLM Plausibility:** 0.85
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** Qst 被广泛用作亲和力指标（p37, p61），M-DOBDC 筛选给出目标窗口（p23），但未见 Qst-容量火山型曲线的定量验证；多数研究只报告单一 Qst 值而无跨体系回归
**新知（incremental claim）:** 将 Qst 从'越高越好'的直觉修正为'最优窗口'的火山型标度，量化低压与高压两种操作条件的差异化最优 Qst，为吸附剂热力学设计提供可计算准则

**Search Best Score:** 0.872 （文献数值证据 4 个）

**Description:** Cu(adci)-2 以极低 Qst₀=27.5 kJ/mol 在 15 kPa 达 2.01 mmol/g（p37）；MOF-74(Ni)-24-140 以 Qst 27–52 kJ/mol 在 1 bar 达 6.61 mmol/g（p61）；M-DOBDC/M-HKUST-1 金属取代筛选将 40–75 kJ/mol 定义为目标热力学窗口（p23）。假设低压(0.15 bar 烟气分压)容量对 Qst₀ 呈火山型（中等 Qst≈35–45 kJ/mol 最优，兼顾亲和与可逆），而 1 bar 容量随 Qst 单调上升但边际递减（受孔容上限约束）。

**Expected Relationship:** 容量(0.15bar) = α·Qst·exp(−β·Qst)（火山型，峰位 Qst*≈40 kJ/mol）；容量(1bar) = Cmax·(1−exp(−k·Qst))（饱和型）

**Materials:** Cu(adci)-2, MOF-74(Ni), M-MOF-74, NICS-24, CALF-20
**Property:** CO2 吸附容量 (mmol/g) 与等量吸附热 Qst (kJ/mol)

**Source Gap:** Gap 2
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p37: Cu(adci)-2 Qst₀=27.5 kJ/mol，298K/15kPa 容量 2.01 mmol/g
  - p61: MOF-74(Ni) Qst 27–52 kJ/mol，1 bar 容量 6.61 mmol/g（最高）
  - p7: M-MOF-74 CO₂-OMS 结合能 38–48 kJ/mol
  - p23: vdW-DF 筛选 36 金属取代，13 种落入 40–75 kJ/mol 目标窗；OMS 部分电荷为 ΔH 描述符
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.700 (was 0.700) | Queries: 3 | Results: 10 | Assessment: 基于已有文献重叠级别为“none”，当前文献库中没有任何工作提出或验证过“Qst–容量非单调权衡”这一类似主张，因此该假设在机制层面是全新的。该假设不仅揭示了低压容量与Qst之间的火山型最优窗口，还区分了高压容量随Qst饱和的不同行为，并明确指向多种MOF材料体系，具有清晰的定量关系和材料拓展性。综上，该假设的新颖性成立，值得作为原创性研究问题进行验证。
  - 预测值 27.5 kJ/mol（待实验验证，建议方案：微量热法测定零覆盖Qst，或DFT计算结合能作为代理验证）
  - 文献验证: 2.01 mmol/g — 在 12 篇论文中检索到 2 条匹配记录 (来源: p61, p61)
  - 文献验证: 27–52 kJ/mol — 在 12 篇论文中检索到 4 条匹配记录 (来源: p7, p61, p7)
  - 文献验证: 1 bar — 在 12 篇论文中检索到 10 条匹配记录 (来源: P1, p41, p41)
  - 文献验证: 6.61 mmol/g — 在 12 篇论文中检索到 4 条匹配记录 (来源: p23, p44, p23)
  - 文献验证: 40–75 kJ/mol — 在 12 篇论文中检索到 6 条匹配记录 (来源: p7, p7, p61)
  - 文献验证: 0.15 bar — 在 12 篇论文中检索到 2 条匹配记录 (来源: P1, P1)
  - 文献验证: ≈35–45 kJ/mol — 在 12 篇论文中检索到 2 条匹配记录 (来源: p7, p7)
  - 文献验证: 0.15bar — 在 12 篇论文中检索到 2 条匹配记录 (来源: P1, P1)
  - 预测值 ≈40 kJ/mol（待实验验证，建议方案：微量热法测定零覆盖Qst，或DFT计算结合能作为代理验证）
  - 文献验证: 1bar — 在 12 篇论文中检索到 10 条匹配记录 (来源: P1, p41, p41)

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.75
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证

**Scientific Explanation (LLM):**
> 理论基础：符合热力学与吸附平衡原理。低压下吸附容量受亲和力（Qst）与可逆性（解吸能耗）共同控制，火山型关系合理；高压下接近孔容饱和，容量随Qst上升但受限于孔容，饱和型模型符合Langmuir型吸附行为。文献一致性：支持证据链中Cu(adci)-2低Qst低压容量、MOF-74(Ni)高压高容量、M-MOF-74结合能窗口等均与假设定性吻合；但未直接验证40kJ/mol为最优峰位，属于合理外推。可验证性：可通过微量热法测Qst、低压与高压等温线精确拟合两种函数，也可用DFT计算不同MOF的结合能并关联容量，验证路径清晰。新颖性：检索显示无重叠文献，首次提出‘Qst-容量非单调权衡’的定量标度关系，区分低压火山型与高压饱和型，具有机制层面新意。但火山峰位参数依赖有限数据，需更多体系检验，故扣分0.15。；系统查重: 10 篇结果，重叠=none，新颖性 0.70->0.70

**External Validation:**
  - overall_match: True
  - databases_checked: ['materials_project', 'oqmd', 'hmof_core_mof', 'nomad']
  - supporting_evidence: ['MOF-74: CO2 吸附容量 = 3.0-8.6 mmol/g (文献 meta-analysis, CoRE MOF 2014 / hMOF)', 'MOF-74: Qst = 20-50 kJ/mol (文献 meta-analysis, CoRE MOF 2014 / hMOF)', 'MOF-74: CO2 吸附容量 = 3.0-8.6 mmol/g (文献 meta-analys
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaaditcu', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 2. ⏳ 湿度增强指数 η 与孔道化学描述符的定量关系（水竞争 vs 水增强的统一标度）

**Confidence:** 0.78 | **Novelty:** 0.72 | **LLM Plausibility:** 0.42
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5

**已知（prior work）:** MOF 湿态稳定性综述（p26, p32）指出水竞争是普遍问题，但未建立 η 与孔道化学描述符的定量标度；酰胺功能化 Fe-dbai（p41）与固定水策略（p49）为 2024-2025 年新发现，无统一模型
**新知（incremental claim）:** 提出湿度增强指数 η 作为统一量纲，将竞争（η<100%）与增强（η>100%）两类现象纳入同一线性标度，并以 OMS 密度与水稳定位点密度为自变量建立可检验回归

**Search Best Score:** 0.662 （文献数值证据 5 个）

**Description:** 文献中湿度对 MOF 的 CO₂ 捕获呈现方向性矛盾：NICS-24 湿态容量 −85%（水竞争，p36），Fe-dbai 在 60% RH 保持 94%（p41），PEI@MIL-101(Cr) 在 70% RH 容量反升 36%（p40），TYUT-ATZ-β 通过固定水获得超高选择性（p49）。假设存在统一描述符——孔道内强水结合位点密度与 CO₂ 结合位点的竞争比——决定湿度增强指数 η = 容量(RH)/容量(干) 的符号与大小。具体假设：η 随开放金属位点(OMS)密度升高而降低（OMS 是水的主要攻击/竞争位点），随受限稳定水合位点（如酰胺、固定水通道）密度升高而升高。

**Expected Relationship:** η = a - b·(OMS密度) + c·(水稳定位点密度)，其中 a≈94(基准), b≈0.5~1.0, c≈0.3~0.6；验证：η(Fe-dbai)=94%, η(NICS-24)=15%, η(PEI@MIL-101)=136%

**Materials:** M-MOF-74, Fe-dbai, NICS-24, PEI@MIL-101(Cr), TYUT-ATZ-beta
**Property:** CO2 容量湿度保持率 η (%)

**Source Gap:** Gap 1
**Search Method:** hybrid (10 iterations, 21 candidates)

**Evidence Chain:**
  - p36: NICS-24 湿态容量 −85%（η≈15%），水优先于 CO₂ 吸附（强氢键）
  - p41: Fe-dbai 60%RH 工作容量保持 94%（η≈94%），酰胺基团 + 受限效应增强 CO₂ 亲和
  - p40: PEI@MIL-101(Cr) 70%RH 容量 1.43 vs 干 1.05 mmol/g（η≈136%）
  - p49: TYUT-ATZ-β 固定 H₂O 于扩散通道，CO₂/N₂=2031，湿态稳定 100+ 循环
  - p7/p32: M-MOF-74 中 H₂O/NH₃ 可置换 OMS 上的 CO₂，湿态不稳定
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.720 (was 0.720) | Queries: 3 | Results: 0 | Assessment: 已有文献未提出或验证类似主张，且未发现任何重叠研究。该假设首次尝试建立湿度增强指数η与孔道化学描述符之间的统一标度，涵盖水竞争与水增强两种对立机制，并引入多种MOF材料体系，具备明确的新机制和定量关系。因此，该假设的新颖性仍然成立。

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.83
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证

**Scientific Explanation (LLM):**
> 1. 理论基础：水与CO2对吸附位点的竞争符合热力学原理，但将η归因于两种位点密度的线性叠加缺乏微观热力学依据，不同机制（竞争vs增强）的驱动力不同，难以统一为简单线性标度。2. 文献一致性：部分证据支持（如M-MOF-74水竞争、Fe-dbai受限效应），但PEI@MIL-101(Cr)的容量上升源于胺基与CO2反应且水促进胺基利用率，并非“稳定水合位点”；NICS-24与Fe-dbai测试条件（RH、温度）不同，直接比较η值不合理，证据链存在混淆。3. 可验证性：原则上可设计系列MOF调控OMS和稳定水合位点密度进行实验验证，但需明确“稳定水合位点密度”的量化定义，并控制孔径、孔环境等协变量，否则难以得到可靠标度。4. 新颖性：检索未见相同工作，但类似构效关系在其他多孔材料中已有研究，且该线性模型过于简化，并未揭示竞争/增强的微观本质，新颖性有限。综合其有合理内核但过度简化，评分较低。；系统查重: 0 篇结果，重叠=none，新颖性 0.72->0.72

---

### 3. ⏳ 胺功能化'低浓度容量 vs 湿度耐受'存在 Pareto 权衡，酰胺/超碱 IL 可突破前沿

**Confidence:** 0.82 | **Novelty:** 0.68 | **LLM Plausibility:** 0.78
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 胺功能化 DAC 吸附剂综述（p26, p22）指出胺-水竞争问题但未量化 Pareto 前沿；p36/p41/p45 为 2023-2025 个案，无跨体系对比
**新知（incremental claim）:** 建立胺功能化 MOF 的'容量-湿度耐受' Pareto 前沿，定量评估酰胺/超碱 IL 策略的突破潜力，提出 ΔE 结合能差作为 DAC 吸附剂筛选描述符

**Search Best Score:** 0.817 （文献数值证据 6 个）

**Description:** 胺功能化提升低浓度容量（NICS-24 在 2 mbar 达 0.7 mmol/g，为 CALF-20 4 倍，CO₂/N₂ 8 倍，p36）但湿态容量 −85%；而酰胺功能化 Fe-dbai 湿态保持 94%（p41）、超碱 IL 复合 MOF 在 400 ppm 达 0.58 mmol/g 且循环稳定（p45）、PEI 负载 MIL-101 湿态容量反升（p40）。假设：伯胺/二胺接枝密度升高 → 容量(400ppm) 上升但湿度保持率下降，形成 Pareto 前沿；酰胺（氢键供体弱于伯胺）与超碱 IL（位阻 + 化学吸附）可突破前沿（右上角未占据区域）。

**Expected Relationship:** 容量@400ppm = A·(胺密度)^m；保持率 = B·exp(−k·胺密度)；ΔE = E(CO2−胺) − E(H2O−胺) 为筛选描述符（ΔE>0 则保持率高）

**Materials:** NICS-24, Fe-dbai, PEI@MIL-101(Cr), 超碱IL复合MOF, mmen-Mg2(dobpdc)
**Property:** 低浓度 CO2 容量 (mmol/g@400ppm) vs 湿度容量保持率 (%)

**Source Gap:** Gap 4
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p36: NICS-24 0.7 mmol/g@2mbar（4×CALF-20），湿态 −85%
  - p41: Fe-dbai 酰胺功能化，60%RH 保持 94%，6.4 mmol/g@1bar
  - p45: 超碱 IL 复合 MOF，400ppm 下 0.58 mmol/g，循环稳定
  - p40: PEI@MIL-101(Cr)，−20°C 70%RH 容量 1.43 mmol/g（湿态反升）
  - p1: mmen-Mg₂(dobpdc) 中 H₂O 影响链式吸附
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.680 (was 0.680) | Queries: 3 | Results: 0 | Assessment: 已有文献未提出或验证“低浓度容量与湿度耐受存在 Pareto 权衡”这一主张，当前假设与现有工作无重叠。该假设引入了新的定量权衡关系，并提出了超碱 IL 复合 MOF 等突破性材料体系，具有机制与材料层面的双重新颖性。因此，该研究假设的新颖性仍然成立。

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.70
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证

**Scientific Explanation (LLM):**
> 理论基础：符合吸附热力学与竞争吸附原理。伯胺接枝密度增加会提高CO2亲和位点数量，但强极性胺基同时增强水分子竞争吸附，导致湿度耐受性下降，符合ΔE描述符的物理逻辑。文献一致性：NICS-24、Fe-dbai、超碱IL复合MOF及PEI@MIL-101的证据链分别支持胺功能化容量提升、酰胺弱氢键保湿度、位阻型超碱IL抗水及聚合物湿态亲水增容，但PEI湿态反升可能源于低温水凝聚或载体孔道亲水协同，不完全支持单一Pareto权衡。可验证性：可通过控制接枝密度、湿度系列实验及DFT计算结合能ΔE直接验证，定量关系可拟合。新颖性：检索显示无重叠，提出'Pareto前沿'及超碱IL突破路径具有机制新颖性，但低浓度容量与湿度保持率的普适权衡在各类胺吸附剂中已有间接体现，故不完全全新。综合评分为0.78，假设方向合理但需细化PEI异常机制及ΔE适用范围。；系统查重: 0 篇结果，重叠=none，新颖性 0.68->0.68

---

### 4. ⏳ MOF-74(Ni) 合成温度-时长响应曲面：容量与 Qst 存在非单调最优窗口

**Confidence:** 0.82 | **Novelty:** 0.65 | **LLM Plausibility:** 0.45
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5

**已知（prior work）:** p61 报告了单一最优合成条件（140°C/24h）但无系统 DoE；p44 报告 MW 方法改进；未见 MOF-74 合成温度-时长-容量响应曲面文献
**新知（incremental claim）:** 提出 MOF-74(Ni) 合成参数-性能的二次响应面模型，将离散'最佳条件'升级为连续可外推的合成-性能映射

**Search Best Score:** 0.816 （文献数值证据 8 个）

**Description:** MOF-74(Ni) 在 140°C/24 h 合成条件（冷凝回流）下达 8.29/6.61 mmol/g（273/298 K），为文献常规合成的 2.0/2.1 倍，Qst 可调 27–52 kJ/mol（p61）；CALF-20 微波合成时间缩短 12 倍、容量 +20%（p44）。假设：合成温度 T 与时长 t 对容量存在响应曲面容量 = f(T, t)，最优窗口位于中等温度×长时长（结晶度与缺陷/OMS 暴露的平衡）；Qst 随合成温度单调可调（缺陷密度调控）。预测 120–140°C 区间存在容量极大值，超出后因团聚/相变下降。

**Expected Relationship:** 容量 = a + b·T + c·t + d·T² + e·T·t（二次响应面，鞍点/极大值在 T*≈130±15°C）；Qst = q0 + q1·T（线性可调）

**Materials:** MOF-74(Ni), CALF-20
**Property:** CO2 容量 (mmol/g) vs 合成温度 (C) / 时长 (h)

**Source Gap:** Gap 5
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p61: MOF-74(Ni)-24-140 为 2.0/2.1× 文献值；Qst 27–52 kJ/mol 可调（合成条件调节）
  - p44: CALF-20 MW 合成 → 容量 +20%，时间 −12 倍，产率 97%
  - p12: Zr-MOF 凝胶形态设计（合成条件-形态-性能关联）
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.650 (was 0.650) | Queries: 3 | Results: 5 | Assessment: 已有文献未提出或验证类似主张，重叠级别为“none”，因此不存在直接竞争或重复。该假设以MOF-74(Ni)为对象，系统考察合成温度与时长对CO₂容量和吸附热（Qst）的非单调响应曲面，并明确“最优窗口”这一定量机制，具有材料体系与关系层面的新颖性。综上，该研究假设的新颖性仍然成立。

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.60
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证

**Scientific Explanation (LLM):**
> 理论基础：中等温度×长时长有利于平衡结晶度与缺陷/OMS暴露，非单调响应在原理上可行，但二次响应面和Qst随T线性可调的假设缺乏坚实理论依据，属于经验拟合。文献一致性：所引MOF-74(Ni)容量为文献值2.0/2.1倍缺乏可信参考基准，与已知Ni-MOF-74高容量事实冲突；CALF-20微波合成属跨体系过程强化证据，不能直接支持该响应曲面。可验证性：可通过系统变温变时合成、CO2等温线和Clausius-Clapeyron计算Qst验证，实验路径明确。新颖性：检索显示无直接重叠，但‘合成条件-缺陷-性能’优化思路在MOF领域较普遍，且Qst线性调控和T*窗口未给出机制性标度律，新颖性有限。总体评分偏低，反映假设具备可检验性但定量表述和证据链可靠性不足。；系统查重: 5 篇结果，重叠=none，新颖性 0.65->0.65

---

### 5. ⏳ 柔性 gate-opening MOF 的选择性-温度反常正相关（S 随 T 升高）由开孔阈值-温度耦合驱动

**Confidence:** 0.70 | **Novelty:** 0.75 | **LLM Plausibility:** 0.78
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 0.0/5

**已知（prior work）:** 柔性 MOF 的 gate-opening 吸附研究（p48）报道了数据但未解释选择性-温度反常；p14 的滞后分析聚焦机理而非温度标度；刚性 MOF 温度标度律（p61）为经典对照
**新知（incremental claim）:** 提出'开孔阈值-温度耦合'假说解释柔性 MOF 选择性随温度升高的反常，将 dS/dT 符号与开孔应变能关联，为 TSA 操作窗口设计提供新准则（热再生可增强分离度）

**Search Best Score:** 0.664 （文献数值证据 2 个）

**Description:** 刚性 MOF 遵循 van't Hoff 行为：容量与选择性随温度升高而下降（MOF-74(Ni)：8.29→6.61 mmol/g，273→298 K，p61）。但柔性 ZnDatzBdc 的 CO₂/N₂ 选择性从 273 K 的 107 升至 298 K 的 129（CO₂/CH₄：35→44）（p48）。假设该反常源于 gate-opening 的开孔阈值压力随温度变化：CO₂ 在更高温度下跨越开孔阈值（阈值压力下降），进入孔内吸附，而 N₂/CH₄ 始终低于阈值被排除，导致选择性净增。预测柔性 MOF 的选择性-温度斜率 dS/dT > 0 的温区与开孔应变能正相关。

**Expected Relationship:** S(T) = S0·exp(λ·(T−T0))，λ>0 反常；λ ∝ 开孔应变能/孔道柔性；刚性 MOF 的 λ<0 为对照

**Materials:** ZnDatzBdc, ELM-11, MIL-53, 柔性MOF
**Property:** CO2/N2 选择性随温度的变化 dS/dT

**Source Gap:** Gap 3
**Search Method:** mcts (10 iterations, 21 candidates)

**Evidence Chain:**
  - p48: ZnDatzBdc CO₂/N₂=107(273K)→129(298K)；CO₂/CH₄=35(273K)→44(298K)；S 形等温线、gate-opening 开/闭相变
  - p61: MOF-74(Ni) 容量 8.29(273K)→6.61(298K)，经典负温度依赖
  - p14: 双胺 MOF 协同吸附滞后揭示一阶相变与链聚合机理（温度-占据曲线）
  - [Novelty Verification] Overlap: none | Adjusted novelty: 0.750 (was 0.750) | Queries: 3 | Results: 0 | Assessment: 已有文献检索显示该假设与现有工作无重叠，未有研究明确提出或验证“柔性MOF开孔阈值-温度耦合导致CO2/N2选择性随温度反常正相关”这一主张。该假设引入了新的机制解释（开孔阈值与温度耦合）及定量关系（dS/dT为正），并针对ZnDatzBdc、ELM-11、MIL-53等具体柔性MOF体系，具备足够的新颖性。因此，该研究假设的新颖性仍然成立。

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.80
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证
  - `?`: ❌ 未查证

**Scientific Explanation (LLM):**
> 该假设基于柔性MOF的gate-opening相变热力学提出合理机制：开孔阈值压力随温度下降可使CO2在高温下进入孔道而N2/CH4被排除，从而选择性反常升高，这符合相变压力与温度的关系（若开孔吸附总焓为正）。文献中ZnDatzBdc等体系确实表现出S型等温线和选择性随温度升高的现象，与假设一致，但普适性仍需更多体系验证。假设可通过变温等温线、原位PXRD和分子模拟直接检验，可验证性很高。新颖性检索显示无重叠，提出的dS/dT与开孔应变能正相关关系具有新意。综合看，机理与定量关系较新颖，但开孔阈值随温度变化的方向可能因体系而异，故评分适中偏高。；系统查重: 0 篇结果，重叠=none，新颖性 0.75->0.75

---
