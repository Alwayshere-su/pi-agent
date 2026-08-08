# -*- coding: utf-8 -*-
"""更新 p# 最终核验清单（v2）：整合用户 doi.org 解析结果 + 新候选 + p118/p27 同篇。"""
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# p# -> (最终候选 DOI, 判定, 说明, 状态)
ROWS = [
    ('16',  '10.1021/acsestengg.4c00503', '高置信', 'Humidity Effects on DAC with Amine-Functionalized MOFs', 'DOI 有效（403 反爬，落地 URL 正确）'),
    ('20',  '10.61511/eam.v2i2.2024.1431', '高置信', 'Amine-modified Ni-DOBDC MOF CO2 capacity（Ni-DOBDC=Ni-MOF-74）', 'DOI 落地 200，标题可读'),
    ('52',  '10.1021/acs.iecr.5c04931', '强吻合(换)', 'PSA 捕集技术经济+能耗（Karimi）｜备选 10.1021/acsami.3c04079', 'DOI 落地 200，标题可读'),
    ('55',  '10.1016/j.energy.2025.135505', '弱匹配', 'energy penalty reduction low CO2 content', 'DOI 落地 200，标题可读'),
    ('54',  '10.48448/dcn4-gz78', '高置信', 'DataCite 确认：Amine-functionalized Oxide Sorbents for DAC', 'DOI 落地 200（figshare）'),
    ('60',  '10.3390/su17156796', '高置信', 'Dynamic TVSA for DAC', 'DOI 有效（403 反爬）'),
    ('62',  '10.1016/j.efmat.2023.01.002', '高置信', 'Microwave-assisted bimetallic NiCo-MOF-74', 'DOI 落地 200，标题可读'),
    ('118', '10.1016/j.jcis.2021.12.163', '高置信', 'isosteric heat of MOF-74(Ni)——⚠️ 与 p27 疑似同篇（见下）', 'DOI 落地 200，标题可读'),
    ('128', '10.3389/fmats.2022.825592', '强吻合(换)', '水导致柔性 MOF CO2 容量下降机理（Watanabe 2022）——替换原 CeO2 错误候选', 'DOI 落地 200，标题可读'),
    ('129', '10.3390/jcs5040102', '高置信', 'Isosteric Enthalpy CO2 on Micro-Mesoporous（胺化 SBA-15 Qst）', 'DOI 有效（403 反爬）'),
    ('139', '10.1021/acsomega.4c06322', '未命中强候选', '水共吸附（但体系为甲醛 Fe-HHTP-MOF，不理想）——需人工按 gap 语境定位', 'DOI 有效（403 反爬）'),
    ('168', '10.1021/acsearthspacechem.7b00142', '弱匹配', 'Water-Assisted Proton Dissociation（水解离；原 .s001 已取主 DOI）', 'DOI 有效（403 反爬）'),
    ('169', '10.1021/acs.jpcc.6b11719', '弱匹配', 'Mixed-Metal MOF Water Adsorption（原 .s001 已取主 DOI）', 'DOI 有效（403 反爬）'),
    ('185', '10.46690/capi.2023.01.02', '高置信', 'CO2 adsorption of M-MOF-74 by molecular simulation（标题完全吻合）', 'DOI 落地 200，标题可读'),
    ('188', '10.1021/acs.iecr.5b03727', '强吻合(换)', 'TSA 后燃烧捕集多柱实验（Marx 2016）｜备选 10.1021/acs.iecr.6b03887', 'DOI 落地 200，标题可读'),
]

lines = [
    '# p# 证据核验清单（v2，2026-08）',
    '',
    '> 状态已整合：① doi.org 实际解析 15/15 全部可落地（9 个 200 标题可读；6 个 403 为 ACS/MDPI 反爬，落地 URL 正确指向出版商页，DOI 有效非断链）；',
    '> ② 4 条弱匹配已重检索换候选（Crossref 复核存在）；③ p118/p27 疑似同篇待合并。',
    '> **剩余**：逐条打开原文确认身份 → 勾选 → 回填 gap_report（`p#（DOI: xxx）`）。',
    '',
    '| 状态 | p# | 候选 DOI（已核验存在） | 判定 | 说明 | 核验记录 |',
    '|------|----|----------------------|------|------|---------|',
]

for pid, doi, verdict, note, verify in ROWS:
    lines.append('| ☐ 待确认 | p%s | `%s` | %s | %s | %s |' % (pid, doi, verdict, note, verify))

lines += [
    '',
    '### ⚠️ p118/p27 疑似同篇（需人工确认）',
    '',
    '- 两 p# 均指向 `10.1016/j.jcis.2021.12.163`（Taming structure and modulating CO2 adsorption isosteric heat of MOF-74(Ni)，Lei 2022, JCIS）；',
    '- p27 提供 29 kJ/mol 甜点、p118 提供 25–40 kJ/mol 窗口——很可能同一来源被引两次；',
    '- **处理**：打开原文确认两个数值是否同出自此文 → 若是，合并为一条引用（`同 p27（DOI: …）`）。',
    '',
    '### 未决项',
    '',
    '- p139：现有候选体系不匹配（甲醛 Fe-HHTP-MOF），建议按 gap 语境（水-CO2 无竞争）人工定位或接受标【待核验】；',
    '- p16/p60/p129/p139/p168/p169：DOI 有效但出版商页反爬（403），Crossref 元数据已核验，人工确认时建议用 DOI 直链或机构访问。',
    '',
]

dst = ROOT / 'workspace/_pids_final_checklist.md'
dst.write_text('\n'.join(lines), encoding='utf-8')
print('[OK] 已更新 %s（%d 条）' % (dst, len(ROWS)))
