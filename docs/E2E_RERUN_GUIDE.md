# GOAI 路线 A — v2 端到端全量重跑指南（E2E_RERUN_GUIDE.md）

> 针对 **问题 #12 残余**：主案例（`workspace/outputs/literature_survey/`）的
> `search_h*.json` 中 `llm_guidance` 是**回填的审计记录**（`note` 带 `[回填审计]`，
> 事件与 `iteration_log` 采样点无关联），LLM 建议未真正影响搜索采样路径。
> 本指南用于在 **v2 代码**上以**全新 run-dir** 完整重跑主案例，验证 LLM 搜索引导
> 真实生效。

---

## 1. 结论速览（已核实，附代码证据）

| 项目 | 结论 | 证据 |
|---|---|---|
| LLM 引导在搜索循环内**是否默认启用** | ✅ **默认启用，无需任何环境变量/命令行参数开关** | `pi_agent/tools.py:3862-3864`：`llm_enabled = bool(getattr(self, "_on_think", None)) or bool(getattr(self, "_call_llm", None))`。`_call_llm` 是同文件类方法（`tools.py:571`，恒存在），`_on_think` 在 `pi_agent/agent.py:260` 绑定——二者恒非空 → `llm_enabled=True` → `tools.py:3868-3869` 把 `llm_guide` 注入 `engine.bayes_opt._llm_guide` 与 `engine.mcts_searcher._llm_guide` |
| 真实 LLM 调用是否成功 | 取决于 `DEEPSEEK_API_KEY` 与网络；失败时**优雅降级**，不影响搜索 | `pi_agent/tools.py:668-687`（`_call_llm` 直接调 DeepSeek，失败回退 `_on_think`）；`tools.py:669-675`（LLM 不可用时原样返回候选并置默认分） |
| LLM 建议是否真正影响采样 | ✅ v2 已实现：`_apply_llm_regions` 把 `prune_regions`/`focus_regions` 应用到 `_acquisition`（聚焦区间采样 + 剪枝剔除） | `literature_agent/discovery.py:1283-1327`（`_apply_llm_regions`）；`discovery.py:1342-1397`（`_acquisition` 中 focus/prune 生效）；触发节奏 `iteration % 5 == 4`（`discovery.py:1138`） |
| run-dir 隔离 | ✅ `--run-dir <name>` 完全隔离 outputs / memory / logs / checkpoint / 文献缓存 | `utils/config.py:38-62`（`set_run_dir`）；`main.py:66-71, 86-88` |
| 重跑建议 run-dir | `mof_e2e_v3`（当前确认不存在；已完成参考运行 `mof_e2e_v4` 的产出在 `workspace/outputs/mof_e2e_v4/`） | — |

**为什么主案例会"回填"**：主案例运行时代码里 `_llm_guide` 未注入（或注入后仅记录事件、
未应用 region），事后由 `scripts/backfill_llm_guidance.py` 真实调用
DeepSeek 生成 suggestion/regions 写回 `search_h*.json` 的 `llm_guidance` 字段
（审计痕迹见 `workspace/logs/llm_guidance_audit.jsonl`，`note` 均含 `[回填审计]`）。
v2 已在 `discovery.py` 补齐 **region 应用到 `_acquisition` 采样** 的真实路径。

---

## 2. 运行前置检查（脚本自动完成）

运行前请确认：

1. **Python 环境**：项目依赖已安装（`pip install -r requirements.txt`）；
   `python main.py --help` 可正常打印。
2. **DeepSeek API key 有效**：`.api_key` 文件含 `DEEPSEEK_API_KEY=sk-...`（非占位符），
   或已设环境变量 `DEEPSEEK_API_KEY`。脚本会调用
   `utils.config._is_placeholder` / `_has_valid_api_key` 检查。
3. **磁盘空间 ≥ 3 GB**（文献缓存与产物均落在 workspace/）。
4. **run-dir 无冲突**：`mof_e2e_v3` 对应的 5 个隔离目录必须均不存在
   （`workspace/outputs/mof_e2e_v3/literature_survey`、
   `workspace/memory/mof_e2e_v3`、`workspace/logs/mof_e2e_v3`、
   `workspace/checkpoint/mof_e2e_v3`、`workspace/data/literature_cache/mof_e2e_v3`）。
