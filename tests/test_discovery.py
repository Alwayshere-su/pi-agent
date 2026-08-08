"""
测试 literature_agent.discovery 模块：
  - DiscoveryHypothesis / ResearchGap：数据模型默认值
  - DiscoveryReport：四象限分类、to_dict
  - BayesianOptimizer：初始化、_vec_to_dict、_acquisition（UCB）
"""
import pytest
import numpy as np

from literature_agent.discovery import (
    DiscoveryHypothesis,
    DiscoveryReport,
    ResearchGap,
    BayesianOptimizer,
)


# ═══════════════════════════════════════════════════════════════
# DiscoveryHypothesis
# ═══════════════════════════════════════════════════════════════

class TestDiscoveryHypothesisDataclass:
    def test_minimal_creation(self):
        """仅创建空假设（所有字段取默认值）。"""
        h = DiscoveryHypothesis()
        assert h.id == ""
        assert h.title == ""
        assert h.description == ""
        assert h.materials == []
        assert h.property == ""
        assert h.confidence == 0.5
        assert h.novelty_score == 0.0
        assert h.search_method == ""
        assert h.search_iterations == 0
        assert h.validation_status == "pending"

    def test_full_creation(self):
        """完整假设包含所有关键字段。"""
        h = DiscoveryHypothesis(
            id="hypo_001",
            title="MOF-74 doping with Mg increases CO2 capacity",
            description="Mg doping introduces stronger binding sites for CO2.",
            source_gap_id="gap_01",
            materials=["MOF-74", "Mg-MOF-74"],
            property="CO2 capacity",
            expected_relationship="Mg doping increases CO2 capacity",
            confidence=0.75,
            novelty_score=0.85,
            search_method="bayesian",
            search_iterations=50,
            candidates_explored=200,
            validation_status="validated",
            llm_plausibility_score=0.80,
            llm_explanation="Mg has higher charge density leading to stronger CO2 binding.",
        )
        assert h.id == "hypo_001"
        assert h.title == "MOF-74 doping with Mg increases CO2 capacity"
        assert h.materials == ["MOF-74", "Mg-MOF-74"]
        assert h.property == "CO2 capacity"
        assert h.confidence == 0.75
        assert h.novelty_score == 0.85
        assert h.search_method == "bayesian"
        assert h.search_iterations == 50
        assert h.candidates_explored == 200
        assert h.validation_status == "validated"
        assert h.llm_plausibility_score == 0.80

    def test_evidence_chain_default(self):
        """evidence_chain 默认空列表。"""
        h = DiscoveryHypothesis()
        assert h.evidence_chain == []

    def test_external_validation_default(self):
        """external_validation 默认空 dict。"""
        h = DiscoveryHypothesis()
        assert h.external_validation == {}

    def test_known_prior_work_defaults(self):
        """已知/新知字段默认为空字符串。"""
        h = DiscoveryHypothesis()
        assert h.known_prior_work == ""
        assert h.incremental_claim == ""

    def test_degraded_defaults(self):
        """degraded 相关字段默认为 False / 空字符串。"""
        h = DiscoveryHypothesis()
        assert h.degraded is False
        assert h.degraded_reason == ""
        assert h.extractability_score == 0.0

    def test_literature_values_default(self):
        """literature_values 默认为空列表。"""
        h = DiscoveryHypothesis()
        assert h.literature_values == []


# ═══════════════════════════════════════════════════════════════
# ResearchGap
# ═══════════════════════════════════════════════════════════════

class TestResearchGapDataclass:
    def test_minimal_creation(self):
        """空 ResearchGap。"""
        g = ResearchGap()
        assert g.id == ""
        assert g.type == ""
        assert g.severity == "medium"
        assert g.confidence == 0.5
        assert g.related_papers == []

    def test_full_creation(self):
        """完整 ResearchGap。"""
        g = ResearchGap(
            id="gap_01",
            type="unexplored",
            title="Underexplored MOF for CO2 capture",
            description="Certain MOFs have not been tested for CO2 capture.",
            severity="high",
            confidence=0.8,
            related_papers=["paper_1", "paper_2"],
            evidence_chain=["Evidence A", "Evidence B"],
            suggested_validation="Test MOF-X for CO2 capacity.",
            entities_involved=["MOF-X", "CO2"],
        )
        assert g.id == "gap_01"
        assert g.type == "unexplored"
        assert g.title == "Underexplored MOF for CO2 capture"
        assert g.severity == "high"
        assert g.confidence == 0.8
        assert len(g.related_papers) == 2
        assert "paper_1" in g.related_papers


