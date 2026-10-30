"""compact 摘要域：把结果压缩为 bounded 摘要文本。

从 paos.py 提取；仅依赖 typing 与域内常量。
"""
from typing import Any


COMPACT_MAILBOX_DESCRIPTION_MAX_CHARS = 1200


COMPACT_MAILBOX_RESOLUTION_MAX_CHARS = 600


COMPACT_MAILBOX_IDENTITY_MAX_CHARS = 160


def _bounded_compact_text(value: Any, max_chars: int) -> tuple[str, bool]:
    text = value if isinstance(value, str) else ""
    if len(text) <= max_chars:
        return text, False
    return "", True


def compact_request_ref(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "request_id",
        "request_type",
        "direction",
        "status",
        "bindings",
        "source_session_id",
        "target_session_id",
        "requires_human",
    )
    result = {key: item.get(key) for key in keys if key in item}
    bounded_fields = (
        ("target_identity_id", COMPACT_MAILBOX_IDENTITY_MAX_CHARS),
        ("description", COMPACT_MAILBOX_DESCRIPTION_MAX_CHARS),
        ("resolution", COMPACT_MAILBOX_RESOLUTION_MAX_CHARS),
    )
    for field, max_chars in bounded_fields:
        if field not in item:
            continue
        value, omitted = _bounded_compact_text(item.get(field), max_chars)
        result[field] = value
        if omitted:
            result[f"{field}_omitted"] = True
    return result


def compact_mailbox(
    mailbox: dict[str, Any],
    *,
    limit: int = 6,
) -> dict[str, Any]:
    inbox_all = list(mailbox.get("inbox") or [])
    waiting_all = list(mailbox.get("waiting") or [])
    inbox = [
        compact_request_ref(item)
        for item in inbox_all[:limit]
        if isinstance(item, dict)
    ]
    waiting = [
        compact_request_ref(item)
        for item in waiting_all[:limit]
        if isinstance(item, dict)
    ]
    return {
        "counts": dict(mailbox.get("counts") or {}),
        "inbox": inbox,
        "waiting": waiting,
        "meta": {
            "inbox_omitted": max(0, len(inbox_all) - len(inbox)),
            "waiting_omitted": max(0, len(waiting_all) - len(waiting)),
            "recent_not_included": len(mailbox.get("recent") or []),
        },
    }


def compact_work(work: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(work, dict):
        return None
    keys = (
        "id",
        "title",
        "status",
        "objective",
        "done_when",
        "note",
        "updated_at",
    )
    return {key: work.get(key) for key in keys if key in work}


def compact_action(action: dict[str, Any]) -> dict[str, Any]:
    result = {
        "action_id": action.get("action_id"),
        "method": action.get("method"),
        "path": action.get("path"),
    }
    if action.get("constraints"):
        result["constraints"] = action.get("constraints")
    return result
