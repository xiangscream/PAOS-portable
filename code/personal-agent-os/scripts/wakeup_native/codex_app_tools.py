"""Codex Desktop App Tools transport used by the native Wake worker."""

from __future__ import annotations

import json
import os
import struct
import uuid
from typing import Any


APP_TOOLS_PIPE_PATH_ENV = "CODEX_APP_TOOLS_PIPE_PATH"


class ActiveThreadWriter(RuntimeError):
    """The native Codex thread is still writing; defer instead of retrying."""


class CodexCallerOutOfProcessTree(RuntimeError):
    """The caller is outside the Codex Desktop process tree (pipe env absent)."""


class CodexTargetPipeRuntime(RuntimeError):
    """The app-tools pipe exists but the background runtime refused/failed."""


class DesktopPipeClient:
    def __init__(self, pipe_path: str, caller_thread_id: str):
        self.pipe_path = pipe_path
        self.caller_thread_id = caller_thread_id
        self._next_id = 1
        self._tool_namespaces: dict[str, str] | None = None

    @staticmethod
    def _read_exact(stream: Any, size: int) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = stream.read(remaining)
            if not chunk:
                raise EOFError("Codex Desktop pipe closed")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        with open(self.pipe_path, "r+b", buffering=0) as stream:
            stream.write(struct.pack("<I", len(payload)))
            stream.write(payload)
            size = struct.unpack("<I", self._read_exact(stream, 4))[0]
            response = json.loads(self._read_exact(stream, size).decode("utf-8"))
        if "error" in response:
            raise CodexTargetPipeRuntime(
                response["error"].get("message") or "Codex Desktop pipe request failed"
            )
        return response["result"]

    def _tool_namespace(self, tool_name: str) -> str:
        if self._tool_namespaces is None:
            result = self.request("tools/list", {"threadStartKind": "all"})
            tools = result.get("tools")
            if not isinstance(tools, list):
                raise CodexTargetPipeRuntime("Codex app-tools tools/list returned no tool catalog.")
            self._tool_namespaces = {
                item["name"]: item["namespace"]
                for item in tools
                if isinstance(item, dict)
                and isinstance(item.get("name"), str)
                and isinstance(item.get("namespace"), str)
            }
        namespace = self._tool_namespaces.get(tool_name)
        if not namespace:
            raise CodexTargetPipeRuntime(f"Codex app tool was not advertised: {tool_name}")
        return namespace

    def call_tool(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request(
            "tools/call",
            {
                "arguments": arguments,
                "callerSource": "codex",
                "callId": f"mcp-call-{uuid.uuid4().hex}",
                "namespace": self._tool_namespace(tool),
                "threadId": self.caller_thread_id,
                "tool": tool,
                "turnId": f"mcp-turn-{uuid.uuid4().hex}",
            },
        )
        if not result.get("success"):
            raise CodexTargetPipeRuntime(f"Codex app tool failed: {tool}")
        return result

    def thread_status(self, thread_id: str) -> str | None:
        result = self.call_tool("read_thread", {"threadId": thread_id, "turnLimit": 1})
        items = result.get("contentItems") or []
        if not items:
            return None
        thread = json.loads(items[0]["text"]).get("thread") or {}
        status = thread.get("status") or {}
        return status.get("type") if thread.get("id") == thread_id else None

    def wake(self, thread_id: str, prompt: str, *, model: str | None = None) -> None:
        arguments = {"threadId": thread_id, "prompt": prompt}
        if model is not None:
            arguments["model"] = model
        self.call_tool("send_message_to_thread", arguments)


class CodexDesktop:
    def locate(self, thread_id: str) -> tuple[DesktopPipeClient, str]:
        pipe_path = os.environ.get(APP_TOOLS_PIPE_PATH_ENV, "").strip()
        if not pipe_path:
            raise CodexCallerOutOfProcessTree(
                f"{APP_TOOLS_PIPE_PATH_ENV} is not set by Codex Desktop."
            )
        caller_thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
        if not caller_thread_id:
            raise CodexCallerOutOfProcessTree(
                "CODEX_THREAD_ID is not set for the app-tools caller."
            )

        client = DesktopPipeClient(pipe_path, caller_thread_id)
        status = client.thread_status(thread_id)
        if status is None:
            raise CodexTargetPipeRuntime(
                f"Codex Desktop app-tools did not return Thread: {thread_id}"
            )
        return client, status
