"""orient 导览域：工位/库/下一步的定位与展示。

从 paos.py 提取；域内自包含，对外只依赖 paos_library / paos_installation / paos_workstation。
"""
from pathlib import Path
from typing import Any

from paos_library import LibraryProblem, load_library_roots
from paos_installation import resolve_library_roots_path
from paos_workstation import posix_windows_drive_locator


def _orient_source_root(
    installation: dict[str, Any] | None,
    issues: list[dict[str, str]],
) -> str:
    if installation is None:
        return ""
    if not installation.get("configured"):
        issues.append(
            {
                "kind": "source_locator_unregistered",
                "detail": "installation descriptor 未配置；Source locator 留空。",
            }
        )
        return ""
    locator = str(installation.get("source_root") or "")
    runtime_path = Path(posix_windows_drive_locator(locator)).expanduser()
    if not runtime_path.is_dir():
        issues.append(
            {
                "kind": "source_locator_unavailable",
                "detail": f"配置的 Source locator 当前不可验证：{locator}",
            }
        )
        return ""
    return locator


def _orient_library_roots(
    installation: dict[str, Any] | None,
    issues: list[dict[str, str]],
) -> dict[str, str]:
    roots_path = resolve_library_roots_path(installation=installation or {})
    try:
        roots = load_library_roots(roots_path)
    except LibraryProblem as problem:
        issues.append(
            {
                "kind": "library_roots_invalid",
                "code": problem.code,
                "detail": str(problem),
            }
        )
        return {
            "state": "invalid",
            "config_path": str(roots_path),
            "workflow_root": "",
            "skill_root": "",
        }
    if not roots.get("registered"):
        issues.append(
            {
                "kind": "library_roots_unregistered",
                "detail": f"Workflow/Skill Library roots 未登记：{roots_path}",
            }
        )
        return {
            "state": "unregistered",
            "config_path": str(roots_path),
            "workflow_root": "",
            "skill_root": "",
        }
    return {
        "state": "registered",
        "config_path": str(roots_path),
        "workflow_root": str(roots.get("workflow_root") or ""),
        "skill_root": str(roots.get("skill_root") or ""),
    }


def _orient_next_action(
    request_inbox_count: int,
    unhandled_mail_count: int,
    current: dict[str, str],
    open_tasks: list[dict[str, Any]],
    todo_is_coherent: bool,
) -> str:
    """Workless：责任来源只有 Current(next)/TODO open tasks/正式 Request/未处理 Mail；
    不存在 live Work 推导，也不从历史消息推断主线。"""
    if not todo_is_coherent:
        return (
            "TODO 当前区不可用；不从历史推断下一步。"
            "先以正式 Mail/Notice 恢复真实责任再继续。"
        )
    next_text = str(current.get("next") or "").strip()
    if next_text and next_text not in {"无", "-", "none", "without", "none"}:
        return next_text
    if open_tasks:
        return f"处理 TODO 待办 {open_tasks[0].get('id')}：{open_tasks[0].get('title')}"
    if request_inbox_count:
        return (
            "处理正式 PAOS Request inbox（仅与 TODO 主线相关项；"
            "陈旧/无关 Request 记为待收口，不篡位）。"
        )
    if unhandled_mail_count:
        return "可查看未处理 Mail，但不从历史消息推断新的主线。"
    return "当前无未完成责任；保持待机或向 Coordinator 确认新责任。"


def _todo_current_view(todo: dict[str, Any]) -> dict[str, Any]:
    raw = todo.get("current")
    current = dict(raw) if isinstance(raw, dict) else {}
    if todo.get("schema") == "paos-todo/v3":
        current.setdefault("work", current.get("current_work", ""))
        current.setdefault("next", current.get("next_action", ""))
        current.setdefault("results", current.get("results", ""))
        current.setdefault("inflight", current.get("inflight", ""))
    return current


