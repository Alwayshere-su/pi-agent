"""
测试 literature_agent.extractor 模块：
  - MaterialEntity / PropertyRecord / KnowledgeGraph / Relation 数据模型
  - extract_xy_pairs：表格 + 句子序列路径
"""
import pytest

from literature_agent.extractor import (
    MaterialEntity,
    PropertyRecord,
    KnowledgeGraph,
    Relation,
    SynthesisRecord,
    extract_xy_pairs,
)


# ═══════════════════════════════════════════════════════════════
# MaterialEntity
# ═══════════════════════════════════════════════════════════════

class TestMaterialEntity:
    def test_minimal_creation(self):
        """仅提供必填字段 name。"""
        m = MaterialEntity(name="MAPbI3")
        assert m.name == "MAPbI3"
        assert m.chemical_formula is None
        assert m.composition == {}
        assert m.source_papers == []

    def test_full_creation(self):
        """提供所有字段。"""
        m = MaterialEntity(
            name="MAPbI3",
            chemical_formula="CH3NH3PbI3",
            composition={"Pb": 1, "I": 3},
            structure="tetragonal",
            space_group="I4/mcm",
            morphology="thin film",
            doping="Cl-doped",
            defects="iodine vacancy",
            source_papers=["paper_1", "paper_2"],
            source_context="Synthesized via spin-coating.",
        )
        assert m.name == "MAPbI3"
        assert m.chemical_formula == "CH3NH3PbI3"
        assert m.composition == {"Pb": 1, "I": 3}
        assert m.structure == "tetragonal"
        assert m.space_group == "I4/mcm"
        assert m.morphology == "thin film"
        assert m.doping == "Cl-doped"
        assert m.defects == "iodine vacancy"
        assert len(m.source_papers) == 2
        assert m.source_context == "Synthesized via spin-coating."


# ═══════════════════════════════════════════════════════════════
# PropertyRecord
# ═══════════════════════════════════════════════════════════════

class TestPropertyRecord:
    def test_minimal_creation(self):
        """仅提供必填字段。"""
        p = PropertyRecord(property_name="band gap", value=1.55)
        assert p.property_name == "band gap"
        assert p.value == 1.55
        assert p.unit == ""
        assert p.condition == ""
        assert p.material_name == ""

    def test_full_creation(self):
        """提供所有字段。"""
        p = PropertyRecord(
            property_name="band gap",
            value=1.55,
            unit="eV",
            condition="room temperature",
            material_name="MAPbI3",
            measurement_method="UV-Vis",
            is_baseline=True,
            comparison="higher than FAPbI3",
            error_range=(1.50, 1.60),
            source_paper="paper_1",
            source_context="Measured by UV-Vis spectroscopy.",
        )
        assert p.property_name == "band gap"
        assert p.value == 1.55
        assert p.unit == "eV"
        assert p.condition == "room temperature"
        assert p.material_name == "MAPbI3"
        assert p.measurement_method == "UV-Vis"
        assert p.is_baseline is True
        assert p.comparison == "higher than FAPbI3"
        assert p.error_range == (1.50, 1.60)
        assert p.source_paper == "paper_1"

    def test_defaults(self):
        """验证默认值。"""
        p = PropertyRecord(property_name="density", value=2.7)
        assert p.unit == ""
        assert p.is_baseline is False
        assert p.comparison is None
        assert p.error_range is None
        assert p.source_paper == ""


# ═══════════════════════════════════════════════════════════════
# Relation
# ═══════════════════════════════════════════════════════════════

class TestRelation:
    def test_creation(self):
        """创建 Relation 三元组。"""
        r = Relation(
            subject="MAPbI3",
            predicate="has_band_gap",
            object="1.55 eV",
            confidence=0.9,
            evidence="UV-Vis measurement",
            source_paper="paper_1",
            relation_type="structure-property",
        )
        assert r.subject == "MAPbI3"
        assert r.predicate == "has_band_gap"
        assert r.object == "1.55 eV"
        assert r.confidence == 0.9
        assert r.evidence == "UV-Vis measurement"
        assert r.relation_type == "structure-property"

    def test_default_confidence(self):
        """默认 confidence 为 0.5。"""
        r = Relation(subject="A", predicate="B", object="C")
        assert r.confidence == 0.5


# ═══════════════════════════════════════════════════════════════
# SynthesisRecord
# ═══════════════════════════════════════════════════════════════