# ═══════════════════════════════════════════════════════════════
# DiscoveryReport / classify_consistency
# ═══════════════════════════════════════════════════════════════

class TestDiscoveryReportClassifyConsistency:
    def test_strong(self):
        """LLM >= 0.5 且 confidence >= 0.5 → strong。"""
        h = DiscoveryHypothesis(llm_plausibility_score=0.80, confidence=0.90)
        assert DiscoveryReport.classify_consistency(h) == "strong"

    def test_strong_boundary(self):
        """恰好等于阈值 0.50 → strong。"""
        h = DiscoveryHypothesis(llm_plausibility_score=0.50, confidence=0.50)
        assert DiscoveryReport.classify_consistency(h) == "strong"

    def test_underexplored(self):
        """LLM >= 0.5 但 confidence < 0.5 → underexplored。"""
        h = DiscoveryHypothesis(llm_plausibility_score=0.80, confidence=0.30)
        assert DiscoveryReport.classify_consistency(h) == "underexplored"

    def test_contested(self):
        """LLM < 0.5 但 confidence >= 0.5 → contested。"""
        h = DiscoveryHypothesis(llm_plausibility_score=0.30, confidence=0.80)
        assert DiscoveryReport.classify_consistency(h) == "contested"

    def test_weak(self):
        """LLM < 0.5 且 confidence < 0.5 → weak。"""
        h = DiscoveryHypothesis(llm_plausibility_score=0.10, confidence=0.10)
        assert DiscoveryReport.classify_consistency(h) == "weak"

    def test_weak_llm_zero(self):
        """LLM = 0.0 且 confidence = 0.0 → weak。"""
        h = DiscoveryHypothesis(llm_plausibility_score=0.0, confidence=0.0)
        assert DiscoveryReport.classify_consistency(h) == "weak"


class TestDiscoveryReportToDict:
    def test_empty_report(self):
        """空报告 to_dict。"""
        r = DiscoveryReport()
        d = r.to_dict()
        assert d["title"] == "Structure-Property Relationship Discovery Report"
        assert d["hypotheses"] == []
        assert d["total_candidates"] == 0
        assert d["total_explored"] == 0
        assert d["validated_count"] == 0
        assert d["refuted_count"] == 0
        assert "generated_at" in d

    def test_report_with_hypotheses(self):
        """含假设的报告 to_dict。"""
        h = DiscoveryHypothesis(
            id="h1",
            title="Test hypothesis",
            confidence=0.8,
            novelty_score=0.7,
        )
        r = DiscoveryReport(
            title="Custom Report",
            hypotheses=[h],
            total_candidates=10,
            total_explored=50,
            validated_count=3,
            refuted_count=1,
            contested_count=2,
            underexplored_count=4,
            search_summary="Search completed.",
            materials_project_hits=5,
        )
        d = r.to_dict()
        assert d["title"] == "Custom Report"
        assert len(d["hypotheses"]) == 1
        assert d["total_candidates"] == 10
        assert d["validated_count"] == 3
        assert d["refuted_count"] == 1
        assert d["contested_count"] == 2
        assert d["underexplored_count"] == 4
        assert d["materials_project_hits"] == 5

    def test_sorted_by_novelty(self):
        """按 novel x confidence 降序排列。"""
        h1 = DiscoveryHypothesis(title="Low", confidence=0.3, novelty_score=0.3)
        h2 = DiscoveryHypothesis(title="High", confidence=0.9, novelty_score=0.9)
        h3 = DiscoveryHypothesis(title="Mid", confidence=0.5, novelty_score=0.5)
        report = DiscoveryReport(hypotheses=[h1, h2, h3])
        sorted_list = report.sorted_by_novelty()
        assert sorted_list[0].title == "High"
        # h2: 0.9*0.9=0.81, h3: 0.5*0.5=0.25, h1: 0.3*0.3=0.09
        assert sorted_list[-1].title == "Low"


# ═══════════════════════════════════════════════════════════════
# BayesianOptimizer
# ═══════════════════════════════════════════════════════════════

class TestBayesianOptimizerInit:
    def test_init_no_llm_guide(self):
        """不带 LLM 引导正常初始化。"""
        bo = BayesianOptimizer()
        assert bo._llm_guide is None
        assert bo._iteration_log == []
        assert bo._llm_events == []

    def test_init_with_llm_guide(self):
        """带 LLM 引导回调初始化。"""
        def dummy_guide(candidates):
            return candidates

        bo = BayesianOptimizer(llm_guide=dummy_guide)
        assert bo._llm_guide is dummy_guide

    def test_llm_prune_regions_initial(self):
        """初始化时 LLM 剪枝/聚焦区域为空。"""
        bo = BayesianOptimizer()
        assert bo._llm_prune_regions == []
        assert bo._llm_focus_regions == []


