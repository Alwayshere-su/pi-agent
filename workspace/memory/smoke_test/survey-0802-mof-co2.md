# Agent Experiment Memory — survey

## 调研：MOF materials for CO2 capture
- [MOF CO2 捕获调研（首次，2026-08-02）](survey-0802-mof-co2.md) — 13 篇论文；Top Gap：MLIP 系统偏差（Gap 1）、水对胺功能化吸附机理（Gap 2）；5 条假设已生成（budget 耗尽前未搜索）

## 检索策略
检索词：MOF materials CO2 capture adsorption / machine learning MOF CO2 adsorption screening（2 次 0 命中后停止）；数据源 arXiv；13 篇去重论文

## 知识图谱摘要
- 材料数：8（M-DOBDC、M-HKUST-1、mmen-Mg2(dobpdc)、MIL-120、CALF-20、ZIF-8/4、Fe-MOF-74、数据库）
- 性质数：7（吸附容量/ΔH/选择性/共吸附/扩散/DAC指标/吸附能）
- 关键关系数：6（R1-R6）

## Top 研究空白
1. MLIP 对 CO2 吸附能系统偏差 — 高/0.75 — 证据：p12,p6 — 验证：偏差 vs 结构描述符回归
2. 水对胺功能化链式吸附定量影响 — 高/0.70 — 证据：p10,p5 — 验证：胺密度系列 ΔH 位移
3. 金属取代 MOF-74 ΔH 与描述符关联 — 中/0.65 — 证据：p3,p8

## 发现结果（路线 A）
- 5 条假设已生成（hypotheses.json，bayesian）：MLIP-开放金属位点、胺类型-水效应、金属共价性-ΔH、超微孔-扩散帕累托、DAC/烟道气排序反转
- ⚠️ 预算耗尽，未执行 run_discovery_search / validate_discovery — 下次运行必须对每条假设 ≥5 轮搜索 + top-1 验证

## 反思
- 检索效率：组合检索词 0 命中率高，简单词更好；应改用更通用的查询
- 预算分配失误：阶段一检索多轮 0 命中浪费预算，下次单轮检索 ≤4 次
- 下一轮聚焦：执行 5 条假设的 discovery search（每假设 ≥5 轮）、top-1 validate、model_comparison + symbolic_regression
