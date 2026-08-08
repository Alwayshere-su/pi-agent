#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sci-Base 数据集本地索引准备工具
========================================

复赛复现性支持:为 literature_agent.search.SciBaseSearcher 准备本地索引
(index.json + papers.json),使 Sci-Base 数据源可用。

Sci-Base 数据集: HuggingFace `opendatalab/Sci-Base`
  - 2500万+ 篇论文、6000亿+ tokens,覆盖含材料科学在内的 10 个学科
  - 数据极大(完整下载需数百 GB),默认只取样本

用法(全部从项目根目录执行):
    # 1) 查看指引(默认动作,不联网、不下载、不写文件)
    python -X utf8 scripts/prepare_scibase.py

    # 2) 已有一份 Sci-Base 索引文件 → 拷入 LITERATURE_CACHE_DIR 启用
    #    若 index.json 同目录存在 papers.json 会一并拷贝
    python -X utf8 scripts/prepare_scibase.py --index <path/to/index.json>

    # 3) 从 HuggingFace 拉取样本并构建本地索引(需先安装 datasets)
    #    --limit 默认取 500 条样本;设 --limit 0 表示不限制(完整下载,不推荐)
    python -X utf8 scripts/prepare_scibase.py --download --limit 500

说明:
    - 目标目录 = LITERATURE_CACHE_DIR(环境变量可覆盖),
      默认 workspace/data/literature_cache,与 SciBaseSearcher 默认读取目录一致。
    - 索引就绪后 SciBaseSearcher.available 即返回 True。
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 数据集标识与默认样本量
REPO_ID = "opendatalab/Sci-Base"
DEFAULT_LIMIT = 500  # 默认只取样本,避免误触发大下载
_PREPARE_SCRIPT = "scripts/prepare_scibase.py"

# SciBaseSearcher 搜索词打分用停用词,与 literature_agent/search.py 保持一致
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "on",
    "to", "for", "with", "and", "or", "by", "from", "at", "as", "be",
    "this", "that", "it", "its", "we", "our", "their", "has", "have",
    "been", "can", "may", "will", "would", "could", "should",
}


# ═══════════════════════════════════════════════════════════════
# 路径解析
# ═══════════════════════════════════════════════════════════════

def _project_root() -> Path:
    """返回项目根目录(本文件位于 <root>/scripts/ 下)。"""
    return Path(__file__).resolve().parent.parent


def get_literature_cache_dir() -> Path:
    """解析 LITERATURE_CACHE_DIR(与 utils.config 保持一致,尊重环境变量与 run_dir 隔离)。

    优先复用 utils.config(它已处理 LITERATURE_CACHE_DIR 环境变量与
    set_run_dir 的 run_dir 隔离);无法 import 时回退到环境变量 / 默认相对路径。
    """
    try:
        # `python -X utf8 scripts/prepare_scibase.py` 时 cwd 即项目根,
        # 加入 sys.path 以便 import utils.config
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        from utils.config import LITERATURE_CACHE_DIR as _dir  # noqa: PLC0415
        return Path(_dir)
    except Exception:
        pass
    env = os.environ.get("LITERATURE_CACHE_DIR", "").strip()
    if env:
        return Path(env)
    return Path("workspace/data/literature_cache")


# ═══════════════════════════════════════════════════════════════
# 文本处理(与 literature_agent/search.py 的 SciBaseSearcher 对齐)
# ═══════════════════════════════════════════════════════════════

def _tokenize(text: str) -> List[str]:
    """简单分词 + 去停用词(与 SciBaseSearcher._tokenize 逻辑一致)。"""
    import re

    text = re.sub(r"[^\w\s-]", " ", text.lower())
    tokens = []
    for token in text.split():
        token = token.strip()
        if len(token) > 2 and token not in _STOPWORDS:
            tokens.append(token)
    return tokens


