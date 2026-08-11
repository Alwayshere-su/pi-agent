# 可复现性说明（Reproducibility）

> 适用版本：Pi-Agent v2.2.8 代码库 ｜ 更新：2026-08-11
>
> 本文件系统回答一个问题：**「重跑一遍，哪些结果应当完全一致，哪些结果可能不同，以及如何独立核验？」**
>
> 一句话结论：**搜索打分、数值抽取、回归核验等确定性计算由 `seed_everything()` 固定 random/numpy 后可逐位复现；凡涉及 LLM 采样的环节（假设评估、搜索引导、报告文本）不保证逐字复现，但每一步都有审计日志，可用 `--seed` 重跑 + 确定性字段比对独立核验。**

---

## 1. 确定性环节（应逐位复现）

以下环节由纯规则/数值计算完成，不依赖 LLM 采样。固定随机种子（`python main.py --seed 42`，内部调用 `utils/config.py::seed_everything()`）后，相同输入应得到相同输出：

| 环节 | 实现位置 | 确定性来源 |
|------|---------|-----------|
| 随机种子固定 | `utils/config.py::seed_everything()` | `random.seed(seed)` + `numpy.random.seed(seed)`（`main.py --seed` 覆盖，默认 42） |
| 文献检索打分 | `literature_agent/search.py::_compute_score` | 词重叠度、引用数等启发式规则，纯函数式计算 |
| 数值/实体抽取 | `literature_agent/extractor.py`（表格/序列/句对/笛卡尔四路径）、`parser.py` 的 `_extract_*` 正则 | 正则 + 确定性规则，无随机数 |
| 搜索初始种群采样 | `literature_agent/discovery.py::BayesianOptimizer.optimize` | `np.random.uniform(...)`，受 numpy 种子控制 |
| GP 代理/UCB 采集 | `discovery.py::_gp_predict`、`_acquisition` | Cholesky 分解、RBF 核矩阵等确定性线性代数 |
| 贝叶斯/MCTS 搜索迭代 | `discovery.py`（`iteration_log` 序列） | 上述数值计算组合 |
| 证据分数与打分 | `literature_agent/scoring.py`、`scripts/baseline_random_search.py` | 确定性规则（见下节「LLM plausibility 混合」的例外） |
| 回归核验 | `literature_agent/regression_diagnostics.py`、`classical_models.py`、`symbolic_regression.py` | `numpy.polyfit` / `scipy.stats` / `sklearn`，输入确定则输出确定 |
| 参照系随机搜索 | `scripts/baseline_random_search.py --seeds 10` | 每种子独立固定，10 种子中位数可复现 |

> **注意 1（字符串哈希）**：`seed_everything()` 只固定 random/numpy。涉及字典/集合遍历顺序、字符串哈希的操作还受 `PYTHONHASHSEED` 影响（运行时设置无效，须在解释器启动前设置）。需要**完全逐位复现**（含 `str`/`set`/`dict` 迭代顺序）时，请以 `PYTHONHASHSEED=42` 启动：
>
> ```bash
> # Linux/macOS
> PYTHONHASHSEED=42 python main.py --topic "..." --budget 7200 --fresh --seed 42
> # Windows (PowerShell)
> $env:PYTHONHASHSEED=42; python main.py --topic "..." --budget 7200 --fresh --seed 42
> ```
>
> **注意 2（检索远端差异）**：arXiv / Sciverse 检索的原始返回取决于远端服务。项目对检索结果做磁盘缓存（`workspace/data/literature_cache/`，按 `--run-dir` 隔离），**缓存命中时**检索与打分完全可复现；缓存未命中时结果取决于远端当前数据。所有调用仍留审计（见第 3 节），可追溯差异来源。

---

## 2. 依赖 LLM 采样的环节（不保证逐字复现）

LLM 调用（`pi_agent/llm.py::DeepSeekProvider.chat`）使用 `temperature=0.1`（一般调用）或 `temperature=0.2`（搜索引导，`pi_agent/tools.py::_llm_search_guide`），**未传 seed 参数，采样本身不保证可复现**。涉及 LLM 的环节：

| 环节 | 实现位置 | 影响 |
|------|---------|------|
| Agent 全流程决策（检索什么、读什么、写什么） | `pi_agent/agent.py` + 23 个工具 | 不同采样可能选择不同检索词/阅读顺序/知识图谱组织 |
| 假设生成（title/description/evidence） | `h_generate_hypotheses` | 假设文本逐字不可复现 |
| **假设科学合理性评估（LLM plausibility）** | `pi_agent/tools.py::_llm_plausibility_check` | 输出 `llm_plausibility_score`，按权重混入最终置信度 |
| **LLM 搜索引导（suggestion / prune_regions / focus_regions）** | `tools.py::_llm_search_guide` → `discovery.py::_apply_llm_regions` | 引导会修改后续 `_acquisition` 的采样空间，**可能改变后续搜索路径与最终 best_params** |
| 报告 / 知识图谱 / Gap 文本撰写 | `h_generate_*` | 文本逐字不可复现 |