5. **网络可达**：api.deepseek.com、Sciverse 检索源、arxiv/semantic scholar（检索失败
   会走缓存或降级，但 LLM 引导需要 DeepSeek 在线）。

> 脚本 `--dry-run` 可单独执行前置检查，不实际运行。

---

## 3. 运行步骤

### 3.1 一键脚本（推荐）

在项目根目录执行（脚本内部自动切换到项目根）：

```powershell
# PowerShell / cmd 均可
python scripts/run_e2e_rerun.py --dry-run        # ① 只做前置检查
python scripts/run_e2e_rerun.py                   # ② 全新重跑（mof_e2e_v3, budget 7200, fresh, seed 42）
```

脚本会依次完成：前置检查 → 打印运行命令 → 执行
`python main.py --topic "MOF materials for CO2 capture" --run-dir mof_e2e_v3 --budget 7200 --fresh --seed 42`
→ 运行后校验（`llm_guidance` 真实性 + 产物清单 + 新旧对比）→ 输出通过/失败结论。

常用参数：

| 参数 | 说明 |
|---|---|
| `--run-dir` | 默认 `mof_e2e_v3`，换名即换隔离空间 |
| `--budget` | 默认 7200 秒；小规模验证可用 `--budget 1800` |
| `--seed` | 默认 42（确定性计算可复现；LLM 采样不受种子控制） |
| `--resume` | 断点续跑（同 run-dir 不带 `--fresh`） |
| `--fresh` | 全新开始（默认；会删除当前 run-dir 的 checkpoint） |
| `--dry-run` | 只检查不运行 |
| `--skip-verify` / `--no-compare` | 跳过校验 / 跳过新旧对比 |

### 3.2 手动命令（等价于脚本内部逻辑）

```powershell
python main.py --topic "MOF materials for CO2 capture" --run-dir mof_e2e_v3 --budget 7200 --fresh --seed 42 2>&1 | Tee-Object workspace/logs/mof_e2e_v3/run_e2e_rerun.log
```

运行日志同时落在 `workspace/logs/mof_e2e_v3/run_e2e_rerun.log`
（及带时间戳副本 `run_e2e_rerun_YYYYMMDD_HHMMSS.log`）。

---

## 4. 预计时长与 token 成本（估算）

> ⚠️ 以下均为**估算**，实际受 API 延迟、网络、检索源配额、Agent 决策轮数影响。

- **时长**：预算固定 7200s（2 小时）。主案例历史运行约 32 轮、结束时剩余约 226s
  （见 `workspace/logs/trajectory_survey.json`），即实际约 **1.9 小时**。
  重跑估算 **60–120 分钟**（Agent 通常跑到接近预算耗尽或提前收尾）。
- **DeepSeek 调用次数（估算 70–100 次）**：
  - Agent 主循环：每轮 1 次 `call_with_tools`，约 **30–45 次**。
  - LLM 搜索引导 `_llm_search_guide`：每条假设每次 `run_discovery_search` 触发
    `1`（initial 种群，`discovery.py:1094-1118`）+ `floor((N-1)/5)+1` 次
    （周期 `iteration % 5 == 4`，`discovery.py:1138`）。
    主案例 5 条假设若按 `N=10/10/30/30/30` 计 → `3+3+7+7+7 = 27` 次，
    加上可能的补强搜索，约 **27–35 次**。
  - 其他阶段（知识抽取 LLM 精提、假设生成、Gap 分析、plausibility 检查、报告生成）：
    约 **10–20 次**。
- **Token 成本（估算）**：
  - 搜索引导每次 prompt 约 1.7K 字符（≈0.9–1K token）、输出约 300 字符（≈0.2K token）。
  - 主循环 prompt 含系统提示 + 工具定义 + 对话历史（超长自动压缩，`agent.py:836-850`），
    单轮 input 约 5–15K token、output 约 0.5–2K token。
  - 合计 **input ≈ 0.4–0.8M token，output ≈ 0.1–0.2M token**；
    按 DeepSeek 主流档位（flash 级，输入≈¥0.5–2/M、输出≈¥2–4/M 量级）估算
    **总成本约 ¥1–5 / $0.2–0.7**（实际以 DeepSeek 官方计费为准）。

