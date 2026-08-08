"""
文档解析器 — 科学文献 PDF/DOCX/HTML 批量解析
============================================
三层/四层架构：
  1. MinerU Cloud API (远程引擎) — PDF → 结构化 JSON（保留表格/公式/图表位置）
  2. MinerU 本地服务 (localhost:8888) — 自部署实例
  3. MinerU pip 包 (magic-pdf / mineru) — 本地 Python 包直接调用
  4. markitdown (本地引擎) — PDF/DOCX/HTML → Markdown

自动选择策略（优先级递减）：
  - MinerU Cloud API (需要 MINERU_API_KEY)
  - MinerU localhost:8888 (需要本地部署)
  - MinerU pip 包 (需要 pip install magic-pdf)
  - markitdown (始终可用)

解析结果统一为 ParsedDocument dataclass，包含：
  - 全文 Markdown
  - 章节结构（标题层级树）
  - 参考文献列表
  - 图表引用索引
  - 元数据（标题、作者、DOI 等）
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 本地引擎（缺包时降级而非整个模块 import 失败）
# 修复：markitdown 缺失时仍允许 MinerU Cloud/Local/pip 正常使用，
# 仅 MarkItDownParser.parse 返回 parse_engine="error:markitdown_missing" 的错误文档。
try:
    from markitdown import MarkItDown
    _HAS_MARKITDOWN = True
except ImportError:
    MarkItDown = None
    _HAS_MARKITDOWN = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class Section:
    """文档章节"""
    title: str
    level: int                       # 标题层级 (1=#, 2=##, ...)
    content: str = ""                # 该节正文（不含子节）
    start_line: int = 0
    end_line: int = 0
    subsections: List[Section] = field(default_factory=list)
    tables: List[Dict] = field(default_factory=list)     # [{caption, markdown_table}]
    figures: List[str] = field(default_factory=list)      # [figure_caption]
    equations: List[str] = field(default_factory=list)    # [latex_formula]


@dataclass
class Reference:
    """参考文献条目"""
    index: int = 0
    raw_text: str = ""
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None


@dataclass
class ParsedDocument:
    """统一文档解析结果"""
    filepath: str
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    full_text: str = ""                    # 全文 Markdown
    sections: List[Section] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parse_engine: str = "auto"             # 默认 "auto"；解析后覆盖为实际引擎名
                                           # 如 "markitdown" | "mineru" | "markitdown (...)"
    parse_time_seconds: float = 0.0

    # 材料科学特有字段
    materials_mentioned: List[str] = field(default_factory=list)
    properties_mentioned: List[str] = field(default_factory=list)
    methods_mentioned: List[str] = field(default_factory=list)

    @property
    def text_sections(self) -> List[Section]:
        """返回所有非空的顶层章节"""
        return [s for s in self.sections if s.content.strip() or s.subsections]


# ═══════════════════════════════════════════════════════════════
# MarkItDown Parser Wrapper
# ═══════════════════════════════════════════════════════════════

class MarkItDownParser:
    """基于 markitdown 的本地文档解析器"""

    def parse(self, filepath: str) -> ParsedDocument:
        if not _HAS_MARKITDOWN:
            # markitdown 未安装：返回带标记的错误文档，不抛异常
            return ParsedDocument(
                filepath=filepath, title="", full_text="",
                parse_engine="error:markitdown_missing",
            )

        import time
        t0 = time.time()

        md = MarkItDown()
        result = md.convert(filepath)
        raw_markdown = result.markdown
        title = result.title or self._extract_title(raw_markdown, filepath)

        # ── PDF 表格增强（GOAI #14：markitdown 对复杂表格/公式解析弱）──
        # 对 PDF 输入，若 markitdown 提取的表格不足，用 pdfplumber 补充提取
        # 结构化表格（追加到文末并标注来源）。pdfplumber 不可用/解析失败时
        # 静默回退，不改变原 markdown，也不抛异常。
        engine = "markitdown"
        if str(filepath).lower().endswith(".pdf"):
            enhanced, n_tables = self._enhance_pdf_tables(filepath, raw_markdown)
            if n_tables > 0:
                raw_markdown = enhanced
                engine = "markitdown+pdfplumber"

        doc = ParsedDocument(
            filepath=filepath,
            title=title,
            full_text=raw_markdown,
            parse_engine=engine,
            parse_time_seconds=round(time.time() - t0, 2),
        )

        # 结构解析
        doc.sections = self._parse_sections(raw_markdown)
        doc.references = self._extract_references(raw_markdown)
        doc.abstract = self._extract_abstract(raw_markdown)
        doc.authors = self._extract_authors(raw_markdown)

        # 材料科学实体快速提取（正则）
        doc.materials_mentioned = _extract_materials(raw_markdown)
        doc.properties_mentioned = _extract_properties(raw_markdown)
        doc.methods_mentioned = _extract_methods(raw_markdown)

        return doc

    def _parse_sections(self, text: str) -> List[Section]:
        """解析 Markdown 标题层级，构建章节树"""
        lines = text.split("\n")
        # 找所有标题行
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        headings: List[Tuple[int, int, str, str]] = []  # (line_idx, level, marker, title)

        for i, line in enumerate(lines):
            m = heading_pattern.match(line.strip())
            if m:
                level = len(m.group(1))
                headings.append((i, level, m.group(1), m.group(2).strip()))

        if not headings:
            return [Section(title="Full Text", level=0, content=text)]

        # 构建章节树
        root_sections: List[Section] = []
        stack: List[Section] = []  # 层级栈

        for idx, (line_idx, level, _, title) in enumerate(headings):
            section = Section(title=title, level=level, start_line=line_idx)

            # 确定内容范围
            if idx + 1 < len(headings):
                next_line = headings[idx + 1][0]
                content_lines = lines[line_idx + 1:next_line]
            else:
                content_lines = lines[line_idx + 1:]
            section.content = "\n".join(content_lines).strip()
            section.end_line = line_idx + len(content_lines)

            # 找到正确的父级
            while stack and stack[-1].level >= level:
                stack.pop()

            if stack:
                stack[-1].subsections.append(section)
            else:
                root_sections.append(section)

            stack.append(section)

        return root_sections

    def _extract_abstract(self, text: str) -> str:
        """从文本中提取摘要"""
        patterns = [
            r'(?:^|\n)#*\s*(?:Abstract|ABSTRACT|摘要)\s*\n+(.*?)(?:\n#+\s|\n\n(?:Introduction|INTRO|引言))',
            r'(?:^|\n)(?:Abstract|ABSTRACT)[：:]\s*(.*?)(?:\n\n|\n(?:Keywords|KEYWORDS|关键词))',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
            if m:
                return m.group(1).strip()[:2000]
        # Fallback: first substantial paragraph
        paragraphs = text.split("\n\n")
        for p in paragraphs[:5]:
            p = p.strip()
            if len(p) > 100 and not p.startswith("#"):
                return p[:2000]
        return ""

    def _extract_authors(self, text: str) -> List[str]:
        """提取作者列表"""
        # 简单的作者行匹配
        author_patterns = [
            r'(?:Authors?|AUTHORS)[：:]\s*(.+?)(?:\n|$)',
            r'\n([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:,\s*[A-Z][a-z]+(?:\s+[A-Z]\.?)?){2,})',
        ]
        for pat in author_patterns:
            m = re.search(pat, text[:2000], re.MULTILINE)
            if m:
                names = re.split(r'[,;、]', m.group(1))
                return [n.strip() for n in names if len(n.strip()) > 2]
        return []

    def _extract_references(self, text: str) -> List[Reference]:
        """提取参考文献"""
        refs: List[Reference] = []

        # 找参考文献区域
        ref_section_patterns = [
            r'(?:^|\n)#*\s*(?:References?|REFERENCES|参考文献|Bibliography|BIBLIOGRAPHY)\s*\n+(.*?)(?:\n#+\s|\Z)',
        ]
        ref_text = ""
        for pat in ref_section_patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                ref_text = m.group(1)
                break

        if not ref_text:
            return refs

        # 解析编号引用 [1], [2], 等
        ref_entries = re.split(r'\n\s*(?=\[\d+\]|\d+\.\s)', ref_text)
        for i, entry in enumerate(ref_entries):
            entry = entry.strip()
            if not entry or len(entry) < 10:
                continue

            ref = Reference(index=i + 1, raw_text=entry[:500])

            # 提取 DOI
            doi_match = re.search(r'(?:doi|DOI)[：:\s]*([^\s,]+)', entry)
            if doi_match:
                ref.doi = doi_match.group(1).rstrip('.')

            # 提取年份
            year_match = re.search(r'\((\d{4})\)', entry)
            if year_match:
                ref.year = int(year_match.group(1))

            # 提取标题（引号内）
            title_match = re.search(r'[""]([^""]+)[""]', entry)
            if title_match:
                ref.title = title_match.group(1)[:200]

            refs.append(ref)

        return refs

    @staticmethod
    def _extract_title(text: str, filepath: str) -> str:
        """提取文档标题"""
        # 第一个 # 标题
        m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        if m:
            return m.group(1).strip()
        # 第一行非空文本
        for line in text.split("\n")[:5]:
            line = line.strip()
            if line and len(line) > 10:
                return line[:200]
        return Path(filepath).stem

    @staticmethod
    def _enhance_pdf_tables(filepath: str, raw_markdown: str):
        """用 pdfplumber 补充提取 PDF 表格（GOAI #14：markitdown 表格解析弱）。

        触发条件（全部满足）：
          - 输入为 .pdf；
          - markitdown 已产出的 markdown 表格 < 3 个（避免重复/冲突）；
          - pdfplumber 可导入且能成功打开 PDF。

        提取结果以 markdown 表格追加到文末（含页码标注与分隔标题），
        保证 extractor.py 的表格路径（`| ... |`）能解析到结构化数据。

        Returns:
            (enhanced_markdown, n_tables_added)：解析失败或条件不满足时
            返回 (raw_markdown, 0)，绝不抛异常。
        """
        if not str(filepath).lower().endswith(".pdf"):
            return raw_markdown, 0
        existing_tables = len(re.findall(r"^\|.*\|\s*$", raw_markdown, re.MULTILINE))
        if existing_tables >= 3:
            return raw_markdown, 0
        try:
            import pdfplumber  # 延迟导入：依赖可选
        except ImportError:
            return raw_markdown, 0

        md_tables: List[str] = []
        try:
            with pdfplumber.open(filepath) as pdf:
                for pi, page in enumerate(pdf.pages):
                    for table in page.extract_tables():
                        if not table or len(table) < 2:
                            continue
                        rows = []
                        for r in table[:50]:  # 防御超大表
                            cells = [
                                (str(c or "")).replace("|", "\\|")
                                .replace("\n", " ").strip()[:80]
                                for c in r
                            ]
                            rows.append(cells)
                        header = rows[0]
                        md = "| " + " | ".join(header) + " |\n"
                        md += "| " + " | ".join("---" for _ in header) + " |\n"
                        for body_row in rows[1:]:
                            md += "| " + " | ".join(body_row) + " |\n"
                        md_tables.append(
                            f"<!-- pdfplumber 表格提取 (page {pi + 1}) -->\n{md}"
                        )
        except Exception:
            # 解析失败静默回退（不阻塞主流程，与 DocumentParser 回退策略一致）
            return raw_markdown, 0

        if not md_tables:
            return raw_markdown, 0
        appendix = (
            "\n\n## 附录：PDF 表格提取（pdfplumber 增强）\n\n"
            + "\n\n".join(md_tables)
        )
        return raw_markdown + appendix, len(md_tables)


# ═══════════════════════════════════════════════════════════════
# MinerU API Client
# ═══════════════════════════════════════════════════════════════

class MinerUParser:
    """MinerU 文档解析引擎客户端

    MinerU 是开源 PDF 解析引擎，支持：
      - PDF → 结构化 Markdown/JSON
      - 表格保留（含复杂合并单元格）
      - 数学公式识别并转为 LaTeX
      - 图表位置保留 + 图片提取

    支持三种模式（优先级递减）：
      1. MinerU Cloud API（mineru.net）
      2. 本地部署（自建服务 localhost:8888）
      3. pip 包直接调用（magic-pdf / mineru）
    """

    API_BASE = "https://mineru.net"
    LOCAL_BASE = os.environ.get("MINERU_LOCAL_URL", "http://localhost:8888")

    # 异步解析轮询配置
    _POLL_INTERVAL_SECONDS = 2.0   # 轮询间隔
    _POLL_MAX_ATTEMPTS = 150       # 最大轮询次数（5 分钟）

    # ── 检测 pip 包是否可用 ──
    _pip_module: Optional[str] = None    # 记录实际可导入的模块名
    _pip_checked: bool = False

    @classmethod
    def _detect_pip_module(cls) -> Optional[str]:
        """检测可用的 MinerU pip 包。

        尝试顺序: magic_pdf (官方包名) → mineru (别名)

        Returns:
            可用模块名，或 None
        """
        if cls._pip_checked:
            return cls._pip_module

        cls._pip_checked = True
        candidates = [
            ("magic_pdf", "magic_pdf"),
            ("mineru", "mineru"),
        ]
        for mod_name, _ in candidates:
            try:
                __import__(mod_name)
                cls._pip_module = mod_name
                return mod_name
            except ImportError:
                continue
        return None

    @classmethod
    @property
    def pip_available(cls) -> bool:
        """MinerU pip 包是否可用（类级别，不依赖实例）。"""
        return cls._detect_pip_module() is not None

    def __init__(self, mode: str = "cloud"):
        self.mode = mode  # "cloud" | "local" | "pip"
        self._available: Optional[bool] = None
        self._status_detail: Dict[str, Any] = {}
        try:
            import requests as _requests
            self._requests = _requests
        except ImportError:
            self._requests = None
            logger.warning("requests 库未安装，MinerU 网络检查不可用")

    @property
    def available(self) -> bool:
        """检查 MinerU 是否可用（结果缓存，避免重复网络请求）。"""
        if self._available is not None:
            return self._available

        if self.mode == "cloud":
            # MinerU Cloud v1 API 无需 Authorization，仅需检测网络连通性
            try:
                if self._requests is None:
                    self._available = False
                    self._status_detail = {
                        "available": False, "mode": "cloud",
                        "reason": "requests 库未安装",
                    }
                    return False
                # 轻量连通性检查（不实际提交任务）
                resp = self._requests.get(
                    f"{self.API_BASE}/api/v1/agent/parse/url",
                    timeout=5,
                )
                # 405 Method Not Allowed = 端点存在（GET 不支持，POST 才支持）
                # 或其他非 5xx 响应 = 服务可达
                is_ok = resp.status_code < 500
                self._available = is_ok
                self._status_detail = {
                    "available": is_ok,
                    "mode": "cloud",
                    "endpoint": self.API_BASE,
                    "http_status": resp.status_code,
                    "reason": "服务可达" if is_ok else f"HTTP {resp.status_code}",
                }
            except Exception as e:
                self._available = False
                self._status_detail = {
                    "available": False,
                    "mode": "cloud",
                    "endpoint": self.API_BASE,
                    "reason": f"连通性检查失败: {e}",
                }
        elif self.mode == "local":
            try:
                if self._requests is None:
                    self._available = False
                    self._status_detail = {
                        "available": False, "mode": "local",
                        "reason": "requests 库未安装",
                    }
                    return False
                resp = self._requests.get(f"{self.LOCAL_BASE}/health", timeout=3)
                is_ok = resp.status_code == 200
                self._available = is_ok
                self._status_detail = {
                    "available": is_ok,
                    "mode": "local",
                    "endpoint": self.LOCAL_BASE,
                    "http_status": resp.status_code,
                    "reason": "OK" if is_ok else f"HTTP {resp.status_code}",
                }
            except Exception as e:
                self._available = False
                self._status_detail = {
                    "available": False,
                    "mode": "local",
                    "endpoint": self.LOCAL_BASE,
                    "reason": f"本地服务不可达: {e}",
                }
        elif self.mode == "pip":
            mod = self._detect_pip_module()
            self._available = mod is not None
            self._status_detail = {
                "available": mod is not None,
                "mode": "pip",
                "module": mod,
                "reason": f"pip 包可用: {mod}" if mod else "pip 包未安装 (magic-pdf / mineru)",
            }

        return self._available

    def get_status_report(self) -> Dict[str, Any]:
        """返回 MinerU 状态详情（用于诊断报告）。"""
        _ = self.available  # 触发检测
        return dict(self._status_detail)

    def reset_status_cache(self) -> None:
        """重置可用性缓存，迫使下次 available 访问重新检测。"""
        self._available = None
        self._status_detail = {}

    def parse(self, filepath: str, url: Optional[str] = None) -> Optional[ParsedDocument]:
        """通过 MinerU 解析文档。

        Args:
            filepath: 本地文件路径（local/pip 模式必需）
            url: 远程文件 URL（cloud 模式使用，如 arXiv PDF 链接）
        """
        if not self.available:
            return None

        import time
        t0 = time.time()

        try:
            if self.mode == "cloud":
                target = url or filepath
                # 本地文件路径不是合法 URL：跳过 Cloud tier，避免无效 POST 白耗预算
                # （pi_agent 的 h_parse_paper 只传 filepath，无 url）
                if target and not str(target).startswith(("http://", "https://")):
                    self._status_detail["parse_error"] = (
                        f"本地路径 {os.path.basename(str(target))} 不是 URL，Cloud tier 跳过")
                    return None
                result = self._parse_cloud(target)
            elif self.mode == "local":
                result = self._parse_local(filepath)
            elif self.mode == "pip":
                result = self._parse_pip(filepath)
            else:
                result = None

            if result:
                result.parse_time_seconds = round(time.time() - t0, 2)

            return result
        except Exception as e:
            # 记录真实失败原因（供 DocumentParser 回退标注，而非连通性检查的 reason）
            self._status_detail["parse_error"] = str(e)
            logger.warning(
                "MinerU 解析失败 (mode=%s, file=%s): %s",
                self.mode, os.path.basename(filepath), e,
            )
            return None

    def _parse_cloud(self, file_url: str) -> Optional[ParsedDocument]:
        """通过 MinerU Cloud v1 异步 API 解析远程文档。

        API: POST https://mineru.net/api/v1/agent/parse/url
        流程: 提交解析任务 → 获取 task_id → 轮询等待完成 → 获取解析结果
        无需 Authorization。

        Args:
            file_url: 远程文件的 URL（如 arXiv PDF 链接）
        """
        import time

        # ── Step 1: Submit parse task（带重试：429/5xx/网络错误 3 次指数退避）──
        payload = {
            "url": file_url,
            "language": "en",          # 材料科学论文以英文为主
            "enable_table": True,
            "is_ocr": False,
            "enable_formula": True,
        }
        submit_data = None
        for _attempt in range(3):
            try:
                resp = self._requests.post(
                    f"{self.API_BASE}/api/v1/agent/parse/url",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                resp.raise_for_status()
                submit_data = resp.json()
                break
            except Exception as e:
                logger.warning("MinerU Cloud 提交任务失败 (尝试 %d/3): %s", _attempt + 1, e)
                if _attempt < 2:
                    time.sleep(2 * (_attempt + 1))
        if submit_data is None:
            self._status_detail["parse_error"] = "MinerU Cloud 提交任务失败（重试 3 次）"
            logger.error("MinerU Cloud 提交任务失败: 重试 3 次均失败")
            return None

        if submit_data.get("code") != 0:
            self._status_detail["parse_error"] = (
                f"MinerU Cloud 提交失败: code={submit_data.get('code')} msg={submit_data.get('msg')}")
            logger.error("MinerU Cloud 提交失败: code=%s msg=%s",
                         submit_data.get("code"), submit_data.get("msg"))
            return None

        task_id = submit_data.get("data", {}).get("task_id", "")
        if not task_id:
            self._status_detail["parse_error"] = "MinerU Cloud 未返回 task_id"
            logger.error("MinerU Cloud 未返回 task_id")
            return None

        logger.info("MinerU Cloud 任务已提交: task_id=%s", task_id)

        # ── Step 2: Poll for result ──
        # 连续失败计数：网络故障不白耗预算，连续 5 次失败即放弃（走 markitdown 回退）
        result_data = None
        consecutive_failures = 0
        for attempt in range(self._POLL_MAX_ATTEMPTS):
            time.sleep(self._POLL_INTERVAL_SECONDS)
            try:
                poll_resp = self._requests.get(
                    f"{self.API_BASE}/api/v1/agent/task/{task_id}",
                    timeout=15,
                )
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()
                consecutive_failures = 0  # 成功一次即清零
            except Exception as e:
                consecutive_failures += 1
                logger.warning("MinerU Cloud 轮询失败 (attempt %d, 连续 %d 次): %s",
                               attempt + 1, consecutive_failures, e)
                if consecutive_failures >= 5:
                    self._status_detail["parse_error"] = (
                        f"MinerU Cloud 连续 {consecutive_failures} 次轮询失败，放弃")
                    logger.warning("MinerU Cloud 连续 %d 次轮询失败，放弃（走 markitdown 回退）",
                                   consecutive_failures)
                    return None
                continue

            status = poll_data.get("data", {}).get("status", "")
            if status in ("done", "completed", "success"):
                result_data = poll_data.get("data", {}).get("result", poll_data.get("data", {}))
                break
            elif status in ("failed", "error"):
                logger.error("MinerU Cloud 解析失败: task_id=%s status=%s", task_id, status)
                return None
            # else: still processing, continue polling

            if (attempt + 1) % 30 == 0:
                logger.info("MinerU Cloud 仍在解析中: task_id=%s attempt=%d", task_id, attempt + 1)

        if result_data is None:
            self._status_detail["parse_error"] = "MinerU Cloud 轮询超时（无结果）"
            logger.warning("MinerU Cloud 轮询超时: task_id=%s", task_id)
            return None

        # ── Step 3: Convert to ParsedDocument ──
        # result_data 可能是 JSON 结构（含 markdown）或直接是解析后的 dict
        if isinstance(result_data, str):
            try:
                import json
                result_data = json.loads(result_data)
            except json.JSONDecodeError:
                return self._to_parsed_document(
                    {"markdown": result_data}, file_url, "mineru-cloud"
                )

        return self._to_parsed_document(result_data, file_url, "mineru-cloud")

    def _parse_local(self, filepath: str) -> Optional[ParsedDocument]:
        with open(filepath, "rb") as f:
            resp = self._requests.post(
                f"{self.LOCAL_BASE}/parse",
                files={"file": f},
                timeout=300,
            )
        resp.raise_for_status()
        data = resp.json()
        return self._to_parsed_document(data, filepath, "mineru")

    def _parse_pip(self, filepath: str) -> Optional[ParsedDocument]:
        """使用 pip 安装的 magic-pdf/mineru 包直接解析 PDF。

        尝试调用 magic_pdf 的 CLI 或 Python API：
          - magic_pdf.tools.common.parse_pdf()  (推荐方式)
          - magic_pdf 的 CLI: magic-pdf parse <file>

        Returns:
            ParsedDocument 或 None
        """
        mod = self._detect_pip_module()
        if mod is None:
            return None

        # 尝试方式 1: magic_pdf 的 Python API
        if mod == "magic_pdf":
            try:
                import magic_pdf.tools.common as mp_tools
                # magic_pdf 将 PDF 解析为中间 JSON，再转为 markdown
                result = mp_tools.parse_pdf(filepath)
                if isinstance(result, dict):
                    return self._to_parsed_document(result, filepath, "mineru-pip")
                # 如果返回的是路径，读取 JSON
                if isinstance(result, str) and os.path.exists(result):
                    with open(result, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return self._to_parsed_document(data, filepath, "mineru-pip")
            except Exception as e:
                logger.debug("magic_pdf Python API 调用失败: %s，尝试 CLI 方式", e)

            # 尝试方式 2: CLI 调用
            try:
                import tempfile
                output_dir = tempfile.mkdtemp(prefix="mineru_")
                proc = subprocess.run(
                    ["magic-pdf", "parse", filepath, "-o", output_dir],
                    capture_output=True, text=True, timeout=300,
                )
                if proc.returncode == 0:
                    # 查找输出中的 .md 或 .json 文件
                    md_files = list(Path(output_dir).rglob("*.md"))
                    json_files = list(Path(output_dir).rglob("*.json"))
                    if json_files:
                        with open(json_files[0], "r", encoding="utf-8") as f:
                            data = json.load(f)
                        return self._to_parsed_document(data, filepath, "mineru-pip")
                    if md_files:
                        markdown_text = md_files[0].read_text(encoding="utf-8")
                        return self._to_parsed_document(
                            {"markdown": markdown_text}, filepath, "mineru-pip"
                        )
                else:
                    logger.debug("magic-pdf CLI 失败: %s", proc.stderr[:200])
            except Exception as e:
                logger.debug("magic-pdf CLI 调用失败: %s", e)

        # 尝试 mineru 模块的 API
        if mod == "mineru":
            try:
                import mineru
                # mineru 通常提供一个 parse() 或 convert() 函数
                if hasattr(mineru, "parse"):
                    result = mineru.parse(filepath)
                    if isinstance(result, dict):
                        return self._to_parsed_document(result, filepath, "mineru-pip")
                if hasattr(mineru, "convert"):
                    result = mineru.convert(filepath)
                    if isinstance(result, str):
                        return self._to_parsed_document(
                            {"markdown": result}, filepath, "mineru-pip"
                        )
            except Exception as e:
                logger.debug("mineru 模块调用失败: %s", e)

        return None

    def _to_parsed_document(self, data: Dict, filepath: str, engine: str) -> ParsedDocument:
        md_content = data.get("markdown", data.get("content", ""))
        sections_data = data.get("sections", data.get("structure", []))

        sections = []
        for s in sections_data:
            sections.append(Section(
                title=s.get("title", ""),
                level=s.get("level", 1),
                content=s.get("content", ""),
                tables=s.get("tables", []),
                figures=s.get("figures", []),
                equations=s.get("equations", []),
            ))

        refs = []
        for i, r in enumerate(data.get("references", [])):
            refs.append(Reference(
                index=i + 1,
                raw_text=r.get("raw", ""),
                title=r.get("title"),
                authors=r.get("authors"),
                year=r.get("year"),
                doi=r.get("doi"),
            ))

        return ParsedDocument(
            filepath=filepath,
            title=data.get("title"),
            authors=data.get("authors", []),
            abstract=data.get("abstract", ""),
            full_text=md_content,
            sections=sections,
            references=refs,
            metadata=data.get("metadata", {}),
            parse_engine=engine,
            materials_mentioned=data.get("materials", []),
            properties_mentioned=data.get("properties", []),
            methods_mentioned=data.get("methods", []),
        )


# ═══════════════════════════════════════════════════════════════
# Unified Parser Interface
# ═══════════════════════════════════════════════════════════════

class DocumentParser:
    """统一文档解析入口。

    自动选择最优解析引擎（优先级递减）：
      1. MinerU Cloud API — 最优质量（mineru.net 公开接口）
      2. MinerU 本地服务 — 高质量，需本地部署
      3. MinerU pip 包 — 本地直接调用，需 pip install magic-pdf
      4. markitdown — 本地离线，免费，始终可用

    用法:
        parser = DocumentParser()          # 默认 prefer_mineru=True，优先使用 MinerU
        doc = parser.parse("paper.pdf")
        print(doc.title, len(doc.sections))
        print(f"引擎: {doc.parse_engine}, MinerU: {parser.mineru_available}")
    """

    def __init__(self,
                 prefer_mineru: bool = True):
        self._markitdown = MarkItDownParser()
        self._mineru_cloud = MinerUParser(mode="cloud")
        self._mineru_local = MinerUParser(mode="local")
        self._mineru_pip = MinerUParser(mode="pip")
        self._prefer_mineru = prefer_mineru

    def _try_mineru_tier(self, parser: MinerUParser, filepath: str,
                         tier_name: str, url: Optional[str] = None) -> Optional[ParsedDocument]:
        """尝试单个 MinerU tier 解析。"""
        if not parser.available:
            return None
        doc = parser.parse(filepath, url=url)
        if doc:
            logger.info(
                "MinerU (%s) 解析成功: %s (%.1fs)",
                tier_name, os.path.basename(filepath), doc.parse_time_seconds,
            )
        return doc

    def parse(self, filepath: str, url: Optional[str] = None) -> ParsedDocument:
        """解析单个文档，自动选择最优引擎。

        选择策略（优先级递减）：
          - Cloud API > localhost:8888 > pip 包 > markitdown

        prefer_mineru=True（默认）：严格按上述顺序尝试全部 MinerU tier，
        全部不可用时回退 markitdown，并在 parse_engine 字段标注原因。
        prefer_mineru=False：快速路径——仅尝试本地 pip 包（跳过 Cloud/Local
        网络探测），仍保持 "MinerU 优先、markitdown 兜底" 的混合策略。

        Args:
            filepath: 本地文件路径
            url: 远程文件 URL（Cloud 模式优先使用，如 arXiv PDF 链接）

        MinerU 所有 tier 不可用时自动回退到 markitdown。
        """
        mineru_tried = False
        mineru_fail_reason = ""

        # 组装 MinerU tier 尝试序列（优先级递减：Cloud > localhost:8888 > pip 包）
        if self._prefer_mineru:
            # 严格路径：尝试全部 tier（含 Cloud/Local 网络连通性探测）
            tiers = [
                (self._mineru_cloud, "cloud", {"url": url}),
                (self._mineru_local, "local", {}),
                (self._mineru_pip, "pip", {}),
            ]
        else:
            # 快速路径：仅尝试本地 pip 包（import 检测，无网络开销）
            tiers = [(self._mineru_pip, "pip", {})]

        for parser, tier_name, kwargs in tiers:
            doc = self._try_mineru_tier(parser, filepath, tier_name, **kwargs)
            if doc:
                return doc
            # 该 tier 宣称可用但实际解析失败——记录原因，供回退标注
            if parser.available:
                mineru_tried = True
                if not mineru_fail_reason:
                    # 优先取真实解析失败原因（parse_error），退而取连通性检查 reason
                    mineru_fail_reason = (
                        parser._status_detail.get("parse_error")
                        or parser._status_detail.get("reason", f"{tier_name} 解析失败")
                    )

        # Fallback to markitdown
        doc = self._markitdown.parse(filepath)

        if mineru_tried:
            doc.parse_engine = f"markitdown (MinerU 调用失败: {mineru_fail_reason})"
        else:
            # 收集不可用原因；快速路径只报告实际探测过的 pip，避免触发网络探测
            if self._prefer_mineru:
                status_sources = [
                    (self._mineru_cloud, "Cloud"),
                    (self._mineru_local, "Local"),
                    (self._mineru_pip, "pip"),
                ]
            else:
                status_sources = [(self._mineru_pip, "pip")]
            reasons = []
            for parser, tier_name in status_sources:
                status = parser.get_status_report()
                if not status.get("available"):
                    reasons.append(status.get("reason", f"{tier_name} 不可用"))
            reason_str = "; ".join(reasons) if reasons else "未知"
            doc.parse_engine = f"markitdown (MinerU unavailable: {reason_str})"
            logger.debug(
                "MinerU 不可用 (%s)，使用 markitdown 解析: %s",
                reason_str, os.path.basename(filepath),
            )

        return doc

    def parse_batch(self,
                    filepaths: List[str],
                    max_workers: int = 4) -> Dict[str, ParsedDocument]:
        """批量并发解析文档

        Args:
            filepaths: 文件路径列表
            max_workers: 并发数

        Returns:
            {filepath: ParsedDocument} 字典
        """
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.parse, fp): fp for fp in filepaths}
            for future in as_completed(futures):
                fp = futures[future]
                try:
                    results[fp] = future.result()
                except Exception as e:
                    # 单文件失败不阻断批量处理
                    results[fp] = ParsedDocument(
                        filepath=fp,
                        full_text=f"[Parse Error: {e}]",
                        parse_engine="error",
                    )
        return results

    def parse_directory(self,
                        directory: str,
                        patterns: List[str] = None) -> Dict[str, ParsedDocument]:
        """解析目录下所有文档

        Args:
            directory: 目录路径
            patterns: 文件扩展名列表，默认 [".pdf", ".docx", ".html", ".txt"]

        Returns:
            {filepath: ParsedDocument} 字典
        """
        patterns = patterns or [".pdf", ".docx", ".html", ".htm", ".txt", ".md"]
        dir_path = Path(directory)
        if not dir_path.exists():
            return {}

        filepaths = []
        for pat in patterns:
            filepaths.extend(str(p) for p in dir_path.glob(f"**/*{pat}"))

        return self.parse_batch(filepaths)


# ═══════════════════════════════════════════════════════════════
# Quick Entity Extractors (Regex-based, for speed)
# ═══════════════════════════════════════════════════════════════

def _extract_materials(text: str) -> List[str]:
    """快速提取材料名（正则）"""
    patterns = [
        r'\b[A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*)+(?:\b|_)',  # 化学式
        r'\b(?:perovskite|MOF|zeolite|graphene|MXene|TMD|HEA|COF|QD)\b',
        r'\b(?:metal-organic framework|covalent organic framework)\b',
        r'\b(?:oxide|sulfide|nitride|carbide|alloy|ceramic|polymer|composite)\b',
        r'\b(?:TiO2|SiO2|Al2O3|ZnO|Fe2O3|CuO|NiO|MoS2|WS2|BN|SiC|GaN|GaAs)\b',
        r'\b(?:MAPbI3|CsPbI3|FAPbI3|YBa2Cu3O7|LiFePO4|LiCoO2|NaFePO4)\b',
        r'\b(?:ZIF-\d+|UiO-\d+|MIL-\d+|HKUST-\d+|IRMOF-\d+)\b',
    ]
    materials = set()
    for i, pat in enumerate(patterns):
        # 化学式模式（索引 0）大小写敏感，避免 IGNORECASE 把普通英文词当材料
        flags = 0 if i == 0 else re.IGNORECASE
        for m in re.findall(pat, text, flags):
            if len(m) > 2:
                materials.add(m)
    return sorted(materials)[:50]


def _extract_properties(text: str) -> List[str]:
    """快速提取性质名"""
    patterns = [
        r'\b(?:band gap|conductivity|resistivity|capacitance|dielectric|permittivity)\b',
        r'\b(?:thermal conductivity|thermal expansion|specific heat|heat capacity)\b',
        r'\b(?:Young\'s modulus|bulk modulus|shear modulus|hardness|tensile strength|yield strength|elastic)\b',
        r'\b(?:PCE|power conversion efficiency|EQE|fill factor|open.circuit voltage|short.circuit current)\b',
        r'\b(?:figure of merit|ZT|Seebeck coefficient|carrier mobility|carrier concentration)\b',
        r'\b(?:catalytic activity|TOF|TON|selectivity|conversion|Faradaic efficiency|overpotential)\b',
        r'\b(?:adsorption capacity|uptake|permeability|permeance|separation factor)\b',
        r'\b(?:corrosion rate|corrosion potential|passivation|pitting|oxidation)\b',
        r'\b(?:magnetic moment|coercivity|remanence|Curie temperature|susceptibility)\b',
        r'\b(?:phase transition temperature|Tc|melting point|decomposition temperature|Tg)\b',
        r'\b(?:stability|degradation|lifetime|durability|cyclability|coulombic efficiency)\b',
        r'\b(?:photoluminescence|PLQY|quantum yield|fluorescence|phosphorescence)\b',
    ]
    props = set()
    for pat in patterns:
        for m in re.findall(pat, text, re.IGNORECASE):
            props.add(m.lower())
    return sorted(props)[:50]


def _extract_methods(text: str) -> List[str]:
    """快速提取实验/计算方法"""
    patterns = [
        r'\b(?:DFT|density functional theory|HF|Hartree.Fock|CCSD|MP2|GW approximation)\b',
        r'\b(?:molecular dynamics|MD simulation|Monte Carlo|MCTS|kinetic Monte Carlo)\b',
        r'\b(?:machine learning|deep learning|neural network|CNN|GNN|random forest|SVM)\b',
        r'\b(?:XRD|XPS|TEM|SEM|STEM|AFM|STM|NMR|EPR|FTIR|Raman|UV.vis|XANES|EXAFS)\b',
        r'\b(?:CVD|PVD|ALD|MBE|sputtering|spin.coating|dip.coating|electrodeposition)\b',
        r'\b(?:sol.gel|hydrothermal|solvothermal|co.precipitation|solid.state|mechanochemical)\b',
        r'\b(?:TG|DSC|DTA|TGA|BET|BJH|porosimetry|chemisorption|physisorption)\b',
        r'\b(?:VASP|Quantum ESPRESSO|CP2K|LAMMPS|GROMACS|Gaussian|ORCA|WIEN2k)\b',
        r'\b(?:Bayesian optimization|genetic algorithm|active learning|transfer learning)\b',
    ]
    methods = set()
    for pat in patterns:
        for m in re.findall(pat, text, re.IGNORECASE):
            methods.add(m)
    return sorted(methods)[:50]


# ═══════════════════════════════════════════════════════════════
# MinerU Status Checker
# ═══════════════════════════════════════════════════════════════

def check_mineru_status() -> Dict[str, Any]:
    """检查 MinerU 集成可用性状态，返回完整诊断报告。

    检查项（优先级递减）：
      1. MinerU Cloud API (mineru.net, 无需 API Key, 公开访问)
      2. MinerU 本地服务 (localhost:8888)
      3. MinerU pip 包 (magic-pdf/mineru)

    Returns:
        {
            "mineru_available": bool,
            "cloud": {"available": bool, "endpoint": str, "detail": str},
            "local": {"available": bool, "endpoint": str, "detail": str},
            "pip": {"available": bool, "module": str | None, "detail": str},
            "recommended_engine": str,
            "fallback_engine": str,
            "diagnosis": str,
        }
    """
    report: Dict[str, Any] = {
        "mineru_available": False,
        "cloud": {"available": False, "endpoint": MinerUParser.API_BASE, "detail": ""},
        "local": {"available": False, "endpoint": MinerUParser.LOCAL_BASE, "detail": ""},
        "pip": {"available": False, "module": None, "detail": ""},
        "recommended_engine": "markitdown",
        "fallback_engine": "markitdown",
        "diagnosis": "",
    }

    # ── 检查 Cloud 模式（无需 API Key）──
    cloud_parser = MinerUParser(mode="cloud")
    cloud_status = cloud_parser.get_status_report()
    report["cloud"]["available"] = cloud_status.get("available", False)
    report["cloud"]["detail"] = cloud_status.get("reason", "")
    if cloud_status.get("available"):
        report["mineru_available"] = True
        report["recommended_engine"] = "mineru-cloud"
        report["diagnosis"] = "MinerU Cloud 可用 — 公开 API，无需 API Key"

    # ── 检查 Local 模式 ──
    local_parser = MinerUParser(mode="local")
    local_status = local_parser.get_status_report()
    report["local"]["available"] = local_status.get("available", False)
    report["local"]["detail"] = local_status.get("reason", "")
    if local_status.get("available"):
        report["mineru_available"] = True
        if not report["recommended_engine"].startswith("mineru-cloud"):
            report["recommended_engine"] = "mineru-local"
        report["diagnosis"] = report.get("diagnosis", "") or "MinerU 本地服务可用"

    # ── 检查 pip 模式 ──
    pip_parser = MinerUParser(mode="pip")
    pip_status = pip_parser.get_status_report()
    report["pip"]["available"] = pip_status.get("available", False)
    report["pip"]["module"] = pip_status.get("module")
    report["pip"]["detail"] = pip_status.get("reason", "")
    if pip_status.get("available"):
        report["mineru_available"] = True
        if report["recommended_engine"] == "markitdown":
            report["recommended_engine"] = "mineru-pip"
        if report["diagnosis"]:
            report["diagnosis"] += "；MinerU pip 包可用"
        else:
            report["diagnosis"] = f"MinerU pip 包可用 (模块: {pip_status.get('module')})"

    # ── 总结 ──
    if not report["mineru_available"]:
        reasons = []
        if report["cloud"]["detail"]:
            reasons.append(f"Cloud: {report['cloud']['detail']}")
        if report["local"]["detail"]:
            reasons.append(f"Local: {report['local']['detail']}")
        if report["pip"]["detail"]:
            reasons.append(f"Pip: {report['pip']['detail']}")
        report["diagnosis"] = (
            "MinerU 不可用 — 自动回退到 markitdown 本地引擎。"
            "原因：" + "；".join(reasons)
            + "。启用 MinerU 指引：Cloud 模式无需 API Key（mineru.net 公开接口，"
            "确认网络可访问 https://mineru.net 即可）；本地服务请自行部署 MinerU "
            "并监听 localhost:8888（或设置 MINERU_LOCAL_URL）；pip 模式执行 "
            "`pip install magic-pdf` 安装后即可用。详见 "
            "https://github.com/opendatalab/MinerU"
        )

    return report


def print_mineru_status() -> None:
    """打印 MinerU 集成状态报告（人类可读格式）。"""
    report = check_mineru_status()
    print("=" * 60)
    print("  MinerU 集成状态报告")
    print("=" * 60)
    print(f"  总体可用:     {'是' if report['mineru_available'] else '否'}")
    print(f"  推荐引擎:     {report['recommended_engine']}")
    print(f"  回退引擎:     {report['fallback_engine']}")
    print(f"  Cloud 端点:   {report['cloud']['endpoint']}")
    print(f"  Cloud 状态:   {'可用' if report['cloud']['available'] else '不可用'} — {report['cloud']['detail']}")
    print(f"  Local 端点:   {report['local']['endpoint']}")
    print(f"  Local 状态:   {'可用' if report['local']['available'] else '不可用'} — {report['local']['detail']}")
    print(f"  Pip  模块:    {report['pip'].get('module') or 'N/A'}")
    print(f"  Pip  状态:    {'可用' if report['pip']['available'] else '不可用'} — {report['pip']['detail']}")
    print(f"  诊断:         {report['diagnosis']}")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# Quick Test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # 先打印 MinerU 状态
    print_mineru_status()
    print()

    parser = DocumentParser()
    if len(sys.argv) > 1:
        doc = parser.parse(sys.argv[1])
        print(f"Title: {doc.title}")
        print(f"Authors: {doc.authors}")
        print(f"Abstract: {doc.abstract[:200]}...")
        print(f"Sections: {len(doc.sections)}")
        print(f"References: {len(doc.references)}")
        print(f"Materials: {doc.materials_mentioned[:10]}")
        print(f"Properties: {doc.properties_mentioned[:10]}")
        print(f"Methods: {doc.methods_mentioned[:10]}")
        print(f"Engine: {doc.parse_engine} ({doc.parse_time_seconds}s)")
    else:
        print("Usage: python parser.py <filepath>")
    print()
    print(f"MinerU 可用: {parser.mineru_available}")
