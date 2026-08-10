## 调研：卤化物钙钛矿带隙与稳定性（halide perovskite band gap and stability）— 第二轮

### 检索策略
- 首轮（08-02）：9 组检索词，34 篇论文
- 第二轮（08-10）新增：perovskite band gap temperature；halide perovskite stability decomposition energy；lead-free perovskite photovoltaic absorber stability；double perovskite band gap ML 等 8 组检索词，新增 37 篇（共 71 篇）
- 数据源：arXiv + Semantic Scholar；缓存 workspace/data/literature_cache/perovskite/search_results.json

### 知识图谱摘要（更新）
- 材料数：19（新增 CsSnI3、CsPbBr3、FAxMA1-xPbI3、Cs1-xRbxPbI3、K2SnGeX6、AgInI4、Cs2Au2X6、Cs2CuBiCl6、C6H4NH2CuBr2I）
- 性质数：6（带隙、带隙类型、稳定性、吸收系数、温度-带隙行为、分解能）
- 关键关系数：27（R1-R27，新增 R16-R27：温度-带隙反常、电离能稳定性判据、ML 预测、卤素替换带隙等）
- **量化建模数值表**：表 A（温度-带隙，CsSnI3/CsPbBr3）、表 B（组分-带隙，Vegard 二次拟合）、表 C（压力-带隙，MA2PtI6 分段）、表 D（材料-带隙-稳定性排序 8 材料）

### Top 研究空白（更新）
1. Gap 1 带隙-稳定性 trade-off 无定量联合描述符 — 高 — 0.85（新增 p50/p57/p65 证据）
2. Gap 6 温度-带隙反常标度缺失（新增） — 高 — 0.78（p36/p38/p39/p49）
3. Gap 2 双钙钛矿间接→直接带隙调控 — 高 — 0.80（新增 p70 AgInI4）
4. Gap 3 ML 联合预测脱节 — 中 — 0.80（新增 p60/p64/p65）
5. Gap 4 压力-带隙标度缺失 — 中 — 0.75
6. Gap 5 2D/3D 界面耦合 — 中 — 0.70

### 发现结果（路线 A，本轮核心）
5 条具体假设全部完成搜索（每条 10 轮、21 候选，best 0.88-0.97）：
1. ✅ hypo_0 带隙-稳定性 trade-off — 已验证（OQMD：I 0.716 eV / Br 1.349 eV），best 0.964，置信度 0.96
2. ✅ hypo_2 双钙钛矿间接→直接调控 — 已验证（OQMD：Cl 2.661→Br 1.349→I 0.716 eV 卤素替换趋势，与 p66 K2SnGeX6 一致），best 0.966，置信度 0.97
3. ⏳ hypo_1 温度-带隙反常标度 — best 0.964，Slack 经典模型失效（R²≈0），非谐机制主导
4. ⏳ hypo_3 压力-带隙分段标度 — best 0.960
5. ⏳ hypo_4 ML 联合预测 — best 0.882
- model_comparison：hypo_0/hypo_1 已执行（数据受笛卡尔积污染，如实记录为"无提升"，LLM 解释归因非谐机制）
- symbolic_regression：hypo_0/hypo_1 已执行（R²≈0.04，数据成分污染）
- 双轨验证完成：2 条假设 OQMD 外部验证通过

### 经验教训
- generate_hypotheses 对中文 Gap 类型词解析不佳（\w 不匹配中文）→ 本轮手动构造 hypotheses.json
- run_model_comparison 提取文献数值时，正文中"数字+单位"会污染笛卡尔积配对 → 数值表需独立 ### 分块 + 数据行带单位；正文带单位数值会被误提取（本轮已清理 knowledge_graph 正文单位）
- search_results.json 混合多主题缓存需过滤（MOF 遗留数据）

### 反思
- 最令人惊讶：CsSnI3 温度升高带隙**打开**（dEg/dT>0，0.24 eV@500K）——经典 Slack 模型在此体系完全失效，非谐机制主导
- 最有效方向：温度-带隙 + 稳定性分解能的检索词命中率最高
- 下一轮：① 补充 MA2PtI6/Cs2AgBiBr6 绝对带隙值（表 C 补全）② 用 p53/p65 数据集做 ML 联合预测实证 ③ 修复 model comparison 数据提取（数值表已独立分块）
