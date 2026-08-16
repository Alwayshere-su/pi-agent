# Harness 修改框架（2026GOAI-3 · 路线 A）

> 本文档基于 2026-08 完整扫描报告 + 本人对仓库的逐项复核实证后撰写。
> 所有问题均已定位到「文件:行号」级，所有修复方案均给出**操作步骤 + 验证命令**。
> 核心理念：**JSON 产物是唯一事实源，一切提交文档是派生产物；数据链断则构建失败，不许静默降级。**

---

## 0. 修改哲学（先立规矩，再动手）

| # | 原则 | 落地方式 |
|---|------|---------|
| P1 | **单一事实源** | `hypotheses.json` / `search_h*.json` / `references.bib` 是事实源；SP 清单、解释文档、README 一律由脚本生成，禁止手工改文档绕过数据 |
| P2 | **可重跑、可复现** | 所有修复脚本进 `scripts/` 并入库；生成文档头部自带脚本名+生成日期；重跑前后 diff 可控 |
| P3 | **诚实披露 > 粉饰** | 修不了的数据（如 thermoelectric 6 行日志）就如实降级声明，绝不补造日志/数字 |
| P4 | **fail-fast 哨兵** | 生成脚本内置占位符/零分/引用缺失检测，命中即非零退出，防止坏文档再次入库 |
| P5 | **一次修复，双处验证** | 每次改动：改事实源 → 重跑生成 → 验证命令 → 提交前全量 checklist（见 §6） |

---

## 1. 已核实的现状证据表（操作者必读）

以下全部为本次亲测结果（Python UTF-8 读取，非转述）：

| 问题 | 证据 |
|------|------|
| P0-1：Best Score 全 0 | 6 主题 `hypotheses.json` 的 `best_score` = 0.0 或 null（主案例 `[0.0, 0.0, null, 0.0, null]`）；同目录 `search_h0..4.json` 真实分数 0.433~0.965（主案例 0.6645/0.8286/0.6771/0.9131/0.7343）。两份 SP 清单各 31 处 `0.000` |
| P0-2a：已知工作/增量占位 | 提交版 `路线A_构效关系清单与解释文档/ROUTE_A_SP_LIST.md` L65-66、L87-88、L107-108、L129-130、L149-150 = 「具体结论需人工/LLM 补写」「增量待补写」；**但 `workspace/outputs/ROUTE_A_SP_LIST.md` 同位置已是真实内容** → 提交版是旧生成物，同步即可修复 |
| P0-2b：证据链格式占位 | 解释文档 `ROUTE_A_EXPLANATION.md` L175/193/211/231/251/286/306/328/346 共 9 处「（证据链条目存在，但需清理格式）」→ `build_route_a_docs.py` L223 兜底文案；另 L282/304 统计验证行是 **raw Python dict 原文**（LLM 撰写残留） |
| P0-3：p# 语义错位 | 主案例 bib（71 条）中：`p65`=UiO-66@IL 复合膜（Chemosphere 2022）、`p67`=ZIF-8 氨基 MMM（Sep Purif Technol 2022）——与 hypo_1 声称的「双金属 MOF-74 1:1 最佳」完全无关；`p22`/`p24`/`p147` 语义正确。证据链使用 21 个 p# 键，其中 **`p9` 在 bib 中不存在**；`p116` 与 `p210` 是同一篇论文（MOF@MOF core-shell，2025）两个键 |
| P1-1：CI 125 失实 | `tests/test_core.py`（697 行）与 `tests/test_search_isolation.py`（228 行）全部为 `_test_*` + `main()` 风格 → pytest 不收集；`python tests/test_core.py` 实测报 `ModuleNotFoundError: No module named 'utils'`（根因：ROOT 三层上级计算，文件从 `scripts/test_core_functions/` 移到 `tests/` 后 ROOT 指向仓库父目录）；`ci.yml` L60-61 注释「125 项覆盖 core functions、search isolation」失实 |
| P1-2：日志口径 | thermoelectric `search_log.jsonl` 仅 6 行，但 `gap_report.md`/`paper_summaries.md` 声称 209 篇；主案例 `search_log.jsonl` 208 行 vs `gap_report`「546 papers」；主案例 `paper_summaries.md` 实际 **46 篇**（三处口径互不一致） |
| P2 组 | 方案文档 P56「两次判断直接改变搜索方向」vs REPRODUCIBILITY §3.1「主案例 llm_guidance 为事后回填、未影响采样」；`pyproject.toml` 用 `>=`、缺 chromadb 等、mypy 3.10 vs CI 3.11/3.12；Dockerfile 无 USER/无 VOLUME、装全量 ~3GB；`.api_key` 已被 .gitignore 覆盖；根目录 16 个 `_*.py` |

