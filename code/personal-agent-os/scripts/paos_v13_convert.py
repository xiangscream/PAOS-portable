"""One-time V1.3 workstation conversion helpers.

The converter preserves source files before changing an active Home.  It does
not infer business completion, does not ACK Sessions, and never creates an
activation intent for imported historical inputs.

The migration manifest is evidence/rollback material, not a second runtime
queue or a long-lived handling authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

from paos_home import project_agent_home, rooter_home
from paos_mail import (
    MAIL_ID_RE,
    MailProblem,
    parse_mail_frontmatter,
    read_handling,
)
from paos_notice import (
    NoticeProblem,
    import_notice,
    input_identity,
    notice_id_for,
    notice_path,
)
from paos_todo_v3 import (
    TodoV3Problem,
    parse_todo_v3,
    read_todo_v3,
    render_todo_v3,
    write_todo_v3,
)
from paos_workstation import (
    WorkstationProblem,
    parse_todo_markdown,
    posix_windows_drive_locator,
)


MIGRATION_SCHEMA = "paos-v13-home-migration/v1"
_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:\d{4}-)?(?:[awrseg]\d+|T-\d+)(?![A-Za-z0-9])",
    re.IGNORECASE,
)


class V13ConversionProblem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        staged.write_text(text, encoding="utf-8", newline="\n")
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def _clean_manifest_id(value: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,119}", text):
        raise V13ConversionProblem(
            "v13_manifest_id_invalid",
            "manifest_id 格式无效。",
            {"manifest_id": text},
        )
    return text


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_context_refs(text: str) -> list[str]:
    return _unique(match.group(0) for match in _REFERENCE_RE.finditer(text))


def _sections(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    active = ""
    for raw in text.splitlines():
        if raw.startswith("## "):
            active = raw[3:].strip()
            result.setdefault(active, [])
            continue
        if active:
            result.setdefault(active, []).append(raw)
    return result


def _current_result_values(text: str) -> list[str]:
    current = _sections(text).get("当前") or []
    values: list[str] = []
    for raw in current:
        stripped = raw.strip()
        if stripped.startswith("成果："):
            values.append(stripped[len("成果：") :].strip())
    return _unique(values)


def _task_from_v2(item: dict[str, Any]) -> dict[str, Any]:
    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    waiting = str(details.get("waiting") or "").strip()
    state = "done" if item.get("done") else ("waiting" if waiting else "todo")
    return {
        "id": str(item.get("id") or ""),
        "title": str(item.get("title") or ""),
        "state": state,
        "waiting": waiting,
        "result": str(details.get("result") or ""),
        "artifact_ref": str(details.get("artifact") or ""),
        "notify_after": [],
    }


def _v2_task_occurrences(source_text: str) -> dict[str, list[dict[str, Any]]]:
    """Locate task ids in the active ## 待办 section for actionable errors."""
    result: dict[str, list[dict[str, Any]]] = {}
    active = False
    pattern = re.compile(
        r"^\s*-\s+\[[ xX]\]\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s+(.+?)\s*$"
    )
    for line_number, raw in enumerate(source_text.splitlines(), start=1):
        if raw.startswith("## "):
            active = raw[3:].strip() == "待办"
            continue
        if not active:
            continue
        match = pattern.match(raw)
        if not match:
            continue
        task_id = match.group(1)
        result.setdefault(task_id, []).append(
            {
                "line": line_number,
                "text": raw.strip(),
            }
        )
    return result


def _first_heading(text: str) -> str:
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _mail_summary(text: str, meta: dict[str, Any], filename: str) -> str:
    return (
        str(meta.get("subject") or "").strip()
        or _first_heading(text)
        or Path(filename).stem
    )


def _project_mail_source_ref(
    *,
    filename: str,
    declared_message_id: str,
) -> tuple[str, str, str]:
    """Return stable source_ref, identity mode and mapping note.

    Standard Mail keeps its declared message_id. Historical plain Markdown or
    invalid ids use an explicit filename alias; no sender/time/handling fact is
    fabricated.
    """
    declared = str(declared_message_id or "").strip()
    if declared and MAIL_ID_RE.fullmatch(declared):
        return declared, "message_id", ""
    if declared:
        return (
            f"legacy-mail-file:{filename}",
            "filename_alias",
            "declared_message_id_invalid_used_filename_alias",
        )
    return (
        f"legacy-mail-file:{filename}",
        "filename_alias",
        "message_id_missing_used_filename_alias",
    )


def _scan_project_mailbox(
    *,
    root: Path,
    agent_id: str,
) -> dict[str, Any]:
    mailbox = Path(root) / "Workstations" / agent_id / "mailbox"
    if not mailbox.is_dir():
        raise V13ConversionProblem(
            "v13_mailbox_missing",
            f"Project Home mailbox 不存在：{mailbox}",
            {"agent_id": agent_id, "path": str(mailbox)},
        )

    notices: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []
    files = sorted(path for path in mailbox.glob("*.md") if path.is_file())
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            unmapped.append(
                {
                    "source_path": str(path),
                    "source_filename": path.name,
                    "reason": "mail_file_unreadable",
                    "detail": str(exc),
                    "recovery": "保留原件；修复可读性后按同一 migration manifest 补映射。",
                }
            )
            continue

        meta = parse_mail_frontmatter(text)
        declared = str(meta.get("message_id") or "").strip()
        source_ref, identity_mode, mapping_note = _project_mail_source_ref(
            filename=path.name,
            declared_message_id=declared,
        )
        handling = {
            "handled": False,
            "state": "unhandled",
            "reason": "",
            "handled_at": "",
        }
        if identity_mode == "message_id":
            try:
                handling = read_handling(root, agent_id, declared)
            except MailProblem as problem:
                unmapped.append(
                    {
                        "source_path": str(path),
                        "source_filename": path.name,
                        "declared_message_id": declared,
                        "reason": problem.code,
                        "detail": str(problem),
                        "recovery": (
                            "保留原 Mail 与 legacy handling 原件；修复处理记录后补映射，"
                            "不要猜成 handled 或 pending。"
                        ),
                    }
                )
                continue

        notices.append(
            {
                "source_ref": source_ref,
                "message_id": declared if identity_mode == "message_id" else "",
                "source_path": str(path),
                "source_filename": path.name,
                "identity_mode": identity_mode,
                "mapping_note": mapping_note,
                "subject": _mail_summary(text, meta, path.name),
                "created_at": str(meta.get("created_at") or ""),
                "state": "handled" if handling.get("handled") else "pending",
                "handled_at": str(handling.get("handled_at") or ""),
                "resolution": (
                    (
                        _legacy_resolution(str(handling.get("state") or "handled"))
                        + (
                            f": {str(handling.get('reason') or '').strip()}"
                            if str(handling.get("reason") or "").strip()
                            else ""
                        )
                    )
                    if handling.get("handled")
                    else ""
                ),
                "legacy_handling_state": str(
                    handling.get("state") or "unhandled"
                ),
            }
        )

    return {
        "mail_count": len(files),
        "mapped_count": len(notices),
        "unmapped_count": len(unmapped),
        "notices": notices,
        "unmapped_inputs": unmapped,
    }


