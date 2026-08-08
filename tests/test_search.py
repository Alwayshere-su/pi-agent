"""
测试 literature_agent.search 模块：
  - _normalize_doi：DOI 规范化
  - SearchResult：id 属性、to_dict、to_markdown
  - _normalize_title / _title_similarity：标题处理
  - _parse_arxiv_xml：arXiv XML 解析
  - SearchQuery：dataclass 默认值
"""
import pytest
import hashlib

from literature_agent.search import (
    _normalize_doi,
    _parse_arxiv_xml,
    SearchResult,
    SearchQuery,
    LiteratureSearcher,
)


# ═══════════════════════════════════════════════════════════════
# _normalize_doi
# ═══════════════════════════════════════════════════════════════

class TestNormalizeDoi:
    def test_standard_doi(self):
        """标准 DOI 格式：保持不变（小写）。"""
        assert _normalize_doi("10.1000/abc.123") == "10.1000/abc.123"

    def test_https_prefix(self):
        """https://doi.org/ 前缀被移除。"""
        assert _normalize_doi("https://doi.org/10.1000/abc.123") == "10.1000/abc.123"

    def test_http_prefix(self):
        """http://dx.doi.org/ 前缀被移除。"""
        assert _normalize_doi("http://dx.doi.org/10.1000/abc.123") == "10.1000/abc.123"

    def test_doi_colon_prefix(self):
        """'doi:' 前缀被移除。"""
        assert _normalize_doi("doi:10.1000/abc.123") == "10.1000/abc.123"
        assert _normalize_doi("DOI: 10.1000/abc.123") == "10.1000/abc.123"

    def test_uppercase(self):
        """大小写统一转为小写。"""
        assert _normalize_doi("10.1000/ABC.DEF") == "10.1000/abc.def"

    def test_trailing_punctuation(self):
        """尾部标点被移除。"""
        assert _normalize_doi("10.1000/abc.123.") == "10.1000/abc.123"
        assert _normalize_doi("10.1000/abc.123,") == "10.1000/abc.123"
        assert _normalize_doi("10.1000/abc.123;") == "10.1000/abc.123"

    def test_whitespace(self):
        """首尾空白被移除。"""
        assert _normalize_doi("  10.1000/abc.123  ") == "10.1000/abc.123"

    def test_none_or_empty(self):
        """None 或空字符串返回 None。"""
        assert _normalize_doi(None) is None
        assert _normalize_doi("") is None
        assert _normalize_doi("  ") is None


# ═══════════════════════════════════════════════════════════════
# SearchResult
# ═══════════════════════════════════════════════════════════════

class TestSearchResultId:
    def test_id_with_doi(self):
        """有 DOI 时 id 返回 'doi:xxx'。"""
        r = SearchResult(title="Test", doi="10.1000/abc.123")
        assert r.id == "doi:10.1000/abc.123"

    def test_id_with_paper_id_no_doi(self):
        """有 paper_id 但无 DOI 时返回 'paper:xxx'。"""
        r = SearchResult(title="Test", paper_id="sciverse_doc_999")
        assert r.id == "paper:sciverse_doc_999"

    def test_id_with_both(self):
        """同时有 DOI 和 paper_id 时优先返回 DOI 格式。"""
        r = SearchResult(title="Test", doi="10.1000/abc.123", paper_id="sciverse_doc_999")
        assert r.id == "doi:10.1000/abc.123"

    def test_id_fallback_to_title(self):
        """既无 DOI 也无 paper_id 时返回 title:md5_hash。"""
        r = SearchResult(title="A Unique Paper Title")
        expected_hash = hashlib.md5("A Unique Paper Title".encode()).hexdigest()[:12]
        assert r.id == f"title:{expected_hash}"

    def test_id_none_doi_paper_id(self):
        """DOI 为 None、paper_id 为 None 时，退回到 title hash。"""
        r = SearchResult(title="Fallback Title", doi=None, paper_id=None)
        expected_hash = hashlib.md5("Fallback Title".encode()).hexdigest()[:12]
        assert r.id == f"title:{expected_hash}"


class TestSearchResultToDict:
    def test_basic_to_dict(self, sample_search_result_kwargs):
        """to_dict 返回包含所有字段的 dict。"""
        r = SearchResult(**sample_search_result_kwargs)
        d = r.to_dict()
        assert d["title"] == "Test Paper on Perovskite Solar Cells"
        assert d["doi"] == "10.1234/test.001"
        assert d["score"] == 0.85
        assert d["source"] == "sciverse"
        assert len(d["authors"]) == 3

    def test_empty_defaults(self):
        """默认值字段正常序列化。"""
        r = SearchResult(title="Minimal")
        d = r.to_dict()
        assert d["title"] == "Minimal"
        assert d["authors"] == []
        assert d["abstract"] == ""
        assert d["score"] == 0.0
        assert d["citation_count"] == 0


