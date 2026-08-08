# 调研反思日志 — 热电材料 ZT 优化

## 阶段一（文献调研）反思
- **检索质量**：11 个角度检索获得 209 篇有效热电论文（arxiv 160 + semantic_scholar 49），主流体系全覆盖（Bi₂Te₃/PbTe/SnSe/HH/skutterudite/GeTe）。长查询返回 0 篇，改用短核心词（"Bi2Te3 thermoelectric"）后命中率高。教训：检索 API 对简短关键词更友好。
- **知识覆盖**：知识图谱含 14 条关系（R01-R14）、8 大材料体系、10+ 关键数值。覆盖不足：有机热电、器件级效率、Mg₃Sb₂。
- **Gap 重要性**：6 个 Gap 中 Gap 1（ML-实验断层, 0.92）和 Gap 2（n 型 SnSe 落后, 0.88）置信度最高，具备可执行性（可实验验证）。
- **发现潜力**：Gap 1/2/6 可支撑 3 个强假设（纳米晶尺寸-ZT、卤素掺杂-n 型 SnSe、共振掺杂标度）。

## 阶段二（构效关系发现）策略调整
- 预算仅剩 231s，按规则 2 将假设从 5 缩减为 3（保留 Gap 1/2/6 对应假设 0/1/3）。
- 每个假设至少搜索 5 轮，优先保证搜索覆盖（规则 4 硬约束）。
- 若预算不足，可跳过 validate/generate_discovery_report，但搜索覆盖不可缺省。

## 下一步
1. 编辑 hypotheses.json 保留假设 0/1/3
2. 依次 run_discovery_search(0/1/3, n_iterations≥5)
3. 视预算 validate + report
4. 写记忆 + 更新 MEMORY.md + stop
