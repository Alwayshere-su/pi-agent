## 调研：热电材料 ZT 优化 — 量化验证阶段（quantitative validation phase）

### 本阶段任务
对已有 5 条假设执行 run_model_comparison + symbolic_regression；补搜未覆盖假设

### 执行内容
1. **知识图谱补数值表**（规则 7）：新增「七、量化建模数值表」6 张表（7.1-7.6），
   20 个可追溯数值点：方钴矿温度-ZT 6 行（TE041/046/037/040/039/047）、
   half-Heusler 温度-ZT 5 行（TE016×2/007/146×2）、SnSe 温度-ZT 3 行（TE113×2/115）、
   跨体系峰值 ZT-温度 6 行（TE065/041/040/146/113/002）、填充分数-性能 3 行、晶粒尺寸 1 行
2. **补搜未覆盖假设**：idx 3（共振掺杂）8 轮 19 候选 best 0.329；idx 4（Yb 方钴矿）
   8 轮 19 候选 best 0.786，confidence 0.55→0.79 → **5 条假设全部 search_iterations > 0** ✅
3. **model_comparison ×4**（idx 0/1/2/4；idx 3 数据不足）：
   - 候选三次 R²≈0.26-0.29 vs Slack 经典 R²=-0.00（负对照）
   - 嵌套 F 检验 p=0.14-0.16 均不显著 → **跨材料温度-ZT 无普适标度（负结果）**
4. **symbolic_regression ×4**（idx 0/1/2/4；idx 3 数据不足）：
   - R²=0.66-0.79 但 9-12 参数复杂表达式（log/sin/exp 嵌套）→ 典型过拟合
5. **validate_discovery ×2**（idx 0、idx 4）：均 inconclusive
   （MP/OQMD/NOMAD 无 ZT 实验数据）→ 印证数据层断层

### 关键发现
1. **负结果（有价值）**：跨材料温度-ZT 单变量模型不显著（R²≈0.29, p>0.05），
   ZT 必须用多材料描述符（带隙/有效质量/声速）预测 → 强化 Gap 1（0.92→0.93）
2. **新 Gap 7**（0.65）：共振掺杂文献摘要无 Seebeck µV/K 定量数值 →
   "浓度-Seebeck"标度无法从摘要级证据链建模
3. **数据异质性如实标注**：同数据集（15-17 点温度-ZT）被 idx 0/2/4 共享，
   符号回归表达式完全相同（R²=0.789）——这是数据来源有限的真实反映

### 文件状态
- knowledge_graph.md：+R15（温度-ZT 无普适标度负结果）、+量化数值表 7.1-7.6
- gap_report.md：+Gap 7、Gap 1 置信度强化至 0.93
- discovery_report.md：+量化验证结果汇总章节
- 新增：model_comparison_0/1/2/4.md、symbolic_0/1/2/4.md、search_h3/h4.json

### 反思
- 摘要级数据是量化建模的硬约束：ZT 数据点足够（20 个），但 Seebeck/PF/晶粒尺寸
  数据严重不足——下一轮应解析全文 PDF 或补充检索含 Seebeck 数值的文献
- 外部数据库验证对热电 ZT 几乎不可行（MP/OQMD 无输运数据），双轨验证的
  "计算库交叉验证"轨道在热电领域天然受限——建议下一轮尝试 NOMAD 输运数据或
  ThermoElectric 专项数据库（如 TEDB）
- 下次迭代聚焦：多描述符 ZT 回归（T+Eg+m*+vs）、解析全文提取 Seebeck 曲线
