# -*- coding: utf-8 -*-
"""
finalize validation discovery — 同步 hypo_4/5 搜索字段 + 用 DiscoveryReport.from_files 重生成报告
=================================================================================================
1) 把 hypo_4/5（下标 3、4）的搜索字段同步为真实搜索（search_h3/4.json 已由
   rerun_validation_search.py 生成）：
   - search_iterations: 0 → 6
   - candidates_explored: 0 → 17（len(iteration_log) + 10）
   - search_warning: 清空（此前"搜索未执行"已不成立）
   - llm_explanation: 对齐 hypo_1/2/3 口径
   - best_score 保持 0.0：与 hypo_1/2/3 一致——h_run_discovery_search 不回写该字段，
     真实 best_score 在 search_h3/4.json 与 discovery_report 中（0.835 / 0.833）。
2) 用 DiscoveryReport.from_files(discovery_dir) 离线重生成 discovery_report.{json,md}
   （不依赖 LLM，从 hypotheses.json + search_h*.json 汇总）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

os.environ["SURVEY_DIR"] = "workspace/outputs/validation/literature_survey"

import utils.config as _cfg
from literature_agent.discovery import DiscoveryReport

_cfg.SURVEY_DIR = "workspace/outputs/validation/literature_survey"
DISCOVERY_DIR = ROOT / "workspace" / "outputs" / "validation" / "literature_survey" / "discovery"

LLM_EXPL = "LLM 合理性评分未产出有效值（支撑文献仅摘要级证据，无定量数据可评估），保留默认 0.0"


def main() -> int:
    hypo_path = DISCOVERY_DIR / "hypotheses.json"
    data = json.loads(hypo_path.read_text(encoding="utf-8"))

    for idx in (3, 4):
        h = data[idx]
        assert h["id"] in ("hypo_4", "hypo_5"), f"下标 {idx} 对应 {h.get('id')}，预期 hypo_4/5"
        before = (h["search_iterations"], h["candidates_explored"], h["search_warning"][:12])
        h["search_iterations"] = 6
        h["candidates_explored"] = 17
        h["search_warning"] = ""
        h["llm_explanation"] = LLM_EXPL
        print(f"  {h['id']}: {before} -> "
              f"(search_iterations=6, candidates=17, search_warning='', llm_explanation aligned)")

    hypo_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ hypotheses.json 已写回（仅改 hypo_4/5 的 4 个字段，其余原样保留）\n")

    # ── DiscoveryReport.from_files 离线重生成报告 ──
    report = DiscoveryReport.from_files(str(DISCOVERY_DIR))
    md_path, json_path = report.save(str(DISCOVERY_DIR))
    print(f"✅ discovery_report 已生成:\n   {md_path}\n   {json_path}\n")

    print(f"头部统计: total_candidates={report.total_candidates}, "
          f"total_explored={report.total_explored}, validated={report.validated_count}, "
          f"refuted={report.refuted_count}, contested={report.contested_count}, "
          f"underexplored={report.underexplored_count}, mp_hits={report.materials_project_hits}")
    for i, h in enumerate(report.hypotheses):
        print(f"  #{i} {h.id}: best_score={h.best_score:.4f} "
              f"| literature_values={len(h.literature_values)} "
              f"| degraded={h.degraded} | search_warning={'Y' if h.search_warning else 'N'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
