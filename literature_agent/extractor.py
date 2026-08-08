"""
知识图谱数据模型 — 文献调研的核心数据结构
===========================================
定义材料实体、性质记录、合成条件、关系三元组，
以及跨文献知识融合（实体对齐 + 关系去重 + 冲突检测）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict, fields as dc_fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class MaterialEntity:
    """材料实体"""
    name: str
    chemical_formula: Optional[str] = None
    composition: Dict[str, float] = field(default_factory=dict)
    structure: Optional[str] = None
    space_group: Optional[str] = None
    morphology: Optional[str] = None
    doping: Optional[str] = None
    defects: Optional[str] = None
    source_papers: List[str] = field(default_factory=list)
    source_context: str = ""


@dataclass
class PropertyRecord:
    """性质记录（单个数值）"""
    property_name: str
    value: float
    unit: str = ""
    condition: str = ""
    material_name: str = ""
    measurement_method: str = ""
    is_baseline: bool = False
    comparison: Optional[str] = None
    error_range: Optional[Tuple[float, float]] = None
    source_paper: str = ""
    source_context: str = ""


@dataclass
class SynthesisRecord:
    """合成/工艺记录"""
    material_name: str
    method: str
    precursors: List[str] = field(default_factory=list)
    temperature: Optional[float] = None
    temperature_unit: str = "°C"
    pressure: Optional[float] = None
    pressure_unit: str = "atm"
    duration: Optional[float] = None
    duration_unit: str = "h"
    solvent: Optional[str] = None
    atmosphere: Optional[str] = None
    ph: Optional[float] = None
    yield_value: Optional[float] = None
    yield_unit: str = "%"
    post_treatment: Optional[str] = None
    source_paper: str = ""
    source_context: str = ""


@dataclass
class Relation:
    """知识关系三元组"""
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5
    evidence: str = ""
    source_paper: str = ""
    relation_type: str = ""


@dataclass
class KnowledgeGraph:
    """文献知识图谱"""
    materials: List[MaterialEntity] = field(default_factory=list)
    properties: List[PropertyRecord] = field(default_factory=list)
    synthesis: List[SynthesisRecord] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    papers_processed: List[str] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    def save(self, filepath: str):
        # 原子写（临时文件 + rename），避免进程中断留下半截 JSON
        _p = Path(filepath)
        _p.parent.mkdir(parents=True, exist_ok=True)
        _tmp = _p.with_suffix(".json.tmp")
        _tmp.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
        import os as _os
        _os.replace(str(_tmp), str(_p))

    @staticmethod
    def load(filepath: str) -> KnowledgeGraph:
        """从 JSON 文件加载知识图谱（兼容最小化格式，容忍未知键/损坏）。

        防御：损坏/非 dict JSON 抛 ValueError（调用方处理）；
        条目中的未知键按 dataclass 字段过滤，避免 TypeError。
        """
        try:
            data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            raise ValueError(f"损坏的知识图谱 JSON: {filepath}: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(f"知识图谱 JSON 结构异常（非 dict）: {filepath}")

        def _build(cls, item):
            if not isinstance(item, dict):
                return None
            allowed = {f.name for f in dc_fields(cls)}
            try:
                return cls(**{k: v for k, v in item.items() if k in allowed})
            except TypeError:
                return None  # 必填字段缺失/类型不符 → 跳过该条目（容错加载）

        kg = KnowledgeGraph()
        kg.materials = [m for m in (_build(MaterialEntity, x)
                                   for x in data.get("materials", [])) if m is not None]
        kg.properties = [p for p in (_build(PropertyRecord, x)
                                    for x in data.get("properties", [])) if p is not None]
        kg.synthesis = [s for s in (_build(SynthesisRecord, x)
                                   for x in data.get("synthesis", [])) if s is not None]
        kg.relations = [r for r in (_build(Relation, x)
                                   for x in data.get("relations", [])) if r is not None]
        kg.papers_processed = data.get("papers_processed", [])
        kg.extraction_metadata = data.get("extraction_metadata", {})
        return kg

    def stat(self) -> Dict:
        """返回图谱统计信息。"""
        return {
            "materials": len(self.materials),
            "properties": len(self.properties),
            "synthesis_records": len(self.synthesis),
            "relations": len(self.relations),
            "papers_processed": len(self.papers_processed),
            "unique_property_types": len(set(p.property_name for p in self.properties)),
            "unique_methods": len(set(s.method for s in self.synthesis)),
        }


# ═══════════════════════════════════════════════════════════════
# Knowledge Fusion — 跨批/跨文献实体对齐与去重
# ═══════════════════════════════════════════════════════════════

class KnowledgeFusion:
    """跨文献知识融合：实体对齐 + 关系去重 + 冲突检测"""

    @staticmethod
    def merge(kg1: KnowledgeGraph, kg2: KnowledgeGraph) -> KnowledgeGraph:
        """合并两个知识图谱，按实体键去重。"""
        merged = KnowledgeGraph()

        # 材料实体去重（基于名称标准化）
        seen_materials: Dict[str, MaterialEntity] = {}
        for m in kg1.materials + kg2.materials:
            _key_base = (m.chemical_formula or m.name) or ""
            key = _key_base.lower().strip()
            if key in seen_materials:
                seen_materials[key].source_papers.extend(m.source_papers)
                seen_materials[key].source_papers = list(set(seen_materials[key].source_papers))
            else:
                seen_materials[key] = m
        merged.materials = list(seen_materials.values())

        # 性质去重（同材料 + 同性质 + 同条件）
        seen_props: Dict[Tuple, PropertyRecord] = {}
        for p in kg1.properties + kg2.properties:
            key = ((p.material_name or "").lower(), (p.property_name or "").lower(),
                   (p.condition or "").lower())
            if key not in seen_props:
                seen_props[key] = p
        merged.properties = list(seen_props.values())

        # 合成工艺去重
        seen_syn: Set[Tuple] = set()
        for s in kg1.synthesis + kg2.synthesis:
            key = ((s.material_name or "").lower(), (s.method or "").lower(), str(s.temperature))
            if key not in seen_syn:
                seen_syn.add(key)
                merged.synthesis.append(s)

        # 关系去重
        seen_rel: Set[Tuple] = set()
        for r in kg1.relations + kg2.relations:
            key = (r.subject.lower(), r.predicate.lower(), r.object.lower())
            if key not in seen_rel:
                seen_rel.add(key)
                merged.relations.append(r)

        merged.papers_processed = list(set(kg1.papers_processed + kg2.papers_processed))
        return merged


# ═══════════════════════════════════════════════════════════════
# Numerical Value Extraction — 从文本中提取数值+单位+上下文
# ═══════════════════════════════════════════════════════════════

# 单位归一化表
_UNIT_NORM_MAP = {
    "kj/mol": "kj/mol", "kj / mol": "kj/mol", "kj mol-1": "kj/mol",
    "kj mol1": "kj/mol", "kjmol": "kj/mol",
    "mmol/g": "mmol/g", "mmol / g": "mmol/g",
    "mol/kg": "mol/kg", "mmol/cm3": "mmol/cm3",
    "mg/g": "mg/g", "m2/g": "m2/g", "wt%": "wt%", "wt %": "wt%",
    "bar": "bar", "ppm": "ppm", "ev": "ev",
    "h": "h", "min": "min", "%": "%",
    "k": "k",
}

# 数值+单位正则
_VALUE_UNIT_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*'
    r'('
    r'[Kk][Jj]\s*/\s*[Mm][Oo][Ll]|'
    r'[Kk][Jj]\s*[Mm][Oo][Ll]\s*[-]*[1]?|'
    r'mmol\s*/\s*g\b|mol\s*/\s*kg\b|mmol\s*/\s*cm3\b|'
    r'mg\s*/\s*g\b|m2\s*/\s*g\b|wt\s*%|'
    r'bar\b|ppm\b|eV\b|'
    r'[Kk]\b|min\b|h\b|'
    r'%\s*(?:RH|rh)?'
    r')',
    re.IGNORECASE,
)


def _normalize_unit(raw_unit: str) -> str:
    """将文献中的单位字符串归一化为标准形式。"""
    u = raw_unit.strip().lower()
    u = re.sub(r'\s+', ' ', u)
    u = re.sub(r'[-]+', '', u).replace('1', '')
    u = u.strip()
    for variant, canon in _UNIT_NORM_MAP.items():
        if u == variant or u.replace(' ', '') == variant.replace(' ', ''):
            return canon
    u_nospace = u.replace(' ', '')
    for variant, canon in _UNIT_NORM_MAP.items():
        if u_nospace == variant.replace(' ', ''):
            return canon
    return u


def extract_numerical_values_with_context(
    text: str,
    unit_patterns: List[str] = None,
) -> List[Dict[str, Any]]:
    """从文本中提取所有 (value, unit, context_sentence) 三元组。

    可用于数值验证器在文献中搜索相似数值范围。

    Args:
        text: 文献或假设文本
        unit_patterns: 可选的单位过滤列表（如 ["kj/mol", "mmol/g"]），
                       为 None 时不过滤，提取所有单位类型。

    Returns:
        List of dicts, each containing:
            - value: float — 数值
            - unit: str — 归一化后的单位
            - raw_text: str — 原始匹配文本
            - context_sentence: str — 匹配所在的句子/片段（最多200字符）
            - start_pos: int — 在原文中的起始位置
    """
    if unit_patterns is not None:
        unit_patterns = [u.lower().strip() for u in unit_patterns]

    results = []
    for m in _VALUE_UNIT_RE.finditer(text):
        value = float(m.group(1))
        raw_unit = m.group(2)
        unit_norm = _normalize_unit(raw_unit)

        # 单位过滤
        if unit_patterns is not None and unit_norm not in unit_patterns:
            continue

        # 过滤不合理数值
        if value <= 0 or value > 1e8:
            continue

        # 过滤纯数字上下文误匹配（K/h/min 需要上下文验证）
        if unit_norm in ("k", "h", "min"):
            ctx_start = max(0, m.start() - 30)
            ctx_end = min(len(text), m.end() + 30)
            ctx = text[ctx_start:ctx_end]
            if unit_norm == "k" and not re.search(
                r'温度|[Tt]emp|吸附|反应|开[尔文]|kelvin', ctx
            ):
                continue
            if unit_norm == "h" and not re.search(
                r'[Hh]our|[Hh]rs?|小时|[Tt]ime|暴露|时间', ctx
            ):
                continue
            if unit_norm == "min" and not re.search(
                r'[Mm]inute|分钟|[Tt]ime|暴露|时间', ctx
            ):
                continue

        # 提取上下文句子
        ctx_start = max(0, m.start() - 100)
        ctx_end = min(len(text), m.end() + 150)
        context_raw = text[ctx_start:ctx_end].strip()

        # 尝试按句子边界截断
        sentence_breaks = ['. ', '.\n', '。', '\n\n', '; ']
        best_start = context_raw
        for sep in sentence_breaks:
            if sep in context_raw[:100]:
                last_sep = context_raw[:100].rfind(sep)
                if last_sep > 10:
                    best_start = context_raw[last_sep + len(sep):]
                    break
        best_end = best_start
        for sep in sentence_breaks:
            if sep in best_start[60:]:
                first_sep = best_start[60:].find(sep)
                if 0 < first_sep < 200:
                    best_end = best_start[:60 + first_sep]
                    break
        context_sentence = (best_end or best_start)[:200].strip()

        results.append({
            "value": value,
            "unit": unit_norm,
            "raw_text": m.group(0).strip(),
            "context_sentence": context_sentence,
            "start_pos": m.start(),
        })

    return results


# ═══════════════════════════════════════════════════════════════
# (x, y) Numerical Pair Extraction — 从文献文本提取数值对用于模型对比
# ═══════════════════════════════════════════════════════════════

# 单位 → 物理类别映射（用于判断 x 与 y 单位是否同类，避免把两个 y 值配对）
_UNIT_CATEGORY = {
    "k": "temperature", "kelvin": "temperature", "kelvins": "temperature",
    "°c": "temperature", "℃": "temperature", "°f": "temperature",
    "bar": "pressure", "kpa": "pressure", "mpa": "pressure",
    "atm": "pressure", "pa": "pressure", "torr": "pressure",
    "mmol/g": "capacity", "mmol/cm3": "capacity", "mol/kg": "capacity",
    "mg/g": "capacity", "cm3/g": "capacity", "m2/g": "surface_area",
    "kj/mol": "energy", "ev": "energy",
    "h": "time", "hr": "time", "min": "time", "s": "time",
    "%": "ratio", "wt%": "ratio", "ppm": "ratio",
}

# 宽松单位归一化：处理 g-1 / cm-3 / mol-1 等文献常见写法
# 注意：使用 ASCII 边界 (?![A-Za-z0-9]) 而非 \b，
#       因为 Python re 默认 Unicode 模式下 \b 会把中文当词字符，
#       导致 "273 K 下" 这类中文语境无法匹配单位。
_XY_UNIT_TOKEN = (
    r'(?:'
    r'[°◦˚]\s*[cCkKfF](?![A-Za-z0-9])|℃(?![A-Za-z0-9])|kelvins?(?![A-Za-z0-9])|'
    r'kj\s*/\s*mol(?![A-Za-z0-9])|kj\s*mol-?1?(?![A-Za-z0-9])|'
    r'mmol\s*/\s*g(?![A-Za-z0-9])|mmol\s*/\s*cm3(?![A-Za-z0-9])|'
    r'mmol\s*cm-?3(?![A-Za-z0-9])|'
    r'mol\s*/\s*kg(?![A-Za-z0-9])|'
    r'mg\s*/\s*g(?![A-Za-z0-9])|m2\s*/\s*g(?![A-Za-z0-9])|cm3\s*/\s*g(?![A-Za-z0-9])|'
    r'wt\s*%|'
    r'kpa(?![A-Za-z0-9])|mpa(?![A-Za-z0-9])|atm(?![A-Za-z0-9])|'
    r'bar(?![A-Za-z0-9])|torr(?![A-Za-z0-9])|pa(?![A-Za-z0-9])|'
    r'k(?![A-Za-z0-9])|hr(?![A-Za-z0-9])|h(?![A-Za-z0-9])|'
    r'min(?![A-Za-z0-9])|s(?![A-Za-z0-9])|ev(?![A-Za-z0-9])|ppm(?![A-Za-z0-9])|%'
    r')'
)

# 范围式数值（from 5.0 to 3.2 mmol/g / 300–500 K / 5.0-3.2 mmol/g）
_XY_RANGE_RE = re.compile(
    r'(?<![\d.])(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(?:to|[-–—~])\s*'
    r'(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(' + _XY_UNIT_TOKEN + r')',
    re.IGNORECASE,
)
# 单值+单位
_XY_UNIT_RE = re.compile(
    r'(?<![\d.])(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(' + _XY_UNIT_TOKEN + r')',
    re.IGNORECASE,
)

# 句子切分：中文句号/感叹/问号/分号、换行，以及英文句点后跟大写
_SENT_SPLIT_RE = re.compile(r'[。！？!?；;\n]+|(?<=[.])\s+(?=[A-Z0-9])')

# Markdown 表格行 / 分隔行
_TABLE_ROW_RE = re.compile(r'^\s*\|.*\|\s*$')
_TABLE_SEP_RE = re.compile(r'^\s*\|[\s:\-|]+\|\s*$')
_CELL_NUM_RE = re.compile(r'[-+]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?')

# 表头黑名单列（年份/文献编号等非量值列）
_HEADER_BLACKLIST_RE = re.compile(
    r'year|年份|ref(?:erence)?\b|doi|编号|文献|entry\b', re.IGNORECASE)


def _normalize_unit_loose(raw_unit: str) -> str:
    """宽松单位归一化：处理 g-1、cm-3、mol-1 等文献常见写法后再走标准归一化。"""
    u = raw_unit.strip()
    u = u.replace('−', '-').replace('–', '-')
    u = re.sub(r'\b(g)\s*[-]?\s*1\b', 'g', u)
    u = re.sub(r'\b(cm)\s*[-]?\s*3\b', 'cm3', u)
    u = re.sub(r'\b(mol)\s*[-]?\s*1\b', 'mol', u)
    u = re.sub(r'\bkj\s*[-]?\s*mol\b', 'kj/mol', u)
    u = re.sub(r'\bmmol\s*[-]?\s*(?:/\s*)?(g|cm3)\b', r'mmol/\1', u)
    u = re.sub(r'\b(mol)\s*[-]?\s*(?:/\s*)?kg\b', 'mol/kg', u)
    u = re.sub(r'\b(mg|m2|cm3)\s*[-]?\s*(?:/\s*)?g\b', r'\1/g', u)
    u = re.sub(r'\bwt\s*%\b', 'wt%', u)
    return _normalize_unit(u)


def _unit_category(unit_norm: str) -> str:
    """返回单位所属物理类别；未知单位按自身字符串视为独立类别。"""
    return _UNIT_CATEGORY.get(unit_norm, unit_norm)


def _norm_patterns(patterns: Optional[List[str]]) -> Optional[Set[str]]:
    """归一化用户传入的单位过滤列表；None 表示不过滤。"""
    if patterns is None:
        return None
    out = set()
    for p in patterns:
        if p and str(p).strip():
            out.add(_normalize_unit_loose(str(p)))
    return out if out else None


def _find_value_units(text: str) -> List[Tuple[float, str, int]]:
    """在文本中提取 (value, unit_norm, start_pos) 三元组（按出现顺序）。

    范围式写法（"from 5.0 to 3.2 mmol/g"、"300–500 K"）会把单位传播给两端数值。
    """
    items = []
    covered = []
    for m in _XY_RANGE_RE.finditer(text):
        try:
            v1 = float(m.group(1))
            v2 = float(m.group(2))
        except ValueError:
            continue
        unit = _normalize_unit_loose(m.group(3))
        items.append((v1, unit, m.start()))
        items.append((v2, unit, m.start(2)))
        covered.append((m.start(), m.end()))
    for m in _XY_UNIT_RE.finditer(text):
        if any(s <= m.start() and m.end() <= e for s, e in covered):
            continue
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        unit = _normalize_unit_loose(m.group(2))
        items.append((v, unit, m.start()))
    items.sort(key=lambda t: t[2])
    return items


def _valid_xy_value(item: Tuple[float, str, int], sentence: str) -> bool:
    """数值过滤：0 < value < 1e6；跳过无量值语境的大整数（年份/文献编号）。"""
    v, unit, start = item
    if not (0 < v < 1e6):
        return False
    if v >= 10000 and v == int(v):
        ctx = sentence[max(0, start - 20): start + 25]
        if unit in ("k", "kelvin", "kelvins", "°c", "℃"):
            if not re.search(r'温度|[Tt]emp|[Kk]elvin|吸附|开尔文|反应', ctx):
                return False
        elif unit in ("h", "hr", "min", "s"):
            if not re.search(r'小时|[Hh]our|[Tt]ime|时间|暴露', ctx):
                return False
    return True


def _split_xy_values(
    items: List[Tuple[float, str, int]],
    x_patterns: Optional[Set[str]],
    y_patterns: Optional[Set[str]],
) -> Tuple[List[Tuple[float, str, int]], List[Tuple[float, str, int]]]:
    """把句内数值按单位过滤/类别分成 x 候选与 y 候选（保证 x、y 单位不同类）。"""
    if x_patterns is not None and y_patterns is not None:
        xs = [it for it in items if it[1] in x_patterns]
        ys = [it for it in items if it[1] in y_patterns]
        return xs, ys
    if x_patterns is not None:
        xs = [it for it in items if it[1] in x_patterns]
        x_cats = {_unit_category(it[1]) for it in xs}
        ys = [it for it in items
              if it not in xs and _unit_category(it[1]) not in x_cats]
        return xs, ys
    if y_patterns is not None:
        ys = [it for it in items if it[1] in y_patterns]
        y_cats = {_unit_category(it[1]) for it in ys}
        xs = [it for it in items
              if it not in ys and _unit_category(it[1]) not in y_cats]
        return xs, ys
    # 均不过滤：按单位类别出现顺序取前两个不同类别作为 x 类与 y 类
    cats = []
    for it in items:
        cat = _unit_category(it[1])
        if cat not in cats:
            cats.append(cat)
    if len(cats) < 2:
        return [], []
    x_cat, y_cat = cats[0], cats[1]
    xs = [it for it in items if _unit_category(it[1]) == x_cat]
    ys = [it for it in items if _unit_category(it[1]) == y_cat]
    return xs, ys


def _sentence_pairs(
    sentence: str,
    x_patterns: Optional[Set[str]],
    y_patterns: Optional[Set[str]],
) -> List[Dict[str, Any]]:
    """从单个句子提取 (x, y) 配对。

    策略优先级：sequence（句内多 x 多 y，按出现顺序对齐）
              > sentence_pair（句内恰好 1 x + 1 y）
              > cartesian（兜底笛卡尔积，每句最多 4 对）。
    """
    items = _find_value_units(sentence)
    if not items:
        return []
    items = [it for it in items if _valid_xy_value(it, sentence)]
    if not items:
        return []
    xs, ys = _split_xy_values(items, x_patterns, y_patterns)
    if not xs or not ys:
        return []
    if _unit_category(xs[0][1]) == _unit_category(ys[0][1]):
        return []
    context = sentence.strip()[:200]
    if len(xs) >= 2 and len(ys) >= 2:
        source = "sequence"
        combos = list(zip(xs, ys))
    elif len(xs) == 1 and len(ys) == 1:
        source = "sentence_pair"
        combos = [(xs[0], ys[0])]
    else:
        source = "cartesian"
        combos = [(xv, yv) for xv in xs for yv in ys][:4]
    pairs = []
    for xv, yv in combos:
        pairs.append({
            "x": xv[0], "y": yv[0],
            "x_unit": xv[1], "y_unit": yv[1],
            "context_sentence": context,
            "source": source,
        })
    return pairs


def _extract_tables(text: str) -> List[Dict[str, Any]]:
    """解析 Markdown 表格，返回 {header, rows, raw} 列表。"""
    tables = []
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if _TABLE_ROW_RE.match(line):
            block = []
            j = i
            while j < n and _TABLE_ROW_RE.match(lines[j]):
                block.append(lines[j])
                j += 1
            header = None
            rows = []
            for bl in block:
                if _TABLE_SEP_RE.match(bl):
                    continue
                cells = [c.strip() for c in bl.strip().strip('|').split('|')]
                if header is None:
                    header = cells
                else:
                    rows.append(cells)
            if header:
                tables.append({"header": header, "rows": rows, "raw": block})
            i = j
        else:
            i += 1
    return tables


def _strip_tables(text: str, tables: List[Dict[str, Any]]) -> str:
    """从文本中移除已解析的表格行，剩余部分用于句子级提取。"""
    if not tables:
        return text
    table_lines = set()
    for t in tables:
        table_lines.update(t["raw"])
    return "\n".join(ln for ln in text.splitlines() if ln not in table_lines)


def _unit_from_header(cell: str) -> Optional[str]:
    """从表头单元格解析单位，如 'T (K)'、'Capacity (mmol/g)'、'P / bar'。"""
    cell = cell.strip()
    if not cell:
        return None
    m = re.search(r'[\(（]([^()（）]*)[\)）]', cell)
    if m:
        u = m.group(1).strip()
        return _normalize_unit_loose(u) if u else None
    m = re.search(r'\s*/\s*([^\s/|]+)\s*$', cell)
    if m:
        u = m.group(1).strip()
        return _normalize_unit_loose(u) if u else None
    return None


def _parse_cell_number(cell: str) -> Optional[float]:
    """解析数据单元格中的数值（0 < v < 1e6），无数字则返回 None。"""
    m = _CELL_NUM_RE.search(cell)
    if not m:
        return None
    try:
        v = float(m.group())
    except ValueError:
        return None
    if not (0 < v < 1e6):
        return None
    return v


def _select_xy_columns(
    col_units: List[Optional[str]],
    blacklist: Set[int],
    x_patterns: Optional[Set[str]],
    y_patterns: Optional[Set[str]],
) -> Tuple[List[int], List[int]]:
    """根据单位过滤与类别规则选出 x 列与 y 列。"""
    valid = [i for i, u in enumerate(col_units)
             if u is not None and i not in blacklist]
    if x_patterns is not None and y_patterns is not None:
        x_cols = [i for i in valid if col_units[i] in x_patterns]
        y_cols = [i for i in valid if col_units[i] in y_patterns]
        return x_cols, y_cols
    if x_patterns is not None:
        x_cols = [i for i in valid if col_units[i] in x_patterns]
        x_cats = {_unit_category(col_units[i]) for i in x_cols}
        y_cols = [i for i in valid
                  if i not in x_cols and _unit_category(col_units[i]) not in x_cats]
        return x_cols, y_cols
    if y_patterns is not None:
        y_cols = [i for i in valid if col_units[i] in y_patterns]
        y_cats = {_unit_category(col_units[i]) for i in y_cols}
        x_cols = [i for i in valid
                  if i not in y_cols and _unit_category(col_units[i]) not in y_cats]
        return x_cols, y_cols
    # 均不过滤：按列顺序取前两个不同类别的列
    x_cols, y_cols = [], []
    seen_cats = set()
    for i in valid:
        cat = _unit_category(col_units[i])
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        if not x_cols:
            x_cols.append(i)
        elif not y_cols:
            y_cols.append(i)
            break
    return x_cols, y_cols


def _table_row_pairs(
    tables: List[Dict[str, Any]],
    x_patterns: Optional[Set[str]],
    y_patterns: Optional[Set[str]],
) -> List[Dict[str, Any]]:
    """从 Markdown 表格数据行提取 (x, y) 配对（source="table_row"）。"""
    pairs = []
    for t in tables:
        header = t["header"]
        col_units = [_unit_from_header(c) for c in header]
        blacklist = {i for i, c in enumerate(header)
                     if _HEADER_BLACKLIST_RE.search(c)}
        x_cols, y_cols = _select_xy_columns(
            col_units, blacklist, x_patterns, y_patterns)
        if not x_cols or not y_cols:
            continue
        if _unit_category(col_units[x_cols[0]]) == _unit_category(col_units[y_cols[0]]):
            continue
        for row in t["rows"]:
            row_vals = [_parse_cell_number(c) for c in row]
            x_vals = [(row_vals[xi], col_units[xi]) for xi in x_cols
                      if xi < len(row_vals) and row_vals[xi] is not None]
            y_vals = [(row_vals[yi], col_units[yi]) for yi in y_cols
                      if yi < len(row_vals) and row_vals[yi] is not None]
            if not x_vals or not y_vals:
                continue
            context = " | ".join(row).strip()[:200]
            if len(x_vals) == 1 and len(y_vals) == 1:
                combos = [(x_vals[0], y_vals[0])]
            else:
                combos = [(xv, yv) for xv in x_vals for yv in y_vals][:4]
            for xv, yv in combos:
                pairs.append({
                    "x": xv[0], "y": yv[0],
                    "x_unit": xv[1], "y_unit": yv[1],
                    "context_sentence": context,
                    "source": "table_row",
                })
    return pairs


def extract_xy_pairs(
    text: str,
    x_unit_patterns: Optional[List[str]] = None,
    y_unit_patterns: Optional[List[str]] = None,
    max_pairs: int = 200,
) -> List[Dict[str, Any]]:
    """从文献文本提取 (x, y) 数值配对，用于模型对比与构效关系分析。

    提取策略（按优先级）：
        a) Markdown 表格行配对（source="table_row"）：
           识别表头含单位的列（如 "T (K)"、"Capacity (mmol/g)"，单位在括号内），
           同一数据行的 x 列与 y 列数值直接配对。
        b) 句子序列配对（source="sequence"）：
           同句含多个带 x 单位的值与多个带 y 单位的值
           （如 "uptake decreased from 5.0 to 3.2 mmol/g as T increased from 300 to 500 K"），
           按出现顺序对齐配对。
        c) 句对配对（source="sentence_pair"）：
           同一段落内多个短句各含一个 x 值和一个 y 值
           （如 "At 298 K, uptake is 5.0 mmol/g."），按句提取配对。
        d) 兜底笛卡尔积（source="cartesian"）：
           同句内 x 值集合与 y 值集合笛卡尔积，每句最多 4 对。

    单位过滤：x_unit_patterns / y_unit_patterns 为 None 时不过滤（提取所有），
              否则只保留归一化后匹配的单位；x 与 y 单位必须不同类。

    数值过滤：0 < value < 1e6；跳过纯年份/文献编号（整数 > 10000 且无单位上下文的
              裸数字不参与——表头单位明确时不在此限）。

    Args:
        text: 非结构化文献文本
        x_unit_patterns: 可选 x 单位过滤列表（如 ["K"]，已支持 g-1/cm-3 等写法）
        y_unit_patterns: 可选 y 单位过滤列表（如 ["mmol/g"]）
        max_pairs: 返回配对数上限

    Returns:
        List of dicts, each containing:
            - x: float — x 轴数值
            - y: float — y 轴数值
            - x_unit: str — 归一化后的 x 单位
            - y_unit: str — 归一化后的 y 单位
            - context_sentence: str — 配对所在句子/表格行（最多200字符）
            - source: str — "table_row"|"sentence_pair"|"sequence"|"cartesian"
    """
    if not text or not text.strip():
        return []
    x_pat = _norm_patterns(x_unit_patterns)
    y_pat = _norm_patterns(y_unit_patterns)

    tables = _extract_tables(text)
    results = []
    seen = set()

    def _add(pair: Dict[str, Any]) -> bool:
        key = (pair["x"], pair["y"], pair["x_unit"],
               pair["y_unit"], pair["source"])
        if key in seen:
            return False
        seen.add(key)
        results.append(pair)
        return True

    for pair in _table_row_pairs(tables, x_pat, y_pat):
        _add(pair)
        if max_pairs is not None and len(results) >= max_pairs:
            return results

    remaining = _strip_tables(text, tables)
    for sent in _SENT_SPLIT_RE.split(remaining):
        sent = sent.strip()
        if not sent:
            continue
        for pair in _sentence_pairs(sent, x_pat, y_pat):
            _add(pair)
            if max_pairs is not None and len(results) >= max_pairs:
                return results
    return results


# ═══════════════════════════════════════════════════════════════
# 模块级自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    # Windows GBK 控制台打印 ²/°C/✓ 等 Unicode 会 UnicodeEncodeError：统一 UTF-8 输出
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
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
    _pairs = extract_xy_pairs(sample_text)
    _by_source: Dict[str, int] = defaultdict(int)
    for _p in _pairs:
        _by_source[_p["source"]] += 1

    print("=== extract_xy_pairs 自测 ===")
    print(f"共提取 {len(_pairs)} 个 (x,y) 配对")
    print("来源统计:", dict(_by_source))
    print("--- 详细结果 ---")
    print(json.dumps(_pairs, ensure_ascii=False, indent=2))
    assert _by_source.get("table_row", 0) >= 3, "表格行配对应至少 3 个"
    assert _by_source.get("sequence", 0) >= 2, "序列配对应至少 2 个"
    print("=== 自测通过: table_row>=3, sequence>=2 ===")
