"""Read-only/local Coordinator preflight helpers for S3-2.

The functions here consume already-fetched PAOS projections plus local paths.
They never perform HTTP or durable PAOS writes. Collaboration transport
ownership is deliberately deferred to S5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paos_workstation import preflight_workspace

ENTERABLE_WORK_STATUSES = {"todo", "doing", "blocked"}
ACTIVE_OWNER_STATUSES = {"pending_ack", "active"}


def _current_work_id(session: dict[str, Any]) -> str:
    """Mirror the canonical legacy current_work_item_id projection.

    The Agent CLI stays REST-only and therefore does not import server workflow
    modules, but it must not invent a second lifecycle interpretation. Current
    PAOS semantics are: explicit current_work_item_id first, otherwise the first
    legacy work_item_ids entry.
    """
    direct = str(session.get("current_work_item_id") or "").strip()
    if direct:
        return direct
    work_ids = session.get("work_item_ids") or []
    if isinstance(work_ids, list) and work_ids:
        return str(work_ids[0] or "").strip()
    return ""


def _find(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get("id") or "") == item_id:
            return item
    return None


def session_from_project(project: dict[str, Any], session_id: str) -> dict[str, Any]:
    """Return one Session from the supplied Project snapshot, or an empty view."""
    for item in project.get("sessions") or []:
        if isinstance(item, dict) and str(item.get("id") or "") == session_id:
            return item
    return {}


def build_resource_preflight(
    *,
    project: dict[str, Any],
    coordinator: dict[str, Any],
    target: dict[str, Any],
    target_work_id: str,
    root: Path | None,
    materials: list[str],
    reviewer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the S3-owned dispatch prerequisites without side effects."""
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    def check(code: str, ok: bool, message: str, **details: Any) -> None:
        item = {"code": code, "ok": bool(ok), "message": message, **details}
        checks.append(item)
        if not ok:
            issues.append(item)

    project_id = str(project.get("id") or "")
    coordinator_id = str(coordinator.get("id") or "")
    target_id = str(target.get("id") or "")
    organization = project.get("organization") or {}
    current_coordinator_id = str(organization.get("coordinator_session_id") or "")
    check(
        "coordinator_current",
        bool(coordinator_id) and current_coordinator_id == coordinator_id,
        "Supplied Coordinator must match the current Project organization pointer.",
        supplied_session_id=coordinator_id,
        current_session_id=current_coordinator_id,
    )
    check(
        "coordinator_active",
        coordinator.get("status") == "active",
        "Coordinator must be active.",
        status=coordinator.get("status"),
    )
    check(
        "coordinator_acknowledged",
        coordinator.get("acknowledgement") is not None,
        "Coordinator must acknowledge its current Cycle before dispatch.",
    )
    coordinator_runtime = str(coordinator.get("runtime_id") or "").strip()
    check(
        "coordinator_runtime_bound",
        bool(coordinator_runtime),
        "Coordinator must have a current Runtime binding before dispatch.",
        runtime_id=coordinator_runtime,
    )
    coordinator_cycle = int(coordinator.get("current_cycle") or 0)
    coordinator_pack = str((coordinator.get("entry") or {}).get("context_pack_id") or "").strip()
    check(
        "coordinator_tenure_present",
        coordinator_cycle > 0 and bool(coordinator_pack),
        "Coordinator must expose a current Cycle and Context Pack.",
        execution_cycle=coordinator_cycle,
        context_pack_id=coordinator_pack,
    )

    target_work = _find(
        [item for item in (project.get("work_items") or []) if isinstance(item, dict)],
        target_work_id,
    )
    check(
        "target_work_exists",
        target_work is not None,
        "Target Work must exist in the Project.",
        target_work_item_id=target_work_id,
    )
    if target_work is not None:
        check(
            "target_work_enterable",
            target_work.get("status") in ENTERABLE_WORK_STATUSES,
            "Target Work must be todo/doing/blocked for switch_work.",
            status=target_work.get("status"),
        )

    check(
        "target_agent_active",
        target.get("status") == "active",
        "Target Agent must already have an active Runtime tenure; lifecycle changes stay Human-owned.",
        status=target.get("status"),
    )
    check(
        "target_agent_acknowledged",
        target.get("acknowledgement") is not None,
        "Target Agent must acknowledge the current Cycle before directed dispatch.",
    )
    runtime_id = str(target.get("runtime_id") or "").strip()
    check(
        "target_runtime_bound",
        bool(runtime_id),
        "Target Agent must have a current Runtime binding.",
        runtime_id=runtime_id,
    )
    current_cycle = int(target.get("current_cycle") or 0)
    current_pack = str((target.get("entry") or {}).get("context_pack_id") or "").strip()
    check(
        "target_tenure_present",
        current_cycle > 0 and bool(current_pack),
        "Target Agent must expose a current Cycle and Context Pack.",
        execution_cycle=current_cycle,
        context_pack_id=current_pack,
    )

    old_work_id = _current_work_id(target)
    check(
        "target_work_changes",
        bool(old_work_id) and old_work_id != target_work_id,
        "Directed dispatch must target a Work different from the Agent's current Work.",
        current_work_item_id=old_work_id,
        target_work_item_id=target_work_id,
    )
    old_work = _find(
        [item for item in (project.get("work_items") or []) if isinstance(item, dict)],
        old_work_id,
    ) if old_work_id else None
    if old_work is not None and old_work.get("status") == "doing":
        other_owners = []
        for session in project.get("sessions") or []:
            if not isinstance(session, dict):
                continue
            if str(session.get("id") or "") == target_id:
                continue
            if session.get("status") not in ACTIVE_OWNER_STATUSES:
                continue
            if _current_work_id(session) == old_work_id:
                other_owners.append(str(session.get("id") or ""))
        check(
            "would_orphan_doing_work",
            bool(other_owners),
            "Switching this Agent would leave its current doing Work without another active/pending owner.",
            current_work_item_id=old_work_id,
            other_owner_session_ids=other_owners,
        )

    if reviewer is not None:
        reviewer_id = str(reviewer.get("id") or "")
        check(
            "reviewer_independent",
            bool(reviewer_id)
            and reviewer_id not in {target_id, coordinator_id},
            "Reviewer must be a distinct Agent from both execution target and Coordinator.",
            reviewer_session_id=reviewer_id,
        )
        check(
            "reviewer_active",
            reviewer.get("status") == "active",
            "Reviewer must be active before formal responsibility is created.",
            status=reviewer.get("status"),
        )
        check(
            "reviewer_acknowledged",
            reviewer.get("acknowledgement") is not None,
            "Reviewer must acknowledge its current Cycle.",
        )
        reviewer_runtime = str(reviewer.get("runtime_id") or "").strip()
        check(
            "reviewer_runtime_bound",
            bool(reviewer_runtime),
            "Reviewer must have a current Runtime binding.",
            runtime_id=reviewer_runtime,
        )
        reviewer_work = _current_work_id(reviewer)
        check(
            "reviewer_not_source_worker",
            reviewer_work != target_work_id,
            "Independent Reviewer must not currently execute the Work it will review.",
            reviewer_current_work_item_id=reviewer_work,
            source_work_item_id=target_work_id,
        )

    if root is None:
        check(
            "workspace_root_present",
            False,
            "Project root_path or an explicit --root is required for Runtime-local material checks.",
        )
        path_result = {"ready": False, "root_path": "", "checks": [], "issues": []}
    else:
        key_files = [str(item) for item in (project.get("key_files") or [])]
        path_result = preflight_workspace(root, key_files, materials)
        for item in path_result["checks"]:
            code = f"path_{item['kind']}"
            check(
                code,
                bool(item["ok"]),
                "Runtime-local path must be reachable.",
                path=item["path"],
                raw=item["raw"],
                reason=item["reason"],
            )

    return {
        "schema": "paos-coordinator-resource-preflight/v1",
        "project_id": project_id,
        "ready": not issues,
        "checks": checks,
        "issues": issues,
        "root_path": path_result.get("root_path", ""),
        "coordinator_execution": {
            "session_id": coordinator_id,
            "runtime_id": coordinator_runtime,
            "execution_cycle": coordinator_cycle,
            "context_pack_id": coordinator_pack,
        },
        "target_execution": {
            "session_id": target_id,
            "runtime_id": runtime_id,
            "execution_cycle": current_cycle,
            "context_pack_id": current_pack,
        },
        "collaboration_transport": {
            "status": "deferred_to_s5",
            "checked": False,
        },
    }
