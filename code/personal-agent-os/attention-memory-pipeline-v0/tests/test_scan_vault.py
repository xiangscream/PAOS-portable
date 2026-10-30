from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scan_vault import (
    MANIFEST_SCHEMA,
    ScanError,
    compare_manifests,
    manifest_from_source,
    run_scan,
    scan_vault,
)


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_VAULT = ROOT / "synthetic-vault"
NOW = datetime.fromisoformat("2026-07-29T09:00:00+08:00")


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


class ScanVaultTests(unittest.TestCase):
    def test_scan_does_not_modify_source(self) -> None:
        before = tree_hash(SYNTHETIC_VAULT)
        scan_vault(SYNTHETIC_VAULT, NOW)
        after = tree_hash(SYNTHETIC_VAULT)
        self.assertEqual(before, after)

    def test_every_ingested_object_has_provenance(self) -> None:
        state, _ = scan_vault(SYNTHETIC_VAULT, NOW)
        collections = [
            state["tasks"],
            state["tips"],
            state["projects"],
            state["archives"],
            state["source_objects"],
            state["review_candidates"],
        ]
        for collection in collections:
            for item in collection:
                self.assertTrue(item["source_refs"])
                for source_ref in item["source_refs"]:
                    self.assertIn("path", source_ref)
                    self.assertRegex(source_ref["sha256"], r"^[0-9a-f]{64}$")

    def test_tasks_keep_execution_contract_sections(self) -> None:
        state, _ = scan_vault(SYNTHETIC_VAULT, NOW)
        for task in state["tasks"]:
            for field in ("current_question", "deliverable", "done_when"):
                self.assertTrue(task[field])

        lrc101 = next(
            task for task in state["tasks"] if task["id"] == "task-lrc101-report"
        )
        self.assertEqual(
            lrc101["deliverable"],
            "报告开头一页：一句话问题、三段因果链和一个明确结论。",
        )

    def test_tip_does_not_become_task(self) -> None:
        state, _ = scan_vault(SYNTHETIC_VAULT, NOW)
        task_ids = {item["id"] for item in state["tasks"]}
        tip_ids = {item["id"] for item in state["tips"]}
        self.assertIn("tip-weak-model-canary", tip_ids)
        self.assertNotIn("tip-weak-model-canary", task_ids)

    def test_conflict_and_missing_scope_stay_candidates(self) -> None:
        state, _ = scan_vault(SYNTHETIC_VAULT, NOW)
        candidate_types = {
            item["candidate_type"]: item for item in state["review_candidates"]
        }
        self.assertIn("conflict", candidate_types)
        self.assertIn("scope_missing", candidate_types)
        self.assertTrue(
            all(item["status"] == "candidate" for item in state["review_candidates"])
        )

    def test_progress_debt_preserves_domain_and_project(self) -> None:
        state, _ = scan_vault(SYNTHETIC_VAULT, NOW)
        debts = [
            item
            for item in state["review_candidates"]
            if item["candidate_type"] == "progress_debt"
        ]
        projects = {item["project"] for item in debts}
        domains = {item["domain_code"] for item in debts}
        self.assertIn("obs-agent", projects)
        self.assertIn("Agent-Memory-Lab", projects)
        self.assertIn("personal", domains)
        self.assertIn("agent_ops", domains)

    def test_secret_field_blocks_entire_note_without_value_echo(self) -> None:
        state, _ = scan_vault(SYNTHETIC_VAULT, NOW)
        blocked = [
            item
            for item in state["source_index"]
            if item["ingest_status"] == "blocked"
        ]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(
            blocked[0]["path"], "_blocked/secret-field-example.md"
        )
        serialized = json.dumps(state, ensure_ascii=False)
        self.assertNotIn("synthetic-placeholder-never-ingest", serialized)

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "build" / "attention-state.json"
            manifest = root / "build" / "source-manifest.json"
            report = root / "build" / "scan-report.md"
            state = run_scan(
                SYNTHETIC_VAULT,
                output,
                manifest,
                report,
                NOW,
                dry_run=True,
            )
            self.assertGreater(state["scan_summary"]["tasks"], 0)
            self.assertFalse(output.exists())
            self.assertFalse(manifest.exists())
            self.assertFalse(report.exists())

    def test_change_detection_finds_added_modified_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_vault = Path(temp_dir) / "vault"
            shutil.copytree(SYNTHETIC_VAULT, copied_vault)
            previous = manifest_from_source(copied_vault)

            modified = copied_vault / "10-Work" / "LRC101" / "report-mainline.md"
            modified.write_text(
                modified.read_text(encoding="utf-8") + "\n新增合成变化。\n",
                encoding="utf-8",
            )
            deleted = copied_vault / "10-Work" / "Collaboration" / "sensor-sync.md"
            deleted.unlink()
            added = copied_vault / "00-Inbox" / "new-tip.md"
            added.write_text(
                "---\n"
                "schema: attention-note/v0\n"
                "id: test-new-tip\n"
                "object_type: tip\n"
                "domain: personal\n"
                "project: unassigned\n"
                "thread: inbox\n"
                "status: active\n"
                "review_state: candidate\n"
                "sensitivity: personal\n"
                "updated: 2026-07-29T09:00:00+08:00\n"
                "---\n\n# 新 Tip\n\n## 摘要\n\n测试新增。\n",
                encoding="utf-8",
            )

            current = manifest_from_source(copied_vault)
            changes = compare_manifests(previous, current)
            self.assertIn("00-Inbox/new-tip.md", changes["added"])
            self.assertIn(
                "10-Work/LRC101/report-mainline.md", changes["modified"]
            )
            self.assertIn(
                "10-Work/Collaboration/sensor-sync.md", changes["deleted"]
            )

    def test_output_inside_source_is_rejected(self) -> None:
        with self.assertRaises(ScanError):
            run_scan(
                SYNTHETIC_VAULT,
                SYNTHETIC_VAULT / "build" / "state.json",
                ROOT / "build" / "manifest.json",
                ROOT / "build" / "report.md",
                NOW,
                dry_run=True,
            )

    def test_manifest_schema_is_stable(self) -> None:
        manifest = manifest_from_source(SYNTHETIC_VAULT)
        self.assertEqual(manifest["schema"], MANIFEST_SCHEMA)
        self.assertGreater(len(manifest["files"]), 0)


if __name__ == "__main__":
    unittest.main()

