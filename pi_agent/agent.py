"""
Pi-Agent 核心 — 自主文献调研 Agent 主循环
==========================================
基于 ReAct 模式（Think → Act → Observe）的自动化文献调研系统。

架构层次：
  Layer 1: LLMClient — DeepSeek API 调用抽象
  Layer 2: PiAgent  — 事件驱动 + 状态机 + 工具管线 + 会话持久化 + 上下文压缩

Agent 在预算内自主完成四阶段流程：
  阶段1: 文献检索（多源并发搜索 + 相关性筛选）
  阶段2: 知识抽取（正则快提 → LLM 精提 → 知识图谱融合）
  阶段3: Gap 分析（矛盾检测 / 缺失连接 / 未探索空间 / 新颖性评分）
  阶段4: 报告生成（结构化 Markdown + JSON + 证据链）

每轮循环：LLM 分析局势 → 决定行动 → 执行工具 → 观察结果 → 更新记忆 → 进入下一轮
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

from pi_agent.events import (
    Event, EventBus,
    EVENT_AGENT_START, EVENT_AGENT_END,
    EVENT_TURN_START, EVENT_TURN_END,
    EVENT_TOOL_START, EVENT_TOOL_END,
    make_logging_listener,
)
from pi_agent.llm import LLMClient
from pi_agent.state_machine import StateMachine, AgentState
from pi_agent.session import SessionManager
from pi_agent.context import compress_messages
from pi_agent.config import CONTEXT_COMPRESSION_THRESHOLD  # 压缩阈值（字符），统一来自 pi_agent/config.py
from pi_agent.tools import build_tool_manager
from pi_agent.memory_quality import audit_memory_file, format_audit_report

# 多主题运行目录（由 main.py --run-dir 设置，默认 survey 兼容历史路径）
import utils.config as _cfg
from utils.budget_tracker import BudgetTracker


def dedupe_markdown_sections(text: str) -> str:
    """对 Markdown 文档做段落级去重（幂等，可复用）。

    背景：Agent 收尾时常反复 write_file（或 append 模式）写入完整 MEMORY.md，
    容易把同一段落（如“定量验证结果”）连续粘贴多份，导致记忆索引膨胀失真。
    此函数按 Markdown 小节段落去重，供记忆写入路径调用。

    规则：
      - 以 `# ~ ######` 标题行为段落边界，标题行连同其后的内容块视为一个段落；
      - 段落唯一键 = 归一化后的标题文本（小写、去空白）；无标题的游离文本块
        以整块归一化结果作为键；
      - 相同键的段落只保留最后一次出现（内容以最新为准，即“更新而非追加”）；
      - 归一化 = 逐行去掉首尾空白、丢弃空行、统一换行符。
    若文档没有重复段落则原样返回（不产生任何改动），保证幂等。
    """
    if not text:
        return text
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # ── 按标题行拆分段落块 ──
    blocks: List = []            # (kind, key, block_lines)   kind: "head" | "body"
    cur_kind = None
    cur_key = ""
    cur_lines: List[str] = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            if cur_lines:
                blocks.append((cur_kind, cur_key, cur_lines))
            heading = (m.group(1) + " " + m.group(2)).strip()
            cur_kind = "head"
            cur_key = heading.lower()
            cur_lines = [line]
        else:
            if cur_kind is None:
                cur_kind = "body"
                cur_key = ""
            cur_lines.append(line)
    if cur_lines:
        blocks.append((cur_kind, cur_key, cur_lines))

    def _norm(block_lines: List[str]) -> str:
        return "\n".join(l.strip() for l in block_lines if l.strip()).strip().lower()

    # ── 计算每个块的唯一键 ──
    keyed: List = []
    for kind, key, block_lines in blocks:
        if kind == "head":
            k = key
        else:
            k = _norm(block_lines)
            if not k:
                continue  # 空块直接丢弃
        keyed.append((k, block_lines))

    # ── 相同键只保留最后一次出现 ──
    last_idx: Dict[str, int] = {}
    for i, (k, _) in enumerate(keyed):
        last_idx[k] = i

    dropped = 0
    kept_blocks: List[List[str]] = []
    for i, (k, block_lines) in enumerate(keyed):
        if last_idx.get(k) == i:
            kept_blocks.append(block_lines)
        else:
            dropped += 1
    if dropped == 0:
        return text  # 无重复，原样返回

    rebuilt = "\n".join("\n".join(b) for b in kept_blocks).strip()
    if rebuilt:
        rebuilt += "\n"
    return rebuilt


# ═══════════════════════════════════════════════════════════
# 预算追踪：支持中断恢复的累计消耗语义
# ═══════════════════════════════════════════════════════════

# 预算耗尽后仍允许执行的"轻量收尾"工具白名单：
# 放行不启动新探索的纯收尾操作：写记忆 / 读文件 / 停止 / 思考，
# 以及一次性报告生成（generate_discovery_report 产出路线 A 发现报告——
# 必交提交物，且在预算耗尽前通常已完成搜索，仅缺报告落盘）。
# 搜索 / 验证 / 建模 / 符号回归 / shell 等一律拦截——
# 历史实测这些工具单次可耗时 16~68s（validate_discovery≈40s、
# run_model_comparison≈16s、symbolic_regression≈20s），若在耗尽后
# 继续放行会累计突破时间预算（600s 预算实测超支 40s 的根源）。
_WRAPUP_LIGHT_TOOLS = {
    "stop", "write_file", "edit_file", "read_file", "think",
    "generate_discovery_report",  # 发现报告：一次性收尾产物，放行
    "generate_report",            # 仅返回指引文本，不耗时，放行
}

# 兼容别名：旧白名单 `_WRAPUP_ALLOWED_TOOLS`（曾把 run_discovery_search /
# validate_discovery / generate_*_report 等重量级收尾工具一并放行，是本次
# 预算超支 40s 的直接根源）已废弃；保留此名称仅供
# scripts/budget_resume_test/test_budget_resume.py 等历史脚本 import 不中断，
# 语义指向新的轻量放行集合。新逻辑一律以 _WRAPUP_LIGHT_TOOLS /
# _WRAPUP_HEAVY_TOOLS 为准。
_WRAPUP_ALLOWED_TOOLS = _WRAPUP_LIGHT_TOOLS

# 预算耗尽后必须拒绝的"重量级新任务"：禁止启动任何新的
# 搜索 / 验证 / 模型对比 / 符号回归 / 假设生成 / shell 等耗时操作。
# （若这些工具在预算耗尽前已启动并正在执行则无法中断——设计边界，
#  这里只阻止新的启动。）
_WRAPUP_HEAVY_TOOLS = {
    "search_papers", "run_discovery_search", "validate_discovery",
    "run_model_comparison", "symbolic_regression", "generate_hypotheses",
    "start_shell", "run_shell", "parse_paper",
}


def _budget_wrapup_hook_impl(tracker: BudgetTracker, tool_name: str) -> Optional[str]:
    """预算耗尽后的强制收尾拦截逻辑（纯函数，便于单测）。

    当预算已耗尽（含安全余量）时：
      - 轻量收尾工具（write_file / read_file / edit_file / stop / think）放行；
      - 其余工具一律拒绝并返回提示消息，其中重量级新任务（搜索 / 验证 /
        模型对比 / 符号回归 / 报告生成 / shell 等）给出明确说明，
        防止 Agent 在收尾阶段继续启动耗时操作而突破预算。
    返回 None 表示放行。
    """
    if not tracker.must_stop_now():
        return None
    if tool_name in _WRAPUP_LIGHT_TOOLS:
        return None
    if tool_name in _WRAPUP_HEAVY_TOOLS:
        return (
            f"⛔ 预算已耗尽（已用 {tracker.elapsed():.0f}s / 总计 {tracker.total_budget}s），"
            f"工具 `{tool_name}` 属于搜索/验证/建模/报告等重量级任务，已被拦截。"
            f"预算耗尽后不得启动新的搜索（search_papers / run_discovery_search）、"
            f"验证（validate_discovery）、模型对比（run_model_comparison）、"
            f"符号回归（symbolic_regression）或报告生成，"
            f"只允许轻量收尾：write_file / read_file / edit_file / stop。"
            f"请立即写入记忆、整理已有结果，然后调用 stop。"
        )
    return (
        f"⛔ 预算已耗尽（已用 {tracker.elapsed():.0f}s / 总计 {tracker.total_budget}s），"
        f"工具 `{tool_name}` 不属于收尾白名单，已被拦截。"
        f"只允许 write_file / read_file / edit_file / stop（及 think）完成收尾，"
        f"请立即写入记忆、整理已有结果，然后调用 stop。"
    )


class _ResumableBudgetTracker(BudgetTracker):
    """支持从 checkpoint 恢复的预算追踪器。

    原 BudgetTracker.elapsed() 只统计自 start() 起的墙钟时间，无法表达
    「恢复前已消耗的时间」。旧实现用 `start_time -= budget_elapsed` 回拨
    时钟，语义混乱且易与暂停 / 多次恢复叠加出错。

    本子类新增 `accrued`（恢复前已累计消耗的秒数）：
      elapsed()   = accrued + 本次进程自 start() 起的墙钟时间
      remaining() = total_budget - elapsed()          （继承后自动生效）
    于是恢复后 remaining = total_budget - budget_elapsed —— 已用时间从
    预算中正确扣减，而非回拨 start_time 造成累计超支。默认（无 checkpoint）
    时 accrued=0，行为与原 BudgetTracker 完全一致。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accrued: float = 0.0  # 恢复前已消耗秒数（checkpoint budget_elapsed）

    def set_accrued(self, elapsed: float) -> None:
        """注入恢复前已消耗的时间（来自 checkpoint 的 budget_elapsed）。"""
        try:
            self.accrued = max(0.0, float(elapsed or 0.0))
        except (TypeError, ValueError):
            self.accrued = 0.0

    def elapsed(self) -> float:
        """累计已消耗时间 = 恢复前已消耗 + 本次运行墙钟时间。"""
        return self.accrued + super().elapsed()

    def budget_used_pct(self) -> float:
        """已用预算百分比（含恢复前累计），避免小预算下除零。"""
        if self.total_budget <= 0:
            return 0.0
        return self.elapsed() / self.total_budget * 100


