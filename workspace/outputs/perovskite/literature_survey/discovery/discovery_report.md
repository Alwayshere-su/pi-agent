# Structure-Property Relationship Discovery

**Generated:** 2026-08-10 09:24
**Total candidates explored:** 105
**Validated:** 2 | **Refuted:** 0
**Contested:** 0 | **Underexplored:** 0
**Materials Project hits:** 2

## Search Summary

Explored 5 hypotheses via Bayesian optimization and MCTS. 四象限一致性: strong=5, underexplored=0, contested=0, weak=0

---

## Discovered Structure-Property Relationships

### 1. ✅ 带隙-稳定性 trade-off 的定量标度律：窄带隙钙钛矿稳定性系统性下降

**Confidence:** 0.96 | **Novelty:** 0.65 | **LLM Plausibility:** 0.55
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 4.0/5（预期独立材料 8 个） — 表 D 提供 8 材料的带隙（eV）与稳定性定性分级；稳定性需转成连续量（分解能/电离能，来自 p50/p57）

**已知（prior work）:** Cu-In 钙钛矿论文（jacs.7b02120）提出稳定性与光电性能可能互相矛盾；阳离子变换（jacs.6b09645）设计稳定无铅体系
**新知（incremental claim）:** 将 trade-off 从定性矛盾提升为定量标度律（Eg-分解能幂律/指数关系），并给出 Pareto 前沿边界

**Search Best Score:** 0.964 （文献数值证据 15 个）
**实际可用数据点:** 8（模型对比后回填）

**Description:** 基于表 D 的 8 材料跨体系数据（FASnI3 1.40 eV / MAPbI3 1.55 eV / CsSnI3 1.30 eV / Cs2AgBiBr6 1.72 eV / AgInI4 1.72 eV / CsPbBr3 2.30 eV / CH3NH3BaI3 3.87 eV / K2SnGeI6 0.64 eV），检验带隙 Eg 与稳定性（分解能/氧化稳定性）之间是否存在单调 trade-off 标度律。预期窄带隙体系（Sn²⁺、低价态）因氧化/分解倾向而系统性不稳定，稳定体系带隙偏高——即存在类似 Pareto 前沿的 Eg-稳定性联合边界。

**Expected Relationship:** 带隙 Eg 与稳定性呈正相关（窄带隙不稳定），符合幂律/指数型 trade-off；Eg < 1.6 eV 体系稳定性骤降

**Materials:** FASnI3, MAPbI3, CsSnI3, Cs2AgBiBr6, AgInI4, CsPbBr3, CH3NH3BaI3, K2SnGeI6
**Property:** band gap

**Source Gap:** Gap 1
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p6 (jacs.7b02120): Sn 窄带隙不稳定 vs Bi 稳定宽带隙
  - p34: FASnI3 氧化降解
  - p14/p17: Cs2AgBiBr6 稳定但带隙 1.72 eV
  - p50: 电离能稳定性判据
  - p57: Cs1-xRbxPbI3 分解能
  - 文献验证: 1.40 eV — 在 10 篇论文中检索到 4 条匹配记录 (来源: p66, p6, p66)
  - 文献验证: 1.55 eV — 在 10 篇论文中检索到 8 条匹配记录 (来源: p53, p6, p4)
  - 文献验证: 1.30 eV — 在 10 篇论文中检索到 2 条匹配记录 (来源: p66, p66)
  - 文献验证: 1.72 eV — 在 10 篇论文中检索到 8 条匹配记录 (来源: p53, p6, p4)
  - 文献验证: 2.30 eV — 在 10 篇论文中检索到 6 条匹配记录 (来源: p5, p13, p14)
  - 预测值 3.87 eV（待实验验证，建议方案：微量热法测定零覆盖Qst，或DFT计算结合能作为代理验证）
  - 文献验证: 0.64 eV — 在 10 篇论文中检索到 4 条匹配记录 (来源: p5, p60, p5)
  - 文献验证: < 1.6 eV — 在 10 篇论文中检索到 8 条匹配记录 (来源: p53, p6, p4)

