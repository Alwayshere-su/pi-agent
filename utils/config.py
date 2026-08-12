"""全局配置常量"""
import os
from pathlib import Path

# 时间预算
TOTAL_BUDGET_SECONDS = 7200  # 2 小时
SAFETY_MARGIN_SECONDS = 300  # 5 分钟安全余量

# ── 随机种子与可复现性 ──
# 默认固定种子：搜索打分等确定性计算可完全复现（main.py --seed 可覆盖）。
# LLM 采样（DeepSeek）不受此约束——其采样本身不保证可复现。
SEED = 42  # 默认全局随机种子


# ═══════════════════════════════════════════════════════════════
# 多主题运行目录（run_dir 隔离）
# ═══════════════════════════════════════════════════════════════
# 默认 run_dir="survey" 与历史版本完全兼容：
#   outputs → workspace/outputs/literature_survey/
#   memory  → workspace/memory/survey/
# 传入 --run-dir <name> 后各主题的产物/记忆/checkpoint 完全隔离，
# 支持同一 Agent 在不同材料主题上并行调研（泛化性验证）。
SURVEY_DIR = os.environ.get("SURVEY_DIR", "workspace/outputs/literature_survey")
MEMORY_DIR = os.environ.get("SURVEY_MEMORY_DIR", "workspace/memory/survey")
LOGS_DIR = os.environ.get("SURVEY_LOGS_DIR", "workspace/logs")
CHECKPOINT_DIR = os.environ.get("SURVEY_CHECKPOINT_DIR", "workspace")
# 文献检索缓存目录（按 run_dir 隔离，2026-08 修复）：
#   survey（默认）→ workspace/data/literature_cache（历史路径，向后兼容已有 MOF 产物）
#   其他 run_dir  → workspace/data/literature_cache/<run_dir>/
# 隔离的对象包括 search_results.json 累积文件、scibase 论文池（papers.json/index.json）、
# arxiv / semantic_scholar 查询缓存、search_log.jsonl，避免跨主题检索结果串味。
# 可通过环境变量 LITERATURE_CACHE_DIR 覆盖基准目录（如测试/沙箱环境）。
LITERATURE_CACHE_DIR = os.environ.get(
    "LITERATURE_CACHE_DIR", "workspace/data/literature_cache"
)


def set_run_dir(run_dir: str) -> None:
    """按主题运行目录隔离 outputs / memory / logs / checkpoint / 文献缓存。

    Args:
        run_dir: 主题运行目录名。空串或 "survey" 时恢复默认（向后兼容）。
    """
    global SURVEY_DIR, MEMORY_DIR, LOGS_DIR, CHECKPOINT_DIR, LITERATURE_CACHE_DIR
    if not run_dir or run_dir == "survey":
        SURVEY_DIR = os.environ.get("SURVEY_DIR", "workspace/outputs/literature_survey")
        MEMORY_DIR = os.environ.get("SURVEY_MEMORY_DIR", "workspace/memory/survey")
        LOGS_DIR = os.environ.get("SURVEY_LOGS_DIR", "workspace/logs")
        CHECKPOINT_DIR = os.environ.get("SURVEY_CHECKPOINT_DIR", "workspace")
        LITERATURE_CACHE_DIR = os.environ.get(
            "LITERATURE_CACHE_DIR", "workspace/data/literature_cache"
        )
        return
    SURVEY_DIR = f"workspace/outputs/{run_dir}/literature_survey"
    MEMORY_DIR = f"workspace/memory/{run_dir}"
    LOGS_DIR = f"workspace/logs/{run_dir}"
    CHECKPOINT_DIR = f"workspace/checkpoint/{run_dir}"
    # Windows 路径安全：统一为正斜杠拼接（与项目内其它路径风格一致）
    LITERATURE_CACHE_DIR = os.path.join(
        os.environ.get("LITERATURE_CACHE_DIR", "workspace/data/literature_cache"),
        run_dir,
    ).replace("\\", "/")


def get_literature_cache_dir() -> str:
    """返回当前 run_dir 对应的文献缓存目录。

    向后兼容：run_dir="survey"（默认）时返回历史路径
    workspace/data/literature_cache，已有累积产物（如 MOF 主题的
    search_results.json）保持原位可继续读取；非默认 run_dir 时返回
    workspace/data/literature_cache/<run_dir>/，实现跨主题检索缓存隔离。
    """
    return LITERATURE_CACHE_DIR


