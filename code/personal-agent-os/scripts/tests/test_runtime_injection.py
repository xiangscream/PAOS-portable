import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import runtime_injection as injection


class NativeInjectionTests(unittest.TestCase):
    request_id = "a" * 32

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = patch.object(Path, "home", return_value=self.root)
        self.home.start()
        self.addCleanup(self.home.stop)
        self.addCleanup(self.temp.cleanup)
        self.target = {"runtime": "codex", "session_id": "original-native-id"}

    def codex(self, status):
        client = Mock()
        desktop = patch.object(injection, "CodexDesktop")
        mock = desktop.start()
        mock.return_value.locate.return_value = (client, status)
        self.addCleanup(desktop.stop)
        return client

    def opencode(self, state=None):
        self.target = {"runtime": "opencode", "session_id": "ses_original", "base_url": "http://127.0.0.1:4096"}
        return patch.object(injection, "_request", side_effect=[
            ({"id": "ses_original", "directory": "/workspace/中文"}, 200),
            ({} if state is None else {"ses_original": {"type": state}}, 200),
            (None, 204),
        ])

    def workbuddy(self):
        runtime = self.root / "extension.runtime.json"
        runtime.write_text(json.dumps({"targets": ["original-native-id"], "endpoint": "http://127.0.0.1:4567", "token": "fixture-only"}), encoding="utf-8")
        self.target = {"runtime": "workbuddy", "session_id": "original-native-id", "runtime_file": str(runtime)}
        return patch.object(injection.uuid, "uuid4", return_value=uuid.UUID(hex=self.request_id))

    def test_codex_accepted_once_no_model_or_business_state(self):
        client = self.codex("idle")
        result = injection.inject(self.target, "真实业务提醒")
        client.wake.assert_called_once_with("original-native-id", "真实业务提醒", model=None)
        self.assertEqual(result, {"accepted": True, "runtime": "codex", "session_id": "original-native-id"})
        self.assertFalse(any(p.name.endswith(".json") for p in self.root.rglob("*")))

    def test_codex_active_does_not_queue_or_retry(self):
        client = self.codex("active")
        with self.assertRaises(injection.InjectionError) as raised:
            injection.inject(self.target, "提醒")
        client.wake.assert_not_called()
        self.assertEqual(raised.exception.code, "native_busy")
        self.assertEqual(raised.exception.state, "native_busy")
        self.assertFalse(raised.exception.details()["retry"])

    def test_codex_explicit_model(self):
        client = self.codex("notLoaded")
        injection.inject(self.target, "提醒", model="human-selected-model")
        client.wake.assert_called_once_with("original-native-id", "提醒", model="human-selected-model")

    def test_codex_missing_pipe_before_submission_is_a_definite_rejection(self):
        for error in (FileNotFoundError(2, "fixture-old-pipe"), PermissionError(5, "fixture-denied"),
                      EOFError("fixture-status-eof"), json.JSONDecodeError("fixture-json", "bad", 0)):
            with self.subTest(error=type(error).__name__), patch.object(injection, "CodexDesktop") as desktop:
                desktop.return_value.locate.side_effect = error
                with self.assertRaises(injection.InjectionError) as raised:
                    injection.inject(self.target, "提醒")
                self.assertIs(type(raised.exception), injection.InjectionError)
                self.assertEqual(raised.exception.code, "codex_preflight_failed")
                self.assertEqual(raised.exception.diagnostic["phase"], "status_read")
                self.assertFalse(raised.exception.details()["retry"])
                desktop.return_value.locate.assert_called_once()
                desktop.return_value.wake.assert_not_called()

    def test_codex_submission_error_is_not_reclassified_as_preflight_failure(self):
        for error in (OSError("fixture-send"), EOFError("fixture-eof"),
                      json.JSONDecodeError("fixture-json", "bad", 0),
                      UnicodeDecodeError("utf-8", b"\xff", 0, 1, "fixture"),
                      injection.CodexTargetPipeRuntime("fixture-native")):
            with self.subTest(error=type(error).__name__):
                client = self.codex("idle")
                client.wake.side_effect = error
                with self.assertRaises(injection.InjectionUncertain) as raised:
                    injection.inject(self.target, "提醒")
                self.assertEqual(raised.exception.diagnostic["phase"], "native_submit")
                self.assertFalse(raised.exception.details()["retry"])
                client.wake.assert_called_once()

    def test_actual_codex_transport_only_forwards_explicit_model(self):
        from wakeup_native.codex_app_tools import DesktopPipeClient
        client = DesktopPipeClient("fixture", "caller")
        client.call_tool = Mock()
        client.wake("original", "提醒")
        client.call_tool.assert_called_once_with("send_message_to_thread", {"threadId": "original", "prompt": "提醒"})
        client.call_tool.reset_mock()
        client.wake("original", "提醒", model="human-model")
        client.call_tool.assert_called_once_with("send_message_to_thread", {"threadId": "original", "prompt": "提醒", "model": "human-model"})

    def test_stop_prevents_any_native_access(self):
        stop = self.root / "STOP"
        stop.touch()
        self.target["stop_file"] = str(stop)
        with patch.object(injection, "CodexDesktop") as desktop:
            with self.assertRaises(injection.InjectionError):
                injection.inject(self.target, "提醒")
            desktop.assert_not_called()

    def test_opencode_directory_scoped_single_post_no_completion_poll(self):
        with self.opencode() as request:
            result = injection.inject(self.target, "提醒")
        self.assertEqual(result["http_status"], 204)
        self.assertEqual([call.args[2] for call in request.call_args_list], ["GET", "GET", "POST"])
        self.assertIn("directory=%2Fworkspace%2F", request.call_args_list[1].args[3])
        self.assertIn("directory=%2Fworkspace%2F", request.call_args_list[2].args[3])
        self.assertEqual(request.call_args_list[2].args[4], {"parts": [{"type": "text", "text": "提醒"}]})

    def test_opencode_status_is_observed_without_blocking_native_admission(self):
        for state in ("busy", "retry", "unknown"):
            with self.subTest(state=state), self.opencode(state) as request:
                result = injection.inject(self.target, "提醒")
                self.assertEqual(result["native_state"], state)
                self.assertEqual(request.call_count, 3)

    def test_opencode_missing_directory_does_not_infer_idle(self):
        with self.opencode() as request:
            request.side_effect = [({"id": "ses_original"}, 200)]
            with self.assertRaises(injection.InjectionError):
                injection.inject(self.target, "提醒")
            self.assertEqual(request.call_count, 1)

    def test_opencode_stop_at_effect_boundary(self):
        stop = self.root / "STOP"
        with self.opencode() as request:
            self.target["stop_file"] = str(stop)
            def response(*args):
                if args[3].startswith("/session/status"):
                    stop.touch()
                    return {}, 200
                return {"id": "ses_original", "directory": "/original"}, 200
            request.side_effect = response
            with self.assertRaises(injection.InjectionError):
                injection.inject(self.target, "提醒")
            self.assertEqual(request.call_count, 2)

    def test_opencode_explicit_native_model(self):
        model = {"providerID": "human-provider", "modelID": "human-model"}
        with self.opencode() as request:
            injection.inject(self.target, "提醒", model=model)
        self.assertEqual(request.call_args.args[4]["model"], model)

    def test_workbuddy_uses_granted_target_and_native_receipt(self):
        with self.workbuddy(), patch.object(injection, "_request", return_value=({"session_id": "original-native-id", "clientRequestId": self.request_id, "bridge_result": {"disposition": "queued", "item": {"text": "native internal content"}}}, 200)) as request:
            result = injection.inject(self.target, "提醒")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["native_disposition"], "queued")
        self.assertNotIn("bridge_result", result)
        self.assertNotIn("native internal content", json.dumps(result))
        self.assertEqual(request.call_count, 1)
        self.assertNotIn("modelId", request.call_args.args[4])
        self.assertNotIn("fixture-only", json.dumps(result))

    def test_workbuddy_wrong_grant_prevents_post(self):
        with self.workbuddy(), patch.object(injection, "_request") as request:
            self.target["session_id"] = "ungranted"
            with self.assertRaises(injection.InjectionError):
                injection.inject(self.target, "提醒")
            request.assert_not_called()

    def test_workbuddy_ambiguous_receipt_never_retries(self):
        with self.workbuddy(), patch.object(injection, "_request", return_value=({"session_id": "different", "clientRequestId": self.request_id}, 200)) as request:
            with self.assertRaises(injection.InjectionError):
                injection.inject(self.target, "提醒")
            self.assertEqual(request.call_count, 1)

    def test_native_io_failure_never_retries(self):
        client = self.codex("idle")
        client.wake.side_effect = EOFError("native pipe closed")
        with self.assertRaises(injection.InjectionUncertain):
            injection.inject(self.target, "提醒")
        self.assertEqual(client.wake.call_count, 1)

    def test_cross_process_native_lock_is_nonblocking_and_releases(self):
        # The child uses the same actual OS lock, without contacting a Runtime.
        code = """
import sys
from pathlib import Path
import runtime_injection as m
m.Path.home = classmethod(lambda cls: Path(sys.argv[1]))
try:
    with m._native_lock({'runtime':'codex','session_id':'original-native-id'}):
        print('acquired')
except m.InjectionError:
    print('busy')
    raise SystemExit(2)
"""
        env = {**os.environ, "PYTHONPATH": str(SCRIPTS)}
        def child():
            return subprocess.run([sys.executable, "-X", "utf8", "-c", code, str(self.root)], env=env, capture_output=True, text=True, encoding="utf-8")
        with injection._native_lock(self.target):
            result = child()
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout.strip(), "busy")
        result = child()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "acquired")

    def test_standalone_cli_does_not_import_project_store(self):
        code = "import runtime_injection,sys; assert not any(n.endswith('project_store') for n in sys.modules)"
        result = subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONPATH": str(SCRIPTS)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_returns_call_error_without_business_state(self):
        request = {"target": {"runtime": "unsupported", "session_id": "native"}, "message": "提醒"}
        result = subprocess.run([sys.executable, str(SCRIPTS / "runtime_injection.py")], input=json.dumps(request).encode(), capture_output=True)
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(set(value), {"accepted", "error"})
        self.assertFalse(value["accepted"])
        self.assertEqual(result.stderr, b"")


if __name__ == "__main__":
    unittest.main()
