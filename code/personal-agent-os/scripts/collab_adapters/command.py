"""command adapter：按配置好的参数列表启动一个命令，shell=False。

这正是“Adapter 决定怎么唤醒”，Watcher 不关心具体 Runtime。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from collab_adapters.base import BaseAdapter

ALLOWED_PLACEHOLDERS = {"{native_session_id}", "{wake_prompt}"}


def _extract_placeholders(template: list[str]) -> set[str]:
    found: set[str] = set()
    for arg in template:
        start = 0
        while True:
            left = arg.find("{", start)
            if left < 0:
                break
            right = arg.find("}", left + 1)
            if right < 0:
                found.add(arg[left:])
                break
            found.add(arg[left:right + 1])
            start = right + 1
    return found


class CommandAdapter(BaseAdapter):
    name = "command"

    def can_wake(self) -> tuple[bool, str]:
        template = self.cfg.get("command_template")
        if not isinstance(template, list) or not template:
            return False, "command_template 必须是非空参数列表"
        if not all(isinstance(item, str) and item for item in template):
            return False, "command_template 每项都必须是文本"
        first = str(template[0])
        exe = Path(first)
        if exe.is_absolute():
            if not exe.is_file():
                return False, f"可执行入口未找到：{first}"
        else:
            from shutil import which

            resolved = which(first)
            if resolved is None:
                return False, f"可执行入口未找到：{first}"
        placeholders = _extract_placeholders(template)
        invalid = sorted(placeholders - ALLOWED_PLACEHOLDERS)
        if invalid:
            return False, f"command_template 含不支持的占位符：{invalid[0]}"
        if "{native_session_id}" in placeholders and not str(
            self.cfg.get("native_session_id", "")
        ).strip():
            return False, "command_template 使用 native_session_id，但配置值为空"
        cwd = self.cfg.get("cwd")
        if cwd and not Path(str(cwd)).is_dir():
            return False, f"cwd 不存在或不是目录：{cwd}"
        return True, "command adapter ready"

    def wake(
        self,
        *,
        target_session_id: str,
        request_id: str,
        wake_prompt: str,
    ) -> dict[str, Any]:
        template = [str(item) for item in self.cfg["command_template"]]
        native_session_id = str(self.cfg.get("native_session_id", ""))
        args = [
            arg.replace("{native_session_id}", native_session_id).replace("{wake_prompt}", wake_prompt)
            for arg in template
        ]
        env = dict(os.environ)
        extra_env = self.cfg.get("env")
        if isinstance(extra_env, dict):
            env.update({str(k): str(v) for k, v in extra_env.items()})
        cwd = str(self.cfg.get("cwd") or "") or None
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True, "pid": process.pid, "detail": f"started pid={process.pid} command={args}"}