def _scan_rooter_mailbox(path: Path) -> dict[str, Any]:
    mailbox = Path(path) / "mailbox"
    if not mailbox.is_dir():
        return {
            "mail_count": 0,
            "mapped_count": 0,
            "unmapped_count": 0,
            "notices": [],
            "unmapped_inputs": [],
            "excluded_files": [],
        }

    notices: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    files = sorted(file for file in mailbox.glob("*.md") if file.is_file())
    for file in files:
        if file.name.lower() == "readme.md":
            excluded.append(
                {
                    "source_path": str(file),
                    "source_filename": file.name,
                    "reason": "mailbox_management_readme",
                }
            )
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            unmapped.append(
                {
                    "source_path": str(file),
                    "source_filename": file.name,
                    "reason": "rooter_mail_file_unreadable",
                    "detail": str(exc),
                    "recovery": "保留原件；修复可读性后按同一 manifest 补映射。",
                }
            )
            continue
        meta = parse_mail_frontmatter(text)
        declared = str(meta.get("message_id") or "").strip()
        if declared and MAIL_ID_RE.fullmatch(declared):
            source_ref = declared
            identity_mode = "message_id"
            mapping_note = ""
        elif declared:
            source_ref = f"rooter-mail-file:{file.name}"
            identity_mode = "filename_alias"
            mapping_note = "declared_message_id_invalid_used_filename_alias"
        else:
            source_ref = f"rooter-mail-file:{file.name}"
            identity_mode = "filename_alias"
            mapping_note = "plain_markdown_filename_alias"

        notices.append(
            {
                "source_ref": source_ref,
                "source_path": str(file),
                "source_filename": file.name,
                "declared_message_id": (
                    declared if identity_mode == "message_id" else ""
                ),
                "identity_mode": identity_mode,
                "mapping_note": mapping_note,
                "summary": _mail_summary(text, meta, file.name),
                "created_at": str(meta.get("created_at") or ""),
                "state": "pending",
            }
        )

    return {
        "mail_count": len(files) - len(excluded),
        "mapped_count": len(notices),
        "unmapped_count": len(unmapped),
        "notices": notices,
        "unmapped_inputs": unmapped,
        "excluded_files": excluded,
    }


def _load_migration_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise V13ConversionProblem(
            "v13_manifest_invalid",
            f"manifest 无法读取：{path}",
            {"path": str(path)},
        ) from exc
    if not isinstance(value, dict) or value.get("schema") != MIGRATION_SCHEMA:
        raise V13ConversionProblem(
            "v13_manifest_invalid",
            "manifest schema 无效。",
            {"path": str(path)},
        )
    return value


def _replay_existing_conversion(
    *,
    manifest_path: Path,
    expected_home_kind: str,
    expected_home_id: str,
    expected_project_id: str,
    expected_home_path: Path,
) -> dict[str, Any] | None:
    """Return an already-applied conversion without re-planning v3 as v2.

    Idempotent replay validates the preserved original backup plus the current
    v3 Home identity, but deliberately does not compare current TODO bytes with
    the original candidate: post-cutover progress must survive repeated apply.
    """
    if not manifest_path.is_file():
        return None
    manifest = _load_migration_manifest(manifest_path)
    home = manifest.get("home") if isinstance(manifest.get("home"), dict) else {}
    expected = {
        "home_kind": expected_home_kind,
        "home_id": expected_home_id,
        "project_id": expected_project_id,
        "home_path": str(expected_home_path),
    }
    mismatches = {
        key: {"existing": str(home.get(key) or ""), "expected": value}
        for key, value in expected.items()
        if str(home.get(key) or "") != value
    }
    if mismatches:
        raise V13ConversionProblem(
            "v13_manifest_conflict",
            "现有 manifest 指向不同 Home。",
            {"path": str(manifest_path), "mismatches": mismatches},
        )

    backup = Path(str(manifest.get("todo_backup_path") or ""))
    if not backup.is_file():
        raise V13ConversionProblem(
            "v13_manifest_backup_missing",
            "现有 manifest 的原 TODO backup 不存在。",
            {"path": str(manifest_path), "todo_backup_path": str(backup)},
        )
    actual_backup_sha = _sha256_bytes(backup.read_bytes())
    if actual_backup_sha != str(manifest.get("source_todo_sha256") or ""):
        raise V13ConversionProblem(
            "v13_manifest_backup_changed",
            "现有 manifest 的原 TODO backup 与记录不一致。",
            {
                "path": str(manifest_path),
                "expected_sha256": manifest.get("source_todo_sha256"),
                "actual_sha256": actual_backup_sha,
            },
        )

    try:
        current = read_todo_v3(expected_home_path / "TODO.md")
    except TodoV3Problem as problem:
        raise V13ConversionProblem(
            "v13_manifest_not_active",
            "manifest 已存在，但当前 Home 不再处于对应 V1.3 合同；拒绝伪装 replay。",
            {"path": str(manifest_path), "cause": str(problem)},
        ) from problem
    if (
        current.get("home_kind") != expected_home_kind
        or current.get("home_id") != expected_home_id
        or str(current.get("project_id") or "") != expected_project_id
    ):
        raise V13ConversionProblem(
            "v13_manifest_current_home_mismatch",
            "当前 TODO v3 identity 与 manifest Home 不一致。",
            {"path": str(manifest_path)},
        )

    return {
        **manifest,
        "replayed": True,
        "current_todo_sha256": _sha256_bytes(
            (expected_home_path / "TODO.md").read_bytes()
        ),
        "post_cutover_progress_preserved": True,
    }


