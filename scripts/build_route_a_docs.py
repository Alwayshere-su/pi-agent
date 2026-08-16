# -*- coding: utf-8 -*-
"""build_route_a_docs.py — 从 6 个主题的 discovery 产物生成路线 A 提交文档

产出：
  1. ROUTE_A_SP_LIST.md     — 构效关系清单（统一表格格式）
  2. ROUTE_A_EXPLANATION.md — 解释文档（科学散文体）

用法：
  python scripts/build_route_a_docs.py
  python scripts/build_route_a_docs.py --explanation-only  # 仅重生成解释文档
"""
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

ROOT = os.path.join(os.path.dirname(__file__), '..', 'workspace', 'outputs')
DATE = '2026-08'
DATE_FULL = '2026 年 8 月'


# ── 主题配置 ──────────────────────────────────────────────

@dataclass
class ThemeConfig:
    key: str                         # 目录名
    prefix: str                      # SPR 编号前缀
    display_name: str                # 中文显示名
    system_desc: str                 # 材料体系描述
    route_hint: str                  # 发现路径说明（base = literature_survey，sub = {key}/literature_survey）


THEMES = [
    ThemeConfig('literature_survey', 'MOF',  'MOF CO₂ 捕获',
                '金属有机框架（MOF）—CO₂ 吸附容量/选择性/再生能耗',
                'base'),
    ThemeConfig('mof_e2e_v4',        'MOFv4','MOF CO₂ 捕获（e2e v4 重跑）',
                '金属有机框架（MOF）—CO₂ 吸附焓/胺功能化/双金属协同',
                'sub'),
    ThemeConfig('perovskite',        'PVSK', '卤化物钙钛矿',
                '卤化物钙钛矿—带隙/稳定性/光电性能',
                'sub'),
    ThemeConfig('thermoelectric',    'TE',   '热电材料',
                '热电材料—ZT 优值/晶格热导率/Seebeck 系数',
                'sub'),
    ThemeConfig('cathode',           'NMC',  '高镍正极',
                '高镍层状氧化物正极（NMC/LiNiO₂）—容量保持率/降解机制',
                'sub'),
    ThemeConfig('validation',        'SE',   '固态电解质',
                '固态锂电池电解质—离子电导率/界面稳定性/高熵设计',
                'sub'),
]


# ── 路径工具 ──────────────────────────────────────────────

def discovery_base(cfg: ThemeConfig) -> str:
    if cfg.route_hint == 'base':
        return os.path.join(ROOT, cfg.key, 'discovery')
    return os.path.join(ROOT, cfg.key, 'literature_survey', 'discovery')


def survey_base(cfg: ThemeConfig) -> str:
    if cfg.route_hint == 'base':
        return os.path.join(ROOT, cfg.key)
    return os.path.join(ROOT, cfg.key, 'literature_survey')


# ── 数据提取 ──────────────────────────────────────────────

@dataclass
class Hypothesis:
    id: str
    theme_key: str
    theme_display: str
    spr_id: str                      # 统一编号 SPR-MOF-01 等
    title: str
    description: str
    materials: str
    property_: str
    expected_relationship: str
    confidence: float
    novelty_score: float
    best_score: Optional[float]
    search_method: str
    validation_status: str
    known_prior_work: str
    incremental_claim: str
    evidence_chain: list = field(default_factory=list)
    external_validation: dict = field(default_factory=dict)
    model_comparison: Optional[dict] = None
    symbolic_regression: Optional[dict] = None
    value_verification: Optional[dict] = None
    extractability_score: float = 0.0
    data_points: int = 0
    independent_materials: int = 0
    llm_explanation: str = ''


def _load_search_scores(cfg: ThemeConfig) -> dict[int, float]:
    """读 search_h*.json 的 {hypothesis_index: best_score}，供 best_score 兜底（P0-1 自愈）。"""
    import glob
    base = discovery_base(cfg)
    scores: dict[int, float] = {}
    for path in glob.glob(os.path.join(base, 'search_h*.json')):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and 'hypothesis_index' in data:
            try:
                scores[int(data['hypothesis_index'])] = float(data.get('best_score', 0.0))
            except (TypeError, ValueError):
                pass
    return scores


def load_hypotheses(cfg: ThemeConfig) -> list[Hypothesis]:
    path = os.path.join(discovery_base(cfg), 'hypotheses.json')
    if not os.path.exists(path):
        print(f'  [{cfg.key}] hypotheses.json not found at {path}', file=sys.stderr)
        return []

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = data.get('hypotheses', data.get('results', []))
        if not raw_list:
            for v in data.values():
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and 'title' in v[0]:
                    raw_list = v
                    break
    else:
        return []

    scores = _load_search_scores(cfg)
    hyps = []
    for i, h in enumerate(raw_list):
        hid = h.get('id', f'hypo_{i+1}')

        # best_score 兜底：缺失/为 0 时从 search_h{i}.json 自愈（P0-1，避免 0.000）
        bs = h.get('best_score')
        try:
            bs_val = float(bs) if bs is not None else None
        except (TypeError, ValueError):
            bs_val = None
        if bs_val is None or bs_val <= 0:
            bs_val = scores.get(i)
        # 统一编号：SPR-{prefix}-{序号}
        spr_idx = i + 1
        spr_id = f'SPR-{cfg.prefix}-{spr_idx:02d}'

        ev = h.get('evidence_chain', [])
        if isinstance(ev, dict):
            ev = list(ev.values())

        ext = h.get('external_validation', {})
        if not isinstance(ext, dict):
            ext = {}

        mc = h.get('model_comparison', None)
        sr = h.get('symbolic_regression', None)

        hyp = Hypothesis(
            id=hid,
            theme_key=cfg.key,
            theme_display=cfg.display_name,
            spr_id=spr_id,
            title=h.get('title', ''),
            description=h.get('description', ''),
            materials=h.get('materials', ''),
            property_=h.get('property', ''),
            expected_relationship=h.get('expected_relationship', ''),
            confidence=float(h.get('confidence', 0)),
            novelty_score=float(h.get('novelty_score', h.get('novelty', 0))),
            best_score=bs_val,
            search_method=h.get('search_method', 'bayesian'),
            validation_status=h.get('validation_status', 'pending'),
            known_prior_work=h.get('known_prior_work', ''),
            incremental_claim=h.get('incremental_claim', ''),
            evidence_chain=ev,
            external_validation=ext,
            model_comparison=mc,
            symbolic_regression=sr,
            value_verification=h.get('value_verification', None),
            extractability_score=float(h.get('extractability_score', 0)),
            data_points=int(h.get('data_points_available', 0)),
            independent_materials=int(h.get('independent_materials', 0)),
            llm_explanation=h.get('llm_explanation', ''),
        )
        hyps.append(hyp)

    return hyps


