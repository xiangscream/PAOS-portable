"""Slice-1 thin-slice controlled-copy test (s027, w071/r062).

Uses PR126/PR127 owner modules under candidate-source:
- paos_home.project_agent_home / rooter_home for stable Home identity
- paos_notice.create_notice / handle_notice / request_notice_activation
  for handled and pending input mapping
- paos_attention_service.activation_work(Home) for stable read

Never touches production Source; exercise only on isolated temp copies.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

CANDIDATE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CANDIDATE))

from paos_home import project_agent_home, rooter_home
from paos_notice import create_notice, handle_notice
from paos_attention_service import activation_work


def _fake_project(root: str) -> dict[str, Any]:
    return {
        "id": "3002",
        "root_path": root,
        "sessions": [{"id": "3002-s027"}, {"id": "3002-s010"}],
    }


def test_slice1_project_agent_home_identity(tmp_path: Path) -> None:
    home = project_agent_home(
        project=_fake_project(str(tmp_path)),
        agent_id="3002-s027",
        require_existing=False,
    )
    assert home["home_kind"] == "project_agent"
    assert home["home_id"] == "3002-s027"
    assert home["project_id"] == "3002"
    assert home["home_path"].endswith(f"Workstations/3002-s027")


def test_slice1_rooter_home_identity(tmp_path: Path) -> None:
    rooter_root = tmp_path / "rooter-001"
    rooter_root.mkdir()
    home = rooter_home(home_path=str(rooter_root), require_existing=False)
    assert home["home_kind"] == "rooter"
    assert home["home_id"] == "rooter-001"
    assert home["project_id"] == ""


def test_slice1_pending_and_handled_notice_mapping(tmp_path: Path) -> None:
    home_dir = tmp_path / "Workstations" / "3002-s027"
    home_dir.mkdir(parents=True)
    # pending Notice with explicit activation intent
    pending = create_notice(
        home_path=home_dir,
        home_kind="project_agent",
        home_id="3002-s027",
        project_id="3002",
        source_kind="mail",
        source_ref="msg-s010-w067-formally-accepted-20261003",
        summary="w067 formally accepted.",
        activation_request_id="act-3002-s027-1",
    )
    assert pending["state"] == "pending"
    assert pending["activation_request_id"] == "act-3002-s027-1"
    # handled Notice with no activation request
    handled = create_notice(
        home_path=home_dir,
        home_kind="project_agent",
        home_id="3002-s027",
        project_id="3002",
        source_kind="mail",
        source_ref="msg-s010-w067-accepted-lifecycle-closeout-20261003",
        summary="w067 lifecycle accepted.",
        activation_request_id="act-3002-s027-2",
    )
    assert handled["state"] == "pending"
    got_handled = handle_notice(
        home_path=home_dir,
        notice_id=handled["notice_id"],
        resolution="closed",
        action_ref=str(handled["path"]),
    )
    assert got_handled["state"] == "handled"
    assert got_handled["resolution"] == "closed"
    # historical pending WITHOUT explicit intent stays import-only
    historical = create_notice(
        home_path=home_dir,
        home_kind="project_agent",
        home_id="3002-s027",
        project_id="3002",
        source_kind="mail",
        source_ref="msg-legacy-no-intent",
        summary="no intent imported",
        activation_request_id="",
    )
    assert historical["state"] == "pending"
    assert not historical.get("activation_request_id")
    # activation_work only surfaces explicit intent
    home_ref = project_agent_home(
        project=_fake_project(str(tmp_path)),
        agent_id="3002-s027",
        require_existing=True,
    )
    items = activation_work(home_ref)["items"]
    notices = [
        i
        for i in items
        if str(i.get("source_ref") or "").startswith("msg-s010-w067")
    ]
    assert len(notices) == 1
    assert notices[0]["activation_request_id"] == "act-3002-s027-1"
    # no historical pending in activation_work
    assert all(
        str(i.get("activation_request_id") or "") for i in items
    )


def test_slice1_rerun_same_notice_idempotent(tmp_path: Path) -> None:
    home_dir = tmp_path / "Workstations" / "3002-s027"
    home_dir.mkdir(parents=True)
    first = create_notice(
        home_path=home_dir,
        home_kind="project_agent",
        home_id="3002-s027",
        project_id="3002",
        source_kind="mail",
        source_ref="msg-test-idempo",
        summary="repeat message",
        activation_request_id="act-x-1",
    )
    second = create_notice(
        home_path=home_dir,
        home_kind="project_agent",
        home_id="3002-s027",
        project_id="3002",
        source_kind="mail",
        source_ref="msg-test-idempo",
        summary="repeat message",
        activation_request_id="act-x-1",
    )
    assert first["notice_id"] == second["notice_id"]
    assert second["created"] is False
