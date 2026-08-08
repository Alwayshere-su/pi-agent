# -*- coding: utf-8 -*-
"""
记忆质量评估模块（纯函数：不读写文件、不调用 LLM）
====================================================

用于对 Agent 跨轮记忆（MEMORY.md 索引 + survey-*.md 记忆文件）中的
Markdown 小节做启发式质量评分，识别"表面化摘要"——无数值/数据证据、
无来源引用、无明确结论、占位/空泛、过短等，供 Agent 记忆写入路径做
增强审计。

设计约束：
  - 纯函数：同一输入必然得到同一输出，便于单测与并行复用；
  - 只评估与报告：不自动删改 Agent 写的记忆（避免误伤）；
  - 低质量判定：score < LOW_SCORE_THRESHOLD，或命中 SEVERE_FLAGS
    中的严重 flag（如 placeholder）。
"""

from __future__ import annotations

import re
from typing import List

# ── 阈值与常量 ──
LOW_SCORE_THRESHOLD = 0.35          # score 低于该值视为低质量
SEVERE_FLAGS = ("placeholder",)     # 命中即视为低质量的严重 flag
TOO_SHORT_CHARS = 40                # 小节正文去空白后字符数低于该值判"过短"
MAX_REPORT_ITEMS = 10               # 审计报告中最多展示的低质量明细条数

# ── 正则：数值/数据证据 ──
# 数字+科学单位 / 小数（置信度、增益等）/ 数值区间与变化 / 中文量词
_QUANT_RE = re.compile(
    r"(?:"
    r"\d+(?:\.\d+)?\s*(?:"
    r"mmol/g|mol/g|mg/g|ml/g|mL/g|µg/g|ug/g|wt%|wt\.%|at%|vol%|"
    r"K\b|°C|℃|eV|kJ/mol|kJ\s?mol|kcal/mol|cal/mol|kJ·mol|"
    r"MPa|GPa|kPa|Pa\b|bar\b|Torr|mmHg|"
    r"nm\b|µm|μm|mm\b|cm\b|Å\b|cm−1|cm-1|"
    r"s\b|min\b|h\b|day\b|yr\b|"
    r"%\b|ppm|ppb|RH\b|m²/g|m2/g|cc/g|cm³/g|cm3/g"
    r")"
    r")"
    r"|\d+\.\d+"                              # 小数
    r"|\d+(?:\.\d+)?\s*[-–—→↔~]\s*\d+(?:\.\d+)?"  # 数值区间/变化（0.65→0.75）
    r"|\d+\s*[万亿]"
    r"|\d+(?:\.\d+)?\s*(?:篇|个|种|例|组|轮|倍|次|天|小时|分钟)"
)

# ── 正则：来源引用特征 ──
# 文献编号 / 页码引用 / arXiv / DOI / URL / 年份 / 期刊名
_SOURCE_RE = re.compile(
    r"\[[0-9]+\]"                        # [12]
    r"|\b[pP]\s?\d{1,4}\b"               # p65
    r"|\barXiv[:\s/]"
    r"|\bdoi\b|doi\.org|https?://"
    r"|[（(]\s*(?:19|20)\d{2}\s*[)）]"    # (2019)
    r"|\b(?:19|20)\d{2}\b"               # 裸年份 2019 / 2023
    r"|文献|参考文献|\bJACS\b|\bNature\b|\bScience\b|\bAngew\b"
    r"|\bACS\b|\bRSC\b|\bElsevier\b|\bWiley\b|\bSpringer\b"
)

# ── 正则：明确结论特征 ──
# 结论性动词 / 比较与变化 / 判定性符号
_CONCLUSION_RE = re.compile(
    r"发现|表明|显示|说明|证实|验证|确证|揭示|结论|意味着|推断|推测|"
    r"优于|高于|低于|好于|大于|小于|提升|提高|增强|减弱|下降|降低|"
    r"达到|突破|创纪录|显著|稳定|支持|驳斥|反驳|"
    r"[-–—→↔↑↓><≥≤=]|\bvs\.?\b|相比|对比|强于|不如|弱于"
)

