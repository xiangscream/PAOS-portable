"""Shared TODO v3 parser/renderer and legal Home writer.

These primitives are the shared, wired TODO v3 path: the Home owner's durable
plan is parsed and rendered here, and all legal Home writes (full ``todo-write``
and field-level ``todo-update``) go through one cross-platform write section
with byte-accurate, line-ending-preserving output and an optional expected
fingerprint guard.

TODO v3 owns only the Home owner's plan (Project governance facts).  External
input handling and Runtime/communication facts (PAOS Work state, Runtime
attempts, CAT/Mail transport) remain independent of this module.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _reject_result_refs(value: Any) -> list:
    _ = value
    raise TodoV3Problem(
        "todo_v3_result_refs_invalid",
        "result_refs 必须是引用清单（JSON 行字符串数组）；形如列表的字符串请先规范成真列表。",
    )


TODO_SCHEMA = "paos-todo/v3"

TASK_SCHEMA = "paos-todo-task/v1"
TASK_STATES = {"todo", "doing", "waiting", "done", "cancelled"}
_TASK_HEADING_RE = re.compile(r"^###\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s*$")


class TodoV3Problem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _single_line(value: Any, *, label: str, max_chars: int = 1000) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > max_chars:
        raise TodoV3Problem(
            "todo_v3_field_too_long",
            f"{label} 超过 {max_chars} 字符限制。",
            {"label": label, "max_chars": max_chars},
        )
    return text


def _required(value: Any, *, label: str, max_chars: int = 1000) -> str:
    text = _single_line(value, label=label, max_chars=max_chars)
    if not text:
        raise TodoV3Problem(
            "todo_v3_field_missing",
            f"{label} 不能为空。",
            {"label": label},
        )
    return text


def _json_line(key: str, value: Any) -> str:
    return f"{key}: {json.dumps(value, ensure_ascii=False)}"


def _json_decode_error_position(raw_stripped: str, exc: json.JSONDecodeError) -> int:
    """把 `json.JSONDecodeError` 的 0-based `pos` 换算成调用者能对上的一基
    行内列号（同一次 json.loads 使用的输入 ``raw_stripped``）。"""
    return max(int(getattr(exc, "pos", 0)) + 1, 1)


def _trailing_comma_removal_hint(raw_stripped: str,
                                exc: json.JSONDecodeError) -> str:
    """只在解析器**明确**报 Extra data，而 pos 之后的原文真正只剩一个
    逗号（可含空白）时，糖衣式给出删尾逗号的修复指示；其余形态不发任何
    猜想，由调用方如实转发 `original_error` 原文。"""
    if "Extra data" not in str(exc):
        return ""
    pos = int(getattr(exc, "pos", 0) or 0)
    tail = raw_stripped[pos:].strip()
    if tail == ",":
        return (
            "解析器明确指出字符串闭合后剩余内容只是一个逗号；"
            "删除该行尾逗号，让本行只保留单个 JSON scalar（`key: \"value\"`）。"
        )
    return ""


def _parse_json_value(raw: str, *, key: str, line_no: int | None = None,
                      task_id: str | None = None) -> Any:
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        stripped = raw.strip()
        details: dict[str, Any] = {"key": key, "value": stripped}
        if line_no is not None:
            details["line_no"] = line_no
        if task_id is not None:
            details["task_id"] = task_id
        column = _json_decode_error_position(stripped, exc)
        details["column"] = column
        details["original_error"] = str(exc)
        # 同一次 json.loads 已拒绝；shape 提示只在解析器证实"Extra data
        # 且剩余原件真是单个逗号"的窄背景下给出，不猜正文。
        shape_hint = _trailing_comma_removal_hint(stripped, exc)
        if shape_hint:
            details["shape_hint"] = shape_hint
        message = f"TODO v3 字段无法解析：{key}"
        if line_no is not None:
            message += f"（第 {line_no} 行"
            if task_id:
                message += f"，task {task_id}"
            message += f"，第 {column} 个字符）"
        details["position"] = (
            f"line {line_no}, char {column}" if line_no is not None
            else f"char {column}"
        )
        raise TodoV3Problem(
            "todo_v3_invalid", message, details
        ) from exc


def normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    task_id = _required(task.get("id"), label="task.id", max_chars=120)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", task_id):
        raise TodoV3Problem(
            "todo_v3_task_id_invalid",
            "task.id 格式无效。",
            {"task_id": task_id},
        )
    title = _required(task.get("title"), label="task.title", max_chars=1000)
    state = _required(task.get("state") or "todo", label="task.state", max_chars=40)
    if state not in TASK_STATES:
        raise TodoV3Problem(
            "todo_v3_task_state_invalid",
            f"task.state 必须是 {sorted(TASK_STATES)} 之一。",
            {"task_id": task_id, "state": state},
        )
    result = _single_line(task.get("result"), label="task.result", max_chars=2000)
    artifact_ref = _single_line(
        task.get("artifact_ref"),
        label="task.artifact_ref",
        max_chars=1000,
    )
    waiting = _single_line(task.get("waiting"), label="task.waiting", max_chars=1000)
    notify_after = task.get("notify_after") or []
    if not isinstance(notify_after, list):
        raise TodoV3Problem(
            "todo_v3_notify_after_invalid",
            "task.notify_after 必须是 list。",
            {"task_id": task_id},
        )
    normalized_notify: list[dict[str, str]] = []
    for item in notify_after:
        if not isinstance(item, dict):
            raise TodoV3Problem(
                "todo_v3_notify_after_invalid",
                "notify_after item 必须是 object。",
                {"task_id": task_id},
            )
        to = _required(item.get("to"), label="notify_after.to", max_chars=160)
        when = _required(item.get("when"), label="notify_after.when", max_chars=1000)
        source_ref = _single_line(
            item.get("source_ref"),
            label="notify_after.source_ref",
            max_chars=1000,
        )
        normalized_notify.append(
            {"to": to, "when": when, "source_ref": source_ref}
        )

    def _ref_list(key: str) -> list[str]:
        raw = task.get(key) or []
        if not isinstance(raw, list):
            raise TodoV3Problem(
                f"todo_v3_task_{key}_invalid",
                f"task.{key} 必须是 list。",
                {"task_id": task_id},
            )
        return [
            _required(value, label=f"task.{key} item", max_chars=1000)
            for value in raw
            if str(value or "").strip()
        ]

    return {
        "schema": TASK_SCHEMA,
        "id": task_id,
        "title": title,
        "state": state,
        "waiting": waiting,
        "result": result,
        "artifact_ref": artifact_ref,
        "notify_after": normalized_notify,
        # 任务层引用（方案 §130-131）：source_refs 关联输入/Notice，
        # acceptance_refs 关联接受方原件与所接受成果版本（无接受环节可空）。
        "source_refs": _ref_list("source_refs"),
        "acceptance_refs": _ref_list("acceptance_refs"),
    }


def render_todo_v3(
    *,
    home_kind: str,
    home_id: str,
    project_id: str = "",
    objective: str,
    approved_scope: str = "",
    stage: str = "",
    next_action: str,
    waiting: str = "",
    results: str = "",
    result_refs: Iterable[str] = (),
    context_refs: Iterable[str] = (),
    legacy_source_ref: str = "",
    inflight: str = "",
    alignment_ref: str = "",
    input_version: str = "",
    delivery: str = "",
    dependencies: str = "",
    continuation_to: str = "",
    boundaries: str = "",
    history_ref: str = "",
    latest_readback: str = "",
    updated_at: str = "",
    tasks: Iterable[dict[str, Any]] = (),
) -> str:
    home_kind = _required(home_kind, label="home_kind", max_chars=40)
    if home_kind not in {"project_agent", "rooter"}:
        raise TodoV3Problem(
            "todo_v3_home_kind_invalid",
            "home_kind 必须是 project_agent 或 rooter。",
            {"home_kind": home_kind},
        )
    home_id = _required(home_id, label="home_id", max_chars=160)
    project_id = _single_line(project_id, label="project_id", max_chars=160)
    if home_kind == "project_agent" and not project_id:
        raise TodoV3Problem(
            "todo_v3_project_id_missing",
            "project_agent TODO 必须带 project_id。",
            {"home_id": home_id},
        )

    current = {
        "objective": _required(objective, label="objective", max_chars=2000),
        "approved_scope": _single_line(
            approved_scope,
            label="approved_scope",
            max_chars=2000,
        ),
        "stage": _single_line(stage, label="stage", max_chars=500),
        "next_action": _required(
            next_action,
            label="next_action",
            max_chars=2000,
        ),
        "waiting": _single_line(waiting, label="waiting", max_chars=2000),
        "results": _single_line(results, label="results", max_chars=2000),
        "result_refs": [
            _required(value, label="result_refs item", max_chars=1000)
            for value in (
                () if result_refs is None else result_refs
            )
            if str(value or "").strip()
        ],
        "context_refs": [
            _required(value, label="context_refs item", max_chars=1000)
            for value in context_refs
            if str(value or "").strip()
        ],
        "legacy_source_ref": _single_line(
            legacy_source_ref,
            label="legacy_source_ref",
            max_chars=1000,
        ),
        "inflight": _single_line(inflight, label="inflight", max_chars=2000),
        "alignment_ref": _single_line(
            alignment_ref,
            label="alignment_ref",
            max_chars=2000,
        ),
        "input_version": _single_line(
            input_version,
            label="input_version",
            max_chars=1000,
        ),
        "delivery": _single_line(delivery, label="delivery", max_chars=2000),
        "dependencies": _single_line(
            dependencies,
            label="dependencies",
            max_chars=2000,
        ),
        "continuation_to": _single_line(
            continuation_to,
            label="continuation_to",
            max_chars=1000,
        ),
        "boundaries": _single_line(
            boundaries,
            label="boundaries",
            max_chars=2000,
        ),
        "history_ref": _single_line(
            history_ref,
            label="history_ref",
            max_chars=1000,
        ),
        "latest_readback": _single_line(
            latest_readback,
            label="latest_readback",
            max_chars=2000,
        ),
    }
    if updated_at.strip():
        current["updated_at"] = _single_line(
            updated_at, label="updated_at", max_chars=100
        )
    normalized_tasks = [normalize_task(task) for task in tasks]
    task_ids = [task["id"] for task in normalized_tasks]
    if len(task_ids) != len(set(task_ids)):
        raise TodoV3Problem(
            "todo_v3_duplicate_task_id",
            "TODO v3 task id 重复。",
            {"task_ids": task_ids},
        )

    lines = [
        "---",
        _json_line("schema", TODO_SCHEMA),
        _json_line("home_kind", home_kind),
        _json_line("home_id", home_id),
        _json_line("project_id", project_id),
        "---",
        "",
        "# Current",
        "",
    ]
    for key in (
        "objective",
        "approved_scope",
        "stage",
        "next_action",
        "waiting",
        "results",
        "result_refs",
        "context_refs",
        "legacy_source_ref",
        "inflight",
        "alignment_ref",
        "input_version",
        "delivery",
        "dependencies",
        "continuation_to",
        "boundaries",
        "history_ref",
        "latest_readback",
    ):
        lines.append(_json_line(key, current[key]))
    if "updated_at" in current:
        lines.append(_json_line("updated_at", current["updated_at"]))

    lines += ["", "# Tasks", ""]
    if not normalized_tasks:
        lines.append("_none_")
    for task in normalized_tasks:
        lines += [
            f"### {task['id']}",
            _json_line("schema", TASK_SCHEMA),
            _json_line("title", task["title"]),
            _json_line("state", task["state"]),
            _json_line("waiting", task["waiting"]),
            _json_line("result", task["result"]),
            _json_line("artifact_ref", task["artifact_ref"]),
            _json_line("notify_after", task["notify_after"]),
        ]
        if task.get("source_refs"):
            lines.append(_json_line("source_refs", task["source_refs"]))
        if task.get("acceptance_refs"):
            lines.append(_json_line("acceptance_refs", task["acceptance_refs"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_todo_v3(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise TodoV3Problem("todo_v3_invalid", "TODO v3 缺少 front matter。")
    meta: dict[str, Any] = {}
    index = 1
    while index < len(lines):
        raw = lines[index]
        index += 1
        if raw.strip() == "---":
            break
        key, sep, value = raw.partition(":")
        if sep:
            key = key.strip()
            if key in meta:
                raise TodoV3Problem(
                    "todo_v3_invalid",
                    f"TODO v3 front matter 重复字段：{key}",
                )
            meta[key] = _parse_json_value(value, key=key, line_no=index)
    else:
        raise TodoV3Problem("todo_v3_invalid", "TODO v3 front matter 未闭合。")

    if meta.get("schema") != TODO_SCHEMA:
        raise TodoV3Problem(
            "todo_v3_invalid",
            "TODO schema 不是 paos-todo/v3。",
            {"schema": meta.get("schema")},
        )

    current: dict[str, Any] = {}
    tasks: list[dict[str, Any]] = []
    mode = ""
    task: dict[str, Any] | None = None
    while index < len(lines):
        raw = lines[index]
        index += 1
        stripped = raw.strip()
        if stripped == "# Current":
            mode = "current"
            task = None
            continue
        if stripped == "# Tasks":
            mode = "tasks"
            task = None
            continue
        match = _TASK_HEADING_RE.match(stripped)
        if match and mode == "tasks":
            if task is not None:
                tasks.append(normalize_task(task))
            task = {"id": match.group(1)}
            continue
        if not stripped or stripped == "_none_":
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            continue
        key = key.strip()
        # 原行号 / 所属 task 一起带进失败详情，让本人一眼真实定位不必再猜。
        active_task_id = task.get("id") if task is not None else None
        parsed = _parse_json_value(value, key=key, line_no=index, task_id=active_task_id)
        if mode == "current":
            current[key] = parsed
        elif mode == "tasks" and task is not None:
            task[key] = parsed

    if task is not None:
        tasks.append(normalize_task(task))

    for key in ("objective", "next_action"):
        if not _single_line(current.get(key), label=key, max_chars=2000):
            raise TodoV3Problem(
                "todo_v3_invalid",
                f"TODO v3 Current 缺少 {key}。",
                {"field": key},
            )

    home_kind = _required(meta.get("home_kind"), label="home_kind", max_chars=40)
    home_id = _required(meta.get("home_id"), label="home_id", max_chars=160)
    project_id = _single_line(meta.get("project_id"), label="project_id", max_chars=160)
    if home_kind == "project_agent" and not project_id:
        raise TodoV3Problem(
            "todo_v3_project_id_missing",
            "project_agent TODO 必须带 project_id。",
            {"home_id": home_id},
        )

    counts = {state: 0 for state in sorted(TASK_STATES)}
    for item in tasks:
        counts[item["state"]] += 1
    counts["total"] = len(tasks)
    return {
        "schema": TODO_SCHEMA,
        "home_kind": home_kind,
        "home_id": home_id,
        "project_id": project_id,
        "current": current,
        "tasks": tasks,
        "counts": counts,
    }


def read_todo_v3(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TodoV3Problem(
            "todo_v3_missing",
            f"TODO v3 不存在：{path}",
            {"path": str(path)},
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise TodoV3Problem(
            "todo_v3_unreadable",
            f"TODO v3 无法读取：{path}",
            {"path": str(path)},
        ) from exc
    return {**parse_todo_v3(text), "path": str(path)}


MANAGED_CURRENT_FIELDS = frozenset(
    {
        "objective",
        "approved_scope",
        "stage",
        "next_action",
        "waiting",
        "results",
        "result_refs",
        "context_refs",
        "legacy_source_ref",
        "inflight",
        "alignment_ref",
        "input_version",
        "delivery",
        "dependencies",
        "continuation_to",
        "boundaries",
        "history_ref",
        "latest_readback",
        "updated_at",
    }
)
_LIST_CURRENT_FIELDS = frozenset({"result_refs", "context_refs"})


def fingerprint_todo_v3(path: Path) -> str:
    """sha256 of the exact on-disk bytes; the optimistic-lock fingerprint."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise TodoV3Problem(
            "todo_v3_unreadable",
            f"TODO v3 无法读取：{path}",
            {"path": str(path)},
        ) from exc
    return hashlib.sha256(data).hexdigest()


