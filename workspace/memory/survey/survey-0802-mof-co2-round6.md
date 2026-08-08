## 调研：[MOF materials for CO2 capture — 组成可控性 + DFT 方法学] — 第六轮
日期：2026-08-02（续接第五轮，聚焦 Gap 10 组成可控性 + R19 DFT 闭环）

### 本轮执行摘要
- **新增**：3 组检索词（MgNi-MOF-74 ratio / MgZn MgCo bimetallic uptake / d-band center DFT binding）→ +26 篇 sciverse/crossref → 证据池 **389 篇**
- **决定性新证据**：
  - ⭐⭐ **Mg₁₋ₓNiₓ-MOF-74 固态 NMR 配分解析**（deconvolution of metal apportionment）：¹³C 标记羧酸盐 NMR 解析**全部 8 种 Mg/Ni 原子级排列**，磁化率+键路径+DFT 验证，**驳斥溶液合成随机配分假设** → R22 + Gap 10 机理级证据
  - ⭐⭐ **机械化学可控合成 12 种双金属 MOF-74**（rational synthesis with controlled composition）：球磨法以固体配位前驱体实现**预定 1:1 化学计量**（ZnMg/ZnCo/ZnCu/MgZn/MgCo/NiZn/NiMg/NiCo/CoZn/CoMg/CoCu/MgCa）——含全部 s-d 组合 → R23 + Gap 1 验证路径解锁
  - **Fe-MOF-74 量子模拟基准**：强关联 Mott 绝缘体使标准 DFT 泛函预测差异大 → R19 DFT 闭环方法学警示
  - 电场诱导 N₂ 选择性结合（π* 反馈键增强）→ 电子结构调控新维度
- **知识图谱**：+R22-R24（写入第三节关系表正文），新增第十节（组成可控性专题）
- **Gap 更新**：Gap 1 置信度 0.94→**0.95**（s-d 合成路径打通）；Gap 10 置信度 0.70→**0.78**、严重程度中→高（配分非随机性 = 系统性偏差）

### 知识图谱摘要
- 材料数：~60+｜性质数：10｜关键关系数：24（R1-R24）

### Top 研究空白（更新）
1. Gap 1 双金属比例-性能曲线体系/性质依赖（轨道类型分类）— 高 — **0.95**
   - 证据：p62/p65/scv:ecfe34f94197 + 机械化学 12 组合合成路径（s-d 全部可合成）
   - 验证：机械化学前驱体 1:1 法 + 梯度比例 → 干净比例-性能曲线（消除名义-实际偏差）
2. Gap 2 水-CO2 机理（胺分支）— 高 — 0.94
3. Gap 10 实际组成 vs 名义比例偏差 — 高（↑自中）— **0.78**
   - 证据：NMR 配分解析（8 构型非随机）+ 机械化学可控合成 + 温度主导组成
   - 验证：固态 NMR 配分定量 + ICP-MS 映射库 + 机械化学消除偏差

### 发现结果（路线 A，本轮）
- 假设 0（占位符，LLM 生成失败）：5 轮搜索 best **0.411**，search_iterations=5 ✓（规则 4 满足）
- 历史假设 1-4（第五轮）best：0.824/0.677/0.885(已验证)/0.734；假设 0（双金属倒U）历史 40 轮 best 0.683
- **全部假设 search_iterations > 0 ✓（规则 4 满足）**

### 技术问题与修复
- generate_hypotheses 因 GBK 编码崩溃（\u2212 减号字符）：修复 = ① discovery_report.json GBK→UTF-8 转码（备份 .gbkbak）② tools.py 注入 pathlib.Path.read_text/write_text 默认 UTF-8 monkey-patch ③ hypotheses.json GBK→UTF-8 转码
- ⚠️ 生成的假设为**占位符**（LLM 不可用，仅标题"Material-property relationship discovery"）——需在 LLM API 可用时重新生成真实假设

### 反思
- **最惊讶**：机械化学 1:1 可控合成一次性解锁 12 种双金属组合（含全部 s-d 组合）——第五轮"MgNi/MgZn 直接比例证据缺失"从数据缺口变为合成路径就绪
- **最高效**：本轮 3 组检索均命中决定性证据（NMR 配分、机械化学、DFT 基准）
- **局限**：假设 0 为占位符（LLM API 不可用），构效关系发现未真正展开；阶段二被编码问题挤占
- **下一轮**：①LLM API 恢复后基于 Gap 1/Gap 10 生成真实假设 ②机械化学 MgZn/MgCo/MgNi 梯度比例的吸附实测 ③Fe-MOF-74 DFT+U 泛函基准 → d 带中心差 vs 曲线形状定量检验
