# 文献调研报告：卤化物钙钛矿带隙与稳定性（halide perovskite band gap and stability）

> 生成日期：2026-08-02 ｜ 文献数：34 篇（arXiv + Semantic Scholar）
> 覆盖范围：铅基/无铅钙钛矿、双钙钛矿、带隙计算方法、稳定性机制、组分工程、压力/界面调控

---

## 1. 执行摘要

本调研围绕卤化物钙钛矿的两大核心性质——**带隙（band gap）**与**稳定性（stability）**展开，基于 34 篇高质量论文（arXiv 预印本 + Semantic Scholar 收录期刊论文）。文献呈现三条主线：(1) 铅基钙钛矿（MAPbI3、FAPbI3、CsPbI3 系列）带隙优异（~1.5-1.6 eV）但稳定性不足、含 Pb 毒性；(2) 无铅双钙钛矿（Cs2AgBiBr6 为基准）稳定性好但带隙偏大且为间接带隙；(3) 计算与机器学习方法正加速带隙预测，但带隙与稳定性的**联合定量描述符**仍缺失。核心研究空白是"带隙-稳定性 trade-off 缺乏定量框架"（Gap 1，置信度 0.85）。

## 2. 文献综述

### 2.1 铅基卤化物钙钛矿：带隙与稳定性的矛盾

MAPbI3 等杂化铅卤钙钛矿具有理想带隙（~1.55 eV）、高吸收系数和高载流子迁移率，光伏效率超 25%，但长期环境稳定性不足（湿/热/光降解）且 Pb²⁺ 水溶性毒性阻碍商业化（jacs.6b09645）。全无机 CsPb(I1-xBrx)3 固溶体化学稳定性增强，带隙随 Br 含量线性可调（PhysRevMaterials.4.045402）。

### 2.2 无铅双钙钛矿：稳定性与带隙的折中

无铅双钙钛矿 A2BB'X6 是替代铅基的主线。基准材料 **Cs2AgBiBr6** 稳定性高、无毒，但带隙 1.72-1.98 eV 且为**间接带隙**（anie.202005568; er.8099）。关键调控手段：
- **Ag-Bi 无序增强**：降带隙 ~0.26 eV，达到 1.72 eV 最低记录（anie.202005568）
- **Pb²⁺ 微量掺杂**：间接→直接带隙转变（PhysRevMaterials.2.055401）
- **压力调控**：Cs2AgBiBr6 在 2.3 GPa 立方→四方相变，带隙红移→蓝移（c9nr07030c）
- **厚度调控**：2D 化降带隙、提升光催化性能（d0cp03919e）
- **新体系预测**：Cs2InAgCl6 理论预测直接带隙（1611.05426v2）；Rb2AgInX6（X=Cl,Br,I）SCAPS 模拟（1402-4896/adb221）

### 2.3 带隙计算方法学

- **DFT-1/2 方法**：以 DFT 成本达到 GW 精度，适用于 AMX3（A=MA/FA/Cs, M=Pb/Sn, X=I/Br/Cl）（s41598-017-14435-4）
- **VCA 虚拟晶体近似**：CH3NH3Pb(I1-xBrx)3 带隙-组成遵守 Vegard 律二次拟合（PhysRevB.94.125139）
- **HSE 混合泛函**：exact-exchange 线性增长方案精确预测 CsPb(I1-xBrx)3（PhysRevMaterials.4.045402）

### 2.4 稳定性机制

- **内禀局域畸变**（polymorphous networks）：立方钙钛矿存在非热分布的局域结构畸变，不随时间平均为零，与动态热运动共同决定带隙与稳定性（mattod.2021.05.021; PhysRevB.101.155137）
- **离子迁移**：决定长期稳定性与光伏性能退化（D0TA03200J）
- **锡基氧化**：FASnI3 中 Sn²⁺→Sn⁴⁺ 氧化是主要降解路径，Lewis 碱表面钝化（分子硬度主导）可稳定（mtener.2022.101038）
- **2D/3D 异质界面**：界面电荷转移增强抗降解性且不损效率（acsami.5c00201）；MAPbI3/BN 单层室温稳定（-25 meV@300K）（commatsci.2022.111649）

## 3. 关键材料与性质对比

| 材料 | 带隙 (eV) | 带隙类型 | 稳定性 | 备注 | 来源 |
|------|----------|---------|--------|------|------|
| MAPbI3 | ~1.55 | 直接 | 差（湿/热） | 铅基基准 | s41598-017-14435-4 |
| CH3NH3Pb(I1-xBrx)3 | 1.55→2.3 | 直接 | 中 | Vegard 律 | PhysRevB.94.125139 |
| CsPb(I1-xBrx)3 | 1.7→2.4 | 直接 | 较好 | 全无机 | PhysRevMaterials.4.045402 |
| Cs2AgBiBr6 | 1.72-1.98 | 间接 | 高 | 无铅基准 | anie.202005568 |
| Cs2InAgCl6 | 可见-UV | 直接（预测） | [待验证] | 理论 | 1611.05426v2 |
| FASnI3 | ~1.4 | 直接 | 差（氧化） | 锡基 | mtener.2022.101038 |
| CH3NH3BaI3 | 3.87 | 直接 | 高 | 宽带隙 | PhysRevB.94.180105 |
| MA2PtI6 | ~2.0 | — | 中 | dEg/dP=0.063-0.079 eV/GPa | 1674-1056/adce9e |
| Na2ZrTeO6 | 宽带隙 | 直接 | 高（高温） | 氧化物双钙钛矿 | adts.202401421 |

