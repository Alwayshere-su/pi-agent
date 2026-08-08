# Pi-Agent —— 材料科学文献驱动的构效关系自主发现智能体

> **GOAI 赛道三** | **方向三** · 材料科学文献驱动的科学发现智能体 | **路线 A** · 构效关系发现
>
> **开源仓库**：[github.com/Alwayshere-su/pi-agent](https://github.com/Alwayshere-su/pi-agent)（公开 · 代码 MIT · 文档与运行产物 CC BY 4.0）
>
> **版本**：v2.2.1（初赛终版）｜**最后更新**：2026-08
>
> **核心成果**：一个以 LLM 为核心、端到端自主运行的文献驱动科学发现智能体。在有限时间预算内完成「文献检索 → 知识抽取 → Gap 识别 → 构效关系假设 → 贝叶斯/MCTS 搜索 → 外部验证 → 报告生成」全流程。针对 MOF 材料 CO₂ 捕获主题，经 11 轮迭代、546 篇次检索（去重后证据池 543 条、最终收录 46 篇），识别 10 项 Research Gap，生成 5 条构效关系假设，完成定量回归核验与 Materials Project / OQMD 外部交叉验证——流程完整、发现有效、引用干净、证据链可审计。

> **文档维护约定**：本 README 与代码/产物同步更新；每次修改项目（代码、依赖、配置、产物口径、工具数量等）后，必须同步更新本文件（含「版本与更新记录」一节）。不一致即视为缺陷。

---

## 一、科学问题与动机

金属有机框架（MOF）是 CO₂ 捕获领域最具潜力的材料家族之一，过去二十年产出数万篇论文。但该领域存在三个结构化问题，恰好构成 AI 可介入的切入点：

| 问题 | 具体表现 | 文献证据示例 |
|------|---------|-------------|
| **知识碎片化** | 吸附容量、选择性、吸附热（Qst）等关键性能分散在上千篇论文中，缺乏统一结构化整理 | 546 篇次检索的性能数据需 Agent 自行组织为知识图谱 |
| **结论矛盾** | 同一材料在不同合成路线下性能数值差异巨大，材料-工艺-性能关系远未厘清 | Ni-MOF-74 的 CO₂ 容量报道值横跨 3.99–8.29 mmol/g |
| **权衡关系未被刻画** | 高容量、高选择性、低再生能耗三者存在公认 trade-off，但 Pareto 前沿形状与驱动因素无定量结论 | Qst 报道值 25–40 kJ/mol 窗口 vs 29 kJ/mol 甜点 |

**为什么 AI 可以介入**：文献驱动的科学发现是一条「检索 → 阅读 → 抽取 → 组织 → 推理 → 验证」的流水线，恰好可被 LLM Agent 端到端接管——检索/解析 API 化（arXiv、Sciverse、MinerU），知识组织与假设生成由 LLM 自主完成，搜索与验证可闭环（贝叶斯/MCTS + 外部数据库）。

---

## 二、系统概览

Agent 按两阶段自主运行，共 **23 个工具**，事件驱动 + 状态机 + 工具管线架构：

```
阶段一：文献调研（基本任务）
  自主检索 → 筛选去重 → 双引擎 PDF 解析 → 摘要整理
    → 知识图谱撰写（Markdown，材料/性质/数值/关系/矛盾）
    → Research Gap 识别（10 项，带置信度与证据链）
    → 调研报告生成（六章结构 + 参考文献）

阶段二：路线 A 构效关系发现
  假设生成（5 条，材料×性质×预期关系×置信度）
    → 贝叶斯优化（RBF-GP 代理 + MLE 超参数 + UCB）/ MCTS 搜索
    → 定量回归核验（二次/线性/LOOCV + 嵌套 F 检验）
    → 外部数据库验证（Materials Project / OQMD / NOMAD）
    → 参照系对比（同预算随机搜索，10 种子）
    → 发现报告（正结果/负结果/异常/反例四类信号）

    ↑ 跨轮记忆（MEMORY.md + 运行反思 + 记忆质量审计）驱动下一轮迭代（共 11 轮）
```

Agent 的检索策略、知识图谱组织、Gap 排序、假设方向、补检索时机均为 Agent 自主决策，非固定脚本。

---

## 三、核心产出

### 3.1 Research Gap 清单（10 项）

| # | Gap 名称 | 类型 | 严重程度 | 置信度 |
|---|---------|------|---------|--------|
| 1 | 双金属 MOF 金属比例-容量定量关系缺失（倒 U 型非普适性） | 缺失连接 | 高 | 0.95 |
| 2 | 水-CO₂ 竞争/协同机理矛盾（OMS vs 胺二分机理统一） | 矛盾→机理统一 | 高 | **0.97** |
| 3 | 容量-选择性-再生能 Pareto 前沿未刻画 | 缺失连接 | 高 | 0.85 |
| 4 | ML 筛选-实验闭环断裂 + 数据库误差 | 缺失连接 | 中 | 0.75 |
| 5 | DAC（400 ppm）数据稀缺 | 未探索空间 | 中 | 0.85 |
| 6 | OMS 密度-Qst 标度律缺失 | 缺失连接 | 中 | 0.72 |
| 7 | 材料-再生工艺耦合优化缺失 | 缺失连接 | 中 | 0.78 |
| 8 | 杂质气体（NO₂/SO₂）影响研究稀缺 | 未探索空间 | 中 | 0.70 |
| 9 | 缺陷工程的定量 OMS 控制缺失（缺陷类型二分） | 缺失连接 | 中→高 | 0.80 |
| 10 | 双金属实际组成 vs 名义比例偏差的系统量化缺失 | 缺失连接 | 中→高 | 0.78 |

Gap 排序逻辑：严重程度 × 置信度 × 与已有发现的关联度。Top 3（Gap 1/2/9）连续四轮稳定，与发现信号一一对应。

### 3.2 构效关系假设（5 条）

| # | 假设 | 置信度 | Novelty | 搜索方式 | Best Score |
|---|------|--------|---------|---------|------------|
| hypo_1 | 双金属 MOF-74 金属比例与 CO₂ 吸附容量呈倒 U 型定量关系 | 0.88 | 0.82 | bayesian | 0.665 |
| hypo_2 | 胺功能化 MOF 湿态 CO₂ 容量随 RH 呈峰值增强（胺型促进 vs OMS 抑制双分支） | 0.90 | 0.85 | bayesian | **0.829** |
| hypo_3 | MOF 的 Qst 在 25–40 kJ/mol 窗口可实现容量-选择性-再生能耗 Pareto 最优 | 0.62 | 0.78 | bayesian | 0.677 |
| hypo_4 | MOF-74 缺陷类型依赖：缺失配体型 vs 溶剂甲酸盐占据型对 OMS/容量影响相反 | **0.92** | **0.88** | bayesian | **0.913** |
| hypo_5 | MOF 在痕量 NO₂/SO₂ 暴露后 CO₂ 容量衰减率与 OMS 密度和孔道亲水性相关 | 0.63 | **0.90** | bayesian | 0.734 |

合计 165 个候选点探索（`total_explored=165`，search_summary 判定 strong=5）。

### 3.3 关键发现信号（四类，运行前定义）

| 类型 | 内容 |
|------|------|
| **正结果** | 双金属倒 U 型（hypo_1, 0.88）；水 RH 双分支（hypo_2, 0.90）；缺陷类型二分（hypo_4, 0.92）——均置信度 ≥ 0.7 且有 p# 证据链 |
| **负结果** | MP/OQMD 对 MOF 吸附性质覆盖为 0——升级为方法论发现（Gap 4 延伸证据） |
| **异常** | Ni-MOF-74 容量 3.99 vs 8.29 mmol/g 矛盾区间；水-CO₂ 竞争/协同机理矛盾 |
| **反例** | 胺功能化 MOF 低湿度容量反升（"水促进"分支），与"水总是有害"朴素假设相反 |

### 3.4 定量验证与参照系

- **贝叶斯 vs 随机参照系（v2 打分，10 种子 × 40 评估）**：同预算公平对比——**5 条假设全部 bayesian_wins**（diff_median +0.014~+0.039，见 `baseline_random.json`）。v2 增强打分（打分函数分段线性拉伸）修复了初赛版 10 种子 3:2 区分度不足的问题；初赛版结论如实记录于提交材料。
- **统计验证**：嵌套 F 检验（hypo_1 二次 vs 线性，F=9.909, p=0.0254）在 α=0.05 下显著；NiCo-MOF-74 五个独立实测点（archive_v3_realdata）二次 R²=0.7694 vs 经典 Vegard 线性基线 R²=-0.1530（ΔR²=+0.92）。"候选 vs 经典模型"正面对比因数据不足尚未达成，达成路径（表格化知识图谱）已明确并列入复赛计划。

---

## 四、架构亮点

| 亮点 | 说明 |
|------|------|
| **事件驱动 + 状态机 + 工具管线** | PiAgent 主循环以事件驱动、状态机（IDLE→RUN→DONE）管理生命周期，**23 个工具**注入管线，各层解耦 |
| **双引擎 PDF 解析** | MinerU 默认优先（Cloud > 本地服务 > pip 包），不可用时自动回退 markitdown_utils 本地引擎。回退原因记录于 `parse_engine` 字段 |
| **三层 Sciverse 接入** | MCP > Skill > REST 三模式依次检测、自动降级，全部不可用时回退纯 arXiv（始终可用）。审计日志标注当前激活模式 |
| **贝叶斯 + MCTS 搜索** | RBF-GP 代理（超参数 MLE 拟合）+ UCB 采集函数；MCTS 默认每 10 轮 LLM 引导（频率可配置）。LLM 引导事件写入 `_llm_events` / `llm_guidance` 审计字段 |
| **跨轮记忆** | MEMORY.md + 运行反思 + 记忆质量自动审计（五维评分，低质量条目标记归档），让 Agent 在多轮之间继承结论、积累证据 |
| **四层证据追溯** | 最终报告中的 Gap/假设引用 → `paper_summaries.md` 文献条目 → `search_log.jsonl` 检索查询 → `sciverse_skill_log.jsonl` 原始 API 调用 |

---

## 五、证据链与审计

每个结论均可通过四层追溯机制验证：

```
Gap/假设中的 p# 引用  →  paper_summaries.md（标题/DOI）
    →  search_log.jsonl（检索查询、数据源、结果数）
    →  sciverse_skill_log.jsonl（API 调用 ID、时间戳、参数 SHA256 哈希）
```

- **运行轨迹**：`workspace/logs/trajectory_survey.json` 逐条记录每轮思考/工具调用/预算消耗
- **审计机制说明**：`workspace/outputs/literature_survey/audit_trail.md`
- **API 审计**：`workspace/logs/sciverse_skill_log.jsonl` 截至 2026-08 共 **149 条**调用记录（持续累积，以日志实际行为准）
- **零虚假引用**：所有引用经 Sciverse API 调用记录 + 论文 ID 双重验证；gap_report.md 中 48 处 p# 引用 46 处（96%）内联 DOI（经 Crossref/DataCite/doi.org 核验真实存在）

---

## 六、快速开始

### 环境与安装

- Python 3.10+（开发/CI 环境 3.12，CI matrix 另含 3.11）
- Windows / Linux / macOS

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate.bat
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### 配置 API Key

在项目根目录创建 `.api_key` 文件（已 `.gitignore`，不入库）：

```
DEEPSEEK_API_KEY=sk-xxxx
SCIVERSE_API_KEY=sci_xxxx
MINERU_API_KEY=mineru-xxxx   # 可选，见下方 MinerU 启用说明
```

> DeepSeek：推理大模型（OpenAI 兼容接口，可替换，必填）。Sciverse：文献检索（可选，缺失时回退纯 arXiv）。MinerU：PDF 解析引擎（可选，云 API 需 `MINERU_API_KEY`，缺失时自动回退本地 markitdown；启用方式见[附录 D](#附录-dmineru-pdf-解析引擎启用指南)）。

### 运行

```bash
python main.py --topic "MOF materials for CO2 capture" --budget 600
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `--topic` | 调研主题（必填） | — |
| `--run-dir` | 运行目录名（多主题并行隔离） | `survey` |
| `--budget` | 时间预算（秒） | 7200 |
| `--fresh` | 强制从头开始 | 关 |
| `--seed` | 随机种子（确定性计算） | 42 |

### 多主题运行（Agent 泛化性验证）

同一 Agent 在 **8 个主题**上独立调研（产物与记忆互不干扰）。公开仓库保留主案例与正式主题产物；冒烟/重跑主题（smoke_test / g3test / mof_rerun / mof_rerun_v2）产物本地留存、不入库：

```bash
python main.py --topic "MOF materials for CO2 capture" --budget 600
python main.py --topic "halide perovskite band gap and stability" --run-dir perovskite --budget 600 --fresh
python main.py --topic "thermoelectric materials ZT optimization" --run-dir thermoelectric --budget 600 --fresh
python main.py --topic "high-nickel cathode capacity retention" --run-dir cathode --budget 600 --fresh
```

> 已归档运行：`validation`（固态电解质）、`mof_e2e_v4`（e2e 全量重跑，含 llm_guidance 审计实证）；冒烟验证（`smoke_test` / `g3test`）与旧版重跑（`mof_rerun` / `mof_rerun_v2`）产物本地留存。

### 参照系复现

```bash
python scripts/baseline_random_search.py --iterations 40 --seeds 10
```

### 模块自测（离线，无需网络）

```bash
python -m pytest tests/          # 项目级单元测试（122 项）
python literature_agent/classical_models.py   # Slack/Vegard 参数恢复自检
python literature_agent/symbolic_regression.py # 表达式恢复自检
python literature_agent/extractor.py          # 数值 (x,y) 配对自测
python literature_agent/parser.py             # MinerU 状态诊断
```

---

## 七、项目结构

```
main.py                          # 入口：参数解析 + 预算 + 异常处理
demo.py                          # 配置/MinerU 状态演示
pi_agent/
├── agent.py                     # PiAgent 主循环（事件驱动 + 状态机 + 工具管线）
├── llm.py                       # LLM 调用 + 工具 schema（DeepSeek/OpenAI 兼容）
├── tools.py / _tools_impl.py    # 23 个工具实现
├── prompts.py                   # 系统提示词（两阶段流程 + 预算策略）
├── state_machine.py             # Agent 状态机
├── memory_quality.py            # 跨轮记忆质量自动审计
└── events.py / context.py / session.py / config.py
literature_agent/
├── search.py                    # arXiv + Sciverse 检索与缓存
├── sciverse_mcp.py              # Sciverse 三层接入适配（MCP/Skill/REST）
├── parser.py                    # 双引擎 PDF 解析（MinerU + 本地回退）
├── extractor.py                 # 实体/数值抽取（表格/序列/句对/笛卡尔四路径）
├── discovery.py                 # 贝叶斯优化 + MCTS + 外部数据库验证
├── scoring.py                   # 证据打分
├── classical_models.py          # Slack / Vegard 经典模型
├── symbolic_regression.py       # 符号回归
├── bayesian_regression.py       # 贝叶斯回归
├── regression_diagnostics.py    # 回归诊断
├── cross_theme.py               # 跨主题连接
└── evidence_chain_report.py     # 证据链报告
utils/
├── config.py                    # API Key / 种子 / 模型配置
└── budget_tracker.py            # 时间预算跟踪
scripts/
├── baseline_random_search.py    # 随机探索参照系（v2 打分）
├── run_e2e_rerun.py / run_validation_pipeline.py / run_nico5_validation.py  # 重跑管线
├── meta_analysis.py / prepare_scibase.py / verify_scoring.py 等
├── budget_resume_test/  cache_isolation_test/  test_core_functions/  # 回归测试
tests/                           # pytest 单元测试
vendor/bash/                     # 内置 Git Bash（Windows 下 shell 工具运行时依赖）
workspace/
├── outputs/<run-dir>/literature_survey/  # 各主题产出
├── memory/<run-dir>/                      # 跨轮记忆
├── logs/                                  # 运行轨迹 + 审计日志
└── data/literature_cache/                 # 文献缓存（已 gitignore）
```

---

## 八、合规披露（摘要）

| 项 | 说明 |
|----|------|
| **开源仓库** | [github.com/Alwayshere-su/pi-agent](https://github.com/Alwayshere-su/pi-agent)（公开，2026-08 上线） |
| **商业 API** | DeepSeek（`deepseek-v4-flash`，推理）、Sciverse（文献检索）。替代方案：任意 OpenAI 兼容端点、纯 arXiv 检索（零成本） |
| **PDF 解析** | MinerU（推荐：云 API `mineru.net` / 本地部署 `localhost:8888`，启用见[附录 D](#附录-dmineru-pdf-解析引擎启用指南)）+ markitdown_utils（本地回退，结果确定可复现） |
| **数据来源** | arXiv（开放获取）、Sciverse（仅标题+摘要内部使用）、Sci-Base（HuggingFace）、Materials Project / OQMD / NOMAD（公开数据库） |
| **密钥管理** | `.api_key` 已 gitignore，不入库 |
| **许可证** | 代码 MIT；文档与运行产物 CC BY 4.0 |
| **已有项目** | 独立实现，无基于已有项目 |

> 合规披露摘要见上表（商业 API / 数据来源 / 许可证）；完整披露（开源计划、费用假设、替代方案、迁移成本、可复现性影响）见本仓库内文档与赛题提交说明。

---

## 九、引用本项目的文档索引

| 文档 | 内容 |
|------|------|
| `初赛提交材料.md` | 完整方案说明、技术路线、实验结果、评审自查（**本地文档，不入公开仓库**） |
| `初赛方案_修改清单.md` | docx 方案逐项核对清单（**本地文档，不入公开仓库**） |
| `材料科学文献调研Agent_算法赛初赛方案.docx` | 初赛提交方案（**本地提交物，不入公开仓库**） |
| `workspace/outputs/literature_survey/gap_report.md` | 10 项 Gap 完整清单 + 证据链 |
| `workspace/outputs/literature_survey/knowledge_graph.md` | R1–R33 构效关系知识图谱 |
| `workspace/outputs/literature_survey/paper_register.md` | 文献登记表（546 篇次口径说明 + 543 条证据池） |
| `workspace/outputs/literature_survey/discovery/` | 假设、搜索记录、定量验证、参照系、外部验证（docx 全部数字的证据源） |
| `workspace/outputs/literature_survey/audit_trail.md` | 证据链审计机制说明 |

---

## 十、版本与更新记录

> 维护约定：每次修改项目（代码 / 依赖 / 配置 / 产物口径 / 工具数量 / 文档索引）后，在此追加一行，并同步更新上文对应章节。禁止只改代码不改 README。

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0 | 2026-08 | 初赛终版重写：工具数 19→23 同步；参照系更新为 v2 打分 5 条全胜（diff +0.014~+0.039）；开发环境统一 Python 3.12；8 主题口径；Sciverse 审计 149 条；文档索引去除非真实文件；新增本节维护约定 |
| v2.0.1 | 2026-08 | 一致性修缮：ARCHITECTURE.md 工具数 19→23（3 处）；`pi_agent/tools.py` 工厂注释 "all 9 tools"→"all 23 tools"；REPRODUCIBILITY.md 工具数 19→23；`scripts/fill_initial_template.py`（docx 生成模板）工具数 19→23 |
| v2.1.0 | 2026-08 | 代码健壮性修缮（审计驱动，全量回归 125 passed）：① 上下文压缩保留 user_goal + 压缩后清理孤儿 tool 消息（恢复场景不再失忆主题/API 400）；② 恢复启动不再删除迭代脚本；③ LLM 调用全部显式 timeout=120 + 不可恢复错误（密钥/权限/模型不存在）立即放弃重试；④ 搜索固定 SEED 保证可复现；⑤ 后台子进程 atexit 自动清理 + 超时杀进程树 + daemon 线程 + 输出缓冲上限；⑥ read/write/list 路径沙箱 + `.api_key` 等敏感文件读写拦截；⑦ MinerU：缺包降级、Cloud 不 POST 本地路径、提交重试、轮询连续失败 5 次提前放弃（防预算黑洞）、parse_engine 记录真实原因；⑧ 外部验证单库异常降级不中断 discovery、OQMD 响应格式防护、缓存按 run_dir 隔离且原子读写；⑨ 知识图谱 load/merge 容错、`.api_key` 读取 UTF-8、预算除零防御、checkpoint 原子写与损坏留档 |
| v2.1.1 | 2026-08 | symbolic_regression 域保护（完整跑冒烟发现并修复）：`_NP_FUNCS` 的 log/log10/sqrt/tan/exp 对域外输入产生 NaN/Inf，导致 `predict` 抛"非有限值"异常、工具崩溃——改为截断到有限值（log 下限 EPS、sqrt 下限 0、tan/exp clip），不适用的表达式由 MSE 自然淘汰。冒烟验证：`--run-dir smoke_fix` 600s 完整跑通（30 轮、48 篇文献、3 条假设、LLM 搜索引导注入 6 次事件、双轨验证、发现报告），修复后 symbolic_regression 正常产出报告 |
| v2.2.0 | 2026-08 | 冒烟运行暴露问题批量修复（4 并行 agent + 父级回归）：① `generate_hypotheses` LLM 假设生成双路径增强——`_extract_json_object` 增贪婪兜底提取、新增 `_hypotheses_from_json` 兼容 dict/裸数组、独立 API 路径复用 `_call_llm` 并增加 JSON 约束重试、异常全部带 `type(e).__name__` 诊断（不再静默失败）；② 预算超支 40s 修复——收尾白名单拆分 `_WRAPUP_LIGHT_TOOLS`（write/read/edit/stop/think + 一次性报告生成）与 `_WRAPUP_HEAVY_TOOLS`（搜索/验证/模型对比/符号回归/shell 预算耗尽后一律拒绝），`_inject_final_warning` 文案同步，`budget_resume_test` 断言更新为与新设计一致；③ 临时文件残留清理——删除 `smoke_fix/refs_tmp.md` 与主案例 `gap_report.md.bak`，prompts.py 新增「产物零临时文件残留」规则（用后必删、收尾前 list_files 自查）；④ stderr 降噪——Sci-Base 缺索引提示改为进程内仅首次完整打印（模块级标志 + 锁），后续只一行简短提示 |
| v2.2.1 | 2026-08 | 开源上线：代码推送至公开 GitHub 仓库 [github.com/Alwayshere-su/pi-agent](https://github.com/Alwayshere-su/pi-agent)（公开 · MIT）；`.gitignore` 补齐排除（赛题 zip / 官方模板 / 会话副本 / `workspace/code/` Agent 运行时脚本 / `*.bak-*` 等）；README 头部与合规表新增开源仓库链接；初赛方案 docx 为本地提交物、不入公开仓库（README 索引已标注） |
| v2.2.2 | 2026-08 | 仓库精简：内部/赛题文档（ARCHITECTURE / COMPLIANCE / REPRODUCIBILITY / RERUN_GUIDE / E2E_RERUN_GUIDE / CROSS_THEME_REPORT / problem_definition / 补充 / 赛题内容）移出公开仓库（本地保留，`.gitignore` 排除）；README 同步去除这些文档的引用死链（合规摘要、可复现性要点、MinerU 策略已内嵌 README），文档索引标注本地文档 |
| v2.2.3 | 2026-08 | 仓库再瘦身：历史归档 `scripts/_archive_pid_work/`（33 个一次性核验脚本）与一次性回填脚本 `backfill_llm_guidance*`（2 个）移出公开仓库（本地保留）；README 项目结构同步移除归档目录行；冒烟主题产物（smoke_test/g3test/mof_rerun/mof_rerun_v2）保留作为泛化性过程证据 |
| v2.2.4 | 2026-08 | 仓库精简（209→180）：docx 生成工具（`build_prelim_proposal.py`/`fill_initial_template.py`）与冒烟/旧版重跑主题产物（smoke_test / g3test / mof_rerun / mof_rerun_v2 三目录）移出公开仓库（本地保留，`.gitignore` 排除）；README 主题表述更新（保留主案例 + mof_e2e_v4 + 4 个正式主题：cathode / perovskite / thermoelectric / validation） |
| v2.2.5 | 2026-08 | 复现性修缮（组委会复现扫描）：① `docker-compose.yml` 的 `env_file: .api_key` 改 `required: false`——无 `.api_key` 也能 `docker compose up`（与 README"缺失自动降级"承诺一致）；② 模块自检命令（`classical_models.py` / `extractor.py` / `symbolic_regression.py`）加 Windows UTF-8 输出兜底——GBK 控制台打印 `²`/`°C` 不再 UnicodeEncodeError，复现命令跨平台可跑；③ `DocumentParser` 补 `mineru_available` 属性（README 附录 D 的 `python literature_agent/parser.py` 诊断命令依赖，此前 AttributeError）；验证：pytest 122 passed、四个自检命令与 demo.py 全部 exit 0 |

---

## 附录 A：Sciverse 三层接入方式详解

本项目实际以 **REST API 直连为主**。另有两个可选扩展接入方式，由同一适配层按优先级自动检测：

1. **REST API 直连（实际主模式）**：设置 `SCIVERSE_API_KEY`，调用 `https://api.sciverse.space`。当前仓库审计记录 **149 条**（统计时点 2026-08；`sciverse_skill_log.jsonl` 持续累积，以日志实际行为准），`adapter_mode` 均为 `rest`。
2. **可选扩展 · JSON-RPC MCP 适配层**：设置 `SCIVERSE_MCP_URL` 后，以自研轻量 JSON-RPC 2.0 HTTP 客户端向第三方 MCP server 端点通信。
3. **可选扩展 · 外部 Skill 脚本**：设置 `SCIVERSE_SKILL_PATH` 后，通过 `subprocess` 调用外部 Python 脚本（stdin/stdout JSON）。
4. **检测与回退**：`create_sciverse_adapter()` 依次检测 MCP > Skill > REST，任一不可用则降级；全部不可用时回退纯 arXiv。
5. **审计证据链**：无论接入模式，每次调用均生成标准化审计记录（`sciverse_skill_log.jsonl`），含调用 ID、时间戳、参数 SHA256 哈希、结果摘要。

## 附录 B：参照系复现步骤

1. `python main.py --topic "MOF materials for CO2 capture" --budget 600 --fresh --seed 42`
2. 检查 `workspace/outputs/literature_survey/` 五件套是否齐全
3. `python scripts/baseline_random_search.py --iterations 40 --seeds 10`
4. 查看结果 `workspace/outputs/literature_survey/discovery/baseline_random.json`（v2 打分，5 条假设应全部 bayesian_wins）

LLM 采样不保证逐字可复现；搜索打分等确定性计算由文献数值确定（`seed_everything()` 固定 random/numpy）。

> 可复现性要点见上文（确定性计算由 `--seed` 固定；LLM 采样随机但结论带证据链可独立核验）；本地另有 REPRODUCIBILITY.md 完整说明。

## 附录 C：输出结构

```
workspace/outputs/<run-dir>/literature_survey/
├── paper_summaries.md           # 检索结果摘要整理
├── knowledge_graph.md           # Agent 自写知识图谱
├── gap_report.md                # Research Gap 清单
├── survey_report.md             # 调研报告（六章 + 参考文献）
└── discovery/
    ├── hypotheses.json          # 5 条假设
    ├── search_h0-4.json         # 每条假设的搜索记录（v2.0 含 llm_guidance 审计字段）
    ├── quantitative_validation.md/.json  # 定量回归核验
    ├── materials_project_validation.json # 外部数据库验证
    ├── discovery_report.md/.json         # 发现报告
    └── baseline_random.json             # 参照系结果（v2 打分）
```

## 附录 D：MinerU PDF 解析引擎启用指南

> MinerU 是 OpenDataLab 的开源文档解析引擎（PDF→结构化内容），对复杂表格/数学公式/中文论文的解析质量优于本地 markitdown。本项目的双引擎策略：**MinerU 优先（Cloud > 本地服务 > pip 包），全部不可用时自动回退 markitdown**（离线、结果确定可复现）。回退原因写入 `ParsedDocument.parse_engine` 字段，可在每个解析结果与 `mineru_test_results.json` 中审计。

### D.1 云 API 方式（mineru.net）

1. 在 MinerU 平台注册获取 API Key：<https://mineru.net>（OpenDataLab 开源文档解析引擎，赛题资源表亦标注获取方式为 mineru.net）；
2. 二选一配置 `MINERU_API_KEY`：
   - 环境变量：`set MINERU_API_KEY=your-key`（Windows）或 `export MINERU_API_KEY=your-key`（Linux/macOS）；
   - 或写入项目根目录 `.api_key` 文件（已 `.gitignore`，不入库）：`MINERU_API_KEY=your-key`；
3. 验证：运行 `python demo.py`（`config_status` 中 `[OK] mineru`）或 `python literature_agent/parser.py` 查看 Cloud 端点状态（`https://mineru.net/api/v1/agent/parse/url`）。

> 说明：`MINERU_API_KEY` 由 `utils/config.py` 读取（环境变量 + `.api_key` 文件，与 `SCIVERSE_API_KEY` / `MATERIALS_PROJECT_API_KEY` 同模式）。Cloud 解析为异步任务（提交→轮询→取结果，见 `literature_agent/parser.py::_parse_cloud`），受网络与平台配额影响，属已知限制。

### D.2 本地服务方式（localhost:8888）

适合需要稳定、低延迟、不受云配额影响的场景。`MinerUParser.LOCAL_BASE` 默认 `http://localhost:8888`，可用环境变量 `MINERU_LOCAL_URL` 覆盖。健康检查端点为 `GET /health`，解析端点为 `POST /parse`（见 `parser.py`）。

```bash
# 示意：docker 启动 MinerU 本地服务并映射到 8888 端口
# （具体镜像名/参数以 MinerU 官方仓库 https://github.com/opendatalab/MinerU 发布的部署说明为准）
docker run -d --name mineru-local -p 8888:8888 mineru/mineru-service:latest
```

启动后验证：`python literature_agent/parser.py` 打印的 `Local 状态` 应为可用。

### D.3 自动回退行为与已知限制

| 项 | 说明 |
|----|------|
| **自动回退** | MinerU 任一通道不可用/解析失败时，`DocumentParser` 自动回退 markitdown 本地引擎，`parse_engine` 记录原因（如 `markitdown (MinerU unavailable: ...)`） |
| **质量差异** | markitdown 对复杂表格（合并单元格）、数学公式（LaTeX）与部分 PDF 版式解析较弱；MinerU 在上述场景质量更优。可解析质量差异影响下游数值抽取的覆盖率 |
| **可复现性** | markitdown 离线确定可复现；MinerU 远程引擎受网络/配额/服务端版本影响，结果可能细微差异 |
| **强制本地** | 需要精确复现时可不配置 `MINERU_API_KEY`/`MINERU_LOCAL_URL`，或对 `DocumentParser(prefer_mineru=False)` 走纯本地路径 |

---

*许可证：代码 MIT；文档与运行产物 CC BY 4.0（不含第三方 API 数据）。*
