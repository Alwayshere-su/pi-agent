"""
会话管理 — Pi-Agent Layer 2
============================
支持对话状态的保存、恢复和删除操作。

相比原始 CheckpointManager，保存了恢复所需的全部状态：
消息历史、预算消耗、迭代计数、轨迹日志，而不仅仅是消息列表。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionManager:
    """
    会话持久化：保存/恢复对话 + Agent 状态。

    用法:
        sm = SessionManager("classification")
        sm.save(iteration=5, messages=[...], budget_elapsed=120.0,
                trajectory=[...], experiments_completed=3)
        data = sm.load()  # 返回 dict 或 None
    """

    def __init__(self, task_type: str, checkpoint_dir: str = "workspace"):
        self._path = Path(checkpoint_dir) / "checkpoint_survey.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ── Save ──

    def save(self, iteration: int, messages: List[Dict], budget_elapsed: float,
             best_val: float = 0.0, summary: str = "",
             trajectory: List[Dict] = None,
             experiments_completed: int = 0) -> bool:
        """Save full session state to disk."""
        try:
            data = {
                "iteration": iteration,
                "messages": messages,
                "budget_elapsed": budget_elapsed,
                "best_val": best_val,
                "summary": summary,
                "trajectory": trajectory or [],
                "experiments_completed": experiments_completed,
                "timestamp": datetime.now().isoformat(),
            }
            # 原子写（临时文件 + rename），避免中断留下半截 checkpoint
            _tmp = self._path.with_suffix(".json.tmp")
            _tmp.write_text(
                json.dumps(data, ensure_ascii=False, default=str),
                encoding="utf-8")
            os.replace(str(_tmp), str(self._path))
            return True
        except Exception as e:
            # 保存失败必须可见：静默失败会让恢复场景拿到旧 checkpoint 而困惑
            print(f"  ⚠️ [SessionManager] checkpoint 保存失败: {e}", file=sys.stderr)
            return False

    # ── Load ──

    def load(self) -> Optional[Dict]:
        """Load saved session state. Returns None if no checkpoint exists."""
        if not self._path.exists():
            return None
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as e:
            # 损坏 checkpoint：改名留档（保留证据，可人工排查），按无 checkpoint 处理
            try:
                _corrupt = self._path.with_suffix(".json.corrupt")
                os.replace(str(self._path), str(_corrupt))
                print(f"  ⚠️ [SessionManager] checkpoint 损坏已留档: {_corrupt}（{e}）",
                      file=sys.stderr)
            except OSError:
                pass
            return None

    def exists(self) -> bool:
        return self._path.exists()

    # ── Delete ──

    def delete(self) -> bool:
        """Delete the checkpoint file (called on clean completion)."""
        try:
            if self._path.exists():
                self._path.unlink()
            return True
        except OSError:
            return False


