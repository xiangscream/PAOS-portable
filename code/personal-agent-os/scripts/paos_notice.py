"""Production Notice registry and handling state.

This filesystem-backed module is part of the current v3 Home/CLI path. It keeps:

- one durable input identity per target Home;
- one pending/handled Notice fact per input;
- an explicit activation request marker that migration does not create;
- Mail dispatch -> Notice projection without copying Mail body;
- per-item atomic writes, so callers never rewrite a monolithic NOTICE file.

Read the merged Notice state through the official attention read surface
(`paos attention show`, `attention rooter-show`, and `read_home_state`) rather
than treating a Markdown registration file as current handling state. Writes
stay behind the existing Notice service/CLI. Runtime attempts remain owned by
the Wake layer; this module does not schedule, retry, wake, ACK CAT, mutate
Work/Request state, or infer completion.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


NOTICE_SCHEMA = "paos-notice/v1"
NOTICE_LIST_SCHEMA = "paos-notice-list/v1"
NOTICE_READ_SCHEMA = "paos-notice-read/v1"
NOTICE_STATES = {"pending", "handled"}
HOME_KINDS = {"project_agent", "rooter"}


class NoticeProblem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _utc_now_iso_precise() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _single_line(value: Any, *, label: str, max_chars: int = 500) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > max_chars:
        raise NoticeProblem(
            "notice_field_too_long",
            f"{label} 超过 {max_chars} 字符限制。",
            {"label": label, "max_chars": max_chars},
        )
    return text


def _required_single_line(
    value: Any,
    *,
    label: str,
    max_chars: int = 500,
) -> str:
    text = _single_line(value, label=label, max_chars=max_chars)
    if not text:
        raise NoticeProblem(
            "notice_field_missing",
            f"{label} 不能为空。",
            {"label": label},
        )
    return text


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def input_identity(
    *,
    home_kind: str,
    home_id: str,
    project_id: str = "",
    source_kind: str,
    source_ref: str,
) -> dict[str, str]:
    home_kind = _required_single_line(home_kind, label="home_kind", max_chars=40)
    if home_kind not in HOME_KINDS:
        raise NoticeProblem(
            "notice_home_kind_invalid",
            f"home_kind 必须是 {sorted(HOME_KINDS)} 之一。",
            {"home_kind": home_kind},
        )
    home_id = _required_single_line(home_id, label="home_id", max_chars=160)
    project_id = _single_line(project_id, label="project_id", max_chars=160)
    if home_kind == "project_agent" and not project_id:
        raise NoticeProblem(
            "notice_project_id_missing",
            "project_agent Notice 必须带 project_id。",
            {"home_id": home_id},
        )
    source_kind = _required_single_line(
        source_kind,
        label="source_kind",
        max_chars=40,
    )
    source_ref = _required_single_line(
        source_ref,
        label="source_ref",
        max_chars=1000,
    )
    return {
        "home_kind": home_kind,
        "home_id": home_id,
        "project_id": project_id,
        "source_kind": source_kind,
        "source_ref": source_ref,
    }


def notice_id_for(identity: dict[str, str]) -> str:
    digest = _sha256_text(_canonical_json(identity))
    return f"notice-{digest[:24]}"


def notice_dir(home_path: Path) -> Path:
    return Path(home_path) / "notices"


def notice_path(home_path: Path, notice_id: str) -> Path:
    notice_id = _required_single_line(
        notice_id,
        label="notice_id",
        max_chars=80,
    )
    if not notice_id.startswith("notice-"):
        raise NoticeProblem(
            "notice_id_invalid",
            "notice_id 格式无效。",
            {"notice_id": notice_id},
        )
    return notice_dir(home_path) / f"{notice_id}.md"


def _handled_record_path(home_path: Path, notice_id: str) -> Path:
    return notice_dir(home_path) / ".handled" / f"{notice_id}.json"


def _read_record_path(home_path: Path, notice_id: str) -> Path:
    # Reuse notice_path validation so a read sidecar stays inside the Notice namespace.
    canonical_id = notice_path(home_path, notice_id).stem
    return notice_dir(home_path) / ".read" / f"{canonical_id}.json"


def _activation_request_dir(home_path: Path, notice_id: str) -> Path:
    return notice_dir(home_path) / ".activation" / notice_id


def _organization_update_dir(home_path: Path, notice_id: str) -> Path:
    return notice_dir(home_path) / ".organization" / notice_id


def _organization_update_path(
    home_path: Path,
    notice_id: str,
    operation_id: str,
) -> Path:
    return (
        _organization_update_dir(home_path, notice_id)
        / f"{_sha256_text(operation_id)[:32]}.json"
    )


def _read_organization_updates(
    home_path: Path,
    notice_id: str,
) -> list[dict[str, Any]]:
    directory = _organization_update_dir(home_path, notice_id)
    if not directory.is_dir():
        return []
    updates: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        record = _read_json_record(
            path,
            code="notice_organization_update_invalid",
        )
        if (
            record.get("schema") != "paos-notice-organization/v1"
            or record.get("notice_id") != notice_id
            or not str(record.get("operation_id") or "").strip()
            or not isinstance(record.get("changes"), dict)
        ):
            raise NoticeProblem(
                "notice_organization_update_invalid",
                "Notice organization sidecar 内容无效。",
                {"path": str(path), "notice_id": notice_id},
            )
        updates.append(record)
    updates.sort(
        key=lambda item: (
            str(item.get("recorded_at") or ""),
            str(item.get("operation_id") or ""),
        )
    )
    return updates


def _activation_request_path(
    home_path: Path,
    notice_id: str,
    request_id: str,
) -> Path:
    request_id = _required_single_line(
        request_id,
        label="activation_request_id",
        max_chars=160,
    )
    return _activation_request_dir(home_path, notice_id) / f"{request_id}.json"


def _read_json_record(path: Path, *, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NoticeProblem(
            code,
            f"Notice sidecar 无法读取：{path}",
            {"path": str(path), "cause": str(exc)},
        ) from exc
    if not isinstance(value, dict):
        raise NoticeProblem(
            code,
            f"Notice sidecar 内容无效：{path}",
            {"path": str(path)},
        )
    return value


def _read_handled_record(
    home_path: Path,
    notice_id: str,
) -> dict[str, Any] | None:
    path = _handled_record_path(home_path, notice_id)
    if not path.is_file():
        return None
    record = _read_json_record(path, code="notice_handled_record_invalid")
    if (
        record.get("schema") != "paos-notice-handled/v1"
        or record.get("notice_id") != notice_id
    ):
        raise NoticeProblem(
            "notice_handled_record_invalid",
            f"Notice handled sidecar schema/identity 无效：{path}",
            {"path": str(path), "notice_id": notice_id},
        )
    return record


def _read_notice_read_record(
    home_path: Path,
    notice_id: str,
) -> dict[str, Any] | None:
    path = _read_record_path(home_path, notice_id)
    if not path.is_file():
        return None
    record = _read_json_record(path, code="notice_read_record_invalid")
    if (
        record.get("schema") != NOTICE_READ_SCHEMA
        or record.get("notice_id") != notice_id
    ):
        raise NoticeProblem(
            "notice_read_record_invalid",
            f"Notice read sidecar schema/identity 无效：{path}",
            {"path": str(path), "notice_id": notice_id},
        )
    reader_kind = str(record.get("reader_home_kind") or "").strip()
    reader_id = str(record.get("reader_home_id") or "").strip()
    reader_project = str(record.get("reader_project_id") or "").strip()
    read_at = str(record.get("read_at") or "").strip()
    if reader_kind not in {"project_agent", "rooter"} or not reader_id or not read_at:
        raise NoticeProblem(
            "notice_read_record_invalid",
            f"Notice read sidecar identity/timestamp 无效：{path}",
            {"path": str(path), "notice_id": notice_id},
        )
    if reader_kind == "project_agent" and not reader_project:
        raise NoticeProblem(
            "notice_read_record_invalid",
            f"project_agent read sidecar 缺少 reader_project_id：{path}",
            {"path": str(path), "notice_id": notice_id},
        )
    if reader_kind == "rooter" and reader_project:
        raise NoticeProblem(
            "notice_read_record_invalid",
            f"rooter read sidecar 不得带 reader_project_id：{path}",
            {"path": str(path), "notice_id": notice_id},
        )
    return {
        **record,
        "reader_home_kind": reader_kind,
        "reader_home_id": reader_id,
        "reader_project_id": reader_project,
        "read_at": read_at,
        "path": str(path),
    }


def _read_activation_requests(
    home_path: Path,
    notice_id: str,
) -> list[dict[str, Any]]:
    directory = _activation_request_dir(home_path, notice_id)
    if not directory.is_dir():
        return []
    result: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        record = _read_json_record(
            path,
            code="notice_activation_request_invalid",
        )
        if (
            record.get("schema") != "paos-notice-activation-request/v1"
            or record.get("notice_id") != notice_id
            or record.get("activation_request_id") != path.stem
        ):
            raise NoticeProblem(
                "notice_activation_request_invalid",
                f"Notice activation sidecar schema/identity 无效：{path}",
                {"path": str(path), "notice_id": notice_id},
            )
        result.append(record)
    result.sort(
        key=lambda item: (
            str(item.get("requested_at") or ""),
            str(item.get("activation_request_id") or ""),
        )
    )
    return result

def _atomic_create(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        staged.write_text(text, encoding="utf-8", newline="\n")
        try:
            os.link(staged, path)
            return True
        except FileExistsError:
            return False
        except OSError:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            try:
                fd = os.open(path, flags)
            except FileExistsError:
                return False
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
            except Exception:
                path.unlink(missing_ok=True)
                raise
            return True
    except OSError as exc:
        raise NoticeProblem(
            "notice_write_failed",
            f"无法创建 Notice：{path}",
            {"path": str(path), "os_error": str(exc)},
        ) from exc
    finally:
        staged.unlink(missing_ok=True)


def _atomic_replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        staged.write_text(text, encoding="utf-8", newline="\n")
        os.replace(staged, path)
    except OSError as exc:
        staged.unlink(missing_ok=True)
        raise NoticeProblem(
            "notice_write_failed",
            f"无法更新 Notice：{path}",
            {"path": str(path), "os_error": str(exc)},
        ) from exc


def _frontmatter_line(key: str, value: Any) -> str:
    return f"{key}: {json.dumps(value, ensure_ascii=False)}"


def _render_notice(record: dict[str, Any]) -> str:
    summary = str(record.get("summary") or "")
    meta_order = (
        "schema",
        "notice_id",
        "home_kind",
        "home_id",
        "project_id",
        "source_kind",
        "source_ref",
        "state",
        "created_at",
        "handled_at",
        "resolution",
        "action_ref",
        "activation_request_id",
        "activation_requested_at",
        "summary_sha256",
    )
    lines = ["---"]
    lines.extend(_frontmatter_line(key, record.get(key, "")) for key in meta_order)
    lines += [
        "---",
        "",
        f"# {summary}",
        "",
        "详情正文保留在 source_ref 指向的原来源；本 Notice 只保存 attention 事实。",
        "",
    ]
    return "\n".join(lines)


def _parse_notice_text(text: str, *, path: Path) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise NoticeProblem(
            "notice_invalid",
            f"Notice 缺少 front matter：{path}",
            {"path": str(path)},
        )
    meta: dict[str, Any] = {}
    closed = False
    for raw in lines[1:]:
        if raw.strip() == "---":
            closed = True
            break
        key, sep, value = raw.partition(":")
        if not sep:
            continue
        key = key.strip()
        if key in meta:
            raise NoticeProblem(
                "notice_invalid",
                f"Notice front matter 重复字段：{key}",
                {"path": str(path), "key": key},
            )
        try:
            meta[key] = json.loads(value.strip())
        except json.JSONDecodeError as exc:
            raise NoticeProblem(
                "notice_invalid",
                f"Notice front matter 无法解析：{key}",
                {"path": str(path), "key": key},
            ) from exc
    if not closed:
        raise NoticeProblem(
            "notice_invalid",
            f"Notice front matter 未闭合：{path}",
            {"path": str(path)},
        )
    if meta.get("schema") != NOTICE_SCHEMA:
        raise NoticeProblem(
            "notice_invalid",
            f"Notice schema 无效：{path}",
            {"path": str(path), "schema": meta.get("schema")},
        )
    if meta.get("state") not in NOTICE_STATES:
        raise NoticeProblem(
            "notice_invalid",
            f"Notice state 无效：{path}",
            {"path": str(path), "state": meta.get("state")},
        )
    identity = input_identity(
        home_kind=str(meta.get("home_kind") or ""),
        home_id=str(meta.get("home_id") or ""),
        project_id=str(meta.get("project_id") or ""),
        source_kind=str(meta.get("source_kind") or ""),
        source_ref=str(meta.get("source_ref") or ""),
    )
    expected_id = notice_id_for(identity)
    if meta.get("notice_id") != expected_id or path.stem != expected_id:
        raise NoticeProblem(
            "notice_identity_mismatch",
            "Notice 文件名或 notice_id 与 source identity 不一致。",
            {
                "path": str(path),
                "expected_notice_id": expected_id,
                "actual_notice_id": meta.get("notice_id"),
            },
        )
    summary = ""
    for index, raw in enumerate(lines):
        if raw.strip() == "---" and index > 0:
            body = lines[index + 1 :]
            for candidate in body:
                candidate = candidate.strip()
                if candidate.startswith("# "):
                    summary = candidate[2:].strip()
                    break
            break
    if _sha256_text(summary) != str(meta.get("summary_sha256") or ""):
        raise NoticeProblem(
            "notice_summary_mismatch",
            "Notice 摘要与已记录 hash 不一致。",
            {"path": str(path)},
        )
    return {**meta, "summary": summary, "path": str(path)}


def read_notice(home_path: Path, notice_id: str) -> dict[str, Any]:
    """Read immutable Notice identity plus independent atomic sidecars."""
    home_path = Path(home_path)
    path = notice_path(home_path, notice_id)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise NoticeProblem(
            "notice_missing",
            f"Notice 不存在：{path}",
            {"path": str(path), "notice_id": notice_id},
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise NoticeProblem(
            "notice_unreadable",
            f"Notice 无法读取：{path}",
            {"path": str(path), "notice_id": notice_id},
        ) from exc

    base = _parse_notice_text(text, path=path)
    handled = _read_handled_record(home_path, notice_id)
    read_record = _read_notice_read_record(home_path, notice_id)
    requests = _read_activation_requests(home_path, notice_id)
    updates = _read_organization_updates(home_path, notice_id)
    return _project_notice(base, handled, read_record, requests, updates)


def _project_notice(
    base: dict[str, Any],
    handled: dict[str, Any] | None,
    read_record: dict[str, Any] | None,
    requests: list[dict[str, Any]],
    updates: list[dict[str, Any]],
) -> dict[str, Any]:
    projected = dict(base)
    if read_record is not None:
        projected.update(
            {
                "read": True,
                "read_at": str(read_record.get("read_at") or ""),
                "read_by_home_kind": str(
                    read_record.get("reader_home_kind") or ""
                ),
                "read_by_home_id": str(read_record.get("reader_home_id") or ""),
                "read_by_project_id": str(
                    read_record.get("reader_project_id") or ""
                ),
            }
        )
    else:
        projected.update(
            {
                "read": False,
                "read_at": "",
                "read_by_home_kind": "",
                "read_by_home_id": "",
                "read_by_project_id": "",
            }
        )
    if handled is not None:
        projected.update(
            {
                "state": "handled",
                "handled_at": str(handled.get("handled_at") or ""),
                "resolution": str(handled.get("resolution") or ""),
                "action_ref": str(handled.get("action_ref") or ""),
            }
        )
    elif str(projected.get("state") or "pending") != "handled":
        projected.update({"state": "pending", "handled_at": "", "resolution": "", "action_ref": ""})

    if requests:
        latest = requests[-1]
        projected["activation_request_id"] = str(latest.get("activation_request_id") or "")
        projected["activation_requested_at"] = str(latest.get("requested_at") or "")
    else:
        projected["activation_request_id"] = str(base.get("activation_request_id") or "")
        projected["activation_requested_at"] = str(base.get("activation_requested_at") or "")
    projected["activation_requests"] = requests

    projected["source_summary"] = str(projected.get("summary") or "")
    projected["sort_order"] = None
    projected["archived"] = False
    for update in updates:
        changes = update.get("changes") or {}
        if "summary" in changes:
            projected["summary"] = str(changes.get("summary") or "")
        if "sort_order" in changes:
            projected["sort_order"] = changes.get("sort_order")
        if "archived" in changes:
            projected["archived"] = bool(changes.get("archived"))
    projected["organization_updates"] = updates
    projected["organization_updated_at"] = (
        str(updates[-1].get("recorded_at") or "") if updates else ""
    )
    return projected

def create_notice(
    *,
    home_path: Path,
    home_kind: str,
    home_id: str,
    project_id: str = "",
    source_kind: str,
    source_ref: str,
    summary: str,
    activation_request_id: str = "",
    created_at: str = "",
    preserve_empty_created_at: bool = False,
) -> dict[str, Any]:
    """Create immutable input identity, then optional activation intent."""
    home_path = Path(home_path)
    if not home_path.is_dir():
        raise NoticeProblem(
            "notice_home_missing",
            f"Home 不存在：{home_path}",
            {"home_path": str(home_path), "home_id": home_id},
        )
    identity = input_identity(
        home_kind=home_kind, home_id=home_id, project_id=project_id,
        source_kind=source_kind, source_ref=source_ref,
    )
    summary = _required_single_line(summary, label="summary", max_chars=500)
    request_id = _single_line(activation_request_id, label="activation_request_id", max_chars=160)
    notice_id = notice_id_for(identity)
    path = notice_path(home_path, notice_id)
    record = {
        "schema": NOTICE_SCHEMA, "notice_id": notice_id, **identity,
        "state": "pending",
        "created_at": (
            created_at
            if preserve_empty_created_at
            else (created_at or utc_now_iso())
        ),
        "handled_at": "", "resolution": "", "action_ref": "",
        "activation_request_id": "", "activation_requested_at": "",
        "summary_sha256": _sha256_text(summary), "summary": summary,
    }
    created = _atomic_create(path, _render_notice(record))
    if not created:
        existing = read_notice(home_path, notice_id)
        mismatches = {
            key: {"existing": existing.get(key), "requested": record.get(key)}
            for key in ("home_kind", "home_id", "project_id", "source_kind", "source_ref", "summary_sha256")
            if existing.get(key) != record.get(key)
        }
        if mismatches:
            raise NoticeProblem(
                "notice_source_conflict",
                "相同 source identity 已存在不同 Notice 内容。",
                {"notice_id": notice_id, "mismatches": mismatches},
            )
    if request_id:
        requested = request_notice_activation(
            home_path=home_path, notice_id=notice_id, activation_request_id=request_id
        )
        return {**requested, "created": created}
    return {**read_notice(home_path, notice_id), "created": created}

def import_notice(
    *,
    home_path: Path,
    home_kind: str,
    home_id: str,
    project_id: str = "",
    source_kind: str,
    source_ref: str,
    summary: str,
    state: str,
    created_at: str = "",
    handled_at: str = "",
    resolution: str = "",
    action_ref: str = "",
) -> dict[str, Any]:
    """Import pre-existing input without manufacturing activation intent."""
    state = _required_single_line(state, label="state", max_chars=40)
    if state not in NOTICE_STATES:
        raise NoticeProblem("notice_state_invalid", f"state 必须是 {sorted(NOTICE_STATES)} 之一。", {"state": state})
    base = create_notice(
        home_path=home_path, home_kind=home_kind, home_id=home_id, project_id=project_id,
        source_kind=source_kind, source_ref=source_ref, summary=summary,
        activation_request_id="",
        created_at=created_at,
        preserve_empty_created_at=True,
    )
    if str(base.get("activation_request_id") or "") or base.get("activation_requests"):
        raise NoticeProblem(
            "notice_import_conflict",
            "迁移目标已存在 activation intent，拒绝重新解释为历史导入。",
            {"notice_id": base.get("notice_id")},
        )
    if state == "handled":
        marker = _create_handled_record(
            home_path=Path(home_path),
            notice_id=str(base["notice_id"]),
            handled_at=_single_line(handled_at, label="handled_at", max_chars=80),
            resolution=_single_line(resolution, label="resolution", max_chars=500),
            action_ref=_single_line(action_ref, label="action_ref", max_chars=1000),
        )
        return {**read_notice(Path(home_path), str(base["notice_id"])),
                "created": bool(base.get("created")), "imported": True,
                "handling_created": bool(marker.get("created"))}
    current = read_notice(Path(home_path), str(base["notice_id"]))
    if current.get("state") == "handled":
        raise NoticeProblem(
            "notice_import_conflict",
            "迁移请求为 pending，但该 Notice 已有 handled 事实。",
            {"notice_id": base.get("notice_id")},
        )
    return {**current, "created": bool(base.get("created")), "imported": True}

def _create_handled_record(
    *, home_path: Path, notice_id: str, handled_at: str, resolution: str, action_ref: str,
) -> dict[str, Any]:
    path = _handled_record_path(home_path, notice_id)
    record = {
        "schema": "paos-notice-handled/v1", "notice_id": notice_id,
        "handled_at": handled_at,
        "resolution": resolution, "action_ref": action_ref,
    }
    encoded = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if _atomic_create(path, encoded):
        return {**record, "path": str(path), "created": True}
    existing = _read_handled_record(home_path, notice_id)
    assert existing is not None
    if any(str(existing.get(key) or "") != str(record.get(key) or "") for key in ("resolution", "action_ref")):
        raise NoticeProblem(
            "notice_handling_conflict",
            "Notice 已被另一个写者处理；拒绝覆盖不同处理结果。",
            {
                "notice_id": notice_id,
                "existing_resolution": existing.get("resolution"),
                "existing_action_ref": existing.get("action_ref"),
                "requested_resolution": resolution,
                "requested_action_ref": action_ref,
            },
        )
    return {**existing, "path": str(path), "created": False}


def request_notice_activation(
    *, home_path: Path, notice_id: str, activation_request_id: str,
) -> dict[str, Any]:
    """Append activation intent; never rewrite handling or source fields."""
    home_path = Path(home_path)
    request_id = _required_single_line(activation_request_id, label="activation_request_id", max_chars=160)
    current = read_notice(home_path, notice_id)
    if current.get("state") != "pending":
        raise NoticeProblem("notice_already_handled", "已 handled 的 Notice 不能重新请求 activation。", {"notice_id": notice_id})
    path = _activation_request_path(home_path, notice_id, request_id)
    record = {
        "schema": "paos-notice-activation-request/v1",
        "notice_id": notice_id,
        "activation_request_id": request_id,
        "requested_at": utc_now_iso(),
    }
    created = _atomic_create(path, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    if not created:
        existing = _read_json_record(path, code="notice_activation_request_invalid")
        if (existing.get("schema") != record["schema"]
            or existing.get("notice_id") != notice_id
            or existing.get("activation_request_id") != request_id):
            raise NoticeProblem(
                "notice_activation_request_conflict",
                "activation_request_id 已存在不同内容。",
                {"notice_id": notice_id, "activation_request_id": request_id},
            )
    updated = read_notice(home_path, notice_id)
    if updated.get("state") != "pending":
        raise NoticeProblem(
            "notice_handled_during_activation_request",
            "Notice 在 activation request 写入期间已 handled；请求证据保留但不得激活。",
            {"notice_id": notice_id, "activation_request_id": request_id},
        )
    return {**updated, "activation_request_created": created}

def mark_notice_read(
    *,
    home_path: Path,
    notice_id: str,
    reader_home_kind: str,
    reader_home_id: str,
    reader_project_id: str = "",
) -> dict[str, Any]:
    """Explicitly mark one Notice read, independently of handled state.

    The read receipt is a first-read fact for the exact Home that owns the
    Notice. Repeated calls are idempotent and retain the first read timestamp.
    This is an explicit mutation; ordinary Notice reads/lists never create it.
    """
    home_path = Path(home_path)
    current = read_notice(home_path, notice_id)
    expected_kind = str(current.get("home_kind") or "")
    expected_id = str(current.get("home_id") or "")
    expected_project = str(current.get("project_id") or "")
    reader_home_kind = _required_single_line(
        reader_home_kind,
        label="reader_home_kind",
        max_chars=40,
    )
    reader_home_id = _required_single_line(
        reader_home_id,
        label="reader_home_id",
        max_chars=160,
    )
    reader_project_id = _single_line(
        reader_project_id,
        label="reader_project_id",
        max_chars=160,
    )
    if reader_home_kind not in {"project_agent", "rooter"}:
        raise NoticeProblem(
            "notice_read_home_kind_invalid",
            "reader_home_kind 无效。",
            {"reader_home_kind": reader_home_kind},
        )
    if (
        reader_home_kind != expected_kind
        or reader_home_id != expected_id
        or reader_project_id != expected_project
    ):
        raise NoticeProblem(
            "notice_read_identity_mismatch",
            "只能由拥有该 Notice 的精确 Home 标读；不允许用其它 Home 预览代写。",
            {
                "notice_id": notice_id,
                "notice_home": {
                    "home_kind": expected_kind,
                    "home_id": expected_id,
                    "project_id": expected_project,
                },
                "reader_home": {
                    "home_kind": reader_home_kind,
                    "home_id": reader_home_id,
                    "project_id": reader_project_id,
                },
            },
        )
    if current.get("read"):
        return {**current, "read_changed": False}
    path = _read_record_path(home_path, notice_id)
    record = {
        "schema": NOTICE_READ_SCHEMA,
        "notice_id": notice_id,
        "reader_home_kind": reader_home_kind,
        "reader_home_id": reader_home_id,
        "reader_project_id": reader_project_id,
        "read_at": _utc_now_iso_precise(),
    }
    created = _atomic_create(
        path,
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
    )
    if not created:
        existing = _read_notice_read_record(home_path, notice_id)
        if existing is None:
            raise NoticeProblem(
                "notice_read_record_missing_after_conflict",
                "Notice read sidecar 创建竞争后无法回读。",
                {"path": str(path), "notice_id": notice_id},
            )
        if (
            str(existing.get("reader_home_kind") or "") != reader_home_kind
            or str(existing.get("reader_home_id") or "") != reader_home_id
            or str(existing.get("reader_project_id") or "") != reader_project_id
        ):
            raise NoticeProblem(
                "notice_read_identity_conflict",
                "Notice 已由不同 Home 标读；拒绝覆盖首读事实。",
                {"path": str(path), "notice_id": notice_id},
            )
    updated = read_notice(home_path, notice_id)
    if (
        str(updated.get("read_by_home_kind") or "") != reader_home_kind
        or str(updated.get("read_by_home_id") or "") != reader_home_id
        or str(updated.get("read_by_project_id") or "") != reader_project_id
    ):
        raise NoticeProblem(
            "notice_read_identity_conflict",
            "Notice 标读回读身份与当前 Home 不一致。",
            {"notice_id": notice_id},
        )
    return {**updated, "read_changed": bool(created)}


def handle_notice(
    *, home_path: Path, notice_id: str, resolution: str = "", action_ref: str = "",
) -> dict[str, Any]:
    """Atomically establish handled fact without read-modify-replace."""
    home_path = Path(home_path)
    current = read_notice(home_path, notice_id)
    resolution = _single_line(resolution, label="resolution", max_chars=500)
    action_ref = _single_line(action_ref, label="action_ref", max_chars=1000)
    if current.get("state") == "handled":
        if (str(current.get("resolution") or "") == resolution
            and str(current.get("action_ref") or "") == action_ref):
            return {**current, "changed": False}
        raise NoticeProblem(
            "notice_handling_conflict",
            "Notice 已 handled，不能静默改写既有处理结果。",
            {"notice_id": notice_id,
             "existing_resolution": current.get("resolution"),
             "existing_action_ref": current.get("action_ref")},
        )
    marker = _create_handled_record(
        home_path=home_path, notice_id=notice_id, handled_at=utc_now_iso(),
        resolution=resolution, action_ref=action_ref,
    )
    return {**read_notice(home_path, notice_id), "changed": bool(marker.get("created"))}



def _sidecar_index_from_blobs(directory: Path, blobs: dict[str, bytes], record_for) -> dict[str, Any]:
    handled: dict[str, dict[str, Any]] = {}
    read_records: dict[str, dict[str, Any]] = {}
    activation: dict[str, list[dict[str, Any]]] = {}
    organization: dict[str, list[dict[str, Any]]] = {}
    for relative in sorted(blobs):
        parts = relative.split("/")
        path = directory / relative
        if len(parts) == 2 and parts[0] == ".handled" and relative.endswith(".json"):
            record = record_for(path, "notice_handled_record_invalid")
            notice_id = path.stem
            if record.get("schema") != "paos-notice-handled/v1" or record.get("notice_id") != notice_id:
                raise NoticeProblem("notice_handled_record_invalid", f"Notice handled sidecar schema/identity 无效：{path}", {"path": str(path), "notice_id": notice_id})
            handled[notice_id] = record
        elif len(parts) == 2 and parts[0] == ".read" and relative.endswith(".json"):
            record = record_for(path, "notice_read_record_invalid")
            notice_id = path.stem
            if record.get("schema") != NOTICE_READ_SCHEMA or record.get("notice_id") != notice_id:
                raise NoticeProblem("notice_read_record_invalid", f"Notice read sidecar schema/identity 无效：{path}", {"path": str(path), "notice_id": notice_id})
            reader_kind = str(record.get("reader_home_kind") or "").strip()
            reader_id = str(record.get("reader_home_id") or "").strip()
            reader_project = str(record.get("reader_project_id") or "").strip()
            read_at = str(record.get("read_at") or "").strip()
            if reader_kind not in {"project_agent", "rooter"} or not reader_id or not read_at:
                raise NoticeProblem("notice_read_record_invalid", f"Notice read sidecar identity/timestamp 无效：{path}", {"path": str(path), "notice_id": notice_id})
            if reader_kind == "project_agent" and not reader_project:
                raise NoticeProblem("notice_read_record_invalid", f"project_agent read sidecar 缺少 reader_project_id：{path}", {"path": str(path), "notice_id": notice_id})
            if reader_kind == "rooter" and reader_project:
                raise NoticeProblem("notice_read_record_invalid", f"rooter read sidecar 不得带 reader_project_id：{path}", {"path": str(path), "notice_id": notice_id})
            read_records[notice_id] = {**record, "reader_home_kind": reader_kind, "reader_home_id": reader_id, "reader_project_id": reader_project, "read_at": read_at, "path": str(path)}
        elif len(parts) == 3 and parts[0] in {".activation", ".organization"} and relative.endswith(".json"):
            notice_id = parts[1]
            if parts[0] == ".activation":
                record = record_for(path, "notice_activation_request_invalid")
                if record.get("schema") != "paos-notice-activation-request/v1" or record.get("notice_id") != notice_id or record.get("activation_request_id") != path.stem:
                    raise NoticeProblem("notice_activation_request_invalid", f"Notice activation sidecar schema/identity 无效：{path}", {"path": str(path), "notice_id": notice_id})
                activation.setdefault(notice_id, []).append(record)
            else:
                record = record_for(path, "notice_organization_update_invalid")
                if record.get("schema") != "paos-notice-organization/v1" or record.get("notice_id") != notice_id or not str(record.get("operation_id") or "").strip() or not isinstance(record.get("changes"), dict):
                    raise NoticeProblem("notice_organization_update_invalid", "Notice organization sidecar 内容无效。", {"path": str(path), "notice_id": notice_id})
                organization.setdefault(notice_id, []).append(record)
    for records in (activation, organization):
        for notice_id in records:
            records[notice_id].sort(key=lambda item: (str(item.get("requested_at") or item.get("recorded_at") or ""), str(item.get("activation_request_id") or item.get("operation_id") or "")))
    return {"handled": handled, "read": read_records, "activation": activation, "organization": organization}

def _read_sidecar_index(directory: Path, blobs: dict[str, bytes] | None = None) -> dict[str, Any]:
    """Read sidecar directories once, preserving each record's validation."""
    base_dir = directory

    def raw_for(path: Path) -> bytes | None:
        if blobs is None:
            return None
        return blobs.get(path.relative_to(base_dir).as_posix())

    def record_for(path: Path, code: str) -> dict[str, Any]:
        raw = raw_for(path)
        if raw is None:
            return _read_json_record(path, code=code)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise NoticeProblem(code, f"Notice sidecar 无法读取：{path}", {"path": str(path), "cause": str(exc)}) from exc
        if not isinstance(value, dict):
            raise NoticeProblem(code, f"Notice sidecar 内容无效：{path}", {"path": str(path)})
        return value

    if blobs is not None:
        return _sidecar_index_from_blobs(directory, blobs, record_for)

    handled: dict[str, dict[str, Any]] = {}
    read_records: dict[str, dict[str, Any]] = {}
    base = directory / ".handled"
    if base.is_dir():
        for path in base.glob("*.json"):
            record = record_for(path, "notice_handled_record_invalid")
            if record.get("schema") != "paos-notice-handled/v1" or record.get("notice_id") != path.stem:
                raise NoticeProblem(
                    "notice_handled_record_invalid",
                    f"Notice handled sidecar schema/identity 无效：{path}",
                    {"path": str(path), "notice_id": path.stem},
                )
            handled[path.stem] = record
    base = directory / ".read"
    if base.is_dir():
        for path in base.glob("*.json"):
            record = record_for(path, "notice_read_record_invalid")
            notice_id = path.stem
            if record.get("schema") != NOTICE_READ_SCHEMA or record.get("notice_id") != notice_id:
                raise NoticeProblem(
                    "notice_read_record_invalid",
                    f"Notice read sidecar schema/identity 无效：{path}",
                    {"path": str(path), "notice_id": notice_id},
                )
            reader_kind = str(record.get("reader_home_kind") or "").strip()
            reader_id = str(record.get("reader_home_id") or "").strip()
            reader_project = str(record.get("reader_project_id") or "").strip()
            read_at = str(record.get("read_at") or "").strip()
            if reader_kind not in {"project_agent", "rooter"} or not reader_id or not read_at:
                raise NoticeProblem(
                    "notice_read_record_invalid",
                    f"Notice read sidecar identity/timestamp 无效：{path}",
                    {"path": str(path), "notice_id": notice_id},
                )
            if reader_kind == "project_agent" and not reader_project:
                raise NoticeProblem(
                    "notice_read_record_invalid",
                    f"project_agent read sidecar 缺少 reader_project_id：{path}",
                    {"path": str(path), "notice_id": notice_id},
                )
            if reader_kind == "rooter" and reader_project:
                raise NoticeProblem(
                    "notice_read_record_invalid",
                    f"rooter read sidecar 不得带 reader_project_id：{path}",
                    {"path": str(path), "notice_id": notice_id},
                )
            read_records[notice_id] = {
                **record,
                "reader_home_kind": reader_kind,
                "reader_home_id": reader_id,
                "reader_project_id": reader_project,
                "read_at": read_at,
                "path": str(path),
            }
    activation: dict[str, list[dict[str, Any]]] = {}
    organization: dict[str, list[dict[str, Any]]] = {}
    for name, target, schema, code, message in (
        (".activation", activation, "paos-notice-activation-request/v1",
         "notice_activation_request_invalid", "activation"),
        (".organization", organization, "paos-notice-organization/v1",
         "notice_organization_update_invalid", "organization"),
    ):
        base = directory / name
        if not base.is_dir():
            continue
        for notice_dir_path in base.iterdir():
            if not notice_dir_path.is_dir():
                continue
            records: list[dict[str, Any]] = []
            for path in sorted(notice_dir_path.glob("*.json")):
                record = record_for(path, code)
                if record.get("schema") != schema or record.get("notice_id") != notice_dir_path.name:
                    raise NoticeProblem(
                        code,
                        f"Notice {message} sidecar schema/identity 无效：{path}",
                        {"path": str(path), "notice_id": notice_dir_path.name},
                    )
                if name == ".activation" and record.get("activation_request_id") != path.stem:
                    raise NoticeProblem(
                        code,
                        f"Notice activation sidecar schema/identity 无效：{path}",
                        {"path": str(path), "notice_id": notice_dir_path.name},
                    )
                if name == ".organization" and (
                    not str(record.get("operation_id") or "").strip()
                    or not isinstance(record.get("changes"), dict)
                ):
                    raise NoticeProblem(
                        code,
                        "Notice organization sidecar 内容无效。",
                        {"path": str(path), "notice_id": notice_dir_path.name},
                    )
                records.append(record)
            if records:
                records.sort(
                    key=lambda item: (
                        str(item.get("requested_at") or item.get("recorded_at") or ""),
                        str(item.get("activation_request_id") or item.get("operation_id") or ""),
                    )
                )
                target[notice_dir_path.name] = records
    return {"handled": handled, "read": read_records, "activation": activation, "organization": organization}

