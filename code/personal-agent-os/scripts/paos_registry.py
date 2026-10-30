"""Minimal Project locator for the headless PAOS Agent work base.

A registry record is *not* a project report or a Session/Work database. It
contains only an ID, an existing Obsidian/project root, explicit Home IDs, and
one Coordinator Home ID. Project knowledge stays in the vault's current note;
ongoing work stays in each Home's TODO. The optional in-memory session-shaped
view below connects existing Home writers without persisting legacy lifecycles.

No HTTP server, schema upgrade, or implicit search of neighboring directories.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Iterable

from paos_installation import effective_data_root, load_installation_descriptor
from paos_workstation import posix_windows_drive_locator

REGISTRY_SCHEMA = "paos-project-registry/v1"
_RECORD_KEYS = frozenset({"schema", "id", "root_path", "homes", "coordinator_home_id"})
_PROJECT_ID_RE = re.compile(r"[123]\d{3}\Z")


class RegistryProblem(ValueError):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.details = details


class ProjectRegistry:
    """One file per project; creates only on explicit registration."""

    def __init__(self, installation_path: Path):
        self.installation_path = Path(installation_path)

    @staticmethod
    def _project_id(project_id: str) -> str:
        if not isinstance(project_id, str) or not _PROJECT_ID_RE.fullmatch(project_id):
            raise RegistryProblem("project_id_invalid", "项目 ID 必须是 1xxx/2xxx/3xxx。")
        return project_id

    def _path(self, project_id: str) -> Path:
        installation = load_installation_descriptor(self.installation_path)
        return (effective_data_root(installation) / "project-registry" / "projects" /
                f"{self._project_id(project_id)}.json")

    @staticmethod
    def _check(record: Any, project_id: str, path: Path) -> dict[str, Any]:
        label = str(path)
        if not isinstance(record, dict) or set(record) != _RECORD_KEYS or record.get("schema") != REGISTRY_SCHEMA:
            raise RegistryProblem(
                "project_schema_invalid",
                f"项目登记必须是 {REGISTRY_SCHEMA} 的最小字段集；不读取旧项目管理 JSON。",
                path=label,
            )
        if record.get("id") != project_id:
            raise RegistryProblem("project_registry_invalid", "项目登记身份与文件不符。", path=label)
        locator = record.get("root_path")
        if not isinstance(locator, str) or not locator.strip():
            raise RegistryProblem("project_root_missing", "项目缺少 root_path。", path=label)
        if not Path(posix_windows_drive_locator(locator)).expanduser().is_absolute():
            raise RegistryProblem("project_root_invalid", "项目 root_path 必须为绝对定位。", path=label)
        homes = record.get("homes")
        if not isinstance(homes, list) or not homes:
            raise RegistryProblem("project_members_invalid", "至少登记 Coordinator 的一个 Home。", path=label)
        seen: set[str] = set()
        for home in homes:
            if (not isinstance(home, str) or
                not re.fullmatch(rf"{project_id}-s(?:\d{{3}}|[1-9]\d{{3,}})", home) or home in seen):
                raise RegistryProblem("project_members_invalid", "Home ID 无效或重复。", path=label)
            seen.add(home)
        coordinator = record.get("coordinator_home_id")
        if not isinstance(coordinator, str) or coordinator not in seen:
            raise RegistryProblem("project_coordinator_invalid", "Coordinator 必须是本项目登记 Home。", path=label)
        return record

    def read_record(self, project_id: str) -> dict[str, Any]:
        """Read the exact new registration shape, with no generated status."""
        path = self._path(project_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RegistryProblem("project_not_registered", "登记项目不存在。", path=str(path)) from exc
        except (OSError, UnicodeError, ValueError) as exc:
            raise RegistryProblem("project_registry_unreadable", "项目登记无法读取。", path=str(path)) from exc
        return self._check(value, project_id, path)

    def read(self, project_id: str) -> dict[str, Any]:
        """In-memory Home-writer view; no second durable project representation.

        `sessions` is only the input shape consumed by the existing Mail/Home
        writers. Here `active` means registered Home, *not* a live Runtime.
        We do not restore Session cycles, work items, legacy summaries, or
        a fake project revision.
        """
        record = self.read_record(project_id)
        root = Path(posix_windows_drive_locator(record["root_path"])).expanduser()
        return {
            **record,
            "name": root.name,  # Derived for workstation ENTRY; never stored.
            "sessions": [{"id": home, "status": "active"} for home in record["homes"]],
            "organization": {"coordinator_session_id": record["coordinator_home_id"]},
        }

    def register(
        self, project_id: str, *, root_path: str,
        coordinator_home_id: str, homes: Iterable[str] = (),
    ) -> dict[str, Any]:
        """Create one registration without overwriting an existing project.

        Existing files with different bytes (especially legacy Project JSON)
        are never truncated. Registration does not create a Home, Runtime
        binding, latest-alignment note, or any project business content.
        """
        project_id = self._project_id(project_id)
        root = Path(posix_windows_drive_locator(str(root_path))).expanduser()
        if not root.is_absolute() or not root.is_dir():
            raise RegistryProblem("project_root_invalid", "项目 root 必须是现有绝对目录。", root_path=str(root_path))
        ordered = [coordinator_home_id]
        ordered.extend(home for home in homes if home != coordinator_home_id)
        record = {
            "schema": REGISTRY_SCHEMA,
            "id": project_id,
            "root_path": str(root.resolve()),
            "homes": ordered,
            "coordinator_home_id": coordinator_home_id,
        }
        path = self._path(project_id)
        self._check(record, project_id, path)
        if path.exists():
            if self.read_record(project_id) == record:
                return {"created": False, "record": record}
            raise RegistryProblem("project_already_registered", "项目登记已存在且内容不同；不覆盖，请先核对原件。", path=str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.new-{uuid.uuid4().hex}")
        try:
            temp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            try:
                os.link(temp, path)  # create-if-absent: no overwrite on concurrent registration
            except FileExistsError:
                if self.read_record(project_id) == record:
                    return {"created": False, "record": record}
                raise RegistryProblem("project_already_registered", "并发登记已存在且不同；没有覆盖。", path=str(path))
        except OSError as exc:
            raise RegistryProblem("project_registry_write_failed", "无法安全建立项目登记。", path=str(path), cause=str(exc)) from exc
        finally:
            temp.unlink(missing_ok=True)
        return {"created": True, "record": record}
