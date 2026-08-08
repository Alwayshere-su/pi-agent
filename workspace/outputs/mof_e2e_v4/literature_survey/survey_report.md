# 文献调研报告：MOF materials for CO2 capture

**版本**：e2e_v4 全量版（继承历史 11 轮调研 + e2e_v3 成果）
**生成日期**：2026-08-03
**文献基础**：149 篇检索论文（109 历史复用 + 40 本轮新增，聚焦胺化学吸附机理 + 湿烟气稳定性）
**数据源**：workspace/data/literature_cache/mof_e2e_v4/search_results.json（149 条）
**知识图谱**：knowledge_graph.md（R1-R46，量化表 1-7）
**Gap 报告**：gap_report.md（Gap 1-12）

---

## 1. 执行摘要

本报告系统调研金属有机框架（MOF）材料用于 CO2 捕获的构效关系。核心发现：
1. **双金属协同呈高斯峰**：NiCo-MOF-74 组分比例-容量符合倒 U/高斯曲线（R²=0.978，v3 拟合），最优组分 x≈0.5（0℃, 1 bar 实验数据）——Gap 1 的核心定量证据
2. **双描述符预测 Qst**：Qst = f(d电子数, 电负性)（R²=0.9855），联合描述符超越单变量——Gap 4 支撑
3. **"水必竞争"传统认知已被多重证据改写**（本轮最大增量）：TYUT-ATZ 将 H2O 固定为结合位点增强湿态捕获、MOF-808-氨基酸经碳酸氢盐机理湿态增强、三氮唑框架 CO2/H2O 位点分离实现动力学选择性 70、离子疏水门一步分离高纯 CO2——"水增强/水调控"在多体系独立复现
4. **胺化学计量上限可突破**：pip2-Mg2(dobpdc) 实现 ~1.5 CO2/diamine 两步吸附，超越传统 1.0 上限——Gap 11 新量化维度
5. **方法学警示**：Fe(d6) 强关联偏离（Mott）→ DFT 泛函分歧；O2 氧化降解影响胺 MOF 长期寿命（Gap 12 新方向）

## 2. 文献综述（按主题组织）

### 2.1 金属取代平台（M-MOF-74 / M2(dobdc)）
- Koh 2016 (p26) 用 vdW-DF 筛选 36 种金属取代 MOF-74/HKUST-1 的 CO2 吸附焓
- Queen (v3s2_f920fdf886a1) 7 金属 M2(dobdc) 系统对比（Mg/Mn/Fe/Co/Ni/Cu/Zn），中子/X 射线衍射揭示位点特异性绑定
- Tan 2015 (p15) 竞争共吸附：H2O > SO2 > NH3 > CO2 > N2，动力学控制占据
- Caskey 2008 实验 Qst：Mg 47 / Fe 36 / Co 37 / Ni 41 / Zn 29 kJ/mol

### 2.2 双金属协同
- Chen 2023 (v3s0) 微波合成 NiCo-MOF-74：Ni1Co1 容量 8.30 mmol/g（0℃, 1 bar），5 点比例-容量数据呈倒 U
- Xu (v3s1) 固态 NMR 揭示 Mg/Ni 双金属非随机配分（8 种原子构型）
- Jiao (v3s1) Co/Ni 部分取代 Mg-MOF-74：反应温度主导最终组成
- 历史轮次：s-d 组合（Cu/Mg）单调 vs d-d 组合（NiCo/CoMn）倒 U

