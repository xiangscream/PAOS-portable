"""tests/test_hook_blackbox.py — Codex Stop-hook 黑盒测试（Windows PowerShell）。

覆盖复评仍未闭合的 3 条路径：日志持久化 gate、step_no 类型/取值错误、负步数。
"""
import json
import os
import platform
import subprocess
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1] / "codex_stop_adapter.ps1"


def make_run(root: Path, max_steps: int = 3, session: str = "3002-s900", request: str = "3002-r900") -> dict:
    run = {
        "schema": "collab-run/v1",
        "run_id": "run-blackbox",
        "project_id": "3002",
        "session_id": session,
        "request_id": request,
        "max_steps": max_steps,
        "ttl_minutes": 30,
        "expires_at": "2099-01-01T00:00:00Z",
    }
    (root / "run.json").write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
    return run


def set_readonly(p: Path):
    subprocess.run(["cmd", "/c", "attrib", "+r", str(p)], capture_output=True)


def clear_readonly(p: Path):
    subprocess.run(["cmd", "/c", "attrib", "-r", str(p)], capture_output=True)


def run_adapter(run_dir: Path, pointer_dir: Path):
    pointer_dir.mkdir(parents=True, exist_ok=True)
    pointer = pointer_dir / "paos-collab-active-run.json"
    pointer.write_text(json.dumps({"run_dir": str(run_dir), "active": True, "run_id": "run-blackbox"}), encoding="utf-8")
    env = dict(os.environ)
    env["TEMP"] = str(pointer_dir)
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ADAPTER)],
        capture_output=True, text=True, env=env, timeout=60,
    )
    return p


@unittest.skipUnless(platform.system() == "Windows", "black-box PowerShell hook tests require Windows")
class HookBlackboxTests(unittest.TestCase):

    def test_log_write_failure_never_blocks_and_keeps_marker(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            run_dir.mkdir()
            make_run(run_dir)
            events = run_dir / "events.jsonl"
            events.write_text("", encoding="utf-8")
            set_readonly(events)  # 计数落盘必失败
            try:
                marker = run_dir / "marker.json"
                marker.write_text(json.dumps({
                    "run_id": "run-blackbox", "session_id": "3002-s900", "request_id": "3002-r900",
                    "step_no": 1, "expires_at": "2099-01-01T00:00:00Z", "reason": "B",
                }), encoding="utf-8")
                p = run_adapter(run_dir, base / "tmp")
                self.assertEqual(p.returncode, 0)
                self.assertEqual(p.stdout.strip(), "")
                self.assertTrue(marker.exists(), "落盘失败时不得消费 marker，应放回原位")
            finally:
                clear_readonly(events)

    def test_step_no_bad_type_is_marker_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            run_dir.mkdir()
            make_run(run_dir)
            (run_dir / "events.jsonl").write_text("", encoding="utf-8")
            (run_dir / "marker.json").write_text(json.dumps({
                "run_id": "run-blackbox", "session_id": "3002-s900", "request_id": "3002-r900",
                "step_no": "oops", "expires_at": "2099-01-01T00:00:00Z", "reason": "bad",
            }), encoding="utf-8")
            p = run_adapter(run_dir, base / "tmp")
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout.strip(), "")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("marker_invalid_step", events)
            self.assertFalse((run_dir / "marker.json").exists())

    def test_valid_marker_blocks_once_and_persists_count(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            run_dir.mkdir()
            run = make_run(run_dir)
            (run_dir / "events.jsonl").write_text("", encoding="utf-8")
            (run_dir / "marker.json").write_text(json.dumps({
                "run_id": run["run_id"], "session_id": run["session_id"], "request_id": run["request_id"],
                "step_no": 1, "expires_at": run["expires_at"], "reason": "B",
            }), encoding="utf-8")
            p = run_adapter(run_dir, base / "tmp")
            self.assertEqual(p.returncode, 0)
            self.assertIn("continue-one-step", p.stdout)
            self.assertFalse((run_dir / "marker.json").exists())
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"event":"continue"', events)
            self.assertIn('"step":1', events)

    def test_max_steps_reached_never_blocks_and_keeps_marker(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            run_dir.mkdir()
            run = make_run(run_dir, max_steps=1)
            (run_dir / "events.jsonl").write_text(
                '{"ts":"t","event":"continue","step":1}\n', encoding="utf-8"
            )
            (run_dir / "marker.json").write_text(json.dumps({
                "run_id": run["run_id"], "session_id": run["session_id"], "request_id": run["request_id"],
                "step_no": 2, "expires_at": run["expires_at"], "reason": "over budget",
            }), encoding="utf-8")
            p = run_adapter(run_dir, base / "tmp")
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout.strip(), "")
            self.assertTrue((run_dir / "marker.json").exists(), "达上限后不得消费 marker")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(events.count('"event":"continue"'), 1)

    def test_step_no_non_positive_is_marker_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            run_dir.mkdir()
            make_run(run_dir)
            (run_dir / "events.jsonl").write_text("", encoding="utf-8")
            (run_dir / "marker.json").write_text(json.dumps({
                "run_id": "run-blackbox", "session_id": "3002-s900", "request_id": "3002-r900",
                "step_no": 0, "expires_at": "2099-01-01T00:00:00Z", "reason": "zero",
            }), encoding="utf-8")
            p = run_adapter(run_dir, base / "tmp")
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout.strip(), "")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("marker_invalid_step", events)


if __name__ == "__main__":
    unittest.main()