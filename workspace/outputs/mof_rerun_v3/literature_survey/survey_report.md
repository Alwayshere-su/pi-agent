# MOF 材料用于 CO₂ 捕获：吸附性能、湿度效应与构效关系综述

**调研主题**：MOF materials for CO₂ capture
**生成日期**：2026-08-11（第二轮检索补充至 2026-08-11 晚）
**文献规模**：77 篇（arXiv 33 + semantic_scholar 44），论文 ID p1–p77
**证据原则**：所有数值与结论均标注论文 ID，可追溯至 `papers.json`

---

## 摘要

金属有机框架（MOF）凭借超高比表面积、可调的孔道化学与结构多样性，已成为 CO₂ 捕获（烟气后燃烧捕集 PCC、直接空气捕获 DAC、沼气提纯）领域最具潜力的吸附剂类别。本综述基于 63 篇文献，系统梳理了 19 种代表性 MOF 体系的 CO₂ 吸附容量、CO₂/N₂ 选择性、等量吸附热（Qst）、湿度耐受性与循环稳定性，归纳了 13 条关键构效关系（R1–R13），识别出 5 个高价值研究空白（Gap 1–5）。核心发现：(1) 开放金属位点（OMS）与胺功能化是提升 CO₂ 亲和力的两大主策略；(2) 湿度效应存在方向性矛盾——竞争吸附可致容量下降 85%，而受限水/酰胺功能化可使容量保持 94% 甚至提升；(3) Qst 与容量的关系非单调，存在"低热高效"（Cu(adci)-2）与"高热高容"（MOF-74(Ni)）两个极端；(4) 柔性 MOF 呈现选择性随温度升高的反直觉行为，挑战刚性 MOF 的经典热力学标度律。

---

## 一、方法论与检索策略

| 检索词 | 来源 | 命中 |
|--------|------|------|
| CO2 capture metal-organic framework | semantic_scholar | 30 |
| MOF for CO2 adsorption | arxiv | 20 |
| carbon dioxide capture MOF | arxiv | 8 |
| MOF flue gas CO2 / MOF CO2 separation membrane | arxiv | 2 |
| 复用的历史 arxiv 缓存（MOF-74、CALF-20、mmen-Mg₂(dobpdc) 等） | arxiv(cache) | 10（并入） |

去重后共 63 篇唯一论文。数值数据经正则扫描从摘要中提取，关键数据点双重核对（容量数值 + 条件标注）。

---

## 二、材料体系全景（19 种 MOF）

### 2.1 开放金属位点（OMS）类——高亲和力路线
- **MOF-74 系列（M-DOBDC，M=Ni/Mg/Co/Zn）**：一维六方孔道 + 高密度 OMS。MOF-74(Ni)-24-140（优化合成）达 8.29/6.61 mmol/g @273/298 K、1 bar，为文献 MOF-74-Ni 的 2.0/2.1 倍；Qst 可调 27–52 kJ/mol；CO₂/N₂=49（p61）。CO₂-OMS 结合能 38–48 kJ/mol（p7）。36 种金属取代 vdW-DF 筛选显示 13 种落入 40–75 kJ/mol 目标热力学窗口，OMS 部分电荷可作为 ΔH 描述符（p23）。Fe-MOF-74 为磁性 Mott 绝缘体，需量子化学处理（p21）。**短板**：湿态结构不稳定（p32），H₂O/NH₃ 可置换 CO₂（p7）。
- **HKUST-1（M-HKUST-1）**：桨轮 SBU，金属取代筛选 5 种（Be/Mg/Ca/Sr/Sc）落入目标窗口（p23）。
- **Fe-soc（Fe-dbai）**：soc 拓扑 + 酰胺 + OMS 协同，6.4 mmol/g、CO₂/N₂=64 @298 K/1 bar，60% RH 工作容量保持 94%（p41）——**湿态性能最优的 OMS 材料之一**。
- **Cu(adci)-2**：超微孔 + 氨基 + Cu⁺，2.01 mmol/g @298 K/15 kPa，Qst₀ 仅 27.5 kJ/mol（低热高效），60% RH 仍可捕获（p37）。