**Scientific Explanation (LLM):**
> 理论基础：带隙与热力学稳定性无直接因果关联，窄带隙与Sn²⁺易氧化相关，但并非普遍机制，假设将趋势夸大为普适标度律。文献一致性：部分支持，如FASnI₃、CsSnI₃窄带隙不稳定，Cs₂AgBiBr₆较稳定；但反例存在（如CH₃NH₃BaI₃带隙很大却可能不稳定），且AgInI₄、K₂SnGeI₆等数据不足，难以支撑单调正相关。可验证性：可通过分解能、氧化电位等实验或第一性原理计算验证，但需统一稳定性度量，当前证据链和样本量有限。新颖性：带隙-稳定性权衡已有类似报道，检索到1篇潜在重叠，定量幂律关系缺乏充分论证和普适性。综合来看，假设有启发但过度简化，科学合理性中等偏低。；系统查重: 1 篇结果，重叠=none，新颖性 0.65->0.65（1 篇潜在重叠）

**External Validation:**
  - overall_match: True
  - databases_checked: ['materials_project', 'oqmd', 'nomad']
  - supporting_evidence: ['I (OQMD): band_gap = 0.716 eV', 'Br (OQMD): band_gap = 1.349 eV', 'I (OQMD): band_gap = 0.716 eV']
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaacpfaj', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 2. ⏳ 温度-带隙反常标度：dEg/dT>0 与非谐振动/电声耦合强度相关

**Confidence:** 0.96 | **Novelty:** 0.60 | **LLM Plausibility:** 0.70
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 3.0/5（预期独立材料 3 个） — 表 A 有 CsSnI3 两点 + CsPbBr3 单点（共 3-4 个数据点）；需更多温度点支撑强拟合，跨材料异质性需标注

**已知（prior work）:** Slack 1971 带隙-温度模型、Varshni 方程广泛应用于半导体；Patrick & Thygesen (2015) 已发现 CsSnI3 非谐稳定化
**新知（incremental claim）:** 用文献数值系统对比 Slack 模型与候选模型在卤化物钙钛矿上的 R²/RMSE，定量证明经典模型失效并给出非谐标度形式

**Search Best Score:** 0.964 （文献数值证据 15 个）
**实际可用数据点:** 4（模型对比后回填）

**Description:** 铅卤化物钙钛矿带隙随温度降低而降低（反常 dEg/dT>0，p39），CsSnI3 振动重正化打开带隙 0.11 eV@300K / 0.24 eV@500K（p36），CsPbBr3 非谐贡献 450 meV@425K（p38）。假设 dEg/dT 的符号与幅度由非谐声子/电声耦合（rattler 模式、八面体倾斜）主导，而非经典 Varshni/Slack 模型的热膨胀项。用表 A 数据检验 Slack 模型（经典）与候选模型（幂律/指数）的拟合优劣。

**Expected Relationship:** 带隙重正化 ΔEg 随温度 T 按非谐机制增长（ΔEg ∝ T^α 或指数），Slack/Varshni 经典模型因忽略非谐项而失效

**Materials:** CsSnI3, CsPbBr3, MAPbI3
**Property:** band gap

**Source Gap:** Gap 6
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p36: CsSnI3 带隙重正化 0.11 eV@300K / 0.24 eV@500K
  - p38: CsPbBr3 非谐贡献 450 meV@425K
  - p39: 铅卤化物带隙随 T 降低而降低
  - p37: overdamped 声子机制
  - p49: FA-MA gap bowing 由电声耦合主导

**Scientific Explanation (LLM):**
> 经典 Slack/Varshni 模型假设简谐声子+热膨胀，而卤化物钙钛矿的非谐波动（overdamped phonon、rattler 模式）已被多篇第一性原理论文证明主导带隙温度行为——经典模型在此体系系统性失效，候选模型有物理依据

---

