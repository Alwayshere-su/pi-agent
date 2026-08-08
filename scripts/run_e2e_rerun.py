#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOAI 路线 A — v2 端到端全量重跑一键脚本（问题 #12 残余验证）
================================================================
背景
----
主案例（MOF materials for CO2 capture）的 search_h*.json 中 llm_guidance
是**回填的审计记录**（note 带 "[回填审计]"、事件与 iteration_log 采样点无
关联），LLM 建议未真正影响搜索采样路径。v2 代码（literature_agent/discovery.py
的 BayesianOptimizer）已实现 `llm_guide` 回调：_llm_search_guide 真实调用
DeepSeek 生成 suggestion / prune_regions / focus_regions，_apply_llm_regions
将其应用到 _acquisition 采样阶段（聚焦采样 + 剪枝剔除）。

本脚本在**全新 run-dir** 上执行一次完整重跑（避免覆盖主案例产物），并自动
校验新 search_h*.json 的 llm_guidance 是否由真实 LLM 调用产生、是否真正影响
采样。

用法（脚本会自行切换到项目根目录，任意 cwd 均可）：
    python workspace/code/survey/run_e2e_rerun.py --dry-run            # 只做前置检查，不运行
    python workspace/code/survey/run_e2e_rerun.py                       # 全新重跑（run-dir=mof_e2e_v3, --fresh）
    python workspace/code/survey/run_e2e_rerun.py --resume              # 断点续跑（同 run-dir，不带 --fresh）
    python workspace/code/survey/run_e2e_rerun.py --run-dir my_run --budget 3600 --seed 42
    python workspace/code/survey/run_e2e_rerun.py --skip-verify         # 只跑，不做运行后校验

说明：本脚本只负责编排（前置检查 → 运行 main.py → 运行后校验）。
main.py 的真实执行与 LLM 调用在本环境外进行（父代理执行），脚本不做任何伪造。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── 项目根：workspace/code/survey/run_e2e_rerun.py → 上溯 3 级 ──
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # 统一以项目根为 cwd（utils.config 的路径都是相对 cwd）
sys.path.insert(0, str(ROOT))  # 确保可 import 项目包（utils / pi_agent / literature_agent）

# ── Windows console compatibility: force UTF-8 for stdout ──────
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

MIN_FREE_GB = 3.0          # 磁盘空间下限（GB）
REQUIRED_MODULES = [
    "utils.config",
    "pi_agent.agent",
    "literature_agent.discovery",
    "openai",
]
# run_dir 涉及的隔离目录（set_run_dir 规则）
RUN_DIR_DIRS = [
    "workspace/outputs/{rd}/literature_survey",
    "workspace/memory/{rd}",
    "workspace/logs/{rd}",
    "workspace/checkpoint/{rd}",
    "workspace/data/literature_cache/{rd}",
]
CHECKPOINT_FILE = "workspace/checkpoint/{rd}/checkpoint_survey.json"
# 主案例（旧）产物目录：用于对比"回填 vs 真实"
OLD_SURVEY_DIR = Path("workspace/outputs/literature_survey")


# ═══════════════════════════════════════════════════════════════════
# 1) 前置检查
# ═══════════════════════════════════════════════════════════════════

def check_deps() -> list[tuple[bool, str]]:
    """依赖导入检查：返回 [(passed, msg), ...]。"""
    problems: list[tuple[bool, str]] = []
    for mod in REQUIRED_MODULES:
        try:
            __import__(mod)
        except Exception as e:  # noqa: BLE001
            problems.append((False, f"依赖导入失败: {mod} → {e}"))
    if not problems:
        # 尝试导入 utils.config 里的关键常量，确认包可用
        try:
            from utils.config import DEEPSEEK_API_KEY, set_run_dir  # noqa: F401
            problems.append((True, "全部必需依赖导入成功"))
        except Exception as e:  # noqa: BLE001
            problems.append((False, f"utils.config 导入异常: {e}"))
    return problems


