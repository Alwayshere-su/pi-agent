# -*- coding: utf-8 -*-
"""p# DOI 回填工具：读确认文件（每行 `p#:DOI`），批量补注到 gap_report。

用法：
    1. 在 workspace/_pid_confirmed.txt 中写入已人工确认的条目（每行一个）：
       p20:10.61511/eam.v2i2.2024.1431
       p62:10.1016/j.efmat.2023.01.002
    2. python scripts/_backfill_pid_dois.py
    3. 脚本只对确认文件中列出的 p# 补注（p#（DOI: xxx）），其余保持原样。
"""
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAP = ROOT / 'workspace/outputs/literature_survey/gap_report.md'
CONF = ROOT / 'workspace/_pid_confirmed.txt'

if not CONF.exists():
    print('[提示] 未找到确认文件 %s，已创建模板（请填入确认条目后重跑）' % CONF)
    CONF.write_text('# 每行一个：p#:DOI（人工打开原文确认后填写）\n# p20:10.61511/eam.v2i2.2024.1431\n', encoding='utf-8')
    raise SystemExit(0)

confirmed = {}
for line in CONF.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    m = re.match(r'p(\d+)\s*[:：]\s*(10\.\d{4,}[^\s]*)', line)
    if m:
        confirmed[m.group(1)] = m.group(2)

if not confirmed:
    print('[提示] 确认文件无有效条目，退出')
    raise SystemExit(0)

text = io.open(GAP, encoding='utf-8').read()
backup = str(GAP) + '.bak'
io.open(backup, 'w', encoding='utf-8').write(text)
print('[备份]', backup)


def annotate(m):
    pid = m.group(1)
    tail = text[m.end():m.end() + 30]
    if re.search(r'10\.\d{4,}', tail):
        return m.group(0)
    doi = confirmed.get(pid)
    if not doi:
        return m.group(0)
    return m.group(0) + '（DOI: %s）' % doi


new_text, n = re.subn(r'\bp(\d+)\b', annotate, text)
io.open(GAP, 'w', encoding='utf-8').write(new_text)

# 统计
occ = len(re.findall(r'\bp\d+\b', new_text))
n_doi = sum(1 for mm in re.finditer(r'\bp(\d+)\b', new_text)
            if re.search(r'10\.\d{4,}', new_text[mm.end():mm.end() + 40]))
print('回填完成：确认条目 %d 条，处理 %d 处 | 现 p# 带 DOI: %d/%d（%.0f%%）' % (
    len(confirmed), n, n_doi, occ, 100 * n_doi / occ))
print('未在确认文件中的 p# 保持原样（如需全部闭环请补全 %s）' % CONF)