def seed_everything(seed: int = SEED) -> int:
    """固定全局随机种子，保证确定性计算可复现。

    设置 random.seed 与 numpy.random.seed（numpy 缺失时自动跳过，不强依赖）。
    PYTHONHASHSEED 须在解释器启动前设置才生效，运行时设置无效，故仅作提示。

    Args:
        seed: 随机种子，默认取配置 SEED。

    Returns:
        实际生效的种子值。
    """
    import random

    random.seed(seed)
    try:
        import numpy as _np
        _np.random.seed(seed)
    except ImportError:
        pass  # numpy 不可用时跳过，不硬依赖
    if "PYTHONHASHSEED" not in os.environ:
        print(
            f"[seed] 随机种子已固定为 {seed}（random/numpy）。"
            "PYTHONHASHSEED 未设置——如需完全复现（含字符串哈希），"
            f"请以 PYTHONHASHSEED={seed} 启动解释器（运行时设置无效）。"
        )
    return seed

# ── API Key ──
# @external: utils/resource_registry.py → "DeepSeek API"
#   来源: https://platform.deepseek.com (商业 API, deepseek-chat, 2026-08)
#   用途: LLM 推理、假设生成、报告撰写
#   替代: vLLM 本地部署开源模型（改 DEEPSEEK_BASE_URL 即可）
# 方式1: 环境变量 DEEPSEEK_API_KEY
# 方式2: 项目根目录创建 .api_key 文件，写入 DeepSeek API Key

def _load_api_key_file() -> dict[str, str]:
    """解析 .api_key 文件，支持两种格式：
    第一行（无 =）：视为 DEEPSEEK_API_KEY（向后兼容）
    后续 KEY=VALUE 行：解析为对应环境变量
    """
    keys: dict[str, str] = {}
    key_file = Path(__file__).resolve().parent.parent / ".api_key"
    if not key_file.exists():
        return keys
    for line in key_file.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip()
        else:
            # 向后兼容：纯文本行视为 DeepSeek key
            if "DEEPSEEK_API_KEY" not in keys:
                keys["DEEPSEEK_API_KEY"] = line
    return keys


def _resolve_api_key() -> str:
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key:
        return env_key
    return _load_api_key_file().get("DEEPSEEK_API_KEY", "")

# 加载 Sciverse key（支持 SCIVERSE_API_KEY 和 SCIVERSE_API_TOKEN 两种名称）
# @external: utils/resource_registry.py → "Sciverse API"
#   来源: https://sciverse.opendatalab.com (商业 API, 2026-08)
#   用途: 跨出版商语义检索
#   替代: arXiv API + Semantic Scholar + Crossref
_SCIVERSE_KEY = (
    os.environ.get("SCIVERSE_API_KEY", "")
    or os.environ.get("SCIVERSE_API_TOKEN", "")
)
if not _SCIVERSE_KEY:
    _file_keys = _load_api_key_file()
    _SCIVERSE_KEY = (
        _file_keys.get("SCIVERSE_API_KEY", "")
        or _file_keys.get("SCIVERSE_API_TOKEN", "")
    )
if _SCIVERSE_KEY:
    os.environ.setdefault("SCIVERSE_API_KEY", _SCIVERSE_KEY)

# ── MinerU PDF 解析 API Key ──
# @external: utils/resource_registry.py → "MinerU"
#   来源: https://mineru.net (开源, Cloud/pip, 2026-08)
#   替代: markitdown + pdfplumber（本地解析，无需 API Key）
# 方式1: 环境变量 MINERU_API_KEY
# 方式2: .api_key 文件中写入 MINERU_API_KEY=your_key
# MinerU 是 OpenDataLab 的开源文档解析引擎（PDF→结构化内容），官网/注册:
#   https://mineru.net
# Cloud 端点: https://mineru.net/api/v1/agent/parse/url（见 literature_agent/parser.py）
# 本地端点:   http://localhost:8888（可用环境变量 MINERU_LOCAL_URL 覆盖）
# 说明: 设置 MINERU_API_KEY 可获得认证/配额更稳定的云解析通道；
#       未设置时 parser 也会尝试连通公开端点，但受网络与服务端配额影响，
#       全部不可用时自动回退 markitdown 本地引擎（离线、结果可复现）。

_MINERU_KEY = os.environ.get("MINERU_API_KEY", "")
if not _MINERU_KEY:
    _file_keys = _load_api_key_file()
    _MINERU_KEY = _file_keys.get("MINERU_API_KEY", "")
if _MINERU_KEY:
    os.environ.setdefault("MINERU_API_KEY", _MINERU_KEY)