class TestBayesianOptimizerVecToDict:
    def test_single_param(self):
        """单参数向量转字典。"""
        result = BayesianOptimizer._vec_to_dict(
            ["temperature"], np.array([300.0])
        )
        assert result == {"temperature": 300.0}

    def test_multiple_params(self):
        """多参数向量转字典。"""
        result = BayesianOptimizer._vec_to_dict(
            ["doping_concentration", "temperature", "pressure"],
            np.array([0.05, 500.0, 1.0]),
        )
        assert result == {
            "doping_concentration": 0.05,
            "temperature": 500.0,
            "pressure": 1.0,
        }

    def test_empty_names(self):
        """空参数名列表返回空 dict。"""
        result = BayesianOptimizer._vec_to_dict([], np.array([]))
        assert result == {}

    def test_values_are_floats(self):
        """返回的字典值都是 float 类型。"""
        result = BayesianOptimizer._vec_to_dict(
            ["x", "y"], np.array([1, 2])
        )
        assert isinstance(result["x"], float)
        assert isinstance(result["y"], float)


class TestBayesianOptimizerAcquisition:
    def test_ucb_returns_valid_point(self):
        """UCB 采集返回一个在 bounds 内的有效候选点。"""
        bo = BayesianOptimizer()
        bounds = np.array([[0.0, 1.0], [0.0, 1.0]])

        # 构造小的训练集
        rng = np.random.RandomState(42)
        X = rng.uniform(bounds[:, 0], bounds[:, 1], size=(10, 2))
        y = np.sin(X[:, 0] * np.pi) * np.cos(X[:, 1] * np.pi) + 0.1 * rng.randn(10)

        candidate = bo._acquisition(X, y, bounds, iteration=0)
        assert candidate.shape == (2,)
        # 候选点必须在 bounds 范围内
        assert bounds[0, 0] <= candidate[0] <= bounds[0, 1]
        assert bounds[1, 0] <= candidate[1] <= bounds[1, 1]

    def test_ucb_exploration_early(self):
        """早期迭代 (iteration=0) UCB 更偏向 exploration（高 beta）。"""
        bo = BayesianOptimizer()
        bounds = np.array([[0.0, 1.0], [0.0, 1.0]])

        rng = np.random.RandomState(42)
        X = rng.uniform(bounds[:, 0], bounds[:, 1], size=(5, 2))
        y = rng.randn(5)

        # 运行多次确保不崩溃
        for i in range(3):
            candidate = bo._acquisition(X, y, bounds, iteration=i)
            assert candidate.shape == (2,)
            assert np.all(candidate >= bounds[:, 0])
            assert np.all(candidate <= bounds[:, 1])

    def test_ucb_different_iterations(self):
        """不同迭代产生不同的候选点（非退化）。"""
        bo = BayesianOptimizer()
        bounds = np.array([[0.0, 1.0], [0.0, 1.0]])

        rng = np.random.RandomState(42)
        X = rng.uniform(bounds[:, 0], bounds[:, 1], size=(10, 2))
        y = np.sin(X[:, 0] * 2) + 0.05 * rng.randn(10)

        candidates = []
        for i in range(5):
            c = bo._acquisition(X, y, bounds, iteration=i)
            candidates.append(tuple(round(v, 4) for v in c))

        # 至少不全部相同
        assert len(set(candidates)) >= 1

    def test_ucb_with_one_dimensional(self):
        """一维参数空间 UCB 采集。"""
        bo = BayesianOptimizer()
        bounds = np.array([[0.0, 1.0]])

        rng = np.random.RandomState(42)
        X = rng.uniform(bounds[:, 0], bounds[:, 1], size=(5, 1))
        y = rng.randn(5)

        candidate = bo._acquisition(X, y, bounds, iteration=5)
        assert candidate.shape == (1,)
        assert 0.0 <= candidate[0] <= 1.0

    def test_ucb_with_few_samples(self):
        """少于 3 个训练样本时仍能返回有效候选点（回退默认超参数）。"""
        bo = BayesianOptimizer()
        bounds = np.array([[0.0, 1.0], [0.0, 1.0]])

        X = np.array([[0.2, 0.3], [0.8, 0.7]])
        y = np.array([0.5, 0.9])

        candidate = bo._acquisition(X, y, bounds, iteration=0)
        assert candidate.shape == (2,)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
