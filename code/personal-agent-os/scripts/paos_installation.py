"""Machine-local PAOS installation locators, independent of the active checkout."""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from paos_workstation import posix_windows_drive_locator

INSTALLATION_SCHEMA = "paos-installation/v1"
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


class InstallationProblem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def resolve_installation_path(explicit: str | None = None) -> Path:
    raw = explicit or os.environ.get("PAOS_INSTALLATION_FILE")
    if not raw:
        return Path.home() / ".paos" / "installation.json"
    return Path(posix_windows_drive_locator(str(raw))).expanduser()


def resolve_library_roots_path(
    *,
    installation: dict[str, Any] | None = None,
    explicit: str | None = None,
) -> Path:
    raw = (
        explicit
        or os.environ.get("PAOS_LIBRARY_ROOTS_CONFIG")
        or (installation or {}).get("library_roots_config")
    )
    if not raw:
        return Path.home() / ".paos" / "library-roots.json"
    return Path(posix_windows_drive_locator(str(raw))).expanduser()


def _stable_path_locator(raw: Any, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise InstallationProblem(
            "installation_descriptor_invalid",
            f"installation descriptor 缺少非空 {field}。",
            {"field": field},
        )
    locator = raw.strip()
    is_absolute = Path(locator).is_absolute() or bool(_WINDOWS_DRIVE_RE.match(locator))
    is_unc = locator.startswith(("\\\\", "//"))
    if not (is_absolute or is_unc):
        raise InstallationProblem(
            "installation_descriptor_invalid",
            f"installation descriptor 的 {field} 必须是绝对路径。",
            {"field": field, "value": locator},
        )
    if _WINDOWS_DRIVE_RE.match(locator):
        return locator.replace("\\", "/")
    return locator


def _optional_stable_path_locator(raw: Any, field: str) -> str:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return ""
    return _stable_path_locator(raw, field)


def load_installation_descriptor(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {
            "schema": INSTALLATION_SCHEMA,
            "configured": False,
            "path": str(path),
            "source_root": "",
            "data_root": "",
            "library_roots_config": "",
            "rooter_home": "",
        }
    if not path.is_file():
        raise InstallationProblem(
            "installation_descriptor_invalid",
            f"installation descriptor 路径不是文件：{path}",
            {"path": str(path)},
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InstallationProblem(
            "installation_descriptor_invalid",
            f"installation descriptor 无法读取：{path}",
            {"path": str(path), "cause": str(exc)},
        ) from exc
    if not isinstance(value, dict) or value.get("schema") != INSTALLATION_SCHEMA:
        raise InstallationProblem(
            "installation_descriptor_invalid",
            f"installation descriptor schema 无效：{path}",
            {"path": str(path), "schema": value.get("schema") if isinstance(value, dict) else None},
        )
    if not str(value.get("data_root") or "").strip():
        raise InstallationProblem(
            "installation_data_root_missing",
            "安装描述缺 data_root；请显式执行 install configure --data-root。",
            {"path": str(path)},
        )
    return {
        "schema": INSTALLATION_SCHEMA,
        "configured": True,
        "path": str(path),
        "source_root": _stable_path_locator(value.get("source_root"), "source_root"),
        "data_root": _stable_path_locator(value.get("data_root"), "data_root"),
        "library_roots_config": _stable_path_locator(
            value.get("library_roots_config"), "library_roots_config"
        ),
        "rooter_home": _optional_stable_path_locator(
            value.get("rooter_home"), "rooter_home"
        ),
        "agent_numbers_config": _optional_stable_path_locator(
            value.get("agent_numbers_config"), "agent_numbers_config"
        ),
    }


def effective_data_root(descriptor: dict[str, Any]) -> Path:
    """Return the registered data root; missing configuration is an explicit error."""
    if not descriptor.get("configured"):
        raise InstallationProblem(
            "installation_not_registered", "当前安装未登记，无法定位数据根。"
        )
    raw = str(descriptor.get("data_root") or "").strip()
    if not raw:
        raise InstallationProblem(
            "installation_data_root_missing",
            "安装描述缺 data_root；请显式执行 install configure --data-root。",
            {"path": descriptor.get("path")},
        )
    root = Path(posix_windows_drive_locator(raw)).expanduser()
    if not root.is_absolute():
        raise InstallationProblem(
            "installation_data_root_invalid", "data_root 不是绝对路径。", {"data_root": raw}
        )
    return root


def write_installation_descriptor(
    path: Path,
    *,
    source_root: str,
    library_roots_config: str,
    rooter_home: str | None = None,
    agent_numbers_config: str | None = None,
    data_root: str | None = None,
) -> dict[str, Any]:
    path = Path(path)
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise InstallationProblem(
                "installation_descriptor_invalid",
                f"现有安装描述不可读，拒绝覆盖：{path}",
                {"path": str(path), "cause": type(error).__name__},
            ) from error
        if not isinstance(existing, dict):
            raise InstallationProblem(
                "installation_descriptor_invalid",
                f"现有安装描述不是对象，拒绝覆盖：{path}",
                {"path": str(path)},
            )
    preserved = existing.get("data_root") if isinstance(existing, dict) else ""
    if rooter_home is None:
        rooter_home = str((existing or {}).get("rooter_home") or "")
    if agent_numbers_config is None:
        agent_numbers_config = str((existing or {}).get("agent_numbers_config") or "")
    if data_root is None:
        data_root = str(preserved or "")
    elif not str(data_root).strip():
        raise InstallationProblem(
            "installation_data_root_invalid", "显式 data_root 不能为空。"
        )
    if not str(data_root).strip():
        raise InstallationProblem(
            "installation_data_root_missing",
            "新安装或旧安装补字段必须显式提供 --data-root。",
            {"path": str(path)},
        )
    payload = {
        "schema": INSTALLATION_SCHEMA,
        "source_root": _stable_path_locator(source_root, "source_root"),
        "data_root": _stable_path_locator(data_root, "data_root"),
        "library_roots_config": _stable_path_locator(
            library_roots_config, "library_roots_config"
        ),
        "rooter_home": _optional_stable_path_locator(
            rooter_home, "rooter_home"
        ),
        "agent_numbers_config": _optional_stable_path_locator(
            agent_numbers_config, "agent_numbers_config"
        ),
    }
    temporary = path.with_name(f"{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise InstallationProblem(
            "installation_descriptor_write_failed",
            f"installation descriptor 写入失败：{path}",
            {"path": str(path), "cause": str(exc)},
        ) from exc
    return load_installation_descriptor(path)
