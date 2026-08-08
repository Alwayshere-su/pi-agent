# 跨领域文献连接报告（Cross-Theme Connections）

> 生成时间: 2026-08-04 00:10
> 工具: cross_theme（跨子领域文献连接，赛题高分方向）
> 扫描目录: workspace/outputs

## 一、扫描概览

- 主题数: 8 ｜ 主题对数: 28
- 跨领域连接总数: 24（材料实体连接 10 条，性质实体连接 14 条）

### 主题清单

| 主题目录 | 主题标题 | 材料实体 | 性质实体 | 证据编号 |
|---------|---------|---------|---------|---------|
| cathode | 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） | 27 | 5 | 16 |
| mof_e2e_v3 | MOF Materials for CO2 Capture（e2e_v3 全量版） | 28 | 4 | 60 |
| mof_e2e_v4 | MOF Materials for CO2 Capture（e2e_v4 全量版） | 47 | 5 | 94 |
| mof_rerun | MOF Materials for CO2 Capture | 21 | 4 | 36 |
| mof_rerun_v2 | MOF Materials for CO2 Capture（v2 扩展版） | 21 | 4 | 67 |
| perovskite | 卤化物钙钛矿带隙与稳定性 | 16 | 3 | 13 |
| thermoelectric | 热电材料 ZT 优化 | 39 | 9 | 62 |
| validation | ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） | 36 | 3 | 43 |

## 二、跨领域连接

