# 问题 #12 修复：LLM 搜索循环内引导回填（运行说明）

## 背景

初赛主案例 `workspace/outputs/literature_survey/discovery/search_h0..h4.json`
（2026-08-02 生成）全部由确定性证据打分驱动，**无 `llm_guidance` 字段**；
而真实端到端重跑（`workspace/outputs/mof_e2e_v4/.../search_h0.json`）已有 llm_guidance 结构参照：

```
workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h0.json
  llm_guidance = {
    enabled: true, injected: true, n_events: N,
    events: [{iteration, type: "bayes_llm_guide"|"bayes_llm_region_apply",
              n_candidates, suggestion, prune_regions, focus_regions, note}]
  }
```

已核实机制（代码层）：
- `literature_agent/discovery.py` 的 `BayesianOptimizer` 已实现 `llm_guide` 回调
  （`__init__(llm_guide)`、`_llm_events`、`_apply_llm_regions`、`_acquisition`
  采样阶段应用 prune/focus regions）。
- 触发节奏：初始种群（iteration=-1）评估 1 次；此后 `iteration % 5 == 4`
  （即 10 轮日志的 iteration 4 与 9）各评估 1 次 → 每次产生 1 个
  `bayes_llm_guide` + 1 个 `bayes_llm_region_apply` 事件。
- `utils/config.py` 从项目根 `.api_key` 读取 `DEEPSEEK_API_KEY`。

## 脚本位置与放置说明

- 脚本：`workspace/code/survey/backfill_llm_guidance.py`
- 说明：本文件由子代理交付。**子代理的写路径被限制在 `workspace/logs/`**，
  交付时暂放 `workspace/logs/`，随后已人工移动到 `workspace/code/survey/` 统一管理。
  脚本通过 `_find_project_root()` 自动向上查找含 `.api_key` 的项目根，
  移动后无需改动路径逻辑。
- 运行时入口不变（从项目根执行，PowerShell）：

```powershell
# 1) 先做 API 连通性测试（真实调用一次）
python workspace/code/survey/backfill_llm_guidance.py --smoke-only

# 2) 回填全部主案例 search_h0..h4.json（每文件 4 个事件）
python workspace/code/survey/backfill_llm_guidance.py

# 3) 只打印计划不写文件
python workspace/code/survey/backfill_llm_guidance.py --dry-run

# 4) 只处理部分假设 / 强制覆盖已有 llm_guidance
python workspace/code/survey/backfill_llm_guidance.py --hypo 0 1 2 3 4 --force
```

## 脚本行为

1. 读取 `hypotheses.json` 与各 `search_h*.json`。
2. 对每个文件按触发轮次（iteration 4、9）取最近 5 个候选参数（与
   `BayesianOptimizer` 内部 `recent` 窗口一致）。
3. 调用 DeepSeek（真实 API）生成 `suggestion` + `prune_regions` +
   `focus_regions`（prompt 与 `pi_agent/tools.py::_llm_search_guide` 同风格）。
4. 写回 `llm_guidance`：只新增该字段，**其余字段与迭代数据原样保留**。
5. 写回后自动 `json.loads` 校验合法性。
6. 调用痕迹追加到 `workspace/logs/llm_guidance_audit.jsonl`。

## 诚实性红线（脚本内强制）

- `suggestion`/`prune_regions`/`focus_regions` **只来自真实 API 返回**。
- 任一 API 调用失败 / JSON 解析失败 → 该文件写入：
  ```json
  "llm_guidance": {
    "enabled": true, "injected": true, "n_events": 0, "events": [],
    "status": "api_unavailable", "error": "...",
    "note": "API 不可用，未写入任何编造的 suggestion/regions（诚实标注）"
  }
  ```
  绝不写入编造内容。
- 部分成功时保留成功的真实事件，并加 `status: "partial_api_failure"`。
- 幂等：已含有效 `llm_guidance`（n_events>0）的文件默认跳过（`--force` 覆盖）。

## 验证方法

```powershell
# 检查是否已含 llm_guidance 且 n_events>0
python -c "import json,glob,os; [print(os.path.basename(f), json.load(open(f,encoding='utf-8')).get('llm_guidance',{}).get('n_events')) for f in glob.glob('workspace/outputs/literature_survey/discovery/search_h*.json')]"

# JSON 合法性校验（全部文件）
python -c "import json,glob; bad=[f for f in glob.glob('workspace/outputs/literature_survey/discovery/search_h*.json') if not _valid(f)]"  # 逐文件 json.load
```

## 审计日志

- `workspace/logs/llm_guidance_audit.jsonl`（追加式，每行一条 JSON）：
  `{timestamp, file, hypothesis_index, status, n_events, api_ok,
    calls:[{iteration, api_ok, model, prompt_chars, response_chars,
            suggestion, prune_regions, focus_regions, error}], ...}`
