# 合规披露文档

> **项目**：Pi-Agent —— 材料科学文献驱动的构效关系自主发现智能体
> **赛道**：GOAI 算法赛题 · 方向三 · 路线 A（构效关系发现）
> **版本**：v2.2.8（初赛终版）｜**日期**：2026-08-11
>
> 本文档依据赛题要求（`赛题内容.md` 第五节"开源与合规要求"与 `补充.md` 评审标准），完整披露项目的开源计划、商业 API 使用、闭源模型说明、数据来源与授权、第三方依赖等信息。

---

## 一、开源计划

### 1.1 初赛阶段

- 初赛不强制提交代码，但已明确开源边界。
- **开源仓库已于 2026-08 上线并公开**：<https://github.com/Alwayshere-su/pi-agent>（公开仓库，241 文件、16+ commits、MIT 许可），包含：
  - `pi_agent/` + `literature_agent/` + `main.py` 核心代码
  - `requirements.txt` 依赖清单（精确版本锁定）
  - 配置文件说明（`.api_key` 模板、环境变量配置）
  - 随机种子说明（`--seed 42`，`seed_everything()` 固定 random/numpy）
  - 复现步骤（见 README.md 附录 B）
- 探索日志、知识图谱、运行反思等产物以 Markdown/JSON 随仓库开放（API Key 除外）。
- 后续代码/文档变更将持续推送至该仓库（`git push`）。

### 1.2 复赛阶段

- 提供可运行代码仓库，含 README、环境配置、运行说明。
- 提供运行入口（`python main.py --topic "..." --budget 600 --seed 42`）。
- 提供参照系复现脚本（`scripts/baseline_random_search.py`）。
- LLM 采样不保证逐字可复现，但所有结论带论文 ID 证据链，可被领域专家独立核验。

### 1.3 代码许可

- 代码采用 MIT 许可。
- 文档与运行产物以 CC BY 4.0 公开（不含第三方 API 数据）。

---

## 二、商业 API 披露

### 2.1 DeepSeek API（推理 LLM）

| 项 | 说明 |
|----|------|
| **模型** | `deepseek-v4-flash` |
| **调用环节** | LLM 推理与决策（`utils/config.py` 与 `pi_agent/llm.py`）；工具调用由 LLM 驱动 |
| **费用假设** | 600s 单轮约数十次 LLM 调用（含工具调用、推理、报告生成）。仅需 API Key（环境变量 `DEEPSEEK_API_KEY`），按 token 计费 |
| **替代方案** | 任意 OpenAI 兼容端点——设置环境变量 `DEEPSEEK_BASE_URL`（切换服务地址）和 `DEEPSEEK_MODEL`（切换模型名）即可替换为其他兼容服务（如 OpenAI、本地部署的 vLLM 等），无需修改代码 |
| **对可复现性的影响** | LLM 采样存在随机性，不保证逐字可复现。但：① 搜索打分等确定性计算由文献数值确定（`--seed` 固定 random/numpy）；② Agent 结论均附带论文 ID 证据链（p# 引用），任何结论可被领域专家独立核验；③ 路径见 README.md 附录 B |

### 2.2 Sciverse API（文献检索）

| 项 | 说明 |
|----|------|
| **调用环节** | 文献检索（`literature_agent/search.py`），通过 `literature_agent/sciverse_mcp.py` 适配层接入 |
| **接入模式** | **三层自动检测与降级**：REST API 直连（主模式）> 可选 JSON-RPC MCP 适配 > 可选外部 Skill 脚本。任一不可用自动降级；全部不可用时自动回退到纯 arXiv 检索（始终可用） |
| **费用假设** | 需要 `SCIVERSE_API_KEY`（在 sciverse.opendatalab.com 注册获取） |
| **替代方案** | 纯 arXiv 检索（开放获取，零成本，始终可用）——缺失 `SCIVERSE_API_KEY` 或不配置时自动回退 |
| **审计机制** | 每次 Sciverse API 调用均生成标准化审计记录（`workspace/logs/<run-dir>/sciverse_skill_log.jsonl`），包含调用 ID、时间戳、参数 SHA256 哈希、结果摘要、接入模式（`adapter_mode`）等字段。详见 `workspace/outputs/literature_survey/audit_trail.md` |

### 2.3 MinerU（PDF 解析引擎）

