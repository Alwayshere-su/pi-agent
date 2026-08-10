# 跨领域文献连接报告（Cross-Theme Connections）

> 生成时间: 2026-08-10 09:11
> 工具: cross_theme（跨子领域文献连接，赛题高分方向）
> 扫描目录: workspace/outputs

## 一、扫描概览

- 主题数: 5 ｜ 主题对数: 10
- 跨领域连接总数: 24（材料实体连接 12 条，性质实体连接 12 条）

### 主题清单

| 主题目录 | 主题标题 | 材料实体 | 性质实体 | 证据编号 |
|---------|---------|---------|---------|---------|
| cathode | 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） | 30 | 5 | 24 |
| mof_e2e_v4 | MOF Materials for CO2 Capture（e2e_v4 全量版） | 47 | 5 | 94 |
| perovskite | 卤化物钙钛矿带隙与稳定性 | 33 | 4 | 50 |
| thermoelectric | 热电材料 ZT 优化 | 39 | 9 | 62 |
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

### C05. [材料实体] 共享「soc」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 卤化物钙钛矿带隙与稳定性 的文献中均出现材料/材料族「soc」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p16；卤化物钙钛矿带隙与稳定性 中关联到 p46。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 卤化物钙钛矿带隙与稳定性，可双向启发各自的材料设计。
- **共享实体**: soc
- **证据编号**: p16, p46
- **可证伪假设**（Expected Relationship）: 材料 soc 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 卤化物钙钛矿带隙与稳定性 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 soc 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 soc 的跨子领域证据（p16；p46）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C06. [性质实体] 共享「机械稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 卤化物钙钛矿带隙与稳定性 都围绕性质「机械稳定性」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p06, p14, p22 表明 机械稳定性 受结构/工艺变量调控；卤化物钙钛矿带隙与稳定性 中证据 PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105 表明 机械稳定性 的驱动机制。机械稳定性 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 机械稳定性
- **证据编号**: PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421, anie.202005568, er.8099, mtener.2022
- **可证伪假设**（Expected Relationship）: 以 机械稳定性 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 机械稳定性 对结构变量 X 的标度关系（p06, p14, p22）可定量预测 卤化物钙钛矿带隙与稳定性 中另一类材料体系在相同变量变化下的 机械稳定性 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 机械稳定性 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C07. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；卤化物钙钛矿带隙与稳定性 的证据 PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421, anie.202005568, er.8099, mtener.2022
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 卤化物钙钛矿带隙与稳定性 的同类材料（PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C08. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42, p46；热电材料 ZT 优化 中关联到 C6CP03211G), TE135, TE136。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 10.1039, C6CP03211G), TE135, TE136, TE139, TE146, p39, p42
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42, p46；C6CP03211G), TE135, TE136）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C09. [材料实体] 共享「单晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「单晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p24, p25；热电材料 ZT 优化 中关联到 TE113。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 单晶
- **证据编号**: TE113, p24, p25
- **可证伪假设**（Expected Relationship）: 材料 单晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 单晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 单晶 的跨子领域证据（p24, p25；TE113）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C10. [材料实体] 共享「多晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「多晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p24；热电材料 ZT 优化 中关联到 TE115。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 多晶
- **证据编号**: TE115, p06, p24
- **可证伪假设**（Expected Relationship）: 材料 多晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 多晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 多晶 的跨子领域证据（p06, p24；TE115）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C11. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；热电材料 ZT 优化 的证据 TE057 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: TE057, p06, p14, p22, p24, p25, p27, p31
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 热电材料 ZT 优化 的同类材料（TE057），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C12. [材料实体] 共享「多晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的文献中均出现材料/材料族「多晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p24；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中关联到 P041, P072。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes），可双向启发各自的材料设计。
- **共享实体**: 多晶
- **证据编号**: P041, P072, p06, p24
- **可证伪假设**（Expected Relationship）: 材料 多晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 多晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 多晶 的跨子领域证据（p06, p24；P041, P072）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C13. [材料实体] 共享「高镍正极」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的文献中均出现材料/材料族「高镍正极」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p32；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中关联到 P006, P010, P011。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes），可双向启发各自的材料设计。
- **共享实体**: 高镍正极
- **证据编号**: P006, P010, P011, P012, P013, P014, P015, P016
- **可证伪假设**（Expected Relationship）: 材料 高镍正极 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 高镍正极 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 高镍正极 的跨子领域证据（p06, p32；P006, P010, P011）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C14. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42, p45 表明 扩散系数 受结构/工艺变量调控；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中证据 P038, P039 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: P038, P039, p35, p42, p45
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42, p45）可定量预测 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C15. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的证据 P006, P010, P011 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: P006, P010, P011, P017, P020, P023, P024, P027
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的同类材料（P006, P010, P011），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C16. [材料实体] 共享「nh2」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 卤化物钙钛矿带隙与稳定性 的文献中均出现材料/材料族「nh2」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Chen, adma.202410500, adma.202410500)；卤化物钙钛矿带隙与稳定性 中关联到 p68。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 卤化物钙钛矿带隙与稳定性，可双向启发各自的材料设计。
- **共享实体**: nh2
- **证据编号**: 10.1002, 2025, Chen, adma.202410500, adma.202410500), p68
- **可证伪假设**（Expected Relationship）: 材料 nh2 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 卤化物钙钛矿带隙与稳定性 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 nh2 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 nh2 的跨子领域证据（Chen, adma.202410500, adma.202410500)；p68）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C17. [材料实体] 共享「nh3」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 卤化物钙钛矿带隙与稳定性 的文献中均出现材料/材料族「nh3」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Tan, p15, 2015；卤化物钙钛矿带隙与稳定性 中关联到 PhysRevB.94.125139, PhysRevB.94.180105, p13。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 卤化物钙钛矿带隙与稳定性，可双向启发各自的材料设计。
- **共享实体**: nh3
- **证据编号**: 2015, PhysRevB.94.125139, PhysRevB.94.180105, Tan, p13, p14, p15, p17
- **可证伪假设**（Expected Relationship）: 材料 nh3 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 卤化物钙钛矿带隙与稳定性 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 nh3 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 nh3 的跨子领域证据（Tan, p15, 2015；PhysRevB.94.125139, PhysRevB.94.180105, p13）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C18. [性质实体] 共享「稳定性」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：MOF Materials for CO2 Capture（e2e_v4 全量版） 的证据 Choe, Sun, Wang 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；卤化物钙钛矿带隙与稳定性 的证据 PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 10.1021, 10.3390, 2022, 2025, Choe, PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：MOF Materials for CO2 Capture（e2e_v4 全量版） 中观测到的稳定性-掺杂浓度关系（Choe, Sun, Wang）可迁移到 卤化物钙钛矿带隙与稳定性 的同类材料（PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.180105），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C19. [材料实体] 共享「纳米复合」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「纳米复合」：MOF Materials for CO2 Capture（e2e_v4 全量版） 中其证据关联到 Bae, Bueken, Caskey；热电材料 ZT 优化 中关联到 TE093。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v4 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 纳米复合
- **证据编号**: 10.1002, 10.1021, 10.1039, 10.26434, 10.3390, 2008, 2012, 2015
- **可证伪假设**（Expected Relationship）: 材料 纳米复合 在 MOF Materials for CO2 Capture（e2e_v4 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 纳米复合 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 纳米复合 的跨子领域证据（Bae, Bueken, Caskey；TE093）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C20. [性质实体] 共享「稳定性」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：MOF Materials for CO2 Capture（e2e_v4 全量版） 的证据 Choe, Sun, Wang 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；热电材料 ZT 优化 的证据 TE057 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 10.1021, 10.3390, 2022, 2025, Choe, Sun, TE057, Wang
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：MOF Materials for CO2 Capture（e2e_v4 全量版） 中观测到的稳定性-掺杂浓度关系（Choe, Sun, Wang）可迁移到 热电材料 ZT 优化 的同类材料（TE057），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C21. [性质实体] 共享「扩散系数」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 都围绕性质「扩散系数」展开：MOF Materials for CO2 Capture（e2e_v4 全量版） 中证据 Magnin, p17, p27 表明 扩散系数 受结构/工艺变量调控；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中证据 P038, P039 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: 2023, Magnin, P038, P039, p17, p27, p4, p5
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，MOF Materials for CO2 Capture（e2e_v4 全量版） 中观测到的 扩散系数 对结构变量 X 的标度关系（Magnin, p17, p27）可定量预测 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C22. [性质实体] 共享「稳定性」

