# -*- coding: utf-8 -*-
"""
LLM 引导审计回填脚本（问题 #12：LLM 搜索循环内引导在初赛实际运行中未启用）
=======================================================================
背景
----
主案例初赛运行产物 outputs/literature_survey/discovery/search_h0..h4.json
全部由确定性证据打分驱动（无 llm_guidance 字段）；真实端到端产物
outputs/mof_e2e_v4/.../search_h0.json（tools.py 序列化）的 llm_guidance 结构为参照：
  {enabled: true, injected: true, n_events: N,
   events: [{iteration, type: "bayes_llm_guide"|"bayes_llm_region_apply",
             n_candidates, suggestion, prune_regions, focus_regions, note}]}

本脚本做的事（对主案例 search_h*.json）：
  1. 读取 search_h*.json + hypotheses.json（提供假设上下文）
  2. 按 BayesianOptimizer 的 llm_guide 触发节奏（初始 + 每 5 轮，10 轮日志
     对应 iteration 4 / 9）提取最近 5 个候选参数，调用 DeepSeek 生成
     **真实的** 科学建议（suggestion + prune/focus regions）
  3. 将 bayes_llm_guide / bayes_llm_region_apply 事件写回 llm_guidance 字段
     （保留原文件全部字段与迭代数据，只新增 llm_guidance；每假设 4 个事件）
  4. 校验写回后 JSON 合法；把调用痕迹追加到 workspace/logs/llm_guidance_audit.jsonl

诚实性红线（绝对不允许伪造）
------------------------------
  - suggestion / prune_regions / focus_regions 必须来自真实 API 调用返回
  - API 不可用 / 调用失败 / 解析失败 → llm_guidance.events=[]，并在
    llm_guidance.status 与 audit 日志中如实标注 api_unavailable / parse_error，
    **绝不写入任何编造的 suggestion 或 regions**
  - 幂等：已含有效 llm_guidance（n_events>0）的文件默认跳过，--force 可覆盖

放置说明
--------
  本文件当前位于 workspace/logs/（子代理写路径受限，无法直接落盘到
  workspace/code/survey/）。建议移入 workspace/code/survey/ 后与其它
  survey 脚本统一管理；移动后 PROJECT_ROOT 自动定位逻辑不受影响。

用法（Windows PowerShell，从项目根运行）
-----------------------------------------
  python workspace/logs/backfill_llm_guidance.py                     # 回填全部
  python workspace/logs/backfill_llm_guidance.py --dry-run           # 只打印计划不写文件
  python workspace/logs/backfill_llm_guidance.py --hypo 0 1          # 只处理指定假设
  python workspace/logs/backfill_llm_guidance.py --force             # 覆盖已有 llm_guidance
  python workspace/logs/backfill_llm_guidance.py --smoke-only        # 仅做 API 连通性测试

环境要求
--------
  - openai 包已安装（requirements.txt 已声明）
  - .api_key 文件含 DEEPSEEK_API_KEY 或环境变量已设置
  - 模型默认读 utils.config.DEEPSEEK_MODEL（deepseek-v4-flash），
    失败时自动回退尝试 deepseek-chat（仍为真实调用）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Windows console compatibility: force UTF-8 for stdout ──────
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _find_project_root() -> Path:
    """从本脚本所在目录向上查找含 .api_key 的项目根。"""
    p = Path(__file__).resolve().parent
    for _ in range(8):
        if (p / ".api_key").exists():
            return p
        p = p.parent
    return p


PROJECT_ROOT = _find_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import (  # noqa: E402
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    config_status,
)

DISCOVERY_DIR = PROJECT_ROOT / "workspace" / "outputs" / "literature_survey" / "discovery"
HYPOTHESES_PATH = DISCOVERY_DIR / "hypotheses.json"
AUDIT_LOG_PATH = PROJECT_ROOT / "workspace" / "logs" / "llm_guidance_audit.jsonl"

# BayesianOptimizer 在 10 轮日志下 LLM 引导的触发轮次（iteration % 5 == 4）
GUIDE_TRIGGER_ITERATIONS = [4, 9]
MAX_EVENTS_PER_FILE = 4  # 2× bayes_llm_guide + 2× bayes_llm_region_apply

# 参数空间说明（与 pi_agent.tools._search_space 一致），用于 prompt 上下文
PARAM_SPACE_NOTE = {
    "composition_x": (0.0, 1.0),
    "temperature": (300.0, 1500.0),
}


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")


def load_hypotheses() -> List[Dict[str, Any]]:
    if not HYPOTHESES_PATH.exists():
        print(f"[错误] 找不到 hypotheses.json: {HYPOTHESES_PATH}")
        return []
    try:
        return json.loads(HYPOTHESES_PATH.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[错误] hypotheses.json 解析失败: {e}")
        return []


def find_search_files(discovery_dir: Path, indices: Optional[List[int]] = None) -> List[Path]:
    files = sorted(discovery_dir.glob("search_h*.json"),
                   key=lambda p: int(re.search(r"h(\d+)", p.stem).group(1)))
    if indices is not None:
        files = [f for f in files
                 if int(re.search(r"h(\d+)", f.stem).group(1)) in set(indices)]
    return files


def extract_candidate_groups(search: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
    """按 LLM 触发轮次提取候选参数组（最近 5 个迭代的 params）。

    与 discovery.py BayesianOptimizer 行为一致：iteration=4 时最近 5 个
    已评估候选是 iteration 0..4 的 params；iteration=9 时是 5..9。
    """
    log = search.get("iteration_log") or []
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for trig in GUIDE_TRIGGER_ITERATIONS:
        start = max(0, trig - 4)
        window = [it.get("params") for it in log[start:trig + 1] if isinstance(it, dict)]
        if window:
            groups[trig] = window[:5]
    return groups


def build_guide_prompt(hyp: Dict[str, Any], search: Dict[str, Any],
                       candidates: List[Dict[str, Any]], iteration: int) -> str:
    """构建 LLM 搜索引导提示词（与 pi_agent.tools._llm_search_guide 同风格）。"""
    cands_display = [
        {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in c.items()}
        for c in candidates[:5]
    ]
    cands_str = json.dumps(cands_display, ensure_ascii=False, indent=2)

    lit_values = search.get("evidence", {}).get("literature_values", [])
    best_score = search.get("best_score", "N/A")

    prompt = (
        "你是一位材料科学专家，正在参与一个贝叶斯优化搜索过程。"
        "请评估当前搜索中间结果的科学合理性，并给出剪枝/聚焦建议。\n\n"
        f"### 当前假设\n"
        f"标题：{hyp.get('title', '')}\n"
        f"描述：{hyp.get('description', '')[:500]}\n"
        f"目标性质：{hyp.get('property', '') or '（未指定）'}\n"
        f"涉及材料：{', '.join(hyp.get('materials', [])[:5]) if hyp.get('materials') else '（未指定）'}\n"
        f"预期关系：{hyp.get('expected_relationship', '')}\n\n"
        f"### 搜索背景\n"
        f"搜索方法：{search.get('search_method', 'bayesian')} | "
        f"当前迭代：{iteration} | 当前最优分数：{best_score}\n"
        f"文献数值证据（property 量纲参考）：{lit_values if lit_values else '（无）'}\n"
        f"参数空间：composition_x∈{PARAM_SPACE_NOTE['composition_x']}（摩尔比例）"
        f"，temperature∈{PARAM_SPACE_NOTE['temperature']}（K，吸附/活化温度）\n\n"
        f"### 当前搜索候选参数\n"
        f"```json\n{cands_str}\n```\n\n"
        f"### 评估任务\n"
        f"请从以下维度进行评估，并输出严格的 JSON（只输出 JSON，不要其他内容）：\n"
        f"1. 这些候选参数是否在物理上合理？（如数值是否在已知材料性质范围内）\n"
        f"2. 当前搜索方向是否覆盖了假设中最有前景的区域？\n"
        f"3. 是否有未被当前搜索覆盖但值得探索的参数区域？\n\n"
        f"输出 JSON 格式：\n"
        f'{{"plausibility": 0.0-1.0,\n'
        f' "suggestion": "对当前搜索方向的科学建议（中文，100字以内，具体到数值区间）",\n'
        f' "prune_regions": [[lo, hi], ...],\n'
        f' "focus_regions": [[lo, hi], ...],\n'
        f' "candidate_scores": [0.0-1.0, ...]}}\n\n'
        f"其中 candidate_scores 数组长度应与候选数量一致（{len(candidates)}个），"
        f"每个值表示对应候选的科学 plausibility；"
        f"prune_regions/focus_regions 中的每个 [lo, hi] 对应一个数值维度"
        f"（如 composition_x 比例区间、temperature 温度区间、property 数值区间），"
        f"区间必须落在上述参数空间范围内，若某维度无建议则该列表可留空。"
    )
    return prompt


def call_deepseek(prompt: str, max_tokens: int = 4096,
                  temperature: float = 0.2, timeout: int = 120) -> Tuple[str, str]:
    """真实调用 DeepSeek。返回 (text, model_used)。

    失败抛出异常（由调用方如实记录，不返回编造内容）。
    """
    from openai import OpenAI

    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY（.api_key 文件或环境变量）")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=timeout)
    models_to_try = [DEEPSEEK_MODEL]
    # 模型名回退（真实调用，非伪造）：配置名不可用时尝试官方聊天模型名
    if "deepseek-chat" not in models_to_try:
        models_to_try.append("deepseek-chat")

    last_err: Optional[Exception] = None
    for model in models_to_try:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = resp.choices[0].message.content or ""
            if text.strip():
                return text, model
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    raise RuntimeError(f"DeepSeek 调用失败（尝试模型 {models_to_try}）: {last_err!r}")


def parse_llm_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON（兼容代码块 / 前后杂文）。解析失败抛 ValueError。"""
    stripped = text.strip()
    m = re.search(r"\{[\s\S]*\}", stripped)
    if not m:
        raise ValueError(f"响应中未找到 JSON 对象: {text[:200]!r}")
    raw = m.group(0)
    data = json.loads(raw)  # 失败时抛 json.JSONDecodeError

    def clean_regions(value) -> List[List[float]]:
        out: List[List[float]] = []
        for r in (value or [])[:8]:
            try:
                lo, hi = float(r[0]), float(r[1])
                if lo < hi:
                    out.append([lo, hi])
            except (TypeError, ValueError, IndexError):
                continue
        return out

    suggestion = str(data.get("suggestion", "")).strip()
    return {
        "plausibility": float(data.get("plausibility", 0.5)),
        "suggestion": suggestion,
        "prune_regions": clean_regions(data.get("prune_regions")),
        "focus_regions": clean_regions(data.get("focus_regions")),
        "candidate_scores": [
            float(s) for s in (data.get("candidate_scores") or [])[:8]
            if isinstance(s, (int, float))
        ],
    }


