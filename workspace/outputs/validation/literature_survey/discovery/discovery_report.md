# Structure-Property Relationship Discovery Report

**Generated:** 2026-08-16 15:36
**Total candidates explored:** 83
**Validated:** 0 | **Refuted:** 0
**Contested:** 5 | **Underexplored:** 0
**Materials Project hits:** 0

## Search Summary

Explored 5 hypotheses via Bayesian optimization and MCTS. 四象限一致性: strong=0, underexplored=0, contested=5, weak=0. degraded=1 (占位/降级)

---

## Discovered Structure-Property Relationships

### 1. ⏳ 氧/钼双掺杂对硫银锗矿硫化物电解质电导率与H2S释放量的双目标优化窗口

**Confidence:** 0.79 | **Novelty:** 0.75 | **LLM Plausibility:** 0.00
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5 — 摘要级证据，无全文解析，无可提取的定量 (x,y) 数据序列

**已知（prior work）:** 已有文献确立硫银锗矿 Li₆PS₅Cl 水解产 H₂S 的路径（P023 拉曼、P027 隔膜水解）与表面工程提升湿度稳定性（P031），Mo-O 双掺杂实现稳定全固态电池（P024）；但 O/Mo-O 掺杂浓度-电导率/H₂S 释放的双目标优化窗口未定量
**新知（incremental claim）:** 给出 O 含量 0.1–0.3 时电导率≥1 mS/cm 且 H₂S 释放降 50%+ 的双目标窗口，并论证 Mo-O 双掺杂优于单氧掺杂

**Search Best Score:** 0.786 （文献数值证据 1 个）

**Description:** 硫化物固态电解质在潮湿环境中易水解产生H2S，而掺杂氧或金属氧化物（如MoO2）可能同时改善电导率和湿度稳定性。本假说认为，氧掺杂引入更强的局部共价键和更致密的阴离子框架，一方面通过缺陷工程维持甚至提升Li+迁移率，另一方面氧位点与水分子的结合能高于硫位点，从而抑制水解反应。通过系统调控Li6PS5Cl中的O含量及Mo-O共掺杂比例，可以突破传统“电导率-湿度稳定性”此消彼长的权衡关系。

**数值验证结果**
- **预测值（待实验验证）**: `50%` — 在 5 篇论文摘要中检索，未找到直接支撑。
  建议验证方案: 预测值 50%（待实验验证，建议方案：元素分析或TGA定量组成变化）

**Expected Relationship:** 预期存在一个掺杂浓度区间（例如O含量0.1–0.3），使室温电导率保持≥1 mS/cm的同时，H2S释放量降低50%以上。氧/钼双掺杂的效果优于单一氧掺杂，因为Mo可进一步稳定晶格并促进Li+跃迁。

**Materials:** Li6PS5Cl, Li6PS5Cl1-xOx, Mo-O共掺杂Li6PS5Cl, Li6PS5I
**Property:** 室温离子电导率及H2S生成速率

**Source Gap:** Gap 2
**Search Method:** bayesian (5 iterations, 16 candidates)

**Evidence Chain:**
  - P024
  - P031
  - P027
  - P023
  - 预测值 50%（待实验验证，建议方案：元素分析或TGA定量组成变化）
  - [Novelty Verification] Overlap: none | Novelty: 0.750 (was 0.750) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 0.00
  - `50%`: ❌ 未查证
  - 未查证值: 50%

**Scientific Explanation (LLM):**
> LLM 合理性评分未产出有效值（支撑文献仅摘要级证据，无定量数据可评估），保留默认 0.0

---

### 2. ⏳ 高熵阳离子无序度与固态电解质室温离子电导率的火山型关系及机器学习预测闭环

**Confidence:** 0.65 | **Novelty:** 0.85 | **LLM Plausibility:** 0.00
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5 — 摘要级证据，无全文解析，无可提取的定量 (x,y) 数据序列

**已知（prior work）:** 已有文献建立 ML/LLM 预测 SSE 离子电导率的框架与 OBELiX 实验数据集（P068、P080、P079），MD 方法对比（P074）；但构型熵 S_cfg 与电导率的火山型定量关系及 ML 预测-实验闭环未建立
**新知（incremental claim）:** 提出电导率随构型熵先升后降的火山型关系，并以局域配位环境为特征的 ML 模型预测-实验验证形成闭环

**Search Best Score:** 0.274 （文献数值证据 0 个）

**Description:** 机器学习筛选出的高熵固态电解质候选材料缺乏实验验证，且高熵带来的晶格畸变对离子输运的影响尚不明确。本假说提出，在卤化物/硫化物框架中引入多种阳离子（如Y, In, Sc, Ho, Er）形成高熵固溶体，构型熵增加会拓宽锂离子迁移势垒分布，但适度无序可增加迁移通道的连通性和瓶颈尺寸；过高熵值则产生严重晶格畸变，堵塞迁移路径。利用OBELiX等数据库训练机器学习模型，预测不同高熵组成的电导率，并用实验测量值校验，可建立构型熵-电导率的定量关系并改进模型外推能力。

