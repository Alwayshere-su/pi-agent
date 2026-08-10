# 文献调研报告：卤化物钙钛矿带隙与稳定性（halide perovskite band gap and stability）

> 生成日期：2026-08-02 ｜ 更新日期：2026-08-10（第二轮：71 篇论文，新增 37 篇）
> 覆盖范围：铅基/无铅钙钛矿、双钙钛矿、带隙计算方法、稳定性机制、组分工程、压力/界面调控、温度-带隙反常行为、ML/高通量预测

---

## 1. 执行摘要

本调研围绕卤化物钙钛矿的两大核心性质——**带隙（band gap）**与**稳定性（stability）**展开，基于 71 篇论文（arXiv 预印本 + Semantic Scholar）。文献呈现三条主线：(1) 铅基钙钛矿（MAPbI3、FAPbI3、CsPbI3 系列）带隙优异（~1.5-1.6 eV）但稳定性不足、含 Pb 毒性；(2) 无铅双钙钛矿（Cs2AgBiBr6 为基准）稳定性好但带隙偏大且为间接带隙；(3) 计算与机器学习方法正加速带隙预测（p53 的 495 化合物、p65 的 1221 化合物数据集），但带隙与稳定性的**联合定量描述符**仍缺失。第二轮新增证据揭示：温度-带隙反常行为（dEg/dT>0，p36/p38/p39/p49）、电离能稳定性判据（p50）、Cs1-xRbxPbI3 分解热力学（p57）、ML 联合预测可行性（p60）。

**核心研究空白**："带隙-稳定性 trade-off 缺乏定量框架"（Gap 1，置信度 0.85）与"温度-带隙反常标度缺失"（Gap 6，新识别，0.78）。

## 2. 文献综述

### 2.1 铅基卤化物钙钛矿：带隙与稳定性的矛盾

MAPbI3 等杂化铅卤钙钛矿具有理想带隙（~1.55 eV）、高吸收系数和高载流子迁移率，光伏效率超 25%，但长期环境稳定性不足（湿/热/光降解）且 Pb²⁺ 水溶性毒性阻碍商业化（p8, jacs.6b09645）。全无机 CsPb(I1-xBrx)3 固溶体化学稳定性增强，带隙随 Br 含量线性可调（p4/p52, PhysRevMaterials.4.045402）。混合阳离子 FAxMA1-xPbI3 存在温度诱导 gap bowing（p49），Cs1-xRbxPbI3 在 Rb≈0.7 达到效率-稳定性最优、RbPbI3 立方相永不稳定（p57）。

### 2.2 无铅双钙钛矿：稳定性与带隙的折中

无铅双钙钛矿 A2BB'X6 是替代铅基的主线。基准材料 **Cs2AgBiBr6** 稳定性高、无毒，但带隙 1.72-1.98 eV 且为**间接带隙**（p14, anie.202005568; p17, er.8099）。关键调控手段：
- **Ag-Bi 无序增强**：降带隙 ~0.26 eV，达到 1.72 eV 最低记录（p14）
- **Pb²⁺ 微量掺杂**：间接→直接带隙转变（p11, PhysRevMaterials.2.055401）
- **压力调控**：Cs2AgBiBr6 在 2.3 GPa 立方→四方相变，带隙红移→蓝移（p15, c9nr07030c）
- **厚度调控**：2D 化降带隙、提升光催化性能（p16, d0cp03919e）
- **新体系**：Cs2InAgCl6 理论预测直接带隙（p1, 1611.05426v2）；AgInI4 直接带隙 1.72 eV 且稳定（p70）；Cs2Au2X6 可见带隙低激子结合能（p67）；Cs2CuBiCl6（p62）；K2SnGeX6 带隙 0.64-2.44 eV 卤素可调（p66）

### 2.3 带隙计算方法学

- **DFT-1/2 方法**：以 DFT 成本达到 GW 精度（p2, s41598-017-14435-4）
- **VCA 虚拟晶体近似**：CH3NH3Pb(I1-xBrx)3 带隙-组成遵守 Vegard 律二次拟合（p13, PhysRevB.94.125139）
- **HSE 混合泛函**：exact-exchange 线性增长方案精确预测 CsPb(I1-xBrx)3（p4/p52）
- **有限温度带隙方案**：范围分离杂化 + SOC + 零点振动 special displacement 法，MAE 0.17 eV vs 实验（p46）

### 2.4 温度-带隙反常行为（第二轮新增主线）