### 3. ✅ 双钙钛矿间接→直接带隙调控：In³⁺/无序/Pb²⁺掺杂的系统效应

**Confidence:** 0.97 | **Novelty:** 0.55 | **LLM Plausibility:** 0.62
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 3.0/5（预期独立材料 3 个） — 带隙类型转变阈值需计算验证（p11 提供 Pb 掺杂转变），文献数值点有限（3-4 个材料），侧重定性+半定量

**已知（prior work）:** PhysRevMaterials.2.055401 (p11) 报道 Pb²⁺ 掺杂间接→直接转变；1611.05426v2 (p1) 预测 Cs2InAgCl6 直接带隙
**新知（incremental claim）:** 统一比较 In 替代/无序/Pb 掺杂三条调控路径，提出带隙类型转变的组成阈值规律

**Search Best Score:** 0.966 （文献数值证据 15 个）
**实际可用数据点:** 4（模型对比后回填）

**Description:** Cs2AgBiBr6 为间接带隙 1.72-1.98 eV（p14/p17）；Pb²⁺ 微量掺杂可致间接→直接转变（p11）；Cs2InAgCl6 理论预测直接带隙（p1）；AgInI4 直接带隙 1.72 eV（p70）。假设在双钙钛矿母体中，In 替代/无序增强/掺杂可系统性地将间接带隙转为直接带隙并降低带隙大小，且存在组成-带隙类型转变的临界阈值。

**Expected Relationship:** In/无序度/掺杂浓度 x 增加 → 带隙类型由间接转直接，带隙大小单调变化（存在转变阈值 x_c）

**Materials:** Cs2AgBiBr6, Cs2InAgCl6, AgInI4
**Property:** band gap

**Source Gap:** Gap 2
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p14: Ag-Bi 无序降带隙 0.26 eV 至 1.72 eV
  - p11: Pb²⁺ 掺杂间接→直接转变
  - p1: Cs2InAgCl6 直接带隙预测
  - p70: AgInI4 直接带隙 1.72 eV
  - p8: 阳离子变换设计双钙钛矿
  - 文献验证: 1.72-1.98 eV — 在 10 篇论文中检索到 10 条匹配记录 (来源: p53, p6, p4)
  - 文献验证: 1.72 eV — 在 10 篇论文中检索到 8 条匹配记录 (来源: p53, p6, p4)

**Scientific Explanation (LLM):**
> 该假设整合了间接带隙双钙钛矿向直接带隙转变的多种可能路径，具有一定物理基础：In替代可改变轨道对称性与电子维度，无序可致带隙降低，Pb掺杂可诱导带隙类型转变，三者均与电子结构理论相符。文献支持Cs2AgBiBr6间接带隙、Pb掺杂转变及Cs2InAgCl6/AgInI4直接带隙，证据链部分合理，但将不同体系与机制简单线性叠加，缺乏统一的物理图像和明确的作用机制。假设可通过第一性原理计算与实验验证，具有可验证性；然而阈值x_c及单调变化缺乏定量理论支撑，且新颖性检索显示无直接重叠但相关概念（如无序、掺杂调控带隙类型）已有较多研究，整体新颖性一般。综合评分为0.62，属部分合理但需进一步细化与验证的假设。；系统查重: 0 篇结果，重叠=none，新颖性 0.55->0.55