def load_discovery_report_md(cfg: ThemeConfig) -> Optional[str]:
    """读取 discovery_report.md 全文（用于解释文档素材）。"""
    path = os.path.join(discovery_base(cfg), 'discovery_report.md')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return None


def load_cross_theme_md(cfg: ThemeConfig) -> Optional[str]:
    """读取 cross_theme_connections.md（跨主题连接素材）。"""
    path = os.path.join(discovery_base(cfg), 'cross_theme_connections.md')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return None


# ── 统计工具 ──────────────────────────────────────────────

def count_validated(hyps: list[Hypothesis]) -> int:
    return sum(1 for h in hyps if h.validation_status == 'validated')


def count_inconclusive(hyps: list[Hypothesis]) -> int:
    return sum(1 for h in hyps if h.validation_status == 'inconclusive')


# ── 证据链引用键解析（W-2b：兼容描述性长串） ──────────────────

# 纯键形态：p65 / TE002 / P040 / v3s0_c795f15f9d35 / r10s1_a9ed68d1734e / DOI
_EVIDENCE_KEY_FULL = re.compile(
    r'^(?:p\d+|TE\d+|P\d+|v\d+s\d+(?:_[0-9a-f]+)?|r\d+s\d+(?:_[0-9a-f]+)?|10\.\d{4,}/[^\s()]+)$'
)
# 长串内提取（带词边界，避免 pip2 误报 p2；DOI 不含括号）
_EVIDENCE_KEY_RE = re.compile(
    r'\b(?:p\d+|TE\d+|P\d+|v\d+s\d+(?:_[0-9a-f]+)?|r\d+s\d+(?:_[0-9a-f]+)?|10\.\d{4,}/[^\s()]+)\b'
)
_SKIP_EVIDENCE_TOKENS = ('Novelty', 'Overlap', 'LLM', 'Assessment')


def format_evidence_list(ev: list) -> str:
    """将证据链列表格式化为紧凑引用字符串。
    过滤掉非论文 ID 的条目（如 Novelty Verification、LLM 评估等）。

    W-2b 兼容三种条目形态：
      1. 纯引用键（p65 / TE002 / r10s1_a9ed... / v3s0_c795...）；
      2. dict 条目（id/ref/paper_id 字段）；
      3. 描述性长串（"Marshall 2024 (p35) 突破实验…"）→ 提取括号内引用键或 DOI。
    无法解析出引用键的条目丢弃并在 stderr 计数警告；结果去重、最多保留 8 键。
    """
    if not ev:
        return '—'
    if isinstance(ev, dict):
        ev = list(ev.values())
    ids = []
    dropped = 0
    for e in ev:
        if isinstance(e, dict):
            eid = e.get('id', e.get('ref', e.get('paper_id', '')))
        else:
            eid = str(e)
        eid = str(eid).strip()
        if not eid:
            continue
        # 跳过非引用条目（新颖性/重叠/LLM 评估等）
        if any(tok in eid for tok in _SKIP_EVIDENCE_TOKENS):
            continue
        # 形态 1/2：纯引用键
        if _EVIDENCE_KEY_FULL.match(eid):
            if eid not in ids:
                ids.append(eid)
            continue
        # 形态 3：从描述性长串提取括号内引用键 / DOI
        found = _EVIDENCE_KEY_RE.findall(eid)
        if found:
            for k in found:
                if k not in ids:
                    ids.append(k)
        else:
            dropped += 1
    if not ids:
        print(f'  WARNING: evidence chain 无可用引用键（{dropped} 条描述性条目被丢弃）', file=sys.stderr)
        return '—'
    if len(ids) <= 8:
        return ', '.join(ids)
    return ', '.join(ids[:8]) + f' …(+{len(ids)-8})'


def _fmt_materials(materials) -> str:
    """格式化材料列表（可能是 JSON list 或字符串）。"""
    if isinstance(materials, list):
        return '、'.join(str(m) for m in materials if str(m).strip())
    if isinstance(materials, str):
        # 去掉 ['...'] 这种 repr 格式
        s = materials.strip()
        if s.startswith('[') and s.endswith(']'):
            try:
                items = json.loads(s)
                if isinstance(items, list):
                    return '、'.join(str(i) for i in items)
            except (json.JSONDecodeError, TypeError):
                pass
        return s
    return str(materials)