def list_notices(home_path: Path, blobs: dict[str, bytes] | None = None) -> dict[str, Any]:
    directory = notice_dir(home_path)
    if not directory.is_dir():
        return {
            "schema": NOTICE_LIST_SCHEMA,
            "home_path": str(home_path),
            "count": 0,
            "pending_count": 0,
            "archived_count": 0,
            "archived_pending_count": 0,
            "activation_requested_count": 0,
            "read_count": 0,
            "unread_pending_count": 0,
            "read_pending_count": 0,
            "handled_unread_count": 0,
            "items": [],
        }
    index = _read_sidecar_index(directory, blobs)
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("notice-*.md")):
        notice_id = path.stem
        try:
            text = (
                blobs[path.relative_to(directory).as_posix()].decode("utf-8")
                if blobs is not None and path.relative_to(directory).as_posix() in blobs
                else path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError) as exc:
            raise NoticeProblem(
                "notice_unreadable", f"Notice 无法读取：{path}", {"path": str(path)}
            ) from exc
        items.append(
            _project_notice(
                _parse_notice_text(text, path=path),
                index["handled"].get(notice_id),
                index["read"].get(notice_id),
                index["activation"].get(notice_id, []),
                index["organization"].get(notice_id, []),
            )
        )
    items.sort(
        key=lambda item: (
            1 if item.get("archived") else 0,
            0 if item.get("state") == "pending" else 1,
            0 if isinstance(item.get("sort_order"), int) else 1,
            int(item.get("sort_order") or 0),
            str(item.get("created_at") or ""),
            str(item.get("notice_id") or ""),
        )
    )
    pending = [item for item in items if item.get("state") == "pending"]
    archived = [item for item in items if item.get("archived")]
    requested = [
        item
        for item in pending
        if str(item.get("activation_request_id") or "")
    ]
    read = [item for item in items if item.get("read")]
    unread_pending = [
        item
        for item in pending
        if not item.get("read")
    ]
    read_pending = [
        item
        for item in pending
        if item.get("read")
    ]
    handled_unread = [
        item
        for item in items
        if item.get("state") == "handled" and not item.get("read")
    ]
    return {
        "schema": NOTICE_LIST_SCHEMA,
        "home_path": str(home_path),
        "count": len(items),
        "pending_count": len(pending),
        "archived_count": len(archived),
        "archived_pending_count": sum(
            1 for item in archived if item.get("state") == "pending"
        ),
        "activation_requested_count": len(requested),
        "read_count": len(read),
        "unread_pending_count": len(unread_pending),
        "read_pending_count": len(read_pending),
        "handled_unread_count": len(handled_unread),
        "items": items,
    }


