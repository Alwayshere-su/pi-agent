## 调研：高镍正极容量保持率（high-nickel cathode capacity retention）
### 检索策略
- 检索词："lithium battery cathode capacity retention"、"NMC cathode lithium ion battery"、"lithium ion battery cathode degradation"、"nickel rich cathode electrolyte interface"、"electrolyte additive lithium battery high voltage stability" 等 10+ 组合
- 数据源：arXiv（Sciverse 命中少），结果累积 794 篇中人工精炼 19 篇核心论文
- 缓存：workspace/data/literature_cache/cathode_papers.json（19 篇）

### 知识图谱摘要
- 材料数：13（NMC811/622/333、LiNiO2、单晶/多晶 NMC、核壳、涂层 Al2O3/AlF3/ZrO2/MgO/SiO2、电解质 ADN-LiTFSI、EMIMDep、SiOx 负极等）
- 性质数：13（容量保持率、电压衰减、日历损失、Ni 氧化态异质性、位错临界应力、阳离子无序、表面重构、氧释放、裂纹润湿、LLI、Li 扩散等）
- 关键关系数：14（R1-R14，见 knowledge_graph.md）

### Top 研究空白
1. Gap 1（单晶 NMC 化学-力学耦合缺失）— 严重程度：高 — 置信度：0.80
   证据：p24（Ziesche 2025 光谱叠层成像）, p25（Wang 2023 微力学测试）
   验证方案：同一单晶颗粒顺序"光谱成像→微力学压缩"关联实验
2. Gap 4（裂纹润湿-表面重构耦合）— 严重程度：中高 — 置信度：0.75
   证据：p31（Luza-Vega 2026）, p32（Li 2021）
   验证方案：扩展 p31 模型加入表面重构反应动力学项
3. Gap 3（Ni 含量-容量保持率定量权衡）— 严重程度：高 — 置信度：0.72
   证据：p22（Houchins 2018）, p24, p32
   验证方案：NMCx（x=0.6-1.0）归一化循环数据元分析

### 发现结果（路线 A）
1. 假设 0（单晶 NMC811 Ni 氧化态异质性→位错裂纹）— 已搜索 6 轮，best 0.614，置信度 0.72
2. 假设 1（裂纹润湿→表面重构释氧→容量衰减）— 已搜索 6 轮，best 0.488，置信度 0.70
3. 假设 2（Ni 含量-保持率非单调权衡）— 已搜索 5 轮，best 0.548，置信度 0.68
4. 假设 3（涂层 Li 电导-副反应阻抗帕累托）— 已搜索 5 轮，best 0.433，置信度 0.65
5. 假设 4（Ni 氧化态↑→混排势垒↓→岩盐相变）— 已搜索 5 轮，best 0.508，置信度 0.63
- 外部验证：未执行（预算耗尽，规则 4 允许跳过）

### 反思
- 最令人惊讶的发现：单晶 NMC 虽消除晶间裂纹，但 Ni 氧化态空间异质性（化学不均一）仍存——机械稳定≠化学稳定
- 最高效搜索方向：宽泛句式 "lithium ion battery cathode degradation"（命中 20 篇高质量）
- 下一轮迭代应聚焦：假设 0 的 validate_discovery（单晶 NMC811 化学-力学耦合最具发现潜力，best 0.614）
