## 调研：MOF materials for CO2 capture（v2 迭代）
日期：2026-08-03 | run_dir: mof_rerun_v2

### 检索策略
- 检索词：metal-organic frameworks carbon dioxide capture（12 篇）/ MOF CO2 adsorption（23 篇）/ diamine appended metal organic framework CO2 cooperative adsorption（2 篇）/ metal organic framework carbon capture process simulation energy（3 篇）
- 数据源：arXiv；v2 缓存 37 篇（p1-p37），v1 缓存已清理（知识经 v1 知识图谱/gap_report 保留）
- 教训：检索后端对长复合词敏感（4 次 0 命中），通用短词更有效

### 知识图谱摘要（v2：R1-R19）
- 材料数：~10 体系（M-MOF-74、mmen/diamine-M2(dobpdc)、HKUST-1、CALF-20、MIL-120、ZIF-8、UiO-66-X、CMSM、卟啉石墨烯、水稳定 Zn-MOF）
- 性质数：~15（Qst、容量、选择性、扩散、诱导效应、工艺能耗等）
- 关键关系数：19（v1 的 R1-R14 + v2 新增 R15-R19：竞争吸附动力学/湿度诱导效应/工艺经济性/凝胶形态/混合气统一ML）
- 量化建模数值表：3 张（金属取代 Qst 表 n=5、竞争绑定能排序、RH-诱导效应映射）

### Top 研究空白（v2）
1. Gap 9 湿度诱导效应跨材料标度律 — 高 — 0.80（Marshall p35 实验+理论；Owens p24）
2. Gap 3 水-胺协同vs抑制 — 高 — 0.85（v1 0.75 提升，新增 p35/p20 证据）
3. Gap 4 金属取代多性质筛选 — 中 — 0.70（v2 已量化单性质：d电子数/电负性 vs Qst）
4. Gap 1 力场/MLIP 系统性偏差 — 高 — 0.85
5. Gap 10 材料-工艺经济性代理模型（新增）— 中 — 0.70

### 发现结果（路线 A）
1. M-MOF-74 金属 d 电子构型 vs CO2 吸附焓 — **已验证（量化）**
   - d 电子数线性：Qst = -1.496·Nd + 47.278（R²=0.723, RMSE=3.12）
   - 电负性 U 型二次：R²=0.983（嵌套 F p=0.011 显著，n=5）
   - Fe(d6) 偏离趋势线 ↔ 强关联 Mott 效应（Rocca p30）
   - 外部验证：v2 validate_discovery 为 inconclusive（占位假设）；v1 曾命中 ZIF-8/HKUST-1（CoRE/hMOF）
2. 湿度诱导效应/水-胺切换/OMS 偏差/工艺经济性 — 候选假设 H1-H4 未搜索（工具链限制+预算），科学论证保留于 discovery_report.md

### 工具链教训（重要！）
- generate_hypotheses / run_discovery_search 在会话内维护单一占位假设并**覆盖文件系统 hypotheses.json**；手工写入 5 条会被覆盖
- run_model_comparison / symbolic_regression 依赖工具内部状态（property 字段），文件修改无效 → 用自写脚本完成量化验证（quant_validate_v2.py）
- 下一轮建议：直接用 run_discovery_search 多次调用探索不同 Gap（每次生成新占位假设），或修改工具调用参数

### 反思
- 最惊讶：电负性 vs Qst 的 U 型二次关系（R²=0.983, p=0.011）——Ni 电负性最高但 Qst 非最低，v1 LLM 已预示此非单调性，v2 用数值证实
- 最高效方向：知识图谱量化数值表（n=5 真实实验值）支撑量化验证
- 下一轮聚焦：Gap 9 湿度诱导效应搜索（DAC 关键）+ 扩展金属集（Ca/Mn/Cu）验证 d 电子标度律 + 双描述符 (Nd, χ) 联合建模