def organize_notice(
    *,
    home_path: Path,
    notice_id: str,
    summary: str | None = None,
    sort_order: int | None = None,
    archived: bool | None = None,
    operation_id: str = "",
) -> dict[str, Any]:
    """Append one presentation-only Notice organization update.

    Source identity/body, pending/handled, activation requests, TODO and Runtime
    attempts are untouched. Reusing operation_id with the same changes is
    idempotent; reusing it with different changes fails.
    """
    home_path = Path(home_path)
    current = read_notice(home_path, notice_id)
    changes: dict[str, Any] = {}
    if summary is not None:
        changes["summary"] = _required_single_line(
            summary,
            label="summary",
            max_chars=500,
        )
    if sort_order is not None:
        if isinstance(sort_order, bool) or not isinstance(sort_order, int):
            raise NoticeProblem(
                "notice_sort_order_invalid",
                "sort_order 必须是整数。",
                {"sort_order": sort_order},
            )
        if not -1_000_000 <= sort_order <= 1_000_000:
            raise NoticeProblem(
                "notice_sort_order_invalid",
                "sort_order 超出允许范围。",
                {"sort_order": sort_order},
            )
        changes["sort_order"] = sort_order
    if archived is not None:
        if not isinstance(archived, bool):
            raise NoticeProblem(
                "notice_archive_flag_invalid",
                "archived 必须是布尔值。",
                {"archived": archived},
            )
        changes["archived"] = archived
    if not changes:
        raise NoticeProblem(
            "notice_organization_empty",
            "至少提供 summary / sort_order / archived 之一。",
            {"notice_id": notice_id},
        )

    op = _single_line(operation_id, label="operation_id", max_chars=160)
    if not op:
        op = f"notice-org-{uuid.uuid4().hex}"
    path = _organization_update_path(home_path, notice_id, op)
    record = {
        "schema": "paos-notice-organization/v1",
        "notice_id": notice_id,
        "operation_id": op,
        "recorded_at": _utc_now_iso_precise(),
        "changes": changes,
    }
    created = _atomic_create(
        path,
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
    )
    if not created:
        existing = _read_json_record(
            path,
            code="notice_organization_update_invalid",
        )
        if (
            existing.get("schema") != record["schema"]
            or existing.get("notice_id") != notice_id
            or existing.get("operation_id") != op
            or existing.get("changes") != changes
        ):
            raise NoticeProblem(
                "notice_organization_conflict",
                "operation_id 已存在不同 Notice organization 内容。",
                {
                    "notice_id": notice_id,
                    "operation_id": op,
                    "existing_changes": existing.get("changes"),
                    "requested_changes": changes,
                },
            )
    updated = read_notice(home_path, notice_id)
    if updated.get("source_ref") != current.get("source_ref"):
        raise NoticeProblem(
            "notice_identity_changed",
            "Notice organization 不得改变 source identity。",
            {"notice_id": notice_id},
        )
    return {
        **updated,
        "organization_operation_id": op,
        "organization_update_created": created,
        "runtime_wake_performed": False,
    }