---

## 2. 工单总览（执行顺序 = 编号顺序）

```
W-1 (P0-1) 分数回填 + 生成器加固
   └─> W-2 (P0-2) 文档再生成 + 占位符哨兵（依赖 W-1 的输出）
W-3 (P0-3) 证据链语义对齐（可独立并行）
W-4 (P1-1) 测试真实化（可独立并行）
W-5 (P1-2) 日志口径统一（可独立并行）
W-6 (P2组) 表述/依赖/Docker/密钥/清理（零散，见 §7）
```

建议批处理：**批次一 = W-1+W-2**（半天，消灭两个 P0 的文档观感）；**批次二 = W-3**（半天，内容级作业）；**批次三 = W-4+W-5+W-6**（半天）。每批次结束跑 §6 门禁。

---

## 3. W-1（P0-1）：Best Score 数据链路修复

### 3.1 根因（已核实）
- `scripts/build_route_a_docs.py` L155 只读 `hypotheses.json.best_score`；
- 搜索分数只写入 `search_h{i}.json.best_score`（含 `hypothesis_index` 字段），**从未回填**到 hypotheses.json；
- 6 个主题无一幸免；`g3test`/`smoke_test` 无 search 文件（best_score=null，但它们不在 THEMES 配置里，不产出文档，可不动）。

### 3.2 操作步骤

**Step 1 — 新增回填脚本 `scripts/backfill_best_scores.py`（入库）**
- 遍历 6 个主题（复用 `build_route_a_docs.py` 的 `THEMES`/`discovery_base` 逻辑，import 它即可）；
- 对每个主题：读 `search_h*.json`，按 `hypothesis_index`（**不要按文件名顺序猜**）建立 `{idx: best_score}` 映射；
- 读 `hypotheses.json`（注意两种结构：主案例为顶层 list；其余为 dict 且键为 `hypotheses`），按索引写回 `best_score`；已有非零值则跳过并报告；
- 输出变更报告（主题 / hypo id / 旧值 → 新值），默认**不覆盖原文件**，写 `best_score` 到副本或先 `git stash` 对比；确认无误后 `--apply` 落盘。

**Step 2 — 加固 `build_route_a_docs.py`**
- `load_hypotheses()` 增加兜底：若 `best_score` 缺失或为 0，尝试从同目录 `search_h{i}.json`（i = 该假设在列表中的下标）读取补上——保证即使回填脚本漏跑，生成器也能自愈；
- 显示层：`best_score` 为 None 时输出 `—`（不再输出 `0.000`）；
- `generate_sp_list()` 结束前做校验：统计 `best_score <= 0` 且存在对应 search 文件的假设数，>0 则 `print('FATAL: ...')` 并 `sys.exit(1)`（P4 哨兵）。

**Step 3 — 重新生成两份清单**
```powershell
python scripts/build_route_a_docs.py --sp-list "workspace/outputs/ROUTE_A_SP_LIST.md"
Copy-Item workspace/outputs/ROUTE_A_SP_LIST.md "路线A_构效关系清单与解释文档/ROUTE_A_SP_LIST.md" -Force
```
（或把默认输出路径改为提交目录，二选一，但必须保证**两份一致**。）

**Step 4 — 验证**
```powershell
Select-String -Path "路线A_构效关系清单与解释文档/ROUTE_A_SP_LIST.md" -Pattern "Best Score" | Select-Object -First 8
```
预期：`0.665 / 0.829 / 0.677 / 0.913 / 0.734 …`，全表无 `0.000`，且与 README「0.665–0.913」、CROSS_THEME_REPORT 表一致。

### 3.3 注意事项
- **perovskite 的 search_h0/h1 分数几乎相同（0.9642×2）不是 bug**（同一假设多次采样的合理结果），不要"顺手修正"；
- thermoelectric search_h3 = 0.3289 是真实低分（该主题诚实记录了负结果），保留原样；
- 回填后 hypotheses.json 会 diff，务必连同提交，让事实源与文档同步。

---

## 4. W-2（P0-2）：占位文本清除 + 哨兵

### 4.1 分两个子问题处理