---

## 5. 失败处理与断点续跑（budget_resume 机制）

### 5.1 机制说明

- 每轮 Agent 循环结束都会保存会话 checkpoint 到
  `workspace/checkpoint/<run_dir>/checkpoint_survey.json`
  （`pi_agent/session.py:34-53`，含 `iteration / messages / budget_elapsed / trajectory`）。
- 再次以**同一 run-dir、不带 `--fresh`** 启动时，`PiAgent.run()` 自动检测
  checkpoint 并恢复（`pi_agent/agent.py:545-558`）：`start_iter = ckpt["iteration"]`，
  `budget.set_accrued(ckpt["budget_elapsed"])` —— **剩余预算 = 总预算 − 已用**
  （`_ResumableBudgetTracker`，`agent.py:161-195`），不会累计超支。
- 预算耗尽后 `_budget_wrapup_hook`（`agent.py:439-449`）拦截"继续探索"类工具、
  放行收尾类工具（`run_discovery_search` / `validate_discovery` / 写报告 / `stop`）。

### 5.2 常见失败与处理

| 场景 | 处理 |
|---|---|
| 网络中断 / API 超时 | 待网络恢复后**重跑同一条命令（不加 `--fresh`）**，从最近 checkpoint 续跑；进程被杀未存盘的一轮最多丢失 |
| 中途 Ctrl+C | 同上；`run_e2e_rerun.py --resume` 等价 |
| 运行完成但校验失败 | 查看 `run_e2e_rerun.log` 与校验输出；若 `n_events` 少或 `suggestion` 为空，多为 LLM 调用失败降级（API key/网络），可加预算重跑（`--budget` 调大，带 `--resume`） |
| 想重新开始 | 换新 `--run-dir`（推荐），或确认无误后对**当前 run-dir** 加 `--fresh`（会删除其 checkpoint；不删 outputs/轨迹） |
| 磁盘不足 | 清理 `workspace/data/literature_cache` 下不需要的旧缓存 |

> ⚠️ 注意：`--fresh` 会删除 `workspace/checkpoint/<run_dir>/checkpoint_*.json`
> （`agent.py:273-285`），**续跑时切勿带 `--fresh`**；`--fresh` 不会删除 outputs/
> trajectory/记忆，仅清 checkpoint。

---

## 6. 如何验证「LLM 引导真正影响采样」

重跑后对 `workspace/outputs/mof_e2e_v3/literature_survey/discovery/search_h*.json`
做以下核对（脚本 `verify` 已自动化大部分）：

### 6.1 结构判据（真实 vs 回填）

| 字段 | 主案例旧产物（回填） | v2 重跑（期望真实） |
|---|---|---|
| `llm_guidance.enabled / injected` | `true / true` | `true / true` |
| `llm_guidance.n_events` | 4（每条假设仅补 2 次引导 + 2 次 region_apply） | **≥ 3**（initial + 2 次周期）+ 对应 region_apply；`N=30` 时 ≥ 7 + 7 |
| 事件 `note` | 含 **`[回填审计]`** | **不含**（`_apply_llm_regions` 真实写入，`discovery.py:1326`） |
| 事件与 `iteration_log` 关联 | 无关联（回填事件 `iteration` 与采样点对不上） | `bayes_llm_guide` 的 `iteration` 与 `iteration_log` 中的 4/9/… 对齐 |

### 6.2 采样路径判据（最有力证据）

`iteration_log` 记录的是每次 `_acquisition` 实际选中的采样点（`best_params` 对应的
params 序列）。v2 中 `_apply_llm_regions` 在 `iteration % 5 == 4` 时应用
prune/focus（`discovery.py:1138-1159`），因此：

