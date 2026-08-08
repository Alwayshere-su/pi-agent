"""
测试 literature_agent.parser 的解析引擎回退与表格增强（GOAI #14）：
  - 无 MinerU 时 MarkItDownParser 本地引擎正常工作（回退路径）
  - _enhance_pdf_tables 触发条件：仅 .pdf、表格不足、pdfplumber 可用
  - _enhance_pdf_tables 静默回退：非 PDF / 表格足够 / pdfplumber 缺失 / 解析异常
"""
import sys
import types
from pathlib import Path

from literature_agent.parser import MarkItDownParser


def _write_temp_md(tmp_path: Path, content: str = None) -> Path:
    p = tmp_path / "sample.md"
    p.write_text(
        content or "# Title\n\nSome paragraph with CO2 uptake 8.3 mmol/g.\n",
        encoding="utf-8",
    )
    return p


class TestMarkItDownFallback:
    """无 MinerU 时 MarkItDownParser 作为本地引擎正常工作（回退路径）。"""

    def test_parse_markdown_file(self, tmp_path):
        p = _write_temp_md(tmp_path)
        doc = MarkItDownParser().parse(str(p))
        assert doc.parse_engine == "markitdown"
        assert "CO2 uptake 8.3 mmol/g" in doc.full_text
        assert doc.title
        assert doc.sections  # 章节树构建成功

    def test_parse_extracts_materials_and_properties(self, tmp_path):
        p = _write_temp_md(
            tmp_path,
            "# Title\n\nMg-MOF-74 shows CO2 adsorption capacity of 8.3 mmol/g.\n",
        )
        doc = MarkItDownParser().parse(str(p))
        assert any("mof" in (m or "").lower() for m in doc.materials_mentioned)
        assert any("adsorption" in (k or "").lower() for k in doc.properties_mentioned)


class TestPdfTableEnhance:
    """_enhance_pdf_tables 触发条件与静默回退。"""

    def test_non_pdf_returns_unchanged(self, tmp_path):
        p = _write_temp_md(tmp_path)
        text = "no table here"
        out, n = MarkItDownParser._enhance_pdf_tables(str(p), text)
        assert out == text
        assert n == 0

    def test_pdf_with_enough_tables_skipped(self, tmp_path):
        # 已有表格 >=3 时跳过——该检查在 pdfplumber.open 之前，
        # 无需真实 PDF 文件即可验证。
        fake = str(tmp_path / "fake.pdf")
        md = "| a | b |\n|---|---|\n| 1 | 2 |\n\n" * 3
        out, n = MarkItDownParser._enhance_pdf_tables(fake, md)
        assert out == md
        assert n == 0

    def test_pdf_with_pdfplumber_unavailable_skipped(self, tmp_path, monkeypatch):
        # sys.modules 中置 None 强制 import pdfplumber 抛 ImportError
        fake = str(tmp_path / "fake.pdf")
        monkeypatch.setitem(sys.modules, "pdfplumber", None)
        out, n = MarkItDownParser._enhance_pdf_tables(fake, "few tables")
        assert out == "few tables"
        assert n == 0

    def test_pdf_with_mock_pdfplumber_appends_tables(self, tmp_path, monkeypatch):
        fake = str(tmp_path / "fake.pdf")
        fake_pdfplumber = types.ModuleType("pdfplumber")

        class FakePage:
            def extract_tables(self):
                return [[["材料", "CO2容量"], ["Mg-MOF-74", "8.3"], ["Ni-MOF-74", "3.99"]]]

        class FakePdf:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            @property
            def pages(self):
                return [FakePage()]

        fake_pdfplumber.open = staticmethod(lambda path: FakePdf())
        monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

        out, n = MarkItDownParser._enhance_pdf_tables(fake, "# title")
        assert n == 1
        assert "pdfplumber 表格提取" in out
        assert "Mg-MOF-74" in out and "8.3" in out

    def test_pdf_with_exception_silently_falls_back(self, tmp_path, monkeypatch):
        fake = str(tmp_path / "fake.pdf")
        fake_pdfplumber = types.ModuleType("pdfplumber")

        class Boom:
            @staticmethod
            def open(path):
                raise RuntimeError("corrupt pdf")

        fake_pdfplumber.open = Boom.open
        monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

        out, n = MarkItDownParser._enhance_pdf_tables(fake, "# title")
        assert out == "# title"
        assert n == 0