**W-2a：SP 清单「已知工作/增量贡献」占位（提交版过期）**
- 已核实：`workspace/outputs/ROUTE_A_SP_LIST.md` 的对应行是**真实内容**（如 L65「已有文献确立开放金属位点（OMS）密度与 CO₂ 容量/选择性正相关（p22 钴基 MOF…）」）→ 提交版是旧脚本在 hypotheses.json 被 enrich（`scripts/inject_evidence_chain.py` / `backfill_redline2.py` 时代）**之前**生成的；
- 操作：W-1 的 Step 3 同步即可自动修复；同步后 grep 哨兵确认。

**W-2b：MOFv4 证据链「需清理格式」（生成器正则过窄）**
- 根因：`format_evidence_list`（build_route_a_docs.py L203-226）只认 `^(p\d+|TE\d+|P\d+|r\d+s\d+_[0-9a-f]+)$`；而 mof_e2e_v4 的证据链是「作者 年份 (key) 一句话描述」长串（如 `Marshall 2024 (p35) 突破实验：低RH诱导…`）→ 全部落进 L223 兜底文案；
- 操作：扩展解析规则，对每条 evidence 依次尝试：
  1. 提取括号内引用键 `(p\d+|TE\d+|P\d+|v\d+s\d+_[0-9a-f]+|10\.\d{4,}/\S+)` → 归一化为 `p#/TE#/r#/DOI`；
  2. 提取 `DOI`（mof_e2e_v4 有 `(10.1021/jacs.8b102…)` 形式）→ 保留 DOI 形式；
  3. 均无法解析 → **丢弃该条并在 stderr 计数警告**（不再输出占位句）；
  4. 描述性条目最多保留前 8 个键 + `(+N)` 计数（维持现有截断行为）。

**W-2c：解释文档清理（LLM 撰写残留）**
- `ROUTE_A_EXPLANATION.md` L175 等 9 处「需清理格式」在 W-2b 修复后**重跑生成骨架**即可消失；但 L282/304 的 raw dict（`{'verdict': 'no_improvement', ...}`）说明 `format_mc_summary` 对 mof_e2e_v4 的 `model_comparison` 键名（`delta_r2`/`f_supported` 等）不识别 → 扩展 `format_mc_summary`：兜底解析 `verdict/reason/delta_r2/f_supported` 键，输出「verdict + ΔR²=…」一句话；同时给 `generate_explanation` 增加「输出文本含 `{'` 即报错」的哨兵（raw dict 泄漏检测）。

**W-2d：占位符哨兵（全文档通用）**
在 `generate_sp_list` / `generate_explanation` 末尾统一执行：
```python
BLOCKED = ('待补写', '需人工', '需清理格式', '待生成', 'TBD', 'xxx')
hits = [w for w in BLOCKED if w in text]
if hits: print(f'FATAL: placeholder detected {hits}'); sys.exit(1)
```

### 4.2 验证
```powershell
Select-String -Path "路线A_构效关系清单与解释文档\*.md","workspace\outputs\ROUTE_A_*.md" -Pattern "补写|需清理格式|0.000" | Measure-Object
```
预期：0 命中（Best Score 0.000 已由 W-1 消除）。

---

## 5. W-3（P0-3）：证据链 p# 语义对齐（四层追溯链修复）

> 这是唯一需要**内容级人工作业**的工单，无法纯脚本完成；但脚本可以把工作量从"全人工"降到"只审错位项"。

### 5.1 已核实的事实
- 主案例 bib 71 条；证据链使用 21 个 p# 键，**p9 在 bib 中不存在**（hypo_4 证据链引用）；
- `p116` 与 `p210` 内容重复（同一篇 MOF@MOF core-shell 2025）；
- `p65`/`p67` 是膜分离论文（UiO-66@IL MMM / ZIF-8 MMM），被 hypo_1 当作双金属 MOF-74 证据——**语义错位确认**；
- 扫描报告另指出 p182=p30、p147=p188 重复（本次抽查未覆盖，脚本里一并查）。

### 5.2 操作步骤

**Step 1 — 审计脚本 `scripts/audit_evidence_keys.py`（入库，长期使用）**
对 6 主题分别输出三张表：
1. **缺失表**：证据链使用但 references.bib 没有的键（已知 ≥1：主案例 p9）；
2. **重复表**：bib 中标题（归一化：去大小写/空格/卷页）哈希相同的多键条目（已知：p116/p210；待查 p182/p30、p147/p188）；
3. **语义表**：每条假设的 `expected_relationship` 关键词 × 证据链各键的 bib 标题，两两输出（供 LLM/人工判读）。

