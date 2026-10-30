"""PAOS TODO v4: one Obsidian-readable Home fact, not a generated workbench.

Only identity belongs in frontmatter. Pinned is free Markdown. Current is a
small, single-writer machine-readable section; Tasks are native Markdown
checkboxes (their markers, not a second state field, own task state).

Full writes and Current updates share the same cross-process lock, raw-byte
fingerprint and atomic publish. There is intentionally no v3 compatibility path.
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

TODO_SCHEMA = "paos-todo/v4"
TASK_SCHEMA = "paos-todo-task/v1"
TASK_MARKERS = {"todo": " ", "doing": "/", "waiting": "?", "done": "x", "cancelled": "-"}
MARKER_STATES = {value: key for key, value in TASK_MARKERS.items()}
TASK_STATES = frozenset(TASK_MARKERS)
CURRENT_FIELDS = {
    "objective": "Objective",
    "next_action": "Next action",
    "waiting": "Waiting",
    "inflight": "Inflight",
    "context_refs": "Context refs",
    "result_refs": "Result refs",
    "updated_at": "Updated at",
}
LIST_CURRENT_FIELDS = frozenset({"context_refs", "result_refs"})
TASK_FIELDS = {
    "waiting": "Waiting",
    "result": "Result",
    "artifact_ref": "Artifact",
    "source_refs": "Source refs",
    "acceptance_refs": "Acceptance refs",
    "notify_after": "Notify after",
}
_TASK_LIST_FIELDS = {"source_refs", "acceptance_refs", "notify_after"}
_TASK_HEADER = re.compile(r"^- \[([ /?x-])\] \*\*([A-Za-z0-9][A-Za-z0-9._-]*)\*\* · (.+)$")
_CURRENT_LINE = re.compile(r"^- \*\*([^*]+):\*\*(?: (.*))?$")
_TASK_LINE = re.compile(r"^  - \*\*([^*]+):\*\*(?: (.*))?$")
_NOTIFY_TO = re.compile(r"^    - \*\*To:\*\* (.+)$")
_NOTIFY_WHEN = re.compile(r"^      - \*\*When:\*\* (.+)$")
_NOTIFY_SOURCE = re.compile(r"^      - \*\*Source:\*\* (.*)$")
_TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class TodoProblem(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _bad(message: str, *, line: int | None = None, code: str = "todo_invalid") -> None:
    raise TodoProblem(code, message, {"line_no": line} if line is not None else {})


def _scalar(value: Any, name: str, *, required: bool = False, max_chars: int = 2000) -> str:
    if not isinstance(value, str):
        _bad(f"{name} 必须是文本，不能自动把对象转换为字符串。")
    if "\n" in value or "\r" in value or len(value) > max_chars:
        _bad(f"{name} 只能是一行，最多 {max_chars} 字；长原文放 Pinned 或来源文件。")
    value = value.strip()
    if required and not value:
        _bad(f"{name} 不能为空。")
    return value


def _refs(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (tuple, list)):
        _bad(f"{name} 必须是引用列表。")
    return [_scalar(item, name, required=True, max_chars=1000) for item in value]


def normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(task, dict):
        _bad("任务必须是对象。")
    unknown = set(task) - {"schema", "id", "title", "state", *TASK_FIELDS}
    if unknown:
        _bad(f"任务包含不支持的字段：{sorted(unknown)}。")
    ident = _scalar(task.get("id"), "task.id", required=True, max_chars=120)
    if not _TASK_ID.fullmatch(ident):
        _bad(f"非法任务 ID：{ident}")
    title = _scalar(task.get("title"), "task.title", required=True, max_chars=1000)
    state = task.get("state", "todo")
    if state not in TASK_STATES:
        _bad(f"任务状态必须是 {sorted(TASK_STATES)} 之一。")
    notify = task.get("notify_after") or []
    if not isinstance(notify, list):
        _bad("notify_after 必须是对象列表。")
    normalized_notify = []
    for item in notify:
        if not isinstance(item, dict) or set(item) - {"to", "when", "source_ref"}:
            _bad("notify_after 仅允许 to/when/source_ref 对象。")
        normalized_notify.append({
            "to": _scalar(item.get("to"), "notify_after.to", required=True),
            "when": _scalar(item.get("when"), "notify_after.when", required=True),
            "source_ref": _scalar(item.get("source_ref", ""), "notify_after.source_ref"),
        })
    return {
        "schema": TASK_SCHEMA, "id": ident, "title": title, "state": state,
        "waiting": _scalar(task.get("waiting", ""), "task.waiting"),
        "result": _scalar(task.get("result", ""), "task.result"),
        "artifact_ref": _scalar(task.get("artifact_ref", ""), "task.artifact_ref"),
        "source_refs": _refs(task.get("source_refs", []), "task.source_refs"),
        "acceptance_refs": _refs(task.get("acceptance_refs", []), "task.acceptance_refs"),
        "notify_after": normalized_notify,
    }


def _validate_identity(home_kind: str, home_id: str, project_id: str) -> None:
    if home_kind not in {"project_agent", "rooter"}:
        _bad("home_kind 只允许 project_agent 或 rooter。")
    _scalar(home_id, "home_id", required=True, max_chars=160)
    _scalar(project_id, "project_id", max_chars=160)
    if home_kind == "project_agent" and not project_id:
        _bad("project_agent 必须有 project_id。")
    if home_kind == "rooter" and project_id:
        _bad("Rooter 是安装级工位，project_id 应为空。")


def _current_lines(current: dict[str, Any]) -> list[str]:
    output: list[str] = []
    for key, label in CURRENT_FIELDS.items():
        value = current.get(key, [] if key in LIST_CURRENT_FIELDS else "")
        if key in LIST_CURRENT_FIELDS:
            values = _refs(value, key)
            if values:
                output.append(f"- **{label}:**")
                output.extend(f"  - {item}" for item in values)
        else:
            value = _scalar(value, key, required=key in {"objective", "next_action"})
            if value:
                output.append(f"- **{label}:** {value}")
    return output


def render_todo(*, home_kind: str, home_id: str, project_id: str = "",
                pinned: str = "", objective: str, next_action: str,
                waiting: str = "", inflight: str = "",
                context_refs: Iterable[str] = (), result_refs: Iterable[str] = (),
                updated_at: str = "", tasks: Iterable[dict[str, Any]] = ()) -> str:
    _validate_identity(home_kind, home_id, project_id)
    if not isinstance(pinned, str):
        _bad("Pinned 必须是 Markdown 文本。")
    if any(line.strip() in {"# Pinned", "# Current", "# Tasks"} for line in pinned.splitlines()):
        _bad("Pinned 内不能嵌套保留的一级标题；使用二级标题。")
    current = dict(objective=objective, next_action=next_action, waiting=waiting,
                   inflight=inflight, context_refs=list(context_refs or []),
                   result_refs=list(result_refs or []), updated_at=updated_at)
    task_rows = [normalize_task(t) for t in tasks]
    ids = [t["id"] for t in task_rows]
    if len(set(ids)) != len(ids):
        _bad("任务 ID 不允许重复。")
    lines = ["---", f"schema: {json.dumps(TODO_SCHEMA)}",
             f"home_kind: {json.dumps(home_kind)}", f"home_id: {json.dumps(home_id, ensure_ascii=False)}",
             f"project_id: {json.dumps(project_id)}", "---", "", "# Pinned", ""]
    if pinned.strip("\n"):
        lines += pinned.strip("\n").splitlines()
    lines += ["", "# Current", ""] + _current_lines(current) + ["", "# Tasks", ""]
    for task in task_rows:
        marker = TASK_MARKERS[task["state"]]
        lines += [f"- [{marker}] **{task['id']}** · {task['title']}"]
        for key, label in TASK_FIELDS.items():
            value = task[key]
            if key in {"source_refs", "acceptance_refs"}:
                if value:
                    lines += [f"  - **{label}:**"] + [f"    - {ref}" for ref in value]
            elif key == "notify_after":
                if value:
                    lines.append("  - **Notify after:**")
                    for notice in value:
                        lines += [f"    - **To:** {notice['to']}", f"      - **When:** {notice['when']}"]
                        if notice["source_ref"]:
                            lines.append(f"      - **Source:** {notice['source_ref']}")
            elif value:
                lines.append(f"  - **{label}:** {value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    if not lines or lines[0] != "---":
        _bad("TODO 缺少 Obsidian frontmatter。", line=1)
    meta: dict[str, str] = {}
    for i in range(1, len(lines)):
        if lines[i] == "---":
            if set(meta) != {"schema", "home_kind", "home_id", "project_id"}:
                _bad("frontmatter 只能并且必须包含 schema、home_kind、home_id、project_id。")
            return meta, i + 1
        if not lines[i].strip() or ":" not in lines[i]:
            _bad("frontmatter 只能使用简单文本属性。", line=i+1)
        key, val = lines[i].split(":", 1)
        if key not in {"schema", "home_kind", "home_id", "project_id"} or key in meta:
            _bad(f"重复或未知属性：{key}", line=i+1)
        val = val.strip()
        if val.startswith('"'):
            try: val = json.loads(val)
            except (ValueError, TypeError): _bad(f"frontmatter 属性 {key} 引号不完整。", line=i+1)
        meta[key] = _scalar(val, key)
    _bad("frontmatter 未闭合。")
    raise AssertionError


def _section_range(lines: list[str], begin: int, title: str) -> tuple[int, int]:
    starts = [i for i in range(begin, len(lines)) if lines[i] == title]
    if len(starts) != 1:
        _bad(f"TODO 应有且只有一个 {title}。")
    start = starts[0]
    end = next((i for i in range(start+1, len(lines)) if lines[i].startswith("# ")), len(lines))
    return start, end


def _parse_current(rows: list[str], first_line: int) -> dict[str, Any]:
    inverse = {value: key for key, value in CURRENT_FIELDS.items()}
    current: dict[str, Any] = {}
    active_list = None
    for offset, line in enumerate(rows):
        if not line.strip():
            continue
        if (match := _CURRENT_LINE.fullmatch(line)):
            label, body = match.group(1), (match.group(2) or "")
            if label not in inverse:
                _bad(f"未知 Current 字段：{label}", line=first_line+offset)
            key = inverse[label]
            if key in current:
                _bad(f"重复 Current 字段：{label}", line=first_line+offset)
            if key in LIST_CURRENT_FIELDS:
                if body:
                    _bad(f"{label} 应使用缩进 Markdown 列表。", line=first_line+offset)
                current[key] = []
                active_list = key
            else:
                current[key] = _scalar(body, key, required=key in {"objective", "next_action"})
                active_list = None
            continue
        if active_list and line.startswith("  - "):
            current[active_list].append(_scalar(line[4:], active_list, required=True, max_chars=1000))
            continue
        _bad("Current 中只能写可识别的 Markdown 属性列表；长说明放 Pinned。", line=first_line+offset)
    if not current.get("objective") or not current.get("next_action"):
        _bad("Current 必须包含 Objective 和 Next action。")
    return {**{"waiting": "", "inflight": "", "context_refs": [], "result_refs": [], "updated_at": ""}, **current}


def _parse_tasks(rows: list[str], first_line: int) -> list[dict[str, Any]]:
    inverse = {v: k for k, v in TASK_FIELDS.items()}
    tasks: list[dict[str, Any]] = []
    task: dict[str, Any] | None = None
    current_list: str | None = None
    current_notice: dict[str, str] | None = None
    for offset, line in enumerate(rows):
        if not line.strip():
            continue
        if match := _TASK_HEADER.fullmatch(line):
            if task is not None:
                tasks.append(normalize_task(task))
            marker, ident, title = match.groups()
            task = {"id": ident, "title": title, "state": MARKER_STATES[marker]}
            current_list = None
            current_notice = None
            continue
        if task is None:
            _bad("Tasks 仅支持 Markdown checkbox 任务；格式为 - [ ] **T-001** · 标题。", line=first_line+offset)
        if match := _TASK_LINE.fullmatch(line):
            label, val = match.group(1), match.group(2) or ""
            if label not in inverse:
                _bad(f"未知任务字段：{label}", line=first_line+offset)
            key = inverse[label]
            if key in task:
                _bad(f"重复任务字段：{label}", line=first_line+offset)
            if key in _TASK_LIST_FIELDS:
                if val:
                    _bad(f"{label} 应为缩进列表。", line=first_line+offset)
                task[key] = []
                current_list = key
            else:
                task[key] = _scalar(val, key)
                current_list = None
            current_notice = None
            continue
        if current_list == "notify_after" and (m := _NOTIFY_TO.fullmatch(line)):
            current_notice = {"to": m.group(1).strip()}
            task["notify_after"].append(current_notice)
            continue
        if current_list == "notify_after" and current_notice is not None:
            if (m := _NOTIFY_WHEN.fullmatch(line)):
                if "when" in current_notice:
                    _bad("重复通知条件。", line=first_line+offset)
                current_notice["when"] = m.group(1).strip()
                continue
            if (m := _NOTIFY_SOURCE.fullmatch(line)):
                if "source_ref" in current_notice:
                    _bad("重复通知来源。", line=first_line+offset)
                current_notice["source_ref"] = m.group(1).strip()
                continue
        if current_list in {"source_refs", "acceptance_refs"} and line.startswith("    - "):
            task[current_list].append(_scalar(line[6:], current_list, required=True, max_chars=1000))
            continue
        _bad("任务内容不符合既有 Markdown 列表合同。", line=first_line+offset)
    if task is not None:
        tasks.append(normalize_task(task))
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        _bad("任务 ID 重复。")
    return tasks


def parse_todo(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        _bad("TODO 必须是 UTF-8 文本。")
    lines = text.splitlines()
    meta, start = _frontmatter(lines)
    if meta["schema"] != TODO_SCHEMA:
        _bad(f"TODO schema 必须为 {TODO_SCHEMA}。", code="todo_schema_invalid")
    _validate_identity(meta["home_kind"], meta["home_id"], meta["project_id"])
    pinned_begin, pinned_end = _section_range(lines, start, "# Pinned")
    current_begin, current_end = _section_range(lines, start, "# Current")
    tasks_begin, tasks_end = _section_range(lines, start, "# Tasks")
    if not (start <= pinned_begin < current_begin < tasks_begin and
            pinned_end == current_begin and current_end == tasks_begin and tasks_end == len(lines)):
        _bad("TODO 必须依次包含 # Pinned、# Current、# Tasks，且无额外顶级区段。")
    if any(line.strip() for line in lines[start:pinned_begin]):
        _bad("frontmatter 与 Pinned 之间不能有未登记正文。")
    pinned = "\n".join(lines[pinned_begin+1:pinned_end]).strip("\n")
    current = _parse_current(lines[current_begin+1:current_end], current_begin+2)
    tasks = _parse_tasks(lines[tasks_begin+1:tasks_end], tasks_begin+2)
    counts = {state: sum(t["state"] == state for t in tasks) for state in sorted(TASK_STATES)}
    counts["total"] = len(tasks)
    return {"schema": TODO_SCHEMA, "home_kind": meta["home_kind"],
            "home_id": meta["home_id"], "project_id": meta["project_id"],
            "pinned": pinned, "current": current, "tasks": tasks, "counts": counts}


def read_todo(path: Path) -> dict[str, Any]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise TodoProblem("todo_unreadable", f"TODO 无法读取：{path}", {"path": str(path)}) from exc
    return {**parse_todo(text), "path": str(path)}


def fingerprint_todo(path: Path) -> str:
    try: return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc: raise TodoProblem("todo_unreadable", f"TODO 无法读取：{path}") from exc


LOCK_TIMEOUT_SECONDS = 10.0
LOCK_POLL_SECONDS = 0.05


@contextlib.contextmanager
def todo_lock(path: Path, *, timeout: float = LOCK_TIMEOUT_SECONDS):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock.v2")
    deadline = time.monotonic() + max(0., float(timeout))
    acquired = False
    body_error = None
    try:
        while True:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TodoProblem("todo_lock_timeout", f"TODO 写锁等待超时：{path}")
                time.sleep(min(LOCK_POLL_SECONDS, max(deadline-time.monotonic(), 0)))
            except OSError as exc:
                raise TodoProblem("todo_lock_error", f"TODO 写锁不可访问：{path}") from exc
            else:
                acquired = True
                os.close(fd)
                break
        try:
            yield
        except BaseException as exc:
            body_error = exc
            raise
    finally:
        if acquired:
            try: lock_path.unlink()
            except FileNotFoundError: pass
            except OSError as exc:
                if body_error is None:
                    raise TodoProblem("todo_lock_error", f"TODO 写锁无法释放：{path}") from exc


def _write_locked(path: Path, data: bytes, *, create_only: bool = False,
                  expected_fingerprint: str | None = None) -> None:
    current = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if expected_fingerprint is not None and current != expected_fingerprint:
        raise TodoProblem("todo_fingerprint_conflict", "TODO 已被其他写者修改，请重新读取。",
                          {"expected": expected_fingerprint, "actual": current})
    if create_only and path.exists():
        raise TodoProblem("todo_exists", f"TODO 已存在：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        stage.write_bytes(data)
        if create_only:
            try: os.link(stage, path)
            except FileExistsError as exc: raise TodoProblem("todo_exists", f"TODO 已存在：{path}") from exc
        else:
            os.replace(stage, path)
    finally:
        stage.unlink(missing_ok=True)


def write_todo(path: Path, text: str, *, create_only: bool = False,
               expected_fingerprint: str | None = None) -> None:
    parse_todo(text)
    with todo_lock(path):
        _write_locked(Path(path), text.encode("utf-8"), create_only=create_only,
                      expected_fingerprint=expected_fingerprint)



def validate_current_updates(updates: dict[str, Any]) -> dict[str, Any]:
    """Pure validation reused before Notice read/handle and before disk updates."""
    if not updates or set(updates) - set(CURRENT_FIELDS):
        raise TodoProblem("todo_field_unsupported", "只能更新当前合同明确允许的字段。")
    return {key: (_refs(val, key) if key in LIST_CURRENT_FIELDS
                  else _scalar(val, key, required=key in {"objective", "next_action"}))
            for key, val in updates.items()}


def update_todo_current(path: Path, updates: dict[str, Any], *,
                        expected_fingerprint: str | None = None,
                        now: str | None = None, touch_updated_at: bool = True) -> dict[str, Any]:
    """Update Current only. Pinned + task bytes (and their EOL) are untouched."""
    path = Path(path)
    with todo_lock(path):
        raw = path.read_bytes()
        fp = hashlib.sha256(raw).hexdigest()
        if expected_fingerprint and expected_fingerprint != fp:
            raise TodoProblem("todo_fingerprint_conflict", "TODO 已被其他写者修改，请重新读取。",
                              {"expected": expected_fingerprint, "actual": fp})
        original = raw.decode("utf-8")
        parsed = parse_todo(original)
        normalized = dict(parsed["current"])
        normalized.update(validate_current_updates(updates))
        if all(normalized[key] == parsed["current"].get(key) for key in updates):
            return {"changed": False, "fingerprint": fp, "path": str(path),
                    "updated_at": parsed["current"].get("updated_at", "")}
        written_at = None
        if touch_updated_at and "updated_at" not in updates:
            written_at = now or datetime.now(timezone.utc).isoformat()
            normalized["updated_at"] = written_at
        eol = "\r\n" if b"\r\n" in raw else "\n"
        lines = original.splitlines(keepends=True)
        cur_idx = next(i for i, row in enumerate(lines) if row.strip() == "# Current")
        task_idx = next(i for i, row in enumerate(lines) if row.strip() == "# Tasks")
        prefix = "".join(lines[:cur_idx+1])
        suffix = "".join(lines[task_idx:])
        edited = prefix + eol + eol.join(_current_lines(normalized)) + eol*2 + suffix
        parse_todo(edited)
        _write_locked(path, edited.encode("utf-8"), expected_fingerprint=fp)
        return {"changed": True, "fingerprint": hashlib.sha256(edited.encode("utf-8")).hexdigest(),
                "path": str(path), "updated_at": written_at or normalized.get("updated_at", "")}