def activation_candidates(home_path: Path) -> list[dict[str, Any]]:
    """Return pending inputs with explicit activation intent.

    Import-only pending Notices are deliberately absent.  P3 must reconcile each
    returned request_id with Wake/native attempt evidence before doing anything.
    """
    listing = list_notices(home_path)
    return [
        item
        for item in listing["items"]
        if item.get("state") == "pending"
        and str(item.get("activation_request_id") or "")
    ]


def persist_mail_dispatch_notices(
    *,
    root: Path,
    dispatch: dict[str, Any],
    recipient_homes: dict[str, dict[str, Any]],
    request_activation: bool,
    activation_request_id: str = "",
    restrict_targets: list[str] | None = None,
) -> dict[str, Any]:
    """Project Mail into exact pre-resolved Project Agent Homes.

    Transport recipient ids are not enough to infer a Home. Callers must resolve
    each recipient through the current Project roster first. Rooter uses an
    explicit rooter Home through the generic source-registration service.
    """
    root = Path(root)
    project_id = _required_single_line(dispatch.get("project_id"), label="dispatch.project_id", max_chars=160)
    message_id = _required_single_line(dispatch.get("message_id"), label="dispatch.message_id", max_chars=1000)
    summary = _required_single_line(dispatch.get("subject"), label="dispatch.subject", max_chars=500)
    request_id = _single_line(activation_request_id, label="activation_request_id", max_chars=160)
    if request_activation and not request_id:
        raise NoticeProblem(
            "notice_activation_request_id_missing",
            "request_activation=true 时必须提供稳定 activation_request_id。",
            {"message_id": message_id},
        )
    items: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    allowed = set(restrict_targets or [])
    for delivery in dispatch.get("deliveries") or []:
        if not isinstance(delivery, dict):
            continue
        agent_id = str(delivery.get("recipient_agent_id") or "").strip()
        state = str(delivery.get("state") or "")
        if not agent_id:
            continue
        if agent_id not in recipient_homes:
            skipped.append({"agent_id": agent_id, "delivery_state": state})
            continue
        if allowed and agent_id not in allowed:
            skipped.append({"agent_id": agent_id, "delivery_state": state})
            continue
        if state not in {"delivered", "already_delivered"}:
            skipped.append({"agent_id": agent_id, "delivery_state": state})
            continue
        ref = recipient_homes.get(agent_id)
        if not isinstance(ref, dict):
            raise NoticeProblem(
                "notice_recipient_home_missing",
                "Mail recipient 缺少已解析 Home；拒绝从 transport 数据猜工位。",
                {"agent_id": agent_id, "project_id": project_id},
            )
        if (ref.get("schema") != "paos-home-ref/v1"
            or ref.get("home_kind") != "project_agent"
            or str(ref.get("home_id") or "") != agent_id
            or str(ref.get("project_id") or "") != project_id):
            raise NoticeProblem(
                "notice_recipient_home_mismatch",
                "Mail recipient Home 与 Project/Agent identity 不一致。",
                {"agent_id": agent_id, "project_id": project_id, "home_ref": ref},
            )
        home_path = Path(str(ref.get("home_path") or ""))
        if not home_path.is_dir():
            raise NoticeProblem(
                "notice_recipient_home_missing",
                f"已解析 Home 不存在：{home_path}",
                {"agent_id": agent_id, "home_path": str(home_path)},
            )
        items.append(
            create_notice(
                home_path=home_path, home_kind="project_agent", home_id=agent_id,
                project_id=project_id, source_kind="mail", source_ref=message_id,
                summary=summary,
                activation_request_id=request_id if request_activation else "",
            )
        )
    return {
        "schema": "paos-mail-notice-projection/v1",
        "project_id": project_id, "message_id": message_id,
        "request_activation": bool(request_activation),
        "activation_request_id": request_id if request_activation else "",
        "items": items, "skipped": skipped,
        "meta": {
            "mail_body_copied": False,
            "runtime_wake_performed": False,
            "recipient_home_guessed": False,
            "migration_without_request_activation_is_silent": True,
        },
    }
