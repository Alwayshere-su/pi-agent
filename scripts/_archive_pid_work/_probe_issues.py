# -*- coding: utf-8 -*-
"""抽查 3 个关键缺陷项的真实性（工具数、afac2026 硬编码、CI/pandas 版本）。"""
import io
import re

# 1) 工具数：找 tools.py 中的工具定义模式
t = io.open('pi_agent/tools.py', encoding='utf-8').read()
# 常见工具注册模式：TOOL_NAME = "xxx" 或 name="xxx" 或 register("xxx")
names = re.findall(r'name\s*=\s*["\'](\w+)["\']', t)
names2 = re.findall(r'def (\w+)_handler', t)
names3 = re.findall(r'["\']([a-z_]+)["\']\s*:\s*(?:TOOL|Handler|callable)', t)
print('name= 模式:', len(names), sorted(set(names))[:40])
print('def *_handler:', len(names2))
print('键映射模式:', len(names3))

# 2) afac2026
t2 = io.open('pi_agent/_tools_impl.py', encoding='utf-8').read()
i = t2.find('afac2026')
print('\nafac2026 位置:', i)
if i >= 0:
    print('上下文:', t2[max(0, i - 80):i + 60].replace('\n', ' '))

# 3) requirements pandas/scikit-learn
t3 = io.open('requirements.txt', encoding='utf-8').read()
print('\nrequirements 相关行:')
for l in t3.splitlines():
    if 'pandas' in l or 'scikit' in l or 'python' in l.lower():
        print(' ', l)
