"""Durable Workstation Mail for PAOS V1.1.

This is file-based transport into each Agent's stable Workstation mailbox/.
It is deliberately separate from the existing PAOS "Agent Mailbox" projection,
which remains a read-only view over canonical Request/Assignment responsibility.

Mail is durable communication, not governance authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


MAIL_SCHEMA = "paos-workstation-mail/v1"
DISPATCH_SCHEMA = "paos-workstation-mail-dispatch/v1"
HANDLED_SCHEMA = "paos-workstation-mail-handled/v1"
MAIL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,119}$")
MAX_SUBJECT_CHARS = 240
MAX_BODY_CHARS = 256 * 1024


class MailProblem(RuntimeError):
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


def new_message_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"mail-{stamp}-{uuid.uuid4().hex[:10]}"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_single_line(value: Any, *, label: str, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > max_chars:
        raise MailProblem(
            "mail_field_too_long",
            f"{label} 超过 {max_chars} 字符限制。",
            {"field": label, "max_chars": max_chars},
        )
    return text


def _validate_message_id(value: str) -> str:
    text = str(value or "").strip()
    if not MAIL_ID_RE.fullmatch(text):
        raise MailProblem(
            "mail_message_id_invalid",
            "message_id 必须为 3–120 位字母、数字、点、下划线或短横线。",
            {"message_id": text},
        )
    return text


def _atomic_create(path: Path, text: str) -> bool:
    """Create immutable text once. Return False when it already exists."""
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
            # Fallback for filesystems without hard-link support.
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
        raise MailProblem(
            "mail_write_failed",
            f"无法写入 Mail 文件：{path}",
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
        raise MailProblem(
            "mail_handling_write_failed",
            f"无法更新 Mail handling 记录：{path}",
            {"path": str(path), "os_error": str(exc)},
        ) from exc
    finally:
        staged.unlink(missing_ok=True)


def _project_agent_ids(project: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for session in project.get("sessions", []) or []:
        if not isinstance(session, dict):
            continue
        agent_id = str(session.get("id") or "").strip()
        if agent_id and agent_id not in result:
            result.append(agent_id)
    return result


def _broadcast_agent_ids(project: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for session in project.get("sessions", []) or []:
        if not isinstance(session, dict):
            continue
        if session.get("status") == "historical":
            continue
        agent_id = str(session.get("id") or "").strip()
        if agent_id and agent_id not in result:
            result.append(agent_id)
    return result


def resolve_recipients(
    project: dict[str, Any],
    *,
    recipients: Iterable[str] | None = None,
    broadcast: bool = False,
    registry_lookup: Callable[[str], Any] | None = None,
) -> list[str]:
    requested = list(recipients or [])
    if broadcast and requested:
        raise MailProblem(
            "mail_recipient_mode_conflict",
            "broadcast 与显式 --to 不能同时使用。",
        )
    known = _project_agent_ids(project)
    if broadcast:
        resolved = _broadcast_agent_ids(project)
    else:
        resolved = []
        for value in requested:
            agent_id = str(value or "").strip()
            if agent_id and agent_id not in resolved:
                resolved.append(agent_id)
        unknown = [agent_id for agent_id in resolved if agent_id not in known]
        if unknown and registry_lookup is not None:
            # 统一 S 号/跨 Project 合同：不在被调 Project 名册的 recipient，
            # 若能经安装 registry 解析出真实 Home 就放行（路由由 Home 轴分支
            # 负责投递到对方工位）。真实解析错误（损坏/权限/代码缺陷）按
            # resolve_home_by_registry 原合同直接传播，不静默吞；仅“未登记
            # 该 Home”（attention_recipient_home_not_registered）维持拒绝为
            # unknown 的既有语义。
            registry_lookup_resolved: list[str] = []
            for agent_id in unknown:
                try:
                    registry_lookup(agent_id)
                except Exception as problem:
                    if getattr(problem, "code", None) == "attention_recipient_home_not_registered":
                        continue
                    raise
                registry_lookup_resolved.append(agent_id)
            unknown = [agent_id for agent_id in unknown if agent_id not in set(registry_lookup_resolved)]
        if unknown:
            raise MailProblem(
                "mail_recipient_unknown",
                "存在不属于当前 Project 的 Agent recipient。",
                {"unknown_recipients": unknown},
            )
    if not resolved:
        raise MailProblem(
            "mail_recipient_empty",
            "Mail 至少需要一个明确 recipient。",
        )
    return resolved


def _render_mail(
    *,
    message_id: str,
    project_id: str,
    recipient_id: str,
    created_at: str,
    sender_kind: str,
    sender_id: str,
    subject: str,
    body: str,
    audience: str,
) -> str:
    q = lambda value: json.dumps(str(value), ensure_ascii=False)
    return "\n".join(
        [
            "---",
            f"schema: {MAIL_SCHEMA}",
            f"message_id: {q(message_id)}",
            f"project_id: {q(project_id)}",
            f"recipient_agent_id: {q(recipient_id)}",
            f"created_at: {q(created_at)}",
            f"sender_kind: {q(sender_kind)}",
            f"sender_id: {q(sender_id)}",
            f"audience: {q(audience)}",
            f"subject: {q(subject)}",
            "---",
            "",
            f"# {subject}",
            "",
            body.rstrip(),
            "",
        ]
    )


def _dispatch_path(root: Path, message_id: str) -> Path:
    return root / ".paos" / "mail" / "dispatch" / f"{message_id}.json"


def _mail_path(root: Path, recipient_id: str, message_id: str) -> Path:
    return root / "Workstations" / recipient_id / "mailbox" / f"{message_id}.md"


def _handled_path(root: Path, recipient_id: str, message_id: str) -> Path:
    return (
        root
        / "Workstations"
        / recipient_id
        / "mailbox"
        / ".handled"
        / f"{message_id}.json"
    )


def _load_dispatch(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MailProblem(
            "mail_dispatch_missing",
            f"Mail dispatch 不存在：{path}",
            {"path": str(path)},
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MailProblem(
            "mail_dispatch_invalid",
            f"Mail dispatch 无法读取：{path}",
            {"path": str(path), "cause": str(exc)},
        ) from exc
    if not isinstance(value, dict) or value.get("schema") != DISPATCH_SCHEMA:
        raise MailProblem(
            "mail_dispatch_invalid",
            f"Mail dispatch schema 无效：{path}",
            {"path": str(path)},
        )
    return value


def _assert_dispatch_matches(
    dispatch: dict[str, Any],
    *,
    project_id: str,
    sender_kind: str,
    sender_id: str,
    subject: str,
    body: str,
) -> None:
    expected = {
        "project_id": project_id,
        "sender_kind": sender_kind,
        "sender_id": sender_id,
        "subject": subject,
        "body_sha256": _sha256_text(body),
    }
    mismatches = {
        key: {"existing": dispatch.get(key), "requested": value}
        for key, value in expected.items()
        if dispatch.get(key) != value
    }
    if mismatches:
        raise MailProblem(
            "mail_message_id_conflict",
            "相同 message_id 已用于不同 Mail 内容或 sender；拒绝覆盖。",
            {"message_id": dispatch.get("message_id"), "mismatches": mismatches},
        )


def send_mail(
    *,
    root: Path,
    project: dict[str, Any],
    subject: str,
    body: str,
    recipients: Iterable[str] | None = None,
    broadcast: bool = False,
    sender_kind: str = "human",
    sender_id: str = "",
    message_id: str = "",
    registry_lookup: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Persist a stable dispatch envelope, then deliver immutable MD copies.

    The dispatch envelope freezes the recipient set on first send. Retrying the
    same message_id reuses that snapshot and never silently adds later Agents.
    """
    root = Path(root)
    if not root.is_dir():
        raise MailProblem(
            "mail_project_root_missing",
            f"Project root 不存在：{root}",
            {"root_path": str(root)},
        )
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        raise MailProblem("mail_project_id_missing", "Project 缺少 id。")

    subject = _clean_single_line(subject, label="subject", max_chars=MAX_SUBJECT_CHARS)
    if not subject:
        raise MailProblem("mail_subject_empty", "Mail subject 不能为空。")
    body = str(body or "")
    if len(body) > MAX_BODY_CHARS:
        raise MailProblem(
            "mail_body_too_long",
            f"Mail body 超过 {MAX_BODY_CHARS} 字符限制。",
            {"max_chars": MAX_BODY_CHARS},
        )
    sender_kind = _clean_single_line(
        sender_kind or "human", label="sender_kind", max_chars=40
    )
    sender_id = _clean_single_line(sender_id, label="sender_id", max_chars=120)
    message_id = _validate_message_id(message_id or new_message_id())
    dispatch_path = _dispatch_path(root, message_id)

    if dispatch_path.exists():
        dispatch = _load_dispatch(dispatch_path)
        _assert_dispatch_matches(
            dispatch,
            project_id=project_id,
            sender_kind=sender_kind,
            sender_id=sender_id,
            subject=subject,
            body=body,
        )
        requested_audience = "broadcast" if broadcast else "targeted"
        if dispatch.get("audience") != requested_audience:
            raise MailProblem(
                "mail_message_id_conflict",
                "相同 message_id 的 audience 与本次发送模式不一致。",
                {
                    "message_id": message_id,
                    "existing_audience": dispatch.get("audience"),
                    "requested_audience": requested_audience,
                },
            )
        if not broadcast:
            requested_recipients = resolve_recipients(
                project, recipients=recipients, broadcast=False,
                registry_lookup=registry_lookup,
            )
            if requested_recipients != list(dispatch.get("recipients") or []):
                raise MailProblem(
                    "mail_message_id_conflict",
                    "相同 message_id 的 targeted recipient set 不一致。",
                    {
                        "message_id": message_id,
                        "existing_recipients": list(dispatch.get("recipients") or []),
                        "requested_recipients": requested_recipients,
                    },
                )
        frozen_recipients = [
            str(value)
            for value in (dispatch.get("recipients") or [])
            if isinstance(value, str) and value
        ]
        audience = str(dispatch.get("audience") or "targeted")
        # 幂等重发：envelope 事实以不可变 dispatch 快照为准（created_at/sender 不漂移）；
        # body 已由 _assert_dispatch_matches 以 body_sha256 核对为同一原文。
        sender_kind = str(dispatch.get("sender_kind") or "")
        sender_id = str(dispatch.get("sender_id") or "")
        envelope_created_at = str(dispatch.get("created_at") or "")
    else:
        frozen_recipients = resolve_recipients(
            project, recipients=recipients, broadcast=broadcast,
            registry_lookup=registry_lookup,
        )
        audience = "broadcast" if broadcast else "targeted"
        created_at = utc_now_iso()
        envelope_created_at = created_at
        expected_files: dict[str, dict[str, str]] = {}
        for recipient_id in frozen_recipients:
            rendered = _render_mail(
                message_id=message_id,
                project_id=project_id,
                recipient_id=recipient_id,
                created_at=created_at,
                sender_kind=sender_kind,
                sender_id=sender_id,
                subject=subject,
                body=body,
                audience=audience,
            )
            expected_files[recipient_id] = {
                "relative_path": str(
                    Path("Workstations")
                    / recipient_id
                    / "mailbox"
                    / f"{message_id}.md"
                ),
                "sha256": _sha256_text(rendered),
            }
        dispatch = {
            "schema": DISPATCH_SCHEMA,
            "message_id": message_id,
            "project_id": project_id,
            "created_at": created_at,
            "sender_kind": sender_kind,
            "sender_id": sender_id,
            "audience": audience,
            "subject": subject,
            "body_sha256": _sha256_text(body),
            "recipients": frozen_recipients,
            "expected_files": expected_files,
        }
        dispatch_text = json.dumps(dispatch, ensure_ascii=False, indent=2) + "\n"
        if not _atomic_create(dispatch_path, dispatch_text):
            # A concurrent sender won the same ID. Re-read and verify it.
            dispatch = _load_dispatch(dispatch_path)
            _assert_dispatch_matches(
                dispatch,
                project_id=project_id,
                sender_kind=sender_kind,
                sender_id=sender_id,
                subject=subject,
                body=body,
            )
            frozen_recipients = list(dispatch.get("recipients") or [])
            audience = str(dispatch.get("audience") or audience)

    deliveries: list[dict[str, Any]] = []
    created_at = str(dispatch.get("created_at") or "")
    expected_files = dispatch.get("expected_files") or {}
    for recipient_id in frozen_recipients:
        mailbox = root / "Workstations" / recipient_id / "mailbox"
        destination = _mail_path(root, recipient_id, message_id)
        if not mailbox.is_dir():
            deliveries.append(
                {
                    "recipient_agent_id": recipient_id,
                    "state": "workstation_missing",
                    "path": str(destination),
                }
            )
            continue

        rendered = _render_mail(
            message_id=message_id,
            project_id=project_id,
            recipient_id=recipient_id,
            created_at=created_at,
            sender_kind=sender_kind,
            sender_id=sender_id,
            subject=subject,
            body=body,
            audience=audience,
        )
        expected_sha = str(
            (expected_files.get(recipient_id) or {}).get("sha256")
            or _sha256_text(rendered)
        )
        if destination.exists():
            try:
                existing = destination.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise MailProblem(
                    "mail_delivery_conflict",
                    f"已存在的 Mail 无法读取：{destination}",
                    {"path": str(destination), "cause": str(exc)},
                ) from exc
            if _sha256_text(existing) != expected_sha:
                raise MailProblem(
                    "mail_delivery_conflict",
                    "目标 mailbox 中同 message_id 的文件内容不匹配，拒绝覆盖。",
                    {
                        "recipient_agent_id": recipient_id,
                        "path": str(destination),
                    },
                )
            deliveries.append(
                {
                    "recipient_agent_id": recipient_id,
                    "state": "already_delivered",
                    "path": str(destination),
                }
            )
            continue

        created = _atomic_create(destination, rendered)
        deliveries.append(
            {
                "recipient_agent_id": recipient_id,
                "state": "delivered" if created else "already_delivered",
                "path": str(destination),
            }
        )

    counts: dict[str, int] = {}
    for item in deliveries:
        state = str(item["state"])
        counts[state] = counts.get(state, 0) + 1
    # 正式原 envelope：投递链（含跨 Project 外投）必须携带完整原文字段，
    # 不再以 dispatch 收据裁剪件冒充原信（S010 c783 实测正文丢失根因）。
    return {
        "schema": DISPATCH_SCHEMA,
        "message_id": message_id,
        "project_id": project_id,
        "created_at": str(envelope_created_at),
        "sender_kind": str(sender_kind),
        "sender_id": str(sender_id),
        "audience": audience,
        "subject": subject,
        "body": body,
        "recipients": list(frozen_recipients),
        "dispatch_path": str(dispatch_path),
        "deliveries": deliveries,
        "counts": counts,
    }