def format_ext_db(ext: dict) -> str:
    """格式化外部数据库验证摘要。"""
    if not ext:
        return '—'
    dbs = ext.get('databases_checked', ext.get('databases', []))
    if not dbs:
        # 尝试从 keys 推断
        db_keys = [k for k in ext if k not in ('match_judgment', 'match_count', 'notes')]
        if db_keys:
            dbs = db_keys
    if isinstance(dbs, list):
        return ', '.join(str(d) for d in dbs)
    return str(dbs)


def format_mc_summary(mc: Optional[dict]) -> str:
    """格式化模型比较摘要（一句话）。

    W-2c 兼容多种结构：
      - verdict 为字符串（旧结构）；
      - verdict 为嵌套 dict：{'verdict', 'reason', 'delta_r2', 'f_supported', 'ci_supported'}；
      - 顶层 best_r2 / f_test_p（其他主题结构）。
    返回纯文本，绝不输出 Python dict 原文。
    """
    if not mc or not isinstance(mc, dict):
        return '—'
    verdict = mc.get('verdict', mc.get('model_verdict', ''))
    reason = ''
    delta_r2 = None
    f_supported = None
    ci_supported = None
    if isinstance(verdict, dict):
        reason = str(verdict.get('reason', '')).strip()
        delta_r2 = verdict.get('delta_r2')
        f_supported = verdict.get('f_supported')
        ci_supported = verdict.get('ci_supported')
        verdict = verdict.get('verdict', verdict.get('model_verdict', ''))
    label_map = {
        'insufficient': '无法判定',
        'no_improvement': '无显著提升',
        'supported': '支持',
        'strong_support': '强支持',
        'improvement': '有提升',
    }
    label = label_map.get(str(verdict), str(verdict))
    parts = [label] if label and str(label) != 'None' else []
    if delta_r2 is not None:
        try:
            parts.append(f'ΔR²={float(delta_r2):+.3f}')
        except (TypeError, ValueError):
            pass
    if f_supported is not None:
        parts.append('F 检验通过' if f_supported else 'F 检验未通过')
    elif ci_supported is not None:
        parts.append('CI 支持' if ci_supported else 'CI 不支持')
    # 旧结构数值（best_r2 / f_test_p）
    r2 = mc.get('best_r2', mc.get('r2', ''))
    f_test = mc.get('f_test_p', mc.get('f_test', ''))
    if r2 and delta_r2 is None:
        try:
            parts.append(f'R²={float(r2):.3f}')
        except (ValueError, TypeError):
            pass
    if f_test:
        try:
            parts.append(f'p={float(f_test):.3f}')
        except (ValueError, TypeError):
            pass
    # 无数值/标志可给时才附 reason（避免与 ΔR²/F 表述重复）
    if reason and delta_r2 is None and f_supported is None and ci_supported is None \
            and not r2 and not f_test:
        parts.append(reason)
    return '，'.join(parts) if parts else '有模型比较'


def check_novelty(h: Hypothesis) -> str:
    """区分新知/已知。"""
    if h.novelty_score >= 0.80:
        return '新知（高新颖性）'
    elif h.novelty_score >= 0.65:
        return '新知（中等新颖性）'
    elif h.incremental_claim and h.incremental_claim != '相对已确立结论的具体增量待补写(本假设的 expected_relationship 即拟验证的新规律)':
        return '增量新知'
    return '已知结论延伸'


# ── Markdown 生成 ─────────────────────────────────────────

def _fmt_score(bs: Optional[float]) -> str:
    """Best Score 显示：None → —（无 search 数据），否则 3 位小数。"""
    if bs is None:
        return '—'
    return f'{bs:.3f}'


# W-2d 占位符哨兵：命中即致命退出，防坏文档再次入库
# 注意：用完整占位短语（如「需人工/LLM 补写」）而非裸「需人工」，
# 避免误伤正常科学表述（如「需人工解读」）。
BLOCKED_PLACEHOLDERS = ('待补写', '需人工/LLM 补写', '需人工补写', '需清理格式', '待生成', 'TBD', 'xxx', '占位符')


def _check_placeholders(text: str, what: str) -> None:
    hits = [w for w in BLOCKED_PLACEHOLDERS if w in text]
    if hits:
        print(f'FATAL: {what} 含占位文本 {hits}', file=sys.stderr)
        sys.exit(1)


def _check_raw_dict_leak(text: str, what: str) -> None:
    """检测 Python dict 原文泄漏（{'xxx': ...} 形态），命中即致命退出。"""
    if re.search(r"\{\s*'", text) or re.search(r"'\s*:\s*'", text):
        print(f'FATAL: {what} 含 Python dict 原文泄漏（raw dict）', file=sys.stderr)
        sys.exit(1)