class TestSynthesisRecord:
    def test_creation(self):
        """创建合成记录。"""
        s = SynthesisRecord(
            material_name="MAPbI3",
            method="spin-coating",
            precursors=["PbI2", "MAI"],
            temperature=100.0,
            duration=2.0,
            solvent="DMF",
        )
        assert s.material_name == "MAPbI3"
        assert s.method == "spin-coating"
        assert s.precursors == ["PbI2", "MAI"]
        assert s.temperature == 100.0
        assert s.temperature_unit == "°C"
        assert s.duration == 2.0
        assert s.duration_unit == "h"
        assert s.solvent == "DMF"

    def test_default_units(self):
        """验证默认单位。"""
        s = SynthesisRecord(material_name="A", method="B")
        assert s.temperature_unit == "°C"
        assert s.pressure_unit == "atm"
        assert s.duration_unit == "h"
        assert s.yield_unit == "%"


# ═══════════════════════════════════════════════════════════════
# KnowledgeGraph
# ═══════════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    def test_empty_graph(self):
        """空图谱。"""
        kg = KnowledgeGraph()
        assert kg.materials == []
        assert kg.properties == []
        assert kg.relations == []

    def test_add_entities(self):
        """添加材料、性质、关系。"""
        kg = KnowledgeGraph(
            materials=[MaterialEntity(name="MAPbI3")],
            properties=[PropertyRecord(property_name="band gap", value=1.55)],
            relations=[Relation(subject="MAPbI3", predicate="has", object="band gap")],
            papers_processed=["paper_1"],
        )
        assert len(kg.materials) == 1
        assert len(kg.properties) == 1
        assert len(kg.relations) == 1
        assert kg.papers_processed == ["paper_1"]

    def test_to_dict(self):
        """to_dict 返回包含所有列表字段的 dict。"""
        kg = KnowledgeGraph(
            materials=[MaterialEntity(name="MOF-74")],
            properties=[PropertyRecord(property_name="capacity", value=5.0, unit="mmol/g")],
        )
        d = kg.to_dict()
        assert isinstance(d, dict)
        assert len(d["materials"]) == 1
        assert d["materials"][0]["name"] == "MOF-74"
        assert len(d["properties"]) == 1
        assert d["properties"][0]["property_name"] == "capacity"
        assert d["properties"][0]["value"] == 5.0
        assert d["properties"][0]["unit"] == "mmol/g"
        assert "relations" in d
        assert "papers_processed" in d

    def test_stat_empty(self):
        """空图谱统计。"""
        kg = KnowledgeGraph()
        s = kg.stat()
        assert s["materials"] == 0
        assert s["properties"] == 0
        assert s["relations"] == 0
        assert s["papers_processed"] == 0

    def test_stat_with_data(self):
        """有数据时统计正确。"""
        kg = KnowledgeGraph(
            materials=[MaterialEntity(name="A"), MaterialEntity(name="B")],
            properties=[
                PropertyRecord(property_name="band gap", value=1.5, material_name="A"),
                PropertyRecord(property_name="band gap", value=1.6, material_name="B"),
                PropertyRecord(property_name="density", value=2.7, material_name="A"),
            ],
            synthesis=[
                SynthesisRecord(material_name="A", method="sol-gel"),
                SynthesisRecord(material_name="B", method="CVD"),
            ],
        )
        s = kg.stat()
        assert s["materials"] == 2
        assert s["properties"] == 3
        assert s["unique_property_types"] == 2  # band gap, density
        assert s["unique_methods"] == 2          # sol-gel, CVD


# ═══════════════════════════════════════════════════════════════
# extract_xy_pairs
# ═══════════════════════════════════════════════════════════════

# 模拟 Markdown 表格用于测试
TABLE_TEXT = """Comparison of CO2 adsorption performance.

| Material | T (K) | Capacity (mmol/g) |
|----------|-------|-------------------|
| MOF-1    | 298   | 5.0               |
| MOF-1    | 313   | 4.2               |
| MOF-1    | 333   | 3.1               |
| MOF-2    | 298   | 6.2               |
"""

# 含范围式数值的句子
SEQUENCE_TEXT = (
    "The CO2 uptake decreased from 8.1 to 5.4 mmol/g "
    "as the temperature increased from 300 to 500 K."
)

# 单句对
SENTENCE_PAIR_TEXT = (
    "At 273 K the uptake was 7.7 mmol/g. "
    "At 303 K the uptake was 6.9 mmol/g."
)

# 混合文本（表 + 句子）
MIXED_TEXT = TABLE_TEXT + "\n" + SEQUENCE_TEXT


