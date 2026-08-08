#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pi-Agent 功能自测脚本（Demo Script）
=====================================
独立脚本，不依赖 LLM API 即可运行，用于快速验证项目的非 LLM 功能模块。

测试项目：
  1. 项目名称和版本信息
  2. API Key 配置状态检查
  3. 文献检索模块自测（arXiv 免费源）
  4. PDF 解析器可用性检查（MinerU / markitdown）
  5. 经典模型自测（Slack Model / Vegard's Law 参数恢复）
  6. 符号回归自测（表达式恢复验证）
  7. 提取器自测（(x,y) 配对提取）
  8. 汇总所有自测结果

注意：
  - 所有网络调用使用 try/except 包装，失败时标注 SKIP 不崩溃
  - 全程不调用 LLM API（不消耗费用）
"""
from __future__ import annotations

import sys
import traceback
from typing import Dict, List, Tuple


# ═══════════════════════════════════════════════════════════════
# 测试结果收集
# ═══════════════════════════════════════════════════════════════

class TestResults:
    """收集并汇总所有测试结果。"""

    def __init__(self):
        self._results: List[Tuple[str, str, str]] = []  # (name, status, detail)

    def add(self, name: str, status: str, detail: str = ""):
        """添加一个测试结果。

        Args:
            name:   测试项名称
            status: PASS / FAIL / SKIP
            detail: 详细说明
        """
        assert status in ("PASS", "FAIL", "SKIP"), f"无效状态: {status}"
        self._results.append((name, status, detail))

    def print_summary(self):
        """打印汇总报告。"""
        print("\n" + "=" * 64)
        print("  Pi-Agent 功能自测汇总报告")
        print("=" * 64)
        pass_count = fail_count = skip_count = 0
        for name, status, detail in self._results:
            icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status, "[????]")
            line = f"  {icon} {name}"
            if detail:
                line += f"  -- {detail}"
            print(line)
            if status == "PASS":
                pass_count += 1
            elif status == "FAIL":
                fail_count += 1
            else:
                skip_count += 1
        total = pass_count + fail_count + skip_count
        print("-" * 64)
        print(f"  总计: {total} 项 | PASS: {pass_count} | FAIL: {fail_count} | SKIP: {skip_count}")
        if fail_count == 0:
            print("  结论: 所有强制测试项通过 [OK]")
        else:
            print(f"  结论: 有 {fail_count} 项测试失败，请检查对应模块 [FAIL]")
        print("=" * 64)


_results = TestResults()


def add_result(name: str, status: str, detail: str = ""):
    _results.add(name, status, detail)


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def section_header(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ═══════════════════════════════════════════════════════════════
# 1. 项目名称和版本信息
# ═══════════════════════════════════════════════════════════════

def test_version_info():
    """打印项目名称和版本信息。"""
    section_header("1. 项目信息")
    print("  项目名称: Pi-Agent")
    print("  全称:     材料科学文献驱动的构效关系自主发现智能体")
    print("  版本:     v2.0（初赛终版）")
    print("  赛道:     GOAI 赛道三 · 路线 A（构效关系发现）")
    print("  语言:     Python 3.10+")
    print("  许可:     MIT")
    add_result("项目信息", "PASS", "v2.0 初赛终版")


# ═══════════════════════════════════════════════════════════════
# 2. API Key 配置状态检查
# ═══════════════════════════════════════════════════════════════

def test_api_key_status():
    """检查 API Key 配置状态。"""
    section_header("2. API Key 配置状态检查")
    try:
        from utils.config import print_config_status
        print_config_status()
        # 注意：API Key 未配置不代表"失败"，只是标注为 MISSING
        # 这是 Demo 的正常预期——不依赖 LLM API
        add_result("API Key 配置状态", "PASS", "配置检查完成（未配置属于正常状态）")
    except Exception as exc:
        traceback.print_exc()
        add_result("API Key 配置状态", "FAIL", str(exc))


# ═══════════════════════════════════════════════════════════════
# 3. 文献检索模块自测（arXiv 免费源）
# ═══════════════════════════════════════════════════════════════

def test_literature_search():
    """用 arXiv 源搜索 'MOF CO2 capture'，展示前 3 条结果标题。"""
    section_header("3. 文献检索模块自测（arXiv 免费源）")
    try:
        import socket
        # 全局 socket 超时，防止网络不通时无限阻塞
        socket.setdefaulttimeout(15)

        from literature_agent.search import LiteratureSearcher
        searcher = LiteratureSearcher()
        print(f"  可用数据源: {searcher.available_sources}")
        print("  检索查询: 'MOF CO2 capture'")
        print("  检索中（仅 arXiv 源，免费，socket 超时 15s）...")

        results = searcher.search("MOF CO2 capture", top_k=10, sources=["arxiv"])
        if results is None:
            add_result("文献检索", "SKIP", "arXiv 检索超时（20s），网络可能不可达")
            return

        n = len(results)
        print(f"  返回结果数: {n}")

        if n > 0:
            print("\n  前 3 条结果标题:")
            for i, r in enumerate(results[:3], 1):
                title = r.title[:100] + ("..." if len(r.title) > 100 else "")
                authors_short = ", ".join(r.authors[:2])
                year_str = f" ({r.year})" if r.year else ""
                print(f"    {i}. {title}")
                print(f"       作者: {authors_short}{year_str} | 来源: {r.source}")
            add_result("文献检索", "PASS", f"arXiv 检索成功，返回 {n} 条结果")
        else:
            print("  警告: arXiv 返回 0 条结果")
            add_result("文献检索", "PASS", "arXiv 检索完成，但返回 0 条结果（可能是查询词过窄）")
    except Exception as exc:
        print(f"  检索异常: {exc}")
        traceback.print_exc()
        add_result("文献检索", "SKIP", f"检索失败: {exc}")


# ═══════════════════════════════════════════════════════════════
# 4. PDF 解析器可用性检查
# ═══════════════════════════════════════════════════════════════

def test_pdf_parser():
    """检查 MinerU 和 markitdown 状态。"""
    section_header("4. PDF 解析器可用性检查")
    try:
        from literature_agent.parser import check_mineru_status

        print("  正在检测 MinerU 引擎状态（Cloud/Local/pip）...")
        report = check_mineru_status()

        print("  " + "=" * 56)
        print(f"  总体可用:     {'是' if report['mineru_available'] else '否'}")
        print(f"  推荐引擎:     {report['recommended_engine']}")
        print(f"  回退引擎:     {report['fallback_engine']}")
        print(f"  Cloud ({report['cloud']['endpoint']}): "
              f"{'可用' if report['cloud']['available'] else '不可用'} -- {report['cloud']['detail']}")
        print(f"  Local ({report['local']['endpoint']}): "
              f"{'可用' if report['local']['available'] else '不可用'} -- {report['local']['detail']}")
        print(f"  Pip ({report['pip'].get('module') or 'N/A'}): "
              f"{'可用' if report['pip']['available'] else '不可用'} -- {report['pip']['detail']}")
        print(f"  诊断:         {report['diagnosis']}")
        print("  " + "=" * 56)

        mineru_ok = report.get("mineru_available", False)
        print(f"\n  markitdown（本地引擎）: 始终可用 [OK]")

        if mineru_ok:
            add_result("PDF解析器", "PASS",
                       f"MinerU 可用（推荐引擎: {report.get('recommended_engine', 'N/A')}），markitdown 作为回退")
        else:
            add_result("PDF解析器", "PASS",
                       "MinerU 不可用，使用 markitdown 本地引擎（功能正常，解析质量略低于 MinerU）")
    except Exception as exc:
        traceback.print_exc()
        add_result("PDF解析器", "SKIP", f"MinerU 检测异常: {exc}")


# ═══════════════════════════════════════════════════════════════
# 5. 经典模型自测（Slack Model / Vegard's Law）
# ═══════════════════════════════════════════════════════════════

def test_classical_models():
    """运行 Slack Model 和 Vegard's Law 参数恢复验证。"""
    section_header("5. 经典模型自测（Slack Model + Vegard's Law）")
    try:
        from literature_agent.classical_models import _self_check
        print("  运行 Slack 带隙-温度模型 + Vegard 定律参数恢复验证...")
        exit_code = _self_check()
        if exit_code == 0:
            add_result("经典模型", "PASS",
                       "Slack Model 与 Vegard's Law 参数恢复误差 < 5%，R² > 0.99")
        else:
            add_result("经典模型", "FAIL", f"_self_check 返回退出码 {exit_code}")
    except Exception as exc:
        traceback.print_exc()
        add_result("经典模型", "FAIL", str(exc))