- **CsSnI3**：振动重正化**打开**带隙 0.11 eV@300K / 0.24 eV@500K（反常 dEg/dT>0，p36, PhysRevB.92.201205）
- **CsPbBr3**：非谐振动贡献达 450 meV@425K，带隙随温度"温和变化"（p38）；overdamped 声子机制（p37）
- **铅卤化物普遍反常**：带隙随温度降低而降低（p39, jpclett.9b00876）；高压实验分离热膨胀与电声耦合
- **FA-MA gap bowing**：电子-声子耦合主导，FA rattler 模式耦合八面体倾斜（p49）

### 2.5 稳定性机制

- **内禀局域畸变**（polymorphous networks）：不随时间平均为零，决定带隙与稳定性（p3, mattod.2021.05.021; p10, PhysRevB.101.155137; p56）
- **离子迁移**：决定长期稳定性（p12, D0TA03200J）
- **锡基氧化**：FASnI3 中 Sn²⁺→Sn⁴⁺ 氧化是主要降解路径，Lewis 碱表面钝化（分子硬度主导）（p34, mtener.2022.101038）
- **电离能稳定性判据**：分解反应焓与电离能关联，容差/八面体因子不足以预测（p50, jpcc.7b00333）
- **ML+DFT 分解能**：稳定性工程（p51）；AVA2FAPb2I7 准 2D 添加剂稳定晶界（p55）
- **2D/3D 异质界面**：界面电荷转移增强抗降解性且不损效率（p33, acsami.5c00201）；MAPbI3/BN 室温稳定（-25 meV@300K）（p5）

### 2.6 ML 与高通量预测（第二轮新增）

- **p53**：495 个 ABX3 卤化物钙钛矿高通量 DFT 数据集
- **p65**：1221 个 A2BB'X6 双钙钛矿，4 类物理描述符（packing/bonding/polarization/electronic identity），凸包 E_hull≤0 筛选
- **p60**：ML 联合预测带隙 RMSE 21 meV + 形成能 39 meV/atom
- **p64**：ML 筛选无铅双钙钛矿光伏；**p19**：联合预测稳定性和带隙（摘要缺失细节）；**p41**：ML 双钙钛矿带隙

## 3. 关键材料与性质对比

| 材料 | 带隙 (eV) | 带隙类型 | 稳定性 | 备注 | 来源 |
|------|----------|---------|--------|------|------|
| MAPbI3 | ~1.55 | 直接 | 差（湿/热） | 铅基基准 | p2 |
| CH3NH3Pb(I1-xBrx)3 | 1.55→2.3 | 直接 | 中 | Vegard 律二次拟合 | p13 |
| CsPb(I1-xBrx)3 | 1.7→2.4 | 直接 | 较好 | 全无机 HSE | p4/p52 |
| Cs2AgBiBr6 | 1.72-1.98 | 间接 | 高 | 无铅基准 | p14/p17 |
| CsSnI3 | ~1.3 | 直接 | 中（非谐稳定） | dEg/dT>0 反常 | p36 |
| CsPbBr3 | ~2.3 | 直接 | 较好 | 非谐贡献 450 meV@425K | p38 |
| FASnI3 | ~1.4 | 直接 | 差（氧化） | 锡基 | p34 |
| CH3NH3BaI3 | 3.87 | 直接 | 高 | 宽带隙 | p7 |
| MA2PtI6 | ~2.0 | — | 中 | dEg/dP=0.063-0.079 eV/GPa | p20 |
| AgInI4 | 1.72 | 直接 | 高 | In 替代 Bi 稳定 | p70 |
| K2SnGeI6 | 0.64 | [待验证] | 高 | 卤素替换至 I | p66 |
| Cs2Au2I6 | 可见区 | 直接 | 较好 | 低激子结合能 | p67 |

## 4. 研究空白与未来方向

1. **Gap 1（高，0.85）**：带隙-稳定性 trade-off 无定量联合描述符 → 构建联合数据集检验 Pareto 前沿（新增 p50/p57/p65 证据）
2. **Gap 6（高，0.78，新增）**：温度-带隙反常行为（dEg/dT>0）缺乏统一标度 → 计算 dEg/dT 与电声耦合/rattler 频率关联
3. **Gap 2（高，0.80）**：间接→直接带隙调控手段缺乏系统性比较 → 同一母体上对比无序/掺杂/压力/厚度
4. **Gap 3（中，0.80）**：ML 带隙预测与稳定性预测脱节 → 多任务学习联合预测（p60 证明技术上可行）
5. **Gap 4（中，0.75）**：压力-带隙响应体系间标度缺失 → 计算 dEg/dP 与描述符关联
6. **Gap 5（中，0.70）**：2D/3D 界面电荷转移-带隙-稳定性耦合定量缺失 → 系统扫描界面参数

