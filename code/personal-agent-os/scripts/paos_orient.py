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
    unhandled_mail_count: int,
    current: dict[str, str],
    open_tasks: list[dict[str, Any]],
    todo_is_coherent: bool,
) -> str:
    """责任来源只有当前 TODO 与未处理输入；
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
    if unhandled_mail_count:
        return "可查看未处理 Mail，但不从历史消息推断新的主线。"
    return "当前无未完成责任；保持待机或向 Coordinator 确认新责任。"


def _todo_current_view(todo: dict[str, Any]) -> dict[str, Any]:
    current = todo.get("current")
    if not isinstance(current, dict):
        return {}
    return {**current, "next": current.get("next_action", "")}


def _todo_open_tasks(todo: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(t) for t in todo.get("tasks", [])
            if isinstance(t, dict) and t.get("state") not in {"done", "cancelled"}]


def _orient_todo_contract_issues(todo: dict[str, Any], project_id: str, agent_id: str) -> list[str]:
    issues = []
    if todo.get("schema") != "paos-todo/v4":
        return [f"TODO schema 不支持：{todo.get('schema') or '缺失'}；需要 paos-todo/v4"]
    for field, value in (("project_id", project_id), ("home_id", agent_id), ("home_kind", "project_agent")):
        if todo.get(field) != value:
            issues.append(f"{field} 应为 {value}，实际为 {todo.get(field)}")
    current = todo.get("current")
    if not isinstance(current, dict):
        issues.append("Current 无法解析")
    else:
        for key in ("objective", "next_action"):
            if not str(current.get(key) or "").strip():
                issues.append(f"Current 缺少 {key}")
    return issues


def render_orient(payload: dict[str, Any]) -> str:
    identity = payload.get("identity") or {}
    todo = payload.get("todo") or {}
    project = payload.get("project") or {}
    communication = payload.get("communication") or {}
    mail = communication.get("durable_mail") or {}
    entry = payload.get("entry") or {}
    lines = [
        f"PAOS orient — {identity.get('agent_id')} @ {identity.get('project_id')}",
        f"Who: {identity.get('agent_id')} ({identity.get('identity_id') or 'unregistered'})"
        + (f" · 员工号 {identity.get('staff_number')}" if identity.get('staff_number') else ""),
        f"Project: {identity.get('project_id')} · {identity.get('project_name') or ''}",
        f"Status: {identity.get('status') or ''}",
        f"ENTRY: {'available' if entry.get('available') else 'missing'} · {entry.get('path') or ''}",
        f"TODO: {'trusted' if todo.get('trusted') else 'untrusted'} · {todo.get('current', {}).get('next') or ''}",
        f"Mail: {mail.get('count', 0)} total / {mail.get('unhandled_count', 0)} unhandled",
        f"Source: {project.get('source_root') or '（未登记或不可验证）'}",
        f"Libraries: {project.get('library_roots', {}).get('state', 'unknown')}",
        f"Runtime reachability: {payload.get('runtime_reachability', 'unknown')}",
    ]
    if payload.get("inconsistencies"):
        lines.append("Issues:")
        lines.extend(f"  ! {issue.get('detail')}" for issue in payload["inconsistencies"])
    lines.append(f"Next: {payload.get('next_action') or ''}")
    return "\n".join(lines)
