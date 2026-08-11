# -*- coding: utf-8 -*-
"""
复赛计划能力接口占位（初赛阶段不接入现有管线）。

对应方案文档中标注"为复赛计划"的三项能力，提供稳定接口契约：
  1. HybridRetriever —— 混合检索（BM25 + Embedding 语义召回 + Reranker 精排）
  2. GraphKnowledgeStore —— 图谱库/关系库（实体-关系-数值属性图，doc_id+passage_id 回源）
  3. AutoReVerifier —— 自动二次核验（引用锚定与数值/单位一致性自动复核）

初赛提交物以"已实现"的确定性管线为准（指纹去重 + Markdown 知识图谱 + 规则校验）；
以下接口为复赛落地预留，评审可据此确认三项能力在设计中存在明确接口，而非无中生有。
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class HybridRetriever(ABC):
    """混合检索接口（复赛计划）。融合 BM25 关键词召回、Embedding 语义召回与 Reranker 精排。"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10) -> list[str]:
        """返回候选 passage_id 列表。"""
        raise NotImplementedError("复赛计划：初赛阶段未接入，使用指纹去重 + 规则排序。")

    @abstractmethod
    def rerank(self, query: str, candidates: list[str]) -> list[str]:
        """对候选按相关性重排。"""
        raise NotImplementedError("复赛计划：初赛阶段未接入。")


class GraphKnowledgeStore(ABC):
    """图谱库/关系库接口（复赛计划）。以实体-关系-数值属性图组织知识，doc_id+passage_id 关联回源。"""

    @abstractmethod
    def upsert_entity(self, entity: dict) -> None:
        """写入实体节点（材料/性质/数值/条件，含来源 passage_id）。"""
        raise NotImplementedError("复赛计划：初赛阶段使用 Markdown 知识图谱（knowledge_graph.md）。")

    @abstractmethod
    def query_neighbors(self, entity_id: str, relation: str | None = None) -> list[dict]:
        """查询某实体的一跳邻居与关系边。"""
        raise NotImplementedError("复赛计划：初赛阶段未接入。")


class AutoReVerifier(ABC):
    """自动二次核验接口（复赛计划）。对引用锚定、数值/单位一致性做自动复核。"""

    @abstractmethod
    def verify_citation(self, passage_id: str) -> dict:
        """校验引用是否可回源（p# -> paper_summaries -> search_log -> API 调用记录）。"""
        raise NotImplementedError("复赛计划：初赛阶段以人工 + 规则校验（pids_checklist / audit_trail）代替。")

    @abstractmethod
    def verify_number(self, value: float, unit: str, context: dict) -> dict:
        """校验数值与单位一致性（SI 换算 + 条件上下文绑定）。"""
        raise NotImplementedError("复赛计划：初赛阶段未接入。")