def todo_v2_to_v3_text(
    *,
    source_text: str,
    project_id: str,
    agent_id: str,
    legacy_source_ref: str,
    source_path: str = "",
) -> tuple[str, dict[str, Any]]:
    """Convert a trusted v2 TODO without treating its Current summary as history.

    The explicit Current result text remains Current.  References found anywhere
    in the original document are carried separately in context_refs, so older
    accepted artifacts/handoffs are not overwritten or silently promoted to a
    current task.
    """
    parsed = parse_todo_markdown(source_text)
    if parsed.get("schema") != "paos-todo/v2":
        raise V13ConversionProblem(
            "v13_todo_source_schema_invalid",
            "只接受 paos-todo/v2 作为 Project Home 转换输入。",
            {"schema": parsed.get("schema"), "agent_id": agent_id},
        )
    metadata_issues = list(parsed.get("metadata_issues") or [])
    if metadata_issues:
        raise V13ConversionProblem(
            "v13_todo_source_invalid",
            "TODO v2 front matter 无法安全转换。",
            {"agent_id": agent_id, "issues": metadata_issues},
        )
    if str(parsed.get("project_id") or "") != project_id:
        raise V13ConversionProblem(
            "v13_todo_project_mismatch",
            "TODO v2 project_id 与目标 Project 不一致。",
            {
                "expected": project_id,
                "actual": parsed.get("project_id"),
                "agent_id": agent_id,
            },
        )
    if str(parsed.get("agent_id") or "") != agent_id:
        raise V13ConversionProblem(
            "v13_todo_agent_mismatch",
            "TODO v2 agent_id 与目标 Home 不一致。",
            {
                "expected": agent_id,
                "actual": parsed.get("agent_id"),
            },
        )

    current = parsed.get("current") if isinstance(parsed.get("current"), dict) else {}
    objective = str(current.get("objective") or "").strip()
    next_action = str(current.get("next") or "").strip()
    if not objective or not next_action:
        raise V13ConversionProblem(
            "v13_todo_current_incomplete",
            "TODO v2 Current 缺少 objective/next；拒绝由转换器猜业务。",
            {
                "agent_id": agent_id,
                "objective": objective,
                "next_action": next_action,
            },
        )

    current_results = _current_result_values(source_text)
    if not current_results and str(current.get("results") or "").strip():
        current_results = [str(current.get("results") or "").strip()]
    result_refs = extract_context_refs("\n".join(current_results))
    context_refs = extract_context_refs(source_text)
    tasks = [
        _task_from_v2(item)
        for item in (parsed.get("tasks") or [])
        if isinstance(item, dict)
    ]
    occurrences = _v2_task_occurrences(source_text)
    duplicates = {
        task_id: items
        for task_id, items in occurrences.items()
        if len(items) > 1
    }
    if duplicates:
        raise V13ConversionProblem(
            "v13_todo_duplicate_task_id",
            "TODO v2 的 ## 待办 中存在重复 task id；拒绝静默合并或重命名。",
            {
                "agent_id": agent_id,
                "source_ref": legacy_source_ref,
                "source_path": source_path,
                "duplicate_task_ids": sorted(duplicates),
                "occurrences": [
                    {"task_id": task_id, **item}
                    for task_id in sorted(duplicates)
                    for item in duplicates[task_id]
                ],
                "recovery": "由 Home 本人修正源 TODO 的重复 ID 后重跑 dry-run。",
            },
        )
    text = render_todo_v3(
        home_kind="project_agent",
        home_id=agent_id,
        project_id=project_id,
        objective=objective,
        approved_scope="",
        stage=str(current.get("stage") or ""),
        next_action=next_action,
        waiting=str(current.get("waiting") or ""),
        results="；".join(current_results),
        result_refs=result_refs,
        context_refs=context_refs,
        legacy_source_ref=legacy_source_ref,
        inflight=str(current.get("inflight") or ""),
        alignment_ref="",
        input_version="legacy:paos-todo/v2",
        delivery="",
        dependencies="",
        continuation_to="",
        tasks=tasks,
    )
    return text, {
        "current_result_values": current_results,
        "result_refs": result_refs,
        "context_refs": context_refs,
        "task_ids": [task["id"] for task in tasks],
    }


def rooter_plain_todo_to_v3_text(
    *,
    source_text: str,
    home_id: str,
    legacy_source_ref: str,
    objective: str,
    next_action: str,
    approved_scope: str = "",
    stage: str = "",
    waiting: str = "",
    results: str = "",
    inflight: str = "",
    alignment_ref: str = "",
    input_version: str = "",
    delivery: str = "",
    dependencies: str = "",
    continuation_to: str = "",
    tasks: Iterable[dict[str, Any]] = (),
) -> tuple[str, dict[str, Any]]:
    """Convert Rooter plain Markdown only with explicit Current mapping.

    The converter preserves the old text by reference and extracts references,
    but it never guesses Rooter's current objective/next action from prose.
    """
    objective = str(objective or "").strip()
    next_action = str(next_action or "").strip()
    if not objective or not next_action:
        raise V13ConversionProblem(
            "v13_rooter_current_required",
            "Rooter plain Markdown 转换必须显式提供 objective 与 next_action。",
            {"home_id": home_id},
        )
    refs = extract_context_refs(source_text)
    text = render_todo_v3(
        home_kind="rooter",
        home_id=home_id,
        objective=objective,
        approved_scope=approved_scope,
        stage=stage,
        next_action=next_action,
        waiting=waiting,
        results=results,
        result_refs=extract_context_refs(results),
        context_refs=refs,
        legacy_source_ref=legacy_source_ref,
        inflight=inflight,
        alignment_ref=alignment_ref,
        input_version=input_version or "legacy:plain-markdown",
        delivery=delivery,
        dependencies=dependencies,
        continuation_to=continuation_to,
        tasks=tasks,
    )
    return text, {"context_refs": refs}


def _legacy_resolution(handling_state: str) -> str:
    state = str(handling_state or "handled").strip()
    return f"legacy_mail_{state}"


