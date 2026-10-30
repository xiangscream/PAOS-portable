"""V1.3 Home resolution for Project Agents and Rooter.

This module keeps identity/location resolution narrow. It does not create a
Project Session, change formal Work responsibility, or start a Runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paos_workstation import posix_windows_drive_locator


HOME_REF_SCHEMA = "paos-home-ref/v1"
HOME_KINDS = {"project_agent", "rooter"}


class HomeProblem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _clean(value: Any, label: str, *, required: bool = True) -> str:
    text = " ".join(str(value or "").split())
    if required and not text:
        raise HomeProblem(
            "home_field_missing",
            f"{label} 不能为空。",
            {"field": label},
        )
    return text


def project_agent_home(
    *,
    project: dict[str, Any],
    agent_id: str,
    root_override: str = "",
    require_existing: bool = True,
) -> dict[str, Any]:
    project_id = _clean(project.get("id"), "project_id")
    agent_id = _clean(agent_id, "agent_id")
    root_raw = _clean(
        root_override or project.get("root_path"),
        "root_path",
    )
    sessions = [
        item for item in (project.get("sessions") or [])
        if isinstance(item, dict)
    ]
    if not any(str(item.get("id") or "") == agent_id for item in sessions):
        raise HomeProblem(
            "home_agent_unknown",
            "目标 Agent 不属于该 Project 的登记成员。",
            {"project_id": project_id, "agent_id": agent_id},
        )
    root = Path(posix_windows_drive_locator(root_raw)).expanduser()
    home_path = root / "Workstations" / agent_id
    if require_existing and not home_path.is_dir():
        raise HomeProblem(
            "home_missing",
            f"Agent Home 不存在：{home_path}",
            {
                "project_id": project_id,
                "agent_id": agent_id,
                "home_path": str(home_path),
            },
        )
    return {
        "schema": HOME_REF_SCHEMA,
        "home_kind": "project_agent",
        "home_id": agent_id,
        "project_id": project_id,
        "home_path": str(home_path),
        "project_root": str(root),
    }


def agent_project_id(agent_id: str) -> str:
    """Stable project id from the Project set convention `<pid>-sxxx` —
    deterministic, never a guess; raises when the convention doesn't hold."""
    text = str(agent_id or "").strip()
    head, sep, _ = text.partition("-s")
    if not sep or not head.strip().isdigit():
        raise HomeProblem(
            "home_agent_unknown",
            "Agent id 不符合 `<pid>-sxxx` 登记约定；无法定位所属 Project。",
            {"agent_id": text},
        )
    return head


def rooter_home(
    *,
    home_path: str | Path,
    home_id: str = "rooter-001",
    require_existing: bool = True,
) -> dict[str, Any]:
    home_id = _clean(home_id, "home_id")
    path = Path(posix_windows_drive_locator(str(home_path))).expanduser()
    if require_existing and not path.is_dir():
        raise HomeProblem(
            "home_missing",
            f"Rooter Home 不存在：{path}",
            {"home_id": home_id, "home_path": str(path)},
        )
    return {
        "schema": HOME_REF_SCHEMA,
        "home_kind": "rooter",
        "home_id": home_id,
        "project_id": "",
        "home_path": str(path),
        "project_root": "",
    }


def normalize_home_ref(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != HOME_REF_SCHEMA:
        raise HomeProblem(
            "home_ref_invalid",
            "Home ref schema 无效。",
            {"schema": value.get("schema") if isinstance(value, dict) else None},
        )
    kind = _clean(value.get("home_kind"), "home_kind")
    if kind not in HOME_KINDS:
        raise HomeProblem(
            "home_kind_invalid",
            f"home_kind 必须是 {sorted(HOME_KINDS)} 之一。",
            {"home_kind": kind},
        )
    home_id = _clean(value.get("home_id"), "home_id")
    project_id = _clean(value.get("project_id"), "project_id", required=False)
    home_path = _clean(value.get("home_path"), "home_path")
    if kind == "project_agent" and not project_id:
        raise HomeProblem(
            "home_project_id_missing",
            "project_agent Home 必须带 project_id。",
            {"home_id": home_id},
        )
    if kind == "rooter" and project_id:
        raise HomeProblem(
            "home_rooter_project_forbidden",
            "Rooter Home 不绑定 Project Session。",
            {"home_id": home_id, "project_id": project_id},
        )
    return {
        "schema": HOME_REF_SCHEMA,
        "home_kind": kind,
        "home_id": home_id,
        "project_id": project_id,
        "home_path": home_path,
        "project_root": str(value.get("project_root") or ""),
    }


def todo_path(home_ref: dict[str, Any]) -> Path:
    ref = normalize_home_ref(home_ref)
    return Path(ref["home_path"]) / "TODO.md"


def notices_path(home_ref: dict[str, Any]) -> Path:
    ref = normalize_home_ref(home_ref)
    return Path(ref["home_path"]) / "notices"