| 项 | 说明 |
|----|------|
| **状态** | 开源文档解析引擎（OpenDataLab），官网 <https://mineru.net>；云 API 建议配置 `MINERU_API_KEY`（环境变量或 `.api_key` 文件条目），未配置时 parser 仍会尝试连通公开端点但受网络/配额影响 |
| **调用环节** | PDF 文档解析（`literature_agent/parser.py`） |
| **接入模式** | 三种模式可选：Cloud v1（mineru.net，需 `MINERU_API_KEY` 认证通道）> 本地服务（`MINERU_LOCAL_URL` 环境变量，默认 `http://localhost:8888`，可 docker 部署）> pip 包（magic-pdf/mineru）。默认 `prefer_mineru=True` |
| **替代方案** | 全部不可用时自动回退 markitdown_utils 本地引擎（离线免费，结果完全可复现）。回退原因记录于 `ParsedDocument.parse_engine` 字段。启用方式见 README.md 附录 D |
| **费用/配额** | 云 API 受服务商配额限制；本地部署（localhost:8888）不受配额影响 |

---

## 三、闭源模型说明

| 项 | 说明 |
|----|------|
| **闭源模型** | DeepSeek（`deepseek-v4-flash`）——商业闭源模型 |
| **使用范围** | LLM 推理与决策：假设生成、知识图谱撰写、Gap 识别、报告生成、搜索内引导（v2.0 默认启用） |
| **使用原因** | DeepSeek 提供高性价比的推理能力（OpenAI 兼容接口），适合多轮 Agent 运行（600s 单轮约数十次调用） |
| **替代方案** | 接口兼容 OpenAI API 规范，可替换为任意 OpenAI 兼容端点——设置 `DEEPSEEK_BASE_URL` 与 `DEEPSEEK_MODEL` 环境变量即可切换（如 OpenAI GPT-4o、本地 vLLM 部署的开源模型等），无需修改代码 |
| **迁移成本** | 低——仅需修改环境变量，代码零改动。但不同模型的推理质量与响应速度会有差异，可能影响 Agent 表现 |
| **对可复现性的影响** | 见 2.1 节。核心发现信号（Gap、假设框架）不依赖特定 LLM——可通过证据链独立核验 |

---

## 四、PDF 解析引擎策略

项目采用**双引擎 PDF 解析**策略，兼顾解析质量与离线可复现：

| 引擎 | 类型 | 优先级 | 说明 |
|------|------|--------|------|
| **MinerU** | 推荐引擎（远程/本地服务） | 默认优先 | Cloud v1（mineru.net，配置 `MINERU_API_KEY` 启用）> 本地服务（`http://localhost:8888`，docker 部署）> pip 包。对中文论文和复杂表格/公式解析质量更优。`prefer_mineru=True` 默认启用 |
| **markitdown_utils** | 本地回退引擎（离线） | 自动回退 | 离线免费，结果完全确定可复现。MinerU 全部不可用时自动切换 |

**启用方式**：
- **云 API**：在 <https://mineru.net> 注册获取 `MINERU_API_KEY`，通过环境变量或项目根目录 `.api_key` 文件条目配置（读取逻辑见 `utils/config.py`，与 `SCIVERSE_API_KEY` 同模式）；
- **本地服务**：docker 部署 MinerU 并监听 `localhost:8888`（`MinerUParser.LOCAL_BASE`，可用 `MINERU_LOCAL_URL` 覆盖），健康检查 `GET /health`、解析 `POST /parse`；
- 完整步骤见 README.md「附录 D：MinerU PDF 解析引擎启用指南」。

**回退行为对可复现性的影响**：
- markitdown_utils 本地引擎的解析结果完全确定可复现；
- MinerU 远程引擎受网络状况和 API 配额影响，解析结果可能因服务端更新而细微差异；
- 建议在需要精确复现的实验中使用本地引擎（不设置 `MINERU_API_KEY` 和 `MINERU_LOCAL_URL` 时自动回退）；
- 回退原因始终记录于 `ParsedDocument.parse_engine` 字段，可审计追溯。

---

## 五、数据来源与授权