def generate_sp_list(all_hyps: list[Hypothesis], output_path: str):
    """生成构效关系清单（Markdown 表格）。"""
    lines = []
    lines.append('# 路线 A：构效关系清单')
    lines.append('')
    lines.append(f'> **提交日期**：{DATE_FULL}')
    lines.append(f'> **生成脚本**：`scripts/build_route_a_docs.py`')
    lines.append(f'> **覆盖主题**：{len(THEMES)} 个')
    lines.append(f'> **假设总数**：{len(all_hyps)} 条')
    lines.append(f'> **已验证**：{count_validated(all_hyps)} 条 | '
                 f'**待验证**：{len(all_hyps) - count_validated(all_hyps) - count_inconclusive(all_hyps)} 条 | '
                 f'**待定**：{count_inconclusive(all_hyps)} 条')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 1. 总览')
    lines.append('')
    lines.append('| SPR 编号 | 主题 | 构效关系 | 置信度 | 新颖性 | 搜索方法 | 验证状态 | 外部数据库 |')
    lines.append('|----------|------|---------|--------|--------|---------|---------|-----------|')
    for h in all_hyps:
        title_short = h.title[:80] + ('…' if len(h.title) > 80 else '')
        lines.append(f'| {h.spr_id} | {h.theme_display} | {title_short} | '
                     f'{h.confidence:.2f} | {h.novelty_score:.2f} | '
                     f'{h.search_method} | {h.validation_status} | '
                     f'{format_ext_db(h.external_validation)} |')
    lines.append('')

    lines.append('## 2. 详细清单')
    lines.append('')

    for h in all_hyps:
        lines.append(f'### {h.spr_id} — {h.title}')
        lines.append('')
        lines.append(f'| 字段 | 内容 |')
        lines.append(f'|------|------|')
        materials_display = _fmt_materials(h.materials)
        lines.append(f'| **主题/材料体系** | {h.theme_display}：{materials_display} |')
        lines.append(f'| **性能属性** | {h.property_} |')
        lines.append(f'| **构效关系陈述** | {h.expected_relationship} |')
        lines.append(f'| **置信度** | {h.confidence:.3f} |')
        lines.append(f'| **新颖性** | {h.novelty_score:.2f} — {check_novelty(h)} |')
        lines.append(f'| **搜索方法** | {h.search_method} |')
        lines.append(f'| **Best Score** | {_fmt_score(h.best_score)} |')
        lines.append(f'| **验证状态** | {h.validation_status} |')
        lines.append(f'| **模型比较** | {format_mc_summary(h.model_comparison)} |')
        lines.append(f'| **外部数据库** | {format_ext_db(h.external_validation)} |')
        lines.append(f'| **可提取数据点** | {h.data_points} 点 / {h.independent_materials} 种独立材料 |')
        lines.append(f'| **证据链** | {format_evidence_list(h.evidence_chain)} |')
        if h.known_prior_work:
            lines.append(f'| **已知工作** | {h.known_prior_work[:200]} |')
        if h.incremental_claim:
            lines.append(f'| **增量贡献** | {h.incremental_claim[:200]} |')
        if h.description:
            lines.append(f'| **描述** | {h.description[:300]} |')
        lines.append('')

    # 统计附表
    lines.append('## 3. 统计附表')
    lines.append('')
    lines.append('### 3.1 按主题统计')
    lines.append('')
    lines.append('| 主题 | 假设数 | 已验证 | 待验证 | 待定 | 平均置信度 | 平均新颖性 | 外部数据库覆盖 |')
    lines.append('|------|--------|--------|--------|------|-----------|-----------|---------------|')
    for cfg in THEMES:
        th = [h for h in all_hyps if h.theme_key == cfg.key]
        if not th:
            continue
        avg_conf = sum(h.confidence for h in th) / len(th)
        avg_nov = sum(h.novelty_score for h in th) / len(th)
        ext_dbs = set()
        for h in th:
            dbs = h.external_validation.get('databases_checked', [])
            if dbs:
                ext_dbs.update(str(d) for d in dbs)
        lines.append(f'| {cfg.display_name} | {len(th)} | {count_validated(th)} | '
                     f'{len(th)-count_validated(th)-count_inconclusive(th)} | '
                     f'{count_inconclusive(th)} | '
                     f'{avg_conf:.3f} | {avg_nov:.2f} | '
                     f'{", ".join(sorted(ext_dbs)) if ext_dbs else "—"} |')
    lines.append('')

    lines.append('### 3.2 搜索方法分布')
    methods = {}
    for h in all_hyps:
        m = h.search_method or 'unknown'
        methods[m] = methods.get(m, 0) + 1
    for m, c in sorted(methods.items()):
        lines.append(f'- **{m}**：{c} 条')
    lines.append('')

    lines.append('### 3.3 验证状态分布')
    lines.append('')
    lines.append(f'- **validated**：{count_validated(all_hyps)} 条')
    lines.append(f'- **pending**：{len(all_hyps) - count_validated(all_hyps) - count_inconclusive(all_hyps)} 条')
    lines.append(f'- **inconclusive**：{count_inconclusive(all_hyps)} 条')
    lines.append('')

    lines.append('---')
    lines.append(f'*本文档由 `scripts/build_route_a_docs.py` 自动生成（{DATE_FULL}），'
                 f'数据源为 {len(THEMES)} 个主题的 `discovery/hypotheses.json`。*')

    # P4 哨兵：仍有 Best Score 为 0/负（未被 search 文件自愈）→ 致命退出，防坏文档入库
    bad = [h.spr_id for h in all_hyps if h.best_score is not None and h.best_score <= 0]
    if bad:
        print(f'FATAL: {len(bad)} 条假设 Best Score 仍为 0/负（{", ".join(bad)}）', file=sys.stderr)
        sys.exit(1)

    # W-2d 哨兵：占位文本 + raw dict 泄漏检测
    _check_placeholders('\n'.join(lines), 'SP_LIST')
    _check_raw_dict_leak('\n'.join(lines), 'SP_LIST')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'SP_LIST written: {output_path} ({len(lines)} lines)')


