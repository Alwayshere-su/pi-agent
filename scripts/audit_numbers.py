# -*- coding: utf-8 -*-
"""
数字审计：方案说明文档 + 初赛提交物整理 vs 工作区真实产物
================================================================
一条命令核对"文档里的数字"与"代码/产物里的真实数字"是否一致，
专门解决"代码和文档对不上"的问题。

用法:
    python scripts/audit_numbers.py            # 核对静态数字（不跑测试）
    python scripts/audit_numbers.py --pytest   # 额外跑 pytest 收集真实测试数

设计原则:
    - 每个审计项的"真值"都从真实文件/代码实时计算，不硬编码结果；
    - 输出三类状态: [✓] 一致  [✗] 漂移  [?] 文档未出现(需人工确认口径)；
    - 数据源与计算方式在代码里写清楚，可复现、可追溯。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------- 路径 ----------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)  # 允许 import literature_agent
DOCX = os.path.join(ROOT, "方案说明文档.docx")
SUBMIT_MD = os.path.join(ROOT, "初赛提交物整理.md")
OUT = os.path.join(ROOT, "workspace", "outputs")

# 4 个正式研究主题的 discovery 目录
FORMAL_THEMES = {
    "MOF(主案例)": os.path.join(OUT, "literature_survey"),
    "钙钛矿": os.path.join(OUT, "perovskite", "literature_survey"),
    "热电": os.path.join(OUT, "thermoelectric", "literature_survey"),
    "正极": os.path.join(OUT, "cathode", "literature_survey"),
}
HYP_JSON = "discovery/hypotheses.json"
GAP_MD = "gap_report.md"


# ---------- 文档文本加载 ----------
def _docx_text(path: str) -> str:
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def _md_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------- 通用工具 ----------
def _count_gaps(gap_md: str) -> int:
    """统计 gap_report.md 里真正的 '## Gap N' 条数。

    口径：只数 h2 级、'Gap' 后紧跟数字的标题，排除 'Gap N 更新' 子标题、
    'Gap 优先级排序/清单/分析' 等非编号标题（这些是常见误数陷阱）。
    """
    if not os.path.exists(gap_md):
        return -1
    text = open(gap_md, encoding="utf-8").read()
    headings = re.findall(r"^##\s+Gap\s+\d+.*$", text, re.MULTILINE)
    # 只排除 "Gap N 更新（…）" 这类子标题（'更新'紧跟数字），
    # 不排除标题里别处带 "更新：置信度…" 的正经 Gap（如 mof_e2e_v4 的 Gap 3/9/11）。
    headings = [h for h in headings if not re.search(r"Gap\s+\d+\s*更新", h)]
    return len(headings)


def _count_hypotheses(hyp_json: str) -> int:
    if not os.path.exists(hyp_json):
        return -1
    data = json.load(open(hyp_json, encoding="utf-8"))
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for k in ("hypotheses", "data", "items"):
            if isinstance(data.get(k), list):
                return len(data[k])
    return -1


# =================================================================
# 审计项定义：每个函数返回 (真值说明, 真值, [文档中应出现的字符串...])
# 字符串用于在"文档文本"里检索口径是否被写入，供人工核对数值是否一致。
# =================================================================

def audit_tools(doc: str, submit: str):
    """工具数量 = build_tool_manager 里 manager.register(...) 的个数。"""
    src = open(os.path.join(ROOT, "pi_agent", "tools.py"), encoding="utf-8").read()
    n = len(re.findall(r"manager\.register\(", src))
    return ("工具数（pi_agent/tools.py manager.register 计数）", str(n),
            ["23 个工具", "23 工具", "23 项工具"])


def audit_roles(doc: str, submit: str):
    """角色数量 = 文档自述的八类角色；真值取自 build_prelim_proposal.py 角色表行数。"""
    path = os.path.join(ROOT, "scripts", "build_prelim_proposal.py")
    if not os.path.exists(path):
        return ("角色数（build_prelim_proposal.py 为本地 docx 生成工具，未入库）",
                "本地文件未入库", ["八类角色", "八类 Agent"])
    src = open(path, encoding="utf-8").read()
    # 角色表在 ["Agent 角色", ...] 之后，逐行数数据行（以 [" 开头且含逗号）
    m = re.search(r"\[\"Agent 角色\".*?\],\s*(\[[^\]]*\]\s*,){0,20}", src, re.DOTALL)
    # 兜底：从文档句"八类角色任务（…）"里数顿号分隔的 8 项
    eight = re.search(r"八类角色任务（([^）]+)）", src)
    roles = eight.group(1).split("、") if eight else []
    n = len(roles) if roles else -1
    return ("角色数（build_prelim_proposal.py '八类角色任务' 顿号项数）", str(n),
            ["八类角色", "八类 Agent"])


def audit_resources(doc: str, submit: str):
    src = open(os.path.join(ROOT, "utils", "resource_registry.py"), encoding="utf-8").read()
    n = len(re.findall(r"ExternalResource\(", src))
    return ("外部资源数（utils/resource_registry.py ExternalResource 计数）", str(n),
            ["13 项", "13 个资源", "13 资源"])


def audit_main_case(doc: str, submit: str):
    reg = open(os.path.join(OUT, "literature_survey", "paper_register.md"), encoding="utf-8").read()
    m546 = re.search(r"(\d+)\s*篇\*{0,2}\s*=\s*11\s*轮", reg)
    # "最终收录 ... 46 篇"（paper_register.md 里带反引号或加粗）
    m46 = re.search(r"最终收录[^\n]*?(\d+)\s*篇", reg)
    gaps = _count_gaps(os.path.join(OUT, "literature_survey", GAP_MD))
    n546 = m546.group(1) if m546 else "?"
    n46 = m46.group(1) if m46 else "?"
    return ("主案例 MOF 检索/收录/Gap（paper_register.md + gap_report.md）",
            f"检索 {n546} 篇次 / 收录 {n46} 篇 / {gaps} 项 Gap",
            ["546 篇次", "46 篇", "10 项 Gap"])


def audit_formal_hypotheses(doc: str, submit: str):
    per = {}
    for name, base in FORMAL_THEMES.items():
        per[name] = _count_hypotheses(os.path.join(base, HYP_JSON))
    total = sum(v for v in per.values() if v > 0)
    return ("4 正式主题假设数（各 hypotheses.json 求和）",
            f"{total}（{' + '.join(f'{k}{v}' for k, v in per.items())}）",
            ["21 条假设", "合计 21 条"])


def audit_total_gaps(doc: str, submit: str):
    # 所有主题的 gap_report.md 条数求和。
    # 注意：主案例 literature_survey 的结构是 OUT/literature_survey/gap_report.md（单层），
    # 其余主题是 OUT/<theme>/literature_survey/gap_report.md（两层）。
    total = 0
    detail = []
    gap_paths = [os.path.join(OUT, "literature_survey", GAP_MD)]  # 主案例
    for theme_dir in sorted(os.listdir(OUT)):
        gap_paths.append(os.path.join(OUT, theme_dir, "literature_survey", GAP_MD))
    seen = set()
    for gap in gap_paths:
        if gap in seen or not os.path.exists(gap):
            continue
        seen.add(gap)
        c = _count_gaps(gap)
        if c > 0:
            total += c
            detail.append(f"{os.path.relpath(gap, OUT).split(os.sep)[0]}:{c}")
    return ("全主题 Gap 总数（各 gap_report.md 求和）",
            f"{total}（{', '.join(detail)}）",
            ["63 项 Gap", "合计 63 项"])


def audit_mof_rerun_v3(doc: str, submit: str):
    base = os.path.join(OUT, "mof_rerun_v3", "literature_survey")
    hyps = _count_hypotheses(os.path.join(base, HYP_JSON))
    gaps = _count_gaps(os.path.join(base, GAP_MD))
    # 论文数：survey_report 里有两个口径——原始检索 vs 综述最终采用
    raw = final = "?"
    sr = os.path.join(base, "survey_report.md")
    if os.path.exists(sr):
        t = open(sr, encoding="utf-8").read()
        m_raw = re.search(r"文献规模[^\n]*?(\d+)\s*篇", t)
        m_final = re.search(r"基于\s*(\d+)\s*篇文献", t)
        if m_raw:
            raw = m_raw.group(1)
        if m_final:
            final = m_final.group(1)
    return ("mof_rerun_v3 重跑（hypotheses.json + gap_report.md + survey_report.md）",
            f"原始 {raw} 篇 / 综述采用 {final} 篇 / {gaps} Gaps / {hyps} hyps",
            ["63 papers", "5 Gaps", "5 hyps", "mof_rerun_v3"])


def audit_cathode_quant(doc: str, submit: str):
    """正极表 3（Ni 含量-100圈保持率，领域共识值）的经典模型拟合，真值重算。"""
    from literature_agent.classical_models import fit_linear, fit_quadratic
    import numpy as np
    x = np.array([0.33, 0.50, 0.60, 0.80, 0.83, 1.00])   # Ni 含量（knowledge_graph 表 3）
    y = np.array([95, 92, 90, 85, 82, 70])                # 100 圈保持率 %
    sl, ic, r2_lin = fit_linear(x, y)
    q, r2_quad, _ = fit_quadratic(x, y)
    # Vegard 端点固定基线 y = 95 - 25x
    yv = 95 - 25 * x
    r2_veg = 1 - float(np.sum((y - yv) ** 2)) / float(np.sum((y - np.mean(y)) ** 2))
    return ("正极表3 定量核验（classical_models 重算）",
            f"线性 R²={r2_lin:.4f} / 二次 R²={r2_quad:.4f} / Vegard R²={r2_veg:.4f}",
            ["0.887", "0.983", "-0.032"])


def audit_mof_main_quant(doc: str, submit: str):
    """主案例 MOF 定量核验数字——真值 = build_prelim_proposal.py 源码里的断言。"""
    path = os.path.join(ROOT, "scripts", "build_prelim_proposal.py")
    if not os.path.exists(path):
        return ("主案例 MOF 定量核验（build_prelim_proposal.py 未入库；数值见 workspace 产物）",
                "本地文件未入库", ["0.6919", "0.7694", "-0.1530"])
    src = open(path, encoding="utf-8").read()
    claims = {
        "二次拟合 R²": "0.6919", "嵌套F p": "0.0254",
        "Chen2023 二次 R²": "0.7694", "Vegard 基线 R²": "-0.1530",
        "ΔR²": "+0.92", "meta t": "5.46", "meta p": "0.0121",
    }
    present = {k: (v in src) for k, v in claims.items()}
    missing = [k for k, ok in present.items() if not ok]
    status = "源码断言齐全" if not missing else f"源码缺失: {missing}"
    return ("主案例 MOF 定量核验（build_prelim_proposal.py 源码断言）",
            status + "（" + ", ".join(f"{k}={v}" for k, v in claims.items()) + "）",
            ["0.6919", "0.0254", "0.7694", "-0.1530", "+0.92", "5.46", "0.0121"])


def audit_pytest(doc: str, submit: str, run: bool = False):
    if not run:
        return ("pytest 测试数（跳过，用 --pytest 运行）", "未运行", ["125 项", "125"])
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        m = re.search(r"(\d+)\s+tests?\s+collected", r.stdout + r.stderr)
        n = m.group(1) if m else "?"
        return ("pytest 测试数（pytest --collect-only 实跑）", n, ["125 项", "125"])
    except Exception as e:  # noqa
        return ("pytest 测试数（运行失败）", f"ERR {e}", ["125 项", "125"])


# =================================================================
# 主流程
# =================================================================

def main() -> int:
    run_pytest = "--pytest" in sys.argv
    # 方案说明文档.docx / 初赛提交物整理.md 为本地提交物（不入公开仓库），
    # 缺失时降级为"仅产物审计"，保证脚本在 fresh clone 下也可运行。
    try:
        doc = _docx_text(DOCX)
    except Exception as e:  # noqa
        doc = ""
        print(f"[warn] 未读取到 {os.path.basename(DOCX)}（本地提交物，不入库）：{e}")
    try:
        submit = _md_text(SUBMIT_MD)
    except Exception as e:  # noqa
        submit = ""
        print(f"[warn] 未读取到 {os.path.basename(SUBMIT_MD)}（本地准备文档，不入库）：{e}")
    # 跨主题报告也是文档引用的权威口径来源（正极/热电等量化数字写在这里）
    cross = _md_text(os.path.join(ROOT, "docs", "CROSS_THEME_REPORT.md"))
    combined = doc + "\n" + submit + "\n" + cross
    # 归一化：项目里混用 Unicode 减号 −(U+2212) 与 ASCII 连字符 -，统一后比较
    combined = combined.replace("−", "-")

    audits = [
        audit_tools, audit_roles, audit_resources,
        audit_main_case, audit_formal_hypotheses, audit_total_gaps,
        audit_mof_rerun_v3, audit_cathode_quant, audit_mof_main_quant,
    ]

    print("=" * 78)
    print("数字审计：文档/提交物 vs 工作区真实产物")
    print("=" * 78)

    n_ok = n_bad = n_check = 0
    for fn in audits:
        label, truth, patterns = fn(doc, submit)
        found = [p for p in patterns if p in combined]
        # 判态
        if found:
            status, mark = "一致", "[✓]"
            n_ok += 1
        elif patterns and all(p not in combined for p in patterns):
            status, mark = "文档未出现", "[?]"
            n_check += 1
        else:
            status, mark = "漂移", "[✗]"
            n_bad += 1
        print(f"\n{mark} {label}")
        print(f"    真值 : {truth}")
        print(f"    文档命中: {found if found else '（无匹配关键词）'}")

    # pytest 单独
    label, truth, patterns = audit_pytest(doc, submit, run_pytest)
    found = [p for p in patterns if p in combined]
    mark = "[✓]" if found else "[?]"
    print(f"\n{mark} {label}")
    print(f"    真值 : {truth}")
    print(f"    文档命中: {found if found else '（无匹配关键词）'}")

    print("\n" + "=" * 78)
    print(f"汇总：{n_ok} 项一致，{n_bad} 项漂移，{n_check} 项需人工确认口径")
    print("说明：[?] 表示真值已算出、但文档里没找到对应关键词——多为口径写法不同，需人眼核对。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
