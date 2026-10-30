"""Offline receiver/HTTP fixtures: no Desktop pipe or model is contacted."""
import errno
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_injection as injection
from wakeup_native.codex_receiver import SelfReminder, make_server


class CodexDiagnosticsTests(unittest.TestCase):
    request_id = "a" * 32

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.client = Mock()
        self.client.thread_status.return_value = "idle"
        self.reminder = SelfReminder(self.client, "fixture-self", Path(temp.name) / "STOP")
        self.log = io.StringIO()
        self.target = {"runtime": "codex", "session_id": "fixture-self",
                       "extension": {"endpoint": "http://127.0.0.1:12345", "token": "private-fixture-token"}}

    def server(self, log=None):
        server = make_server(self.reminder, "private-fixture-token", self.log if log is None else log)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 3)
        self.addCleanup(server.shutdown)
        self.target["extension"]["endpoint"] = f"http://127.0.0.1:{server.server_port}"
        return server

    def send(self):
        return injection._codex_extension_send(self.target, "private-fixture-prompt", None)

    def rows(self):
        return [json.loads(line) for line in self.log.getvalue().splitlines()]

    def assert_private_absent(self, value):
        text = json.dumps(value)
        for private in ("private-fixture-prompt", "private-fixture-token", "private-pipe-path", "private-exception-text"):
            self.assertNotIn(private, text)

    def test_real_http_correlates_stages_without_forwarding_id_to_native(self):
        self.server()
        with patch.object(injection.uuid, "uuid4", return_value=Mock(hex=self.request_id)):
            result = self.send()
        self.assertTrue(result["accepted"])
        self.assertEqual(result["request_id"], self.request_id)
        self.client.wake.assert_called_once_with("fixture-self", "private-fixture-prompt")
        rows = self.rows()
        self.assertEqual([r["event"] for r in rows], ["request_received", "status_read_started", "status_read_returned",
                         "native_submit_started", "native_result_returned", "http_reply_returned"])
        self.assertTrue(all(r["request_id"] == self.request_id and r["elapsed_ms"] >= 0 for r in rows))
        self.assert_private_absent(rows)

    def test_unknown_status_remains_rejected_and_never_submits(self):
        self.server()
        self.client.thread_status.return_value = None
        with self.assertRaises(injection.InjectionError) as raised:
            self.send()
        self.assertNotIsInstance(raised.exception, injection.InjectionUncertain)
        self.assertEqual(raised.exception.code, "native_unavailable")
        self.assertEqual(raised.exception.details()["diagnostic"]["http_status"], 503)
        self.client.wake.assert_not_called()
        self.assertNotIn("native_submit_started", [r["event"] for r in self.rows()])

    def test_status_rejection_preserves_machine_native_status_over_real_http(self):
        self.server()
        for status, expected in (("systemError", "systemError"),
                                 (None, "not_returned"),
                                 ("private-status-value", "unrecognized")):
            with self.subTest(status=status):
                self.client.thread_status.return_value = status
                with self.assertRaises(injection.InjectionError) as raised:
                    self.send()
                value = raised.exception.details()
                self.assertEqual(value["error_code"], "native_unavailable")
                self.assertEqual(value["diagnostic"]["phase"], "status_read")
                self.assertEqual(value["diagnostic"]["native_status"], expected)
                self.assertFalse(value["retry"])
                self.client.wake.assert_not_called()
                if status == "private-status-value":
                    self.assert_private_absent([value, self.rows()])

    def test_status_error_preserves_machine_fields_before_native_submit(self):
        self.server()
        error = OSError(errno.EIO, "private-exception-text")
        error.winerror = 10053
        self.client.thread_status.side_effect = error
        with self.assertRaises(injection.InjectionError) as raised:
            self.send()
        value = raised.exception.details()
        self.assertEqual(value["error_code"], "native_unreachable")
        self.assertEqual(value["diagnostic"]["phase"], "status_read")
        self.assertEqual(value["diagnostic"]["exception_type"], "OSError")
        self.assertEqual(value["diagnostic"]["errno"], errno.EIO)
        self.assertEqual(value["diagnostic"]["winerror"], 10053)
        self.client.wake.assert_not_called()
        self.assert_private_absent([value, self.rows()])

    def test_native_lost_receipt_remains_unknown_single_submission(self):
        self.server()
        self.client.wake.side_effect = EOFError("private-pipe-path")
        with self.assertRaises(injection.InjectionUncertain) as raised:
            self.send()
        value = raised.exception.details()
        self.assertEqual(value["error_code"], "delivery_not_confirmed")
        self.assertFalse(value["retry"])
        self.assertEqual(value["diagnostic"]["phase"], "native_submit")
        self.assertEqual(value["diagnostic"]["exception_type"], "EOFError")
        self.client.wake.assert_called_once()
        self.assertIn("native_result_unknown", [r["event"] for r in self.rows()])
        self.assert_private_absent([value, self.rows()])

    def test_http_timeout_keeps_request_id_without_retry(self):
        with patch.object(injection, "_request", side_effect=URLError(TimeoutError("private-exception-text"))) as request:
            with self.assertRaises(injection.InjectionUncertain) as raised:
                self.send()
        request.assert_called_once()
        value = raised.exception.details()
        self.assertEqual(value["diagnostic"]["exception_type"], "TimeoutError")
        self.assertEqual(value["diagnostic"]["phase"], "http_wait")
        self.assertEqual(value["diagnostic"]["request_id"], request.call_args.kwargs["request_id"])
        self.assertEqual(set(request.call_args.args[4]), {"session_id", "message"})
        self.assert_private_absent(value)

    def test_connection_refused_keeps_definite_offline(self):
        with patch.object(injection, "_request", side_effect=URLError(ConnectionRefusedError(errno.ECONNREFUSED, "private-exception-text"))):
            with self.assertRaises(injection.InjectionError) as raised:
                self.send()
        self.assertNotIsInstance(raised.exception, injection.InjectionUncertain)
        self.assertEqual(raised.exception.code, "receiver_connection_refused")
        self.assertEqual(raised.exception.diagnostic["errno"], errno.ECONNREFUSED)
        self.assert_private_absent(raised.exception.details())

    def test_untrusted_error_body_does_not_copy_free_text_or_replace_request_id(self):
        body = {"error": "native_busy", "detail": "private-exception-text", "diagnostic": {
            "request_id": "b" * 32, "phase": "status_read", "prompt": "private-fixture-prompt",
            "token": "private-fixture-token", "native_status": "private-exception-text",
            "winerror": 10053, "http_status": 200}}
        error = HTTPError("http://fixture", 409, "private-exception-text", {}, io.BytesIO(json.dumps(body).encode()))
        with patch.object(injection.uuid, "uuid4", return_value=Mock(hex=self.request_id)), \
                patch.object(injection, "_request", side_effect=error):
            with self.assertRaises(injection.InjectionError) as raised:
                self.send()
        self.assertEqual(raised.exception.diagnostic["request_id"], self.request_id)
        self.assertEqual(raised.exception.diagnostic["http_status"], 409)
        self.assert_private_absent(raised.exception.details())

    def test_formal_mail_reminder_keeps_diagnostic_and_unknown_semantics(self):
        import paos
        diagnostic = {"request_id": self.request_id, "phase": "http_wait", "exception_type": "TimeoutError"}
        error = injection.InjectionUncertain("Codex receiver response not confirmed; do not resend", diagnostic=diagnostic)
        with patch.object(paos, "load_native_targets", return_value={"fixture-home": self.target}), \
                patch.object(paos, "native_inject", side_effect=error) as send:
            result = paos._inject_from_contact_store(Path("fixture-home-root"), agent_id="fixture-home",
                message_id="fixture-source", sender_id="fixture-sender", subject="fixture")
        self.assertIsNone(result["accepted"])
        self.assertEqual(result["state"], "delivery_uncertain")
        self.assertFalse(result["retry"])
        self.assertEqual(result["diagnostic"], diagnostic)
        send.assert_called_once()
        self.assert_private_absent(result)

    def test_formal_mail_reminder_keeps_native_status_on_definite_rejection(self):
        import paos
        diagnostic = {"request_id": self.request_id, "phase": "status_read",
                      "native_status": "systemError", "http_status": 503}
        error = injection.InjectionError("Codex receiver rejected (HTTP 503)",
                                         code="native_unavailable", state="native_unavailable",
                                         diagnostic=diagnostic)
        with patch.object(paos, "load_native_targets", return_value={"fixture-home": self.target}), \
                patch.object(paos, "native_inject", side_effect=error) as send:
            result = paos._inject_from_contact_store(Path("fixture-home-root"), agent_id="fixture-home",
                message_id="fixture-source", sender_id="fixture-sender", subject="fixture")
        self.assertIs(result["accepted"], False)
        self.assertEqual(result["state"], "native_unavailable")
        self.assertFalse(result["retry"])
        self.assertEqual(result["diagnostic"], diagnostic)
        send.assert_called_once()
        self.assert_private_absent(result)

    def handler(self, server):
        handler = server.RequestHandlerClass.__new__(server.RequestHandlerClass)
        payload = json.dumps({"session_id": "fixture-self", "message": "private-fixture-prompt"}).encode()
        handler.path = "/send"
        handler.headers = {"Authorization": "Bearer private-fixture-token", "X-PAOS-Request-ID": self.request_id,
                           "Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        return handler

    def test_reply_disconnect_records_failure_after_native_result_without_resend(self):
        server = make_server(self.reminder, "private-fixture-token", self.log)
        self.addCleanup(server.server_close)
        handler = self.handler(server)
        handler.wfile.write.side_effect = ConnectionAbortedError(errno.ECONNABORTED, "private-exception-text")
        handler.do_POST()
        self.client.wake.assert_called_once()
        events = [r["event"] for r in self.rows()]
        self.assertLess(events.index("native_result_returned"), events.index("http_reply_failed"))
        self.assertNotIn("http_reply_returned", events)
        self.assertEqual(self.rows()[-1]["http_status"], 200)
        self.assertEqual(self.rows()[-1]["exception_type"], "ConnectionAbortedError")
        self.assert_private_absent(self.rows())

    def test_raw_error_responses_have_only_machine_fields(self):
        server = make_server(self.reminder, "private-fixture-token", self.log)
        self.addCleanup(server.server_close)
        handler = self.handler(server)
        self.client.thread_status.side_effect = OSError(errno.EIO, "private-exception-text")
        handler.do_POST()
        handler.send_response.assert_called_once_with(503)
        body = json.loads(handler.wfile.write.call_args.args[0])
        self.assertEqual(set(body), {"error", "retry", "diagnostic"})
        self.assertEqual(body["error"], "native_unreachable")
        self.assert_private_absent(body)
        self.client.wake.assert_not_called()

        invalid = self.handler(server)
        invalid.rfile = io.BytesIO(b"not-json")
        invalid.headers["Content-Length"] = "8"
        invalid.do_POST()
        invalid.send_response.assert_called_once_with(400)
        body = json.loads(invalid.wfile.write.call_args.args[0])
        self.assertEqual(set(body), {"error", "retry"})
        self.assertEqual(body["error"], "invalid_request")
        self.client.wake.assert_not_called()

    def test_log_failure_is_visible_and_does_not_repeat_or_change_accepted_send(self):
        log = Mock()
        log.write.side_effect = OSError(errno.ENOSPC, "private-exception-text")
        server = make_server(self.reminder, "private-fixture-token", log)
        self.addCleanup(server.server_close)
        handler = self.handler(server)
        output = io.StringIO()
        with patch("sys.stderr", output):
            handler.do_POST()
        self.client.wake.assert_called_once()
        handler.send_response.assert_called_once_with(200)
        result = json.loads(handler.wfile.write.call_args.args[0])
        self.assertTrue(result["accepted"])
        failures = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertTrue(all(row["event"] == "request_log_failed" for row in failures))
        self.assert_private_absent(failures)

    def test_bad_request_id_never_reaches_desktop_or_logs_header(self):
        server = make_server(self.reminder, "private-fixture-token", self.log)
        self.addCleanup(server.server_close)
        handler = self.handler(server)
        handler.headers["X-PAOS-Request-ID"] = "private-fixture-token"
        handler.do_POST()
        handler.send_response.assert_called_once_with(400)
        self.client.thread_status.assert_not_called()
        self.assertEqual(self.rows(), [])


if __name__ == "__main__":
    unittest.main()