- **主题对**: MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：MOF Materials for CO2 Capture（e2e_v4 全量版） 的证据 Choe, Sun, Wang 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的证据 P006, P010, P011 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 10.1021, 10.3390, 2022, 2025, Choe, P006, P010, P011
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：MOF Materials for CO2 Capture（e2e_v4 全量版） 中观测到的稳定性-掺杂浓度关系（Choe, Sun, Wang）可迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的同类材料（P006, P010, P011），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C23. [材料实体] 共享「钙钛矿」

- **主题对**: 卤化物钙钛矿带隙与稳定性（perovskite） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 卤化物钙钛矿带隙与稳定性 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「钙钛矿」：卤化物钙钛矿带隙与稳定性 中其证据关联到 PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.125139；热电材料 ZT 优化 中关联到 TE003。同一实体承载两类子领域的性质约束，将 卤化物钙钛矿带隙与稳定性 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 钙钛矿
- **证据编号**: 1611.05426v2, PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.125139, PhysRevB.94.180105, PhysRevMaterials.4.045402, TE003, adts.202401421
- **可证伪假设**（Expected Relationship）: 材料 钙钛矿 在 卤化物钙钛矿带隙与稳定性 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 钙钛矿 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 钙钛矿 的跨子领域证据（PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.125139；TE003）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C24. [材料实体] 共享「钙钛矿氧化物」