def _first(record: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """按候选 key 顺序取第一个非空值(兼容 Sci-Base 不同 schema)。"""
    for k in keys:
        if k in record and record[k] is not None and record[k] != "":
            return record[k]
    return default


def _normalize_record(row: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """把 HuggingFace 原始记录规范化为 SciBaseSearcher 期望的论文字段。

    对字段名做容错(Sci-Base 列名随版本可能变化);无法提取 title 的记录
    会被调用方丢弃(无标题论文无法检索)。
    """
    title = _first(row, ["title", "paper_title", "Title", "name"], "")
    if not title:
        return {}
    authors_raw = _first(row, ["authors", "author", "authors_list", "Authors"], [])
    if isinstance(authors_raw, str):
        authors = [a.strip() for a in authors_raw.replace(";", ",").split(",") if a.strip()]
    elif isinstance(authors_raw, (list, tuple)):
        authors = [str(a) for a in authors_raw]
    else:
        authors = []
    abstract = _first(row, ["abstract", "Abstract", "summary"], "") or ""
    year = _first(row, ["year", "publication_year", "pub_year", "Year"], None)
    doi = _first(row, ["doi", "DOI"], None)
    journal = _first(row, ["journal", "venue", "publication_venue_name", "Journal"], "")
    paper_id = str(
        _first(row, ["id", "paper_id", "corpus_id", "sha"], "")
        or doi
        or f"paper_{idx}"
    )
    return {
        "title": str(title),
        "authors": authors,
        "abstract": str(abstract),
        "year": int(year) if isinstance(year, (int, float)) and not isinstance(year, bool) else year,
        "doi": str(doi) if doi else None,
        "journal": str(journal) if journal else "",
        "keywords": [],
        "paper_id": paper_id,
    }


def build_index(records: List[Dict[str, Any]]) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, Any]]]:
    """从论文记录构建倒排索引。

    Returns:
        (index, papers): index = {term: [paper_id, ...]}, papers = {paper_id: meta}
        与 SciBaseSearcher._load_index 读取的 index.json / papers.json 格式一致。
    """
    papers: Dict[str, Dict[str, Any]] = {}
    index: Dict[str, List[str]] = {}
    for i, rec in enumerate(records):
        pid = str(rec.get("paper_id") or rec.get("doi") or f"paper_{i}")
        papers[pid] = rec
        text = f"{rec.get('title', '')} {rec.get('abstract', '')}"
        for term in set(_tokenize(text)):
            index.setdefault(term, []).append(pid)
    return index, papers


