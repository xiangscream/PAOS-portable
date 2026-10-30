"""Read existing Project registration files without a Core HTTP process.

This is a locator/identity reader, not a second ProjectStore. It never writes
Project JSON, synthesizes missing projects, or interprets business summaries.
Home writers continue owning TODO, Mail and Notice. Older lifecycle/progress
fields may remain in the input file but are not a prerequisite for locating work.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paos_installation import effective_data_root, load_installation_descriptor
from paos_workstation import posix_windows_drive_locator


class RegistryProblem(ValueError):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.details = details


class ProjectRegistry:
    def __init__(self, installation_path: Path):
        # Lazy: --help / CAT / install configure do not need a Project registry.
        self.installation_path = Path(installation_path)

    def read(self, project_id: str) -> dict[str, Any]:
        if not isinstance(project_id, str) or not re.fullmatch(r"[123]\d{3}", project_id):
            raise RegistryProblem("project_id_invalid", "项目 ID 必须是 1xxx/2xxx/3xxx。")
        installation = load_installation_descriptor(self.installation_path)
        root = effective_data_root(installation) / "project-registry" / "projects"
        path = root / f"{project_id}.json"
        try:
            project = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RegistryProblem("project_not_registered", "登记项目不存在。", path=str(path)) from exc
        except (OSError, UnicodeError, ValueError) as exc:
            raise RegistryProblem("project_registry_unreadable", "项目登记无法读取。", path=str(path)) from exc
        if not isinstance(project, dict) or project.get("id") != project_id:
            raise RegistryProblem("project_registry_invalid", "项目登记身份与文件不符。", path=str(path))
        if project.get("schema") != "paos-project/v3":
            raise RegistryProblem("project_schema_invalid", "需要 paos-project/v3 登记。", path=str(path))
        locator = project.get("root_path")
        if not isinstance(locator, str) or not locator.strip():
            raise RegistryProblem("project_root_missing", "项目缺少 root_path。", path=str(path))
        if not Path(posix_windows_drive_locator(locator)).expanduser().is_absolute():
            raise RegistryProblem("project_root_invalid", "项目 root_path 必须为绝对定位。", path=str(path))
        sessions = project.get("sessions")
        if not isinstance(sessions, list):
            raise RegistryProblem("project_members_invalid", "项目 sessions 必须为成员数组。", path=str(path))
        ids: set[str] = set()
        for session in sessions:
            sid = session.get("id") if isinstance(session, dict) else None
            if not isinstance(sid, str) or not re.fullmatch(rf"{project_id}-s(?:\d{{3}}|[1-9]\d{{3,}})", sid) or sid in ids:
                raise RegistryProblem("project_members_invalid", "成员 ID 无效或重复。", path=str(path))
            ids.add(sid)
        organization = project.get("organization") or {}
        coordinator = organization.get("coordinator_session_id") if isinstance(organization, dict) else None
        if not isinstance(organization, dict) or (coordinator is not None and
                (not isinstance(coordinator, str) or coordinator not in ids)):
            raise RegistryProblem("project_coordinator_invalid", "Coordinator 必须引用登记成员。", path=str(path))
        return project