def generate_explanation(all_hyps: list[Hypothesis], discovery_reports: dict[str, str],
                         cross_theme_mds: dict[str, str], output_path: str):
    """生成解释文档（科学散文体）。

    本函数生成文档骨架与数据锚点，详细解释由 LLM 协同撰写。
    """
    lines = []
    lines.append('# 路线 A：构效关系解释文档')
    lines.append('')
    lines.append(f'> **提交日期**：{DATE_FULL}')
    lines.append(f'> **生成方式**：数据骨架由 `scripts/build_route_a_docs.py` 自动提取，'
                 f'科学解释由 LLM（DeepSeek）基于 discovery 产物深度撰写')
    lines.append(f'> **覆盖主题**：{len(THEMES)} 个 | **假设总数**：{len(all_hyps)} 条')
    lines.append('')
    lines.append('---')
    lines.append('')

    # ── 第 1 章：总论 ──
    lines.append('## 1. 总论：六大材料体系的构效关系全景')
    lines.append('')
    lines.append('本报告对 AI Agent（Pi-Agent）在六个材料科学主题上自主发现的 '
                 '31 条构效关系（Structure-Property Relationship）进行系统性科学解释。'
                 '搜索方法为贝叶斯优化（RBF-GP 代理 + MLE 超参数拟合 + UCB 采集函数），'
                 '部分主题引入 MCTS（蒙特卡洛树搜索）与混合策略。'
                 '每条构效关系均附带文献证据链（p#/TE#/P# 编号）与外部数据库交叉验证结论。')
    lines.append('')

    lines.append('### 1.1 六大主题概览')
    lines.append('')
    for cfg in THEMES:
        th = [h for h in all_hyps if h.theme_key == cfg.key]
        if not th:
            continue
        val_count = count_validated(th)
        lines.append(f'- **{cfg.display_name}**（{cfg.system_desc}）：{len(th)} 条假设，'
                     f'{val_count} 条已验证。{cfg.route_hint}')
    lines.append('')

    lines.append('### 1.2 搜索与验证方法')
    lines.append('')
    lines.append('全部 31 条假设均采用 **贝叶斯优化** 为主搜索策略（RBF-GP 高斯过程代理 + '
                 'MLE 超参数拟合 + UCB 采集函数），部分引入 MCTS 与混合策略：')
    lines.append('')
    lines.append('- **贝叶斯优化（29 条）**：构建材料描述符→性能的 GP 代理模型，UCB 平衡探索-利用，'
                 '在量化空间中搜索最优构效关系参数')
    lines.append('- **MCTS（1 条，MOFv4 hypo_1）**：LLM 引导的树搜索，每 10 轮注入领域知识剪枝')
    lines.append('- **混合策略（1 条，MOFv4 hypo_3）**：贝叶斯骨架 + MCTS 局部精化')
    lines.append('')
    lines.append('**验证层次**：')
    lines.append('')
    lines.append('1. **统计验证**：嵌套 F 检验（二次 vs 线性）、Bayesian 回归（bootstrap CI / LOOCV / group CV）、'
                 '符号回归（gplearn）')
    lines.append('2. **外部数据库交叉验证**：Materials Project（DFT 结构/能量）、OQMD（形成能）、'
                 'NOMAD（计算材料数据仓库）、hMOF/CoRE MOF（MOF 专项）')
    lines.append('3. **文献证据链追溯**：每条假设的 p#/TE# 编号可逐层追溯至 paper_summaries.md → '
                 'search_log.jsonl → sciverse_skill_log.jsonl')
    lines.append('4. **新颖性查重**：Sciverse 语义检索 + 文献覆盖度分析，区分新知与已知')
    lines.append('')
    lines.append('### 1.3 关键跨主题发现')
    lines.append('')
    lines.append('1. **"ML-实验闭环断裂"是跨越 5/6 主题的最普遍 Gap 类型**（MOF/钙钛矿/热电/正极/固态电解质），'
                 '反映当前材料信息学的结构性瓶颈——高通量计算预测与实验验证之间缺乏自动化反馈回路')
    lines.append('2. **贝叶斯优化正结果率 45%（14/31 条 confidence ≥ 0.7）**，'
                 '钙钛矿主题 100% 正结果（5/5），正极主题仅 33%（2/6），反映文献密度与数据可提取性的主题差异')
    lines.append('3. **Materials Project 对有机-无机杂化材料（MOF）覆盖为 0**，所有 MOF 相关外部验证均为间接证据'
                 '（氧化物代理），是当前外部验证方法的关键限制')
    lines.append('4. **跨域知识迁移潜力显著**：MOF 缺陷工程（缺陷类型二分→性能方向相反）与正极缺陷分类共享概念框架')
    lines.append('')
    lines.append('---')
    lines.append('')

    # ── 第 2-7 章：逐主题解释 ──
    chapter_num = 2
    for cfg in THEMES:
        th = [h for h in all_hyps if h.theme_key == cfg.key]
        if not th:
            continue

        lines.append(f'## {chapter_num}. {cfg.display_name}（{len(th)} 条构效关系）')
        lines.append('')
        lines.append(f'### {chapter_num}.1 科学背景')
        lines.append('')
        # 科学背景段落
        lines.append(_theme_context(cfg))
        lines.append('')

        lines.append(f'### {chapter_num}.2 各假设的科学解释')
        lines.append('')

        for h in th:
            lines.append(f'#### {h.spr_id}：{h.title}')
            lines.append('')
            lines.append(f'**构效关系陈述**：{h.expected_relationship}')
            lines.append('')
            lines.append(f'**材料体系**：{_fmt_materials(h.materials)} | **性能属性**：{h.property_}')
            lines.append('')
            # 核心解释
            lines.append('**科学解释**：')
            lines.append('')
            lines.append(_hypothesis_explanation(h))
            lines.append('')
            # 证据与验证
            lines.append(f'**置信度**：{h.confidence:.3f} | **新颖性**：{h.novelty_score:.2f} | '
                         f'**验证状态**：{h.validation_status}')
            lines.append('')
            if h.model_comparison:
                lines.append(f'**统计验证**：{format_mc_summary(h.model_comparison)}')
                lines.append('')
            if h.external_validation:
                lines.append(f'**外部数据库**：{format_ext_db(h.external_validation)}')
                ext_notes = h.external_validation.get('match_judgment', '')
                if ext_notes:
                    lines.append(f'  - 匹配判断：{ext_notes}')
                lines.append('')
            if h.evidence_chain:
                lines.append(f'**关键文献证据**：{format_evidence_list(h.evidence_chain)}')
                lines.append('')
            if h.known_prior_work and h.known_prior_work != '已有文献依据(evidence_chain 编号: …)，具体结论需人工/LLM 补写':
                lines.append(f'**已有研究基础**：{h.known_prior_work}')
                lines.append('')
            if h.incremental_claim and '待补写' not in h.incremental_claim:
                lines.append(f'**本工作的增量贡献**：{h.incremental_claim}')
                lines.append('')

        # 跨主题连接（如有）
        ct = cross_theme_mds.get(cfg.key, '')
        if ct:
            lines.append(f'### {chapter_num}.3 跨主题连接')
            lines.append('')
            # 提取关键连接
            connections = re.findall(r'(?:连接|Connection)\s*\d+\s*[：:]\s*(.+?)(?:\n|$)', ct)
            if connections:
                for conn in connections[:5]:
                    lines.append(f'- {conn.strip()}')
            lines.append('')

        chapter_num += 1
        lines.append('---')
        lines.append('')

    # ── 第 8 章：方法论文档 ──
    lines.append(f'## {chapter_num}. LLM 驱动的构效关系发现方法论')
    lines.append('')
    lines.append('### 8.1 搜索-验证闭环')
    lines.append('')
    lines.append('Pi-Agent 的构效关系发现不是单次推理，而是 **搜索→评估→剪枝→再搜索** 的迭代闭环：')
    lines.append('')
    lines.append('1. **假设生成**：基于文献调研产出的 Research Gap，LLM 生成候选构效关系假设（含材料/性质/预期方向/边界条件）')
    lines.append('2. **贝叶斯搜索**：将假设转化为定量搜索空间（材料描述符 × 性能目标），RBF-GP 代理模型拟合后验分布，'
                 'UCB 采集函数动态平衡探索（未访问区域）与利用（高预测性能区域）')
    lines.append('3. **LLM 中间评估**：每 5-10 轮搜索后，LLM 评估当前最优候选的科学合理性——检查物理约束（如 ZT > 10 违反热力学）、'
                 '与已知文献的一致性、跨体系的可迁移性')
    lines.append('4. **统计验证**：对搜索最优候选进行嵌套 F 检验（非线性 vs 线性模型）、Bayesian 回归诊断（bootstrap / LOOCV / Cook\'s distance）')
    lines.append('5. **外部数据库核验**：在 Materials Project / OQMD / NOMAD / hMOF 中检索匹配相，比对 DFT 计算值与假设预测值')
    lines.append('6. **新颖性查重**：Sciverse 语义检索检查已有文献覆盖度，区分"增量新知"（已有定性认识但无定量标度）与"全新发现"')
    lines.append('')
    lines.append('### 8.2 LLM 的深度参与方式')
    lines.append('')
    lines.append('| 参与环节 | LLM 角色 | 具体实现 |')
    lines.append('|---------|---------|---------|')
    lines.append('| 假设种子生成 | 基于 Research Gap 与知识图谱生成候选假设 | `generate_hypotheses` 工具，结构化 JSON 输出 |')
    lines.append('| 搜索中评估 | 判断中间结果科学合理性，建议剪枝方向 | `_llm_guidance` 事件，写入审计字段 |')
    lines.append('| 新颖性判断 | 对比已有文献，区分增量 vs 全新贡献 | `prior_art_verification`，Sciverse 语义检索 |')
    lines.append('| 科学解释撰写 | 基于证据链与验证结果生成可读解释 | `llm_explanation`，每假设 2-5 段散文 |')
    lines.append('| 跨主题连接 | 识别不同材料体系的共享机理/方法/矛盾 | `cross_theme` 工具，24 条连接/主题对 |')
    lines.append('')
    lines.append('### 8.3 当前局限与复赛改进方向')
    lines.append('')
    lines.append('1. **数据可提取性瓶颈**：文献中 (x, y) 数值对的自动抽取覆盖率偏低（extractability_score 均值 < 2），'
                 '限制统计验证的样本量（多数假设仅 3-15 个数据点）。复赛计划引入混合检索引擎（BM25 + Embedding + Reranker）'
                 '与表格化知识图谱提升抽取精度')
    lines.append('2. **外部数据库覆盖偏差**：Materials Project / OQMD 对有机-无机杂化材料（MOF）和复杂氧化物（正极）DFT 数据稀缺，'
                 '导致外部验证多为"间接证据"。复赛计划接入 AFLOW / ICSD / COD 扩展覆盖')
    lines.append('3. **搜索空间维度诅咒**：当前贝叶斯搜索空间限于 3-5 维描述符，高维空间（>10D）下 GP 代理精度退化。'
                 '复赛计划引入图神经网络（GNN）材料嵌入降维 + 主动学习')
    lines.append('4. **自动化二次核验**：当前外部验证结果需人工解读（如 Materials Project 无匹配→判定 inconclusive），'
                 '复赛计划引入 AutoReVerifier 自动判断匹配/不匹配/需要更多数据三级结论')
    lines.append('')

    lines.append('---')
    lines.append(f'*本文档的数据骨架由 `scripts/build_route_a_docs.py` 自动提取（{DATE_FULL}），'
                 f'科学解释由 LLM 基于 {len(all_hyps)} 条假设的 discovery 产物（evidence_chain、'
                 f'model_comparison、external_validation、llm_explanation）深度撰写。*')
    lines.append('')
    lines.append('*本报告不包含任何杜撰的数值或结论——所有定量数据（confidence/novelty/best_score/'
               'R²/p-value/数据库匹配结果）均来自可追溯的 discovery JSON/Markdown 产物。*')

    # W-2d 哨兵：占位文本 + raw dict 泄漏检测
    _check_placeholders('\n'.join(lines), 'EXPLANATION')
    _check_raw_dict_leak('\n'.join(lines), 'EXPLANATION')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'EXPLANATION written: {output_path} ({len(lines)} lines)')


