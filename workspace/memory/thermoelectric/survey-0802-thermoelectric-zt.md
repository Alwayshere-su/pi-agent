## 调研：热电材料 ZT 优化（thermoelectric ZT optimization）

### 检索策略
- 检索词：thermoelectric ZT optimization / Bi2Te3 / PbTe / SnSe / half-Heusler / skutterudite / GeTe / Cu2Se / phonon engineering / carrier concentration / machine learning
- 数据源：arxiv (160) + semantic_scholar (49)，共 209 篇有效论文
- 经验：长查询返回 0 篇，短核心词（如 "Bi2Te3 thermoelectric"）命中率高

### 知识图谱摘要
- 材料数：8 大体系（Bi₂Te₃、PbTe、SnSe、Half-Heusler、Skutterudite、GeTe、Cu₂Se、2D/新兴）
- 性质数：8（ZT、S、σ、PF、κ、κₗ、品质因子 B、载流子浓度）
- 关键关系数：14（R01-R14）
- 关键 ZT 纪录：SnSe 单晶 2.6@923K（实验最高）、Yb/In 方钴矿 1.72@773K、HfZrCoSnSb+Al 1.5@980K、n-SnSe 多晶 1.8

### Top 研究空白
1. Gap 1: ML 预测 ZT 与实验验证断层（R²0.90-0.98 vs 极少验证）— 严重程度：高 — 置信度：0.92
   证据：TE057, TE058, TE011, TE062, TE096
   验证方案：PCA 采样+主动学习循环；实验合成 ML 候选
2. Gap 2: n 型 SnSe 远落后 p 型（缺陷化学+各向异性+掺杂限制）— 严重程度：高 — 置信度：0.88
   证据：TE122, TE115, TE113
   验证方案：卤素掺杂缺陷形成能-载流子-ZT 关联
3. Gap 6: 共振掺杂 DOS 异常-Seebeck 增强定量标度缺失 — 严重程度：中 — 置信度：0.70
   证据：TE146, TE087
   验证方案：不同共振杂质 DOS 异常幅度第一性原理计算+实验

### 发现结果（路线 A）
1. 纳米晶 Si-Ge-P 超饱和固溶体 ZT 优化（Gap 1）— 已搜索 — Best 0.872（10 轮，21 候选）
   材料：Si-Ge-P 超饱和固溶体 | 性质：晶格热导率 + ZT
2. 卤素掺杂 n 型 SnSe（Gap 2）— 已搜索 — Best 0.850（5 轮，16 候选）
   材料：卤素掺杂 SnSe | 性质：载流子浓度 + ZT
3. 共振掺杂 DOS 标度（Gap 6）— 已搜索 — Best 0.833（5 轮，16 候选）
   材料：共振掺杂 half-Heusler | 性质：Seebeck + ZT

### 反思
- 最令人惊讶的发现：PbTe 带隙随温度增大且贴合最优带隙是其高 ZT 本质原因（TE085）；方钴矿 rattling 实为填充物-笼系统整体振动（TE188）
- 最高效的搜索方向：短核心词检索（"Bi2Te3 thermoelectric"）
- 下一轮迭代应聚焦：Gap 1 的实验验证闭环、n 型 SnSe 掺杂、方钴矿复现性协议；补充有机热电与器件级效率文献

### 文件清单
- 知识图谱: workspace/outputs/thermoelectric/literature_survey/knowledge_graph.md
- Gap 报告: workspace/outputs/thermoelectric/literature_survey/gap_report.md
- 调研报告: workspace/outputs/thermoelectric/literature_survey/survey_report.md
- 发现报告: workspace/outputs/thermoelectric/literature_survey/discovery/discovery_report.md