def dispatch_status(
    root: Path,
    message_id: str,
    *,
    registry_lookup: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """公共 Mail 状态读面。跨 Project / Rooter 接收者的 durable Mail 不落在
    发送方 root。传 registry_lookup（如 resolve_home_by_registry）时，登记
    Home 即权威：全部接收者按当前登记读，同名源端旧副本不覆盖登记事实
    （原 dispatch 合同 sha256 仍是内容唯一事实，冲突/篡改如实在
    state/conflict 报告）；登记失败如实传播，不猜路径、不静默 fallback、
    无新 store。不传 resolver 则维持 ToolIo 原明确合同（旧路径读面）。"""
    root = Path(root)
    message_id = _validate_message_id(message_id)
    dispatch = _load_dispatch(_dispatch_path(root, message_id))
    states: list[dict[str, Any]] = []
    expected_files = dispatch.get("expected_files") or {}
    resolved_homes: dict[str, dict[str, Any]] | None = None
    if registry_lookup is not None:
        resolved_homes = {
            str(recipient_id): registry_lookup(str(recipient_id))
            for recipient_id in dispatch.get("recipients") or []
        }
    for recipient_id in dispatch.get("recipients") or []:
        if resolved_homes is not None:
            path = (
                Path(str((resolved_homes.get(str(recipient_id)) or {}).get("home_path") or ""))
                / "mailbox"
                / f"{message_id}.md"
            )
        else:
            path = _mail_path(root, str(recipient_id), message_id)
        expected_sha = str(
            (expected_files.get(str(recipient_id)) or {}).get("sha256") or ""
        )
        if not path.is_file():
            state = "missing"
            actual_sha = ""
        else:
            try:
                actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                state = "unreadable"
                actual_sha = ""
            else:
                state = "delivered" if actual_sha == expected_sha else "conflict"
        states.append(
            {
                "recipient_agent_id": str(recipient_id),
                "state": state,
                "path": str(path),
                "sha256": actual_sha,
            }
        )
    return {
        "schema": "paos-workstation-mail-status/v1",
        "message_id": message_id,
        "project_id": dispatch.get("project_id"),
        "subject": dispatch.get("subject"),
        "audience": dispatch.get("audience"),
        "recipients": list(dispatch.get("recipients") or []),
        "deliveries": states,
    }


def expected_mail_sha(root: Path, message_id: str, recipient_id: str) -> str:
    """-existing Mail 合同：per-recipient 原件 sha256（dispatch 唯一事实源）"""
    dispatch = _load_dispatch(_dispatch_path(root, _validate_message_id(message_id)))
    entry = (dispatch.get("expected_files") or {}).get(str(recipient_id)) or {}
    return str(entry.get("sha256") or "")
def parse_mail_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if not sep:
            continue
        raw = value.strip()
        try:
            result[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            result[key.strip()] = raw
    return result


def list_mail(root: Path, agent_id: str) -> dict[str, Any]:
    mailbox = Path(root) / "Workstations" / agent_id / "mailbox"
    if not mailbox.is_dir():
        raise MailProblem(
            "mailbox_missing",
            f"Agent mailbox 不存在：{mailbox}",
            {"agent_id": agent_id, "path": str(mailbox)},
        )
    items: list[dict[str, Any]] = []
    unhandled_count = 0
    for path in sorted(mailbox.glob("*.md"), reverse=True):
        try:
            meta = parse_mail_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            items.append(
                {
                    "filename": path.name,
                    "path": str(path),
                    "error": str(exc),
                    "handled": False,
                    "handling_state": "unhandled",
                }
            )
            unhandled_count += 1
            continue
        declared_message_id = str(meta.get("message_id") or "").strip()
        message_id = declared_message_id or path.stem
        try:
            handling = read_handling(root, agent_id, message_id)
        except MailProblem as problem:
            handling = {
                "handled": False,
                "state": "unhandled",
                "error": {
                    "code": problem.code,
                    "detail": str(problem),
                    "details": problem.details,
                },
            }
        if not handling.get("handled"):
            unhandled_count += 1
        items.append(
            {
                "filename": path.name,
                "path": str(path),
                "message_id": message_id,
                "declared_message_id": declared_message_id,
                "message_id_source": (
                    "frontmatter" if declared_message_id else "filename_fallback"
                ),
                "created_at": meta.get("created_at", ""),
                "sender_kind": meta.get("sender_kind", ""),
                "sender_id": meta.get("sender_id", ""),
                "subject": meta.get("subject", ""),
                "audience": meta.get("audience", ""),
                "handled": bool(handling.get("handled")),
                "handling_state": str(handling.get("state") or "unhandled"),
                "handling_reason": str(handling.get("reason") or ""),
                "handling_error": handling.get("error"),
            }
        )
    return {
        "schema": "paos-workstation-mail-list/v1",
        "agent_id": agent_id,
        "mailbox_path": str(mailbox),
        "count": len(items),
        "unhandled_count": unhandled_count,
        "items": items,
    }


def read_mail(root: Path, agent_id: str, message_id: str) -> dict[str, Any]:
    message_id = _validate_message_id(message_id)
    path = _mail_path(Path(root), agent_id, message_id)
    if not path.is_file():
        raise MailProblem(
            "mail_message_missing",
            f"Mail message 不存在：{path}",
            {"agent_id": agent_id, "message_id": message_id, "path": str(path)},
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise MailProblem(
            "mail_message_unreadable",
            f"Mail message 无法读取：{path}",
            {"path": str(path), "cause": str(exc)},
        ) from exc
    meta = parse_mail_frontmatter(text)
    try:
        handling = read_handling(root, agent_id, message_id)
    except MailProblem as problem:
        handling = {
            "handled": False,
            "state": "unhandled",
            "error": {
                "code": problem.code,
                "detail": str(problem),
                "details": problem.details,
            },
        }
    return {
        "schema": "paos-workstation-mail-read/v1",
        "agent_id": agent_id,
        "message_id": message_id,
        "path": str(path),
        "metadata": meta,
        "markdown": text,
        "handling": handling,
    }


def read_handling(root: Path, agent_id: str, message_id: str) -> dict[str, Any]:
    message_id = _validate_message_id(message_id)
    path = _handled_path(Path(root), agent_id, message_id)
    if not path.is_file():
        return {"handled": False, "state": "unhandled", "reason": ""}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MailProblem(
            "mail_handled_record_invalid",
            f"Mail handled 记录无法读取：{path}",
            {"path": str(path), "cause": str(exc)},
        ) from exc
    if (
        not isinstance(record, dict)
        or record.get("schema") != HANDLED_SCHEMA
        or record.get("message_id") != message_id
        or record.get("state") not in {"handled", "replied", "incorporated"}
    ):
        raise MailProblem(
            "mail_handled_record_invalid",
            f"Mail handled 记录内容无效：{path}",
            {"path": str(path), "message_id": message_id},
        )
    return {
        "handled": True,
        "state": str(record["state"]),
        "reason": str(record.get("reason") or ""),
        "handled_at": str(record.get("handled_at") or ""),
    }


def mark_mail_handled(
    root: Path,
    agent_id: str,
    message_id: str,
    *,
    state: str = "handled",
    reason: str = "",
) -> dict[str, Any]:
    """Record minimal handling metadata without modifying immutable Mail."""
    message_id = _validate_message_id(message_id)
    if state not in {"handled", "replied", "incorporated"}:
        raise MailProblem(
            "mail_handled_state_invalid",
            "handled state 必须是 handled、replied 或 incorporated。",
            {"state": state},
        )
    original = read_mail(root, agent_id, message_id)
    metadata = original.get("metadata") or {}
    prior = original.get("handling") or {}
    if prior.get("error"):
        raise MailProblem(
            str((prior.get("error") or {}).get("code") or "mail_handled_record_invalid"),
            str((prior.get("error") or {}).get("detail") or "Mail handling 记录无效。"),
            {"agent_id": agent_id, "message_id": message_id},
        )
    if metadata.get("recipient_agent_id") != agent_id:
        raise MailProblem(
            "mail_handled_recipient_mismatch",
            "只能标记当前 Agent 收件箱中的 Mail。",
            {"agent_id": agent_id, "message_id": message_id},
        )
    path = _handled_path(Path(root), agent_id, message_id)
    previous = prior or {"handled": False, "state": "unhandled"}
    if previous.get("handled"):
        previous_state = str(previous.get("state") or "")
        if previous_state == state or (
            previous_state in {"replied", "incorporated"} and state == "handled"
        ):
            return {
                "schema": HANDLED_SCHEMA,
                "message_id": message_id,
                "path": str(path),
                "created": False,
                **previous,
            }
        if previous_state != "handled":
            raise MailProblem(
                "mail_handled_transition_conflict",
                "Mail 已进入另一种终态，不能改写处理结果。",
                {"message_id": message_id, "existing_state": previous_state, "requested_state": state},
            )
    record = {
        "schema": HANDLED_SCHEMA,
        "message_id": message_id,
        "state": state,
        "reason": _clean_single_line(reason, label="handled reason", max_chars=240),
        "handled_at": utc_now_iso(),
    }
    encoded = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if previous.get("handled"):
        _atomic_replace(path, encoded)
        created = False
    else:
        created = _atomic_create(path, encoded)
    current = read_handling(root, agent_id, message_id)
    return {
        "schema": HANDLED_SCHEMA,
        "message_id": message_id,
        "path": str(path),
        "created": created,
        **current,
    }
