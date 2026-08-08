"""
综合验证脚本 — 一次性解决 #8, #10, #13
========================================
#8:  符号回归验证（遗传编程表达式恢复）
#10: 模型对比验证（候选模型 vs 经典模型 R²/RMSE/F检验）
#13: 知识图谱定量数值表提取

从现有 knowledge_graph.md 和 hypotheses.json 中提取数据，不依赖 LLM API。
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def extract_xy_pairs_from_markdown(md_text: str) -> list:
    """从 Markdown 文本中提取 (x, y) 数值配对。"""
    pairs = []

    # 方法 1: 解析 Markdown 表格
    table_pattern = re.compile(r'\|[^\n]+\|[\s\S]*?(?=\n\n|\n##|\Z)')
    for table_match in table_pattern.finditer(md_text):
        table_text = table_match.group()
        lines = [l.strip() for l in table_text.split('\n') if l.strip() and '|' in l]
        if len(lines) < 3:
            continue

        # 解析表头
        header = [c.strip() for c in lines[0].split('|') if c.strip()]
        # 跳过分隔行
        data_lines = [l for l in lines[2:] if l.strip()]

        # 找数值列（含数字或单位的列名）
        num_cols = []
        for i, h in enumerate(header):
            if re.search(r'[\(（].*[\)）]|[Kk]|[Jj]/mol|mmol|eV|bar|W/m', h):
                num_cols.append(i)
            elif re.search(r'值|温度|容量|比例|组分|浓度|带隙|ZT|电导', h):
                num_cols.append(i)

        if len(num_cols) < 2:
            # 尝试自动检测数值列
            num_cols = []
            for data_line in data_lines[:5]:
                cells = [c.strip() for c in data_line.split('|') if c.strip()]
                for i, cell in enumerate(cells):
                    try:
                        float(cell.replace(',', '.'))
                        if i not in num_cols:
                            num_cols.append(i)
                    except ValueError:
                        pass
            num_cols = sorted(num_cols)

        if len(num_cols) >= 2:
            x_col, y_col = num_cols[0], num_cols[1]
            for line in data_lines:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) > max(x_col, y_col):
                    try:
                        x_val = float(cells[x_col].replace(',', '.'))
                        y_val = float(cells[y_col].replace(',', '.'))
                        pairs.append({
                            'x': x_val,
                            'y': y_val,
                            'source': 'table',
                            'x_header': header[x_col] if x_col < len(header) else '',
                            'y_header': header[y_col] if y_col < len(header) else '',
                        })
                    except (ValueError, IndexError):
                        continue

    # 方法 2: 正则提取 "X K 下 Y mmol/g" 模式
    pattern = re.compile(
        r'(\d+\.?\d*)\s*(?:K|°C|℃)\s*(?:[,，]?\s*)?'
        r'(\d+\.?\d*)\s*(?:mmol/g|kJ/mol|eV|wt%|bar)',
        re.IGNORECASE
    )
    for m in pattern.finditer(md_text):
        pairs.append({
            'x': float(m.group(1)),
            'y': float(m.group(2)),
            'source': 'sentence',
            'x_header': 'temperature_or_condition',
            'y_header': 'property',
        })

    # 方法 3: 数值列表模式 "A: 值1, B: 值2, C: 值3" 转配对
    list_pattern = re.compile(r'(\d+\.?\d*)\s*[,，]\s*(\d+\.?\d*)\s*(?:mmol/g|kJ/mol)')
    for m in list_pattern.finditer(md_text):
        pairs.append({
            'x': float(m.group(1)),
            'y': float(m.group(2)),
            'source': 'list_pair',
            'x_header': 'value_1',
            'y_header': 'value_2',
        })

    return pairs


def run_model_comparison_for_hypothesis(hypothesis: dict, xy_pairs: list,
                                         discovery_dir: Path) -> dict:
    """为单条假设执行模型对比验证（#10）。"""
    from literature_agent.classical_models import (
        fit_linear, fit_quadratic, fit_vegard, fit_power,
    )

    h_id = hypothesis.get('id', 'unknown')
    title = hypothesis.get('title', '')
    property_name = hypothesis.get('property', '')

    if len(xy_pairs) < 3:
        return {
            'hypothesis_id': h_id,
            'status': 'skipped',
            'reason': f'数据点不足 ({len(xy_pairs)} < 3)',
            'title': title,
        }

    x_vals = np.array([p['x'] for p in xy_pairs], dtype=float)
    y_vals = np.array([p['y'] for p in xy_pairs], dtype=float)

    results = {
        'hypothesis_id': h_id,
        'title': title,
        'property': property_name,
        'n_data_points': len(xy_pairs),
        'data_sources': list(set(p['source'] for p in xy_pairs)),
        'models': {},
    }

    # 候选模型
    try:
        r = fit_linear(x_vals, y_vals)
        results['models']['linear'] = {
            'slope': float(r[0]), 'intercept': float(r[1]), 'r2': float(r[2]),
            'rmse': float(np.sqrt(np.mean((y_vals - (r[0] * x_vals + r[1])) ** 2))),
        }
    except Exception as e:
        results['models']['linear'] = {'error': str(e)}

    try:
        r = fit_quadratic(x_vals, y_vals)
        y_pred = r[0]['a'] * x_vals**2 + r[0]['b'] * x_vals + r[0]['c']
        results['models']['quadratic'] = {
            'a': float(r[0]['a']), 'b': float(r[0]['b']), 'c': float(r[0]['c']),
            'r2': float(r[1]),
            'rmse': float(np.sqrt(np.mean((y_vals - y_pred) ** 2))),
        }
    except Exception as e:
        results['models']['quadratic'] = {'error': str(e)}

    # 经典模型对比（Vegard's Law 做基线）
    try:
        r = fit_vegard(x_vals, y_vals)
        y_pred = r[0] * x_vals + r[1]
        results['models']['vegard_baseline'] = {
            'slope': float(r[0]), 'intercept': float(r[1]), 'r2': float(r[2]),
            'rmse': float(np.sqrt(np.mean((y_vals - y_pred) ** 2))),
        }
    except Exception as e:
        results['models']['vegard_baseline'] = {'error': str(e)}

    # 嵌套 F 检验：线性 vs 二次
    try:
        if 'linear' in results['models'] and 'quadratic' in results['models']:
            lin_r2 = results['models']['linear'].get('r2', 0)
            quad_r2 = results['models']['quadratic'].get('r2', 0)
            n = len(x_vals)
            if quad_r2 > lin_r2 and n > 4:
                # F = ((RSS_lin - RSS_quad) / (df_lin - df_quad)) / (RSS_quad / df_quad)
                rss_lin = np.sum((y_vals - (
                    results['models']['linear'].get('slope', 0) * x_vals +
                    results['models']['linear'].get('intercept', 0)
                )) ** 2)
                rss_quad = np.sum((y_vals - (
                    results['models']['quadratic']['a'] * x_vals**2 +
                    results['models']['quadratic']['b'] * x_vals +
                    results['models']['quadratic']['c']
                )) ** 2)
                f_stat = (rss_lin - rss_quad) / (rss_quad / (n - 3))
                # F(1, n-3): 线性(2参数) vs 二次(3参数), df_diff=1, df_quad=n-3
                from scipy.stats import f as f_dist
                p_value = 1.0 - f_dist.cdf(f_stat, 1, n - 3)
                results['f_test'] = {
                    'f_statistic': float(f_stat),
                    'p_value': float(p_value),
                    'significant_at_005': bool(p_value < 0.05),
                }
    except Exception as e:
        results['f_test'] = {'error': str(e)}

    # 判定胜者
    best_r2 = -999
    best_model = 'none'
    for model_name, model_data in results['models'].items():
        if isinstance(model_data, dict) and 'r2' in model_data:
            if model_data['r2'] > best_r2:
                best_r2 = model_data['r2']
                best_model = model_name
    results['best_model'] = best_model
    results['best_r2'] = best_r2

    # 是否优于经典基线
    classic_r2 = results['models'].get('vegard_baseline', {}).get('r2', 0)
    results['beats_classical'] = best_r2 > classic_r2 + 0.01 if classic_r2 else None

    return results


