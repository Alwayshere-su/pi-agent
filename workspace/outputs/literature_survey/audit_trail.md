# Sciverse API 调用审计证据链说明

> 本文档说明 Pi-Agent 项目中 Sciverse 学术文献检索 API 调用的完整审计机制。
> 无论通过 MCP、Skill 还是 REST 直接调用，每条 API 调用均生成标准化审计记录，
> 从最终报告中的论文引用可逐层追溯到原始的 API 请求。

---

## 1. 审计机制概述

### 1.1 设计原则

项目遵循"**调用即审计**"原则：每一次对 Sciverse API 的调用（无论是检索、语义搜索还是全文读取），
都在调用发生时自动生成一条不可篡改的审计记录。审计信息包括：

- **谁**：接入模式（MCP / Skill / REST）
- **何时**：精确到毫秒的中国标准时间戳（UTC+8）
- **做什么**：工具名（`search` / `semantic_search` / `read_content`）
- **参数是什么**：参数 SHA256 哈希 + 脱敏摘要
- **返回了什么**：结果数量和内容摘要

### 1.2 审计日志存储位置

| 日志文件 | 路径 | 记录内容 |
|---------|------|---------|
| Sciverse 调用审计日志 | `workspace/logs/sciverse_skill_log.jsonl` | 每次 Sciverse API 调用的完整审计记录（JSONL 格式，每行一条 JSON 记录） |
| 文献检索日志 | `workspace/data/literature_cache/search_log.jsonl` | 每次多源文献检索的汇总记录（含检索词、数据源、结果数、耗时、Sciverse 接入模式） |
| 论文摘要 | `workspace/outputs/literature_survey/paper_summaries.md` | 检索结果的结构化摘要（含论文标题、DOI、摘要片段） |
| 知识图谱 | `workspace/outputs/literature_survey/knowledge_graph.md` | Agent 自主撰写的材料-性质-数值关系图谱（每条关系带论文引用 p#） |
| Gap 报告 | `workspace/outputs/literature_survey/gap_report.md` | Agent 识别的研究空白（Gap 1-7，带论文引用） |
| 发现报告 | `workspace/outputs/literature_survey/discovery/discovery_report.md` | 阶段二发现结果（假设 + 证据支持） |

---

## 2. `search_log.jsonl` 字段说明

### 2.1 文件格式

每行一条 JSON 记录，对应一次 `LiteratureSearcher.search()` 调用（可能涉及多个数据源的并发检索）。

### 2.2 字段定义