### 2.2 胺功能化类——低浓度（DAC）高效路线
- **Mg₂(dobpdc)(二胺)**：双胺协同吸附，阶梯等温线 + 滞后，机理为链聚合（p14）；化学吸附+物理吸附协同突破 1 equiv CO₂/二胺 限制（p47）；H₂O 影响链式行为（p1）；可纺成 70% MOF 中空纤维、保持 98% 容量（p56）。
- **NICS-24（Zn-草酸 3,5-二氨基三唑）**：2 mbar/25°C 达 0.7 mmol/g，为 CALF-20 的 4 倍；CO₂/N₂ 8 倍、CO₂/O₂ 30 倍；但湿态容量 −85%（p36）。
- **PEI@CA/MIL-101(Cr) 单块体**：−20°C/400 ppm 达 1.05 mmol/g（干）/1.43 mmol/g（70% RH）；TSA 工作容量 0.95 mmol/g、60°C 再生（p40）。
- **MOF-177 胺功能化**（p42）、**超碱 IL 复合 MOF**（400 ppm 下 0.58 mmol/g，p45）、**Cu 基 NU-2100**（捕获+催化转化甲酸 100% 选择性，p50）。

### 2.3 水稳定/疏水类——湿烟气实用路线
- **CALF-20(Zn)**：>450,000 循环（蒸汽/湿酸性气）、低成本、可微波合成（时间 −12 倍、产率 97%、容量 +20%，p44）；等网状系列 PVSA 提纯 CH₄ 成本 $4.31/kg、能耗 9.35 kWh/kg（p19）；角孔道中 CO₂/H₂O 扩散异常（p3, p35）。
- **TYUT-ATZ-β**：将 H₂O 固定于扩散通道的反直觉策略，CO₂/N₂=2031 @298 K、75% RH 下 100+ 循环稳定（p49）。
- **ZnDatzBdc**：柔性 gate-opening MOF，氢键开关 + 苯环旋转驱动开/闭相变；CO₂/N₂=107(273 K)/129(298 K)、CO₂/CH₄=35/44；PVSA 理论工作容量 94.9 cm³/cm³（p48）。
- **UiO-66（Zr）**：结构化分级孔吸附剂，2.0 mmol/g、CO₂/N₂=17 @25°C/1 bar（p46）；凝胶形态设计（p12）。
- **Zn/Co-ZIF@ANF 气凝胶**：5.99 mmol/g、CO₂/N₂=35 @25°C/1 bar，10 循环保持 95.19%（p38）。

### 2.4 孔工程与多功能类
- **SNNU-196-Ni**：局部-全局协同孔分区（LGS-PSP），CO₂ 容量 +206%，光催化转化近 100%（p52）。
- **Li⁺@NOTT-101-(COOH)₂**：Li⁺ 螯合分区，C₂H₂ 205 cm³/g、C₂H₂/CO₂=13（p55）。
- **Ag₁₂bpy-NH₂**：微孔"CO₂ 中继" + 电还原位点，捕获-电还原一体化（p58）。
- **Pt-MOCOF**：MOF/COF 杂化单晶，光电还原 CO₂→乙醇 FE 83.5%（p59）。
- **MOF-CNFs 纤维素气凝胶**：0.15 bar/298 K 达 1.8 mmol/g，8 循环保持 97%（p43）。

### 2.5 计算/机器学习驱动的材料设计
GHP-MOFassemble 扩散模型（p2）、Mofasa 全原子潜扩散（p18）、LEGO-MOF（p30，纯 CO₂ 吸收相对提升 147.5%）、CarbNN 主动迁移学习（p5）、GFlowNets 逆设计（p11）、ALIGNN-GNN 预测吸附（p13）、MPNN 可解释模型（p24）、CRAFTED 等温线数据库（273/298/323 K × 2 力场 × 4 电荷方案，p4）、Open DAC 2023 数据集（p22）、MLIP-MC（p16）、MARTINI 粗粒化 MOF/聚合物（p15, p6）、MPTA 多组分理论（p9）、MatCreatioNN（12 万候选筛选，p17）、量子计算模拟（p20, p21）。