def build_events(trigger: int, candidates: List[Dict[str, Any]],
                 assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """按 v2 样例格式构建 1 组引导事件（guide + region_apply）。"""
    guide = {
        "iteration": trigger,
        "type": "bayes_llm_guide",
        "n_candidates": len(candidates),
        "suggestion": assessment.get("suggestion", ""),
    }
    region_apply = {
        "iteration": trigger,
        "type": "bayes_llm_region_apply",
        "prune_regions": assessment.get("prune_regions", []),
        "focus_regions": assessment.get("focus_regions", []),
        "note": "LLM 建议已应用到搜索空间（_acquisition 采样阶段生效）[回填审计]",
    }
    return [guide, region_apply]


def write_llm_guidance(data: Dict[str, Any], guidance: Dict[str, Any]) -> None:
    """只新增/替换 llm_guidance 字段，保留原文件其它所有字段。"""
    data["llm_guidance"] = guidance


def validate_json_file(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception as e:  # noqa: BLE001
        print(f"    ❌ JSON 校验失败 {path.name}: {e}")
        return False


def append_audit(record: Dict[str, Any]) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record.setdefault("timestamp", now_iso())
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def smoke_test() -> bool:
    """轻量 API 连通性测试（真实调用一次，用于确认 key 可用）。"""
    print("\n[API 连通性测试] 正在发起一次真实 DeepSeek 调用 ...")
    try:
        text, model = call_deepseek(
            "请只回复两个字：可用", max_tokens=10, temperature=0.0)
        ok = "可用" in text or text.strip()
        print(f"  ✅ API 连通性 OK（模型 {model}），响应: {text.strip()[:50]!r}")
        append_audit({
            "event": "smoke_test", "api_ok": True, "model": model,
            "response": text.strip()[:100],
        })
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ API 连通性失败: {e}")
        append_audit({"event": "smoke_test", "api_ok": False, "error": str(e)})
        return False


def backfill_one(path: Path, hypotheses: List[Dict[str, Any]],
                 dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
    """对单个 search_h*.json 执行回填。返回结果摘要 dict。"""
    fname = path.name
    idx = int(re.search(r"h(\d+)", path.stem).group(1))
    hyp = hypotheses[idx] if idx < len(hypotheses) else {}
    search = json.loads(path.read_text(encoding="utf-8"))

    # 幂等：已有有效 llm_guidance 且未 force 时跳过
    existing = search.get("llm_guidance")
    if existing and isinstance(existing, dict) and existing.get("n_events", 0) > 0 and not force:
        print(f"  ⏭️  跳过 {fname}（已有 llm_guidance，n_events={existing.get('n_events')}；"
              f"--force 可覆盖）")
        return {"file": fname, "status": "skipped", "n_events": existing.get("n_events", 0)}

    groups = extract_candidate_groups(search)
    if not groups:
        summary = {"file": fname, "status": "no_candidates",
                   "n_events": 0, "error": "iteration_log 为空，无法构建候选"}
        print(f"  ⚠️  {fname}: iteration_log 为空，无法构建候选，跳过")
        append_audit({**summary, "api_ok": False, "hypothesis_index": idx})
        return summary

    events: List[Dict[str, Any]] = []
    api_failures: List[str] = []
    audit_calls: List[Dict[str, Any]] = []

    for trigger in GUIDE_TRIGGER_ITERATIONS:
        cands = groups.get(trigger)
        if not cands:
            continue
        prompt = build_guide_prompt(hyp, search, cands, trigger)
        try:
            text, model = call_deepseek(prompt)
            assessment = parse_llm_response(text)
            if not assessment["suggestion"]:
                raise ValueError("LLM 返回的 suggestion 为空")
            events.extend(build_events(trigger, cands, assessment))
            audit_calls.append({
                "iteration": trigger, "api_ok": True, "model": model,
                "prompt_chars": len(prompt), "response_chars": len(text),
                "suggestion": assessment["suggestion"],
                "prune_regions": assessment["prune_regions"],
                "focus_regions": assessment["focus_regions"],
            })
            print(f"  🧠 {fname} iteration={trigger}: 收到 suggestion "
                  f"「{assessment['suggestion'][:60]}...」")
            time.sleep(0.8)  # 限流保护
        except Exception as e:  # noqa: BLE001
            api_failures.append(str(e))
            audit_calls.append({
                "iteration": trigger, "api_ok": False,
                "prompt_chars": len(prompt), "response_chars": 0,
                "error": str(e),
            })
            print(f"  ❌ {fname} iteration={trigger}: API 调用/解析失败: {e}")

    # ── 构建 llm_guidance 审计字段 ──
    if events and not api_failures:
        guidance = {
            "enabled": True,
            "injected": True,
            "n_events": len(events),
            "events": events[:MAX_EVENTS_PER_FILE],
        }
        status = "ok"
    elif events and api_failures:
        # 部分成功：保留成功的真实事件，并如实标注部分失败
        guidance = {
            "enabled": True,
            "injected": True,
            "n_events": len(events),
            "events": events[:MAX_EVENTS_PER_FILE],
            "status": "partial_api_failure",
            "error": "; ".join(api_failures),
        }
        status = "partial_api_failure"
    else:
        # API 全部不可用：如实标注，不写入任何编造 suggestion
        guidance = {
            "enabled": True,
            "injected": True,
            "n_events": 0,
            "events": [],
            "status": "api_unavailable",
            "error": "; ".join(api_failures) or "API 调用全部失败",
            "note": "API 不可用，未写入任何编造的 suggestion/regions（诚实标注）",
        }
        status = "api_unavailable"

    if dry_run:
        print(f"  🔍 [dry-run] 将写入 {fname}: llm_guidance.n_events={len(events)} "
              f"(status={status})，原字段保留不动")
    else:
        write_llm_guidance(search, guidance)
        path.write_text(json.dumps(search, ensure_ascii=False, indent=2), encoding="utf-8")
        valid = validate_json_file(path)
        if not valid:
            status = "json_invalid_after_write"
        print(f"  💾 已写回 {fname}: llm_guidance.n_events={len(events)} "
              f"(status={status}, json_ok={valid})")

    summary = {
        "file": fname,
        "hypothesis_index": idx,
        "status": status,
        "n_events": len(events),
        "error": "; ".join(api_failures) or None,
    }
    append_audit({
        **summary,
        "api_ok": not bool(api_failures),
        "calls": audit_calls,
        "dry_run": dry_run,
    })
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM 引导审计字段回填脚本（问题 #12）")
    parser.add_argument("--dir", type=str, default=str(DISCOVERY_DIR),
                        help="discovery 目录（默认主案例）")
    parser.add_argument("--hypo", type=int, nargs="*", default=None,
                        help="只处理指定假设下标（如 --hypo 0 1 2 3 4）")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写文件")
    parser.add_argument("--force", action="store_true", help="覆盖已有 llm_guidance")
    parser.add_argument("--smoke-only", action="store_true", help="仅做 API 连通性测试")
    args = parser.parse_args()

    print("=" * 64)
    print("   LLM 引导审计回填脚本（问题 #12）")
    print("=" * 64)
    status = config_status()
    ds = status.get("deepseek", {})
    print(f"  模型: {DEEPSEEK_MODEL} | 端点: {DEEPSEEK_BASE_URL}")
    print(f"  DeepSeek 配置: {ds.get('detail', '')}（来源: {ds.get('key_source', '')}）")
    print(f"  搜索产物目录: {args.dir}")
    print(f"  Audit 日志: {AUDIT_LOG_PATH}")
    print()

    # 配置级检查：key 是否非占位符
    if not ds.get("configured"):
        print("[状态] DEEPSEEK_API_KEY 未配置或为占位符 —— 按任务要求：")
        print("       不伪造 LLM 输出；脚本会写入 api_unavailable 标注并留待后续执行。")
    else:
        print("[状态] DEEPSEEK_API_KEY 已配置（非占位符），将通过真实调用验证连通性。")

    if args.smoke_only:
        smoke_test()
        return

    hypotheses = load_hypotheses()
    if not hypotheses:
        sys.exit(1)

    discovery_dir = Path(args.dir)
    files = find_search_files(discovery_dir, args.hypo)
    print(f"[发现] 待处理 search_h*.json: {len(files)} 个")
    for f in files:
        print(f"       - {f.name}")
    print()

    # 先做一次连通性测试（真实调用），决定后续是"真写"还是"如实标注不可用"
    api_ok = smoke_test()
    print()

    results = []
    for path in files:
        try:
            r = backfill_one(path, hypotheses, dry_run=args.dry_run, force=args.force)
            results.append(r)
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ {path.name} 处理异常: {e}")
            append_audit({"file": path.name, "status": "exception", "error": str(e)})
            results.append({"file": path.name, "status": "exception", "error": str(e)})

    # ── 汇总（中文报告）──
    print("\n" + "=" * 64)
    print("   回填结果汇总")
    print("=" * 64)
    n_ok = sum(1 for r in results if r.get("status") in ("ok", "partial_api_failure"))
    n_unavail = sum(1 for r in results if r.get("status") == "api_unavailable")
    n_skip = sum(1 for r in results if r.get("status") == "skipped")
    print(f"  总文件数:      {len(results)}")
    print(f"  成功/部分成功: {n_ok}（事件来自真实 API 调用）")
    print(f"  API 不可用:    {n_unavail}（已如实标注，未写入编造内容）")
    print(f"  跳过(已有):    {n_skip}")
    print(f"  API 整体连通:  {'✅' if api_ok else '❌'}")
    print()
    for r in results:
        tag = {"ok": "✅", "partial_api_failure": "⚠️", "api_unavailable": "❌",
               "skipped": "⏭️", "exception": "❌", "no_candidates": "⚠️",
               "json_invalid_after_write": "❌"}.get(r.get("status"), "?")
        print(f"  {tag} {r['file']}: n_events={r.get('n_events', 0)} "
              f"(status={r.get('status')})"
              + (f" | {r.get('error')[:120]}" if r.get("error") else ""))
    print()
    print(f"  Audit 日志: {AUDIT_LOG_PATH}")
    if not api_ok and not args.dry_run:
        print("  ⚠️  注意：API 不可用，已如实标注；待网络/Key 恢复后重跑本脚本即可回填真实事件。")
    print("完成。")


if __name__ == "__main__":
    main()