## 5. 阶段二发现摘要（路线 A）

基于 5 条假设（覆盖 Gap 1/2/3/4/6）完成贝叶斯搜索（每条 10 轮、21 候选），2 条假设通过外部数据库验证：

1. **✅ 带隙-稳定性 trade-off（hypo_0）**：搜索 best 0.964；OQMD 验证 I 0.716 eV / Br 1.349 eV；文献数值 15 个；置信度 0.96 → 窄带隙体系（Sn²⁺/低价态）系统性不稳定，存在 Pareto 型边界
2. **✅ 双钙钛矿间接→直接调控（hypo_2）**：搜索 best 0.966；OQMD 验证 Cl 2.661→Br 1.349→I 0.716 eV（卤素替换降带隙趋势，与 p66 一致）；置信度 0.97
3. **⏳ 温度-带隙反常标度（hypo_1）**：best 0.964；Slack 经典模型在卤化物钙钛矿上失效（R²≈0），LLM 归因于非谐声子/电声耦合主导——需更多温度数据点
4. **⏳ ML 联合预测（hypo_4）**：best 0.882；技术可行（p60），带隙-稳定性可分离性待验证
5. **⏳ 压力-带隙分段标度（hypo_3）**：best 0.960；MA2PtI6 1.2 GPa 分段闭合规律待外部数据补全

## 6. 参考文献（关键可追溯）

| # | 论文 | DOI/ID |
|---|------|--------|
| 1 | Accurate and efficient band gap predictions of metal halide perovskites using the DFT-1/2 method | 10.1038/s41598-017-14435-4 |
| 2 | Anharmonic stabilization and band gap renormalization in the perovskite CsSnI3 | 10.1103/PhysRevB.92.201205 |
| 3 | Anharmonic Fluctuations Govern the Band Gap of Halide Perovskites | arXiv 2023 |
| 4 | On the role of the electron-phonon interaction in the temperature dependence of the gap | 10.1021/acs.jpclett.9b00876 |
| 5 | Ionization energy as a stability criterion for halide perovskites | 10.1021/acs.jpcc.7b00333 |
| 6 | A High-Throughput Computational Dataset of Halide Perovskite Alloys | arXiv 2023 |
| 7 | First-principles study on the chemical decomposition of CsPbI3 and RbPbI3 | arXiv 2018 |
| 8 | Machine-learning Based Screening of Lead-free Halide Double Perovskites | arXiv 2022 |
| 9 | Genome-Guided Interpretable Screening of Phase-Stable Lead-Free Double Perovskites | arXiv 2026 |
| 10 | Origin of the Temperature-Induced Gap Bowing of Formamidinium-Methylammonium Lead Iodide | arXiv |
| 11 | Lead-Free Halide Double Perovskite Cs2AgBiBr6 with Decreased Band Gap | 10.1002/anie.202005568 |
| 12 | Pressure-induced band gap closing of (CH3NH3)2PtI6 | 10.1088/1674-1056/adce9e |
| 13 | Design of Lead-Free Inorganic Halide Perovskites for Solar Cells via Cation-Transmutation | 10.1021/jacs.6b09645 |
| 14 | Cu-In Halide Perovskite solar absorbers | 10.1021/jacs.7b02120 |
| 15 | Computational Screening and Discovery of Silver-Indium Halide Double Salts | arXiv 2025 |
| 16 | Efficiently charting the space of mixed vacancy-ordered perovskites by ML | arXiv 2025 |
| 17 | Machine learning stability and band gap of lead-free halide double perovskite materials | 10.1016/j.solener.2021.09.030 |
| 18 | Influence of halide composition on mixed CH3NH3Pb(I1-xBrx)3 perovskites | 10.1103/PhysRevB.94.125139 |
| 19 | Optoelectronic Properties and Defect Physics of Cs2Au2X6 | 10.1103/PhysRevApplied.13.014005 |
| 20 | First-Principles Study of Novel Lead-Free Double Perovskite beta2SnGeX6 | arXiv 2026 |

> 完整 71 篇论文摘要见 paper_summaries.md；Gap 定义见 gap_report.md；知识图谱（含量化建模数值表）见 knowledge_graph.md；发现报告见 discovery/discovery_report.md。
