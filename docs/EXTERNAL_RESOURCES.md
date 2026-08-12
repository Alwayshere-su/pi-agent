# 外部资源披露清单

> **项目**：Pi-Agent —— 材料科学文献驱动的构效关系自主发现智能体
> **赛道**：GOAI 算法赛题 · 方向三 · 路线 A（构效关系发现）
> **版本**：v2.3.3（初赛终版）｜**日期**：2026-08-12
>
> **用途**：本文档是初赛提交物 #4（外部资源披露），按《参赛手册》2026 年 8 月修订版要求，
> 完整列出项目使用的所有外部公开资源（数据库、API、模型、编译工具）的来源、版本、
> 许可证与替代方案。本文档与代码库中的 `utils/resource_registry.py` 保持同步。

---

## 一、LLM 推理

| 名称 | 来源 | 版本 | 用途 | 许可证 | 必需 | 替代方案 |
|------|------|------|------|--------|:--:|------|
| **DeepSeek API** | https://platform.deepseek.com | deepseek-chat（2026-08） | LLM 推理、假设生成、报告撰写 | 商业 API | 否 | vLLM 本地部署开源模型 |

> 代码位置：`pi_agent/llm.py`（DeepSeekProvider）、`utils/config.py`（DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL）

---

## 二、文献检索

| 名称 | 来源 | 版本 | 用途 | 许可证 | 必需 | 替代方案 |
|------|------|------|------|--------|:--:|------|
| **Sciverse API** | https://sciverse.opendatalab.com | 2026-08 调用时版本 | 跨出版商语义检索（2500 万+篇文献全文定位） | 商业 API（注册获取） | 否 | arXiv API + Semantic Scholar + Crossref |
| **arXiv API** | https://arxiv.org | 实时（2026-08） | 开放获取预印本检索与元数据获取 | CC / free | 是 | —（降级后的主检索源） |
| **Semantic Scholar API** | https://api.semanticscholar.org | 实时（2026-08） | 文献元数据与引用关系检索 | 免费 API | 否 | Crossref API |
| **Sci-Base** | https://huggingface.co/opendatalab/Sci-Base | 2500 万+篇快照版本 | 全文语料（深度解析的开放获取文献） | 数据集许可 | 否 | arXiv + Semantic Scholar 在线检索 |
| **Crossref API** | https://api.crossref.org | 实时（2026-08） | DOI 校验、元数据补全、BibTeX 条目获取 | 免费 API | 否 | — |

> 代码位置：`literature_agent/sciverse_mcp.py`（Sciverse MCP/Skill/REST 适配）、`literature_agent/search.py`（多源检索引擎）、`scripts/build_bib.py`（Crossref DOI→BibTeX）

---

## 三、PDF 解析

| 名称 | 来源 | 版本 | 用途 | 许可证 | 必需 | 替代方案 |
|------|------|------|------|--------|:--:|------|
| **MinerU** | https://mineru.net | Cloud / pip 包（2026-08） | PDF 高精度解析（正文/图表/表格/SI 结构化提取） | 开源 | 否 | markitdown + pdfplumber（本地解析，离线可复现） |

> 代码位置：`literature_agent/parser.py`（MinerUParser，Cloud > Local > pip 三级自动回退）、`utils/config.py`（MINERU_API_KEY）

---

## 四、材料数据库

| 名称 | 来源 | 版本 | 用途 | 许可证 | 必需 | 替代方案 |
|------|------|------|------|--------|:--:|------|
| **Materials Project** | https://materialsproject.org | API 调用时版本（2026-08） | DFT 结构/能量数据交叉验证（路线 A 定量核验参照系） | 开放数据库 | 否 | OQMD / NOMAD |
| **OQMD** | https://oqmd.org | API 调用时版本（2026-08） | 形成能/热力学数据（路线 A 交叉验证第二参照系） | 开放数据库 | 否 | Materials Project |
| **NOMAD** | https://nomad-lab.eu | API 调用时版本（2026-08） | 计算材料科学数据仓库（路线 A 补充验证） | 开放数据库 | 否 | — |
| **hMOF** | 文献构建（2026-08 快照） | 文献快照版本 | MOF 结构-吸附数据（路线 A MOF 体系专项验证） | 公开数据 | 否 | — |

> 代码位置：`literature_agent/discovery.py`（MaterialsProjectValidator，含 MP/OQMD/NOMAD/hMOF 四源交叉验证）
>
> 注：Materials Project 对有机-无机杂化材料（MOF）覆盖为 0，仅能使用氧化物代理做间接热力学参考，为已知系统性能瓶颈。其他可用材料数据库（如 AFLOW 等）未在当前版本中接入，复赛计划扩展。

---

## 五、报告编译工具

| 名称 | 来源 | 版本 | 用途 | 许可证 | 必需 | 替代方案 |
|------|------|------|------|--------|:--:|------|
| **Pandoc** | https://github.com/jgm/pandoc | 3.10.1（vendor/ 单二进制） | Markdown → LaTeX 结构转换 | GPL-2.0-or-later | 是 | 系统级 pandoc 安装 |
| **Tectonic** | https://github.com/tectonic-typesetting/tectonic | 0.17.0（vendor/ 单二进制） | XeTeX 引擎，LaTeX → PDF 编译（TeX Live 轻量替代） | MIT | 是 | 系统级 TeX Live / MiKTeX 安装 |

> 代码位置：`scripts/md2latex.py`（Markdown→LaTeX 转换）、`scripts/compile_report.bat`（一键编译）、`scripts/compile_route_a_pdf.py`（路线 A PDF 编译）、`vendor/README.md`（二进制来源/版本/许可证详情）
>
> 注：pandoc + tectonic 均以单二进制文件存放于 `vendor/` 目录（不入库，`.gitignore` 排除），
> 评审者可从上述 GitHub Releases 页下载或使用系统包管理器安装等效工具。

---

## 六、与代码注册表的对应关系

本文档的每个条目在代码库中有三层对应：

1. **集中注册表**：`utils/resource_registry.py`（13 项 ExternalResource 对象，含 `used_in` 字段追踪使用模块）
2. **调用点注释**：各使用模块的 docstring 中有 `@external: utils/resource_registry.py → <资源名>` 交叉引用
3. **配置文件**：`utils/config.py` 中每个 API Key 变量旁有 `@external` 注释

审计路径：`docs/EXTERNAL_RESOURCES.md`（本文档）→ `utils/resource_registry.py`（代码注册表）→ 各模块 docstring（调用点）→ `utils/config.py`（API Key 配置）

---

*本文档基于 `utils/resource_registry.py` 生成，与方案文档 §5.3 Table 5 一一对应。*
