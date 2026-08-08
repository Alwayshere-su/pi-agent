## 调研：卤化物钙钛矿带隙与稳定性（halide perovskite band gap and stability）

### 检索策略
- 检索词：halide perovskite band gap stability；lead-free double perovskite Cs2AgBiBr6；machine learning halide perovskite；CsPbI3/FAPbI3/tin perovskite 等 9 组
- 数据源：arXiv + Semantic Scholar（自动累积到 search_results.json，经关键词过滤后得 34 篇钙钛矿论文）
- 过滤：排除 526 条 MOF/CO2 遗留数据（workspace/data/literature_cache/search_results.json 混合多主题）
- 2026-08-02 首次调研本主题

### 知识图谱摘要
- 材料数：10（MAPbI3、CH3NH3Pb(I1-xBrx)3、CsPb(I1-xBrx)3、Cs2AgBiBr6、Cs2InAgCl6、FASnI3、CH3NH3BaI3、MA2PtI6、Na2ZrTeO6、2D RP 钙钛矿）
- 性质数：4（带隙、带隙类型、稳定性、吸收系数）
- 关键关系数：15（R1-R15：带隙-组成 Vegard 律、带隙-压力、带隙-无序、稳定性-氧化等）
- 关键数值：Cs2AgBiBr6 带隙 1.72-1.98 eV（间接）；Ag-Bi 无序降带隙 0.26 eV；MA2PtI6 dEg/dP=0.063/0.079 eV/GPa；MAPbI3/BN -25 meV@300K 稳定

### Top 研究空白
1. Gap 1 带隙-稳定性 trade-off 无定量联合描述符 — 严重程度：高 — 置信度：0.85
   证据：jacs.7b02120（Sn 窄带隙不稳定 vs Bi 稳定宽带隙）、jacs.6b09645、mtener.2022.101038、anie.202005568
   验证方案：构建带隙×稳定性（分解能/氧化电位/湿稳定性）联合数据集，检验 Pareto 前沿
2. Gap 2 双钙钛矿间接→直接带隙调控手段缺乏系统性比较 — 严重程度：高 — 置信度：0.80
   证据：jacs.6b09645、PhysRevMaterials.2.055401（Pb 掺杂转变）、anie.202005568（无序降带隙）
   验证方案：同一母体（Cs2AgBiBr6）对比无序/掺杂/压力/厚度对带隙类型+大小的联合效果
3. Gap 3 ML 带隙预测与稳定性预测脱节 — 严重程度：中 — 置信度：0.78
   证据：solener.2021.09.030（唯一联合预测但摘要缺失）
   验证方案：多任务学习联合预测带隙+分解能
4. Gap 4 压力-带隙响应体系间标度缺失 — 严重程度：中 — 置信度：0.75
   证据：c9nr07030c（红移→蓝移）vs 1674-1056/adce9e（单调闭合）
   验证方案：计算系列 dEg/dP 与离子半径/电负性描述符关联
5. Gap 5 2D/3D 界面电荷转移-带隙-稳定性耦合定量缺失 — 严重程度：中 — 置信度：0.70
   证据：acsami.5c00201、commatsci.2022.111649
   验证方案：系统扫描 2D 层参数×3D 组分

### 发现结果（路线 A）
1. 占位假设（hypo_0 "Material-property relationship discovery"）— 待验证（置信度 0.40）
   材料：未指定 ｜ 性质：未指定
   搜索：bayesian 10 轮 21 候选，best score 0.400，文献数值证据 0 个
   外部验证：Materials Project 0 命中（inconclusive）
   说明：generate_hypotheses 未从知识图谱提取到具体实体，生成的是占位假设——下一轮应手动构造具体假设（如 Gap 1 的带隙-稳定性联合描述符）

### 反思
- 最令人惊讶的发现：Cs2AgBiBr6 可通过 Ag-Bi 无序将带隙降至 1.72 eV（anie.202005568），且压力响应与 MA2PtI6 相反——无序/压力调控带隙的机制多样
- 哪个搜索方向最高效：arXiv 计算类（DFT-1/2、VCA、HSE）+ Semantic Scholar 双钙钛矿实验类
- 下一轮迭代应聚焦：手动构造 Gap 1 相关的具体假设（材料：Cs2AgBiBr6 系列 + FASnI3；性质：带隙+分解能），用 generate_hypotheses 的 search_method 参数确保实体提取；扩大检索覆盖 MAPbI3 稳定性实验数据
