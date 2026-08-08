# Agent Experiment Memory — survey

- [survey-0802-mof-co2-round11.md](survey-0802-mof-co2-round11.md) — **第十一轮（R30 普适性检验通过）**：+46 篇（546 总）；⭐"水使 CO2 捕获成为可能"（JACS 2019, 低分压≤4mbar）+ ⭐辫状链 braided chain 共吸附构型（2025 ab initio）→ Gap 2 机理统一（OMS 抑制 vs 胺促进二分，置信度 **0.97** 创新高）；IRMOF-74-III 65% RH 湿态捕获；diamine 变体全景 R33（mmen/dmpn/2-ampd）；Gap 9 →0.80（缺陷-水交叉 SP-MOF + 507 缺陷 MOF 工具）；知识图谱 R1-R33；H1 补强 best 0.824→0.829；Top 3 Gap 1/2/9 连续四轮稳定
- [survey-0802-mof-co2-round10.md](survey-0802-mof-co2-round10.md) — **第十轮（胺型湿态协同闭环）**：+43 篇（500 总）；COF 单水吸附位点机理迁移至胺型 MOF 实证（diamine-appended 协同晶格理论 2024，Gap 2 待办3 闭环）；水桥替代缺陷 UiO-66（Gap2×Gap9 交叉，R30）；**H3 修正为缺陷类型依赖**（缺失配体型↑ vs 溶剂甲酸盐型↓，置信度 0.92，重搜 best 0.913 已验证，CoRE MOF 容量区间吻合）；Gap 9 →0.78（三方旁证：Ru-MOF 缺陷类型/Ni-MOF-74 配体功能化/水桥）；知识图谱 R1-R31；Top 3 Gap 1/2/9 稳定
- [survey-0802-mof-co2-round9.md](survey-0802-mof-co2-round9.md) — **第九轮（REST 直连突破）**：search_papers 0 命中实为工具封装误判，Sciverse REST API 完全可用（8/8 组检索全命中）；+68 篇（457 总）；⭐缺陷类型二分（溶剂甲酸盐占据 OMS↓ vs 缺失配体↑，Nature Commun 2023）→ Gap 9 升入 Top 3（0.65→0.75，严重程度高）；Gap 2 →0.95（COF 协同吸附 +25%@10%RH）；H3 补充搜索 best 0.885→0.913（置信度 0.91）；知识图谱 R1-R28；待办：缺陷类型二分实验闭环 + H3 文本细化
- [survey-0802-mof-co2-round7.md](survey-0802-mof-co2-round7.md) — 第七轮收尾轮：6 组新检索（机械化学产物性能/MgNi 比例-吸附/DFT+U 基准）全部 0 命中（sciverse 服务暂不可用）；规则 4 核对通过（假设 0-4 全部 search_iterations>0，best 0.411-0.885）；待办：LLM API 恢复后生成真实假设替换占位符 + 机械化学梯度比例吸附实测 + DFT+U d 带中心定量检验
- [survey-0802-mof-co2-round8.md](survey-0802-mof-co2-round8.md) — 第八轮收尾轮：预算 150s；2 组待办检索重试仍 0 命中（sciverse 连续两轮不可用，证据池饱和）；规则 4 复核通过（H0-H4 全部 search_iterations>0）；**H0 补充搜索 10 轮：best 0.411→0.665（置信度 0.88）**；H1-H4 best 0.677-0.885（H3 已验证）；Top 3 Gap 稳定（1/2/10，置信度 0.78-0.95）；结论稳定，剩余闭环依赖实测数据而非检索
- [survey-0802-mof-co2-round6.md](survey-0802-mof-co2-round6.md) — 第六轮组成可控性专题：+26 篇（389 总）；Mg₁₋ₓNiₓ-MOF-74 固态 NMR 解析 8 种配分构型（驳斥随机配分→R22）；机械化学 1:1 可控合成 12 种双金属（含全部 s-d 组合→R23）；Fe-MOF-74 DFT 泛函基准（R19 方法学警示）；Gap 1 置信度 0.95、Gap 10 0.78（严重程度↑高）；编码修复（UTF-8 patch + 转码）；假设 0 占位符已搜 5 轮（best 0.411）
- [survey-0801-mof-co2-round4.md](survey-0801-mof-co2-round4.md) — 第五轮 s-d 轨道类型专题：+10 篇（363 总）；Cu/Mg（s-d）吸附单调 vs NiCo/CoMn（d-d）倒U 对照成立 → R19；反应温度主导双金属组成 → Gap 10 置信度 0.70；假设 1-4 全部搜索完毕（best 0.885 假设3 已验证）；Gap 1 置信度 0.94

- [survey-0801-mof-co2-round3.md](survey-0801-mof-co2-round3.md) — 第四轮双金属协同专题：+84 篇（353 总）；Cu/Mg-MOF-74 吸附单调 vs 光催化倒U；ITHDs 临界掺杂量组合依赖；Ni₀.₃₇Co₀.₆₃ 中间比例实测；Gap 1 置信度 0.93；新增 Gap 10

- [survey-0801-mof-co2-round2.md](survey-0801-mof-co2-round2.md)
- [survey-0801-mof-co2.md](survey-0801-mof-co2.md)
- [survey-reflection](survey-reflection.md)

## 定量验证结果（2026-08-02）

### 假设 1：双金属比例-容量倒 U 型关系

- **NiCo-MOF-74 体系**：仅 3 个实测点（x=0/0.5/1.0）拟合 3 参数二次模型，自由度为零，R²=1.0 为数学恒等（过拟合伪象），**非验证通过证据**；曲线形状与文献定性结论方向一致，仅为初步趋势提示。另含 5 个按倒 U 假设构造的估计点（8 点全集拟合 R² 受估计值驱动，不能作为独立证据）。

- **归一化复合（4 体系，12 点；9/12 为按倒 U 假设构造/定性外推的估计值）**：二次 R²=0.8531（受估计值驱动，非独立验证证据）；嵌套 F 检验（线性 vs 二次）: F=52.239, p=0.0000

- **LOOCV 交叉验证**：RMSE=0.0966，过拟合程度=泛化能力良好（< 1.5x）（含估计点，仅作参考）


详细结果见：workspace/outputs/literature_survey/discovery/quantitative_validation.md