# ── 正则：占位 / 空泛文本 ──
_PLACEHOLDER_RE = re.compile(
    r"待补充|待完善|待更新|后续补充|稍后补充|此处补|补记|省略|"
    r"\bTBD\b|\bTODO\b|\bFIXME\b|placeholder|占位|未完成|稍后更新|"
    r"lorem ipsum|内容待|细节待",
    re.IGNORECASE,
)

# 各 flag 的扣分权重
_FLAG_PENALTIES = {
    "placeholder": 0.60,        # 占位/空泛最严重
    "too_short": 0.30,          # 过短信息密度低
    "no_numeric_evidence": 0.20,
    "vague_conclusion": 0.15,
    "no_source": 0.15,
}


def score_memory_entry(text: str) -> dict:
    """对一段记忆文本（一个 Markdown 小节）做质量评分。

    返回: {"score": 0.0-1.0, "flags": [...], "detail": str}
      score 由 1.0 起始按命中 flag 扣分，夹取到 [0.0, 1.0]；
      flags 可能包含:
        placeholder         占位/空泛文本（"待补充""TBD""未完成"等，且无数值证据）
        too_short           正文去空白后过短
        no_numeric_evidence 无数值/数据证据（数字+单位、小数、比较或量词）
        no_source           无来源引用（文献编号/页码/DOI/URL/年份/期刊名）
        vague_conclusion    无明确结论表达（结论性动词或比较关系）
    """
    if not text or not text.strip():
        return {
            "score": 0.0,
            "flags": ["placeholder", "too_short", "no_numeric_evidence",
                      "no_source", "vague_conclusion"],
            "detail": "空文本，无法提供任何记忆价值。",
        }

    t = text.strip()
    body_chars = len(re.sub(r"\s+", "", t))

    has_quant = bool(_QUANT_RE.search(t))
    has_source = bool(_SOURCE_RE.search(t))
    has_conclusion = bool(_CONCLUSION_RE.search(t))
    # 占位词仅在"无量化证据"时才算占位——真实记忆（含数值）中出现的
    # "占位符/未完成"等描述是状态信息，不应误判为空泛。
    is_placeholder = bool(_PLACEHOLDER_RE.search(t)) and not has_quant
    is_too_short = body_chars < TOO_SHORT_CHARS

    flags: List[str] = []
    if is_placeholder:
        flags.append("placeholder")
    if is_too_short:
        flags.append("too_short")
    if not has_quant:
        flags.append("no_numeric_evidence")
    if not has_source:
        flags.append("no_source")
    if not has_conclusion:
        flags.append("vague_conclusion")

    score = 1.0 - sum(_FLAG_PENALTIES.get(f, 0.0) for f in flags)
    score = round(max(0.0, score), 3)

    detail = (
        f"长度 {body_chars} 字；数值证据：{'有' if has_quant else '无'}；"
        f"来源引用：{'有' if has_source else '无'}；"
        f"明确结论：{'有' if has_conclusion else '无'}"
        f"{'；占位/空泛：是' if is_placeholder else ''}"
        f"{'；过短：是' if is_too_short else ''}"
        f"。扣分项：{flags if flags else '无'}，综合得分 {score:.2f}。"
    )
    return {"score": score, "flags": flags, "detail": detail}


def _split_sections(md_text: str) -> List[dict]:
    """按 `#~######` 标题行切分 Markdown，返回小节列表。

    与 agent.py dedupe_markdown_sections 采用相同的切分思路：
    标题行为小节边界，标题行连同其后的正文构成一个小节；
    无标题的游离文本块单独成节。
    返回 [{"heading": str|None, "lines": [str, ...]}, ...]。
    """
    if not md_text:
        return []
    text = md_text.replace("\r\n", "\n").replace("\r", "\n")
    sections: List[dict] = []
    cur_heading = None
    cur_lines: List[str] = []
    for line in text.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            if cur_lines:
                sections.append({"heading": cur_heading, "lines": cur_lines})
            cur_heading = line.strip()          # 保留完整标题行
            cur_lines = [line]
        else:
            cur_lines.append(line)
    if cur_lines:
        sections.append({"heading": cur_heading, "lines": cur_lines})
    return sections


