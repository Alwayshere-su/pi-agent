"""
LLM 调用抽象层 — Pi-Agent Layer 1
===================================
提供统一的 LLM 调用接口，封装 DeepSeek API。

@external: utils/resource_registry.py → "DeepSeek API"
  来源: https://platform.deepseek.com (商业 API, 2026-08)
  模型: deepseek-v4-flash (OpenAI 兼容接口)
  替代: vLLM 本地部署开源模型（改 DEEPSEEK_BASE_URL 即可）

特性：
  - Tool call 参数 JSON 自动修复（LLM 输出格式错误时）
  - API 调用期间心跳动画（防止看起来卡死）
  - 指数退避重试（最多 5 次）
  - 纯文本推理模式（think 工具专用，不触发 tool call）
  - 重复 tool call 检测与自动修复
"""
from __future__ import annotations

import json
import os
import sys
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── Tool definitions ──

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "think",
            "description": "Deep reasoning tool. Call this when you need to analyze complex situations, form hypotheses, or plan strategy. The system will give you space to reason without the pressure of selecting other tools.\n\n"
                           "Use think when: you've gathered enough information and need to form a hypothesis before experimenting; you've received unexpected results and need to understand why; you're at a decision point with multiple options.\n\n"
                           "Do NOT use think for: simple file reads, monitoring training, or routine operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "What to think about, e.g. 'Which material-property gaps are most promising to explore next?' or 'Why did this search fail?'"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Recursively list all files in a directory. Used to discover available data, code, log, and output files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list, e.g. workspace or workspace/outputs",
                        "default": "workspace"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob filter pattern, e.g. *.csv or *.json",
                        "default": "**/*"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read any project file. Can read memory/logs/data, previously generated code, and project source under agent/ predictors/. JSON files display a structural summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "File path, e.g. workspace/outputs/_research_knowledge_rec.json"
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a file. Supports .md (memory) and .py (code), no content length limit. Special characters in content (quotes, newlines, backslashes) are auto-escaped — pass raw code directly, no manual handling needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Target file path"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write. Quotes/newlines/backslashes are auto-escaped, pass raw Python code directly"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["overwrite", "append"],
                        "description": "Write mode",
                        "default": "overwrite"
                    }
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file via exact string replacement. Supports two modes:\n\n"
                           "Single replacement: pass old_string + new_string, replaces first occurrence (add replace_all=true to replace all)\n"
                           "Batch replacement: pass patches=[{\"old_string\":\"...\",\"new_string\":\"...\"}, ...] to change multiple different locations at once",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path of the file to modify"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Text to replace, must match exactly (including indentation). Mutually exclusive with patches."
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement text. Mutually exclusive with patches."
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Whether to replace all matches (default false, only replaces first occurrence)",
                        "default": False
                    },
                    "patches": {
                        "type": "array",
                        "description": "Batch replacement list, each entry has old_string and new_string. Mutually exclusive with old_string/new_string.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "old_string": {"type": "string", "description": "Text to replace"},
                                "new_string": {"type": "string", "description": "Replacement text"}
                            },
                            "required": ["old_string", "new_string"]
                        }
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Execute a shell command in the workspace sandbox (3600s timeout). python automatically points to project .venv Python; numpy/pandas/scipy/sklearn/openai etc. are all installed.\n\n"
                           "To run a training script: python workspace/code/xxx.py (script must be self-contained with explicit imports of all libraries; load data yourself). "
                           "Write code with write_file first, then execute with run_shell.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_shell",
            "description": "Non-blocking launch of a long-running command (e.g. training script). Returns process ID immediately, program runs in background. "
                           "Agent monitors output every few seconds with check_shell; kill_shell to terminate early if issues detected. "
                           "Do NOT use run_shell for training scripts — it blocks until the script finishes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute, e.g. 'python workspace/code/train.py'"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds, default 3600",
                        "default": 3600
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_shell",
            "description": "Check background process status and new output. Each call auto-blocks for up to 90 seconds, returning early if output appears or the process ends. "
                           "Used for real-time monitoring of training scripts — view loss curves, detect Traceback/CUDA errors.\n\n"
                           "**status meanings**: loading=loading data (no first line of output yet, wait patiently); running=normal operation; completed=finished; "
                           "error=crashed; stuck=had output but no new output for >2 min (genuinely stuck or zombie process).\n\n"
                           "do NOT kill loading status! Data loading/co-visit matrix construction may have no output for 1-2 minutes, this is normal. "
                           "Only kill on stuck or error. For zombie processes (files saved but process won't exit), kill then use list_files to check output directly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "integer",
                        "description": "Process ID returned by start_shell"
                    }
                },
                "required": ["pid"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kill_shell",
            "description": "Terminate a background process. Use when training issues are detected (error/stuck/loss not decreasing), then edit_file to fix code and start_shell to restart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "integer",
                        "description": "Process ID to terminate"
                    }
                },
                "required": ["pid"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop",
            "description": "Stop the survey. Call after generating the report + writing memory files. No parameters.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_papers",
            "description": "Search scientific literature across multiple sources (arXiv, Sciverse, Sci-Base). Returns structured paper metadata with abstracts, DOIs, and relevance scores. Use this to discover papers on a research topic — you can call it multiple times with different queries to explore from different angles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query, e.g. 'MOF materials for CO2 capture'"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 20, max 50)",
                        "default": 20
                    },
                    "material": {
                        "type": "string",
                        "description": "Optional: specific material name to filter by, e.g. 'ZIF-8'"
                    },
                    "property": {
                        "type": "string",
                        "description": "Optional: specific property to filter by, e.g. 'adsorption capacity'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_paper",
            "description": "Parse a PDF/DOCX/HTML paper into structured Markdown text. Extracts sections, references, and identifies materials/properties/methods mentioned. Use this on individual papers you want to analyze deeply.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the paper file (PDF, DOCX, HTML, or TXT)"
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_knowledge",
            "description": "整理论文摘要为可读 Markdown（workspace/outputs/literature_survey/paper_summaries.md）供 Agent 阅读分析。不构建 JSON 知识图谱——知识抽取、关系识别与知识图谱撰写由 Agent 自行完成（write_file workspace/outputs/literature_survey/knowledge_graph.md）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "papers_json": {
                        "type": "string",
                        "description": "JSON string mapping paper IDs to their text content. Use filepath instead if data is in a file."
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to a JSON file containing {paper_id: text} mapping. Preferred over papers_json for large datasets."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_gaps",
            "description": "检查论文摘要（paper_summaries.md）是否就绪并返回 Gap 分析指引。真正的 Gap 识别（矛盾结论/缺失连接/未探索空间）由 Agent 阅读摘要后完成，并 write_file 输出 gap_report.md。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_hypotheses",
            "description": "Generate testable structure-property relationship hypotheses from research gaps. Uses LLM to evaluate scientific plausibility and novelty. Saves to workspace/outputs/literature_survey/discovery/. Use this after analyze_gaps when you have meaningful gaps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_method": {
                        "type": "string",
                        "enum": ["bayesian", "mcts", "hybrid"],
                        "description": "Search algorithm for exploring material space",
                        "default": "bayesian"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_discovery_search",
            "description": "Execute Bayesian optimization or MCTS over material-parameter space to discover novel structure-property relationships. Scoring is grounded in the Agent's own knowledge graph (knowledge_graph.md) or paper summaries. Use this after generate_hypotheses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis_index": {
                        "type": "integer",
                        "description": "Which hypothesis to search (0-indexed from hypotheses list)"
                    },
                    "n_iterations": {
                        "type": "integer",
                        "description": "Search iterations (default 30, max 100)",
                        "default": 30
                    }
                },
                "required": ["hypothesis_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_novelty",
            "description": "系统性地对假设进行已有文献查重，验证新颖性（赛题红线2/冲高分方向1：怎么证明『这真的没人做过』）。为每条假设生成 3-5 条反向检索查询，检索已有文献，计算文本重叠度，调整 novelty_score。不依赖 LLM 判定——使用启发式文本相似度（Jaccard）评估重叠，避免『LLM 自己说是新的』。Use this after generate_hypotheses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis_index": {
                        "type": "integer",
                        "description": "要验证的假设索引（-1 表示全部，默认全部）",
                        "default": -1
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "每个查询返回的结果数（默认 5，最大 10）",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_discovery",
            "description": "Cross-validate discovered structure-property relationships against Materials Project, OQMD, NOMAD (restapi.nomad-lab.eu, 公开查询免 key), and hMOF/CoRE MOF databases. Returns matching entries and validation status. NOMAD 查询失败(无网/限流)会明确降级标注,不影响其它库。Use this after run_discovery_search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis_index": {
                        "type": "integer",
                        "description": "Which hypothesis to validate (0-indexed)"
                    }
                },
                "required": ["hypothesis_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_model_comparison",
            "description": "经典模型对比（赛题硬性验证标准）：对给定构效关系假设，用候选模型（线性/二次/幂律/指数等，由文献数值自动判定最优）与经典物理模型（Slack 带隙-温度模型、Vegard 定律等，从 literature_agent.classical_models 导入）在同一组文献数值点上拟合，输出 R²/RMSE 对比 + 嵌套 F 检验（候选 vs 经典）+ LLM 解释「候选是否优于经典、旧模型为何失效」。报告保存到 workspace/outputs/literature_survey/discovery/model_comparison_<idx>.md。",
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis_index": {
                        "type": "integer",
                        "description": "Which hypothesis to compare (0-indexed from hypotheses.json)"
                    },
                    "classical_model": {
                        "type": "string",
                        "description": "Optional: 经典模型名称（如 'slack' / 'vegard' / 'linear'）；缺省时依据自变量类型自动选择"
                    }
                },
                "required": ["hypothesis_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "symbolic_regression",
            "description": "符号回归（赛题推荐算法）：对给定构效关系假设，从文献数值中提取 (x, y) 数据点集，用轻量遗传编程符号回归（literature_agent.symbolic_regression，无第三方依赖）拟合可解释表达式（如 a*x^2+b*x+c、a*exp(b*x)+c），输出表达式 + R²/MSE。报告保存到 workspace/outputs/literature_survey/discovery/symbolic_<idx>.md。",
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis_index": {
                        "type": "integer",
                        "description": "Which hypothesis to fit (0-indexed from hypotheses.json)"
                    },
                    "property": {
                        "type": "string",
                        "description": "Optional: 目标性质名（缺省用 hypotheses.json 中该假设的 property）"
                    },
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: 自变量名列表（如 ['temperature','composition']），缺省由文献数值自动提取"
                    },
                    "max_generations": {
                        "type": "integer",
                        "description": "遗传编程最大进化代数，默认 100",
                        "default": 100
                    },
                    "pop_size": {
                        "type": "integer",
                        "description": "遗传编程种群规模，默认 50",
                        "default": 50
                    }
                },
                "required": ["hypothesis_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cross_theme_connections",
            "description": "跨领域文献连接（赛题高分方向）：打破单主题隔离，扫描多个主题的 knowledge_graph.md 与 discovery/hypotheses.json，在共享材料/性质实体上建立「主题A实体──共享实体──主题B实体」连接，每条连接输出中文科学理由、真实论文证据编号、可证伪假设（Expected Relationship 格式）与 novelty 提示。报告保存到 workspace/outputs/literature_survey/discovery/cross_theme_connections.md。run_dirs 缺省时自动发现 workspace/outputs/*/literature_survey（排除 test/smoke 临时主题）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "run_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可选：要扫描的主题 run_dir 列表（如 ['thermoelectric','perovskite']）；缺省自动发现全部主题"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_discovery_report",
            "description": "Generate the Route A discovery report (Markdown + JSON) with validated structure-property relationships, evidence chains, and scientific explanations. Saves to workspace/outputs/literature_survey/discovery/. Call when discovery phase is complete.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Generate the final survey report (Markdown + JSON) from all accumulated data: search results, knowledge graph, and gap analysis. Saves to workspace/outputs/literature_survey/. Use this when you believe the survey coverage is sufficient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The research topic for the report title"
                    }
                },
                "required": ["topic"]
            }
        }
    },
]