class TestSearchResultToMarkdown:
    def test_full_markdown(self, sample_search_result_kwargs):
        """to_markdown 包含标题、作者、期刊、DOI、摘要等。"""
        r = SearchResult(**sample_search_result_kwargs)
        md = r.to_markdown()
        assert "Test Paper on Perovskite Solar Cells" in md
        assert "Alice Wang, Bob Li, Charlie Zhang" in md
        assert "2024" in md
        assert "Journal of Materials Science" in md
        assert "10.1234/test.001" in md
        assert "perovskite" in md.lower()
        assert "Source: sciverse" in md
        assert "Score: 0.850" in md

    def test_no_journal_no_doi(self):
        """无期刊、无 DOI 时不影响格式化。"""
        r = SearchResult(title="Simple Paper")
        md = r.to_markdown()
        assert "Simple Paper" in md
        assert "Journal" not in md
        assert "DOI" not in md

    def test_many_authors(self):
        """超过 3 位作者时显示 'et al.' 及总人数。"""
        r = SearchResult(
            title="Many Authors",
            authors=["A", "B", "C", "D", "E"],
        )
        md = r.to_markdown()
        assert "et al. (5 authors)" in md

    def test_abstract_truncation(self):
        """摘要超过 500 字符时截断。"""
        long_abstract = "X" * 600
        r = SearchResult(title="Long Abstract", abstract=long_abstract)
        md = r.to_markdown()
        assert long_abstract[:500] in md
        assert "X" * 600 not in md

    def test_evidence_snippet(self):
        """全文证据片段存在时显示。"""
        r = SearchResult(title="With Evidence", full_text_snippet="Key finding: x > y.")
        md = r.to_markdown()
        assert "Evidence Snippet" in md
        assert "Key finding: x > y." in md


# ═══════════════════════════════════════════════════════════════
# _normalize_title / _title_similarity
# ═══════════════════════════════════════════════════════════════

class TestNormalizeTitle:
    def test_lowercase_and_strip(self):
        """转小写并去除首尾空白。"""
        result = LiteratureSearcher._normalize_title("  Hello World  ")
        assert result == "hello world"

    def test_remove_punctuation(self):
        """移除非字母数字和空格的标点。"""
        result = LiteratureSearcher._normalize_title("Hello, World! How's it?")
        # 标点被移除，但字母数字和空格保留
        assert result == "hello world hows it"

    def test_chinese_characters_removed(self):
        """中文等非 ASCII 字母数字字符被移除。"""
        result = LiteratureSearcher._normalize_title("Test 测试 Title")
        # '测' 和 '试' 不是 a-z0-9，被移除
        assert result == "test  title"


class TestTitleSimilarity:
    def test_identical_titles(self):
        """完全相同标题相似度为 1.0。"""
        t = LiteratureSearcher._normalize_title("Perovskite solar cell stability")
        assert LiteratureSearcher._title_similarity(t, t) == 1.0

    def test_similar_titles(self):
        """高度相似标题相似度 > 0.5。"""
        t1 = LiteratureSearcher._normalize_title("Perovskite solar cell stability under moisture")
        t2 = LiteratureSearcher._normalize_title("Perovskite solar cell stability under heat")
        sim = LiteratureSearcher._title_similarity(t1, t2)
        assert sim > 0.5, f"Expected > 0.5, got {sim}"

    def test_dissimilar_titles(self):
        """不相似标题相似度很低。"""
        t1 = LiteratureSearcher._normalize_title("Perovskite solar cell stability")
        t2 = LiteratureSearcher._normalize_title("Quantum computing algorithms for optimization")
        sim = LiteratureSearcher._title_similarity(t1, t2)
        assert sim < 0.2, f"Expected < 0.2, got {sim}"

    def test_short_title(self):
        """短标题（少于 3 字符）返回 0.0 因为无法生成 3-gram。"""
        t1 = LiteratureSearcher._normalize_title("AB")
        t2 = LiteratureSearcher._normalize_title("CD")
        sim = LiteratureSearcher._title_similarity(t1, t2)
        assert sim == 0.0


# ═══════════════════════════════════════════════════════════════
# _parse_arxiv_xml
# ═══════════════════════════════════════════════════════════════