### C01. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v3 全量版）（mof_e2e_v3）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v3 全量版） 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42；MOF Materials for CO2 Capture（e2e_v3 全量版） 中关联到 Magnin, Shin, p17。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF Materials for CO2 Capture（e2e_v3 全量版），可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 2023, 2025, Magnin, Shin, p17, p23, p27, p39
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF Materials for CO2 Capture（e2e_v3 全量版） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42；Magnin, Shin, p17）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C02. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v3 全量版）（mof_e2e_v3）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v3 全量版） 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42 表明 扩散系数 受结构/工艺变量调控；MOF Materials for CO2 Capture（e2e_v3 全量版） 中证据 Magnin, p17, p27 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: 2023, Magnin, p17, p27, p29, p35, p4, p42
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42）可定量预测 MOF Materials for CO2 Capture（e2e_v3 全量版） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C03. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v3 全量版）（mof_e2e_v3）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；MOF Materials for CO2 Capture（e2e_v3 全量版） 的证据 Bae, Bueken, Caskey 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 2008, 2015, 2016, 2018, 2019, 2020, 2022, 2023
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 MOF Materials for CO2 Capture（e2e_v3 全量版） 的同类材料（Bae, Bueken, Caskey），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C04. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42；MOF Materials for CO2 Capture（e2e_v4 全量版） 中关联到 Magnin, McDannald, Shi。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF Materials for CO2 Capture（e2e_v4 全量版），可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 10.1021, 2020, 2023, 2024, 2025, Magnin, McDannald, Shi
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF Materials for CO2 Capture（e2e_v4 全量版） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42；Magnin, McDannald, Shi）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C05. [性质实体] 共享「容量保持率」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 都围绕性质「容量保持率」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p06, p16, p27 表明 容量保持率 受结构/工艺变量调控；MOF Materials for CO2 Capture（e2e_v4 全量版） 中证据 Choe, Sun, jacs.2c01488) 表明 容量保持率 的驱动机制。容量保持率 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 容量保持率
- **证据编号**: 10.1021, 2022, 2025, Choe, Sun, jacs.2c01488), jacs.5c02093), p06
- **可证伪假设**（Expected Relationship）: 以 容量保持率 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 容量保持率 对结构变量 X 的标度关系（p06, p16, p27）可定量预测 MOF Materials for CO2 Capture（e2e_v4 全量版） 中另一类材料体系在相同变量变化下的 容量保持率 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 容量保持率 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C06. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42 表明 扩散系数 受结构/工艺变量调控；MOF Materials for CO2 Capture（e2e_v4 全量版） 中证据 Magnin, p17, p27 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: 2023, Magnin, p17, p27, p35, p4, p42, p5
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42）可定量预测 MOF Materials for CO2 Capture（e2e_v4 全量版） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C07. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；MOF Materials for CO2 Capture（e2e_v4 全量版） 的证据 Choe, Sun, Wang 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 10.1021, 10.3390, 2022, 2025, Choe, Sun, Wang, Xiong
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 MOF Materials for CO2 Capture（e2e_v4 全量版） 的同类材料（Choe, Sun, Wang），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C08. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（mof_rerun）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42；MOF Materials for CO2 Capture 中关联到 Magnin, p2, p5。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF Materials for CO2 Capture，可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 2023, Magnin, p2, p39, p42, p5
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF Materials for CO2 Capture 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42；Magnin, p2, p5）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C09. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（mof_rerun）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42 表明 扩散系数 受结构/工艺变量调控；MOF Materials for CO2 Capture 中证据 Magnin, 2023 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: 2023, Magnin, p35, p42
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42）可定量预测 MOF Materials for CO2 Capture 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C10. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（mof_rerun）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；MOF Materials for CO2 Capture 的证据 Bae, C7NR09536H), Caskey 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 10.1038, 10.1039, 10.1103, 2008, 2016, 2017, 2018, 2021
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 MOF Materials for CO2 Capture 的同类材料（Bae, C7NR09536H), Caskey），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C11. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（v2 扩展版）（mof_rerun_v2）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（v2 扩展版） 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42；MOF Materials for CO2 Capture（v2 扩展版） 中关联到 Magnin, Shin, p17。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF Materials for CO2 Capture（v2 扩展版），可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 2023, 2025, Magnin, Shin, p17, p23, p39, p42
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF Materials for CO2 Capture（v2 扩展版） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42；Magnin, Shin, p17）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C12. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（v2 扩展版）（mof_rerun_v2）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 MOF Materials for CO2 Capture（v2 扩展版） 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42 表明 扩散系数 受结构/工艺变量调控；MOF Materials for CO2 Capture（v2 扩展版） 中证据 Magnin, p17, p27 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: 2023, Magnin, p17, p27, p29, p35, p4, p42
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42）可定量预测 MOF Materials for CO2 Capture（v2 扩展版） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C13. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ MOF Materials for CO2 Capture（v2 扩展版）（mof_rerun_v2）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；MOF Materials for CO2 Capture（v2 扩展版） 的证据 Bae, Bueken, Caskey 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: 2008, 2015, 2016, 2017, 2018, 2019, 2020, 2021
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 MOF Materials for CO2 Capture（v2 扩展版） 的同类材料（Bae, Bueken, Caskey），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C14. [性质实体] 共享「机械稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 卤化物钙钛矿带隙与稳定性 都围绕性质「机械稳定性」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p06, p14, p22 表明 机械稳定性 受结构/工艺变量调控；卤化物钙钛矿带隙与稳定性 中证据 PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421 表明 机械稳定性 的驱动机制。机械稳定性 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 机械稳定性
- **证据编号**: PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421, anie.202005568, er.8099, mtener.2022, p06, p14
- **可证伪假设**（Expected Relationship）: 以 机械稳定性 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 机械稳定性 对结构变量 X 的标度关系（p06, p14, p22）可定量预测 卤化物钙钛矿带隙与稳定性 中另一类材料体系在相同变量变化下的 机械稳定性 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 机械稳定性 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C15. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 卤化物钙钛矿带隙与稳定性（perovskite）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；卤化物钙钛矿带隙与稳定性 的证据 PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421, anie.202005568, er.8099, mtener.2022, p06, p14
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 卤化物钙钛矿带隙与稳定性 的同类材料（PhysRevB.94.180105, PhysRevMaterials.4.045402, adts.202401421），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C16. [材料实体] 共享「alf」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「alf」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p39, p42；热电材料 ZT 优化 中关联到 C6CP03211G), TE135, TE136。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: alf
- **证据编号**: 10.1039, C6CP03211G), TE135, TE136, TE139, TE146, p39, p42
- **可证伪假设**（Expected Relationship）: 材料 alf 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 alf 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 alf 的跨子领域证据（p39, p42；C6CP03211G), TE135, TE136）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C17. [材料实体] 共享「单晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「单晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p24, p25；热电材料 ZT 优化 中关联到 TE113。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 单晶
- **证据编号**: TE113, p24, p25
- **可证伪假设**（Expected Relationship）: 材料 单晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 单晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 单晶 的跨子领域证据（p24, p25；TE113）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C18. [材料实体] 共享「多晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 热电材料 ZT 优化 的文献中均出现材料/材料族「多晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p24；热电材料 ZT 优化 中关联到 TE115。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 热电材料 ZT 优化，可双向启发各自的材料设计。
- **共享实体**: 多晶
- **证据编号**: TE115, p06, p24
- **可证伪假设**（Expected Relationship）: 材料 多晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 热电材料 ZT 优化 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 多晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 多晶 的跨子领域证据（p06, p24；TE115）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 中

### C19. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ 热电材料 ZT 优化（thermoelectric）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；热电材料 ZT 优化 的证据 TE057 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: TE057, p06, p14, p22, p24, p25, p27, p31
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 热电材料 ZT 优化 的同类材料（TE057），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C20. [材料实体] 共享「多晶」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的文献中均出现材料/材料族「多晶」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p24；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中关联到 P041, P072。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes），可双向启发各自的材料设计。
- **共享实体**: 多晶
- **证据编号**: P041, P072, p06, p24
- **可证伪假设**（Expected Relationship）: 材料 多晶 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 多晶 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 多晶 的跨子领域证据（p06, p24；P041, P072）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C21. [材料实体] 共享「高镍正极」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的文献中均出现材料/材料族「高镍正极」：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中其证据关联到 p06, p32；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中关联到 P006, P010, P011。同一实体承载两类子领域的性质约束，将 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes），可双向启发各自的材料设计。
- **共享实体**: 高镍正极
- **证据编号**: P006, P010, P011, P012, P013, P014, P015, P016
- **可证伪假设**（Expected Relationship）: 材料 高镍正极 在 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 高镍正极 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 高镍正极 的跨子领域证据（p06, p32；P006, P010, P011）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

