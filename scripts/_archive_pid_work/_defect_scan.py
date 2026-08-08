# -*- coding: utf-8 -*-
"""按 A-E 缺陷清单逐项扫描仓库实际状态（只读）"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = "."


def rd(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def exists(p):
    return os.path.exists(p)


def say(cat, item, status, evidence=""):
    print(f"[{cat}] {item}: {status}" + (f"  | {evidence}" if evidence else ""))


# ================= A 类 =================
readme = rd("README.md")
cj = rd("初赛提交材料.md")
sr = rd(r"workspace/outputs/literature_survey/survey_report.md")
arch = rd("ARCHITECTURE.md")
compl = rd("COMPLIANCE.md")
ppd = rd("problem_definition.md")
bzd = rd("项目不足分析.md")

print("========== A 类：数字/引用不一致 ==========")
# A1 参照结果集
br = rd(r"workspace/outputs/literature_survey/discovery/baseline_random.json")
a1_readme = "3:2" in readme or "-0.050" in readme
a1_cj = "3:2" in cj or "-0.050" in cj
a1_sr = "3:2" in sr or "-0.050" in sr
a1_new = "5:0" in br or "+0.0145" in br or "0.0145" in br
say("A1", "参照结果集数字过时", "存在" if (a1_readme or a1_cj or a1_sr) else "不存在",
    f"README含旧值={a1_readme}, 初赛材料={a1_cj}, survey_report={a1_sr}; baseline_random.json含v2值={a1_new}")

# A2 baseline_v2_full / 4:1
a2_cj = "4:1" in cj or "baseline_v2_full" in cj
a2_f = exists(r"workspace/outputs/literature_survey/discovery/baseline_v2_full.json")
a2_smoke = exists(r"workspace/outputs/literature_survey/discovery/baseline_smoke_all.json")
say("A2", "引用不存在的 baseline_v2_full.json / 4:1", "存在" if (a2_cj and not a2_f) else "不存在/已修复",
    f"初赛材料含4:1或v2_full={a2_cj}; baseline_v2_full.json存在={a2_f}; baseline_smoke_all.json存在={a2_smoke}")

# A3 文献数口径
pid = json.load(open(r"workspace/outputs/literature_survey/papers_pid_index.json", encoding="utf-8"))
ps = rd(r"workspace/outputs/literature_survey/paper_summaries.md")
ct = rd("CROSS_THEME_REPORT.md")
a3 = {"README546": "546" in readme, "初赛材料546": "546" in cj, "方案1.3_546": "546" in rd("材料科学文献调研Agent_算法赛初赛方案.docx") if exists("材料科学文献调研Agent_算法赛初赛方案.docx") else "n/a",
      "CROSS376": "376" in ct, "pid_index": len(pid), "paper_summaries_46": "Total papers: 46" in ps}
say("A3", "文献数口径并存（546/376/180/46）", "存在（口径未统一）",
    f"{a3}")

# A4 docs/problem_definition.md
a4 = "docs/problem_definition.md" in readme
say("A4", "README 引用 docs/problem_definition.md", "存在（路径失效）" if a4 and not exists("docs/problem_definition.md") else "不存在",
    f"README含该路径={a4}; docs/ 存在={exists('docs')}; 根目录problem_definition.md存在={exists('problem_definition.md')}")

# A5 合规性检查报告 2.0.md / baseline_smoke_all.json 引用
a5a = "合规性检查报告 2.0" in cj
a5b = "baseline_smoke_all.json" in cj
a5f1 = exists("合规性检查报告 2.0.md")
say("A5", "初赛材料引用不存在文件", "存在" if ((a5a and not a5f1) or a5b) else "不存在",
    f"合规性检查报告2.0引用={a5a}, 文件存在={a5f1}; baseline_smoke_all引用={a5b}")

# A6 README 附录C discovery_report.md
a6 = "discovery_report.md" in readme
a6f = exists(r"workspace/outputs/literature_survey/discovery/discovery_report.md")
say("A6", "README 附录C 引 discovery_report.md（实际仅 .json）", "存在" if (a6 and not a6f) else "不存在",
    f"README含={a6}; discovery_report.md存在={a6f}")

# A7 CLI --output
a7 = "--output" in cj
main_py = rd("main.py")
a7r = "--run-dir" in main_py
a7o = "--output" in main_py
say("A7", "初赛材料写 --output（main.py 实为 --run-dir）", "存在" if (a7 and "--output" in cj and "--output" not in main_py) else "不存在",
    f"初赛材料含--output={a7}; main.py含--run-dir={a7r}, 含--output={a7o}")

# A8 工具数 19 vs 23
tools_py = rd("pi_agent/tools.py")
reg = re.findall(r"(?:register|register_tool|TOOL|tools)\s*[=(]", tools_py)
say("A8", "19 个工具 vs 实际注册数", "需人工确认（工具注册方式未唯一匹配）",
    f"README含19个={('19 个工具' in readme or '19个工具' in readme)}; tools.py行数={len(tools_py.splitlines())}")

# A9 markitdown_utils
docs_mu = {f: rd(f).count("markitdown_utils") for f in ["README.md", "ARCHITECTURE.md", "COMPLIANCE.md", "初赛提交材料.md", "problem_definition.md", "项目不足分析.md"]}
req = rd("requirements.txt")
say("A9", "markitdown_utils 命名过时", "存在" if sum(docs_mu.values()) > 0 else "不存在",
    f"各文档出现次数={docs_mu}; requirements含markitdown==0.1.7={('markitdown==0.1.7' in req)}")

# A10 COMPLIANCE 依赖表漏 markitdown
sec6 = compl[compl.find("六、"):] if "六、" in compl else compl
say("A10", "COMPLIANCE 依赖表漏 markitdown", "存在（漏列）" if ("markitdown" not in sec6 and "markitdown" not in compl) else "不存在/已含",
    f"COMPLIANCE全文含markitdown={('markitdown' in compl)}")

# A11 gap_report p# 断链
g = rd(r"workspace/outputs/literature_survey/gap_report.md")
pids = sorted({int(x) for x in re.findall(r"\bp(\d+)\b", g)})
pid_idx_md = glob.glob("**/pid_evidence_index.md", recursive=True)
say("A11", "gap_report p# 断链", "存在（需人工补链）",
    f"gap_report 去重p#数={len(pids)}; pid_evidence_index.md={pid_idx_md if pid_idx_md else '未找到'}")

# ================= B 类 =================
print()
print("========== B 类：红线风险 ==========")
ra = glob.glob(r"workspace/outputs/mof_rerun/**/reference_audit.md", recursive=True)
b1 = ""
if ra:
    b1 = rd(ra[0])
say("B1", "mof_rerun reference_audit 高风险引用", "存在" if ("高风险" in b1 or "不可追溯" in b1) else "不存在",
    f"文件={ra}; 含高风险={('高风险' in b1)}, 含不可追溯={('不可追溯' in b1)}")

rep = rd("REPRODUCIBILITY.md")
b2_txt = "疑似构造" in rep or "来源未核实" in rep
mof_rerun_sh = glob.glob(r"workspace/outputs/mof_rerun/**/search_h*.json", recursive=True)
say("B2", "mof_rerun 疑似构造产物残留", "存在" if b2_txt else "不存在",
    f"REPRODUCIBILITY自认={b2_txt}; mof_rerun search_h*.json数={len(mof_rerun_sh)}")

b3 = exists(".api_key")
gi = rd(".gitignore")
say("B3", ".api_key 明文在根目录", "存在（已gitignore，需轮换+确认不打进包）" if b3 else "不存在",
    f".api_key存在={b3}; .gitignore含.api_key={('.api_key' in gi)}")

# ================= C 类 =================
print()
print("========== C 类：工程化/可复现性 ==========")
ci = rd(".github/workflows/ci.yml")
say("C1", "CI Python 3.10 与 pandas/sklearn 冲突", "存在" if ("3.10" in ci and ("pandas==3.0.3" in rd("requirements.txt") or "scikit-learn==1.9.0" in rd("requirements.txt"))) else "需确认",
    f"ci含3.10={('3.10' in ci)}; requirements pandas3.0.3={('pandas==3.0.3' in req)}, sklearn1.9.0={('scikit-learn==1.9.0' in req)}")

docx_scripts = [f for f in glob.glob("scripts/*.py") if "import docx" in rd(f)]
say("C2", "python-docx 未列入依赖", "存在" if docx_scripts and "python-docx" not in req else "不存在",
    f"import docx 的脚本={len(docx_scripts)}; requirements含python-docx={('python-docx' in req)}")

afac = []
for f in glob.glob("pi_agent/*.py"):
    if "afac2026" in rd(f):
        afac.append(f)
say("C3", "pi_agent 硬编码其他项目名 afac2026", "存在" if afac else "不存在", f"{afac}")

vb = exists("vendor/bash")
vgi = "vendor" in gi
di = rd(".dockerignore")
say("C4", "vendor/bash 被排除但为运行时依赖", "需确认",
    f"vendor/bash存在={vb}; .gitignore含vendor={vgi}; .dockerignore含vendor={('vendor' in di)}")

zips = glob.glob("*.zip")
di_entries = [l for l in di.splitlines() if l.strip() and not l.strip().startswith("#")]
say("C5", ".dockerignore 遗漏大文件 / .gitignore 未排 aaa", "存在" if (zips or exists("nul") or "aaa" not in gi) else "不存在",
    f"根目录zip={zips}; nul存在={exists('nul')}; .gitignore含aaa={('aaa' in gi)}; dockerignore条目数={len(di_entries)}")

say("C6", "nul 垃圾文件", "存在" if exists("nul") else "不存在", f"大小={os.path.getsize('nul') if exists('nul') else 0}B")

stale = {}
for f in ["scripts/meta_analysis.py", "scripts/run_e2e_rerun.py", "scripts/backfill_llm_guidance.py"]:
    t = rd(f)
    if "workspace/code/survey" in t:
        stale[f] = t.count("workspace/code/survey")
say("C7", "脚本内失效路径 workspace/code/survey", "存在" if stale else "不存在", f"{stale}")

debug_scripts = sorted(glob.glob("scripts/_*.py"))
say("C8", "调试脚本残留（_前缀）", f"存在 {len(debug_scripts)} 个", f"{debug_scripts}")

cb = glob.glob("consistency_bak/**/*.json", recursive=True) + glob.glob("consistency_bak/*.json")
say("C9", "consistency_bak 备份残留", f"存在（{len(cb)} 个 json）" if cb else "不存在", f"目录存在={exists('consistency_bak')}")

say("C10", "CI 注释测试数 115 vs 实际", "需确认（本地因 scipy DLL 无法收集）",
    f"ci含115={('115' in ci)}, 含122={('122' in ci)}")

# ================= D 类 =================
print()
print("========== D 类：产出完整性与文档过时 ==========")
def theme_files(theme, pat):
    return glob.glob(rf"workspace/outputs/{theme}/**/{pat}", recursive=True)

d1 = {
    "g3test_dr": len(theme_files("g3test", "discovery_report*")),
    "smoke_test_dr": len(theme_files("smoke_test", "discovery_report*")),
    "validation_dr": len(theme_files("validation", "discovery_report*")),
    "cathode_dr": len(theme_files("cathode", "discovery_report*")),
    "thermo_h3": len(theme_files("thermoelectric", "search_h3*")),
    "thermo_h4": len(theme_files("thermoelectric", "search_h4*")),
    "rerun_v2_dr": len(theme_files("mof_rerun_v2", "discovery_report.json")),
}
say("D1", "各主题 discovery 产物不完整", "存在" if (d1["g3test_dr"] == 0 or d1["smoke_test_dr"] == 0 or d1["validation_dr"] == 0 or d1["cathode_dr"] == 0 or d1["thermo_h3"] == 0 or d1["thermo_h4"] == 0 or d1["rerun_v2_dr"] == 0) else "不存在", f"{d1}")

at = rd(r"workspace/outputs/literature_survey/audit_trail.md")
kg = rd(r"workspace/outputs/literature_survey/knowledge_graph.md")
say("D2", "audit_trail 写 Gap 1-7 / knowledge_graph 元数据过时", "存在" if ("Gap 1-7" in at or "Gap 1–7" in at) else "不存在",
    f"audit含Gap1-7={('Gap 1-7' in at or 'Gap 1–7' in at)}; kg头部含2026-08-01={('2026-08-01' in kg[:500])}")

d3_contested = "contested" in ct.lower()
rr_audit = glob.glob(r"workspace/outputs/mof_rerun/**/reference_audit.md", recursive=True)
d3_mr = "contested" in rd(rr_audit[0]).lower() if rr_audit else "n/a"
cathode_hyp = len(glob.glob(r"workspace/outputs/cathode/**/hypotheses.json", recursive=True))
say("D3", "CROSS_THEME_REPORT contested 状态与产物不符", "需人工核对",
    f"CROSS含contested={d3_contested}; mof_rerun reference_audit含contested={d3_mr}; cathode hypotheses.json数={cathode_hyp}")

e2e = rd("E2E_RERUN_GUIDE.md")
say("D4", "E2E_RERUN_GUIDE 默认 v3（产物在 v4）", "存在" if ("v3" in e2e and "v4" not in e2e[:2000]) else "需确认",
    f"guide含v3={('v3' in e2e)}, 前2000字符含v4={('v4' in e2e[:2000])}")

logs = glob.glob("**/*.log", recursive=True)
say("D5", "REPRODUCIBILITY 声称 *.log 不存在", "存在" if (".log" in rep and not logs) else "不存在",
    f"全仓log文件数={len(logs)}; REPRODUCIBILITY含.log={('.log' in rep)}")

# ================= E 类 =================
print()
print("========== E 类：提示 ==========")
aaa = os.listdir("aaa") if exists("aaa") else []
zips2 = glob.glob("*.zip") + glob.glob("aaa/*.zip")
say("E1", "两套方案并存（根目录 vs aaa/zip）", "存在" if (aaa or zips2) else "不存在",
    f"aaa/文件数={len(aaa)}; zip={zips2}")

say("E2", "无 .git / README 无仓库 URL", "需确认",
    f".git存在={exists('.git')}; README含github={('github.com' in readme.lower())}")

docx_team = "【待补充" in rd("材料科学文献调研Agent_算法赛初赛方案.docx") if exists("材料科学文献调研Agent_算法赛初赛方案.docx") else "n/a"
say("E3", "团队介绍【待补充】", f"存在（方案docx含待补充={docx_team}）")

say("E4", "miner_test_results.json 残留 / g3test MEMORY 40B / 缺 sciverse 日志", "存在",
    f"miner_test_results.json={len(glob.glob('**/miner_test_results.json', recursive=True))}; g3test MEMORY大小={os.path.getsize('workspace/memory/g3test/MEMORY.md') if exists('workspace/memory/g3test/MEMORY.md') else 0}B")
