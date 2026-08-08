"""
文献检索工具 — 多数据源统一的科学文献搜索引擎
==============================================
支持三大数据源，按优先级自动切换：
  1. Sciverse API  — 语义检索 + 全文证据片段定位（需 API Key）
  2. Sci-Base      — HuggingFace 开放数据集，2500万+篇论文（本地/远程）
  3. arXiv API     — 免费开放获取论文检索（兜底方案）

检索结果统一为 SearchResult dataclass，包含标题、作者、摘要、
全文链接、来源数据库、相关度分数等字段。

用法:
    from literature_agent.search import LiteratureSearcher

    searcher = LiteratureSearcher()
    results = searcher.search("perovskite solar cell stability", top_k=20)
    for r in results:
        print(r.title, r.score)
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests

# 延迟导入以避免循环依赖
_sciverse_adapter_module = None


def _get_adapter_module():
    """延迟加载 sciverse_mcp 模块"""
    global _sciverse_adapter_module
    if _sciverse_adapter_module is None:
        from literature_agent.sciverse_mcp import (
            create_sciverse_adapter,
            BaseSciverseAdapter,
        )
        _sciverse_adapter_module = (create_sciverse_adapter, BaseSciverseAdapter)
    return _sciverse_adapter_module


def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    """规范化 DOI：去除前缀/空白/尾部标点，统一小写。

    用于跨数据源（Crossref / Sciverse / arXiv）统一比较，
    避免同一篇论文因 DOI 大小写或前缀不同而无法去重。
    """
    if not doi:
        return None
    d = str(doi).strip()
    d = re.sub(r'^https?://(dx\.)?doi\.org/', '', d, flags=re.I)
    d = re.sub(r'^doi:\s*', '', d, flags=re.I)
    d = d.rstrip('.,;')
    d = d.lower()
    return d or None


def _extract_doi(item: Dict[str, Any]) -> Optional[str]:
    """从原始检索条目中提取并规范化 DOI（兼容多种返回格式）。"""
    for key in ("doi", "DOI", "Doi"):
        val = item.get(key)
        if val:
            return _normalize_doi(val)
    # 某些数据源将 DOI 嵌套在 ids / external_ids 对象中
    ids = item.get("ids") or item.get("external_ids") or {}
    if isinstance(ids, dict):
        doi = ids.get("DOI") or ids.get("doi")
        if doi:
            return _normalize_doi(doi)
    # 从 URL 中提取
    url = item.get("url") or ""
    if "doi.org" in str(url):
        return _normalize_doi(str(url).split("doi.org/")[-1])
    return None


def _parse_retry_after(resp: requests.Response) -> Optional[float]:
    """解析 429 响应的 Retry-After 头，返回建议等待秒数。

    支持两种格式：
      - 秒数（整数或小数，如 "5" / "0.5"）
      - HTTP 日期（RFC 7231，如 "Wed, 21 Oct 2015 07:28:00 GMT"）
    头缺失或解析失败时返回 None，由调用方退化为指数退避。
    """
    raw = resp.headers.get("Retry-After")
    if not raw:
        return None
    raw = raw.strip()
    # 格式 1：秒数
    try:
        return float(raw)
    except ValueError:
        pass
    # 格式 2：HTTP 日期（无时区时视为 UTC）
    try:
        dt = parsedate_to_datetime(raw)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


def _retry_delay(retry_base: float, attempt: int,
                 retry_after: Optional[float]) -> float:
    """计算本次重试的等待时间：指数退避与 Retry-After 取较大值，再加随机抖动。

    - 指数退避：retry_base * 2^(attempt-1)，即 1s、2s、4s...
    - Retry-After：服务端明确给出的限流恢复时间，与指数退避取 max。
    - 抖动：0 ~ delay*0.2 的随机量，避免多个请求同时重试造成 thundering herd。
      抖动使用独立种子 random.Random()（系统熵），不占用模块级 random 状态，
      故不受项目 main 入口 seed_everything 的影响，多请求/多线程下延迟互不相同。
    """
    delay = retry_base * (2 ** (attempt - 1))
    if retry_after is not None:
        delay = max(delay, retry_after)
    delay += random.Random().uniform(0.0, delay * 0.2)
    return delay


def _request_with_retry(session: requests.Session, method: str, url: str,
                        max_attempts: int = 3, retry_base: float = 1.0,
                        timeout: int = 30, max_attempts_429: int = 2,
                        **kwargs) -> requests.Response:
    """发送 HTTP 请求，遇 429 限流或 5xx 服务端错误自动重试（指数退避）。

    重试间隔按 retry_base 依次加倍（1s、2s、4s...），最多重试 max_attempts 次。
    每次重试均打印带时间戳的警告到 stderr（构成重试过程的审计痕迹）。
    所有重试耗尽后抛出最后一次异常。

    限流增强（2026-08）：
    - 尊重 Retry-After 头：429 响应若携带 Retry-After（秒数或 HTTP 日期），
      以服务端给出的恢复时间为准，与指数退避取 max。
    - 抖动：每次退避附加 0~delay*0.2 的随机量，避免多请求同时重试打爆限流。
    - 预算保护：429 限流通常恢复缓慢，多次重试只会白白消耗时间预算，故 429
      的重试次数单独受 max_attempts_429（默认 2）限制；网络超时 / 5xx 才按
      max_attempts（默认 3）重试。
    """
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = session.request(method, url, timeout=timeout, **kwargs)
        except requests.RequestException as e:
            last_exc = e
            if attempt < max_attempts:
                delay = _retry_delay(retry_base, attempt, None)
                print(f"  ⚠️ [{time.strftime('%Y-%m-%dT%H:%M:%S')}] 检索请求异常（第 {attempt}/{max_attempts} 次）: "
                      f"{method} {url} → {e}；{delay:.1f}s 后重试", file=sys.stderr)
                time.sleep(delay)
                continue
            raise
        if resp.status_code == 429 or resp.status_code >= 500:
            limit = max_attempts_429 if resp.status_code == 429 else max_attempts
            if attempt < limit:
                retry_after = _parse_retry_after(resp)
                delay = _retry_delay(retry_base, attempt, retry_after)
                ra_txt = (f"，Retry-After {retry_after:.0f}s"
                          if retry_after is not None else "")
                print(f"  ⚠️ [{time.strftime('%Y-%m-%dT%H:%M:%S')}] 检索请求返回 {resp.status_code}（第 {attempt}/{limit} 次）: "
                      f"{method} {url}{ra_txt}；{delay:.1f}s 后重试", file=sys.stderr)
                time.sleep(delay)
                continue
            resp.raise_for_status()  # 最后一次仍失败 → 抛出 HTTPError
        return resp
    raise last_exc  # 防御性代码，理论上不可达


def _cache_read_json(cache_path) -> Optional[list]:
    """读取 JSON 缓存；缺失/损坏返回 None（调用方回退网络请求）。

    损坏缓存直接删除（下次重新抓取），避免数据源静默失效。
    """
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        try:
            cache_path.unlink(missing_ok=True)  # 删除损坏缓存
        except OSError:
            pass
        return None


def _cache_write_json(cache_path, data) -> None:
    """原子写 JSON 缓存（临时文件 + rename），避免进程中断留下半截 JSON。"""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(cache_path))
    except OSError:
        pass


# 单次多源检索的软超时（秒）：某个数据源超过此时限仍未返回则放弃等待，
# 防止限流/慢网（如 arXiv 超时、Semantic Scholar 429）拖垮整体时间预算。
SEARCH_SOURCE_TIMEOUT = 25.0


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class SearchResult:
    """统一的文献检索结果"""
    title: str
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    source: str = "unknown"            # "sciverse" | "scibase" | "arxiv" | "semantic_scholar"
    score: float = 0.0                 # 相关度分数 [0, 1]
    citation_count: int = 0
    journal: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    paper_id: Optional[str] = None          # 数据源真实论文 ID（如 Sciverse doc_id），非标题截断
    full_text_snippet: Optional[str] = None  # 全文证据片段
    pdf_url: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """基于 DOI / 数据源真实论文 ID / 标题的稳定 ID"""
        if self.doi:
            return f"doi:{self.doi}"
        if self.paper_id:
            return f"paper:{self.paper_id}"
        return f"title:{hashlib.md5(self.title.encode()).hexdigest()[:12]}"

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_markdown(self) -> str:
        """格式化为 Markdown 引用条目"""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += f" et al. ({len(self.authors)} authors)"
        year_str = f" ({self.year})" if self.year else ""
        lines = [
            f"### {self.title}",
            f"**Authors:** {authors_str}{year_str}",
        ]
        if self.journal:
            lines.append(f"**Journal:** {self.journal}")
        if self.doi:
            lines.append(f"**DOI:** [{self.doi}](https://doi.org/{self.doi})")
        if self.abstract:
            lines.append(f"\n**Abstract:** {self.abstract[:500]}")
        if self.full_text_snippet:
            lines.append(f"\n**Evidence Snippet:** {self.full_text_snippet[:300]}")
        if self.keywords:
            lines.append(f"\n**Keywords:** {', '.join(self.keywords)}")
        lines.append(f"\n*Source: {self.source} | Score: {self.score:.3f} | Citations: {self.citation_count}*")
        lines.append("")
        return "\n".join(lines)


@dataclass
class SearchQuery:
    """结构化的检索查询"""
    text: str                              # 自然语言查询
    material: Optional[str] = None         # 材料名（如 "MAPbI3"）
    property: Optional[str] = None         # 目标性质（如 "band gap"）
    method: Optional[str] = None           # 方法（如 "DFT", "MCTS"）
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    top_k: int = 20
    sources: List[str] = field(default_factory=lambda: ["arxiv", "scibase"])
    # 自动解析查询中的结构化意图
    parsed_entities: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Data Source Implementations
# ═══════════════════════════════════════════════════════════════

class ArxivSearcher:
    """arXiv API 搜索器（免费，无需 API Key）

    使用 arXiv 官方 API: https://info.arxiv.org/help/api/
    限制：每请求最多返回 ~100 条，请求间隔建议 >3s
    """

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, cache_dir: Optional[str] = None):
        self._session = requests.Session()
        self._last_request = 0.0
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: SearchQuery, max_results: int = 50) -> List[SearchResult]:
        # arXiv 不支持自然语言短语，拆成单词用 AND 连接
        # "MOF CO2 capture" → all:MOF AND all:CO2 AND all:capture
        def _tokenize(text: str) -> list[str]:
            # 保留引号内的短语，其余拆词
            phrases = re.findall(r'"([^"]+)"', text)
            remaining = re.sub(r'"[^"]+"', '', text)
            words = [w for w in remaining.split() if len(w) > 1]
            return phrases + words

        terms = _tokenize(query.text)
        # 去掉太短的噪声词
        noise = {'of', 'for', 'in', 'on', 'the', 'a', 'an', 'is', 'are', 'and', 'or', 'with', 'by', 'to', 'at', 'as'}
        terms = [t for t in terms if t.lower() not in noise]

        # 加上材料/性质作为额外 AND 条件
        if query.material:
            terms.append(query.material)
        if query.property:
            terms.append(query.property)

        if not terms:
            terms = [query.text]

        search_query = " AND ".join(f'all:{t}' if ' ' not in t else f'all:"{t}"'
                                    for t in terms[:10])  # 最多 10 个词，避免过于严格

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": min(max_results, 100),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        results = self._fetch(params)
        # Re-sort by relevance to query
        for r in results:
            r.score = self._compute_score(r, query)
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:max_results]

    def _fetch(self, params: Dict) -> List[SearchResult]:
        # Rate limiting
        elapsed = time.time() - self._last_request
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)

        cache_key = None
        if self._cache_dir:
            cache_key = self._cache_dir / f"arxiv_{hashlib.md5(str(params).encode()).hexdigest()[:16]}.json"
            if cache_key.exists():
                data = _cache_read_json(cache_key)
                if data is not None:
                    return [_dict_to_result(d) for d in data]

        resp = _request_with_retry(
            self._session, "GET", self.BASE_URL, params=params, timeout=30,
        )
        self._last_request = time.time()
        resp.raise_for_status()

        results = _parse_arxiv_xml(resp.text)

        if cache_key:
            _cache_write_json(cache_key, [r.to_dict() for r in results])
        return results

    @staticmethod
    def _compute_score(result: SearchResult, query: SearchQuery) -> float:
        """基于文本匹配的相关度分数"""
        score = 0.0
        query_lower = query.text.lower()
        title_lower = result.title.lower()
        abstract_lower = result.abstract.lower()

        # Title match
        query_terms = set(query_lower.split())
        title_terms = set(title_lower.split())
        if query_terms:
            overlap = len(query_terms & title_terms) / len(query_terms)
            score += overlap * 0.5

        # Abstract match
        if query_lower in abstract_lower:
            score += 0.3
        elif any(term in abstract_lower for term in query_terms if len(term) > 3):
            score += 0.2

        # Material/Property bonus
        if query.material and query.material.lower() in abstract_lower:
            score += 0.15
        if query.property and query.property.lower() in abstract_lower:
            score += 0.15

        # Recency bonus
        if result.year and query.year_from:
            if result.year >= query.year_from:
                score += 0.05

        return min(score, 1.0)


class SciverseSearcher:
    """Sciverse API 搜索器（需 API Key / Token）

    Sciverse 科学智能数据库：
      - 5.16 亿条学术元数据
      - 814 种语言，130 万+ 期刊/会议
      - 语义检索 + 全文证据片段定位

    REST API: https://api.sciverse.space
      - /agentic-search  — 智能体语义检索（主力端点，支持 filters）
      - /content         — 读取论文全文片段

    Auth: Bearer Token (从 Sciverse 平台获取)
    """

    BASE_URL = "https://api.sciverse.space"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SCIVERSE_API_KEY", "")
        self._session = requests.Session()
        if self.api_key:
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: SearchQuery, max_results: int = 50,
               filters: Optional[Dict] = None) -> List[SearchResult]:
        """使用 /agentic-search 进行智能体语义检索。

        Args:
            query: SearchQuery 对象
            max_results: 最大返回结果数
            filters: 可选过滤条件，格式:
                {
                    "lang": "en",
                    "publication_published_year": {"gte": 2020},
                    "topics": {
                        "logic": "and",
                        "dimensions": {"primary_topic_domain": "Physical Sciences"}
                    }
                }
        """
        if not self.available:
            return []

        # 构建自然语言查询
        query_parts = [query.text]
        if query.material:
            query_parts.append(query.material)
        if query.property:
            query_parts.append(query.property)

        payload: Dict[str, Any] = {
            "query": " ".join(query_parts),
            "top_k": min(max_results, 50),
        }

        # 构建 filters（合并用户提供的和 query 自带的年份过滤）
        merged_filters = dict(filters) if filters else {}

        # 年份过滤
        year_filter = {}
        if query.year_from:
            year_filter["gte"] = query.year_from
        if query.year_to:
            year_filter["lte"] = query.year_to
        if year_filter:
            merged_filters["publication_published_year"] = year_filter

        if merged_filters:
            payload["filters"] = merged_filters

        try:
            resp = _request_with_retry(
                self._session, "POST", f"{self.BASE_URL}/agentic-search",
                json=payload, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_agentic_response(data, query)
        except requests.RequestException as e:
            # 不静默吞异常，让调用者知道 API 调用的真实状态
            import sys
            print(f"  ⚠️ Sciverse /agentic-search 调用失败: {e}", file=sys.stderr)
            return []

    def meta_search(self, query_text: str, max_results: int = 50,
                    year_from: Optional[int] = None,
                    year_to: Optional[int] = None) -> List[Dict]:
        """传统元数据搜索（REST API 直连，向后兼容）。

        直接返回原始 dict 列表而非 SearchResult，供 SciverseMCPAdapter
        等适配层使用。新代码应优先使用 search() 方法。
        """
        if not self.available:
            return []

        payload: Dict[str, Any] = {
            "query": query_text,
            "top_k": min(max_results, 50),
        }
        if year_from:
            payload.setdefault("filters", {})["publication_published_year"] = \
                payload.get("filters", {}).get("publication_published_year", {}) | {"gte": year_from}
        if year_to:
            payload.setdefault("filters", {})["publication_published_year"] = \
                payload.get("filters", {}).get("publication_published_year", {}) | {"lte": year_to}

        try:
            resp = _request_with_retry(
                self._session, "POST", f"{self.BASE_URL}/agentic-search",
                json=payload, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", data.get("hits", []))
        except requests.RequestException:
            return []

    def semantic_search(self, query_text: str, top_k: int = 10,
                        mode: str = "balanced") -> List[Dict]:
        """语义块检索（用于深度 RAG 阅读）。

        Args:
            query_text: 自然语言查询
            top_k: 返回块数（最大 30）
            mode: 'fast' | 'balanced' | 'quality'

        Returns:
            [{"chunk_id": ..., "doc_id": ..., "title": ..., "chunk": ..., "score": ...}]
        """
        if not self.available:
            return []

        payload = {"query": query_text, "top_k": min(top_k, 30), "mode": mode}
        try:
            resp = _request_with_retry(
                self._session, "POST", f"{self.BASE_URL}/agentic-search",
                json=payload, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("hits", [])
        except requests.RequestException:
            return []

    def read_content(self, doc_id: str, offset: int = 0, limit: int = 4096) -> Optional[str]:
        """读取论文全文片段。"""
        if not self.available:
            return None
        try:
            resp = _request_with_retry(
                self._session, "GET", f"{self.BASE_URL}/content",
                params={"doc_id": doc_id, "offset": offset, "limit": min(limit, 16384)},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("text", "")
        except requests.RequestException:
            return None

    def _parse_agentic_response(self, data: Dict, query: SearchQuery) -> List[SearchResult]:
        """解析 /agentic-search 返回的搜索结果。

        优先提取真实 ID：DOI（多种字段/嵌套/URL 形式均可识别）或
        Sciverse 论文 ID（doc_id 等），绝不用标题截断字符串充当 ID。
        同时兼容 Sciverse 返回的实际字段名（author / publication_published_year /
        publication_venue_name_unified 等）。
        """
        results = []
        items = data.get("results", data.get("hits", data.get("data", [])))
        if not isinstance(items, list):
            # 防御：返回格式异常（如 dict/None）时退化为空列表，不抛异常
            items = []
        for item in items:
            try:
                authors = item.get("authors", [])
                if isinstance(authors, str):
                    authors = [a.strip() for a in authors.split(",") if a.strip()]
                elif not isinstance(authors, list):
                    authors = []
                if not authors:
                    # Sciverse 将作者列表放在小写 "author" 字段
                    raw_authors = item.get("author") or []
                    if isinstance(raw_authors, list):
                        authors = [a.strip() for a in raw_authors
                                   if isinstance(a, str) and a.strip()]

                score = item.get("score", item.get("relevance", 0.0))
                if not score:
                    cc = item.get("citation_count", 0)
                    try:
                        score = float(cc) / 1000.0
                    except (TypeError, ValueError):
                        # citation_count 可能是字符串/对象，安全降级
                        score = 0.0
                try:
                    score_f = float(score) if score else 0.5
                except (TypeError, ValueError):
                    # Sciverse score 字段可能为字符串/对象，安全降级为默认分，
                    # 避免整条论文被跳过（2026-08 修复：10 条→0 条的元凶）
                    score_f = 0.5

                # 真实 ID：优先 DOI，其次 Sciverse 论文 ID（doc_id 等）
                doi = _extract_doi(item)
                paper_id = (item.get("doc_id") or item.get("paper_id")
                            or item.get("sciverse_id") or None)
                if isinstance(paper_id, str):
                    paper_id = paper_id.strip() or None

                year = (item.get("year") or item.get("publication_year")
                        or item.get("publication_published_year"))
                journal = (item.get("journal") or item.get("publication_venue_name")
                           or item.get("publication_venue_name_unified"))
                results.append(SearchResult(
                    title=item.get("title", "") or "",
                    authors=authors,
                    abstract=item.get("abstract", item.get("description", "")),
                    year=year,
                    doi=doi,
                    url=item.get("url") or (f"https://doi.org/{doi}" if doi else ""),
                    source="sciverse",
                    score=score_f,
                    citation_count=item.get("citation_count", 0),
                    journal=journal,
                    keywords=item.get("keywords", []),
                    paper_id=paper_id,
                    raw_metadata=item,
                ))
            except Exception:
                # 单条解析失败跳过该条，避免拖垮整个数据源
                continue
        return results


# Sci-Base 缺索引降级提示：进程内仅首次完整打印"准备索引"多行说明，
# 之后每次只打印一行简短提示，避免多行说明随每次检索重复刷屏 stderr。
_SCI_BASE_INDEX_WARNED = False
_SCI_BASE_INDEX_WARN_LOCK = threading.Lock()


class SciBaseSearcher:
    """Sci-Base 数据集搜索器

    Sci-Base: HuggingFace opendatalab/Sci-Base
      - 2500万+篇论文，6000亿+ tokens
      - 覆盖含材料科学在内的10个学科
      - 支持本地索引或 HuggingFace Datasets 远程加载

    当本地无 Sci-Base 数据时，回退为关键词索引模式
    （通过 arXiv 获取论文后本地建立倒排索引）。

    本地索引就绪判定：index.json 存在于索引目录（默认 LITERATURE_CACHE_DIR）。
    准备索引（复现性支持，见 scripts/prepare_scibase.py）：
      python -X utf8 scripts/prepare_scibase.py --index <你的index.json>
      python -X utf8 scripts/prepare_scibase.py --download --limit 500
    """

    def __init__(self,
                 cache_dir: Optional[str] = None,
                 index_path: Optional[Union[str, Path]] = None):
        """初始化 Sci-Base 搜索器。

        Args:
            cache_dir: 缓存基准目录。缺省时取 LITERATURE_CACHE_DIR
                （环境变量可覆盖，默认 workspace/data/literature_cache），
                与 scripts/prepare_scibase.py 的落盘目录保持一致。
            index_path: 显式指定 index.json 路径；缺省时查
                cache_dir/index.json。
        """
        if cache_dir is None:
            cache_dir = os.environ.get(
                "LITERATURE_CACHE_DIR", "workspace/data/literature_cache"
            )
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path: Path = (
            Path(index_path) if index_path is not None
            else (self._cache_dir / "index.json")
        )
        self._index: Dict[str, List[str]] = {}  # term → [paper_ids]
        self._papers: Dict[str, Dict] = {}
        self._index_loaded = False
        if not self.available:
            # 降级提示（不阻塞检索，仅 stderr）：
            # 进程内首次打印完整的"准备索引"多行说明，之后只打印一行简短提示，
            # 避免每次检索都把多行说明重复刷屏（模块级标志 + 锁，容忍并发竞态）。
            global _SCI_BASE_INDEX_WARNED
            with _SCI_BASE_INDEX_WARN_LOCK:
                first_warn = not _SCI_BASE_INDEX_WARNED
                _SCI_BASE_INDEX_WARNED = True
            if first_warn:
                print(
                    "[Sci-Base] 本地索引未就绪(index.json 不存在)，"
                    "Sci-Base 数据源暂不可用。\n"
                    "  准备索引（二选一）：\n"
                    "    1) 已有 Sci-Base 索引文件：\n"
                    "       python -X utf8 scripts/prepare_scibase.py "
                    "--index <你的index.json路径>\n"
                    "    2) 从 HuggingFace 拉取样本构建（需 pip install datasets）：\n"
                    "       python -X utf8 scripts/prepare_scibase.py "
                    "--download --limit 500\n"
                    "  详情：python -X utf8 scripts/prepare_scibase.py",
                    file=sys.stderr,
                )
            else:
                print("[Sci-Base] 索引未就绪，本次跳过", file=sys.stderr)

    @property
    def available(self) -> bool:
        """检查 Sci-Base 是否可用（本地索引 index.json 是否存在）"""
        return self._index_path.exists()

    def search(self, query: SearchQuery, max_results: int = 50) -> List[SearchResult]:
        if not self.available:
            return []

        if not self._index_loaded:
            self._load_index()

        # 倒排索引检索
        query_terms = self._tokenize(query.text)
        if query.material:
            query_terms.extend(self._tokenize(query.material))

        paper_scores: Dict[str, float] = {}
        for term in query_terms:
            if term in self._index:
                idf = max(1.0, 1.0 / len(self._index[term]))
                for paper_id in self._index[term]:
                    paper_scores[paper_id] = paper_scores.get(paper_id, 0) + idf

        # Sort by score and convert
        sorted_papers = sorted(paper_scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for paper_id, score in sorted_papers[:max_results]:
            if paper_id in self._papers:
                paper = self._papers[paper_id]
                results.append(SearchResult(
                    title=paper.get("title", ""),
                    authors=paper.get("authors", []),
                    abstract=paper.get("abstract", ""),
                    year=paper.get("year"),
                    doi=paper.get("doi"),
                    source="scibase",
                    score=min(score / 10.0, 1.0),
                    keywords=paper.get("keywords", []),
                    raw_metadata=paper,
                ))
        return results

    def build_index_from_papers(self, papers: List[Dict]):
        """从论文列表构建本地倒排索引"""
        self._papers = {}
        self._index = {}
        for i, paper in enumerate(papers):
            pid = paper.get("doi") or paper.get("id") or f"paper_{i}"
            self._papers[pid] = paper
            text = f"{paper.get('title','')} {paper.get('abstract','')}"
            for term in set(self._tokenize(text)):
                if term not in self._index:
                    self._index[term] = []
                self._index[term].append(pid)
        self._save_index()
        self._index_loaded = True

    def _load_index(self):
        try:
            index_file = self._index_path
            papers_file = self._index_path.parent / "papers.json"
            if index_file.exists():
                self._index = json.loads(index_file.read_text())
            if papers_file.exists():
                self._papers = json.loads(papers_file.read_text())
            self._index_loaded = True
        except Exception:
            self._index = {}
            self._papers = {}
            self._index_loaded = True

    def _save_index(self):
        try:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            _cache_write_json(self._index_path, self._index)
            _cache_write_json(self._index_path.parent / "papers.json", self._papers)
        except Exception:
            pass

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """简单分词 + 去停用词"""
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "on",
                     "to", "for", "with", "and", "or", "by", "from", "at", "as", "be",
                     "this", "that", "it", "its", "we", "our", "their", "has", "have",
                     "been", "can", "may", "will", "would", "could", "should"}
        text = re.sub(r'[^\w\s-]', ' ', text.lower())
        tokens = []
        for token in text.split():
            token = token.strip()
            if len(token) > 2 and token not in stopwords:
                tokens.append(token)
        return tokens


class SemanticScholarSearcher:
    """Semantic Scholar API 搜索器（免费，无需 API Key）

    使用 Semantic Scholar Academic Graph API:
      https://api.semanticscholar.org/graph/v1/paper/search

    支持 title/abstract 检索，返回 DOI、引用数、发表年份。
    注意 rate limit：无 API Key 时每秒 1 个请求。
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, cache_dir: Optional[str] = None):
        self._session = requests.Session()
        self._last_request = 0.0
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: SearchQuery, max_results: int = 50) -> List[SearchResult]:
        """通过 Semantic Scholar API 检索论文。

        Args:
            query: 搜索查询对象
            max_results: 最大返回结果数（API 限制 100 条/页）

        Returns:
            List[SearchResult]
        """
        # 构建查询字符串（合并主查询 + 材料 + 性质）
        query_text = query.text
        if query.material:
            query_text += f" {query.material}"
        if query.property:
            query_text += f" {query.property}"

        # Rate limiting：无 API Key 时每秒 1 个请求
        elapsed = time.time() - self._last_request
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        params = {
            "query": query_text,
            "limit": min(max_results, 100),
            "fields": "title,authors,abstract,year,externalIds,citationCount,journal,url",
        }

        # 检查缓存
        cache_key = None
        if self._cache_dir:
            key_str = f"s2_{hashlib.md5(str(params).encode()).hexdigest()[:16]}"
            cache_key = self._cache_dir / f"{key_str}.json"
            if cache_key.exists():
                data = _cache_read_json(cache_key)
                if data is not None:
                    return [_dict_to_result(d) for d in data]

        try:
            resp = _request_with_retry(
                self._session, "GET", self.BASE_URL, params=params, timeout=30,
            )
            self._last_request = time.time()
            resp.raise_for_status()
            data = resp.json()
            results = self._parse_response(data, query)

            # 缓存结果
            if cache_key:
                _cache_write_json(cache_key, [r.to_dict() for r in results])

            return results
        except requests.RequestException:
            return []

    def _parse_response(self, data: Dict, query: SearchQuery) -> List[SearchResult]:
        """解析 Semantic Scholar API 响应。"""
        results = []
        for item in data.get("data", []):
            # 提取 DOI
            external_ids = item.get("externalIds", {}) or {}
            doi = external_ids.get("DOI", "")

            # 提取作者列表
            authors_raw = item.get("authors", [])
            authors = [a.get("name", "") for a in authors_raw] if authors_raw else []

            # 发表年份
            year = item.get("year")

            # 引用数
            citation_count = item.get("citationCount", 0)

            # 期刊信息
            journal_info = item.get("journal", {}) or {}
            journal = journal_info.get("name", "")

            # 计算相关度分数
            score = self._compute_score(item, query)

            results.append(SearchResult(
                title=item.get("title", ""),
                authors=authors,
                abstract=item.get("abstract", ""),
                year=year,
                doi=doi,
                url=f"https://doi.org/{doi}" if doi else item.get("url", ""),
                source="semantic_scholar",
                score=score,
                citation_count=citation_count,
                journal=journal,
                raw_metadata=item,
            ))
        return results

    @staticmethod
    def _compute_score(item: Dict, query: SearchQuery) -> float:
        """基于文本匹配和引用数的相关度分数。"""
        score = 0.3  # 基础分
        title = (item.get("title") or "").lower()
        abstract = (item.get("abstract") or "").lower()
        query_lower = query.text.lower()

        # 标题关键词匹配
        query_terms = set(query_lower.split())
        title_terms = set(title.split())
        if query_terms:
            overlap = len(query_terms & title_terms) / len(query_terms)
            score += overlap * 0.4

        # 摘要关键词匹配
        if any(term in abstract for term in query_terms if len(term) > 3):
            score += 0.2

        # 引用数加成（高引用论文加权）
        citation_count = item.get("citationCount", 0)
        if citation_count > 0:
            # 对数缩放：100引用≈0.1，1000引用≈0.15
            import math
            score += min(math.log10(citation_count + 1) / 10, 0.15)

        # 材料/性质额外加成
        if query.material and query.material.lower() in abstract:
            score += 0.1
        if query.property and query.property.lower() in abstract:
            score += 0.1

        return min(score, 1.0)