```json
{
    "timestamp": "2026-08-01T14:32:15",
    "query": "MOF materials for CO2 capture",
    "sources": ["arxiv", "sciverse(mcp)"],
    "result_count": 28,
    "elapsed_seconds": 2.34,
    "sciverse_adapter_mode": "mcp"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | 检索时间（格式 `YYYY-MM-DDTHH:MM:SS`，本地时间） |
| `query` | string | 自然语言检索查询文本 |
| `sources` | list[string] | 本次检索使用的数据源列表。Sciverse 源标注了接入模式：`sciverse(mcp)` / `sciverse(skill)` / `sciverse(rest)`。若为 `sciverse(rest)` 表示进行了 REST API 直连调用（即未通过 MCP/Skill） |
| `result_count` | integer | 去重合并后的最终结果数量 |
| `elapsed_seconds` | float | 检索总耗时（秒） |
| `sciverse_adapter_mode` | string | Sciverse 的实际接入模式。可能值为 `"mcp"`、`"skill"` 或 `"rest"`。若 Sciverse 不可用则该字段仍为 `"rest"` 但 `sources` 列表中不含 sciverse 条目 |

### 2.3 新增字段（v2.0）

从 v2.0 起，`search_log.jsonl` 新增 `sciverse_adapter_mode` 字段，
`available_sources` 中 Sciverse 条目标注具体接入模式（如 `sciverse(mcp)`），
便于在审计时直观判断 API 调用路径。

---

## 3. `sciverse_skill_log.jsonl` 字段说明

### 3.1 文件格式

每行一条 JSON 记录，对应一次 Sciverse API 工具调用（`search` / `semantic_search` / `read_content`）。
比 `search_log.jsonl` 更细粒度——一次 `LiteratureSearcher.search()` 可能触发多条此日志。

### 3.2 完整字段定义

```json
{
    "call_id": "search-a1b2c3d4e5f6-1723456789123",
    "timestamp": "2026-08-01T14:32:15.234+08:00",
    "adapter_mode": "mcp",
    "tool_name": "search",
    "parameters_hash": "a1b2c3d4e5f6a7b8",
    "parameters_summary": {
        "query": "MOF materials for CO2 capture",
        "page_size": 30,
        "page": 1
    },
    "result_count": 25,
    "result_summary": "High-Throughput Screening of MOFs for CO2 Capture... | Metal-Organic Frameworks for... (+20 more)",
    "elapsed_ms": 1234.56,
    "error": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `call_id` | string | 唯一调用标识符。格式：`{工具名}-{参数哈希前16位}-{Unix毫秒时间戳}`。该 ID 在所有日志中全局唯一，可用于精确定位单次 API 调用 |
| `timestamp` | string | 调用发生的精确时间（ISO 8601 格式，中国标准时间 UTC+8） |
| `adapter_mode` | string | 接入模式：`"mcp"`（Model Context Protocol）、`"skill"`（本地 Skill 脚本）或 `"rest"`（直接 REST API 调用） |
| `tool_name` | string | 调用的 Sciverse API 工具名。可能值：`"search"`（结构化元数据检索 /meta-search）、`"semantic_search"`（语义块检索 /agentic-search）、`"read_content"`（读取论文全文片段 /content） |
| `parameters_hash` | string | 调用参数的 SHA256 哈希值的前 16 位十六进制字符。用于验证参数完整性——相同参数始终产生相同哈希；此值可用于在不暴露查询内容的场景下证明某次调用使用了特定参数 |
| `parameters_summary` | object | 调用参数的摘要（脱敏后）。敏感值（如 `api_key`、`token`）显示为 `***REDACTED***`；超长字符串截断至 200 字符 |
| `result_count` | integer | 返回的结果数量。对于 `search`：返回的论文条目数；对于 `semantic_search`：返回的语义块数；对于 `read_content`：1（表示成功返回了文本）或 0（失败） |
| `result_summary` | string | 返回结果的简要摘要。对于检索类调用：取前 5 篇论文标题（截断至 80 字符），以 ` | ` 分隔，并在末尾标注 `(+N more)`；对于 `read_content`：返回文本的前 200 字符 |
| `elapsed_ms` | float | 调用耗时（毫秒） |
| `error` | string or null | 若调用失败，记录错误信息；成功则为 `null` |

---

## 4. 端到端审计追溯路径

### 4.1 从结论到原始 API 调用的追溯链

> **历史轮次论文编号（p#）的解析说明（2026-08 补救）**：
> 早期轮次（第 1–9 轮）论文使用 p# 编号（如 p65、p186），其 DOI 映射见：
> - **可靠映射**：`knowledge_graph.md`（与 gap_report 同一编号体系，p#(DOI) 格式）；
> - **逐条对照**：`discovery/pid_evidence_index.md`（gap_report 引用的 40 个 p# 的状态表：
>   25 个已解析 DOI、3 个有 memory 描述待人工补、12 个待人工定位）；
> - **候选检索池（⚠️ 编号体系不同，勿按 p# 直接取用）**：`papers_pid_index.json` /
>   `paper_summaries_pid.md`（自初赛归档恢复的 180 篇历史论文，可用于按标题/主题
>   人工匹配候选，但其中 p# 编号与当前项目不一致，禁止直接对应 DOI）；
> - **主题描述**：`workspace/memory/survey/` 各轮记忆。
> 追溯路径：Gap 中的 p# → `pid_evidence_index.md` → `knowledge_graph.md` / memory
> → `search_log.jsonl` → `sciverse_skill_log.jsonl`。
> 剩余 12 个 p# 暂无 DOI，其引用上下文见索引表，复赛前人工检索补齐；
> 未补齐前禁止凭空填写 DOI（红线：零虚假引用）。

假设你在 `gap_report.md` 中读到：

> **Gap 2（水稳定性机理矛盾）**：文献中关于水蒸气对 CO₂ 吸附的影响存在矛盾——
> 部分研究（p12）认为水分子竞争占据开放金属位点从而降低 CO₂ 容量，
> 另一些研究（p15、p23）报告在低相对湿度下胺功能化 MOF 反而表现出更高的 CO₂ 容量。

可以按以下路径追溯：

```
步骤 1：定位论文信息
  gap_report.md → paper_summaries.md
  搜索 p12 的标题 → 得到标题 "Water Stability in Metal-Organic Frameworks..."
                      DOI: 10.xxxx/yyyy

步骤 2：定位检索日志
  paper_summaries.md → search_log.jsonl
  在 search_log.jsonl 中按时间范围搜索 → 找到对应的检索条目：
  {
    "timestamp": "2026-08-01T14:32:15",
    "query": "water stability mechanism MOF CO2 adsorption humidity",
    "sources": ["arxiv", "sciverse(mcp)"],
    "sciverse_adapter_mode": "mcp"
  }

步骤 3：定位 API 调用记录
  search_log.jsonl → sciverse_skill_log.jsonl
  在 sciverse_skill_log.jsonl 中按 ~14:32 时间窗口搜索 "search" 工具调用 →
  找到匹配的 call_id: "search-a1b2c3d4e5f6-1723456789123"
  验证 parameters_hash 与查询参数摘要

步骤 4：验证结果一致性
  检查 sciverse_skill_log.jsonl 中该调用的 result_summary 是否包含 p12 的论文标题
```

### 4.2 追溯链示意

```
发现报告中的假设/引用 (p12)
    │
    ▼
paper_summaries.md          ← 论文完整信息 (标题、DOI、摘要、来源)
    │
    ▼
search_log.jsonl            ← 检索查询 + 数据源 + 接入模式
    │
    ▼
sciverse_skill_log.jsonl    ← 原始 API 调用 (call_id、参数哈希、耗时、结果摘要)
    │
    ▼
审计确认：该论文确实是在某次特定参数下的 Sciverse MCP 调用中返回的
```

### 4.3 哈希验证

若需验证某次调用的参数是否与记录一致（防止事后篡改），可使用 `parameters_hash` 进行验证：

```python
import hashlib
import json

# 审计记录中记录的参数
params = {"query": "water stability MOF", "page_size": 30, "page": 1}
# 审计记录中记录的哈希
recorded_hash = "a1b2c3d4e5f6a7b8"

# 计算验证
computed_hash = hashlib.sha256(
    json.dumps(params, sort_keys=True, ensure_ascii=False).encode()
).hexdigest()[:16]

assert computed_hash == recorded_hash, "参数哈希不匹配——记录可能被篡改"
```

---

## 5. 接入模式对审计的影响

| 接入模式 | 审计特点 |
|---------|---------|
| **MCP** | 每次 MCP `tools/call` 请求自动附带标准化元数据。MCP 端点（若支持）可能额外提供服务端审计日志，形成客户端-服务端双重审计 |
| **Skill** | Skill 脚本的 stdin/stdout 通信在进程级别可捕获，审计日志由适配器在进程内生成并立即持久化到 `sciverse_skill_log.jsonl` |
| **REST** | 与现有 `SciverseSearcher` 完全兼容。审计日志同样由适配器层生成，记录到 `sciverse_skill_log.jsonl`。REST 模式下 `adapter_mode` 字段为 `"rest"`，便于区分调用路径 |

**核心保证**：无论使用何种接入模式，审计日志的字段结构和记录时机完全一致。
切换接入模式不会丢失任何审计信息。

---

## 6. 日志完整性保障

### 6.1 即时持久化

每条审计记录在 API 调用返回时**立即**以追加模式写入 JSONL 文件，
而非缓存在内存中批量写入。这确保即使程序异常终止，已完成的调用记录也不会丢失。

### 6.2 写入失败容错

磁盘写入失败（如磁盘满、权限不足）不会阻断主流程——审计日志写入失败时静默跳过，
保障核心检索功能不受影响。此时会在控制台输出警告（若日志级别允许）。

### 6.3 日志轮转建议

JSONL 格式天然支持追加和按时间范围过滤。建议在多次运行后定期归档旧日志：

```bash
# 按日期归档
mv workspace/logs/sciverse_skill_log.jsonl \
   workspace/logs/archive/sciverse_skill_log_2026-08.jsonl
```

---

*本文件用于说明 Pi-Agent 的 Sciverse API 审计证据链机制。*
*更新日期：2026-08-02*
