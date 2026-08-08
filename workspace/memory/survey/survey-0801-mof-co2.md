# 调研记忆：MOF 材料用于 CO2 捕获

## 调研：[MOF materials for CO2 capture]
日期：2026-08-01

### 检索策略
- 检索词：MOF CO2 capture adsorption / CO2-N2 selectivity / Mg-MOF-74 OMS isosteric heat / amine-functionalized MOF post-combustion / high-throughput screening ML / ultramicroporous sieving / humid flue gas stability / direct air capture
- 数据源：sciverse(120) + arXiv(14)，共 134 篇带摘要论文（缓存 153 条，19 条无摘要）
- 8 组检索词多角度覆盖，缓存于 workspace/data/literature_cache/search_results.json + papers.json

### 知识图谱摘要
- 材料数：~40（MOF-74 系 / ZIF 系 / MIL 系 / UiO 系 / HUM / MOF 衍生碳 / 胺功能化体系）
- 性质数：8（CO2 容量、CO2/N2 选择性、Qst、水稳定性、再生性、BET、超微孔体积、OMS 密度）
- 关键关系数：8（R1-R8，见 knowledge_graph.md）

### Top 研究空白
1. 双金属 MOF-74 金属比例-容量定量关系缺失 — 高 — 0.85
   证据：p62（NiCo 8.30 vs Ni 3.99/Co 5.03）、p20（Ni 8.29 矛盾）、p68
   验证方案：GCMC/DFT 计算 + 梯度金属比合成（0-100% 步长 10%）
2. 水-CO2 竞争/协同机理矛盾 — 高 — 0.9
   证据：p16（水促进）vs p129（无影响）vs p139（无竞争）vs p128（衰减）
   验证方案：统一 0-90% RH breakthrough 矩阵
3. 容量-选择性-再生能 Pareto 前沿未刻画 — 高 — 0.8
   证据：p27（Qst 29 甜点）、p118（25-40 窗口）、p120/p36
   验证方案：50+ 材料三维性能图
4. ML 筛选-实验闭环断裂 + 数据库误差（LitMOF p17）— 中 — 0.75
5. DAC 400 ppm 数据稀缺 — 中 — 0.8
6. OMS 密度-Qst 标度律缺失 — 中 — 0.7

### 发现结果（路线 A）
1. 【最高分】中等 Qst 窗口（29-40 kJ/mol）→ 捕获-再生综合最优 — 置信 0.89 — 待验证
   材料：ED@MOF-520、MNOUC、mmen-Mg₂(dobpdc)
   性质：工作容量/再生能耗权衡；预期 Qst<25 选择性<50，Qst>45 再生能耗>120 kJ/mol
2. 双金属 Ni:Co≈1:1 非线性协同（倒 U 型，峰值 ~8.3 mmol/g）— 置信 0.82 → **获 p169 机制支撑（混合金属热力学偏好 + 水稳定性提升）** — 待验证
3. OMS 密度-Qst 线性标度律（斜率 ~2-4 kJ·g/mmol）— 置信 0.82 — 待验证
4. 胺功能化 MOF 容量随 RH 先升后降（峰值 30-50% RH）vs OMS 型单调下降 — 置信 0.86（搜索后提升）— **获 p166/p168 机理支撑（水解离占据 OMS）** — 待验证
- 外部验证：Materials Project/OQMD **0 命中** → 发现"传统无机数据库对 MOF 气体吸附性质覆盖不足"，本身是 Gap 4 的延伸证据
- 补充计算：金属电负性 vs Qst 相关系数 r=-0.579（方向正确，说明需多因素模型）

### 第二轮补充（+35 篇，总计 152 篇）
- 关键新证据：p168（水解离机理）、p169（混合金属偏好+水稳）、p166/p167（水解路径/屏障）、p170（等网状疏水调控）、p153/p157/p159/p165（再生工艺）
- Gap 2 置信度 ↑0.92（OMS 分支机理已解，胺分支待验证）；Gap 1 ↑0.88
- 新增 Gap 7：材料-再生工艺耦合优化缺失（中，0.7）
- 新增构效关系 R9（双金属水稳）、R10（水解离机理）、R11（配体疏水化）

### 反思
- 最令人惊讶：水对 CO2 吸附的影响存在完全相反的结论（促进/无影响/衰减并存），说明该领域缺乏统一实验协议
- 最高效方向：以 MOF-74 系（OMS）为中心的知识图谱密度最高，双金属协同是文献证据最集中的 Gap
- 下一轮迭代：①外部验证可尝试用 OQMD 金属氧化物稳定性近似 MOF 热稳定性 ②增加实验合成类文献检索 ③针对 Qst 甜点区假设补充胺功能化体系文献
