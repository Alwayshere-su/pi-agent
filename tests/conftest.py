"""
pytest 配置与共享 fixtures。
"""
import sys
from pathlib import Path

# 保证从仓库根可导入 utils / pi_agent / literature_agent（W-4 P1-1：
# 测试从 scripts/ 子目录迁入 tests/ 后，sys.path 需显式注入仓库根）
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

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