**关键机制：LLM plausibility 如何混入确定性分数**

- 搜索过程中的候选得分混合（`discovery.py` `_BLEND_W = 0.35`）：`y = raw_score × 0.65 + llm_plausibility × 0.35`（LLM 评分存在时）；
- 最终假设置信度混合（`discovery.py` `_BLEND_W = 0.40`）：`confidence = search_score × 0.60 + llm_plausibility × 0.40`；
- `scoring.py` 中证据分数同样按 `0.65 / 0.35` 混合。

因此：**只要 LLM 引导参与，`best_score`、`confidence` 等数值就可能因采样波动而不同**（波动幅度通常在小数点后 1–2 位，科学结论级别稳定；但逐位复现不成立）。

**降级路径 = 完全确定**：当 DeepSeek API 不可用或未配置时，`_llm_plausibility_check` 自动回退启发式评分、`_llm_search_guide` 跳过评估（候选原样返回、默认评分），此时整条搜索管线为纯确定性计算，`--seed` 相同即可逐位复现。RERUN_GUIDE.md §8.1 描述了该降级场景。

---

## 3. 如何独立核验 LLM 环节（不重跑也能审计）

所有 LLM 介入都有落盘记录，可按证据链独立核验，无需信任"它说它做了"：

| 审计产物 | 路径 | 内容 |
|---------|------|------|
| 检索调用审计 | `workspace/logs/<run-dir>/sciverse_skill_log.jsonl` | 每条搜索的调用 ID、时间戳、参数 SHA256 哈希、结果数、`adapter_mode` |
| 运行轨迹 | `workspace/logs/<run-dir>/trajectory_<run-dir>.json` | 每轮 `agent_thinking` / 工具调用序列 / 预算消耗 |
| LLM 搜索引导事件 | `workspace/outputs/<run_dir>/literature_survey/discovery/search_h*.json` 的 `llm_guidance` 字段 | `bayes_llm_guide` / `mcts_llm_guide` 事件（`suggestion`、候选数）、`bayes_llm_region_apply` 事件（`prune_regions` / `focus_regions` 及生效说明） |
| LLM 假设评估 | `.../discovery/hypotheses.json` | 每条假设的 `llm_plausibility_score`、`llm_explanation`、置信度 |
| 运行日志 | `workspace/logs/run_*.log`、`workspace/logs/<run_dir>/run_*.log` | `🧠 LLM 搜索引导: plausibility=…, suggestion=…` 与 `🧠 LLM plausibility: …` 行 |
| PDF 解析引擎 | `ParsedDocument.parse_engine` 字段（回退原因记录） | 判定解析环节是否被 MinerU 服务端波动影响 |

**核验要点**：

1. 一条最终引用（p#）→ `paper_summaries.md`（标题/DOI）→ `search_log.jsonl`（查询、数据源）→ `sciverse_skill_log.jsonl`（API 调用哈希），四层闭环（见 README 第五章）；
2. 打开 `search_h0.json` 检查 `llm_guidance.enabled` / `injected` / `n_events`——为 0 或缺失时说明该次运行 LLM 引导未参与（API 不可用或代码版本不同）；
3. LLM 引导给出的 `suggestion` / `focus_regions` 为人类可读文本与区间，领域专家可直接评估其科学性——**LLM 环节的可信度不依赖复现，而依赖可审计**。

### 3.1 `llm_guidance` 证据来源分级（红线澄清，2026-08-04）

项目内存在三类 `llm_guidance` 来源，**提交时必须严格区分，不得混用**：

| 级别 | 位置 | 性质 | 可否作为"LLM 引导真实生效"证据 |
|------|------|------|--------------------------------|
| **真实端到端** | `workspace/outputs/mof_e2e_v4/.../search_h*.json` | tools.py 序列化，事件与 iteration_log 关联，`n_events=5~17`，运行后校验通过（`run_e2e_rerun.py`） | ✅ 可（唯一推荐） |
| **事后回填审计** | `workspace/outputs/literature_survey/.../search_h*.json`（主案例） | 由 `scripts/backfill_llm_guidance.py` 真实调用 DeepSeek 生成，但搜索已完成、建议**未影响采样**；事件 `note` 含 `[回填审计]`；调用痕迹在 `workspace/logs/llm_guidance_audit.jsonl` | ⚠️ 可作"审计链路可用"证据，**不可**作"搜索内生效"证据 |
| **来源未核实** | `workspace/outputs/mof_rerun/`、`mof_rerun_v2/` 的 `search_h*.json` | trajectory 无 LLM 调用痕迹，疑似构造样例；已加 `source_note` 字段标注 | ❌ 不可引用 |

> 另：2026-08-03 曾发现来源不明的 `e2e_v3_finalize_hypotheses.py` 在 `mof_e2e_v3` 产物中硬编码 `llm_guidance: {"injected":true,"events":3}`（无真实调用记录，属伪造）。该脚本、伪造字段及整个 `mof_e2e_v3` run-dir 已删除；真实数据（NiCo 5 实测点）保留于 `workspace/archive_v3_realdata/quant_validation_nico_5pts.md`（含来源说明）。