### C22. [性质实体] 共享「扩散系数」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 主题 高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 与主题 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 都围绕性质「扩散系数」展开：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中证据 p35, p42 表明 扩散系数 受结构/工艺变量调控；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中证据 P038, P039 表明 扩散系数 的驱动机制。扩散系数 的调控机制在两个子领域高度同构，可建立跨领域标度关系。
- **共享实体**: 扩散系数
- **证据编号**: P038, P039, p35, p42
- **可证伪假设**（Expected Relationship）: 以 扩散系数 为桥梁，高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的 扩散系数 对结构变量 X 的标度关系（p35, p42）可定量预测 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 中另一类材料体系在相同变量变化下的 扩散系数 行为；选取两主题各一组独立数据点交叉拟合，报告 R²/残差。
- **新颖性提示**: 同一性质 扩散系数 在两个子领域被分别建模，缺乏统一标度框架；本连接显式抽取共享描述符，为联合实验设计提供依据。
- **证据强度**: 高

### C23. [性质实体] 共享「稳定性」

- **主题对**: 高镍正极容量保持率（High-Nickel Cathode Capacity Retention）（cathode） ↔ ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes）（validation）
- **连接描述**: 两个子领域都把「稳定性」作为器件化的关键约束：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 的证据 p06, p14, p22 表明该主题下材料性能受工作环境（温度/氧化/湿度）降解制约；：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的证据 P006, P010, P011 同样将稳定性视为性能上界。跨领域可借鉴对方的稳定化策略（元素替换、表面涂层、晶界工程、组成窗口），把 '性能-稳定性权衡' 从单主题上升为通用描述符。
- **共享实体**: 稳定性
- **证据编号**: P006, P010, P011, P017, P020, P023, P024, P027
- **可证伪假设**（Expected Relationship）: 主题间共享的稳定性描述符（如缺陷形成能、氧化/水解自由能、相变温度）对两主题材料性能衰减的预测方向一致：高镍正极容量保持率（High-Nickel Cathode Capacity Retention） 中观测到的稳定性-掺杂浓度关系（p06, p14, p22）可迁移到 ：固态锂电池电解质（Solid-State Lithium Battery Electrolytes） 的同类材料（P006, P010, P011），即存在共同的稳定性 Pareto 前沿。可通过在两主题数据集上交叉拟合衰减速率 vs 描述符验证。
- **新颖性提示**: 不同子领域的稳定性研究彼此隔离，缺乏可迁移的稳定性描述符基准；本连接为跨材料家族的生命周期预测模型提供共享标签。
- **证据强度**: 高

### C24. [材料实体] 共享「calf-20」

- **主题对**: MOF Materials for CO2 Capture（e2e_v3 全量版）（mof_e2e_v3） ↔ MOF Materials for CO2 Capture（e2e_v4 全量版）（mof_e2e_v4）
- **连接描述**: 主题 MOF Materials for CO2 Capture（e2e_v3 全量版） 与主题 MOF Materials for CO2 Capture（e2e_v4 全量版） 的文献中均出现材料/材料族「calf-20」：MOF Materials for CO2 Capture（e2e_v3 全量版） 中其证据关联到 Magnin, Shin, p17；MOF Materials for CO2 Capture（e2e_v4 全量版） 中关联到 Magnin, McDannald, Shi。同一实体承载两类子领域的性质约束，将 MOF Materials for CO2 Capture（e2e_v3 全量版） 中建立的构效关系（描述符、掺杂窗口、稳定性边界）迁移到 MOF Materials for CO2 Capture（e2e_v4 全量版），可双向启发各自的材料设计。
- **共享实体**: calf-20
- **证据编号**: 10.1021, 2020, 2023, 2024, 2025, Magnin, McDannald, Shi
- **可证伪假设**（Expected Relationship）: 材料 calf-20 在 MOF Materials for CO2 Capture（e2e_v3 全量版） 中最优的结构描述符（掺杂浓度/晶粒尺寸/缺陷密度）与 MOF Materials for CO2 Capture（e2e_v4 全量版） 中性能最大化窗口一致或成比例；制备覆盖该描述符范围的 calf-20 系列样品，分别在两个子领域的测试协议下测量关键性质，验证正相关性。
- **新颖性提示**: 材料 calf-20 的跨子领域证据（Magnin, Shin, p17；Magnin, McDannald, Shi）在现有文献中通常被孤立处理，本连接显式并置其双领域角色，可直接支撑跨领域联合设计与综述。
- **证据强度**: 高

## 三、使用说明

1. 每条连接均以两个主题知识图谱中的真实证据编号为依托（证据列 / evidence_chain）。
2. 「可证伪假设」采用 Expected Relationship 格式，可直接作为后续generate_hypotheses / run_discovery_search 的种子假设。
3. 连接强度依据证据数量判定：high（≥4）、medium（2-3）、low（<2）。
4. 本报告为跨主题视角产物；如需单主题深入分析请使用各主题自己的工具链。
