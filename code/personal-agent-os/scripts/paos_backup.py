#!/usr/bin/env python3
"""Create and restore installation-level PAOS backups.

The archive contains files physically stored under ``private-data/`` plus a
small manifest. It deliberately does not follow symlinks, Windows junctions,
or external paths referenced by those files. Rebuildable ``build/``/``runtime/``
output and the Secret Store are outside this backup scope.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

SCHEMA = "paos-install-backup/v1"
MANIFEST_NAME = "paos-backup-manifest.json"
PRIVATE_PREFIX = "private-data/"


class BackupError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _source_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and commit else None


def _iter_private_files(private_root: Path) -> tuple[list[Path], list[str], list[str]]:
    files: list[Path] = []
    directories: list[str] = []
    skipped_links: list[str] = []
    if not private_root.exists():
        return files, directories, skipped_links

    for current, dirnames, filenames in os.walk(private_root, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(private_root)
        if relative_dir != Path("."):
            directories.append(relative_dir.as_posix())

        kept_dirs: list[str] = []
        for dirname in dirnames:
            child = current_path / dirname
            relative = child.relative_to(private_root).as_posix()
            if _is_link_like(child) or not _inside(child, private_root):
                skipped_links.append(relative)
            else:
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(private_root).as_posix()
            if _is_link_like(path) or not _inside(path, private_root):
                skipped_links.append(relative)
                continue
            if path.is_file():
                files.append(path)

    files.sort(key=lambda item: item.relative_to(private_root).as_posix())
    directories.sort()
    skipped_links.sort()
    return files, directories, skipped_links


def create_backup(repo_root: Path, output: Path, *, data_root: Path | None = None) -> dict[str, object]:
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        raise BackupError(f"仓库目录不存在：{repo_root}")
    private_root = Path(data_root).expanduser().resolve() if data_root else repo_root / "private-data"
    output = output.expanduser().resolve()

    if _is_link_like(private_root):
        raise BackupError("private-data/ 本身是链接或 junction；为避免递归复制外部数据，拒绝备份。")
    if _inside(output, private_root):
        raise BackupError("备份文件不能写进 private-data/，否则会把备份再次打进自己。")
    if output.exists():
        raise BackupError(f"备份目标已存在，拒绝覆盖：{output}")

    files, directories, skipped_links = _iter_private_files(private_root)
    total_bytes = sum(path.stat().st_size for path in files)
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "created_at": _utc_now(),
        "source_commit": _source_commit(repo_root),
        "release_tag": os.environ.get("PAOS_RELEASE_TAG") or None,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "skipped_links": skipped_links,
        "scope": {
            "included": "files physically stored under private-data/",
            "not_embedded": [
                "rebuildable build/ and runtime/ output",
                "Secret Store content",
                "targets of external paths referenced by private-data files",
                "symlink or Windows junction targets",
            ],
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with zipfile.ZipFile(
            temp_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        ) as archive:
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            )
            for directory in directories:
                archive.writestr(f"{PRIVATE_PREFIX}{directory.rstrip('/')}/", b"")
            for path in files:
                relative = path.relative_to(private_root).as_posix()
                archive.write(path, f"{PRIVATE_PREFIX}{relative}")

        with zipfile.ZipFile(temp_path, "r") as archive:
            bad = archive.testzip()
            if bad:
                raise BackupError(f"备份 ZIP 校验失败：{bad}")
            loaded = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
            if loaded.get("schema") != SCHEMA:
                raise BackupError("备份 manifest schema 校验失败。")

        os.replace(temp_path, output)
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise BackupError(f"创建备份失败：{error}") from error
    finally:
        temp_path.unlink(missing_ok=True)

    return manifest


def _safe_member(name: str) -> PurePosixPath:
    if name == MANIFEST_NAME:
        return PurePosixPath(name)
    normalized = PurePosixPath(name)
    if (
        normalized.is_absolute()
        or not name.startswith(PRIVATE_PREFIX)
        or ".." in normalized.parts
        or "\\" in name
    ):
        raise BackupError(f"备份包含非法路径：{name}")
    return normalized


def _validate_archive(archive: zipfile.ZipFile) -> dict[str, object]:
    bad = archive.testzip()
    if bad:
        raise BackupError(f"备份 ZIP 校验失败：{bad}")
    names = archive.namelist()
    if MANIFEST_NAME not in names:
        raise BackupError("备份缺少 paos-backup-manifest.json。")
    for name in names:
        _safe_member(name)
    try:
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BackupError("备份 manifest 无法读取。") from error
    if manifest.get("schema") != SCHEMA:
        raise BackupError(f"不支持的备份 schema：{manifest.get('schema')!r}")
    return manifest


def _extract_private_data(archive: zipfile.ZipFile, staging_root: Path) -> Path:
    staged_private = staging_root / "private-data"
    staged_private.mkdir(parents=True, exist_ok=True)
    for info in archive.infolist():
        if info.filename == MANIFEST_NAME:
            continue
        normalized = _safe_member(info.filename)
        relative = PurePosixPath(*normalized.parts[1:])
        target = staged_private.joinpath(*relative.parts)
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info, "r") as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
    return staged_private


def restore_backup(
    repo_root: Path,
    archive_path: Path,
    *,
    replace_existing: bool = False,
    data_root: Path | None = None,
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        raise BackupError(f"仓库目录不存在：{repo_root}")
    archive_path = archive_path.expanduser().resolve()
    target = Path(data_root).expanduser().resolve() if data_root else repo_root / "private-data"

    if _is_link_like(target):
        raise BackupError("private-data/ 本身是链接或 junction；拒绝用安装级恢复覆盖外部目标。")
    if not archive_path.is_file():
        raise BackupError(f"备份文件不存在：{archive_path}")
    if _inside(archive_path, target):
        raise BackupError("恢复 ZIP 不能位于 private-data/ 内；请先移动到独立备份目录。")
    if target.exists() and any(target.iterdir()) and not replace_existing:
        raise BackupError("private-data/ 已存在且非空；如已先备份，请显式使用 --replace-existing。")

    staging_root = Path(tempfile.mkdtemp(prefix=".paos-restore-", dir=target.parent))
    rollback_path = target.parent / f".{target.name}.pre-restore-{os.getpid()}"
    moved_existing = False
    try:
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                manifest = _validate_archive(archive)
                staged_private = _extract_private_data(archive, staging_root)
        except (OSError, zipfile.BadZipFile) as error:
            raise BackupError(f"无法读取备份：{error}") from error

        if target.exists():
            if any(target.iterdir()):
                if rollback_path.exists():
                    raise BackupError(f"临时回滚目录已存在：{rollback_path}")
                target.rename(rollback_path)
                moved_existing = True
            else:
                target.rmdir()

        try:
            staged_private.rename(target)
        except OSError as error:
            if moved_existing and rollback_path.exists() and not target.exists():
                rollback_path.rename(target)
            raise BackupError(f"恢复数据落盘失败，原 private-data 已回滚：{error}") from error

        if moved_existing and rollback_path.exists():
            shutil.rmtree(rollback_path)
        return manifest
    finally:
        if rollback_path.exists() and not target.exists():
            rollback_path.rename(target)
        shutil.rmtree(staging_root, ignore_errors=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    backup = sub.add_parser("backup", help="备份 private-data/ 用户环境")
    backup.add_argument("--repo-root", type=Path, required=True)
    backup.add_argument("--output", type=Path, required=True)
    backup.add_argument("--data-root", type=Path, help="Registered installation data root")
    backup.add_argument("--installation-file", type=Path, help="Installation descriptor")

    restore = sub.add_parser("restore", help="从安装级备份恢复 private-data/")
    restore.add_argument("--repo-root", type=Path, required=True)
    restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument("--replace-existing", action="store_true")
    restore.add_argument("--data-root", type=Path, help="Registered installation data root")
    restore.add_argument("--installation-file", type=Path, help="Installation descriptor")
    return parser


def _resolve_data_root(args: argparse.Namespace) -> Path | None:
    if args.data_root is not None:
        return args.data_root
    from paos_installation import (
        InstallationProblem,
        effective_data_root,
        load_installation_descriptor,
        resolve_installation_path,
    )

    try:
        descriptor = load_installation_descriptor(
            args.installation_file or resolve_installation_path()
        )
    except InstallationProblem as error:
        if "not_registered" in getattr(error, "code", ""):
            return None
        raise
    if not descriptor.get("configured"):
        return None
    return effective_data_root(descriptor)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        data_root = _resolve_data_root(args)
        if args.command == "backup":
            manifest = create_backup(args.repo_root, args.output, data_root=data_root)
            print(
                f"[OK] 备份完成：{args.output} · "
                f"{manifest['file_count']} files · {manifest['total_bytes']} bytes"
            )
        else:
            manifest = restore_backup(
                args.repo_root,
                args.archive,
                replace_existing=args.replace_existing,
                data_root=data_root,
            )
            print(
                f"[OK] 恢复完成：{args.archive} · "
                f"source_commit={manifest.get('source_commit') or 'unknown'}"
            )
        return 0
    except BackupError as error:
        print(f"[ERROR] {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
