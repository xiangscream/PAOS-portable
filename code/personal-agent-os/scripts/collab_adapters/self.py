"""self adapter：Agent 自己轮询 PAOS / 自己配置 automation，外部 Watcher 不触发。

这是“通用化 / prompt 化”的那一类：具体怎样唤醒由 Agent 自己的配置和
automation 决定，Watcher 只避开自动触发并记录委托。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from collab_adapters.base import BaseAdapter


class SelfAdapter(BaseAdapter):
    name = "self"
    trigger_mode = "self"

    def can_wake(self) -> tuple[bool, str]:
        return False, "self：Agent 自己轮询 PAOS，外部 Watcher 不触发"

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
            "detail": "self：Agent 自行处理，外部不启动进程",
        }
