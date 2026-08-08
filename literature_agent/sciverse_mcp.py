"""
Sciverse MCP/Skill 适配层
=========================

为 Sciverse 科学文献检索提供 MCP (Model Context Protocol) 和 Skill 两种接入模式，
同时保留 REST API 直连作为兜底方案。

设计原则：
  - 轻量级：零外部依赖，仅使用标准库 + requests
  - 审计优先：每次调用自动生成带时间戳、参数哈希、结果摘要的审计日志
  - 自动回退：MCP 不可用 → Skill 不可用 → REST API 直连
  - 向后兼容：与现有 SciverseSearcher 的 REST API 格式完全兼容

检测顺序：
  1. 环境变量 SCIVERSE_MCP_URL → 走 MCP 协议
  2. 环境变量 SCIVERSE_SKILL_PATH → 走本地 Skill 脚本
  3. 否则 → 走 SciverseSearcher REST API 直连（现有实现）

用法:
    from literature_agent.sciverse_mcp import create_sciverse_adapter

    adapter = create_sciverse_adapter()
    results = adapter.search("MOF CO2 capture", top_k=10)
    # adapter.mode 可查看当前使用的接入模式: "mcp" / "skill" / "rest"
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


# ═══════════════════════════════════════════════════════════════
# 中国时区 (UTC+8)
# ═══════════════════════════════════════════════════════════════

CST = timezone(timedelta(hours=8))


def _cst_now() -> str:
    """返回中国标准时间 ISO 格式字符串"""
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


# ═══════════════════════════════════════════════════════════════
# HTTP 请求重试工具（429 / 5xx 指数退避）
# ═══════════════════════════════════════════════════════════════

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
    所有重试耗尽后抛出最后一次异常，由调用方写入审计记录的 error 字段。

    限流增强（2026-08，与 search.py 的 _request_with_retry 保持一致）：
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
                print(f"  ⚠️ [{_cst_now()}] Sciverse 请求异常（第 {attempt}/{max_attempts} 次）: "
                      f"{method} {url} → {e}；{delay:.1f}s 后重试", file=sys.stderr)
                time.sleep(delay)
                continue
            raise
        # 429 限流或 5xx 服务端错误 → 指数退避（含 Retry-After/jitter）后重试
        if resp.status_code == 429 or resp.status_code >= 500:
            limit = max_attempts_429 if resp.status_code == 429 else max_attempts
            if attempt < limit:
                retry_after = _parse_retry_after(resp)
                delay = _retry_delay(retry_base, attempt, retry_after)
                ra_txt = (f"，Retry-After {retry_after:.0f}s"
                          if retry_after is not None else "")
                print(f"  ⚠️ [{_cst_now()}] Sciverse 请求返回 {resp.status_code}（第 {attempt}/{limit} 次）: "
                      f"{method} {url}{ra_txt}；{delay:.1f}s 后重试", file=sys.stderr)
                time.sleep(delay)
                continue
            resp.raise_for_status()  # 最后一次仍失败 → 抛出 HTTPError
        return resp
    raise last_exc  # 防御性代码，理论上不可达


# ═══════════════════════════════════════════════════════════════
# 审计追踪数据模型
# ═══════════════════════════════════════════════════════════════

@dataclass
class AuditRecord:
    """单次 API 调用的审计记录。

    无论是通过 MCP、Skill 还是 REST 调用，均生成此记录。
    每条记录包含调用时间、参数哈希、结果摘要，构成可追溯的证据链。
    """
    call_id: str                           # 唯一调用 ID (基于时间戳+参数哈希)
    timestamp: str                         # 中国标准时间 ISO 格式
    adapter_mode: str                      # "mcp" | "skill" | "rest"
    tool_name: str                         # 调用工具名 ("search" | "semantic_search" | "read_content")
    parameters_hash: str                   # 参数的 SHA256 前 16 位
    parameters_summary: Dict[str, Any]     # 参数摘要（脱敏后）
    result_count: int                      # 返回结果数量
    result_summary: str                    # 结果摘要（如论文标题列表截断）
    elapsed_ms: float                      # 调用耗时（毫秒）
    error: Optional[str] = None            # 错误信息（如有）


@dataclass
class MCPMetadata:
    """MCP 标准元数据——附加在每次返回值上的审计信息。

    对应 MCP 协议中的 metadata 字段，天然构成审计证据链。
    """
    call_id: str
    timestamp: str
    tool: str
    parameters_hash: str
    result_count: int
    adapter_mode: str


# ═══════════════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════════════

class BaseSciverseAdapter(ABC):
    """Sciverse 适配器抽象基类。

    所有接入模式（MCP / Skill / REST）均实现此接口，
    保证上层调用无需感知底层接入方式。
    """

    def __init__(self, mode: str):
        self.mode = mode  # "mcp" | "skill" | "rest"
        self._audit_log: List[AuditRecord] = []
        self._log_path: Optional[Path] = None

    @property
    @abstractmethod
    def available(self) -> bool:
        """当前适配器是否可用"""
        ...

    @abstractmethod
    def search(self, query_text: str, top_k: int = 50,
               year_from: Optional[int] = None, year_to: Optional[int] = None,
               **kwargs) -> Dict[str, Any]:
        """执行文献检索。

        Returns:
            Dict with keys:
              - "results": List of result dicts (title, authors, abstract, doi, year, score, ...)
              - "_mcp_metadata": MCPMetadata (审计追踪)
        """
        ...

    @abstractmethod
    def semantic_search(self, query_text: str, top_k: int = 10,
                        mode: str = "balanced", **kwargs) -> Dict[str, Any]:
        """语义块检索（用于深度 RAG 阅读）。

        Returns:
            Dict with keys: "hits" (list), "_mcp_metadata"
        """
        ...

    @abstractmethod
    def read_content(self, doc_id: str, offset: int = 0,
                     limit: int = 4096, **kwargs) -> Dict[str, Any]:
        """读取论文全文片段。

        Returns:
            Dict with keys: "text" (str), "_mcp_metadata"
        """
        ...

    # ── 审计日志基础设施 ──

    def _make_audit_record(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result_count: int,
        result_summary: str,
        elapsed_ms: float,
        error: Optional[str] = None,
    ) -> AuditRecord:
        """构建一条审计记录"""
        params_str = json.dumps(parameters, sort_keys=True, ensure_ascii=False)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        call_id = f"{tool_name}-{params_hash}-{int(time.time() * 1000)}"

        return AuditRecord(
            call_id=call_id,
            timestamp=_cst_now(),
            adapter_mode=self.mode,
            tool_name=tool_name,
            parameters_hash=params_hash,
            parameters_summary=self._summarize_params(parameters),
            result_count=result_count,
            result_summary=result_summary,
            elapsed_ms=round(elapsed_ms, 2),
            error=error,
        )

    def _make_metadata(self, audit: AuditRecord) -> MCPMetadata:
        """从审计记录生成 MCP 标准元数据"""
        return MCPMetadata(
            call_id=audit.call_id,
            timestamp=audit.timestamp,
            tool=audit.tool_name,
            parameters_hash=audit.parameters_hash,
            result_count=audit.result_count,
            adapter_mode=self.mode,
        )

    @staticmethod
    def _summarize_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """生成参数摘要（对敏感值脱敏）"""
        summary = {}
        for k, v in params.items():
            if k in ("api_key", "token", "authorization"):
                summary[k] = "***REDACTED***"
            elif isinstance(v, str) and len(v) > 200:
                summary[k] = v[:200] + "..."
            else:
                summary[k] = v
        return summary

    @staticmethod
    def _make_result_summary(results: List[Dict], max_items: int = 5) -> str:
        """生成结果摘要——取前几篇论文的标题"""
        if not results:
            return "(empty)"
        titles = [r.get("title", str(r))[:80] for r in results[:max_items]]
        suffix = f" ... (+{len(results) - max_items} more)" if len(results) > max_items else ""
        return " | ".join(titles) + suffix

    def _record_and_return(
        self,
        tool_name: str,
        params: Dict[str, Any],
        data: Dict[str, Any],
        t_start: float,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录审计日志并附加 MCP 元数据后返回"""
        elapsed_ms = (time.time() - t_start) * 1000
        results = data.get("results") or data.get("hits") or []
        result_count = len(results) if isinstance(results, list) else (1 if data.get("text") else 0)
        result_summary = (
            self._make_result_summary(results) if isinstance(results, list)
            else (data.get("text", "")[:200] if data.get("text") else "")
        )

        audit = self._make_audit_record(
            tool_name=tool_name,
            parameters=params,
            result_count=result_count,
            result_summary=result_summary,
            elapsed_ms=elapsed_ms,
            error=error,
        )

        self._audit_log.append(audit)
        self._persist_audit(audit)

        data["_mcp_metadata"] = self._make_metadata(audit)
        return data

    def _persist_audit(self, audit: AuditRecord):
        """持久化审计记录到 JSONL 日志文件。

        目录自动创建；写入失败打印警告（不静默吞掉）。
        日志路径按 run_dir 隔离（2026-08 修复）：动态读取
        utils.config.LOGS_DIR（set_run_dir 后生效，如 workspace/logs/<run_dir>），
        环境变量 SURVEY_LOGS_DIR 可兜底覆盖，避免多主题审计记录混写同一文件。
        """
        try:
            from utils.config import LOGS_DIR as _cfg_logs_dir
        except Exception:
            _cfg_logs_dir = "workspace/logs"
        log_dir = Path(os.environ.get("SURVEY_LOGS_DIR", _cfg_logs_dir))
        self._log_path = log_dir / "sciverse_skill_log.jsonl"
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(audit), ensure_ascii=False) + "\n")
        except Exception as e:
            # 审计日志写入失败不应阻断主流程，但必须可见
            print(f"  ⚠️ 审计日志写入失败 ({self._log_path}): {e}", file=sys.stderr)

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """获取完整审计日志"""
        return [asdict(r) for r in self._audit_log]


