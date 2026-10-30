# -*- coding: utf-8 -*-
"""Tests for the one-time workless installation migration (offline, v2 -> v3)."""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
CORE = REPO_ROOT / "attention-dashboard-v1-static"
for p in (str(SCRIPTS), str(CORE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import migrate_workless_installation as mig  # noqa: E402
from project_domain import (  # noqa: E402
    ARCHIVED_WORK_ITEMS_KEY,
    ARCHIVED_WORK_SUGGESTIONS_KEY,
    PROJECT_SCHEMA,
)
from paos_installation import write_installation_descriptor  # noqa: E402
from project_schema import validate_project  # noqa: E402


def write_local_installation(tmp: Path, rooter_home: Path | None = None) -> Path:
    """本地的安装描述符：测试绝不读、也绝不写真实登记。

    登记 Rooter Home 是迁移范围的一部分，所以每次跑都必须显式指着测试自己的
    描述符，否则 `--apply` 会按真实登记去找真实 Rooter Home。
    """
    descriptor = tmp / "installation.json"
    write_installation_descriptor(
        descriptor,
        source_root=str(tmp / "Source"),
        data_root=str(tmp / "Source" / "private-data"),
        library_roots_config=str(tmp / "library-roots.json"),
        rooter_home=str(rooter_home) if rooter_home is not None else str(tmp / "rooter-001"),
    )
    return descriptor


def v2_project(project_id="3002"):
    """A realistic v2 project: one Work with evidence, one closed Session on it."""
    return {
        "schema": "paos-project/v2",
        "id": project_id,
        "name": "迁移测试",
        "area": "personal",
        "project_type": "finite",
        "status": "active",
        "priority": 1,
        "root_path": "",
        "human": {"original_requirement": "", "current_commitment": "", "ddl": "", "confirmed_at": ""},
        "generated": {"stage": "", "progress_and_results": "", "recent_change": "", "current_gap": "", "tagline": ""},
        "next_items": [],
        "key_files": [],
        "work_items": [
            {
                "id": f"{project_id}-w001",
                "title": "历史 Work",
                "objective": "被归档",
                "done_when": ["保留原样"],
                "status": "done",
                "priority": 1,
                "depends_on": [],
                "note": "",
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-02T00:00:00Z",
                "evaluations": [
                    {
                        "score": 8,
                        "comment": "好",
                        "actor": "human",
                        "created_at": "2026-08-02T00:00:00Z",
                        "operation_id": "op-eval-1",
                    }
                ],
            }
        ],
        "sessions": [
            {
                "id": f"{project_id}-s001",
                "handshake_id": "",
                "identity_id": "implementer",
                "model_id": "",
                "runtime_id": "rt",
                "agent_label": "",
                "work_item_ids": [f"{project_id}-w001"],
                "current_work_item_id": f"{project_id}-w001",
                "current_cycle": 1,
                "cycles": [
                    {
                        "number": 1,
                        "work_item_id": f"{project_id}-w001",
                        "mission": {"objective": "做事", "done_when": ["做完"]},
                        "entry": {"project_revision": 1, "context_pack_id": f"{project_id}-cp001", "context_level": "standard"},
                        "acknowledgement": {"understood_objective": "做事"},
                        "progress": {"status": "done", "summary": "完成", "percent": None, "blockers": [], "next_actions": []},
                        "note_for_next_session": "",
                        "started_at": "2026-08-01T00:00:00Z",
                        "last_active_at": "2026-08-02T00:00:00Z",
                        "ended_at": "2026-08-02T00:00:00Z",
                        "end_kind": "agent_close",
                        "end_reason": "",
                        "close_result": {
                            "result": "completed",
                            "result_summary": "做完",
                            "remaining_work": [],
                            "recommended_next_identity_id": "",
                            "closed_at": "2026-08-02T00:00:00Z",
                        },
                        "close_result_history": [
                            {
                                "result": "completed",
                                "result_summary": "做完",
                                "remaining_work": [],
                                "recommended_next_identity_id": "",
                                "closed_at": "2026-08-02T00:00:00Z",
                            }
                        ],
                        "close_operation_id": "op-close-1",
                        "operation_id": "op-open-1",
                    }
                ],
                "request_ids": [],
                "mission": {"objective": "做事", "done_when": ["做完"]},
                "entry": {"project_revision": 1, "context_pack_id": f"{project_id}-cp001", "context_level": "standard"},
                "runtime_session": {"environment": "", "title": "", "session_id": "", "source_path": ""},
                "acknowledgement": None,
                "progress": {"status": "done", "summary": "完成", "percent": None, "blockers": [], "next_actions": []},
                "status": "completed",
                "started_at": "2026-08-01T00:00:00Z",
                "last_active_at": "2026-08-02T00:00:00Z",
                "closed_at": "2026-08-02T00:00:00Z",
                "close_result": {
                    "result": "completed",
                    "result_summary": "做完",
                    "remaining_work": [],
                    "recommended_next_identity_id": "",
                    "closed_at": "2026-08-02T00:00:00Z",
                },
                "entry_materials": [],
            }
        ],
        "organization": {"coordinator_session_id": None},
        "artifacts": [
            {
                "id": f"{project_id}-a001",
                "path": "out/x.md",
                "type": "doc",
                "purpose": "",
                "work_item_ids": [f"{project_id}-w001"],
                "source_session_id": f"{project_id}-s001",
                "replaces": None,
                "status": "current",
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-01T00:00:00Z",
            }
        ],
        "requests": [
            {
                "id": f"{project_id}-r001",
                "request_type": "assignment",
                "requires_human": False,
                "target_identity_id": "reviewer",
                "target_session_id": None,
                "target_work_item_id": f"{project_id}-w001",
                "description": "请验收",
                "status": "resolved",
                "source_session_id": f"{project_id}-s001",
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-02T00:00:00Z",
                "resolution": "done",
            }
        ],
        "decisions": [],
        "work_suggestions": [
            {
                "id": f"{project_id}-g001",
                "title": "建议",
                "objective": "被归档",
                "done_when": ["条件"],
                "status": "open",
                "source_session_id": f"{project_id}-s001",
                "source_work_item_id": f"{project_id}-w001",
                "created_at": "2026-08-01T00:00:00Z",
                "resolved_at": "",
                "resolution_reason": "",
            }
        ],
        "ledger": [
            {
                "event_id": f"{project_id}-e001",
                "event_type": "session.opened",
                "operation_id": "op-open-1",
                "base_revision": 0,
                "revision": 1,
                "summary": "open",
                "changes": [],
                "occurred_at": "2026-08-01T00:00:00Z",
            }
        ],
        "operation_receipts": {
            "op-open-1": {
                "schema": "paos-operation-receipt/v1",
                "operation_id": "op-open-1",
                "event_id": f"{project_id}-e001",
                "revision": 1,
            }
        },
        "revision": 1,
        "updated_at": "2026-08-01T00:00:00Z",
    }


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "registry"
        (self.root / "projects").mkdir(parents=True)
        self.pid = "3002"
        self.path = self.root / "projects" / f"{self.pid}.json"
        self.path.write_text(json.dumps(v2_project(self.pid), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.installation = write_local_installation(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _migrate(self, **kwargs):
        return mig.migrate(self.root, installation_file=self.installation, **kwargs)

    def test_dry_run_writes_nothing(self):
        before = self.path.read_text(encoding="utf-8")
        report = self._migrate(apply=False)
        self.assertEqual(report["migrated"], 1)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)
        self.assertFalse((self.root / "backups").exists())

    def test_apply_converts_and_preserves_evidence(self):
        report = self._migrate(apply=True)
        self.assertEqual(report["migrated"], 1)
        after = self._load()
        validate_project(after)  # v3 全量校验必须通过

        self.assertEqual(after["schema"], PROJECT_SCHEMA)
        # 退役对象原样归档
        archived = after[ARCHIVED_WORK_ITEMS_KEY]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["id"], f"{self.pid}-w001")
        self.assertEqual(archived[0]["evaluations"][0]["operation_id"], "op-eval-1")
        self.assertEqual(len(after[ARCHIVED_WORK_SUGGESTIONS_KEY]), 1)
        self.assertNotIn("work_items", after)
        self.assertNotIn("work_suggestions", after)

        # 当前事实摘掉 Work 绑定
        session = after["sessions"][0]
        for key in ("work_item_ids", "current_work_item_id", "work_released"):
            self.assertNotIn(key, session)
        self.assertNotIn("target_work_item_id", after["requests"][0])
        self.assertNotIn("work_item_ids", after["artifacts"][0])

        # 历史 Cycle 的 work_item_id 作为惰性历史字段留在原地
        self.assertEqual(session["cycles"][0]["work_item_id"], f"{self.pid}-w001")
        # 证据未被改写
        self.assertEqual(session["close_result"]["result_summary"], "做完")
        self.assertEqual(len(session["cycles"][0]["close_result_history"]), 1)
        self.assertEqual(after["operation_receipts"], v2_project(self.pid)["operation_receipts"])

        # 只追加一条迁移事件
        self.assertEqual(len(after["ledger"]), 2)
        self.assertEqual(after["ledger"][1]["event_type"], mig.MIGRATION_EVENT)
        self.assertEqual(after["ledger"][0]["event_type"], "session.opened")
        self.assertEqual(after["revision"], 2)

    def test_apply_creates_before_state_backup(self):
        report = self._migrate(apply=True)
        backup = Path(report["backup_dir"]) / f"{self.pid}.json"
        self.assertTrue(backup.exists())
        original = json.loads(backup.read_text(encoding="utf-8"))
        self.assertEqual(original["schema"], "paos-project/v2")
        self.assertEqual(len(original["work_items"]), 1)

    def test_idempotent_second_run_skips(self):
        self._migrate(apply=True)
        first = self.path.read_text(encoding="utf-8")
        report = self._migrate(apply=True)
        self.assertEqual(report["migrated"], 0)
        self.assertEqual(report["skipped"], 1)
        self.assertEqual(self.path.read_text(encoding="utf-8"), first)

    def test_unknown_schema_aborts_without_writing_anything(self):
        good = self.path.read_text(encoding="utf-8")
        bad = self.root / "projects" / "3999.json"
        bad.write_text(json.dumps({"schema": "paos-project/vX", "id": "3999"}), encoding="utf-8")
        with self.assertRaises(mig.MigrationError):
            self._migrate(apply=True)
        # 全有或全无：合法文件也不能被写
        self.assertEqual(self.path.read_text(encoding="utf-8"), good)
        self.assertEqual(json.loads(bad.read_text(encoding="utf-8"))["schema"], "paos-project/vX")

    def test_conflicting_archive_state_is_rejected(self):
        project = v2_project(self.pid)
        project[ARCHIVED_WORK_ITEMS_KEY] = [{"id": "x"}]
        self.path.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(mig.MigrationError):
            self._migrate(apply=True)

    def test_conservation_catches_ledger_change(self):
        plan = mig.plan_project(self.path.read_text(encoding="utf-8"), self.path)
        tampered = copy.deepcopy(plan["project"])
        tampered["ledger"] = tampered["ledger"][:1]  # 丢掉追加的迁移事件
        problems = mig._conservation(plan["before"], tampered)
        self.assertTrue(any("ledger" in p for p in problems))

    def test_only_filter(self):
        other = self.root / "projects" / "3001.json"
        payload = v2_project("3001")
        payload["area"] = "personal"
        other.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        report = self._migrate(apply=True, only="3001")
        self.assertEqual(report["migrated"], 1)
        self.assertEqual(json.loads(other.read_text(encoding="utf-8"))["schema"], PROJECT_SCHEMA)
        self.assertEqual(self._load()["schema"], "paos-project/v2")


# ── Home 轴：交给 S032 的 paos_v13_convert，本工具不自造转换 ──

V2_TODO = """---
schema: paos-todo/v2
project_id: 3002
agent_id: 3002-s001
---

# 当前工作

## 当前
Work：3002-w001
目标：把工作做完
阶段：正在做
下一步：继续
等待：（无）
成果：docs/result.md
在途：（无）

## 待办

- [ ] T-001 一条待办
  完成方式：写清楚

## 继续阅读
- ENTRY.md
"""

# 真实安装里 Home 的实际形态：已经迁过一次，是 v3，且仍带 current_work。
V3_TODO = """---
schema: "paos-todo/v3"
home_kind: "project_agent"
home_id: "3002-s001"
project_id: "3002"
---

# Current

objective: "把工作做完"
approved_scope: "本工位范围"
current_work: "3002-w001"
stage: "正在做"
next_action: "继续"
waiting: "（无）"
results: "docs/result.md"
result_refs: []
context_refs: []
history_ref: ""
"""

# 真实 Home 里确实存在的、渲染器不认识的 Current 字段（3002-s010 就是这三个）。
# 先去掉 V3_TODO 自带的空 history_ref，避免同一字段出现两次（YAML 重键只留最后一个）。
V3_TODO_EXTRA_FIELDS = V3_TODO.replace('history_ref: ""\n', "").replace(
    'current_work: "3002-w001"\n',
    'current_work: "3002-w001"\n'
    'latest_readback: "上一轮回读"\n'
    'history_ref: "Archive/3002-s001/TODO-BEFORE.md"\n'
    'boundaries: "不删 Mail/Notice"\n',
)

# 只摘 current_work、其余照旧的候选 —— 这才是合格收敛。
V3_CANDIDATE_GOOD = V3_TODO_EXTRA_FIELDS.replace('current_work: "3002-w001"\n', "")

# 会把三个额外字段一起抹掉的候选（接口静默丢字段时的真实形态）。
V3_CANDIDATE_DROPS_FIELDS = V3_TODO_EXTRA_FIELDS.replace(
    'current_work: "3002-w001"\n'
    'latest_readback: "上一轮回读"\n'
    'history_ref: "Archive/3002-s001/TODO-BEFORE.md"\n'
    'boundaries: "不删 Mail/Notice"\n',
    'latest_readback: ""\nhistory_ref: ""\nboundaries: ""\n',
)

# 3002-s032 的真实形态：列表被写成字符串，接口按字符拆成上百项。
V3_TODO_STRING_REFS = V3_TODO.replace(
    "result_refs: []", "result_refs: \"['a.md', 'b.md']\""
)
V3_CANDIDATE_CHAR_SPLIT = V3_TODO.replace(
    "result_refs: []", 'result_refs: ["[", "a", ".", "m"]'
)


class HomeAxisTestCase(unittest.TestCase):
    """公共夹具：一个项目 + 工位 + 一份本地的安装描述符（绝不碰真实登记）。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "registry"
        (self.root / "projects").mkdir(parents=True)
        self.pid = "3002"
        self.agent = "3002-s001"
        payload = v2_project(self.pid)
        payload["root_path"] = str(self.tmp)
        (self.root / "projects" / f"{self.pid}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self.home = self.tmp / "Workstations" / self.agent
        (self.home / "mailbox").mkdir(parents=True)
        self.rooter_home = self.tmp / "PAOS-Rooter" / "rooter-001"
        (self.rooter_home / "mailbox").mkdir(parents=True)
        self.installation = write_local_installation(self.tmp, rooter_home=self.rooter_home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_todo(self, text, home=None):
        ((home or self.home) / "TODO.md").write_text(text, encoding="utf-8")

    def _todo(self, home=None):
        return ((home or self.home) / "TODO.md").read_text(encoding="utf-8")

    def _migrate(self, **kwargs):
        kwargs.setdefault("installation_file", self.installation)
        return mig.migrate(self.root, **kwargs)

    def _verdict(self, report, home_kind="project_agent", home_id=None):
        wanted = self.agent if home_id is None else home_id
        for item in report["home_details"]:
            if item["home_kind"] == home_kind and str(item["home_id"]) == str(wanted):
                return item
        raise AssertionError(f"报告里没有这个 Home：{home_kind}/{wanted}")

    def _fingerprint(self, *bases) -> dict:
        """Home 侧（Current／Notice／Mailbox）的逐文件指纹，用来证明"零写入"。"""
        digest = {}
        for base in bases or (self.home, self.rooter_home):
            for item in sorted(Path(base).rglob("*")):
                if item.is_file():
                    digest[str(item.relative_to(self.tmp))] = hashlib.sha256(
                        item.read_bytes()
                    ).hexdigest()
        return digest

    def _project_bytes(self) -> bytes:
        return (self.root / "projects" / f"{self.pid}.json").read_bytes()

    def _stale_renderer(self):
        """两条线共用的"渲染器还是旧版"夹具：本线与已配对线都能据此判阻塞。"""
        from unittest import mock

        def render_todo_v3(home_kind, home_id, project_id="", objective="",
                           current_work="", **_kw):
            raise AssertionError("stale renderer 不应被真正调用")

        return mock.patch("paos_todo_v3.render_todo_v3", render_todo_v3)


class HomeInterfaceGuardTests(HomeAxisTestCase):
    """接口没配对时，宁可拒绝，也不产出仍带 current_work 的 TODO。"""

    def test_stale_renderer_blocks_both_axes_and_leaves_bytes_untouched(self):
        self._write_todo(V3_TODO)

        import inspect
        from unittest import mock
        import paos_todo_v3
        stale_signature = "def stale(key): pass"

        def stale_renderer(home_kind: str, home_id: str, project_id: str = "",
                           objective: str = "", current_work: str = "", **_kw):
            """any stale renderer signature keeps current_work in the contract."""
            pass

        with mock.patch("paos_todo_v3.render_todo_v3", stale_renderer):
            self.assertTrue(mig.convert_interface_problem())
            project_before = self._project_bytes()
            home_before = self._fingerprint()
            # apply 在规划之后、首次写入之前就拒绝：连 Project 文件都不动。
            with self.assertRaises(mig.MigrationBlocked) as caught:
                self._migrate(apply=True)
            self.assertEqual(
                caught.exception.blocked[0]["reason"],
                "todo_renderer_still_writes_current_work",
            )
            self.assertEqual(self._project_bytes(), project_before)
            self.assertEqual(self._fingerprint(), home_before)
            self.assertEqual(self._todo(), V3_TODO)
            self.assertEqual(mig.main(["--root", str(self.root), "--apply",
                                       "--installation-file", str(self.installation)]), 3)
            self.assertEqual(self._project_bytes(), project_before)
        self.assertFalse(mig.convert_interface_problem())

    def test_missing_v3_convergence_interface_is_reported_by_name(self):
        """名字不在就报名字；接口由 S032 的固定版给出，本工具不自行实现。"""
        if mig.plan_v3_home_convergence is None:
            self.assertIn("v3_converge_interface_missing", mig.v3_converge_interface_problem())
        else:
            self.assertEqual(mig.v3_converge_interface_problem(), "")

    def test_v2_home_verdicts_follow_the_real_renderer(self):
        """Fresh renderer → v2 Home enters the V2 axis normally;
        stale renderer (guarded case) → named blocked, bytes untouched."""
        self._write_todo(V2_TODO)
        report = self._migrate(apply=False)
        self.assertEqual(self._verdict(report)["state"], mig.HOME_CONVERTIBLE)

        import unittest
        from unittest import mock
        import paos_todo_v3

        def stale_renderer(home_kind: str, home_id: str, project_id: str = "",
                           objective: str = "", current_work: str = "", **_kw):
            pass

        with mock.patch("paos_todo_v3.render_todo_v3", stale_renderer):
            blocked = self._migrate(apply=False)
            self.assertEqual(
                self._verdict(blocked)["state"], mig.HOME_BLOCKED_INTERFACE
            )
            # apply must still refuse the stale renderer and leave the file alone
            self.assertEqual(mig.main(["--root", str(self.root), "--apply",
                                       "--installation-file", str(self.installation)]), 3)
            self.assertEqual(self._todo(), V2_TODO)

    def test_project_only_run_skips_the_home_axis(self):
        self._write_todo(V3_TODO)
        report = self._migrate(apply=True, homes=False)
        self.assertEqual(set(report["homes"].values()), {0})
        self.assertEqual(report["home_details"], [])
        self.assertEqual(self._todo(), V3_TODO)


class BlockedHomePreflightTests(HomeAxisTestCase):
    """规划期已知收敛不了的 Home：在第一次写入之前退出，Project／Current／Notice 零写入。"""

    def test_blocked_home_aborts_before_the_first_write(self):
        self._write_todo(V3_TODO)
        (self.home / "notices").mkdir()
        (self.home / "notices" / "notice-x.md").write_text(
            'schema: "paos-notice/v1"\nstate: "pending"\n', encoding="utf-8"
        )
        project_before = self._project_bytes()
        home_before = self._fingerprint()

        with self._stale_renderer():
            with self.assertRaises(mig.MigrationBlocked):
                self._migrate(apply=True)

        self.assertEqual(self._project_bytes(), project_before)
        self.assertEqual(self._fingerprint(), home_before)
        self.assertFalse((self.root / "backups").exists())
        self.assertEqual(list(self.tmp.rglob("v3-converge")), [])

    def test_blocked_home_exits_three_from_the_command_line_without_writing(self):
        self._write_todo(V3_TODO)
        project_before = self._project_bytes()

        with self._stale_renderer():
            code = mig.main(["--root", str(self.root), "--apply",
                             "--installation-file", str(self.installation)])

        self.assertEqual(code, 3)
        self.assertEqual(self._project_bytes(), project_before)
        self.assertFalse((self.root / "backups").exists())

    def test_each_blocked_home_is_named_with_identity_and_reason(self):
        """项目 Home 与登记的 Rooter Home 各自具名，不合并成一条统计。"""
        self._write_todo(V3_TODO)
        self._write_todo(V3_TODO, home=self.rooter_home)

        with self._stale_renderer():
            with self.assertRaises(mig.MigrationBlocked) as caught:
                self._migrate(apply=True)

        named = sorted(
            (item["home_kind"], item["home_id"], item["reason"])
            for item in caught.exception.blocked
        )
        self.assertEqual(
            named,
            [
                ("project_agent", self.agent, "todo_renderer_still_writes_current_work"),
                ("rooter", "rooter-001", "todo_renderer_still_writes_current_work"),
            ],
        )
        message = str(caught.exception)
        self.assertIn(self.agent, message)
        self.assertIn("rooter-001", message)

    def test_project_axis_alone_still_runs_when_homes_are_blocked(self):
        """`--skip-homes` 是明确的"只迁项目文件"，不是自动跳过有问题的 Home。"""
        self._write_todo(V3_TODO)
        project_before = self._project_bytes()
        home_before = self._fingerprint()

        with self._stale_renderer():
            report = self._migrate(apply=True, homes=False)
            self.assertEqual(report["homes"], {state: 0 for state in mig.HOME_STATES})
            self.assertEqual(
                mig.main(["--root", str(self.root), "--apply", "--skip-homes",
                          "--installation-file", str(self.installation)]), 0)

        self.assertNotEqual(self._project_bytes(), project_before)
        self.assertEqual(self._fingerprint(), home_before)


class HomeEnumerationTests(HomeAxisTestCase):
    """迁移范围以磁盘上的 Home 为准，不以 Session 记录为准。"""

    def test_homes_come_from_disk_not_from_session_records(self):
        payload = json.loads((self.root / "projects" / f"{self.pid}.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["sessions"]), 1)  # 夹具项目里有 1 条 Session
        for extra in ("3002-s002", "3002-s003"):
            (self.tmp / "Workstations" / extra / "mailbox").mkdir(parents=True)
            self._write_todo(V3_TODO.replace('"3002-s001"', f'"{extra}"'),
                             home=self.tmp / "Workstations" / extra)
        self._write_todo(V3_TODO)
        report = self._migrate(apply=False)
        project_homes = [i for i in report["home_details"] if i["home_kind"] == "project_agent"]
        self.assertEqual(sorted(i["home_id"] for i in project_homes),
                         ["3002-s001", "3002-s002", "3002-s003"])

    def test_project_without_root_path_is_reported_and_does_not_abort(self):
        payload = json.loads((self.root / "projects" / f"{self.pid}.json").read_text(encoding="utf-8"))
        payload["root_path"] = ""
        (self.root / "projects" / f"{self.pid}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = self._migrate(apply=False)
        verdict = self._verdict(report, home_id="")
        self.assertEqual(verdict["state"], mig.HOME_ABSENT)
        self.assertEqual(verdict["reason"], "project_root_path_empty")

    def test_rooter_home_comes_from_the_registration_without_a_project_session(self):
        self._write_todo(V3_TODO, home=self.rooter_home)
        report = self._migrate(apply=False)
        verdict = self._verdict(report, home_kind="rooter", home_id="rooter-001")
        self.assertEqual(verdict["project_id"], "")
        self.assertEqual(verdict["home_path"], str(self.rooter_home))
        # manifest 落在登记 Home 的上一级：与 <project_root>/.paos/ 同一套布局
        self.assertEqual(Path(verdict["manifest_root"]), self.rooter_home.parent)

    def test_unregistered_rooter_home_is_reported_not_guessed(self):
        descriptor = json.loads(self.installation.read_text(encoding="utf-8"))
        descriptor["rooter_home"] = ""
        self.installation.write_text(json.dumps(descriptor, ensure_ascii=False), encoding="utf-8")
        report = self._migrate(apply=False)
        verdict = self._verdict(report, home_kind="rooter", home_id="")
        self.assertEqual(verdict["state"], mig.HOME_ABSENT)
        self.assertEqual(verdict["reason"], "rooter_home_not_registered")


class V3ConvergenceWiringTests(HomeAxisTestCase):
    """接线契约：本工具只做分派，收敛本身由 S032 的接口完成。

    真实接口不在本线（它与 paos_workstation 同一次提交），所以这里用替身钉住
    参数与结果的对应关系；真实收敛在"同一完整版本"的配对树上跑，证据在实施报告里。
    """

    def setUp(self):
        super().setUp()
        self._write_todo(V3_TODO)
        self.calls = []
        # 这两条守卫由 S032 的接口决定；本组测的是分派，先把它们置为可用。
        self._saved = (
            mig.convert_interface_problem,
            mig.v3_converge_interface_problem,
            mig.plan_v3_home_convergence,
            mig.apply_v3_home_convergence,
        )
        mig.convert_interface_problem = lambda: ""
        mig.v3_converge_interface_problem = lambda: ""

    def tearDown(self):
        (
            mig.convert_interface_problem,
            mig.v3_converge_interface_problem,
            mig.plan_v3_home_convergence,
            mig.apply_v3_home_convergence,
        ) = self._saved
        super().tearDown()

    def _stub_plan(self, *, candidate: str, removed=("current_work",)):
        def plan_v3_home_convergence(**kwargs):
            self.calls.append(("plan", kwargs))
            return {
                "home_path": str(self.home / "TODO.md"),
                "source_todo_sha256": "a" * 64,
                "candidate_todo_text": candidate,
                "candidate_todo_sha256": "b" * 64,
                "fields_removed": list(removed),
                "tasks_count_before": 0,
                "identity": {},
            }

        return plan_v3_home_convergence

    def _stub_apply(self, replayed=False):
        def apply_v3_home_convergence(**kwargs):
            self.calls.append(("apply", kwargs))
            return {"replayed": replayed, "converged": True, "fields_removed": ["current_work"]}

        return apply_v3_home_convergence

    def test_convergence_is_dispatched_with_the_registered_identity(self):
        target = V3_TODO.replace('current_work: "3002-w001"\n', "")
        mig.plan_v3_home_convergence = self._stub_plan(candidate=target)
        mig.apply_v3_home_convergence = self._stub_apply()

        report = self._migrate(apply=True)

        self.assertEqual(self._verdict(report)["state"], mig.HOME_CONVERTIBLE)
        plan_kwargs = next(kwargs for name, kwargs in self.calls if name == "plan")
        self.assertEqual(plan_kwargs["home_path"], self.home)
        self.assertEqual(plan_kwargs["home_kind"], "project_agent")
        self.assertEqual(plan_kwargs["home_id"], self.agent)
        self.assertEqual(plan_kwargs["project_id"], self.pid)
        apply_kwargs = next(kwargs for name, kwargs in self.calls if name == "apply")
        self.assertEqual(apply_kwargs["project_root"], self.tmp)
        self.assertEqual(apply_kwargs["home_path"], self.home)
        self.assertEqual(apply_kwargs["manifest_id"], mig.HOME_MANIFEST_ID)
        self.assertEqual(len(report["home_converted"]), 1)
        self.assertEqual(report["home_converted"][0]["axis"], mig.AXIS_V3)
        self.assertEqual(report["home_converted"][0]["fields_removed"], ["current_work"])

    def test_replay_is_reported_as_replayed(self):
        target = V3_TODO.replace('current_work: "3002-w001"\n', "")
        mig.plan_v3_home_convergence = self._stub_plan(candidate=target)
        mig.apply_v3_home_convergence = self._stub_apply(replayed=True)
        report = self._migrate(apply=True)
        self.assertTrue(report["home_converted"][0]["replayed"])
        self.assertEqual(mig.main(["--root", str(self.root), "--apply",
                                   "--installation-file", str(self.installation)]), 0)

    def test_home_already_at_target_is_not_rewritten(self):
        mig.plan_v3_home_convergence = self._stub_plan(candidate=V3_TODO)
        mig.apply_v3_home_convergence = self._stub_apply()
        report = self._migrate(apply=True)
        self.assertEqual(self._verdict(report)["state"], mig.HOME_ALREADY_CONVERGED)
        self.assertEqual([name for name, _ in self.calls], ["plan"])
        self.assertEqual(self._todo(), V3_TODO)

    def test_fields_the_interface_declares_as_removed_may_go(self):
        self._write_todo(V3_TODO_EXTRA_FIELDS)
        mig.plan_v3_home_convergence = self._stub_plan(candidate=V3_CANDIDATE_GOOD)
        mig.apply_v3_home_convergence = self._stub_apply()
        report = self._migrate(apply=True)
        self.assertEqual(self._verdict(report)["state"], mig.HOME_CONVERTIBLE)

    def test_candidate_that_drops_current_fields_is_refused(self):
        """渲染器不认识的 Current 字段被静默丢掉时必须拒绝（真实 3002-s010）。"""
        self._write_todo(V3_TODO_EXTRA_FIELDS)
        mig.plan_v3_home_convergence = self._stub_plan(candidate=V3_CANDIDATE_DROPS_FIELDS)
        mig.apply_v3_home_convergence = self._stub_apply()

        verdict = self._verdict(self._migrate(apply=False))
        self.assertEqual(verdict["state"], mig.HOME_BLOCKED_INTERFACE)
        self.assertEqual(
            verdict["reason"],
            "convergence_would_not_preserve:boundaries,history_ref,latest_readback",
        )

        with self.assertRaises(mig.MigrationBlocked) as caught:
            self._migrate(apply=True)

        self.assertEqual([name for name, _ in self.calls].count("apply"), 0)
        self.assertEqual(caught.exception.blocked[0]["home_id"], self.agent)
        self.assertEqual(self._todo(), V3_TODO_EXTRA_FIELDS)

    def test_candidate_that_reshapes_result_refs_is_refused(self):
        """把字符串形式的 result_refs 按字符拆开同样是删证据（真实 3002-s032）。"""
        self._write_todo(V3_TODO_STRING_REFS)
        mig.plan_v3_home_convergence = self._stub_plan(candidate=V3_CANDIDATE_CHAR_SPLIT)
        mig.apply_v3_home_convergence = self._stub_apply()

        verdict = self._verdict(self._migrate(apply=False))
        self.assertEqual(verdict["state"], mig.HOME_BLOCKED_INTERFACE)
        self.assertEqual(verdict["reason"], "convergence_would_not_preserve:result_refs")

        with self.assertRaises(mig.MigrationBlocked):
            self._migrate(apply=True)

        self.assertEqual([name for name, _ in self.calls].count("apply"), 0)
        self.assertEqual(self._todo(), V3_TODO_STRING_REFS)

    def test_rooter_home_uses_the_registration_and_no_project(self):
        rooter_todo = (
            V3_TODO.replace('"3002-s001"', '"rooter-001"')
            .replace('project_id: "3002"', 'project_id: ""')
            .replace('home_kind: "project_agent"', 'home_kind: "rooter"')
        )
        self._write_todo(rooter_todo, home=self.rooter_home)
        mig.plan_v3_home_convergence = self._stub_plan(
            candidate=rooter_todo.replace('current_work: "3002-w001"\n', "")
        )
        mig.apply_v3_home_convergence = self._stub_apply()
        self._migrate(apply=True)
        rooter_calls = [
            kwargs for name, kwargs in self.calls
            if name == "apply" and kwargs["home_kind"] == "rooter"
        ]
        self.assertEqual(len(rooter_calls), 1)
        self.assertEqual(rooter_calls[0]["home_id"], "rooter-001")
        self.assertEqual(rooter_calls[0]["project_id"], "")
        self.assertEqual(rooter_calls[0]["project_root"], self.rooter_home.parent)


if __name__ == "__main__":
    unittest.main()
