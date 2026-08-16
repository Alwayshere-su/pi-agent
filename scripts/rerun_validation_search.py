# -*- coding: utf-8 -*-
"""
validation 主题 hypo_4/5（hypotheses.json 下标 3、4）搜索补跑 — 无 LLM 真实执行
==============================================================================
背景：validation（固态锂电池电解质）5 条假设里，hypo_1/2/3 已由主流程执行过
BayesianOptimizer 搜索（search_h0/1/2.json 有真实 iteration_log），hypo_4/5 此前
被标记为"未执行"（search_iterations=0 / search_h3/4 无迭代日志）。

本脚本复刻 h_run_discovery_search 的确定性逻辑（seed=42、BayesianOptimizer、
知识图谱 knowledge_graph.md 作为唯一证据来源），对 hypo_4/5 真实执行搜索并落盘
search_h3.json / search_h4.json——评分只依赖文献证据打分，不调用 LLM，
best_score 为如实结果（证据数值可能为 0 组，故分数可能偏低，属数据不足的如实反映）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

# 固定运行目录到 validation 主题（务必在 import pi_agent.tools 前设置，
# 因为 pi_agent.tools 模块级 import utils.config 会读取 SURVEY_DIR）
os.environ["SURVEY_DIR"] = "workspace/outputs/validation/literature_survey"

import numpy as np

import utils.config as _cfg
from pi_agent.tools import ToolHandlers
from literature_agent.discovery import BayesianOptimizer
from utils.config import SEED

_cfg.SURVEY_DIR = "workspace/outputs/validation/literature_survey"

DISCOVERY_DIR = ROOT / "workspace" / "outputs" / "validation" / "literature_survey" / "discovery"
N_ITERATIONS = 6  # 与 hypo_1（同为电导率类假设）保持一致；search_h0 即 6 轮


def main() -> int:
    handlers = ToolHandlers(task_type="survey", bench="A", print_fn=print)

    hypo_path = DISCOVERY_DIR / "hypotheses.json"
    hypotheses_data = json.loads(hypo_path.read_text(encoding="utf-8"))

    source_text = handlers._load_knowledge_source()
    if not source_text:
        print("❌ 找不到知识来源（knowledge_graph.md / paper_summaries.md）")
        return 1
    print(f"知识来源字符数: {len(source_text)}")

    for idx in (3, 4):
        hyp = handlers._safe_hypothesis(hypotheses_data[idx])
        evid = handlers._build_evidence_index(source_text, hyp)
        param_space = handlers._search_space(evid)
        unit_filter = handlers._unit_filter(hyp.property)

        print("\n" + "=" * 70)
        print(f"假设 #{idx} — {hyp.title}")
        print(f"  性质: {hyp.property}")
        print(f"  材料数: {len(hyp.materials)}")
        print(f"  性质关键词: {evid['prop_keywords']}")
        print(f"  单位过滤: {unit_filter}")
        print(f"  证据块: {len(evid['blocks'])} | 材料 token: {len(evid['material_tokens'])}")
        print(f"  文献数值: {len(evid['values'])} 个 {evid['values'][:10]}")
        print(f"  参数空间: {param_space}")

        np_state = np.random.get_state()
        np.random.seed(SEED)
        try:
            best_params, best_score, log = BayesianOptimizer().optimize(
                hyp, param_space,
                objective_fn=lambda p: handlers._evidence_score(p, hyp, evid),
                n_iterations=N_ITERATIONS,
            )
        finally:
            np.random.set_state(np_state)

        print(f"  best_score = {best_score:.6f}")
        print(f"  best_params = {best_params}")
        print(f"  iteration_log 长度 = {len(log)}（含 initial）")

        search_results = {
            "hypothesis_index": idx,
            "search_method": "bayesian",
            "iterations": N_ITERATIONS,
            "evidence": {
                "source": "knowledge_graph.md",
                "blocks": len(evid["blocks"]),
                "material_tokens": len(evid["material_tokens"]),
                "property_keywords": evid["prop_keywords"][:10],
                "literature_values": evid["values"][:20],
            },
            "best_params": best_params,
            "best_score": best_score,
            "iteration_log": log[-10:],
        }
        out_file = DISCOVERY_DIR / f"search_h{idx}.json"
        out_file.write_text(
            json.dumps(search_results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  ✅ 已写入 {out_file.name}")
        print(f"  → search_iterations={N_ITERATIONS}, candidates_explored={len(log) + 10}")

    print("\n" + "=" * 70)
    print("搜索补跑完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
