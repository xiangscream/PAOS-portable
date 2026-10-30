"""A25: explicit program rollback that preserves current business data."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMPAT_SCHEMA = "paos-program-compatibility/v1"
DATA_CONTRACT = "paos-data-contract/v1"


class RollbackProblem(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _path_identity(value: str | Path) -> str:
    from paos_workstation import posix_windows_drive_locator

    path = Path(posix_windows_drive_locator(str(value))).expanduser()
    try:
        path = path.resolve()
    except OSError:
        pass
    return os.path.normcase(str(path))


def validate_compatibility(plan: dict[str, Any], compat: dict[str, Any]) -> None:
    for field in ("current_revision", "target_revision"):
        if compat[field] != plan[field]:
            raise RollbackProblem("rollback_compatibility_mismatch", "兼容声明与版本对不一致。", {"field": field})
    for field in ("current_source", "data_root", "target_source"):
        if _path_identity(compat[field]) != _path_identity(plan[field]):
            raise RollbackProblem("rollback_compatibility_mismatch", "兼容声明与本次安装前置不一致。", {"field": field})


def _host_path(value: str | Path) -> Path:
    from paos_workstation import posix_windows_drive_locator

    return Path(posix_windows_drive_locator(str(value))).expanduser()


def _durable_source_locator(current_locator: str, target: Path) -> str:
    text = str(target).replace("\\", "/")
    current = str(current_locator or "")
    if os.name != "nt" and re.match(r"^[A-Za-z]:[/\\]", current):
        match = re.match(r"^/mnt/([A-Za-z])/(.*)$", text)
        if match:
            return f"{match.group(1).upper()}:/{match.group(2)}"
    return text


def _target_clean(root: Path) -> bool:
    try:
        run = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return run.returncode == 0 and not run.stdout.strip()


def _revision(root: Path) -> str | None:
    try:
        run = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = run.stdout.strip()
    return value if run.returncode == 0 and len(value) == 40 else None


def _load_compat(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RollbackProblem("rollback_compatibility_unreadable", "兼容声明不可读。") from error
    if not isinstance(value, dict) or value.get("schema") != COMPAT_SCHEMA:
        raise RollbackProblem("rollback_compatibility_invalid", "兼容声明 schema 无效。")
    if value.get("data_contract") != DATA_CONTRACT:
        raise RollbackProblem("rollback_compatibility_unknown", "目标数据合同未声明为本版本兼容。")
    for field in ("current_source", "current_revision", "data_root", "target_source", "target_revision"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise RollbackProblem("rollback_compatibility_unbound", "兼容声明必须绑定本次安装前置与版本对。", {"field": field})
    for field in ("current_revision", "target_revision"):
        revision = value[field].strip().lower()
        if len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
            raise RollbackProblem("rollback_compatibility_unbound", "revision 必须是 40 位 hex。", {"field": field})
    return value


def plan_program_rollback(
    installation_file: str | Path, target_source: str | Path,
) -> dict[str, Any]:
    from paos_installation import effective_data_root, load_installation_descriptor, resolve_installation_path

    descriptor_path = resolve_installation_path(str(installation_file))
    descriptor = load_installation_descriptor(descriptor_path)
    if not descriptor.get("configured"):
        raise RollbackProblem("installation_not_registered", "当前安装未登记。")
    data_root = _host_path(effective_data_root(descriptor))
    current = _host_path(str(descriptor["source_root"]))
    target = _host_path(target_source)
    if not target.is_absolute() or not target.is_dir():
        raise RollbackProblem("rollback_target_invalid", "目标程序目录必须是已存在的绝对路径。")
    if not (target / "scripts" / "paos.py").is_file():
        raise RollbackProblem("rollback_target_invalid", "目标目录不像 PAOS Source（缺 scripts/paos.py）。")
    if target.resolve() == current.resolve():
        raise RollbackProblem("rollback_noop", "目标 Source 与当前 Source 相同。")
    target_rev = _revision(target)
    current_rev = _revision(current)
    if not current_rev:
        raise RollbackProblem("rollback_current_unverifiable", "当前 Source 没有可核 Git 版本，不能回退。")
    if not target_rev:
        raise RollbackProblem("rollback_target_unverifiable", "目标 Source 没有可核 Git 版本，不能回退。")
    if not _target_clean(target):
        raise RollbackProblem("rollback_target_dirty", "目标 Source 有未提交/人工修改，拒绝覆盖。")
    compat = None
    manifest = target / "program-manifest.json"
    if manifest.is_file():
        compat = _load_compat(manifest)
        if compat["current_revision"] != current_rev or compat["target_revision"] != target_rev:
            raise RollbackProblem("rollback_compatibility_mismatch", "目标 manifest 与 current/target revision 不一致。")
    return {
        "schema": "paos-program-rollback/v1",
        "ok": True,
        "read_only": True,
        "apply": False,
        "current_source": str(current),
        "current_revision": current_rev,
        "target_source": str(target),
        "target_revision": target_rev,
        "data_root": str(data_root),
        "compatibility": compat,
        "ready": compat is not None,
        "reason": None if compat is not None else "compatibility unknown: target has no paos-program manifest; apply requires an explicit compatibility file",
        "business_data_preserved_by": "descriptor source_root switch only; data_root/Home/Project/Library untouched",
    }


def apply_program_rollback(
    installation_file: str | Path,
    target_source: str | Path,
    compatibility_file: str | Path,
    *,
    allow_manual_program_change: bool = False,
) -> dict[str, Any]:
    from paos_installation import (
        effective_data_root,
        load_installation_descriptor,
        resolve_installation_path,
        write_installation_descriptor,
    )

    plan = plan_program_rollback(installation_file, target_source)
    target = Path(plan["target_source"])
    compat = _load_compat(Path(compatibility_file))
    for field in ("current_revision", "target_revision"):
        if compat[field] != plan[field]:
            raise RollbackProblem("rollback_compatibility_mismatch", "兼容声明与版本对不一致。", {"field": field})
    for field in ("current_source", "data_root", "target_source"):
        if _path_identity(compat[field]) != _path_identity(plan[field]):
            raise RollbackProblem("rollback_compatibility_mismatch", "兼容声明与本次安装前置不一致。", {"field": field})
    descriptor_path = resolve_installation_path(str(installation_file))

    def from_state() -> tuple[dict[str, Any], Path]:
        descriptor = load_installation_descriptor(descriptor_path)
        if (
            _path_identity(descriptor.get("source_root") or "") != _path_identity(plan["current_source"])
            or _path_identity(descriptor.get("data_root") or "") != _path_identity(plan["data_root"])
        ):
            raise RollbackProblem("rollback_installation_changed", "plan 之后安装描述已变化，拒绝执行。")
        return descriptor, effective_data_root(descriptor)

    descriptor, data_root = from_state()
    from data_root_writer import DataRootInUseError, DataRootWriterLease

    try:
        lease = DataRootWriterLease(data_root / "project-registry")
    except DataRootInUseError as error:
        raise RollbackProblem(
            "rollback_writer_active", "当前仍有 Core writer 持有数据根；先由 Rooter 正常停止写者。",
        ) from error
    try:
        descriptor, data_root = from_state()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = descriptor_path.with_name(descriptor_path.name + f".before-rollback-{stamp}")
        if backup.exists():
            raise RollbackProblem("rollback_backup_exists", "回退备份路径已存在，拒绝覆盖。")
        temporary = backup.with_name(backup.name + ".staging")
        temporary.write_bytes(descriptor_path.read_bytes())
        os.replace(temporary, backup)
        write_installation_descriptor(
            descriptor_path,
            source_root=_durable_source_locator(str(descriptor.get("source_root") or ""), target),
            library_roots_config=str(descriptor.get("library_roots_config") or ""),
            rooter_home=descriptor.get("rooter_home") or "",
            agent_numbers_config=descriptor.get("agent_numbers_config") or "",
            data_root=str(descriptor.get("data_root") or ""),
        )
    finally:
        lease.close()

    return {
        "schema": "paos-program-rollback/v1",
        "ok": True,
        "read_only": False,
        "apply": True,
        "previous_source": plan["current_source"],
        "source_root": _durable_source_locator(str(descriptor.get("source_root") or ""), target),
        "data_root": str(data_root),
        "descriptor": str(descriptor_path),
        "descriptor_backup": str(backup),
        "note": "program locator switched only; running services may still have old code until their normal restart",
    }