def _detect_eol(text: str) -> str:
    """Preserve the file's line ending: CRLF if the text uses it, else LF."""
    return "\r\n" if "\r\n" in text else "\n"


TODO_V3_LOCK_TIMEOUT_SECONDS = 10.0
TODO_V3_LOCK_POLL_SECONDS = 0.05


def _todo_v3_lock_path(path: Path) -> Path:
    return Path(path).with_name(f".{Path(path).name}.lock.v2")


@contextlib.contextmanager
def todo_v3_lock(
    path: Path,
    *,
    timeout: float = TODO_V3_LOCK_TIMEOUT_SECONDS,
):
    """Cross-platform exclusive-create token for the complete write section.

    The token path is shared by Windows and WSL on the same Home filesystem.
    FileExistsError means normal contention and is retried until the bounded
    timeout; other OS errors remain lock errors. A stale token is fail-closed:
    it is not removed automatically and future writers time out.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _todo_v3_lock_path(path)
    deadline = time.monotonic() + max(float(timeout), 0.0)
    acquired = False
    body_error: BaseException | None = None
    try:
        while True:
            try:
                fd = os.open(
                    str(lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TodoV3Problem(
                        "todo_v3_lock_timeout",
                        f"TODO v3 写锁等待超时：{path}",
                        {
                            "path": str(path),
                            "timeout_seconds": float(timeout),
                        },
                    )
                time.sleep(
                    min(
                        TODO_V3_LOCK_POLL_SECONDS,
                        max(deadline - time.monotonic(), 0.0),
                    )
                )
            except OSError as exc:
                raise TodoV3Problem(
                    "todo_v3_lock_error",
                    f"TODO v3 写锁无法访问：{path}",
                    {"path": str(path), "os_error": str(exc)},
                ) from exc
            else:
                acquired = True
                try:
                    os.close(fd)
                except OSError as exc:
                    raise TodoV3Problem(
                        "todo_v3_lock_error",
                        f"TODO v3 写锁无法关闭：{path}",
                        {"path": str(path), "os_error": str(exc)},
                    ) from exc
                break
        try:
            yield
        except BaseException as exc:
            body_error = exc
            raise
    finally:
        if acquired:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                if body_error is None:
                    raise TodoV3Problem(
                        "todo_v3_lock_error",
                        f"TODO v3 写锁释放失败：{path}",
                        {
                            "path": str(path),
                            "lock_path": str(lock_path),
                            "os_error": str(exc),
                        },
                    ) from exc


def _surgical_replace_current(text: str, updates: dict[str, Any]) -> str:
    """Replace/insert only the updated Current field lines; all other lines,
    unknown Current keys, task bodies and personal content stay byte-identical."""
    lines = text.splitlines()
    heading = next(
        (i for i, line in enumerate(lines) if line.strip() == "# Current"), None
    )
    if heading is None:
        raise TodoV3Problem(
            "todo_v3_current_section_missing",
            "TODO v3 缺少 `# Current` 段；无法做字段级修改（请交回完整恢复载荷）。",
            {},
        )

    def section_end() -> int:
        return next(
            (i for i in range(heading + 1, len(lines)) if lines[i].strip() == "# Tasks"),
            len(lines),
        )

    def is_field_line(line: str) -> bool:
        return line.strip() and not line.lstrip().startswith("#") and ":" in line

    for key, value in updates.items():
        end = section_end()
        matches = [
            i
            for i in range(heading + 1, end)
            if lines[i].partition(":")[0].strip() == key
        ]
        if matches:
            index = matches[-1]
            prefix = lines[index][: lines[index].index(":")]
            lines[index] = f"{prefix}: {json.dumps(value, ensure_ascii=False)}"
            continue
        end = section_end()
        field_indices = [
            i for i in range(heading + 1, end) if is_field_line(lines[i])
        ]
        new_line = f"{key}: {json.dumps(value, ensure_ascii=False)}"
        if field_indices:
            lines.insert(field_indices[-1] + 1, new_line)
        else:
            lines.insert(heading + 1, new_line)
    eol = _detect_eol(text)
    edited = eol.join(lines)
    if text.endswith("\n"):
        edited += eol
    return edited


def update_todo_v3_current(
    path: Path,
    updates: dict[str, Any],
    *,
    expected_fingerprint: str | None = None,
    now: str | None = None,
    touch_updated_at: bool = True,
) -> dict[str, Any]:
    """Take the cross-process lock over the whole critical section, then edit."""
    path = Path(path)
    with todo_v3_lock(path):
        return _update_todo_v3_current_locked(
            path,
            updates,
            expected_fingerprint=expected_fingerprint,
            now=now,
            touch_updated_at=touch_updated_at,
        )


def _update_todo_v3_current_locked(
    path: Path,
    updates: dict[str, Any],
    *,
    expected_fingerprint: str | None = None,
    now: str | None = None,
    touch_updated_at: bool = True,
) -> dict[str, Any]:
    """Field-level, fingerprint-guarded, atomic TODO v3 Current writer.

    - optimistic lock: when ``expected_fingerprint`` is given and differs from
      the on-disk bytes, raise ``todo_v3_fingerprint_conflict`` (no write);
    - field-level: only the submitted Current keys change; unknown Current keys,
      task bodies and any personal content stay untouched;
    - unsupported: a key that is neither managed nor already present in Current
      is rejected explicitly;
    - unchanged: when the edit would not change any byte, no write happens and
      ``updated_at`` is not refreshed (no semantic-time drift);
    - atomic: publish via a staging file + ``os.replace``.
    """
    path = Path(path)
    # 指纹与公开的 fingerprint_todo_v3 同源：都针对磁盘原始字节，避免文本模式
    # 把 CRLF/BOM 归一为 LF 造成同一 TODO 两个指纹、误报冲突（S029 F3）。
    raw_bytes = path.read_bytes()
    original = raw_bytes.decode("utf-8")
    fingerprint = hashlib.sha256(raw_bytes).hexdigest()
    if expected_fingerprint and expected_fingerprint != fingerprint:
        raise TodoV3Problem(
            "todo_v3_fingerprint_conflict",
            "TODO 已被其它写者修改；请以最新指纹重读后再试。",
            {"path": str(path), "expected": expected_fingerprint, "actual": fingerprint},
        )
    parsed = parse_todo_v3(original)
    current_keys = set((parsed.get("current") or {}).keys())
    normalized: dict[str, Any] = {}
    for key, value in updates.items():
        if key not in MANAGED_CURRENT_FIELDS and key not in current_keys:
            raise TodoV3Problem(
                "todo_v3_field_unsupported",
                f"不支持的 Current 字段：{key}（非管理字段且当前不存在）。",
                {"field": key},
            )
        if key in _LIST_CURRENT_FIELDS:
            if value is None:
                normalized[key] = []
            elif isinstance(value, (list, tuple)):
                normalized[key] = [
                    _required(item, label=f"{key} item", max_chars=1000)
                    for item in value
                    if str(item or "").strip()
                ]
            else:
                raise TodoV3Problem(
                    "todo_v3_field_invalid",
                    f"{key} 必须是列表。",
                    {"field": key},
                )
        else:
            normalized[key] = _single_line(value, label=key, max_chars=2000)

    edited = _surgical_replace_current(original, normalized)
    if edited == original:
        return {
            "changed": False,
            "fingerprint": fingerprint,
            "path": str(path),
            "updated_at": (parsed.get("current") or {}).get("updated_at"),
        }
    written_at = None
    if touch_updated_at and "updated_at" not in normalized:
        written_at = now or datetime.now(timezone.utc).isoformat()
        edited = _surgical_replace_current(edited, {"updated_at": written_at})
    parse_todo_v3(edited)  # fail loudly rather than publish an invalid TODO
    staged = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        staged.write_text(edited, encoding="utf-8", newline="\n")
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)
    return {
        "changed": True,
        "fingerprint": hashlib.sha256(edited.encode("utf-8")).hexdigest(),
        "path": str(path),
        "updated_at": written_at
        or normalized.get("updated_at")
        or (parse_todo_v3(edited).get("current") or {}).get("updated_at"),
    }


def write_todo_v3(
    path: Path,
    text: str,
    *,
    create_only: bool = False,
    expected_fingerprint: str | None = None,
) -> None:
    """Atomically publish TODO v3 text under the shared cross-process lock.

    Same lock as ``update_todo_v3_current`` so a full write and a partial write
    cannot interleave. With ``expected_fingerprint`` the full write is also
    guarded: a changed on-disk fingerprint raises ``todo_v3_fingerprint_conflict``.
    """
    path = Path(path)
    with todo_v3_lock(path):
        _write_todo_v3_locked(
            path, text, create_only=create_only,
            expected_fingerprint=expected_fingerprint,
        )


def _write_todo_v3_locked(
    path: Path,
    text: str,
    *,
    create_only: bool = False,
    expected_fingerprint: str | None = None,
) -> None:
    if expected_fingerprint is not None:
        current = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if current != expected_fingerprint:
            raise TodoV3Problem(
                "todo_v3_fingerprint_conflict",
                "TODO 已被其它写者修改；请以最新指纹重读后再试。",
                {"path": str(path), "expected": expected_fingerprint, "actual": current},
            )
    parse_todo_v3(text)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if create_only and path.exists():
        raise TodoV3Problem(
            "todo_v3_exists",
            f"TODO v3 已存在：{path}",
            {"path": str(path)},
        )
    staged = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        staged.write_text(text, encoding="utf-8", newline="\n")
        if create_only:
            try:
                os.link(staged, path)
            except FileExistsError as exc:
                raise TodoV3Problem(
                    "todo_v3_exists",
                    f"TODO v3 已存在：{path}",
                    {"path": str(path)},
                ) from exc
        else:
            os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)