def plan_project_home_conversion(
    *,
    root: Path,
    project: dict[str, Any],
    agent_id: str,
    manifest_id: str,
) -> dict[str, Any]:
    manifest_id = _clean_manifest_id(manifest_id)
    root = Path(posix_windows_drive_locator(str(root))).expanduser()
    try:
        home = project_agent_home(
            project=project,
            agent_id=agent_id,
            root_override=str(root),
        )
    except Exception as problem:
        raise V13ConversionProblem(
            getattr(problem, "code", "v13_home_invalid"),
            str(problem),
            getattr(problem, "details", {}),
        ) from problem
    home_path = Path(home["home_path"])
    todo_path = home_path / "TODO.md"
    if not todo_path.is_file():
        raise V13ConversionProblem(
            "v13_todo_missing",
            f"TODO v2 不存在：{todo_path}",
            {"agent_id": agent_id, "path": str(todo_path)},
        )
    try:
        todo_bytes = todo_path.read_bytes()
        todo_text = todo_bytes.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise V13ConversionProblem(
            "v13_todo_unreadable",
            f"TODO v2 无法读取：{todo_path}",
            {"path": str(todo_path)},
        ) from exc

    legacy_ref = f"migration:{manifest_id}/{agent_id}/TODO.v2.md"
    candidate, todo_evidence = todo_v2_to_v3_text(
        source_text=todo_text,
        project_id=str(project.get("id") or ""),
        agent_id=agent_id,
        legacy_source_ref=legacy_ref,
        source_path=str(todo_path),
    )
    mail_scan = _scan_project_mailbox(root=Path(root), agent_id=agent_id)
    notices = list(mail_scan["notices"])
    return {
        "schema": MIGRATION_SCHEMA,
        "manifest_id": manifest_id,
        "home": home,
        "source_todo_path": str(todo_path),
        "source_todo_sha256": _sha256_bytes(todo_bytes),
        "candidate_todo_text": candidate,
        "candidate_todo_sha256": _sha256_bytes(candidate.encode("utf-8")),
        "todo_evidence": todo_evidence,
        "mail_count": int(mail_scan["mail_count"]),
        "mapped_count": int(mail_scan["mapped_count"]),
        "unmapped_count": int(mail_scan["unmapped_count"]),
        "handled_count": sum(1 for item in notices if item["state"] == "handled"),
        "pending_count": sum(1 for item in notices if item["state"] == "pending"),
        "notices": notices,
        "mail_mappings": [
            {
                "source_ref": item["source_ref"],
                "source_path": item["source_path"],
                "source_filename": item["source_filename"],
                "identity_mode": item["identity_mode"],
                "message_id": item.get("message_id", ""),
                "mapping_note": item.get("mapping_note", ""),
                "state": item["state"],
            }
            for item in notices
        ],
        "unmapped_inputs": list(mail_scan["unmapped_inputs"]),
        "activation_intents_created": 0,
    }


