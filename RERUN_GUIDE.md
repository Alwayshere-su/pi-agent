# Pi-Agent 复赛重跑指南

> 本指南用于在准备好 API Key 后一键重跑主案例，产出以下缺失内容：
> - #7：主案例 `survey_report.md`
> - #8：符号回归实证
> - #10：路线 A "统计优于前人"的定量验证
> - #12：LLM 搜索循环内引导的审计记录
> - #13：知识图谱量化建模数值表

---

## 目录

1. [前置检查](#1-前置检查)
2. [主案例全量重跑（产出 #10 + #12 + #7）](#2-主案例全量重跑产出-10--12--7)
3. [模型对比验证（产出 #10 统计优于前人证据）](#3-模型对比验证产出-10-统计优于前人证据)
4. [符号回归验证（产出 #8）](#4-符号回归验证产出-8)
5. [知识图谱定量数值表补充（#13）](#5-知识图谱定量数值表补充13)
6. [补充主案例 survey_report.md 的备选方案](#6-补充主案例-survey_reportmd-的备选方案)
7. [产出检查清单](#7-产出检查清单)
8. [故障排查](#8-故障排查)

---

## 1. 前置检查

### 1.1 API Key 状态检查

```bash
python demo.py
```

确认以下输出：
- `[PASS] API Key 配置检查`：DeepSeek + Sciverse 均显示 [OK]
- 如果显示 `[MISSING]`，请在项目根目录 `.api_key` 文件中补全：

```
DEEPSEEK_API_KEY=sk-your-deepseek-key
SCIVERSE_API_KEY=your-sciverse-key
MATERIALS_PROJECT_API_KEY=your-mp-key
MINERU_API_KEY=your-mineru-key   # 可选：MinerU 云 API（见 README 附录 D）
```

### 1.2 磁盘空间检查

```bash
# 检查 workspace/ 可用空间（重跑预计需要 ~2GB）
du -sh workspace/
```

### 1.3 依赖检查

```bash
pip install -r requirements.txt
```

---

## 2. 主案例全量重跑（产出 #10 + #12 + #7）

> 使用 v2.0 代码，LLM 搜索引导默认启用。重跑主题与主案例一致（MOF materials for CO2 capture）。

```bash
python main.py \
  --topic "MOF materials for CO2 capture" \
  --run-dir mof_rerun_v2 \
  --budget 7200 \
  --fresh \
  --seed 42
```

**参数说明：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `--topic` | MOF materials for CO2 capture | 与主案例一致的主题 |
| `--run-dir` | mof_rerun_v2 | 独立运行目录，不覆盖旧产物 |
| `--budget` | 7200 | 2 小时预算，确保阶段一+阶段二完整运行 |
| `--fresh` | | 从头开始，不依赖旧 checkpoint |
| `--seed` | 42 | 固定随机种子，确定性计算部分可复现 |

**预期产出路径（`workspace/outputs/mof_rerun_v2/literature_survey/`）：**

| 文件 | 说明 |
|------|------|
| `survey_report.md` | 最终调研报告（#7 解体） |
| `gap_report.md` | Research Gap 分析 |
| `knowledge_graph.md` | 知识图谱（含量化建模数值表，#13） |
| `paper_summaries.md` | 论文摘要集 |
| `audit_trail.md` | 审计证据链 |
| `discovery/search_h*.json` | 各假设的搜索日志（含 `llm_guidance` 字段，#12） |
| `discovery/hypotheses.json` | 假设定义与证据链 |
| `discovery/discovery_report.md` | 发现报告 |
| `discovery/discovery_report.json` | 发现报告（结构化） |
| `discovery/model_comparison_*.md` | 模型对比结果（#10） |
| `discovery/symbolic_*.md` | 符号回归结果（#8） |

### 2.1 验证 LLM 搜索引导已启用（#12）

```bash
# 检查 search_h0.json 是否含 llm_guidance 字段
python -c "
import json
with open('workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h0.json') as f:
    data = json.load(f)
print('llm_guidance' in data)
print('search_method:', data.get('search_method'))
"
```

预期输出：
```
True
search_method: bayesian
```

如果 `llm_guidance` 字段缺失，说明 LLM API 调用失败（检查 DeepSeek API Key 和网络连接）。

### 2.2 验证阶段二全覆盖

```bash
# 检查所有假设的搜索日志
ls -la workspace/outputs/mof_rerun_v2/literature_survey/discovery/search_h*.json
```

预期至少 5 个 `search_h*.json` 文件（对应 5 条假设）。

---

## 3. 模型对比验证（产出 #10 统计优于前人证据）

> 在重跑完成后，对每条假设执行"候选模型 vs 经典模型"对比。

```bash
cd D:/MMLL/4.competition/2026GOAI-3

python -c "
import json
from pathlib import Path
from literature_agent.classical_models import run_model_comparison

run_dir = 'workspace/outputs/mof_rerun_v2/literature_survey'
hypotheses_path = Path(run_dir) / 'discovery' / 'hypotheses.json'

with open(hypotheses_path) as f:
    hypotheses = json.load(f)

for h in hypotheses:
    print(f\"Running model comparison for {h['id']}...\")
    try:
        result = run_model_comparison(h, run_dir=run_dir)
        out_path = Path(run_dir) / 'discovery' / f'model_comparison_{h[\"id\"]}.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f\"  -> Saved to {out_path}\")
    except Exception as e:
        print(f\"  [SKIP] {h['id']}: {e}\")
"
```

**说明：**
- `run_model_comparison` 对每条假设的回归模型与经典模型（Slack Model、Vegard's Law）做统计对比（R-squared、MSE、嵌套 F 检验）
- 如果某假设的数据点不足（< 5 个），该假设会自动跳过
- 输出文件：`discovery/model_comparison_hypo_*.json`

**验证"统计优于前人"标准：**

```bash
python -c "
import json
from pathlib import Path

discovery_dir = Path('workspace/outputs/mof_rerun_v2/literature_survey/discovery')

for f in sorted(discovery_dir.glob('model_comparison_*.json')):
    with open(f) as fp:
        data = json.load(fp)
    print(f'\\n{f.name}:')
    print(f'  Candidate R²:  {data.get(\"candidate_r2\", \"N/A\")}')
    print(f'  Classical R²: {data.get(\"classical_r2\", \"N/A\")}')
    print(f'  F-test p:     {data.get(\"f_test_p\", \"N/A\")}')
    print(f'  Winner:       {data.get(\"winner\", \"N/A\")}')
"
```

预期至少有一条假设的候选模型 R-squared 高于经典模型，且嵌套 F 检验 p < 0.05。

---

## 4. 符号回归验证（产出 #8）

```bash
cd D:/MMLL/4.competition/2026GOAI-3

python -c "
import json
from pathlib import Path
from literature_agent.symbolic_regression import run_symbolic_regression2 as run_sr

run_dir = 'workspace/outputs/mof_rerun_v2/literature_survey'
hypotheses_path = Path(run_dir) / 'discovery' / 'hypotheses.json'
kg_path = Path(run_dir) / 'knowledge_graph.md'

with open(hypotheses_path) as f:
    hypotheses = json.load(f)

for h in hypotheses:
    hypothesis_id = h['id']
    print(f'Running symbolic regression for {hypothesis_id}...')
    try:
        result = run_sr(hypothesis_id=hypothesis_id,
                        hypotheses=hypotheses,
                        kg_path=str(kg_path),
                        run_dir=run_dir)
        out_path = Path(run_dir) / 'discovery' / f'symbolic_{hypothesis_id}.md'
        with open(out_path, 'w') as f:
            f.write(result if isinstance(result, str) else json.dumps(result, indent=2))
        print(f'  -> Saved to {out_path}')
    except Exception as e:
        print(f'  [SKIP] {hypothesis_id}: {e}')
"
```

**注意：** 符号回归对数据量有基本要求（至少 8-10 个 (x,y) 数据点）。如果某假设的 KG 提取点不足，该假设会自动跳过。

---

## 5. 知识图谱定量数值表补充（#13）

> `prompts.py` 规则 7 已要求 Agent 在 knowledge_graph.md 中生成量化建模数值表。重跑时 Agent 应自动遵守此规则，生成结构化的 (x,y) 表。
> 
> 如果重跑后仍未生成，或需要提取更多数值用于回归核验：

```bash
cd D:/MMLL/4.competition/2026GOAI-3

# 方案 A：用 LLM 引导重新提取（推荐，需 API Key）
python -c "
from literature_agent.extractor import structured_te_extraction

kg_path = 'workspace/outputs/mof_rerun_v2/literature_survey/knowledge_graph.md'
structured_te_extraction(kg_path, run_dir='workspace/outputs/mof_rerun_v2/literature_survey')
"

# 方案 B：用脚本从现有产物提取并验证（读取 quantitative_pairs.json 数据池 → 回归报告）
python scripts/run_nico5_validation.py
```

**手工补充模板（如 Agent 未自动生成）：**

在 knowledge_graph.md 的"四、核心数值表"之后，补充如下格式的表格：

```markdown
### 定量建模数据集（供符号回归与线性/二次回归核验用）

#### 数据集 1：双金属 MOF-74 金属比例 → CO2 容量
| 体系 | 金属比例 (x) | CO2 容量 (mmol/g) | 来源 |
|------|-------------|-------------------|------|
| CoMn-MOF-74 | 0.5 (1:1) | — | p65 |
| NiCo-MOF-74 | 0.37 | 8.30 | p62 |
| ... | ... | ... | ... |

#### 数据集 2：金属 d 电子数 → Qst
| 金属 | d 电子数 | Qst (kJ/mol) | 来源 |
|------|---------|-------------|------|
| Mg | 0 | 47 | p20 |
| Fe | 6 | 36 | 历史 |
| ... | ... | ... | ... |
```

---

## 6. 补充主案例 survey_report.md 的备选方案

### 方案 A：从重跑产物复制（推荐）

如果 v2.0 重跑成功，`mof_rerun_v2` 的主题与主案例一致，可直接使用：

```bash
# 复制 survey_report.md 到主案例目录
cp workspace/outputs/mof_rerun_v2/literature_survey/survey_report.md \
   workspace/outputs/literature_survey/survey_report.md
```

> 注意：需在文件头部添加注释说明来源（v2.0 重跑产物），并更新路径引用。

### 方案 B：软链接

如果允许，创建软链接以减少文件重复：

```bash
# Windows (需管理员权限)
mklink workspace\outputs\literature_survey\survey_report.md \
       workspace\outputs\mof_rerun_v2\literature_survey\survey_report.md

# Linux/Mac
ln -sf workspace/outputs/mof_rerun_v2/literature_survey/survey_report.md \
       workspace/outputs/literature_survey/survey_report.md
```

### 方案 C：基于已有文件手动生成

如果 API Key 不可用，当前主案例已有 `gap_report.md`、`knowledge_graph.md`、`paper_summaries.md`，可基于这些文件人工整理 survey_report.md（见本指南附录）。

---

## 7. 产出检查清单

重跑完成后，逐项检查以下文件存在且非空：

### 阶段一：文献调研

- [ ] `workspace/outputs/mof_rerun_v2/literature_survey/survey_report.md`（含摘要、引言、材料分类、方法学评述、Gap 概览、参考文献）
- [ ] `workspace/outputs/mof_rerun_v2/literature_survey/gap_report.md`（含 Gap 编号、严重程度、置信度、证据、验证方案）
- [ ] `workspace/outputs/mof_rerun_v2/literature_survey/knowledge_graph.md`（含材料/性质/构效关系/核心数值表/量化建模数据集）
- [ ] `workspace/outputs/mof_rerun_v2/literature_survey/paper_summaries.md`（含论文标题、DOI、摘要片段）
- [ ] `workspace/outputs/mof_rerun_v2/literature_survey/audit_trail.md`（审计证据链）

### 阶段二：构效关系发现

- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/hypotheses.json`（5 条假设完整定义）
- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/discovery_report.md`
- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/discovery_report.json`
- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h0.json`（含 `llm_guidance` 字段，#12 真实端到端证据）
- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h1.json`（含 `llm_guidance` 字段）
- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h2.json`（含 `llm_guidance` 字段）
- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h3.json`（含 `llm_guidance` 字段）
- [ ] `workspace/outputs/mof_e2e_v4/literature_survey/discovery/search_h4.json`（含 `llm_guidance` 字段）

> ⚠️ 红线提示：`mof_rerun_v2` 的 `search_h*.json` 中 `llm_guidance` 来源未核实
> （trajectory 无 LLM 调用痕迹，已加 `source_note` 标注），**不得**作为"LLM 引导真实生效"
> 的证据引用；唯一真实端到端证据是 `mof_e2e_v4`。

### 定量验证（#10 + #8）

- [ ] `workspace/outputs/mof_rerun_v2/literature_survey/discovery/model_comparison_*.json`（至少 1 个，#10）
- [ ] `workspace/outputs/mof_rerun_v2/literature_survey/discovery/symbolic_*.md`（至少 1 个，#8）

### 主案例补全（#7）

- [ ] `workspace/outputs/literature_survey/survey_report.md`（来源：mof_rerun_v2 产物或基于已有文件人工撰写）

---

## 8. 故障排查

### 8.1 错误：`LLM API 不可用`

**症状：** 日志出现 `LLM API call failed` 或 `DeepSeek API Key not configured`

**解决：**
1. 检查 `.api_key` 文件中的 `DEEPSEEK_API_KEY` 是否正确
2. 测试网络连接：`curl -H "Authorization: Bearer $API_KEY" https://api.deepseek.com/v1/models`
3. 如果 DeepSeek 彻底不可用，降级方案：Agent 仍可运行（确定性搜索 + 启发式打分），但 `llm_guidance` 不会写入 `search_h*.json`

### 8.2 错误：`Sciverse API 不可用`

**症状：** 检索结果仅有 arXiv 来源，Sciverse 检索返回空

**解决：**
1. 检查 `.api_key` 文件中的 `SCIVERSE_API_KEY` 是否正确
2. Agent 会自动降级到 arXiv + Crossref 免费源，仍可完成调研
3. 可以通过设置更高的 `--budget` 补偿检索覆盖度

### 8.3 错误：`阶段二候选点不足`

**症状：** `search_h*.json` 中 `iterations` < 5

**解决：**
1. 增加 `--budget` 到 14400（4 小时）: `--budget 14400`
2. 或者手动补检索文献（阶段一已有 ~50 篇，阶段二依赖阶段一的 KG 内容）

### 8.4 错误：`MinerU PDF 解析失败`

**症状：** paper_summaries 中某论文摘要为 `[MinerU parse failed]`

**解决：**
- MinerU 是外部云服务，偶发不可用是正常的
- Agent 会自动回退到 arXiv/markitdown_utils 解析
- 如果大量论文解析失败（>20%），检查网络连接
- 启用稳定的 MinerU 通道（二选一）：
  - 云 API：在 `.api_key` 中配置 `MINERU_API_KEY=mineru-xxx`（注册 mineru.net），或设置环境变量 `MINERU_API_KEY`；
  - 本地部署：`docker run -d --name mineru-local -p 8888:8888 <官方镜像>` 并监听 `http://localhost:8888`（具体镜像以 MinerU 官方仓库 github.com/opendatalab/MinerU 发布说明为准）。
  - 完整启用说明见 README 附录 D

---

## 附录：无需 API Key 即可执行的验证

以下脚本不调用 LLM API，可在任何时候运行以验证项目代码正确性：

```bash
# 1. 功能自测（不依赖 LLM）
python demo.py

# 2. 经典模型自测
python -c "
from literature_agent.classical_models import test_slack_model, test_vegard
print('Slack Model test:', test_slack_model())
print('Vegard test:', test_vegard())
"

# 3. 符号回归自测
python -c "
from literature_agent.symbolic_regression import test_symbolic_regression1
print(test_symbolic_regression1())
"

# 4. 配置状态报告
python -c "
from utils.config import print_config_status
print_config_status()
"
```

---

*本指南最后更新时间：2026-08-03*
*适用于 Pi-Agent v2.0 代码库*
