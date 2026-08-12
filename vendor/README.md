# Vendor 外部二进制文件说明

本目录存放本项目的零依赖编译工具链二进制文件（不入库，`.gitignore` 排除）。
用于在**无需安装 TeX Live/MiKTeX 发行版**的环境中编译 LaTeX → PDF。

## pandoc 3.10.1

| 项 | 说明 |
|----|------|
| **名称** | Pandoc |
| **版本** | 3.10.1 |
| **来源** | https://github.com/jgm/pandoc/releases/tag/3.10.1 |
| **用途** | Markdown → LaTeX 结构转换（`scripts/md2latex.py` / `scripts/compile_route_a_pdf.py` 调用） |
| **许可证** | GPL-2.0-or-later |
| **平台** | Windows x86_64 (pandoc-3.10.1-windows-x86_64.zip) |
| **是否必需** | 是（LaTeX 报告编译链路的核心环节；如不可用，可用系统级 pandoc 替代） |
| **使用模块** | `scripts/md2latex.py`, `scripts/compile_route_a_pdf.py` |

## tectonic 0.17.0

| 项 | 说明 |
|----|------|
| **名称** | Tectonic |
| **版本** | 0.17.0 |
| **来源** | https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.17.0 |
| **用途** | XeTeX 引擎，LaTeX → PDF 编译（替代 TeX Live 发行版） |
| **许可证** | MIT |
| **平台** | Windows x86_64 (tectonic-0.17.0-x86_64-pc-windows-msvc.zip) |
| **是否必需** | 是（提交格式要求 PDF；如不可用，可用系统 TeX Live/MiKTeX 替代） |
| **使用模块** | `scripts/compile_report.bat`, `scripts/compile_route_a_pdf.py` |
| **注册表引用** | `utils/resource_registry.py` → "TeX Live / MiKTeX"（tectonic 为轻量替代实现） |

---

## 使用说明

本目录不入库（在 `.gitignore` 中排除）。评审者如需复现 PDF 编译：

- **方案 A（推荐）**：安装系统级 TeX Live/MiKTeX + pandoc，直接使用 `compile_report.bat`
- **方案 B**：从上述 GitHub Releases 页下载对应平台二进制文件，放入本目录即可零依赖编译