| 数据来源 | 类型 | 授权状态 | 使用方式 |
|----------|------|----------|----------|
| **arXiv** | 学术预印本 | 开放获取（CC 授权及类似开放许可） | 通过 arXiv API 检索摘要与全文，用于知识抽取与证据索引 |
| **Sciverse** | 科学引文数据库 | 需 API Key（sciverse.opendatalab.com 注册） | **仅取标题+摘要**用于内部调研与假设生成，不对外再分发。调用记录全部留痕审计 |
| **Sci-Base** | 开放数据集 | HuggingFace 开放数据集（opendatalab/Sci-Base，2500 万+篇论文） | 可选接入（`datasets` 包），仅用于文献语料索引 |
| **Materials Project** | 材料结构与性能数据库 | 公开数据库（materialsproject.org） | 氧化物代理热力学数据交叉验证（间接证据），明确标注为间接参考 |
| **OQMD** | 开放量子材料数据库 | 公开数据库（oqmd.org） | 交叉验证查询 |
| **NOMAD** | 计算材料科学数据仓库 | 公开数据库（nomad-lab.eu） | 交叉验证查询 |

**缓存与分发限制**：
- 文献缓存存于 `workspace/data/literature_cache/`（已 `.gitignore` 排除），不进入版本库；
- Sciverse 检索结果不对外再分发；
- 运行产物（知识图谱、Gap 报告等）以 CC BY 4.0 公开，但不含原始第三方 API 数据。

---

## 六、第三方依赖披露

以下为 `requirements.txt` 中所有依赖及其许可证与版本信息：

### LLM API

| 包名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| `openai` | 1.108.1 | DeepSeek API 调用（OpenAI 兼容接口） | Apache 2.0 |

### 文献检索与解析

| 包名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| `requests` | 2.32.5 | HTTP 请求（arXiv API、Sciverse API、REST 调用） | Apache 2.0 |
| `charset-normalizer` | 3.4.6 | 字符编码检测 | MIT |
| `magika` | 1.0.3 | 文件类型检测 | Apache 2.0 |
| `markitdown` | 0.1.7 | 文档转 Markdown（本地解析引擎） | MIT |
| `beautifulsoup4` | 4.12.3 | HTML/XML 解析（markitdown 依赖） | MIT |
| `markdownify` | 1.2.3 | HTML 转 Markdown | MIT |
| `mammoth` | 1.12.0 | DOCX 转 Markdown | BSD-2-Clause |
| `pdfplumber` | 0.11.10 | PDF 文本与表格提取 | MIT |
| `pdfminer.six` | 20260107 | PDF 底层解析 | MIT |

### 数据处理与机器学习

| 包名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| `numpy` | 1.26.4 | 数值计算 | BSD-3-Clause |
| `scipy` | 1.17.1 | 科学计算（`cdist` 用于发现搜索） | BSD-3-Clause |
| `pandas` | 3.0.3 | 数据处理与分析 | BSD-3-Clause |
| `scikit-learn` | 1.9.0 | 机器学习（MLE 超参数拟合、LOOCV 等） | BSD-3-Clause |

### 可选

| 包名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| `datasets` | 4.8.4 | Sci-Base 数据集接入（可选，仅 `--download` 模式需要） | Apache 2.0 |

### 拟实施阶段依赖（已在 requirements.txt 锁定，当前原型及 CI 测试不依赖）

| 包名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| `chromadb` | 1.5.9 | 向量数据库（混合检索，拟实施） | Apache 2.0 |
| `sentence-transformers` | 5.6.1 | Embedding 模型加载（BGE-M3，拟实施） | Apache 2.0 |
| `FlagEmbedding` | 1.4.0 | Reranker 模型（bge-reranker-v2-m3，拟实施） | MIT |

> 所有依赖均为精确版本锁定（`==`），避免上游发布破坏可复现性。版本基于 Python 3.12 / 2026-06 实测环境（通过 `pip freeze` 验证）。

---

## 七、密钥管理

- API Key 存放于项目根目录 `.api_key` 文件（不在仓库内）。
- `.api_key` 已加入 `.gitignore`，不进入版本库。
- 支持通过环境变量 `DEEPSEEK_API_KEY`、`SCIVERSE_API_KEY`、`MINERU_API_KEY`（可选）、`MATERIALS_PROJECT_API_KEY`（可选）提供密钥；`.api_key` 文件内以 `KEY=VALUE` 行记录（见 `utils/config.py::_load_api_key_file`）。
- 提交仓库时不包含任何密钥文件。

---

## 八、已有项目声明

本方案（Pi-Agent）为独立实现，**无基于已有项目继续开发**。所有核心代码（`pi_agent/`、`literature_agent/`、`main.py`、`scripts/`）均为本项目原创开发。

