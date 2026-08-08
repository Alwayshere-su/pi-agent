# MOF 材料 CO2 捕获 — 知识图谱

## 一、材料实体

| 编号 | 材料 | 关键特征 | 来源论文 |
|------|------|----------|----------|
| M1 | M-DOBDC (M=Be,Mg,Ca,Sr,Sc,Ti,V,Cr,Mn,Fe,Co,Ni,Cu,Zn,Mo,W,Sn,Pb) | 金属取代 MOF-74 家族，烟道气低压下 CO2 容量最高的一类 | p3 |
| M2 | M-HKUST-1 | 金属取代 HKUST-1，低压 CO2 吸附候选 | p3 |
| M3 | mmen-Mg2(dobpdc) | 胺功能化 MOF，阶梯状吸附等温线，链式（chaining）吸附机理 | p10 |
| M4 | MIL-120(Al) | 超小孔 MOF，μ2-OH 桥羟基，CO2 吸附剂 | p2 |
| M5 | CALF-20(Zn) | Angstropores 超微孔，13X 沸石替代候选 | p5 |
| M6 | ZIF-8 / ZIF-4 | MLIP 基准测试材料 | p12 |
| M7 | Fe-MOF-74 | 磁性 Mott 绝缘体，暴露金属位点增强 CO2 吸附 | p8 |
| M8 | 数据库：hMOF(137953)、CoRE MOF 2014(726)、CRAFTED | 高通量筛选数据库 | p1, p6 |

## 二、性质实体

| 编号 | 性质 | 描述 | 来源 |
|------|------|------|------|
| P1 | CO2 吸附容量 | GCMC 模拟/实验等温线 | p1, p6, p12 |
| P2 | CO2 吸附焓 ΔH (T=300K) | vdW-DF 超胞计算，与实验吻合 | p3 |
| P3 | CO2/N2 选择性 | 烟道气分离关键 | p6, p9 |
| P4 | CO2/H2O 共吸附 | 湿度环境下的竞争吸附 | p5, p10 |
| P5 | 扩散系数 | CO2/H2O 在超微孔中的反常扩散 | p2, p5 |
| P6 | DAC 指标 | 每单位能量捕获 CO2 上限、纯度上限 | p9 |
| P7 | 吸附能 | DFT 泛函依赖性强（Fe-MOF-74） | p8 |

## 三、关键关系

| 编号 | 材料A | 材料B | 关系类型 | 证据 | 来源 |
|------|-------|-------|----------|------|------|
| R1 | M-DOBDC 金属种类 | CO2 吸附焓 ΔH | 金属取代调谐 ΔH，vdW-DF 预测与实验一致 | M=Mg 系列 ΔH 实验验证 | p3 |
| R2 | 孔尺寸（超小孔/angstropore） | CO2/H2O 扩散动力学 | 超微孔导致异常扩散行为 | MIL-120、CALF-20 | p2, p5 |
| R3 | 胺功能化 | CO2 吸附容量 + 水敏感性 | mmen 链式吸附在 H2O 存在下形成"编织链"新构型 | mmen-Mg2(dobpdc) | p10 |
| R4 | 力场/MLIP 选择 | 预测吸附能准确性 | 通用 MLIP 有系统性偏差，依赖训练数据组成 | ZIF-8/ZIF-4/Mg-MOF-74 基准 | p12, p6 |
| R5 | 开放金属位点 | CO2 吸附能 | 暴露金属位点增强吸附，但强关联体系 DFT 不一致 | Fe-MOF-74 | p8 |
| R6 | 框架动态（μ2-OH 取向） | CO2 吸附行为 | 局部动态显著影响吸附 | MIL-120(Al) MLP+DFT | p2 |

## 四、方法实体

| 编号 | 方法 | 用途 | 来源 |
|------|------|------|------|
| T1 | ALIGNN (GNN) | hMOF CO2 吸附预筛，迁移到 CoRE MOF 排序 | p1 |
| T2 | vdW-DF 超胞计算 | 金属取代 MOF 热力学筛选 | p3 |
| T3 | GHP-MOFassemble（生成式 AI 扩散模型） | 生成可合成 linker 组装 MOF | p7 |
| T4 | MLIP-MC（MACE-MP-0/ORB-v3/fairchem ODAC） | MLIP 驱动的 GCMC 吸附模拟 | p12 |
| T5 | LitMOF（LLM 多智能体） | 文献验证数据库修正 | p11 |
| T6 | B3LYP-D3 簇模型 | MOF linker 上 CO2 结合焓计算 | p4 |
| T7 | 统计力学 + ab initio 格子模型 | 含水 CO2 等温线预测 | p10 |
