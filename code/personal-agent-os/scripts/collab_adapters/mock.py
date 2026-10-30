"""mock adapter：不启动真实进程，只返回结构化测试结果。"""
from __future__ import annotations

from typing import Any

from collab_adapters.base import BaseAdapter


class MockAdapter(BaseAdapter):
    name = "mock"

    def can_wake(self) -> tuple[bool, str]:
        return True, "mock adapter always ready"

    def wake(
        self,
        *,
        target_session_id: str,
        request_id: str,
        wake_prompt: str,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "pid": None,
            "detail": (
                f"mock wake target={target_session_id} "
                f"request={request_id} prompt={wake_prompt}"
            ),
        }