MINERU_API_KEY = _MINERU_KEY
MINERU_LOCAL_URL = os.environ.get("MINERU_LOCAL_URL", "http://localhost:8888")

DEEPSEEK_API_KEY = _resolve_api_key()

# ── Materials Project API Key ──
# @external: utils/resource_registry.py → "Materials Project"
#   来源: https://materialsproject.org (开放数据库, API, 2026-08)
#   用途: DFT 结构/能量数据交叉验证
#   替代: OQMD / NOMAD
# 方式1: 环境变量 MATERIALS_PROJECT_API_KEY 或 MP_API_KEY
# 方式2: .api_key 文件中写入 MATERIALS_PROJECT_API_KEY=your_key 或 MP_API_KEY=your_key
# 注册地址: https://materialsproject.org/api

_MATERIALS_PROJECT_KEY = (
    os.environ.get("MATERIALS_PROJECT_API_KEY", "")
    or os.environ.get("MP_API_KEY", "")
    or os.environ.get("Materials_Project_API", "")
)
if not _MATERIALS_PROJECT_KEY:
    _file_keys = _load_api_key_file()
    _MATERIALS_PROJECT_KEY = (
        _file_keys.get("MATERIALS_PROJECT_API_KEY", "")
        or _file_keys.get("MP_API_KEY", "")
        or _file_keys.get("Materials_Project_API", "")
    )
if _MATERIALS_PROJECT_KEY:
    os.environ.setdefault("MATERIALS_PROJECT_API_KEY", _MATERIALS_PROJECT_KEY)

MATERIALS_PROJECT_API_KEY = _MATERIALS_PROJECT_KEY

# DeepSeek V4 Flash
# @external: utils/resource_registry.py → "DeepSeek API"
# Context window: 1M input, 384K output
# https://api-docs.deepseek.com/quick_start/pricing/
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_MAX_INPUT_TOKENS = 1_000_000   # 1M context window
DEEPSEEK_MAX_OUTPUT_TOKENS = 384_000    # 384K max output
DEEPSEEK_MAX_TOKENS = DEEPSEEK_MAX_OUTPUT_TOKENS  # 向后兼容别名
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


# ═══════════════════════════════════════════════════════════════
# Placeholder / 无效 API Key 检测
# ═══════════════════════════════════════════════════════════════

# 视为"未设置"的占位符模式
_PLACEHOLDER_PATTERNS = [
    "xxx",
    "xxxx",
    "xxxxxx",
    "your-key",
    "your-key-here",
    "your_api_key",
    "your-api-key",
    "your_api_key_here",
    "your-token",
    "your_token",
    "placeholder",
    "changeme",
    "change_me",
    "changethis",
    "todo",
    "put-your-key-here",
    "你的",        # 中文占位符前缀
    "你的key",
    "你的token",
    "sk-your-",
    "sk-xxx",
]


def _is_placeholder(value: str) -> bool:
    """检查 API Key 是否为占位符/无效值。

    返回 True 表示该值应被视为"未设置"。
    """
    if not value or not value.strip():
        return True
    v = value.strip().lower()
    for pat in _PLACEHOLDER_PATTERNS:
        if v == pat:
            return True
        # 前缀匹配（如 "sk-your-"、"你的" 开头）
        if pat.endswith("-") and v.startswith(pat):
            return True
        if pat == "你的" and v.startswith("你的"):
            return True
    return False


def _has_valid_api_key(key_name: str) -> bool:
    """检查指定的 API Key 是否已有效配置（非占位符、非空）。

    Args:
        key_name: 环境变量名，如 "DEEPSEEK_API_KEY"

    Returns:
        True 表示 Key 有效配置
    """
    value = os.environ.get(key_name, "")
    if not value:
        # 尝试从 .api_key 文件读取
        file_keys = _load_api_key_file()
        value = file_keys.get(key_name, "")
    return bool(value) and not _is_placeholder(value)