def check_api_key() -> tuple[bool, str]:
    """API key 状态检查（环境变量 → .api_key 文件）。"""
    try:
        from utils.config import DEEPSEEK_API_KEY, _is_placeholder
        if bool(DEEPSEEK_API_KEY) and not _is_placeholder(DEEPSEEK_API_KEY):
            return True, f"DeepSeek API key 有效（{len(DEEPSEEK_API_KEY)} 字符）"
        return False, "DeepSeek API key 为空或为占位符（检查 .api_key 文件 / DEEPSEEK_API_KEY 环境变量）"
    except Exception as e:  # noqa: BLE001
        return False, f"无法读取 API key 配置: {e}"


def check_disk() -> tuple[bool, str]:
    """磁盘空间检查。"""
    try:
        usage = shutil.disk_usage(ROOT)
        free_gb = usage.free / 1e9
        if free_gb < MIN_FREE_GB:
            return False, f"磁盘空间不足：剩余 {free_gb:.1f}GB < {MIN_FREE_GB}GB"
        return True, f"磁盘空间充足（剩余 {free_gb:.1f}GB）"
    except Exception as e:  # noqa: BLE001
        return True, f"磁盘空间检查失败（忽略）: {e}"


def check_run_dir(run_dir: str, resume: bool) -> tuple[bool, str]:
    """run-dir 隔离目录检查。

    fresh 模式：所有隔离目录必须不存在（避免覆盖任何已有产物）。
    resume 模式：必须存在 checkpoint（否则不是有效续跑点）。
    """
    existing = [d.format(rd=run_dir) for d in RUN_DIR_DIRS if Path(d.format(rd=run_dir)).exists()]
    ckpt = Path(CHECKPOINT_FILE.format(rd=run_dir))

    if resume:
        if not ckpt.exists():
            return False, (
                f"续跑模式（--resume）但未找到 checkpoint：{ckpt}。"
                f"若从未运行过，请去掉 --resume 全新开始。"
            )
        return True, (
            f"续跑模式：将恢复 checkpoint（{ckpt}）。"
            + (f"注意：run-dir 已有 {len(existing)} 个隔离目录，不会被覆盖。" if existing else "")
        )

    if existing:
        return False, (
            f"run-dir '{run_dir}' 已存在以下隔离目录，全新重跑会与之混合：\n  "
            + "\n  ".join(existing)
            + "\n请改用其他 --run-dir，或确认后加 --force（跳过此检查）。"
        )
    return True, f"run-dir '{run_dir}' 全新可用（无任何隔离目录冲突）"


def preflight(args: argparse.Namespace) -> bool:
    """全部前置检查；返回 True 表示可继续。"""
    print("\n" + "=" * 64)
    print("  前置检查")
    print("=" * 64)
    ok = True
    for name, fn in [
        ("依赖导入", check_deps),
        ("API Key", lambda: [check_api_key()]),
        ("磁盘空间", lambda: [check_disk()]),
    ]:
        results = fn()
        for passed, msg in results:
            flag = "[OK]" if passed else "[FAIL]"
            print(f"  {flag} {name}: {msg}")
            ok = ok and passed

    passed, msg = check_run_dir(args.run_dir, args.resume)
    print(f"  {'[OK]' if passed else '[FAIL]'} run-dir 隔离: {msg}")
    ok = ok and passed

    if not ok and not args.force:
        print("\n❌ 前置检查未通过。修复后重试，或加 --force 跳过（不推荐）。")
        return False
    if not ok and args.force:
        print("\n⚠️ 前置检查存在失败项，但 --force 已指定，继续。")
    return True


# ═══════════════════════════════════════════════════════════════════
# 2) 实际运行
# ═══════════════════════════════════════════════════════════════════