# ═══════════════════════════════════════════════════════════════
# Unified Search Interface
# ═══════════════════════════════════════════════════════════════

class LiteratureSearcher:
    """统一文献检索入口。

    多源并发检索，自动去重合并，按相关度排序。
    搜索日志完整记录，构成可审计证据链。

    用法:
        searcher = LiteratureSearcher()
        results = searcher.search("MOF materials for CO2 capture", top_k=30)
        for r in results:
            print(r.to_markdown())
    """

    def __init__(self,
                 sciverse_api_key: Optional[str] = None,
                 cache_dir: Optional[str] = "workspace/data/literature_cache"):
        # 显式解析 Sciverse key（.api_key 文件 / 环境变量 / 参数），
        # 不依赖调用方是否预先 import utils.config —— 否则独立脚本/测试中
        # Sciverse 会因环境变量未注入而静默不可用（available=False 走不到适配器）。
        try:
            from utils.config import _SCIVERSE_KEY as _cfg_sciverse_key
        except Exception:
            _cfg_sciverse_key = ""
        effective_key = (
            sciverse_api_key
            or _cfg_sciverse_key
            or os.environ.get("SCIVERSE_API_KEY", "")
            or None
        )
        self._arxiv = ArxivSearcher(cache_dir=cache_dir)
        self._sciverse = SciverseSearcher(api_key=effective_key)
        self._scibase = SciBaseSearcher(cache_dir=cache_dir)
        self._semantic_scholar = SemanticScholarSearcher(cache_dir=cache_dir)
        self._cache_dir = Path(cache_dir or "workspace/data/literature_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._search_log: List[Dict] = []
        # 数据源熔断器：某源连续失败（异常/超时）达阈值后，本次进程内跳过该源
        # （2026-08 修复：Semantic Scholar 持续超时/连接重置拖垮预算）
        self._source_failures: Dict[str, int] = {}
        self._source_breaker_threshold = 2

        # ── Sciverse MCP/Skill 适配器 ──
        # 优先尝试 MCP/Skill 接入，不可用时回退到 REST API 直连
        self._sciverse_adapter = None
        self._sciverse_adapter_mode = "rest"  # 实际使用模式: "mcp" | "skill" | "rest"
        try:
            create_adapter, _ = _get_adapter_module()
            self._sciverse_adapter = create_adapter(
                api_key=effective_key,
            )
            if self._sciverse_adapter.available:
                self._sciverse_adapter_mode = self._sciverse_adapter.mode
        except Exception:
            # MCP/Skill 模块加载失败，静默回退到 REST API
            pass

    @property
    def available_sources(self) -> List[str]:
        sources = ["arxiv", "semantic_scholar"]  # 两个始终可用的免费源
        if self._sciverse.available or (
            self._sciverse_adapter is not None and self._sciverse_adapter.available
        ):
            # 标注来源类型：通过 MCP/Skill 接入还是直连 REST API
            label = f"sciverse({self._sciverse_adapter_mode})"
            sources.append(label)
        if self._scibase.available:
            sources.append("scibase")
        return sources

    def search(self,
               query_text: str,
               top_k: int = 30,
               material: Optional[str] = None,
               property_name: Optional[str] = None,
               method: Optional[str] = None,
               year_from: Optional[int] = None,
               year_to: Optional[int] = None,
               sources: Optional[List[str]] = None,
               ) -> List[SearchResult]:
        """执行多源文献检索。

        Args:
            query_text: 自然语言检索查询
            top_k: 返回结果数
            material: 材料名称（可选，增强检索精度）
            property_name: 目标性质（可选）
            method: 方法名（可选）
            year_from: 起始年份
            year_to: 截止年份
            sources: 指定数据源列表，默认全部可用源

        Returns:
            去重合并后的 SearchResult 列表，按相关度降序排列
        """
        query = SearchQuery(
            text=query_text,
            material=material,
            property=property_name,
            method=method,
            year_from=year_from,
            year_to=year_to,
            top_k=top_k,
        )

        # Parse structured entities from query
        query.parsed_entities = self._parse_query_entities(query_text)

        sources = sources or self.available_sources
        t_start = time.time()

        # 确定 Sciverse 来源的实际名称及是否走适配器路径
        sciverse_source = None
        for s in sources:
            if s.startswith("sciverse"):
                sciverse_source = s
                break

        # 只要有可用适配器（MCP / Skill / REST），统一走适配器路径，
        # 保证每次 Sciverse API 调用都写入审计日志（README 承诺）
        use_adapter = (
            sciverse_source is not None
            and self._sciverse_adapter is not None
            and self._sciverse_adapter.available
        )

        # 并发多源检索
        all_results: List[SearchResult] = []
        executor = ThreadPoolExecutor(max_workers=4)
        try:
            futures = {}
            if "arxiv" in sources:
                futures[executor.submit(self._arxiv.search, query, top_k)] = "arxiv"
            if sciverse_source:
                if use_adapter:
                    # 通过 MCP/Skill/REST 适配器调用，自动记录审计日志
                    futures[executor.submit(
                        self._sciverse_adapter_search, query, top_k
                    )] = sciverse_source
                elif self._sciverse.available:
                    # 适配器不可用时的最后兜底：传统 REST API 直连
                    futures[executor.submit(
                        self._sciverse.search, query, top_k
                    )] = sciverse_source
            if "scibase" in sources and self._scibase.available:
                futures[executor.submit(self._scibase.search, query, top_k)] = "scibase"
            if "semantic_scholar" in sources:
                if self._source_failures.get("semantic_scholar", 0) >= self._source_breaker_threshold:
                    # 熔断：连续失败达阈值，本轮不再调用该源（省预算）
                    print(f"  ⚠️ semantic_scholar 连续失败 "
                          f"{self._source_failures['semantic_scholar']} 次，本轮熔断跳过",
                          file=sys.stderr)
                else:
                    futures[executor.submit(
                        self._semantic_scholar.search, query, top_k
                    )] = "semantic_scholar"

            try:
                completed_iter = as_completed(futures, timeout=SEARCH_SOURCE_TIMEOUT)
                for future in completed_iter:
                    source_name = futures[future]
                    try:
                        results = future.result()
                        # 成功：熔断计数清零
                        self._source_failures[source_name] = 0
                        if results:
                            all_results.extend(results)
                    except Exception as e:
                        # 单个源失败不阻断整体流程，但不再静默吞掉——
                        # 打印警告 + 熔断计数（连续失败达阈值后本轮跳过该源）
                        self._source_failures[source_name] = (
                            self._source_failures.get(source_name, 0) + 1
                        )
                        print(f"  ⚠️ [{time.strftime('%Y-%m-%dT%H:%M:%S')}] "
                              f"数据源 {source_name} 检索失败（已跳过，连续失败 "
                              f"{self._source_failures[source_name]} 次）: {e}",
                              file=sys.stderr)
            except TimeoutError:
                # 有数据源超过软超时：放弃等待，保住时间预算；未完成源计入失败
                print(f"  ⚠️ 部分数据源超过 {SEARCH_SOURCE_TIMEOUT:.0f}s 软超时，放弃等待",
                      file=sys.stderr)
                for future in list(futures):
                    if not future.done():
                        src = futures[future]
                        self._source_failures[src] = self._source_failures.get(src, 0) + 1
            # 未完成的任务取消，避免线程滞留后台
            for future in list(futures):
                if not future.done():
                    future.cancel()
        finally:
            # wait=False：不等待慢源线程跑完，立即把控制权还给主循环（预算保护）
            executor.shutdown(wait=False, cancel_futures=True)

        # 去重（同 DOI 或高度相似标题）
        merged = self._deduplicate(all_results)
        merged.sort(key=lambda x: x.score, reverse=True)
        merged = merged[:top_k]

        # 记录搜索日志（审计证据链）
        self._log_search(query_text, sources, len(merged), time.time() - t_start)

        return merged

    def smart_search(self,
                     research_question: str,
                     top_k: int = 30) -> List[SearchResult]:
        """智能检索 — 自动解析研究问题中的实体并构造查询。

        Args:
            research_question: 研究问题描述
            top_k: 返回结果数

        Returns:
            搜索结果列表
        """
        entities = self._parse_query_entities(research_question)
        return self.search(
            query_text=research_question,
            top_k=top_k,
            material=entities.get("material"),
            property_name=entities.get("property"),
            method=entities.get("method"),
        )

    def search_by_paper(self,
                        title: str,
                        abstract: str = "",
                        top_k: int = 20) -> List[SearchResult]:
        """基于一篇论文检索相关工作。

        Args:
            title: 论文标题
            abstract: 论文摘要
            top_k: 返回结果数
        """
        # 从标题+摘要中提取关键实体作为查询
        combined = f"{title}. {abstract}"
        entities = self._parse_query_entities(combined)
        query_parts = [title[:100]]  # 用标题主干做精确匹配
        if entities.get("material"):
            query_parts.append(entities["material"])
        if entities.get("property"):
            query_parts.append(f"{entities['material']} {entities['property']}")
        return self.search(" ".join(query_parts), top_k=top_k,
                          material=entities.get("material"),
                          property_name=entities.get("property"))

    # ── 内部方法 ──

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """基于 DOI（规范化后）和标题相似度的去重合并。

        Crossref 与 Sciverse 返回同一篇论文时，即使 DOI 大小写/前缀不同、
        或其中一条缺 DOI，也能正确合并为一条，并补齐 DOI/论文 ID 等字段，
        避免下游以标题截断字符串充当论文 ID。
        """
        seen_dois: Dict[str, SearchResult] = {}
        seen_titles: Dict[str, SearchResult] = {}
        merged: List[SearchResult] = []

        for r in results:
            # DOI 精确匹配（先规范化，统一小写/去前缀）
            norm_doi = _normalize_doi(r.doi)
            if norm_doi:
                # 有 DOI：只按 DOI 去重——DOI 是唯一标识，标题相似不代表同一篇论文
                # （2026-08 修复：3-gram 标题相似度会把 'Real Paper 0'..'Real Paper 9'
                #  这类同前缀的不同论文误合并成 1 条，导致 Sciverse 10 条→1 条）
                if norm_doi in seen_dois:
                    self._merge_result(seen_dois[norm_doi], r)
                    continue
                seen_dois[norm_doi] = r
                seen_titles[self._normalize_title(r.title)] = r  # 供无 DOI 记录匹配
                merged.append(r)
                continue

            # 无 DOI：按标题相似度去重（高阈值，仅作兜底）
            norm_title = self._normalize_title(r.title)
            dup_found = False
            for existing_title, existing in seen_titles.items():
                if self._title_similarity(norm_title, existing_title) > 0.9:
                    self._merge_result(existing, r)
                    dup_found = True
                    break

            if dup_found:
                continue

            seen_titles[norm_title] = r
            merged.append(r)

        return merged

    @staticmethod
    def _merge_result(existing: SearchResult, r: SearchResult) -> None:
        """合并去重命中的两条记录：取更高分并补齐缺失字段。

        同一篇论文的一条记录可能缺少 DOI（如 Sciverse 未返回），
        另一条有 DOI（如 Crossref），合并后统一补到保留的记录上，
        避免下游以标题截断字符串充当论文 ID。
        """
        existing.score = max(existing.score, r.score)
        if r.doi and not existing.doi:
            existing.doi = r.doi
        if r.paper_id and not existing.paper_id:
            existing.paper_id = r.paper_id
        if r.full_text_snippet and not existing.full_text_snippet:
            existing.full_text_snippet = r.full_text_snippet
        if r.abstract and not existing.abstract:
            existing.abstract = r.abstract
        if r.year and not existing.year:
            existing.year = r.year
        if r.authors and not existing.authors:
            existing.authors = r.authors
        if r.journal and not existing.journal:
            existing.journal = r.journal
        if not existing.citation_count and r.citation_count:
            existing.citation_count = r.citation_count

    @staticmethod
    def _normalize_title(title: str) -> str:
        return re.sub(r'[^a-z0-9\s]', '', title.lower()).strip()

    @staticmethod
    def _title_similarity(t1: str, t2: str) -> float:
        """基于 3-gram Jaccard 的标题相似度"""
        def ngrams(s, n=3):
            return set(s[i:i+n] for i in range(len(s)-n+1))
        g1, g2 = ngrams(t1), ngrams(t2)
        if not g1 or not g2:
            return 0.0
        return len(g1 & g2) / len(g1 | g2)

    def _parse_query_entities(self, text: str) -> Dict[str, Any]:
        """从查询文本中解析材料/性质/方法实体。

        使用正则 + 关键词匹配进行初步 NER。更精确的实体识别
        由 LLM 驱动的 extractor 模块完成。
        """
        entities: Dict[str, Any] = {}

        # 常见材料模式（化学式 + 材料名）
        material_patterns = [
            r'\b[A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*)+\b',  # 化学式如 MAPbI3, TiO2
            r'\b(?:perovskite|MOF|zeolite|graphene|carbon nanotube|'
            r'MXene|TMD|HEA|metal-organic framework|'
            r'covalent organic framework|COF|QD|quantum dot|'
            r'nanoparticle|nanowire|thin film|bulk|2D material)\b',
        ]
        materials = []
        for pat in material_patterns:
            materials.extend(re.findall(pat, text, re.IGNORECASE))
        if materials:
            entities["material"] = materials[0]  # 取第一个作为主材料

        # 常见性质模式
        property_patterns = [
            r'\b(?:band gap|conductivity|thermal conductivity|'
            r'electrical conductivity|mechanical strength|hardness|'
            r'catalytic activity|stability|efficiency|PCE|'
            r'power conversion efficiency|figure of merit|ZT|'
            r'carrier mobility|Seebeck coefficient|capacity|'
            r'energy density|power density|corrosion resistance|'
            r'adsorption capacity|selectivity|conversion rate|'
            r'yield|degradation|phase transition|magnetic)\b',
        ]
        properties = []
        for pat in property_patterns:
            properties.extend(re.findall(pat, text, re.IGNORECASE))
        if properties:
            entities["property"] = properties[0]

        # 常见方法模式
        method_patterns = [
            r'\b(?:DFT|density functional theory|molecular dynamics|MD|'
            r'Monte Carlo|MCTS|genetic algorithm|Bayesian optimization|'
            r'machine learning|deep learning|neural network|GNN|'
            r'graph neural network|transfer learning|active learning|'
            r'high-throughput|combinatorial|sol-gel|hydrothermal|'
            r'CVD|PVD|ALD|MBE|sputtering|electrodeposition|'
            r'XRD|TEM|SEM|AFM|XPS|NMR|Raman|FTIR)\b',
        ]
        methods = []
        for pat in method_patterns:
            methods.extend(re.findall(pat, text, re.IGNORECASE))
        if methods:
            entities["method"] = methods[0]

        return entities

    def _sciverse_adapter_search(self, query: SearchQuery, top_k: int) -> List[SearchResult]:
        """通过 MCP/Skill 适配器执行 Sciverse 检索。

        适配器自动记录审计日志到 workspace/logs/sciverse_skill_log.jsonl。
        返回已解析的 SearchResult 列表。

        Args:
            query: 搜索查询对象
            top_k: 最大返回结果数

        Returns:
            List[SearchResult] — 由适配器返回的原始结果解析而来
        """
        adapter = self._sciverse_adapter
        try:
            result = adapter.search(
                query.text,
                top_k=top_k,
                year_from=query.year_from,
                year_to=query.year_to,
            )
        except Exception as e:
            print(f"  ⚠️ Sciverse({self._sciverse_adapter_mode}) 适配器检索异常: {e}",
                  file=sys.stderr)
            return []
        if not isinstance(result, dict):
            print(f"  ⚠️ Sciverse({self._sciverse_adapter_mode}) 返回结构异常: {type(result)}",
                  file=sys.stderr)
            return []
        raw_items = result.get("results", [])

        # 复用 SciverseSearcher 的响应解析逻辑，保证输出格式一致
        # 解析内部已做逐条防御，单条失败不会拖垮整个源
        parsed = self._sciverse._parse_agentic_response(
            {"results": raw_items}, query
        )

        # 使用适配器模式标注来源
        for r in parsed:
            r.source = f"sciverse({self._sciverse_adapter_mode})"

        return parsed

    def _log_search(self, query: str, sources: List[str],
                    result_count: int, elapsed: float):
        """记录搜索日志（审计证据链）"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "query": query,
            "sources": sources or self.available_sources,
            "result_count": result_count,
            "elapsed_seconds": round(elapsed, 2),
            "sciverse_adapter_mode": self._sciverse_adapter_mode,
        }
        self._search_log.append(entry)

        # 持久化日志
        log_path = self._cache_dir / "search_log.jsonl"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # 日志写入失败不应静默吞掉
            import sys
            print(f"  ⚠️ search_log 写入失败 ({log_path}): {e}", file=sys.stderr)

    def get_search_log(self) -> List[Dict]:
        return self._search_log

    def export_results(self, results: List[SearchResult],
                       format: str = "markdown") -> str:
        """导出检索结果为 Markdown 或 JSON"""
        if format == "json":
            return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
        else:
            header = f"# Literature Search Results\n\n"
            header += f"**Query:** {self._search_log[-1]['query'] if self._search_log else 'N/A'}\n"
            header += f"**Sources:** {', '.join(self._search_log[-1]['sources']) if self._search_log else 'N/A'}\n"
            header += f"**Results:** {len(results)}\n\n---\n\n"
            return header + "\n".join(r.to_markdown() for r in results)


# ═══════════════════════════════════════════════════════════════
# arXiv XML Parser
# ═══════════════════════════════════════════════════════════════

def _parse_arxiv_xml(xml_text: str) -> List[SearchResult]:
    """解析 arXiv API 返回的 Atom XML"""
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'arxiv': 'http://arxiv.org/schemas/atom',
    }
    root = ET.fromstring(xml_text)
    results = []
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns)
        title_text = title.text.strip().replace('\n', ' ') if title is not None and title.text else ""

        abstract = entry.find('atom:summary', ns)
        abstract_text = abstract.text.strip().replace('\n', ' ') if abstract is not None and abstract.text else ""

        authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)
                   if a.find('atom:name', ns) is not None]

        doi = None
        for link in entry.findall('atom:link', ns):
            href = link.get('href', '')
            if 'doi.org' in href:
                doi = href.split('doi.org/')[-1]

        published = entry.find('atom:published', ns)
        year = int(published.text[:4]) if published is not None and published.text else None

        pdf_url = None
        for link in entry.findall('atom:link', ns):
            if link.get('title') == 'pdf':
                pdf_url = link.get('href')
                break

        journal = entry.find('arxiv:journal_ref', ns)
        journal_text = journal.text.strip() if journal is not None and journal.text else None

        results.append(SearchResult(
            title=title_text,
            authors=authors,
            abstract=abstract_text,
            year=year,
            doi=doi,
            url=f"https://arxiv.org/abs/{entry.find('atom:id', ns).text.split('/')[-1]}" if entry.find('atom:id', ns) is not None else None,
            source="arxiv",
            score=0.0,  # Will be set by caller
            journal=journal_text,
            pdf_url=pdf_url,
        ))
    return results


def _dict_to_result(d: Dict) -> SearchResult:
    return SearchResult(**{k: v for k, v in d.items() if k in SearchResult.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════
# Quick Test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    searcher = LiteratureSearcher()
    print(f"Available sources: {searcher.available_sources}")

    results = searcher.search("perovskite solar cell stability", top_k=5)
    print(f"\nFound {len(results)} results:\n")
    for r in results:
        print(r.to_markdown())
        print("---")