**Step 2 — 语义核验（半自动）**
- 用一次 LLM 批量调用（DeepSeek），对语义表逐条输出三级判定：`支持 / 中性 / 错位`，附一句理由；主案例 5 条 × 各 3-8 个键 ≈ 25 项，一次调用可完成；
- 输出 `workspace/audit/evidence_semantic_audit.md`（与现有 audit 目录风格一致）作为提交物。

**Step 3 — 修正（按判定执行）**
- `错位` 且能定位到正确文献 → 替换 key（先在 bib 中查是否已有条目；没有则补条目，DOI 必须真实可查）；
- `错位` 且无法定位（如 CoMn-MOF-74 双金属 1:1 的确切文献）→ **从证据链移除该键**，并同步改写 `known_prior_work` 文案（把「（p65、p67）」字样去掉），绝不保留错误引用；
- `缺失`（p9）→ 补 bib 条目，或从证据链移除；
- `重复` → 合并：保留一个 key，另一 key 删除（全仓库 grep 替换引用处）；
- **改完必须同步三处**：`hypotheses.json`（事实源）→ 重跑 `build_route_a_docs.py`（文档）→ 提交。

**Step 4 — 验证**
```powershell
python scripts/audit_evidence_keys.py   # 预期：缺失=0、重复=0
```
再抽查 3 条四层追溯：`p# → paper_summaries.md → search_log.jsonl → sciverse_skill_log`（REPRODUCIBILITY.md §2 有现成指引）。

### 5.3 时间分配建议
主案例 5 条（21 个键）+ MOFv4 5 条优先；其余 4 主题若审计全绿可不动。若时间不允许逐条人工核验，**最低底线**：修复缺失键 + 重复条目 + 主案例 p65/p67 两处公开被引的错位，其余在 COMPLIANCE.md 中如实披露「证据链语义审计于 2026-08 完成、覆盖主案例与 MOFv4」。

---

## 6. W-4（P1-1）：测试真实化（CI 声明 = 实际收集数）

### 6.1 已核实的根因
- `tests/test_core.py` 与 `tests/test_search_isolation.py` 用 `_test_*` 函数 + `main()` 汇总，pytest 默认不收集（收集规则 `test_*`/`*_test`）；
- 直接运行失败：ROOT 计算「上三级」原本适配 `scripts/test_core_functions/test_core.py`，文件移到 `tests/` 后 ROOT=仓库**父目录** → `import utils.config` 失败（实测复现）；
- `tests/conftest.py` 只有 1 个 fixture，无 sys.path 注入。

### 6.2 操作步骤

**Step 1 — 迁移为 pytest 风格（保留独立运行入口）**
- `test_core.py`：把 10 个 `_test_*` 改为 `test_*`（或保留原名 + 在文件底部加 pytest 可见封装 `def test_all(): failures=[]; for fn in [...]: fn(failures); assert not failures`，推荐后者，改动最小）；
- `test_search_isolation.py` 同理；
- ROOT 改为 `Path(__file__).resolve().parents[2]`（tests/ 上两级 = 仓库根），或更稳：在 `tests/conftest.py` 加
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
  ```
  （`python -m pytest` 本身会把 cwd 放入 sys.path，conftest 注入是双保险，也兼容直接 `pytest` 命令）；
- `main()` 保留：`python tests/test_core.py` 仍可独立跑（ROOT 修正后即恢复）。

**Step 2 — 更新 CI 声明**
```powershell
python -m pytest tests/ --collect-only -q | Select-Object -Last 3
```
拿到真实总数 N（125 + 10 + 若干 search_isolation 用例数）后，把 `ci.yml` L60-61 注释改为：
> 共 N 项，覆盖 config、discovery、extractor、search、parser_engine、core functions、budget resume、search isolation。

**Step 3 — 防再失配（可选但推荐）**
`ci.yml` test 步骤后加一步：
```yaml
- name: Verify test count matches declaration
  run: |
    n=$(python -m pytest tests/ --collect-only -q | tail -1 | grep -oP '^\d+' || echo 0)
    test "$n" -eq N || (echo "CI 收集 $n 项 ≠ 声明 N 项"; exit 1)