def _heading_label(heading, text: str) -> str:
    """生成用于报告的简短小节标题（标题行或无标题片段的首行，截断）。"""
    if heading:
        h = re.sub(r"^#{1,6}\s+", "", heading).strip()
        return h if len(h) <= 50 else h[:47] + "…"
    first = ""
    for ln in text.split("\n"):
        if ln.strip():
            first = ln.strip()
            break
    if not first:
        return "（无标题片段）"
    return first if len(first) <= 50 else first[:47] + "…"


def audit_memory_file(md_text: str) -> dict:
    """对整份记忆文件（MEMORY.md 或 survey-*.md）按小节逐条评分。

    返回: {
      "total_entries": int,       已评分的小节数（仅标题无正文的章节头跳过）
      "low_quality": [ {heading, score, flags}, ... ],
      "avg_score": float,
      "summary": str,
    }
    """
    if not md_text or not md_text.strip():
        return {
            "total_entries": 0,
            "low_quality": [],
            "avg_score": 0.0,
            "summary": "（空文档，无记忆条目可审计）",
        }

    entries: List[dict] = []
    for sec in _split_sections(md_text):
        lines = sec["lines"] or []
        # 有标题的小节：首行是标题，正文从第二行起；
        # 无标题的游离正文块：整块都是正文，不应剔除首行。
        body_lines = lines[1:] if sec["heading"] is not None else lines
        if not "\n".join(body_lines).strip():
            continue  # 仅标题行、无正文：章节头不是记忆条目，跳过
        text = "\n".join(lines).strip()
        scored = score_memory_entry(text)
        entries.append({
            "heading": _heading_label(sec["heading"], text),
            "score": scored["score"],
            "flags": scored["flags"],
        })

    low_quality = [
        e for e in entries
        if e["score"] < LOW_SCORE_THRESHOLD
        or any(f in SEVERE_FLAGS for f in e["flags"])
    ]
    avg = (sum(e["score"] for e in entries) / len(entries)) if entries else 0.0

    if not entries:
        summary = "（没有可评分的小节：文档为空或仅含章节标题）"
    elif not low_quality:
        summary = (
            f"共 {len(entries)} 个小节，平均分 {avg:.2f}，"
            "无低质量条目，记忆质量整体良好。"
        )
    else:
        summary = (
            f"共 {len(entries)} 个小节，平均分 {avg:.2f}，其中 "
            f"{len(low_quality)} 条低质量（score < {LOW_SCORE_THRESHOLD} "
            f"或命中 {SEVERE_FLAGS}），建议补充数值证据/来源/明确结论。"
        )

    return {
        "total_entries": len(entries),
        "low_quality": low_quality,
        "avg_score": round(avg, 3),
        "summary": summary,
    }


def format_audit_report(audit: dict) -> str:
    """把审计结果格式化为人类可读的中文报告文本（纯函数）。"""
    total = audit.get("total_entries", 0)
    avg = audit.get("avg_score", 0.0)
    low = audit.get("low_quality", [])

    lines = ["## 记忆质量审计报告"]
    lines.append(f"- 记忆小节数：{total}")
    lines.append(f"- 平均评分：{avg:.2f}（0.0-1.0）")
    lines.append(f"- 低质量条目：{len(low)} 条")
    if low:
        shown = low[:MAX_REPORT_ITEMS]
        for i, e in enumerate(shown, 1):
            lines.append(
                f"  {i}. 「{e['heading']}」 score={e['score']:.2f} "
                f"flags=[{', '.join(e['flags'])}]"
            )
        if len(low) > MAX_REPORT_ITEMS:
            lines.append(f"  … 其余 {len(low) - MAX_REPORT_ITEMS} 条低质量条目略")
        lines.append(
            "- 建议：为上述小节补充数值/数据证据、来源引用"
            "（文献编号/页码/DOI/URL/年份）与明确结论，避免表面化摘要累积。"
        )
    lines.append("")
    lines.append(f"汇总：{audit.get('summary', '')}")
    return "\n".join(lines)
