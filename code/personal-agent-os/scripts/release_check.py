#!/usr/bin/env python3
"""Check PAOS release boundaries and optionally build a source ZIP from HEAD."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


FORBIDDEN_PREFIXES = (
    "private-data/",
    "runtime/",
    "raw-logs/",
    "logs/",
    "build/",
    "attention-memory-pipeline-v0/build/",
)
FORBIDDEN_SUFFIXES = (".pem", ".key", ".pfx", ".log", ".db", ".sqlite", ".sqlite3", ".pid")


class ReleaseCheckError(RuntimeError):
    pass


def forbidden_reason(path: str) -> str | None:
    normalized = PurePosixPath(path.replace("\\", "/")).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    lower = normalized.lower()
    name = PurePosixPath(lower).name

    for prefix in FORBIDDEN_PREFIXES:
        if lower.startswith(prefix):
            return f"tracked release path is private/derived: {normalized}"

    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return f"tracked environment file is not release-safe: {normalized}"
    if name.endswith(FORBIDDEN_SUFFIXES):
        return f"tracked secret/runtime-style file is not release-safe: {normalized}"
    if name.startswith("secrets") or "credential" in name or "-secret" in name:
        return f"tracked secret-style filename is not release-safe: {normalized}"
    return None


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as error:
        raise ReleaseCheckError(f"git 无法执行：{error}") from error


def tracked_files(repo_root: Path) -> list[str]:
    result = _git(repo_root, "ls-files", "-z")
    if result.returncode != 0:
        raise ReleaseCheckError(result.stderr.strip() or "git ls-files 失败")
    return [item for item in result.stdout.split("\0") if item]


def check_release_tree(repo_root: Path) -> list[str]:
    violations: list[str] = []
    for path in tracked_files(repo_root):
        reason = forbidden_reason(path)
        if reason:
            violations.append(reason)
    return violations


def _tracked_tree_dirty(repo_root: Path) -> bool:
    result = _git(repo_root, "status", "--porcelain", "--untracked-files=no")
    if result.returncode != 0:
        raise ReleaseCheckError(result.stderr.strip() or "git status 失败")
    return bool(result.stdout.strip())


def build_source_package(repo_root: Path, output: Path) -> None:
    repo_root = repo_root.resolve()
    output = output.expanduser().resolve()
    violations = check_release_tree(repo_root)
    if violations:
        raise ReleaseCheckError("发行边界检查失败：\n- " + "\n- ".join(violations))
    if _tracked_tree_dirty(repo_root):
        raise ReleaseCheckError("tracked 工作区有未提交改动；拒绝把不明确状态当作发行包来源。")
    if output.exists():
        raise ReleaseCheckError(f"发行包已存在，拒绝覆盖：{output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        result = _git(repo_root, "archive", "--format=zip", f"--output={temp_path}", "HEAD")
        if result.returncode != 0:
            raise ReleaseCheckError(result.stderr.strip() or "git archive 失败")
        with zipfile.ZipFile(temp_path, "r") as archive:
            bad = archive.testzip()
            if bad:
                raise ReleaseCheckError(f"发行 ZIP 校验失败：{bad}")
            archive_violations = [
                reason
                for name in archive.namelist()
                if not name.endswith("/")
                for reason in [forbidden_reason(name)]
                if reason
            ]
            if archive_violations:
                raise ReleaseCheckError(
                    "发行 ZIP 出现禁止路径：\n- " + "\n- ".join(archive_violations)
                )
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--package", type=Path, help="检查通过后用 git archive HEAD 生成 ZIP")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    try:
        violations = check_release_tree(repo_root)
        if violations:
            print("[ERROR] 发行边界检查失败：")
            for violation in violations:
                print(f"- {violation}")
            return 2
        count = len(tracked_files(repo_root))
        print(f"[OK] 发行边界：{count} 个 tracked paths 未发现 private/runtime/secret 类文件。")
        if args.package:
            build_source_package(repo_root, args.package)
            print(f"[OK] source package: {args.package}")
        return 0
    except ReleaseCheckError as error:
        print(f"[ERROR] {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