def apply_project_home_conversion(
    *,
    root: Path,
    project: dict[str, Any],
    agent_id: str,
    manifest_id: str,
) -> dict[str, Any]:
    """Apply one Project Home conversion with rollback-on-error for new writes."""
    root = Path(posix_windows_drive_locator(str(root))).expanduser()
    manifest_id = _clean_manifest_id(manifest_id)
    try:
        resolved_home = project_agent_home(
            project=project,
            agent_id=agent_id,
            root_override=str(root),
        )
    except Exception as problem:
        raise V13ConversionProblem(
            getattr(problem, "code", "v13_home_invalid"),
            str(problem),
            getattr(problem, "details", {}),
        ) from problem
    home_path = Path(resolved_home["home_path"])
    migration_dir = (
        root / ".paos" / "v13-migration" / manifest_id / agent_id
    )
    manifest_path = migration_dir / "manifest.json"
    replayed = _replay_existing_conversion(
        manifest_path=manifest_path,
        expected_home_kind="project_agent",
        expected_home_id=agent_id,
        expected_project_id=str(project.get("id") or ""),
        expected_home_path=home_path,
    )
    if replayed is not None:
        return replayed
    if migration_dir.exists():
        raise V13ConversionProblem(
            "v13_incomplete_migration_dir",
            "发现没有 manifest 的既有迁移目录；拒绝覆盖可能的中断证据。",
            {
                "path": str(migration_dir),
                "recovery": "由 Rooter/Reviewer 检查该目录后显式恢复或移出，再重跑同一转换。",
            },
        )

    plan = plan_project_home_conversion(
        root=root,
        project=project,
        agent_id=agent_id,
        manifest_id=manifest_id,
    )
    migration_dir.mkdir(parents=True, exist_ok=False)
    todo_path = home_path / "TODO.md"
    todo_backup = migration_dir / "TODO.v2.md"
    handling_dir = home_path / "mailbox" / ".handled"
    handling_backup = migration_dir / "handled-v1"
    created_notice_paths: list[Path] = []
    imported_notice_ids: list[str] = []
    todo_replaced = False
    handling_archived_path = home_path / "mailbox" / f".handled.v1-archive-{plan['manifest_id']}"

    try:
        shutil.copy2(todo_path, todo_backup)
        if handling_dir.is_dir():
            shutil.copytree(handling_dir, handling_backup)
        elif handling_dir.exists():
            raise V13ConversionProblem(
                "v13_handling_path_invalid",
                f"legacy handling 路径不是目录：{handling_dir}",
                {"path": str(handling_dir)},
            )

        for item in plan["notices"]:
            before_path = notice_path(
                home_path,
                notice_id_for(
                    input_identity(
                        home_kind="project_agent",
                        home_id=agent_id,
                        project_id=str(project.get("id") or ""),
                        source_kind="mail",
                        source_ref=item["source_ref"],
                    )
                ),
            )
            existed = before_path.exists()
            imported = import_notice(
                home_path=home_path,
                home_kind="project_agent",
                home_id=agent_id,
                project_id=str(project.get("id") or ""),
                source_kind="mail",
                source_ref=item["source_ref"],
                summary=item["subject"],
                state=item["state"],
                created_at=item["created_at"],
                handled_at=item["handled_at"],
                resolution=item["resolution"],
                action_ref=(
                    f"legacy-handling:{item['message_id']}"
                    if item["state"] == "handled" and item.get("message_id")
                    else ""
                ),
            )
            imported_notice_ids.append(str(imported.get("notice_id") or ""))
            if imported.get("created") and not existed:
                created_notice_paths.append(Path(imported["path"]))

        current_sha = _sha256_bytes(todo_path.read_bytes())
        if current_sha != plan["source_todo_sha256"]:
            raise V13ConversionProblem(
                "v13_todo_changed_during_conversion",
                "TODO 在转换准备后发生变化；拒绝覆盖。",
                {
                    "path": str(todo_path),
                    "planned_sha256": plan["source_todo_sha256"],
                    "current_sha256": current_sha,
                },
            )
        write_todo_v3(todo_path, plan["candidate_todo_text"])
        todo_replaced = True

        if handling_dir.is_dir():
            if handling_archived_path.exists():
                raise V13ConversionProblem(
                    "v13_handling_archive_conflict",
                    "legacy handling archive 目标已存在。",
                    {"path": str(handling_archived_path)},
                )
            os.rename(handling_dir, handling_archived_path)

        manifest = {
            key: value
            for key, value in plan.items()
            if key not in {"candidate_todo_text", "notices"}
        }
        manifest.update(
            {
                "replayed": False,
                "todo_backup_path": str(todo_backup),
                "legacy_handling_backup_path": (
                    str(handling_backup) if handling_backup.exists() else ""
                ),
                "legacy_handling_archived_path": (
                    str(handling_archived_path) if handling_archived_path.exists() else ""
                ),
                "notice_ids": [value for value in imported_notice_ids if value],
                "activation_intents_created": 0,
            }
        )
        parse_todo_v3(todo_path.read_text(encoding="utf-8"))
        _atomic_write(
            manifest_path,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        return manifest
    except Exception:
        if handling_archived_path.is_dir() and not handling_dir.exists():
            os.rename(handling_archived_path, handling_dir)
        if todo_replaced and todo_backup.is_file():
            shutil.copy2(todo_backup, todo_path)
        for path in created_notice_paths:
            path.unlink(missing_ok=True)
        shutil.rmtree(migration_dir, ignore_errors=True)
        raise


def plan_v3_home_convergence(
    *,
    home_path: Path,
    home_kind: str,
    home_id: str,
    project_id: str = "",
) -> dict[str, Any]:
    """Plan one Workless field/interface convergence for an EXISTING v3 Home.

    This is not the legacy v2 entry conversion. It re-renders the current v3
    TODO with the workless Current contract (no `current_work` output field),
    keeps every Current field value, every Task row and every notify_after
    binding verbatim, and never touches Notices or Mail.
    """
    todo_path = Path(home_path) / "TODO.md"
    source_text = todo_path.read_text(encoding="utf-8")
    source = parse_todo_v3(source_text)
    if str(source.get("schema") or "") != "paos-todo/v3":
        raise V13ConversionProblem(
            "v3_convergence_not_v3",
            "目标 Home 的 TODO 不是 paos-todo/v3；请走 apply_project_home_conversion 或先核实来源。",
            {"path": str(todo_path), "schema": source.get("schema")},
        )
    current = source.get("current") or {}
    expected_identity = {
        "home_kind": home_kind,
        "home_id": home_id,
        "project_id": project_id,
    }
    for key, value in expected_identity.items():
        if value and str(source.get(key) or "") != value:
            raise V13ConversionProblem(
                "v3_convergence_identity_mismatch",
                f"TODO {key}（{source.get(key)}）与参数 {value} 不一致；拒绝误转他人 Home。",
                {"path": str(todo_path)},
            )
    source_refs = current.get("result_refs")
    if source_refs is not None and not isinstance(source_refs, list):
        raise V13ConversionProblem(
            "todo_v3_result_refs_invalid",
            "result_refs 必须是引用清单（JSON 行字符串数组）；形如列表的字符串请先规范成真列表。",
            {"home": str(home_path), "actual_type": type(source_refs).__name__},
        )
    candidate_text = render_todo_v3(
        home_kind=str(source.get("home_kind") or home_kind),
        home_id=str(source.get("home_id") or home_id),
        project_id=str(source.get("project_id") or project_id),
        objective=str(current.get("objective") or ""),
        approved_scope=str(current.get("approved_scope") or ""),
        stage=str(current.get("stage") or ""),
        next_action=str(current.get("next_action") or ""),
        waiting=str(current.get("waiting") or ""),
        results=str(current.get("results") or ""),
        result_refs=list(current.get("result_refs") or []),
        context_refs=list(current.get("context_refs") or []),
        legacy_source_ref=str(current.get("legacy_source_ref") or ""),
        inflight=str(current.get("inflight") or ""),
        alignment_ref=str(current.get("alignment_ref") or ""),
        input_version=str(current.get("input_version") or ""),
        delivery=str(current.get("delivery") or ""),
        dependencies=str(current.get("dependencies") or ""),
        continuation_to=str(current.get("continuation_to") or ""),
        boundaries=str(current.get("boundaries") or ""),
        history_ref=str(current.get("history_ref") or ""),
        latest_readback=str(current.get("latest_readback") or ""),
        tasks=list(source.get("tasks") or []),
    )
    removed_fields = sorted(
        key
        for key in set(current.keys()) | {"current_work"}
        if key == "current_work" and "current_work" in current
    )
    return {
        "home_path": str(todo_path),
        "source_todo_sha256": _sha256_bytes(todo_path.read_bytes()),
        "candidate_todo_text": candidate_text,
        "candidate_todo_sha256": _sha256_bytes(candidate_text.encode("utf-8")),
        "fields_removed": removed_fields,
        "tasks_count_before": len(list(source.get("tasks") or [])),
        "identity": expected_identity,
    }


def apply_v3_home_convergence(
    *,
    project_root: Path,
    home_path: Path,
    home_kind: str,
    home_id: str,
    project_id: str = "",
    manifest_id: str,
) -> dict[str, Any]:
    """Apply one Workless v3-Home convergence with byte rollback-on-error.

    Idempotent: if the manifest's after-sha equals current TODO bytes the call
    replays (no write). The pre-convergence TODO bytes are preserved as the
    recovery point; Notices and Mail are never touched. Repeatable after post-
    adoption progress: a changed TODO simply converges again from fresh bytes.
    """
    todo_path = Path(posix_windows_drive_locator(str(home_path))).expanduser() / "TODO.md"
    if not todo_path.is_file():
        raise V13ConversionProblem(
            "v3_convergence_todo_missing",
            "目标 Home 没有 TODO.md；无法做 v3 收敛。",
            {"path": str(todo_path)},
        )
    manifest_id = _clean_manifest_id(manifest_id)
    plan = plan_v3_home_convergence(
        home_path=todo_path.parent,
        home_kind=home_kind,
        home_id=home_id,
        project_id=project_id,
    )
    manifest_dir = (
        Path(posix_windows_drive_locator(str(project_root))).expanduser()
        / ".paos" / "v13-migration" / manifest_id / "v3-converge"
        / home_id
    )
    manifest_path = manifest_dir / "manifest.json"

    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise V13ConversionProblem(
                "v3_convergence_manifest_invalid",
                f"v3 收敛 manifest 无法读取：{manifest_path}",
                {"path": str(manifest_path)},
            ) from exc
        if not isinstance(manifest, dict) or manifest.get("schema") != "paos-v3-home-converge-manifest/v1":
            raise V13ConversionProblem(
                "v3_convergence_manifest_invalid",
                "v3 收敛 manifest schema 无效。",
                {"path": str(manifest_path)},
            )
        current_sha = _sha256_bytes(todo_path.read_bytes())
        if current_sha == str(manifest.get("after_todo_sha256") or ""):
            return {
                **manifest,
                "replayed": True,
                "converged": True,
                "no_write": True,
                "current_todo_sha256": current_sha,
            }
    todo_replaced = False
    backup = manifest_dir / "TODO-before.md"
    try:
        if todo_path.read_bytes() != plan["candidate_todo_text"].encode("utf-8"):
            manifest_dir.mkdir(parents=True, exist_ok=False)
            shutil.copy2(todo_path, backup)
            write_todo_v3(todo_path, plan["candidate_todo_text"])
            todo_replaced = True
            manifest = {
                "schema": "paos-v3-home-converge-manifest/v1",
                **{
                    key: value
                    for key, value in plan.items()
                    if key not in {"candidate_todo_text"}
                },
                "replayed": False,
                "converged": True,
                "todo_backup_path": str(backup),
                "after_todo_sha256": plan["candidate_todo_sha256"],
                "notices_touched": 0,
                "mail_touched": 0,
                "convergence_target": "paos-todo/v3 workless contract (no current_work field)",
            }
            _atomic_write(
                manifest_path,
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            )
        else:
            manifest = {
                **{
                    key: value
                    for key, value in plan.items()
                    if key not in {"candidate_todo_text"}
                },
                "replayed": True,
                "converged": True,
                "no_write": True,
                "after_todo_sha256": plan["candidate_todo_sha256"],
                "_manifest_path_unwritten": str(manifest_path),
            }
        return manifest
    except Exception:
        if todo_replaced and backup.is_file():
            shutil.copy2(backup, todo_path)
        if todo_replaced:
            shutil.rmtree(manifest_dir, ignore_errors=True)
        raise


def plan_rooter_home_conversion(
    *,
    home_path: Path,
    home_id: str,
    manifest_id: str,
    current: dict[str, Any],
    tasks: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    manifest_id = _clean_manifest_id(manifest_id)
    try:
        home = rooter_home(home_path=home_path, home_id=home_id)
    except Exception as problem:
        raise V13ConversionProblem(
            getattr(problem, "code", "v13_home_invalid"),
            str(problem),
            getattr(problem, "details", {}),
        ) from problem
    path = Path(home["home_path"])
    todo_path = path / "TODO.md"
    if not todo_path.is_file():
        raise V13ConversionProblem(
            "v13_todo_missing",
            f"Rooter TODO 不存在：{todo_path}",
            {"path": str(todo_path)},
        )
    todo_bytes = todo_path.read_bytes()
    source_text = todo_bytes.decode("utf-8")
    legacy_ref = f"migration:{manifest_id}/{home_id}/TODO.plain.md"
    candidate, todo_evidence = rooter_plain_todo_to_v3_text(
        source_text=source_text,
        home_id=home_id,
        legacy_source_ref=legacy_ref,
        objective=str(current.get("objective") or ""),
        next_action=str(current.get("next_action") or ""),
        approved_scope=str(current.get("approved_scope") or ""),
        stage=str(current.get("stage") or ""),
        waiting=str(current.get("waiting") or ""),
        results=str(current.get("results") or ""),
        inflight=str(current.get("inflight") or ""),
        alignment_ref=str(current.get("alignment_ref") or ""),
        input_version=str(current.get("input_version") or ""),
        delivery=str(current.get("delivery") or ""),
        dependencies=str(current.get("dependencies") or ""),
        continuation_to=str(current.get("continuation_to") or ""),
        tasks=tasks,
    )
    mail_scan = _scan_rooter_mailbox(path)
    notices = list(mail_scan["notices"])
    return {
        "schema": MIGRATION_SCHEMA,
        "manifest_id": manifest_id,
        "home": home,
        "source_todo_path": str(todo_path),
        "source_todo_sha256": _sha256_bytes(todo_bytes),
        "candidate_todo_text": candidate,
        "candidate_todo_sha256": _sha256_bytes(candidate.encode("utf-8")),
        "todo_evidence": todo_evidence,
        "mail_count": int(mail_scan["mail_count"]),
        "mapped_count": int(mail_scan["mapped_count"]),
        "unmapped_count": int(mail_scan["unmapped_count"]),
        "handled_count": 0,
        "pending_count": len(notices),
        "notices": notices,
        "mail_mappings": [
            {
                "source_ref": item["source_ref"],
                "source_path": item["source_path"],
                "source_filename": item["source_filename"],
                "identity_mode": item["identity_mode"],
                "declared_message_id": item.get("declared_message_id", ""),
                "mapping_note": item.get("mapping_note", ""),
                "state": item["state"],
            }
            for item in notices
        ],
        "unmapped_inputs": list(mail_scan["unmapped_inputs"]),
        "excluded_files": list(mail_scan["excluded_files"]),
        "activation_intents_created": 0,
    }


def apply_rooter_home_conversion(
    *,
    home_path: Path,
    home_id: str,
    manifest_id: str,
    current: dict[str, Any],
    tasks: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Apply Rooter plain-Markdown conversion without inventing Project identity."""
    manifest_id = _clean_manifest_id(manifest_id)
    try:
        resolved_home = rooter_home(home_path=home_path, home_id=home_id)
    except Exception as problem:
        raise V13ConversionProblem(
            getattr(problem, "code", "v13_home_invalid"),
            str(problem),
            getattr(problem, "details", {}),
        ) from problem
    path = Path(resolved_home["home_path"])
    migration_dir = path / ".paos" / "v13-migration" / manifest_id
    manifest_path = migration_dir / "manifest.json"
    replayed = _replay_existing_conversion(
        manifest_path=manifest_path,
        expected_home_kind="rooter",
        expected_home_id=home_id,
        expected_project_id="",
        expected_home_path=path,
    )
    if replayed is not None:
        return replayed
    if migration_dir.exists():
        raise V13ConversionProblem(
            "v13_incomplete_migration_dir",
            "发现没有 manifest 的既有 Rooter 迁移目录；拒绝覆盖可能的中断证据。",
            {
                "path": str(migration_dir),
                "recovery": "由 Rooter/Reviewer 检查该目录后显式恢复或移出，再重跑同一转换。",
            },
        )

    plan = plan_rooter_home_conversion(
        home_path=home_path,
        home_id=home_id,
        manifest_id=manifest_id,
        current=current,
        tasks=tasks,
    )
    migration_dir.mkdir(parents=True, exist_ok=False)
    todo_path = path / "TODO.md"
    todo_backup = migration_dir / "TODO.plain.md"
    created_notice_paths: list[Path] = []
    imported_notice_ids: list[str] = []
    todo_replaced = False
    try:
        shutil.copy2(todo_path, todo_backup)
        for item in plan["notices"]:
            identity = input_identity(
                home_kind="rooter",
                home_id=home_id,
                project_id="",
                source_kind="mail",
                source_ref=item["source_ref"],
            )
            target = notice_path(path, notice_id_for(identity))
            existed = target.exists()
            imported = import_notice(
                home_path=path,
                home_kind="rooter",
                home_id=home_id,
                project_id="",
                source_kind="mail",
                source_ref=item["source_ref"],
                summary=item["summary"],
                state="pending",
                created_at=item.get("created_at", ""),
            )
            imported_notice_ids.append(str(imported.get("notice_id") or ""))
            if imported.get("created") and not existed:
                created_notice_paths.append(Path(imported["path"]))

        current_sha = _sha256_bytes(todo_path.read_bytes())
        if current_sha != plan["source_todo_sha256"]:
            raise V13ConversionProblem(
                "v13_todo_changed_during_conversion",
                "Rooter TODO 在转换准备后发生变化；拒绝覆盖。",
                {
                    "path": str(todo_path),
                    "planned_sha256": plan["source_todo_sha256"],
                    "current_sha256": current_sha,
                },
            )
        write_todo_v3(todo_path, plan["candidate_todo_text"])
        todo_replaced = True
        manifest = {
            key: value
            for key, value in plan.items()
            if key not in {"candidate_todo_text", "notices"}
        }
        manifest.update(
            {
                "replayed": False,
                "todo_backup_path": str(todo_backup),
                "legacy_handling_backup_path": "",
                "legacy_handling_archived_path": "",
                "notice_ids": [value for value in imported_notice_ids if value],
                "activation_intents_created": 0,
            }
        )
        parse_todo_v3(todo_path.read_text(encoding="utf-8"))
        _atomic_write(
            manifest_path,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        return manifest
    except Exception:
        if todo_replaced and todo_backup.is_file():
            shutil.copy2(todo_backup, todo_path)
        for target in created_notice_paths:
            target.unlink(missing_ok=True)
        shutil.rmtree(migration_dir, ignore_errors=True)
        raise


def rollback_home_conversion(
    manifest_path: Path,
) -> dict[str, Any]:
    """Restore the pre-V1.3 file contract while preserving post-cutover facts.

    Current V1.3 TODO/Notice files are copied into rollback evidence before the
    old TODO/handling paths are restored. Runtime attempt files are never
    replayed or rewritten here.
    """
    manifest_path = Path(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise V13ConversionProblem(
            "v13_manifest_invalid",
            f"manifest 无法读取：{manifest_path}",
            {"path": str(manifest_path)},
        ) from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != MIGRATION_SCHEMA:
        raise V13ConversionProblem(
            "v13_manifest_invalid",
            "manifest schema 无效。",
            {"path": str(manifest_path)},
        )
    home = manifest.get("home") if isinstance(manifest.get("home"), dict) else {}
    home_path = Path(str(home.get("home_path") or ""))
    if not home_path.is_dir():
        raise V13ConversionProblem(
            "v13_rollback_home_missing",
            f"Home 不存在：{home_path}",
            {"home_path": str(home_path)},
        )
    todo_backup = Path(str(manifest.get("todo_backup_path") or ""))
    if not todo_backup.is_file():
        raise V13ConversionProblem(
            "v13_rollback_backup_missing",
            "原 TODO backup 不存在。",
            {"todo_backup_path": str(todo_backup)},
        )

    rollback_dir = manifest_path.parent / "rollback-current"
    if rollback_dir.exists():
        raise V13ConversionProblem(
            "v13_rollback_already_prepared",
            "rollback-current 已存在；拒绝覆盖先前回退证据。",
            {"path": str(rollback_dir)},
        )
    rollback_dir.mkdir(parents=True)
    current_todo = home_path / "TODO.md"
    if current_todo.is_file():
        shutil.copy2(current_todo, rollback_dir / "TODO.v3.md")
    notices = home_path / "notices"
    if notices.is_dir():
        shutil.copytree(notices, rollback_dir / "notices")

    shutil.copy2(todo_backup, current_todo)

    archived = str(manifest.get("legacy_handling_archived_path") or "")
    legacy_handling = home_path / "mailbox" / ".handled"
    if archived:
        archived_path = Path(archived)
        if legacy_handling.exists():
            raise V13ConversionProblem(
                "v13_rollback_handling_conflict",
                "legacy .handled 已存在；拒绝覆盖。",
                {"path": str(legacy_handling)},
            )
        if archived_path.is_dir():
            os.rename(archived_path, legacy_handling)

    notice_archive = ""
    if notices.is_dir():
        notice_archive_path = (
            home_path
            / f"notices.v13-rollback-{manifest.get('manifest_id')}"
        )
        if notice_archive_path.exists():
            raise V13ConversionProblem(
                "v13_rollback_notice_conflict",
                "Notice rollback archive 已存在。",
                {"path": str(notice_archive_path)},
            )
        os.rename(notices, notice_archive_path)
        notice_archive = str(notice_archive_path)

    rollback = {
        "schema": "paos-v13-home-rollback/v1",
        "manifest_id": manifest.get("manifest_id"),
        "home": home,
        "restored_todo_path": str(current_todo),
        "restored_legacy_handling_path": (
            str(legacy_handling) if legacy_handling.exists() else ""
        ),
        "v13_recovery_dir": str(rollback_dir),
        "v13_notice_archive": notice_archive,
        "runtime_attempts_replayed": False,
        "business_artifacts_deleted": False,
    }
    _atomic_write(
        manifest_path.parent / "rollback.json",
        json.dumps(rollback, ensure_ascii=False, indent=2) + "\n",
    )
    return rollback


def _load_json_file(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise V13ConversionProblem(
            "v13_input_json_invalid",
            f"JSON 输入无法读取：{target}",
            {"path": str(target)},
        ) from exc
    if not isinstance(value, dict):
        raise V13ConversionProblem(
            "v13_input_json_invalid",
            f"JSON 输入必须是 object：{target}",
            {"path": str(target)},
        )
    return value


def _project_from_export(value: dict[str, Any]) -> dict[str, Any]:
    project = value.get("project") if isinstance(value.get("project"), dict) else value
    if not isinstance(project, dict) or not str(project.get("id") or "").strip():
        raise V13ConversionProblem(
            "v13_project_export_invalid",
            "project JSON 缺少有效 project.id。",
        )
    return project


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": plan.get("schema"),
        "manifest_id": plan.get("manifest_id"),
        "home": plan.get("home"),
        "source_todo_path": plan.get("source_todo_path"),
        "source_todo_sha256": plan.get("source_todo_sha256"),
        "candidate_todo_sha256": plan.get("candidate_todo_sha256"),
        "mail_count": plan.get("mail_count"),
        "mapped_count": plan.get("mapped_count"),
        "unmapped_count": plan.get("unmapped_count"),
        "handled_count": plan.get("handled_count"),
        "pending_count": plan.get("pending_count"),
        "mail_mappings": plan.get("mail_mappings") or [],
        "unmapped_inputs": plan.get("unmapped_inputs") or [],
        "excluded_files": plan.get("excluded_files") or [],
        "todo_evidence": plan.get("todo_evidence"),
        "activation_intents_created": plan.get("activation_intents_created", 0),
    }


def build_converter_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paos_v13_convert",
        description=(
            "One-time V1.3 Home converter. It never creates Runtime activation "
            "intent for imported historical inputs."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    project_cmd = sub.add_parser("project-home")
    project_cmd.add_argument("--project-json", required=True)
    project_cmd.add_argument("--root", required=True)
    project_cmd.add_argument("--agent-id", required=True)
    project_cmd.add_argument("--manifest-id", required=True)
    project_cmd.add_argument("--apply", action="store_true")

    rooter_cmd = sub.add_parser("rooter-home")
    rooter_cmd.add_argument("--home-path", required=True)
    rooter_cmd.add_argument("--home-id", default="rooter-001")
    rooter_cmd.add_argument("--manifest-id", required=True)
    rooter_cmd.add_argument("--current-json", required=True)
    rooter_cmd.add_argument("--tasks-json")
    rooter_cmd.add_argument("--apply", action="store_true")

    rollback_cmd = sub.add_parser("rollback")
    rollback_cmd.add_argument("--manifest", required=True)
    return parser


def converter_main(argv: list[str] | None = None) -> int:
    args = build_converter_parser().parse_args(argv)
    try:
        if args.command == "project-home":
            project = _project_from_export(_load_json_file(args.project_json))
            if args.apply:
                result = apply_project_home_conversion(
                    root=Path(args.root),
                    project=project,
                    agent_id=args.agent_id,
                    manifest_id=args.manifest_id,
                )
            else:
                result = _plan_summary(
                    plan_project_home_conversion(
                        root=Path(args.root),
                        project=project,
                        agent_id=args.agent_id,
                        manifest_id=args.manifest_id,
                    )
                )
        elif args.command == "rooter-home":
            current = _load_json_file(args.current_json)
            tasks: list[dict[str, Any]] = []
            if args.tasks_json:
                try:
                    raw_tasks = json.loads(
                        Path(args.tasks_json).read_text(encoding="utf-8")
                    )
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise V13ConversionProblem(
                        "v13_tasks_json_invalid",
                        "tasks JSON 无法读取。",
                        {"path": args.tasks_json},
                    ) from exc
                if not isinstance(raw_tasks, list) or not all(
                    isinstance(item, dict) for item in raw_tasks
                ):
                    raise V13ConversionProblem(
                        "v13_tasks_json_invalid",
                        "tasks JSON 必须是 object 数组。",
                        {"path": args.tasks_json},
                    )
                tasks = raw_tasks
            if args.apply:
                result = apply_rooter_home_conversion(
                    home_path=Path(args.home_path),
                    home_id=args.home_id,
                    manifest_id=args.manifest_id,
                    current=current,
                    tasks=tasks,
                )
            else:
                result = _plan_summary(
                    plan_rooter_home_conversion(
                        home_path=Path(args.home_path),
                        home_id=args.home_id,
                        manifest_id=args.manifest_id,
                        current=current,
                        tasks=tasks,
                    )
                )
        else:
            result = rollback_home_conversion(Path(args.manifest))
    except (
        V13ConversionProblem,
        NoticeProblem,
        TodoV3Problem,
        WorkstationProblem,
        MailProblem,
    ) as problem:
        payload = {
            "ok": False,
            "error": str(problem),
            "error_code": getattr(problem, "code", "v13_conversion_error"),
            "details": getattr(problem, "details", {}),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(converter_main())