---

## 三、关键性质与性能基准

### 3.1 CO₂ 吸附容量基准（298 K 附近，1 bar 或标注条件）

| 材料 | 容量 (mmol/g) | 条件 | 论文 |
|------|---------------|------|------|
| MOF-74(Ni)-24-140 | 8.29 / 6.61 | 273 / 298 K, 1 bar | p61 |
| Fe-dbai | 6.40 | 298 K, 1 bar | p41 |
| Zn/Co-ZIF@ANF | 5.99 | 25°C, 1 bar | p38 |
| Cu(adci)-2 | 2.01 | 298 K, 15 kPa | p37 |
| UiO-66 结构化 | 2.00 | 25°C, 1 bar | p46 |
| NICS-24 | 0.70 | 25°C, 2 mbar | p36 |
| CALF-20 | 0.17 | 25°C, 2 mbar | p36 |
| PEI@MIL-101(Cr) | 0.60–1.43 | 25°C / −20°C, 400 ppm | p40 |
| TYUT-ATZ-β | 62.7 cm³/cm³ | 0.15 bar, 298 K | p49 |

### 3.2 选择性基准（CO₂/N₂）

| 材料 | 选择性 | 条件 | 论文 |
|------|--------|------|------|
| TYUT-ATZ-β | 2031 | 298 K | p49 |
| ZnDatzBdc | 107→129 | 273→298 K | p48 |
| Fe-dbai | 64 | 298 K, 1 bar | p41 |
| MOF-74(Ni) | 49 | 298 K | p61 |
| Zn/Co-ZIF@ANF | 35 | 25°C | p38 |
| UiO-66 | 17 | 25°C | p46 |

### 3.3 等量吸附热基准

| 材料 | Qst (kJ/mol) | 备注 | 论文 |
|------|--------------|------|------|
| Cu(adci)-2 | 27.5 | 低热，易再生 | p37 |
| MOF-74(Ni) | 27–52 | 合成条件可调 | p61 |
| M-MOF-74 (OMS) | 38–48 | CO₂-OMS 结合能 | p7 |
| M-DOBDC/HKUST-1 目标窗 | 40–75 | 13 种金属命中 | p23 |

---

## 四、核心构效关系（详见 knowledge_graph.md 关系表 R1–R13）

1. **R1/R2 — OMS 与亲和力**：OMS 密度与 CO₂ 结合能正相关（38–48 kJ/mol）；OMS 部分电荷是 ΔH 的简单描述符（36 金属筛选）。
2. **R3 — 合成-性能可调**：MOF-74(Ni) 合成温度/时长显著改变容量与 Qst（140°C/24h 最优），但连续映射缺失（→ Gap 5）。
3. **R4/R5 — 胺功能化双刃剑**：低浓度容量提升 4 倍、选择性 8–30 倍，但湿态容量 −85%（→ Gap 4）。
4. **R6 — 湿度效应方向性**：水竞争（−85%）vs 水增强/保持（+94%，S=2031）（→ Gap 1）。
5. **R7 — 柔性 MOF 选择性-温度反常**：ZnDatzBdc 选择性随 T 升高而增大（→ Gap 3）。
6. **R8 — 温度-容量负相关**：MOF-74(Ni) 与 PEI@MIL-101 均验证（van't Hoff 行为）。
7. **R9 — Qst-容量非单调**：低 Qst 高容量（Cu(adci)-2）vs 高 Qst 更高容量（MOF-74(Ni)）（→ Gap 2）。
8. **R10 — 孔分区增强**：SNNU-196-Ni 容量 +206%。
9. **R11 — 协同吸附机理**：双胺链聚合、化学+物理吸附协同。
10. **R12/R13 — 合成/成型工程**：MW 合成 +20% 容量；中空纤维/气凝胶成型保持 95–98% 容量。

---