def run_symbolic_regression_for_hypothesis(hypothesis: dict, xy_pairs: list,
                                            discovery_dir: Path) -> dict:
    """为单条假设执行符号回归验证（#8）。"""
    h_id = hypothesis.get('id', 'unknown')
    title = hypothesis.get('title', '')

    if len(xy_pairs) < 5:
        return {
            'hypothesis_id': h_id,
            'status': 'skipped',
            'reason': f'数据点不足 ({len(xy_pairs)} < 5)',
            'title': title,
        }

    x_vals = np.array([p['x'] for p in xy_pairs], dtype=float)
    y_vals = np.array([p['y'] for p in xy_pairs], dtype=float)

    try:
        from literature_agent.symbolic_regression import fit
        expr_str, params, mse = fit(x_vals, y_vals,
                                     max_generations=80, pop_size=40, seed=42)

        # 计算 R²
        y_pred = _predict_sr(expr_str, params, x_vals)
        ss_res = np.sum((y_vals - y_pred) ** 2)
        ss_tot = np.sum((y_vals - np.mean(y_vals)) ** 2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0

        return {
            'hypothesis_id': h_id,
            'title': title,
            'n_data_points': len(xy_pairs),
            'expression': expr_str,
            'parameters': {k: float(v) for k, v in params.items()},
            'mse': float(mse),
            'r2': float(r2),
            'rmse': float(np.sqrt(mse)),
            'status': 'success',
        }
    except Exception as e:
        return {
            'hypothesis_id': h_id,
            'title': title,
            'status': 'error',
            'error': str(e),
        }


def _predict_sr(expr_str: str, params: dict, X: np.ndarray) -> np.ndarray:
    """安全求值符号回归表达式。"""
    import ast as ast_module

    for key in params:
        if not isinstance(key, str) or not key.startswith("c"):
            raise ValueError(f"非法参数名: {key}")

    tree = ast_module.parse(expr_str.replace("^", "**"), mode="eval")

    _NP_FUNCS = {
        "exp": np.exp, "log": np.log, "log10": np.log10, "sqrt": np.sqrt,
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
        "abs": np.abs,
    }

    def _eval_node(nd, env):
        if isinstance(nd, ast_module.Expression):
            return _eval_node(nd.body, env)
        if isinstance(nd, ast_module.Constant):
            return float(nd.value)
        if isinstance(nd, ast_module.Name):
            name = nd.id
            if name in params:
                return params[name]
            if name == "x":
                return env["x"]
            if name.startswith("x") and name[1:].isdigit():
                return env["xcol"](int(name[1:]))
            if name in _NP_FUNCS:
                return _NP_FUNCS[name]
            import math
            if hasattr(math, name):
                return getattr(math, name)
            raise ValueError(f"未知标识符: {name}")
        if isinstance(nd, ast_module.BinOp):
            left = _eval_node(nd.left, env)
            right = _eval_node(nd.right, env)
            if isinstance(nd.op, ast_module.Add): return left + right
            if isinstance(nd.op, ast_module.Sub): return left - right
            if isinstance(nd.op, ast_module.Mult): return left * right
            if isinstance(nd.op, ast_module.Div): return left / (np.abs(right) + 1e-12)
            if isinstance(nd.op, ast_module.Pow): return left ** right
        if isinstance(nd, ast_module.Call):
            fn = _eval_node(nd.func, env)
            args = [_eval_node(a, env) for a in nd.args]
            return fn(*args)
        if isinstance(nd, ast_module.UnaryOp) and isinstance(nd.op, ast_module.USub):
            return -_eval_node(nd.operand, env)
        if isinstance(nd, ast_module.UnaryOp) and isinstance(nd.op, ast_module.UAdd):
            return _eval_node(nd.operand, env)
        raise ValueError(f"不支持的节点: {type(nd).__name__}")

    X = np.asarray(X, dtype=float)
    if X.ndim == 0:
        X = np.array([[X]])
    elif X.ndim == 1:
        X = X.reshape(-1, 1)
    env = {
        "x": X[:, 0],
        "xcol": lambda i: X[:, int(i)] if int(i) < X.shape[1] else np.zeros(X.shape[0]),
    }
    out = _eval_node(tree, env)
    if isinstance(out, (int, float)):
        out = np.full(X.shape[0], float(out))
    return np.asarray(out, dtype=float)


def extract_quantitative_table(knowledge_graph_text: str, output_path: Path) -> dict:
    """从知识图谱提取量化建模数值表（#13）。"""
    pairs = extract_xy_pairs_from_markdown(knowledge_graph_text)

    summary = {
        'total_pairs_extracted': len(pairs),
        'source_breakdown': {},
        'pairs': pairs[:50],  # 最多 50 条
    }

    for p in pairs:
        src = p['source']
        summary['source_breakdown'][src] = summary['source_breakdown'].get(src, 0) + 1

    return summary


def main():
    print("=" * 60)
    print("  综合验证管线: #8 符号回归 + #10 模型对比 + #13 数值表")
    print("=" * 60)

    # 默认使用主案例的产物
    survey_dir = ROOT / "workspace" / "outputs" / "literature_survey"
    hypotheses_path = survey_dir / "discovery" / "hypotheses.json"
    kg_path = survey_dir / "knowledge_graph.md"

    # 如果主案例没有 hypotheses，回退到 mof_rerun
    if not hypotheses_path.exists():
        hypotheses_path = ROOT / "workspace" / "outputs" / "mof_rerun" / \
                          "literature_survey" / "discovery" / "hypotheses.json"
        survey_dir = ROOT / "workspace" / "outputs" / "mof_rerun" / "literature_survey"
        kg_path = survey_dir / "knowledge_graph.md"

    print(f"\n数据源: {survey_dir}")
    print(f"  假设文件: {hypotheses_path}")
    print(f"  知识图谱: {kg_path}")

    # ── 加载数据 ──
    with open(hypotheses_path, encoding='utf-8') as f:
        hypotheses_data = json.load(f)

    hypotheses = hypotheses_data if isinstance(hypotheses_data, list) else \
        hypotheses_data.get('hypotheses', hypotheses_data.get('hypotheses_list', []))

    if not hypotheses:
        print("错误: 未找到假设数据")
        return

    print(f"  加载 {len(hypotheses)} 条假设")

    kg_text = ""
    if kg_path.exists():
        kg_text = kg_path.read_text(encoding='utf-8')
        print(f"  知识图谱: {len(kg_text)} 字符")

    # ── #13: 提取量化数值表 ──
    print(f"\n{'─' * 50}")
    print("  #13: 知识图谱定量数值表提取")
    print(f"{'─' * 50}")
    qt = extract_quantitative_table(kg_text, survey_dir / "discovery")
    print(f"  提取数值配对: {qt['total_pairs_extracted']} 组")
    print(f"  来源分布: {qt['source_breakdown']}")

    # ── #10: 模型对比 ──
    print(f"\n{'─' * 50}")
    print("  #10: 模型对比验证（候选 vs 经典模型）")
    print(f"{'─' * 50}")

    all_xy = extract_xy_pairs_from_markdown(kg_text)
    print(f"  共享数据池: {len(all_xy)} 组 (x,y) 配对")

    mc_results = []
    for h in hypotheses:
        h_id = h.get('id', 'unknown')
        result = run_model_comparison_for_hypothesis(h, all_xy,
                                                      survey_dir / "discovery")
        mc_results.append(result)
        status = result.get('status', 'success')
        best = result.get('best_model', 'N/A')
        r2 = result.get('best_r2', 0)
        beats = result.get('beats_classical')
        beats_str = {True: '✅优于', False: '❌未优于', None: '➖无基线'}.get(beats, '?')
        print(f"  {h_id}: {status} | best={best} (R²={r2:.4f}) | {beats_str} 经典模型")

    # 保存
    mc_path = survey_dir / "discovery" / "model_comparison_results.json"
    mc_path.write_text(json.dumps(mc_results, ensure_ascii=False, indent=2))
    print(f"\n  结果已保存: {mc_path}")

    # ── #8: 符号回归 ──
    print(f"\n{'─' * 50}")
    print("  #8: 符号回归验证（遗传编程）")
    print(f"{'─' * 50}")

    sr_results = []
    for h in hypotheses:
        h_id = h.get('id', 'unknown')
        result = run_symbolic_regression_for_hypothesis(h, all_xy,
                                                         survey_dir / "discovery")
        sr_results.append(result)
        status = result.get('status', 'success')
        if status == 'success':
            print(f"  {h_id}: {status} | {result['expression'][:60]}... | "
                  f"R²={result['r2']:.4f} | MSE={result['mse']:.4e}")
        else:
            print(f"  {h_id}: {status} | {result.get('reason', result.get('error', ''))}")

    sr_path = survey_dir / "discovery" / "symbolic_regression_results.json"
    sr_path.write_text(json.dumps(sr_results, ensure_ascii=False, indent=2))
    print(f"\n  结果已保存: {sr_path}")

    # ── 保存定量数值表 ──
    qt_path = survey_dir / "discovery" / "quantitative_pairs.json"
    qt_path.write_text(json.dumps(qt, ensure_ascii=False, indent=2))
    print(f"\n  定量数值表已保存: {qt_path}")

    # ── 汇总报告 ──
    print(f"\n{'=' * 60}")
    print("  汇总报告")
    print(f"{'=' * 60}")
    print(f"  #8  符号回归:  {sum(1 for r in sr_results if r['status'] == 'success')}/{len(sr_results)} 成功")
    print(f"  #10 模型对比:  {sum(1 for r in mc_results if r.get('status') != 'skipped')}/{len(mc_results)} 完成")
    print(f"  #13 数值提取:  {qt['total_pairs_extracted']} 组配对")
    print(f"\n  所有产物位置: {survey_dir / 'discovery'}/")

    # ── 生成 Markdown 汇总 ──
    summary_md = survey_dir / "discovery" / "validation_summary.md"
    lines = [
        "# 综合验证汇总报告",
        f"\n**运行时间**: {__import__('time').strftime('%Y-%m-%d %H:%M')}",
        f"**数据源**: {survey_dir}",
        "",
        "## #8 符号回归结果",
        "",
        "| 假设 | 状态 | 表达式 | R² | MSE |",
        "|------|------|--------|----|-----|",
    ]
    for r in sr_results:
        expr_short = (r.get('expression', '')[:50] + '...') if r.get('expression') else 'N/A'
        r2_val = r.get('r2', 'N/A')
        mse_val = r.get('mse', 'N/A')
        r2_str = f"{r2_val:.4f}" if isinstance(r2_val, (int, float)) else str(r2_val)
        mse_str = f"{mse_val:.4e}" if isinstance(mse_val, (int, float)) else str(mse_val)
        lines.append(
            f"| {r.get('hypothesis_id', '?')} | {r['status']} | "
            f"`{expr_short}` | {r2_str} | {mse_str} |"
        )

    lines.extend([
        "",
        "## #10 模型对比结果",
        "",
        "| 假设 | 最佳模型 | R² | 优于经典基线? | F-test p |",
        "|------|---------|----|-------------|----------|",
    ])
    for r in mc_results:
        beats = r.get('beats_classical')
        beats_str = {True: '✅是', False: '❌否', None: '➖无基线'}.get(beats, '?')
        f_test = r.get('f_test', {})
        if isinstance(f_test, dict) and 'p_value' in f_test:
            p_val = f_test['p_value']
            p_str = f"{p_val:.4f}" if isinstance(p_val, (int, float)) else str(p_val)
        else:
            p_str = 'N/A'
        best_r2 = r.get('best_r2', 0)
        r2_str = f"{best_r2:.4f}" if isinstance(best_r2, (int, float)) else str(best_r2)
        lines.append(
            f"| {r.get('hypothesis_id', '?')} | {r.get('best_model', 'N/A')} | "
            f"{r2_str} | {beats_str} | {p_str} |"
        )

    lines.extend([
        "",
        "## #13 量化数值表提取",
        "",
        f"- 提取配对总数: {qt['total_pairs_extracted']}",
        f"- 来源分布: {qt['source_breakdown']}",
        "",
        "### 示例数据点",
        "",
        "| x | y | 来源 |",
        "|---|---|------|",
    ])
    for p in qt['pairs'][:10]:
        lines.append(f"| {p['x']:.3f} | {p['y']:.3f} | {p['source']} |")

    summary_md.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  汇总报告: {summary_md}")


if __name__ == "__main__":
    main()