项目涉及的第三方库（见第六节依赖清单）均为标准开源依赖，不构成"基于已有项目"开发。

---

## 九、Sciverse 接入方式如实说明

### 9.1 实际使用的接入模式

本项目以 **REST API 直连为主**（设置 `SCIVERSE_API_KEY`，调用 `https://api.sciverse.space`），实现见 `literature_agent/sciverse_mcp.py` 的 `SciverseSearcherRestAdapter`。当前仓库历史审计记录（`workspace/logs/literature_survey/sciverse_skill_log.jsonl`）的全部调用的 `adapter_mode` 均为 `rest`。

### 9.2 可选扩展接入模式

另有两个可选扩展接入方式，由同一适配层 `create_sciverse_adapter()` 按优先级自动检测：

| 优先级 | 模式 | 实现 | 配置方式 | 说明 |
|--------|------|------|----------|------|
| 1 | **JSON-RPC MCP 适配层** | `SciverseMCPAdapter` | 设置 `SCIVERSE_MCP_URL` 环境变量 | 以自研轻量 JSON-RPC 2.0 HTTP 客户端（`POST /tools/call`）与第三方 MCP server 端点通信。**注意**：这是项目自研的轻量 MCP 客户端适配层，不是官方 MCP SDK，也不是 MCP server——端点需由第三方 MCP server 提供 |
| 2 | **外部 Skill 脚本** | `SciverseSkillAdapter` | 设置 `SCIVERSE_SKILL_PATH` 环境变量 | 通过 `subprocess` 调用本地 Python 脚本，stdin/stdout JSON 通信，脚本需实现约定接口 |
| 3 | **REST API 直连** | `SciverseSearcherRestAdapter` | 设置 `SCIVERSE_API_KEY` 环境变量 | 调用 `https://api.sciverse.space`（**实际使用的主模式**） |

### 9.3 检测与回退机制

- `create_sciverse_adapter()` 依次检测 MCP（1）> Skill（2）> REST（3），任一模式不可用则自动降级；
- 若全部不可用，检索自动回退到纯 arXiv（始终可用）；
- `LiteratureSearcher.available_sources` 会标注当前实际使用的 Sciverse 接入模式（如 `sciverse(rest)`），方便审计追踪。

### 9.4 审计证据链

无论实际使用何种接入模式，每次 Sciverse API 调用均生成标准化审计记录，持久化于 `workspace/logs/<run-dir>/sciverse_skill_log.jsonl`，包含：
- 唯一调用 ID
- 中国标准时间戳
- 调用参数 SHA256 哈希（前 16 位）
- 结果摘要
- 接入模式（`adapter_mode`）

从最终报告中的一条论文引用，可经标题或 DOI 关联到 `paper_summaries.md` 的文献条目，再经 `search_log.jsonl` 的检索查询关联到具体 API 调用记录，形成完整的端到端审计链条。详见 `workspace/outputs/literature_survey/audit_trail.md`。

---

## 十、合规检查清单

对照赛题 `赛题内容.md` 第五节与 `补充.md` 评审标准，逐条自查：

| 合规项 | 要求 | 状态 | 本文档对应章节 |
|--------|------|------|---------------|
| 开源代码说明 | 初赛说明计划与边界；复赛提交可运行代码 | 已说明 | 第一章 |
| 部署/复现说明 | 运行入口、依赖安装、配置方法、随机种子 | 已提供 | README.md 第六章 + 附录 B |
| 商业 API 披露 | 调用环节、费用假设、权限范围、可替代性、可复现性影响 | 已披露 | 第二章 |
| 闭源模型说明 | 使用范围、原因、替代方案、迁移成本、可复现性影响 | 已说明 | 第三章 |
| 数据来源与授权 | 来源、授权状态、使用方式 | 已列出 | 第五章 |
| 第三方依赖披露 | 完整列表、许可证、关键版本 | 已披露 | 第六章 |
| 密钥管理 | 不入库 | 已实施 | 第七章 |
| 已有项目声明 | 来源、贡献范围、创新点、协议兼容性 | 已声明 | 第八章 |
| 证据链可审计 | 结论可追溯至原始文献与 API 调用 | 已实现 | 第九章 + README.md 第五章 |

---

*本文档依据赛题要求撰写，所有信息和声明均为如实披露。复赛阶段将随代码仓库同步更新。*
