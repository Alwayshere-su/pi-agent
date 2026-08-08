# 调研记忆（第四轮续接）：MOF 双金属协同 CO2 捕获

## 调研：[MOF materials for CO2 capture bimetallic synergy] — 第四轮
日期：2026-08-01（续接第三轮，主题聚焦双金属协同）

### 本轮执行摘要
- **新增**：4 组检索词（bimetallic MOF-74 ratio / mixed-metal dopant OMS / DFT electronic structure / Qst composition）→ +84 篇 sciverse（76 篇带摘要）→ 证据池 **353 篇**
- **产出更新**：knowledge_graph.md（+R14-R18 + 第八节双金属专题）、gap_report.md（Gap 1 细化置信度 0.93 + 新增 Gap 10）、survey_report.md（双金属协同专题）、hypotheses 重新生成（5 条）、discovery search 假设 0（best 0.683）+ 外部验证（MOF-74 容量 meta 3.0-8.6 mmol/g）

### 知识图谱新增（第八节，双金属专题 8 项关键证据）
- **Ni₀.₃₇Co₀.₆₃-MOF-74**（scv:073a40bcc5cb）：x=0.37 中间比例 NO 选择性远超单金属
- **Ni(x)M(1-x)-ITHDs**（scv:66fc8c917582）：临界掺杂量组合依赖（NiCo≈0.1 vs NiZn>0.2）+ ultralarge CO2 容量
- **Cu/Mg-MOF-74 梯度**（scv:ecfe34f94197）：吸附随 Mg 单调增（0.1/0.9 时 9.21 mmol/g），**光催化倒 U（0.6/0.4 最优）**——最优比例性质依赖
- **Mg/Zn(dobpdc) 1:1**（scv:1a24bed1a447）：模板法组成可控，离子半径决定组成比
- **双金属电子态密度**（scv:fe16f430b240）：三类掺杂模式 DOS 可调
- M-BTT 等网状（scv:56f419af470d）、金属离子浸渍（scv:39ca0a621b3c）、碱金属掺杂 HKUST-1（scv:309c6ba090d4）

### 新增/更新构效关系
- R14：双金属最优比例**性质依赖**（吸附单调 vs 催化倒U）— 中置信
- R15：临界掺杂量依赖金属组合 — 中
- R16：组成可控性受离子半径控制 — 中
- R17：双金属 → DOS 可调 → CO2 结合优化 — 中
- R18：金属离子掺杂 → Qst+选择性+容量协同增强 — 中
- R5 细化：倒 U 型非普适（NiCo/CoMn 倒 U，Cu/Mg 单调）

### Top 研究空白（更新）
1. **双金属比例-性能曲线体系/性质依赖性** — 高 — 0.93（↑ 自 0.90，8 项新证据）
   - 证据：p62/p65/p67/scv:ecfe34f94197/scv:66fc8c917582/scv:073a40bcc5cb
   - 验证：多组合×多性质×5-10% 步长梯度合成，三维响应面
2. **新增 Gap 10：实际组成 vs 名义比例偏差量化** — 中 — 0.60
   - 证据：scv:1a24bed1a447（离子半径控制组成）
   - 验证：ICP-MS 再分析 + 名义→实际映射库
3. 其余 Gap 保持（水机理 0.94、Qst Pareto 0.85、工艺 0.78、DAC 0.85、杂质 0.70、OMS-Qst 0.72、ML 0.75、缺陷 0.65）

### 发现结果（路线 A，本轮）
1. 【假设 0】双金属 MOF-74 比例-容量倒 U 型及组合依赖性 — 置信 0.85 — 搜索后 best 0.683
   - 新证据：Ni₀.₃₇Co₀.₆₃（中间比例>端点）、ITHDs（阈值依赖）、Cu/Mg（非倒U吸附）
   - **假设细化**：倒 U 型是部分体系规律（d-d 组合），最优比例依赖组合+性质
   - 外部验证：Materials Project 0 命中（MOF 覆盖不足，与历轮一致）；文献 meta 3.0-8.6 mmol/g 佐证

### 反思
- **最惊讶**：Cu/Mg-MOF-74 中"吸附单调增加 vs 光催化倒 U"并存——同一材料体系的最优比例随目标性质漂移，说明"协同最优"是**多维概念**
- **最高效方向**：sciverse 检索（带摘要比例 90%）远优于 Crossref（17%）——本轮 76/84 篇带摘要
- **局限**：Cu/Mg 是 s-d 组合 vs NiCo/CoMn 是 d-d 组合——倒 U 与否可能由金属电子结构差异（s vs d 轨道参与）决定，需 DFT 验证
- **下一轮**：①检索 s-d 组合（MgCu/MgNi/MgZn）双金属 MOF 吸附数据，检验"轨道类型决定曲线形状"假设 ②用 Cu/Mg 单调数据点扩展定量验证（倒 U vs 单调对比）③组装 MOF 吸附数据集（Gap 4）
