"""Optional board against real disposable v4 Homes; no production or models."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
from front.paos_front_server import Board, BoardProblem, make_server
from paos_installation import write_installation_descriptor
from paos_library import ensure_skill_library, ensure_workflow_library, register_library_roots
from paos_notice import handle_notice, list_notices
from paos_registry import ProjectRegistry, RegistryProblem
from paos_todo import render_todo, write_todo


class BoardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="portable-board-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve() / "中文 空格工作区"
        self.base.mkdir()
        self.install = self.base / "installation.json"
        self.libs = self.base / "library-roots.json"
        workflow, skill = self.base / "workflow", self.base / "skill"
        ensure_workflow_library(workflow)
        ensure_skill_library(skill)
        (workflow / "Guides" / "working.md").write_text(
            "---\nschema: paos-workflow/v1\nid: guide-working\ntitle: 工作方法\nstatus: active\n---\n# 方法\n",
            encoding="utf-8")
        register_library_roots(self.libs, workflow_root=workflow, skill_root=skill)
        write_installation_descriptor(self.install,
                                      source_root=str(PACKAGE / "code/personal-agent-os"),
                                      data_root=str(self.base / "data"), library_roots_config=str(self.libs))
        self.registry = ProjectRegistry(self.install)
        self.roots = {}
        for project, homes in (("1001", ["1001-s001", "1001-s002"]), ("2001", ["2001-s009"])):
            root = self.base / f"项目-{project}"
            root.mkdir()
            self.roots[project] = root
            (root / "INDEX.md").write_text(f"# 项目 {project}\n唯一口径在本目录。", encoding="utf-8")
            self.registry.register(project, root_path=str(root), coordinator_home_id=homes[0], homes=homes)
            for home_id in homes:
                home = root / "Workstations" / home_id
                (home / "mailbox").mkdir(parents=True)
                (home / "notices").mkdir()
                (home / "ENTRY.md").write_text("# 从本人工位恢复", encoding="utf-8")
                write_todo(home / "TODO.md", render_todo(
                    home_kind="project_agent", home_id=home_id, project_id=project,
                    objective=f"维护项目 {project}", next_action="读取已交原件",
                    tasks=[{"id": "T-001", "title": "接续原件", "state": "doing"}]))
        self.board = Board(self.install)

    def test_v4_and_registered_project_not_old_machine_defaults(self):
        with patch.dict(os.environ, {"PAOS_INSTALLATION_FILE": "missing-old-install.json",
                                     "PAOS_BASE_URL": "not a service"}):
            result = self.board.dashboard()
        self.assertEqual(result["project"], "1001")
        self.assertEqual([a["id"] for a in result["agents"]], ["1001-s001", "1001-s002"])
        self.assertEqual(result["agents"][0]["objective"], "维护项目 1001")
        self.assertEqual(result["agents"][0]["tasks"]["doing"], 1)
        self.assertEqual(result["cat"]["error_code"], "cat_not_configured")
        self.assertEqual(result["examples"]["workflow"][0]["id"], "guide-working")
        other = self.board.dashboard("2001")
        self.assertEqual([a["id"] for a in other["agents"]], ["2001-s009"])
        self.assertIn("项目 2001", other["index"])
        with self.assertRaises(RegistryProblem):
            self.board.dashboard("3002")

    def test_real_cli_hint_delivers_once_and_notice_handling_is_projected(self):
        example = self.board.examples()["workflow"][0]
        result = self.board.hint("1001-s002", example)
        self.assertTrue(result["ok"], result)
        home = self.roots["1001"] / "Workstations/1001-s002"
        notices = list_notices(home)
        self.assertEqual(notices["pending_count"], 1)
        self.assertEqual(len(list((home / "mailbox").glob("*.md"))), 1)
        handle_notice(home_path=home, notice_id=notices["items"][0]["notice_id"], resolution="已采纳为参考")
        # The original Notice still declares pending; the formal reader merges its handled sidecar.
        self.assertIn('state: "pending"', next((home / "notices").glob("*.md")).read_text(encoding="utf-8"))
        self.assertEqual(self.board.agent("1001-s002")["pending_notices"], 0)

    def test_invalid_home_is_visible_without_hiding_other_agents(self):
        home = self.roots["1001"] / "Workstations/1001-s002"
        (home / "TODO.md").write_text("old v3 or broken original", encoding="utf-8")
        rows = self.board.dashboard("1001")["agents"]
        self.assertTrue(rows[0]["ok"])
        self.assertFalse(rows[1]["ok"])
        self.assertIn("error_code", rows[1])
        self.assertNotIn("pending_notices", rows[1])

    def test_other_home_todo_cannot_be_displayed_as_this_agent(self):
        home = self.roots["1001"] / "Workstations/1001-s002"
        (home / "TODO.md").write_text(render_todo(home_kind="project_agent", home_id="2001-s009",
                                                  project_id="2001", objective="别人的责任", next_action="接续"), encoding="utf-8")
        with self.assertRaises(BoardProblem) as raised:
            self.board.agent("1001-s002")
        self.assertEqual(raised.exception.code, "todo_identity_mismatch")

    def test_read_side_does_not_require_cat_or_core_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("network not allowed")):
            self.assertTrue(self.board.dashboard()["ok"])
        self.assertEqual(self.board.create_room("讨论", ["1001-s001", "1001-s002"])["error_code"],
                         "cat_not_configured")

    def test_cli_timeout_keeps_result_unknown_and_does_not_repeat(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("paos", 90)) as run:
            result = self.board.run_paos(["health"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result["error_code"], "cli_result_unknown")
        self.assertIs(result["retry"], False)

    def test_cli_cannot_start_reports_definite_failure_without_retrying(self):
        with patch("subprocess.run", side_effect=PermissionError("cannot start this Python")) as run:
            result = self.board.run_paos(["health"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result["error_code"], "cli_start_failed")
        self.assertEqual(result["phase"], "process_start")
        self.assertEqual(result["error_type"], "PermissionError")
        self.assertTrue(result["retry"])

    def test_failed_join_cannot_report_success_or_send_message(self):
        with patch.object(self.board, "cat", return_value={"ok": False, "error_code": "seat_failed"}) as call:
            result = self.board.send_message("room-fixture", "human", "消息", "fixture-id")
        self.assertFalse(result["ok"])
        self.assertEqual(call.call_count, 1)

    def test_http_serves_same_file_reader_and_explicit_error(self):
        server = make_server(self.board, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        origin = f"http://127.0.0.1:{server.server_port}"
        with urlopen(origin + "/api/dashboard?project=1001") as response:
            data = json.load(response)
        self.assertEqual(data["coordinator"], "1001-s001")
        with urlopen(origin + "/") as response:
            self.assertIn("PAOS 画板", response.read().decode("utf-8"))
        request = Request(origin + "/api/room", data=json.dumps(
            {"title": "只测未配置", "members": ["1001-s001", "1001-s002"]}).encode(),
            headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            failure = json.load(response)
        self.assertFalse(failure["ok"])
        self.assertEqual(failure["error_code"], "cat_not_configured")


if __name__ == "__main__":
    unittest.main()