## 五、研究空白（详见 gap_report.md，编号全局一致）

| 编号 | 主题 | 严重程度 | 置信度 |
|------|------|----------|--------|
| Gap 1 | 湿度效应方向矛盾（竞争 vs 增强），缺统一描述符 | 高 | 0.85 |
| Gap 2 | Qst–容量–再生能耗三角权衡无定量 Pareto 模型 | 高 | 0.80 |
| Gap 3 | 柔性 MOF 选择性-温度反常正相关，机理未验证 | 中 | 0.70 |
| Gap 4 | 胺功能化容量-湿度 Pareto 权衡未量化 | 中 | 0.75 |
| Gap 5 | 合成条件-性能连续映射缺失 | 中 | 0.65 |

---

## 六、结论与展望

1. **材料设计主线**：OMS 工程（MOF-74 系列）与胺功能化（Mg₂(dobpdc)、NICS-24）分别主导"高容量"与"低浓度高效"两条路线；水稳定材料（CALF-20、TYUT-ATZ-β、ZnDatzBdc）正成为湿烟气实用化的突破口。
2. **最大争议**：湿度效应方向矛盾（Gap 1）与 Qst 非单调权衡（Gap 2）——两者直接决定吸附剂从实验室走向烟囱/大气的可行性。
3. **ML 加速趋势**：生成模型（Mofasa、GHP-MOFassemble）与图神经网络（ALIGNN）已能高通量预测/生成候选，但实验闭环验证数据仍稀缺，形成"计算推荐-实验确认"的断层。
4. **下一阶段方向**：针对 Gap 1–5 生成可验证构效关系假设，用量化建模（候选 vs 经典模型对比、符号回归）从文献数值中提取统计规律，并经外部数据库交叉验证。

---

## 参考文献（核心 20 篇，完整 63 篇见 papers.json）

| ID | 论文 | DOI/来源 |
|----|------|----------|
| p61 | Taming structure and modulating CO₂ adsorption isosteric heat of MOF-74(Ni) | semantic_scholar |
| p48 | High-Performance Selective CO₂ Capture on ZnDatzBdc (gate-opening) | semantic_scholar |
| p40 | Cold Temperature Direct Air CO₂ Capture with Amine-Loaded MOF Monoliths | semantic_scholar |
| p41 | Efficient CO₂ Capture under Humid Conditions on Fe-dbai | semantic_scholar |
| p36 | Amine-Functionalized Triazolate-Based MOFs (NICS-24) | semantic_scholar |
| p49 | Immobilization of H₂O in TYUT-ATZ-β for humid flue gas | semantic_scholar |
| p37 | An Amine-Functionalized Ultramicroporous MOF Cu(adci)-2 | semantic_scholar |
| p38 | Bimetallic Zn/Co-ZIF@ANF aerogels | semantic_scholar |
| p44 | Microwave-Assisted Synthesis of CALF-20 | semantic_scholar |
| p19 | Techno-economic Evaluation of CALF-20 PVSA | arxiv, 10.1039/D5ME00131E |
| p23 | Thermodynamic Screening of Metal-Substituted MOFs | arxiv |
| p7 | Competitive co-adsorption in M-MOF-74 | arxiv, 10.1021/acs.chemmater.5b00315 |
| p14 | Hysteresis curves of cooperative CO₂ in diamine-Mg₂(dobpdc) | arxiv |
| p47 | High-Capacity Cooperative CO₂ Capture (diamine-MOF) | semantic_scholar |
| p13 | GNN Predictions of MOF CO₂ Adsorption | arxiv, 10.1016/j.commatsci.2022.111388 |
| p4 | CRAFTED isotherm database | arxiv |
| p22 | Open DAC 2023 Dataset | arxiv |
| p32 | Understanding and Controlling Water Stability of MOF-74 | arxiv(cache) |
| p26 | Water-stable MOFs for CO₂ Capture from Ambient Air | arxiv |
| p3/p35 | Abnormal CO₂/H₂O Diffusion in CALF-20 | arxiv |
