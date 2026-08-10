# 反思日志 — 高镍正极容量保持率（第二轮，2026-08-10）

## 本轮成果回顾
1. **补充检索**：semantic_scholar 源命中 8 篇高质量定量论文（p43-p50），论文池 19→27 篇；验证了"arXiv 饱和后切换语义学术源"的有效性
2. **知识图谱扩展**：材料 13→18、性质 13→17、关系 14→22；补充规则 7 强制的量化建模数值表
3. **Gap 更新**：Gap 2/3/5 置信度强化（0.75→0.77、0.72→0.78、0.70→0.78），新增 Gap 8（质子诱导降解）
4. **量化验证（核心突破）**：
   - run_model_comparison(2)：A 层 6 点 R²=0.8873（线性）、B 层噪声暴露文献异质性
   - 补充统计：二次 R²=0.9828（p=0.027）、Vegard 经典模型 R²=-0.032 失效、斜率显著（p=0.005）
   - symbolic_regression(2)：31 点拟合
   - validate_discovery：假设 0 inconclusive（微结构-力学性质不在无机晶体库）、假设 2 validated（OQMD）
5. **discovery_report** 生成 + survey_report 更新

## 反思要点
1. **工具数据提取的深层教训**：run_model_comparison/symbolic_regression 从 knowledge_graph 提取数值点受限于：(a) x 变量正则（x=/比例=/%/温度/压力）；(b) 单位桶（保持率需 property 含"效率"命中 % 桶）；(c) material token 补充正则把 M#/P#/R# 编号、DOI 片段误当材料 token → 材料过滤失效 → 全块笛卡尔积污染。**修复靠输入净化**（编号改格式、化学式 Unicode 化、% 转文字）而非改工具（受保护）。最终 composition 主导成功。
2. **假设 2 的修正**：A 层数据显示 Ni 含量-保持率近似线性强负相关（R²=0.887），二次项显著（p=0.027）提示高 Ni 端加速——"帕累托窗口"未获支持，但"高 Ni 端恶化加剧"方向正确。Vegard 经典混合完全失效（R²<0）。
3. **假设 0 的外部验证预期内失败**：Materials Project/OQMD/NOMAD 是无机晶体数据库，不覆盖"Ni 氧化态异质性→位错裂纹"这类微结构-力学耦合性质——双轨验证的文献证据链（p24+p25）+ 顺序关联实验方案已足够。
4. **最有效的输入净化操作**：ASCII 化学式→Unicode 下标（消除 'ni0' 等 token 误匹配）、表格 y 列显式 %、正文 % 转文字——这些让材料过滤从失效变为生效。

## 下一轮建议
- 假设 0 的定量验证：查找单晶 NMC811 微力学数据（临界应力数值）论文，补充量化数值表后跑 model_comparison(0)
- 假设 3：p46 的火山型数据（涂层含量 vs 性能）可构造量化表（已用文字描述，可改表格）跑 model_comparison(3)
- Gap 8（质子降解）：检索 OEMS 定量数据，生成假设 5 并搜索
- 跨主题连接：cathode 与 thermoelectric/perovskite 主题共享"掺杂-性质"关系，可跑 cross_theme_connections