**Expected Relationship:** 预期室温离子电导率随构型熵S_cfg增大先升高后降低，呈火山型曲线，最优S_cfg对应最大电导率。机器学习模型若以局域配位环境为特征，可定量捕捉该非线性关系；实验验证后，模型预测误差将用于指导下一轮候选合成，形成闭环。

**Materials:** Li3(Y0.2In0.2Sc0.2Ho0.2Er0.2)Cl6, Li3YCl6, Li3InCl6, 高熵硫化物Li6PS5Cl基固溶体
**Property:** 室温离子电导率

**Source Gap:** Gap 3
**Search Method:** bayesian (5 iterations, 16 candidates)

**Evidence Chain:**
  - P068
  - P080
  - P079
  - P074
  - [Novelty Verification] Overlap: none | Novelty: 0.850 (was 0.850) | Queries: 3 | Results: 5

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 合理性评分未产出有效值（支撑文献仅摘要级证据，无定量数据可评估），保留默认 0.0

---

### 3. ⏳ 卤素比例调控卤化物固态电解质室温电导率与湿度稳定性的非线性关系 [⛔ degraded]

**Confidence:** 0.72 | **Novelty:** 0.70 | **LLM Plausibility:** 0.00
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5 — 摘要级证据，无全文解析，无可提取的定量 (x,y) 数据序列

**已知（prior work）:** 已有文献确立卤化物 SSE 的电导率-湿度稳定性权衡与材料化学（P006），ML 预测 Li₃YCl₆₋ₓBrₓ 结构与电导率（P070），SSE 低类玻璃热导率（P040）；但 Br 取代量 x 与室温电导率（火山型）/湿度稳定性的定量关系未系统验证
**新知（incremental claim）:** 给出室温电导率随 Br 取代 x 的火山型（峰值 x≈1.0–1.5）与湿度稳定性单调下降的定量关系，定位电导率>1 mS/cm 且稳定性可接受的最优 x

**Search Best Score:** 0.314 （文献数值证据 0 个）
**Degraded Reason:** ⚠️ 证据数值为空，打分无区分度（搜索空转）: literature_values 为空导致候选参数主要依赖固定基分，best_score 多轮不变。建议在 knowledge_graph.md 中补充定量数值（如容量 mmol/g、Qst kJ/mol），并重跑搜索以利用文献数值先验。
**Search Warning:** ⚠️ 证据数值为空，打分无区分度（搜索空转）: literature_values 为空导致候选参数主要依赖固定基分，best_score 多轮不变。建议在 knowledge_graph.md 中补充定量数值（如容量 mmol/g、Qst kJ/mol），并重跑搜索以利用文献数值先验。

**Description:** 在Li3YCl6等卤化物固态电解质中，用Br-或I-部分取代Cl-可以扩张晶格体积、增大锂离子迁移通道尺寸，从而降低迁移活化能、提升室温离子电导率。然而，较大且极化率较高的卤素离子同时会增强吸湿性和与水分的反应活性，导致湿度稳定性下降。因此，室温离子电导率随Br/I取代比例呈火山型变化，而湿度稳定性呈单调递减，二者之间存在最优卤素配比窗口。本假说通过系统合成Li3YCl6-xBrx系列并测量电导率与湿度暴露后的结构/电导保持率来验证。

**Expected Relationship:** 预期室温离子电导率与Br取代量x呈火山型关系，在x≈1.0–1.5达到峰值；湿度稳定性随x增加单调下降。最优x位于电导率增益与稳定性损失交叉点附近，该点可同时获得>1 mS/cm的室温电导率和可接受的湿度稳定性。

**Materials:** Li3YCl6, Li3YCl6-xBrx, Li3InCl6, Li2ZrCl6
**Property:** 室温离子电导率与湿度稳定性（H2O暴露后电导率保持率）

**Source Gap:** Gap 1
**Search Method:** bayesian (6 iterations, 17 candidates)

**Evidence Chain:**
  - P040
  - P070
  - P006
  - [Novelty Verification] Overlap: none | Novelty: 0.700 (was 0.700) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> [degraded 降级评估] LLM 合理性评分未产出有效值（支撑文献仅摘要级证据，无定量数据可评估），保留默认 0.0

---

### 4. ⏳ Lewis酸性基团浓度对聚合物电解质锂离子迁移数与离子电导率权衡的非单调调控

**Confidence:** 0.62 | **Novelty:** 0.80 | **LLM Plausibility:** 0.00
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5 — 摘要级证据，无全文解析，无可提取的定量 (x,y) 数据序列

