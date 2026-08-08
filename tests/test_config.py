"""
测试 utils.config 模块：
  - _is_placeholder：占位符检测
  - set_run_dir：run_dir 默认恢复 vs 自定义
  - seed_everything：随机种子固定
"""
import pytest
import os
import random

from utils.config import (
    _is_placeholder,
    set_run_dir,
    seed_everything,
    SURVEY_DIR,
    MEMORY_DIR,
    LOGS_DIR,
    CHECKPOINT_DIR,
    LITERATURE_CACHE_DIR,
)


# ═══════════════════════════════════════════════════════════════
# _is_placeholder
# ═══════════════════════════════════════════════════════════════

class TestIsPlaceholder:
    def test_none_or_empty(self):
        """None 或空字符串返回 True。"""
        assert _is_placeholder(None) is True
        assert _is_placeholder("") is True
        assert _is_placeholder("   ") is True

    def test_xxx_patterns(self):
        """xxx/xxxx/xxxxxx 返回 True。"""
        assert _is_placeholder("xxx") is True
        assert _is_placeholder("xxxx") is True
        assert _is_placeholder("xxxxxx") is True

    def test_your_key_patterns(self):
        """'your-key-here' 类占位符返回 True。"""
        assert _is_placeholder("your-key") is True
        assert _is_placeholder("your-key-here") is True
        assert _is_placeholder("your_api_key") is True
        assert _is_placeholder("your-api-key") is True
        assert _is_placeholder("your_api_key_here") is True

    def test_your_token_patterns(self):
        """'your-token' 类占位符返回 True。"""
        assert _is_placeholder("your-token") is True
        assert _is_placeholder("your_token") is True

    def test_placeholder_patterns(self):
        """placeholder/changeme 等返回 True。"""
        assert _is_placeholder("placeholder") is True
        assert _is_placeholder("changeme") is True
        assert _is_placeholder("change_me") is True
        assert _is_placeholder("changethis") is True

    def test_todo(self):
        """'todo' 返回 True。"""
        assert _is_placeholder("todo") is True

    def test_put_your_key_here(self):
        """'put-your-key-here' 返回 True。"""
        assert _is_placeholder("put-your-key-here") is True

    def test_chinese_placeholders(self):
        """中文占位符前缀检测。"""
        assert _is_placeholder("你的") is True
        assert _is_placeholder("你的key") is True
        assert _is_placeholder("你的token") is True
        assert _is_placeholder("你的api密钥") is True  # 前缀"你的"匹配

    def test_sk_prefix_patterns(self):
        """'sk-your-' / 'sk-xxx' 匹配。"""
        assert _is_placeholder("sk-your-") is True
        assert _is_placeholder("sk-your-abc123") is True  # starts with "sk-your-"
        assert _is_placeholder("sk-xxx") is True

    def test_valid_key_is_not_placeholder(self):
        """真实 API Key 格式不应被检测为占位符。"""
        assert _is_placeholder("sk-abc123def456") is False
        assert _is_placeholder("abc123def456ghi789") is False
        assert _is_placeholder("a1b2c3d4e5f6") is False

    def test_case_insensitive(self):
        """大小写不敏感。"""
        assert _is_placeholder("XXX") is True
        assert _is_placeholder("Your-Key-Here") is True
        assert _is_placeholder("CHANGEME") is True
        assert _is_placeholder("TODO") is True

    def test_partial_match_not_triggered(self):
        """不应因为子串匹配而误判。'oxxx' 不应通过 'xxx' 模式匹配。"""
        # "oxxx" != "xxx"（精确匹配不触发）
        assert _is_placeholder("oxxx") is False
        # "my-key" 不匹配任何占位符
        # "my-key" 不是 "your-key"、也不是 "your-key-here"
        assert _is_placeholder("my-key") is False


# ═══════════════════════════════════════════════════════════════
# set_run_dir
# ═══════════════════════════════════════════════════════════════

class TestSetRunDirDefault:
    def test_empty_string_restores_default(self):
        """run_dir="" 恢复默认路径。"""
        # 先设一个自定义值
        set_run_dir("custom_topic")
        # 再恢复默认
        set_run_dir("")
        from utils import config
        assert config.SURVEY_DIR == "workspace/outputs/literature_survey"
        assert config.MEMORY_DIR == "workspace/memory/survey"
        assert config.LOGS_DIR == "workspace/logs"
        assert config.CHECKPOINT_DIR == "workspace"

    def test_survey_restores_default(self):
        """run_dir="survey" 恢复默认路径（向后兼容）。"""
        set_run_dir("custom_topic")
        set_run_dir("survey")
        from utils import config
        assert "literature_survey" in config.SURVEY_DIR

    def teardown_method(self):
        """每个测试后恢复默认 run_dir。"""
        set_run_dir("")


class TestSetRunDirCustom:
    def test_custom_run_dir_changes_paths(self):
        """自定义 run_dir 改变所有路径。"""
        set_run_dir("MOF_CO2")
        from utils import config
        assert "MOF_CO2" in config.SURVEY_DIR
        assert "MOF_CO2" in config.MEMORY_DIR
        assert "MOF_CO2" in config.LOGS_DIR
        assert "MOF_CO2" in config.CHECKPOINT_DIR

    def test_custom_literature_cache_isolation(self):
        """自定义 run_dir 时文献缓存路径隔离。"""
        set_run_dir("test_topic")
        from utils import config
        assert "test_topic" in config.LITERATURE_CACHE_DIR

    def test_custom_run_dir_specific_paths(self):
        """验证具体路径格式。"""
        set_run_dir("perovskite")
        from utils import config
        assert config.SURVEY_DIR == "workspace/outputs/perovskite/literature_survey"
        assert config.MEMORY_DIR == "workspace/memory/perovskite"
        assert config.LOGS_DIR == "workspace/logs/perovskite"
        assert config.CHECKPOINT_DIR == "workspace/checkpoint/perovskite"

    def teardown_method(self):
        """每个测试后恢复默认 run_dir。"""
        set_run_dir("")


# ═══════════════════════════════════════════════════════════════
# seed_everything
# ═══════════════════════════════════════════════════════════════

class TestSeedEverything:
    def test_returns_seed_value(self):
        """返回传入的种子值。"""
        result = seed_everything(42)
        assert result == 42

    def test_random_reproducibility(self):
        """固定种子后 random 可复现。"""
        seed_everything(42)
        seq1 = [random.random() for _ in range(5)]

        seed_everything(42)
        seq2 = [random.random() for _ in range(5)]

        assert seq1 == seq2

    def test_different_seeds_different_sequences(self):
        """不同种子产生不同随机序列。"""
        seed_everything(42)
        seq1 = [random.random() for _ in range(10)]

        seed_everything(123)
        seq2 = [random.random() for _ in range(10)]

        assert seq1 != seq2

    def test_default_seed(self):
        """不传参数时使用配置默认值 SEED=42。"""
        result = seed_everything()
        assert result == 42

    def test_custom_seed(self):
        """自定义种子。"""
        result = seed_everything(999)
        assert result == 999

    def test_numpy_seed_set(self):
        """numpy 随机种子也被固定（如果 numpy 可用）。"""
        seed_everything(42)
        try:
            import numpy as np
            np_seq1 = list(np.random.rand(5))
            seed_everything(42)
            np_seq2 = list(np.random.rand(5))
            assert np_seq1 == np_seq2
        except ImportError:
            pytest.skip("numpy not available")

    def test_zero_seed(self):
        """种子 0 也正常工作。"""
        result = seed_everything(0)
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
