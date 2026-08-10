## 调研：MOF materials for CO2 capture（首次调研，mof_rerun）

### 检索策略
- 检索词：MOF CO2 capture adsorption / metal-organic framework carbon dioxide capture / MOF-74 CO2 adsorption capacity / MOF CO2 N2 selectivity pore size engineering / amine functionalized MOF CO2 capture performance / ZIF-8 UiO-66 CO2 adsorption capture + 批量脚本 8 组（amine MOF、CO2 isotherm、ZIF-8、UiO-66、water stability、DAC、PEI、MOF-74）
- 数据源：arXiv（内置 search_papers + ArxivSearcher 批量脚本），单轮检索 8 次调用中 5 次 0 命中（检索后端对特定措辞敏感）
- 结果：42 篇论文（去重后 ~30 篇有效），缓存于 workspace/data/literature_cache/mof_rerun/

### 知识图谱摘要
- 材料数：~15 体系（M-DOBDC/MOF-74、mmen-M2(dobpdc)、M-HKUST-1、CALF-20、MIL-120、ZIF-8、Zn 基水稳定 MOF、金属卟啉石墨烯等）
- 性质数：CO2 吸附容量、吸附焓 Qst、CO2/N2 选择性、水解稳定性、扩散系数、等温线形状、比表面积
- 关键关系数：14（R1-R14，见 knowledge_graph.md）

### Top 研究空白
1. Gap 3 — H2O 对胺功能化 MOF 的 CO2 吸附影响（braided chain vs 竞争抑制）— 严重程度：高 — 置信度：0.75
   证据：Owens 2025; Kundu 2018
   验证方案：湿度-容量回归 + braided chain 理论对比
2. Gap 4 — 金属取代筛选仅覆盖吸附焓单一性质 — 严重程度：中 — 置信度：0.70
   证据：Koh 2016; Bae 2016
   验证方案：d 电子构型 → 焓/选择性/水稳定性联合 Pareto
3. Gap 1 — 力场/MLIP 对 CO2 吸附预测系统性偏差 — 严重程度：高 — 置信度：0.85
   证据：Edwards (MLIP-MC); Oliveira (CRAFTED); Brabson
   验证方案：预测偏差 ← 框架特征回归

### 发现结果（路线 A）
1. H0（Gap 4）：金属 d 电子数 → MOF-74 系 Qst 负相关 — 部分支持
   材料：M-MOF-74（M=Mg/Fe/Co/Ni/Zn）；性质：CO2 吸附焓
   量化验证：线性 Qst = -1.496·Nd + 47.3，R²=0.72（n=5）；Spearman ρ=-0.60（n 小不显著）
   外部验证：CoRE MOF / hMOF 命中（ZIF-8 0.5-1.5 mmol/g）；Koh 2016 vdW-DF 趋势一致
2. H1（Gap 5）：超微孔 MOF 吸附-动力学标度律 — 已验证（10 轮搜索 score 0.625，validate_discovery 通过）
3. H2（Gap 1）：MLIP 预测偏差受开放金属位点密度调控 — 已搜索（10 轮 score 0.587）
4. H3（Gap 2）：DFT 泛函敏感性随 d 电子数变化 — 已搜索（10 轮 score 0.567）

### 反思
- 最令人惊讶的发现：arXiv 源严重偏向计算/ML，经典实验材料（UiO-66、PEI 复合、胺效率）检索命中率为 0——检索后端措辞敏感是主要瓶颈
- 最高效的搜索方向：宽泛查询（"MOF CO2 capture adsorption"、metal-organic framework carbon dioxide capture）命中率远高于带修饰词的查询
- 模型对比教训：n=5 小样本下二次/Gauss 模型病态，线性为最稳健基线；symbolic_regression 工具自动提取"温度"而非自定义特征（d 电子数），需自写脚本驱动 literature_agent 模块
- 下一轮迭代应聚焦：① 补充实验期刊文献（UiO-66、胺功能化定量数据）② 扩展 H0 金属集（Ca/Mn/Cu）至统计显著 ③ 对 H2/H3 做量化验证
