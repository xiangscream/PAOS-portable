"""Filesystem-only Guide review/promotion helpers for S3-3.

The canonical Project Practice remains a local Markdown file under the Project
workspace. PAOS stays the durable source of Project/Work/Session/Request facts.
This helper only compares and promotes reviewed Guide bytes; it performs no
HTTP and imports no PAOS Store/Workflow modules.
"""

from __future__ import annotations

import difflib
import hashlib
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class GuideProblem(Exception):
    """A Guide review/promotion failure with a stable CLI-facing code."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_sha256(value: str, label: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise GuideProblem(
            "guide_review_hash_invalid",
            f"{label} 必须是 64 位 sha256。",
            {"field": label, "value": text},
        )
    return text


def _safe_path_component(value: str, label: str) -> str:
    text = str(value or "").strip()
    if (
        not text
        or text in {".", ".."}
        or "/" in text
        or "\\" in text
        or Path(text).name != text
    ):
        raise GuideProblem(
            "guide_path_component_invalid",
            f"{label} 不是安全的单一路径组件。",
            {"field": label, "value": text},
        )
    return text


def guide_paths(
    root: Path,
    *,
    work_id: str,
    session_id: str,
    cycle: int,
) -> dict[str, Path]:
    safe_work = _safe_path_component(work_id, "work_id")
    safe_session = _safe_path_component(session_id, "session_id")
    if isinstance(cycle, bool) or not isinstance(cycle, int) or cycle < 1:
        raise GuideProblem(
            "guide_cycle_invalid",
            "cycle 必须是正整数。",
            {"cycle": cycle},
        )
    base = root / ".paos"
    workstation = base / "workstations" / safe_work / safe_session / f"cycle-{cycle}"
    return {
        "canonical": base / "practice" / "WORKFLOW-GUIDE.md",
        "workstation": workstation,
        "candidate": workstation / "GUIDE.md",
        "seed": workstation / "review" / "GUIDE-SEED.md",
    }


def _read_required(path: Path, *, code: str, label: str) -> bytes:
    try:
        if not path.is_file():
            raise FileNotFoundError(path)
        return path.read_bytes()
    except OSError as exc:
        raise GuideProblem(
            code,
            f"{label} 不可读取：{path}",
            {"path": str(path), "os_error": str(exc)},
        ) from exc


def _decode_guide(data: bytes, *, path: Path) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GuideProblem(
            "guide_not_utf8",
            f"Guide 必须是 UTF-8 Markdown：{path}",
            {"path": str(path)},
        ) from exc


def build_guide_diff(
    candidate_src: Path,
    *,
    canonical_src: Path,
) -> dict[str, Any]:
    """Compare one real candidate GUIDE file against the canonical source.

    Workless：无 Work/Cycle 定位；两者都是真实文件路径。"""
    candidate_path = Path(candidate_src)
    canonical_path = Path(canonical_src)
    candidate = _read_required(candidate_path, code="guide_candidate_missing", label="Guide candidate")
    canonical = _read_required(canonical_path, code="canonical_guide_missing", label="Canonical Guide")
    candidate_text = _decode_guide(candidate, path=candidate_path)
    canonical_text = _decode_guide(canonical, path=canonical_path)
    diff = chr(10).join(
        difflib.unified_diff(
            canonical_text.splitlines(),
            candidate_text.splitlines(),
            fromfile="canonical-WORKFLOW-GUIDE.md",
            tofile="candidate-GUIDE.md",
            lineterm="",
        )
    )
    candidate_sha = _sha256(candidate)
    canonical_sha = _sha256(canonical)
    return {
        "schema": "paos-guide-diff/v2",
        "candidate_path": str(candidate_path),
        "canonical_path": str(canonical_path),
        "changed": candidate_sha != canonical_sha,
        "candidate_sha256": candidate_sha,
        "canonical_sha256": canonical_sha,
        "diff": diff,
    }


def validate_current_coordinator(
    project: dict[str, Any],
    *,
    coordinator_session_id: str,
    execution_cycle: int | None = None,
    context_pack_id: str | None = None,
) -> dict[str, Any]:
    """Workless：只校验当前 Coordinator 身份/ack/runtime；Cycle 尾随参数保留但必须为空。"""
    organization = project.get("organization") or {}
    current = str(organization.get("coordinator_session_id") or "")
    if current != coordinator_session_id:
        raise GuideProblem(
            "guide_promoter_not_current_coordinator",
            "只有当前 Project Coordinator 可以通过 Agent CLI 晋升 canonical Guide。",
            {
                "supplied_session_id": coordinator_session_id,
                "current_coordinator_session_id": current,
            },
        )
    coordinator: dict[str, Any] | None = None
    for item in project.get("sessions") or []:
        if isinstance(item, dict) and str(item.get("id") or "") == coordinator_session_id:
            coordinator = item
            break
    if coordinator is None:
        raise GuideProblem(
            "guide_promoter_session_missing",
            f"Coordinator Session 不存在：{coordinator_session_id}",
        )
    if coordinator.get("status") != "active":
        raise GuideProblem(
            "guide_promoter_not_active",
            "Coordinator 必须处于 active 状态。",
            {"status": coordinator.get("status")},
        )
    if coordinator.get("acknowledgement") is None:
        raise GuideProblem(
            "guide_promoter_not_acknowledged",
            "Coordinator 必须先 Acknowledge 当前 Cycle。",
        )
    if not str(coordinator.get("runtime_id") or "").strip():
        raise GuideProblem(
            "guide_promoter_runtime_missing",
            "Coordinator 必须已有当前 Runtime binding。",
        )
    return coordinator


@contextmanager
def _promotion_lock(lock_path: Path) -> Iterator[None]:
    """Cross-platform non-blocking advisory lock with no stale lock ownership."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise GuideProblem(
                "guide_promotion_busy",
                "另一个 Guide promotion 正在进行；拒绝并发覆盖 canonical Guide。",
                {"lock_path": str(lock_path), "os_error": str(exc)},
            ) from exc
        try:
            yield
        finally:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        handle.close()


