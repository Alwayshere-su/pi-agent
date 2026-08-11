# Agent 调研记忆 — MOF 材料用于 CO₂ 捕获（mof_rerun_v3）

> 调研日期：2026-08-11 | 运行目录：workspace/outputs/mof_rerun_v3/
> 阶段一 + 阶段二（路线 A）完整执行

## 调研：[MOF materials for CO2 capture]

### 检索策略
- 数据源：semantic_scholar（44 篇）+ arXiv（27 篇）+ 复用历史 arxiv 缓存（10 篇，含 MOF-74/CALF-20/mmen-Mg2(dobpdc)）
- 有效检索词：`CO2 capture metal-organic framework`（SS 30 命中）、`MOF for CO2 adsorption`（arXiv 20）、`carbon dioxide capture MOF`（arXiv 8）、`MOF flue gas CO2`（1）、`MOF CO2 adsorption temperature dependence`（SS 15，第二轮）
- ⚠️ 检索服务特性：复杂查询词（含连字符 MOF-74/ZIF-8、多关键词组合）常返回 0 命中；短查询（3-4 词）成功率最高；间歇性故障需等待重试
- 共 77 篇唯一论文（p1–p77，第二轮新增 p64–p77：柔性 gate MOF p71、MOF-808-NH2/GO 响应面 p65、CALF-20 平衡传输 p70、尿素湿耐受 p67、四胺 MOF p66 等）

### 知识图谱摘要
- 材料数：19 种 MOF 体系（M1–M19）
- 性质数：9 类（P1–P9：容量/选择性/Qst/工作容量/结合能/水稳定性/循环性/比表面积/成本）
- 关键关系数：13 条（R1–R13，见 knowledge_graph.md）
- 量化建模数值表 5 张（温度-容量 MOF-74(Ni)、温度-选择性 ZnDatzBdc、温度-容量 PEI@MIL-101、材料-容量排序、Qst-容量）

### Top 研究空白
1. **Gap 1 湿度效应方向矛盾** — 严重程度：高 — 置信度：0.85
   证据：p36(−85% 水竞争), p41(+94% 酰胺保持), p49(S=2031 固定水), p40(+36% 湿态反升), p7, p32
   验证方案：同一 MOF 家族 RH 梯度容量-湿度曲线 + DFT 水簇形成能/CO₂ 置换能垒
2. **Gap 2 Qst–容量非单调权衡** — 严重程度：高 — 置信度：0.80
   证据：p37(Cu(adci)-2: Qst=27.5 低热高容量), p61(MOF-74(Ni): Qst 27–52 高热高容), p23(40–75 kJ/mol 目标窗), p7(38–48 kJ/mol)
   验证方案：收集 (Qst₀, 容量@0.15bar, 容量@1bar) 三元组，符号回归找火山型
3. **Gap 3 柔性 MOF 选择性-温度反常** — 中→高 — 0.70→0.80（p48: S=107→129 随 T 升；**p71 新增**：1D MOF gate 压力温度依赖大、建议 TSA）
4. **Gap 4 胺功能化容量-湿度 Pareto** — 中 — 0.75（p36 vs p41/p45）
5. **Gap 5 合成条件-性能映射缺失** — 中 — 0.65（p61, p44）

### 发现结果（路线 A）
1. **[已验证] Qst–容量非单调权衡（hypo_1）** — 置信度 0.87，Search Best 0.872
   材料：Cu(adci)-2, MOF-74(Ni), M-MOF-74, NICS-24, CALF-20
   关系：低压容量对 Qst 火山型（峰位 ≈40 kJ/mol），高压容量随 Qst 饱和
   外部验证：CoRE MOF 2014/hMOF 命中（MOF-74: 容量 3.0–8.6 mmol/g、Qst 20–50 kJ/mol 交叉吻合）
   模型对比：候选三次 R²=0.215 vs 经典 Slack R²=0，嵌套 F 检验 F(2,29)=3.97 p=0.030 显著（candidate_better）
2. [待验证] 胺功能化 Pareto 权衡（hypo_3）— 0.82，Search 0.817，LLM 0.78
3. [待验证] 合成响应曲面（hypo_4）— 0.82，Search 0.816，LLM 0.45（证据链存疑）
4. [待验证] 湿度增强指数 η（hypo_0）— 0.78，Search 0.662，LLM 0.42（线性标度过度简化）
5. [待验证] 柔性 MOF 选择性-温度（hypo_2）— 0.70，Search 0.664，LLM 0.78
- 跨主题连接 24 条（cathode/perovskite/thermoelectric/mof_e2e_v4）
- 独立量化验证（discovery/quant_verification_supplement.md）：ZnDatzBdc 选择性-温度 R=1.000 (dS/dT=+0.88/K, p<0.001) 统计确认反常；PEI@MIL-101 温度-容量 R²=0.79；MOF-74(Ni) 温度-容量斜率 −0.054 mmol/g/K

### 反思
- **最令人惊讶的发现**：柔性 MOF（ZnDatzBdc）的 CO₂/N₂ 选择性随温度升高而增大（107→129），与刚性 MOF 的 van't Hoff 行为完全相反——若普适，将反转 TSA 操作逻辑
- **最高效的搜索方向**：`MOF for CO2 adsorption`（arXiv 命中 20 篇高质量计算/ML 论文）；短查询优于复杂查询
- **工具经验**：run_model_comparison/symbolic_regression 从 knowledge_graph 提取数据时按 hyp.property 的 unit_filter 过滤，混合多表列导致 x/y 错配；无量纲性质（选择性 107/129）超出裸数字 0.01–20 范围被排除——量化表设计需单表单关系
- **下一轮迭代应聚焦**：(1) 补充 MOF-74(Ni) 多温度（323/348/373K）容量数据扩展量化表；(2) 用响应面 DoE 文献验证 hypo_4；(3) 寻找更多柔性 MOF（ELM-11/MIL-53）选择性-温度数据验证 hypo_2