**已知（prior work）:** 已有文献确立弱配位/配位性阴离子对聚合物电解质 t+ 与 σ 的权衡（P038），Lewis 酸性聚合物增强阳离子扩散/抑制阴离子扩散（P039），聚合物界面工程（P059、P001）；但 Lewis 酸基团浓度对 t+-σ 的非单调调控定量未建立
**新知（incremental claim）:** 给出 Lewis 酸基团浓度使 t+（~0.2→0.5+）单调上升而 σ 先升后降的定量关系，定位 t+ 与 σ 同时优于未改性 PEO 的最优浓度

**Search Best Score:** 0.835 （文献数值证据 1 个）

**Description:** 传统PEO基聚合物电解质中，锂离子迁移数t+低（~0.2）且与离子电导率σ存在权衡。弱配位阴离子（如TFSI）并不能解耦Li+与链段运动，而引入Lewis酸性基团（如硼酸酯）或配位性阴离子（如TFSAM）可能通过可逆配位阴离子来降低阴离子迁移率，从而提升t+。本假说系统研究Lewis酸含量及阴离子类型对t+和σ的影响，以期找到协同优化窗口。

**Expected Relationship:** 预期随着Lewis酸基团浓度增加，t+从~0.2单调上升至0.5以上，而σ先升后降。原因是适量Lewis酸增强盐解离并促进Li+传输，但过量Lewis酸会提高玻璃化转变温度或形成交联网络，降低链段运动能力。因此t+-σ权衡曲线存在一个最优Lewis酸浓度，使t+与σ同时优于未改性PEO。

**Materials:** PEO-LiTFSI, 含硼酸酯（Lewis酸）PEO基聚合物, 含TFSAM配位性阴离子的聚合物电解质
**Property:** 锂离子迁移数（t+）与离子电导率（σ）

**Source Gap:** Gap 4
**Search Method:** bayesian (6 iterations, 17 candidates)

**Evidence Chain:**
  - P038
  - P039
  - P059
  - P001
  - [Novelty Verification] Overlap: none | Novelty: 0.800 (was 0.800) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 合理性评分未产出有效值（支撑文献仅摘要级证据，无定量数据可评估），保留默认 0.0

---

### 5. ⏳ 亲锂成核层+电子阻挡层双层界面设计对固态电解质界面电阻的普适降低效应

**Confidence:** 0.66 | **Novelty:** 0.75 | **LLM Plausibility:** 0.00
**Consistency:** contested (争议 — 数据匹配但科学存疑)
**Extractability:** 0.0/5 — 摘要级证据，无全文解析，无可提取的定量 (x,y) 数据序列

**已知（prior work）:** 已有文献确立 Ag 键合界面 0.25 Ω cm²（P047）、LiF 富集 SEI 稳定硫化物/锂界面（P017）、LiCux 三维网络宿主（P060）等单策略，DFT 界面稳定性（P058）与硫化物阳极界面策略（P046）；但「亲锂成核+电子阻挡」双层设计的普适性未提炼
**新知（incremental claim）:** 将多种界面工程提炼为 Ag/LiF 双层普适设计，论证其可将界面电阻从 >100 Ω cm² 降至 <10 Ω cm²，且与 SSE 阴离子种类无关（越不稳定 SSE 受益越大）

**Search Best Score:** 0.833 （文献数值证据 12 个）

**Description:** 实验室中通过Ag@COOH-CNTs、LiF富集层、LiCux三维网络等界面工程可将Li/SSE界面电阻降至0.25 Ω cm²，但工程级全固态电池仍受>100 Ω cm²界面电阻困扰。本假说提出，这些策略成功的共性在于同时满足“亲锂成核位点”和“电子阻挡层”两个功能；若能将其提炼为普适的双层界面设计（如Ag/LiF双层），则可跨硫化物、氧化物、卤化物SSE实现界面电阻的大幅降低。

**Expected Relationship:** 预期在多种SSE上，Ag亲锂层负责诱导均匀锂沉积、降低成核过电位，LiF电子阻挡层负责抑制电子跨界面传输、减少副反应，二者协同可将界面电阻从>100 Ω cm²降至<10 Ω cm²，且该效应与SSE阴离子种类无关。界面电阻降低幅度还可能与SSE的还原稳定性相关，即越不稳定的SSE受益越大。

**Materials:** Li6PS5Cl, Li7La3Zr2O12 (LLZO), Li3YCl6, Ag涂层, LiF涂层, Ag@COOH-CNTs复合层
**Property:** Li/SSE界面电阻（Ω cm²）

**Source Gap:** Gap 5
**Search Method:** bayesian (6 iterations, 17 candidates)

**Evidence Chain:**
  - P047
  - P017
  - P060
  - P058
  - P046
  - [Novelty Verification] Overlap: none | Novelty: 0.750 (was 0.750) | Queries: 3 | Results: 0

**Value Verification (数值文献验证):**
  - 综合验证分数: 1.00

**Scientific Explanation (LLM):**
> LLM 合理性评分未产出有效值（支撑文献仅摘要级证据，无定量数据可评估），保留默认 0.0

---