def promote_guide_candidate(
    candidate_src: Path,
    *,
    canonical_src: Path,
    expected_candidate_sha256: str,
    change_summary: str,
) -> dict[str, Any]:
    """Atomically promote exactly the reviewed candidate file to canonical Guide.

    Workless：无 Work/Cycle/seed 三方对照；安全由 expected_candidate_sha256
    + change_summary + lock + 原子替换组成。"""
    expected_candidate = _validate_sha256(expected_candidate_sha256, "expected_candidate_sha256")
    candidate_path = Path(candidate_src)
    canonical_path = Path(canonical_src)
    candidate = _read_required(candidate_path, code="guide_candidate_missing", label="Guide candidate")
    canonical = _read_required(canonical_path, code="canonical_guide_missing", label="Canonical Guide")
    summary = str(change_summary or "").strip()
    if not summary:
        raise GuideProblem(
            "guide_change_summary_missing",
            "晋升 canonical Guide 必须说明本次可泛化改进。",
        )
    lock_path = canonical_path.parent / ".WORKFLOW-GUIDE.promote.lock"
    with _promotion_lock(lock_path):
        candidate_sha = _sha256(candidate)
        canonical_sha = _sha256(canonical)
        if candidate_sha != expected_candidate:
            raise GuideProblem(
                "guide_candidate_changed_after_review",
                "GUIDE.md 在审阅后发生变化，必须重新生成并审阅 diff。",
                {"expected": expected_candidate, "actual": candidate_sha},
            )
        if candidate_sha == canonical_sha:
            return {
                "schema": "paos-guide-promotion/v1",
                "promoted": False,
                "already_current": True,
                "canonical_path": str(canonical_path),
                "candidate_sha256": candidate_sha,
                "previous_canonical_sha256": canonical_sha,
                "canonical_sha256": canonical_sha,
                "change_summary": summary,
            }
        if not _decode_guide(candidate, path=candidate_path).strip():
            raise GuideProblem(
                "guide_candidate_empty",
                "拒绝用空 GUIDE 覆盖 canonical Practice。",
            )
        staged = canonical_path.parent / f".WORKFLOW-GUIDE.promote-{uuid.uuid4().hex}"
        try:
            with staged.open("wb") as handle:
                handle.write(candidate)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staged, canonical_path)
        except Exception:
            staged.unlink(missing_ok=True)
            raise
        return {
            "schema": "paos-guide-promotion/v1",
            "promoted": True,
            "canonical_path": str(canonical_path),
            "candidate_sha256": candidate_sha,
            "previous_canonical_sha256": canonical_sha,
            "canonical_sha256": candidate_sha,
            "change_summary": summary,
        }
