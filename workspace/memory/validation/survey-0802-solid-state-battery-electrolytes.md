## 调研：固态锂电池电解质（solid-state lithium battery electrolytes）

### 检索策略
- 检索词：solid-state lithium battery electrolytes review / garnet LLZO doping / Li6PS5Cl argyrodite / Li3InCl6 halide / PEO polymer transference number / lithium metal anode interface / machine learning ionic conductivity prediction
- 数据源：arXiv + Semantic Scholar（Sciverse），85 篇命中（P001–P085）
- 日期范围：2026-08-02（单次运行）

### 知识图谱摘要
- 材料数：~40（硫化物/氧化物/卤化物/聚合物/玻璃/高熵）
- 性质数：10（σ、Ea、CCD、界面电阻、t+、稳定窗口、热导率、湿度稳定性、晶界电导、电子电导）
- 关键关系数：14（R1–R14，见 knowledge_graph.md）

### Top 研究空白
1. Gap 1: 卤化物 SSE 系统数据稀缺 — 高 — 0.75
   证据：P040, P070, P006
   验证：构建卤化物 σ/Ea/掺杂数据集，与硫/氧化物同条件对比
2. Gap 2: 硫化物电导-湿度稳定性权衡缺定量模型 — 高 — 0.7
   证据：P024, P031, P027, P023
   验证：掺杂系列 H2S 速率 vs σ 的 Pareto 前沿
3. Gap 3: ML 预测-实验验证闭环缺失 — 中高 — 0.65
   证据：P068, P080, P079
   验证：OBELiX 候选的实验合成实测
4. Gap 4: 聚合物 t+-σ 权衡机制不清 — 中 — 0.6（证据 P038, P039）
5. Gap 5: 界面电阻策略普适性未知 — 中 — 0.6（证据 P047, P017）

### 发现结果（路线 A）
1. 假设0 卤素比例调控卤化物电导-湿度非线性 — 已搜索(6轮) best 0.314 — 置信度 0.72
2. 假设1 氧/钼双掺杂硫银锗矿双目标优化 — 已搜索(5轮) best 0.786 — 置信度 0.79 ← 最佳
3. 假设2 高熵阳离子无序度火山型关系 — 已搜索(5轮) best 0.274 — 置信度 0.65
4. 假设3 Lewis 酸性聚合物 t+-σ 非单调调控 — **未搜索**（预算拦截）
5. 假设4 双层界面设计普适降阻 — **未搜索**（预算拦截）
- ⚠️ 外部验证（Materials Project/OQMD）未执行（预算不足）

### 反思
- 最令人惊讶的发现：Mo-O 双掺杂可同时改善硫化物电导率与湿度稳定性（3.97 mS/cm + H2S↓66%），打破"电导-稳定性"简单权衡叙事（P024, P031）
- 最高效搜索方向：具体材料-性质组合检索（Li6PS5Cl argyrodite 命中 25 篇）；宽泛综述词命中率低
- 下一轮迭代应聚焦：① 完成假设3、4 的 discovery search；② validate_discovery 全部假设；③ 补充卤化物 SSE 专项检索