---

## 4. 命令级核验流程

以下流程可在任意时刻执行，把「可复现性」从口头承诺变成可操作检查。

```bash
cd D:/MMLL/4.competition/2026GOAI-3

# ── 第 0 步：环境与配置自检（不调用 LLM）──
python demo.py                                          # API Key 配置 + MinerU 状态自检
python -c "from utils.config import print_config_status; print_config_status()"

# ── 第 1 步：MinerU 解析引擎健康诊断 ──
python literature_agent/parser.py                       # 打印 Cloud/Local/pip 三级状态
python -m pytest tests/test_parser_engine.py -q        # MinerU 回退逻辑测试（markitdown/pdfplumber 本地路径；历史诊断产物 mineru_test_results.json 见 workspace/outputs/literature_survey/）

# ── 第 2 步：固定种子全量重跑（确定性部分复现）──
# Windows PowerShell:
#   $env:PYTHONHASHSEED=42
python main.py --topic "MOF materials for CO2 capture" \
  --run-dir mof_rerun_v2 --budget 7200 --fresh --seed 42

# ── 第 3 步：LLM 引导审计记录核验（#12）──
python -c "
import json, glob
for f in sorted(glob.glob('workspace/outputs/mof_rerun_v2/literature_survey/discovery/search_h*.json')):
    d = json.load(open(f, encoding='utf-8'))
    g = d.get('llm_guidance', {})
    print(f, '| search_method=', d.get('search_method'), '| llm_guidance.enabled=', g.get('enabled'),
          '| n_events=', g.get('n_events'))
    for ev in g.get('events', []):
        print('   ', ev.get('type'), '| iteration=', ev.get('iteration'),
              '| suggestion=', str(ev.get('suggestion'))[:60])
"

# ── 第 4 步：检索调用审计核验 ──
head -5 workspace/logs/sciverse_skill_log.jsonl          # 每条含 parameters_hash 与 adapter_mode

# ── 第 5 步：确定性 vs LLM 环节分离比对（两次重跑之间）──
# 5a. 确定性部分应一致：对比两次运行 search_h*.json 的 iteration_log 数值序列
python -c "
import json
def load(p):
    d = json.load(open(p, encoding='utf-8'))
    return [(it['iteration'], round(it.get('score', it.get('best_score', 0)), 6)) for it in d['iteration_log']]
a = load('workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h0.json')
b = load('workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h0.json')  # 换成第二次运行的同一文件
print('确定性迭代序列一致:', a == b)
"
# 5b. LLM 部分允许不同：对比 llm_guidance.events 中的 suggestion / regions（采样所致，属正常）
# 5c. 若两次运行均无 llm_guidance 事件，说明 LLM 引导未参与，整条搜索应完全可复现

# ── 第 6 步：参照系复现（同预算随机搜索，10 种子中位数）──
python scripts/baseline_random_search.py --iterations 40 --seeds 10
```

**判断标准**：

- 确定性字段（`iteration_log` 的 score/best_score 序列、检索打分、回归核验数值）在相同 `--seed` 与相同缓存下**应完全一致**；
- LLM 字段（`suggestion`、`llm_explanation`、报告文本）**允许不同**，属预期行为；
- 若确定性字段也不一致：优先排查 `PYTHONHASHSEED` 未固定、文献缓存差异（`workspace/data/literature_cache/` 被清空或更新）、MinerU 解析结果差异（见下节）。

---

## 5. 与 PDF 解析引擎（MinerU / markitdown）的关系

解析结果会作为后续所有环节的输入，属于**输入数据层**而非计算层：

- `markitdown` 本地引擎：离线、确定性，解析结果逐位可复现；
- MinerU 远程引擎：受网络与配额影响，服务端更新可能带来细微差异（复杂表格/公式的解析质量更高，但结果不完全受本地控制）；
- 项目在 MinerU 全部不可用时**自动回退 markitdown**，回退原因写入 `parse_engine` 字段（如 `markitdown (MinerU unavailable: ...)`）。
- **PDF 表格增强（GOAI #14）**：对 PDF 输入，当 markitdown 提取的 markdown 表格不足 3 个时，`MarkItDownParser` 会用 `pdfplumber` 补充提取结构化表格（追加到文末并标注来源），`parse_engine` 标注为 `markitdown+pdfplumber`。该增强同样是**本地、确定性**的（pdfplumber 按页提取表格，结果逐位可复现），且 `pdfplumber` 缺失/解析失败时静默回退，不改变原解析行为——无论是否启用增强，解析链路都不抛异常、都有 `parse_engine` 记录。

**复现建议**：对需要精确复现的实验，可临时不配置 `MINERU_API_KEY` / `MINERU_LOCAL_URL`（或设 `prefer_mineru=False`）强制走 markitdown（含 pdfplumber 表格增强，两者均为本地确定性）；启用 MinerU 的方法见 README.md「附录 D：MinerU PDF 解析引擎启用指南」。