- **主题对**: 卤化物钙钛矿带隙与稳定性（perovskite） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 无机钙钛矿氧化物同时出现在两个子领域：卤化物钙钛矿带隙与稳定性 收录层状钙钛矿氧化物作为热电候选（热电势高，证据 PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.125139）；热电材料 ZT 优化 收录双钙钛矿氧化物 Na2ZrTeO6 的宽带隙与高温稳定性（证据 TE003）。两类证据暗示钙钛矿氧化物家族兼具高温结构稳定性与可调电子输运，是热电-光伏跨界材料平台的天然候选。
- **共享实体**: 钙钛矿氧化物
- **证据编号**: 1611.05426v2, PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.125139, TE003, adts.202401421, anie.202005568, er.8099
- **可证伪假设**（Expected Relationship）: 若层状钙钛矿氧化物的热电性能由 [BO6] 八面体畸变主导（与双钙钛矿Na2ZrTeO6 的高温稳定机制同源），则在相同畸变描述符（容忍因子偏离度、八面体倾斜角）窗口内，热电功率因子与结构稳定温度存在可预测的正相关；可通过在 卤化物钙钛矿带隙与稳定性 的热电数据（PhysRevApplied.13.014005, PhysRevB.92.201205, PhysRevB.94.125139）与 热电材料 ZT 优化 的稳定性数据（TE003）上共同拟合畸变-性能标度律验证。
- **新颖性提示**: 热电与钙钛矿文献几乎不互相引用氧化物骨架的输运/稳定证据；将层状与双钙钛矿氧化物并置为同一材料平台是跨主题综述的新角度，有助提出氧化物基热电器件候选。
- **证据强度**: 高

## 三、使用说明

1. 每条连接均以两个主题知识图谱中的真实证据编号为依托（证据列 / evidence_chain）。
2. 「可证伪假设」采用 Expected Relationship 格式，可直接作为后续generate_hypotheses / run_discovery_search 的种子假设。
3. 连接强度依据证据数量判定：high（≥4）、medium（2-3）、low（<2）。
4. 本报告为跨主题视角产物；如需单主题深入分析请使用各主题自己的工具链。