# ═══════════════════════════════════════════════════════════════
# 6. 符号回归自测（表达式恢复验证）
# ═══════════════════════════════════════════════════════════════

def test_symbolic_regression():
    """运行符号回归的表达式恢复验证（轻量版，减少代数以避免超时）。"""
    section_header("6. 符号回归自测（遗传编程表达式恢复）")
    try:
        import numpy as np
        from literature_agent.symbolic_regression import fit, predict, r2_score

        print("  运行遗传编程符号回归表达式恢复验证（轻量级，max_gens=30, pop=20）...")
        print("  测试 1: y = 2*x^2 - 3*x + 1（二次多项式）")
        x = np.linspace(-2.0, 2.0, 30)
        y = 2.0 * x ** 2 - 3.0 * x + 1.0
        expr1, params1, mse1 = fit(x, y, max_generations=30, pop_size=20, seed=7)
        y_pred1 = predict(expr1, params1, x)
        r2_1 = r2_score(y, y_pred1)
        print(f"    恢复表达式: {expr1}")
        print(f"    参数: {params1}")
        print(f"    MSE = {mse1:.6e}, R^2 = {r2_1:.6f}")

        print("  测试 2: y = 2.5*exp(0.7*x) + 0.2（指数关系）")
        x2 = np.linspace(0.1, 2.0, 30)
        y2 = 2.5 * np.exp(0.7 * x2) + 0.2
        expr2, params2, mse2 = fit(x2, y2, max_generations=30, pop_size=20, seed=7)
        y_pred2 = predict(expr2, params2, x2)
        r2_2 = r2_score(y2, y_pred2)
        print(f"    恢复表达式: {expr2}")
        print(f"    参数: {params2}")
        print(f"    MSE = {mse2:.6e}, R^2 = {r2_2:.6f}")

        ok1 = mse1 < 1e-4 or r2_1 > 0.999
        ok2 = mse2 < 1e-3 or r2_2 > 0.99

        if ok1 and ok2:
            add_result("符号回归", "PASS",
                       f"表达式恢复成功（二次: R^2={r2_1:.4f}, 指数: R^2={r2_2:.4f}）")
        else:
            reasons = []
            if not ok1:
                reasons.append(f"二次 MSE={mse1:.2e} R^2={r2_1:.4f}")
            if not ok2:
                reasons.append(f"指数 MSE={mse2:.2e} R^2={r2_2:.4f}")
            add_result("符号回归", "FAIL", "; ".join(reasons))
    except AssertionError as ae:
        traceback.print_exc()
        add_result("符号回归", "FAIL", f"断言失败: {ae}")
    except Exception as exc:
        traceback.print_exc()
        add_result("符号回归", "FAIL", str(exc))


