"""Runtime Adapter 基础接口。"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class BaseAdapter:
    name = "base"
    trigger_mode = "external"  # external | self | manual

    def __init__(self, cfg: dict[str, Any] | None = None, *, run_dir: Path | None = None):
        self.cfg = cfg or {}
        self.run_dir = run_dir

    def can_wake(self) -> tuple[bool, str]:
        """返回 (是否确信能唤醒, 原因)。不能确定时必须返回 (False, 原因)。"""
        return False, "base adapter cannot wake"

    def wake(
        self,
        *,
        target_session_id: str,
        request_id: str,
        wake_prompt: str,
    ) -> dict[str, Any]:
        """尝试唤醒一个原生会话。必须是非阻塞调用，快速返回。"""
        return {"ok": False, "pid": None, "detail": "base adapter cannot wake"}
