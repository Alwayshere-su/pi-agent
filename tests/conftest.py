"""
pytest 配置与共享 fixtures。
"""
import pytest


@pytest.fixture
def sample_search_result_kwargs():
    """构造 SearchResult 的通用参数字典。"""
    return {
        "title": "Test Paper on Perovskite Solar Cells",
        "authors": ["Alice Wang", "Bob Li", "Charlie Zhang"],
        "abstract": "This paper investigates the stability of perovskite solar cells.",
        "year": 2024,
        "doi": "10.1234/test.001",
        "url": "https://doi.org/10.1234/test.001",
        "source": "sciverse",
        "score": 0.85,
        "citation_count": 42,
        "journal": "Journal of Materials Science",
        "keywords": ["perovskite", "solar cell", "stability"],
        "paper_id": "sciverse_doc_123",
    }