def write_index_files(index: Dict[str, List[str]],
                      papers: Dict[str, Dict[str, Any]],
                      target_dir: Path) -> Tuple[Path, Path]:
    """写入 index.json 与 papers.json,返回文件路径。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    index_file = target_dir / "index.json"
    papers_file = target_dir / "papers.json"
    index_file.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    papers_file.write_text(json.dumps(papers, ensure_ascii=False), encoding="utf-8")
    return index_file, papers_file


# ═══════════════════════════════════════════════════════════════
# 子命令: --index(拷入现成索引)
# ═══════════════════════════════════════════════════════════════

def cmd_index(src: Path) -> int:
    src = Path(src).resolve()
    if not src.exists() or not src.is_file():
        print(f"[prepare_scibase] 错误: index 文件不存在: {src}", file=sys.stderr)
        return 1
    # 先校验 JSON 合法且为 term→list 结构的 dict
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("index.json 顶层应为 {term: [paper_id, ...]} 的 JSON 对象")
    except Exception as exc:  # noqa: BLE001
        print(f"[prepare_scibase] 错误: index.json 解析失败({exc}): {src}", file=sys.stderr)
        return 1

    target_dir = get_literature_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    index_file = target_dir / "index.json"
    shutil.copy2(src, index_file)

    # 同目录若有 papers.json 一并拷贝(检索详情需要),否则提示
    papers_copied = False
    papers_src = src.parent / "papers.json"
    if papers_src.exists():
        shutil.copy2(papers_src, target_dir / "papers.json")
        papers_copied = True

    n_terms = len(data)
    print("=" * 62)
    print("  Sci-Base 本地索引安装完成")
    print("=" * 62)
    print(f"  索引文件 : {src}")
    print(f"  词条数   : {n_terms:,}")
    print(f"  目标目录 : {target_dir}")
    print(f"  index.json -> {index_file}")
    if papers_copied:
        print(f"  papers.json -> {target_dir / 'papers.json'}  (已一并拷贝)")
    else:
        print("  ⚠️ 未找到同目录 papers.json:检索命中后将无法回填论文详情。")
        print("    可运行 --download 模式让脚本自动构建 papers.json。")
    print("-" * 62)
    print("  可用状态: SciBaseSearcher.available = True ✅")
    print(f"  提示: 运行 `python -c \"from literature_agent.search import "
          f"SciBaseSearcher; print(SciBaseSearcher().available)\"` 复核。")
    return 0


# ═══════════════════════════════════════════════════════════════
# 子命令: --download(从 HuggingFace 拉取样本并构建索引)
# ═══════════════════════════════════════════════════════════════

def _load_dataset_streaming(limit: int):
    """流式加载 Sci-Base 数据集,返回可迭代的 record 迭代器。

    探测常见 split 名以兼容数据集版本变化;流式模式不会一次性下载全量数据,
    只在迭代时按需拉取。
    """
    try:
        from datasets import load_dataset  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        print(f"[prepare_scibase] 错误: 未安装 datasets 包 → {exc}", file=sys.stderr)
        print("  安装方式:")
        print("    pip install datasets==4.8.4   # 与 requirements.txt 锁定版本一致")
        print("  或一次性安装全部锁定依赖:")
        print("    pip install -r requirements.txt")
        print("  也可以不下载,改用 --index 模式接入现成索引文件。")
        return None

    import datasets  # noqa: PLC0415

    last_err: Optional[Exception] = None
    for split in ("train", "default", "test", "validation"):
        try:
            ds = datasets.load_dataset(REPO_ID, split=split, streaming=True)
            print(f"[prepare_scibase] 已连接数据集 {REPO_ID} (split={split}),开始流式拉取…")
            return ds
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    # 兜底:不带 split 加载
    try:
        return datasets.load_dataset(REPO_ID, streaming=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[prepare_scibase] 错误: 无法加载数据集 {REPO_ID}", file=sys.stderr)
        print(f"  原因: {exc}", file=sys.stderr)
        print(f"  最近一次 split 探测失败: {last_err}", file=sys.stderr)
        return None


def cmd_download(limit: int) -> int:
    print("⚠️  注意: Sci-Base 完整数据集约 2500 万篇论文(数百 GB),")
    print(f"    当前默认只拉取样本: --limit {limit} 条。")
    print(f"    如需完整下载,请显式指定 `--limit 0`(不推荐,请评估磁盘与带宽)。")
    print()

    ds = _load_dataset_streaming(limit)
    if ds is None:
        return 1

    # 拉取并规范化
    records: List[Dict[str, Any]] = []
    try:
        for i, row in enumerate(ds):
            if limit and i >= limit:
                break
            rec = _normalize_record(row, i)
            if rec.get("title"):
                records.append(rec)
            if (i + 1) % 100 == 0:
                print(f"  已拉取 {i + 1} 条记录…")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  流式拉取中途中断(已用已获取部分构建索引): {exc}", file=sys.stderr)

    if not records:
        print("[prepare_scibase] 错误: 未获取到任何有效记录(无 title 字段)。", file=sys.stderr)
        print("  可能数据集 schema 已变化,请调整 _normalize_record 的候选字段名。")
        return 1

    index, papers = build_index(records)
    target_dir = get_literature_cache_dir()
    index_file, papers_file = write_index_files(index, papers, target_dir)

    n_terms = sum(len(v) for v in index.values())
    print()
    print("=" * 62)
    print("  Sci-Base 样本索引构建完成")
    print("=" * 62)
    print(f"  论文数   : {len(papers):,}")
    print(f"  词条引用 : {n_terms:,}")
    print(f"  index.json  -> {index_file}")
    print(f"  papers.json -> {papers_file}")
    print(f"  目标目录 : {target_dir}")
    print("-" * 62)
    print("  可用状态: SciBaseSearcher.available = True ✅")
    print("  提示: 样本索引仅覆盖部分论文,检索覆盖面有限;")
    print("        完整下载请重新运行 `--download --limit 0`。")
    return 0


# ═══════════════════════════════════════════════════════════════
# 默认动作: 打印指引(不联网、不下载、不写文件)
# ═══════════════════════════════════════════════════════════════

def cmd_guide() -> int:
    target_dir = get_literature_cache_dir()
    print("=" * 62)
    print("  Sci-Base 数据集接入指引")
    print("=" * 62)
    print("  Sci-Base: HuggingFace opendatalab/Sci-Base")
    print("    2500万+ 篇论文、6000亿+ tokens,覆盖含材料科学的 10 个学科。")
    print()
    print("  本地索引目录(LITERATURE_CACHE_DIR):")
    print(f"    {target_dir}")
    print(f"    当前是否存在 index.json: {Path(target_dir, 'index.json').exists()}")
    print()
    print("  方式一 [推荐] 已有 Sci-Base 索引文件(手工/预置):")
    print(f"    python -X utf8 {_PREPARE_SCRIPT} --index <path/to/index.json>")
    print("    (同目录的 papers.json 会被一并拷贝)")
    print()
    print("  方式二 从 HuggingFace 下载样本构建本地索引:")
    print("    前置: pip install datasets==4.8.4")
    print("    python -X utf8 %s --download --limit 500" % _PREPARE_SCRIPT)
    print("    (默认 500 条样本;--limit 0 表示完整下载,数据极大不推荐)")
    print()
    print("  接入后验证:")
    print('    python -c "from literature_agent.search import SciBaseSearcher;'
          ' print(SciBaseSearcher().available)"')
    print()
    print("  提示: 未就绪时 SciBaseSearcher.available=False 并会自动打印本指引的")
    print("        操作命令。本命令(无参数)不联网、不下载、不写文件。")
    print("=" * 62)
    return 0


# ═══════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog=_PREPARE_SCRIPT,
        description="准备 Sci-Base(opendatalab/Sci-Base)本地索引,供 "
                    "literature_agent.search.SciBaseSearcher 使用。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            f"  python -X utf8 {_PREPARE_SCRIPT}\n"
            f"  python -X utf8 {_PREPARE_SCRIPT} --index my_index.json\n"
            f"  python -X utf8 {_PREPARE_SCRIPT} --download --limit 500"
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--index", metavar="PATH", default=None,
        help="把指定的 index.json 拷入 LITERATURE_CACHE_DIR 并启用 Sci-Base"
             "(同目录 papers.json 一并拷贝)",
    )
    group.add_argument(
        "--download", action="store_true",
        help=f"从 HuggingFace 拉取 {REPO_ID} 样本并构建本地索引"
             "(需 pip install datasets;默认只取样本)",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT, metavar="N",
        help=f"下载样本条数(默认 {DEFAULT_LIMIT};0 表示不限制/完整下载)",
    )
    args = parser.parse_args(argv)

    if args.index:
        return cmd_index(args.index)
    if args.download:
        if args.limit < 0:
            print(f"[prepare_scibase] 错误: --limit 不能为负数(当前 {args.limit})。",
                  file=sys.stderr)
            return 1
        return cmd_download(args.limit)
    return cmd_guide()


if __name__ == "__main__":
    sys.exit(main())
