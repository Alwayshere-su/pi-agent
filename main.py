"""
GOAI 材料科学文献调研 Agent — 主入口
=====================================
接收命令行参数，启动 Pi-Agent 系统，在预算内自主完成文献调研。
四阶段流程：检索 → 知识抽取 → Gap 分析 → 报告生成

用法示例:
    python main.py --topic "MOF materials for CO2 capture"
    python main.py --topic "perovskite solar cell stability" --budget 3600 --fresh
"""
import argparse
import sys

from utils.config import SEED, seed_everything

# ── Windows console compatibility: force UTF-8 for stdout ──────
if sys.platform == "win32":
    try:
        import io as _io
        if sys.stdout is not None and hasattr(sys.stdout, "buffer"):
            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass  # stdout 已被包装/无 buffer（嵌入环境）：维持原样


def run_survey(budget: int = None,
               fresh_start: bool = False, research_topic: str = ""):
    """启动文献调研 Agent。

    Agent 在预算内完成：文献检索、知识抽取、Gap分析、报告生成，
    最终输出结构化调研报告（Markdown + JSON）和过程日志。

    参数:
        budget: 时间预算（秒），默认从配置读取 7200
        fresh_start: 是否强制忽略已有 checkpoint
        research_topic: 文献调研主题
    """
    from pi_agent.agent import PiAgent
    from utils.config import SURVEY_DIR

    print(f"\n{'='*60}")
    print(f"  📚 Literature Survey Agent")
    print(f"  Topic: {research_topic}")
    print(f"  Output: {SURVEY_DIR}")
    print(f"{'='*60}")

    brain = PiAgent(
        budget=budget,
        fresh_start=fresh_start,
        research_topic=research_topic,
    )

    crashed = False
    try:
        brain.run()
        print(f"\n[OK] Survey completed successfully.")
    except KeyboardInterrupt:
        print(f"\n[ABORT] User interrupted", file=sys.stderr)
        crashed = True
    except Exception as e:
        print(f"\n[FAIL] Survey crashed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        crashed = True

    if crashed:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="GOAI Literature Survey Agent — 材料科学文献调研智能体"
    )
    parser.add_argument("--topic", default="",
                       help="文献调研主题，如 'MOF materials for CO2 capture'")
    parser.add_argument("--run-dir", default="survey",
                       help="主题运行目录名（默认 'survey'）。多主题并行调研时各传不同名称"
                            "（如 perovskite / thermoelectric / cathode），产物与记忆完全隔离："
                            "outputs 写入 workspace/outputs/<run-dir>/literature_survey/，"
                            "记忆写入 workspace/memory/<run-dir>/")
    parser.add_argument("--fresh", action="store_true",
                       help="强制从头开始，忽略已有 checkpoint")
    parser.add_argument("--budget", type=int, default=None,
                       help="时间预算（秒），默认 7200（2小时）")
    parser.add_argument("--seed", type=int, default=SEED,
                       help=f"随机种子，默认 {SEED}（固定搜索打分等确定性计算；LLM 采样不受影响）")

    args = parser.parse_args()

    if not args.topic:
        print("Error: --topic is required. Example: --topic 'perovskite solar cells'",
              file=sys.stderr)
        sys.exit(1)

    # 多主题运行目录隔离（默认 run_dir="survey"，与历史版本兼容）
    from utils.config import set_run_dir
    set_run_dir(args.run_dir)

    # 固定随机种子（--seed 覆盖 config.SEED），确定性计算部分可复现
    seed_everything(args.seed)

    run_survey(budget=args.budget, fresh_start=args.fresh, research_topic=args.topic)
    print("\n=== Survey completed ===")


if __name__ == "__main__":
    main()