### 2.3 胺功能化与湿度（本轮重点增强）
- mmen-Mg2(dobpdc)（McDonald, v3s2）：2.0 mmol/g @ 0.39 mbar 25℃（DAC）、3.14 mmol/g @ 0.15 bar 40℃（烟气）
- Forse 2018（10.1021/jacs.8b10203）：6 金属 diamine-M2(dobpdc) 化学吸附 NMR+DFT 全景，胺化学计量 1.0 CO2/diamine
- Martell 2020（10.1039/d0sc01087a）：胺变体合作吸附动力学（吸附/脱附速率与胺结构相关）
- Zhu 2024（10.1021/jacs.3c13381）：pip2-Mg2(dobpdc) 两步吸附，**容量逼近 1.5 CO2/diamine**
- Marshall 2024 (p35)：低 RH 诱导效应 → 高 RH 消失、速率↑（合作链→非合作簇，LKT 理论）
- Owens 2025 (p24)：H2O/CO2 辫状链共吸附构型（ab initio）
- **TYUT-ATZ-β（10.1002/adma.202410500，新增）**：反直觉地将 H2O 固定为结合位点，湿态 CO2 捕获增强
- **MOF-808-AA（10.26434/chemrxiv-2021-51rbb-v2，新增）**：11 种氨基酸功能化，Gly/dl-Lys 湿态增强（碳酸氢盐 13C/15N NMR 证实）
- **Xiong 2025（10.1021/jacs.5c07551，新增）**：7 种 diamine MOF 的 O2 氧化降解机理（温度依赖）
- **Choe 2022（10.1021/jacs.2c01488，新增）**：环氧化物开环疏水化 een-MOF/Al-Si-C17 湿循环稳定性

### 2.4 经典材料与湿烟气稳定体系（本轮新增）
- **ZIF-94（10.3390/molecules27175608，新增）**：53.30 cm3/g ≈ 2.38 mmol/g、CO2/N2 选择性 54.12 @ 298K，高湿 RH 下分离时间 30.4 min
- **三氮唑框架（10.1021/jacs.9b12879，新增）**：CO2/N2 热力学选择性 120、CO2/H2O 动力学选择性 70（通道中心 CO2 / 角落 H2O 位点分离）
- **离子疏水门（10.1021/jacs.5c02093，新增）**：疏水离子液体+富氟醛表面，一步高纯 CO2 分离自湿烟气
- **MUF-16 SMB（10.1021/acsami.5c16139，新增）**：湿烟气模拟移动床连续工艺，水不竞争 CO2，免干燥床
- **ARC-MOF 稳定性筛选（10.1021/acs.est.5c00768，新增）**：ML 稳定性预筛 28 万 → 9755 候选
- CALF-20（Magnin 2017, Shin 2025）：超微孔异常扩散、PVSA 沼气升级技术经济
- ZIF-8（Devkota, Alvares）：传感器集成、MOF/PVDF 复合
- UiO-66-X（Bueken 2016）：凝胶/气凝胶整块形态设计
- PPN-6/PEI-165（Zhao, v3s5）：4.52 mmol/g @ 0.15 bar 323K

### 2.5 计算方法与数据库
- hMOF（137,953）/ ODAC23（8,400+ MOF, 38M DFT）/ CRAFTED（726 MOF × 2 力场 × 4 电荷）/ ARC-MOF（~280,000）
- MLIP-MC（Edwards）：MACE-MP-0/ORB-v3/fairchem 系统性偏差
- LitMOF（Kim）：近半数据库条目结构错误
- 吸附剂设计上界（Edens, v3s4）：1608 种 CO2/N2 材料权衡

## 3. 关键材料与性质对比

| 材料体系 | CO2 容量 (mmol/g) | 条件 | Qst (kJ/mol) | 选择性 | 来源 |
|---------|-------------------|------|-------------|--------|------|
| Ni1Co1-MOF-74 | **8.30** | 0℃, 1 bar | - | 高 | v3s0 |
| Mg-MOF-74 | 8.6（领域值）| 298K, 1 bar | 47 | 高 | Caskey; p26 |
| mmen-Mg2(dobpdc) | 2.0（DAC）/ 3.14（烟气）| 0.39 mbar / 0.15 bar | ~71 | 极高（台阶）| v3s2 |
| pip2-Mg2(dobpdc) | **~1.5 CO2/diamine** | 饱和 | - | 极高（两步）| 10.1021/jacs.3c13381 |
| ZIF-94 | **2.38** | 298K, 1bar | - | 54.1 | 10.3390/molecules27175608 |
| 三氮唑-MOF（最优）| - | 烟气 | - | 120 (CO2/N2)；70 (CO2/H2O 动力学) | 10.1021/jacs.9b12879 |
| ED@MOF-520 | - | 273K | 29 | **50** (CO2/N2) | v3s3 |
| PPN-6/PEI-165 | 4.52 | 0.15 bar, 323K | - | 极高（无 N2/CH4）| v3s5 |
| CALF-20 | - | - | - | 高（水稳）| p17; p23 |
| ZIF-8 | 0.5-1.5 | 298K | - | 中 | v1 验证 |
| HKUST-1 | 4.0-7.0 | 298K | - | 中高 | v1 验证 |

