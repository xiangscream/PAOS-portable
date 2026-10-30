"""tests/test_collab_run.py — T-MA-01 窄测试（stdlib unittest，Windows Python 3.11）。"""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collab_run as m


class ProjectPairTests(unittest.TestCase):
    def test_accepts_non_3002_project(self):
        self.assertEqual(m.parse_project_pair("2001-s001", "2001-r001", None), "2001")

    def test_explicit_project_id(self):
        self.assertEqual(m.parse_project_pair("2001-s001", "2001-r001", "2001"), "2001")

    def test_mismatch_rejected(self):
        with self.assertRaises(SystemExit):
            m.parse_project_pair("2001-s001", "3002-r001", None)


class WinToWslTests(unittest.TestCase):
    def test_convert(self):
        self.assertEqual(
            m.win_to_wsl(r"C:\Users\remo\AppData\Local\Temp\run"),
            "/mnt/c/Users/remo/AppData/Local/Temp/run",
        )


class HooksJsonTests(unittest.TestCase):
    def test_backslash_roundtrip(self):
        cmd = r'powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\remo\stop_hook.ps1"'
        text = m.build_codex_hooks(cmd)
        data = json.loads(text)  # 以前 Bad JSON escape sequence: \U 会在这里炸
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], cmd)


class CountContinuesTests(unittest.TestCase):
    def test_strips_bom_and_skips_broken(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "events.jsonl"
            f.write_text(
                '\ufeff{"ts":"t","event":"hook_seen"}\n'
                "not-json\n"
                '{"ts":"t","event":"continue","step":1}\n',
                encoding="utf-8",
            )
            self.assertEqual(m.count_continues(Path(td)), 1)


def ns(**kw):
    return argparse.Namespace(**kw)


class CreateAndCleanupTests(unittest.TestCase):
    def test_create_rejects_nonpositive_limits(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(SystemExit):
                m.cmd_create(ns(run_dir=str(Path(td) / "r"), session_id="3002-s900", request_id="3002-r900", project_id=None, max_steps=0, ttl_minutes=30))
            with self.assertRaises(SystemExit):
                m.cmd_create(ns(run_dir=str(Path(td) / "r"), session_id="3002-s900", request_id="3002-r900", project_id=None, max_steps=3, ttl_minutes=0))

    def test_cleanup_clears_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            (run_dir / "run.json").write_text(
                json.dumps({"schema": "collab-run/v1", "run_id": "run-x", "project_id": "3002",
                            "session_id": "3002-s900", "request_id": "3002-r900",
                            "max_steps": 3, "ttl_minutes": 30, "expires_at": "2099-01-01T00:00:00Z"}),
                encoding="utf-8",
            )
            pointer = Path(td) / "pointer.json"
            m.ACTIVE_POINTER = pointer  # 隔离全局指针
            m.cmd_activate(ns(run_dir=str(run_dir), force=False))
            self.assertTrue(pointer.is_file())
            m.cmd_cleanup(ns(run_dir=str(run_dir), yes=True))
            self.assertFalse(run_dir.exists())
            self.assertFalse(pointer.exists())


if __name__ == "__main__":
    unittest.main()