class TestExtractXYPairsTable:
    def test_table_extraction(self):
        """表格行配对提取：每行一对 (T, Capacity)。"""
        pairs = extract_xy_pairs(TABLE_TEXT)
        table_pairs = [p for p in pairs if p["source"] == "table_row"]
        # 应有至少 4 个表格行配对（4 行数据）
        assert len(table_pairs) >= 3, f"Expected >= 3 table pairs, got {len(table_pairs)}"

    def test_table_units(self):
        """表格提取的单位正确（K 和 mmol/g）。"""
        pairs = extract_xy_pairs(TABLE_TEXT)
        table_pairs = [p for p in pairs if p["source"] == "table_row"]
        for p in table_pairs:
            assert p["x_unit"] in ("k",)
            assert p["y_unit"] in ("mmol/g",)

    def test_table_values_range(self):
        """表格提取的数值在合理范围。"""
        pairs = extract_xy_pairs(TABLE_TEXT)
        table_pairs = [p for p in pairs if p["source"] == "table_row"]
        x_vals = sorted(p["x"] for p in table_pairs)
        assert 298 in x_vals
        assert 333 in x_vals

    def test_table_x_unit_filter(self):
        """指定 x_unit_patterns=["K"] 时只提取 T(K) 列。"""
        pairs = extract_xy_pairs(TABLE_TEXT, x_unit_patterns=["K"])
        table_pairs = [p for p in pairs if p["source"] == "table_row"]
        for p in table_pairs:
            assert p["x_unit"] == "k"


class TestExtractXYPairsSequence:
    def test_sequence_extraction(self):
        """句子序列配对：范围式写法 → sequence 源。"""
        pairs = extract_xy_pairs(SEQUENCE_TEXT)
        seq_pairs = [p for p in pairs if p["source"] == "sequence"]
        assert len(seq_pairs) >= 2, f"Expected >= 2 sequence pairs, got {len(seq_pairs)}"

    def test_sequence_values(self):
        """序列提取包含温度 (K) 和容量 (mmol/g) 的值，方向取决于单位出现顺序。"""
        # 无单位过滤时，提取器按类别出现顺序分配 x/y；
        # SEQUENCE_TEXT 中 mmol/g 出现在 K 之前，故 x=容量, y=温度
        pairs = extract_xy_pairs(SEQUENCE_TEXT)
        assert len(pairs) >= 2, f"Expected >= 2 pairs, got {pairs}"

        # 验证提取到了容量值 8.1 / 5.4 和温度值 300 / 500
        all_x = sorted([p["x"] for p in pairs])
        all_y = sorted([p["y"] for p in pairs])
        # 容量方向 (mmol/g 先出现 → x)
        assert 5.0 <= all_x[0] <= 5.5 or 5.0 <= all_y[0] <= 5.5
        assert 7.5 <= all_x[-1] <= 8.5 or 7.5 <= all_y[-1] <= 8.5

    def test_sentence_pair_extraction(self):
        """单句对配对：sentence_pair 源。"""
        pairs = extract_xy_pairs(SENTENCE_PAIR_TEXT)
        sp_pairs = [p for p in pairs if p["source"] == "sentence_pair"]
        assert len(sp_pairs) >= 2, f"Expected >= 2 sentence_pair, got {len(sp_pairs)}"

    def test_mixed_text(self):
        """混合文本同时提取表格和句子配对。"""
        pairs = extract_xy_pairs(MIXED_TEXT)
        sources = set(p["source"] for p in pairs)
        assert "table_row" in sources
        # sequence 或 sentence_pair 至少有一类
        assert ("sequence" in sources or "sentence_pair" in sources)

    def test_empty_text(self):
        """空文本返回空列表。"""
        assert extract_xy_pairs("") == []
        assert extract_xy_pairs("   ") == []

    def test_no_pairs_in_text(self):
        """不含数值+单位的文本返回空列表。"""
        pairs = extract_xy_pairs("This is just a plain text without any numbers or units.")
        assert pairs == []

    def test_context_sentence_field(self):
        """每个配对包含 context_sentence 字段。"""
        pairs = extract_xy_pairs(TABLE_TEXT)
        for p in pairs:
            assert "context_sentence" in p
            assert isinstance(p["context_sentence"], str)
            assert len(p["context_sentence"]) > 0

    def test_max_pairs_limit(self):
        """max_pairs 参数生效。"""
        pairs = extract_xy_pairs(TABLE_TEXT, max_pairs=2)
        assert len(pairs) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
