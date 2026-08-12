# -*- coding: utf-8 -*-
"""
外部资源注册表（来源与版本）
=============================

对应《GOAI 赛道三参赛手册》2026 年 8 月修订版要求：
  - 外部资源须注明来源与版本，且在代码中体现
  - 所用数据库不限于推荐列表，任何公开可获取的科学数据库均可使用（第 36 条）

本文件集中声明初赛提交物涉及的所有外部资源，与方案文档 5.3 节 Table 5 一一对应。
评审可通过此文件一次性核对所有外部依赖的来源、版本与用途。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExternalResource:
    """外部资源声明。"""
    name: str                              # 名称
    category: str                          # LLM | 检索 | PDF解析 | 文献数据 | 文献元数据 | 材料数据库 | 编译工具
    url: str                               # 来源
    version: str                           # 版本/日期（初赛提交时状态）
    purpose: str                           # 用途
    license_: str                          # 许可证/协议
    required: bool                         # 是否必需（False 表示可降级/替代）
    fallback: Optional[str] = None         # 不可用时的替代方案
    used_in: str = ""                      # 使用该资源的代码模块（逗号分隔），用于代码→注册表的交叉引用


# ── 初赛提交时的外部资源清单（12 项） ──────────────────────────────

RESOURCES: list[ExternalResource] = [
    # ── LLM 推理 ──
    ExternalResource(
        name="DeepSeek API",
        category="LLM",
        url="https://platform.deepseek.com",
        version="deepseek-chat (2026-08 调用时版本)",
        purpose="LLM 推理、假设生成、报告撰写",
        license_="商业 API",
        required=False,
        fallback="vLLM 本地部署开源模型（改 DEEPSEEK_BASE_URL 即可）",
        used_in="pi_agent/llm.py, utils/config.py",
    ),

    # ── 检索 ──
    ExternalResource(
        name="Sciverse API",
        category="检索",
        url="https://sciverse.opendatalab.com",
        version="2026-08 调用时版本",
        purpose="跨出版商语义检索（2500 万+篇文献全文定位）",
        license_="商业 API（注册获取）",
        required=False,
        fallback="arXiv API + Semantic Scholar + Crossref",
        used_in="literature_agent/sciverse_mcp.py, literature_agent/search.py, utils/config.py",
    ),

    # ── PDF 解析 ──
    ExternalResource(
        name="MinerU",
        category="PDF解析",
        url="https://mineru.net",
        version="Cloud / pip 包（按需，2026-08）",
        purpose="PDF 高精度解析（正文/图表/表格/SI 结构化提取）",
        license_="开源",
        required=False,
        fallback="markitdown + pdfplumber（本地解析，无需 API Key）",
        used_in="literature_agent/parser.py, utils/config.py",
    ),

    # ── 文献数据 ──
    ExternalResource(
        name="arXiv API",
        category="文献数据",
        url="https://arxiv.org",
        version="实时（2026-08）",
        purpose="开放获取预印本检索与元数据获取",
        license_="CC / free",
        required=True,
        fallback=None,  # 降级后的主要检索源
        used_in="literature_agent/search.py",
    ),

    ExternalResource(
        name="Semantic Scholar API",
        category="文献数据",
        url="https://api.semanticscholar.org",
        version="实时（2026-08）",
        purpose="文献元数据与引用关系检索",
        license_="免费 API",
        required=False,
        fallback="Crossref API",
        used_in="literature_agent/search.py",
    ),

    ExternalResource(
        name="Sci-Base",
        category="文献数据",
        url="https://huggingface.co/opendatalab/Sci-Base",
        version="2500 万+篇快照版本",
        purpose="全文语料（深度解析的开放获取文献）",
        license_="数据集许可",
        required=False,
        fallback="arXiv + Semantic Scholar 在线检索",
        used_in="literature_agent/search.py",
    ),

    ExternalResource(
        name="Crossref API",
        category="文献元数据",
        url="https://api.crossref.org",
        version="实时（2026-08）",
        purpose="DOI 校验、元数据补全、BibTeX 条目获取",
        license_="免费 API",
        required=False,
        fallback=None,
        used_in="literature_agent/search.py, scripts/build_bib.py",
    ),

    # ── 材料数据库 ──
    ExternalResource(
        name="Materials Project",
        category="材料数据库",
        url="https://materialsproject.org",
        version="API 调用时版本（2026-08）",
        purpose="DFT 结构/能量数据交叉验证（路线 A 定量核验参照系）",
        license_="开放数据库",
        required=False,
        fallback="OQMD / NOMAD",
        used_in="literature_agent/discovery.py, utils/config.py",
    ),

    ExternalResource(
        name="OQMD",
        category="材料数据库",
        url="https://oqmd.org",
        version="API 调用时版本（2026-08）",
        purpose="形成能/热力学数据（路线 A 交叉验证第二参照系）",
        license_="开放数据库",
        required=False,
        fallback="Materials Project",
        used_in="literature_agent/discovery.py",
    ),

    ExternalResource(
        name="NOMAD",
        category="材料数据库",
        url="https://nomad-lab.eu",
        version="API 调用时版本（2026-08）",
        purpose="计算材料科学数据仓库（路线 A 补充验证）",
        license_="开放数据库",
        required=False,
        fallback=None,
        used_in="literature_agent/discovery.py",
    ),

    ExternalResource(
        name="hMOF",
        category="材料数据库",
        url="（文献构建，2026-08 快照版本）",
        version="文献快照版本",
        purpose="MOF 结构-吸附数据（路线 A MOF 体系专项验证）",
        license_="公开数据",
        required=False,
        fallback=None,
        used_in="literature_agent/discovery.py",
    ),

    # ── 报告编译 ──
    ExternalResource(
        name="Pandoc",
        category="编译工具",
        url="https://github.com/jgm/pandoc",
        version="3.10.1 (vendor/, 2026-08)",
        purpose="Markdown → LaTeX 结构转换（调研报告/路线 A 文档编译）",
        license_="GPL-2.0-or-later",
        required=True,
        fallback="系统级 pandoc 安装",
        used_in="scripts/md2latex.py, scripts/compile_route_a_pdf.py",
    ),

    ExternalResource(
        name="Tectonic",
        category="编译工具",
        url="https://github.com/tectonic-typesetting/tectonic",
        version="0.17.0 (vendor/, 2026-08)",
        purpose="XeTeX 引擎，LaTeX → PDF 编译（TeX Live 的轻量替代）",
        license_="MIT",
        required=True,
        fallback="系统级 TeX Live / MiKTeX 安装",
        used_in="scripts/compile_report.bat, scripts/compile_route_a_pdf.py",
    ),
]


# ── 便捷查询 ──

def get_by_name(name: str) -> ExternalResource | None:
    """按名称查找资源。"""
    for r in RESOURCES:
        if r.name == name:
            return r
    return None


def get_by_category(category: str) -> list[ExternalResource]:
    """按类别筛选资源。"""
    return [r for r in RESOURCES if r.category == category]


def get_required_resources() -> list[ExternalResource]:
    """返回所有必需资源（required=True）。"""
    return [r for r in RESOURCES if r.required]


def format_summary() -> str:
    """生成人类可读的资源摘要。"""
    lines = ["外部资源注册表摘要", "=" * 40]
    for r in RESOURCES:
        status = "必需" if r.required else "可选"
        lines.append(f"  [{r.category}] {r.name} — {status}")
        lines.append(f"    来源: {r.url}")
        lines.append(f"    版本: {r.version}")
        lines.append(f"    用途: {r.purpose}")
        if r.fallback:
            lines.append(f"    替代: {r.fallback}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_summary())
