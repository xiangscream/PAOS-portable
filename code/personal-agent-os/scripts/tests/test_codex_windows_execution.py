import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_injection as injection


class WindowsExecutionTests(unittest.TestCase):
    def setUp(self):
        self.target = {"runtime": "codex", "session_id": "fixture-self",
                       "extension": {"receiver_runtime_file": "C:/private/runtime.json",
                                     "execution_environment": "windows",
                                     "windows_python": "C:/Python/python.exe"}}
        self.receipt = {"accepted": True, "runtime": "codex", "session_id": "fixture-self",
                        "via": "target_extension"}
        resolver = patch.object(injection, "resolve_installation_path", return_value=Path("fixture-installation.json"))
        resolver.start()
        self.addCleanup(resolver.stop)

    def wsl(self):
        return patch.object(injection.os, "name", "posix")

    def installation(self):
        return patch.object(injection, "load_installation_descriptor",
                            return_value={"configured": True, "source_root": "C:/安装目录/paos"})

    def child_run(self, result=None, *, side_effect=None):
        result = result or subprocess.CompletedProcess([], 0, json.dumps(self.receipt).encode(), b"")
        return patch.object(injection.subprocess, "run", return_value=result, side_effect=side_effect)

    def test_wsl_selects_windows_before_http_and_forwards_utf8_stdin_once(self):
        with self.wsl(), patch.dict(os.environ, {"WSL_DISTRO_NAME": "fixture"}), \
                self.installation(), self.child_run() as run, \
                patch.object(injection, "_request") as http, \
                patch.object(injection, "CodexDesktop") as desktop, \
                patch.object(injection, "_native_lock") as lock:
            result = injection.inject(self.target, "中文提醒 🐾\n$quoted ' body")
        run.assert_called_once()
        http.assert_not_called()
        desktop.assert_not_called()
        lock.assert_not_called()  # The Windows child owns the Windows lock.
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], "/mnt/c/Python/python.exe")
        self.assertEqual(argv[-1], "C:\\安装目录\\paos\\scripts\\runtime_injection.py")
        self.assertNotIn("中文提醒", " ".join(argv))
        request = json.loads(run.call_args.kwargs["input"].decode("utf-8"))
        self.assertEqual(request["message"], "中文提醒 🐾\n$quoted ' body")
        self.assertEqual(request["target"]["session_id"], "fixture-self")
        self.assertNotIn("model", request)
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["execution_environment"], "windows")

    def test_handoff_omits_caller_credentials_and_preserves_timeout_and_explicit_model(self):
        self.target.update({"caller_pipe": "do-not-copy", "timeout_seconds": 7})
        self.target["extension"]["token"] = "do-not-copy"
        with self.wsl(), patch.dict(os.environ, {"WSL_DISTRO_NAME": "fixture"}), \
                self.installation(), self.child_run() as run:
            injection.inject(self.target, "fixture", model="human-selected")
        data = run.call_args.kwargs["input"].decode("utf-8")
        self.assertNotIn("do-not-copy", data)
        self.assertEqual(json.loads(data)["model"], "human-selected")
        self.assertEqual(json.loads(data)["target"]["timeout_seconds"], 7)
        self.assertEqual(run.call_args.kwargs["timeout"], 12)

    def test_timeout_unreadable_or_wrong_receipt_never_tries_local_or_retries(self):
        cases = [subprocess.TimeoutExpired("fixed-executable", 35),
                 OSError("interop unavailable"),
                 subprocess.CompletedProcess([], 0, b"not-json", b""),
                 subprocess.CompletedProcess([], 0, json.dumps({**self.receipt, "session_id": "other"}).encode(), b""),
                 subprocess.CompletedProcess([], 1, json.dumps({"accepted": False, "error": "STOP"}).encode(), b""),
                 subprocess.CompletedProcess([], 1, json.dumps({"accepted": None, "uncertain": True, "retry": False}).encode(), b"")]
        for case in cases:
            process = self.child_run(side_effect=case) if isinstance(case, BaseException) else self.child_run(case)
            with self.subTest(case=type(case).__name__), self.wsl(), \
                    patch.dict(os.environ, {"WSL_DISTRO_NAME": "fixture"}), self.installation(), \
                    process as run, \
                    patch.object(injection, "_request") as http, \
                    patch.object(injection, "CodexDesktop") as desktop:
                with self.assertRaises(injection.InjectionError):
                    injection.inject(self.target, "fixture")
                run.assert_called_once()
                http.assert_not_called()
                desktop.assert_not_called()

    def test_uncertain_standalone_receipt_does_not_claim_confirmed_rejection(self):
        request = {"target": self.target, "message": "fixture"}
        stream = Mock(buffer=Mock(read=Mock(return_value=json.dumps(request).encode())))
        with patch.object(injection.sys, "stdin", stream), \
                patch.object(injection.sys, "argv", ["runtime_injection.py"]), \
                patch.object(injection, "inject", side_effect=injection.InjectionUncertain("do not resend")), \
                patch("builtins.print") as output:
            self.assertEqual(injection.main(), 1)
        receipt = json.loads(output.call_args.args[0])
        self.assertIsNone(receipt["accepted"])
        self.assertTrue(receipt["uncertain"])
        self.assertFalse(receipt["retry"])

    def test_windows_handoff_preserves_diagnostic_fields_without_retry(self):
        diagnostic = {"request_id": "a" * 32, "phase": "status_read", "native_status": "systemError",
                      "exception_type": "EOFError", "winerror": 10053}
        for uncertain in (True, False):
            receipt = {"accepted": None if uncertain else False, "uncertain": uncertain,
                       "error_code": "delivery_not_confirmed" if uncertain else "native_unreachable",
                       "state": "delivery_uncertain" if uncertain else "native_unavailable", "diagnostic": diagnostic}
            result = subprocess.CompletedProcess([], 1, json.dumps(receipt).encode(), b"")
            with self.subTest(uncertain=uncertain), self.wsl(), self.installation(), self.child_run(result) as run:
                with self.assertRaises(injection.InjectionError) as raised:
                    injection._windows_native(self.target, "fixture", None)
            self.assertEqual(raised.exception.diagnostic, diagnostic)
            self.assertEqual(isinstance(raised.exception, injection.InjectionUncertain), uncertain)
            self.assertFalse(raised.exception.details()["retry"])
            run.assert_called_once()

    def test_stop_prevents_windows_process_start(self):
        with tempfile.TemporaryDirectory() as directory:
            stop = Path(directory) / "STOP"
            stop.touch()
            self.target["stop_file"] = str(stop)
            with patch.object(injection.subprocess, "run") as run:
                with self.assertRaises(injection.InjectionError):
                    injection.inject(self.target, "fixture")
            run.assert_not_called()

    def test_missing_explicit_windows_python_or_installation_fails_before_launch(self):
        with self.wsl(), patch.dict(os.environ, {"WSL_DISTRO_NAME": "fixture"}), \
                patch.object(injection.subprocess, "run") as run:
            self.target["extension"].pop("windows_python")
            with self.assertRaises(ValueError):
                injection.inject(self.target, "fixture")
            self.target["extension"]["windows_python"] = "C:/Python/python.exe"
            with patch.object(injection, "load_installation_descriptor", return_value={"configured": False}):
                with self.assertRaises(injection.InjectionError):
                    injection.inject(self.target, "fixture")
        run.assert_not_called()

    def test_explicit_windows_execution_without_wsl_label_calls_once(self):
        with self.wsl(), patch.dict(os.environ, {}, clear=True), self.installation(), \
                self.child_run() as run, patch.object(injection, "_request") as http, \
                patch.object(injection, "CodexDesktop") as desktop:
            result = injection.inject(self.target, "unlabelled explicit fixture")
        run.assert_called_once()
        http.assert_not_called()
        desktop.assert_not_called()
        self.assertEqual(run.call_args.args[0][0], "/mnt/c/Python/python.exe")
        self.assertEqual(run.call_args.args[0][-1], "C:\\安装目录\\paos\\scripts\\runtime_injection.py")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["execution_environment"], "windows")

    def test_unknown_environment_and_non_receiver_rejected_before_native_access(self):
        for execution in ("auto", "windows"):
            target = {"runtime": "codex", "session_id": "fixture-self",
                      "extension": {"execution_environment": execution}}
            with patch.object(injection, "CodexDesktop") as desktop, self.child_run() as run:
                with self.assertRaises(ValueError):
                    injection.inject(target, "fixture")
            desktop.assert_not_called()
            run.assert_not_called()

    def test_windows_process_and_default_local_route_do_not_delegate(self):
        for explicit in (True, False):
            target = dict(self.target)
            target["extension"] = dict(self.target["extension"])
            if not explicit:
                target["extension"].pop("execution_environment")
            with patch.object(injection.os, "name", "nt"), \
                    patch.object(injection, "_check_stop"), patch.object(injection, "_native_lock"), \
                    patch.object(injection, "_codex", return_value={"via": "target_extension"}) as codex, self.child_run() as run:
                result = injection.inject(target, "fixture")
            codex.assert_called_once()
            run.assert_not_called()
            self.assertEqual(result.get("execution_environment"), "windows" if explicit else None)

    def test_windows_structured_offline_receipt_is_not_flattened_to_generic_rejection(self):
        receipt = {"accepted": False, "error": "dead", "error_code": "receiver_stale_registration",
                   "state": "receiver_offline", "repair_owner": "target_owner", "next_action": "prepare", "retry": False}
        with self.wsl(), patch.dict(os.environ, {"WSL_DISTRO_NAME": "fixture"}), self.installation(), \
                self.child_run(subprocess.CompletedProcess([], 1, json.dumps(receipt).encode(), b"")) as run:
            with self.assertRaises(injection.InjectionError) as error:
                injection.inject(self.target, "offline fixture")
        self.assertEqual(error.exception.state, "receiver_offline")
        self.assertEqual(error.exception.code, "receiver_stale_registration")
        self.assertEqual(error.exception.next_action, "prepare")
        run.assert_called_once()

    @unittest.skipUnless(os.name != "nt" and os.environ.get("WSL_DISTRO_NAME")
                         and os.environ.get("PAOS_TEST_WINDOWS_PYTHON"), "Explicit Windows readonly fixture only")
    def test_real_windows_readonly_grant_pid_check_never_calls_native_inject(self):
        source = Path(__file__).resolve().parents[2]
        python = os.environ["PAOS_TEST_WINDOWS_PYTHON"]
        def windows_path(path):
            return subprocess.run(["wslpath", "-w", str(path)], capture_output=True, check=True, text=True).stdout.strip()
        # A disposable Python process prints its Windows PID then exits, no Desktop context.
        exited = subprocess.run([injection.posix_windows_drive_locator(python), "-c", "import os; print(os.getpid())"],
                                capture_output=True, check=True, text=True)
        with tempfile.TemporaryDirectory(dir=source) as directory:
            root = Path(directory)
            runtime = root / "grant.json"
            runtime.write_text(json.dumps({"schema": "paos-codex-self-reminder/v1", "session_id": "fixture-self",
                "pid": int(exited.stdout.strip()), "endpoint": "http://127.0.0.1:1", "token": "private-fixture"}), encoding="utf-8")
            installation = root / "installation.json"
            installation.write_text(json.dumps({"schema": "paos-installation/v1", "source_root": windows_path(source),
                "library_roots_config": windows_path(root / "library.json")}), encoding="utf-8")
            self.target["extension"].update(receiver_runtime_file=windows_path(runtime), windows_python=python)
            with patch.object(injection, "resolve_installation_path", return_value=installation), \
                    patch.object(injection.subprocess, "run", wraps=subprocess.run) as run:
                view = injection._windows_native(self.target, None, None, receiver_status=True)
            run.assert_called_once()
            self.assertEqual(view["state"], "process_not_running")
            self.assertIs(view["pid_alive"], False)
            self.assertNotIn("private-fixture", json.dumps(view))
            self.assertNotIn("message", json.loads(run.call_args.kwargs["input"].decode()))

    @unittest.skipUnless(os.name != "nt" and os.environ.get("WSL_DISTRO_NAME")
                         and os.environ.get("PAOS_TEST_WINDOWS_PYTHON"), "Explicit WSL/Windows offline fixture only")
    def test_real_wsl_windows_process_rechecks_fixture_stop_before_any_native_access(self):
        source = Path(__file__).resolve().parents[2]
        def windows_path(path):
            return subprocess.run(["wslpath", "-w", str(path)], capture_output=True,
                                  check=True, text=True).stdout.strip()
        with tempfile.TemporaryDirectory(dir=source) as directory:
            root = Path(directory)
            stop = root / "STOP"
            stop.touch()
            installation = root / "installation.json"
            installation.write_text(json.dumps({"schema": "paos-installation/v1",
                "source_root": windows_path(source), "library_roots_config": windows_path(root / "library.json")}),
                encoding="utf-8")
            self.target["extension"]["windows_python"] = os.environ["PAOS_TEST_WINDOWS_PYTHON"]
            self.target["stop_file"] = windows_path(stop)
            with patch.object(injection, "resolve_installation_path", return_value=installation), \
                    patch.object(injection, "_check_stop"), \
                    patch.object(injection.subprocess, "run", wraps=subprocess.run) as run:
                with self.assertRaisesRegex(injection.InjectionError, "Explicit STOP"):
                    injection.inject(self.target, "offline UTF-8 fixture 中文 🐾")
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
