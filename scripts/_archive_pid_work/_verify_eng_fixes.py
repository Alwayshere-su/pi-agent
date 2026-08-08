# -*- coding: utf-8 -*-
"""验证三项工程化修改。"""
import io
import glob
import re

# 1) CI matrix
t = io.open('.github/workflows/ci.yml', encoding='utf-8').read()
print('CI matrix:', re.search(r'python-version: (\[.*?\])', t).group(1))

# 2) afac2026 残留
hits = []
for p in glob.glob('pi_agent/*.py') + glob.glob('literature_agent/*.py') + glob.glob('utils/*.py') + glob.glob('scripts/*.py') + glob.glob('*.py'):
    s = io.open(p, encoding='utf-8', errors='ignore').read()
    if 'afac2026' in s:
        hits.append(p)
print('afac2026 残留:', hits if hits else '无 ✓')

# 3) python-docx 依赖
r = io.open('requirements.txt', encoding='utf-8').read()
p = io.open('pyproject.toml', encoding='utf-8').read()
print('requirements 含 python-docx:', 'python-docx' in r, '| pyproject 含:', 'python-docx' in p)
r_pkgs = set(re.findall(r'^([a-zA-Z0-9_.\-]+)==', r, re.M))
p_pkgs = set(re.findall(r'"([a-zA-Z0-9_.\-]+)>', p))
print('依赖集合差异 → 仅 requirements:', sorted(r_pkgs - p_pkgs) or '无')
print('              → 仅 pyproject:', sorted(p_pkgs - r_pkgs) or '无')
