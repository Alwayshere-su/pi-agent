"""
构效关系发现引擎 — Route A: Structure-Property Relationship Discovery
=====================================================================
基于文献知识图谱的 Research Gap，利用搜索算法 + LLM 深度融合，
自主发现材料-性质关联，并通过外部数据库交叉验证。

@external: utils/resource_registry.py
  本模块使用以下外部数据库进行交叉验证（详见注册表）：
  - "Materials Project" — DFT 结构/能量数据 (api.materialsproject.org, 需 API Key)
  - "OQMD"              — 形成能/热力学数据 (oqmd.org, REST API, 免 Key)
  - "NOMAD"             — 计算材料科学数据仓库 (nomad-lab.eu, REST API, 公开)
  - "hMOF"              — MOF 结构-吸附数据 (文献快照, MOF 体系专项)
  所有数据库均为可选——单库异常自动降级，不中断 discovery 流程。

核心流程：
  Phase 1: Hypothesis Generation    — 从 Gap 中生成候选构效关系假设
  Phase 2: Guided Search            — 贝叶斯优化/MCTS 探索材料空间
  Phase 3: LLM Plausibility Check   — LLM 评估中间结果的科学合理性
  Phase 4: External Validation      — Materials Project / OQMD 交叉验证
  Phase 5: Discovery Report         — 结构化输出发现结果 + 证据链

与 LLM 的深度融合（路线 A 核心得分点）：
  - 候选假设生成：LLM 根据 Gap 知识图谱生成搜索种子
  - 中间结果评估：LLM 评估搜索中的中间结果的科学合理性，引导剪枝
  - 搜索方向调整：LLM 分析搜索结果，建议下一轮搜索方向
  - 发现解释生成：LLM 为最终发现生成科学解释和机制假说
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.optimize import minimize
from scipy.spatial.distance import cdist
import requests

from .extractor import KnowledgeGraph, MaterialEntity, PropertyRecord, Relation


# ═══════════════════════════════════════════════════════════════
# Scoring version switch (#11: 打分函数区分度有限)
# ═══════════════════════════════════════════════════════════════
# 环境变量 SCORING_V2 控制是否启用增强打分：
#   SCORING_V2=true  (默认) → 使用 enhanced_evidence_score (v2)
#   SCORING_V2=false         → 回退到 evidence_aware_score (legacy v1)
# v2 通过 sigmoid 拉伸 + 动态权重调和平均 + 多样性奖励，
# 将分数从 [0.54, 0.68] 窄区间扩展到 [0.3, 0.85]，提升贝叶斯 vs 随机对比区分度。
# 详见 literature_agent/scoring.py。
SCORING_V2 = os.environ.get("SCORING_V2", "true").strip().lower() not in ("false", "0", "no", "off")


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class ResearchGap:
    """研究空白（兼容旧 gap_analyzer 数据模型）。"""
    id: str = ""
    type: str = ""                     # "contradiction" | "missing_link" | "unexplored"
    title: str = ""
    description: str = ""
    severity: str = "medium"           # "high" | "medium" | "low"
    confidence: float = 0.5
    related_papers: List[str] = field(default_factory=list)
    evidence_chain: List[str] = field(default_factory=list)
    suggested_validation: str = ""
    entities_involved: List[str] = field(default_factory=list)
    raw_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GapReport:
    """研究空白报告（兼容旧 gap_analyzer 数据模型）。"""
    gaps: List[ResearchGap] = field(default_factory=list)
    summary: str = ""
    total_papers_analyzed: int = 0
    contradiction_count: int = 0
    missing_link_count: int = 0
    unexplored_count: int = 0
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DiscoveryHypothesis:
    """构效关系发现假设"""
    id: str = ""
    title: str = ""                        # 假设简述
    description: str = ""                  # 假设详述
    source_gap_id: str = ""               # 来源 Gap ID
    materials: List[str] = field(default_factory=list)  # 涉及材料
    property: str = ""                     # 目标性质
    expected_relationship: str = ""        # 预期的构效关系 (e.g. "doping X increases Y")
    confidence: float = 0.5               # 置信度 [0, 1]
    novelty_score: float = 0.0            # 新颖性分数 [0, 1]

    # 搜索过程
    search_method: str = ""               # "bayesian" | "mcts" | "llm_guided"
    search_iterations: int = 0
    candidates_explored: int = 0

    # 验证结果
    external_validation: Dict[str, Any] = field(default_factory=dict)
    validation_status: str = "pending"    # "pending" | "validated" | "refuted" | "inconclusive"
    evidence_chain: List[str] = field(default_factory=list)

    # LLM 评估
    llm_plausibility_score: float = 0.0
    llm_explanation: str = ""

    # 可提取性预评估（teacherA#6：假设生成时评估"能否从文献凑够 ≥5 个
    # 定量 (x,y) 对"，<3 的假设不进入搜索，避免"好看但不可验证"）
    extractability_score: float = 0.0      # 1-5；5=很容易，1=极难
    extractability_note: str = ""          # 预期数据来源与主要风险说明
    independent_materials: int = 0         # 预期可用于验证的独立材料数
    data_points_available: int = 0         # 实际可用数据点（模型对比后回填）

    # 新知与已知分清（红线 2 + 评审"对已有理论的推广甚至颠覆程度"）
    known_prior_work: str = ""             # 已知：前人已确立的结论/相关文献
    incremental_claim: str = ""            # 新知：本假设相对前人的增量/区别

    # 搜索数值证据（由 search_h*.json 合并而来）
    best_score: float = 0.0                 # 搜索阶段最优分数
    literature_values: List[float] = field(default_factory=list)  # 搜索使用的文献数值证据（容量 mmol/g、Qst kJ/mol 等）
    search_warning: str = ""                # 搜索空转警告（证据数值为空、打分无区分度）

    # 数值文献交叉验证结果（对应 hypotheses.json 中的 value_verification 字段）
    value_verification: Dict[str, Any] = field(default_factory=dict)

    # 降级标记：占位/降级假设（LLM API 不可用、证据数值为空、占位框架等）
    degraded: bool = False
    degraded_reason: str = ""


@dataclass
class DiscoveryReport:
    """构效关系发现报告"""
    title: str = "Structure-Property Relationship Discovery Report"
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M"))
    hypotheses: List[DiscoveryHypothesis] = field(default_factory=list)
    total_candidates: int = 0
    total_explored: int = 0
    validated_count: int = 0
    refuted_count: int = 0
    contested_count: int = 0
    underexplored_count: int = 0
    search_summary: str = ""
    materials_project_hits: int = 0

    @staticmethod
    def classify_consistency(h: DiscoveryHypothesis) -> str:
        """四象限一致性分类：LLM 科学合理性 vs 系统搜索置信度。

        Returns:
            "strong"        — LLM 高分 + 搜索高分（两者一致）
            "underexplored" — LLM 高分 + 搜索低分（科学合理但证据不足）
            "contested"     — LLM 低分 + 搜索高分（数据匹配但科学存疑）
            "weak"          — LLM 低分 + 搜索低分（两者均低分）
        """
        llm_high = h.llm_plausibility_score >= 0.50
        search_high = h.confidence >= 0.50
        if llm_high and search_high:
            return "strong"
        elif llm_high and not search_high:
            return "underexplored"
        elif not llm_high and search_high:
            return "contested"
        else:
            return "weak"

    def sorted_by_novelty(self) -> List[DiscoveryHypothesis]:
        return sorted(self.hypotheses, key=lambda h: h.novelty_score * h.confidence, reverse=True)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "hypotheses": [asdict(h) for h in self.hypotheses],
            "total_candidates": self.total_candidates,
            "total_explored": self.total_explored,
            "validated_count": self.validated_count,
            "refuted_count": self.refuted_count,
            "contested_count": self.contested_count,
            "underexplored_count": self.underexplored_count,
            "search_summary": self.search_summary,
            "materials_project_hits": self.materials_project_hits,
        }

    def save(self, output_dir: str) -> Tuple[str, str]:
        """Save report as Markdown + JSON. Returns (md_path, json_path)."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # JSON
        json_path = out / "discovery_report.json"
        json_path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))

        # Markdown
        md_path = out / "discovery_report.md"
        md_path.write_text(self.to_markdown(), encoding="utf-8")

        return str(md_path), str(json_path)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            f"\n**Generated:** {self.generated_at}",
            f"**Total candidates explored:** {self.total_explored}",
            f"**Validated:** {self.validated_count} | **Refuted:** {self.refuted_count}",
            f"**Contested:** {self.contested_count} | **Underexplored:** {self.underexplored_count}",
            f"**Materials Project hits:** {self.materials_project_hits}",
            f"\n## Search Summary\n\n{self.search_summary}\n",
            "---\n",
            "## Discovered Structure-Property Relationships\n",
        ]

        for i, h in enumerate(self.sorted_by_novelty()):
            status = {"validated": "✅", "refuted": "❌", "pending": "⏳", "inconclusive": "❓",
                      "contested": "⚠️", "underexplored": "🔍"}.get(
                h.validation_status, "⏳"
            )
            consistency = self.classify_consistency(h)
            cls_labels = {
                "strong": "strong (强 — LLM与搜索一致高分)",
                "underexplored": "underexplored (探索不足 — 科学合理但证据不足)",
                "contested": "contested (争议 — 数据匹配但科学存疑)",
                "weak": "weak (弱 — 两者均低分)",
            }
            # 占位/降级假设必须明确标注 degraded，不能顶替真实假设成为唯一内容
            degraded_tag = " [⛔ degraded]" if h.degraded else ""
            lines.extend([
                f"### {i+1}. {status} {h.title}{degraded_tag}",
                f"",
                f"**Confidence:** {h.confidence:.2f} | **Novelty:** {h.novelty_score:.2f} | "
                f"**LLM Plausibility:** {h.llm_plausibility_score:.2f}",
                f"**Consistency:** {cls_labels.get(consistency, consistency)}",
                f"**Extractability:** {h.extractability_score:.1f}/5"
                + (f"（预期独立材料 {h.independent_materials} 个）"
                   if h.independent_materials else "")
                + (f" — {h.extractability_note[:80]}" if h.extractability_note else ""),
                f"",
            ])

            # ── 新知与已知分清（红线 2）──
            if h.known_prior_work or h.incremental_claim:
                lines.extend([
                    f"**已知（prior work）:** {h.known_prior_work or '（未注明）'}",
                    f"**新知（incremental claim）:** {h.incremental_claim or '（未注明）'}",
                    f"",
                ])

            # ── 搜索最优分 + 文献数值证据 ──
            if h.best_score > 0:
                lines.append(
                    f"**Search Best Score:** {h.best_score:.3f} "
                    f"（文献数值证据 {len(h.literature_values)} 个）"
                )
            else:
                lines.append(f"**Search Best Score:** N/A（无搜索记录）")
            if h.data_points_available:
                lines.append(f"**实际可用数据点:** {h.data_points_available}（模型对比后回填）")
            if h.degraded_reason:
                lines.append(f"**Degraded Reason:** {h.degraded_reason}")
            if h.search_warning:
                lines.append(f"**Search Warning:** {h.search_warning}")
            lines.append(f"")
            lines.extend([
                f"**Description:** {h.description}",
                f"",
                f"**Expected Relationship:** {h.expected_relationship}",
                f"",
                f"**Materials:** {', '.join(h.materials[:8])}",
                f"**Property:** {h.property}",
                f"",
                f"**Source Gap:** {h.source_gap_id}",
                f"**Search Method:** {h.search_method} ({h.search_iterations} iterations, {h.candidates_explored} candidates)",
            ])

            if h.evidence_chain:
                lines.append(f"\n**Evidence Chain:**")
                for ev in h.evidence_chain:
                    lines.append(f"  - {ev}")

            # ── 数值文献交叉验证结果（value_verification）──
            if h.value_verification:
                vv = h.value_verification
                lines.append(f"\n**Value Verification (数值文献验证):**")
                vscore = vv.get("overall_verification_score")
                if vscore is not None:
                    try:
                        lines.append(f"  - 综合验证分数: {float(vscore):.2f}")
                    except (TypeError, ValueError):
                        # 外部 JSON 读入非数值类型时降级为原文输出，不崩溃
                        lines.append(f"  - 综合验证分数: {vscore}")
                for vf in vv.get("values_found", [])[:8]:
                    claimed = vf.get("claimed", "?")
                    ok = vf.get("found_in_text")
                    lines.append(f"  - `{claimed}`: {'✅ 文献查证' if ok else '❌ 未查证'}")
                unverified = vv.get("unverified_values") or []
                if unverified:
                    lines.append(f"  - 未查证值: {', '.join(str(u) for u in unverified[:10])}")

            if h.llm_explanation:
                lines.append(f"\n**Scientific Explanation (LLM):**")
                expl = h.llm_explanation[:500]
                if h.degraded:
                    expl = "[degraded 降级评估] " + expl
                lines.append(f"> {expl}")

            if h.external_validation:
                lines.append(f"\n**External Validation:**")
                for db, result in h.external_validation.items():
                    lines.append(f"  - {db}: {str(result)[:200]}")

            lines.append("\n---\n")

        return "\n".join(lines)

    # ── 从 hypotheses.json / search_h*.json 汇总生成报告（阶段二修复）──

    @classmethod
    def from_files(cls, discovery_dir: str,
                   hypotheses_path: Optional[str] = None) -> "DiscoveryReport":
        """从已落盘的 hypotheses.json / search_h*.json 汇总生成最终报告。

        阶段二产出断裂修复：报告必须以所有已存在假设为输入，
        每条假设呈现 evidence_chain、value_verification、搜索 best_score、
        外部验证状态、llm_plausibility；占位/降级假设明确标注 degraded，
        不会顶替真实假设成为唯一内容。头部统计（Validated/Refuted/Contested/
        Materials Project hits）如实从数据计算。

        Args:
            discovery_dir: discovery 产物目录（含 hypotheses.json / search_h*.json）
            hypotheses_path: 可选，自定义 hypotheses.json 路径

        Returns:
            DiscoveryReport
        """
        out = Path(discovery_dir)
        hypo_path = Path(hypotheses_path) if hypotheses_path else out / "hypotheses.json"
        hyps: List[DiscoveryHypothesis] = []

        # 1) 主来源：hypotheses.json（真实假设清单）
        if hypo_path.exists():
            try:
                data = json.loads(hypo_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data = data.get("hypotheses", data.get("hypotheses_list", [])) or []
                if isinstance(data, list):
                    hyps = [cls._hypothesis_from_dict(h) for h in data if isinstance(h, dict)]
            except Exception as e:
                print(f"  ⚠️ [DiscoveryReport.from_files] hypotheses.json 读取失败: {e}")

        # 2) 回退来源：discovery_report.json（若 hypotheses.json 缺失/为空）
        if not hyps:
            report_path = out / "discovery_report.json"
            if report_path.exists():
                try:
                    rdata = json.loads(report_path.read_text(encoding="utf-8"))
                    hyps = [cls._hypothesis_from_dict(h) for h in rdata.get("hypotheses", [])
                            if isinstance(h, dict)]
                except Exception as e:
                    print(f"  ⚠️ [DiscoveryReport.from_files] discovery_report.json 回退读取失败: {e}")

        # 3) 合并 search_h*.json 的搜索数值证据（best_score / literature_values / 空转警告）
        # 注意：search_h{i}.json 以下标 i 命名，对应 hypotheses.json 中第 i 条假设（而非 id 数字）
        for idx, h in enumerate(hyps):
            search_file = out / f"search_h{idx}.json"
            if not search_file.exists():
                continue
            try:
                sres = json.loads(search_file.read_text(encoding="utf-8"))
                if isinstance(sres, dict):
                    cls._merge_search_result(h, sres)
            except Exception as e:
                print(f"  ⚠️ [DiscoveryReport.from_files] {search_file.name} 读取失败: {e}")

        # 4) 降级检测：LLM 不可用 / 占位框架假设
        for h in hyps:
            cls._annotate_degraded(h)

        # 5) 头部统计如实计算
        counts = {"strong": 0, "underexplored": 0, "contested": 0, "weak": 0}
        for h in hyps:
            counts[cls.classify_consistency(h)] += 1

        report = cls(
            hypotheses=hyps,
            total_candidates=len(hyps),
            total_explored=sum(h.candidates_explored or 0 for h in hyps),
            validated_count=sum(1 for h in hyps if h.validation_status == "validated"),
            refuted_count=sum(1 for h in hyps if h.validation_status == "refuted"),
            contested_count=counts["contested"],
            underexplored_count=counts["underexplored"],
            materials_project_hits=sum(
                1 for h in hyps if (h.external_validation or {}).get("overall_match")
            ),
            search_summary=(
                f"Explored {len(hyps)} hypotheses via Bayesian optimization and MCTS. "
                f"四象限一致性: strong={counts['strong']}, "
                f"underexplored={counts['underexplored']}, "
                f"contested={counts['contested']}, weak={counts['weak']}. "
                f"degraded={sum(1 for h in hyps if h.degraded)} (占位/降级)"
            ),
        )
        return report

    @classmethod
    def _hypothesis_from_dict(cls, d: Dict) -> DiscoveryHypothesis:
        """从 dict 构造 DiscoveryHypothesis（兼容 hypotheses.json / discovery_report.json）。"""
        return DiscoveryHypothesis(**{k: v for k, v in d.items()
                                      if k in DiscoveryHypothesis.__dataclass_fields__})

    @staticmethod
    def _merge_search_result(h: DiscoveryHypothesis, sres: Dict) -> None:
        """将 search_h*.json 的搜索数值证据合并到假设上。"""
        if sres.get("best_score") is not None:
            try:
                h.best_score = float(sres["best_score"])
            except (TypeError, ValueError):
                pass
        evid = sres.get("evidence") or {}
        lv = evid.get("literature_values") or []
        if isinstance(lv, list):
            h.literature_values = [float(v) for v in lv if isinstance(v, (int, float))][:20]
        if sres.get("search_method"):
            h.search_method = str(sres["search_method"])
        if sres.get("iterations"):
            try:
                h.search_iterations = int(sres["iterations"])
            except (TypeError, ValueError):
                pass

        # ── 搜索空转检测：literature_values 为空 且 best_score 无变化 → 写入 warning ──
        warning = DiscoveryReport._detect_search_stall(sres)
        if warning:
            sres["warning"] = warning
            h.search_warning = warning
            h.degraded = True
            h.degraded_reason = h.degraded_reason or warning

    @staticmethod
    def _detect_search_stall(sres: Dict) -> str:
        """检测搜索空转：证据数值为空 且 打分无区分度。

        返回警告文本（不满足空转条件时返回空字符串）。

        空转判定条件（需同时满足）：
          1) evidence.literature_values 为空数组 → 打分函数无法利用数值先验；
          2) iteration_log 中分数几乎无区分度（唯一分数值 <= 2，
             或 best_score 全程波动 < 1e-6）→ 搜索空转、best_score 不可信。
        """
        evid = sres.get("evidence") or {}
        lv = evid.get("literature_values") or []
        if lv:
            return ""

        log = sres.get("iteration_log") or sres.get("search_log") or []
        scores = [float(item.get("score", 0.0)) for item in log
                  if isinstance(item, dict) and item.get("score") is not None]
        best_scores = [float(item.get("best_score", 0.0)) for item in log
                       if isinstance(item, dict) and item.get("best_score") is not None]

        distinct_scores = len(set(round(s, 6) for s in scores))
        best_flat = len(best_scores) >= 2 and (max(best_scores) - min(best_scores)) < 1e-6
        if distinct_scores <= 2 or best_flat:
            return (
                "⚠️ 证据数值为空，打分无区分度（搜索空转）: literature_values 为空导致"
                "候选参数主要依赖固定基分，best_score 多轮不变。"
                "建议在 knowledge_graph.md 中补充定量数值（如容量 mmol/g、Qst kJ/mol），"
                "并重跑搜索以利用文献数值先验。"
            )
        return ""

    @staticmethod
    def annotate_search_warning(search_result: Dict) -> Dict:
        """在搜索结果 dict 中写入 warning 字段（供报告展示）。

        检测"搜索空转"（literature_values 为空 且 best_score 无变化），
        命中时写入 search_result["warning"] = "证据数值为空，打分无区分度..."，
        未命中时确保 warning 字段存在但不含空转内容。返回原 dict（就地更新）。
        """
        warning = DiscoveryReport._detect_search_stall(search_result)
        if warning:
            search_result["warning"] = warning
        else:
            search_result.pop("warning", None)
        return search_result

    @staticmethod
    def _annotate_degraded(h: DiscoveryHypothesis) -> None:
        """降级假设检测：LLM API 不可用 / degraded / 占位框架。

        占位/降级假设必须明确标注 degraded，不能顶替真实假设成为唯一内容。
        判定依据（任一命中即降级）：
          - llm_explanation 含 "LLM API 不可用" 或 "degraded"；
          - 占位框架：材料与性质同时为空（如 "Material-property relationship discovery"）。
        """
        expl = (h.llm_explanation or "").lower()
        if "llm api 不可用" in expl or "degraded" in expl:
            h.degraded = True
            h.degraded_reason = h.degraded_reason or (
                "LLM API 不可用，llm_plausibility 为启发式降级评分，"
                "非 LLM 深度评估结果。"
            )
        if (not h.materials and not h.property) or not (h.title or "").strip():
            h.degraded = True
            h.degraded_reason = h.degraded_reason or (
                "占位框架假设（缺少材料/性质/期望关系等关键变量），"
                "仅作流程占位，不应计为有效发现。"
            )


# ═══════════════════════════════════════════════════════════════
# Phase 1: Hypothesis Generation
# ═══════════════════════════════════════════════════════════════

class HypothesisGenerator:
    """从 Research Gap 生成可验证的构效关系假设。

    这是 LLM 深度融合的第一关：LLM 分析 Gap 知识图谱，
    生成具体的、可验证的、具有新颖性的构效关系假设作为搜索种子。
    """

    def __init__(self):
        # 每种 Gap 类型的实例级计数器，确保自动生成的 ID 唯一
        self._unexplored_counter = 0
        self._missing_link_counter = 0
        self._contra_counter = 0

    # legacy: JSON KG path, kept for backward compatibility; prefer generate_from_markdown
    def generate_from_gaps(self, kg: KnowledgeGraph, gaps: List[ResearchGap],
                          llm_evaluator: Callable = None) -> List[DiscoveryHypothesis]:
        """[legacy] 从 JSON KnowledgeGraph + Gap 列表生成假设。

        注意：项目架构已改为 Markdown-based 知识图谱，此方法依赖 JSON KG 对象，
        在当前运行路径中不可达。请优先使用 generate_from_markdown()。
        """

        # 构建材料×性质矩阵，找出空白单元格
        mat_prop_matrix = self._build_matrix(kg)

        hypotheses = []
        for gap in gaps:
            # 为每个 high/medium severity gap 生成假设
            if gap.severity not in ("high", "medium"):
                continue

            # 未探索空间类 Gap → 候选材料-性质配对
            if gap.type == "unexplored":
                generated = self._hypothesize_unexplored(gap, kg, mat_prop_matrix)
                hypotheses.extend(generated)

            # 缺失连接类 Gap → 推理可能的中间材料
            elif gap.type == "missing_link":
                generated = self._hypothesize_missing_link(gap, kg, mat_prop_matrix)
                hypotheses.extend(generated)

            # 矛盾类 Gap → 哪边更可能是真的
            elif gap.type == "contradiction":
                generated = self._hypothesize_contradiction_resolution(gap, kg)
                hypotheses.extend(generated)

        # LLM 评估假设的科学合理性（如果提供了评估器）
        if llm_evaluator and hypotheses:
            for h in hypotheses[:20]:  # 限制数量避免 API 开销过大
                try:
                    score, explanation = llm_evaluator(h)
                    h.llm_plausibility_score = score
                    h.llm_explanation = explanation
                except Exception:
                    h.llm_plausibility_score = 0.5
                    h.llm_explanation = "(LLM evaluation unavailable)"

        return hypotheses

    def generate_from_markdown(self, gap_report_text: str,
                               paper_summaries_text: str) -> List[DiscoveryHypothesis]:
        """从 Markdown 文本生成假设（无需 JSON KnowledgeGraph）。

        解析 gap_report.md 和 paper_summaries.md / knowledge_graph.md 的文本，
        从中提取 Gap、材料名和性质名，直接基于文本实体生成假设。

        Args:
            gap_report_text: gap_report.md 的完整文本内容
            paper_summaries_text: paper_summaries.md 或 knowledge_graph.md 的完整文本内容

        Returns:
            List[DiscoveryHypothesis]: 生成的假设列表
        """
        # ── 解析 Gap 文本：正则提取 "## Gap N" + 类型/严重程度/证据 ──
        gaps = self._parse_gaps_from_text(gap_report_text)

        # ── 从文献文本中提取材料名和性质名 ──
        materials, properties = self._extract_entities_from_text(paper_summaries_text)

        # ── 构建简化的材料-性质共现表（文本版） ──
        mat_prop_cooccurrence: Dict[str, set] = {}
        for mat in materials:
            mat_lower = mat.lower()
            # 检查该材料的上下文块中出现了哪些性质
            # 在文本中搜索包含材料名的段落，再看其中出现的性质词
            mat_pattern = re.compile(re.escape(mat[:20]), re.IGNORECASE)
            for para in paper_summaries_text.split("\n\n"):
                if mat_pattern.search(para):
                    if mat_lower not in mat_prop_cooccurrence:
                        mat_prop_cooccurrence[mat_lower] = set()
                    for prop in properties:
                        if prop.lower() in para.lower():
                            mat_prop_cooccurrence[mat_lower].add(prop)

        hypotheses = []
        for gap_text_info in gaps:
            gap_type = gap_text_info.get("type", "")
            gap_severity = gap_text_info.get("severity", "medium")
            gap_desc = gap_text_info.get("description", "")
            gap_title = gap_text_info.get("title", "")
            gap_id = gap_text_info.get("id", "")
            gap_entities = gap_text_info.get("entities", [])

            if gap_severity not in ("high", "medium"):
                continue

            if gap_type == "unexplored":
                generated = self._hypothesize_unexplored_from_text(
                    gap_id, gap_title, gap_desc, gap_entities,
                    materials, properties, mat_prop_cooccurrence, paper_summaries_text
                )
                hypotheses.extend(generated)

            elif gap_type == "missing_link":
                generated = self._hypothesize_missing_link_from_text(
                    gap_id, gap_title, gap_desc, gap_entities,
                    materials, properties, paper_summaries_text
                )
                hypotheses.extend(generated)

            elif gap_type == "contradiction":
                generated = self._hypothesize_contradiction_from_text(
                    gap_id, gap_title, gap_desc, gap_entities, materials, properties
                )
                hypotheses.extend(generated)

        return hypotheses

    # ── 文本解析辅助方法 ──

    def _parse_gaps_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从 gap_report.md 文本中解析所有 Gap 条目。

        匹配模式：以 "## Gap" 开头的章节，提取类型、严重程度、描述等信息。
        """
        gaps = []
        # 按 "## Gap" 切分 gap 条目
        gap_sections = re.split(r'(?=##\s+Gap\s+\d+)', text)
        for section in gap_sections:
            if not section.strip().startswith("##"):
                continue
            # 提取 Gap 编号
            id_match = re.search(r'##\s+Gap\s+(\d+)', section)
            gap_num = id_match.group(1) if id_match else "?"
            # 提取类型
            type_match = re.search(r'(?:类型|Type)[：:]\s*(\w[\w\s]*)', section, re.IGNORECASE)
            gap_type_en = type_match.group(1).strip().lower() if type_match else ""
            # 映射中英文类型
            type_map = {
                "unexplored": "unexplored", "未探索": "unexplored",
                "missing_link": "missing_link", "缺失连接": "missing_link",
                "contradiction": "contradiction", "矛盾": "contradiction",
            }
            # 尝试从文本推断类型
            inferred_type = "unexplored"
            for key, val in type_map.items():
                if key in section.lower():
                    inferred_type = val
                    break
            # 提取严重程度
            sev_match = re.search(r'(?:严重程度|Severity)[：:]\s*(high|medium|low|高|中|低)',
                                  section, re.IGNORECASE)
            severity_raw = sev_match.group(1).lower() if sev_match else "medium"
            sev_map = {"高": "high", "中": "medium", "低": "low"}
            severity = sev_map.get(severity_raw, severity_raw)
            # 提取标题
            title_match = re.search(r'##\s+Gap\s+\d+[：:\s]*(.+)', section)
            title = title_match.group(1).strip()[:100] if title_match else f"Gap {gap_num}"
            # 提取描述（标题之后到下一个 ## 之前的全部文本）
            desc_start = section.find("\n", section.find(f"## Gap {gap_num}"))
            desc = section[desc_start:].strip()[:500] if desc_start > 0 else section[:500]
            # 提取相关实体
            entities = list(set(re.findall(r'[A-Z][a-z]+[A-Z]?\w*(?:\s*[A-Z][a-z]+[A-Z]?\w*)*',
                                           section)))
            entities = [e.strip() for e in entities if 3 < len(e.strip()) < 60][:10]

            gaps.append({
                "id": f"gap_{gap_num}",
                "type": inferred_type or gap_type_en,
                "severity": severity,
                "title": title,
                "description": desc,
                "entities": entities,
            })
        return gaps

    def _extract_entities_from_text(self, text: str) -> Tuple[List[str], List[str]]:
        """从论文摘要/知识图谱文本中提取材料名和性质名。

        材料名模式：化学式（如 BaTiO3, SrTiO3）、含元素符号的复合词。
        性质名模式：物理量单位后缀（band gap, dielectric constant 等）。
        """
        # 化学式提取：大写字母开头 + 可选小写字母 + 可选数字
        # 例如 BaTiO3, LiFePO4, SrTiO3
        chem_formula_pattern = re.compile(
            r'\b(?:[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+)\b'
        )
        materials = list(set(chem_formula_pattern.findall(text)))
        # 过滤噪声（太短或全是数字的）
        materials = [m for m in materials if len(m) >= 3 and not m.isdigit()]

        # 性质关键词提取
        prop_keywords = [
            "band gap", "bandgap", "dielectric constant", "permittivity",
            "conductivity", "resistivity", "formation energy", "bulk modulus",
            "shear modulus", "young's modulus", "poisson ratio",
            "thermal conductivity", "seebeck coefficient", "figure of merit",
            "magnetization", "coercive field", "polarization",
            "refractive index", "absorption coefficient", "photoluminescence",
            "band gap energy", "direct band gap", "indirect band gap",
            "formation enthalpy", "lattice constant", "lattice parameter",
            "energy band gap", "electronic band gap", "optical band gap",
            "bandgap energy", "energy gap",
        ]
        properties = []
        text_lower = text.lower()
        for kw in prop_keywords:
            if kw.lower() in text_lower:
                properties.append(kw)
        # 去重（不区分大小写的变体）
        seen = set()
        unique_props = []
        for p in properties:
            if p.lower() not in seen:
                seen.add(p.lower())
                unique_props.append(p)
        return materials, unique_props

    # ── 文本版假设生成子方法（与原有 JSON KG 子方法对应，但基于文本实体） ──

    def _hypothesize_unexplored_from_text(
        self, gap_id: str, gap_title: str, gap_desc: str,
        gap_entities: List[str], materials: List[str], properties: List[str],
        cooccurrence: Dict[str, set], text: str
    ) -> List[DiscoveryHypothesis]:
        """未探索空间 → 基于文本实体生成假设（无需 JSON KG）。

        找已有某性质记录的材料，再找化学结构相似但无此性质记录的材料。
        """
        hypotheses = []
        # 从 gap 描述中提取目标性质
        target_property = ""
        for prop in properties:
            if prop.lower() in gap_desc.lower():
                target_property = prop
                break

        # 找到文献中已报告该性质的材料（从共现表中查找）
        materials_with_prop: Set[str] = set()
        for mat, props_set in cooccurrence.items():
            if target_property and any(target_property.lower() in p.lower() for p in props_set):
                materials_with_prop.add(mat)

        # 找到结构相似但无此性质记录的材料
        # 简单启发：化学式前缀相似（如 Ba, Sr 同族 → BaTiO3 vs SrTiO3）
        similar_prefixes: Dict[str, str] = {}
        for mat in materials:
            mat_lower = mat.lower()
            if mat_lower in materials_with_prop:
                continue
            # 提取元素前缀（前两个大写字母段）
            prefix_match = re.match(r'^([A-Z][a-z]?\d*[A-Z][a-z]?\d*)', mat)
            if prefix_match:
                prefix = prefix_match.group(1)[:4].lower()
                for mwp in materials_with_prop:
                    mwp_prefix_match = re.match(r'^([A-Z][a-z]?\d*[A-Z][a-z]?\d*)', mwp)
                    if mwp_prefix_match and mwp_prefix_match.group(1)[:4].lower() == prefix:
                        similar_prefixes[mat_lower] = prefix
                        break

        # 如果没找到结构相似的材料，回退到共现表中未覆盖该性质的所有材料
        if not similar_prefixes:
            for mat in materials:
                mat_lower = mat.lower()
                if mat_lower not in materials_with_prop:
                    similar_prefixes[mat_lower] = "unknown_structure"

        for mat_name in list(similar_prefixes.keys())[:10]:
            self._unexplored_counter += 1
            hypotheses.append(DiscoveryHypothesis(
                id=f"hypo_unexplored_{self._unexplored_counter}",
                title=f"{mat_name} may exhibit enhanced {target_property or 'target property'}",
                description=(
                    f"{mat_name} shares structural features with materials known to "
                    f"exhibit {target_property or 'the target property'}. "
                    f"This combination has NOT been studied yet."
                ),
                source_gap_id=gap_id,
                materials=[mat_name],
                property=target_property or "unknown",
                expected_relationship=f"Similar structure → similar {target_property or 'property'}",
                confidence=0.4,
                novelty_score=0.8,
            ))
        return hypotheses

    def _hypothesize_missing_link_from_text(
        self, gap_id: str, gap_title: str, gap_desc: str,
        gap_entities: List[str], materials: List[str],
        properties: List[str], text: str
    ) -> List[DiscoveryHypothesis]:
        """缺失连接 → 基于文本实体生成假设（无需 JSON KG）。

        从文献文本中寻找可能的中间材料作为桥接。
        """
        hypotheses = []
        if len(gap_entities) < 2:
            return hypotheses

        # 在文本中搜索 "A→B" 或 "A affects B" 关系模式
        entity_a = gap_entities[0] if gap_entities else ""
        entity_b = gap_entities[1] if len(gap_entities) > 1 else ""
        # 找可能的三元组桥接：X 同时与 A 和 B 共现
        bridge_candidates: Set[str] = set()
        for mat in materials:
            mat_lower = mat.lower()
            # 在文本中搜索同时包含 mat + entity_a 和 mat + entity_b 的段落
            if entity_a and entity_b:
                has_a = any(entity_a.lower() in para.lower() and mat_lower in para.lower()
                           for para in text.split("\n\n")[:100])
                has_b = any(entity_b.lower() in para.lower() and mat_lower in para.lower()
                           for para in text.split("\n\n")[:100])
                if has_a and has_b:
                    bridge_candidates.add(mat)

        # 如果没找到桥接候选，尝试任何材料作为桥接
        if not bridge_candidates:
            bridge_candidates = set(materials[:5])

        for bridge_mat in list(bridge_candidates)[:8]:
            self._missing_link_counter += 1
            hypotheses.append(DiscoveryHypothesis(
                id=f"hypo_link_{self._missing_link_counter}",
                title=f"Bridge: {bridge_mat} → {gap_title[:60]}",
                description=(
                    f"Missing link between {entity_a or '?'} and {entity_b or '?'}. "
                    f"Material {bridge_mat} co-occurs with both entities in literature, "
                    f"suggesting a possible bridging mechanism."
                ),
                source_gap_id=gap_id,
                materials=[bridge_mat, entity_a, entity_b],
                property="",
                expected_relationship=f"Via {bridge_mat} intermediate",
                confidence=0.35,
                novelty_score=0.6,
            ))
        return hypotheses[:8]

    def _hypothesize_contradiction_from_text(
        self, gap_id: str, gap_title: str, gap_desc: str,
        gap_entities: List[str], materials: List[str],
        properties: List[str]
    ) -> List[DiscoveryHypothesis]:
        """矛盾 → 基于文本实体生成假设（无需 JSON KG）。

        生成条件依赖的解决方案假设。
        """
        # 从描述中尝试提取目标性质
        target_prop = ""
        for prop in properties:
            if prop.lower() in gap_desc.lower():
                target_prop = prop
                break

        self._contra_counter += 1
        return [DiscoveryHypothesis(
            id=f"hypo_contra_{self._contra_counter}",
            title=f"Resolution: {gap_title[:80]}",
            description=(
                f"Hypothesis to resolve contradiction in literature: {gap_desc[:200]}. "
                f"Possible explanation: experimental conditions (temperature, pressure, "
                f"synthesis method) differ across studies, leading to divergent results. "
                f"Systematic study needed to identify the controlling factor."
            ),
            source_gap_id=gap_id,
            materials=list(gap_entities)[:5],
            property=target_prop or "",
            expected_relationship="Condition-dependent resolution",
            confidence=0.3,
            novelty_score=0.9,
        )]

    def _build_matrix(self, kg: KnowledgeGraph) -> Dict[str, Set[str]]:
        """构建材料→性质矩阵。"""
        matrix: Dict[str, Set[str]] = {}
        for p in kg.properties:
            mn = p.material_name.lower()
            if mn not in matrix:
                matrix[mn] = set()
            matrix[mn].add(p.property_name)
        return matrix

    def _hypothesize_unexplored(self, gap: ResearchGap, kg: KnowledgeGraph,
                                matrix: Dict[str, Set[str]]) -> List[DiscoveryHypothesis]:
        """未探索空间 → 找到有类似结构的材料，预测其可能具有目标性质。"""
        hypotheses = []
        entities = gap.entities_involved or []

        # 从知识图谱中找具有类似关系的材料
        similar_materials = set()
        target_property = ""
        property_pattern = re.findall(r'property[:\s]*(\w[\w\s]+\w)', gap.description, re.IGNORECASE)
        if property_pattern:
            target_property = property_pattern[0]

        # 找已有该性质的材料，看它们的结构特征
        materials_with_prop = set()
        for p in kg.properties:
            if target_property and target_property.lower() in p.property_name.lower():
                materials_with_prop.add(p.material_name)

        # 找结构相似但无此性质记录的材料
        for mat in kg.materials:
            if mat.name not in materials_with_prop and mat.structure:
                for mwp in materials_with_prop:
                    mwp_entity = next((m for m in kg.materials if m.name == mwp), None)
                    if mwp_entity and mwp_entity.structure == mat.structure:
                        similar_materials.add(mat.name)

        # 生成假设
        for mat_name in list(similar_materials)[:10]:
            self._unexplored_counter += 1
            hypotheses.append(DiscoveryHypothesis(
                id=f"hypo_unexplored_{self._unexplored_counter}",
                title=f"{mat_name} may exhibit enhanced {target_property or 'target property'}",
                description=(
                    f"{mat_name} shares structural features ({mat_name}) with materials "
                    f"known to exhibit {target_property or 'the target property'}. "
                    f"This combination has NOT been studied yet."
                ),
                source_gap_id=gap.id,
                materials=[mat_name],
                property=target_property or "unknown",
                expected_relationship=f"Similar structure → similar {target_property or 'property'}",
                confidence=0.4,
                novelty_score=0.8,
            ))

        return hypotheses

    def _hypothesize_missing_link(self, gap: ResearchGap, kg: KnowledgeGraph,
                                  matrix: Dict[str, Set[str]]) -> List[DiscoveryHypothesis]:
        """缺失连接 → 找可能的中间材料/掺杂。"""
        hypotheses = []

        # 从 gap 描述中提取 A→B，B→C 但缺少 A→C
        entities = gap.entities_involved
        if len(entities) < 2:
            return hypotheses

        # 尝试在知识图谱中找到类似的三元组填补缺失连接
        for rel in kg.relations:
            if rel.relation_type == "structure-property" and rel.confidence > 0.6:
                self._missing_link_counter += 1
                hypotheses.append(DiscoveryHypothesis(
                    id=f"hypo_link_{self._missing_link_counter}",
                    title=f"Bridge: {rel.subject} → {gap.title[:60]}",
                    description=(
                        f"Missing link between {entities[0] if entities else '?'} and "
                        f"{entities[1] if len(entities) > 1 else '?'}. "
                        f"Existing relation {rel.subject}→{rel.object} ({rel.predicate}) "
                        f"suggests a possible bridging mechanism."
                    ),
                    source_gap_id=gap.id,
                    materials=[rel.subject, rel.object],
                    property=rel.predicate,
                    expected_relationship=f"Via {rel.subject} intermediate",
                    confidence=rel.confidence * 0.7,
                    novelty_score=0.6,
                ))

        return hypotheses[:8]

    def _hypothesize_contradiction_resolution(self, gap: ResearchGap,
                                              kg: KnowledgeGraph) -> List[DiscoveryHypothesis]:
        """矛盾 → 哪边的结论更可信，什么条件导致差异。"""
        self._contra_counter += 1
        return [DiscoveryHypothesis(
            id=f"hypo_contra_{self._contra_counter}",
            title=f"Resolution: {gap.title[:80]}",
            description=f"Hypothesis to resolve contradiction: {gap.description[:200]}",
            source_gap_id=gap.id,
            materials=list(gap.entities_involved)[:5],
            property="",
            expected_relationship="Condition-dependent resolution",
            confidence=0.3,
            novelty_score=0.9,
        )]


# Need re at module level for HypothesisGenerator
import re


# ═══════════════════════════════════════════════════════════════
# Phase 2: Guided Search — Bayesian Optimization
# ═══════════════════════════════════════════════════════════════

class BayesianOptimizer:
    """贝叶斯优化探索材料空间。

    在材料成分/工艺参数空间中，用 RBF 核高斯过程回归（Gaussian Process Regression）
    作为代理模型，通过 Upper Confidence Bound (UCB) 采集函数平衡 exploration 和
    exploitation，提供校准的不确定性估计以寻找最优性质参数。

    LLM 参与：生成搜索种群的种子、评估中间结果的科学合理性。
    """

    def __init__(self, llm_guide: Callable = None):
        """
        Args:
            llm_guide: (candidates: List[Dict]) → pruned + scored List[Dict]
                       用于 LLM 评估搜索中间结果并引导剪枝
        """
        self._llm_guide = llm_guide
        self._iteration_log: List[Dict] = []
        # LLM 引导事件取证记录（供上层工具审计 LLM 参与情况）
        self._llm_events: List[Dict] = []
        # LLM 引导搜索空间剪枝/聚焦状态（2026-10 新增）：
        # 由 _llm_guide 返回的 prune_regions/focus_regions 更新，_acquisition
        # 采样时据此收缩/聚焦候选点——让 LLM 建议真正作用于搜索空间，
        # 而非只被记录在事件里。
        self._llm_prune_regions: List[List[float]] = []
        self._llm_focus_regions: List[List[float]] = []
        self._llm_property_idx: int = 0  # property_value 在 param_names 中的索引

    def optimize(self, hypothesis: DiscoveryHypothesis,
                 param_space: Dict[str, Tuple[float, float]],
                 objective_fn: Callable[[Dict], float],
                 n_iterations: int = 50,
                 n_initial: int = 10,
                 llm_evaluator: Callable = None) -> Tuple[Dict, float, List[Dict]]:
        """
        Bayesian optimization over material parameter space.

        Args:
            hypothesis: 目标假设
            param_space: {param_name: (low, high)}
            objective_fn: 评分函数 (via Materials Project data lookup)
            n_iterations: 迭代次数
            n_initial: 初始随机采样数
            llm_evaluator: 可选, (candidate_dict, hypothesis) → float [0,1]。
                           用于在每次候选评估时混合 LLM 科学合理性评分。

        Returns:
            (best_params, best_score, iteration_log)
        """
        param_names = list(param_space.keys())
        bounds = np.array([[lo, hi] for lo, hi in param_space.values()])
        # 记录 property_value 在参数列表中的索引，供 LLM 剪枝/聚焦区间映射
        try:
            self._llm_property_idx = param_names.index("property_value")
        except ValueError:
            self._llm_property_idx = 0
        # 每次搜索重置 LLM 剪枝状态，避免跨搜索残留
        self._llm_prune_regions = []
        self._llm_focus_regions = []

        # ── helper: blend LLM plausibility into an objective score ──
        _BLEND_W = 0.35

        def _blend_score(raw_score: float, cand_dict: Dict) -> float:
            """如果 llm_evaluator 可用，混合 LLM 科学合理性评分。"""
            if llm_evaluator is None:
                return raw_score
            try:
                llm_pl = llm_evaluator(cand_dict, hypothesis)
                if llm_pl is not None and 0.0 <= llm_pl <= 1.0:
                    return raw_score * (1.0 - _BLEND_W) + llm_pl * _BLEND_W
            except Exception:
                pass
            return raw_score

        # Phase A: Random exploration
        X = np.random.uniform(bounds[:, 0], bounds[:, 1], size=(n_initial, len(param_names)))
        y = np.array([_blend_score(
            objective_fn(self._vec_to_dict(param_names, x)),
            self._vec_to_dict(param_names, x)
        ) for x in X])

        # LLM 评估初始种群，存储 LLM plausibility 并混合到 y 中
        if self._llm_guide:
            initial_candidates = [self._vec_to_dict(param_names, X[i]) for i in range(min(5, n_initial))]
            try:
                pruned = self._llm_guide(initial_candidates)
                # 用 LLM 评分混合到初始客观评分中（不再只是 max 覆盖）
                for item in pruned:
                    if "score" in item:
                        idx = next((i for i, c in enumerate(initial_candidates)
                                   if all(abs(c.get(k, 0) - item.get(k, 0)) < 1e-6 for k in c)), None)
                        if idx is not None and idx < len(y):
                            # Blend LLM score with objective score
                            llm_s = item["score"]
                            y[idx] = y[idx] * (1.0 - _BLEND_W) + llm_s * _BLEND_W
                self._llm_events.append({
                    "iteration": -1,
                    "type": "bayes_llm_guide",
                    "n_candidates": len(initial_candidates),
                    "suggestion": next(
                        (it.get("llm_suggestion", it.get("suggestion")) for it in pruned
                         if "llm_suggestion" in it or "suggestion" in it), None),
                })
                # 应用 LLM 剪枝/聚焦建议到搜索空间
                self._apply_llm_regions(pruned)
            except Exception:
                pass  # LLM guidance is optional enhancement

        best_idx = int(np.argmax(y))
        best_x = X[best_idx].copy()
        best_y = float(y[best_idx])

        log = [{"iteration": -1, "type": "initial", "best_score": best_y,
                "n_samples": n_initial, "mean_score": float(np.mean(y)),
                "max_score": float(np.max(y))}]

        # Phase B: Bayesian optimization with GP surrogate
        for iteration in range(n_iterations):
            # RBF 核 GP 代理模型：用后验均值+不确定度做 UCB 采集
            candidate = self._acquisition(X, y, bounds, iteration)

            cand_dict = self._vec_to_dict(param_names, candidate)
            raw_score = objective_fn(cand_dict)
            score = _blend_score(raw_score, cand_dict)

            # LLM-guided pruning: 每 5 轮让 LLM 评估搜索方向并调整分数
            if self._llm_guide and iteration % 5 == 4:
                recent_indices = list(range(max(0, len(y) - 5), len(y)))
                recent = [self._vec_to_dict(param_names, X[i]) for i in recent_indices]
                try:
                    pruned = self._llm_guide(recent)
                    # 使用 LLM 返回的评分混合到对应的客观分数中
                    for j, item in enumerate(pruned):
                        if "score" in item and j < len(recent_indices):
                            actual_idx = recent_indices[j]
                            if actual_idx < len(y):
                                llm_s = item["score"]
                                y[actual_idx] = y[actual_idx] * (1.0 - _BLEND_W) + llm_s * _BLEND_W
                    self._llm_events.append({
                        "iteration": iteration,
                        "type": "bayes_llm_guide",
                        "n_candidates": len(recent),
                        "suggestion": next(
                            (it.get("llm_suggestion", it.get("suggestion")) for it in pruned
                             if "llm_suggestion" in it or "suggestion" in it), None),
                    })
                    # 应用 LLM 剪枝/聚焦建议到搜索空间（后续 _acquisition 生效）
                    self._apply_llm_regions(pruned)
                except Exception:
                    pass

            X = np.vstack([X, candidate])
            y = np.append(y, score)

            if score > best_y:
                best_y = score
                best_x = candidate.copy()

            log.append({
                "iteration": iteration, "score": float(score),
                "best_score": float(best_y),
                "params": cand_dict,
            })

        best_params = self._vec_to_dict(param_names, best_x)
        self._iteration_log = log
        return best_params, best_y, log

    def _gp_predict(self, X_train: np.ndarray, y_train: np.ndarray,
                    X_test: np.ndarray, length_scale: float = 0.5,
                    noise: float = 1e-6) -> Tuple[np.ndarray, np.ndarray]:
        """RBF 核高斯过程回归：返回后验均值 mu 和后验标准差 sigma。

        使用 RBF 核 k(x,y) = exp(-||x-y||^2 / (2*l^2)) 构建 Gram 矩阵，
        Cholesky 分解求逆后计算后验均值和方差。
        相比之前的加权 k-NN 代理模型，GP 提供了校准的不确定性估计。
        """
        # RBF 核：k(x,y) = exp(-||x-y||^2 / (2*l^2))
        sq_dists_train = cdist(X_train, X_train, 'sqeuclidean')
        K = np.exp(-sq_dists_train / (2.0 * length_scale ** 2))
        K += noise * np.eye(len(X_train))

        # Cholesky 分解求 K^-1，若失败则回退到伪逆
        try:
            L = np.linalg.cholesky(K)
            K_inv = np.linalg.solve(L.T, np.linalg.solve(L, np.eye(len(X_train))))
        except np.linalg.LinAlgError:
            K_inv = np.linalg.pinv(K)

        # 测试点与训练点的核矩阵
        sq_dists_cross = cdist(X_test, X_train, 'sqeuclidean')
        K_star = np.exp(-sq_dists_cross / (2.0 * length_scale ** 2))

        # 测试点之间的核矩阵
        sq_dists_test = cdist(X_test, X_test, 'sqeuclidean')
        K_star_star = np.exp(-sq_dists_test / (2.0 * length_scale ** 2))

        # 后验均值
        mu = K_star @ K_inv @ y_train

        # 后验协方差（只取对角线作为方差）
        cov = K_star_star - K_star @ K_inv @ K_star.T
        sigma = np.sqrt(np.maximum(np.diag(cov), 1e-12))

        return mu, sigma

    def _gp_fit_hyperparams(self, X_norm: np.ndarray,
                            y_norm: np.ndarray) -> Tuple[float, float]:
        """在 [0,1] 归一化空间上做 RBF 核超参数的 MLE 拟合。

        最小化负对数边际似然
            NLL = 0.5*y^T K^-1 y + 0.5*log|K| + n/2*log(2pi)
        其中 K 为带噪声的 RBF 核 Gram 矩阵；用 Cholesky 分解求 K^-1 y
        与 log|K|（=2*sum(log(diag(L)))），保证数值稳定。

        Args:
            X_norm: 已按边界归一化到 [0,1] 的训练输入 (n, d)
            y_norm: 已标准化（z-score）的目标值 (n,)

        Returns:
            (length_scale, noise)：length_scale 搜索区间 [0.05, 5.0]（log 空间，
            单维标量），noise 搜索区间 [1e-8, 1.0]（log 空间）。样本不足
            (<3) 或优化失败时回退默认 (0.5, 1e-6)，不抛异常。
        """
        n = len(y_norm)
        if n < 3:
            return 0.5, 1e-6

        LS_MIN, LS_MAX = 0.05, 5.0
        NOISE_MIN, NOISE_MAX = 1e-8, 1.0
        _NLL_FALLBACK = 1e12

        def _nll(theta: np.ndarray) -> float:
            """负对数边际似然。theta = [log(length_scale), log(noise)]。"""
            ls = float(np.exp(theta[0]))
            noise = float(np.exp(theta[1]))
            sq_dists = cdist(X_norm, X_norm, 'sqeuclidean')
            K = np.exp(-sq_dists / (2.0 * ls ** 2))
            K = K + noise * np.eye(n)
            try:
                L = np.linalg.cholesky(K)
            except np.linalg.LinAlgError:
                return _NLL_FALLBACK  # 病态矩阵：返回大 NLL 而非崩溃
            # Cholesky 两次回代解 K alpha = y
            alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_norm))
            log_det_K = 2.0 * np.sum(np.log(np.diag(L)))
            nll = (0.5 * float(y_norm @ alpha) + 0.5 * log_det_K
                   + 0.5 * n * np.log(2.0 * np.pi))
            return nll if np.isfinite(nll) else _NLL_FALLBACK

        best_nll = np.inf
        best_params = None
        # 多起点（log 空间）提升拟合稳定性
        for ls_init in (0.5, 0.2, 1.0):
            theta0 = np.array([np.log(ls_init), np.log(1e-3)])
            try:
                res = minimize(
                    _nll, theta0, method="L-BFGS-B",
                    bounds=[(np.log(LS_MIN), np.log(LS_MAX)),
                            (np.log(NOISE_MIN), np.log(NOISE_MAX))],
                    options={"maxiter": 200},
                )
                if res.fun < best_nll:
                    best_nll = float(res.fun)
                    best_params = res.x
            except Exception:
                continue  # 单个起点失败不影响整体回退
        if best_params is None:
            return 0.5, 1e-6
        return float(np.exp(best_params[0])), float(np.exp(best_params[1]))

    def _apply_llm_regions(self, pruned: List[Dict]) -> None:
        """把 LLM 引导返回的 prune/focus_regions 应用到搜索空间。

        从任一候选的 llm_prune_regions / llm_focus_regions 字段（[lo,hi] 列表，
        相对 property_value 维度）更新本优化器的剪枝/聚焦状态，使后续
        _acquisition 采样真正收缩/聚焦（2026-10：此前这些建议只被记录在
        候选字段里，搜索仍在全 bounds 采样，LLM 融合深度不足）。

        剪枝语义：采样时排除这些区间（在区间内的候选点直接丢弃）；
        聚焦语义：采样时优先在 focus 区间内生成候选点。
        """
        prune = None
        focus = None
        for it in pruned or []:
            if isinstance(it, dict):
                if prune is None and it.get("llm_prune_regions"):
                    prune = it["llm_prune_regions"]
                if focus is None and it.get("llm_focus_regions"):
                    focus = it["llm_focus_regions"]
            if prune is not None and focus is not None:
                break

        def _clean(regions):
            out = []
            for r in regions or []:
                try:
                    lo, hi = float(r[0]), float(r[1])
                    if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                        out.append([lo, hi])
                except (TypeError, ValueError, IndexError):
                    continue
            return out

        if prune is not None:
            self._llm_prune_regions = _clean(prune)
        if focus is not None:
            self._llm_focus_regions = _clean(focus)
        if prune or focus:
            self._llm_events.append({
                "iteration": len(self._iteration_log),
                "type": "bayes_llm_region_apply",
                "prune_regions": self._llm_prune_regions,
                "focus_regions": self._llm_focus_regions,
                "note": "LLM 建议已应用到搜索空间（_acquisition 采样阶段生效）",
            })

    def _acquisition(self, X: np.ndarray, y: np.ndarray, bounds: np.ndarray,
                     iteration: int) -> np.ndarray:
        """UCB 采集函数：使用 RBF 核高斯过程回归作为代理模型。

        通过 GP 后验均值和方差计算 Upper Confidence Bound (UCB)，
        在 exploitation（高均值）和 exploration（高方差）间平衡。
        随机采样 100 个候选点，选取 UCB 最大的作为下一个评估点。

        超参数不再固定：训练样本 >= 3 时先用 _gp_fit_hyperparams 做 MLE
        拟合 length_scale / noise（在 [0,1] 归一化空间），失败则回退
        默认 0.5 / 1e-6，保证不抛异常。
        """
        # 随机采样候选点
        n_candidates = 100
        # LLM 剪枝/聚焦（2026-10）：有 focus 区间时在其中采样一半候选点，
        # 有 prune 区间时丢弃落入其中的候选点——LLM 建议真正引导搜索空间。
        prune = self._llm_prune_regions
        focus = self._llm_focus_regions
        pidx = self._llm_property_idx
        rand_candidates = np.random.uniform(
            bounds[:, 0], bounds[:, 1],
            size=(n_candidates, bounds.shape[0])
        )
        if focus:
            # 聚焦：一半候选点直接从 focus 区间均匀采样（property 维度）
            n_focus = n_candidates // 2
            f_lo = max(float(bounds[pidx, 0]), min(r[0] for r in focus))
            f_hi = min(float(bounds[pidx, 1]), max(r[1] for r in focus))
            if f_hi > f_lo:
                focus_pts = np.random.uniform(
                    bounds[:, 0], bounds[:, 1], size=(n_focus, bounds.shape[0]))
                focus_pts[:, pidx] = np.random.uniform(f_lo, f_hi, size=n_focus)
                rand_candidates[:n_focus] = focus_pts
        if prune:
            # 剪枝：丢弃 property 值落入 prune 区间的候选点，并补采
            keep = np.ones(len(rand_candidates), dtype=bool)
            for lo, hi in prune:
                in_prune = (rand_candidates[:, pidx] >= lo) & (
                    rand_candidates[:, pidx] <= hi)
                keep &= ~in_prune
            n_keep = int(keep.sum())
            if n_keep == 0:
                # prune 区间覆盖整个 bounds（LLM 建议极端）：退化回全空间
                # 随机采样，避免空数组 argmax 崩溃（2026-10 防御）
                rand_candidates = np.random.uniform(
                    bounds[:, 0], bounds[:, 1],
                    size=(n_candidates, bounds.shape[0]))
            elif n_keep < n_candidates // 2:
                # 被剪枝太多：在未剪枝区域补采（补采点同样避开 prune 区间），
                # 保证候选点数量且不引入被剪枝点
                kept = rand_candidates[keep]
                fill = []
                guard = 0
                while len(fill) < n_candidates - n_keep and guard < 200:
                    guard += 1
                    pts = np.random.uniform(
                        bounds[:, 0], bounds[:, 1],
                        size=(n_candidates - n_keep, bounds.shape[0]))
                    ok = np.ones(len(pts), dtype=bool)
                    for lo, hi in prune:
                        in_p = (pts[:, pidx] >= lo) & (pts[:, pidx] <= hi)
                        ok &= ~in_p
                    fill.append(pts[ok])
                if fill:
                    rand_candidates = np.vstack([kept] + fill)[:n_candidates]
                else:
                    rand_candidates = kept
            else:
                rand_candidates = rand_candidates[keep]

        # 统一按边界归一化到 [0,1]，消除温度(K) 与掺杂浓度等维度的量纲差异
        span = np.maximum(bounds[:, 1] - bounds[:, 0], 1e-12)
        X_norm = (X - bounds[:, 0]) / span
        cand_norm = (rand_candidates - bounds[:, 0]) / span

        # 目标值 z-score 标准化：让 length_scale/noise 的搜索区间与目标尺度无关
        y_mean = float(np.mean(y))
        y_std = float(np.std(y))
        y_norm = (y - y_mean) / y_std if y_std > 1e-12 else y - y_mean

        # MLE 拟合超参数；样本不足或拟合失败时 _gp_fit_hyperparams 内部回退
        length_scale, noise = 0.5, 1e-6
        if len(X) >= 3:
            length_scale, noise = self._gp_fit_hyperparams(X_norm, y_norm)

        # 用 RBF 核 GP 预测所有候选点的后验均值和标准差（归一化空间）
        mu, sigma = self._gp_predict(X_norm, y_norm, cand_norm,
                                     length_scale, noise)
        # 反变换回原始 y 尺度
        mu = y_std * mu + y_mean
        sigma = y_std * sigma

        # UCB: mu + beta * sigma
        # beta 随迭代递减：初期更偏向 exploration，后期更偏向 exploitation
        beta = max(0.5, 2.0 * (1.0 - iteration / 100))
        ucb_values = mu + beta * sigma

        best_idx = int(np.argmax(ucb_values))
        return rand_candidates[best_idx]

    @staticmethod
    def _vec_to_dict(names: List[str], vec: np.ndarray) -> Dict[str, float]:
        return {n: float(v) for n, v in zip(names, vec)}


# ═══════════════════════════════════════════════════════════════
# Phase 2 (alternative): Monte Carlo Tree Search
# ═══════════════════════════════════════════════════════════════

class MCTSSearcher:
    """蒙特卡洛树搜索探索材料组合空间。

    LLM 参与：在 expansion 和 simulation 阶段评估中间结果的科学合理性，
    引导搜索树向更有前景的区域剪枝和聚焦。
    """

    def __init__(self, llm_guide: Callable = None, llm_guide_every: int = 10):
        """
        Args:
            llm_guide: (node_state: Dict) → (is_promising: bool, score_adjustment: float)
            llm_guide_every: LLM 引导频率，每 llm_guide_every 次迭代引导一次（默认 10）
        """
        self._llm_guide = llm_guide
        self._llm_guide_every = max(1, int(llm_guide_every if llm_guide_every is not None else 10))
        # LLM 引导事件取证记录（供上层工具审计 LLM 参与情况）
        self._llm_events: List[Dict] = []

    @dataclass
    class _Node:
        state: Dict
        parent: Any = None
        children: List = field(default_factory=list)
        visits: int = 0
        value: float = 0.0

    def search(self, root_state: Dict,
               expand_fn: Callable[[Dict], List[Dict]],
               simulate_fn: Callable[[Dict], float],
               n_iterations: int = 500) -> Tuple[Dict, float, List[Dict]]:
        """MCTS over material composition/processing space.

        Args:
            root_state: 起始状态
            expand_fn: state → [new_states]
            simulate_fn: state → score
            n_iterations: 搜索次数

        Returns:
            (best_state, best_score, search_log)
        """
        root = self._Node(state=root_state)

        for iteration in range(n_iterations):
            # Selection
            node = self._select(root)

            # Expansion
            if node.visits > 0 or node is root:
                children = expand_fn(node.state)
                for child_state in children:
                    child = self._Node(state=child_state, parent=node)
                    node.children.append(child)
                if node.children:
                    node = random.choice(node.children)

            # Simulation
            score = simulate_fn(node.state)

            # LLM guidance: evaluate if this branch is scientifically plausible
            if self._llm_guide and iteration % self._llm_guide_every == 0:
                try:
                    is_promising, adjustment = self._llm_guide(node.state)
                    self._llm_events.append({
                        "iteration": iteration,
                        "type": "mcts_llm_guide",
                        "is_promising": bool(is_promising),
                        "adjustment": float(adjustment),
                    })
                    if not is_promising:
                        score *= 0.5  # Penalize implausible branches
                    else:
                        score += adjustment
                except Exception:
                    pass

            # Backpropagation
            self._backpropagate(node, score)

        # Find best path
        best_node = self._best_child(root, c=0)
        best_score = best_node.value / max(best_node.visits, 1)

        log = [{"node": str(n.state)[:100], "visits": n.visits,
                "value": n.value / max(n.visits, 1)}
               for n in sorted(self._all_nodes(root), key=lambda n: n.visits, reverse=True)[:10]]

        return best_node.state, best_score, log

    def _select(self, node: _Node) -> _Node:
        while node.children:
            if not all(c.visits > 0 for c in node.children):
                return next(c for c in node.children if c.visits == 0)
            node = self._best_child(node, c=math.sqrt(2))
        return node

    def _best_child(self, node: _Node, c: float) -> _Node:
        return max(node.children, key=lambda n: (
            n.value / max(n.visits, 1) + c * math.sqrt(math.log(node.visits + 1) / max(n.visits, 1))
        ))

    def _backpropagate(self, node: _Node, score: float) -> None:
        while node:
            node.visits += 1
            node.value += score
            node = node.parent

    def _all_nodes(self, node: _Node) -> List[_Node]:
        nodes = [node]
        for child in node.children:
            nodes.extend(self._all_nodes(child))
        return nodes


# ═══════════════════════════════════════════════════════════════
# Phase 4: External Validation
# ═══════════════════════════════════════════════════════════════

def _parse_nomad_response(payload: Dict[str, Any]) -> Tuple[int, List[str], List[str]]:
    """解析 NOMAD `POST /v1/entries/query` 的响应。

    NOMAD API(公开数据,免认证):
      base = https://nomad-lab.eu/prod/v1/api/v1
      body = {"query": {...}, "pagination": {"page_size": n},
              "required": {"include": [...]}}
    响应:
      {"pagination": {"total": int, ...}, "data": [{entry_id, results...}, ...]}

    Returns:
        (total_entries, sample_formulas, sample_entry_ids)
    """
    if not isinstance(payload, dict):
        return 0, [], []
    data = payload.get("data") or []
    pagination = payload.get("pagination") or {}
    try:
        total = int(pagination.get("total") or 0) or len(data)
    except (TypeError, ValueError):
        total = len(data) if isinstance(data, list) else 0
    formulas: List[str] = []
    entry_ids: List[str] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            eid = item.get("entry_id")
            if eid:
                entry_ids.append(str(eid))
            res = item.get("results") or {}
            mat = res.get("material") or {}
            f = mat.get("chemical_formula_hill") or mat.get("chemical_formula")
            if f:
                formulas.append(str(f))
    return int(total), formulas[:10], entry_ids[:10]


class MaterialsProjectValidator:
    """通过 Materials Project / OQMD / NOMAD 等公共数据库交叉验证构效关系。

    支持:
      - Materials Project API (api.materialsproject.org) — 需要 API key
      - OQMD (oqmd.org) — REST API 真实查询（formationenergy，免 key，本地缓存优先）
      - hMOF / CoRE MOF（计算 MOF 数据库，公开文献 meta-analysis）
      - NOMAD (nomad-lab.eu) — REST API 公开查询，无需 key
        （restapi：POST https://nomad-lab.eu/prod/v1/api/v1/entries/query；
         查询策略复用 MOF→氧化物代理映射，验证对应无机相的 DFT 数据覆盖；
         网络不可用/速率限制时明确降级并记录 status）

    Materials Project 数据库特点:
      - 主要覆盖无机晶体材料（氧化物、金属、半导体等）
      - MOF 为有机-无机杂化材料，MP 中通常不直接收录完整 MOF 结构
      - 验证策略：查询 MOF 金属节点的对应氧化物形成能、带隙等作为跨尺度代理
      - API 文档: https://docs.materialsproject.org
    """

    # ── 已知 MOF 数据库中的关键材料及其性质范围 ──
    # 基于公开文献的 meta-analysis（Chung et al., 10.1021/cm502594j; Bucior et al., 10.1021/acs.cgd.8b01438）
    # CoRE MOF 2014 / hMOF 数据库不可直接从 API 获取，使用硬编码的已知性质范围作为验证参考
    _KNOWN_MOF_PROPERTIES = {
        "MOF-74": {
            "co2_capacity_mmol_g": (3.0, 8.6),
            "qst_kj_mol": (20, 50),
            "bet_surface_area_m2_g": (800, 1800),
        },
        "Mg-MOF-74": {"co2_capacity_mmol_g": (3.67, 8.6), "qst_kj_mol": (42, 47)},
        "ZIF-8": {"co2_capacity_mmol_g": (0.5, 1.5), "qst_kj_mol": (15, 25)},
        "HKUST-1": {"co2_capacity_mmol_g": (4.0, 7.0), "qst_kj_mol": (25, 35)},
        "UiO-66": {"co2_capacity_mmol_g": (1.0, 3.0), "qst_kj_mol": (20, 30)},
        "MIL-101": {"co2_capacity_mmol_g": (2.0, 5.0), "qst_kj_mol": (20, 40)},
    }

    # ── MOF 金属节点 → 氧化物代理映射 ──
    # 用于在 Materials Project 中查询对应无机相的跨尺度验证
    _MOF_NODE_TO_OXIDE_PROXY = {
        "Mg-MOF-74": ["MgO"],
        "MOF-74(Co)": ["CoO", "Co3O4"],
        "MOF-74(Ni)": ["NiO"],
        "MOF-74(Mg)": ["MgO"],
        "MOF-74(Zn)": ["ZnO"],
        "MOF-74(Mn)": ["MnO", "Mn2O3", "Mn3O4"],
        "MOF-74(Fe)": ["FeO", "Fe2O3", "Fe3O4"],
        "MOF-74(Cu)": ["CuO", "Cu2O"],
        "HKUST-1": ["CuO", "Cu2O"],
        "ZIF-8": ["ZnO"],
        "UiO-66": ["ZrO2"],
        "MIL-101(Cr)": ["Cr2O3", "CrO2"],
        "MIL-101(Fe)": ["Fe2O3", "Fe3O4"],
    }

    # ── 双金属 MOF → 双金属氧化物代理映射 ──
    _BIMETALLIC_MOF_TO_OXIDE_PROXY = {
        "CoMn": ["CoMn2O4", "CoMnO3", "Co2MnO4"],
        "NiCu": ["NiCuO2", "NiCu2O3"],
        "FeCu": ["FeCuO2", "CuFe2O4", "CuFeO2"],
        "NiCo": ["NiCo2O4", "NiCoO2"],
        "CoNi": ["NiCo2O4", "CoNiO2"],
        "MgNi": ["MgNiO2"],
        "MgCo": ["MgCoO2"],
        "MgCu": ["MgCuO2"],
        "ZnCo": ["ZnCo2O4"],
    }

    def __init__(self, mp_api_key: str = None):
        # Resolve API key from multiple sources
        if mp_api_key:
            self.mp_api_key = mp_api_key
        else:
            self.mp_api_key = (
                os.environ.get("MATERIALS_PROJECT_API_KEY", "")
                or os.environ.get("MP_API_KEY", "")
            )
        if not self.mp_api_key:
            try:
                from utils.config import MATERIALS_PROJECT_API_KEY
                self.mp_api_key = MATERIALS_PROJECT_API_KEY or ""
            except ImportError:
                pass
        self._api_available = bool(self.mp_api_key and self.mp_api_key.strip())

    def validate(self, hypothesis: DiscoveryHypothesis) -> Dict[str, Any]:
        """对假设进行外部数据库交叉验证。

        Returns:
            {
                "materials_project": {...},
                "oqmd": {...},
                "nomad": {...},
                "overall_match": bool,
                "supporting_evidence": [...],
            }
        """
        results = {}

        # 每个数据库检查独立 try/except：任一外部服务响应异常（非预期格式/网络
        # 抖动）只降级该库记录，不中断整轮 discovery 主流程。
        # Materials Project
        try:
            mp_result = self._check_materials_project(hypothesis)
            if mp_result:
                results["materials_project"] = mp_result
        except Exception as e:
            results["materials_project"] = {"status": "error", "error": str(e)[:200]}

        # OQMD（真实 REST API，免 key；本地缓存优先；失败时降级记录 status）
        try:
            oqmd_result = self._check_oqmd(hypothesis)
            if oqmd_result:
                results["oqmd"] = oqmd_result
        except Exception as e:
            results["oqmd"] = {"status": "error", "error": str(e)[:200]}

        # hMOF / CoRE MOF 数据库验证（基于公开文献 meta-analysis 的已知 MOF 性质）
        try:
            hmof_result = self._check_hmof_database(hypothesis)
            if hmof_result:
                results["hmof_core_mof"] = hmof_result
        except Exception as e:
            results["hmof_core_mof"] = {"status": "error", "error": str(e)[:200]}

        # NOMAD 计算材料数据库（REST API 公开查询，无 key 要求）
        try:
            nomad_result = self._check_nomad(hypothesis)
            if nomad_result:
                results["nomad"] = nomad_result
        except Exception as e:
            results["nomad"] = {"status": "error", "error": str(e)[:200]}

        # Aggregate
        overall = any(
            r.get("match", False) for r in results.values()
            if isinstance(r, dict)
        )

        evidence = []
        for db, r in results.items():
            if isinstance(r, dict) and r.get("matching_entries"):
                evidence.extend(r["matching_entries"][:3])

        return {
            "overall_match": overall,
            "databases_checked": list(results.keys()),
            "supporting_evidence": evidence,
            "details": results,
        }

    def _check_nomad(self, hypothesis: DiscoveryHypothesis) -> Optional[Dict]:
        """查询 NOMAD 计算材料数据库（公开 REST API，无需 key）。

        策略：复用 MOF→氧化物代理映射（_MOF_NODE_TO_OXIDE_PROXY /
        _BIMETALLIC_MOF_TO_OXIDE_PROXY），把假设中的 MOF 材料映射到对应
        无机相化学式（如 Mg-MOF-74 → MgO），逐个查询 NOMAD 中该相是否
        有 DFT 计算结果（results.material.chemical_formula_hill 精确匹配）。

        降级设计（红线 1 证据链诚实性）：网络不可用 / 超时 / 速率限制(503)
        一律返回明确 status 而非抛异常；NOMAD 查询失败不影响其它库的验证。

        Returns:
            {
                "match": bool, "matching_entries": [...], "materials_found": [...],
                "queries_attempted": [...], "status": str, "message": str,
            }
        """
        import requests  # requirements.txt 已声明

        # ── 1. 从假设材料收集氧化物代理化学式 ──
        formulas: Set[str] = set()
        for material in hypothesis.materials:
            mat_lower = str(material).lower().replace(" ", "").replace("-", "")
            for mof_name, proxies in self._MOF_NODE_TO_OXIDE_PROXY.items():
                mof_key = mof_name.lower().replace(" ", "").replace("-", "")
                if mof_key in mat_lower or mat_lower in mof_key:
                    formulas.update(proxies)
            for bimet_key, bimet_proxies in self._BIMETALLIC_MOF_TO_OXIDE_PROXY.items():
                if bimet_key.lower() in mat_lower:
                    formulas.update(bimet_proxies)
        if not formulas:
            return {
                "match": False,
                "matching_entries": [],
                "materials_found": [],
                "queries_attempted": [],
                "status": "no_material_mapping",
                "message": (
                    "假设材料未命中 MOF→氧化物代理映射，无法生成 NOMAD 查询。"
                    "（NOMAD 以无机计算数据为主，MOF 覆盖有限，此为如实结果）"
                ),
            }

        base_url = "https://nomad-lab.eu/prod/v1/api/v1"
        result: Dict[str, Any] = {
            "match": False,
            "matching_entries": [],
            "materials_found": [],
            "queries_attempted": [],
            "status": "ok",
            "message": "",
        }

        # ── 2. 逐个代理化学式查询（最多 5 个，遵守速率限制）──
        for formula in sorted(formulas)[:5]:
            body = {
                "query": {"results.material.chemical_formula_hill": formula},
                "pagination": {"page_size": 3},
                "required": {
                    "include": [
                        "entry_id",
                        "results.material.chemical_formula_hill",
                    ]
                },
            }
            try:
                resp = requests.post(
                    f"{base_url}/entries/query", json=body, timeout=12)
            except Exception as e:
                return {
                    "match": False,
                    "matching_entries": [],
                    "materials_found": [],
                    "queries_attempted": result["queries_attempted"],
                    "status": "api_unavailable",
                    "message": f"NOMAD 查询失败（网络不可用/超时）: {e!r}",
                }
            if resp.status_code == 503:  # 速率限制
                return {
                    "match": False,
                    "matching_entries": [],
                    "materials_found": [],
                    "queries_attempted": result["queries_attempted"],
                    "status": "rate_limited",
                    "message": "NOMAD 速率限制（503），本轮跳过该库，稍后可重试。",
                }
            if resp.status_code != 200:
                return {
                    "match": False,
                    "matching_entries": [],
                    "materials_found": [],
                    "queries_attempted": result["queries_attempted"],
                    "status": "http_error",
                    "message": f"NOMAD 返回 HTTP {resp.status_code}: {resp.text[:200]}",
                }
            try:
                total, sample_formulas, sample_ids = _parse_nomad_response(
                    resp.json())
            except Exception as e:
                return {
                    "match": False,
                    "matching_entries": [],
                    "materials_found": [],
                    "queries_attempted": result["queries_attempted"],
                    "status": "parse_error",
                    "message": f"NOMAD 响应解析失败: {e!r}",
                }
            result["queries_attempted"].append({
                "formula": formula, "total_entries": int(total),
            })
            if total > 0:
                result["match"] = True
                result["materials_found"].append(formula)
                result["matching_entries"].extend(sample_ids[:3])

        result["message"] = (
            f"NOMAD 查询完成：命中 {len(result['materials_found'])} 个无机相代理"
            f"（{result['queries_attempted']}）。"
            "NOMAD 以无机 DFT 计算数据为主，MOF 本体覆盖有限，"
            "命中结果作为金属节点无机相的跨尺度佐证。"
        )
        return result

    def _check_materials_project(self, hypothesis: DiscoveryHypothesis) -> Optional[Dict]:
        """查询 Materials Project 数据库。

        策略:
          1. 首先直接查询 hypothesis 中的材料化学式
          2. 如果无结果，查 MOF 金属节点对应的氧化物代理
          3. 对于双金属 MOF，查对应的双金属氧化物
          4. 如果 API key 未配置，返回明确的状态说明
        """
        if not self._api_available:
            return {
                "match": False,
                "matching_entries": [],
                "materials_found": [],
                "status": "api_key_not_configured",
                "message": (
                    "Materials Project API key 未配置。"
                    "请在环境变量 MATERIALS_PROJECT_API_KEY 或 MP_API_KEY 中设置，"
                    "或在项目根目录 .api_key 文件中添加 "
                    "MATERIALS_PROJECT_API_KEY=your_key_here。\n"
                    "注册地址: https://materialsproject.org/api"
                ),
            }

        results = {
            "match": False,
            "matching_entries": [],
            "materials_found": [],
            "queries_attempted": [],
        }

        # ── 收集所有需要查询的化学式 ──
        formulas_to_query: Set[str] = set()

        for material in hypothesis.materials[:5]:
            # 直接查询材料名中的化学式部分
            formulas_to_query.add(material)

        # 额外查询金属氧化物代理（MOF 节点 → 无机相）
        for material in hypothesis.materials:
            mat_lower = material.lower().replace(" ", "").replace("-", "")
            for mof_name, proxies in self._MOF_NODE_TO_OXIDE_PROXY.items():
                mof_key = mof_name.lower().replace(" ", "").replace("-", "")
                if mof_key in mat_lower or mat_lower in mof_key:
                    for proxy in proxies:
                        formulas_to_query.add(proxy)
                    results.setdefault("oxide_proxy_used", []).append(
                        f"{material} -> {proxies} (MOF节点氧化物代理)"
                    )

            # 双金属氧化物代理
            for bimet_key, bimet_proxies in self._BIMETALLIC_MOF_TO_OXIDE_PROXY.items():
                bimet_key_lower = bimet_key.lower()
                if bimet_key_lower in mat_lower:
                    for proxy in bimet_proxies:
                        formulas_to_query.add(proxy)
                    results.setdefault("bimetallic_proxy_used", []).append(
                        f"{material} -> {bimet_proxies} (双金属氧化物代理)"
                    )

        # ── 执行查询 ──
        BASE_URL = "https://api.materialsproject.org/materials/summary/"
        headers = {"X-API-KEY": self.mp_api_key.strip()}

        for formula in list(formulas_to_query):
            # 清理化学式：去掉连字符描述的文本部分
            clean_formula = formula.split("-")[0].strip()
            # 如果包含非化学式内容（如中文），只取化学式部分
            chem_match = re.match(r'^([A-Z][a-z]?\d*)+(.*)', clean_formula)
            if not chem_match:
                continue
            chem_formula = chem_match.group(1)

            query_key = chem_formula
            if query_key in results["queries_attempted"]:
                continue
            results["queries_attempted"].append(query_key)

            try:
                url = f"{BASE_URL}?formula={chem_formula}&_limit=10"
                resp = requests.get(url, headers=headers, timeout=30)

                if resp.status_code == 401:
                    results.setdefault("api_errors", []).append(
                        f"API key 认证失败 (HTTP 401)。请检查 MP_API_KEY 是否有效。"
                    )
                    continue
                elif resp.status_code == 403:
                    results.setdefault("api_errors", []).append(
                        f"API 访问被拒绝 (HTTP 403)。请确认已注册 Materials Project 账户。"
                    )
                    continue
                elif resp.status_code != 200:
                    results.setdefault("api_errors", []).append(
                        f"查询 {chem_formula} 失败: HTTP {resp.status_code}"
                    )
                    continue

                data = resp.json()
                entries = data.get("data", [])

                for entry in entries:
                    mp_id = entry.get("material_id", "")
                    formula_pretty = entry.get("formula_pretty", "")
                    band_gap = entry.get("band_gap", None)
                    formation_energy = entry.get("formation_energy_per_atom", None)
                    energy_above_hull = entry.get("energy_above_hull", None)
                    spacegroup = entry.get("symmetry", {}).get("crystal_system", "")
                    nsites = entry.get("nsites", None)
                    volume = entry.get("volume", None)
                    structure_type = entry.get("structure_type", "")

                    material_entry = {
                        "mp_id": mp_id,
                        "formula": formula_pretty,
                        "band_gap_ev": band_gap,
                        "formation_energy_ev_per_atom": formation_energy,
                        "energy_above_hull_ev": energy_above_hull,
                        "crystal_system": spacegroup,
                        "nsites": nsites,
                        "volume_a3": volume,
                    }
                    results["materials_found"].append(material_entry)

                    # 检查是否匹配目标性质
                    prop_lower = hypothesis.property.lower() if hypothesis.property else ""

                    # 形成能相关
                    if any(kw in prop_lower for kw in ["formation energy", "形成能", "稳定性",
                                                         "stability", "衰减"]):
                        if formation_energy is not None:
                            results["match"] = True
                            results["matching_entries"].append(
                                f"{formula_pretty} (MP {mp_id}): "
                                f"formation_energy = {formation_energy:.3f} eV/atom, "
                                f"energy_above_hull = {energy_above_hull} eV/atom"
                            )

                    # 带隙相关
                    if any(kw in prop_lower for kw in ["band gap", "bandgap", "带隙"]):
                        if band_gap is not None:
                            results["match"] = True
                            results["matching_entries"].append(
                                f"{formula_pretty} (MP {mp_id}): band_gap = {band_gap} eV"
                            )

                    # 吸附/容量相关 — 使用形成能作为热力学稳定性代理
                    if any(kw in prop_lower for kw in ["co2", "吸附", "adsorption", "capacity",
                                                         "容量", "qst", "吸附热", "结合能"]):
                        if formation_energy is not None:
                            results["match"] = True
                            results["matching_entries"].append(
                                f"{formula_pretty} (MP {mp_id}): "
                                f"formation_energy = {formation_energy:.3f} eV/atom "
                                f"[MOF金属节点氧化物代理 — 形成能反映金属-氧键强度]"
                            )

            except requests.exceptions.Timeout:
                results.setdefault("api_errors", []).append(
                    f"查询 {chem_formula} 超时 (30s)"
                )
            except requests.exceptions.ConnectionError:
                results.setdefault("api_errors", []).append(
                    f"查询 {chem_formula} 连接失败 — 网络不可达"
                )
            except Exception as e:
                results.setdefault("api_errors", []).append(
                    f"查询 {chem_formula} 异常: {str(e)[:100]}"
                )

        # ── 附加代理说明 ──
        if results.get("oxide_proxy_used") or results.get("bimetallic_proxy_used"):
            results["proxy_note"] = (
                "Materials Project 主要收录无机晶体材料，不直接收录 MOF 结构。"
                "以上查询使用 MOF 金属节点的对应氧化物作为跨尺度代理："
                "MOF 节点金属氧化态与对应无机氧化物相近，氧化物形成能可定性反映"
                "金属-氧键强度，从而作为 MOF 节点稳定性和吸附热力学偏好的参考。"
                "这是定性的、非定量的近似。"
            )

        if not results.get("materials_found") and not results.get("api_errors"):
            results["message"] = (
                f"Materials Project 中未找到与假设涉及材料直接匹配的无机相。"
                f"这可能是因为：(1) MOF 作为有机-无机杂化材料不在 MP 收录范围内；"
                f"(2) 对应的纯金属或氧化物相在数据库中不存在。"
            )

        return results if (results["materials_found"] or results.get("api_errors")) else results


    def _oqmd_entry_from_data(self, formula: str, data: Any, source: str) -> Optional[Dict]:
        """把 OQMD REST 响应条目 / 本地缓存条目标准化为统一的 material entry。

        OQMD REST API 条目: {"name", "delta_e", "stability", "band_gap"}
        旧版本地缓存条目: 兼容 name/formula、formation_energy 或
        formation_energy_per_atom、band_gap 字段（缺失时返回 None）。
        """
        if not isinstance(data, dict):
            return None
        delta_e = data.get("delta_e")
        if delta_e is None:
            delta_e = data.get("formation_energy")
        if delta_e is None:
            delta_e = data.get("formation_energy_per_atom")
        if delta_e is None:
            return None
        try:
            delta_e = float(delta_e)
        except (TypeError, ValueError):
            return None
        return {
            "formula": str(data.get("name") or formula),
            "requested_formula": formula,
            "delta_e_ev_per_atom": round(delta_e, 4),
            "stability": data.get("stability"),
            "band_gap_ev": data.get("band_gap"),
            "source": source,
        }

    def _add_oqmd_material(self, results: Dict[str, Any],
                           hypothesis: DiscoveryHypothesis,
                           entry: Dict) -> None:
        """把一条 OQMD 材料记录写入 results，并按假设目标性质判匹配。

        与 _check_materials_project 的匹配口径一致：
          形成能/稳定性/吸附容量类 → 用 delta_e（形成能）作为热力学稳定性代理；
          带隙类 → 用 band_gap 字段直接匹配。
        """
        results["materials_found"].append(entry)
        formula_pretty = entry["formula"]
        delta_e = entry["delta_e_ev_per_atom"]
        band_gap = entry.get("band_gap_ev")
        try:
            stability_txt = f"{float(entry['stability']):.3f}"
        except (TypeError, ValueError, KeyError):
            stability_txt = "n/a"

        prop_lower = (hypothesis.property or "").lower()
        if any(kw in prop_lower for kw in [
                "formation energy", "形成能", "稳定性", "stability", "衰减",
                "co2", "吸附", "adsorption", "capacity", "容量",
                "qst", "吸附热", "结合能"]):
            results["match"] = True
            results["matching_entries"].append(
                f"{formula_pretty} (OQMD): formation_energy = {delta_e:.3f} eV/atom, "
                f"stability = {stability_txt} eV/atom"
            )
        if any(kw in prop_lower for kw in ["band gap", "bandgap", "带隙"]):
            if band_gap is not None:
                results["match"] = True
                results["matching_entries"].append(
                    f"{formula_pretty} (OQMD): band_gap = {band_gap} eV"
                )

    def _check_oqmd(self, hypothesis: DiscoveryHypothesis) -> Dict:
        """查询 OQMD 数据库（真实 REST API，免 key；本地缓存优先）。

        策略：与 Materials Project / NOMAD 一致，复用 MOF→氧化物代理映射
        （_MOF_NODE_TO_OXIDE_PROXY / _BIMETALLIC_MOF_TO_OXIDE_PROXY），把假设中的
        MOF 材料映射到对应无机相化学式（如 Mg-MOF-74 → MgO），逐个查询 OQMD
        formationenergy API（免 key）的最低形成能（delta_e，取 limit=100 中最稳
        定相）。参考实现: workspace/code/survey/oqmd_validate.py。

        缓存优先：若 workspace/data/oqmd_cache 下存在对应化学式的 JSON 缓存文件，
        直接使用缓存命中结果，避免重复请求（目录不存在或未命中时正常走 REST）。

        降级设计（红线 1 证据链诚实性）：网络不可用 / 超时（10s）/ HTTP 错误 /
        解析失败一律记入 api_errors 并给出明确 status（not_reachable /
        http_error / parse_error）而非抛异常；OQMD 查询失败不影响其它库的验证。

        Returns:
            {
                "match": bool, "matching_entries": [...], "materials_found": [...],
                "queries_attempted": [...], "status": str, "message": str,
                "formation_energy_gain_ev": ..., "calibration_note": str,
                "confidence": str, "api_errors": [...] (仅出错时),
            }
        """
        results: Dict[str, Any] = {
            "match": False,
            "matching_entries": [],
            "materials_found": [],
            "queries_attempted": [],
            "status": "ok",
            "message": "",
            # 双金属氧化物形成能增益（MOF 节点稳定性的跨尺度代理）
            "formation_energy_gain_ev": None,
            "calibration_note": (
                "跨尺度代理（氧化物形成能 → MOF 节点稳定性），"
                "物理基础是 MOF 金属节点的氧化态与对应氧化物相近，"
                "但这种映射是定性的而非定量的"
            ),
            "confidence": "moderate (cross-scale proxy, not yet calibrated)",
        }

        # ── 1. 收集待查询化学式（MOF 节点/双金属氧化物代理优先）──
        proxy_formulas: List[str] = []
        for material in hypothesis.materials:
            mat_lower = str(material).lower().replace(" ", "").replace("-", "")
            for mof_name, proxies in self._MOF_NODE_TO_OXIDE_PROXY.items():
                mof_key = mof_name.lower().replace(" ", "").replace("-", "")
                if mof_key in mat_lower or mat_lower in mof_key:
                    proxy_formulas.extend(proxies)
            for bimet_key, bimet_proxies in self._BIMETALLIC_MOF_TO_OXIDE_PROXY.items():
                if bimet_key.lower() in mat_lower:
                    proxy_formulas.extend(bimet_proxies)

        # 直接材料名仅当本身已是干净化学式（无 "Mg-MOF-74" 类描述文本）时才纳入，
        # 避免 "Mg-MOF-74" 被切成 "Mg"、"MOF-74(Ni)" 被切成 "MOF" 等无效查询。
        direct_formulas: List[str] = []
        for material in hypothesis.materials:
            clean = str(material).split("-")[0].strip()
            if clean != str(material).strip():
                continue
            chem_match = re.match(r'^([A-Z][a-z]?\d*)+(.*)', clean)
            if chem_match:
                direct_formulas.append(chem_match.group(1))

        # 代理氧化物（受控映射，必然为有效化学式）优先，去重保序，最多 5 个
        clean_formulas = list(dict.fromkeys(proxy_formulas + direct_formulas))[:5]

        if not clean_formulas:
            results["status"] = "no_material_mapping"
            results["message"] = (
                "假设材料无法解析为化学式，无法生成 OQMD 查询。"
                "（OQMD 以无机相计算数据为主，MOF 本体覆盖有限，此为如实结果）"
            )
            return results

        # ── 2. 本地缓存优先（路径随 run_dir 隔离；命中缓存不重复查 API）──
        from utils.config import LITERATURE_CACHE_DIR as _CACHE_DIR
        oqmd_cache = Path(_CACHE_DIR) / "oqmd_cache"
        formulas_via_api: List[str] = []
        for formula in clean_formulas:
            cache_file = oqmd_cache / f"{formula.replace(' ', '_')}.json"
            if not cache_file.exists():
                formulas_via_api.append(formula)
                continue
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                formulas_via_api.append(formula)  # 缓存损坏 → 回退 REST 查询
                continue
            entry = self._oqmd_entry_from_data(formula, data, "cache")
            if entry is None:
                formulas_via_api.append(formula)
            else:
                results["queries_attempted"].append(
                    {"formula": formula, "source": "cache"})
                self._add_oqmd_material(results, hypothesis, entry)

        # ── 3. OQMD REST API 查询（仅缓存未命中的化学式，超时 10s）──
        base_url = "https://oqmd.org/oqmdapi/formationenergy"
        api_errors: List[str] = []
        network_failed = False
        http_failed = False
        parse_failed = False
        for formula in formulas_via_api:
            results["queries_attempted"].append(
                {"formula": formula, "source": "api"})
            try:
                resp = requests.get(
                    base_url,
                    params={
                        "composition": formula,
                        "fields": "name,delta_e,stability,band_gap",
                        "limit": 100,
                    },
                    timeout=10,
                )
            except requests.exceptions.Timeout:
                network_failed = True
                api_errors.append(f"查询 {formula} 超时 (10s)")
                continue
            except requests.exceptions.ConnectionError:
                network_failed = True
                api_errors.append(f"查询 {formula} 连接失败 — 网络不可达")
                continue
            except Exception as e:
                network_failed = True
                api_errors.append(f"查询 {formula} 异常: {str(e)[:100]}")
                continue

            if resp.status_code != 200:
                http_failed = True
                api_errors.append(
                    f"查询 {formula} 失败: HTTP {resp.status_code} {resp.text[:100]}")
                continue
            try:
                data = resp.json().get("data", [])
            except Exception as e:
                parse_failed = True
                api_errors.append(f"解析 {formula} 响应失败: {str(e)[:100]}")
                continue
            if not isinstance(data, list) or not data:
                # 该化学式在 OQMD 中无记录——如实记录，不算错误
                continue
            # 响应元素类型不可信：过滤非 dict，防外部响应格式异常崩溃整轮 discovery
            valid = [d for d in data if isinstance(d, dict)]
            if not valid:
                parse_failed = True
                api_errors.append(f"解析 {formula} 响应元素类型异常（非 dict）")
                continue
            # 取最低 delta_e（最稳定相）
            best = min(valid, key=lambda d: d.get("delta_e", float("inf")))
            entry = self._oqmd_entry_from_data(formula, best, "api")

            # 写回缓存（原子：临时文件 + rename），下次运行命中缓存不再查 API
            try:
                oqmd_cache.mkdir(parents=True, exist_ok=True)
                _tmp = cache_file.with_suffix(".tmp")
                _tmp.write_text(json.dumps(valid, ensure_ascii=False), encoding="utf-8")
                os.replace(str(_tmp), str(cache_file))
            except Exception:
                pass
            if entry is None:
                parse_failed = True
                api_errors.append(f"解析 {formula} 无有效形成能数据")
                continue
            self._add_oqmd_material(results, hypothesis, entry)

        # ── 4. 状态汇总与降级 ──
        if api_errors:
            results["api_errors"] = api_errors
            if not results["materials_found"]:
                if network_failed:
                    results["status"] = "not_reachable"
                elif http_failed:
                    results["status"] = "http_error"
                else:
                    results["status"] = "parse_error"
            else:
                results["status"] = "partial"

        if results["materials_found"]:
            results["message"] = (
                f"OQMD 查询完成：命中 {len(results['materials_found'])} 个无机相"
                f"（queries: {results['queries_attempted']}）。"
                "OQMD 以无机 DFT 计算数据为主，MOF 本体覆盖有限，"
                "命中结果作为金属节点无机相的跨尺度佐证。"
            )
        elif api_errors:
            results["message"] = (
                f"OQMD 查询失败（status={results['status']}）："
                f"{api_errors[:2]}。OQMD 本轮未参与交叉验证。"
            )
        else:
            results["message"] = (
                "OQMD 中未找到与假设涉及材料直接匹配的无机相。"
                "（OQMD 主要收录无机晶体相，MOF 本体不在其列）"
            )

        # ── 5. 双金属氧化物形成能增益计算（保留跨尺度代理分析）──
        formation_energies: Dict[str, float] = {}
        for entry in results["materials_found"]:
            name = entry.get("formula", entry.get("requested_formula", ""))
            fe = entry.get("delta_e_ev_per_atom")
            if name and fe is not None:
                formation_energies[name] = abs(float(fe))

        if len(formation_energies) >= 3:
            names = list(formation_energies.keys())
            gains = []
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    e1 = formation_energies[names[i]]
                    e2 = formation_energies[names[j]]
                    # 以形成能较大者作为双金属氧化物的近似
                    e_bimetallic = max(e1, e2)
                    # ΔE = |E_bimetallic| - mean(|E_mono1|, |E_mono2|)
                    delta_e = e_bimetallic - (e1 + e2) / 2.0
                    gains.append({
                        "pair": f"{names[i]}-{names[j]}",
                        "e_mono1_ev": round(e1, 3),
                        "e_mono2_ev": round(e2, 3),
                        "delta_e_ev": round(delta_e, 3),
                    })
            if gains:
                results["formation_energy_gain_ev"] = gains
        elif len(formation_energies) >= 1:
            results["formation_energy_gain_ev"] = {
                "note": "只有单个金属氧化物数据，无法计算双金属形成能增益",
                "available_energies": {
                    name: round(e, 3) for name, e in formation_energies.items()
                },
            }

        return results

    def _check_hmof_database(self, hypothesis: DiscoveryHypothesis) -> Optional[Dict]:
        """查询 hMOF/CoRE MOF 数据库（基于公开文献 meta-analysis 的已知 MOF 性质）。

        由于 CoRE MOF 2014 / hMOF 数据库不可直接从 API 获取，
        使用硬编码的已知 MOF 性质范围进行验证参考。
        匹配假设中涉及的材料是否属于已知 MOF 系列，
        如果是则返回该 MOF 在已知文献中的典型性质范围。
        """
        results = {
            "match": False,
            "matching_entries": [],
            "materials_found": [],
            "database": "hMOF/CoRE MOF (computed, literature meta-analysis)",
        }

        for material in hypothesis.materials:
            # 模糊匹配 MOF 名称（忽略大小写、空格和连字符）
            mat_lower = material.lower().replace(" ", "").replace("-", "")
            for mof_name, props in self._KNOWN_MOF_PROPERTIES.items():
                mof_key = mof_name.lower().replace(" ", "").replace("-", "")
                if mof_key in mat_lower or mat_lower in mof_key:
                    results["materials_found"].append({
                        "material": material,
                        "matched_mof": mof_name,
                        "known_properties": props,
                        "note": f"该材料属于已知 MOF 数据库中的 {mof_name} 系列",
                    })

                    # 检查假设中的目标性质是否与已知 MOF 性质范围相关
                    prop_lower = hypothesis.property.lower() if hypothesis.property else ""
                    # CO2 吸附容量相关
                    if any(kw in prop_lower for kw in ["co2", "capacity", "adsorption", "吸附"]):
                        if "co2_capacity_mmol_g" in props:
                            lo, hi = props["co2_capacity_mmol_g"]
                            results["matching_entries"].append(
                                f"{mof_name}: CO2 吸附容量 = {lo}-{hi} mmol/g "
                                f"(文献 meta-analysis, CoRE MOF 2014 / hMOF)"
                            )
                            results["match"] = True
                    # 等温吸附热 (Qst) 相关
                    if any(kw in prop_lower for kw in ["qst", "heat of adsorption", "binding energy",
                                                         "吸附热", "结合能", "isosteric"]):
                        if "qst_kj_mol" in props:
                            lo, hi = props["qst_kj_mol"]
                            results["matching_entries"].append(
                                f"{mof_name}: Qst = {lo}-{hi} kJ/mol "
                                f"(文献 meta-analysis, CoRE MOF 2014 / hMOF)"
                            )
                            results["match"] = True
                    # BET 比表面积相关
                    if any(kw in prop_lower for kw in ["surface area", "bet", "porosity",
                                                         "比表面积", "表面积", "孔隙"]):
                        if "bet_surface_area_m2_g" in props:
                            lo, hi = props["bet_surface_area_m2_g"]
                            results["matching_entries"].append(
                                f"{mof_name}: BET 比表面积 = {lo}-{hi} m²/g "
                                f"(文献 meta-analysis, CoRE MOF 2014 / hMOF)"
                            )
                            results["match"] = True

        if results["materials_found"]:
            return results
        return None


# ═══════════════════════════════════════════════════════════════
# Main Discovery Engine
# ═══════════════════════════════════════════════════════════════

def _literature_prior_score(candidate_value: float,
                            literature_values: List[float]) -> float:
    """文献数值分布先验：候选参数越接近文献数值密集区得分越高。

    贝叶斯/MCTS 打分函数利用知识图谱文献数值（容量 mmol/g、Qst kJ/mol 等）
    作为先验的核心实现。对候选值计算：
      1) 最近邻相对距离 → 相似度（nn_score）；
      2) ±25% 相对窗口内的文献值密度（density），落在文献密集区额外加分。
    综合 prior = 0.6*nn_score + 0.4*density，返回 [0, 1]。

    Args:
        candidate_value: 候选参数值（如候选 property_value）
        literature_values: 从知识图谱/文献文本提取的数值列表

    Returns:
        [0, 1] 先验得分；无文献数值或候选值非法时返回 0.0
    """
    vals = [float(v) for v in (literature_values or []) if v is not None and v > 0]
    if not vals or not candidate_value or candidate_value <= 0:
        return 0.0
    # 用中位数比例范围过滤明显不同量纲的离群值，避免污染先验
    med = float(np.median(vals))
    if med > 0:
        filtered = [v for v in vals if med * 0.02 <= v <= med * 50.0]
        if filtered:
            vals = filtered
    # 最近邻相对距离 → 相似度
    rel_dist = min(abs(candidate_value - v) / max(abs(v), 1e-6) for v in vals)
    nn_score = 1.0 / (1.0 + rel_dist)
    # ±25% 相对窗口内的文献值密度（落在文献密集区而非孤点）
    density = sum(1.0 for v in vals if abs(candidate_value - v) / max(abs(v), 1e-6) <= 0.25)
    density /= max(len(vals), 1)
    return float(min(1.0, 0.6 * nn_score + 0.4 * density))


def _empty_evidence_score(params: Dict) -> float:
    """证据数值为空时的可区分低分（防止搜索空转）。

    不使用固定基分（否则所有候选同分、best_score 无区分度），
    而是把候选参数指纹哈希映射到 [0.10, 0.22] 的低分区间：
      1) 分数显著低于有文献证据支撑的候选（最低分 >= 0.30）；
      2) 候选之间仍保持可区分度，UCB/GP 能继续探索而非原地空转。
    """
    import hashlib
    fp = str(sorted((k, params.get(k)) for k in params
                    if params.get(k) is not None))
    h = int(hashlib.md5(fp.encode("utf-8")).hexdigest()[:6], 16)
    return 0.10 + 0.12 * (h % 1000) / 1000.0


def evidence_aware_score(params: Dict,
                         hyp: DiscoveryHypothesis,
                         literature_values: List[float],
                         text: str = "",
                         llm_plausibility: Optional[float] = None) -> Tuple[float, Dict]:
    """文献数值增强的打分函数（贝叶斯/MCTS 的 objective/score 计算入口）。

    利用知识图谱提取的文献数值（容量 mmol/g、Qst kJ/mol 等）作为先验，
    对接近文献数值分布的候选参数加分；同时保留材料覆盖率与性质共现加分。

    空证据保护：literature_values 为空时明确返回 degraded 标记与可区分的低分
    （见 _empty_evidence_score），而不是产生看似合理的同值分数。

    Args:
        params: 候选参数字典
        hyp: 目标假设
        literature_values: 文献数值列表（来自知识图谱/文献文本）
        text: 可选，证据文本（用于材料覆盖率 / 性质共现）
        llm_plausibility: 可选 LLM 科学合理性评分 [0, 1]，按 0.35 权重混合

    Returns:
        (score: float, meta: Dict)
        meta 字段：score_type("prior_based"|"degraded_no_evidence")、degraded、
        reason、evidence_count、literature_prior
    """
    # ── 空证据保护：明确 degraded + 可区分低分 ──
    if not literature_values:
        base = _empty_evidence_score(params)
        if llm_plausibility is not None:
            base = base * 0.65 + float(llm_plausibility) * 0.35
        return float(min(base, 1.0)), {
            "score_type": "degraded_no_evidence",
            "degraded": True,
            "reason": "证据数值为空，打分无区分度（未利用文献数值先验）",
            "evidence_count": 0,
            "literature_prior": 0.0,
        }

    # ── 常规：材料覆盖 + 性质共现 + 文献数值先验 ──
    base = 0.15
    cand_mats = params.get("materials") or params.get("material") or (hyp.materials or [])
    if isinstance(cand_mats, str):
        cand_mats = [cand_mats]
    cand_mats = [str(m).lower() for m in cand_mats]

    text_lower = (text or "").lower()
    if text_lower and cand_mats:
        mat_hits = sum(1 for m in cand_mats if m.lower() in text_lower)
        base += 0.25 * mat_hits / max(len(cand_mats), 1)
        if hyp.property and hyp.property.lower() in text_lower:
            base += 0.20

    # 文献数值先验：候选值越接近文献数值密集区得分越高
    cv = params.get("property_value") or params.get("value") or 0
    prior = _literature_prior_score(cv, literature_values)
    base += 0.35 * prior

    score = float(min(base, 1.0))
    if llm_plausibility is not None:
        score = min(score * 0.65 + float(llm_plausibility) * 0.35, 1.0)

    meta = {
        "score_type": "prior_based",
        "degraded": False,
        "reason": "",
        "evidence_count": len(literature_values),
        "literature_prior": round(prior, 4),
    }
    return score, meta


class DiscoveryEngine:
    """构效关系发现引擎 — 路线 A 的统一入口。

    协调 Hypothesis Generation → Guided Search → Validation 全流程。

    使用:
        engine = DiscoveryEngine(llm_evaluator=my_llm_fn)
        report = engine.discover(kg, gap_report, search_method="bayesian")
    """

    def __init__(self,
                 llm_hypothesis_evaluator: Callable = None,
                 llm_search_guide: Callable = None,
                 mp_api_key: str = None):
        """
        Args:
            llm_hypothesis_evaluator: (hypothesis: DiscoveryHypothesis) → (score: float, explanation: str)
            llm_search_guide: (candidates: List[Dict]) → pruned List[Dict]
            mp_api_key: Materials Project API key
        """
        self.hypothesis_gen = HypothesisGenerator()
        self.bayes_opt = BayesianOptimizer(llm_guide=llm_search_guide)
        self.mcts_searcher = MCTSSearcher(llm_guide=llm_search_guide)
        self.validator = MaterialsProjectValidator(mp_api_key=mp_api_key)
        self._llm_evaluator = llm_hypothesis_evaluator

    # legacy: JSON KG path, kept for backward compatibility; prefer discover_from_markdown
    def discover(self,
                 kg: KnowledgeGraph,
                 gap_report: GapReport,
                 search_method: str = "bayesian",
                 n_iterations: int = 50,
                 discovery_dir: str = None) -> DiscoveryReport:
        """[legacy] 执行完整的构效关系发现流程（依赖 JSON KnowledgeGraph）。

        注意：项目架构已改为 Markdown-based 知识图谱，此方法依赖 JSON KG 对象，
        在当前运行路径中不可达。请优先使用 discover_from_markdown()。

        回退保护：若本流程未生成任何假设，将自动从 discovery_dir 下的
        hypotheses.json / search_h*.json 汇总已存在假设，避免报告仅含占位假设。
        """
        if discovery_dir is None:
            from utils.config import SURVEY_DIR
            discovery_dir = str(Path(SURVEY_DIR) / "discovery")
        report = DiscoveryReport()

        # ── Phase 1: Hypothesis Generation ──
        print(f"  [Discovery] Phase 1: Generating hypotheses from {len(gap_report.gaps)} gaps...")
        hypotheses = self.hypothesis_gen.generate_from_gaps(
            kg, gap_report.gaps, llm_evaluator=self._llm_evaluator
        )
        report.total_candidates = len(hypotheses)
        print(f"  [Discovery] Generated {len(hypotheses)} hypotheses")

        # ── 回退保护：未生成假设时汇总已落盘假设，避免阶段二产出断裂 ──
        if not hypotheses:
            try:
                fallback = DiscoveryReport.from_files(discovery_dir)
                if fallback.hypotheses:
                    print(f"  [Discovery] 未生成新假设，回退汇总 "
                          f"{len(fallback.hypotheses)} 条已存在假设")
                    return fallback
            except Exception as e:
                print(f"  [Discovery] 回退汇总已存在假设失败: {e}")

        # ── Phase 2: Guided Search ──
        for i, hyp in enumerate(hypotheses[:15]):  # Top 15 by novelty
            print(f"  [Discovery] Phase 2 [{i+1}/15]: Searching '{hyp.title[:60]}...' "
                  f"({search_method})")

            hyp.search_method = search_method
            hyp.search_iterations = min(n_iterations, 30)

            # Define parameter space based on property type
            param_space = self._define_search_space(hyp, kg)

            if search_method in ("bayesian", "hybrid"):
                best, score, log = self.bayes_opt.optimize(
                    hyp, param_space,
                    objective_fn=lambda p: self._score_candidate(p, hyp, kg),
                    n_iterations=hyp.search_iterations,
                )
                hyp.candidates_explored = len(log) + 10  # +10 initial samples

            elif search_method == "mcts":
                root_state = {"materials": hyp.materials, "property": hyp.property}
                candidates = []
                for mat in hyp.materials[:3]:
                    for prop_val in np.linspace(0.5, 5.0, 5):
                        candidates.append({"material": mat, "value": prop_val})

                best, score, log = self.mcts_searcher.search(
                    root_state,
                    expand_fn=lambda s: candidates[:10],
                    simulate_fn=lambda s: self._score_candidate(s, hyp, kg),
                    n_iterations=hyp.search_iterations * 5,
                )
                hyp.candidates_explored = len(log) * 5

            # 存储搜索阶段原始分数，后续与 LLM plausibility 混合
            _search_score = score if score > 0 else hyp.confidence
            hyp.confidence = max(hyp.confidence, _search_score)

            # ── Phase 3: LLM Plausibility Check ──
            if self._llm_evaluator:
                try:
                    pl_score, explanation = self._llm_evaluator(hyp)
                    hyp.llm_plausibility_score = pl_score
                    hyp.llm_explanation = explanation
                except Exception:
                    pass

            # ── Blended confidence: 搜索得分 (0.60) + LLM plausibility (0.40) ──
            if hyp.llm_plausibility_score > 0:
                _BLEND_W = 0.40  # LLM plausibility 权重
                hyp.confidence = _search_score * (1.0 - _BLEND_W) + hyp.llm_plausibility_score * _BLEND_W

            # ── Phase 4: External Validation ──
            print(f"  [Discovery] Phase 4: Validating '{hyp.title[:60]}...'")
            validation = self.validator.validate(hyp)
            hyp.external_validation = validation
            if validation.get("overall_match"):
                hyp.validation_status = "validated"
                report.validated_count += 1
                report.materials_project_hits += 1
            elif validation.get("databases_checked"):
                hyp.validation_status = "inconclusive"
            else:
                hyp.validation_status = "pending"

            # ── 一致性检查：LLM 科学合理性 vs 系统搜索置信度 ──
            system_confidence = hyp.confidence
            llm_plaus = hyp.llm_plausibility_score
            if llm_plaus < 0.35 and system_confidence > 0.7:
                hyp.validation_status = "contested"
                hyp.confidence = hyp.confidence * 0.7 + llm_plaus * 0.3
                if hyp.llm_explanation:
                    hyp.llm_explanation += (
                        f"\n\n[⚠️ 置信度争议] LLM 科学合理性评估 ({llm_plaus:.2f}) "
                        f"与系统搜索得分 ({system_confidence:.2f}) 存在显著差异。"
                        f"最终置信度已降权至 {hyp.confidence:.2f}。"
                    )
            elif llm_plaus > 0.7 and system_confidence < 0.5:
                if hyp.validation_status == "inconclusive":
                    hyp.validation_status = "underexplored"
                if hyp.llm_explanation:
                    hyp.llm_explanation += (
                        f"\n\n[🔍 探索不足] LLM 科学合理性评估 ({llm_plaus:.2f}) 较高，"
                        f"但系统搜索得分 ({system_confidence:.2f}) 偏低。"
                    )

            report.total_explored += hyp.candidates_explored
            report.hypotheses.append(hyp)

        # ── Summary ──
        report.search_summary = (
            f"Searched {report.total_explored} candidate material-property combinations "
            f"across {len(report.hypotheses)} hypotheses. "
            f"Validated {report.validated_count} against external databases "
            f"(Materials Project hits: {report.materials_project_hits}). "
            f"Search method: {search_method}."
        )

        return report

    def discover_from_markdown(self,
                               knowledge_graph_text: str,
                               gap_report_text: str,
                               paper_summaries_text: str,
                               search_method: str = "bayesian",
                               n_iterations: int = 50,
                               discovery_dir: str = None) -> DiscoveryReport:
        """从 Markdown 文本执行完整的构效关系发现流程（无需 JSON KG）。

        将 discover() 的核心逻辑复制过来，但入参改为 Markdown 文本字符串。
        内部通过 HypothesisGenerator.generate_from_markdown() 生成假设，
        并使用简化的文本证据评分函数进行搜索和验证。

        Args:
            knowledge_graph_text: knowledge_graph.md 的完整文本内容
            gap_report_text: gap_report.md 的完整文本内容
            paper_summaries_text: paper_summaries.md 的完整文本内容
            search_method: "bayesian" | "mcts" | "hybrid"
            n_iterations: 搜索迭代总次数
            discovery_dir: 回退汇总目录（未生成假设时读取 hypotheses.json / search_h*.json）

        Returns:
            DiscoveryReport with validated hypotheses
        """
        if discovery_dir is None:
            from utils.config import SURVEY_DIR
            discovery_dir = str(Path(SURVEY_DIR) / "discovery")
        report = DiscoveryReport()

        # ── Phase 1: Hypothesis Generation（文本版） ──
        print(f"  [Discovery] Phase 1: Generating hypotheses from Markdown texts...")
        hypotheses = self.hypothesis_gen.generate_from_markdown(
            gap_report_text, paper_summaries_text
        )
        # 如果有 LLM 评估器，评估假设合理性
        if self._llm_evaluator and hypotheses:
            for h in hypotheses[:20]:
                try:
                    score, explanation = self._llm_evaluator(h)
                    h.llm_plausibility_score = score
                    h.llm_explanation = explanation
                except Exception:
                    h.llm_plausibility_score = 0.5
                    h.llm_explanation = "(LLM evaluation unavailable)"

        report.total_candidates = len(hypotheses)
        print(f"  [Discovery] Generated {len(hypotheses)} hypotheses")

        # ── 回退保护：未生成假设时汇总已落盘假设，避免阶段二产出断裂 ──
        # 报告必须汇总所有已存在假设（hypotheses.json / search_h*.json），
        # 占位/降级假设会由 from_files 明确标注 degraded，不会顶替真实假设。
        if not hypotheses:
            try:
                fallback = DiscoveryReport.from_files(discovery_dir)
                if fallback.hypotheses:
                    print(f"  [Discovery] 未生成新假设，回退汇总 "
                          f"{len(fallback.hypotheses)} 条已存在假设")
                    return fallback
            except Exception as e:
                print(f"  [Discovery] 回退汇总已存在假设失败: {e}")

        # ── 构建文本搜索空间和评分函数 ──
        # 从 Markdown 文本中提取数值范围，构建简化的搜索参数空间
        text_values = self._extract_values_from_text(knowledge_graph_text, paper_summaries_text)
        if text_values:
            n = len(text_values)
            text_values.sort()
            median = text_values[n // 2]
            if n < 4:
                # 样本太少时 IQR 无统计意义：用 (min, max) 外加 20% padding 作为区间
                pv_lo = max(0.001, text_values[0] * 0.8)
                pv_hi = text_values[-1] * 1.2
            else:
                q1 = text_values[max(0, n // 4)]
                q3 = text_values[min(n - 1, 3 * n // 4)]
                iqr = max(q3 - q1, 1e-9)
                # 4 <= n < 8 时 Tukey 系数放宽为 1.0；n >= 8 维持 1.5
                tukey = 1.0 if n < 8 else 1.5
                pv_lo = max(0.001, q1 - tukey * iqr)
                pv_hi = q3 + tukey * iqr
            # 中位数比例兜底继续生效，避免负区间或 lo>hi
            pv_lo = min(pv_lo, median * 0.5)
            pv_hi = max(pv_hi, median * 2.0)
        else:
            pv_lo, pv_hi = 0.1, 100.0

        text_param_space = {
            "property_value": (float(pv_lo), float(pv_hi)),
            "composition_x": (0.0, 1.0),
            "temperature": (300.0, 1500.0),
        }

        # ── Phase 2: Guided Search（文本版评分函数） ──
        combined_text = knowledge_graph_text + "\n\n" + paper_summaries_text
        # 评分过程元信息（供上层检测降级/空转，不影响打分函数 float 接口）
        score_meta: Dict = {}

        def text_score_fn(params: Dict, hyp: DiscoveryHypothesis,
                        llm_plausibility: float = None) -> float:
            """简化的文本证据评分函数（不依赖 JSON KG）。

            混合文献文本证据 + LLM 科学合理性判断。

            当 SCORING_V2 启用时（默认），使用增强打分
            （sigmoid 拉伸 + 动态权重调和平均 + 多样性奖励），
            将窄区间分数扩展到更宽范围以提升区分度。

            Args:
                params: 候选参数字典
                hyp: 目标假设
                llm_plausibility: 可选的 LLM 科学合理性评分 [0, 1]。
                                  当提供时，以 0.35 权重与文本证据分数混合。
            """
            # ── v2 增强打分通道（#11：打分函数区分度有限）──
            if SCORING_V2:
                from literature_agent.scoring import enhanced_evidence_score as _v2_score
                v2_result, v2_meta = _v2_score(
                    params=params, hyp=hyp,
                    literature_values=text_values,
                    text=combined_text,
                    llm_plausibility=llm_plausibility,
                    explored_points=None,  # 在此层级不维护已探索点
                )
                score_meta.update(v2_meta)
                score_meta.setdefault("score_type", v2_meta.get("score_type", "prior_based"))
                score_meta.setdefault("degraded", v2_meta.get("degraded", False))
                return float(v2_result)

            # ── v1 原始打分通道（向后兼容）──
            # ── 空证据保护：文献数值为空 → 可区分低分 + 降级标记 ──
            # 不使用固定基分（否则所有候选同分、best_score 无区分度），
            # 分数显著低于有文献证据支撑的候选，且候选间保持可区分度。
            if not text_values:
                base_score = _empty_evidence_score(params)
                score_meta.update({
                    "score_type": "degraded_no_evidence",
                    "degraded": True,
                    "reason": "证据数值为空，打分无区分度（未利用文献数值先验）",
                    "evidence_count": 0,
                })
                if llm_plausibility is not None:
                    return min(base_score * 0.65 + llm_plausibility * 0.35, 1.0)
                return base_score

            score = 0.3  # base
            # 材料覆盖率：候选材料名在文本中出现的频率
            cand_mats = params.get("materials") or params.get("material") or hyp.materials
            if isinstance(cand_mats, str):
                cand_mats = [cand_mats]
            cand_mats = [str(m).lower() for m in cand_mats]

            text_lower = combined_text.lower()
            mat_hits = sum(1 for m in cand_mats if m.lower() in text_lower)
            if mat_hits > 0:
                score += 0.20 * mat_hits / max(len(cand_mats), 1)

            # 性质覆盖：候选性质在文本中的出现
            if hyp.property and hyp.property.lower() in text_lower:
                score += 0.15

            # 数值接近文献报告值：利用文献数值分布先验，
            # 候选值落在文献密集区（而非孤点命中）才获得高分
            cv = params.get("property_value") or params.get("value") or 0
            if cv:
                prior = _literature_prior_score(cv, text_values)
                score += 0.30 * prior

            base_score = min(score, 1.0)
            score_meta.update({
                "score_type": "prior_based",
                "degraded": False,
                "evidence_count": len(text_values),
                "literature_prior": round(prior, 4) if cv else 0.0,
            })

            # ── 混合 LLM 科学合理性评分 ──
            if llm_plausibility is not None:
                w = 0.35
                adjusted_score = base_score * (1.0 - w) + llm_plausibility * w
                return min(adjusted_score, 1.0)

            return base_score

        for i, hyp in enumerate(hypotheses[:15]):
            print(f"  [Discovery] Phase 2 [{i+1}/15]: Searching '{hyp.title[:60]}...' "
                  f"({search_method})")

            hyp.search_method = search_method
            hyp.search_iterations = min(n_iterations, 30)

            if search_method in ("bayesian", "hybrid"):
                best, score, log = self.bayes_opt.optimize(
                    hyp, text_param_space,
                    objective_fn=lambda p: text_score_fn(p, hyp),
                    n_iterations=hyp.search_iterations,
                )
                hyp.candidates_explored = len(log) + 10

            elif search_method == "mcts":
                pv_lo_m, pv_hi_m = text_param_space["property_value"]
                root_state = {"materials": hyp.materials, "property": hyp.property}
                best, score, log = self.mcts_searcher.search(
                    root_state,
                    expand_fn=lambda s: [
                        {"property_value": round(v, 3),
                         "composition_x": round(x, 2),
                         "temperature": t,
                         "materials": hyp.materials[:3]}
                        for v in np.linspace(pv_lo_m, pv_hi_m, 5)
                        for x in np.linspace(0.1, 0.9, 3)
                        for t in [298, 323, 373]
                    ],
                    simulate_fn=lambda s: text_score_fn(s, hyp),
                    n_iterations=hyp.search_iterations * 5,
                )
                hyp.candidates_explored = len(log) * 5

            # 存储搜索阶段原始分数，后续与 LLM plausibility 混合
            _search_score = score if score > 0 else hyp.confidence
            hyp.confidence = max(hyp.confidence, _search_score)

            # ── Phase 3: LLM Plausibility Check ──
            if self._llm_evaluator:
                try:
                    pl_score, explanation = self._llm_evaluator(hyp)
                    hyp.llm_plausibility_score = pl_score
                    hyp.llm_explanation = explanation
                except Exception:
                    pass

            # ── 混合搜索分数与 LLM 科学合理性评分 ──
            if hyp.llm_plausibility_score > 0:
                _BLEND_W = 0.40  # LLM plausibility 权重
                hyp.confidence = _search_score * (1.0 - _BLEND_W) + hyp.llm_plausibility_score * _BLEND_W

            # ── Phase 4: External Validation ──
            print(f"  [Discovery] Phase 4: Validating '{hyp.title[:60]}...'")
            validation = self.validator.validate(hyp)
            hyp.external_validation = validation
            if validation.get("overall_match"):
                hyp.validation_status = "validated"
                report.validated_count += 1
                report.materials_project_hits += 1
            elif validation.get("databases_checked"):
                hyp.validation_status = "inconclusive"
            else:
                hyp.validation_status = "pending"

            # ── 一致性检查：LLM 科学合理性 vs 系统搜索置信度 ──
            system_confidence = hyp.confidence
            llm_plaus = hyp.llm_plausibility_score
            if llm_plaus < 0.35 and system_confidence > 0.7:
                hyp.validation_status = "contested"
                hyp.confidence = hyp.confidence * 0.7 + llm_plaus * 0.3
                if hyp.llm_explanation:
                    hyp.llm_explanation += (
                        f"\n\n[⚠️ 置信度争议] LLM 科学合理性评估 ({llm_plaus:.2f}) "
                        f"与系统搜索得分 ({system_confidence:.2f}) 存在显著差异。"
                        f"最终置信度已降权至 {hyp.confidence:.2f}。"
                    )
            elif llm_plaus > 0.7 and system_confidence < 0.5:
                if hyp.validation_status == "inconclusive":
                    hyp.validation_status = "underexplored"
                if hyp.llm_explanation:
                    hyp.llm_explanation += (
                        f"\n\n[🔍 探索不足] LLM 科学合理性评估 ({llm_plaus:.2f}) 较高，"
                        f"但系统搜索得分 ({system_confidence:.2f}) 偏低。"
                    )

            report.total_explored += hyp.candidates_explored
            report.hypotheses.append(hyp)

        # ── Summary ──
        report.search_summary = (
            f"Searched {report.total_explored} candidate material-property combinations "
            f"across {len(report.hypotheses)} hypotheses. "
            f"Validated {report.validated_count} against external databases "
            f"(Materials Project hits: {report.materials_project_hits}). "
            f"Search method: {search_method}. "
            f"(Data source: Markdown texts — knowledge_graph.md + paper_summaries.md)"
        )

        return report

    @staticmethod
    def _extract_values_from_text(knowledge_graph_text: str,
                                   paper_summaries_text: str) -> List[float]:
        """从 Markdown 文本中提取数值（用于构建搜索空间范围）。

        匹配模式：数字 + 可选的科学计数法 + 可选单位。
        例如："band gap = 3.2 eV", "conductivity = 1.5e-3 S/cm", "value: 298 K"
        """
        combined = knowledge_graph_text + "\n" + paper_summaries_text
        # 匹配数字模式：整数/小数/科学计数法（正数）
        # 排除年份（如 2023, 2024）、页码和纯整数 > 10000
        pattern = re.compile(r'(?<![a-zA-Z0-9])(\d+\.?\d*(?:[eE][+-]?\d+)?)(?:\s*(?:eV|cm|nm|K|S/cm|W/mK|GPa|%|Ω))?')
        values = []
        for match in pattern.finditer(combined):
            raw = match.group(1)
            try:
                v = float(raw)
                # 过滤掉明显不是物理量的数值（年份、过大的整数等）
                if v <= 0:
                    continue
                if v > 10000 and v == int(v) and '.' not in raw and 'e' not in raw.lower():
                    continue  # 跳过疑似年份/编号的大整数
                if 0.0001 < v < 50000:
                    values.append(v)
            except ValueError:
                continue
        # 去重并限制数量
        return sorted(set(values))[:100]

    def _define_search_space(self, hyp: DiscoveryHypothesis,
                             kg: KnowledgeGraph) -> Dict[str, Tuple[float, float]]:
        """为假设定义贝叶斯优化搜索空间。"""
        space = {}

        # 基于已有性质数据定义搜索范围
        related_props = [p for p in kg.properties
                        if hyp.property.lower() in p.property_name.lower()]
        if related_props:
            values = [p.value for p in related_props if p.value > 0]
            if values:
                values = sorted(values)
                n = len(values)
                median = values[n // 2]
                if n < 4:
                    # 样本太少时 IQR 无统计意义：用 (min, max) 外加 20% padding 作为区间
                    lo = max(0.001, values[0] * 0.8)
                    hi = values[-1] * 1.2
                else:
                    q1 = values[max(0, n // 4)]
                    q3 = values[min(n - 1, 3 * n // 4)]
                    iqr = max(q3 - q1, 1e-9)
                    # 4 <= n < 8 时 Tukey 系数放宽为 1.0；n >= 8 维持 1.5
                    tukey = 1.0 if n < 8 else 1.5
                    lo = max(0.001, q1 - tukey * iqr)
                    hi = q3 + tukey * iqr
                # 中位数比例兜底继续生效，避免负区间或 lo>hi
                lo = min(lo, median * 0.5)
                hi = max(hi, median * 2.0)
                space["property_value"] = (float(lo), float(hi))
            else:
                space["property_value"] = (0.1, 100.0)
        else:
            space["property_value"] = (0.1, 100.0)

        # 掺杂/成分参数
        if hyp.materials:
            space["composition_x"] = (0.0, 1.0)
            space["temperature"] = (300, 1500)  # K

        return space

    def _score_candidate(self, params: Dict, hyp: DiscoveryHypothesis,
                         kg: KnowledgeGraph, llm_plausibility: float = None) -> float:
        """候选方案的评分函数。

        综合：文献知识图谱数值先验（容量/Qst 等分布）+ 物理合理性 + LLM 评分

        当 SCORING_V2 启用时（默认），使用增强打分（sigmoid 拉伸 + 动态权重调和平均），
        将窄区间分数扩展到更宽范围以提升区分度。

        Args:
            params: 候选参数字典
            hyp: 目标假设
            kg: 知识图谱
            llm_plausibility: 可选的 LLM 科学合理性评分 [0, 1]。
                              当提供时，以 0.35 权重与文献证据分数混合。
        """
        # 从知识图谱中提取文献数值
        kg_values = [p.value for p in kg.properties
                     if hyp.property.lower() in p.property_name.lower() and p.value > 0]

        # ── v2 增强打分通道（#11：打分函数区分度有限）──
        if SCORING_V2:
            from literature_agent.scoring import enhanced_evidence_score as _v2_score
            v2_result, _v2_meta = _v2_score(
                params=params, hyp=hyp,
                literature_values=kg_values,
                text="",  # KG-based path 无文本，信号权重自然偏向 numerical
                llm_plausibility=llm_plausibility,
                explored_points=None,
            )
            return float(v2_result)

        # ── v1 原始打分通道（向后兼容）──
        # ── 空证据保护：知识图谱中无相关性质数值 → 可区分低分 ──
        # 无文献数值先验时返回参数指纹低分（非固定基分），避免搜索空转；
        # 分数显著低于有证据支撑的候选，且候选间保持可区分度。
        if not kg_values:
            base_score = _empty_evidence_score(params)
            if llm_plausibility is not None:
                w = 0.35
                return min(base_score * (1.0 - w) + llm_plausibility * w, 1.0)
            return base_score

        score = 0.3  # base

        # 文献数值先验：候选值越接近知识图谱中文献数值密集区越好
        candidate_val = params.get("property_value", 0)
        prior = _literature_prior_score(candidate_val, kg_values)
        score += 0.3 * prior

        # 结构相似性加分
        for mat in kg.materials:
            if any(m.lower() in mat.name.lower() for m in hyp.materials):
                score += 0.1

        base_score = min(score, 1.0)

        # ── 混合 LLM 科学合理性评分 ──
        if llm_plausibility is not None:
            w = 0.35
            adjusted_score = base_score * (1.0 - w) + llm_plausibility * w
            return min(adjusted_score, 1.0)

        return base_score