1. **剪枝生效**：某次引导后，`iteration_log` 后续轮次的 `temperature` /
   `property_value` 等应**避开** `prune_regions` 区间。
   - 旧产物反例（`search_h0.json`）：iteration 4 回填的 `prune_regions` 含
     `[1000, 1500]`（温度），但 `iteration_log` 中 iteration 4 采样点温度 = **1463.8K**，
     iteration 0 = 1175.5K —— 高温点仍在采样，证明回填**未影响采样**。
   - 新产物期望：引导后（iteration ≥ 5）不再出现 ≥1000K 采样点（或显著减少）。
2. **聚焦生效**：引导后的采样点应更密集地落在 `focus_regions`（如
   `temperature 300–500K`、`composition_x 0.3–0.7`）。
3. **best_params / best_score 变化**：由于采样空间被 LLM 重塑，新
   `best_params` 与旧值通常不同（旧 `search_h0.json`：`property_value=11.06,
   composition_x=0.59, temperature=355.7`）。该差异**不是失败判据**，仅作
   "搜索路径确实改变"的旁证。
4. **`suggestion` 语义一致性**：`bayes_llm_guide.suggestion` 应描述候选的物理
   不合理点，且与后续采样点的收缩方向一致（例如"温度过高，建议聚焦 300–500K"，
   则后续 iteration_log 温度收敛到该区间）。

### 6.3 自动化对比

```powershell
python scripts/run_e2e_rerun.py --dry-run        # 前置检查
python scripts/run_e2e_rerun.py                   # 重跑 + 自动校验 + 新旧对比表
```

校验退出码：`0` = 通过（injected=true、含 suggestion、无回填标记、产物完整）；
`1` = 校验失败（明细见输出）；`2` = 前置检查失败。

---

## 7. 产物清单（重跑后）

`workspace/outputs/mof_e2e_v3/literature_survey/` 下应包含：

| 文件 | 说明 |
|---|---|
| `survey_report.md` | 最终调研报告（必需） |
| `knowledge_graph.md` | 知识图谱（搜索评分依据） |
| `paper_summaries.md` | 论文摘要池 |
| `gap_report.md` | Gap 分析报告 |
| `discovery/hypotheses.json` | 假设列表（含 `search_iterations`、`confidence`） |
| `discovery/search_h{0..N}.json` | **每条假设的搜索结果**（校验 LLM 引导的核心） |
| `discovery/discovery_report.json` / `.md` | 发现报告 |
| `discovery/validation_summary.md` 等 | 双轨验证 / 定量验证产物 |
| `workspace/logs/mof_e2e_v3/trajectory_mof_e2e_v3.json` | Agent 决策轨迹（证据链） |
| `workspace/memory/mof_e2e_v3/` | 调研记忆 + MEMORY.md 索引 |
| `workspace/checkpoint/mof_e2e_v3/` | 断点续跑 checkpoint（完成后被删除） |

> 主案例旧产物（`workspace/outputs/literature_survey/`）**保持不动**，作为对比基线。

---

## 8. FAQ

- **重跑为什么必须新 run-dir？** 主案例产物用于对比；同目录重跑会覆盖
  `search_h*.json` / `survey_report.md`，丢失"回填 vs 真实"的对照证据。
- **LLM 引导需要配置开关吗？** 不需要。`tools.py:3862-3864` 判断的是 handler
  方法是否存在（恒存在），默认启用；只需 `DEEPSEEK_API_KEY` 有效。
- **LLM 调用失败会怎样？** `_llm_search_guide` 降级（`tools.py:669-675`）：
  候选原样返回 + `score=0.5`，搜索继续；此时 `llm_guidance.injected=true` 但
  事件无 suggestion/regions，`verify` 会提示"无 suggestion"。
- **`--budget` 缩小会影响验证吗？** 若搜索迭代数减少（Agent 按规则动态设
  `n_iterations`），引导事件数相应减少（`N<5` 时可能只有 initial 1 次）；
  建议保持 7200s 以复现主案例规模。
- **重跑结果与主案例不同正常吗？** 正常。LLM 采样不受种子控制，且 v2 搜索路径
  被 LLM 引导重塑；我们验证的是"引导真实影响采样"，而非数值复现。
