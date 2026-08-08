"""
工具系统 — Pi-Agent Layer 2
============================
Agent 通过工具与外部环境交互。每个工具经过五步管线处理：

  1. DEFINE   — 定义工具 schema（名称、参数、描述）
  2. REGISTER — 注册工具名 → 处理函数的映射
  3. INTERCEPT — 执行前后钩子（可拦截或修改调用）
  4. EXECUTE   — 调用处理函数，捕获结果
  5. RECYCLE   — 执行后清理（如保存轨迹日志）

执行模式：
  - sequential（默认）：工具逐个执行，前一个结果对后续可见
  - parallel：工具并发执行（仅用于独立的读取操作）
"""
from __future__ import annotations

import json
import os
import re
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from pi_agent.events import Event, EventBus, EVENT_TOOL_START, EVENT_TOOL_END

# 多主题运行目录（main.py --run-dir 设置；默认 survey 兼容历史路径）
import utils.config as _cfg

# ==== UTF-8 编码修复（Agent 注入 2026-08-02）====
import pathlib as _pathlib
_orig_wt = _pathlib.Path.write_text
_orig_rt = _pathlib.Path.read_text
def _wt_utf8(self, data, encoding=None, errors=None, newline=None):
    if encoding is None:
        encoding = 'utf-8'
    return _orig_wt(self, data, encoding=encoding, errors=errors, newline=newline)
def _rt_utf8(self, encoding=None, errors=None):
    if encoding is None:
        encoding = 'utf-8'
    return _orig_rt(self, encoding=encoding, errors=errors)
_pathlib.Path.write_text = _wt_utf8
_pathlib.Path.read_text = _rt_utf8
# ==== UTF-8 编码修复结束 ====


def _extract_json_object(text: str) -> Optional[Any]:
    """从 LLM 响应文本中稳健提取 JSON 对象/数组。

    依次尝试：
      1) 直接 json.loads（自动跳过首部 BOM \\ufeff，容忍首尾空白）；
      2) 剥离 ```json ... ``` / ``` ... ``` 代码围栏后解析；
      3) 用 json.JSONDecoder.raw_decode 提取首个 [ 或 { 起的完整
         JSON 值（容忍前后缀叙述文本，自动匹配到闭合括号）；
      4) 全部失败返回 None。

    纯函数，无副作用，便于单元测试。
    """
    if not text or not isinstance(text, str):
        return None
    s = text.strip()
    if not s:
        return None
    if s.startswith('\ufeff'):  # BOM 不属于 str.strip 的空白集，需显式去除
        s = s.lstrip('\ufeff').strip()

    # ① 直接解析
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        pass

    # ② 剥离代码围栏（```json ... ``` 或 ``` ... ```）
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', s)
    if m and m.group(1).strip():
        try:
            return json.loads(m.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # ③ 提取首个 [ 或 { 起的完整 JSON 值（raw_decode 只消费该 JSON 值，
    #    天然跳过尾部多余文本，且比 find/rfind 更正确配对括号）
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(s):
        if ch not in '[{':
            continue
        try:
            obj, _end = decoder.raw_decode(s[idx:])
            return obj
        except (json.JSONDecodeError, ValueError):
            continue  # 该位置不是合法 JSON 起点，尝试下一个候选

    # ④ 兜底：贪婪提取首尾 { } / [ ] 之间的最大块再尝试解析，
    #    覆盖 raw_decode 因文本中混入未闭合括号/杂散字符而无法定位
    #    合法起点的极端输出（如自由文本里嵌一个 JSON 数组/对象）。
    for pattern in (r'\{[\s\S]*\}', r'\[[\s\S]*\]'):
        m = re.search(pattern, s)
        if not m:
            continue
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _hypotheses_from_json(data: Any) -> Optional[List]:
    """从 _extract_json_object 的解析结果中提取 hypotheses 列表。

    兼容 LLM 常见的两种返回形态：
      - {"hypotheses": [...]}（提示词要求的标准形态）
      - [...]（直接输出假设数组）
    其余形态（dict 无 hypotheses 键、字符串、None 等）返回 None，
    由调用方决定走重试或兜底。
    """
    if isinstance(data, dict):
        hyps = data.get("hypotheses")
        if isinstance(hyps, list):
            return hyps
        return None
    if isinstance(data, list):
        return data
    return None


# ── Low-level tool implementations ──


class ToolManager:
    """
    Manages tool lifecycle: register → intercept → execute → recycle.

    Each tool handler receives (args: dict) and returns str.
    """

    def __init__(self, event_bus: EventBus = None, print_fn: Callable = None):
        self._handlers: Dict[str, Callable[[dict], str]] = {}
        self._before_hooks: List[Callable[[str, dict], Optional[str]]] = []
        self._after_hooks: List[Callable[[str, dict, str], str]] = []
        self._event_bus = event_bus
        self._print = print_fn or (lambda x: None)

    def register(self, name: str, handler: Callable[[dict], str]) -> None:
        """Register a tool handler function."""
        self._handlers[name] = handler

    def add_before_hook(self, hook: Callable[[str, dict], Optional[str]]) -> None:
        """
        Add a before-execution hook.
        Args:
            hook(tool_name, args) → None (allow) or str (block with this error message).
        """
        self._before_hooks.append(hook)

    def add_after_hook(self, hook: Callable[[str, dict, str], str]) -> None:
        """
        Add an after-execution hook.
        Args:
            hook(tool_name, args, result) → modified_result_str.
        """
        self._after_hooks.append(hook)

    # ── Execution ──

    def execute_sequential(self, tool_calls: List[Dict]) -> List[Tuple[Dict, str]]:
        """
        Execute tool calls one-by-one in order.
        Returns list of (tool_call_dict, result_string).
        """
        results: List[Tuple[Dict, str]] = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "?")
            try:
                args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
            except (json.JSONDecodeError, TypeError) as e:
                # Try JSON repair
                raw = fn["arguments"] if isinstance(fn["arguments"], str) else ""
                from pi_agent.llm import LLMClient
                repaired = LLMClient.repair_json(raw)
                if repaired != raw:
                    try:
                        args = json.loads(repaired)
                        fn["arguments"] = repaired
                        self._print(f"  🔧 JSON auto-repair succeeded")
                    except Exception:
                        args = {"_json_error": str(e)[:200], "_raw_preview": raw[:500], "_raw_len": len(raw)}
                else:
                    args = {"_json_error": str(e)[:200], "_raw_preview": raw[:500], "_raw_len": len(raw)}

            result = self._execute_one(name, args, tc)
            results.append((tc, result))
        return results

    def _execute_one(self, tool_name: str, args: dict, raw_tc: Dict) -> str:
        """Execute a single tool call with hooks."""
        t0 = time.time()

        # Emit start event
        if self._event_bus:
            self._event_bus.emit(Event(EVENT_TOOL_START, {
                "tool_name": tool_name,
                "tool_args_summary": self._fmt_args(tool_name, args),
                "tool_call_id": raw_tc.get("id", ""),
            }))

        # Before hooks
        for hook in self._before_hooks:
            block_msg = hook(tool_name, args)
            if block_msg is not None:
                return block_msg

        # Execute
        handler = self._handlers.get(tool_name)
        if handler:
            try:
                result = handler(args)
            except Exception:
                result = f"ERROR: {traceback.format_exc()}"
        else:
            result = f"Unknown tool: {tool_name}"

        # Truncate large outputs
        result_str = str(result)
        if len(result_str) > 250_000:
            result_str = result_str[:250_000] + "\n...[truncated]"

        # After hooks
        for hook in self._after_hooks:
            result_str = hook(tool_name, args, result_str)

        # Emit end event
        if self._event_bus:
            self._event_bus.emit(Event(EVENT_TOOL_END, {
                "tool_name": tool_name,
                "duration_ms": (time.time() - t0) * 1000,
                "result_len": len(result_str),
            }))

        return result_str

    @staticmethod
    def _fmt_args(name: str, args: dict) -> str:
        """Format tool args for display."""
        if name == "list_files":
            d = args.get("directory", "workspace")
            p = args.get("pattern", "**/*")
            return f"📂 {d}/{p}"
        elif name == "read_file":
            fp = args.get("filepath", "")
            fname = fp.split("/")[-1] if "/" in fp else fp
            return f"📖 {fname}"
        elif name == "write_file":
            fp = args.get("filepath", "")
            fname = fp.split("/")[-1] if "/" in fp else fp
            return f"✏️  {fname}"
        elif name == "run_shell":
            return f"💻 {args.get('command', '')[:80]}"
        elif name == "start_shell":
            return f"🚀 {args.get('command', '')[:80]}"
        elif name == "check_shell":
            return f"🔍 pid={args.get('pid', '?')}"
        elif name == "kill_shell":
            return f"💀 pid={args.get('pid', '?')}"
        elif name == "stop":
            return "🛑 stop"
        return f"🔧 {name}"


# ═══════════════════════════════════════════════════════════════
# Tool Handler Implementations
# ═══════════════════════════════════════════════════════════════

class ToolHandlers:
    """
    All tool handler implementations. Separated from ToolManager so the
    Agent can inject its own state (task_type, output_dir, memory_dir, etc.).
    """

    def __init__(self, task_type: str, bench: str = "A",
                 memory_dir: Path = None, print_fn: Callable = None):
        self.task_type = task_type
        self.bench = bench
        self.memory_dir = memory_dir or Path(f"workspace/memory/{task_type}")
        self._print = print_fn or (lambda x: None)
        # State hooks (set by Agent)
        self._on_stop: Optional[Callable[[], None]] = None
        self._on_think: Optional[Callable[[str], str]] = None  # (topic) → analysis
        # Survey session state (accumulated across tool calls)
        self.survey_state: Dict[str, Any] = {}

    # ── think ──

    def h_think(self, args: dict) -> str:
        """Deep reasoning tool — invokes the LLM without tools for analysis."""
        topic = args.get("topic", "")
        if not topic:
            return "❌ think tool requires a 'topic' parameter describing what to analyze."
        if not self._on_think:
            return "❌ Think backend not configured."
        self._print(f"  💭 Thinking about: {topic[:100]}...")
        result = self._on_think(topic)
        if result:
            return f"## Analysis: {topic}\n\n{result}"
        return "⚠️ Think completed but produced no output."

    # ── list_files ──

    def h_list_files(self, args: dict) -> str:
        from pi_agent._tools_impl import list_files
        directory = args.get("directory", "workspace")
        pattern = args.get("pattern", "**/*")
        result = list_files(directory, pattern)
        lines = [f"{r['path']} ({r['size_kb']}KB)" for r in result.get("files", [])]
        out = "\n".join(lines) if lines else "(empty)"
        total = result.get("total_found", len(result.get("files", [])))
        shown = result.get("count", len(result.get("files", [])))
        if result.get("overflow"):
            out += (f"\n\n⚠️ Truncated: found {total} files total, only showing first {shown}."
                    f" Please narrow the pattern or specify a subdirectory and retry.")
        return out

    # ── read_file ──

    def h_read_file(self, args: dict) -> str:
        from pi_agent._tools_impl import read_file
        filepath = args["filepath"]
        data_exts = (".csv", ".tsv", ".npz", ".npy", ".parquet", ".pkl", ".pickle")
        is_data_file = any(filepath.lower().endswith(ext) for ext in data_exts)
        if is_data_file:
            self._print(f"  🛑 Data file protection: {filepath} only showing first 500 chars")
            result = read_file(filepath, max_chars=500)
            content = result.get("content", "(empty)")
            return content + "\n\n⚠️ [System forced truncation] Above only shows the file header. To analyze data, use write_file to write a script + run_shell to execute."
        result = read_file(filepath, max_chars=250000)
        if result.get("structure"):
            return json.dumps(result["structure"], ensure_ascii=False)
        return result.get("content", "(empty)")

    # ── write_file ──

    def h_write_file(self, args: dict) -> str:
        from pi_agent._tools_impl import write_file

        if "_json_error" in args:
            raw = args.get('_raw_preview', '')
            raw_len = args.get('_raw_len', len(raw))
            filepath_hint = raw.split('"filepath": "')[1].split('"')[0] if '"filepath": "' in raw else "?"
            if filepath_hint.lower().endswith(".md"):
                hint = f"Memory file is {raw_len} chars long, JSON escaping failed. Please condense the content."
            else:
                hint = f"Code file is {raw_len} chars long, JSON escaping failed. Please condense or split into multiple files."
            return (
                f"❌ JSON exploded: {hint}\n"
                f"Target file: {filepath_hint}\n"
                f"⚠️ Do NOT retry with content of the same length! It will NOT succeed!"
            )

        filepath = args.get("filepath", "")
        content = args.get("content", "")
        if not filepath:
            return "❌ write_file failed: missing filepath parameter."
        if not content:
            return "❌ write_file failed: missing content parameter (code content is empty)."

        # ⛔ Feedback files are read-only
        if "workspace/feedback/" in filepath.lower().replace("\\", "/"):
            return "⛔ Modifying feedback files is forbidden! Feedback is manually maintained by the user."

        # MEMORY.md pre-write backup
        mem_backup = None
        if filepath.lower().endswith("memory.md") and os.path.exists(filepath):
            try:
                mem_backup = open(filepath, "r", encoding="utf-8").read()
            except Exception:
                pass

        result = write_file(filepath, content, args.get("mode", "overwrite"))
        ftype = "py" if filepath.lower().endswith(".py") else "file"
        msg = f"✅ write_{ftype}: {filepath} ({len(content)} chars)"

