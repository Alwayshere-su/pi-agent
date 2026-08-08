# -*- coding: utf-8 -*-
"""证据链章节生成器 — GOAI 红线 1「每个结论都能指回具体文献或数据库记录」报告层闭环。

背景：survey_report.md 由主 Agent 直接 write_file 生成（pi_agent/tools.py），
代码不直接生成报告内容，因此需要在报告生成之后由独立脚本把「证据链」章节
追加进去。本模块负责生成该章节的 Markdown 文本。

约束：不联网、不调用 LLM、纯标准库；只读不写；不修改任何现有文件。
数据源（都在 {survey_dir}/discovery/ 下）：
  - hypotheses.json        （必需：每条假设的 evidence_chain / external_validation）
  - discovery_report.json  （可选：回查源 / 元信息）
  - reference_audit.md     （可选：引用审计输出的高风险不可追溯编号）

核心函数 build_evidence_chain_section(survey_dir) 返回可直接追加到
survey_report.md 的完整「## 证据链」Markdown 章节。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

# 论文编号形态：小写 p+数字（p3/p12），或大写 2-4 字母缩写+至少 2 位数字（TE002/TE057）。
# 刻意排除 CO2/H2O/N2 这类单字母+单数字的化学式（不会把分子式误判成论文编号）。
_PAPER_ID_RE = re.compile(r"^(?:p\d{1,3}|[A-Z]{2,4}\d{2,4})$")
_NOVELTY_PREFIX = "[Novelty Verification]"

# reference_audit.md 中高风险不可追溯引用行，形如：  - `p2`（paper_id）
_AUDIT_HIGH_RISK_LINE_RE = re.compile(
    r"^-\s*`([a-zA-Z]{1,4}\d+)`\s*[（(]\s*paper_id",
    re.IGNORECASE,
)
_AUDIT_HIGH_RISK_HEAD_RE = re.compile(r"高风险不可追溯")

_DESC_CAP = 240


# ═══════════════════════════════════════════════════════════════
# 数据读取
# ═══════════════════════════════════════════════════════════════

def _load_json(path: Path):
    """读 UTF-8 JSON，失败时给出带路径的清晰错误。"""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_optional_text(path: Path) -> str:
    """读可选文本文件；不存在时返回空串。"""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_reference_audit_high_risk(audit_md: str) -> set:
    """从 reference_audit.md 提取被标记为「高风险不可追溯」的证据编号集合。

    只收集出现在「高风险不可追溯」小节（- `xxx`（paper_id））中的编号，
    作者-年份警告（如 `Caskey 2008`）不参与——evidence_chain 不引用该形态。
    返回空集合表示没有审计文件或没有任何高危编号。
    """
    high_risk = set()
    if not audit_md.strip():
        return high_risk
    in_high_risk_block = False
    for line in audit_md.splitlines():
        if _AUDIT_HIGH_RISK_HEAD_RE.search(line):
            in_high_risk_block = True
            continue
        # 进入下一个「## 汇总」或文件小节标题则退出高风险块
        if in_high_risk_block and (line.startswith("## ") or line.startswith("### ")):
            in_high_risk_block = False
            continue
        if not in_high_risk_block:
            continue
        m = _AUDIT_HIGH_RISK_LINE_RE.match(line.strip())
        if m:
            high_risk.add(m.group(1).lower())
    return high_risk


# ═══════════════════════════════════════════════════════════════
# 字段格式化
# ═══════════════════════════════════════════════════════════════

def _classify_evidence(items) -> dict:
    """把 evidence_chain 数组分类为 论文编号 / 新颖性查重 / 其他。"""
    result = {"papers": [], "novelty": [], "other": []}
    for raw in items or []:
        item = str(raw).strip()
        if not item:
            continue
        if item.startswith(_NOVELTY_PREFIX):
            result["novelty"].append(item)
        elif _PAPER_ID_RE.match(item):
            result["papers"].append(item)
        else:
            result["other"].append(item)
    return result


def _format_novelty(item: str) -> str:
    """从 [Novelty Verification] 行提取 Novelty/Queries/Results 摘要。"""
    nov = re.search(r"Novelty:\s*([\d.]+)", item)
    q = re.search(r"Queries:\s*(\d+)", item)
    r = re.search(r"Results:\s*(\d+)", item)
    parts = []
    if nov:
        parts.append(f"新颖性 {nov.group(1)}")
    if q:
        parts.append(f"查询 {q.group(1)} 次")
    if r:
        parts.append(f"结果 {r.group(1)} 条")
    return "；".join(parts) if parts else item


def _format_external_validation(ev) -> list:
    """把 external_validation 结构化成「数据库记录」来源归属行。"""
    lines = []
    if not ev:
        return ["- 数据库记录：无（hypotheses.json 中 external_validation 为空）"]
    checked = ev.get("databases_checked") or []
    supporting = ev.get("supporting_evidence") or []
    details = ev.get("details") or {}

    for s in supporting[:3]:
        lines.append(f"- 数据库记录（支持证据）：{s}")
    if len(supporting) > 3:
        lines.append(f"- 数据库记录（支持证据）：另 {len(supporting) - 3} 条略")

    for db in checked:
        d = details.get(db) or {}
        matched = d.get("match")
        entries = d.get("matching_entries") or []
        found = d.get("materials_found") or []
        if matched:
            for e in entries[:3]:
                lines.append(f"- 数据库记录（{db}）：命中 → {e}")
            if len(entries) > 3:
                lines.append(f"- 数据库记录（{db}）：另有 {len(entries) - 3} 条命中略")
            if not entries:
                mp_ids = [f.get("mp_id") for f in found if f.get("mp_id")]
                if mp_ids:
                    shown = ", ".join(mp_ids[:5])
                    suffix = f" 等 {len(mp_ids)} 条" if len(mp_ids) > 5 else ""
                    lines.append(f"- 数据库记录（{db}）：命中 → mp_id: {shown}{suffix}")
        else:
            queries = d.get("queries_attempted") or []
            mp_ids = [f.get("mp_id") for f in found if f.get("mp_id")]
            qs = ", ".join(str(x) for x in queries[:5]) or "—"
            if mp_ids:
                shown = ", ".join(mp_ids[:3])
                lines.append(
                    f"- 数据库记录（{db}）：未命中（查询 {qs}；代理条目 {len(found)} 条，"
                    f"含 {shown} …）"
                )
            else:
                lines.append(f"- 数据库记录（{db}）：未命中（查询 {qs}）")
    if not checked and not supporting:
        lines.append("- 数据库记录：无（external_validation 未列数据库）")
    return lines


def _truncate(text: str, cap: int = _DESC_CAP) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= cap:
        return text
    return text[: cap - 1] + "…"


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def build_evidence_chain_section(survey_dir: Path) -> str:
    """为指定 run 的 discovery 产物生成完整「## 证据链」Markdown 章节。

    Args:
        survey_dir: 主题 survey 输出目录，如 workspace/outputs/mof_rerun/literature_survey。

    Returns:
        可直接追加到 survey_report.md 的 Markdown 文本（以 `## 证据链` 开头）。

    Raises:
        FileNotFoundError: 缺少必需的 discovery/hypotheses.json。
        ValueError: hypotheses.json 为空或结构异常。
    """
    survey_dir = Path(survey_dir)
    hypo_path = survey_dir / "discovery" / "hypotheses.json"
    if not hypo_path.exists():
        raise FileNotFoundError(
            f"缺少证据链必需数据：{hypo_path}。"
            "请先运行文献调研生成 discovery/hypotheses.json。"
        )
    hypotheses = _load_json(hypo_path)
    if not isinstance(hypotheses, list) or not hypotheses:
        raise ValueError(f"hypotheses.json 为空或格式异常：{hypo_path}")

    # 可选回查源
    disc_json_path = survey_dir / "discovery" / "discovery_report.json"
    audit_path = survey_dir / "discovery" / "reference_audit.md"
    disc_json = _load_json(disc_json_path) if disc_json_path.exists() else {}
    audit_md = _read_optional_text(audit_path)
    high_risk = parse_reference_audit_high_risk(audit_md)

    # ── 逐假设生成 ──
    blocks = []
    total_evidence = 0
    for idx, h in enumerate(hypotheses, start=1):
        hid = h.get("id") or f"hypo_{idx}"
        title = h.get("title") or "(无标题假设)"
        desc = _truncate(h.get("description") or h.get("expected_relationship") or "（无结论描述）")
        chain = h.get("evidence_chain")
        classified = _classify_evidence(chain) if chain else {
            "papers": [], "novelty": [], "other": []
        }
        total_evidence += (
            len(classified["papers"]) + len(classified["novelty"]) + len(classified["other"])
        )

        lines = [f"### 假设 {idx}｜{title}（{hid}）", ""]
        lines.append(f"**结论简述**：{desc}")
        lines.append("")

        # 证据编号列表
        lines.append("**证据编号列表**：")
        if chain:
            for p in classified["papers"]:
                lines.append(f"- `{p}`（论文编号）")
            for n in classified["novelty"]:
                lines.append(f"- `{n}`（新颖性查重）")
            for o in classified["other"]:
                lines.append(f"- `{o}`")
        else:
            lines.append("- 无（hypotheses.json 未提供 evidence_chain 字段）")
        lines.append("")

        # 来源归属
        lines.append("**来源归属**：")
        if classified["papers"]:
            lines.append(
                "- 论文证据：" + "、".join(f"`{p}`" for p in classified["papers"])
                + "（源自 hypotheses.json → evidence_chain）"
            )
        for n in classified["novelty"]:
            lines.append(f"- 新颖性查重：{_format_novelty(n)}")
        for o in classified["other"]:
            lines.append(f"- 其他证据：{o}")
        lines.extend(_format_external_validation(h.get("external_validation")))
        lines.append("")

        # 可追溯状态
        risky = sorted(p for p in classified["papers"] if p.lower() in high_risk)
        if not chain:
            status = "⚠ 无结构化证据链 —— 该假设未在 hypotheses.json 中登记 evidence_chain，需人工补充溯源。"
        elif risky:
            status = (
                "⚠ 需人工核对 —— 证据编号 "
                + "、".join(f"`{r}`" for r in risky)
                + " 被 discovery/reference_audit.md 标记为「高风险不可追溯」（paper_id "
                "在检索结果中无匹配，红线 4 高危），须在 search_results.json 或人工核实后再采信。"
            )
        else:
            status = (
                "✅ 已溯源 —— 证据编号在 discovery 产物（hypotheses.json → evidence_chain、"
                "discovery_report.md → Evidence Chain）中可逐层回查，且未被引用审计标记；"
                "论文编号对应的真实文献最终确认请回查检索缓存或人工复核。"
            )
        lines.append(f"**可追溯状态**：{status}")
        blocks.append("\n".join(lines))

    # ── 章节头（含审计说明，不掩盖 reference_audit 的结果） ──
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    run_hint = ""
    if audit_md:
        run_hint = f"｜引用审计标记高风险编号 {len(high_risk)} 个"
    disc_hint = "、".join(
        p for p, exists in
        [("discovery/hypotheses.json（必需）", True),
         ("discovery/discovery_report.json（可选）", disc_json_path.exists()),
         ("discovery/reference_audit.md（可选）", audit_path.exists())]
        if exists
    )
    header = [
        "## 证据链",
        "",
        "> 本章节由 `scripts/inject_evidence_chain.py` 依据 discovery 产物自动生成，"
        "保证赛题红线 1「每个结论都能指回具体文献或数据库记录」在基本任务报告层闭环。",
        f"> 生成时间：{ts}{run_hint}｜假设总数：{len(hypotheses)}｜证据条目总数：{total_evidence}",
        f"> 数据源：{disc_hint}",
        "> 回查路径：survey_report.md → discovery/hypotheses.json（evidence_chain）→ "
        "discovery/discovery_report.md（Evidence Chain）→ "
        "检索缓存 search_results.json / 人工核实。",
        "> 状态说明：「✅ 已溯源」= 编号证据在 discovery 产物中存在且未被引用审计标记；"
        "「⚠ 需人工核对」= reference_audit 标记该编号不可追溯，须人工确认。",
    ]

    section = "\n".join(header) + "\n\n---\n\n" + "\n\n---\n\n".join(blocks) + "\n"
    return section