# ── 多主题支持：工具 schema 中的路径在使用时按当前 run_dir 动态改写 ──
# TOOL_DEFINITIONS 保持原始定义不变；call_with_tools() 每次调用时通过
# _resolved_tools() 根据 utils.config.SURVEY_DIR（由 main.py --run-dir 设置）
# 将描述中的 "workspace/outputs/literature_survey" 改写为当前主题目录。
# 默认 run_dir="survey" 时改写前后一致，与历史版本完全兼容。


# ═══════════════════════════════════════════════════════════════
# Provider Registry
# ═══════════════════════════════════════════════════════════════

class Provider:
    """Abstract base for LLM providers."""

    def __init__(self, name: str, model: str, max_tokens: int):
        self.name = name
        self.model = model
        self.max_tokens = max_tokens

    def chat(self, messages: List[Dict], tools: List[Dict] = None,
             temperature: float = 0.1) -> Tuple[str, str, List[Dict]]:
        """
        Returns (content, reasoning_content, tool_calls_list).
        Each tool call in the list is: {"id": ..., "type": "function", "function": {"name": ..., "arguments": ...}}
        """
        raise NotImplementedError



class DeepSeekProvider(Provider):
    """DeepSeek API (OpenAI-compatible)."""

    def __init__(self):
        from utils.config import DEEPSEEK_MODEL, DEEPSEEK_MAX_TOKENS, DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY
        super().__init__("deepseek", DEEPSEEK_MODEL, DEEPSEEK_MAX_TOKENS)
        self.base_url = DEEPSEEK_BASE_URL
        self.api_key = DEEPSEEK_API_KEY

    def chat(self, messages: List[Dict], tools: List[Dict] = None,
             temperature: float = 0.1) -> Tuple[str, str, List[Dict]]:
        from openai import OpenAI
        # timeout=120：防止单次 API 调用无限阻塞（SDK 默认 600s，5 次重试最坏 50 分钟）
        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=120)
        kwargs = dict(
            model=self.model, messages=messages,
            max_tokens=self.max_tokens, temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        reasoning = getattr(msg, 'reasoning_content', '') or ''
        content = msg.content or ''
        if not content and reasoning:
            content = reasoning
        tcs = []
        for tc in (msg.tool_calls or []):
            tcs.append({
                "id": tc.id, "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments}
            })
        return content, reasoning, tcs


# ═══════════════════════════════════════════════════════════════
# LLM Client (Unified Interface)
# ═══════════════════════════════════════════════════════════════

class LLMClient:
    """
    Unified LLM client with multi-provider support and auto-failover.

    Usage:
        client = LLMClient()
        content, reasoning, tool_calls = client.call_with_tools(messages)
    """

    def __init__(self, primary: str = None, print_fn: Callable = None):
        self._print = print_fn or (lambda x: None)
        self._providers: Dict[str, Provider] = {}
        self._active: Optional[str] = None

        try:
            ds = DeepSeekProvider()
            if ds.api_key:
                self._providers["deepseek"] = ds
                self._active = "deepseek"
                self._print(f"[LLM] DeepSeek initialized (model: {ds.model})")
        except Exception as e:
            self._print(f"[LLM] DeepSeek init failed: {e}")

        if not self._providers:
            raise RuntimeError(
                "No LLM provider available! Set DEEPSEEK_API_KEY env var "
                "or create .api_key file in project root with your DeepSeek API Key."
            )

        self._print(f"[LLM] Active: {self._active}")

    @property
    def available(self) -> bool:
        return len(self._providers) > 0

    @property
    def active_provider_name(self) -> str:
        return self._active or "none"

    @property
    def _active_provider(self) -> Provider:
        return self._providers[self._active]

    # ── JSON Repair (same logic as original) ──

    @staticmethod
    def repair_json(raw: str) -> str:
        """Attempt to repair common LLM JSON errors."""
        if not raw or not isinstance(raw, str):
            return raw
        result = []
        in_string = False
        escape_next = False
        string_start = -1
        i = 0
        while i < len(raw):
            ch = raw[i]
            if escape_next:
                result.append(ch); escape_next = False; i += 1; continue
            if ch == '\\':
                result.append(ch); escape_next = True; i += 1; continue
            if ch == '"':
                if in_string:
                    j = i + 1
                    while j < len(raw) and raw[j] in ' \t\r\n':
                        j += 1
                    next_ch = raw[j] if j < len(raw) else ''
                    if j >= len(raw) or next_ch in ',}]':
                        result.append('"'); in_string = False
                    elif next_ch == ':':
                        if string_start >= 0 and (i - string_start) > 30:
                            result.append('\\"')
                        else:
                            result.append('"'); in_string = False
                    else:
                        result.append('\\"')
                else:
                    result.append('"'); in_string = True; string_start = i
                i += 1; continue
            if in_string:
                if ch == '\n': result.append('\\n')
                elif ch == '\r': result.append('\\r')
                elif ch == '\t': result.append('\\t')
                else: result.append(ch)
            else:
                result.append(ch)
            i += 1
        repaired = ''.join(result)
        if in_string:
            repaired += '"'
        import re
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        return repaired

    # ── Main API ──

    def _resolved_tools(self) -> List[Dict]:
        """返回工具 schema，路径按当前 run_dir 动态改写。"""
        from utils.config import SURVEY_DIR
        if SURVEY_DIR == "workspace/outputs/literature_survey":
            return TOOL_DEFINITIONS
        return json.loads(
            json.dumps(TOOL_DEFINITIONS, ensure_ascii=False).replace(
                "workspace/outputs/literature_survey", SURVEY_DIR
            )
        )

    def call_with_tools(self, messages: List[Dict]) -> Tuple[Optional[str], Optional[str], Optional[List[Dict]]]:
        """
        Call LLM with tool definitions. Auto-retries + provider switch on failure.

        Returns (content, reasoning, tool_calls) — each can be None on total failure.
        """
        if not self._providers:
            return None, None, None

        last_error = ""

        for attempt in range(5):
            _heartbeat_stop = False
            try:
                # Heartbeat spinner thread
                spinner = ["|", "/", "-", "\\"]

                def _heartbeat():
                    frame = 0
                    for _ in range(600):
                        if _heartbeat_stop: break
                        time.sleep(0.5)
                        if not _heartbeat_stop:
                            print(f"\r     {spinner[frame % 4]}", end="", flush=True)
                            frame += 1

                hb = threading.Thread(target=_heartbeat, daemon=True)
                hb.start()

                provider = self._active_provider
                content, reasoning, tcs = provider.chat(messages, tools=self._resolved_tools())

                _heartbeat_stop = True; hb.join(timeout=1)

                if not content and reasoning:
                    content = reasoning

                return content, reasoning, (tcs if tcs else None)

            except Exception as e:
                _heartbeat_stop = True
                last_error = str(e)

                # 不可恢复错误（密钥/权限/模型不存在）：重试无意义，立即放弃保存预算
                try:
                    from openai import AuthenticationError as _AuthErr
                    from openai import PermissionDeniedError as _PermErr
                    from openai import NotFoundError as _NotFoundErr
                    _non_retryable = (_AuthErr, _PermErr, _NotFoundErr)
                except ImportError:
                    _non_retryable = ()
                if _non_retryable and isinstance(e, _non_retryable):
                    self._print(f"  [LLM] Non-retryable API error, aborting: {last_error[:300]}")
                    return None, None, None

                # Repetitive tool call / invalid parameter detection
                if "repetitive" in last_error.lower() or "invalid" in last_error.lower():
                    cut_at = None
                    for i in range(len(messages) - 1, -1, -1):
                        if messages[i].get("role") == "assistant" and messages[i].get("tool_calls"):
                            cut_at = i; break
                    if cut_at is not None and cut_at > 1:
                        removed = len(messages) - cut_at
                        # 有意副作用：原地截断调用方消息列表（agent 的 self._messages），
                        # 打破重复调用死循环；用切片赋值保持引用一致，避免 del+append 中间态
                        messages[:] = messages[:cut_at]
                        self._print(f"  [LLM] Repetitive call detected, removed last {removed} messages")
                    dead_pid_hint = ""
                    for i in range(len(messages) - 1, max(-1, len(messages) - 6), -1):
                        m = messages[i]
                        if m.get("role") == "tool" and "不存在" in str(m.get("content", "")):
                            import re as _re
                            mp = _re.search(r'进程\s*(\d+)', str(m.get("content", "")))
                            if mp:
                                dead_pid_hint = (
                                    f"（进程 {mp.group(1)} 已死，请勿再次检查。"
                                    f"使用 list_files 查看输出，read logs 分析错误，"
                                    f"修复代码后 start_shell 重新启动。）"
                                )
                            break
                    messages.append({
                        "role": "user",
                        "content": (
                            "[系统] ⚠️ 检测到连续重复调用，对话历史已截断。"
                            "你必须改变操作——不要用相同参数再次调用同一工具！"
                            + dead_pid_hint +
                            "可执行的操作：list_files 检查输出目录，read_file 读取日志/记忆/反馈，"
                            "write_file 编写分析或修复代码，start_shell 启动新任务，"
                            "read_file 查阅参考文档寻找新方向。"
                        )
                    })

                # Auto-switch logic can be added here if multiple providers configured

            if attempt < 4:
                delay = min(3 * (2 ** attempt), 60)
                self._print(f"  [LLM] Retry {attempt+1}/5 in {delay}s: {last_error}")
                time.sleep(delay)

        self._print(f"  ⚠️ All 5 API retries exhausted, auto-stop to save existing results")
        return None, None, None

    def think(self, messages: List[Dict], max_tokens: int = 800) -> str:
        """Text-only call for deep reasoning — no tools, just thinking.

        Used for the Think phase before the Act phase, to let the LLM
        reason deeply without the pressure of selecting tools.
        Retries up to 3 times with exponential backoff on failure.
        """
        if not self._providers:
            return "❌ No LLM provider available for thinking."

        last_error = ""
        for attempt in range(3):
            try:
                provider = self._active_provider
                from openai import OpenAI
                client = OpenAI(api_key=provider.api_key, base_url=provider.base_url, timeout=120)
                resp = client.chat.completions.create(
                    model=provider.model,
                    messages=messages,
                    max_tokens=min(max_tokens, provider.max_tokens),
                    temperature=0.1,
                )
                if resp and resp.choices:
                    msg = resp.choices[0].message
                    content = msg.content or ""
                    reasoning = getattr(msg, "reasoning_content", "") or ""
                    if content:
                        return content
                    if reasoning:
                        return reasoning
                    return "⚠️ Think completed but LLM returned empty response."
            except Exception as e:
                last_error = str(e)
                if attempt < 2:
                    delay = min(2 * (2 ** attempt), 30)
                    time.sleep(delay)

        self._print(f"  ⚠️ think tool failed after 3 retries: {last_error}")
        return f"⚠️ Think failed after 3 retries: {last_error[:200]}"
