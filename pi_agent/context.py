"""
上下文压缩管线 — Pi-Agent Layer 2
==================================
当对话历史过长时自动压缩，保持在 LLM 上下文窗口限制内。

压缩策略：
  messages → [裁剪过长消息] → [提取摘要] → [修剪旧消息] → 压缩后的消息

保留头部（system + user_goal），压缩中间轮次为结构化摘要，保留尾部最近消息。

摘要格式（四段式）：
  1. 关键数据发现
  2. 有效方法（最优配置 + 分数）
  3. 失败记录（禁止重复）
  4. 当前优化方向
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def _mechanical_summary(trajectory: List[Dict], experiments_completed: int) -> str:
    """Simple mechanical summary — no LLM needed."""
    lines = [
        "1. Key data findings: see latest memory file",
        "2. Effective methods: see MEMORY.md index",
        f"3. Completed experiments: {experiments_completed}",
        "4. Current direction: incrementally improve from best known config",
    ]
    recent_thinking = []
    for t in trajectory[-8:]:
        content = str(t.get("agent_thinking", ""))[:200]
        if content:
            recent_thinking.append(f"   - {content}")
    if recent_thinking:
        lines.append("5. Recent thoughts:")
        lines.extend(recent_thinking[-3:])
    return "\n".join(lines)


def compress_messages(
    messages: List[Dict],
    trajectory: List[Dict],
    experiments_completed: int,
    compression_summary: str = "",
    print_fn: Callable = None,
    threshold: int = 3_500_000,
) -> List[Dict]:
    """
    Compress conversation context to prevent overflow.

    Structure after compression:
      [system][user_goal][compressed_summary]...[recent tail messages]

    Args:
        messages: full message list (system + user + assistant + tool)
        trajectory: recent trajectory entries for summary
        experiments_completed: count for summary
        compression_summary: previous summary text (carried forward)
        print_fn: optional logging
        threshold: char count that triggers compression

    Returns:
        Compressed message list (may be unchanged if under threshold).
    """
    _print = print_fn or (lambda x: None)
    n = len(messages)

    if n <= 10:
        return messages

    # Only compress if total chars exceed threshold
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    if total_chars < threshold:
        return messages

    _print(f"\n  📦 Compressing context ({total_chars} → ...)")

    keep_recent = max(n // 2, 10)
    # 保留头部 system + user_goal（调研主题）。注意 user_goal 不一定是 index 1：
    # 恢复场景下 agent.py 会在 index 1 注入 "[Previous round summary]" 摘要，
    # 若按固定 index 截取 head=messages[:2] 会连同 middle 一起丢掉 user_goal
    # （缺陷修复：压缩后 Agent 失忆调研主题）。这里按内容前缀跳过摘要消息。
    head = [messages[0]]
    for _m in messages[1:]:
        if _m.get("role") == "user":
            _c = str(_m.get("content", ""))
            if _c.startswith("[Previous round summary]") or _c.startswith("[Context compressed"):
                continue
            head.append(_m)
            break
    else:
        if len(messages) > 1:  # 兜底：找不到明确 user_goal 时保留原第二条
            head.append(messages[1])
    middle = messages[2:-keep_recent]
    tail = messages[-keep_recent:]

    # Truncate oversized individual messages in tail
    truncated_tail = []
    for m in tail:
        c = str(m.get("content", ""))
        if len(c) > 4000:
            m_copy = dict(m)
            m_copy["content"] = c[:4000] + f"\n...[truncated, was {len(c)} chars]"
            truncated_tail.append(m_copy)
        else:
            truncated_tail.append(m)

    # Strip leading tool messages from tail
    while truncated_tail and truncated_tail[0].get("role") == "tool":
        truncated_tail.pop(0)

    # Generate summary
    summary_text = _mechanical_summary(trajectory, experiments_completed)

    prev = f"Previous summary:\n{compression_summary}\n\n" if compression_summary else ""
    summary = {"role": "user", "content": f"[Context compressed — layered summary]\n{prev}{summary_text}"}

    result = head + [summary] + truncated_tail

    # 压缩后清理孤儿消息，避免 DeepSeek API 400（tool 响应必须紧跟
    # 对应的 assistant.tool_calls）：middle 被丢弃后，tail 开头可能残留
    # 无配对的 tool 消息，或带 tool_calls 的 assistant 缺后续 tool 响应。
    clean: List[Dict] = []
    pending_tool_calls = 0
    for _m in result:
        role = _m.get("role")
        if role == "assistant" and _m.get("tool_calls"):
            pending_tool_calls = len(_m["tool_calls"])
            clean.append(_m)
        elif role == "tool":
            if pending_tool_calls > 0:
                pending_tool_calls -= 1
                clean.append(_m)
            # else: 孤儿 tool 消息（其 assistant 在已丢弃的 middle 中），丢弃
        else:
            clean.append(_m)
    if clean and clean[-1].get("role") == "assistant" and clean[-1].get("tool_calls"):
        last = dict(clean[-1])
        last.pop("tool_calls", None)  # 尾部缺 tool 响应：剥离 tool_calls 保留文本
        clean[-1] = last
    result = clean

    new_chars = sum(len(str(m.get("content", ""))) for m in result)
    _print(f"      → {new_chars} chars")

    return result