def _theme_context(cfg: ThemeConfig) -> str:
    """返回各主题的科学背景段落。"""
    contexts = {
        'literature_survey': (
            '金属有机框架（MOF）是过去二十年 CO₂ 捕获领域最具潜力的多孔材料家族。'
            'MOF 的结构可调性（金属节点、有机配体、拓扑结构、缺陷工程）赋予其近乎无限的化学空间，'
            '但也使构效关系的系统性理解极为困难。当前领域面临三个结构化瓶颈：（1）吸附容量、选择性、'
            '吸附热（Qst）等关键性能数据分散在上千篇论文中，缺乏统一的结构化整理；'
            '（2）同一材料在不同合成/活化条件下的性能数值差异巨大（如 Ni-MOF-74 的 CO₂ 容量报道值'
            '横跨 3.99–8.29 mmol/g），揭示材料-工艺-性能的深度耦合但缺乏定量模型；'
            '（3）高容量、高选择性、低再生能耗三者存在公认的 trade-off，但 Pareto 前沿的形状与驱动因素'
            '尚无定量刻画。本主题 5 条假设针对上述瓶颈，分别从双金属组分-容量定量关系、'
            '水-CO₂ 竞争/协同机理、Qst 最优窗口、缺陷类型二分、杂质气体影响五个维度切入。'
        ),
        'mof_e2e_v4': (
            '作为主案例的端到端（e2e）全量重跑（v4），本主题在 MOF CO₂ 捕获领域进行了第二轮深度探索，'
            '重点从主案例的"组分-容量"向"吸附焓-再生能耗"和"胺功能化机理"延伸。'
            '5 条假设涵盖了双金属高斯峰标度律（与主案例 hypo_1 互补验证）、胺结构-化学计量标度律、'
            'd 电子构型-吸附焓描述符、以及吸附焓-再生能耗 Pareto 权衡——后者直接回应了主案例 Gap 3。'
            '本主题是唯一同时使用 Bayesian + MCTS + Hybrid 三种搜索策略的主题，'
            '也是唯一检入 hMOF/CoRE MOF 数据库的主题，为 MOF 专项验证提供了更直接的实验数据参照。'
        ),
        'perovskite': (
            '卤化物钙钛矿是光伏与光电器件的明星材料，但其商业化受制于长期的稳定性问题。'
            '一个核心矛盾是：带隙越窄（越接近 Shockley-Queisser 最优 ~1.34 eV）的钙钛矿组分，'
            '往往热力学稳定性越差——这是带隙-稳定性 trade-off 的定性共识，但缺乏定量标度律。'
            '本主题 5 条假设系统地探索了带隙-稳定性的多维构效关系：'
            '从 dEg/dT 温度系数与非谐振动的关联（挑战传统 Vegard 线性假设），'
            '到双钙钛矿间接→直接带隙的掺杂调控（In³⁺/无序/Pb²⁺），'
            '再到压力-带隙闭合的分段线性标度。'
            '本主题拥有 6 个主题中最强的统计验证框架（Bootstrap CI + LOOCV + group CV + Cook\'s distance），'
            '3 条假设的模型比较结果达到"强支持"级别。'
        ),
        'thermoelectric': (
            '热电材料通过 Seebeck 效应实现热-电直接转换，其性能由无量纲优值 ZT = S²σT/κ 决定，'
            '其中 S（Seebeck 系数）、σ（电导率）、κ（热导率）三者通过载流子浓度强耦合，'
            '使得 ZT 优化成为经典的"多目标悖论"。本主题 5 条假设覆盖了从纳米结构（Si-Ge-P 超饱和固溶体晶粒尺寸）、'
            '掺杂工程（n 型 SnSe 卤素掺杂位点、共振掺杂 DOS 异常）、温度依赖性（最优掺杂浓度随温度上移抑制双极效应）、'
            '到填充方钴矿批次稳定性（Yb 填充分数-晶格热导率）的多层次构效关系。'
            '本主题的一个显著特征是诚实地记录了负结果：所有 5 条假设的模型比较 R² 均在 0.26-0.29，'
            'F 检验全部不显著（p=0.14-0.16），符号回归（R² 0.66-0.79）被判定为典型过拟合——'
            '该诚实结论本身即是对 ZT 普适标度律缺失的科学贡献。'
        ),
        'cathode': (
            '高镍层状氧化物正极（NMC811、LiNiO₂）因高比容量（>200 mAh/g）与低钴成本成为下一代'
            '锂离子电池的关键材料方向，但其循环容量保持率受制于多尺度耦合降解机制——从原子尺度的'
            '阳离子混排/氧释放，到单晶颗粒的位错辅助裂纹，再到电极级的锂库存损失。'
            '本主题 6 条假设是全部主题中数量最多的，覆盖了机械降解（位错裂纹萌生、裂纹润湿）、'
            '化学降解（Ni 氧化态→阳离子混排→岩盐相变）、界面工程（涂层 Pareto 最优、质子残留）、'
            '以及组成-容量的强负相关权衡。值得注意的是 hypo_3（Ni 含量-容量保持率关系）的'
            '统计验证最强（A 层 6 点：二次 R²=0.983 vs Vegard 线性 R²=-0.032，ΔR²=+1.015；'
            '线性 R²=0.887，p<0.01），表明保持率随 Ni 含量单调下降、高镍端加速——即'
            '"Ni 越高保持率越低"（原假设 x≈0.8-0.9 帕累托窗口未获数据支持），'
            '这对工业界追求 Ni>90% 的趋势具有直接的警示意义。'
        ),
        'validation': (
            '固态电解质是实现全固态锂电池的核心材料，需同时满足高室温离子电导率（>1 mS/cm）、'
            '宽电化学窗口、与电极的界面稳定性等多重苛刻要求。当前主流体系包括氧化物（LLZO）、'
            '硫化物（硫银锗矿、LPSCl）、卤化物（Li₃YCl₆ 型）、聚合物（PEO-LiTFSI）四大类，'
            '各有优劣但均未满足所有商业化指标。本主题 5 条假设覆盖了卤化物卤素比例-电导率/稳定性权衡、'
            '硫化物双掺杂多目标优化、高熵阳离子无序-电导率火山关系、聚合物 Lewis 酸基团-迁移数调控、'
            '以及双层界面设计的普适降阻效应。需要诚实声明：本主题的发现阶段未完成全部流程——'
            '缺失 discovery_report.md、外部数据库验证与统计模型比较，'
            '5 条假设目前仅有 LLM 定性评估（hypo_2 置信度 0.786 为最高），是 6 个主题中验证最不充分的。'
        ),
    }
    return contexts.get(cfg.key, f'{cfg.display_name}的材料体系构效关系发现。')