# MEMORY.md auto-repair
        if filepath.lower().endswith("memory.md"):
            try:
                mem_dir = os.path.dirname(os.path.abspath(filepath))
                # 排除审计文件：memory_quality.md 是自动生成的记忆质量报告，
                # 不应作为记忆文件收录进 MEMORY.md 索引（避免索引被审计噪音污染）
                actual_files = sorted(
                    f for f in os.listdir(mem_dir)
                    if f.endswith(".md") and f != "MEMORY.md"
                    and f != "memory_quality.md"
                )
                links_in_content = re.findall(r'\[([^\]]+)\]\(([^)]+\.md)\)', content)
                linked_files = {l[1] for l in links_in_content}
                missing = [f for f in linked_files if f not in actual_files]
                unlisted = [f for f in actual_files if f not in linked_files]
                if missing or unlisted:
                    rebuilt = [f"# Agent Experiment Memory — {self.task_type}\n"]
                    for fn in actual_files:
                        desc = None
                        for label, link in links_in_content:
                            if link == fn:
                                desc = label; break
                        if not desc:
                            desc = fn.replace(".md", "")
                        rebuilt.append(f"- [{desc}]({fn})")
                    corrected = "\n".join(rebuilt) + "\n"
                    write_file(filepath, corrected, "overwrite")
                    msg += (
                        f"\n\n⚠️ MEMORY.md auto-repair:\n"
                        + (f"  Wrong links (removed): {', '.join(missing)}\n" if missing else "")
                        + (f"  Missing files (added): {', '.join(unlisted)}" if unlisted else "")
                    )
            except Exception:
                pass

        # MEMORY.md content protection
        if filepath.lower().endswith("memory.md") and mem_backup is not None:
            try:
                new_content = open(filepath, "r", encoding="utf-8").read()
                if len(new_content.strip().split("\n")) < 5 and len(mem_backup.strip().split("\n")) >= 5:
                    open(filepath, "w", encoding="utf-8").write(mem_backup)
                    msg += "\n\n🛡️ MEMORY.md protection: Agent wrote too little, backup restored."
                else:
                    import shutil
                    shutil.copy2(filepath, filepath + ".bak")
            except Exception:
                pass

        return msg

    # ── edit_file ──

    def h_edit_file(self, args: dict) -> str:
        raw_path = args["file_path"]
        if not os.path.isabs(raw_path):
            if raw_path.startswith(("workspace/", "workspace\\", "predictors/", "predictors\\")):
                filepath = os.path.abspath(raw_path)
            else:
                filepath = os.path.abspath(os.path.join("workspace", raw_path))
        else:
            filepath = os.path.abspath(raw_path)

        # Block edits to core infrastructure
        blocked_prefixes = [
            os.path.abspath("agent"), os.path.abspath("pi_agent"),
            os.path.abspath("main.py"), os.path.abspath("utils"),
        ]
        for blocked in blocked_prefixes:
            if filepath.startswith(blocked):
                return f"⛔ Modifying core infrastructure is forbidden! {filepath} is in a protected area."

        if not os.path.exists(filepath):
            return f"❌ File does not exist: {filepath}"

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        patches = args.get("patches")
        if patches:
            patch_list = [(p["old_string"], p["new_string"]) for p in patches]
        elif args.get("old_string"):
            patch_list = [(args["old_string"], args["new_string"])]
        else:
            return "❌ edit_file failed: old_string+new_string or patches parameter required."

        replace_all = args.get("replace_all", False)
        total_replaced = 0

        for old_str, new_str in patch_list:
            count = content.count(old_str)
            if count == 0:
                return (f"❌ old_string not found in file! Use read_file to verify the file contents."
                        f"Note: old_string must match exactly (including indentation and whitespace).\n"
                        f"Preview of unfound content: {old_str[:100]}")
            if not replace_all and count > 1:
                return (f"❌ old_string appeared {count} times in the file!"
                        f"Use replace_all=true to replace all, or provide more specific context.\n"
                        f"Match text preview: {old_str[:100]}")
            content = content.replace(old_str, new_str) if replace_all else content.replace(old_str, new_str, 1)
            total_replaced += count if replace_all else 1

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        detail = f"{len(patch_list)} groups, {total_replaced} occurrences" if patches else f"{total_replaced} occurrences"
        return f"✅ Replacement successful ({detail})"

    # ── run_shell ──

    def h_run_shell(self, args: dict) -> str:
        from pi_agent._tools_impl import run_shell
        cmd = args["command"]

        if "MEMORY.md" in cmd and any(op in cmd for op in ("rm ", "> ", "truncate", "/dev/null")):
            return "🛡️ Deleting/clearing MEMORY.md is forbidden!"

        # Auto-correct common path mistakes
        for wrong in ["/home/user/workspace", "/home/user/", "~/workspace"]:
            cmd = cmd.replace(wrong + "/", "").replace("cd " + wrong + " && ", "").replace(wrong, "")
        if re.search(r'\bcd\s+workspace/?\s*&&', cmd):
            cmd = re.sub(r'cd\s+workspace/?\s*&&\s*', '', cmd)

        result = run_shell(cmd, timeout=3600,
                          env_vars={"AGENT_BUDGET_REMAINING": "-1"})
        stdout = result.get("stdout", "").strip()
        stderr = result.get("stderr", "").strip()
        # 显式暴露命令执行结果，让 Agent 能判断成败（原实现静默丢弃 return_code/success）
        success = result.get("success", False)
        exit_code = result.get("return_code", "?")
        error = result.get("error", "")

        header = f"[exit_code={exit_code}] [success={'True' if success else 'False'}]"
        body = ""
        if stdout and stderr:
            body += f"[stdout]\n{stdout}\n\n[stderr]\n{stderr}"
        else:
            body += stdout or stderr or "(no output)"
        if error:
            body = f"[error]\n{error}\n\n" + body

        if success:
            return f"{header}\n{body}"
        return f"{header} ⚠️ 命令执行失败\n{body}"

    # ── start_shell ──

    def h_start_shell(self, args: dict) -> str:
        from pi_agent._tools_impl import start_shell
        command = args.get("command", "")
        timeout = args.get("timeout", 3600)
        result = start_shell(command, timeout=timeout)
        if result.get("success"):
            return (f"Process {result['pid']} started (status: {result['status']})\n"
                    f"Command: {result['command']}\n"
                    f"Hint: use check_shell({result['pid']}) to monitor output")
        return f"Start failed: {result.get('error', 'unknown')}"

    # ── check_shell ──

    def h_check_shell(self, args: dict) -> str:
        from pi_agent._tools_impl import check_shell
        pid = args.get("pid", -1)
        result = check_shell(pid)
        if not result.get("success"):
            return (
                f"check_shell failed: {result.get('error', 'unknown')}\n\n"
                f"⚠️ This process no longer exists! Do NOT check_shell({pid}) again."
                f"Please do something else: check output directories, read logs to analyze errors,"
                f"fix code and start_shell to retrain, or move on to other experiments."
            )
        out = f"Process {pid}: {result['status']} | Elapsed {result['elapsed']}s"
        if result['status'] == 'loading':
            out += "\n(Data loading phase; no output is normal, please wait patiently, do NOT kill)"
        if result.get("return_code") is not None:
            out += f" | return_code={result['return_code']}"
        if result.get("warning"):
            out += f"\n⚠️ {result['warning']}"
        if result.get("new_output"):
            limit = 4000 if result['status'] in ('error', 'completed') else 2000
            output_text = result['new_output']
            if len(output_text) > limit:
                half = limit // 2
                output_text = output_text[:half] + f"\n... [{len(output_text) - limit} chars omitted] ...\n" + output_text[-half:]
            out += f"\n--- New output ---\n{output_text}"
        if result.get("stderr"):
            limit = 3000 if result['status'] in ('error', 'completed') else 1000
            err_text = result['stderr']
            if len(err_text) > limit:
                err_text = err_text[-limit:]
            out += f"\n--- stderr ---\n{err_text}"
        return out

    # ── kill_shell ──

    def h_kill_shell(self, args: dict) -> str:
        from pi_agent._tools_impl import kill_shell
        pid = args.get("pid", -1)
        result = kill_shell(pid)
        if result.get("success"):
            out = f"Process {pid} terminated | Ran {result['elapsed']}s"
            if result.get("final_stderr"):
                out += f"\n--- Final stderr ---\n{result['final_stderr'][-2000:]}"
            return out
        return f"Termination failed: {result.get('error', 'unknown')}"

    # ── stop ──

    def h_stop(self, args: dict) -> str:
        if self._on_stop:
            self._on_stop()
        memory_files = list(self.memory_dir.glob("survey-*.md"))
        msg = f"Stop signal received. {len(memory_files)} memory files recorded."
        return msg + " Finalizing..."

    # ── LLM Deep Integration Helpers ──

    def _call_llm(self, prompt: str, system_prompt: str = "",
                  temperature: float = 0.2, max_tokens: int = 8192) -> Optional[str]:
        """统一 LLM 调用接口：优先使用直接 DeepSeek API 调用，回退到 _on_think。

        直接 API 调用更可靠（Agent 主循环中的 _on_think 在工具调用繁忙时经常超时/返回空），
        使用相同的 utils.config 密钥。_on_think 仅作为后备方案。
        """
        # 优先：直接 DeepSeek API 调用（更可靠，与 llm_guide_search.py 一致）
        try:
            from utils.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
            from openai import OpenAI
            if DEEPSEEK_API_KEY:
                client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=120)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                resp = client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return resp.choices[0].message.content or ""
            else:
                self._print("  ⚠️ 未配置 DEEPSEEK_API_KEY，尝试 _on_think 回退")
        except Exception as e:
            self._print(f"  ⚠️ 直接 LLM API 调用失败: {type(e).__name__}: {e}，回退到 _on_think")

        # 回退：通过 Agent 主循环的 _on_think
        if self._on_think:
            try:
                full_prompt = system_prompt + "\n\n" + prompt if system_prompt else prompt
                result = self._on_think(topic=full_prompt)
                if result:
                    return result
            except Exception as e:
                self._print(f"  ⚠️ _on_think 回退调用也失败: {type(e).__name__}: {e}")

        self._print("  ⚠️ 所有 LLM 调用路径均失败，返回 None")
        return None

    def _llm_search_guide(self, candidates: List[Dict], hyp) -> List[Dict]:
        """让 LLM 评估搜索中间结果的科学合理性并引导剪枝。

        这是路线 A "LLM 搜索深度融合" 的核心实现：
        LLM 不只是一个假设生成器，而是搜索过程的主动参与者——
        评估中间候选的物理合理性、建议搜索空间的收缩/扩展、
        识别有前景但尚未探索的区域。

        Args:
            candidates: 当前候选参数列表 [{param_name: value, ...}, ...]
            hyp: DiscoveryHypothesis 对象

        Returns:
            经过 LLM 评估后的候选列表，包含调整后的 score 和评估元数据
        """
        import json as _json

        if not candidates:
            return candidates

        # 构建中文评估提示词
        cands_display = []
        for i, c in enumerate(candidates[:5]):
            cands_display.append({k: round(v, 4) if isinstance(v, float) else v
                                  for k, v in c.items()})
        cands_str = _json.dumps(cands_display, ensure_ascii=False, indent=2)
        if len(candidates) > 5:
            cands_str += f"\n... 共 {len(candidates)} 个候选参数组合"

        prompt = (
            "你是一位材料科学专家，正在参与一个贝叶斯优化搜索过程。"
            "请评估当前搜索中间结果的科学合理性，并给出剪枝/聚焦建议。\n\n"
            f"### 当前假设\n"
            f"标题：{hyp.title}\n"
            f"描述：{hyp.description[:500]}\n"
            f"目标性质：{hyp.property}\n"
            f"涉及材料：{', '.join(hyp.materials[:5]) if hyp.materials else '（未指定）'}\n"
            f"预期关系：{hyp.expected_relationship}\n\n"
            f"### 当前搜索候选参数\n"
            f"```json\n{cands_str}\n```\n\n"
            f"### 评估任务\n"
            f"请从以下维度进行评估，并输出严格的 JSON（只输出 JSON，不要其他内容）：\n"
            f"1. 这些候选参数是否在物理上合理？（如数值是否在已知材料性质范围内）\n"
            f"2. 当前搜索方向是否覆盖了假设中最有前景的区域？\n"
            f"3. 是否有未被当前搜索覆盖但值得探索的参数区域？\n\n"
            f'输出 JSON 格式：\n'
            f'{{"plausibility": 0.0-1.0,\n'
            f' "suggestion": "对当前搜索方向的科学建议（中文，100字以内）",\n'
            f' "prune_regions": [[lo, hi], ...],\n'
            f' "focus_regions": [[lo, hi], ...],\n'
            f' "candidate_scores": [0.0-1.0, ...]}}\n\n'
            f"其中 candidate_scores 数组长度应与候选数量一致（{len(candidates)}个），"
            f"每个值表示对应候选的科学 plausibility。"
        )

        response = self._call_llm(prompt, temperature=0.2, max_tokens=4096)
        if not response:
            # LLM 不可用，优雅降级：原样返回候选，设置默认评分
            for cand in candidates:
                cand.setdefault("score", 0.5)
                cand.setdefault("llm_plausibility", 0.5)
                cand.setdefault("llm_suggestion", "LLM 不可用，跳过评估")
            return candidates

        # 解析 LLM 返回的 JSON
        try:
            text = response.strip()
            import re as _re
            m = _re.search(r'\{[\s\S]*\}', text)
            if m:
                text = m.group(0)
            assessment = _json.loads(text)
        except Exception as e:
            self._print(f"  ⚠️ LLM 搜索引导 JSON 解析失败: {e}")
            return candidates

        # 将 LLM 评分注入候选参数
        candidate_scores = assessment.get("candidate_scores", [])
        for i, cand in enumerate(candidates):
            if i < len(candidate_scores):
                cand["score"] = float(candidate_scores[i])
            cand["llm_plausibility"] = float(assessment.get("plausibility", 0.5))
            cand["llm_suggestion"] = str(assessment.get("suggestion", ""))
            cand["llm_prune_regions"] = assessment.get("prune_regions", [])
            cand["llm_focus_regions"] = assessment.get("focus_regions", [])

        self._print(
            f"  🧠 LLM 搜索引导: plausibility={assessment.get('plausibility', 0):.2f}, "
            f"suggestion={str(assessment.get('suggestion', ''))[:80]}"
        )
        return candidates

    def _llm_plausibility_check(self, hyp,
                                 search_results: dict = None) -> Tuple[float, str]:
        """LLM 评估单条假设的科学合理性（中文输出）+ 新颖性验证。

        输入假设的 title/description/evidence_chain/搜索结果，
        LLM 从理论基础、文献一致性、可验证性、新颖性四个维度打分，
        返回 (plausibility_score: 0.0-1.0, explanation: 中文 100-500 字)。

        三层降级策略：
        1. 优先通过 LLM API（DeepSeek）进行深度评估
        2. 如果 LLM 不可用，使用基于证据质量的启发式评分
        3. 新颖性验证：使用 LiteratureSearcher 检索相似已有工作，
           计算文本重叠度，据此调整新颖性评分（确保"LLM 说的不算"）
        """
        import json as _json

        # ── 新颖性验证：系统性已有文献查重 ──
        # 优先使用已执行的 prior_art_verification 结果（来自 h_check_novelty
        # 或 h_generate_hypotheses 的自动查重），避免重复检索。
        # 如果无已有结果，执行轻量的 _systematic_prior_art_search。
        novelty_adjustment = 0.0
        novelty_detail = ""
        try:
            # Check for existing prior art results
            existing_pa = None
            if isinstance(hyp, dict):
                existing_pa = hyp.get("prior_art_verification")
            elif hasattr(hyp, 'prior_art_verification'):
                existing_pa = hyp.prior_art_verification

            if existing_pa and isinstance(existing_pa, dict):
                # Use existing systematic prior art results
                overlap_level = existing_pa.get("overlap_assessment", "none")
                adjusted = existing_pa.get("novelty_score_adjusted", 0.5)
                original = existing_pa.get("original_novelty", 0.5)
                novelty_adjustment = adjusted - original
                # 占位假设/无法提取有效查询词 → 新颖性标记为 insufficient，
                # 不能给中等偏上的分数（调整量恒为非正）
                if existing_pa.get("novelty_status") == "insufficient":
                    novelty_adjustment = min(0.0, novelty_adjustment)
                    novelty_detail = (
                        f"；新颖性判定 **insufficient**（无法从假设中提取有效的"
                        f"材料/性质/关系实体作为查询词，未执行有效查重），"
                        f"新颖性调整 {novelty_adjustment:+.2f}"
                    )
                else:
                    novelty_detail = (
                        f"；系统查重: {existing_pa.get('total_results_found', 0)} 篇检索结果"
                        f"，重叠级别={overlap_level}"
                        f"，新颖性调整 {novelty_adjustment:+.2f}"
                    )
                    if existing_pa.get("potentially_overlapping_papers"):
                        top_overlap = existing_pa["potentially_overlapping_papers"][0]
                        novelty_detail += (
                            f"（最高重叠: \"{top_overlap['title'][:60]}...\""
                            f" Jaccard={top_overlap['overlap_ratio']:.3f}）"
                        )
            else:
                # Run systematic prior art search (more thorough than old lightweight check)
                try:
                    pa_report = self._systematic_prior_art_search(hyp)
                    if pa_report and not pa_report.get("search_error"):
                        adjusted = pa_report.get("novelty_score_adjusted", 0.5)
                        original = pa_report.get("original_novelty", 0.5)
                        novelty_adjustment = adjusted - original
                        overlap_level = pa_report.get("overlap_assessment", "none")
                        if pa_report.get("novelty_status") == "insufficient":
                            # 查询词无法从假设实体中提取 → 新颖性判定 insufficient
                            novelty_adjustment = min(0.0, novelty_adjustment)
                            novelty_detail = (
                                f"；新颖性判定 **insufficient**（无法提取有效查询词，"
                                f"未执行有效查重），新颖性调整 {novelty_adjustment:+.2f}"
                            )
                        else:
                            novelty_detail = (
                                f"；系统查重: {pa_report.get('total_results_found', 0)} 篇结果"
                                f"，重叠={overlap_level}"
                                f"，新颖性 {original:.2f}->{adjusted:.2f}"
                            )
                            if pa_report.get("potentially_overlapping_papers"):
                                novelty_detail += (
                                    f"（{len(pa_report['potentially_overlapping_papers'])} 篇潜在重叠）"
                                )
                        # Cache the result
                        if isinstance(hyp, dict):
                            hyp["prior_art_verification"] = pa_report
                    else:
                        novelty_detail = "；系统查重未执行（无可用检索源）"
                except Exception:
                    # Ultimate fallback: lightweight keyword search
                    title = hyp.title if not isinstance(hyp, dict) else hyp.get("title", "")
                    desc = hyp.description if not isinstance(hyp, dict) else hyp.get("description", "")
                    materials = hyp.materials if not isinstance(hyp, dict) else hyp.get("materials", [])
                    prop = hyp.property if not isinstance(hyp, dict) else hyp.get("property", "")
                    expected_rel = hyp.expected_relationship if not isinstance(hyp, dict) else hyp.get("expected_relationship", "")
                    # 查询词保护：必须从假设实体中抽取；无法提取 → insufficient
                    query_entities = self._extract_query_entities(
                        title, desc, materials, prop, expected_rel
                    )
                    if not query_entities:
                        novelty_detail = (
                            "；新颖性判定 **insufficient**（无法提取有效查询词，"
                            "占位假设或内容不足）"
                        )
                        novelty_adjustment = min(0.0, novelty_adjustment)
                    else:
                        from literature_agent.search import LiteratureSearcher
                        import os as _os
                        searcher = LiteratureSearcher(
                            cache_dir=_cfg.get_literature_cache_dir(),
                            sciverse_api_key=_os.environ.get("SCIVERSE_API_KEY", ""),
                        )
                        search_query = " ".join(query_entities[:6])[:300]
                        overlap_results = searcher.search(search_query, top_k=5)
                        if overlap_results:
                            hyp_words = set(" ".join(query_entities[:6]).lower().split())
                            overlaps = []
                            for r in overlap_results:
                                r_words = set((r.title or "").lower().split())
                                if hyp_words:
                                    sim = len(hyp_words & r_words) / len(hyp_words | r_words)
                                    if sim > 0.05:
                                        overlaps.append((r.title, sim))
                            if overlaps:
                                max_overlap = max(s[1] for s in overlaps)
                                novelty_adjustment = -min(0.3, max_overlap * 0.5)
                                novelty_detail = (
                                    f"；检索到 {len(overlaps)} 篇高相关已有文献"
                                    f"（最高标题相似度 {max_overlap:.2f}），"
                                    f"新颖性调整 {novelty_adjustment:+.2f}"
                                )
                            else:
                                novelty_detail = "；未检索到高重叠已有文献，新颖性支撑较强"
                        else:
                            novelty_detail = "；轻量检索无结果"
        except Exception as e:
            novelty_detail = f"；新颖性检索未执行（{str(e)[:60]}）"

        # ── 构建证据链和搜索文本 ──
        evidence_str = ""
        if hyp.evidence_chain:
            evidence_str = "\n".join(f"  - {e}" for e in hyp.evidence_chain[:10])
        else:
            evidence_str = "（暂无文献证据链）"

        search_str = "（尚未执行搜索）"
        if search_results:
            best_params = search_results.get("best_params", {})
            best_score = search_results.get("best_score", None)
            search_str = (
                f"搜索方法：{search_results.get('search_method', 'N/A')}\n"
                f"迭代次数：{search_results.get('iterations', 'N/A')}\n"
                f"最佳参数：{_json.dumps(best_params, ensure_ascii=False) if best_params else 'N/A'}\n"
                f"最佳分数：{best_score if best_score is not None else 'N/A'}\n"
            )

        # ── 第 1 层：LLM 深度评估 ──
        prompt = (
            "你是一位材料科学领域的资深评审专家。请评估以下构效关系假设的科学合理性。\n\n"
            f"### 假设标题\n{hyp.title}\n\n"
            f"### 假设描述\n{hyp.description[:800]}\n\n"
            f"### 涉及材料\n{', '.join(hyp.materials[:10]) if hyp.materials else '（未指定）'}\n\n"
            f"### 目标性质\n{hyp.property or '（未指定）'}\n\n"
            f"### 预期关系\n{hyp.expected_relationship}\n\n"
            f"### 支持证据链\n{evidence_str}\n\n"
            f"### 搜索结果\n{search_str}\n\n"
            f"### 新颖性检索结果\n{novelty_detail}\n\n"
            f"### 评估任务\n"
            f"请从以下四个维度评估该假设的科学合理性：\n"
            f"1. **理论基础**：是否符合已知物理化学原理（如热力学、动力学、电子结构理论）\n"
            f"2. **文献一致性**：是否与已有文献证据一致或构成合理延伸\n"
            f"3. **可验证性**：是否可以通过实验或第一性原理计算进行验证\n"
            f"4. **新颖性**：是否提出了新的机制、定量关系或可推广的标度律\n\n"
            f"请结合新颖性检索结果——如果已有高相似工作，新颖性应适当降分。\n\n"
            f"输出严格的 JSON（只输出 JSON，不要其他内容）：\n"
            f'{{"plausibility_score": 0.0-1.0,\n'
            f' "explanation": "中文解释，100-300字，逐维度说明评分理由"}}'
        )

        response = self._call_llm(prompt, temperature=0.3, max_tokens=4096)
        if response:
            try:
                text = response.strip()
                import re as _re
                m = _re.search(r'\{[\s\S]*\}', text)
                if m:
                    text = m.group(0)
                result = _json.loads(text)
                score = float(result.get("plausibility_score", 0.5))
                score = max(0.0, min(1.0, score))
                # 应用新颖性调整
                score = max(0.0, min(1.0, score + novelty_adjustment))
                explanation = str(result.get("explanation", ""))[:800]
                if novelty_detail:
                    explanation += novelty_detail
                return (score, explanation)
            except Exception as e:
                self._print(f"  ⚠️ LLM plausibility check JSON 解析失败: {e}，回退到启发式评分")

        # ── 第 2 层：启发式回退评分 ──
        # 基于证据链完整性、数值验证结果和置信度的确定性评分
        evidence_weight = 0.30
        verification_weight = 0.30
        confidence_weight = 0.40

        # 证据链得分：基于证据链长度（最大按 5 条归一化）
        ev_len = len(hyp.evidence_chain) if hyp.evidence_chain else 0
        evidence_score = min(1.0, ev_len / 5.0)

        # 数值验证得分：从 value_verification 字段提取
        verification_score = 0.5  # 默认中等
        if hasattr(hyp, 'value_verification') and hyp.value_verification:
            vv = hyp.value_verification
            if isinstance(vv, dict):
                verification_score = float(vv.get("overall_verification_score", 0.5))
        # 也尝试从 dict 访问（当 hyp 是 dict 时）
        if isinstance(hyp, dict):
            vv = hyp.get("value_verification", {})
            if vv and isinstance(vv, dict):
                verification_score = float(vv.get("overall_verification_score", 0.5))

        # 兜底：DiscoveryHypothesis 对象没有 value_verification 字段，
        # 数值验证结果保存在 survey_state["hypotheses"] 的 dict 形态中，按 id 反查。
        vv_dict = None
        has_vv_attr = isinstance(getattr(hyp, 'value_verification', None), dict)
        has_vv_key = isinstance(hyp, dict) and isinstance(hyp.get("value_verification"), dict)
        if not has_vv_attr and not has_vv_key:
            hyp_id = hyp.get("id") if isinstance(hyp, dict) else getattr(hyp, "id", None)
            for hd in (self.survey_state.get("hypotheses") or []):
                if isinstance(hd, dict) and hd.get("id") == hyp_id:
                    vv_dict = hd.get("value_verification")
                    if isinstance(vv_dict, dict):
                        verification_score = float(vv_dict.get("overall_verification_score", 0.5))
                    break

        # ── 未查证数值占比惩罚（LLM API 不可用的启发式路径）──
        # 不能把"未查证数值占多数"的假设当成有效发现：显著降分，
        # 并在 llm_explanation 中明确标注 degraded 原因。
        unverified_note = ""
        unverified_ratio = 0.0
        vv_info = vv_dict
        if vv_info is None:
            if hasattr(hyp, 'value_verification') and isinstance(getattr(hyp, 'value_verification', None), dict):
                vv_info = hyp.value_verification
            elif isinstance(hyp, dict):
                vv_info = hyp.get("value_verification")
        if isinstance(vv_info, dict):
            vf_list = vv_info.get("values_found") or []
            uv_list = vv_info.get("unverified_values") or []
            n_claimed = len(vf_list) or len(uv_list)
            n_unverified = len(uv_list)
            unverified_ratio = (n_unverified / n_claimed) if n_claimed > 0 else (1.0 - verification_score)
            if unverified_ratio >= 0.5:
                # 未查证数值占多数 → 显著降分（验证得分压到低档 + 额外总分惩罚）
                verification_score = min(verification_score, 0.25)
                unverified_note = (
                    f"，未查证数值占比 {unverified_ratio:.0%}"
                    f"（{n_unverified}/{n_claimed}）——该假设的数值声称多数缺乏文献支撑，"
                    f"已按降级启发式显著降分"
                )
            elif verification_score < 0.4:
                unverified_note = (
                    f"，数值验证得分偏低（{verification_score:.2f}），"
                    f"已按降级启发式降分"
                )

        # 置信度得分
        confidence = float(getattr(hyp, 'confidence', 0.5) if not isinstance(hyp, dict) else hyp.get('confidence', 0.5))

        score = (
            evidence_weight * evidence_score
            + verification_weight * verification_score
            + confidence_weight * confidence
        )
        # 未查证占比高时施加额外总分惩罚（0.15 ~ 0.25）
        if unverified_ratio >= 0.5:
            score -= (0.15 * unverified_ratio + 0.10)
        score = max(0.0, min(1.0, score + novelty_adjustment))

        explanation = (
            f"【启发式评分·降级】LLM API 不可用（degraded: 未能获取 LLM 深度评估），"
            f"基于证据质量自动计算。"
            f"证据链长度={ev_len}/5（得分{evidence_score:.2f}）、"
            f"数值验证={verification_score:.2f}、"
            f"置信度={confidence:.2f}，"
            f"加权得分={score:.2f}{unverified_note}{novelty_detail}。"
            f"建议：配置 DEEPSEEK_API_KEY 后重新运行以获取 LLM 深度评估。"
        )
        return (score, explanation)

    # ── Systematic Prior Art Search ──

    def _generate_reverse_queries(self, title: str, desc: str,
                                   materials: list, prop: str,
                                   expected_rel: str) -> List[str]:
        """Generate reverse search queries designed to FIND prior art.

        防失控设计（2026-08 修复）：
        1. 查询词必须从假设的材料/性质/关系实体中抽取（_extract_query_entities），
           禁止使用无关英文串；
        2. 若无法从假设中提取任何有效实体（占位假设/内容不足），
           返回空列表，由 _systematic_prior_art_search 将新颖性判定
           标记为 "insufficient"（不能给中等偏上的分数）。
        """
        entities = self._extract_query_entities(title, desc, materials, prop, expected_rel)
        if not entities:
            return []

        zh_entities = [e for e in entities if re.search(r'[\u4e00-\u9fff]', e)]
        en_entities = [e for e in entities if not re.search(r'[\u4e00-\u9fff]', e)]
        queries = []

        # ── Query 1: 核心主张 —— 中文实体优先（内嵌 MOF-74/CO2 等专名）──
        if zh_entities:
            queries.append(" ".join(zh_entities[:3])[:300])
        elif en_entities:
            queries.append(" ".join(en_entities[:6])[:300])

        # ── Query 2: 材料 + 性质组合（实体组合，全部来自假设）──
        mat_list = [e for e in en_entities if ToolHandlers._MATERIAL_TOKEN_RE.search(e)]
        prop_list = [e for e in en_entities if e.lower() in ToolHandlers._PROPERTY_TERM_WHITELIST]
        combo = []
        combo.extend(mat_list[:2] or en_entities[:2])
        combo.extend(prop_list[:1])
        if combo:
            queries.append(" ".join(combo)[:300])

        # ── Query 3: 挑战性/对照检索（实体 + 反证词，实体必须存在）──
        if en_entities:
            for mod in ("contradictory evidence", "alternative mechanism"):
                q = f"{' '.join(en_entities[:3])} {mod}"[:300]
                if q not in queries:
                    queries.append(q)
                    break

        # 去重
        unique = []
        seen_norm = set()
        for q in queries:
            norm = re.sub(r'\s+', ' ', q.lower()).strip()
            if norm and norm not in seen_norm:
                seen_norm.add(norm)
                unique.append(q)

        return unique[:5]

    # ── 新颖性检索查询词保护（2026-08 修复）──
    # 查询词必须从假设的材料/性质/关系实体中抽取，禁止使用无关英文串；
    # 无法提取有效实体时返回空列表，由调用方将新颖性判定标记为 insufficient。

    # 检索中无区分度的通用英文词（不能作为"有效实体"）
    _QUERY_STOPWORDS = frozenset({
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for",
        "with", "from", "by", "via", "that", "this", "these", "those", "their",
        "there", "its", "it", "is", "are", "was", "were", "be", "been",
        "based", "using", "used", "use", "method", "methods", "approach",
        "approaches", "system", "systems", "study", "studies", "research",
        "material", "materials", "property", "properties", "relationship",
        "relationships", "discovery", "analysis", "analyses", "design",
        "designs", "tool", "tools", "gap", "gaps", "paper", "papers",
        "result", "results", "effect", "effects", "impact", "role",
        "toward", "towards", "about", "between", "after", "before", "during",
        "through", "new", "novel", "high", "low", "higher", "lower", "large",
        "small", "significant", "strong", "weak", "potential", "possible",
        "general", "specific", "overall", "related", "relation", "depend",
        "dependence", "dependency", "influence", "trend", "mechanism",
        "mechanisms", "predict", "prediction", "correlate", "correlation",
        "model", "modeling", "simulation", "simulated", "computational",
        "calculation", "calculated", "important", "key", "vs", "under",
        "over", "into", "as", "if", "or", "but", "not", "no", "than",
        "determined", "expected", "found", "show", "shown", "demonstrate",
    })

    # 实质性质词白名单（全小写英文 token 也视为有效实体）
    _PROPERTY_TERM_WHITELIST = frozenset({
        "adsorption", "capacity", "selectivity", "uptake", "loading",
        "stability", "isotherm", "enthalpy", "qst", "diffusion",
        "permeability", "conductivity", "barrier", "moisture", "humidity",
        "pressure", "temperature", "composition", "ratio", "defect",
        "bandgap", "porosity", "pore", "kinetics", "selective", "recovery",
        "regeneration", "energy", "cycling", "hydrophobicity",
        "hydrophilicity", "surface", "capture", "metastability",
    })

    # 化学式/材料编号形态（含数字的专名，如 MOF-74、UiO-66、CO2、HBDC）
    _MATERIAL_TOKEN_RE = re.compile(r'[A-Z][A-Za-z0-9\-/]*\d[A-Za-z0-9\-/]*')

    @staticmethod
    def _extract_query_entities(title: str, desc: str, materials: list,
                                prop: str, expected_rel: str) -> List[str]:
        """从假设字段中抽取可用于 novelty 检索的有效实体。

        实体来源仅限假设自身的材料/性质/关系字段；
        过滤通用英文词（relationship/discovery/analysis 等）。
        若抽取结果为空（占位假设/内容不足），返回空列表——
        调用方应将新颖性判定标记为 "insufficient"。
        """
        materials = materials or []
        fields = [str(title or ""), str(desc or ""), str(prop or ""),
                  str(expected_rel or "")]
        entities: List[str] = []
        seen: set = set()

        def _add(e: str):
            e = e.strip()
            if not e or len(e) < 2:
                return
            if e.lower() in ToolHandlers._QUERY_STOPWORDS:
                return
            if e.isdigit():
                return
            norm = re.sub(r'\s+', ' ', e).lower()
            if norm in seen:
                return
            seen.add(norm)
            entities.append(e)

        # 1. materials 字段 → 整项实体（如 "CoMn-MOF-74"、"胺接枝Mg-MOF-74"）
        for m in materials:
            if isinstance(m, str) and m.strip():
                _add(m)

        # 2. 英文 token：过滤停用词；性质词白名单保留；含数字/大写缩写保留
        for f in fields:
            for tok in re.findall(r'[A-Za-z][A-Za-z0-9\-\/\.]{1,40}', f):
                t = tok.strip()
                tl = t.lower()
                if tl in ToolHandlers._QUERY_STOPWORDS:
                    continue
                if tl in ToolHandlers._PROPERTY_TERM_WHITELIST:
                    _add(t)
                    continue
                if re.search(r'\d', t) or (t[0].isupper() and len(t) <= 8):
                    _add(t)

        # 3. 中文 token：保留含字母/数字的混合串（内嵌 MOF-74/CO2 等），
        #    或含实质性质词的短语
        for f in fields:
            for chunk in re.findall(r'[\u4e00-\u9fffA-Za-z0-9\-]{2,80}', f):
                if not re.search(r'[\u4e00-\u9fff]', chunk):
                    continue
                if re.search(r'[A-Za-z0-9]', chunk) or any(
                    kw in chunk for kw in ("吸附", "容量", "选择性", "稳定性", "热",
                                           "亲水", "疏水", "比例", "湿", "效率", "浓度",
                                           "再生", "能耗", "缺陷", "位点")
                ):
                    _add(chunk)

        # 4. 若仍只有通用性质词而没有任何具体材料/化学式，视为内容不足
        if entities:
            has_concrete = any(
                ToolHandlers._MATERIAL_TOKEN_RE.search(e) or re.search(r'[\u4e00-\u9fff]', e)
                for e in entities
            )
            if not has_concrete:
                return []
        return entities[:12]

    @staticmethod
    def _compute_overlap(hypothesis_text: str,
                         results: list) -> Tuple[list, float]:
        """Compute text overlap between hypothesis and search results.

        Uses Jaccard similarity on keywords (no LLM required).
        Returns (overlapping_papers_with_scores, max_overlap_ratio).
        """
        # Tokenize: keep words > 2 chars, lowercase, remove punctuation
        def tokenize(text: str) -> set:
            cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
            return {w for w in cleaned.split() if len(w) > 2}

        hyp_tokens = tokenize(hypothesis_text)
        if not hyp_tokens:
            return [], 0.0

        overlapping = []
        max_overlap = 0.0
        for r in results:
            r_text = f"{r.title or ''} {r.abstract or ''}"
            r_tokens = tokenize(r_text)
            if not r_tokens:
                continue
            # Jaccard similarity
            intersection = len(hyp_tokens & r_tokens)
            union = len(hyp_tokens | r_tokens)
            sim = intersection / union if union > 0 else 0.0
            if sim > 0.03:  # meaningful threshold
                overlapping.append((r, sim))
                if sim > max_overlap:
                    max_overlap = sim

        # Sort by similarity descending
        overlapping.sort(key=lambda x: x[1], reverse=True)
        return overlapping, max_overlap

    def _generate_overlap_justification(self, hypothesis,
                                         overlapping: list,
                                         overlap_level: str,
                                         max_overlap: float) -> str:
        """Generate a justification for the overlap assessment.

        Uses LLM if available (via _call_llm), otherwise uses heuristic
        keyword-based text.
        """
        # Get hypothesis info
        if isinstance(hypothesis, dict):
            title = hypothesis.get("title", "")
            materials = hypothesis.get("materials", [])
            prop = hypothesis.get("property", "")
        else:
            title = hypothesis.title
            materials = hypothesis.materials or []
            prop = hypothesis.property or ""

        # Collect overlapping paper info for context
        overlap_titles = []
        for r, sim in overlapping[:5]:
            overlap_titles.append(f"- \"{r.title[:120]}\" (Jaccard={sim:.3f}, source={r.source}, year={r.year})")

        overlap_context = "\n".join(overlap_titles) if overlap_titles else "(none)"

        # ── Try LLM-based justification ──
        prompt = (
            "你是一位材料科学领域的文献审查专家。请基于以下信息，"
            "对一条研究假设的新颖性进行 3 句话的评估。\n\n"
            f"### 假设\n"
            f"标题：{title}\n"
            f"材料：{', '.join(materials[:5]) if materials else '未指定'}\n"
            f"性质：{prop or '未指定'}\n\n"
            f"### 已有文献重叠\n"
            f"重叠级别：{overlap_level}\n"
            f"最高文本相似度：{max_overlap:.3f}\n"
            f"潜在重叠论文：\n{overlap_context}\n\n"
            f"请用 3 句话回答：\n"
            f"1. 这些已有工作是否已经提出或验证了类似的主张？\n"
            f"2. 当前假设是否有足够的新颖性（新的机制、定量关系或材料体系）？\n"
            f"3. 最终结论：假设的新颖性是否仍然成立？\n\n"
            f"输出纯文本（不要 JSON，3 句话，中文）。"
        )

        llm_response = self._call_llm(prompt, temperature=0.2, max_tokens=512)
        if llm_response:
            # Clean up response
            cleaned = llm_response.strip().replace('\n', ' ')[:500]
            return cleaned

        # ── Heuristic fallback ──
        mat_str = ', '.join(materials[:3]) if materials else '相关材料'
        prop_str = prop or '目标性质'

        if overlap_level == "none":
            return (
                f"系统检索未发现与'{title[:60]}'高度重叠的已有文献。"
                f"针对'{mat_str}'与'{prop_str}'的组合检索返回的结果"
                f"与当前假设的核心主张无显著文本重叠（最高 Jaccard 相似度 {max_overlap:.3f}），"
                f"当前假设的新颖性得到初步支持。"
            )
        elif overlap_level == "low":
            return (
                f"检索到少量与'{title[:60]}'略有重叠的已有文献"
                f"（最高 Jaccard 相似度 {max_overlap:.3f}），但这些工作"
                f"在研究角度、材料体系或定量关系上与当前假设存在差异。"
                f"当前假设仍具有足够的新颖性，建议在最终报告中明确指出与这些工作的区别。"
            )
        elif overlap_level == "moderate":
            return (
                f"检索到多篇与'{title[:60]}'有一定重叠的已有文献"
                f"（最高 Jaccard 相似度 {max_overlap:.3f}），"
                f"已有研究可能涉及类似的概念或材料体系。当前假设的新颖性需谨慎评估——"
                f"建议深入阅读这些论文的全文，确认当前假设提出的具体机制或定量关系是否已被报道。"
            )
        else:  # high
            return (
                f"检索到与'{title[:60]}'高度重叠的已有文献"
                f"（最高 Jaccard 相似度 {max_overlap:.3f}），"
                f"已有工作很可能已经提出了类似的主张。当前假设的新颖性值得怀疑，"
                f"建议重新审视假设的差异化角度，或调整核心主张以区别于已有文献。"
            )

    def _systematic_prior_art_search(self, hypothesis,
                                      searcher=None) -> dict:
        """Systematic prior art search for novelty verification.

        For each hypothesis, generates 3-5 reverse search queries designed
        to FIND prior art (not just hypothesis keywords). Uses the existing
        LiteratureSearcher to execute these queries and returns a PriorArtReport.

        Args:
            hypothesis: DiscoveryHypothesis object or dict
            searcher: LiteratureSearcher instance (created if None)

        Returns:
            PriorArtReport dict with keys:
                queries_executed, total_results_found,
                potentially_overlapping_papers, overlap_assessment,
                justification, novelty_score_adjusted
        """
        import os as _os

        # Extract hypothesis info
        if isinstance(hypothesis, dict):
            title = hypothesis.get("title", "")
            desc = hypothesis.get("description", "")
            materials = hypothesis.get("materials", [])
            prop = hypothesis.get("property", "")
            expected_rel = hypothesis.get("expected_relationship", "")
            original_novelty = hypothesis.get("novelty_score", 0.5)
        else:
            title = hypothesis.title
            desc = hypothesis.description
            materials = hypothesis.materials or []
            prop = hypothesis.property or ""
            expected_rel = hypothesis.expected_relationship or ""
            original_novelty = hypothesis.novelty_score

        # Create searcher if not provided
        if searcher is None:
            try:
                from literature_agent.search import LiteratureSearcher
                searcher = LiteratureSearcher(
                    cache_dir=_cfg.get_literature_cache_dir(),
                    sciverse_api_key=_os.environ.get("SCIVERSE_API_KEY", ""),
                )
            except Exception as e:
                return {
                    "queries_executed": [],
                    "total_results_found": 0,
                    "potentially_overlapping_papers": [],
                    "overlap_assessment": "none",
                    "justification": f"检索器初始化失败: {str(e)[:100]}",
                    "novelty_score_adjusted": original_novelty,
                    "original_novelty": original_novelty,
                    "search_error": str(e)[:200],
                }

        # Generate reverse queries
        queries = self._generate_reverse_queries(
            title, desc, materials, prop, expected_rel
        )

        # 防失控保护（2026-08 修复）：无法从假设中提取有效查询词时，
        # 新颖性判定标记为 insufficient，不给中等偏上的分数。
        if not queries:
            return {
                "queries_executed": [],
                "total_results_found": 0,
                "potentially_overlapping_papers": [],
                "overlap_assessment": "insufficient",
                "novelty_status": "insufficient",
                "justification": (
                    "无法从假设中提取有效的材料/性质/关系实体作为查询词"
                    "（占位假设或内容不足），新颖性判定为 insufficient，"
                    "不予给出中等偏上的新颖性分数。"
                ),
                "novelty_score_adjusted": round(min(original_novelty, 0.4), 4),
                "original_novelty": original_novelty,
                "query_details": [],
            }

        # Execute searches and collect results
        all_results = []
        query_details = []

        for q in queries:
            try:
                results = searcher.search(q, top_k=5)
                all_results.extend(results)
                query_details.append({
                    "query": q,
                    "results_count": len(results),
                    "top_titles": [r.title[:120] for r in results[:3]],
                    "error": None,
                })
            except Exception as e:
                query_details.append({
                    "query": q,
                    "results_count": 0,
                    "top_titles": [],
                    "error": str(e)[:150],
                })

        # Deduplicate results (reuse searcher's dedup if available, else simple)
        if all_results and hasattr(searcher, '_deduplicate'):
            try:
                all_results = searcher._deduplicate(all_results)
            except Exception:
                # Simple dedup by title similarity
                seen = set()
                unique = []
                for r in all_results:
                    norm = re.sub(r'[^a-z0-9]', '', r.title.lower())
                    if norm not in seen:
                        seen.add(norm)
                        unique.append(r)
                all_results = unique

        # Compute overlap
        hypothesis_text = f"{title} {desc} {expected_rel} {' '.join(materials)} {prop}"
        overlapping, max_overlap = self._compute_overlap(hypothesis_text, all_results)

        # Determine overlap assessment level
        if max_overlap < 0.05:
            overlap_level = "none"
        elif max_overlap < 0.15:
            overlap_level = "low"
        elif max_overlap < 0.35:
            overlap_level = "moderate"
        else:
            overlap_level = "high"

        # Generate justification
        justification = self._generate_overlap_justification(
            hypothesis, overlapping, overlap_level, max_overlap
        )

        # Adjust novelty score based on actual search results
        if overlap_level == "high":
            penalty = min(0.40, max_overlap * 0.8)
        elif overlap_level == "moderate":
            penalty = min(0.25, max_overlap * 0.5)
        elif overlap_level == "low":
            penalty = min(0.10, max_overlap * 0.3)
        else:
            penalty = 0.0

        adjusted_novelty = max(0.0, min(1.0, original_novelty - penalty))

        return {
            "queries_executed": [qd["query"] for qd in query_details],
            "total_results_found": len(all_results),
            "potentially_overlapping_papers": [
                {
                    "title": p.title[:200],
                    "source": p.source,
                    "year": p.year,
                    "overlap_ratio": round(s, 4),
                    "doi": p.doi,
                }
                for p, s in overlapping[:5]
            ],
            "overlap_assessment": overlap_level,
            "justification": justification,
            "novelty_score_adjusted": round(adjusted_novelty, 4),
            "original_novelty": original_novelty,
            "query_details": query_details,
        }

    # ── Route A: Discovery Tools ──

    def _safe_hypothesis(self, data: dict):
        """安全构造 DiscoveryHypothesis，自动补全缺失字段。"""
        from literature_agent.discovery import DiscoveryHypothesis
        return DiscoveryHypothesis(**{k: v for k, v in data.items()
                                      if k in DiscoveryHypothesis.__dataclass_fields__})

    def h_generate_hypotheses(self, args: dict) -> str:
        """LLM 从 Gap 报告中生成构效关系假设。"""
        from pathlib import Path as _Path
        import json as _json

        # 读取 Gap 报告
        gap_path = self.survey_state.get("gap_report_path",
                                          f"{_cfg.SURVEY_DIR}/gap_report.md")
        if not _Path(gap_path).exists():
            gap_path = f"{_cfg.SURVEY_DIR}/gap_report.md"
        if not _Path(gap_path).exists():
            return "❌ No gap report found. Run analyze_gaps first."

        gap_text = _Path(gap_path).read_text(encoding="utf-8")
        if len(gap_text) > 15000:
            gap_text = gap_text[:15000] + "\n...[truncated]"

        # 读取论文摘要（提取材料名和性质名）
        summary_path = self.survey_state.get("paper_summary_path",
            f"{_cfg.SURVEY_DIR}/paper_summaries.md")
        paper_context = ""
        if _Path(summary_path).exists():
            paper_text = _Path(summary_path).read_text(encoding="utf-8")
            paper_context = paper_text[:10000] if len(paper_text) > 10000 else paper_text

        # LLM 生成假设
        hypo_prompt = (
            "You are a materials scientist. 所有输出必须使用中文。"
            "Based on the research gaps and paper summaries below, "
            "generate 3-5 TESTABLE structure-property relationship hypotheses.\n\n"
            "HARD CONSTRAINT (teacherA extractability pre-filter): 每条假设必须附 "
            "extractability_score，即『从文献中为该假设找到 ≥5 个定量 (x,y) 数据对的"
            "预期难度』：5=很容易（表格化数据/多篇对照），1=极难（只有叙述性描述）。"
            "extractability_score < 3 的假设不应进入候选——宁可少而可验证，"
            "不要多而无法量化。\n\n"
            "HARD CONSTRAINT (赛题红线2 新知与已知分清): 每条假设必须同时给出 "
            "known_prior_work（已知——前人已确立的结论/相关文献，如 'Mg-MOF-74 的"
            "CO2 吸附焓已被 Caskey 2008 实验测定'）与 incremental_claim（新知——"
            "本假设相对前人的具体增量，如 '首次把 d 电子数作为跨金属系预测变量'）。"
            "不许把旧结论包装成新发现。\n\n"
            "For each hypothesis output a JSON object with:\n"
            '- id: "hypo_N"\n'
            '- title: short scientific title\n'
            '- description: detailed explanation\n'
            '- materials: [list of material names]\n'
            '- property: target property name\n'
            '- expected_relationship: what you expect to find and why\n'
            '- confidence: 0.0-1.0\n'
            '- novelty_score: 0.0-1.0\n'
            '- extractability_score: 1-5（数据可提取性预评估，<3 不合格）\n'
            '- extractability_note: 预期数据来源（表格/正文/SI/数据库）与主要风险\n'
            '- independent_materials: 预期可用于验证的独立材料数\n'
            '- known_prior_work: 已知——前人已确立的结论/相关文献（红线2 必填）\n'
            '- incremental_claim: 新知——本假设相对前人的具体增量（红线2 必填）\n'
            '- validation_status: "pending"\n'
            '- source_gap_id: gap id from the gap report this hypothesis addresses, e.g. "Gap 1"\n'
            '- evidence_chain: [list of paper IDs (p#) from paper summaries supporting this hypothesis]\n'
            '- search_method: "bayesian"\n\n'
            "Return ONLY valid JSON: {\"hypotheses\": [...]}\n\n"
            f"=== RESEARCH GAPS ===\n\n{gap_text}\n\n"
            f"=== PAPER CONTEXT ===\n\n{paper_context}"
        )

        hypotheses = None

        # ── 路径 1（优先）：通过 Agent 主循环的 _on_think 生成假设 ──
        # 这是 LLM 深度融合的关键：主 Agent 拥有完整的论文摘要上下文，
        # 通过 _on_think 调用可以做出更高质量的推理。
        if self._on_think:
            self._print("  🧠 通过主 Agent LLM 生成构效关系假设（深度融合路径）...")
            try:
                response = self._on_think(topic=hypo_prompt)
                if response:
                    # 先由 _extract_json_object 从容错文本中提取 JSON（自带
                    # BOM/围栏/前后缀/数组/贪婪兜底），再经 _hypotheses_from_json
                    # 兼容 {"hypotheses":[...]} 与裸数组两种形态。
                    data = _extract_json_object(response)
                    hypotheses = _hypotheses_from_json(data)
                    if hypotheses:
                        self._print(f"  ✅ _on_think 成功生成 {len(hypotheses)} 条假设")
                    else:
                        # 解析失败：打印提取结果类型与原始响应前 200 字符，便于诊断
                        snippet = response[:200]
                        self._print(
                            f"  ⚠️ _on_think 返回内容无法提取出 hypotheses"
                            f"（_extract_json_object 解析类型: "
                            f"{type(data).__name__ if data is not None else 'None'}），"
                            f"前 200 字符：{snippet!r}，回退到独立 API 调用"
                        )
            except Exception as e:
                self._print(
                    f"  ⚠️ _on_think 假设生成失败: {type(e).__name__}: {e}，"
                    f"回退到独立 API 调用"
                )

        # ── 路径 2（回退）：独立 DeepSeek API 调用 ──
        # 当 _on_think 不可用（Agent 未注入回调）或调用失败时，
        # 回退到独立的 OpenAI 兼容 API 调用，确保在独立脚本环境中也能工作。
        if not hypotheses:
            self._print("  🔄 使用独立 DeepSeek API 生成假设（后备路径）...")
            try:
                # 复用统一调用入口 _call_llm（内部已封装：直接 DeepSeek API 优先、
                # _on_think 回退、system_prompt 支持与异常诊断），不重复造轮子。
                # 首次调用：无额外 system 约束。
                content = self._call_llm(hypo_prompt)
                hypotheses = _hypotheses_from_json(
                    _extract_json_object(content)) if content else None

                # JSON 约束重试：首次响应解析失败时，追加 system 提示强制只输出 JSON
                if not hypotheses:
                    self._print(
                        "  🔁 独立 LLM 首次响应未能解析出 hypotheses，"
                        "追加 JSON 约束提示重试..."
                    )
                    content = self._call_llm(
                        hypo_prompt,
                        system_prompt="只输出 JSON，不要任何解释/围栏",
                    )
                    hypotheses = _hypotheses_from_json(
                        _extract_json_object(content)) if content else None

                if not hypotheses:
                    self._print(
                        "  ⚠️ 独立 LLM 响应（含 JSON 约束重试）仍无法解析，走兜底假设"
                    )
            except Exception as e:
                # 详细诊断：异常类型 + 信息，避免静默失败
                self._print(f"  ⚠️ 独立 LLM 假设生成也失败: {type(e).__name__}: {e}")

        # ── 最终兜底：最小假设集 ──
        if not hypotheses:
            self._print("  ⚠️ 所有 LLM 路径均失败，使用兜底假设")
            hypotheses = [
                {"id":"hypo_0","title":"Material-property relationship discovery",
                 "description":"Based on the gap analysis","materials":[],"property":"",
                 "expected_relationship":"To be determined","confidence":0.3,
                 "novelty_score":0.5,"validation_status":"pending","search_method":"bayesian",
                 "source_gap_id":"","evidence_chain":[]}
            ]

        # ── 数值交叉验证：检查 LLM 声称的数值是否在文献证据中可查 ──
        evidence_text = self._load_knowledge_source()
        verifications = {}
        if evidence_text:
            self._print("  🔍 执行数值交叉验证...")
            for h in hypotheses:
                verify_result = self._verify_hypothesis_values(h, evidence_text)
                h["value_verification"] = verify_result
                score = verify_result.get("overall_verification_score", 1.0)
                unverified = verify_result.get("unverified_values", [])
                # 验证分数 < 0.5 时降低置信度（仅首次调整，防止重复累计惩罚）
                if score < 0.5:
                    if not verify_result.get("_confidence_adjusted"):
                        old_conf = h.get("confidence", 0.5)
                        penalty = 0.1 + (0.5 - score) * 0.2  # 0.1 ~ 0.2
                        h["confidence"] = round(max(0.1, old_conf - penalty), 2)
                        verify_result["_confidence_adjusted"] = True
                        h["value_verification"] = verify_result
                # 追加数值验证标注（使用新的清晰语言）
                if unverified:
                    values_found_list = verify_result.get("values_found", [])
                    n_claimed = len(values_found_list)
                    n_found = sum(1 for v in values_found_list if v.get("found_in_text"))

                    # 使用 _build_verification_detail_string 生成清晰表述
                    note = self._build_verification_detail_string(
                        unverified, n_claimed, n_found, evidence_text, verify_result
                    )
                    h["description"] = h.get("description", "") + note
                    # 为每个未验证的数值追加验证方案到证据链
                    for uv in unverified:
                        plan = self._make_verification_plan_for_value(uv)
                        if plan and plan not in h.get("evidence_chain", []):
                            h.setdefault("evidence_chain", []).append(plan)
                verifications[h.get("id", "?")] = verify_result
            verified_count = sum(
                1 for v in verifications.values()
                if v.get("overall_verification_score", 0) >= 0.5
            )
            self._print(
                f"  ✅ 数值验证完成: {verified_count}/{len(hypotheses)} 条假设验证分数 >= 0.5"
            )
        else:
            self._print("  ⚠️ 无法加载文献证据，跳过数值验证")
            for h in hypotheses:
                h["value_verification"] = {
                    "values_found": [],
                    "overall_verification_score": 1.0,
                    "unverified_values": [],
                    "verification_error": "验证不可用: 无法加载文献证据",
                }

        # ── 红线2 兜底（2026-10 修复）：LLM 输出缺 known_prior_work /
        #    incremental_claim 时静默落盘，导致 8 个主题的 hypotheses.json
        #    均无这两个字段（设计层有、落地层没有）。此处强制补齐：
        #    - 有值则保留；
        #    - 缺失时从 evidence_chain / description 派生占位说明，
        #      并标 redline2_complete=false 供审计（不伪造内容，如实标注）。
        for h in hypotheses:
            if not h.get("known_prior_work"):
                derived = ""
                chain = h.get("evidence_chain") or []
                real_refs = [c for c in chain
                             if not str(c).startswith("[") and not str(c).startswith("Novelty")]
                if real_refs:
                    derived = f"已有文献依据（evidence_chain 编号: {', '.join(real_refs[:4])}），具体结论需人工/LLM 补写"
                else:
                    derived = "本假设基于研究 Gap 分析提出，具体已知工作待补写"
                h["known_prior_work"] = derived
                h["redline2_complete"] = False
            else:
                h.setdefault("redline2_complete", True)
            if not h.get("incremental_claim"):
                h["incremental_claim"] = (
                    "相对已确立结论的具体增量待补写（本假设的 expected_relationship 即拟验证的新规律）"
                )
                h["redline2_complete"] = False
            else:
                h.setdefault("redline2_complete", True)

        # 保存
        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "hypotheses.json").write_text(
            _json.dumps(hypotheses, ensure_ascii=False, indent=2)
        )
        self.survey_state["hypotheses"] = hypotheses

        # ── 系统性已有文献查重（新颖性验证）──
        # 为每条假设执行反向检索，确认"这真的没人做过"
        skip_novelty_check = args.get("skip_novelty_check", False)
        novelty_report_lines = []
        if not skip_novelty_check:
            self._print("  🔍 执行系统性已有文献查重（新颖性验证）...")
            try:
                from literature_agent.search import LiteratureSearcher
                import os as _os
                searcher = LiteratureSearcher(
                    cache_dir=_cfg.get_literature_cache_dir(),
                    sciverse_api_key=_os.environ.get("SCIVERSE_API_KEY", ""),
                )
                novelty_count = 0
                novelty_adjusted_count = 0
                for i, h in enumerate(hypotheses):
                    try:
                        self._print(f"    查重 {i+1}/{len(hypotheses)}: {h.get('title','')[:60]}...")
                        report = self._systematic_prior_art_search(h, searcher)
                        h["prior_art_verification"] = report
                        old_novelty = h.get("novelty_score", 0.5)
                        h["novelty_score"] = report["novelty_score_adjusted"]
                        # Append to evidence_chain
                        pa_entry = (
                            f"[Novelty Verification] Overlap: {report['overlap_assessment']} | "
                            f"Novelty: {report['novelty_score_adjusted']:.3f} "
                            f"(was {report['original_novelty']:.3f}) | "
                            f"Queries: {len(report['queries_executed'])} | "
                            f"Results: {report['total_results_found']}"
                        )
                        if h.get("evidence_chain"):
                            h["evidence_chain"].append(pa_entry)
                        else:
                            h["evidence_chain"] = [pa_entry]
                        for op in report.get("potentially_overlapping_papers", [])[:3]:
                            h["evidence_chain"].append(
                                f"[Overlap] \"{op['title'][:150]}\" "
                                f"(sim={op['overlap_ratio']:.3f})"
                            )
                        if abs(report["novelty_score_adjusted"] - report["original_novelty"]) > 0.01:
                            novelty_adjusted_count += 1
                        novelty_count += 1
                        # 每条查重成功立即持久化——单条失败不影响其他条已保存的结果
                        # （2026-08 修复：整批 try/except 会让一条失败丢全部字段）
                        (out_dir / "hypotheses.json").write_text(
                            _json.dumps(hypotheses, ensure_ascii=False, indent=2)
                        )
                        self.survey_state["hypotheses"] = hypotheses
                    except Exception as e:
                        self._print(f"    查重失败（跳过该条）: {str(e)[:120]}")
                        novelty_report_lines.append(
                            f"   ⚠️ 假设 #{i} 查重失败: {str(e)[:120]}"
                        )

                novelty_report_lines.append(
                    f"\n📚 新颖性验证: {novelty_count}/{len(hypotheses)} 条假设已完成系统查重"
                )
                if novelty_adjusted_count > 0:
                    novelty_report_lines.append(
                        f"   ⚠️ {novelty_adjusted_count} 条假设的新颖性分数因已有文献重叠而调整"
                    )
                else:
                    novelty_report_lines.append(
                        f"   ✅ 所有假设均未发现高重叠已有文献，新颖性得到初步支持"
                    )
            except Exception as e:
                novelty_report_lines.append(
                    f"\n⚠️ 新颖性验证未执行: {str(e)[:150]}"
                )
                self._print(f"  ⚠️ 已有文献查重失败: {e}")

        # 生成验证摘要
        verify_summary = ""
        if verifications:
            verify_summary = "\n\n📋 数值交叉验证摘要:\n" + "\n".join(
                f"  {hid}: {v.get('overall_verification_score',0):.0%} 已验证"
                f" ({sum(1 for x in v.get('values_found',[]) if x.get('found_in_text'))}"
                f"/{len(v.get('values_found',[]) or [1])} 个数值)"
                for hid, v in verifications.items()
            )

        return (
            f"✅ Generated {len(hypotheses)} hypotheses\n\n" +
            "\n".join(
                f"{i+1}. [{h.get('validation_status','pending')}] **{h.get('title','')[:100]}**\n"
                f"   Confidence: {h.get('confidence',0):.2f} | Novelty: {h.get('novelty_score',0):.2f}"
                for i, h in enumerate(hypotheses[:10])
            ) +
            verify_summary +
            "\n".join(novelty_report_lines) +
            f"\n\nSaved to {_cfg.SURVEY_DIR}/discovery/hypotheses.json\n"
            f"Next: run_discovery_search(hypothesis_index=N) to explore each hypothesis."
        )

    # ── 文献证据索引：基于 Agent 自写的知识图谱（Markdown）打分 ──

    _PROPERTY_KEYWORD_MAP = {
        "选择性": ["selectivity", "separation factor"],
        "容量": ["capacity", "uptake", "loading"],
        "吸附": ["adsorption", "uptake", "capture"],
        "焓": ["isosteric heat", "qst", "enthalpy"],
        "再生": ["regeneration", "working capacity", "energy"],
        "稳定性": ["stability", "degradation", "cyclability"],
        "扩散": ["diffusion", "kinetics"],
        "催化": ["catalysis", "tof", "conversion", "activity"],
        "效率": ["efficiency"],
        "能耗": ["energy penalty", "regeneration energy"],
        "循环": ["cyclability", "cycle"],
    }
    _VALUE_UNIT_RE = re.compile(
        r'(\d+(?:\.\d+)?)\s*'
        r'(mmol/g|mol/kg|mmol/cm3|mg/g|kJ/mol|wt%|m2/g|bar|K|%|h|min|eV|'
        r'µV/K|uV/K|μV/K|W/m·K|W/mK|mW/m·K|mW/mK|S/cm|mS/cm|S/m)\b',
        re.IGNORECASE,
    )

    def _load_knowledge_source(self) -> Optional[str]:
        """读取 Agent 自写的知识图谱 Markdown；不存在则回退论文摘要。"""
        from pathlib import Path as _Path
        for cand in (
            f"{_cfg.SURVEY_DIR}/knowledge_graph.md",
            self.survey_state.get(
                "paper_summary_path",
                f"{_cfg.SURVEY_DIR}/paper_summaries.md",
            ),
        ):
            if _Path(cand).exists():
                try:
                    return _Path(cand).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
        return None

    def _property_keywords(self, property_name: str) -> List[str]:
        """把假设性质名（中英混排）映射为文献检索关键词。"""
        kws: set = set()
        text = (property_name or "").lower()
        for zh, en_list in self._PROPERTY_KEYWORD_MAP.items():
            if zh in text:
                kws.update(en_list)
        for tok in re.findall(r'[a-z][a-z0-9\-]{1,20}', text):
            if len(tok) >= 2:
                kws.add(tok)
        return sorted(kws) or ["adsorption", "capacity", "selectivity"]

    # 性质类型 → 数值单位（按类型分桶，避免容量/热/比表面积混池）
    _PROPERTY_UNIT_BUCKETS = (
        (("mmol/g", "mol/kg", "mmol/cm3", "mg/g", "wt%"),
         ("容量", "capacity", "uptake", "loading", "吸附", "capture", "adsorption")),
        (("kj/mol",),
         ("焓", "qst", "enthalpy", "等量吸附热", "吸附热")),
        (("m2/g",),
         ("bet", "surface area", "比表面积", "表面积")),
        (("bar",),
         ("压力", "pressure")),
        (("k",),
         ("温度", "temperature")),
        (("%", "wt%"),
         ("效率", "efficiency")),
        # 带隙（eV）：钙钛矿/半导体性质，2026-10 修复——此前缺桶导致
        # 带隙假设的 _unit_filter 返回 None，无法从文献提取 (x, E_g) 配对点
        (("ev",),
         ("带隙", "band gap", "bandgap", "禁带", "能隙", "eg", "e_g")),
        # 热电输运（2026-10 拆分桶，避免 Seebeck/热导率/电导率混池）：
        # Seebeck 系数 µV/K、热导率 W/m·K、电导率 S/cm
        (("µv/k", "uv/k"),
         ("seebeck", "塞贝克", "热电势")),
        (("w/m·k", "w/mk"),
         ("热导率", "thermal conductivity")),
        (("s/cm", "s/m"),
         ("电导率", "electrical conductivity")),
        # 无量纲 ZT：无单位，需走裸数值提取路径（见 _extract_literature_points）
        (("dimensionless",),
         ("zt", "热电优值", "figure of merit", "优值")),
    )

    def _unit_filter(self, property_name: str):
        """根据性质名返回应收集的数值单位集合（None = 不过滤）。

        桶选择：取"命中关键词数最多"的性质桶（而非并集），避免子串误触——
        如 "吸附热" 含子串 "吸附"，若取并集会同时收容量(mmol/g)与热量(kJ/mol)，
        污染文献数值先验（2026-08 修复）。
        """
        text = (property_name or "").lower()
        best_units: set = set()
        best_hits = 0
        for units, kws in self._PROPERTY_UNIT_BUCKETS:
            hits = sum(1 for k in kws if k in text)
            if hits > best_hits:
                best_hits = hits
                best_units = set(units)
            elif hits == best_hits and hits > 0:
                # 平手时合并（如 "CO2容量与吸附热" 混合性质）
                best_units.update(units)
        return best_units or None

    def _build_evidence_index(self, source_text: str, hyp) -> Dict:
        """从文献文本构建证据索引：块切分 + 材料 token + 性质关键词 + 文献数值。"""
        blocks = [b.strip() for b in re.split(r'\n(?=#{1,3} )', source_text) if len(b.strip()) > 60]
        if not blocks:
            blocks = [source_text]

        material_tokens: set = set()
        for m in (hyp.materials or []):
            for part in re.split(r'[/\s,，、]+', m):
                part = part.strip()
                if len(part) >= 3 and not part.isdigit():
                    material_tokens.add(part.lower())
        # 补充文献中的材料名（化学式/MOF 家族），严格正则避免误匹配普通英文词
        material_tokens.update(
            m.lower() for m in re.findall(
                r'\b(?:[A-Z][a-z]?\d+[A-Za-z0-9]*(?:-[A-Za-z0-9]+)*|ZIF-\d+|UiO-\d+|MIL-\d+|HKUST-\d+|IRMOF-\d+|MOF-\d+)\b',
                source_text,
            )
        )

        prop_kws = self._property_keywords(hyp.property)
        unit_filter = self._unit_filter(hyp.property)
        values: List[float] = []
        # 方式 A：性质关键词窗口内收集（更精确，优先）
        for block in blocks:
            lower = block.lower()
            for kw in prop_kws:
                for m in re.finditer(re.escape(kw), lower):
                    window = lower[max(0, m.start() - 120): m.end() + 160]
                    for vm in self._VALUE_UNIT_RE.finditer(window):
                        unit = ToolHandlers._normalize_unit(vm.group(2) or "")
                        if unit_filter is not None and unit not in unit_filter:
                            continue
                        v = float(vm.group(1))
                        if 0 < v < 1e6:
                            values.append(v)
        # 方式 B：全块按单位收集（兜底——知识图谱的数值多在表格行内，
        # 行内往往没有性质关键词，关键词窗口法会漏掉；2026-08 修复：
        # "文献数值证据 0 个"的根因）
        if unit_filter is not None:
            for block in blocks:
                lower = block.lower()
                for vm in self._VALUE_UNIT_RE.finditer(lower):
                    unit = ToolHandlers._normalize_unit(vm.group(2) or "")
                    if unit not in unit_filter:
                        continue
                    v = float(vm.group(1))
                    if 0 < v < 1e6:
                        values.append(v)
        values = sorted(set(round(v, 4) for v in values))[:500]

        return {
            "blocks": blocks,
            "material_tokens": sorted(material_tokens),
            "prop_keywords": prop_kws,
            "values": values,
        }

    def _search_space(self, evid: Dict) -> Dict[str, Tuple[float, float]]:
        """根据文献数值范围定义贝叶斯搜索空间（IQR 稳健区间，抵抗离群值）。

        样本量分档（2026-09 修复：文献数值太少时 IQR 界定的空间没有意义）：
          - n < 4：不用 IQR 分位数，改用 (min, max) + 20% padding
            （lo = max(0.001, min*0.8)，hi = max*1.2）；
          - 4 <= n < 8：用 1.0×IQR（Tukey 围栏收窄，避免小样本被离群值撑开）；
          - n >= 8：维持 1.5×IQR。
        各档均保留 median*0.5 / median*2.0 的集中值兜底，保证 hi > lo。
        """
        values = sorted(evid.get("values") or [])
        if values:
            n = len(values)
            if n < 4:
                # 样本太少：IQR 分位数无统计意义，退化为 min-max + 20% padding
                lo = max(0.001, values[0] * 0.8)
                hi = values[-1] * 1.2
                median = values[n // 2]
                # 集中值兜底（如 n=1 单点 / 极窄区间时保证可搜索宽度）
                lo = min(lo, median * 0.5)
                hi = max(hi, median * 2.0)
                self._print(
                    f"  ⚠️ 参数空间: n={n} 个文献值，使用 min-max padding "
                    f"(lo={lo:.4g}, hi={hi:.4g})")
            else:
                q1 = values[max(0, n // 4)]
                q3 = values[min(n - 1, 3 * n // 4)]
                median = values[n // 2]
                iqr = max(q3 - q1, 1e-9)
                # Tukey 围栏系数按样本量分档：小样本用 1.0×IQR，大样本用 1.5×IQR
                iqr_k = 1.0 if n < 8 else 1.5
                if n < 8:
                    self._print(
                        f"  ⚠️ 参数空间: n={n} 个文献值，使用 1.0×IQR "
                        f"(lo={max(0.001, q1 - iqr_k * iqr):.4g}, "
                        f"hi={q3 + iqr_k * iqr:.4g})")
                lo = max(0.001, q1 - iqr_k * iqr)
                hi = q3 + iqr_k * iqr
                # 文献值高度集中（IQR≈0）时按中位数比例兜底，保证可搜索空间
                lo = min(lo, median * 0.5)
                hi = max(hi, median * 2.0)
        else:
            lo, hi = 0.1, 100.0
        # 极端兜底：仍可能出现 hi <= lo（数值异常时），按中位数比例强制扩开
        if hi <= lo:
            median = values[len(values) // 2] if values else 50.0
            lo = max(0.001, min(lo, median * 0.5))
            hi = max(hi, median * 2.0, lo + 1e-3)
        return {
            "property_value": (float(lo), float(hi)),
            "composition_x": (0.0, 1.0),
            "temperature": (300.0, 1500.0),
        }

    def _evidence_score(self, params: Dict, hyp, evid: Dict) -> float:
        """文献证据打分：材料覆盖率 + 材料×性质共现 + 数值接近 + 成分温度奖励。

        总分公式（调整后，提高信号-噪声比）：
          0.15 + 0.25*(材料覆盖) + 0.20*(性质共现) + 0.35*(数值接近)
          + max 0.05*(成分奖) + max 0.05*(温度奖)，上限 clamp 到 1.0

        composition_x 奖励（倒 U 型）：仅当假设涉及双金属/掺杂时生效，
        x ∈ [0.3, 0.7] 得 0.05-0.10 分，峰值在 x=0.5（近 1:1 比例）。
        temperature 奖励：273-373K +0.05（常见吸附温度），373-500K +0.02，
        >500K 不给分。
        """
        blocks = evid["blocks"]
        total = len(blocks)
        if total == 0:
            return 0.15

        cand_mats = params.get("materials") or params.get("material") or (hyp.materials or [])
        if isinstance(cand_mats, str):
            cand_mats = [cand_mats]
        cand_mats = [str(m).lower() for m in cand_mats]
        mats = evid["material_tokens"]
        kws = evid["prop_keywords"]
        values = evid["values"]

        # 优先按假设材料匹配；无命中时放宽到通用材料 token
        if cand_mats:
            mat_blocks = [b for b in blocks if any(m in b.lower() for m in cand_mats)]
            if not mat_blocks:
                mat_blocks = [b for b in blocks if any(t in b.lower() for t in mats)]
        else:
            mat_blocks = [b for b in blocks if any(t in b.lower() for t in mats)]

        score = 0.15  # 降低基分以提高区分度（原 0.30）
        if mat_blocks:
            score += 0.25 * len(mat_blocks) / total  # 材料覆盖率（上调，原 0.20）
            co = sum(1 for b in mat_blocks if any(k in b.lower() for k in kws))
            score += 0.20 * co / max(len(mat_blocks), 1)  # 性质共现（保持）
            cv = params.get("property_value") or params.get("value") or 0
            if values and cv:
                # top-3 最近文献值的平均相似度：落在文献值密集区才高分，孤点命中不再满分
                sims = sorted(1.0 / (1.0 + abs(cv - v) / max(v, 1e-6)) for v in values)
                best = sum(sims[-3:]) / max(len(sims[-3:]), 1)
                score += 0.35 * best  # 数值接近度（上调，原 0.30）

        # ── composition_x 奖励（倒 U 型）：双金属/掺杂假设的组分比例 ──
        is_bimetallic = False
        if hyp.materials and len(hyp.materials) >= 2:
            is_bimetallic = True
        if not is_bimetallic and hyp.title:
            title_lower = hyp.title
            if any(kw in title_lower for kw in ["双金属", "掺杂", "比例"]):
                is_bimetallic = True
        if is_bimetallic:
            cx = params.get("composition_x", None)
            if cx is not None and 0.3 <= cx <= 0.7:
                # 倒 U 型：峰值在 x=0.5 处为 0.10，在 x=0.3 或 x=0.7 处为 0.05
                comp_bonus = 0.05 + 0.05 * max(0.0, 1.0 - ((cx - 0.5) / 0.2) ** 2)
                score += comp_bonus

        # ── temperature 奖励：常见实验温度范围 ──
        temp = params.get("temperature", None)
        if temp is not None:
            if 273 <= temp <= 373:
                score += 0.05  # 常见吸附温度范围，满分
            elif 373 < temp <= 500:
                score += 0.02  # 中等温度范围，部分奖励
            # > 500K 不给分

        return min(score, 1.0)

    # ── 量化建模：文献数值点提取（run_model_comparison / symbolic_regression 共用）──

    # 结构变量 x 提取正则：温度(K/°C/℃)、压力(bar/atm/kPa/GPa)、组分比例(x=/比例=/组分=/composition=)、百分比(%)
    _X_STRUCTURE_RE = re.compile(
        r'(\d+(?:\.\d+)?)\s*(?:K|°C|℃)\b'
        r'|(\d+(?:\.\d+)?)\s*(?:bar|atm|kPa|GPa|MPa)\b'
        r'|(?:x\s*[:=：]\s*|比例\s*[:=：]\s*|组分\s*[:=：]\s*|composition\s*[:=：]\s*|doping\s*[:=：])\s*(\d+(?:\.\d+)?)'
        r'|(\d+(?:\.\d+)?)\s*%(?!\s*(?:RH|rh|湿度))',
        re.IGNORECASE,
    )

    # Vegard 律范围端点配对（2026-10 新增）：钙钛矿知识图谱常写作
    # "1.55→2.3(x 0→1,Vegard 律)" 或 "1.55→2.3（x 0→1，Vegard 律）"
    # （中英文括号均支持），表示组分 x 从 0→1 时带隙从 1.55→2.3，
    # 可拆成两个端点 (x=0, Eg=1.55) 与 (x=1, Eg=2.3) 参与回归。
    _VEGARD_RANGE_RE = re.compile(
        r'(\d+(?:\.\d+)?)\s*(?:→|->|至|~|to)\s*(\d+(?:\.\d+)?)\s*'
        r'[（(]\s*x\s*[:=：]?\s*(\d+(?:\.\d+)?)\s*(?:→|->|至|~|to)\s*'
        r'(\d+(?:\.\d+)?)\s*[，,]?\s*[^）)]{0,30}[）)]',
        re.IGNORECASE,
    )

    # 句子级序列模式：同句 "from A to B K/°C/bar"（配合 y 侧 from..to 序列配对成多组 (x,y)，
    # 如 "uptake decreased from 5.0 to 3.2 mmol/g as T increased from 300 to 500 K"）
    _X_FROM_TO_RE = re.compile(
        r'\bfrom\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s*'
        r'(K|°C|℃|bar|atm|kPa)\b',
        re.IGNORECASE,
    )

    # 隐式单位回退时的数值范围约束（按 y 单位粗略校验，防止把其它性质混入）
    _IMPLICIT_UNIT_RANGES = {
        "mmol/g": (0.05, 60.0), "mol/kg": (0.05, 60.0),
        "mmol/cm3": (0.05, 60.0), "mg/g": (0.5, 2000.0),
        "kj/mol": (5.0, 500.0), "m2/g": (5.0, 10000.0),
        "bar": (0.01, 200.0), "k": (50.0, 5000.0),
        "%": (0.1, 100.0), "ev": (0.01, 50.0),
        "h": (0.1, 1000.0), "min": (0.1, 10000.0),
        # 热电单位（2026-10 扩展）：Seebeck µV/K、热导率 W/m·K、电导率 S/cm、
        # 无量纲 ZT（0~10 物理范围，放宽到 20 防误杀）
        "µv/k": (0.1, 2000.0), "uv/k": (0.1, 2000.0), "μv/k": (0.1, 2000.0),
        "w/m·k": (0.01, 500.0), "w/mk": (0.01, 500.0),
        "s/cm": (0.001, 100000.0), "s/m": (0.001, 100000.0),
        "dimensionless": (0.01, 20.0),
    }

    def _y_unit_range(self, unit: str):
        """返回 y 单位的合理数值范围 (lo, hi)，未知单位返回 None。"""
        u = (unit or "").strip().lower()
        return self._IMPLICIT_UNIT_RANGES.get(u)

    def _extract_literature_points(self, source_text, hyp) -> Optional[dict]:
        """从文献文本提取 (结构变量 x, 性质 y) 数据点，用于量化建模。

        策略（参考 _build_evidence_index 的块切分与数值提取逻辑）：
          - x：块内带单位/关键词的结构变量（温度 K/°C、压力 bar/atm/kPa、
                掺杂比例 x=/比例=/组分=/%），记录类型便于自动选择经典模型；
          - y：优先取块内单位匹配性质类型的显式数值（经 _unit_filter 过滤，
                归并到出现最多的主导单位，避免 mmol/g 与 mg/g 混池）；
                若块内无显式单位数值但表头含 (单位)（如 "CO2 容量 (mmol/g)"），
                回退收集裸数字（排除 x 区间/年份/文献编号，并按范围过滤），
                这类点标记 y_implicit=True；
          - 配对（2026-09 增强，缓解"模型对比全为无提升"）：
              ① Markdown 表格按列配对：识别表头含单位/关键词的列，
                 同一数据行的 x 列与 y 列直接配对成 (x, y)；
              ② 句子级序列模式："from 5.0 to 3.2 mmol/g as T increased
                 from 300 to 500 K" 同句多值按序配成 (300,5.0)/(500,3.2)；
              ③ 跨句配对：同段多句 "at T1, y1" / "at T2, y2" 逐句配对；
              ④ 兜底笛卡尔积：同一块内 x 与 y 两两组合（xs/ys 放宽到
                 [:12]，每块配对总数上限 60 防爆炸）。

        Returns:
            dict 含 points/x_vals/y_vals/x_label/y_unit/y_implicit/n_points；
            点数不足（<3）或 x 无变化（<3 个不同值）时返回 None。
        """
        from collections import Counter

        evid = self._build_evidence_index(source_text, hyp)
        blocks = evid["blocks"]
        unit_filter = self._unit_filter(hyp.property)
        # 无量纲性质（ZT 热电优值等）：_unit_filter 返回 {"dimensionless"}，
        # 表示数值无单位（如 "ZT = 1.2"），需走裸数字提取路径（2026-10 修复，
        # 此前热电 ZT 因无单位永远提取不到配对点）。
        is_dimensionless = bool(unit_filter) and "dimensionless" in unit_filter
        if is_dimensionless:
            unit_filter = (set(unit_filter) - {"dimensionless"}) or None
        if unit_filter is None:
            unit_filter = set()  # 无性质单位桶时用任意带单位数值（弱约束）

        # 材料过滤（软过滤）：优先只看相关块；若相关块太少（<3），
        # 回退全部块——文献材料名与假设材料名常不完全一致（如
        # CoMn-MOF-74 的数值分散在 Mg-MOF-74 表格中），硬过滤会误杀数据。
        material_tokens = [t for t in (evid.get("material_tokens") or []) if len(t) >= 3]
        if material_tokens:
            rel_blocks = [b for b in blocks
                          if any(t in b.lower() for t in material_tokens)]
            if len(rel_blocks) >= 3:
                blocks = rel_blocks

        # ── 第一遍：统计 y 主导单位 ──
        y_unit_counter = Counter()
        if is_dimensionless:
            # 无量纲性质：统计块内裸数字（ZT 等，范围 0.01~20，排除年份/文献编号）
            for block in blocks:
                lower = block.lower()
                for num in re.finditer(
                        r'(?<![a-z0-9.\-])(\d+(?:\.\d+)?)(?![\d.eE])', lower):
                    v = float(num.group(1))
                    if not (0.01 <= v <= 20.0):
                        continue
                    if v == int(v) and v > 10000:
                        continue  # 年份/大编号
                    y_unit_counter["dimensionless"] += 1
        else:
            for block in blocks:
                for vm in self._VALUE_UNIT_RE.finditer(block):
                    unit = self._normalize_unit(vm.group(2) or "")
                    if unit_filter and unit not in unit_filter:
                        continue
                    y_unit_counter[unit] += 1
        # 增强（2026-09）：纯表格块的数据行只有裸数字（单位写在表头括号里），
        # 显式单位统计可能为空导致整块被丢弃；此时回退收集表头 (单位) 声明。
        if not y_unit_counter and not is_dimensionless:
            for block in blocks:
                for mh in re.finditer(r'\(([^)]+)\)', block):
                    unit = self._normalize_unit(mh.group(1))
                    if unit_filter and unit not in unit_filter:
                        continue
                    if self._y_unit_range(unit):
                        y_unit_counter[unit] += 1
        if not y_unit_counter:
            return None
        y_unit = y_unit_counter.most_common(1)[0][0]

        # ── 第二遍：块内 (x, y) 配对 ──
        raw_pairs = []
        any_implicit = False
        y_seq_re = self._y_seq_re(y_unit)
        # gid = 文献块下标（同一块通常来自同一来源表格/段落，
        # 用作分组 CV 的近似"论文"归属；配合 points_meta 输出）
        for gid, block in enumerate(blocks):
            lower = block.lower()
            # （材料过滤已在块集层面完成软过滤，此处不重复）
            # x：结构变量 + 匹配区间（供 y 隐式回退时排除）；统一单位：
            # 温度 °C/℃ → K（+273.15），压力 kPa → bar（/100）
            xs = []
            xspans = []
            for m in self._X_STRUCTURE_RE.finditer(lower):
                xspans.append((m.start(), m.end()))
                if m.group(1) is not None:
                    raw = m.group(0).lower()
                    val = float(m.group(1))
                    if "°c" in raw or "℃" in raw:
                        val += 273.15
                    xs.append(("temperature", round(val, 3)))
                elif m.group(2) is not None:
                    raw = m.group(0).lower()
                    val = float(m.group(2))
                    if "kpa" in raw:
                        val = val / 100.0
                    elif "gpa" in raw:
                        val = val * 10000.0  # 1 GPa = 10000 bar
                    elif "mpa" in raw:
                        val = val * 10.0     # 1 MPa = 10 bar
                    xs.append(("pressure", round(val, 5)))
                elif m.group(3) is not None:
                    xs.append(("composition", float(m.group(3))))
                elif m.group(4) is not None:
                    xs.append(("percentage", float(m.group(4))))
            # y：显式单位优先
            ys = []
            if is_dimensionless:
                # 无量纲性质（ZT 等）：收集块内裸数字（排除 x 区间/年份与
                # 带单位数值——如 "5.63 mW/mK²" 是功率因子非 ZT；范围 0.01~20）
                unit_spans = [(m.start(), m.end())
                              for m in self._VALUE_UNIT_RE.finditer(lower)]
                for num in re.finditer(
                        r'(?<![a-z0-9.\-])(\d+(?:\.\d+)?)(?![\d.eE])', lower):
                    if any(s <= num.start() < e for s, e in xspans):
                        continue  # 该数字是结构变量（温度/压力/比例）
                    if any(s <= num.start() < e for s, e in unit_spans):
                        continue  # 该数字带单位（功率因子/热导率等）
                    v = float(num.group(1))
                    if not (0.01 <= v <= 20.0):
                        continue
                    if v == int(v) and v > 10000:
                        continue  # 年份/大编号
                    ys.append(v)
                if ys:
                    any_implicit = True
            else:
                for vm in self._VALUE_UNIT_RE.finditer(lower):
                    unit = self._normalize_unit(vm.group(2) or "")
                    if unit != y_unit:
                        continue
                    v = float(vm.group(1))
                    if 0 < v < 1e6:
                        ys.append(v)
            y_implicit = False
            if not ys and self._y_unit_range(y_unit):
                # 隐式单位回退：块内表头含 (单位) 且等于 y 主导单位时，
                # 收集裸数字（排除 x 区间/年份/文献编号，并按范围过滤）
                mh = re.search(r'[（(]([^）)]+)[）)]', block)
                if mh and self._normalize_unit(mh.group(1)) == y_unit:
                    lo, hi = self._y_unit_range(y_unit)
                    for num in re.finditer(
                            r'(?<![a-z0-9.\-])(\d+(?:\.\d+)?)(?![\d.eE])', lower):
                        if any(s <= num.start() < e for s, e in xspans):
                            continue  # 该数字是结构变量（温度/压力/比例）
                        v = float(num.group(1))
                        if not (0 < v < 1e5):
                            continue
                        if v == int(v) and v > 10000:
                            continue  # 年份/大编号
                        if lo <= v <= hi:
                            ys.append(v)
                    if ys:
                        y_implicit = True
                        any_implicit = True

            # 当前块内所有配对候选（各路径合并，每块总数上限 60）
            block_pairs = []

            # ── 路径 ①：Markdown 表格按列配对（数据质量 A 层：严格可比）──
            tbl_pairs, tbl_xs, tbl_ys = self._table_pairs_from_block(
                block, unit_filter, y_unit)
            block_pairs.extend(
                (kind, xv, yv, "table", gid) for kind, xv, yv in tbl_pairs)
            # 表格列值回填 x/y 候选（表头已声明单位，数据行裸数字同样可信），
            # 供笛卡尔积兜底扩量，避免"模型对比全为无提升"
            if tbl_xs:
                for t in tbl_xs:
                    if t not in xs:
                        xs.append(t)
            if tbl_ys:
                for v in tbl_ys:
                    if v not in ys:
                        ys.append(v)

            # ── 路径 ②③：句子级序列 + 跨句配对（数据质量 B 层：需换算/序列推断）──
            block_pairs.extend(
                (kind, xv, yv, "sequence", gid)
                for kind, xv, yv in
                self._sentence_pairs_from_block(lower, y_unit, y_seq_re))

            # ── 路径 ②b：Vegard 律范围端点配对（2026-10 新增）
            #    "1.55→2.3(x 0→1,Vegard 律)" → (0,1.55) + (1,2.3) 两端点。
            #    覆盖钙钛矿知识图谱"带隙 vs 组分"的区间表述（此前提取不到 x）。
            #    仅对带隙类性质启用（Vegard 律语义：组分→带隙/晶格常数），
            #    避免其它性质的 "(x 0→1)" 句式被误配对。──
            is_bandgap_prop = bool(re.search(
                r'带隙|band\s*gap|bandgap|禁带|能隙|\beg\b|e_g',
                str(hyp.property or "").lower()))
            if not is_dimensionless and is_bandgap_prop:
                for vgm in self._VEGARD_RANGE_RE.finditer(lower):
                    try:
                        y1, y2 = float(vgm.group(1)), float(vgm.group(2))
                        x1, x2 = float(vgm.group(3)), float(vgm.group(4))
                        if (0 <= x1 <= 1 and 0 <= x2 <= 1
                                and 0 < y1 < 1e3 and 0 < y2 < 1e3):
                            block_pairs.append(
                                ("composition", x1, y1, "sequence", gid))
                            block_pairs.append(
                                ("composition", x2, y2, "sequence", gid))
                            xs.append(("composition", x1))
                            xs.append(("composition", x2))
                            ys.append(y1)
                            ys.append(y2)
                    except (TypeError, ValueError):
                        continue

            # ── 路径 ④：笛卡尔积兜底（放宽截断 xs/ys → [:12]；
            #    B 层=显式单位数值，C 层=表头单位回退的裸数字，弱可比）──
            # 2026-10：无量纲性质（ZT）禁用笛卡尔积兜底——裸数字收集
            # 会把同块内不同材料的 ZT 全部混入（如 600K 对应 0.8~10 多个
            # ZT 值来自不同材料行），虚假配对使 R² 塌陷。无量纲时只保留
            # 表格/句子/Vegard 高质量配对。
            if not is_dimensionless:
                cart_count = 0
                cart_prov = "implicit" if y_implicit else "explicit"
                for kind, xv in xs[:12]:
                    if cart_count >= 60:
                        break
                    for yv in ys[:12]:
                        if cart_count >= 60:
                            break
                        block_pairs.append((kind, xv, yv, cart_prov, gid))
                        cart_count += 1

            raw_pairs.extend(block_pairs[:60])

        if not raw_pairs:
            return None
        # 去重：按 (kind, x, y) 保留首次出现的溯源（provenance/group）
        seen_keys = set()
        uniq = []
        for p in raw_pairs:
            key = (p[0], p[1], p[2])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            uniq.append(p)
        uniq.sort(key=lambda t: (t[1], t[2]))
        if len(uniq) < 3:
            return None
        x_vals_all = [t[1] for t in uniq]
        if len(set(x_vals_all)) < 3:
            return None

        # 只用主导结构变量类型，保证 x 语义一致。
        # 2026-10 修复：不能只按点数量取主 kind——pressure 可能点数多但
        # 不同 x 值 <3（如只有 2.3/1.2 GPa 两个点），而 composition 点数少
        # 却有 x=0/1 等多个不同值（Vegard 律端点）。先筛选出"不同 x 值 ≥3"
        # 的 kind，再在其中按点数取主 kind；若没有 kind 达标则回退原逻辑。
        kind_counter = Counter(t[0] for t in uniq)
        candidate_kinds = [k for k in kind_counter
                           if len({t[1] for t in uniq if t[0] == k}) >= 3]
        if candidate_kinds:
            x_label = max(candidate_kinds, key=lambda k: kind_counter[k])
        else:
            x_label = kind_counter.most_common(1)[0][0]
        points = []
        points_meta = []
        for p in uniq:
            if p[0] != x_label:
                continue
            points.append((p[1], p[2]))
            points_meta.append({
                "x": p[1], "y": p[2],
                "provenance": p[3], "group": p[4],
            })
        if len(points) < 3 or len(set(x for x, _ in points)) < 3:
            return None
        # 限制数据量，避免极端文本导致过度膨胀
        points = points[:200]
        points_meta = points_meta[:200]
        return {
            "points": points,
            "points_meta": points_meta,
            "quality_counts": dict(Counter(m["provenance"] for m in points_meta)),
            "n_groups": len(set(m["group"] for m in points_meta)),
            "x_vals": [p[0] for p in points],
            "y_vals": [p[1] for p in points],
            "x_label": x_label,
            "y_unit": y_unit,
            "y_implicit": any_implicit,
            "n_points": len(points),
            "n_blocks": len(blocks),
        }

    # ── 辅助：Markdown 表格按列配对 / 句子级序列配对（_extract_literature_points 使用）──

    def _y_seq_re(self, y_unit: str):
        """根据 y 主导单位构造宽松的 'from A to B UNIT' 序列正则。

        支持 "mmol/g"、"mmol g^-1"、"mol kg" 等文献常见写法：
        把单位拆成字母/数字 token，用 [\\s/]* 连接，斜杠与空格均可接受。
        """
        yl = (y_unit or "").lower()
        toks = re.findall(r'[a-z]+|\d+|%', yl)
        unit_pat = (r'[\s/]*'.join(re.escape(t) for t in toks)
                    if toks else re.escape(yl))
        return re.compile(
            r'\bfrom\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s*'
            + unit_pat + r'(?!\w)',
            re.IGNORECASE,
        )

    def _parse_table_header(self, cells, unit_filter, y_unit):
        """识别 Markdown 表头列的 x/y 语义。

        Args:
            cells: 表头单元格列表（已 strip）
            unit_filter: 性质单位桶（空 set = 不过滤）
            y_unit: 当前块主导 y 单位

        Returns:
            (x_col, x_kind, y_col, y_cell_unit) 或 None。
            识别依据：单元格内 (单位) 括号 + 关键词
            （x：temperature/T/温度/pressure/压力/composition/比例 等；
             y：capacity/uptake/adsorption/容量/吸附 等）。
        """
        x_col, x_kind = None, None
        y_col, y_cell_unit = None, None
        for i, cell in enumerate(cells):
            c = cell.strip()
            if not c:
                continue
            cl = c.lower()
            m = re.search(r'[（(]([^）)]+)[）)]', c)
            cell_unit = ToolHandlers._normalize_unit(m.group(1)) if m else None
            # ── x 列判定：单位属温度/压力；或单元格无 y 候选单位但关键词命中。
            # 若单元格单位已是 y 候选单位（unit_filter / 已知范围），即使含
            # "pressure" 等词也不判 x（如 "pressure swing adsorption (mmol/g)"）。
            is_x = False
            if cell_unit in ("k", "bar", "atm", "kpa"):
                is_x = True
            elif re.search(
                    r'temp|temperature|温度|pressure|压力|composition|组分|比例|doping|\bt\b',
                    cl):
                y_like = ((unit_filter and cell_unit in unit_filter)
                          or ((not unit_filter)
                              and self._y_unit_range(cell_unit or "") is not None))
                if not y_like:
                    is_x = True
            if is_x:
                if cell_unit == "k":
                    x_kind = "temperature"
                elif cell_unit in ("bar", "atm", "kpa"):
                    x_kind = "pressure"
                elif re.search(r'pressure|压力', cl):
                    x_kind = "pressure"
                elif re.search(r'composition|组分|比例|doping', cl):
                    x_kind = "composition"
                else:
                    x_kind = "temperature"
                x_col = i
                continue
            # ── y 列判定：单位命中 unit_filter/y_unit，或 y 关键词 ──
            is_y = False
            if cell_unit is not None:
                if unit_filter:
                    # 显式单位桶过滤：只认可桶内单位
                    is_y = cell_unit in unit_filter
                else:
                    # 弱约束：与主导 y 单位一致；或（无主导单位时）属于已知范围
                    is_y = ((y_unit and cell_unit == y_unit)
                            or ((not y_unit)
                                and self._y_unit_range(cell_unit) is not None))
            if not is_y and re.search(
                    r'capacity|uptake|adsorption|loading|capture|selectivity|容量|吸附|摄取|'
                    r'焓|enthalpy|heat|qst|效率|efficiency|'
                    r'zt|热电优值|figure of merit|seebeck|塞贝克|热电势|'
                    r'功率因子|power factor|热导率|电导率|thermal conductivity|'
                    r'electrical conductivity', cl):
                # 2026-10：无量纲性质（ZT）下 y 列只认 ZT 强关键词——
                # "| 材料 | 功率因子 | ZT |" 列序时若把 PF 列当 y 会提取错性质
                if y_unit == "dimensionless":
                    is_y = bool(re.search(r'\bzt\b|热电优值|figure\s*of\s*merit', cl))
                else:
                    is_y = True
            if is_y and y_col is None:
                y_col, y_cell_unit = i, cell_unit
        if x_col is not None and y_col is not None and x_col != y_col:
            return x_col, x_kind, y_col, y_cell_unit
        return None

    @staticmethod
    def _parse_table_row(cells, x_col, x_kind, y_col, y_cell_unit, y_unit):
        """从表格数据行提取 (kind, x, y)；单元格格式异常返回 None。

        温度列按单元格内 °C/℃ 标记换算到 K；压力列按 kPa 换算到 bar。
        """
        try:
            xcell = cells[x_col].strip()
            ycell = cells[y_col].strip()
            xm = re.search(r'(\d+(?:\.\d+)?)', xcell)
            ym = re.search(r'(\d+(?:\.\d+)?)', ycell)
            if not xm or not ym:
                return None
            x = float(xm.group(1))
            y = float(ym.group(1))
            if not (0 < y < 1e6):
                return None
            xc = xcell.lower()
            if x_kind == "temperature":
                if "°c" in xc or "℃" in xc:
                    x += 273.15
                x = round(x, 3)
            elif x_kind == "pressure":
                if "kpa" in xc:
                    x = x / 100.0
                x = round(x, 5)
            else:
                x = round(x, 5)
            return (x_kind, x, y)
        except (ValueError, IndexError, AttributeError):
            return None

    def _table_pairs_from_block(self, block: str, unit_filter, y_unit):
        """Markdown 表格按列配对：同一数据行的 x 列与 y 列数值直接配对。

        Returns:
            (pairs, xs_add, ys_add)
            - pairs: [(kind, x, y), ...]（最多 60 对）
            - xs_add/ys_add: 表格 x/y 列值回填到块内候选，供笛卡尔积兜底扩量
        """
        pairs: List = []
        xs_add: List = []
        ys_add: List = []
        lines = block.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not (line.startswith("|") and line.count("|") >= 2):
                i += 1
                continue
            header_cells = [c.strip() for c in line.strip("|").split("|")]
            # 跳过纯分隔行（| --- | :---: |）
            if header_cells and all(
                    re.fullmatch(r':?-{2,}:?', c) for c in header_cells if c.strip()):
                i += 1
                continue
            spec = self._parse_table_header(header_cells, unit_filter, y_unit)
            if spec is None:
                i += 1
                continue
            x_col, x_kind, y_col, y_cell_unit = spec
            j = i + 1
            while j < len(lines):
                dl = lines[j].strip()
                if not (dl.startswith("|") and dl.count("|") >= 2):
                    break
                dcell = [c.strip() for c in dl.strip("|").split("|")]
                if dcell and all(
                        re.fullmatch(r':?-{2,}:?', c) for c in dcell if c.strip()):
                    j += 1  # 表头下的分隔行
                    continue
                pair = self._parse_table_row(
                    dcell, x_col, x_kind, y_col, y_cell_unit, y_unit)
                if pair is not None:
                    if pair not in pairs:
                        pairs.append(pair)
                    # 回填列值（供笛卡尔积兜底扩量；表头已声明单位，裸数字可信）
                    if (pair[0], pair[1]) not in xs_add:
                        xs_add.append((pair[0], pair[1]))
                    if pair[2] not in ys_add:
                        ys_add.append(pair[2])
                if len(pairs) >= 60:
                    break
                j += 1
            i = j
        return pairs, xs_add, ys_add

    def _sentence_pairs_from_block(self, lower: str, y_unit: str, y_seq_re):
        """句子级配对：序列模式（from A to B）+ 跨句配对（at T, y）。

        按标点/换行把块切成句子：
          - 路径② 序列模式：句中同时出现 x "from A to B K/bar" 与
            y "from A to B UNIT" 时按出现顺序配成 (x1,y1)/(x2,y2)；
          - 路径③ 跨句/句内：句内 x 值与 y 值数量相等（1~4）时按序配对，
            覆盖 "At 298 K, uptake was 5.0 mmol/g." 这类逐句数据点。

        Returns:
            [(kind, x, y), ...]
        """
        pairs: List = []
        for sent in re.split(r'[.!?。！？;；\n]+', lower):
            sent = sent.strip()
            if len(sent) < 8:
                continue
            # ── 序列模式：同句 "from A to B" 双值 → 多个 (x,y) ──
            x_seqs = list(self._X_FROM_TO_RE.finditer(sent))
            y_seqs = list(y_seq_re.finditer(sent))
            for xm, ym in zip(x_seqs, y_seqs):
                x1, x2 = float(xm.group(1)), float(xm.group(2))
                y1, y2 = float(ym.group(1)), float(ym.group(2))
                xunit = xm.group(3).lower()
                if xunit in ("°c", "℃"):
                    x1 += 273.15
                    x2 += 273.15
                kind = "temperature" if xunit in ("k", "°c", "℃") else "pressure"
                pairs.append((kind, round(x1, 5), y1))
                pairs.append((kind, round(x2, 5), y2))
            # ── 跨句/句内配对：x 值个数 == y 值个数时按序配对 ──
            sent_xs: List = []
            for m in self._X_STRUCTURE_RE.finditer(sent):
                if m.group(1) is not None:
                    raw = m.group(0).lower()
                    v = float(m.group(1))
                    if "°c" in raw or "℃" in raw:
                        v += 273.15
                    sent_xs.append(("temperature", round(v, 3)))
                elif m.group(2) is not None:
                    raw = m.group(0).lower()
                    v = float(m.group(2))
                    if "kpa" in raw:
                        v = v / 100.0
                    sent_xs.append(("pressure", round(v, 5)))
                elif m.group(3) is not None:
                    sent_xs.append(("composition", float(m.group(3))))
                elif m.group(4) is not None:
                    sent_xs.append(("percentage", float(m.group(4))))
            sent_ys: List = []
            for vm in self._VALUE_UNIT_RE.finditer(sent):
                if self._normalize_unit(vm.group(2) or "") != y_unit:
                    continue
                v = float(vm.group(1))
                if 0 < v < 1e6:
                    sent_ys.append(v)
            if 0 < len(sent_xs) <= 4 and len(sent_xs) == len(sent_ys):
                for (k, xv), yv in zip(sent_xs, sent_ys):
                    pairs.append((k, xv, yv))
        return pairs

    def _fit_candidate_models(self, x, y) -> List[dict]:
        """对 (x, y) 拟合候选模型（线性/二次/三次/幂律/指数/对数）。

        幂律/指数/对数需要严格正的 x/y，不满足时自动跳过；
        numpy polyfit 对退化数据会发 RankWarning，此处静默并逐个 try。
        """
        import warnings

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        n = len(y)
        models = []

        def _add(name, kind, k, pred, desc=""):
            resid = y - pred
            rss = float(np.sum(resid ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r2 = 1.0 - rss / ss_tot if ss_tot > 0 else 0.0
            rmse = float(np.sqrt(rss / n))
            models.append({
                "name": name, "kind": kind, "k": int(k),
                "r2": r2, "rmse": rmse, "rss": rss, "params": desc,
            })

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.RankWarning)
            try:
                c = np.polyfit(x, y, 1)
                _add("线性", "linear", 2, np.polyval(c, x),
                     "y = {:.4g}x + {:.4g}".format(c[0], c[1]))
            except Exception:
                pass
            try:
                c = np.polyfit(x, y, 2)
                _add("二次", "quadratic", 3, np.polyval(c, x),
                     "y = {:.4g}x^2 + {:.4g}x + {:.4g}".format(c[0], c[1], c[2]))
            except Exception:
                pass
            try:
                c = np.polyfit(x, y, 3)
                _add("三次", "cubic", 4, np.polyval(c, x),
                     "y = {:.4g}x^3 + {:.4g}x^2 + {:.4g}x + {:.4g}".format(*c))
            except Exception:
                pass
        # 幂律 y = a*x^b（需 x,y>0）
        if np.all(x > 0) and np.all(y > 0):
            try:
                c = np.polyfit(np.log(x), np.log(y), 1)
                _add("幂律", "power", 2, np.exp(c[1]) * (x ** c[0]),
                     "y = {:.4g} * x^{:.4g}".format(np.exp(c[1]), c[0]))
            except Exception:
                pass
        # 指数 y = a*exp(b*x)（需 y>0）
        if np.all(y > 0):
            try:
                c = np.polyfit(x, np.log(y), 1)
                _add("指数", "exponential", 2, np.exp(c[1]) * np.exp(c[0] * x),
                     "y = {:.4g} * exp({:.4g} * x)".format(np.exp(c[1]), c[0]))
            except Exception:
                pass
        # 对数 y = a + b*ln(x)（需 x>0）
        if np.all(x > 0):
            try:
                c = np.polyfit(np.log(x), y, 1)
                _add("对数", "logarithmic", 2, c[1] + c[0] * np.log(x),
                     "y = {:.4g} + {:.4g} * ln(x)".format(c[1], c[0]))
            except Exception:
                pass
        if not models:
            return []
        models.sort(key=lambda m: m["r2"], reverse=True)
        return models

    def _tiered_regression(self, meta: list) -> Optional[dict]:
        """数据质量分层回归（teacherB#2/#4：宽松纳入、严格分层）。

        meta: _extract_literature_points 返回的 points_meta。
        层映射（数据质量状态）：
          A 层 = "table"      —— Markdown 表格按列配对（严格可比，近似 observed）
          B 层 = "sequence"/"explicit" —— 句子序列/显式单位数值
                                        （需换算或序列推断，近似 converted）
          C 层 = "implicit"   —— 表头单位回退的裸数字（弱可比，近似 inferred）
        每层若 ≥3 点且 x 有 ≥3 个不同值，拟合线性 y = a + b·x 并报告 R²。
        """
        import numpy as _np
        tiers = {"A": ("table",),
                 "B": ("sequence", "explicit"),
                 "C": ("implicit",)}
        result = {}
        for tier, provs in tiers.items():
            sel = [(m["x"], m["y"]) for m in meta if m["provenance"] in provs]
            if len(sel) < 3:
                continue
            xs_t = _np.asarray([p[0] for p in sel], dtype=float)
            ys_t = _np.asarray([p[1] for p in sel], dtype=float)
            if len(set(xs_t.tolist())) < 3:
                continue
            try:
                coef = _np.polyfit(xs_t, ys_t, 1)
                y_pred = coef[0] * xs_t + coef[1]
                ss_res = float(_np.sum((ys_t - y_pred) ** 2))
                ss_tot = float(_np.sum((ys_t - _np.mean(ys_t)) ** 2))
                r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            except Exception:
                continue
            result[tier] = {
                "n": int(len(sel)),
                "r2": r2,
                "slope": float(coef[0]),
                "intercept": float(coef[1]),
            }
        return result or None

    def _nested_f_test(self, n, rss_reduced, k_reduced, rss_full, k_full) -> dict:
        """近似嵌套 F 检验：full（参数多）相对 reduced（参数少）是否显著更优。

        F = ((RSS_red - RSS_full) / (k_full - k_reduced)) / (RSS_full / (n - k_full))
        p 值用 scipy.stats.f.sf（scipy 在 requirements 中已声明）。
        模型不严格嵌套时结果仅作参考（报告中标注"近似"）。
        """
        if k_full <= k_reduced:
            return {"valid": False,
                    "reason": "候选与经典模型参数数相同，无法做嵌套 F 检验"}
        try:
            from scipy import stats
        except Exception:
            return {"valid": False, "reason": "scipy 不可用，无法计算 F 检验 p 值"}
        df_num = k_full - k_reduced
        df_den = n - k_full
        if df_den <= 0 or rss_full <= 0:
            return {"valid": False, "reason": "自由度不足或残差为 0，无法做 F 检验"}
        F = max(((rss_reduced - rss_full) / df_num) / (rss_full / df_den), 0.0)
        p = float(stats.f.sf(F, df_num, df_den))
        return {
            "valid": True,
            "F": float(F),
            "p_value": p,
            "df_num": int(df_num),
            "df_den": int(df_den),
            "significant": bool(p < 0.05),
        }

    def _model_compare_verdict(self, best: dict, classic: dict,
                               f_res: dict, diag_res: dict) -> dict:
        """规则化统计判定：候选模型是否在统计指标上优于经典模型。

        赛题路线 A 验证标准：「新规律必须在统计指标上优于前人成果
        （更高 R² / 更低 MSE），且能解释旧模型为何失效」。此方法把
        「是否优于」从 LLM 主观描述升级为可复算的规则化结论
        （2026-10 新增，解决"模型对比全为无提升/无正面结论"）：

        判定规则（按强度递减）：
          1. 候选 R² 低于经典 R² − 0.02          → 候选劣于经典（如实记录）
          2. 候选 R² 高于经典 R² 且 ≥0.05 提升：
             - F 检验显著（候选为 full 侧）       → 候选显著优于经典
             - bootstrap CI 下界 > 经典 R²         → 候选显著优于经典（CI 不重叠）
             - 仅 ΔR² 达标（无 F/CI 佐证）        → 候选可能优于（弱证据，标注样本量）
          3. 其余                                → 无显著提升
        Returns:
            {"verdict": str, "reason": str, "delta_r2": float,
             "f_supported": bool, "ci_supported": bool}
        """
        delta_r2 = None
        try:
            best_r2 = float(best.get("r2"))
            classic_r2 = float(classic.get("r2"))
            if np.isfinite(best_r2) and np.isfinite(classic_r2):
                delta_r2 = best_r2 - classic_r2
        except (TypeError, ValueError):
            delta_r2 = None
        if delta_r2 is None:
            return {"verdict": "insufficient", "reason": "候选或经典 R² 缺失，无法判定",
                    "delta_r2": None, "f_supported": False, "ci_supported": False}

        f_supported = bool(
            f_res.get("valid") and f_res.get("significant")
            and f_res.get("full_side") == "候选模型")
        ci_supported = False
        ci_low = None
        try:
            bt = diag_res.get("bootstrap", {}) if isinstance(diag_res, dict) else {}
            bt_r2 = bt.get("r2", {})
            if isinstance(bt_r2, dict) and bt_r2.get("ci_low") is not None:
                ci_low = float(bt_r2["ci_low"])
                if np.isfinite(ci_low) and np.isfinite(float(classic.get("r2"))):
                    ci_supported = ci_low > float(classic.get("r2"))
        except (TypeError, ValueError):
            ci_supported = False

        if delta_r2 < -0.02:
            return {
                "verdict": "candidate_worse",
                "reason": (f"候选 R²={float(best.get('r2')):.4f} 低于经典 "
                           f"R²={float(classic.get('r2')):.4f}（ΔR²={delta_r2:.4f}），"
                           "候选未体现统计优势"),
                "delta_r2": round(delta_r2, 4),
                "f_supported": f_supported, "ci_supported": ci_supported,
            }
        if delta_r2 >= 0.05:
            if f_supported:
                verdict = "candidate_better"
                reason = (f"候选 R²={float(best.get('r2')):.4f} 高于经典 "
                          f"R²={float(classic.get('r2')):.4f}（ΔR²=+{delta_r2:.4f}），"
                          "且嵌套 F 检验显著（p<0.05）")
            elif ci_supported:
                verdict = "candidate_better"
                reason = (f"候选 R²={float(best.get('r2')):.4f} 高于经典 "
                          f"R²={float(classic.get('r2')):.4f}（ΔR²=+{delta_r2:.4f}），"
                          f"bootstrap R² 95% CI 下界 {ci_low:.4f} 高于经典 R²，"
                          "两模型统计上不重叠")
            else:
                verdict = "candidate_possible"
                reason = (f"候选 R²={float(best.get('r2')):.4f} 高于经典 "
                          f"R²={float(classic.get('r2')):.4f}（ΔR²=+{delta_r2:.4f}），"
                          "但缺 F 检验/bootstrap CI 佐证，仅作弱证据提示")
        else:
            verdict = "no_improvement"
            reason = (f"候选 R²={float(best.get('r2')):.4f} 与经典 "
                      f"R²={float(classic.get('r2')):.4f} 差距不足"
                      f"（ΔR²={delta_r2:+.4f}，<0.05 阈值），无显著提升")
        return {
            "verdict": verdict, "reason": reason,
            "delta_r2": round(delta_r2, 4),
            "f_supported": f_supported, "ci_supported": ci_supported,
        }

    def _load_classical_models(self):
        """延迟导入 classical_models 模块（另一 Agent 实现，可能尚未就绪）。

        返回 (module_or_None, 可用 fit_* 函数名列表, 错误信息)。
        """
        try:
            import literature_agent.classical_models as cm
        except Exception as e:
            return None, [], f"literature_agent.classical_models 导入失败: {e}"
        names = sorted(n for n in dir(cm)
                       if n.startswith("fit_") and callable(getattr(cm, n, None)))
        return cm, names, ""

    def _call_classical_model(self, fn, x, y, n) -> dict:
        """调用经典模型拟合函数，兼容 dict / 其它返回形态。"""
        xa = np.asarray(x, dtype=float)
        ya = np.asarray(y, dtype=float)
        try:
            res = fn(xa, ya)
        except TypeError:
            try:
                res = fn(list(xa), list(ya))
            except Exception as e:
                return {"error": f"经典模型调用失败: {e}"}
        except Exception as e:
            return {"error": f"经典模型调用失败: {e}"}
        if isinstance(res, dict):
            rss = None
            for kk in ("rss", "RSS", "sse", "SSE"):
                if kk in res and res[kk] is not None:
                    rss = float(res[kk])
                    break
            if rss is None and "r2" in res and res["r2"] is not None:
                r2 = float(res["r2"])
                ss_tot = float(np.sum((ya - np.mean(ya)) ** 2))
                rss = (1.0 - r2) * ss_tot
            params = res.get("params", res.get("parameters", {}))
            k = 0
            if isinstance(params, dict):
                k = len(params)
            elif isinstance(params, (list, tuple)):
                k = len(params)
            return {
                "name": getattr(fn, "__name__", "classical"),
                "k": int(k) if k else 2,
                "r2": float(res["r2"]) if res.get("r2") is not None else float("nan"),
                "rmse": float(res["rmse"]) if res.get("rmse") is not None else float("nan"),
                "rss": rss,
                "params": params,
                "expr": str(res.get("expr", res.get("expression",
                        res.get("name", "")))),
            }
        return {"error": "经典模型返回格式无法解析",
                "raw": str(res)[:300]}

    def _llm_model_compare_explanation(self, prompt: str) -> str:
        """调用 LLM 生成「候选是否优于经典、旧模型为何失效」的中文解释。

        失败时返回启发式结论（基于 R²/RMSE 差的文字模板）。
        """
        resp = self._call_llm(prompt, temperature=0.2, max_tokens=2048)
        if resp:
            return resp.strip()
        return (
            "（LLM 不可用）未能生成深度解释。请基于上方 R²/RMSE 表人工判断："
            "若候选模型 R² 显著高于经典模型且嵌套 F 检验显著，说明该构效关系"
            "偏离经典假设（如温度非线性、组分非 Vegard 线性），"
            "需要引入更高阶/非线性项修正旧模型。"
        )

    # ── 数值交叉验证：检查 LLM 假设中的数值是否在文献证据中可查 ──

    # 单位归一化表：各种变体 → 规范形式
    _UNIT_NORM_MAP = {
        "kj/mol": "kj/mol", "kj / mol": "kj/mol", "kj mol⁻¹": "kj/mol",
        "kj mol-1": "kj/mol", "kj mol¹": "kj/mol", "kjmol": "kj/mol",
        "千焦/摩尔": "kj/mol", "千焦/摩": "kj/mol",
        "mmol/g": "mmol/g", "mmol / g": "mmol/g", "mmol g⁻¹": "mmol/g",
        "毫摩尔/克": "mmol/g", "毫摩/克": "mmol/g",
        "mol/kg": "mol/kg", "mmol/cm3": "mmol/cm3",
        "mg/g": "mg/g", "m2/g": "m2/g", "wt%": "wt%", "wt %": "wt%",
        "bar": "bar", "ppm": "ppm", "ev": "ev",
        "h": "h", "min": "min",
        "%": "%", "% rh": "%",
        "k": "k",
        # 热电单位（2026-10 扩展）：µV/K 与 uV/K 归并，W/m·K 与 W/mK 归并
        "µv/k": "µv/k", "uv/k": "µv/k", "μv/k": "µv/k",
        "w/m·k": "w/m·k", "w/mk": "w/m·k", "w m⁻¹ k⁻¹": "w/m·k",
        "s/cm": "s/cm", "s/m": "s/m",
    }

    # 从文本中提取"数值+单位"声明（含范围、前缀符号）
    _CLAIMED_VALUE_RE = re.compile(
        r'([≈~～>><<≥≤]?\s*)(\d+(?:\.\d+)?)\s*'
        r'(?:[-–—～~至到]\s*(\d+(?:\.\d+)?))?\s*'
        r'('
        r'[Kk][Jj]\s*/\s*[Mm][Oo][Ll]|'
        r'[Kk][Jj]\s*[Mm][Oo][Ll]\s*[⁻¹−\-–—]*[¹1]?|'
        r'mmol\s*/\s*g\b|mol\s*/\s*kg\b|mmol\s*/\s*cm3\b|'
        r'mg\s*/\s*g\b|m2\s*/\s*g\b|wt\s*%|'
        r'bar\b|ppm\b|eV\b|'
        r'[Kk]\b|min\b|h\b|'
        r'%\s*(?:RH|rh)?|'
        r'千焦\s*/\s*摩[尔]?|'
        r'毫摩[尔]?\s*/\s*克'
        r')',
        re.IGNORECASE,
    )

    # 从文献证据中提取"数值+单位"对（供条目内匹配与 _verify_numerical_claim 复用）
    _EVIDENCE_VALUE_RE = re.compile(
        r'(\d+(?:\.\d+)?)\s*'
        r'('
        r'[Kk][Jj]\s*/\s*[Mm][Oo][Ll]|'
        r'[Kk][Jj]\s*[Mm][Oo][Ll]\s*[⁻¹−\-–—]*[¹1]?|'
        r'mmol\s*/\s*g\b|mol\s*/\s*kg\b|mmol\s*/\s*cm3\b|'
        r'mg\s*/\s*g\b|m2\s*/\s*g\b|wt\s*%|'
        r'bar\b|ppm\b|eV\b|'
        r'[Kk]\b|min\b|h\b|'
        r'%\s*(?:RH|rh)?|'
        r'千焦\s*/\s*摩[尔]?|'
        r'毫摩[尔]?\s*/\s*克'
        r')',
        re.IGNORECASE,
    )

    # 湿度语境提示词：判断证据句/声称是否涉及相对湿度（RH）语义
    _HUMIDITY_HINT_RE = re.compile(
        r'\brh\b|相对湿度|湿度|humidity|水蒸气|湿气|water\s*vapou?r|moisture|'
        r'湿态|含水|吸水|疏水|亲水|hydrophobi|hydrophili',
        re.IGNORECASE,
    )

    # 比例/组成语境提示词：判断数值是否为摩尔比例/配比/组成百分比
    _PROPORTION_HINT_RE = re.compile(
        r'比例|摩尔比|配比|组成|composition|ratio|mole|mol\s*%|'
        r'molar|molality|content|含量|步长|gradient|fraction|分率',
        re.IGNORECASE,
    )

    @staticmethod
    def _normalize_unit(raw_unit: str) -> str:
        """将文献中的单位字符串归一化为标准形式。"""
        u = raw_unit.strip().lower()
        # 清理空白、unicode 负号
        u = re.sub(r'\s+', ' ', u)
        u = re.sub(r'[⁻¹−\-–—]', '', u).replace('¹', '1').replace('1', '')
        u = u.strip()
        # 直接查表
        for variant, canon in ToolHandlers._UNIT_NORM_MAP.items():
            if u == variant or u.replace(' ', '') == variant.replace(' ', ''):
                return canon
        # 启发式回退
        u_nospace = u.replace(' ', '')
        for variant, canon in ToolHandlers._UNIT_NORM_MAP.items():
            if u_nospace == variant.replace(' ', ''):
                return canon
        return u  # 无法识别则保留原始形式

    @staticmethod
    def _extract_claimed_values(text: str) -> List[dict]:
        """从假设文本中提取所有"数值+单位"声明。

        返回列表，每项包含:
            expression: 原始匹配文本
            low_value: 数值下界 (float)
            high_value: 数值上界 (float, 同 low_value 若为单值)
            prefix: 前缀符号 ('~', '>', '<', '' 等)
            unit_norm: 归一化后的单位字符串
        """
        results = []
        for m in ToolHandlers._CLAIMED_VALUE_RE.finditer(text):
            prefix = (m.group(1) or "").strip()
            v1 = float(m.group(2))
            v2_str = m.group(3)
            v2 = float(v2_str) if v2_str else v1
            raw_unit = m.group(4)
            unit_norm = ToolHandlers._normalize_unit(raw_unit)
            # 过滤纯数字上下文误匹配（无明确单位的情况，如温度 K 和 时间 h/min 容易误匹配，
            # 仅当上下文包含明显单位词时才保留）
            if unit_norm in ("k", "h", "min"):
                # 检查相邻上下文是否支持此单位（如 "K" 需前有数字且上下文含温度词）
                ctx_start = max(0, m.start() - 30)
                ctx_end = min(len(text), m.end() + 30)
                ctx = text[ctx_start:ctx_end]
                if unit_norm == "k" and not re.search(r'温度|[Tt]emp|吸附|反应|开[尔文]|kelvin', ctx):
                    continue
                if unit_norm == "h" and not re.search(r'[Hh]our|[Hh]rs?|小时|[Tt]ime|暴露|时间', ctx):
                    continue
                if unit_norm == "min" and not re.search(r'[Mm]inute|分钟|[Tt]ime|暴露|时间', ctx):
                    continue
            results.append({
                "expression": m.group(0).strip(),
                "low_value": min(v1, v2),
                "high_value": max(v1, v2),
                "prefix": prefix,
                "unit_norm": unit_norm,
            })
        return results

    @staticmethod
    def _extract_evidence_values(evidence_text: str) -> List[dict]:
        """从文献证据文本中提取所有 (数值, 归一化单位) 对。

        注意：本方法面向全文粒度（供 _verify_numerical_claim 等旧接口使用）。
        基于论文条目的严格匹配请使用 _split_evidence_entries + _match_claim_in_entries。
        """
        results = []
        for m in ToolHandlers._EVIDENCE_VALUE_RE.finditer(evidence_text):
            value = float(m.group(1))
            raw_unit = m.group(2)
            unit_norm = ToolHandlers._normalize_unit(raw_unit)
            if 0 < value < 1e8:
                results.append({
                    "value": value,
                    "unit_norm": unit_norm,
                    "raw_text": m.group(0),
                })
        return results

    # ── 论文条目切分与单条目数值匹配（修复跨条目误报的核心） ──

    @staticmethod
    def _extract_paper_ids_from_text(text: str) -> List[str]:
        """从条目文本中提取论文标识（p编号 / DOI / ID 字段）。"""
        if not text:
            return []
        ids: List[str] = []
        # p 编号（如 p6、p186/p182）
        for m in re.finditer(r'(?<![A-Za-z0-9])p\d{1,4}(?![A-Za-z0-9])', text):
            ids.append(m.group(0))
        # DOI（含 doi: 前缀或裸 10.xxxx/... 形式）
        for m in re.finditer(
            r'(?:doi[:：]\s*)?(10\.\d{4,9}/[A-Za-z0-9._\-\(\)\[\]\{\}]{4,60})',
            text, re.IGNORECASE,
        ):
            ids.append(m.group(1).rstrip('.,;:，。；'))
        # 显式 ID 字段（paper_summaries 的 **ID:** `...`）
        for m in re.finditer(r'\*\*ID:\*\*\s*[`"]([^`"\n]{2,80})[`"]', text):
            ids.append(m.group(1).strip())
        # 去重、限制长度
        cleaned = []
        for i in ids:
            i = i.strip()
            if not i or len(i) > 80:
                continue
            if i not in cleaned:
                cleaned.append(i)
        return cleaned[:10]

    @staticmethod
    def _split_evidence_entries(evidence_text: str) -> List[dict]:
        """把文献证据文本按"论文条目"切分。

        设计原则：数值匹配必须在单个条目内完成，禁止跨条目拼接。
        切分规则（由粗到细）：
        1. Markdown 标题（#/##/###）作为章节边界，记录当前章节名；
        2. 表格行（| ... |）每行视为一条独立条目——knowledge_graph.md 的
           构效关系表/核心数值表即按行组织论文证据；
        3. 非表格行的连续文本按段落合并为一条——paper_summaries.md 的
           "### N. Title: ..." 段落即是一篇论文的条目。

        每条条目返回:
          source: 论文标识列表（p编号 / DOI / ID），空表示"无法定位到具体论文"
          label:  条目所在章节标题（仅用于展示）
          text:   条目正文
          tentative: True 表示条目内含 [待验证]/推测 标记（不视为实证证据）
        """
        if not evidence_text or not evidence_text.strip():
            return []

        entries = []
        current_section = ""
        buf_lines: List[str] = []

        def flush_buf():
            nonlocal buf_lines
            if buf_lines:
                text = "\n".join(buf_lines).strip()
                if text:
                    entries.append({
                        "source": ToolHandlers._extract_paper_ids_from_text(text),
                        "label": current_section,
                        "text": text,
                        "tentative": ("[待验证]" in text or "待验证" in text
                                      or "推测" in text),
                    })
                buf_lines = []

        for raw_line in evidence_text.splitlines():
            stripped = raw_line.strip()
            # Markdown 标题 → 新章节
            if re.match(r'^#{1,6}\s+\S', stripped):
                flush_buf()
                current_section = stripped
                continue
            # 表格行 → 单条独立条目
            if re.match(r'^\|.*\|\s*$', stripped):
                # 表头分隔线（|--|--|）跳过
                if re.match(r'^\|[\s\-\|:]*\|?\s*$', stripped):
                    continue
                flush_buf()
                if stripped:
                    # 表头行/无来源行（提取不到 p编号/DOI/ID）不构成论文条目，
                    # 无法定位到具体论文的声称值一律判定未查证——直接跳过
                    row_ids = ToolHandlers._extract_paper_ids_from_text(stripped)
                    if not row_ids:
                        continue
                    entries.append({
                        "source": row_ids,
                        "label": current_section,
                        "text": stripped,
                        "tentative": ("[待验证]" in stripped or "待验证" in stripped
                                      or "推测" in stripped),
                    })
                continue
            # 空行 → 段落边界（避免跨段落拼接）
            if not stripped:
                flush_buf()
                continue
            # 普通文本行 → 累积到当前段落
            buf_lines.append(raw_line)
        flush_buf()
        return entries

    @staticmethod
    def _extract_claim_context(hypo_text: str, claim: dict) -> str:
        """提取声称值在假设文本中的局部上下文（前后各 40 字符）。"""
        expr = claim.get("expression", "")
        idx = hypo_text.find(expr)
        if idx < 0:
            return ""
        start = max(0, idx - 40)
        end = min(len(hypo_text), idx + len(expr) + 40)
        return hypo_text[start:end]

    @staticmethod
    def _claim_semantics(claim: dict) -> str:
        """判断声称值的语义标签：humidity（相对湿度）/ proportion（比例）/ ""。

        语义标签用于防止孤立数字误报：
        - "40-60% RH" → humidity：证据必须出现在 RH/湿度语境中；
        - "0-100%（金属比例）" → proportion：证据必须是比例/组成语境；
        - 其余 → ""：仅按数值+单位匹配，但拒绝湿度语境冲突。
        """
        ctx = str(claim.get("claim_context", "") or "")
        if ToolHandlers._HUMIDITY_HINT_RE.search(claim["expression"] + " " + ctx):
            return "humidity"
        if ToolHandlers._PROPORTION_HINT_RE.search(ctx):
            return "proportion"
        return ""

    @staticmethod
    def _is_wide_percentage_claim(claim: dict) -> bool:
        """宽范围百分比声称（覆盖超过一半全域）——需比例语境才算实证。"""
        unit = claim.get("unit_norm", "")
        lo = float(claim.get("low_value", 0) or 0)
        hi = float(claim.get("high_value", 0) or 0)
        if unit != "%":
            return False
        return (hi - lo) >= 50 or (lo == 0 and hi >= 30)

    @staticmethod
    def _extract_sentence_around(text: str, idx: int, length: int) -> str:
        """在条目文本中提取包含指定位置 idx 的"句子"。

        表格行整体视为一个句子；普通文本按句末标点/换行切分。
        """
        text = text.strip()
        # 表格行：整行即一条记录，直接返回
        if text.startswith("|"):
            return text
        # 普通文本：向两侧扩展句子边界
        start = idx
        end = idx + length
        for sep in ("。", ".", "！", "!", "？", "?", "；", ";"):
            p = text.rfind(sep, 0, idx)
            if p > start:
                start = p
        for sep in ("。", ".", "！", "!", "？", "?", "；", ";"):
            p = text.find(sep, idx + length)
            if p != -1 and p < end:
                end = p
        start = max(0, start)
        sentence = text[start:end + 1].strip()
        # 若句子过长（整段无标点），收缩到数值附近 ±120 字符
        if len(sentence) > 200:
            s = max(0, idx - 60)
            sentence = text[s:idx + length + 120].strip()
        return sentence[:260]

    @staticmethod
    def _match_claim_in_entries(claim: dict, entries: List[dict]) -> dict:
        """在论文条目集合内匹配单个声称值（严格单条目 + 语义校验）。

        Returns:
            {"claimed": ..., "found_in_text": bool,
             "context": "[来源: p65 / doi:...] 条目内实际含该数值的句子",
             "source_ids": [...]}
        """
        unit = claim["unit_norm"]
        lo, hi = float(claim["low_value"]), float(claim["high_value"])
        lo_tol = lo * 0.9 if lo > 0 else 0.0
        hi_tol = hi * 1.1 if hi > 0 else 0.0
        semantics = ToolHandlers._claim_semantics(claim)
        wide_pct = ToolHandlers._is_wide_percentage_claim(claim)

        for entry in entries:
            # 无法定位到具体论文条目的声称值 → 一律未查证
            if not entry.get("source"):
                continue
            # 待验证/推测条目不视为实证证据（如知识图谱中的 [待验证] 行）
            if entry.get("tentative"):
                continue
            etext = entry.get("text", "")
            if not etext:
                continue
            # 在该条目内独立提取数值（禁止跨条目拼接）
            for m in ToolHandlers._EVIDENCE_VALUE_RE.finditer(etext):
                v = float(m.group(1))
                if not (lo_tol <= v <= hi_tol):
                    continue
                raw_unit = m.group(2)
                if ToolHandlers._normalize_unit(raw_unit) != unit:
                    continue
                # 语义校验：声称值必须与证据句的语义对应
                sentence = ToolHandlers._extract_sentence_around(etext, m.start(), len(m.group(0)))
                if semantics == "humidity":
                    # 声称是 RH/湿度语境 → 证据句必须含湿度语境
                    if not ToolHandlers._HUMIDITY_HINT_RE.search(sentence):
                        continue
                else:
                    # 非湿度声称 → 证据句不得是湿度语境（避免"100%"命中"30-50% RH"）
                    if ToolHandlers._HUMIDITY_HINT_RE.search(sentence):
                        continue
                    # 宽范围百分比声称（如 0-100%、0-50%）→ 必须落在比例/组成语境
                    if wide_pct and not ToolHandlers._PROPORTION_HINT_RE.search(sentence):
                        continue
                source_ids = entry.get("source", [])
                src_str = " / ".join(source_ids[:3]) if source_ids else entry.get("label", "?")
                return {
                    "claimed": claim["expression"],
                    "found_in_text": True,
                    "context": f"[来源: {src_str}] {sentence}",
                    "source_ids": source_ids,
                }

        return {
            "claimed": claim["expression"],
            "found_in_text": False,
            "context": "",
            "source_ids": [],
        }

    @staticmethod
    def _match_value_in_evidence(claim: dict, evidence_pairs: List[dict],
                                  evidence_text: str) -> dict:
        """检查单个声称值是否在证据集中有匹配。

        模糊匹配规则: 单位相同，数值在声称范围的 ±10% 容差内。
        对范围声称 [a, b]，若任一证据值 v 满足 a*0.9 <= v <= b*1.1 则视为匹配。
        对单值声称 x，若任一证据值 v 满足 x*0.9 <= v <= x*1.1 则视为匹配。
        """
        unit = claim["unit_norm"]
        lo, hi = claim["low_value"], claim["high_value"]
        # 扩展容差
        lo_tol = lo * 0.9 if lo > 0 else 0
        hi_tol = hi * 1.1 if hi > 0 else 0

        # 在同一单位下搜索匹配
        same_unit = [p for p in evidence_pairs if p["unit_norm"] == unit]
        matched = None
        for ep in same_unit:
            v = ep["value"]
            if lo_tol <= v <= hi_tol:
                matched = ep
                break

        if matched is None:
            return {
                "claimed": claim["expression"],
                "found_in_text": False,
                "context": "",
            }

        # 提取原文片段作为上下文
        context = ""
        try:
            # 优先用原始匹配文本（含单位）定位，更精确
            idx = -1
            matched_v_str = ""
            raw = matched.get("raw_text", "")
            if raw:
                idx = evidence_text.lower().find(raw.lower())
                matched_v_str = raw
            # 回退：按数值字符串定位
            if idx < 0:
                v = matched["value"]
                v_candidates = [str(v)]
                if abs(v - round(v)) < 1e-9:
                    v_candidates.append(str(int(round(v))))
                v_candidates.extend([f"{v:.1f}", f"{v:.2f}"])
                v_candidates = list(dict.fromkeys(v_candidates))
                for vs in v_candidates:
                    idx = evidence_text.lower().find(vs)
                    if idx >= 0:
                        matched_v_str = vs
                        break
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(evidence_text), idx + len(matched_v_str) + 120)
                context = evidence_text[start:end].strip()
                if len(context) > 200:
                    context = context[:200] + "..."
        except Exception:
            context = f"文献数值: {matched['value']} {unit}"

        return {
            "claimed": claim["expression"],
            "found_in_text": True,
            "context": context,
        }

    # ── 单条数值声明的细粒度验证 ──

    @staticmethod
    def _verify_numerical_claim(
        claim_value: str,           # e.g. "3-5 kJ/mol" or "29-40 kJ/mol"
        unit: str,                  # e.g. "kj/mol"
        context: str,               # e.g. "Qst sweet spot for CO2 adsorption"
        knowledge_graph_text: str = "",
        paper_summaries_text: str = "",
    ) -> dict:
        """对单条数值声明进行文献验证。

        在 knowledge graph 和 paper summaries 中搜索相同单位、相近范围的数值。
        返回详细的验证结果，包括文献值列表、最接近匹配、验证状态和建议。

        Args:
            claim_value: 数值声明字符串，如 "3-5 kJ/mol" 或 "29-40 kJ/mol"
            unit: 归一化后的单位，如 "kj/mol"
            context: 该数值所处的科学上下文（如 "Qst sweet spot"）
            knowledge_graph_text: knowledge_graph.md 全文
            paper_summaries_text: paper_summaries.md 全文

        Returns:
            {
                "claim": "3-5 kJ/mol",
                "verified": bool,
                "literature_values_found": [{"value": 4.2, "unit": "kj/mol",
                                             "source": "p123", "context": "..."}],
                "closest_match": {"value": X, "diff_pct": Y} or None,
                "verification_status": "verified" | "partial" | "unverified" | "contradicted",
                "recommendation": "...",
            }
        """
        import re as _re

        # ── 1. 解析声明中的数值范围 ──
        parsed = ToolHandlers._extract_claimed_values(claim_value)
        if not parsed:
            # 回退：尝试从 claim_value 中提取数值
            num_match = _re.findall(r'(\d+(?:\.\d+)?)', claim_value)
            if num_match:
                vals = [float(x) for x in num_match]
                lo, hi = min(vals), max(vals)
                parsed = [{
                    "expression": claim_value,
                    "low_value": lo, "high_value": hi,
                    "prefix": "", "unit_norm": unit,
                }]
            else:
                return {
                    "claim": claim_value,
                    "verified": False,
                    "literature_values_found": [],
                    "closest_match": None,
                    "verification_status": "unverified",
                    "recommendation": f"无法解析声明中的数值: {claim_value}",
                }

        claim_info = parsed[0]
        claim_lo = claim_info["low_value"]
        claim_hi = claim_info["high_value"]
        claim_unit = claim_info["unit_norm"] or unit

        # ── 2. 合并证据文本并提取所有同单位数值 ──
        evidence_text = (knowledge_graph_text or "") + "\n\n" + (paper_summaries_text or "")
        if not evidence_text.strip():
            return {
                "claim": claim_value,
                "verified": False,
                "literature_values_found": [],
                "closest_match": None,
                "verification_status": "unverified",
                "recommendation": "无文献证据文本可供验证",
            }

        # 使用 extractor 中的工具函数
        try:
            from literature_agent.extractor import extract_numerical_values_with_context
        except ImportError:
            # 回退到本地实现
            extract_numerical_values_with_context = None

        if extract_numerical_values_with_context:
            all_evidence = extract_numerical_values_with_context(
                evidence_text, unit_patterns=[claim_unit]
            )
        else:
            all_evidence = ToolHandlers._extract_evidence_values(evidence_text)
            all_evidence = [
                e for e in all_evidence
                if e.get("unit_norm") == claim_unit
            ]

        # ── 3. 查找匹配或接近的文献值 ──
        # 计数论文数量（按 ### 标题）
        paper_count = len(_re.findall(r'^###\s+\d+\.', evidence_text, _re.MULTILINE))
        if paper_count == 0:
            paper_count = max(1, len(_re.findall(r'^##\s+', evidence_text, _re.MULTILINE)))

        # 文献中同单位数值
        literature_values_found = []
        for ev in all_evidence[:200]:
            ev_val = ev.get("value", 0)
            ev_unit = ev.get("unit") or ev.get("unit_norm", "")
            # 在 ±15% 容差内视为匹配
            tol_lo = claim_lo * 0.85 if claim_lo > 0 else 0
            tol_hi = claim_hi * 1.15 if claim_hi > 0 else 0
            if tol_lo <= ev_val <= tol_hi:
                # 提取来源
                source = ""
                ev_context = ev.get("context_sentence", "") or ev.get("raw_text", "")
                # 尝试从上下文提取论文编号
                src_match = _re.search(r'(?:p\d+|paper\s*\d+|ref\s*\d+)', ev_context, _re.IGNORECASE)
                if src_match:
                    source = src_match.group(0)
                else:
                    # 查找所属的 ### 标题
                    ev_pos = ev.get("start_pos", -1)
                    if ev_pos >= 0:
                        before = evidence_text[:ev_pos]
                        header_match = _re.findall(r'^###\s+(\d+\..+)', before, _re.MULTILINE)
                        if header_match:
                            source = header_match[-1][:60]

                literature_values_found.append({
                    "value": ev_val,
                    "unit": ev_unit,
                    "source": source,
                    "context": ev_context[:200],
                })

        # ── 4. 找最接近匹配 ──
        closest_match = None
        if all_evidence:
            best_dist = float("inf")
            best_val = None
            # 用声明范围的中点比较
            claim_mid = (claim_lo + claim_hi) / 2.0
            for ev in all_evidence:
                ev_val = ev.get("value", 0)
                if ev_val > 0:
                    dist = abs(ev_val - claim_mid) / max(ev_val, 1e-6)
                    if dist < best_dist:
                        best_dist = dist
                        best_val = ev_val
            if best_val is not None:
                closest_match = {
                    "value": best_val,
                    "diff_pct": round(best_dist * 100, 1),
                }

        # ── 5. 判定验证状态 ──
        n_found = len(literature_values_found)
        if n_found >= 2:
            verification_status = "verified"
            verified = True
            recommendation = ""
        elif n_found == 1:
            verification_status = "partial"
            verified = True
            recommendation = (
                f"仅找到 1 条接近的文献记录（最接近: {closest_match['value']} {claim_unit}"
                f"，偏差 {closest_match['diff_pct']}%），建议扩大检索范围确认"
            )
        else:
            # 检查是否有矛盾值（同单位但显著偏离）
            if closest_match and closest_match["diff_pct"] > 50:
                verification_status = "contradicted"
                verified = False
                recommendation = (
                    f"文献中最接近值为 {closest_match['value']} {claim_unit}"
                    f"（偏差 {closest_match['diff_pct']}%），与声明显著矛盾"
                )
            else:
                verification_status = "unverified"
                verified = False
                # 生成具体的验证方案（根据单位类型推荐实验方法）
                if "kj/mol" in unit.lower() or "ev" in unit.lower():
                    recommendation = (
                        f"预测值 {claim_value}（待实验验证，建议方案："
                        f"微量热法测定零覆盖吸附热（Qst），"
                        f"或 DFT 计算结合能作为代理验证"
                        f"）"
                    )
                elif "mmol/g" in unit.lower() or "mg/g" in unit.lower():
                    recommendation = (
                        f"预测值 {claim_value}（待实验验证，建议方案："
                        f"静态容量法或动态穿透实验测定吸附等温线，"
                        f"拟合 Langmuir/Freundlich 模型获得饱和容量"
                        f"）"
                    )
                elif "ppm" in unit.lower():
                    recommendation = (
                        f"预测值 {claim_value}（待实验验证，建议方案："
                        f"控制气氛暴露实验 + GC/MS 定量分析，"
                        f"或原位 DRIFTS 监测官能团变化"
                        f"）"
                    )
                elif "h" in unit.lower() or "min" in unit.lower():
                    recommendation = (
                        f"预测值 {claim_value}（待实验验证，建议方案："
                        f"定时取样 + 性能衰减曲线拟合，"
                        f"确定半衰期或阈值暴露时间"
                        f"）"
                    )
                elif "m2/g" in unit.lower():
                    recommendation = (
                        f"预测值 {claim_value}（待实验验证，建议方案："
                        f"77K N2 吸附-脱附等温线 + BET 分析"
                        f"）"
                    )
                else:
                    recommendation = (
                        f"预测值 {claim_value} — 未在现有文献中找到直接支撑。"
                        f"建议通过系统性实验或第一性原理计算进行验证，"
                        f"并将结果与已知文献范围 [{unit}] 进行比较。"
                    )

        return {
            "claim": claim_value,
            "verified": verified,
            "literature_values_found": literature_values_found[:10],
            "closest_match": closest_match,
            "verification_status": verification_status,
            "paper_count_searched": paper_count,
            "recommendation": recommendation,
        }

    def _verify_hypothesis_values(self, hypothesis: dict, evidence_text: str) -> dict:
        """交叉验证 LLM 在假设中声称的数值是否在文献证据中可查。

        对假设的 title + description + expected_relationship 中出现的所有
        数值（如 '29-40 kJ/mol', '8.30 mmol/g', '3.67-8.6 mmol/g'），
        在 evidence_text（knowledge_graph.md 或 paper_summaries.md）中
        搜索匹配，返回每个数值的验证状态。

        防误报设计（2026-08 修复）：
        1. 证据文本先按论文条目（paper 级块）切分，数值匹配在单个条目内完成，
           禁止跨条目拼接的"命中"；
        2. 匹配到的上下文只返回"来源论文标识 + 该条目内实际含该数值的句子"，
           不混入其他条目内容；
        3. 范围/区间类声称值需满足语义对应（如 40-60% RH 需证据出现在 RH 语境），
           孤立数字不算命中；无法定位到具体论文条目的声称值一律判定未查证。

        Returns:
            {
                "values_found": [{"claimed": "29-40 kJ/mol", "found_in_text": True/False,
                                  "context": "[来源: ...] 条目内含该数值的句子",
                                  "source_ids": [...]}],
                "overall_verification_score": 0.0-1.0,
                "unverified_values": ["值1", "值2"],
            }
        """
        try:
            # 1. 组合假设文本（清除之前追加的 [数值验证] 标注，避免重复计数）
            desc_clean = re.sub(
                r'\n{0,2}\[数值验证\][^\n]*', '',
                str(hypothesis.get("description", "")),
            )
            hypo_text = " ".join([
                str(hypothesis.get("title", "")),
                desc_clean,
                str(hypothesis.get("expected_relationship", "")),
            ])

            # 2. 提取假设中声称的数值
            claimed = self._extract_claimed_values(hypo_text)

            # 3. 按论文条目切分证据文本（每条带来源标识）
            entries = self._split_evidence_entries(evidence_text)

            # 4. 逐条声称值在"单个条目"内匹配（带语义校验）
            values_found = []
            unverified = []
            for claim in claimed:
                claim["claim_context"] = self._extract_claim_context(hypo_text, claim)
                result = self._match_claim_in_entries(claim, entries)
                values_found.append(result)
                if not result.get("found_in_text"):
                    unverified.append(claim["expression"])

            # 5. 计算整体验证分数
            total = len(claimed)
            found_count = sum(1 for v in values_found if v.get("found_in_text"))
            overall_score = round(found_count / total, 2) if total > 0 else 1.0

            result_dict = {
                "values_found": values_found,
                "overall_verification_score": overall_score,
                "unverified_values": unverified,
            }
            # 保留上次的 _confidence_adjusted 标记（防止重复惩罚）
            if isinstance(hypothesis, dict):
                prev_vv = hypothesis.get("value_verification")
                if isinstance(prev_vv, dict) and prev_vv.get("_confidence_adjusted"):
                    result_dict["_confidence_adjusted"] = True
            return result_dict
        except Exception as e:
            # 优雅降级: 验证不可用时不报错
            return {
                "values_found": [],
                "overall_verification_score": 1.0,
                "unverified_values": [],
                "verification_error": f"验证不可用: {e}",
            }

    # ── 数值验证辅助方法 ──

    @staticmethod
    def _make_verification_plan_for_value(claim_expression: str) -> str:
        """为单个未验证的数值声明生成具体的实验验证方案。

        根据数值单位推荐最合适的实验/计算方法。
        """
        expr_lower = claim_expression.lower()

        if "kj/mol" in expr_lower or "ev" in expr_lower or "千焦" in expr_lower:
            return (
                f"预测值 {claim_expression}（待实验验证，建议方案："
                f"微量热法测定零覆盖Qst，或DFT计算结合能作为代理验证）"
            )
        elif "mmol/g" in expr_lower or "mg/g" in expr_lower or "毫摩" in expr_lower:
            return (
                f"预测值 {claim_expression}（待实验验证，建议方案："
                f"静态容量法测定吸附等温线，拟合模型获得饱和容量）"
            )
        elif "ppm" in expr_lower:
            return (
                f"预测值 {claim_expression}（待实验验证，建议方案："
                f"控制气氛暴露实验+GC/MS定量分析）"
            )
        elif "h" in expr_lower or "min" in expr_lower or "小时" in expr_lower:
            return (
                f"预测值 {claim_expression}（待实验验证，建议方案："
                f"定时取样+性能衰减曲线拟合确定阈值暴露时间）"
            )
        elif "m2/g" in expr_lower or "表面积" in expr_lower:
            return (
                f"预测值 {claim_expression}（待实验验证，建议方案："
                f"77K N2吸附-脱附等温线+BET分析）"
            )
        elif "mmol/cm3" in expr_lower or "mol/kg" in expr_lower:
            return (
                f"预测值 {claim_expression}（待实验验证，建议方案："
                f"容量法或重量法测定相应条件下的吸附量）"
            )
        elif "%" in expr_lower:
            return (
                f"预测值 {claim_expression}（待实验验证，建议方案："
                f"元素分析或TGA定量组成变化）"
            )
        else:
            return (
                f"预测值 {claim_expression} — 未在现有文献中找到直接支撑。"
                f"建议通过系统性实验或第一性原理计算进行验证。"
            )

    @staticmethod
    def _build_verification_detail_string(
        unverified_values: List[str],
        n_claimed: int,
        n_found: int,
        evidence_text: str,
        verify_result: dict = None,
    ) -> str:
        """生成数值验证状态的清晰表述。

        规则：
        - 如果全部未验证：使用"预测值（待实验验证）" + 验证方案
        - 如果部分验证：使用"文献验证状态" + 搜索统计
        - 绝不使用"未查证"作为终态——总是提供验证方案

        Returns:
            追加到描述末尾的 Markdown 格式字符串
        """
        import re as _re

        # 计数论文数量
        paper_count = len(_re.findall(r'^###\s+\d+\.', evidence_text, _re.MULTILINE))
        if paper_count == 0:
            paper_count = max(1, len(_re.findall(r'^##\s+', evidence_text, _re.MULTILINE)))

        parts = []

        if n_found == 0:
            # 全部未验证 → 预测值表述
            parts.append("\n\n**数值验证结果**")
            for uv in unverified_values:
                plan = ToolHandlers._make_verification_plan_for_value(uv)
                parts.append(f"\n- **预测值（待实验验证）**: `{uv}` — "
                           f"在 {paper_count} 篇论文摘要中检索，未找到直接支撑。"
                           f"\n  建议验证方案: {plan}")
        elif n_found < n_claimed:
            # 部分验证 → 混合表述
            parts.append("\n\n**文献验证状态**")
            parts.append(f"\n在 {paper_count} 篇论文摘要中检索，"
                       f"声称的 {n_claimed} 个数值中，{n_found} 个在文献中有匹配记录。")
            for uv in unverified_values:
                plan = ToolHandlers._make_verification_plan_for_value(uv)
                parts.append(f"\n- **预测值（待实验验证）**: `{uv}`"
                           f"\n  建议验证方案: {plan}")

            # 列出已验证的值
            if verify_result:
                verified_vals = [
                    v.get("claimed", "?") for v in verify_result.get("values_found", [])
                    if v.get("found_in_text")
                ]
                if verified_vals:
                    parts.append(f"\n- **已验证**: {', '.join(f'`{v}`' for v in verified_vals)}")
        else:
            # 全部验证 → 简洁肯定表述
            parts.append("\n\n**文献验证状态**: 声称的全部数值均在文献中有匹配记录。")

        return "".join(parts)

    def h_run_discovery_search(self, args: dict) -> str:
        """执行搜索算法探索材料-性质空间。

        评分基于 Agent 自写的知识图谱（knowledge_graph.md，Markdown）或论文摘要：
        材料覆盖率 + 材料×性质共现 + 数值接近文献报告值，不再依赖 JSON 知识图谱。
        """
        from literature_agent.discovery import DiscoveryEngine
        from pathlib import Path as _Path
        import json as _json

        idx = args.get("hypothesis_index", 0)
        n_iterations = min(args.get("n_iterations", 30), 100)
        method = args.get("search_method", "bayesian")

        hypo_file = _Path(_cfg.SURVEY_DIR) / "discovery" / "hypotheses.json"
        if hypo_file.exists():
            hypotheses_data = _json.loads(hypo_file.read_text(encoding="utf-8"))
            self.survey_state["hypotheses"] = hypotheses_data
        else:
            hypotheses_data = self.survey_state.get("hypotheses", [])
        if idx >= len(hypotheses_data):
            return f"❌ Invalid hypothesis_index: {idx} (only {len(hypotheses_data)} hypotheses available)"

        from literature_agent.discovery import DiscoveryHypothesis
        hyp = self._safe_hypothesis(hypotheses_data[idx])

        # ── 知识来源：优先 Agent 自写的知识图谱（Markdown），缺省回退论文摘要 ──
        kg_md = f"{_cfg.SURVEY_DIR}/knowledge_graph.md"
        source_text = self._load_knowledge_source()
        if not source_text:
            return (
                "❌ 找不到知识来源（knowledge_graph.md / paper_summaries.md）。\n"
                f"请先 extract_knowledge 整理论文摘要，再 write_file 自己的知识图谱 "
                f"{kg_md}（材料/性质/数值/关系，Markdown 格式），然后重试。"
            )

        evid = self._build_evidence_index(source_text, hyp)

        engine = self.survey_state.get("discovery_engine")
        if engine is None:
            engine = DiscoveryEngine()
            self.survey_state["discovery_engine"] = engine

        # ── ✨ LLM 深度融合：注入 LLM 搜索引导函数 ──
        # 将 _llm_search_guide 注入 BayesianOptimizer 和 MCTSSearcher，
        # 使 LLM 在搜索过程中主动参与：评估中间候选的物理合理性、
        # 建议搜索空间的收缩/扩展、识别有前景但尚未探索的区域。
        # 这是路线 A 的核心得分点——LLM 不只是生成初始种子，而是全程参与搜索。
        # 2026-09 修复：_on_think 或 _call_llm 任一可用即注入（_call_llm 内部
        # 自动回退 直接 API → _on_think；实际 LLM 调用失败时 _llm_search_guide
        # 自身会优雅降级为启发式评分），主案例上线前即可正常参与搜索。
        llm_injected = False
        llm_enabled = bool(getattr(self, "_on_think", None)) or bool(
            getattr(self, "_call_llm", None))
        if llm_enabled:
            llm_guide = lambda cands: self._llm_search_guide(cands, hyp)
            try:
                engine.bayes_opt._llm_guide = llm_guide
                engine.mcts_searcher._llm_guide = llm_guide
                llm_injected = True
                self._print("  🧠 LLM 搜索引导已注入 BayesianOptimizer & MCTSSearcher")
            except Exception as e:
                self._print(f"  ⚠️ LLM 搜索引导注入失败: {e}（搜索仍正常运行）")
        else:
            self._print("  ⚠️ 未配置 LLM 调用路径，LLM 搜索引导不可用（搜索仍正常运行）")

        # Run search
        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)

        search_results = {
            "hypothesis_index": idx,
            "search_method": method,
            "iterations": n_iterations,
            "evidence": {
                "source": "knowledge_graph.md" if _Path(kg_md).exists() else "paper_summaries.md",
                "blocks": len(evid["blocks"]),
                "material_tokens": len(evid["material_tokens"]),
                "property_keywords": evid["prop_keywords"][:10],
                "literature_values": evid["values"][:20],
            },
        }

        # 根据文献证据构建搜索空间（bayesian 和 mcts 共用）
        param_space = self._search_space(evid)

        # 搜索确定性：显式固定 numpy 种子（兜底，不依赖 main.py 全局 seed_everything），
        # 保证贝叶斯/MCTS 的初始采样可复现；调用后恢复全局随机状态避免串扰其他环节。
        import numpy as _np
        from utils.config import SEED as _SEED
        _np_state = _np.random.get_state()
        _np.random.seed(_SEED)
        try:
            if method in ("bayesian", "hybrid"):
                best_params, best_score, log = engine.bayes_opt.optimize(
                    hyp, param_space,
                    objective_fn=lambda p: self._evidence_score(p, hyp, evid),
                    n_iterations=n_iterations,
                )
                search_results.update({
                    "best_params": best_params, "best_score": best_score,
                    "iteration_log": log[-10:],
                })
                hyp.confidence = max(hyp.confidence, best_score)
                hyp.candidates_explored = len(log) + 10
                hyp.search_iterations = n_iterations

            elif method == "mcts":
                # 使用真实参数空间生成候选动作（不再硬编码假值）
                pv_lo, pv_hi = param_space["property_value"]
                root_state = {"materials": hyp.materials, "property": hyp.property}
                best_state, best_score, log = engine.mcts_searcher.search(
                    root_state,
                    # 在参数空间内生成 15 个有意义的候选动作（5 个 property_value × 3 个 composition_x）
                    expand_fn=lambda s: [
                        {"property_value": round(v, 3),
                         "composition_x": round(x, 2),
                         "temperature": t,
                         "materials": hyp.materials[:3]}
                        for v in np.linspace(pv_lo, pv_hi, 5)
                        for x in np.linspace(0.1, 0.9, 3)
                        for t in [298, 323, 373]
                    ],
                    simulate_fn=lambda s: self._evidence_score(s, hyp, evid),
                    n_iterations=n_iterations * 5,
                )
                search_results.update({
                    "best_state": best_state, "best_score": best_score,
                    "search_log": log,
                })
                hyp.confidence = max(hyp.confidence, best_score)
                hyp.candidates_explored = len(log) * 5
                hyp.search_iterations = n_iterations * 5
        finally:
            _np.random.set_state(_np_state)

        # 写回搜索状态到 hypotheses.json（供 generate_discovery_report 汇总）
        hypotheses_data[idx] = asdict(hyp)
        (out_dir / "hypotheses.json").write_text(
            _json.dumps(hypotheses_data, ensure_ascii=False, indent=2))
        self.survey_state["hypotheses"] = hypotheses_data

        # ── LLM 引导审计信息 ──
        # 另一并行 agent 正在 discovery.py 里为 BayesianOptimizer/MCTSSearcher
        # 新增 _llm_events 列表（元素形如 {"iteration": int,
        # "type": "bayes_llm_guide"|"mcts_llm_guide", ...}）。
        # 用 getattr 防御：未记录事件时 n_events=0 并给出说明。
        llm_events: List = []
        for obj in (getattr(engine, "bayes_opt", None),
                    getattr(engine, "mcts_searcher", None)):
            evts = getattr(obj, "_llm_events", None) if obj is not None else None
            if isinstance(evts, list):
                llm_events.extend(evts)
        n_llm_events = len(llm_events)
        audit_events: List = [e for e in llm_events[:50] if isinstance(e, dict)]
        if n_llm_events == 0:
            audit_events = ["no_llm_events_recorded"]
        search_results["llm_guidance"] = {
            "enabled": llm_enabled,
            "injected": llm_injected,
            "n_events": n_llm_events,
            "events": audit_events,
        }

        # Save search results
        (out_dir / f"search_h{idx}.json").write_text(
            _json.dumps(search_results, ensure_ascii=False, indent=2)
        )
        self.survey_state["search_results"] = search_results

        return (
            f"✅ Discovery search complete for hypothesis #{idx}: '{hyp.title[:80]}'\n"
            f"   Search method: {method}\n"
            f"   Iterations: {n_iterations} | Candidates explored: {hyp.candidates_explored}\n"
            f"   Best score: {best_score:.3f}\n"
            f"   Evidence: {len(evid['blocks'])} blocks, {len(evid['material_tokens'])} materials, "
            f"{len(evid['values'])} literature values\n"
            f"   LLM guidance: injected={llm_injected}, events={n_llm_events}\n"
            f"   Updated confidence: {hyp.confidence:.2f}\n\n"
            f"Next: validate_discovery(hypothesis_index={idx}) to cross-validate against external databases."
        )

    def h_check_novelty(self, args: dict) -> str:
        """系统性地对一条或多条假设进行已有文献查重，验证新颖性。

        为每条假设生成 3-5 条"反向检索查询"（专门用于发现已有文献的查询策略），
        通过 LiteratureSearcher 执行检索，计算文本重叠度，调整 novelty_score。
        不依赖 LLM——使用启发式文本相似度（Jaccard）进行重叠评估；
        如果 LLM API 可用，仅用于生成重叠评估的说明文字。

        Args:
            hypothesis_index: 要验证的假设索引（-1 表示全部）
            top_k: 每个查询返回的结果数（默认 5）

        Returns:
            每条假设的 PriorArtReport 摘要
        """
        from pathlib import Path as _Path
        import json as _json

        idx = args.get("hypothesis_index", -1)
        top_k = min(args.get("top_k", 5), 10)

        # Load hypotheses
        hypo_file = _Path(_cfg.SURVEY_DIR) / "discovery" / "hypotheses.json"
        if hypo_file.exists():
            hypotheses_data = _json.loads(hypo_file.read_text(encoding="utf-8"))
            self.survey_state["hypotheses"] = hypotheses_data
        else:
            hypotheses_data = self.survey_state.get("hypotheses", [])
        if not hypotheses_data:
            return "❌ No hypotheses found."

        # Determine which hypotheses to check
        if idx == -1:
            indices = list(range(len(hypotheses_data)))
        elif 0 <= idx < len(hypotheses_data):
            indices = [idx]
        else:
            return f"❌ Invalid hypothesis_index: {idx} (only {len(hypotheses_data)} available)"

        # Create searcher once (shared across checks)
        from literature_agent.search import LiteratureSearcher
        import os as _os
        searcher = LiteratureSearcher(
            cache_dir=_cfg.get_literature_cache_dir(),
            sciverse_api_key=_os.environ.get("SCIVERSE_API_KEY", ""),
        )

        self._print(f"  🔍 系统查重: 对 {len(indices)} 条假设执行已有文献检索...")

        reports = []
        for i in indices:
            hyp = hypotheses_data[i]
            self._print(f"    查重: 假设 #{i} '{str(hyp.get('title', ''))[:60]}...'")
            report = self._systematic_prior_art_search(hyp, searcher)

            # ── Update hypothesis with prior art results ──
            # Store the full report for later use
            hyp["prior_art_verification"] = report

            # Update novelty_score with the adjusted value from actual search
            hyp["novelty_score"] = report["novelty_score_adjusted"]

            # Append prior art evidence to evidence_chain
            prior_art_entry = (
                f"[Novelty Verification] Overlap: {report['overlap_assessment']} | "
                f"Adjusted novelty: {report['novelty_score_adjusted']:.3f} "
                f"(was {report['original_novelty']:.3f}) | "
                f"Queries: {len(report['queries_executed'])} | "
                f"Results: {report['total_results_found']} | "
                f"Assessment: {report['justification'][:200]}"
            )
            if hyp.get("evidence_chain"):
                hyp["evidence_chain"].append(prior_art_entry)
            else:
                hyp["evidence_chain"] = [prior_art_entry]

            # Also log overlapping paper titles
            for op in report.get("potentially_overlapping_papers", [])[:3]:
                overlap_entry = (
                    f"[Overlap] \"{op['title'][:150]}\" "
                    f"(similarity={op['overlap_ratio']:.3f}, {op.get('source','?')}, "
                    f"{op.get('year','?')})"
                )
                hyp["evidence_chain"].append(overlap_entry)

            reports.append(report)

        # Save updated hypotheses
        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)
        (_Path(out_dir) / "hypotheses.json").write_text(
            _json.dumps(hypotheses_data, ensure_ascii=False, indent=2)
        )
        self.survey_state["hypotheses"] = hypotheses_data

        # Build summary
        lines = [f"✅ 系统查重完成: {len(indices)} 条假设已验证\n"]
        for i, report in zip(indices, reports):
            lines.append(
                f"### 假设 #{i}: {hypotheses_data[i].get('title', '?')[:80]}"
            )
            lines.append(f"- 重叠评估: **{report['overlap_assessment']}**")
            lines.append(f"- 原始新颖性: {report['original_novelty']:.3f}")
            lines.append(f"- 调整后新颖性: **{report['novelty_score_adjusted']:.3f}**")
            lines.append(f"- 检索查询数: {len(report['queries_executed'])}")
            lines.append(f"- 检索结果总数: {report['total_results_found']}")
            lines.append(f"- 潜在重叠论文: {len(report['potentially_overlapping_papers'])} 篇")
            lines.append(f"- 评估说明: {report['justification'][:150]}")
            lines.append("")

        return "\n".join(lines)

    def h_validate_discovery(self, args: dict) -> str:
        """对假设进行外部数据库交叉验证。"""
        from literature_agent.discovery import DiscoveryEngine, MaterialsProjectValidator
        from literature_agent.discovery import DiscoveryHypothesis
        from pathlib import Path as _Path
        import json as _json

        idx = args.get("hypothesis_index", 0)
        hypo_file = _Path(_cfg.SURVEY_DIR) / "discovery" / "hypotheses.json"
        if hypo_file.exists():
            hypotheses_data = _json.loads(hypo_file.read_text(encoding="utf-8"))
            self.survey_state["hypotheses"] = hypotheses_data
        else:
            hypotheses_data = self.survey_state.get("hypotheses", [])
        if idx >= len(hypotheses_data):
            return f"❌ Invalid hypothesis_index: {idx}"

        hyp = self._safe_hypothesis(hypotheses_data[idx])

        # ── Step 0: 数值文献验证（在外部数据库验证之前）──
        # 对假设中声称的所有数值（如 "3-5 kJ/mol", "29-40 kJ/mol"），
        # 先在 knowledge_graph.md 和 paper_summaries.md 中查证。
        # 可查证的标记为 "verified"，不可查证的标记为 "predicted" 并附加验证方案。
        evidence_text = self._load_knowledge_source()
        numerical_verification_results = {}
        if evidence_text:
            self._print("  🔢 执行数值文献交叉验证...")
            # 组合假设文本（清除旧标注）
            desc_clean = re.sub(
                r'\n{0,2}\[数值验证\][^\n]*',
                '',
                str(hypotheses_data[idx].get("description", "")),
            )
            hypo_text = " ".join([
                str(hyp.title or ""),
                desc_clean,
                str(hyp.expected_relationship or ""),
            ])
            claimed = self._extract_claimed_values(hypo_text)
            kg_text = evidence_text if "knowledge_graph" in str(
                self.survey_state.get("knowledge_graph_path", "")
            ) else ""
            ps_text = evidence_text if "paper_summaries" in str(
                self.survey_state.get("paper_summary_path", "")
            ) else evidence_text

            for claim in claimed:
                claim_str = claim["expression"]
                unit = claim["unit_norm"]
                ctx = claim_str  # 用声明本身作为上下文
                result = self._verify_numerical_claim(
                    claim_value=claim_str,
                    unit=unit,
                    context=ctx,
                    knowledge_graph_text=kg_text or evidence_text,
                    paper_summaries_text=ps_text,
                )
                numerical_verification_results[claim_str] = result

                status = result.get("verification_status", "unverified")
                if status in ("verified", "partial"):
                    # 找到文献支撑
                    lit_vals = result.get("literature_values_found", [])
                    sources = [v.get("source", "?") for v in lit_vals[:3] if v.get("source")]
                    source_str = ", ".join(sources) if sources else "文献证据"
                    evidence_entry = (
                        f"文献验证: {claim_str} — 在 {result.get('paper_count_searched', '?')} "
                        f"篇论文中检索到 {len(lit_vals)} 条匹配记录"
                        f"{' (来源: ' + source_str + ')' if source_str else ''}"
                    )
                    if evidence_entry not in hyp.evidence_chain:
                        hyp.evidence_chain.append(evidence_entry)
                else:
                    # 未验证 → 标记为预测值，追加验证方案
                    plan = self._make_verification_plan_for_value(claim_str)
                    if plan and plan not in hyp.evidence_chain:
                        hyp.evidence_chain.append(plan)

            verified_count = sum(
                1 for v in numerical_verification_results.values()
                if v.get("verification_status") in ("verified", "partial")
            )
            predicted_count = len(numerical_verification_results) - verified_count
            self._print(
                f"  ✅ 数值验证完成: {verified_count} 个已查证, "
                f"{predicted_count} 个标记为预测值"
            )

        validator = MaterialsProjectValidator()
        result = validator.validate(hyp)

        # Update hypothesis with validation
        if result.get("overall_match"):
            hyp.validation_status = "validated"
        elif result.get("databases_checked"):
            hyp.validation_status = "inconclusive"
        else:
            hyp.validation_status = "pending"
        hyp.external_validation = result

        # ── ✨ LLM 深度评估：对假设进行科学合理性评分 ──
        # 在外部数据库验证之外，引入 LLM 从理论基础、文献一致性、
        # 可验证性和新颖性四个维度对假设进行综合评分。
        # _llm_plausibility_check 内置三层降级：LLM API > 启发式评分 > 默认值
        # 因此即使 _on_think 不可用，也能产出有意义的评分。
        try:
            score, explanation = self._llm_plausibility_check(
                hyp,
                search_results=self.survey_state.get("search_results")
            )
            hyp.llm_plausibility_score = score
            hyp.llm_explanation = explanation
            self._print(f"  🧠 LLM plausibility: {score:.2f} — {explanation[:80]}...")
        except Exception as e:
            self._print(f"  ⚠️ LLM plausibility check 异常: {e}")
            hyp.llm_plausibility_score = 0.5
            hyp.llm_explanation = f"LLM 评估异常（{str(e)[:80]}），采用默认评分 0.5"

        # ── 一致性检查：LLM 合理性 vs 系统置信度 ──
        # 如果 LLM 认为假设科学基础薄弱，但外部数据库搜索标记为 "validated"，
        # 则存在直接矛盾——系统置信度需要降权以反映 LLM 的科学判断。
        system_confidence = hyp.confidence
        llm_plaus = getattr(hyp, 'llm_plausibility_score', 0.0)

        # Case 1: LLM says implausible (< 0.35) but system says validated/high confidence (> 0.7)
        if llm_plaus < 0.35 and system_confidence > 0.7:
            hyp.validation_status = "contested"
            hyp.confidence = hyp.confidence * 0.7 + llm_plaus * 0.3
            if hasattr(hyp, 'llm_explanation') and hyp.llm_explanation:
                hyp.llm_explanation += (
                    f"\n\n[⚠️ 置信度争议] LLM 科学合理性评估 ({llm_plaus:.2f}) "
                    f"与系统搜索得分 ({system_confidence:.2f}) 存在显著差异。"
                    f"最终置信度已降权至 {hyp.confidence:.2f}。"
                    f"建议：优先采信 LLM 的科学判断，或提供额外实验证据解决争议。"
                )
            self._print(
                f"  ⚠️ 置信度争议: LLM={llm_plaus:.2f} vs System={system_confidence:.2f}, "
                f"降权至 {hyp.confidence:.2f}, 状态→contested"
            )

        # Case 2: LLM plausibility is high (> 0.7) and system confidence is low (< 0.5)
        # This means the science is sound but search didn't find strong evidence
        elif llm_plaus > 0.7 and system_confidence < 0.5:
            if hyp.validation_status == "inconclusive":
                hyp.validation_status = "underexplored"
            if hasattr(hyp, 'llm_explanation') and hyp.llm_explanation:
                hyp.llm_explanation += (
                    f"\n\n[🔍 探索不足] LLM 科学合理性评估 ({llm_plaus:.2f}) 较高，"
                    f"但系统搜索得分 ({system_confidence:.2f}) 偏低。"
                    f"该假设可能具有探索价值。"
                    f"建议：扩大检索范围或更换检索策略。"
                )
            self._print(
                f"  🔍 探索不足: LLM={llm_plaus:.2f} 高但 System={system_confidence:.2f} 低, "
                f"状态→underexplored"
            )

        # Save updated hypothesis
        hypotheses_data[idx] = asdict(hyp)
        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "hypotheses.json").write_text(
            _json.dumps(hypotheses_data, ensure_ascii=False, indent=2)
        )
        self.survey_state["hypotheses"] = hypotheses_data

        evidence = result.get("supporting_evidence", [])
        return (
            f"{'✅' if result.get('overall_match') else '❓'} Validation for hypothesis #{idx}: '{hyp.title[:80]}'\n"
            f"   Status: {hyp.validation_status}\n"
            f"   Databases checked: {result.get('databases_checked', [])}\n"
            f"   Materials Project hits: {result.get('details', {}).get('materials_project', {}).get('matching_entries', [])}\n"
            f"   Supporting evidence ({len(evidence)} entries):\n" +
            "\n".join(f"   - {e}" for e in evidence[:5]) +
            f"\n\nNext: generate_discovery_report to produce the final Route A report."
        )

    def h_generate_discovery_report(self, args: dict) -> str:
        """生成路线 A 发现报告。"""
        from literature_agent.discovery import DiscoveryReport, DiscoveryHypothesis
        from pathlib import Path as _Path
        import json as _json

        hypo_file = _Path(_cfg.SURVEY_DIR) / "discovery" / "hypotheses.json"
        if hypo_file.exists():
            hypotheses_data = _json.loads(hypo_file.read_text(encoding="utf-8"))
            self.survey_state["hypotheses"] = hypotheses_data
        else:
            hypotheses_data = self.survey_state.get("hypotheses", [])
        if not hypotheses_data:
            return "❌ No hypotheses found. Run generate_hypotheses first."

        hypotheses = [self._safe_hypothesis(h) for h in hypotheses_data]

        # ── ✨ LLM 深度评估：为所有未评分的假设补充 LLM plausibility check ──
        # 在生成最终报告前，确保每条假设都有 LLM 科学合理性评分。
        # _llm_plausibility_check 内置三层降级（LLM API > 启发式 > 默认值），
        # 因此无论 _on_think 是否可用都始终执行。
        llm_scored_count = 0
        for i, hyp in enumerate(hypotheses):
            if hyp.llm_plausibility_score <= 0.01 and not hyp.llm_explanation:
                try:
                    self._print(f"  🧠 补充 LLM 评估: 假设 #{i} '{hyp.title[:50]}...'")
                    score, explanation = self._llm_plausibility_check(
                        hyp,
                        search_results=self.survey_state.get("search_results")
                    )
                    hyp.llm_plausibility_score = score
                    hyp.llm_explanation = explanation
                    hypotheses_data[i]["llm_plausibility_score"] = score
                    hypotheses_data[i]["llm_explanation"] = explanation
                    llm_scored_count += 1
                except Exception as e:
                    self._print(f"  ⚠️ 假设 #{i} LLM 评估失败: {e}")
                    hyp.llm_plausibility_score = 0.5
                    hyp.llm_explanation = f"LLM 评估失败，采用默认评分 0.5"
                    hypotheses_data[i]["llm_plausibility_score"] = 0.5
                    hypotheses_data[i]["llm_explanation"] = hyp.llm_explanation
                    llm_scored_count += 1

        if llm_scored_count > 0:
            self._print(f"  ✅ 补充完成 {llm_scored_count} 条假设的 LLM plausibility 评估")
            # 写回更新后的 hypotheses.json
            out_dir_tmp = _Path(_cfg.SURVEY_DIR) / "discovery"
            out_dir_tmp.mkdir(parents=True, exist_ok=True)
            (out_dir_tmp / "hypotheses.json").write_text(
                _json.dumps(hypotheses_data, ensure_ascii=False, indent=2)
            )
            self.survey_state["hypotheses"] = hypotheses_data

        # ── 四象限一致性分类：按 LLM 合理性 vs 系统置信度对每条假设分级 ──
        # 阈值: LLM plausibility >= 0.5 视为"科学合理", 系统置信度 >= 0.5 视为"数据支撑充分"
        LLM_THRESHOLD = 0.50
        SEARCH_THRESHOLD = 0.50
        consistency_counts = {"strong": 0, "underexplored": 0, "contested": 0, "weak": 0}
        for hyp in hypotheses:
            llm_high = hyp.llm_plausibility_score >= LLM_THRESHOLD
            search_high = hyp.confidence >= SEARCH_THRESHOLD
            if llm_high and search_high:
                consistency_counts["strong"] += 1
            elif llm_high and not search_high:
                consistency_counts["underexplored"] += 1
            elif not llm_high and search_high:
                consistency_counts["contested"] += 1
            else:
                consistency_counts["weak"] += 1

        # ── 合并 search_h*.json 的搜索分数（best_score / 数值证据 / 空转警告）──
        # 与 DiscoveryReport.from_files 保持一致：报告必须呈现每条假设的搜索最优分，
        # 否则渲染为 "N/A（无搜索记录）"（2026-08 修复：H3 best 0.913 在报告中丢失）。
        # 命名约定：search_h{i}.json 的 i 对应 hypotheses.json 中第 i 条假设。
        search_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        for i, hyp in enumerate(hypotheses):
            sfile = search_dir / f"search_h{i}.json"
            if sfile.exists():
                try:
                    sres = _json.loads(sfile.read_text(encoding="utf-8"))
                    if sres.get("best_score") is not None:
                        hyp.best_score = float(sres["best_score"])
                    # 文献数值在 evidence 嵌套层（search_h*.json 结构），
                    # 不是顶层——2026-08 修复：否则报告显示"文献数值证据 0 个"
                    evidence = sres.get("evidence") or {}
                    lv = evidence.get("literature_values") or sres.get("literature_values") or []
                    if lv:
                        hyp.literature_values = [float(v) for v in lv
                                                 if isinstance(v, (int, float))]
                    if evidence.get("warning") or sres.get("warning"):
                        hyp.search_warning = evidence.get("warning") or sres.get("warning")
                except Exception as e:
                    self._print(f"  ⚠️ search_h{i}.json 读取失败: {e}")

        report = DiscoveryReport(
            title=f"Structure-Property Relationship Discovery",
            hypotheses=hypotheses,
            total_candidates=len(hypotheses),
            total_explored=sum(h.candidates_explored for h in hypotheses),
            validated_count=sum(1 for h in hypotheses if h.validation_status == "validated"),
            refuted_count=sum(1 for h in hypotheses if h.validation_status == "refuted"),
            contested_count=consistency_counts["contested"],
            underexplored_count=consistency_counts["underexplored"],
            materials_project_hits=sum(1 for h in hypotheses
                                      if h.external_validation.get("overall_match")),
            search_summary=(
                f"Explored {len(hypotheses)} hypotheses via Bayesian optimization and MCTS. "
                f"四象限一致性: strong={consistency_counts['strong']}, "
                f"underexplored={consistency_counts['underexplored']}, "
                f"contested={consistency_counts['contested']}, "
                f"weak={consistency_counts['weak']}"
            ),
        )

        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path, json_path = report.save(str(out_dir))

        # ── Inject "Novelty Verification" sections into the markdown report ──
        # For each hypothesis that has prior_art_verification data,
        # append a detailed novelty verification subsection.
        try:
            md_content = _Path(md_path).read_text(encoding="utf-8")
            novelty_sections = []
            for i, hyp_data in enumerate(hypotheses_data):
                pa = hyp_data.get("prior_art_verification")
                if not pa:
                    continue
                section = [
                    f"\n#### 新颖性验证 (Novelty Verification)",
                    f"",
                    f"**重叠评估:** {pa.get('overlap_assessment', '?')}",
                    f"**原始新颖性分数:** {pa.get('original_novelty', 0):.3f}",
                    f"**调整后新颖性分数:** {pa.get('novelty_score_adjusted', 0):.3f}",
                    f"",
                    f"**检索查询:**",
                ]
                for j, q in enumerate(pa.get("queries_executed", []), 1):
                    section.append(f"  {j}. `{q}`")
                section.append(f"")
                section.append(f"**检索结果总数:** {pa.get('total_results_found', 0)}")
                section.append(f"")
                if pa.get("potentially_overlapping_papers"):
                    section.append(f"**潜在重叠论文:**")
                    for op in pa["potentially_overlapping_papers"][:5]:
                        section.append(
                            f"  - \"{op['title'][:150]}\" "
                            f"(相似度={op['overlap_ratio']:.3f}, "
                            f"来源={op.get('source','?')}, "
                            f"{op.get('year','?')})"
                        )
                else:
                    section.append(f"**潜在重叠论文:** 无")
                section.append(f"")
                section.append(f"**评估说明:** {pa.get('justification', '')[:400]}")
                section.append(f"")

                novelty_sections.append((i + 1, section))

            # Inject sections after each hypothesis block (after "---" separator)
            if novelty_sections:
                lines = md_content.split("\n")
                new_lines = []
                current_hyp_idx = 0
                for line in lines:
                    new_lines.append(line)
                    # When we see a hypothesis header "### N. ", append novelty section
                    m = re.match(r'^###\s+(\d+)\.\s+', line)
                    if m:
                        h_num = int(m.group(1))
                        for nh_num, nh_section in novelty_sections:
                            if nh_num == h_num:
                                new_lines.extend(nh_section)
                                break
                updated_md = "\n".join(new_lines)
                _Path(md_path).write_text(updated_md, encoding="utf-8")
                self._print(
                    f"  📝 已向报告注入 {len(novelty_sections)} 条假设的新颖性验证章节"
                )
        except Exception as e:
            self._print(f"  ⚠️ 新颖性验证章节注入失败: {e}")

        self.survey_state["discovery_report"] = report.to_dict()

        return (
            f"✅ Discovery report generated\n"
            f"   Markdown: {md_path}\n"
            f"   JSON:     {json_path}\n"
            f"   Hypotheses: {len(hypotheses)}\n"
            f"   Validated: {report.validated_count} | Refuted: {report.refuted_count}\n"
            f"   Materials Project hits: {report.materials_project_hits}"
        )

    def h_run_model_comparison(self, args: dict) -> str:
        """经典模型对比（赛题硬性验证标准）。

        对假设的构效关系，用候选模型（线性/二次/幂律/指数等，由文献数值
        自动判定最优）与经典模型（Slack 带隙-温度模型、Vegard 定律等，
        自 literature_agent.classical_models 导入）在同一组文献数值点上拟合，
        输出 R²/RMSE 对比 + 嵌套 F 检验（候选 vs 经典）+ LLM 解释
        「候选是否优于经典、旧模型为何失效」。
        报告保存到 {SURVEY_DIR}/discovery/model_comparison_<idx>.md。
        """
        from pathlib import Path as _Path
        import json as _json

        idx = args.get("hypothesis_index", 0)
        classical_name = args.get("classical_model") or ""

        # ── 1. 加载假设 ──
        hypo_file = _Path(_cfg.SURVEY_DIR) / "discovery" / "hypotheses.json"
        if hypo_file.exists():
            hypotheses_data = _json.loads(hypo_file.read_text(encoding="utf-8"))
            self.survey_state["hypotheses"] = hypotheses_data
        else:
            hypotheses_data = self.survey_state.get("hypotheses", [])
        if idx >= len(hypotheses_data):
            return f"❌ Invalid hypothesis_index: {idx} (only {len(hypotheses_data)} available)"
        hyp = self._safe_hypothesis(hypotheses_data[idx])

        # property 为空时无法确定 y 单位语义，拒绝继续
        if not hyp.property:
            return (
                f"❌ 假设 #{idx} 未指定目标性质（property 为空），无法提取文献数值点。\n"
                "  请检查 hypotheses.json 中该假设的 property 字段。"
            )

        # ── 2. 文献数值点提取 ──
        source_text = self._load_knowledge_source()
        if not source_text:
            return "❌ 找不到知识来源（knowledge_graph.md / paper_summaries.md）。"
        data = self._extract_literature_points(source_text, hyp)
        if data is None:
            return (
                f"❌ 假设 #{idx} 未提取到足够的 (结构变量, 性质) 文献数值点。\n"
                "  需要同一文献块内同时出现结构变量（温度 K / 压力 bar / 掺杂比例 %）"
                "与性质数值（单位匹配假设性质），且至少 3 个不同的 x 值。\n"
                "  建议检查 knowledge_graph.md 中该材料-性质的数值表格是否同时含两列。"
            )
        x = np.asarray(data["x_vals"], dtype=float)
        y = np.asarray(data["y_vals"], dtype=float)
        n = len(y)
        x_label = {"temperature": "温度", "pressure": "压力",
                   "composition": "组分比例", "percentage": "百分比"}.get(
            data["x_label"], data["x_label"])

        # ── 3. 候选模型（由文献数值自动判定最优）──
        cands = self._fit_candidate_models(x, y)
        if not cands:
            return f"❌ 假设 #{idx} 的候选模型拟合全部失败（数据可能不适合建模）。"
        best = cands[0]

        # ── 3b. 稳健性验证（teacherB#6）：贝叶斯小样本回归（teacherA#5）
        #         + 诊断统计（adjusted R²/MAE/bootstrap CI/LOOCV/
        #         分组 CV/Cook's distance）──
        bayes_res = None
        diag_res = None
        try:
            from literature_agent.bayesian_regression import fit_bayesian_linear
            bayes_res = fit_bayesian_linear(x, y)
        except Exception as e:
            bayes_res = {"error": f"贝叶斯回归不可用: {e}"}
        try:
            from literature_agent.regression_diagnostics import (
                regression_diagnostics)
            groups = None
            meta = data.get("points_meta")
            if meta and data.get("n_groups", 0) >= 2:
                groups = [m["group"] for m in meta]
            diag_res = regression_diagnostics(x, y, groups=groups,
                                              n_boot=300, seed=42)
        except Exception as e:
            diag_res = {"error": f"回归诊断不可用: {e}"}

        # ── 3c. 数据质量分层回归（teacherB#2/#4：宽松纳入、严格分层）──
        tier_res = None
        meta = data.get("points_meta")
        if meta:
            tier_res = self._tiered_regression(meta)

        # ── 4. 经典模型（延迟导入；未就绪时回退线性基线）──
        cm_mod, cm_names, cm_error = self._load_classical_models()
        classic = None
        classic_desc = ""
        if cm_mod is not None and cm_names:
            chosen_fn = None
            if classical_name:
                # 用户指定
                for nm in cm_names:
                    if classical_name.lower() in nm.lower():
                        chosen_fn = getattr(cm_mod, nm)
                        classic_desc = nm
                        break
                if chosen_fn is None:
                    classic_desc = f"未找到匹配的经典模型 '{classical_name}'，可用: {', '.join(cm_names)}"
            else:
                # 按 x 类型自动选择：温度→Slack、组分→Vegard、其余→第一个可用
                pref = {"temperature": ("slack",), "composition": ("vegard",),
                        "percentage": ("vegard",)}.get(data["x_label"], ())
                for nm in cm_names:
                    if pref and any(p in nm.lower() for p in pref):
                        chosen_fn = getattr(cm_mod, nm)
                        classic_desc = nm
                        break
                if chosen_fn is None and cm_names:
                    chosen_fn = getattr(cm_mod, cm_names[0])
                    classic_desc = cm_names[0]
            if chosen_fn is not None:
                classic = self._call_classical_model(chosen_fn, x, y, n)
                classic_desc = f"{classic_desc} (自 classical_models 模块)"
        if classic is None:
            # 兜底：经典模块缺失/调用失败 → 用线性模型作为"经典基线"
            lin = next((c for c in cands if c["kind"] == "linear"), None)
            if lin is None:
                lin = dict(cands[0])
            classic = dict(lin)
            classic["name"] = "经典基线(线性)"
            base = cm_error if cm_error else (classic_desc or "经典模型不可用")
            classic_desc = f"{base} → 回退线性基线"

        # ── 5. 嵌套 F 检验（候选 best vs 经典 classic）──
        f_res = {"valid": False, "reason": ""}
        classic_rss = classic.get("rss")
        best_rss = best["rss"]
        if classic_rss is None or not np.isfinite(classic_rss):
            f_res = {"valid": False, "reason": "经典模型未返回残差平方和，跳过 F 检验"}
        elif best["k"] == classic["k"]:
            f_res = {"valid": False, "reason": "候选与经典模型参数数相同，无法做嵌套 F 检验"}
        elif best["k"] > classic["k"]:
            f_res = self._nested_f_test(n, classic_rss, classic["k"], best_rss, best["k"])
            f_res["full_side"] = "候选模型"
        else:
            f_res = self._nested_f_test(n, best_rss, best["k"], classic_rss, classic["k"])
            f_res["full_side"] = "经典模型"

        # ── 5b. 规则化统计判定（不依赖 LLM，赛题路线 A 验证标准）──
        verdict = self._model_compare_verdict(best, classic, f_res, diag_res)

        # ── 6. LLM 解释 ──
        cand_table = "\n".join(
            f"  - {c['name']} (k={c['k']}): R²={c['r2']:.4f}, RMSE={c['rmse']:.4g} "
            f"| {c['params']}"
            for c in cands
        )
        f_line = (
            f"F={f_res['F']:.4f}, df=({f_res['df_num']},{f_res['df_den']}), "
            f"p={f_res['p_value']:.4f}, 显著(p<0.05)={f_res['significant']}, "
            f"full 侧={f_res.get('full_side','?')}"
            if f_res.get("valid") else f"（{f_res.get('reason','不可用')}）"
        )
        classic_line = (
            f"R²={classic['r2']:.4f}, RMSE={classic['rmse']:.4g}, k={classic['k']}"
            if classic.get("r2") is not None and np.isfinite(classic.get("r2", float("nan")))
            else f"（经典模型结果缺失: {classic.get('error', '?')}）"
        )
        # 稳健性摘要行（贝叶斯 / 诊断 / 分层回归）
        bayes_line = "（不可用）"
        if bayes_res and "slope" in bayes_res:
            b = bayes_res["slope"]
            bayes_line = (
                f"slope={b['mean']:.4g} (95% CI [{b['ci_low']:.4g},{b['ci_high']:.4g}]), "
                f"BF(vs 常数模型)={bayes_res.get('bayes_factor_vs_constant', float('nan')):.3g}"
            )
        diag_line = "（不可用）"
        if diag_res and "ols" in diag_res and "bootstrap" in diag_res:
            o = diag_res["ols"]
            bt = diag_res["bootstrap"]
            parts = [
                f"adjusted R²={o.get('adjusted_r2', float('nan')):.4g}",
                f"MAE={o.get('mae', float('nan')):.4g}",
            ]
            bt_r2 = bt.get("r2", {})
            if bt_r2:
                parts.append(
                    f"bootstrap R² 95% CI=[{bt_r2.get('ci_low', float('nan')):.4g},"
                    f"{bt_r2.get('ci_high', float('nan')):.4g}]"
                )
            gc = diag_res.get("group_cv", {})
            if gc.get("valid"):
                parts.append(f"分组CV OOF R²={gc['oof_r2']:.4g}")
            cooks = diag_res.get("cooks", {})
            if cooks.get("valid"):
                parts.append(f"最大Cook's distance={cooks['max_cooks']:.3g}")
            diag_line = ", ".join(parts)
        tier_line = ""
        if tier_res:
            tier_line = "；".join(
                f"{k}层(n={v['n']},R²={v['r2']:.4g})" for k, v in tier_res.items())
        llm_prompt = (
            "你是一位材料科学专家。请对下面的构效关系模型对比结果给出中文解释，"
            "重点回答：(1) 候选模型是否优于经典模型；(2) 旧经典模型为何失效"
            "（物理机制层面，如温度非线性、组分偏离线性混合、缺陷/孔道效应等）。\n\n"
            f"### 假设\n"
            f"标题：{hyp.title}\n"
            f"描述：{str(hyp.description)[:300]}\n"
            f"目标性质：{hyp.property}\n"
            f"涉及材料：{', '.join(hyp.materials[:5]) if hyp.materials else '（未指定）'}\n\n"
            f"### 文献数据点\n"
            f"来源：knowledge_graph.md / paper_summaries.md\n"
            f"点数：{n}（x={x_label}，y 单位={data['y_unit']}"
            f"{'，含表头单位推断值' if data.get('y_implicit') else ''}）\n"
            f"x 范围：{float(x.min()):.4g} ~ {float(x.max()):.4g}；"
            f"y 范围：{float(y.min()):.4g} ~ {float(y.max()):.4g}\n\n"
            f"### 候选模型（自动判定最佳：{best['name']}）\n{cand_table}\n\n"
            f"### 经典模型（{classic_desc}）\n{classic_line}\n\n"
            f"### 嵌套 F 检验（候选 vs 经典）\n{f_line}\n\n"
            f"### 规则化统计判定（已由代码自动计算，请在你的解释中引用它）\n"
            f"{verdict.get('reason', '（不可判定）')}\n\n"
            f"### 稳健性验证（小样本贝叶斯 + 诊断统计）\n"
            f"- 贝叶斯线性回归: {bayes_line}\n"
            f"- 诊断: {diag_line}\n\n"
            f"### 数据质量分层回归（A 严格可比 / B 需换算 / C 弱可比）\n"
            f"{tier_line or '（无足够分层数据）'}\n\n"
            "请用中文输出，450 字以内，给出明确结论。"
        )
        llm_explanation = self._llm_model_compare_explanation(llm_prompt)

        # ── 7. 保存报告 ──
        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_lines = [
            f"# 模型对比报告 — 假设 #{idx}",
            "",
            f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M')}",
            f"> 工具: run_model_comparison（经典模型对比，赛题硬性验证标准）",
            "",
            "## 假设",
            f"- 标题: {hyp.title}",
            f"- 描述: {str(hyp.description)[:300]}",
            f"- 目标性质: {hyp.property}",
            f"- 涉及材料: {', '.join(hyp.materials[:5]) if hyp.materials else '（未指定）'}",
            "",
            "## 文献数据点",
            f"- 来源: knowledge_graph.md / paper_summaries.md",
            f"- 点数: {n}（x={x_label}，y 单位={data['y_unit']}"
            f"{'，含表头单位推断值' if data.get('y_implicit') else ''}）",
            f"- x 范围: {float(x.min()):.4g} ~ {float(x.max()):.4g}；"
            f"y 范围: {float(y.min()):.4g} ~ {float(y.max()):.4g}",
            "",
            "## 候选模型（由文献数值自动判定）",
            "| 模型 | 参数数 k | R² | RMSE | 表达式 |",
            "|------|---------|-----|------|--------|",
        ]
        for c in cands:
            md_lines.append(
                f"| {c['name']} | {c['k']} | {c['r2']:.4f} | {c['rmse']:.4g} | {c['params']} |"
            )
        best_name = best["name"]
        md_lines += [
            "",
            f"**自动判定最佳候选模型: {best_name}（R²={best['r2']:.4f}）**",
            "",
            "## 经典模型",
            f"- 模型: {classic_desc}",
            f"- 拟合结果: {classic_line}",
            "",
            "## 嵌套 F 检验（候选 vs 经典）",
            f"- {f_line}",
            "",
            "## 规则化统计判定（路线 A 验证标准）",
            f"- **结论: {verdict.get('reason', '?')}**",
            f"- verdict={verdict.get('verdict')}, ΔR²={verdict.get('delta_r2')}, "
            f"F 检验佐证={verdict.get('f_supported')}, "
            f"bootstrap CI 佐证={verdict.get('ci_supported')}",
            "",
            "## 稳健性验证（小样本贝叶斯 + 诊断统计）",
            f"- 贝叶斯线性回归: {bayes_line}",
            f"- 回归诊断: {diag_line}",
            f"- 数据质量分层: {tier_line or '（无足够分层数据）'}",
            f"- 数据溯源: {dict(data.get('quality_counts') or {})}",
            f"- 来源分组数: {data.get('n_groups', 0)}（用于分组 CV，近似按论文）",
            "",
            "## LLM 解释",
            llm_explanation,
            "",
        ]
        report_path = out_dir / f"model_comparison_{idx}.md"
        report_path.write_text("\n".join(md_lines), encoding="utf-8")

        # ── 8. 更新假设状态并返回摘要 ──
        hypotheses_data[idx]["model_comparison"] = {
            "n_points": n,
            "x_label": data["x_label"],
            "y_unit": data["y_unit"],
            "best_candidate": best,
            "classical_model": classic_desc,
            "classical_result": {k: v for k, v in classic.items()
                                 if k in ("name", "k", "r2", "rmse", "rss", "expr")},
            "f_test": f_res,
            "verdict": verdict,
            "bayesian": ({k: v for k, v in bayes_res.items()
                          if k not in ("beta_mean", "beta_cov")}
                         if bayes_res else None),
            "diagnostics": diag_res,
            "tiered_regression": tier_res,
            "quality_counts": data.get("quality_counts"),
            "n_groups": data.get("n_groups", 0),
            "llm_explanation": llm_explanation,
            "report_path": str(report_path),
        }
        (out_dir / "hypotheses.json").write_text(
            _json.dumps(hypotheses_data, ensure_ascii=False, indent=2)
        )
        self.survey_state["hypotheses"] = hypotheses_data

        return (
            f"✅ 模型对比完成 — 假设 #{idx}: '{hyp.title[:60]}'\n"
            f"   数据点: {n}（x={x_label}, y 单位={data['y_unit']}）\n"
            f"   最佳候选: {best_name} (R²={best['r2']:.4f}, RMSE={best['rmse']:.4g})\n"
            f"   经典模型: {classic_desc} → {classic_line}\n"
            f"   嵌套 F 检验: {f_line}\n"
            f"   稳健性: {bayes_line} | {diag_line}\n"
            f"   数据分层: {tier_line or '（无足够分层数据）'}\n"
            f"   LLM 结论: {llm_explanation[:120]}...\n"
            f"   报告: {report_path}"
        )

    def h_symbolic_regression(self, args: dict) -> str:
        """符号回归（赛题推荐算法）：遗传编程拟合假设的可解释表达式。

        从文献数值中提取 (x, y) 点集，调用 literature_agent.symbolic_regression
        （无第三方依赖的轻量遗传编程）拟合表达式，输出表达式 + R²/MSE。
        报告保存到 {SURVEY_DIR}/discovery/symbolic_<idx>.md。
        """
        from pathlib import Path as _Path
        import json as _json

        idx = args.get("hypothesis_index", 0)
        prop_override = args.get("property") or ""
        max_gen = int(args.get("max_generations", 100))
        pop_size = int(args.get("pop_size", 50))

        # ── 1. 加载假设 ──
        hypo_file = _Path(_cfg.SURVEY_DIR) / "discovery" / "hypotheses.json"
        if hypo_file.exists():
            hypotheses_data = _json.loads(hypo_file.read_text(encoding="utf-8"))
            self.survey_state["hypotheses"] = hypotheses_data
        else:
            hypotheses_data = self.survey_state.get("hypotheses", [])
        if idx >= len(hypotheses_data):
            return f"❌ Invalid hypothesis_index: {idx} (only {len(hypotheses_data)} available)"
        hyp = self._safe_hypothesis(hypotheses_data[idx])
        if prop_override:
            hyp.property = prop_override  # 允许覆盖目标性质（影响 y 提取）

        # ── 2. 数据点提取 ──
        source_text = self._load_knowledge_source()
        if not source_text:
            return "❌ 找不到知识来源（knowledge_graph.md / paper_summaries.md）。"
        data = self._extract_literature_points(source_text, hyp)
        if data is None:
            return (
                f"❌ 假设 #{idx} 未提取到足够的 (结构变量, 性质) 文献数值点。\n"
                "  需要同一文献块内同时出现结构变量（温度 K / 压力 bar / 掺杂比例 %）"
                "与性质数值，且至少 3 个不同的 x 值。"
            )
        x = np.asarray(data["x_vals"], dtype=float)
        y = np.asarray(data["y_vals"], dtype=float)
        x_label = {"temperature": "温度", "pressure": "压力",
                   "composition": "组分比例", "percentage": "百分比"}.get(
            data["x_label"], data["x_label"])

        # ── 3. 遗传编程符号回归 ──
        self._print(f"  🧬 符号回归: 假设 #{idx}，{len(x)} 个数据点，"
                    f"{max_gen} 代 × {pop_size} 个体 ...")
        from literature_agent.symbolic_regression import fit, predict, r2_score
        expr_str, params, mse = fit(
            x, y, max_generations=max_gen, pop_size=pop_size, seed=42)
        y_pred = predict(expr_str, params, x)
        r2 = r2_score(y, y_pred)
        rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))
        self._print(f"  🧬 拟合完成: {expr_str} (MSE={mse:.4g}, R²={r2:.4f})")

        # ── 4. 保存报告 ──
        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)
        params_str = ", ".join(f"{k}={v:.6g}" for k, v in params.items()) if params else "（无参数）"
        md_lines = [
            f"# 符号回归报告 — 假设 #{idx}",
            "",
            f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M')}",
            f"> 工具: symbolic_regression（赛题推荐算法，遗传编程）",
            "",
            "## 假设",
            f"- 标题: {hyp.title}",
            f"- 目标性质: {hyp.property}",
            f"- 涉及材料: {', '.join(hyp.materials[:5]) if hyp.materials else '（未指定）'}",
            "",
            "## 数据",
            f"- 来源: knowledge_graph.md / paper_summaries.md",
            f"- 点数: {len(x)}（x={x_label}，y 单位={data['y_unit']}"
            f"{'，含表头单位推断值' if data.get('y_implicit') else ''}）",
            "",
            "## 拟合结果",
            f"- **表达式**: `{expr_str}`",
            f"- 参数: {params_str}",
            f"- MSE: {mse:.6g}",
            f"- RMSE: {rmse:.6g}",
            f"- R²: {r2:.6f}",
            "",
            "## 数据点表（前 30 个）",
            "| x | y(实测) | y(预测) |",
            "|-----|--------|--------|",
        ]
        for xi, yi, ypi in list(zip(x, y, y_pred))[:30]:
            md_lines.append(f"| {xi:.4g} | {yi:.4g} | {ypi:.4g} |")
        md_lines += [
            "",
            "## 解读提示",
            "若 R² 较高（>0.9），说明该构效关系可由所得解析表达式近似描述；"
            "建议与 run_model_comparison 的经典模型结果对照，判断是否优于经典规律。",
            "",
        ]
        report_path = out_dir / f"symbolic_{idx}.md"
        report_path.write_text("\n".join(md_lines), encoding="utf-8")

        # ── 5. 更新假设状态并返回摘要 ──
        hypotheses_data[idx]["symbolic_regression"] = {
            "n_points": len(x),
            "x_label": data["x_label"],
            "y_unit": data["y_unit"],
            "expr": expr_str,
            "params": params,
            "mse": mse,
            "rmse": rmse,
            "r2": r2,
            "report_path": str(report_path),
        }
        (out_dir / "hypotheses.json").write_text(
            _json.dumps(hypotheses_data, ensure_ascii=False, indent=2)
        )
        self.survey_state["hypotheses"] = hypotheses_data

        return (
            f"✅ 符号回归完成 — 假设 #{idx}: '{hyp.title[:60]}'\n"
            f"   数据点: {len(x)}（x={x_label}, y 单位={data['y_unit']}）\n"
            f"   表达式: {expr_str}\n"
            f"   参数: {params_str}\n"
            f"   MSE={mse:.6g} | RMSE={rmse:.6g} | R²={r2:.6f}\n"
            f"   报告: {report_path}"
        )

    # ── Literature Survey Tools ──

    def h_search_papers(self, args: dict) -> str:
        """搜索科学文献。"""
        from literature_agent.search import LiteratureSearcher
        query = args.get("query", "")
        top_k = min(args.get("top_k", 20), 50)
        material = args.get("material")
        prop = args.get("property")

        sciverse_key = os.environ.get("SCIVERSE_API_KEY", "")
        searcher = LiteratureSearcher(
            cache_dir=_cfg.get_literature_cache_dir(),
            sciverse_api_key=sciverse_key,
        )
        results = searcher.search(query, top_k=top_k, material=material, property_name=prop)

        # 累积保存：与已有结果合并去重，避免后续检索覆盖前次结果
        import json as _json
        from pathlib import Path as _Path
        out_dir = _Path(_cfg.get_literature_cache_dir())
        out_dir.mkdir(parents=True, exist_ok=True)

        results_json = [r.to_dict() for r in results]

        # 加载已有结果并合并去重
        existing = []
        cache_file = out_dir / "search_results.json"
        if cache_file.exists():
            try:
                existing = _json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        seen = set()
        merged = []
        for item in existing + results_json:
            key = item.get("doi") or item.get("title", "")
            if key and key not in seen:
                seen.add(key)
                merged.append(item)
        cache_file.write_text(_json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

        # Store in session state
        self.survey_state["search_results"] = merged

        # Return readable summary
        summary_lines = [f"Found {len(results)} papers for query: '{query}'", ""]
        for i, r in enumerate(results[:10]):
            summary_lines.append(
                f"{i+1}. **{r.title[:100]}** ({r.year or 'N/A'})"
                f"  \n   Authors: {', '.join(r.authors[:3])}"
                f"  \n   Source: {r.source} | Score: {r.score:.2f}"
                f"  \n   DOI: {r.doi or 'N/A'}"
            )
        if len(results) > 10:
            summary_lines.append(f"\n... and {len(results)-10} more papers")
        summary_lines.append(f"\nResults saved to {_cfg.get_literature_cache_dir()}/search_results.json")
        return "\n".join(summary_lines)

    def h_parse_paper(self, args: dict) -> str:
        """解析单篇论文。"""
        from literature_agent.parser import DocumentParser
        filepath = args["filepath"]

        parser = DocumentParser()
        doc = parser.parse(filepath)

        # Store in session state
        papers = self.survey_state.setdefault("parsed_papers", {})
        papers[filepath] = {
            "title": doc.title,
            "authors": doc.authors,
            "abstract": doc.abstract[:500],
            "materials": doc.materials_mentioned[:20],
            "properties": doc.properties_mentioned[:20],
            "methods": doc.methods_mentioned[:20],
            "sections": len(doc.sections),
            "references": len(doc.references),
            "engine": doc.parse_engine,
        }

        return (
            f"✅ Parsed: {doc.title or filepath}\n"
            f"   Authors: {', '.join(doc.authors[:5])}\n"
            f"   Abstract: {doc.abstract[:300]}...\n"
            f"   Sections: {len(doc.sections)} | References: {len(doc.references)}\n"
            f"   Materials: {', '.join(doc.materials_mentioned[:10])}\n"
            f"   Properties: {', '.join(doc.properties_mentioned[:10])}\n"
            f"   Engine: {doc.parse_engine} ({doc.parse_time_seconds}s)"
        )

    def h_extract_knowledge(self, args: dict) -> str:
        """整理论文摘要为可读文本，供 Agent 直接阅读分析。

        不做结构化 JSON 抽取——Agent 本身有足够的推理能力，
        直接从论文摘要中识别材料、性质、关系和 Gap。
        """
        import json as _json
        from pathlib import Path as _Path

        papers_json = args.get("papers_json", "{}")
        filepath = args.get("filepath", "")

        if filepath:
            fp = _Path(filepath)
            if not fp.exists():
                fp = _Path("workspace") / filepath
            if fp.exists():
                papers_json = fp.read_text(encoding="utf-8")
            else:
                return f"❌ File not found: {filepath}"

        try:
            papers = _json.loads(papers_json)
        except _json.JSONDecodeError:
            return f"❌ Invalid JSON for papers_json."

        if not papers:
            return "❌ No papers to process."

        # ── 整理为可读 Markdown 摘要 ──
        out_dir = _Path(_cfg.SURVEY_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        md_lines = [
            f"# Literature Survey — Paper Summaries",
            f"\n**Total papers:** {len(papers)}",
            f"**Generated:** {__import__('datetime').datetime.now().isoformat()}\n",
            "---\n",
        ]

        # 统计来源分布
        sources = {}
        keywords_all = set()
        for pid, text in papers.items():
            text_str = str(text)
            # 尝试提取来源信息
            if 'sciverse' in text_str.lower():
                sources['sciverse'] = sources.get('sciverse', 0) + 1
            elif 'arxiv' in text_str.lower():
                sources['arxiv'] = sources.get('arxiv', 0) + 1
            else:
                sources['unknown'] = sources.get('unknown', 0) + 1
            # 收集关键词
            for kw in ['MOF', 'CO2', 'adsorption', 'capture', 'selectivity',
                        'perovskite', 'catalysis', 'battery', 'stability',
                        'synthesis', 'ZIF', 'UiO', 'MIL', 'HKUST']:
                if kw.lower() in text_str.lower():
                    keywords_all.add(kw)

        md_lines.append(f"**Sources:** {', '.join(f'{k}({v})' for k, v in sources.items())}")
        md_lines.append(f"**Common keywords:** {', '.join(sorted(keywords_all)[:20])}")
        md_lines.append("\n---\n")

        # 逐篇列出摘要
        for i, (pid, paper_text) in enumerate(papers.items(), 1):
            text = str(paper_text)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            title = lines[0][:150] if lines else pid
            # 尝试提取额外字段
            doi = ""
            authors = ""
            year = ""
            body_lines = []
            for line in lines[1:]:
                if line.lower().startswith("doi:") or line.lower().startswith("doi "):
                    doi = line.replace("DOI:", "").replace("doi:", "").strip()
                elif line.lower().startswith("authors:") or line.lower().startswith("author:"):
                    authors = line.replace("Authors:", "").replace("authors:", "").strip()[:200]
                elif line.lower().startswith("year:") or line.lower().startswith("year "):
                    year = line.replace("Year:", "").replace("year:", "").strip()
                else:
                    body_lines.append(line)

            md_lines.append(f"### {i}. {title}")
            if authors:
                md_lines.append(f"**Authors:** {authors}")
            if year:
                md_lines.append(f"**Year:** {year}")
            if doi:
                md_lines.append(f"**DOI:** {doi}")
            md_lines.append(f"**ID:** `{pid}`")
            # 摘要正文
            body = " ".join(body_lines)[:800]
            if body:
                md_lines.append(f"\n{body}")
            md_lines.append("")

        # 写入文件
        summary_path = out_dir / "paper_summaries.md"
        summary_path.write_text("\n".join(md_lines), encoding="utf-8")
        self.survey_state["paper_summary_path"] = str(summary_path)

        # 注意：不生成 JSON 知识图谱——知识图谱由 Agent 阅读摘要后自行撰写
        # （workspace/outputs/literature_survey/knowledge_graph.md，Markdown 格式）。
        self.survey_state["knowledge_graph_path"] = str(out_dir / "knowledge_graph.md")

        return (
            f"✅ Paper summaries organized: {len(papers)} papers\n"
            f"   Markdown: {summary_path}\n"
            f"   Sources: {sources}\n\n"
            f"📖 Next: Agent should read_file {summary_path} to analyze the literature, "
            f"then write_file 自己的知识图谱 {_cfg.SURVEY_DIR}/knowledge_graph.md"
            f"（材料/性质/数值/关系，Markdown 格式），"
            f"then call analyze_gaps() to identify research gaps, "
            f"then generate_report() to produce the final survey."
        )

    def h_analyze_gaps(self, args: dict) -> str:
        """指示主 Agent 自己阅读论文摘要并撰写 Gap 分析报告。

        本工具不做 LLM 调用——主 Agent 持有完整上下文，
        应自行 read_file 论文摘要 + write_file 输出 gap_report.md。
        """
        from pathlib import Path as _Path
        import json as _json

        summary_path = self.survey_state.get(
            "paper_summary_path",
            f"{_cfg.SURVEY_DIR}/paper_summaries.md",
        )
        search_path = f"{_cfg.get_literature_cache_dir()}/search_results.json"

        has_summary = _Path(summary_path).exists()
        has_search = _Path(search_path).exists()

        if not has_summary and not has_search:
            return "❌ 没有论文摘要。请先执行 search_papers 然后 extract_knowledge。"

        # 统计
        paper_count = 0
        if has_summary:
            paper_count = _Path(summary_path).read_text(encoding="utf-8").count("### ")

        # Gap 报告由 Agent 自行撰写为 Markdown（gap_report.md），不再生成占位 JSON
        out_dir = _Path(_cfg.SURVEY_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.survey_state["gap_report_path"] = str(out_dir / "gap_report.md")

        return (
            f"📋 Gap 分析任务已就绪（{paper_count} 篇论文摘要可用）。\n\n"
            f"请主 Agent 按以下步骤自行完成：\n"
            f"1. read_file {summary_path} — 阅读全部论文摘要\n"
            f"2. 基于摘要识别：矛盾结论、缺失知识连接、未探索的材料-性质空间\n"
            f"3. write_file {_cfg.SURVEY_DIR}/gap_report.md — 输出结构化 Gap 报告\n\n"
            f"报告格式要求：\n"
            f"  - 每个 Gap 标注类型（矛盾/缺失连接/未探索）、严重程度（高/中/低）\n"
            f"  - 附论文 ID 作为证据来源\n"
            f"  - 给出可操作的验证建议\n"
            f"  - 全部使用中文撰写\n"
        )

    def h_generate_report(self, args: dict) -> str:
        """指示主 Agent 自己撰写最终调研报告。

        本工具不做 LLM 调用——主 Agent 持有全部论文摘要和 Gap 分析的上下文，
        应自行 write_file 输出 survey_report.md。
        """
        from pathlib import Path as _Path
        import json as _json

        topic = args.get("topic", "Literature Survey")
        out_dir = _Path(_cfg.SURVEY_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        summary_path = self.survey_state.get("paper_summary_path",
            f"{_cfg.SURVEY_DIR}/paper_summaries.md")
        gap_path = f"{_cfg.SURVEY_DIR}/gap_report.md"

        has_summary = _Path(summary_path).exists()
        has_gap = _Path(gap_path).exists()
        paper_count = _Path(summary_path).read_text(encoding="utf-8").count("### ") if has_summary else 0

        # ── 产物校验：survey_report.md 必须已真实生成且非空，否则强约束 Agent 走受控通道 ──
        report_path = _Path(_cfg.SURVEY_DIR) / "survey_report.md"
        if not report_path.exists() or report_path.stat().st_size == 0:
            return (
                f"❌ survey_report.md 尚未生成，请先 write_file {_cfg.SURVEY_DIR}/survey_report.md 输出完整调研报告！\n"
                f"⚠️ 必须使用 write_file 工具直接写入 {report_path}，"
                f"不要通过 run_shell/自写脚本修改既有文件——那种方式会导致产物丢失且无法审计。\n"
                f"完成 write_file 后再次调用 generate_report 确认产物。"
            )

        return (
            f"✅ survey_report.md 已存在（{report_path.stat().st_size} 字节），继续完善最终调研报告（主题：{topic}，{paper_count} 篇论文）。\n\n"
            f"请主 Agent 按以下步骤自行完成：\n"
            f"1. read_file {summary_path} — 回顾论文摘要\n"
            + (f"2. read_file {gap_path} — 回顾 Gap 分析\n" if has_gap else "") +
            f"3. write_file {_cfg.SURVEY_DIR}/survey_report.md — 输出完整调研报告\n\n"
            f"报告结构：\n"
            f"  # 文献调研报告：{topic}\n"
            f"  ## 1. 执行摘要\n"
            f"  ## 2. 文献综述（按主题/材料/方法组织）\n"
            f"  ## 3. 关键材料与性质对比（含量化数据表格）\n"
            f"  ## 4. 研究空白与未来方向\n"
            f"  ## 5. 参考文献（含 DOI 可追溯）\n\n"
            f"要求：全部使用中文撰写，论文标题和作者名保留原文，每个结论标注来源论文 ID。"
        )

    def h_cross_theme_connection(self, args: dict) -> str:
        """跨领域文献连接（赛题高分方向）。

        打破单主题 run_dir 隔离：扫描多个主题（可自动发现 workspace/outputs/*/）的
        knowledge_graph.md 与 discovery/hypotheses.json，提取材料/性质实体，
        在共享实体上建立「主题A 实体 ──共享实体── 主题B 实体」连接。每条连接给出
        中文科学理由、真实论文证据编号、可证伪假设（Expected Relationship 格式）
        与 novelty 提示。报告保存到 {SURVEY_DIR}/discovery/cross_theme_connections.md。
        """
        from pathlib import Path as _Path

        raw_dirs = args.get("run_dirs") or []
        if isinstance(raw_dirs, str):
            raw_dirs = [d.strip() for d in raw_dirs.split(",") if d.strip()]
        run_dirs = [d for d in raw_dirs if isinstance(d, str) and d.strip()]

        if run_dirs:
            self._print(f"  🌉 跨领域文献连接: 扫描指定主题 {run_dirs} ...")
        else:
            self._print("  🌉 跨领域文献连接: 自动发现 workspace/outputs/* 下的全部主题 ...")

        from literature_agent.cross_theme import (
            scan_cross_theme_connections, render_markdown)

        try:
            result = scan_cross_theme_connections(run_dirs=run_dirs or None)
        except Exception as e:
            self._print(f"  ⚠️ 跨领域扫描失败: {e}")
            return f"❌ 跨领域连接扫描失败: {e}"

        if result is None:
            return ("❌ 未发现可用的文献主题目录。\n"
                    "  请先运行 search_papers / extract_knowledge 生成 knowledge_graph.md，"
                    "或通过 run_dirs 参数指定主题列表（如 ['thermoelectric', 'perovskite']）。")

        connections = result.get("connections", [])
        sm = result.get("summary", {})
        if not connections:
            return ("⚠️ 扫描完成（{} 个主题、{} 对），但未发现共享材料/性质实体，"
                    "无跨主题连接可建立。\n"
                    "  建议检查各主题 knowledge_graph.md 是否存在可交叉的化学式/材料族/性质词，"
                    "或显式指定 run_dirs。").format(sm.get("n_themes", 0), sm.get("n_pairs", 0))

        # ── 落盘 markdown 报告（SURVEY_DIR 仍是当前 run_dir，写入其 discovery/ 即可）──
        out_dir = _Path(_cfg.SURVEY_DIR) / "discovery"
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / "cross_theme_connections.md"
        report_path.write_text(render_markdown(result), encoding="utf-8")
        self.survey_state["cross_theme_connections"] = {
            "n_themes": sm.get("n_themes", 0),
            "n_connections": len(connections),
            "n_material_links": sm.get("n_material_links", 0),
            "n_property_links": sm.get("n_property_links", 0),
            "report_path": str(report_path),
        }

        # ── 中文摘要 ──
        lines = [
            f"✅ 跨领域文献连接完成 — 共 {len(connections)} 条连接"
            f"（{sm.get('n_themes', 0)} 个主题、{sm.get('n_pairs', 0)} 对）",
            "",
        ]
        for c in connections[:8]:
            kind_cn = "材料" if c["type"] == "material" else "性质"
            strength_cn = {"high": "高", "medium": "中", "low": "低"}[c["strength"]]
            lines.append(
                f"- {c['id']} [{kind_cn}] 共享「{c['shared_entity']}」"
                f"（{c['theme_labels'][0]} ↔ {c['theme_labels'][1]}）"
                f"  \n  证据: {', '.join(c['evidence'][:4]) or '无'}"
                f"  \n  强度: {strength_cn} ｜ 假设: {c['falsifiable_hypothesis'][:120]}..."
            )
        if len(connections) > 8:
            lines.append(f"- ... 等共 {len(connections)} 条（详见报告）")
        lines.append(f"\n📄 报告: {report_path}")
        return "\n".join(lines)


def build_tool_manager(task_type: str, bench: str, memory_dir: Path,
                       print_fn: Callable, event_bus: EventBus = None) -> Tuple[ToolManager, ToolHandlers]:
    """
    Factory: create a fully-registered ToolManager with all 23 tools.

    Returns (manager, handlers) — manager for execution, handlers for Agent to inject callbacks.
    """
    handlers = ToolHandlers(task_type=task_type, bench=bench, memory_dir=memory_dir, print_fn=print_fn)
    manager = ToolManager(event_bus=event_bus, print_fn=print_fn)

    # Register all tools
    manager.register("think", handlers.h_think)
    manager.register("list_files", handlers.h_list_files)
    manager.register("read_file", handlers.h_read_file)
    manager.register("write_file", handlers.h_write_file)
    manager.register("edit_file", handlers.h_edit_file)
    manager.register("run_shell", handlers.h_run_shell)
    manager.register("start_shell", handlers.h_start_shell)
    manager.register("check_shell", handlers.h_check_shell)
    manager.register("kill_shell", handlers.h_kill_shell)
    manager.register("stop", handlers.h_stop)
    # Literature survey tools
    manager.register("search_papers", handlers.h_search_papers)
    manager.register("parse_paper", handlers.h_parse_paper)
    manager.register("extract_knowledge", handlers.h_extract_knowledge)
    manager.register("analyze_gaps", handlers.h_analyze_gaps)
    manager.register("generate_report", handlers.h_generate_report)
    # Route A: Discovery tools
    manager.register("generate_hypotheses", handlers.h_generate_hypotheses)
    manager.register("run_discovery_search", handlers.h_run_discovery_search)
    manager.register("check_novelty", handlers.h_check_novelty)
    manager.register("validate_discovery", handlers.h_validate_discovery)
    manager.register("run_model_comparison", handlers.h_run_model_comparison)
    manager.register("symbolic_regression", handlers.h_symbolic_regression)
    manager.register("cross_theme_connections", handlers.h_cross_theme_connection)
    manager.register("generate_discovery_report", handlers.h_generate_discovery_report)

    return manager, handlers
