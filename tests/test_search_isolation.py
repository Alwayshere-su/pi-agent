# -*- coding: utf-8 -*-
"""
跨主题文献缓存隔离测试
======================
验证 2026-08 修复：search_results.json 等文献检索缓存按 run_dir 隔离，
不同主题（perovskite / thermoelectric / cathode）的检索累积互不干扰。

独立运行（无需 pytest，无需联网、无需 API Key）：
    python -X utf8 scripts/cache_isolation_test/test_search_isolation.py

要点：
  - 通过环境变量 LITERATURE_CACHE_DIR 把缓存基准目录指到临时目录，
    避免污染 workspace/data/literature_cache（不触碰已有 MOF 产物）。
  - 用桩替换 literature_agent.search.LiteratureSearcher，不发起真实网络请求。
  - 直接调用 pi_agent.tools.ToolHandlers.h_search_papers 的累积写盘路径，
    与线上 Agent 行为完全一致。
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile

# 项目根（scripts/cache_isolation_test/ → 上两级）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ── 桩：不联网的检索结果 ──

def _make_result(title: str) -> "_FakeResult":
    return _FakeResult(
        title=title,
        year=2024,
        authors=["Test Author"],
        source="fake",
        score=0.9,
        doi=f"10.9999/{hashlib.md5(title.encode('utf-8')).hexdigest()[:8]}",
    )


class _FakeResult:
    """模拟 SearchResult 的最小对象（含 h_search_papers 用到的全部字段）。"""

    def __init__(self, title, year, authors, source, score, doi):
        self.title = title
        self.year = year
        self.authors = authors
        self.source = source
        self.score = score
        self.doi = doi
        self.abstract = ""
        self.url = None
        self.citation_count = 0
        self.journal = None
        self.keywords = []
        self.paper_id = None
        self.full_text_snippet = None
        self.pdf_url = None
        self.raw_metadata = {}

    def to_dict(self):
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "year": self.year,
            "doi": self.doi,
            "url": self.url,
            "source": self.source,
            "score": self.score,
            "citation_count": self.citation_count,
            "journal": self.journal,
            "keywords": self.keywords,
            "paper_id": self.paper_id,
            "full_text_snippet": self.full_text_snippet,
            "pdf_url": self.pdf_url,
            "raw_metadata": self.raw_metadata,
        }


class _FakeSearcher:
    """按查询关键词返回固定论文列表，绝不联网。"""

    # 每个主题 4 篇固定论文（前 2 篇 / 后 2 篇对应不同检索批次）
    _PAPERS = {
        "perovskite": [
            "Perovskite solar cell efficiency record",
            "Perovskite phase stability degradation mechanism",
            "Perovskite lead halide band gap tuning",
            "Perovskite encapsulation long-term stability",
        ],
        "thermoelectric": [
            "Thermoelectric ZT optimization Bi2Te3",
            "Thermoelectric SnSe record figure of merit",
            "Thermoelectric PbTe band convergence doping",
            "Thermoelectric half-Heusler engineering",
        ],
    }

    def __init__(self, *args, **kwargs):
        pass  # 忽略 cache_dir / sciverse_api_key

    def search(self, query, top_k=20, material=None, property_name=None):
        text = (query or "").lower()
        if "perovskite" in text:
            pool = self._PAPERS["perovskite"]
        elif "thermoelectric" in text:
            pool = self._PAPERS["thermoelectric"]
        else:
            return []
        # 第一批查询取前 2 篇；第二批查询（stability/band/SnSe 等）取后 2 篇；
        # 其余取 1 篇。DOI 按标题哈希生成，批次间互不重复。
        if any(k in text for k in ("efficiency", "record", "zt", "bi2te3", "optimization")):
            batch = pool[:2]
        elif any(k in text for k in ("stability", "degradation", "band", "snse", "phase")):
            batch = pool[2:4]
        else:
            batch = pool[:1]
        return [_make_result(t) for t in batch[:max(0, top_k)]]


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    failures = []
    tmp = tempfile.mkdtemp(prefix="goai_cache_isolation_")
    os.environ["LITERATURE_CACHE_DIR"] = tmp  # 测试期基准目录 → 临时目录

    def check(cond, msg):
        if not cond:
            failures.append(msg)
            print(f"  ✗ FAIL: {msg}")

    try:
        import literature_agent.search as search_mod
        import utils.config as cfg
        from pi_agent.tools import ToolHandlers

        # 替换为桩，保证测试完全离线
        search_mod.LiteratureSearcher = _FakeSearcher

        # ── 1) run_dir → 缓存目录映射 ──
        print("[1] 校验 set_run_dir / get_literature_cache_dir 路径映射")
        cfg.set_run_dir("perovskite")
        expect_pv = os.path.join(tmp, "perovskite").replace("\\", "/")
        check(cfg.get_literature_cache_dir() == expect_pv,
              f"perovskite 缓存目录应为 {expect_pv}，实际 {cfg.get_literature_cache_dir()}")

        cfg.set_run_dir("thermoelectric")
        expect_te = os.path.join(tmp, "thermoelectric").replace("\\", "/")
        check(cfg.get_literature_cache_dir() == expect_te,
              f"thermoelectric 缓存目录应为 {expect_te}，实际 {cfg.get_literature_cache_dir()}")

        cfg.set_run_dir("survey")  # 默认 → 基准目录本身（向后兼容）
        check(cfg.get_literature_cache_dir() == tmp,
              f"survey 缓存目录应为基准 {tmp}，实际 {cfg.get_literature_cache_dir()}")

        # ── 2) 两个 run_dir 的 search_papers 累积互不干扰 ──
        print("[2] 模拟 perovskite / thermoelectric 两个主题的检索累积")
        handlers = ToolHandlers(task_type="survey")

        cfg.set_run_dir("perovskite")
        handlers.h_search_papers({"query": "perovskite solar cell efficiency", "top_k": 5})
        handlers.h_search_papers({"query": "perovskite stability degradation", "top_k": 5})
        pv_file = os.path.join(tmp, "perovskite", "search_results.json")
        check(os.path.exists(pv_file), f"perovskite 累积文件应存在: {pv_file}")
        pv_data = _read_json(pv_file)
        check(len(pv_data) == 4,
              f"perovskite 两次检索应累积 4 篇，实际 {len(pv_data)}")
        titles_pv = {d["title"] for d in pv_data}
        check(all("perovskite" in t.lower() for t in titles_pv),
              f"perovskite 累积文件不应混入其它主题论文: {titles_pv}")

        cfg.set_run_dir("thermoelectric")
        handlers.h_search_papers({"query": "thermoelectric material ZT optimization", "top_k": 5})
        te_file = os.path.join(tmp, "thermoelectric", "search_results.json")
        check(os.path.exists(te_file), f"thermoelectric 累积文件应存在: {te_file}")
        te_data = _read_json(te_file)
        check(len(te_data) == 2,
              f"thermoelectric 首次检索应累积 2 篇，实际 {len(te_data)}")
        titles_te = {d["title"] for d in te_data}
        check(titles_te.isdisjoint(titles_pv),
              f"跨主题污染！thermoelectric 文件混入了 perovskite 论文: {titles_te & titles_pv}")

        # 反向验证：perovskite 文件也未因 thermoelectric 检索而变化
        pv_data_after = _read_json(pv_file)
        check({d["title"] for d in pv_data_after} == titles_pv,
              "perovskite 累积文件在其它主题检索后不应被改动")

        # ── 3) 默认 survey 保持原路径、本轮不产生新文件 ──
        print("[3] 校验默认 survey 的向后兼容行为")
        cfg.set_run_dir("survey")
        check(not os.path.exists(os.path.join(tmp, "search_results.json")),
              "默认 survey 本轮未检索，不应在基准目录生成 search_results.json")

        # ── 4) 返回摘要中展示的是当前 run_dir 的隔离路径 ──
        print("[4] 校验工具返回摘要中的缓存路径")
        cfg.set_run_dir("perovskite")
        summary = handlers.h_search_papers({"query": "perovskite lead halide", "top_k": 5})
        check(cfg.get_literature_cache_dir() + "/search_results.json" in summary,
              "h_search_papers 返回摘要应展示 perovskite 隔离路径")
    except Exception as e:
        import traceback
        traceback.print_exc()
        failures.append(f"执行异常: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        os.environ.pop("LITERATURE_CACHE_DIR", None)
        # 防御：cfg 仅在 try 内成功导入后才存在
        if "cfg" in dir() or "cfg" in locals():
            cfg.set_run_dir("survey")  # 恢复全局默认，避免影响后续运行

    if failures:
        print(f"\n❌ 测试未通过：{len(failures)} 项失败")
        return 1
    print("\n✅ ALL TESTS PASSED — 跨主题文献缓存隔离生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