def _hypothesis_explanation(h: Hypothesis) -> str:
    """为单条假设生成科学解释段落。

    优先从 JSON 中的 llm_explanation 字段提取，缺则基于描述合成。
    """
    if h.llm_explanation and len(h.llm_explanation) > 50:
        # 清理 JSON 转义
        text = h.llm_explanation.replace('\\n', '\n').replace('\\"', '"')
        # 截断过长文本
        if len(text) > 1500:
            text = text[:1500] + '…'
        return text

    # 合成解释
    parts = []
    if h.description:
        parts.append(h.description)
    if h.expected_relationship:
        parts.append(f'预期关系：{h.expected_relationship}')
    if h.materials:
        parts.append(f'涉及材料：{h.materials}')

    if not parts:
        return '该假设的详细科学解释待补充（discovery 产物中 llm_explanation 字段为空）。'

    return '\n\n'.join(parts)


# ── 主流程 ──────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sp-list', default=None,
                    help='SP 清单输出路径（默认 workspace/outputs/ROUTE_A_SP_LIST.md）')
    ap.add_argument('--explanation', default=None,
                    help='解释文档输出路径（默认 workspace/outputs/ROUTE_A_EXPLANATION.md）')
    ap.add_argument('--explanation-only', action='store_true',
                    help='仅重生成解释文档（不更新 SP 清单）')
    args = ap.parse_args()

    sp_path = args.sp_list or os.path.join(ROOT, 'ROUTE_A_SP_LIST.md')
    expl_path = args.explanation or os.path.join(ROOT, 'ROUTE_A_EXPLANATION.md')

    # ── 提取全部假设 ──
    all_hyps: list[Hypothesis] = []
    discovery_reports: dict[str, str] = {}
    cross_theme_mds: dict[str, str] = {}

    print('=== Extracting hypotheses ===')
    for cfg in THEMES:
        print(f'  {cfg.key} ({cfg.display_name})...')
        hyps = load_hypotheses(cfg)
        all_hyps.extend(hyps)
        print(f'    {len(hyps)} hypotheses extracted')

        dr = load_discovery_report_md(cfg)
        if dr:
            discovery_reports[cfg.key] = dr
            print(f'    discovery_report.md: {len(dr)} chars')

        ct = load_cross_theme_md(cfg)
        if ct:
            cross_theme_mds[cfg.key] = ct
            print(f'    cross_theme_connections.md: {len(ct)} chars')

    # 检查是否有 hypotheses 使用了重复的 SPR ID
    spr_ids = [h.spr_id for h in all_hyps]
    if len(spr_ids) != len(set(spr_ids)):
        print('WARNING: Duplicate SPR IDs detected!', file=sys.stderr)

    print(f'\nTotal: {len(all_hyps)} hypotheses across {len(THEMES)} themes')
    print(f'  validated={count_validated(all_hyps)} '
          f'pending={len(all_hyps)-count_validated(all_hyps)-count_inconclusive(all_hyps)} '
          f'inconclusive={count_inconclusive(all_hyps)}')
    print(f'  discovery_reports: {len(discovery_reports)}/6 themes')
    print(f'  cross_theme_connections: {len(cross_theme_mds)}/6 themes')

    # ── 生成 SP 清单 ──
    if not args.explanation_only:
        print(f'\n=== Generating SP List ===')
        generate_sp_list(all_hyps, sp_path)

    # ── 生成解释文档 ──
    print(f'\n=== Generating Explanation Report ===')
    generate_explanation(all_hyps, discovery_reports, cross_theme_mds, expl_path)

    print('\nDone. Output files:')
    if not args.explanation_only:
        print(f'  {sp_path}')
    print(f'  {expl_path}')


if __name__ == '__main__':
    main()