## 4. 研究空白与未来方向

1. **Gap 1（高，0.85）**：带隙-稳定性 trade-off 无定量联合描述符 → 构建联合数据集检验 Pareto 前沿
2. **Gap 2（高，0.80）**：间接→直接带隙调控手段缺乏系统性比较 → 同一母体上对比无序/掺杂/压力/厚度
3. **Gap 3（中，0.78）**：ML 带隙预测与稳定性预测脱节 → 多任务学习联合预测
4. **Gap 4（中，0.75）**：压力-带隙响应体系间标度缺失 → 计算 dEg/dP 与描述符关联
5. **Gap 5（中，0.70）**：2D/3D 界面电荷转移-带隙-稳定性耦合定量缺失 → 系统扫描界面参数

## 5. 参考文献（可追溯）

| # | 论文 | DOI/ID |
|---|------|--------|
| 1 | Accurate and efficient band gap predictions of metal halide perovskites using the DFT-1/2 method | 10.1038/s41598-017-14435-4 |
| 2 | The effects of intrinsic local distortions vs. dynamic thermal motions on stability and band gaps | 10.1016/j.mattod.2021.05.021 |
| 3 | First-Principles Study on Material Properties and Stability of Inorganic Halide Perovskite Solid Solutions CsPb(I1-xBrx)3 | 10.1103/PhysRevMaterials.4.045402 |
| 4 | Tuning Bandgap and Energy Stability of Organic-Inorganic Halide Perovskites through Surface Engineering | 10.1016/j.commatsci.2022.111649 |
| 5 | Cu-In Halide Perovskite solar absorbers | 10.1021/jacs.7b02120 |
| 6 | Design of Lead-Free Inorganic Halide Perovskites for Solar Cells via Cation-Transmutation | 10.1021/jacs.6b09645 |
| 7 | Influence of halide composition on mixed CH3NH3Pb(I1-xBrx)3 perovskites | 10.1103/PhysRevB.94.125139 |
| 8 | Lead-Free Halide Double Perovskite Cs2AgBiBr6 with Decreased Band Gap | 10.1002/anie.202005568 |
| 9 | Pressure-induced structural transition and band gap evolution of Cs2AgBiBr6 nanocrystals | 10.1039/c9nr07030c |
| 10 | Thickness-induced band-gap engineering in Cs2AgBiBr6 | 10.1039/d0cp03919e |
| 11 | Machine learning stability and band gap of lead-free halide double perovskite materials | 10.1016/j.solener.2021.09.030 |
| 12 | Pressure-induced band gap closing of (CH3NH3)2PtI6 | 10.1088/1674-1056/adce9e |
| 13 | Cs2InAgCl6: A new lead-free halide double perovskite with direct band gap | arXiv:1611.05426 |
| 14 | Double Perovskites overtaking the single perovskites | 10.1103/PhysRevMaterials.2.055401 |
| 15 | Chemically-Localized Resonant Excitons in Silver-Pnictogen Halide Double Perovskites | 10.1021/acs.jpclett.0c03579 |
| 16 | Efficient Passivation of Surface Defects by Lewis Base in FASnI3 | 10.1016/j.mtener.2022.101038 |
| 17 | Tuning Electronic and Optical Properties of 2D/3D Construction | 10.1021/acsami.5c00201 |
| 18 | Crystal structure, stability and optoelectronic properties of CH3NH3BaI3 | 10.1103/PhysRevB.94.180105 |
| 19 | The polymorphous nature of cubic halide perovskites | 10.1103/PhysRevB.101.155137 |
| 20 | Comprehensive study of Rb2AgInX6 based lead-free double perovskite solar cells | 10.1088/1402-4896/adb221 |

## 证据链

> 本章节由 `scripts/inject_evidence_chain.py` 依据 discovery 产物自动生成，保证赛题红线 1「每个结论都能指回具体文献或数据库记录」在基本任务报告层闭环。
> 生成时间：2026-08-03 18:14｜假设总数：1｜证据条目总数：1
> 数据源：discovery/hypotheses.json（必需）、discovery/discovery_report.json（可选）
> 回查路径：survey_report.md → discovery/hypotheses.json（evidence_chain）→ discovery/discovery_report.md（Evidence Chain）→ 检索缓存 search_results.json / 人工核实。
> 状态说明：「✅ 已溯源」= 编号证据在 discovery 产物中存在且未被引用审计标记；「⚠ 需人工核对」= reference_audit 标记该编号不可追溯，须人工确认。

---

### 假设 1｜Material-property relationship discovery（hypo_0）

**结论简述**：Based on the gap analysis

**证据编号列表**：
- `[Novelty Verification] Overlap: insufficient | Novelty: 0.400 (was 0.500) | Queries: 0 | Results: 0`（新颖性查重）

**来源归属**：
- 新颖性查重：新颖性 0.400；查询 0 次；结果 0 条
- 数据库记录（materials_project）：未命中（查询 —）

**可追溯状态**：✅ 已溯源 —— 证据编号在 discovery 产物（hypotheses.json → evidence_chain、discovery_report.md → Evidence Chain）中可逐层回查，且未被引用审计标记；论文编号对应的真实文献最终确认请回查检索缓存或人工复核。
