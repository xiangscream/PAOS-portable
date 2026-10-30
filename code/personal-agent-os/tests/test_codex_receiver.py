import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from wakeup_native.codex_receiver import ReceiverError, SelfReminder, make_server, serve


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        home = patch("runtime_injection.Path.home", return_value=Path(self.temp.name))
        home.start()
        self.addCleanup(home.stop)
        self.stop = Path(self.temp.name) / "STOP"
        self.client = Mock()
        self.client.thread_status.return_value = "idle"
        self.reminder = SelfReminder(self.client, "target-self", self.stop)
        self.payload = {"session_id": "target-self", "message": "new reminder"}

    def assert_refused(self, code, payload=None):
        with self.assertRaises(ReceiverError) as raised:
            self.reminder.send(self.payload if payload is None else payload)
        self.assertEqual(raised.exception.code, code)
        self.client.wake.assert_not_called()

    def test_exact_self_single_send_no_model_no_completion(self):
        result = self.reminder.send(self.payload)
        self.client.thread_status.assert_called_once_with("target-self")
        self.client.wake.assert_called_once_with("target-self", "new reminder")
        self.assertEqual(result, {"accepted": True, "session_id": "target-self", "completed": False,
                                  "native_status_before_submit": "idle"})

    def test_wrong_target_never_reads_or_sends(self):
        self.assert_refused("target_not_granted", {**self.payload, "session_id": "other"})
        self.client.thread_status.assert_not_called()

    def test_no_arbitrary_method_model_or_caller_override(self):
        for key in ("method", "model", "caller_thread_id", "pipe_path", "tool"):
            with self.subTest(key=key):
                self.assert_refused("invalid_request", {**self.payload, key: "override"})
        self.client.thread_status.assert_not_called()

    def test_empty_message_never_calls_desktop(self):
        self.assert_refused("invalid_request", {**self.payload, "message": " "})
        self.client.thread_status.assert_not_called()

    def test_active_submits_one_existing_host_followup(self):
        self.client.thread_status.return_value = "active"
        result = self.reminder.send(self.payload)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["native_status_before_submit"], "active")
        self.client.wake.assert_called_once_with("target-self", "new reminder")

    def test_unknown_is_not_idle(self):
        for status, expected in (("systemError", "systemError"),
                                 (None, "not_returned"),
                                 ("private-status-value", "unrecognized")):
            with self.subTest(status=status):
                self.client.thread_status.return_value = status
                with self.assertRaises(ReceiverError) as raised:
                    self.reminder.send(self.payload)
                self.assertEqual(raised.exception.code, "native_unavailable")
                self.assertEqual(raised.exception.status, 503)
                self.assertEqual(raised.exception.diagnostic, {"phase": "status_read",
                                                               "native_status": expected})
                self.client.wake.assert_not_called()
                if status == "private-status-value":
                    self.assertNotIn(status, json.dumps(raised.exception.diagnostic))

    def test_stop_before_probe(self):
        self.stop.touch()
        self.assert_refused("native_stopped")
        self.client.thread_status.assert_not_called()

    def test_stop_between_probe_and_send(self):
        def become_stopped(session):
            self.stop.touch()
            return "idle"
        self.client.thread_status.side_effect = become_stopped
        self.assert_refused("native_stopped")

    def test_read_failure_does_not_submit(self):
        self.client.thread_status.side_effect = OSError("native endpoint gone")
        self.assert_refused("native_unreachable")

    def test_send_failure_is_uncertain_no_second_send(self):
        self.client.wake.side_effect = EOFError("private Desktop pipe pathname")
        with self.assertRaises(ReceiverError) as raised:
            self.reminder.send(self.payload)
        self.assertEqual(raised.exception.code, "delivery_not_confirmed")
        self.assertNotIn("private Desktop pipe pathname", str(raised.exception))
        self.client.wake.assert_called_once()

    def test_launcher_uses_only_own_inherited_context(self):
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "own", "CODEX_APP_TOOLS_PIPE_PATH": "inherited"}, clear=True):
            receiver = SelfReminder.from_desktop(self.stop)
        self.assertEqual(receiver.session_id, "own")
        self.assertEqual(receiver.client.caller_thread_id, "own")
        self.assertEqual(receiver.client.pipe_path, "inherited")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ReceiverError):
                SelfReminder.from_desktop(self.stop)

    def test_runtime_grant_has_no_desktop_pipe_and_is_removed_on_exit(self):
        runtime_file = Path(self.temp.name) / "private" / "runtime.json"
        server = Mock(server_port=12345)
        def observe():
            grant = json.loads(runtime_file.read_text(encoding="utf-8"))
            self.assertEqual(set(grant), {"schema", "pid", "endpoint", "session_id", "token", "process_identity", "receiver_behavior"})
            self.assertEqual(grant["session_id"], "target-self")
            self.assertEqual(grant["endpoint"], "http://127.0.0.1:12345")
            self.assertNotIn("pipe_path", grant)
        server.serve_forever.side_effect = observe
        with patch.object(SelfReminder, "from_desktop", return_value=self.reminder), \
                patch("wakeup_native.codex_receiver.make_server", return_value=server):
            serve(runtime_file, self.stop)
        self.assertFalse(runtime_file.exists())
        server.server_close.assert_called_once()
        rows = self.lifecycle_rows(runtime_file)
        self.assertEqual([row["event"] for row in rows], ["starting", "ready", "exit"])
        self.assertEqual(rows[-1]["outcome"], "normal_return")
        self.assertIsNone(rows[-1]["exception_type"])
        self.assertEqual(rows[1]["session_id"], "target-self")
        self.assertEqual(rows[0]["pid"], os.getpid())
        self.assertEqual(rows[0]["parent_pid"], os.getppid())

    def lifecycle_rows(self, runtime_file):
        log = runtime_file.with_name(runtime_file.name + ".lifecycle.jsonl")
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    def test_failure_logged_without_secret_text_and_original_error_propagates(self):
        runtime_file = Path(self.temp.name) / "runtime.json"
        server = Mock(server_port=12345)
        error = RuntimeError("private-pipe-and-token-value")
        server.serve_forever.side_effect = error
        with patch.object(SelfReminder, "from_desktop", return_value=self.reminder), \
                patch("wakeup_native.codex_receiver.make_server", return_value=server):
            with self.assertRaises(RuntimeError) as raised:
                serve(runtime_file, self.stop)
        self.assertIs(raised.exception, error)
        self.assertFalse(runtime_file.exists())
        rows = self.lifecycle_rows(runtime_file)
        self.assertEqual(rows[-1]["exception_type"], "RuntimeError")
        self.assertEqual(rows[-1]["outcome"], "exception")
        self.assertNotIn("private-pipe-and-token-value", json.dumps(rows))
        self.client.wake.assert_not_called()

    def test_missing_desktop_records_startup_failure_without_creating_runtime(self):
        runtime_file = Path(self.temp.name) / "runtime.json"
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ReceiverError):
                serve(runtime_file, self.stop)
        self.assertFalse(runtime_file.exists())
        rows = self.lifecycle_rows(runtime_file)
        self.assertEqual([row["event"] for row in rows], ["starting", "exit"])
        self.assertEqual(rows[-1]["error_code"], "codex_caller_unavailable")

    def test_duplicate_launch_preserves_existing_grant_and_appends_evidence(self):
        runtime_file = Path(self.temp.name) / "runtime.json"
        server = Mock(server_port=12345)
        with patch.object(SelfReminder, "from_desktop", return_value=self.reminder), \
                patch("wakeup_native.codex_receiver.make_server", return_value=server):
            serve(runtime_file, self.stop)
            prior = self.lifecycle_rows(runtime_file)
            runtime_file.write_text("original-private-grant", encoding="utf-8")
            with self.assertRaises(ReceiverError):
                serve(runtime_file, self.stop)
        self.assertEqual(runtime_file.read_text(encoding="utf-8"), "original-private-grant")
        rows = self.lifecycle_rows(runtime_file)
        self.assertEqual(rows[:len(prior)], prior)
        self.assertEqual(rows[-1]["exception_type"], "ReceiverError")
        server.serve_forever.assert_called_once()

    def test_keyboard_interrupt_is_recorded_and_not_swallowed(self):
        runtime_file = Path(self.temp.name) / "runtime.json"
        server = Mock(server_port=12345)
        server.serve_forever.side_effect = KeyboardInterrupt
        with patch.object(SelfReminder, "from_desktop", return_value=self.reminder), \
                patch("wakeup_native.codex_receiver.make_server", return_value=server):
            with self.assertRaises(KeyboardInterrupt):
                serve(runtime_file, self.stop)
        self.assertFalse(runtime_file.exists())
        self.assertEqual(self.lifecycle_rows(runtime_file)[-1]["exception_type"], "KeyboardInterrupt")

    def test_same_thread_positive_dead_grant_is_archived_and_rotated_at_original_locator(self):
        runtime_file = Path(self.temp.name) / "different-owner-layout.json"
        old = {"schema": "paos-codex-self-reminder/v1", "pid": 123456,
               "session_id": "target-self", "endpoint": "http://127.0.0.1:1234", "token": "old-private-grant"}
        runtime_file.write_text(json.dumps(old), encoding="utf-8")
        server = Mock(server_port=12345)
        def ready():
            new = json.loads(runtime_file.read_text(encoding="utf-8"))
            self.assertEqual(new["session_id"], old["session_id"])
            self.assertNotEqual(new["token"], old["token"])
        server.serve_forever.side_effect = ready
        with patch.object(SelfReminder, "from_desktop", return_value=self.reminder), \
                patch("paos_contact._local_pid_alive", return_value=False), \
                patch("wakeup_native.codex_receiver.make_server", return_value=server):
            serve(runtime_file, self.stop)
        archives = list(runtime_file.parent.glob(runtime_file.name + ".stale-*.json"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(json.loads(archives[0].read_text(encoding="utf-8")), old)
        self.assertEqual([row["event"] for row in self.lifecycle_rows(runtime_file)],
                         ["starting", "stale_archived", "ready", "exit"])

    def test_live_unknown_and_foreign_thread_grants_never_rotate(self):
        runtime_file = Path(self.temp.name) / "runtime.json"
        for session, alive in (("target-self", True), ("target-self", None), ("other-thread", False)):
            old = {"schema": "paos-codex-self-reminder/v1", "pid": 123456,
                   "session_id": session, "endpoint": "http://127.0.0.1:1234", "token": "private-grant",
                   "process_identity": "windows:123"}
            runtime_file.write_text(json.dumps(old), encoding="utf-8")
            with patch.object(SelfReminder, "from_desktop", return_value=self.reminder), \
                    patch("paos_contact._local_pid_alive", return_value=alive), \
                    patch("wakeup_native.process_identity.process_snapshot", return_value={"alive": alive, "identity": "windows:123"}), \
                    patch("wakeup_native.codex_receiver.make_server") as make:
                with self.assertRaises(ReceiverError) as error:
                    serve(runtime_file, self.stop)
                self.assertEqual(error.exception.code, "receiver_not_rotatable")
            make.assert_not_called()
            self.assertEqual(json.loads(runtime_file.read_text(encoding="utf-8")), old)
            self.assertEqual(list(runtime_file.parent.glob(runtime_file.name + ".stale-*.json")), [])

    def test_prepare_respects_original_stop_without_archiving_or_starting(self):
        runtime_file = Path(self.temp.name) / "runtime.json"
        runtime_file.write_text("keep-original-evidence", encoding="utf-8")
        self.stop.touch()
        with patch.object(SelfReminder, "from_desktop", return_value=self.reminder), \
                patch("wakeup_native.codex_receiver.make_server") as make:
            with self.assertRaises(ReceiverError) as error:
                serve(runtime_file, self.stop)
        self.assertEqual(error.exception.code, "native_stopped")
        self.assertEqual(runtime_file.read_text(encoding="utf-8"), "keep-original-evidence")
        make.assert_not_called()

    def test_lifecycle_open_failure_is_visible_and_does_not_start_receiver(self):
        runtime_file = Path(self.temp.name) / "runtime.json"
        runtime_file.with_name(runtime_file.name + ".lifecycle.jsonl").mkdir()
        with patch.object(SelfReminder, "from_desktop") as from_desktop:
            with self.assertRaises(OSError):
                serve(runtime_file, self.stop)
        from_desktop.assert_not_called()
        self.assertFalse(runtime_file.exists())

    def test_abrupt_fixture_termination_leaves_flushed_ready_not_false_exit(self):
        # Offline fixture only. No Desktop pipe is opened and no reminder is sent.
        runtime_file = Path(self.temp.name) / "fixture-runtime.json"
        env = {**os.environ, "CODEX_THREAD_ID": "fixture-self",
               "CODEX_APP_TOOLS_PIPE_PATH": "fixture-never-opened"}
        process = subprocess.Popen(
            [sys.executable, "-B", "-m", "wakeup_native.codex_receiver",
             "--runtime-file", str(runtime_file), "--stop-file", str(self.stop)],
            cwd=Path(__file__).resolve().parents[1] / "scripts", env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and process.poll() is None:
                if runtime_file.exists() and len(self.lifecycle_rows(runtime_file)) == 2:
                    break
                time.sleep(0.02)
            self.assertTrue(runtime_file.exists())
            rows = self.lifecycle_rows(runtime_file)
            self.assertEqual([row["event"] for row in rows], ["starting", "ready"])
            self.assertEqual(rows[0]["pid"], process.pid)
            process.kill()  # Only the Popen fixture above; never a production PID.
            process.wait(timeout=5)
            self.assertTrue(runtime_file.exists())
            self.assertEqual(self.lifecycle_rows(runtime_file), rows)
            self.assertNotIn("fixture-never-opened", json.dumps(rows))
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_real_http_authorization_and_exact_payload_gate(self):
        server = make_server(self.reminder, "local-grant")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.assertEqual(server.server_address[0], "127.0.0.1")
        origin = f"http://127.0.0.1:{server.server_port}"
        opener = build_opener(ProxyHandler({}))
        def send(payload, token):
            request = Request(origin + "/send", data=json.dumps(payload).encode(),
                              headers={"Authorization": "Bearer " + token}, method="POST")
            return opener.open(request, timeout=3)
        with self.assertRaises(HTTPError) as unauthenticated:
            send(self.payload, "wrong")
        self.assertEqual(unauthenticated.exception.code, 401)
        self.client.thread_status.assert_not_called()
        with self.assertRaises(HTTPError) as forbidden:
            send({**self.payload, "session_id": "another"}, "local-grant")
        self.assertEqual(forbidden.exception.code, 403)
        self.client.thread_status.assert_not_called()
        with send(self.payload, "local-grant") as response:
            result = json.load(response)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["completed"])
        self.client.wake.assert_called_once()


if __name__ == "__main__":
    unittest.main()