class PiAgent:
    """自主机器学习实验 Agent。

    核心设计：
      - 事件驱动：所有关键生命周期节点发出事件，便于日志记录和扩展
      - 状态机：RUNNING → TOOL_EXECUTING → RUNNING → ... → DONE，含状态钩子
      - 工具管线：define → register → intercept → execute → recycle
      - 会话管理：保存/恢复完整对话状态，支持中断后恢复
      - 上下文压缩：长对话自动压缩，保持在 LLM 上下文窗口内
      - 预算追踪：实时监控时间消耗，到期自动提醒收尾
    """

    def __init__(self, output_dir: str = "workspace/outputs/",
                 budget: int = None, fresh_start: bool = False,
                 research_topic: str = ""):
        """初始化文献调研 Agent。

        参数:
            output_dir: 输出根目录
            budget: 时间预算（秒），默认从配置读取 7200（2小时）
            fresh_start: True 则删除已有 checkpoint，强制从头开始
            research_topic: 文献调研主题
        """
        self.task_type = "survey"
        self.output_dir = output_dir
        self.bench = "A"  # 保持兼容
        self._stop_requested = False
        self.research_topic = research_topic

        # ── 时间预算追踪（支持中断恢复的累计消耗语义） ──
        from utils.config import TOTAL_BUDGET_SECONDS, SAFETY_MARGIN_SECONDS
        if budget is not None:
            self.budget = _ResumableBudgetTracker(total_budget=budget, safety_margin=SAFETY_MARGIN_SECONDS)
        else:
            self.budget = _ResumableBudgetTracker(total_budget=TOTAL_BUDGET_SECONDS, safety_margin=SAFETY_MARGIN_SECONDS)

        # ── 事件总线：解耦各模块通信 ──
        self.events = EventBus()
        self.events.on_any(make_logging_listener(self._print))

        # ── 状态机：管理 Agent 生命周期状态 ──
        self.state_machine = StateMachine()
        self._setup_state_hooks()

        # ── LLM 客户端：通过 DeepSeek API 进行推理决策 ──
        self.llm = LLMClient(print_fn=self._print)

        # ── 会话管理：支持中断恢复（checkpoint，按 run_dir 隔离） ──
        self.session = SessionManager("survey", checkpoint_dir=_cfg.CHECKPOINT_DIR)

        # ── 调研记忆：记录每次调研的发现、Gap、分析（按 run_dir 隔离） ──
        self._memory_dir = Path(_cfg.MEMORY_DIR)
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._memory_index = self._memory_dir / "MEMORY.md"
        self._protect_memory_index()

        # ── 工具管线：Agent 可调用的所有工具（读写文件、启停脚本等） ──
        self._tool_manager, self._tool_handlers = build_tool_manager(
            task_type="survey", bench="A", memory_dir=self._memory_dir,
            print_fn=self._print, event_bus=self.events,
        )
        self._tool_handlers._on_stop = self._handle_stop
        self._tool_handlers._on_think = self._handle_think

        # ── 记忆索引写入保护：任何工具写 MEMORY.md 后立即段落级去重（幂等） ──
        # 防止 Agent 反复 write_file/append 把同一段落连续粘贴多份，索引膨胀失真
        self._tool_manager.add_after_hook(self._memory_index_dedup_hook)

        # ── 预算强制收尾：预算耗尽后拦截"继续探索"类工具，只放行收尾操作 ──
        # 防止 Agent 在剩余 0s 后仍启动新的搜索 / 长脚本，导致累计超支
        self._tool_manager.add_before_hook(self._budget_wrapup_hook)

        # ── 清理上次运行的临时文件（仅 fresh 启动）──
        # 恢复（非 fresh）时保留 workspace/code/iteration_*.py：
        # 对话历史可能引用上轮脚本（read_file 追溯），恢复时删除会断链。
        if fresh_start:
            self._cleanup_workspace()

        if fresh_start:
            self.session.delete()
            # 清理上次运行的 checkpoint 文件（仅当前 run_dir），避免 Agent 产生困惑。
            # 注意：只删 checkpoint_*.json，不删 trajectory_*.json——运行轨迹是
            # 证据链审计的核心（赛题红线 1），必须保留以便评审追溯检索/推理/决策
            # 过程（2026-10 修复：此前 --fresh 会一并删除轨迹导致证据链底层断裂）。
            # 局限说明：同 run_dir 连续多次完整运行结束时 _save_trajectory 会
            # 同名覆盖旧轨迹（trajectory_<run_dir>.json）；如需多轮轨迹并存，
            # 应在运行前手动归档旧轨迹文件。
            import glob as _g2
            for stale in _g2.glob(os.path.join(_cfg.CHECKPOINT_DIR, "checkpoint_*.json")):
                try: os.remove(stale)
                except OSError: pass

        # ── 核心运行时状态 ──
        self._user_goal = ""               # 用户目标描述
        self._compression_summary = ""     # 上下文压缩后的摘要
        self._last_experiment_done = False # 上一轮训练是否刚完成（触发反思）
        self._last_agent_thinking = ""     # Agent 最近一次的思考内容
        self._messages: List[Dict] = []    # LLM 对话历史
        self._trajectory: List[Dict] = []  # 实验轨迹日志
        self._experiments_completed = 0    # 已完成阶段计数
        if self._memory_dir.exists():
            self._experiments_completed = len(list(self._memory_dir.glob("survey-*.md")))

    # ═══════════════════════════════════════════════════════════
    # 初始化辅助方法
    # ═══════════════════════════════════════════════════════════

    def _setup_state_hooks(self):
        """在状态转移上挂载钩子函数。"""

        def _on_enter_running():
            pass

        def _on_enter_tool_executing():
            pass

        def _on_enter_done():
            self._print(f"\n🏁 Agent entering DONE state — finalizing...")

        self.state_machine.on_enter(AgentState.RUNNING, _on_enter_running)
        self.state_machine.on_enter(AgentState.TOOL_EXECUTING, _on_enter_tool_executing)
        self.state_machine.on_enter(AgentState.DONE, _on_enter_done)

    def _protect_memory_index(self):
        """MEMORY.md 损坏时从备份恢复。防止索引丢失导致历史实验无法读取。"""
        bak_path = self._memory_dir / "MEMORY.md.bak"
        if not self._memory_index.exists() or self._memory_index.stat().st_size < 50:
            if bak_path.exists() and bak_path.stat().st_size > 100:
                import shutil
                shutil.copy2(str(bak_path), str(self._memory_index))
                self._print(f"  🛡️ MEMORY.md restored from backup ({bak_path.stat().st_size} bytes)")
            elif not self._memory_index.exists():
                self._memory_index.write_text(f"# Agent Experiment Memory — {self.task_type}\n\n", encoding="utf-8")

    def _memory_index_dedup_hook(self, tool_name: str, args: dict, result_str: str) -> str:
        """MEMORY.md 写入后的段落级去重钩子（挂在工具管线 after-hook 上）。

        Agent 收尾时常反复 write_file（或 append 模式）写入完整 MEMORY.md，
        容易把同一段落连续粘贴多份，导致记忆索引膨胀失真。本钩子在每次
        明确写入 MEMORY.md 的工具执行完成后，立即对索引做幂等去重，防止
        重复段落跨轮累积。只对指向 MEMORY.md 的写入路径触发，不会主动
        改动历史产物文件。

        去重之后追加记忆质量审计（_audit_memory_quality）：发现低质量
        条目（无数值/来源/明确结论等表面化摘要）时向 Agent 返回警告，
        并归档报告到 memory_quality.md。审计为增强功能，任何失败都不
        影响原有的去重与写入流程。
        """
        try:
            # ── 判定本次工具调用是否写到了 MEMORY.md ──
            target = ""
            if tool_name in ("write_file", "edit_file"):
                target = str(args.get("filepath") or args.get("file_path") or "")
            elif tool_name in ("run_shell", "start_shell"):
                cmd = str(args.get("command") or "")
                if "memory.md" in cmd.lower():
                    target = "MEMORY.md"
            if not target or "memory.md" not in target.lower():
                return result_str
            if not self._memory_index.exists():
                return result_str

            old = self._memory_index.read_text(encoding="utf-8")
            new = dedupe_markdown_sections(old)
            suffix = ""
            if new != old:
                self._memory_index.write_text(new, encoding="utf-8")
                # 同步 .bak 备份，避免将来索引损坏从备份恢复时又带回重复段落
                bak_path = self._memory_dir / "MEMORY.md.bak"
                if bak_path.exists():
                    bak_path.write_text(new, encoding="utf-8")

                removed = len(old.split("\n")) - len(new.split("\n"))
                self._print(f"  🧹 MEMORY.md 段落去重：移除重复内容 {removed} 行（幂等保护）")
                suffix += f"\n\n🧹 MEMORY.md 已自动段落去重，移除重复内容 {removed} 行（幂等保护）。"

                # ── 记忆质量审计（增强，非硬依赖；失败不影响去重与写入） ──
                # 仅在实际更新 MEMORY.md 时审计，避免无变化重写触发重复报告
                suffix += self._audit_memory_quality()
            return result_str + suffix
        except Exception as e:
            self._print(f"  ⚠️ MEMORY.md dedup hook failed: {e}")
            return result_str

    def _audit_memory_quality(self) -> str:
        """对 MEMORY.md 做质量审计（增强功能，失败不影响主流程）。

        读取去重后的 MEMORY.md，按小节评分；若存在低质量条目
        （score < 0.35 或命中 placeholder 等严重 flag），向 Agent 返回
        一段追加警告，并把审计报告追加归档到 memory_dir/memory_quality.md
        （带时间戳）。只审计+报告，不自动删改 Agent 写的记忆。
        任何异常仅打印日志并返回空串，绝不影响原有写入流程。
        """
        try:
            if not self._memory_index.exists():
                return ""
            md_text = self._memory_index.read_text(encoding="utf-8")
            audit = audit_memory_file(md_text)
            if not audit.get("low_quality"):
                return ""

            low = audit["low_quality"]
            heads = "、".join(e["heading"] for e in low[:5])
            if len(low) > 5:
                heads += " 等"
            warning = (
                f"\n\n⚠️ 记忆质量审计：发现 {len(low)} 条低质量条目"
                f"（{heads}），建议补充数值证据/来源/明确结论"
                f"（详见 {self._memory_dir / 'memory_quality.md'}）。"
            )

            # 归档审计报告：追加模式 + 时间戳
            qa_file = self._memory_dir / "memory_quality.md"
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            entry = (
                f"\n\n---\n\n## 审计时间：{timestamp}\n\n"
                f"{format_audit_report(audit)}"
            )
            with open(qa_file, "a", encoding="utf-8") as f:
                f.write(entry)

            self._print(
                f"  📋 MEMORY.md 质量审计：发现 {len(low)} 条低质量条目"
                f"（平均分 {audit.get('avg_score', 0.0):.2f}）→ {qa_file.name}"
            )
            return warning
        except Exception as e:
            self._print(f"  ⚠️ MEMORY.md quality audit failed: {e}")
            return ""

    def _cleanup_workspace(self):
        """清理上次运行残留的临时文件和迭代脚本。"""
        import glob as _g
        import shutil
        for f in _g.glob("workspace/code/iteration_*.py"):
            try: os.remove(f)
            except OSError: pass
        tmp_dir = Path("workspace/outputs/.tmp")
        if tmp_dir.exists():
            try: shutil.rmtree(tmp_dir)
            except OSError: pass
            tmp_dir.mkdir(parents=True, exist_ok=True)

    def _budget_wrapup_hook(self, tool_name: str, args: dict) -> Optional[str]:
        """预算耗尽后的强制收尾 before-hook（挂在工具管线上）。

        预算耗尽（must_stop_now，含安全余量）后：
          - 轻量收尾工具（write_file / read_file / edit_file / stop / think）放行；
          - 搜索 / 验证 / 模型对比 / 符号回归 / 报告生成 / shell 等重量级
            任务一律拒绝，防止收尾阶段再启动耗时操作（历史实测单个此类
            工具即可耗 16~68s）导致实际用时突破预算。
        """
        return _budget_wrapup_hook_impl(self.budget, tool_name)

    def _inject_final_warning(self) -> None:
        """向对话注入预算耗尽的收尾指令（user 消息），提醒 Agent 剩余不足。

        与 must_stop_now 检查配合：循环顶部与每次 LLM 调用返回后调用，
        保证恢复场景下 Agent 能及时收到"剩余不足、必须收尾"的提示。
        """
        self._messages.append({
            "role": "user",
            "content": (
                f"⏰ 预算已耗尽（已用 {self.budget.elapsed():.0f}s / 总计 {self.budget.total_budget}s，"
                f"剩余 {self.budget.remaining():.0f}s）。收尾阶段已启动，请严格遵守：\n"
                f"- 只允许轻量收尾工具：write_file / read_file / edit_file / stop（及 think）。\n"
                f"- 不得启动任何新的搜索（search_papers / run_discovery_search）、"
                f"验证（validate_discovery）、模型对比（run_model_comparison）、"
                f"符号回归（symbolic_regression）或报告生成（generate_report / "
                f"generate_discovery_report）任务——这些重量级工具已被拦截，"
                f"即使已有结果需要验证/对比也只能放弃，预算不允许。\n"
                f"请立即完成收尾：\n"
                f"1) 将已有调研发现整理写入 {_cfg.SURVEY_DIR}/（直接 write_file 落盘，"
                f"不要再调用生成报告工具）\n"
                f"2) write_file 记忆到 {_cfg.MEMORY_DIR}/ 并更新 MEMORY.md\n"
                f"3) 调用 stop 工具结束本次调研\n"
            )
        })

    def _handle_stop(self):
        """Agent 调用 stop 工具时触发：标记停止请求。"""
        self._stop_requested = True

    def _handle_think(self, topic: str) -> str:
        """Agent 调用 think 工具时触发：做一次纯文本深度推理。

        复用当前对话上下文，但不产生 tool call，让 LLM 对特定话题做深入分析。
        """
        think_msg = {
            "role": "user",
            "content": (
                f"[深度思考]\n"
                f"主题：{topic}\n\n"
                f"请深入分析当前局势。考虑以下方面：\n"
                f"- 现有结果告诉我们什么？\n"
                f"- 可以形成什么假设？底层机制是什么？\n"
                f"- 存在哪些风险和替代方案？\n\n"
                f"进行透彻分析，然后给出明确的下一步建议及其理由。"
            )
        }
        # 构建纯文本消息列表（去掉 tool_calls 和对应的 tool 响应）
        # DeepSeek API 要求：role=tool 的消息必须前面有带 tool_calls 的 assistant 消息
        # 纯文本推理模式下必须同时去掉两者
        clean = []
        for m in self._messages:
            role = m.get("role", "")
            if role == "tool":
                # 跳过：tool 响应依赖 tool_calls，纯文本模式不需要
                continue
            elif "tool_calls" in m:
                # 保留 assistant 的思考内容，去掉 tool_calls 元数据
                clean.append({k: v for k, v in m.items() if k != "tool_calls"})
            else:
                clean.append(m)
        messages = clean + [think_msg]
        result = self.llm.think(messages, max_tokens=1200)
        self._print(f"     💭 {result[:300]}...")
        return result

    # ═══════════════════════════════════════════════════════════
    # 系统提示词构建
    # ═══════════════════════════════════════════════════════════

    def _build_system_prompt(self) -> str:
        """构建系统提示词（多主题：按当前 run_dir 动态改写路径）。"""
        from pi_agent.prompts import build_survey_system_prompt
        return build_survey_system_prompt()

    # ═══════════════════════════════════════════════════════════
    # 主循环 — ReAct 模式 (Think → Act → Observe)
    # ═══════════════════════════════════════════════════════════

    def run(self) -> Dict:
        """启动自主文献调研循环。

        ReAct 模式流程：
          1. LLM 思考（Think）：分析当前状态 → 决定下一步行动
          2. 执行工具（Act）：运行检索/抽取脚本、读写文件、监控进程
          3. 观察结果（Observe）：读取脚本输出 → 更新调研记忆
          4. 循环直到预算耗尽或 Agent 主动停止

        每轮记录写入 trajectory log，供评审核查调研过程。
        """
        self.budget.start()
        self.events.emit(Event(EVENT_AGENT_START, {"task": self.task_type, "bench": self.bench}))

        self._print(f"\n{'='*60}")
        self._print(f"🔬 Pi-Agent: {self.task_type}")
        self._print(f"{'='*60}")
        self._print(f"  Budget: {self.budget.total_budget}s | "
                    f"Model: {self.llm._active_provider.model} ({self.llm.active_provider_name})")
        self._print(f"  Architecture: Pi-Agent (event-driven + state machine + tool pipeline)")
        self._print(f"{'='*60}")

        # ── 加载 checkpoint 或全新开始 ──
        start_iter = 0
        if self.session.exists():
            ckpt = self.session.load()
            if ckpt:
                self._print(f"  🔄 Resuming from checkpoint: iter={ckpt['iteration']}")
                start_iter = ckpt["iteration"]
                self._compression_summary = ckpt.get("summary", "")
                # 恢复前已用时间从预算中正确扣减（剩余 = 总预算 - budget_elapsed），
                # 而非回拨 start_time 造成 wall-clock 累计语义混乱 / 累计超支
                self.budget.set_accrued(ckpt.get("budget_elapsed", 0))
                self._messages = ckpt.get("messages", [])
                self._trajectory = ckpt.get("trajectory", [])
                self._experiments_completed = ckpt.get("experiments_completed", 0)
                self._print(f"      Restored {len(self._messages)} messages, {len(self._trajectory)} trajectory entries | "
                            f"已用 {self.budget.elapsed():.0f}s / 总计 {self.budget.total_budget}s，剩余 {self.budget.remaining():.0f}s")

        # ── 构建初始消息 ──
        if start_iter == 0:
            self._user_goal = (
                f"调研主题：{self.research_topic}。\n"
                f"📖 第零步（每次运行必须先执行！）：\n"
                f"1) read_file {_cfg.MEMORY_DIR}/MEMORY.md — 检查是否有历史调研记录\n"
                f"2) read_file workspace/feedback/survey.md — 检查评审反馈（如有）\n"
                f"3) list_files {_cfg.get_literature_cache_dir()}/ — 查找缓存的论文和搜索日志\n"
                f"4) list_files workspace/code/survey/ — 查找已有的搜索/抽取脚本\n"
                f"⚠️ 如果 MEMORY.md 已有调研记录：从已知的最佳知识图谱开始继续。\n"
                f"⚠️ 如果是首次调研（空记忆）：执行完整的四阶段流程。\n"
                f"所有搜索/抽取脚本由你编写（write_file）并通过 start_shell 执行。\n"
                f"使用 literature_agent 包中的 search / parser / extractor / gap_analyzer / report_generator 模块。\n"
                f"收尾前，将记忆写入 {_cfg.MEMORY_DIR}/ 并更新 MEMORY.md。\n"
                f"所有思考和输出请使用中文。\n"
            )
            start_iter = 1

        if not self._messages:
            system_prompt = self._build_system_prompt()
            # 提示 Agent 历史实验/调研记忆的位置
            hints = []
            if self._memory_index.exists():
                hints.append(
                    f"历史记忆文件位于 `{self._memory_index}`。"
                    f"**请使用 read_file 工具自行读取**。"
                )
            roadmap_path = Path(_cfg.MEMORY_DIR) / "exploration_roadmap.md"
            if roadmap_path.exists():
                hints.append(
                    f"探索路线图位于 `{roadmap_path}`。"
                    f"**请使用 read_file 工具自行读取**。"
                )
            if hints:
                system_prompt += "\n\n## 🧠 Historical Experiment Memory\n" + "\n\n".join(hints) + "\n"

            self._messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._user_goal},
            ]

        # 上下文压缩后的摘要注入
        if self._compression_summary and start_iter > 1:
            self._messages.insert(1, {
                "role": "user",
                "content": f"[Previous round summary]\n{self._compression_summary}\n\nContinue experimenting; do not repeat work already done."
            })

        # ── 检查 API 可用性 ──
        if not self.llm.available:
            self._print(f"\n❌ No LLM provider available. Exiting.")
            self.events.emit(Event(EVENT_AGENT_END, {"reason": "no_api"}))
            return {}

        # ═══════════════════════════════════════════════════
        # ReAct 主循环
        # ═══════════════════════════════════════════════════
        self.state_machine.transition(AgentState.RUNNING)
        iteration = start_iter
        budget_final_warning_given = False

        while not self._stop_requested:
            # ── 预算耗尽检查（turn 边界及时强制收尾） ──
            if self.budget.must_stop_now() and not budget_final_warning_given:
                budget_final_warning_given = True
                self._print(f"\n⏰ Budget exhausted, waiting for Agent to wrap up...")
                self._inject_final_warning()

            iteration += 1
            elapsed_before = self.budget.elapsed()

            self.events.emit(Event(EVENT_TURN_START, {
                "iteration": iteration,
                "budget_elapsed": elapsed_before,
                "budget_remaining": self.budget.remaining(),
            }))
            self._print(f"\n─ Iteration #{iteration} | Elapsed {elapsed_before:.0f}s ─")

            # ── 反思触发：上一阶段刚完成，强制 Agent 分析结果 ──
            if self._last_experiment_done:
                self._messages.append({
                    "role": "user",
                    "content": (
                        "[反思] 上一阶段刚刚完成。在开始任何新工作之前：\n"
                        "1. 结果是否符合你的假设？为什么（不）符合？\n"
                        "2. 你学到了什么之前不知道的东西？\n"
                        "3. 下一步计划是否仍然合理？必要时调整策略。\n\n"
                        "将简要反思写入 {_cfg.MEMORY_DIR}/survey-reflection.md，然后继续。"
                    )
                })
                self._last_experiment_done = False

            # ── 阶段 1: LLM 调用（Think） ──
            t_api_start = time.time()
            content, reasoning, tool_calls_raw = self.llm.call_with_tools(self._messages)
            t_api_elapsed = time.time() - t_api_start

            remaining = self.budget.remaining()
            # 用比例判断而非绝对值，避免小预算时一直误报
            hint = " ⏳ 时间充裕" if self.budget.budget_used_pct() < 75 else " ⚠️ 时间紧张，准备收尾"
            self._print(f"     API time {t_api_elapsed:.1f}s | Remaining {remaining:.0f}s{hint}")

            # 长 API 调用返回后立即检查预算：耗尽则及时注入收尾指令（提示 Agent
            # 剩余不足），并配合 before-hook 拦截本轮"继续探索"类工具强制收尾，
            # 避免恢复场景下预算检查要到下一轮 turn 边界才生效而累计超支
            if self.budget.must_stop_now() and not budget_final_warning_given:
                budget_final_warning_given = True
                self._print(f"\n⏰ Budget exhausted, waiting for Agent to wrap up...")
                self._inject_final_warning()

            if content is None and tool_calls_raw is None:
                self._print(f"  ❌ LLM call failed completely — stopping")
                self._stop_requested = True
                break

            # 显示 Agent 的思考内容
            thinking_text = content or reasoning or ""
            if thinking_text.strip():
                self._last_agent_thinking = thinking_text
            if content:
                self._print(f"\n{'─'*50}\n🧠 Agent:\n   {content}\n{'─'*50}")
            elif reasoning:
                self._print(f"\n{'─'*50}\n🧠 Agent:\n   {reasoning[:500]}\n{'─'*50}")

            # 将 LLM 响应加入对话历史
            assistant_msg = {
                "role": "assistant",
                "content": content or "",
                "reasoning_content": reasoning or "",
            }
            if tool_calls_raw:
                assistant_msg["tool_calls"] = tool_calls_raw
            self._messages.append(assistant_msg)

            if not tool_calls_raw:
                continue

            # ── 阶段 2: 执行工具（Act） ──
            self.state_machine.transition(AgentState.TOOL_EXECUTING)

            round_tools_list = []  # 本轮工具调用摘要（轨迹日志）
            results = self._tool_manager.execute_sequential(tool_calls_raw)

            for tc_raw, result_str in results:
                fn = tc_raw.get("function", {})
                tool_name = fn.get("name", "?")

                self._fmt_tool_result(tool_name, result_str)

                try:
                    args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
                except Exception:
                    args = {}

                # 工具结果加入对话历史（LLM 下次调用时可见）
                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tc_raw.get("id", "call_0"),
                    "content": result_str,
                })

                # 记录工具调用摘要（用于轨迹日志）
                tool_summary = {"tool": tool_name}
                if tool_name == "read_file":
                    tool_summary["file"] = args.get("filepath", "")[:120]
                elif tool_name in ("write_file", "edit_file"):
                    tool_summary["file"] = args.get("file_path", args.get("filepath", ""))[:120]
                elif tool_name == "start_shell":
                    tool_summary["command"] = args.get("command", "")[:120]
                elif tool_name == "run_shell":
                    # 审计 run_shell：记录命令前 200 字符与执行结果（h_run_shell 返回头部格式）
                    tool_summary["command"] = args.get("command", "")[:200]
                    m = re.match(r"\[exit_code=([^\]]+)\] \[success=(True|False)\]", str(result_str))
                    if m:
                        tool_summary["exit_code"] = m.group(1)
                        tool_summary["success"] = m.group(2) == "True"
                elif tool_name == "check_shell":
                    tool_summary["pid"] = args.get("pid", "?")
                elif tool_name == "kill_shell":
                    tool_summary["pid"] = args.get("pid", "?")
                elif tool_name == "stop":
                    tool_summary["action"] = "stop"
                round_tools_list.append(tool_summary)

                # ── 检测实验是否完成 ──
                _is_experiment = False
                result_str_lower = str(result_str).lower()
                _has_metrics = any(kw in result_str for kw in (
                    "NDCG", "Accuracy", "Best", "Done", "最优", "全部完成"
                ))
                _has_error = any(kw in result_str_lower for kw in (
                    "traceback", "error:", "nameerror", "keyerror",
                    "attributeerror", "syntaxerror", "runtimeerror", "cuda error"
                ))
                if tool_name == "check_shell" and _has_metrics:
                    _is_experiment = True
                elif tool_name == "run_shell":
                    _is_experiment = _has_metrics and not _has_error
                if _is_experiment:
                    self._experiments_completed += 1
                    self._last_experiment_done = True  # 下一轮触发反思
                    self._print(f"  📊 Experiment #{self._experiments_completed} completed")

            # ── 构建轨迹日志条目 ──
            thinking = self._last_agent_thinking[:500] if self._last_agent_thinking else ""
            if not thinking and round_tools_list:
                tool_names = [t["tool"] for t in round_tools_list]
                thinking = f"[Tool calls: {', '.join(tool_names[:5])}]"

            # 从思考中提取策略摘要
            strategy = ""
            if thinking:
                sentences = [s.strip() for s in thinking.replace("\n", " ").split("。") if s.strip()]
                strategy = "。".join(sentences[-2:]) if len(sentences) >= 2 else (sentences[-1] if sentences else thinking[:200])

            round_config = self._extract_round_config(thinking_text, round_tools_list, {})

            self._trajectory.append({
                "round": len(self._trajectory) + 1,
                "iteration": iteration,
                "agent_thinking": thinking,
                "config": round_config if round_config else None,
                "feedback": None,  # 预留字段：当前无跨轮反馈产生来源，恒为空
                "strategy": strategy if strategy else None,
                "tools_called": round_tools_list,
                "budget_remaining": int(self.budget.remaining()),
            })
            self._save_trajectory()

            self.events.emit(Event(EVENT_TURN_END, {
                "iteration": iteration,
                "tools_executed": len(round_tools_list),
            }))

            # ── 会话 checkpoint：支持中断后恢复 ──
            self.session.save(
                iteration=iteration, messages=self._messages,
                budget_elapsed=self.budget.elapsed(),
                summary=self._compression_summary,
                trajectory=self._trajectory,
                experiments_completed=self._experiments_completed,
            )

            self.state_machine.transition(AgentState.RUNNING)

            # ── 预算提醒：每 5 轮或达到阈值时通知 Agent ──
            remaining = self.budget.remaining()
            pct = remaining / self.budget.total_budget * 100
            if not hasattr(self, '_budget_pcts_seen'):
                self._budget_pcts_seen = set()
            budget_msg = None
            if iteration % 5 == 0:
                budget_msg = (
                    f"⏰ 预算状态：已用 {self.budget.elapsed():.0f}s / 总计 {self.budget.total_budget}s，"
                    f"剩余 {remaining:.0f}s（{pct:.0f}%）。剩余 <300s 时请收尾。"
                )
            for threshold in [50, 25, 10]:
                if pct < threshold and threshold not in self._budget_pcts_seen:
                    self._budget_pcts_seen.add(threshold)
                    budget_msg = (
                        f"⏰⚠️ 仅剩 {remaining:.0f}s（{pct:.0f}%）预算！"
                        f"必须收尾：生成报告、写入记忆、调用 stop。"
                    )
                    break
            if budget_msg:
                self._messages.append({"role": "user", "content": budget_msg})
                self._print(f"  ⏰ {budget_msg}")

            # ── 上下文压缩：对话过长时自动压缩 ──
            _total_chars = sum(len(str(m.get("content", ""))) for m in self._messages)
            if _total_chars > CONTEXT_COMPRESSION_THRESHOLD:
                self._messages = compress_messages(
                    messages=self._messages,
                    trajectory=self._trajectory,
                    experiments_completed=self._experiments_completed,
                    compression_summary=self._compression_summary,
                    print_fn=self._print,
                )
                reminder = (
                    f"上下文已压缩。请重新 read_file {self._memory_index} 了解全局实验状态，"
                    f"并按需读取具体记忆文件。已完成 {self._experiments_completed} 个实验阶段。"
                )
                self._messages.append({"role": "user", "content": reminder})

        # ── 收尾：保存轨迹、清理 session ──
        self._print(f"\n🏁 Experiment ended | {len(self._trajectory)} rounds")
        self.state_machine.transition(AgentState.DONE)
        self.events.emit(Event(EVENT_AGENT_END, {"total_rounds": len(self._trajectory)}))

        self._save_trajectory()
        self.session.delete()

        return self._verify_survey_report()

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    def _fmt_tool_result(self, name: str, result: str):
        """格式化输出工具执行结果（避免刷屏）。"""
        lines = result.strip().split("\n")
        if name == "list_files":
            count = len([l for l in lines if l.strip()])
            self._print(f"     → Found {count} files")
            for line in lines[:8]:
                self._print(f"       {line}")
            if count > 8:
                self._print(f"       ... {count - 8} more files")
        elif name == "read_file":
            preview = result[:200].replace("\n", " ")
            self._print(f"     → {preview}...")
        elif name == "write_file" and "✅" in result:
            for line in result.strip().split("\n"):
                line = line.strip()
                if line:
                    self._print(f"     {line}")
        elif name == "start_shell":
            preview = result[:200].replace("\n", " ")
            self._print(f"     → {preview}")
        elif name == "check_shell":
            non_empty = [l for l in result.split("\n") if l.strip()]
            for line in non_empty[-6:]:
                self._print(f"       {line[:150]}")
        elif name == "kill_shell":
            preview = result[:200].replace("\n", " ")
            self._print(f"     → {preview}")
        elif name == "stop":
            self._print(f"     🛑 Experiment ended")
        else:
            preview = result[:200].replace("\n", " ")
            self._print(f"     → {preview}")

    def _trajectory_filename(self) -> str:
        """轨迹日志文件名：按 run_dir 隔离，避免多主题命名误导。

        LOGS_DIR 已按 run_dir 隔离（非默认 run_dir 时为
        workspace/logs/<run_dir>/），文件名同步改为 trajectory_<run_dir>.json；
        默认 run_dir="survey" 时 LOGS_DIR 为 workspace/logs（无子目录），
        保持历史文件名 trajectory_survey.json 以兼容已有产物引用。
        """
        logs_basename = os.path.basename(os.path.normpath(_cfg.LOGS_DIR))
        if logs_basename in ("", "logs"):
            return "trajectory_survey.json"  # 默认 survey：兼容历史路径
        return f"trajectory_{logs_basename}.json"

    def _save_trajectory(self):
        """持久化调研轨迹日志到磁盘（按 run_dir 隔离）。"""
        try:
            path = os.path.join(_cfg.LOGS_DIR, self._trajectory_filename())
            os.makedirs(_cfg.LOGS_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "task": "survey",
                    "agent_type": "pi-agent",
                    "total_rounds": len(self._trajectory),
                    "trajectory": self._trajectory,
                }, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            self._print(f"  ⚠️ Trajectory save failed: {e}")

    def _verify_survey_report(self) -> Dict:
        """核验 Agent 是否生成了调研报告（survey_report.md）。

        返回 {} 保持历史调用兼容；结果以打印为准。
        """
        report_path = Path(_cfg.SURVEY_DIR) / "survey_report.md"
        if report_path.exists():
            self._print(f"  ✅ Found survey report ({report_path})")
        else:
            self._print(f"  ❌ survey_report.md 缺失！期望路径：{report_path}（请检查 Agent 是否真正调用了 write_file 生成报告）")
        return {}

    @staticmethod
    def _extract_round_config(thinking_text: str, round_tools: list, round_feedback: dict) -> Optional[Dict]:
        """从 Agent 思考文本中提取结构化配置信息（轨迹日志用）。"""
        config = {}

        # ── 搜索关键词识别 ──
        search_kw = re.findall(r'(?:search|query|检索)[:\s]*["\']?([^"\'\n]{5,100})["\']?', thinking_text, re.IGNORECASE)
        if search_kw:
            config["search_queries"] = search_kw[:5]

        # ── 发现的实体 ──
        for label, patterns in [
            ("materials", [r'(?:material|材料)[:\s]*([A-Z][a-z]?[0-9A-Za-z]{1,20})']),
            ("properties", [r'(?:property|性质)[:\s]*(band gap|conductivity|PCE|stability|efficiency)[\w\s]*']),
        ]:
            seen = set()
            for pat in patterns:
                for m in re.findall(pat, thinking_text, re.IGNORECASE):
                    seen.add(m.strip())
            if seen:
                config[label] = sorted(seen)[:10]

        # ── 修改的文件名 ──
        touched = []
        for t in round_tools:
            if t.get("tool") in ("write_file", "edit_file"):
                fp = t.get("file", "")
                if fp:
                    touched.append(fp)
        if touched:
            config["touched_files"] = touched

        # ── run_shell 命令审计：记录命令前 200 字符与执行结果（随轨迹落盘） ──
        shell_calls = []
        for t in round_tools:
            if t.get("tool") == "run_shell":
                entry = {"command": t.get("command", "")[:200]}
                if "exit_code" in t:
                    entry["exit_code"] = t["exit_code"]
                if "success" in t:
                    entry["success"] = t["success"]
                shell_calls.append(entry)
        if shell_calls:
            config["run_shell_calls"] = shell_calls

        if round_feedback:
            config["feedback"] = round_feedback

        return config if config else None

    def _print(self, msg: str):
        print(msg, flush=True)