```

**Step 4 — 验证**
```powershell
python -m pytest tests/ -q          # 全绿
python tests/test_core.py           # 独立入口也 PASS
```

---

## 7. W-5（P1-2）：检索日志/篇数口径统一

### 7.1 操作步骤
**Step 1 — 审计脚本 `scripts/audit_log_counts.py`（入库）**
对 6 主题输出对照表：`search_log.jsonl 行数 × paper_summaries 实际条目数 × gap_report/文档声称篇数`，三列并排，一眼看出口径差。

**Step 2 — 分主题处置（原则：改文档口径，不改日志）**
- **thermoelectric**：6 行日志 vs 声称 209 篇无法还原 → 在 `gap_report.md`/paper_summaries 头部加 provenance 注记（如「检索日志仅保留 6 条轮次记录（2026-08-02 运行），篇数为汇总期计数，逐条日志不可复现」）；CROSS_THEME_REPORT L312 同步该注记；**禁止补造日志**；
- **主案例**：`gap_report`「10 Gaps, 546 papers」→ 改为可核验口径：「546 篇次检索（search_log 208 行，含批内多结果）+ 46 篇入库摘要（paper_summaries）」或直接引用 paper_summaries 的 46；三处数字（546/208/46）在报告中用一句话说明关系；
- **perovskite**：`paper_summaries.md` 当前已是正常 markdown（71 篇，2026-08-10 生成）——扫描报告提到的 dict 残留是历史版本，确认 git 中当前版本即可，无需处理。

**Step 3 — 验证**：`audit_log_counts.py` 输出与所有文档声称逐项一致；grep 全文搜「546」「209」确认无孤立数字。

---

## 8. W-6（P2 组，零散快修）

| 工单 | 操作 | 验证 |
|------|------|------|
| W-6a | 方案文档 P56「两次判断直接改变搜索方向」→ 按 REPRODUCIBILITY §3.1 降级为「主案例 llm_guidance 为事后回填审计（未影响采样）；仅 mof_e2e_v4 为真实端到端 LLM 引导」 | 两文档口径 grep 一致 |
| W-6b | README 中 F=9.909/p=0.0254 处加脚注：「基于 8 点含 5 个估计点；独立 5 实测点 F 检验 p=0.158 不显著」 | README 通读该段落 |
| W-6c | pyproject.toml 依赖与 requirements.txt 对齐：要么 pyproject 锁 `==` 版本并补 chromadb（若列为运行依赖），要么注明「pyproject 为开发档，运行以 requirements.txt 为准」；`[tool.mypy] python_version = "3.12"` | `pip check` 通过 |
| W-6d | Dockerfile：`COPY requirements-test.txt` + 精简安装（注释说明完整依赖用于开发）；加 `RUN useradd -m appuser` + `USER appuser`；加 `VOLUME ["/app/workspace"]`；ENV 保持 | `docker build` 通过（或至少 dockerfile lint） |
| W-6e | `.api_key` 已 gitignore（已核实）→ 补充动作：`git log --all --oneline -- .api_key` 查历史是否入库；若入库则轮换 4 条密钥并在 docs/COMPLIANCE.md 记录轮换日期 | git log 无 .api_key 记录 |
| W-6f | 根目录 16 个 `_*.py` 移入 `scripts/_archive/`（gitignore 已有 `scripts/_*.py` 规则，直接删或归档均可）；清理 `*.bak-*` 噪音 | `git status` 干净 |

---

## 9. 提交前门禁 Checklist（每批次必跑）

```powershell
# 1. 测试真实化
python -m pytest tests/ -q                      # 全绿
python -m pytest tests/ --collect-only -q | Select-Object -Last 1   # 数字 == ci.yml 声明

# 2. 文档零占位
Select-String -Path "路线A_构效关系清单与解释文档\*.md","workspace\outputs\ROUTE_A_*.md" `
  -Pattern "补写|需清理格式|待生成|0.000|TBD" | Measure-Object      # == 0

# 3. Best Score 一致性（脚本比对 search_h*.json 与文档，W-1 附带的校验输出）

# 4. 证据链审计
python scripts/audit_evidence_keys.py           # 缺失=0 重复=0（语义表另附）

# 5. 仓库整洁
git status                                       # 无 _*.py / 备份 / 临时文件

# 6. 口径一致
python scripts/audit_log_counts.py               # 日志/篇数三列对齐
```

---

## 10. 一句话总结

**三个 P0 的修复路径完全不一样，别混着做：**
- P0-1 是**工程 bug**：回填脚本 + 生成器加固，半天可灭；
- P0-2 是**同步事故**：重新生成 + 哨兵，随 W-1 一起灭；
- P0-3 是**内容债**：必须脚本辅助 + 人工/LLM 判定，留足时间，主案例和 MOFv4 优先。

修完后你的文档将变成「**从 JSON 一键再生成、生成即校验、校验不过不产出**」的闭环，评审交叉核对任何数字都能追溯到文件——这才是复赛最稳的护城河。
