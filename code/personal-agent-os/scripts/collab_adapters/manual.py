"""manual adapter：不自动唤醒，等待人类唤醒目标 Agent。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from collab_adapters.base import BaseAdapter


class ManualAdapter(BaseAdapter):
    name = "manual"
    trigger_mode = "manual"

    def can_wake(self) -> tuple[bool, str]:
        return False, "manual adapter：该 Runtime 由人类唤醒"

    def wake(
        self,
        *,
        target_session_id: str,
        request_id: str,
        wake_prompt: str,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "pid": None,
            "detail": "manual adapter：该 Runtime 需要人类唤醒",
        }