def _todo_open_tasks(todo: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = [
        dict(item)
        for item in (todo.get("tasks") or [])
        if isinstance(item, dict)
    ]
    if todo.get("schema") == "paos-todo/v3":
        result: list[dict[str, Any]] = []
        for item in tasks:
            state = str(item.get("state") or "todo")
            item["done"] = state in {"done", "cancelled"}
            if not item["done"]:
                result.append(item)
        return result
    return [item for item in tasks if not item.get("done")]


def _orient_todo_contract_issues(
    todo: dict[str, Any], project_id: str, agent_id: str
) -> list[str]:
    issues: list[str] = []
    schema = str(todo.get("schema") or "")
    if schema not in {"paos-todo/v2", "paos-todo/v3"}:
        issues.append(
            f"schema 必须为 paos-todo/v2 或 paos-todo/v3，实际为 {schema or '缺失'}"
        )
        return issues

    if str(todo.get("project_id") or "") != project_id:
        issues.append(
            f"project_id 必须为 {project_id}，实际为 {todo.get('project_id') or '缺失'}"
        )

    if schema == "paos-todo/v3":
        if todo.get("home_kind") != "project_agent":
            issues.append(
                f"home_kind 必须为 project_agent，实际为 {todo.get('home_kind') or '缺失'}"
            )
        if str(todo.get("home_id") or "") != agent_id:
            issues.append(
                f"home_id 必须为 {agent_id}，实际为 {todo.get('home_id') or '缺失'}"
            )
        current = todo.get("current")
        if not isinstance(current, dict):
            issues.append("Current 无法解析")
        else:
            for field in ("objective", "next_action"):
                if not str(current.get(field) or "").strip():
                    issues.append(f"Current 缺少有效字段：{field}")
        return issues

    if todo.get("agent_id") != agent_id:
        issues.append(
            f"agent_id 必须为 {agent_id}，实际为 {todo.get('agent_id') or '缺失'}"
        )
    if todo.get("metadata_issues"):
        issues.extend(f"front matter {item}" for item in todo["metadata_issues"])
    if todo.get("missing_sections"):
        issues.append("缺少区段：" + "、".join(todo["missing_sections"]))
    if todo.get("duplicate_sections"):
        issues.append("必需区段重复：" + "、".join(todo["duplicate_sections"]))
    if todo.get("malformed_tasks"):
        issues.append("待办行格式无效：" + "；".join(todo["malformed_tasks"]))

    current = todo.get("current")
    if not isinstance(current, dict):
        issues.append("当前区无法解析")
    else:
        for field in ("objective", "stage", "next"):
            if not str(current.get(field) or "").strip():
                issues.append(f"当前区缺少有效字段：{field}")
    return issues


def render_orient(payload: dict[str, Any]) -> str:
    identity = payload.get("identity") or {}
    work = payload.get("current_work") or {}
    todo = payload.get("todo") or {}
    project = payload.get("project") or {}
    communication = payload.get("communication") or {}
    mail = communication.get("durable_mail") or {}
    requests = communication.get("formal_requests") or {}
    request_counts = (requests.get("counts") or {})
    entry = payload.get("entry") or {}
    lines = [
        f"PAOS orient — {identity.get('agent_id')} @ {identity.get('project_id')}",
        f"Who: {identity.get('agent_id')} ({identity.get('identity_id') or 'unregistered'})"
        + (f" · 员工号 {identity.get('staff_number')}" if identity.get('staff_number') else ""),
        f"Project: {identity.get('project_id')} · {identity.get('project_name') or ''}",
        f"Status: {identity.get('status') or ''}",
        f"Work: {work.get('id') or '（无当前 Work）'} · {work.get('title') or ''}",
        f"ENTRY: {'available' if entry.get('available') else 'missing'} · {entry.get('path') or ''}",
        f"TODO: {'trusted' if todo.get('trusted') else 'untrusted'} · {todo.get('current', {}).get('next') or ''}",
        f"Mail: {mail.get('count', 0)} total / {mail.get('unhandled_count', 0)} unhandled; Request inbox/waiting: {request_counts.get('inbox', 0)}/{request_counts.get('waiting', 0)}",
        f"Source: {project.get('source_root') or '（未登记或不可验证）'}",
        f"Libraries: {project.get('library_roots', {}).get('state', 'unknown')}",
        f"Runtime reachability: {payload.get('runtime_reachability', 'unknown')}",
    ]
    if payload.get("inconsistencies"):
        lines.append("Issues:")
        lines.extend(f"  ! {issue.get('detail')}" for issue in payload["inconsistencies"])
    lines.append(f"Next: {payload.get('next_action') or ''}")
    return "\n".join(lines)