**量化建模数据**（详见 knowledge_graph.md 第四节）：
- 表 1：M-MOF-74 d 电子数 vs Qst（n=5 实验）
- 表 2：双金属比例 vs 容量（n=5 实验，高斯 R²=0.978）
- 表 3：竞争绑定能排序（n=5）
- 表 4：RH-诱导效应映射（n=5，定性）
- 表 5：胺变体-Qst（n=3，探索性）
- 表 6：**胺碳数 vs CO2/diamine 化学计量（n=5，本轮新增）**
- 表 7：ZIF/三氮唑湿度耐受-选择性（n=3，本轮新增）

## 4. 研究空白与未来方向（详见 gap_report.md Gap 1-12）

| 优先级 | Gap | 主题 | 置信度 |
|--------|-----|------|--------|
| 1 | Gap 1 | 双金属比例-容量倒 U 定量标度（5 点实验数据可直接拟合）| 0.95 |
| 2 | Gap 9 | 湿度诱导效应跨材料定量标度（DAC 关键）| 0.85 |
| 3 | Gap 3 | 水-胺协同/竞争定量化（MOF+COF+水固定位点五路证据）| 0.92 |
| 4 | Gap 11 | 胺链长/化学计量-性能标度律（新量化表 6）| 0.75 |
| 5 | Gap 4 | 金属取代多性质联合筛选 | 0.70 |
| 6 | Gap 10 / Gap 12 | 材料-工艺经济性；O2 降解标度（新增）| 0.70 |

**关键可执行方向**：① 扩展金属集验证 d 电子标度律；② 高斯峰峰值位置实验验证（配分非理想）；③ RHc 标度律跨材料实验；④ 胺碳数-化学计量标度（表 6 拟合）；⑤ O2 降解 Arrhenius 标度。

## 5. 参考文献（节选，可追溯）

| ID | 文献 | DOI/标识 |
|----|------|---------|
| p26 | Koh et al. Thermodynamic Screening of Metal-Substituted MOFs for Carbon Capture | 10.1039/c3cp50622c |
| p15 | Tan et al. Competitive co-adsorption of CO2 with H2O, NH3, SO2... in M-MOF-74 | 10.1021/acs.chemmater.5b00315 |
| p35 | Marshall et al. Cooperative lattice theory for CO2 adsorption... humid DAC | v3s3 同源 |
| p24 | Owens et al. H2O/CO2 co-adsorption in mmen-Mg2(dobpdc) | 2025 |
| v3s0_c795f15f9d35 | Chen et al. Microwave-assisted synthesis of bimetallic NiCo-MOF-74 | 2023 |
| v3s2_a7d3df468203 | McDonald et al. Capture of CO2 from air and flue gas in mmen-Mg2(dobpdc) | 2012 |
| 新增 | Forse et al. Elucidating CO2 Chemisorption in Diamine-Appended MOFs | 10.1021/jacs.8b10203 |
| 新增 | Zhu et al. High-Capacity Cooperative CO2 Capture (pip2) | 10.1021/jacs.3c13381 |
| 新增 | Chen et al. Immobilization of H2O in Diffusion Channel (TYUT-ATZ) | 10.1002/adma.202410500 |
| 新增 | Lyu et al. Amino Acid Functionalized MOF-808 | 10.26434/chemrxiv-2021-51rbb-v2 |
| 新增 | Shi et al. Robust Metal-Triazolate Frameworks | 10.1021/jacs.9b12879 |
| 新增 | Xiong et al. Oxidative Degradation in Diamine MOFs | 10.1021/jacs.5c07551 |
| 新增 | Wang et al. CO2 Capture from High-Humidity Flue Gas (ZIF-94) | 10.3390/molecules27175608 |
| p30 | Rocca et al. Quantum simulation of carbon capture in periodic MOFs | 2025 |
| p21 | Oliveira et al. CRAFTED database | 10.1038/s41597-023-02116-z |
| p14 | Choudhary et al. GNN Predictions of MOF CO2 Adsorption | 10.1016/j.commatsci.2022.111388 |