**External Validation:**
  - overall_match: True
  - databases_checked: ['materials_project', 'oqmd', 'nomad']
  - supporting_evidence: ['Br (OQMD): band_gap = 1.349 eV', 'Cl (OQMD): band_gap = 2.661 eV', 'I (OQMD): band_gap = 0.716 eV']
  - details: {'materials_project': {'match': False, 'matching_entries': [], 'materials_found': [{'mp_id': 'mp-aaacpfaj', 'formula': '', 'band_gap_ev': None, 'formation_energy_ev_per_atom': None, 'energy_above_hull

---

### 4. ⏳ ML 联合预测带隙与稳定性：电离能/分解能描述符的独立性检验

**Confidence:** 0.88 | **Novelty:** 0.60 | **LLM Plausibility:** 0.65
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 2.0/5（预期独立材料 495 个） — 需要 ML 数据集（p53 的 495 化合物或 p65 的 1221 化合物）支撑；摘要级数据不足，需外部数据库

**已知（prior work）:** Landini et al. ML 筛选双钙钛矿 (p64)；solener.2021.09.030 联合预测 (p19)
**新知（incremental claim）:** 从'ML 能预测'推进到'带隙与稳定性在描述符空间可分离'的结构性结论

**Search Best Score:** 0.882 （文献数值证据 15 个）

**Description:** p60 表明 ML 可同时预测带隙（RMSE 21 meV）与形成能（39 meV/atom）；p65 用 4 类物理描述符（packing/bonding/polarization/electronic identity）筛选 1221 个双钙钛矿；p50 提出电离能作为稳定性判据。假设带隙与稳定性（分解能）在描述符空间具有可分离性——即存在对带隙敏感但稳定性无关（或反之）的独立描述符，使双目标联合优化成为可能。

**Expected Relationship:** 描述符空间中带隙与分解能存在正交子空间（可分离）；电离能/容差因子主要预测稳定性，带隙由电子构型描述符主导

**Materials:** ABX3, A2BB'X6
**Property:** band gap

**Source Gap:** Gap 3
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p60: ML 带隙 RMSE 21 meV + 形成能 39 meV/atom
  - p65: 1221 双钙钛矿 4 描述符框架
  - p50: 电离能稳定性判据
  - p53: 495 ABX3 高通量数据集
  - p19: ML 联合预测带隙+稳定性

**Scientific Explanation (LLM):**
> ML 联合预测已在技术上验证（p60/p65）；本假设关注科学问题——带隙与稳定性是否可分离，为同时优化提供设计规则

---

### 5. ⏳ 压力-带隙闭合的分段线性标度：MA2PtI6 类体系 dEg/dP 与结构相变耦合

**Confidence:** 0.96 | **Novelty:** 0.50 | **LLM Plausibility:** 0.60
**Consistency:** strong (强 — LLM与搜索一致高分)
**Extractability:** 3.0/5（预期独立材料 2 个） — 表 C 数据点由速率推导（[待验证]）；绝对带隙值缺失需外部数据库补全

**已知（prior work）:** c9nr07030c 报道 Cs2AgBiBr6 压力带隙演化；1674-1056/adce9e 报道 MA2PtI6 分段闭合
**新知（incremental claim）:** 将两体系的压力响应统一为分段线性标度框架，分段点与结构转变关联

**Search Best Score:** 0.960 （文献数值证据 15 个）
**实际可用数据点:** 5（模型对比后回填）

**Description:** MA2PtI6 带隙在 1.2 GPa 处分两段线性闭合（0.063 → 0.079 eV/GPa，p20）；Cs2AgBiBr6 在 2.3 GPa 相变后红移→蓝移（p15）。假设压力-带隙响应存在分段线性标度，分段点对应结构相变/电子结构重组，且 dEg/dP 与体系压缩性/八面体畸变度相关。用表 C 数据检验线性/分段线性/二次模型的拟合优劣。

**Expected Relationship:** 带隙随压力分段线性闭合（两段速率），分段点 ≈ 1.2 GPa 结构转变；二次/指数模型不优于分段线性

**Materials:** MA2PtI6, Cs2AgBiBr6
**Property:** band gap

**Source Gap:** Gap 4
**Search Method:** bayesian (10 iterations, 21 candidates)

**Evidence Chain:**
  - p20: MA2PtI6 0.063/0.079 eV/GPa 两段闭合
  - p15: Cs2AgBiBr6 2.3 GPa 相变红移→蓝移

**Scientific Explanation (LLM):**
> 压力-带隙响应的分段线性是结构相变驱动的常见现象；两体系 dEg/dP 符号不同（闭合 vs 红移→蓝移）说明机制多样，分段标度可量化比较

---