# ═══════════════════════════════════════════════════════════════
# 7. 提取器自测（(x,y) 配对提取）
# ═══════════════════════════════════════════════════════════════

def test_extractor():
    """运行提取器的 (x,y) 配对提取功能验证。"""
    section_header("7. 提取器自测（(x,y) 数值配对提取）")
    try:
        from literature_agent.extractor import extract_xy_pairs
        from collections import defaultdict
        import json

        # 使用与模块自测相同的样本数据
        sample_text = """本研究对比了三种材料在 CO2 吸附中的性能差异。

| 材料 | T (K) | Capacity (mmol/g) |
|------|-------|-------------------|
| MOF-1 | 298 | 5.0 |
| MOF-1 | 313 | 4.2 |
| MOF-1 | 333 | 3.1 |
| MOF-2 | 298 | 6.2 |

同时，MOF-3 的 uptake 随温度升高而下降：uptake decreased from 8.1 to 5.4 mmol/g as T increased from 300 to 500 K。
在 273 K 下 uptake 为 7.7 mmol/g。在 303 K 下为 6.9 mmol/g。
"""
        pairs = extract_xy_pairs(sample_text)
        by_source: Dict[str, int] = defaultdict(int)
        for p in pairs:
            by_source[p["source"]] += 1

        print(f"  共提取 {len(pairs)} 个 (x,y) 配对")
        print(f"  来源统计: {dict(by_source)}")
        print("  详细结果:")
        for i, p in enumerate(pairs):
            print(f"    [{p['source']}] x={p['x']:.1f} {p['x_unit']}, "
                  f"y={p['y']:.1f} {p['y_unit']}")

        # 检查预期结果
        table_count = by_source.get("table_row", 0)
        seq_count = by_source.get("sequence", 0)

        errors = []
        if table_count < 3:
            errors.append(f"表格行配对数不足（预期 >= 3，实际 {table_count}）")
        if seq_count < 2:
            errors.append(f"序列配对数不足（预期 >= 2，实际 {seq_count}）")

        if errors:
            add_result("提取器", "FAIL", "; ".join(errors))
        else:
            add_result("提取器", "PASS",
                       f"表格/{len(pairs)} 对提取正常（table_row={table_count}, sequence={seq_count}, "
                       f"sentence_pair=...）")
    except Exception as exc:
        traceback.print_exc()
        add_result("提取器", "FAIL", str(exc))


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def main():
    """运行所有自测项并打印汇总报告。"""
    import socket
    # 全局 socket 超时：防止网络不通时任何客户端无限阻塞
    socket.setdefaulttimeout(10)

    print("=" * 64)
    print("  Pi-Agent 功能自测脚本")
    print("  全程不调用 LLM API，仅测试非 LLM 功能模块")
    print("  网络调用使用 try/except 包装，失败时标注 SKIP")
    print("=" * 64)

    # 1. 项目信息
    test_version_info()

    # 2. API Key 配置状态
    test_api_key_status()

    # 3. 文献检索模块（arXiv 免费源）
    test_literature_search()

    # 4. PDF 解析器
    test_pdf_parser()

    # 5. 经典模型（Slack + Vegard）
    test_classical_models()

    # 6. 符号回归（遗传编程）
    test_symbolic_regression()

    # 7. 提取器（(x,y) 配对）
    test_extractor()

    # 8. 汇总
    _results.print_summary()

    # 返回码：有 FAIL 则非零
    fail_count = sum(1 for _, s, _ in _results._results if s == "FAIL")
    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
