from __future__ import annotations

import builtins
import io
import json
import os
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from wakeup_native.codex_app_tools import (
    APP_TOOLS_PIPE_PATH_ENV,
    CodexDesktop,
    DesktopPipeClient,
)


class _Pipe:
    def __init__(self, response: dict):
        payload = json.dumps(response, separators=(",", ":")).encode("utf-8")
        self._reply = io.BytesIO(struct.pack("<I", len(payload)) + payload)
        self.writes: list[bytes] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def write(self, value: bytes) -> int:
        self.writes.append(value)
        return len(value)

    def read(self, size: int) -> bytes:
        return self._reply.read(size)


class CodexAppToolsTests(unittest.TestCase):
    def test_request_uses_length_prefixed_utf8_jsonrpc(self):
        pipe = _Pipe({"jsonrpc": "2.0", "id": 1, "result": {"tools": []}})
        client = DesktopPipeClient("test-pipe", "caller-thread")

        with mock.patch.object(builtins, "open", return_value=pipe) as open_pipe:
            result = client.request("tools/list", {"threadStartKind": "all"})

        open_pipe.assert_called_once_with("test-pipe", "r+b", buffering=0)
        self.assertEqual(result, {"tools": []})
        size = struct.unpack("<I", pipe.writes[0])[0]
        request = json.loads(pipe.writes[1][:size].decode("utf-8"))
        self.assertEqual(request["method"], "tools/list")
        self.assertEqual(request["params"], {"threadStartKind": "all"})

    def test_wake_resolves_tool_namespace_and_separates_caller_from_target(self):
        client = DesktopPipeClient("test-pipe", "caller-thread")
        with mock.patch.object(
            client,
            "request",
            side_effect=[
                {"tools": [{"name": "send_message_to_thread", "namespace": "codex_app"}]},
                {"success": True},
            ],
        ) as request:
            client.wake("target-thread", "continue this task")

        self.assertEqual(
            request.call_args_list[0].args,
            ("tools/list", {"threadStartKind": "all"}),
        )
        self.assertEqual(request.call_args_list[1].args[0], "tools/call")
        params = request.call_args_list[1].args[1]
        self.assertEqual(params["threadId"], "caller-thread")
        self.assertEqual(params["namespace"], "codex_app")
        self.assertEqual(
            params["arguments"],
            {"threadId": "target-thread", "prompt": "continue this task"},
        )

    def test_thread_status_reads_and_validates_the_exact_target_thread(self):
        thread = {
            "thread": {"id": "target-thread", "status": {"type": "notLoaded"}}
        }
        other_thread = {
            "thread": {"id": "other-thread", "status": {"type": "idle"}}
        }
        client = DesktopPipeClient("test-pipe", "caller-thread")
        with mock.patch.object(
            client,
            "call_tool",
            side_effect=[
                {"contentItems": [{"text": json.dumps(thread)}]},
                {"contentItems": [{"text": json.dumps(other_thread)}]},
            ],
        ) as call_tool:
            status = client.thread_status("target-thread")
            mismatched_status = client.thread_status("target-thread")

        self.assertEqual(status, "notLoaded")
        self.assertIsNone(mismatched_status)
        self.assertEqual(
            call_tool.call_args_list[0].args,
            ("read_thread", {"threadId": "target-thread", "turnLimit": 1}),
        )

    def test_locate_requires_caller_context_and_reads_the_exact_target(self):
        fake_client = mock.Mock()
        fake_client.thread_status.return_value = "idle"
        with mock.patch.dict(
            os.environ,
            {
                APP_TOOLS_PIPE_PATH_ENV: "test-pipe",
                "CODEX_THREAD_ID": "caller-thread",
            },
            clear=True,
        ), mock.patch(
            "wakeup_native.codex_app_tools.DesktopPipeClient",
            return_value=fake_client,
        ) as client_factory:
            client, status = CodexDesktop().locate("target-thread")

        client_factory.assert_called_once_with("test-pipe", "caller-thread")
        fake_client.thread_status.assert_called_once_with("target-thread")
        self.assertIs(client, fake_client)
        self.assertEqual(status, "idle")


if __name__ == "__main__":
    unittest.main()
