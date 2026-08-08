# -*- coding: utf-8 -*-
"""
预算恢复回归测试：验证 checkpoint 恢复后时间预算按「扣减」语义工作。

背景（2026GOAI 项目 bug）：
  pi_agent/agent.py 旧恢复逻辑用 `self.budget.start_time -= budget_elapsed`
  回拨开始时间，而 BudgetTracker.elapsed() 计算的是 wall-clock 累计，语义混乱。
  实测：--budget 600 的主题第一次运行 255s 后中断，续跑后日志显示
  「已用 865s / 总计 600s，剩余 0s」——Agent 累计运行远超预算才强制收尾。

本测试独立可运行（无需 pytest）：
    python -X utf8 scripts/budget_resume_test/test_budget_resume.py

覆盖点：
  1. 首次运行已用 X 秒 → 保存 checkpoint（budget_elapsed=X）；
  2. 恢复（新 tracker + set_accrued）后 remaining == total_budget - X；
  3. 恢复后 elapsed == X + 本次运行墙钟时间（不重复累计、不丢时间）；
  4. 预算耗尽后 must_stop_now() 触发，强制收尾拦截逻辑拦截「继续探索」类
     工具、放行收尾类工具（默认无 checkpoint 行为不变）。
"""
import os
import sys
import tempfile

# 把项目根目录加入 sys.path，保证脚本可从任意目录独立运行
_PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

import utils.budget_tracker as _bt_mod
from pi_agent.agent import (
    _WRAPUP_ALLOWED_TOOLS,
    _ResumableBudgetTracker,
    _budget_wrapup_hook_impl,
)
from pi_agent.session import SessionManager


class _FakeClock:
    """可手动推进的假时钟，避免测试真实等待数百秒。"""

    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _install_fake_clock():
    """替换 utils.budget_tracker 模块内的 time.time，返回可推进的假时钟。"""
    fake = _FakeClock()
    _bt_mod.time.time = fake
    return fake


def _restore_real_clock():
    _bt_mod.time.time = __import__("time").time


def test_resume_remaining():
    """恢复后 remaining == total - elapsed，elapsed 按累计语义增长且不超支。"""
    fake = _install_fake_clock()
    try:
        total = 600
        # ── 首次运行：已用 255s ──
        tr = _ResumableBudgetTracker(total_budget=total)
        tr.start()
        fake.advance(255)
        assert abs(tr.elapsed() - 255) < 1e-6, f"首次运行已用时间应为 255s，实际 {tr.elapsed()}"

        # 首次运行结束时保存 checkpoint（budget_elapsed）
        ckpt_elapsed = tr.elapsed()

        # ── 恢复：新 tracker（模拟新进程）注入已消耗时间 ──
        tr2 = _ResumableBudgetTracker(total_budget=total)
        tr2.start()
        tr2.set_accrued(ckpt_elapsed)

        # 恢复瞬间：剩余预算 = 总预算 - 已用
        assert abs(tr2.elapsed() - 255) < 1e-6
        assert abs(tr2.remaining() - (total - 255)) < 1e-6, \
            f"恢复后剩余预算应为 {total - 255}，实际 {tr2.remaining()}"

        # ── 续跑 100s：elapsed = 255 + 100，remaining = 600 - 355 ──
        fake.advance(100)
        assert abs(tr2.elapsed() - 355) < 1e-6, f"恢复后续跑 elapsed 应为 355，实际 {tr2.elapsed()}"
        assert abs(tr2.remaining() - 245) < 1e-6
        assert not tr2.must_stop_now()  # 245 - 60(安全余量) > 0

        # ── 续跑直到预算耗尽：must_stop_now 必须及时触发（强制收尾机制生效） ──
        fake.advance(200)  # elapsed=555, remaining=45，已低于安全余量 60
        assert tr2.must_stop_now(), "预算耗尽后 must_stop_now() 应触发（及时强制收尾）"
        fake.advance(300)  # elapsed=855：继续运行也保持 must_stop_now，remaining 钳制为 0
        assert tr2.must_stop_now()
        assert tr2.remaining() == 0.0

        # ── 默认（无 checkpoint）行为不变：accrued=0，与原 BudgetTracker 一致 ──
        tr3 = _ResumableBudgetTracker(total_budget=total)
        tr3.start()
        fake.advance(10)
        assert abs(tr3.elapsed() - 10) < 1e-6
        assert abs(tr3.remaining() - (total - 10)) < 1e-6
        assert abs(tr3.budget_used_pct() - (10 / total * 100)) < 1e-6
    finally:
        _restore_real_clock()