# ═══════════════════════════════════════════════════════════════
# MCP 适配器：基于 Model Context Protocol 的 Sciverse 接入
# ═══════════════════════════════════════════════════════════════

class SciverseMCPAdapter(BaseSciverseAdapter):
    """MCP (Model Context Protocol) 接入适配器。

    通过 MCP 协议与 Sciverse 服务通信。
    若 MCP 端点不可用或调用失败，调用者应回退到 SciverseSkillAdapter 或 REST API。

    MCP 协议工具映射:
      - mcp://sciverse/search          → /search
      - mcp://sciverse/semantic_search → /semantic-search
      - mcp://sciverse/read_content    → /read-content

    环境变量:
      SCIVERSE_MCP_URL: MCP 服务端点 URL（如 http://localhost:8080/mcp）
    """

    def __init__(self, mcp_url: Optional[str] = None):
        super().__init__(mode="mcp")
        self._mcp_url = mcp_url or os.environ.get("SCIVERSE_MCP_URL", "")
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "PiAgent-SciverseMCP/1.0",
        })
        # 尝试传递 API Key 以认证
        api_key = os.environ.get("SCIVERSE_API_KEY", "")
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"

    @property
    def available(self) -> bool:
        if not self._mcp_url:
            return False
        try:
            # 尝试 ping MCP 端点
            resp = self._session.get(
                self._mcp_url.rstrip("/") + "/health",
                timeout=5,
            )
            return resp.status_code < 500
        except requests.RequestException:
            return False

    def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any],
                       timeout: int = 30) -> Dict[str, Any]:
        """通用 MCP 工具调用方法。

        向 MCP 端点发送 JSON-RPC 格式的 tools/call 请求。
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": hashlib.md5(str(arguments).encode()).hexdigest()[:8],
        }

        resp = _request_with_retry(
            self._session, "POST", self._mcp_url.rstrip("/"),
            json=payload, timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")

        # MCP 返回格式: {"result": {"content": [...]}}
        result = data.get("result", {})
        content = result.get("content", [])
        # 尝试提取第一个 text 内容
        if content and isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_content = item.get("text", "{}")
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError:
                        return {"raw_text": text_content}
        return result

    def search(self, query_text: str, top_k: int = 50,
               year_from: Optional[int] = None, year_to: Optional[int] = None,
               **kwargs) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "query": query_text,
            "top_k": min(top_k, 50),
        }
        year_filter = {}
        if year_from:
            year_filter["gte"] = year_from
        if year_to:
            year_filter["lte"] = year_to
        if year_filter:
            payload["filters"] = {"publication_published_year": year_filter}
        t_start = time.time()

        try:
            data = self._call_mcp_tool("search", payload)
            return self._record_and_return("search", payload, data, t_start)
        except Exception as e:
            t_start_fb = time.time()
            try:
                # 回退：MCP 失败时尝试直接 REST 调用
                data = self._rest_fallback_search(payload)
                return self._record_and_return("search", payload, data, t_start)
            except Exception as e2:
                return self._record_and_return(
                    "search", payload,
                    {"results": [], "error": str(e2)},
                    t_start, error=str(e)
                )

    def semantic_search(self, query_text: str, top_k: int = 10,
                        mode: str = "balanced", **kwargs) -> Dict[str, Any]:
        params = {
            "query": query_text,
            "top_k": min(top_k, 30),
            "mode": mode,
            **kwargs,
        }
        t_start = time.time()

        try:
            data = self._call_mcp_tool("semantic_search", params)
            data.setdefault("hits", data.get("results", []))
            return self._record_and_return("semantic_search", params, data, t_start)
        except Exception as e:
            t_start_fb = time.time()
            try:
                data = self._rest_fallback_semantic(params)
                return self._record_and_return("semantic_search", params, data, t_start)
            except Exception as e2:
                return self._record_and_return(
                    "semantic_search", params,
                    {"hits": [], "error": str(e2)},
                    t_start, error=str(e)
                )

    def read_content(self, doc_id: str, offset: int = 0,
                     limit: int = 4096, **kwargs) -> Dict[str, Any]:
        params = {
            "doc_id": doc_id,
            "offset": offset,
            "limit": min(limit, 16384),
            **kwargs,
        }
        t_start = time.time()

        try:
            data = self._call_mcp_tool("read_content", params)
            return self._record_and_return("read_content", params, data, t_start)
        except Exception as e:
            try:
                data = self._rest_fallback_content(params)
                return self._record_and_return("read_content", params, data, t_start)
            except Exception as e2:
                return self._record_and_return(
                    "read_content", params,
                    {"text": None, "error": str(e2)},
                    t_start, error=str(e)
                )

    # ── MCP 不可用时的 REST 回退 ──

    def _rest_fallback_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """REST API 回退：/agentic-search"""
        resp = _request_with_retry(
            self._session, "POST", "https://api.sciverse.space/agentic-search",
            json=payload, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _rest_fallback_semantic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """REST API 回退：/agentic-search"""
        resp = _request_with_retry(
            self._session, "POST", "https://api.sciverse.space/agentic-search",
            json=params, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _rest_fallback_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """REST API 回退：/content"""
        resp = _request_with_retry(
            self._session, "GET", "https://api.sciverse.space/content",
            params=params, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════
# Skill 适配器：将 Sciverse 检索封装为本地 Skill
# ═══════════════════════════════════════════════════════════════

class SciverseSkillAdapter(BaseSciverseAdapter):
    """Skill 接口适配器。

    将 Sciverse 检索封装为本地可调用的 Skill。
    支持两种运行模式：
      1. 调用外部 Skill 脚本（通过 SCIVERSE_SKILL_PATH 指定）
      2. 内置 REST API 回退（Skill 脚本不可用时自动切换）

    Skill 约定：
      - 输入：JSON（stdin 或 --input 参数）
      - 输出：JSON（stdout）
      - 脚本需实现 run 子命令或直接接受 JSON 参数

    环境变量:
      SCIVERSE_SKILL_PATH: Skill 脚本路径（如 /path/to/sciverse_skill.py）
    """

    def __init__(self, skill_path: Optional[str] = None):
        super().__init__(mode="skill")
        self._skill_path = skill_path or os.environ.get("SCIVERSE_SKILL_PATH", "")
        self._rest_fallback = SciverseSearcherRestAdapter()

    @property
    def available(self) -> bool:
        if self._skill_path and Path(self._skill_path).exists():
            return True
        # 即使 Skill 脚本不存在，只要 REST API 配置了 API Key 也算可用
        return self._rest_fallback.available

    def _run_skill(self, action: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """尝试通过 Skill 脚本执行操作。

        Args:
            action: 操作名 ("search", "semantic_search", "read_content")
            params: 参数字典

        Returns:
            Skill 脚本的标准输出（JSON 解析后），失败返回 None
        """
        if not self._skill_path or not Path(self._skill_path).exists():
            return None

        input_data = json.dumps({"action": action, "params": params}, ensure_ascii=False)
        try:
            result = subprocess.run(
                [sys.executable, self._skill_path, action],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError,
                FileNotFoundError, OSError):
            pass
        return None

    def search(self, query_text: str, top_k: int = 50,
               year_from: Optional[int] = None, year_to: Optional[int] = None,
               **kwargs) -> Dict[str, Any]:
        params = {
            "query": query_text,
            "page_size": min(top_k, 50),
            "page": 1,
            "year_from": year_from,
            "year_to": year_to,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        params = {k: v for k, v in params.items() if v is not None}
        t_start = time.time()

        # 优先尝试 Skill 脚本
        data = self._run_skill("search", params)
        if data is not None:
            return self._record_and_return("search", params, data, t_start)

        # 回退到 REST API
        try:
            data = self._rest_fallback.search(query_text, top_k, year_from, year_to)
            return self._record_and_return("search", params, data, t_start)
        except Exception as e:
            return self._record_and_return(
                "search", params,
                {"results": [], "error": str(e)},
                t_start, error=str(e)
            )

    def semantic_search(self, query_text: str, top_k: int = 10,
                        mode: str = "balanced", **kwargs) -> Dict[str, Any]:
        params = {
            "query": query_text,
            "top_k": min(top_k, 30),
            "mode": mode,
            **kwargs,
        }
        t_start = time.time()

        data = self._run_skill("semantic_search", params)
        if data is not None:
            data.setdefault("hits", data.get("results", []))
            return self._record_and_return("semantic_search", params, data, t_start)

        try:
            data = self._rest_fallback.semantic_search(query_text, top_k, mode)
            return self._record_and_return("semantic_search", params, data, t_start)
        except Exception as e:
            return self._record_and_return(
                "semantic_search", params,
                {"hits": [], "error": str(e)},
                t_start, error=str(e)
            )

    def read_content(self, doc_id: str, offset: int = 0,
                     limit: int = 4096, **kwargs) -> Dict[str, Any]:
        params = {"doc_id": doc_id, "offset": offset, "limit": min(limit, 16384), **kwargs}
        t_start = time.time()

        data = self._run_skill("read_content", params)
        if data is not None:
            return self._record_and_return("read_content", params, data, t_start)

        try:
            data = self._rest_fallback.read_content(doc_id, offset, limit)
            return self._record_and_return("read_content", params, data, t_start)
        except Exception as e:
            return self._record_and_return(
                "read_content", params,
                {"text": None, "error": str(e)},
                t_start, error=str(e)
            )

    def run(self, research_question: str, top_k: int = 30) -> Dict[str, Any]:
        """Skill 主入口——接收自然语言研究问题，输出结构化检索结果。

        这是 Skill 接口的核心方法，模拟真实 Skill 的 run() 约定。

        Args:
            research_question: 自然语言研究问题（如 "MOF 材料用于 CO2 捕获的
                               最新进展"）
            top_k: 最大返回结果数

        Returns:
            {
                "question": str,
                "results": List[Dict],
                "result_count": int,
                "_mcp_metadata": MCPMetadata,
            }
        """
        t_start = time.time()
        result = self.search(research_question, top_k=top_k)
        result["question"] = research_question
        return result


# ═══════════════════════════════════════════════════════════════
# REST 直连适配器（包装现有 SciverseSearcher）
# ═══════════════════════════════════════════════════════════════

class SciverseSearcherRestAdapter(BaseSciverseAdapter):
    """REST API 直连适配器——包装现有的 SciverseSearcher 实现。

    这是最终兜底方案。当 MCP 和 Skill 均不可用时使用此适配器。
    通过直接实例化 SciverseSearcher 并调用其 REST 方法完成检索。
    """

    BASE_URL = "https://api.sciverse.space"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(mode="rest")
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

    def search(self, query_text: str, top_k: int = 50,
               year_from: Optional[int] = None, year_to: Optional[int] = None,
               **kwargs) -> Dict[str, Any]:
        if not self.available:
            return {"results": [], "error": "No API key configured"}

        payload: Dict[str, Any] = {
            "query": query_text,
            "top_k": min(top_k, 50),
        }
        # 年份过滤通过 filters 传递
        year_filter = {}
        if year_from:
            year_filter["gte"] = year_from
        if year_to:
            year_filter["lte"] = year_to
        if year_filter:
            payload["filters"] = {"publication_published_year": year_filter}

        t_start = time.time()

        try:
            resp = _request_with_retry(
                self._session, "POST", f"{self.BASE_URL}/agentic-search",
                json=payload, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._record_and_return("search", payload, data, t_start)
        except Exception as e:
            return self._record_and_return(
                "search", payload,
                {"results": [], "error": str(e)},
                t_start, error=str(e)
            )

    def semantic_search(self, query_text: str, top_k: int = 10,
                        mode: str = "balanced", **kwargs) -> Dict[str, Any]:
        if not self.available:
            return {"hits": [], "error": "No API key configured"}

        params = {"query": query_text, "top_k": min(top_k, 30), "mode": mode}
        t_start = time.time()

        try:
            resp = _request_with_retry(
                self._session, "POST", f"{self.BASE_URL}/agentic-search",
                json=params, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._record_and_return("semantic_search", params, data, t_start)
        except Exception as e:
            return self._record_and_return(
                "semantic_search", params,
                {"hits": [], "error": str(e)},
                t_start, error=str(e)
            )

    def read_content(self, doc_id: str, offset: int = 0,
                     limit: int = 4096, **kwargs) -> Dict[str, Any]:
        if not self.available:
            return {"text": None, "error": "No API key configured"}

        params = {"doc_id": doc_id, "offset": offset, "limit": min(limit, 16384)}
        t_start = time.time()

        try:
            resp = _request_with_retry(
                self._session, "GET", f"{self.BASE_URL}/content",
                params=params, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._record_and_return("read_content", params, data, t_start)
        except Exception as e:
            return self._record_and_return(
                "read_content", params,
                {"text": None, "error": str(e)},
                t_start, error=str(e)
            )


# ═══════════════════════════════════════════════════════════════
# 统一适配层工厂函数
# ═══════════════════════════════════════════════════════════════

def create_sciverse_adapter(
    mcp_url: Optional[str] = None,
    skill_path: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseSciverseAdapter:
    """自动检测可用模式并返回最佳适配器实例。

    检测优先级：MCP > Skill > REST

    检测逻辑：
      1. 若环境变量 SCIVERSE_MCP_URL 已设置，或参数 mcp_url 非空
         → 尝试创建 SciverseMCPAdapter，检测其可用性
      2. 若环境变量 SCIVERSE_SKILL_PATH 已设置，或参数 skill_path 非空
         → 尝试创建 SciverseSkillAdapter，检测其可用性
      3. 若环境变量 SCIVERSE_API_KEY 已设置，或参数 api_key 非空
         → 使用 SciverseSearcherRestAdapter (REST API 直连)
      4. 均不可用
         → 返回 SciverseSearcherRestAdapter (available=False)，
           调用者应知晓 Sciverse 不可用并回退到 arxiv 等其他源

    Args:
        mcp_url: MCP 服务端点 URL（可选，优先级高于环境变量）
        skill_path: Skill 脚本路径（可选，优先级高于环境变量）
        api_key: API Key（可选，优先级高于环境变量）

    Returns:
        最佳可用的适配器实例

    Example:
        >>> adapter = create_sciverse_adapter()
        >>> print(adapter.mode)  # "mcp" / "skill" / "rest"
        >>> if adapter.available:
        ...     result = adapter.search("MOF CO2 capture", top_k=10)
    """
    # Level 1: MCP
    effective_mcp = mcp_url or os.environ.get("SCIVERSE_MCP_URL", "")
    if effective_mcp:
        adapter = SciverseMCPAdapter(mcp_url=effective_mcp)
        if adapter.available:
            return adapter

    # Level 2: Skill
    effective_skill = skill_path or os.environ.get("SCIVERSE_SKILL_PATH", "")
    if effective_skill:
        adapter = SciverseSkillAdapter(skill_path=effective_skill)
        if adapter.available:
            return adapter

    # Level 3: REST API direct
    effective_key = api_key or os.environ.get("SCIVERSE_API_KEY", "")
    adapter = SciverseSearcherRestAdapter(api_key=effective_key)
    return adapter  # 如果 api_key 为空，available 为 False，调用者应回退


# ═══════════════════════════════════════════════════════════════
# Sciverse 状态诊断
# ═══════════════════════════════════════════════════════════════


def check_sciverse_status(
    api_key: Optional[str] = None,
    mcp_url: Optional[str] = None,
    skill_path: Optional[str] = None,
) -> Dict[str, Any]:
    """检查 Sciverse 集成可用性状态，返回完整诊断报告。

    检查项（优先级递减）：
      1. MCP 模式 — SCIVERSE_MCP_URL 环境变量
      2. Skill 模式 — SCIVERSE_SKILL_PATH 环境变量
      3. REST 模式 — SCIVERSE_API_KEY 环境变量

    Args:
        api_key: Sciverse API Key（可选，默认从环境变量读取）
        mcp_url: MCP 服务端点 URL（可选）
        skill_path: Skill 脚本路径（可选）

    Returns:
        {
            "sciverse_available": bool,
            "active_mode": str | None,     # "mcp" | "skill" | "rest" | None
            "mcp": {"available": bool, "url": str, "detail": str},
            "skill": {"available": bool, "path": str, "detail": str},
            "rest": {"available": bool, "has_api_key": bool, "detail": str},
            "diagnosis": str,               # 人类可读的诊断信息
            "setup_instructions": [str],    # 未配置模式的安装说明
        }
    """
    effective_key = api_key or os.environ.get("SCIVERSE_API_KEY", "")
    effective_mcp = mcp_url or os.environ.get("SCIVERSE_MCP_URL", "")
    effective_skill = skill_path or os.environ.get("SCIVERSE_SKILL_PATH", "")

    report: Dict[str, Any] = {
        "sciverse_available": False,
        "active_mode": None,
        "mcp": {"available": False, "url": effective_mcp or "(未设置)", "detail": ""},
        "skill": {"available": False, "path": effective_skill or "(未设置)", "detail": ""},
        "rest": {"available": False, "has_api_key": bool(effective_key), "detail": ""},
        "diagnosis": "",
        "setup_instructions": [],
    }

    # ── Tier 1: MCP 模式 ──
    if effective_mcp:
        mcp_adapter = SciverseMCPAdapter(mcp_url=effective_mcp)
        mcp_available = mcp_adapter.available
        report["mcp"]["available"] = mcp_available
        if mcp_available:
            report["mcp"]["detail"] = f"MCP 端点可达: {effective_mcp}"
            report["sciverse_available"] = True
            report["active_mode"] = "mcp"
            report["diagnosis"] = "Sciverse MCP 模式可用"
        else:
            report["mcp"]["detail"] = f"MCP 端点不可达: {effective_mcp}"
    else:
        report["mcp"]["detail"] = "SCIVERSE_MCP_URL 未设置"

    # ── Tier 2: Skill 模式 ──
    if not report["sciverse_available"]:
        if effective_skill:
            skill_adapter = SciverseSkillAdapter(skill_path=effective_skill)
            skill_available = skill_adapter.available
            report["skill"]["available"] = skill_available
            if skill_available:
                skill_path_exists = Path(effective_skill).exists()
                if skill_path_exists:
                    report["skill"]["detail"] = f"Skill 脚本存在: {effective_skill}"
                else:
                    report["skill"]["detail"] = f"Skill 脚本不存在，但 REST 回退可用"
                report["sciverse_available"] = True
                report["active_mode"] = "skill"
                report["diagnosis"] = "Sciverse Skill 模式可用"
            else:
                report["skill"]["detail"] = "Skill 脚本不存在且 REST 回退不可用"
        else:
            report["skill"]["detail"] = "SCIVERSE_SKILL_PATH 未设置"

    # ── Tier 3: REST 模式 ──
    if not report["sciverse_available"]:
        rest_adapter = SciverseSearcherRestAdapter(api_key=effective_key)
        rest_available = rest_adapter.available
        report["rest"]["available"] = rest_available
        report["rest"]["has_api_key"] = bool(effective_key)
        if rest_available:
            report["rest"]["detail"] = "API Key 已配置"
            report["sciverse_available"] = True
            report["active_mode"] = "rest"
            report["diagnosis"] = "Sciverse REST API 可用"
        else:
            if effective_key:
                report["rest"]["detail"] = "API Key 已设置但适配器未可用（请检查密钥有效性）"
            else:
                report["rest"]["detail"] = "SCIVERSE_API_KEY 未设置"

    # ── 生成诊断信息和安装说明 ──
    if not report["sciverse_available"]:
        report["diagnosis"] = (
            "Sciverse 不可用 — 所有接入模式均未配置。"
            "MCP: " + report["mcp"]["detail"] + "；"
            "Skill: " + report["skill"]["detail"] + "；"
            "REST: " + report["rest"]["detail"]
        )
        report["setup_instructions"] = [
            "方式1 (REST): 设置环境变量 SCIVERSE_API_KEY=<your_key>",
            "方式2 (REST): 在 .api_key 文件中添加 SCIVERSE_API_KEY=<your_key>",
            "方式3 (MCP): 设置环境变量 SCIVERSE_MCP_URL=http://<host>:<port>/mcp",
            "方式4 (Skill): 设置环境变量 SCIVERSE_SKILL_PATH=/path/to/sciverse_skill.py",
            "注册 Sciverse API Key: https://sciverse.space (需申请)",
        ]
    else:
        report["setup_instructions"] = [
            f"当前使用模式: {report['active_mode']}",
        ]

    return report


def print_sciverse_status() -> None:
    """打印 Sciverse 集成状态报告（人类可读格式）。"""
    report = check_sciverse_status()
    print("=" * 60)
    print("  Sciverse 集成状态报告")
    print("=" * 60)
    print(f"  总体可用:     {'是' if report['sciverse_available'] else '否'}")
    print(f"  活跃模式:     {report['active_mode'] or '无'}")
    print(f"  MCP URL:      {report['mcp']['url']}")
    print(f"  MCP 状态:     {'可用' if report['mcp']['available'] else '不可用'} — {report['mcp']['detail']}")
    print(f"  Skill 路径:   {report['skill']['path']}")
    print(f"  Skill 状态:   {'可用' if report['skill']['available'] else '不可用'} — {report['skill']['detail']}")
    print(f"  REST API Key: {'已设置' if report['rest']['has_api_key'] else '未设置'}")
    print(f"  REST 状态:    {'可用' if report['rest']['available'] else '不可用'} — {report['rest']['detail']}")
    print(f"  诊断:         {report['diagnosis']}")
    if report["setup_instructions"]:
        print("  安装说明:")
        for instr in report["setup_instructions"]:
            print(f"    - {instr}")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# 快速测试
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Sciverse MCP/Skill 适配层 快速检测 ===\n")

    adapter = create_sciverse_adapter()
    print(f"  模式: {adapter.mode}")
    print(f"  可用: {adapter.available}")

    if adapter.available:
        print("\n  运行 smoke test (search 'MOF CO2 capture', top_k=3) ...")
        result = adapter.search("MOF CO2 capture", top_k=3)
        metadata = result.get("_mcp_metadata")
        if metadata:
            print(f"    call_id: {metadata.call_id}")
            print(f"    tool: {metadata.tool}")
            print(f"    result_count: {metadata.result_count}")
        results = result.get("results", [])
        for r in results[:3]:
            print(f"    - {r.get('title', 'N/A')[:80]}")
    else:
        print("\n  所有模式均不可用。请设置 SCIVERSE_API_KEY 环境变量。")
        print("  当前环境变量状态:")
        print(f"    SCIVERSE_MCP_URL:   {'已设置' if os.environ.get('SCIVERSE_MCP_URL') else '未设置'}")
        print(f"    SCIVERSE_SKILL_PATH: {'已设置' if os.environ.get('SCIVERSE_SKILL_PATH') else '未设置'}")
        print(f"    SCIVERSE_API_KEY:   {'已设置' if os.environ.get('SCIVERSE_API_KEY') else '未设置'}")

    print("\n  审计日志条目:", len(adapter.get_audit_log()))