def run_survey(args: argparse.Namespace) -> int:
    """调用 main.py 运行 Agent（真实执行，由本脚本外部环境提供 Python 能力）。"""
    log_dir = Path(f"workspace/logs/{args.run_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"run_e2e_rerun_{time.strftime('%Y%m%d_%H%M%S')}.log"
    # 同时保留一个固定名日志便于续跑查找
    fixed_log = log_dir / "run_e2e_rerun.log"

    cmd = [
        sys.executable, "main.py",
        "--topic", args.topic,
        "--run-dir", args.run_dir,
        "--budget", str(args.budget),
        "--seed", str(args.seed),
    ]
    if args.fresh:
        cmd.append("--fresh")

    print("\n" + "=" * 64)
    print("  运行命令")
    print("=" * 64)
    print("  " + " ".join(cmd))
    print(f"  日志: {log_path}  （运行前先清空固定名日志）")
    fixed_log.write_text("", encoding="utf-8")

    with log_path.open("w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            cmd, cwd=str(ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lf.write(line)
        ret = proc.wait()
        # 同步到固定名日志（续跑时便于查看最近一次）
        try:
            shutil.copyfile(log_path, fixed_log)
        except OSError:
            pass

    print(f"\n{'='*64}\n  main.py 退出码: {ret}\n{'='*64}")
    return ret


# ═══════════════════════════════════════════════════════════════════
# 3) 运行后校验：llm_guidance 真实性 + 产物清单
# ═══════════════════════════════════════════════════════════════════

def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def verify_llm_guidance(run_dir: str) -> tuple[list[str], list[dict], dict]:
    """校验新 search_h*.json 的 llm_guidance。

    返回 (failures, per_file, summary)。
    判据：
      A. llm_guidance.enabled == True 且 injected == True
      B. n_events >= 2（initial 事件 + 至少一个周期事件）
      C. 至少一个 bayes_llm_guide 事件带非空 suggestion（证明真实 LLM 参与）
      D. 没有任何事件 note 含 "[回填审计]"（证明非回填产物）
      E. 若搜索方法是 bayesian，应存在 bayes_llm_region_apply 事件
         （证明 prune/focus 已应用到搜索空间）
    """
    dis_dir = Path(f"workspace/outputs/{run_dir}/literature_survey/discovery")
    files = sorted(dis_dir.glob("search_h*.json")) if dis_dir.exists() else []
    failures: list[str] = []
    per_file: list[dict] = []

    if not files:
        failures.append(f"未找到 {dis_dir}/search_h*.json —— 搜索阶段可能未执行或产物路径异常")
        return failures, per_file, {
            "n_files": 0, "n_fail": len(failures),
            "all_injected": False, "all_with_suggestion": False, "none_backfilled": True,
        }

    for f in files:
        data = _read_json(f)
        rec = {"file": f.name}
        guidance = data.get("llm_guidance") or {}
        enabled = bool(guidance.get("enabled"))
        injected = bool(guidance.get("injected"))
        n_events = int(guidance.get("n_events", 0))
        events = guidance.get("events") or []
        if not isinstance(events, list):
            events = []
        events = [e for e in events if isinstance(e, dict)]

        has_suggestion = any(
            e.get("type") == "bayes_llm_guide" and str(e.get("suggestion") or "").strip()
            for e in events
        )
        has_backfill_note = any("[回填审计]" in str(e.get("note", "")) for e in events)
        has_region_apply = any(e.get("type") == "bayes_llm_region_apply" for e in events)

        rec.update({
            "enabled": enabled, "injected": injected, "n_events": n_events,
            "has_suggestion": has_suggestion,
            "has_backfill_note": has_backfill_note,
            "has_region_apply": has_region_apply,
            "best_params": data.get("best_params") or data.get("best_state"),
            "iterations": data.get("iterations") or data.get("iterations", len(data.get("iteration_log", []))),
            "search_method": data.get("search_method"),
        })

        if not (enabled and injected):
            failures.append(f"{f.name}: llm_guidance.enabled/injected 不为 true（enabled={enabled}, injected={injected}）")
        if n_events < 2:
            failures.append(f"{f.name}: n_events={n_events} < 2，LLM 引导未按预期触发")
        if not has_suggestion:
            failures.append(f"{f.name}: 无带 suggestion 的 bayes_llm_guide 事件——LLM 可能未成功返回建议（检查 API key / 网络）")
        if has_backfill_note:
            failures.append(f"{f.name}: 事件 note 含 '[回填审计]'——疑似回填产物，请确认是否运行了正确的新 run-dir")
        if rec["search_method"] == "bayesian" and not has_region_apply:
            failures.append(f"{f.name}: bayesian 搜索但无 bayes_llm_region_apply 事件——prune/focus 未应用到搜索空间")

        per_file.append(rec)

    summary = {
        "n_files": len(files),
        "n_fail": len(failures),
        "all_injected": all(r["injected"] and r["enabled"] for r in per_file),
        "all_with_suggestion": all(r["has_suggestion"] for r in per_file),
        "none_backfilled": not any(r["has_backfill_note"] for r in per_file),
    }
    return failures, per_file, summary


def verify_artifacts(run_dir: str) -> tuple[list[str], list[str]]:
    """产出文件清单检查。返回 (missing, present)。"""
    base = Path(f"workspace/outputs/{run_dir}/literature_survey")
    expected = [
        "survey_report.md",
        "knowledge_graph.md",
        "paper_summaries.md",
        "gap_report.md",
        "discovery/hypotheses.json",
        "discovery/discovery_report.json",
    ]
    present = []
    missing = []
    for rel in expected:
        p = base / rel
        if p.exists() and p.stat().st_size > 0:
            present.append(rel)
        else:
            missing.append(rel)
    # 附加项
    extras = sorted(base.glob("discovery/search_h*.json"))
    if extras:
        present.append(f"discovery/search_h*.json × {len(extras)}")
    tr = Path(f"workspace/logs/{run_dir}")
    trajs = sorted(tr.glob("trajectory_*.json"))
    if trajs:
        present.append(f"logs/{run_dir}/{trajs[0].name}")
    mem = Path(f"workspace/memory/{run_dir}")
    mem_files = sorted(mem.glob("*.md"))
    if mem_files:
        present.append(f"memory/{run_dir}/ *.md × {len(mem_files)}")
    return missing, present


def compare_with_old(run_dir: str) -> str:
    """对比新 run-dir 与主案例（旧 survey）的 search_h*.json。"""
    old_dir = OLD_SURVEY_DIR / "discovery"
    new_dir = Path(f"workspace/outputs/{run_dir}/literature_survey/discovery")
    if not old_dir.exists():
        return "（未找到主案例旧产物 workspace/outputs/literature_survey/discovery，跳过对比）"

    lines = [
        "\n" + "=" * 64,
        "  新旧 search_h*.json 对比（问题 #12 验证）",
        "=" * 64,
        f"{'file':<12}{'best_score':<12}{'best_property':<18}{'injected':<10}{'n_events':<9}回填标记",
    ]
    old_files = sorted(old_dir.glob("search_h*.json"))
    new_files = sorted(new_dir.glob("search_h*.json")) if new_dir.exists() else []
    for f in old_files:
        d = _read_json(f)
        bp = d.get("best_params") or {}
        g = d.get("llm_guidance") or {}
        events = g.get("events") or []
        if not isinstance(events, list):
            events = []
        note_flag = "回填" if any("[回填审计]" in str(e.get("note", "")) for e in events if isinstance(e, dict)) else "?"
        pv = bp.get("property_value", "?")
        lines.append(
            f"{f.name:<12}{d.get('best_score', 0):<12.3f}{str(pv)[:16]:<18}"
            f"{str(g.get('injected')):<10}{g.get('n_events', 0):<9}{note_flag}"
        )
    for f in new_files:
        d = _read_json(f)
        bp = d.get("best_params") or {}
        g = d.get("llm_guidance") or {}
        events = g.get("events") or []
        if not isinstance(events, list):
            events = []
        note_flag = "回填" if any("[回填审计]" in str(e.get("note", "")) for e in events if isinstance(e, dict)) else "真实"
        pv = bp.get("property_value", "?")
        lines.append(
            f"{f.name:<12}{d.get('best_score', 0):<12.3f}{str(pv)[:16]:<18}"
            f"{str(g.get('injected')):<10}{g.get('n_events', 0):<9}{note_flag}"
        )
    lines.append(
        "\n判读：旧产物回填标记='回填'；新产物应='真实' 且 n_events 与迭代数匹配"
        "（N 次迭代 → initial 1 + floor((N-1)/5)+1 次引导事件）。"
    )
    return "\n".join(lines)


def verify(run_dir: str, compare: bool) -> int:
    """运行后校验；返回退出码（0=通过）。"""
    print("\n" + "=" * 64)
    print("  运行后校验")
    print("=" * 64)

    failures, per_file, summary = verify_llm_guidance(run_dir)
    missing, present = verify_artifacts(run_dir)

    print(f"\n  [llm_guidance 校验] {summary['n_files']} 个 search_h*.json："
          f"全部 injected={summary['all_injected']}, 全部含 suggestion={summary['all_with_suggestion']}, "
          f"无回填标记={summary['none_backfilled']}")
    for r in per_file:
        flag = "✓" if (r["injected"] and r["has_suggestion"] and not r["has_backfill_note"]) else "✗"
        print(f"    {flag} {r['file']}: enabled={r['enabled']} injected={r['injected']} "
              f"n_events={r['n_events']} method={r['search_method']} "
              f"region_apply={r['has_region_apply']}")

    print(f"\n  [产出清单]")
    for p in present:
        print(f"    ✓ {p}")
    for m in missing:
        print(f"    ✗ 缺失: {m}")

    if compare:
        print(compare_with_old(run_dir))

    # 汇总
    ok = (not failures) and (not missing)
    print("\n" + "=" * 64)
    if ok:
        print("  ✅ 运行后校验通过：LLM 引导真实生效，产物完整。")
    else:
        print(f"  ❌ 校验存在 {len(failures)} 项 llm_guidance 问题 + {len(missing)} 项缺失产物：")
        for f_ in failures:
            print(f"    - {f_}")
        for m in missing:
            print(f"    - 缺失: {m}")
    print("=" * 64)
    return 0 if ok else 1


# ═══════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="GOAI 路线 A v2 端到端重跑（问题 #12：LLM 引导真实生效验证）")
    parser.add_argument("--run-dir", default="mof_e2e_v3",
                        help="新运行目录名（默认 mof_e2e_v3；必须与主案例 survey 不同）")
    parser.add_argument("--topic", default="MOF materials for CO2 capture",
                        help="调研主题（默认主案例主题）")
    parser.add_argument("--budget", type=int, default=7200,
                        help="时间预算秒（默认 7200 = 2 小时）")
    parser.add_argument("--seed", type=int, default=42,
                        help="随机种子（默认 42）")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fresh", dest="fresh", action="store_true", default=True,
                       help="全新开始：忽略已有 checkpoint（默认）")
    group.add_argument("--resume", dest="resume", action="store_true", default=False,
                       help="断点续跑：从 checkpoint 恢复（同 run-dir，勿与 --fresh 同用）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只做前置检查并打印运行命令，不实际运行")
    parser.add_argument("--force", action="store_true",
                        help="跳过前置检查失败（不推荐）")
    parser.add_argument("--skip-verify", action="store_true",
                        help="跳过运行后校验")
    parser.add_argument("--no-compare", action="store_true",
                        help="不做新旧产物对比")
    args = parser.parse_args()
    if args.resume:
        args.fresh = False  # resume 与 fresh 互斥，续跑时取消 --fresh

    print(f"项目根: {ROOT}")
    print(f"run-dir: {args.run_dir} | topic: {args.topic} | budget: {args.budget}s | "
          f"seed: {args.seed} | 模式: {'fresh' if args.fresh else 'resume'}")

    if not preflight(args):
        return 2

    print("\n" + "=" * 64)
    print("  运行命令（预备）")
    print("=" * 64)
    cmd = [
        sys.executable, "main.py",
        "--topic", args.topic,
        "--run-dir", args.run_dir,
        "--budget", str(args.budget),
        "--seed", str(args.seed),
    ]
    if args.fresh:
        cmd.append("--fresh")
    print("  " + " ".join(cmd))
    if args.dry_run:
        print("\n[dry-run] 仅检查，不执行。退出。")
        return 0

    ret = run_survey(args)
    if ret != 0:
        print(f"\n⚠️ main.py 退出码 {ret}——Agent 可能异常/被中断。")
        print("  若为网络中断：修复后重跑同命令（不加 --fresh）即可断点续跑。")

    if args.skip_verify:
        print("\n[skip-verify] 跳过运行后校验。")
        return ret if ret != 0 else 0

    vr = verify(args.run_dir, compare=not args.no_compare)
    return vr if ret == 0 else ret


if __name__ == "__main__":
    sys.exit(main())