def _build_mineru_status(file_keys: dict) -> dict:
    """构建 MinerU（PDF 解析）配置状态诊断。

    MinerU 双通道：
      - 云 API（mineru.net）——设置 MINERU_API_KEY 获得认证/配额更稳定的通道；
      - 本地服务（默认 http://localhost:8888，可用 MINERU_LOCAL_URL 覆盖）。
    parser.py 在全部通道不可用时自动回退 markitdown 本地引擎（离线可复现）。
    """
    env_key = os.environ.get("MINERU_API_KEY", "")
    file_key = file_keys.get("MINERU_API_KEY", "")
    key_val = env_key or file_key
    key_ok = bool(key_val) and not _is_placeholder(key_val)
    local_url = os.environ.get("MINERU_LOCAL_URL", "http://localhost:8888")

    if env_key and not _is_placeholder(env_key):
        source = "环境变量"
        detail = f"MINERU_API_KEY 已通过环境变量配置（云 API）"
    elif file_key and not _is_placeholder(file_key):
        source = ".api_key 文件"
        detail = f"MINERU_API_KEY 已通过 .api_key 文件配置（云 API）"
    elif env_key and _is_placeholder(env_key):
        source = "环境变量(占位符)"
        detail = f"MINERU_API_KEY 为占位符值，视为未配置"
    elif file_key and _is_placeholder(file_key):
        source = ".api_key(占位符)"
        detail = f".api_key 文件中的 MINERU_API_KEY 为占位符值，视为未配置"
    else:
        source = "未配置"
        detail = (
            "MINERU_API_KEY 未设置（环境变量或 .api_key 文件）——云 API 通道未启用；"
            "parser 仍会尝试连通公开端点，受网络/配额影响，全部失败时自动回退 markitdown。"
        )
    detail += f"；本地端点: {local_url}（MINERU_LOCAL_URL 可覆盖，或 docker 部署监听 :8888）"

    return {"configured": key_ok, "key_source": source, "detail": detail}


def config_status() -> dict:
    """返回所有服务配置状态的诊断报告。

    检查所有 API Key 和服务的可用性：
      - DeepSeek API (LLM)
      - Sciverse API (文献检索)
      - MinerU (PDF 解析) — Cloud/Local/pip 三级
      - Materials Project API (材料数据)

    Returns:
        {
            "deepseek": {"configured": bool, "key_source": str, "detail": str},
            "sciverse": {"configured": bool, "key_source": str, "detail": str},
            "mineru": {"configured": bool, "key_source": str, "detail": str},
            "materials_project": {"configured": bool, "key_source": str, "detail": str},
            "summary": str,
            "all_configured": bool,
        }
    """
    file_keys = _load_api_key_file()

    def _check_key(env_name: str, global_var: str) -> dict:
        """检查单个 API Key 的配置状态"""
        env_val = os.environ.get(env_name, "")
        file_val = file_keys.get(env_name, "")

        if env_val and not _is_placeholder(env_val):
            source = "环境变量"
            detail = f"已通过环境变量 {env_name} 配置"
        elif file_val and not _is_placeholder(file_val):
            source = ".api_key 文件"
            detail = f"已通过 .api_key 文件配置 ({env_name})"
        elif env_val and _is_placeholder(env_val):
            source = "环境变量(占位符)"
            detail = f"环境变量 {env_name} 包含占位符值，视为未配置"
        elif file_val and _is_placeholder(file_val):
            source = ".api_key(占位符)"
            detail = f".api_key 文件中的 {env_name} 为占位符值，视为未配置"
        else:
            source = "未配置"
            detail = f"{env_name} 未设置（环境变量或 .api_key 文件）"

        configured = bool(global_var) and not _is_placeholder(global_var)
        return {"configured": configured, "key_source": source, "detail": detail}

    report = {
        "deepseek": _check_key("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY),
        "sciverse": _check_key("SCIVERSE_API_KEY", _SCIVERSE_KEY),
        "mineru": _build_mineru_status(file_keys),
        "materials_project": _check_key("MATERIALS_PROJECT_API_KEY", MATERIALS_PROJECT_API_KEY),
    }
    # 汇总
    all_ok = all(v["configured"] for k, v in report.items() if k not in ("all_configured", "summary"))
    report["all_configured"] = all_ok

    if all_ok:
        report["summary"] = "所有 API Key 已正确配置"
    else:
        missing = [k for k, v in report.items()
                   if k not in ("all_configured", "summary") and not v["configured"]]
        report["summary"] = f"以下 API Key 未配置或为占位符: {', '.join(missing)}"

    return report


def print_config_status() -> None:
    """打印配置状态报告（人类可读格式）。"""
    status = config_status()
    print("=" * 60)
    print("  API Key 配置状态报告")
    print("=" * 60)
    for service, info in status.items():
        if service in ("all_configured", "summary"):
            continue
        symbol = "[OK]" if info["configured"] else "[MISSING]"
        print(f"  {symbol} {service}: {info['detail']} (来源: {info['key_source']})")
    print(f"\n  汇总: {status['summary']}")
    print("=" * 60)