def test_checkpoint_roundtrip():
    """通过 SessionManager 完成 存 checkpoint → 恢复 的完整往返。"""
    fake = _install_fake_clock()
    tmpdir = tempfile.mkdtemp(prefix="budget_resume_ckpt_")
    try:
        total = 600
        sm = SessionManager("survey", checkpoint_dir=tmpdir)

        # 首次运行：迭代 3 轮后中断（已用 255s），保存 checkpoint
        tr = _ResumableBudgetTracker(total_budget=total)
        tr.start()
        fake.advance(255)
        ckpt_elapsed = tr.elapsed()
        ok = sm.save(
            iteration=3, messages=[{"role": "user", "content": "test"}],
            budget_elapsed=ckpt_elapsed, trajectory=[{"round": 1}],
            experiments_completed=1,
        )
        assert ok, "checkpoint 保存失败"
        assert sm.exists()

        # 恢复：模拟不带 --fresh 重新运行（新进程读取 checkpoint）
        data = sm.load()
        assert data is not None, "checkpoint 加载失败"
        tr2 = _ResumableBudgetTracker(total_budget=total)
        tr2.start()
        tr2.set_accrued(data.get("budget_elapsed", 0))
        assert abs(tr2.remaining() - (total - 255)) < 1e-6, \
            f"恢复后 remaining 应等于 total - budget_elapsed（255），实际 {tr2.remaining()}"

        # 继续运行到预算耗尽，强制收尾在正确时点触发
        fake.advance(245)  # elapsed=500, remaining=100 > 安全余量 60 → 未到强制线
        assert not tr2.must_stop_now()
        fake.advance(60)   # elapsed=560, remaining=40 < 安全余量 60 → 强制收尾
        assert tr2.must_stop_now()
    finally:
        sm.delete()  # 清理临时 checkpoint（不动 workspace/ 产物）
        _restore_real_clock()


def test_wrapup_hook_blocks_exploration():
    """预算耗尽后：探索类工具被拦截、收尾类工具放行；预算未耗尽不拦截。"""
    fake = _install_fake_clock()
    try:
        tr = _ResumableBudgetTracker(total_budget=600)
        tr.start()
        fake.advance(600)  # 预算已耗尽
        assert tr.must_stop_now()

        # 探索类工具：必须被拦截并给出明确提示
        for name in ("search_papers", "start_shell", "run_shell",
                     "parse_paper", "extract_knowledge", "analyze_gaps"):
            msg = _budget_wrapup_hook_impl(tr, name)
            assert msg is not None and "已耗尽" in msg, f"探索类工具 {name} 应被拦截"
            assert name not in _WRAPUP_ALLOWED_TOOLS

        # 探索/验证/建模类工具（超支根源）：预算耗尽后拒绝
        for name in ("run_discovery_search", "validate_discovery",
                     "run_model_comparison", "symbolic_regression"):
            msg = _budget_wrapup_hook_impl(tr, name)
            assert msg is not None and "预算已耗尽" in msg, f"{name} 应被拦截"
            assert name not in _WRAPUP_ALLOWED_TOOLS, f"{name} 不应在放行名单"

        # 一次性报告生成（路线 A 发现报告，必交产物）：预算耗尽后放行
        for name in ("generate_discovery_report", "generate_report"):
            assert name in _WRAPUP_ALLOWED_TOOLS, f"{name} 应在放行名单"
            assert _budget_wrapup_hook_impl(tr, name) is None, f"{name} 应放行"

        # 收尾类工具：全部放行
        for name in _WRAPUP_ALLOWED_TOOLS:
            assert _budget_wrapup_hook_impl(tr, name) is None, f"收尾类工具 {name} 应放行"

        # 预算未耗尽：不拦截任何工具
        tr3 = _ResumableBudgetTracker(total_budget=600)
        tr3.start()
        fake.advance(10)
        assert _budget_wrapup_hook_impl(tr3, "search_papers") is None
        assert _budget_wrapup_hook_impl(tr3, "stop") is None
    finally:
        _restore_real_clock()


def main():
    tests = [
        ("恢复后 remaining == total - elapsed 且累计不超支", test_resume_remaining),
        ("SessionManager 存 checkpoint → 恢复 完整往返", test_checkpoint_roundtrip),
        ("预算耗尽后强制收尾拦截（探索拦截 / 收尾放行）", test_wrapup_hook_blocks_exploration),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {name}\n     断言失败: {e}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {name}\n     异常: {type(e).__name__}: {e}")

    total = len(tests)
    if failed:
        print(f"\n结果: {total - failed}/{total} 通过，{failed} 失败 ❌")
        sys.exit(1)
    print(f"\n结果: 全部 {total} 项通过 ✅")
    sys.exit(0)


if __name__ == "__main__":
    main()
