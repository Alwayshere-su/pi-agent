# 跨领域文献连接报告（Cross-Theme Connections）

> 生成时间: 2026-08-11 21:28
> 工具: cross_theme（跨子领域文献连接，赛题高分方向）
> 扫描目录: workspace/outputs

## 一、扫描概览

- 主题数: 6 ｜ 主题对数: 15
- 跨领域连接总数: 24（材料实体连接 14 条，性质实体连接 10 条）

### 主题清单

| 主题目录 | 主题标题 | 材料实体 | 性质实体 | 证据编号 |
|---------|---------|---------|---------|---------|
| cathode | 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） | 31 | 5 | 24 |
| mof_e2e_v4 | MOF Materials for CO2 Capture（e2e_v4 全量版） | 47 | 5 | 94 |
| mof_rerun_v3 | MOF 材料用于 CO2 捕获 | 30 | 4 | 55 |
| perovskite | 卤化物钙钛矿带隙与稳定性 | 33 | 4 | 50 |
| thermoelectric | 热电材料 ZT 优化 | 50 | 9 | 66 |
| validation | ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） | 36 | 3 | 43 |

## 二、跨领域连接

### C01. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42, p46；MOF Materials for CO2 Capture（e2e_v4 全量版） 中关联到 Magnin, McDannald, Shi。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF Materials for CO2 Capture（e2e_v4 全量版），可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 10.1021, 2020, 2023, 2024, 2025, Magnin, McDannald, Shi
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF Materials for CO2 Capture（e2e_v4 全量版） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42, p46；Magnin, McDannald, Shi）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C02. [性质实体] 共享「容量保持率」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 都围绕性质「容量保持率」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p06, p16, p27 表明 容量保持率 受结构/工艺变量调控；MOF Materials for CO2 Capture（e2e_v4 全量版） 中证据 Choe, Sun, jacs.2c01488) 表明 容量保持率 的驱动机制。容量保持率 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 容量保持率
- **证据编号**: 10.1021, 2022, 2025, Choe, Sun, jacs.2c01488), jacs.5c02093), p06
- **可证伪假设**（Expected Relationship）: 以 容量保持率 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 容量保持率 对结构变量 X 的标度关系（p06, p16, p27）可定量预测 MOF Materials for CO2 Capture（e2e_v4 全量版） 中另一类材料体系在相同变量变化下的 容量保持率 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 容量保持率 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C03. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42, p45 表明 扩散系数 受结构/工艺变量调控；MOF Materials for CO2 Capture（e2e_v4 全量版） 中证据 Magnin, p17, p27 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: 2023, Magnin, p17, p27, p35, p4, p42, p45
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42, p45）可定量预测 MOF Materials for CO2 Capture（e2e_v4 全量版） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C04. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；MOF Materials for CO2 Capture（e2e_v4 全量版） 的证据 Choe, Sun, Wang 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 10.1021, 10.3390, 2022, 2025, Choe, Sun, Wang, Xiong
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 MOF Materials for CO2 Capture（e2e_v4 全量版） 的同类材料（Choe, Sun, Wang），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C05. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF 材料用于 CO2 捕获 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42, p46；MOF 材料用于 CO2 捕获 中关联到 P1, p12, p19。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF 材料用于 CO2 捕获，可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: P1, p12, p19, p23, p3, p35, p36, p37
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF 材料用于 CO2 捕获 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42, p46；P1, p12, p19）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C06. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF 材料用于 CO2 捕获 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42, p45 表明 扩散系数 受结构/工艺变量调控；MOF 材料用于 CO2 捕获 中证据 p11, p13, p17 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: p11, p13, p17, p18, p2, p24, p30, p35
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42, p45）可定量预测 MOF 材料用于 CO2 捕获 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C07. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；MOF 材料用于 CO2 捕获 的证据 P6, P7, p12 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: P6, P7, p06, p12, p14, p19, p22, p24
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 MOF 材料用于 CO2 捕获 的同类材料（P6, P7, p12），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C08. [材料实体] 共享「soc」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 卤化物钙钛矿带隙与稳定性 的文献中均出现材料/材料族「soc」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p16；卤化物钙钛矿带隙与稳定性 中关联到 p46。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 卤化物钙钛矿带隙与稳定性，可双向启发各自的材料设计。
- **共享实体**: soc
- **证据编号**: p16, p46
- **可证伪假设**（Expected Relationship）: 材料 soc 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 卤化物钙钛矿带隙与稳定性 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 soc 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 soc 的跨子领域证据（p16；p46）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C09. [性质实体] 共享「机械稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 卤化物钙钛矿带隙与稳定性 都围绕性质「机械稳定性」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p06, p14, p22 表明 机械稳定性 受结构/工艺变量调控；卤化物钙钛矿带隙与稳定性 中证据 PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105 表明 机械稳定性 的驱动机制。机械稳定性 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 机械稳定性
- **证据编号**: PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421, anie.202005568, er.8099, mtener.2022
- **可证伪假设**（Expected Relationship）: 以 机械稳定性 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 机械稳定性 对结构变量 X 的标度关系（p06, p14, p22）可定量预测 卤化物钙钛矿带隙与稳定性 中另一类材料体系在相同变量变化下的 机械稳定性 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 机械稳定性 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C10. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；卤化物钙钛矿带隙与稳定性 的证据 PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421, anie.202005568, er.8099, mtener.2022
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 卤化物钙钛矿带隙与稳定性 的同类材料（PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C11. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42, p46；热电材料 ZT 优化 中关联到 C6CP03211G), TE135, TE136。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 10.1039, C6CP03211G), TE135, TE136, TE139, TE146, p39, p42
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42, p46；C6CP03211G), TE135, TE136）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C12. [材料实体] 共享「单晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「单晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p24, p25；热电材料 ZT 优化 中关联到 TE113。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 单晶
- **证据编号**: TE113, p24, p25
- **可证伪假设**（Expected Relationship）: 材料 单晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 单晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 单晶 的跨子领域证据（p24, p25；TE113）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C13. [材料实体] 共享「多晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「多晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p24；热电材料 ZT 优化 中关联到 TE115。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 多晶
- **证据编号**: TE115, p06, p24
- **可证伪假设**（Expected Relationship）: 材料 多晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 多晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 多晶 的跨子领域证据（p06, p24；TE115）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C14. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；热电材料 ZT 优化 的证据 TE057 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: TE057, p06, p14, p22, p24, p25, p27, p31
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 热电材料 ZT 优化 的同类材料（TE057），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C15. [材料实体] 共享「多晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的文献中均出现材料/材料族「多晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p24；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中关联到 P041, P072。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes），可双向启发各自的材料设计。
- **共享实体**: 多晶
- **证据编号**: P041, P072, p06, p24
- **可证伪假设**（Expected Relationship）: 材料 多晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 多晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 多晶 的跨子领域证据（p06, p24；P041, P072）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C16. [材料实体] 共享「高镍正极」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的文献中均出现材料/材料族「高镍正极」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p32；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中关联到 P006, P010, P011。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes），可双向启发各自的材料设计。
- **共享实体**: 高镍正极
- **证据编号**: P006, P010, P011, P012, P013, P014, P015, P016
- **可证伪假设**（Expected Relationship）: 材料 高镍正极 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 高镍正极 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 高镍正极 的跨子领域证据（p06, p32；P006, P010, P011）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C17. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42, p45 表明 扩散系数 受结构/工艺变量调控；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中证据 P038, P039 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: P038, P039, p35, p42, p45
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42, p45）可定量预测 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C18. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的证据 P006, P010, P011 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: P006, P010, P011, P017, P020, P023, P024, P027
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的同类材料（P006, P010, P011），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C19. [材料实体] 共享「calf-20」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 MOF 材料用于 CO2 捕获 的文献中均出现材料/材料族「calf-20」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Magnin, McDannald, Shi；MOF 材料用于 CO2 捕获 中关联到 P1, p12, p19。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF 材料用于 CO2 捕获，可双向启发各自的材料设计。
- **共享实体**: calf-20
- **证据编号**: 10.1021, 2020, 2023, 2024, 2025, Magnin, McDannald, P1
- **可证伪假设**（Expected Relationship）: 材料 calf-20 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF 材料用于 CO2 捕获 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 calf-20 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 calf-20 的跨子领域证据（Magnin, McDannald, Shi；P1, p12, p19）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C20. [材料实体] 共享「co2」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 MOF 材料用于 CO2 捕获 的文献中均出现材料/材料族「co2」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Bae, Caskey, Chen；MOF 材料用于 CO2 捕获 中关联到 P1, P2, p36。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF 材料用于 CO2 捕获，可双向启发各自的材料设计。
- **共享实体**: co2
- **证据编号**: 10.1002, 10.1021, 10.1039, 10.26434, 10.3390, 2008, 2015, 2016
- **可证伪假设**（Expected Relationship）: 材料 co2 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF 材料用于 CO2 捕获 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 co2 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 co2 的跨子领域证据（Bae, Caskey, Chen；P1, P2, p36）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C21. [材料实体] 共享「en-mg2dobpdc」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 MOF 材料用于 CO2 捕获 的文献中均出现材料/材料族「en-mg2dobpdc」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Forse, Marshall, Martell；MOF 材料用于 CO2 捕获 中关联到 p1, p36, p40。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF 材料用于 CO2 捕获，可双向启发各自的材料设计。
- **共享实体**: en-mg2dobpdc
- **证据编号**: 10.1021, 10.1039, 2018, 2024, 2025, Forse, Marshall, Martell
- **可证伪假设**（Expected Relationship）: 材料 en-mg2dobpdc 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF 材料用于 CO2 捕获 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 en-mg2dobpdc 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 en-mg2dobpdc 的跨子领域证据（Forse, Marshall, Martell；p1, p36, p40）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C22. [材料实体] 共享「m-dobdc」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 MOF 材料用于 CO2 捕获 的文献中均出现材料/材料族「m-dobdc」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Bae, Caskey, Koh；MOF 材料用于 CO2 捕获 中关联到 p21, p23, p61。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF 材料用于 CO2 捕获，可双向启发各自的材料设计。
- **共享实体**: m-dobdc
- **证据编号**: 2008, 2015, 2016, Bae, Caskey, Koh, Tan, p15
- **可证伪假设**（Expected Relationship）: 材料 m-dobdc 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF 材料用于 CO2 捕获 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 m-dobdc 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 m-dobdc 的跨子领域证据（Bae, Caskey, Koh；p21, p23, p61）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C23. [材料实体] 共享「mil-120」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 MOF 材料用于 CO2 捕获 的文献中均出现材料/材料族「mil-120」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Fan, p13, 2025；MOF 材料用于 CO2 捕获 中关联到 p8。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF 材料用于 CO2 捕获，可双向启发各自的材料设计。
- **共享实体**: mil-120
- **证据编号**: 2025, Fan, p13, p8
- **可证伪假设**（Expected Relationship）: 材料 mil-120 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF 材料用于 CO2 捕获 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 mil-120 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 mil-120 的跨子领域证据（Fan, p13, 2025；p8）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C24. [材料实体] 共享「mmen-mg2dobpdc」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ MOF 材料用于 CO2 捕获（mof_rerun_v3）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 MOF 材料用于 CO2 捕获 的文献中均出现材料/材料族「mmen-mg2dobpdc」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Forse, Marshall, Martell；MOF 材料用于 CO2 捕获 中关联到 p1, p36, p40。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF 材料用于 CO2 捕获，可双向启发各自的材料设计。
- **共享实体**: mmen-mg2dobpdc
- **证据编号**: 10.1021, 10.1039, 2018, 2024, 2025, Forse, Marshall, Martell
- **可证伪假设**（Expected Relationship）: 材料 mmen-mg2dobpdc 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF 材料用于 CO2 捕获 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 mmen-mg2dobpdc 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 mmen-mg2dobpdc 的跨子领域证据（Forse, Marshall, Martell；p1, p36, p40）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

## 三、使用说明

1. 每条连接均以两个主题知识图谱中的真实证据编号为依托（证据列 / evidence_chain）。
2. 「可证伪假设」采用 Expected Relationship 格式，可直接作为后续generate_hypotheses / run_discovery_search 的种子假设。
3. 连接强度依据证据数量判定：high（≥4）、medium（2-3）、low（<2）。
4. 本报告为跨主题视角产物；如需单主题深入分析请使用各主题自己的工具链。