VALID_ARXIV_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Deep Learning for Perovskite Band Gap Prediction</title>
    <summary>  We present a deep learning model for predicting band gaps
    of perovskite materials with high accuracy.  </summary>
    <author>
      <name>John Smith</name>
    </author>
    <author>
      <name>Jane Doe</name>
    </author>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate"/>
    <link href="http://arxiv.org/pdf/2401.00001v1" title="pdf" rel="related"/>
    <link href="http://dx.doi.org/10.1234/arxiv.test.001" rel="related"/>
    <published>2024-01-15T12:00:00Z</published>
    <arxiv:journal_ref>Nature Materials 23, 100-110 (2024)</arxiv:journal_ref>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2402.00002v1</id>
    <title>MOF Materials for CO2 Capture: A Review</title>
    <summary>This review covers recent advances in MOF-based CO2 capture.</summary>
    <author>
      <name>Alice Chen</name>
    </author>
    <published>2024-02-20T08:00:00Z</published>
  </entry>
</feed>"""


class TestParseArxivXml:
    def test_parse_valid_xml(self):
        """解析有效的 arXiv Atom XML，返回 SearchResult 列表。"""
        results = _parse_arxiv_xml(VALID_ARXIV_ATOM_XML)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_first_entry_fields(self):
        """验证第一条记录的各字段解析。"""
        results = _parse_arxiv_xml(VALID_ARXIV_ATOM_XML)
        r = results[0]
        assert r.title == "Deep Learning for Perovskite Band Gap Prediction"
        assert len(r.authors) == 2
        assert "John Smith" in r.authors
        assert "Jane Doe" in r.authors
        assert "deep learning" in r.abstract.lower()
        assert r.year == 2024
        assert r.doi == "10.1234/arxiv.test.001"
        assert r.source == "arxiv"
        assert r.url == "https://arxiv.org/abs/2401.00001v1"
        assert r.pdf_url == "http://arxiv.org/pdf/2401.00001v1"
        assert r.journal == "Nature Materials 23, 100-110 (2024)"

    def test_second_entry_minimal(self):
        """验证第二条简略记录（无 DOI、无 journal、无 pdf_url）。"""
        results = _parse_arxiv_xml(VALID_ARXIV_ATOM_XML)
        r = results[1]
        assert r.title == "MOF Materials for CO2 Capture: A Review"
        assert r.authors == ["Alice Chen"]
        assert r.year == 2024
        assert r.doi is None
        assert r.journal is None
        assert r.pdf_url is None

    def test_empty_xml(self):
        """空 XML（无 entry 元素）返回空列表。"""
        empty_xml = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        results = _parse_arxiv_xml(empty_xml)
        assert results == []

    def test_score_default(self):
        """解析后的初始 score 为 0.0（由调用方后续设置）。"""
        results = _parse_arxiv_xml(VALID_ARXIV_ATOM_XML)
        for r in results:
            assert r.score == 0.0


# ═══════════════════════════════════════════════════════════════
# SearchQuery
# ═══════════════════════════════════════════════════════════════

class TestSearchQueryDataclass:
    def test_minimal_creation(self):
        """仅提供必填字段 text。"""
        q = SearchQuery(text="MOF CO2 capture")
        assert q.text == "MOF CO2 capture"
        assert q.material is None
        assert q.property is None
        assert q.method is None
        assert q.year_from is None
        assert q.year_to is None
        assert q.top_k == 20
        assert q.sources == ["arxiv", "scibase"]
        assert q.parsed_entities == {}

    def test_full_creation(self):
        """提供所有字段。"""
        q = SearchQuery(
            text="MOF CO2 capture",
            material="MOF-74",
            property="adsorption capacity",
            method="DFT",
            year_from=2020,
            year_to=2024,
            top_k=30,
            sources=["sciverse", "arxiv"],
            parsed_entities={"material": "MOF-74"},
        )
        assert q.text == "MOF CO2 capture"
        assert q.material == "MOF-74"
        assert q.property == "adsorption capacity"
        assert q.method == "DFT"
        assert q.year_from == 2020
        assert q.year_to == 2024
        assert q.top_k == 30
        assert q.sources == ["sciverse", "arxiv"]
        assert q.parsed_entities == {"material": "MOF-74"}

    def test_sources_default_list_is_independent(self):
        """默认 sources 列表是独立实例（修改不影响其他实例）。"""
        q1 = SearchQuery(text="Query 1")
        q2 = SearchQuery(text="Query 2")
        q1.sources.append("sciverse")
        # q2 不应受影响
        assert q2.sources == ["arxiv", "scibase"]
        assert "sciverse" not in q2.sources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
