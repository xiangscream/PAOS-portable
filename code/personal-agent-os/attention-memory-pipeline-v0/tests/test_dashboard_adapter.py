from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from dashboard_adapter import DASHBOARD_SCHEMA, adapt_state, rank_items
from scan_vault import scan_vault


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_VAULT = ROOT / "synthetic-vault"
NOW = datetime.fromisoformat("2026-07-29T09:00:00+08:00")


class DashboardAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        state, _ = scan_vault(SYNTHETIC_VAULT, NOW)
        cls.dashboard = adapt_state(state, NOW)

    def test_schema_and_default_top_three(self) -> None:
        self.assertEqual(self.dashboard["schema"], DASHBOARD_SCHEMA)
        self.assertEqual(
            self.dashboard["defaultTopThree"],
            [
                "task-sensor-sync",
                "task-lrc101-report",
                "commitment-thursday-product-learning",
            ],
        )

    def test_long_term_items_fill_after_urgent_completion(self) -> None:
        ranked = rank_items(
            self.dashboard["items"],
            NOW,
            [
                "task-sensor-sync",
                "task-lrc101-report",
                "commitment-thursday-product-learning",
            ],
        )
        self.assertEqual(
            [item["id"] for item in ranked[:2]],
            ["task-obs-agent-recovery", "task-memory-markdown-baseline"],
        )

    def test_every_dashboard_item_keeps_source_refs(self) -> None:
        for item in self.dashboard["items"]:
            self.assertTrue(item["sourceRefs"])
            self.assertIn("/", item["source"])
            self.assertNotIn(":\\", item["source"])

    def test_every_dashboard_item_keeps_execution_contract(self) -> None:
        for item in self.dashboard["items"]:
            self.assertTrue(item["currentQuestion"])
            self.assertTrue(item["deliverable"])
            self.assertTrue(item["doneWhen"])

    def test_candidates_never_leave_candidate_status(self) -> None:
        self.assertTrue(self.dashboard["nightCandidates"])
        self.assertTrue(
            all(
                candidate["status"] == "candidate"
                for candidate in self.dashboard["nightCandidates"]
            )
        )

    def test_tip_is_not_in_dashboard_tasks(self) -> None:
        ids = {item["id"] for item in self.dashboard["items"]}
        self.assertNotIn("tip-weak-model-canary", ids)


if __name__ == "__main__":
    unittest.main()