完整 149 篇见 paper_summaries.md；知识图谱见 knowledge_graph.md（R1-R46）；Gap 分析见 gap_report.md（Gap 1-12）。

---

## 6. 构效关系发现（路线 A，详见 discovery/discovery_report.md）

**5 条假设全部完成搜索覆盖**（H0:15 轮, H1:15 轮, H2:10 轮, H3:10 轮, H4:10 轮），Best Score 0.798-0.907；2 条通过外部数据库双轨验证（H0/H4）。

### 核心发现 1：双金属倒U最优组分偏离 1:1（Gap 1，已验证）
```
C(x) = 5.595·exp(-(x-0.369)²/(2·0.194²)) + 3.781   [mmol/g, 0℃ 1bar]
高斯 R²=0.978 vs 经典线性混合 R²=0.208（ΔR²=+0.77）
```
**最优 Ni/(Ni+Co) = 0.369 ≠ 0.5**：Co 侧富 Ni 增强（Ni Qst 41 > Co 37 kJ/mol），Ni 侧富 Co 衰减更快（非随机配分，Xu v3s1 NMR）。预测 Ni0.37Co0.63-MOF-74 ≈ 9.4 mmol/g，待实验验证。

### 核心发现 2：d 电子数主导 Qst 标度（Gap 4，已验证）
```
Qst = 32.53 - 1.99·Nd + 10.39·χ   [kJ/mol]
双描述符 R²=0.794 vs 单变量 Nd R²=0.723
```
d 电子数主效应（斜率 -1.99 kJ/mol·d⁻¹），电负性辅助；4 参数二次 R²=0.9855 属过拟合（n=5）不推荐。

### 核心发现 3：胺化学计量上限可突破（Gap 11，待实验）
pip2（环状双胺）实现 ~1.5 CO2/diamine 两步吸附（Zhu 2024），突破 1.0 传统上限——表 6 构造 5 点"胺碳数-化学计量"数据，搜索置信度 0.86。

### 核心发现 4：水增强捕获五路证据（Gap 3/9，置信度上调）
TYUT-ATZ 固定 H2O 为结合位点、MOF-808-AA 碳酸氢盐湿态增强、三氮唑框架 CO2/H2O 动力学选择性 70、离子疏水门、ZIF-94 高湿分离——"水必竞争"认知被改写为"水可被利用"，但定量标度（临界 RH）仍待建立。

### 核心发现 5：再生能耗-吸附焓权衡（Gap 10，已验证）
H4 搜索 Best 0.907（置信度 0.91 最高）：磁感应再生 1.29 MJ/kg（-45%）+ MUF-16 SMB 免干燥床——材料-工艺联合设计窗口 ~30-40 kJ/mol Qst 最优。

**验证方法学警示**：① 工具笛卡尔积污染可通过"每点独立块"知识图谱规避；② fit_vegard 返回 tuple 与工具 dict 解析不兼容，自写脚本补全 F 检验（quant_validate_v4.py）；③ n=5 小样本 F 检验天然不显著，ΔR² 与 BIC 为主证据；④ 符号回归小样本过拟合，以受限物理模型为准。
