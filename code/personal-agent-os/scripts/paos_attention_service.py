"""V1.3 narrow application service shared by CLI/HTTP/runtime adapters.

This module composes existing durable Mail/CAT source facts with Home/TODO/
Notice facts.  It deliberately does not perform Runtime Wake; P3 owns
reconciliation from explicit activation intent to native attempts.
"""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from paos_installation import (
    load_installation_descriptor,
    resolve_installation_path,
)
from paos_agent_numbers import load_numbers

from paos_cat_activation import (
    CatActivationProblem,
    persist_cat_agent_message,
    verify_cat_exchange_source,
)
from paos_home import (
    HOME_REF_SCHEMA,
    HomeProblem,
    normalize_home_ref,
    project_agent_home,
    rooter_home,
    todo_path,
)
from paos_mail import (
    MAIL_ID_RE,
    MailProblem,
    dispatch_status,
    expected_mail_sha,
    _sha256_text,
    list_mail,
    parse_mail_frontmatter,
    read_mail,
    send_mail,
    _atomic_create,
    _render_mail,
)
from paos_notice import (
    NoticeProblem,
    activation_candidates,
    create_notice,
    handle_notice,
    input_identity,
    list_notices,
    mark_notice_read,
    organize_notice,
    notice_id_for,
    persist_mail_dispatch_notices,
    read_notice,
    request_notice_activation,
)
from paos_todo_v3 import (
    TodoV3Problem,
    fingerprint_todo_v3,
    parse_todo_v3,
    read_todo_v3,
    render_todo_v3,
    update_todo_v3_current,
    write_todo_v3,
)
from paos_workstation import locator_like, posix_windows_drive_locator
from paos_home import agent_project_id


ATTENTION_SERVICE_SCHEMA = "paos-attention-service/v1"


def _runtime_root(value: str | Path) -> Path:
    return Path(posix_windows_drive_locator(str(value))).expanduser()


def _assert_home_v3(home_ref: dict[str, Any]) -> dict[str, Any]:
    """Home 身份只校验固定工位定位与 paos-todo/v3 schema 标识（frontmatter 级）。

    Current 正文（字段/区段）解析失败不阻断正常 Mail/Notice 读取；
    错误 Current 由 Home 状态视图自身如实呈现（s029 缺换行事故教训）。"""
    ref = normalize_home_ref(home_ref)
    todo_file = todo_path(ref)
    if not todo_file.is_file():
        raise AttentionServiceProblem(
            "attention_home_not_v3",
            "目标 Home 尚未采用 paos-todo/v3（TODO.md 缺失）；拒绝提前写入 V1.3 Notice。",
            {
                "home_kind": ref["home_kind"],
                "home_id": ref["home_id"],
                "todo_path": str(todo_file),
            },
        )
    schema_line = ""
    for raw_line in todo_file.read_bytes()[:4096].splitlines():
        text_line = raw_line.decode("utf-8", "replace").strip()
        if text_line.startswith("schema:"):
            schema_line = text_line.split(":", 1)[1].strip().strip('"')
            break
    if schema_line != "paos-todo/v3":
        raise AttentionServiceProblem(
            "attention_home_not_v3",
            "目标 Home 尚未采用 paos-todo/v3；拒绝提前写入 V1.3 Notice。",
            {
                "home_kind": ref["home_kind"],
                "home_id": ref["home_id"],
                "todo_path": str(todo_file),
                "frontmatter_schema": schema_line or "",
            },
        )
    return ref


def _registry_projects_root(descriptor: dict[str, Any]) -> Path:
    from paos_installation import InstallationProblem, effective_data_root

    try:
        data_root = effective_data_root(descriptor)
    except InstallationProblem as problem:
        raise AttentionServiceProblem(
            problem.code,
            str(problem),
            problem.details,
        ) from problem
    # 真实 ProjectStore 合同：projects_dir = <registry root>/projects，
    # 即 <data_root>/project-registry/projects/<pid>.json。
    root = _runtime_root(data_root) / "project-registry" / "projects"
    if not root.is_dir():
        raise AttentionServiceProblem(
            "attention_projects_registry_missing",
            "登记数据根下没有 Project registry；不创建空 Store。",
            {"path": str(root)},
        )
    return root


def resolve_home_by_registry(agent_id: str, *, installation_file: str | None = None) -> dict[str, Any]:
    """按安装 registry 解析跨 Project 的精确 Home（`<pid>-sxxx` 约定）。

    员工：所属 Project 的 registry JSON → project_agent_home（不改被调 Project）；
    rooter-001：安装描述的 Rooter Home。不猜目录后缀；无精确登记 Home 即报错。
    installation_file：与 CLI `--installation-file` 同一入口的服务参数（env 缺席）。"""
    todo_schema_suffix = ""
    try:
        descriptor = load_installation_descriptor(
            resolve_installation_path(installation_file)
        )
    except Exception as problem:
        raise AttentionServiceProblem(
            "attention_registry_unavailable",
            f"安装 registry 不可用，无法按登记路由 {agent_id}：{problem}",
        ) from problem
    if agent_id == "rooter-001":
        rooter_path = str(descriptor.get("rooter_home") or "").strip()
        if not rooter_path:
            raise AttentionServiceProblem(
                "attention_recipient_home_not_registered",
                "安装描述未登记 Rooter Home。",
                {"recipient": agent_id},
            )
        return rooter_home(home_path=rooter_path, home_id="rooter-001")
    if not agent_id or "-" not in agent_id:
        raise AttentionServiceProblem(
            "attention_recipient_home_not_registered",
            f"接收者 {agent_id} 不是精确登记 Home，拒绝按目录后缀猜。",
            {"recipient": agent_id},
        )
    try:
        project_id = agent_project_id(agent_id)
        # CLI and cross-Project routing read the same registration contract.
        from paos_registry import ProjectRegistry
        project = ProjectRegistry(resolve_installation_path(installation_file)).read(project_id)
    except AttentionServiceProblem:
        raise
    except Exception as problem:
        raise AttentionServiceProblem(
            "attention_recipient_project_not_registered",
            f"接收者 {agent_id} 所属 Project 无法在安装 registry 解析：{problem}",
            {"recipient": agent_id},
        ) from problem
    return project_agent_home(project=project, agent_id=agent_id)


def _deliver_external_mail_copy(
    *,
    home_ref: dict[str, Any],
    project: dict[str, Any],
    envelope: dict[str, Any],
    message_id: str,
    request_activation: bool,
    activation_request_id: str,
) -> dict[str, Any]:
    """Write one immutable mail copy + optional Notice into a resolved Home
    outside the invoked Project（跨 Project 员工或 Rooter）。"""
    home_path = Path(str(home_ref["home_path"]))
    recipient_id = str(home_ref["home_id"])
    target_mailbox = home_path / "mailbox"
    target_mailbox.mkdir(parents=True, exist_ok=True)
    mail_path = target_mailbox / f"{message_id}.md"
    mail_text = _render_mail(
        message_id=message_id,
        project_id=str(project.get("id") or ""),
        recipient_id=recipient_id,
        created_at=str(envelope.get("created_at") or ""),
        sender_kind=str(envelope.get("sender_kind") or ""),
        sender_id=str(envelope.get("sender_id") or ""),
        subject=str(envelope.get("subject") or ""),
        body=str(envelope.get("body") or ""),
        audience=str(envelope.get("audience") or "targeted"),
    )
    # 既有不可变 Mail 合同：复用 paos_mail._atomic_create 一次原子创建；
    # 并发 TOCTOU 不覆写（两个投递同时见到不存在，只有一个 link 实际落盘，
    # 落败者读到既有内容再比对）。同内容同 ID 幂等收束；异内容同 ID 是
    # 真实冲突，直接抛错，不 overwrite 伪装成功。无新锁/框架/fallback。
    mail_created = _atomic_create(mail_path, mail_text)
    mail_state = "delivered"
    if not mail_created:
        existing_text = mail_path.read_text(encoding="utf-8")
        if existing_text != mail_text:
            raise AttentionServiceProblem(
                "attention_external_mail_conflict",
                f"跨 Project Mail 副本 {mail_path.name} 已存在且内容不一致，拒绝覆写。",
                {
                    "message_id": message_id,
                    "recipient": recipient_id,
                    "mail_path": str(mail_path),
                },
            )
        # 同 ID 同内容重放：报告已在该 Home 常驻（不是新投递），无重复 Notice。
        mail_state = "already_delivered"
    notice = create_notice(
        home_path=home_path,
        home_kind=str(home_ref["home_kind"]),
        home_id=recipient_id,
        # 归属按既有 Home/source-status 合同：Notice 属于收件人 Home 自己的
        # 项目身份（跨 Project 时是对方 Project，不是发送方），正式
        # source-status 才能按稳定身份命中；原错误归属 Notice 原件保留。
        project_id=str(home_ref.get("project_id") or ""),
        source_kind="mail",
        source_ref=message_id,
        summary=str(envelope.get("subject") or message_id),
        activation_request_id=activation_request_id if request_activation else "",
    )
    return {
        "recipient": recipient_id,
        "home_kind": str(home_ref["home_kind"]),
        "project_id": str(home_ref.get("project_id") or ""),
        "mail_path": str(mail_path),
        "mail_state": mail_state,
        "notice_id": str(notice.get("notice_id") or ""),
        # Real persisted Notice state for this recipient's Home copy (created or
        # pre-existing on idempotent replay); the CLI read face reports it
        # instead of guessing pending from Mail delivery.
        "notice_state": str(notice.get("state") or ""),
        "created": bool(notice.get("created")),
    }


def _same_project_home(
    home_ref: dict[str, Any],
    project: dict[str, Any],
    root: Path,
) -> bool:
    """True only when the resolved Home is exactly this invoked Project's
    `<root>/Workstations/<agent_id>` fixed workstation. Rooter and cross-
    project Homes must take the registry delivery branch."""
    if str(home_ref.get("home_kind") or "") != "project_agent":
        return False
    agent_id = str(home_ref.get("home_id") or "")
    if agent_id and agent_id != str(home_ref.get("home_id") or ""):
        return False
    for item in project.get("sessions") or []:
        if isinstance(item, dict) and str(item.get("id") or "") == agent_id:
            expected = Path(posix_windows_drive_locator(str(root))).expanduser() / "Workstations" / agent_id
            return Path(str(home_ref.get("home_path") or "")).resolve() == expected.resolve()
    return False


class AttentionServiceProblem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _map_problem(problem: Exception) -> AttentionServiceProblem:
    code = getattr(problem, "code", "attention_service_error")
    details = getattr(problem, "details", {})
    return AttentionServiceProblem(str(code), str(problem), dict(details or {}))


def _stable_initial_activation_request_id(
    *,
    source_kind: str,
    source_ref: str,
    targets: Iterable[str],
) -> str:
    target_text = "\0".join(sorted(str(value) for value in targets))
    digest = hashlib.sha256(
        f"{source_kind}\0{source_ref}\0{target_text}".encode("utf-8")
    ).hexdigest()[:32]
    return f"activation-initial-{digest}"


def new_activation_request_id() -> str:
    return f"activation-{uuid.uuid4().hex}"


def resolve_project_home(
    *,
    project: dict[str, Any],
    agent_id: str,
    root_override: str = "",
    require_existing: bool = True,
    require_todo_v3: bool = True,
) -> dict[str, Any]:
    """定位真实登记 Home。旧 TODO 有效性只属于读/路由合同；TODO 恢复写口
    （todo-write）以当前登记 Home 身份为前置，新载荷的 v3 合同由
    write_home_todo 自行校验，不要求旧文件先完好（恢复死锁收口）。"""
    try:
        home_ref = project_agent_home(
            project=project,
            agent_id=agent_id,
            root_override=root_override,
            require_existing=require_existing,
        )
        return _assert_home_v3(home_ref) if require_todo_v3 else home_ref
    except HomeProblem as problem:
        raise _map_problem(problem) from problem


def resolve_rooter_home(
    *,
    home_path: str | Path,
    home_id: str = "rooter-001",
    require_existing: bool = True,
    require_todo_v3: bool = True,
) -> dict[str, Any]:
    try:
        home_ref = rooter_home(
            home_path=home_path,
            home_id=home_id,
            require_existing=require_existing,
        )
        return _assert_home_v3(home_ref) if require_todo_v3 else home_ref
    except HomeProblem as problem:
        raise _map_problem(problem) from problem



HOME_READ_MODEL_SCHEMA = "paos-home-read/v1"


def _home_read_iso_from_mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OSError, OverflowError, ValueError):
        return None


def _home_read_todo_fingerprint(path: Path) -> str | None:
    try:
        return fingerprint_todo_v3(path)
    except (OSError, ValueError):
        return None


def _home_read_notice_tree(path: Path, *, collect: dict[str, bytes] | None = None, fingerprint_only: bool = False) -> dict[str, Any]:
    directory = Path(path)
    if not directory.is_dir():
        return {
            "available": False,
            "status_basis": "not_registered",
            "path": str(directory),
            "fingerprint_sha256": None,
            "file_count": 0,
            "filesystem_updated_at": None,
            "error": None,
        }
    digest = hashlib.sha256()
    file_count = 0
    latest_mtime: float | None = None
    try:
        # One scandir walk; the tree is fully observed twice (before/after).
        # Directory links are not followed, but the file predicate keeps the
        # original Path.is_file() follow behavior so linked ordinary files in
        # the registered tree remain in scope.
        paths: list[Path] = []
        stack = [directory]
        while stack:
            current = stack.pop()
            with os.scandir(current) as iterator:
                for entry in iterator:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                    elif entry.is_file():
                        paths.append(Path(entry.path))
        ordered = sorted(paths, key=lambda item: item.relative_to(directory).as_posix())

        def read_chunk(chunk: list[Path]) -> list[tuple[bytes, float | None]]:
            result: list[tuple[bytes, float | None]] = []
            for item in chunk:
                raw = item.read_bytes()
                if fingerprint_only:
                    result.append((raw, None))
                    continue
                try:
                    mtime = item.stat().st_mtime
                except OSError:
                    mtime = None
                result.append((raw, mtime))
            return result

        workers = 64
        size = max(1, (len(ordered) + workers - 1) // workers)
        chunks = [ordered[index:index + size] for index in range(0, len(ordered), size)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            observed = [item for part in pool.map(read_chunk, chunks) for item in part]
        for item, (raw, mtime) in zip(ordered, observed):
            relative = item.relative_to(directory).as_posix()
            if collect is not None:
                collect[relative] = raw
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(raw)
            digest.update(b"\0")
            file_count += 1
            if mtime is not None and (latest_mtime is None or mtime > latest_mtime):
                latest_mtime = mtime
    except (OSError, ValueError) as exc:
        return {
            "available": False,
            "status_basis": "read_error",
            "path": str(directory),
            "fingerprint_sha256": None,
            "file_count": file_count,
            "filesystem_updated_at": None,
            "error": type(exc).__name__,
        }
    return {
        "available": True,
        "status_basis": "raw_bytes_tree",
        "path": str(directory),
        "fingerprint_sha256": digest.hexdigest(),
        "file_count": file_count,
        "filesystem_updated_at": (
            datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            if latest_mtime is not None
            else None
        ),
        "error": None,
    }


def _home_read_notice_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "notice_id": item.get("notice_id"),
        "source_kind": item.get("source_kind"),
        "source_ref": item.get("source_ref"),
        "summary": item.get("summary"),
        "state": item.get("state"),
        "read": item.get("read"),
        "read_at": item.get("read_at"),
        "handled": item.get("handled"),
        "handled_at": item.get("handled_at"),
        "activation_request_id": item.get("activation_request_id"),
        "path": item.get("path"),
    }


def _home_read_consistency(
    before_todo: str | None,
    after_todo: str | None,
    before_notices: dict[str, Any],
    after_notices: dict[str, Any],
) -> str:
    if (
        before_todo is not None
        and after_todo is not None
        and before_todo != after_todo
    ):
        return "changed_during_read"
    before_notice_fp = before_notices.get("fingerprint_sha256")
    after_notice_fp = after_notices.get("fingerprint_sha256")
    if (
        before_notice_fp is not None
        and after_notice_fp is not None
        and before_notice_fp != after_notice_fp
    ):
        return "changed_during_read"
    if (
        before_notices.get("status_basis") == "read_error"
        or after_notices.get("status_basis") == "read_error"
    ):
        return "source_fingerprint_unknown"
    if before_todo is None or after_todo is None:
        return "source_fingerprint_unknown"
    return "best_effort_multi_file"


def read_home_state(home_ref: dict[str, Any]) -> dict[str, Any]:
    try:
        ref = normalize_home_ref(home_ref)
        todo_file = todo_path(ref)
        notices_dir = Path(ref["home_path"]) / "notices"
        todo_before = _home_read_todo_fingerprint(todo_file)
        blobs: dict[str, bytes] = {}
        notice_paths: list[Path] = []
        notices_before = _home_read_notice_tree(notices_dir, collect=blobs)
        todo = read_todo_v3(todo_file)
        notices = list_notices(Path(ref["home_path"]), blobs=blobs)
        todo_after = _home_read_todo_fingerprint(todo_file)
        notices_after = _home_read_notice_tree(notices_dir, fingerprint_only=True)
        before_fp = notices_before.get("fingerprint_sha256")
        after_fp = notices_after.get("fingerprint_sha256")
        if before_fp is not None and after_fp is not None and before_fp == after_fp:
            # Unchanged bytes: keep the first observation's complete fields
            # (filesystem timestamp, file count) instead of the lean pass.
            notices_after = notices_before
    except (HomeProblem, TodoV3Problem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem

    current = dict(todo.get("current") or {})
    notice_items = list(notices.get("items") or [])
    read_pending = [
        _home_read_notice_row(item)
        for item in notice_items
        if item.get("state") == "pending" and bool(item.get("read"))
    ]
    unread_pending = [
        _home_read_notice_row(item)
        for item in notice_items
        if item.get("state") == "pending" and not bool(item.get("read"))
    ]
    handled_unread = [
        _home_read_notice_row(item)
        for item in notice_items
        if item.get("state") == "handled" and not bool(item.get("read"))
    ]
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    todo_updated_at = str(current.get("updated_at") or "").strip() or None
    read_model = {
        "schema": HOME_READ_MODEL_SCHEMA,
        "observed_at": observed_at,
        "home": ref,
        "current": current,
        "tasks": list(todo.get("tasks") or []),
        "sources": {
            "todo": {
                "path": str(todo_file),
                "version": str(todo.get("schema") or "unknown"),
                "fingerprint_sha256": todo_after,
                "semantic_updated_at": todo_updated_at,
                "semantic_updated_at_basis": (
                    "current.updated_at" if todo_updated_at else "unknown"
                ),
                "filesystem_updated_at": _home_read_iso_from_mtime(todo_file),
                "available": True,
            },
            "notices": {
                **notices_after,
                "version": "paos-notice/v1",
                "semantic_updated_at": None,
                "semantic_updated_at_basis": "unknown",
            },
        },
        "reachability": {
            "home": "readable",
            "todo": "readable",
            "notices": "readable" if notices_after.get("available") else "missing_or_unreadable",
            "mailbox": "not_read",
        },
        "filter_scope": {
            "home": "exact resolved Home only",
            "todo": "exact Home/TODO.md only",
            "notices": "Home/notices tree; semantic items are Notice files and recognized read/handled/activation/organization sidecars; unknown files are not parsed",
            "mailbox": "not scanned by this read model",
            "history": "not scanned by this read model",
            "project_store": "not scanned by this local read model",
        },
        "consistency": _home_read_consistency(
            todo_before,
            todo_after,
            notices_before,
            notices_after,
        ),
        "recovery": {
            "counts": {
                "unread_pending": len(unread_pending),
                "read_pending": len(read_pending),
                "handled_unread": len(handled_unread),
            },
            "unread_pending": unread_pending,
            "read_pending": read_pending,
            "handled_unread": handled_unread,
        },
    }
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "todo": todo,
        "notices": notices,
        "read_model": read_model,
    }


def list_home_notices(home_ref: dict[str, Any]) -> dict[str, Any]:
    try:
        ref = normalize_home_ref(home_ref)
        notices = list_notices(Path(ref["home_path"]))
    except (HomeProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "notices": notices,
    }


def write_home_todo(
    *,
    home_ref: dict[str, Any],
    text: str,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Validate identity before atomically replacing the Home owner's TODO v3."""
    try:
        ref = normalize_home_ref(home_ref)
        candidate = parse_todo_v3(text)
    except (HomeProblem, TodoV3Problem) as problem:
        raise _map_problem(problem) from problem

    if (
        candidate.get("home_kind") != ref["home_kind"]
        or candidate.get("home_id") != ref["home_id"]
    ):
        raise AttentionServiceProblem(
            "attention_todo_home_mismatch",
            "TODO v3 Home identity 与目标 Home 不一致；原文件未修改。",
            {
                "target_home": ref,
                "todo_home_kind": candidate.get("home_kind"),
                "todo_home_id": candidate.get("home_id"),
            },
        )
    if (
        ref["home_kind"] == "project_agent"
        and candidate.get("project_id") != ref["project_id"]
    ):
        raise AttentionServiceProblem(
            "attention_todo_project_mismatch",
            "TODO v3 project_id 与目标 Home 不一致；原文件未修改。",
            {
                "target_project_id": ref["project_id"],
                "todo_project_id": candidate.get("project_id"),
            },
        )

    # render 契约对等：写进去的文字必须能被同版 render_todo_v3 原样复现。
    # todo-write 接受而渲染器拒绝（超长字段、非列表 result_refs、
    # render 不认识的字段形态）一律在入口拒绝，Home 不产生"收敛不了"的状态。
    c = candidate.get("current") or {}
    try:
        re_rendered = render_todo_v3(
            home_kind=str(candidate.get("home_kind") or ""),
            home_id=str(candidate.get("home_id") or ""),
            project_id=str(candidate.get("project_id") or ""),
            objective=str(c.get("objective") or ""),
            approved_scope=str(c.get("approved_scope") or ""),
            stage=str(c.get("stage") or ""),
            next_action=str(c.get("next_action") or ""),
            waiting=str(c.get("waiting") or ""),
            results=str(c.get("results") or ""),
            result_refs=list(c.get("result_refs") or []),
            context_refs=list(c.get("context_refs") or []),
            legacy_source_ref=str(c.get("legacy_source_ref") or ""),
            inflight=str(c.get("inflight") or ""),
            alignment_ref=str(c.get("alignment_ref") or ""),
            input_version=str(c.get("input_version") or ""),
            delivery=str(c.get("delivery") or ""),
            dependencies=str(c.get("dependencies") or ""),
            continuation_to=str(c.get("continuation_to") or ""),
            boundaries=str(c.get("boundaries") or ""),
            history_ref=str(c.get("history_ref") or ""),
            latest_readback=str(c.get("latest_readback") or ""),
            updated_at=str(c.get("updated_at") or ""),
            tasks=list(candidate.get("tasks") or []),
        )
    except TodoV3Problem as problem:
        raise _map_problem(problem) from problem
    # Full todo-write preserves the caller's exact UTF-8 text/line endings.
    normalized_input = text
    if re_rendered != normalized_input:
        # 语义对等（而非整篇排版相等）：valid Current 的正常编辑不应被字段顺序、
        # 空行或排版噪音挡住。直接比较「输入的解析值」与「同版渲染文本的解析值」
        # ——语义无丢失即通过，原文写入； 有值被渲染器丢掉才是结构漂移，入口拒绝。
        try:
            recaparsed = parse_todo_v3(re_rendered)
        except TodoV3Problem as problem:
            raise _map_problem(problem) from problem
        if candidate.get("home_kind") != recaparsed.get("home_kind") or candidate.get(
            "home_id"
        ) != recaparsed.get("home_id") or candidate.get("project_id") != recaparsed.get(
            "project_id"
        ):
            raise AttentionServiceProblem(
                "attention_todo_write_unrenderable",
                "TODO 身份语义在解析/渲染间不一致（可能字段超限或类型漂移）；原文件未修改。",
                {"todo_path": str(todo_path(ref))},
            )
        # 合同语义比较（不是两个完整 dict 硬相等）：已提供值必须原样保留；省略的
        # 可选字段与显式空/空列表默认值按合同等价（renderer 对已知字段统一补默认
        # 行）；输入里 renderer 无法保留的未知 key 或被转换的类型才是丢失。
        input_current = dict(candidate.get("current") or {})
        recap_current = dict(recaparsed.get("current") or {})
        known_fields = {
            key
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
                "updated_at",
            )
        }
        unknown_input_keys = sorted(set(input_current) - known_fields)
        if unknown_input_keys:
            raise AttentionServiceProblem(
                "attention_todo_write_unrenderable",
                "TODO Current 含渲染器无法保留的未知字段；不会静默丢弃。"
                "请去除该字段或改为已知合同字段；原文件未修改。",
                {"todo_path": str(todo_path(ref)), "unknown_keys": unknown_input_keys},
            )
        for key in sorted(known_fields):
            provided = input_current.get(key, "")
            kept_value = recap_current.get(key, "")
            if provided != kept_value and not (provided in ("", [], None) and kept_value in ("", [], None)):
                raise AttentionServiceProblem(
                    "attention_todo_write_unrenderable",
                    f"TODO Current 字段 {key} 的值在解析/渲染间有丢失；原文件未修改。",
                    {"todo_path": str(todo_path(ref)), "field": key},
                )

        if candidate.get("tasks") != recaparsed.get("tasks"):
            raise AttentionServiceProblem(
                "attention_todo_write_unrenderable",
                "TODO Tasks 在解析/渲染间有丢失；原文件未修改。",
                {"todo_path": str(todo_path(ref))},
            )
        written_sha_tier = "semantic"
    else:
        written_sha_tier = "normalized"

    path = todo_path(ref)
    try:
        # No pre-lock fingerprint read: the guard (if any) is evaluated inside the
        # writer's lock against the caller-supplied expected value.
        write_todo_v3(path, normalized_input, expected_fingerprint=expected_fingerprint)
        todo = read_todo_v3(path)
    except TodoV3Problem as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "todo": todo,
        "written_sha_tier": written_sha_tier,
    }


# Current 字段维护入口：只允许这些既有 paos-todo/v3 Current 字段。
TODO_V3_CURRENT_FIELDS: tuple[str, ...] = (
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
)
TODO_V3_LIST_FIELDS: frozenset[str] = frozenset({"result_refs", "context_refs"})


def update_home_todo_fields(
    *,
    home_ref: dict[str, Any],
    updates: dict[str, Any],
    expected_fingerprint: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Update only the named Current fields of the one real TODO v3.

    Surgically replaces/inserts just the submitted Current field lines in the
    original text; everything else (front matter and any extra metadata, other
    Current lines including tolerated unknown fields, and the whole Task region
    with its comments/layout) is preserved, using the existing writer's newline
    normalization. Reuses the existing
    Home locator, TODO parser (for identity + submitted-value validation via the
    renderer) and the atomic writer. Unknown fields, malformed values, a
    missing/unreadable/bad TODO, or an identity mismatch all fail before any
    write.
    """
    if not updates:
        raise AttentionServiceProblem(
            "attention_todo_update_empty",
            "未提供任何要更新的 Current 字段（用 --set field=value）。",
            {"valid_fields": list(TODO_V3_CURRENT_FIELDS)},
        )
    unknown = sorted(k for k in updates if k not in TODO_V3_CURRENT_FIELDS)
    if unknown:
        raise AttentionServiceProblem(
            "attention_todo_update_unknown_field",
            "存在未知的 Current 字段；拒绝写入。",
            {"unknown_fields": unknown, "valid_fields": list(TODO_V3_CURRENT_FIELDS)},
        )
    try:
        ref = normalize_home_ref(home_ref)
    except HomeProblem as problem:
        raise _map_problem(problem) from problem
    path = todo_path(ref)
    try:
        original_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as problem:
        raise AttentionServiceProblem(
            "attention_todo_update_source_missing",
            "目标 Home 没有可读的 paos-todo/v3；请用现行官方恢复写口 "
            "`paos attention todo-write` 交回完整恢复载荷后再字段维护。",
            {"todo_path": str(path), "reason": "todo_v3_missing"},
        ) from problem
    except (OSError, UnicodeError) as problem:
        raise AttentionServiceProblem(
            "attention_todo_update_source_missing",
            "目标 Home 的 TODO 无法读取；请用现行官方恢复写口 "
            "`paos attention todo-write` 交回完整恢复载荷后再字段维护。",
            {"todo_path": str(path), "reason": type(problem).__name__},
        ) from problem
    try:
        existing = parse_todo_v3(original_text)
    except TodoV3Problem as problem:
        # 坏/旧 TODO 不自动修复、不丢旧内容；明确引导现行官方恢复写口。
        raise AttentionServiceProblem(
            "attention_todo_update_source_invalid",
            "当前 TODO 不是可解析的 paos-todo/v3（旧格式/语法错误）；本入口不自动修复、"
            "不丢旧内容，请用现行官方恢复写口 `paos attention todo-write` 交回完整恢复载荷。",
            {"todo_path": str(path), "reason": str(problem)},
        ) from problem

    if (
        existing.get("home_kind") != ref["home_kind"]
        or existing.get("home_id") != ref["home_id"]
    ):
        raise AttentionServiceProblem(
            "attention_todo_home_mismatch",
            "TODO v3 Home identity 与目标 Home 不一致；原文件未修改。",
            {
                "target_home": ref,
                "todo_home_kind": existing.get("home_kind"),
                "todo_home_id": existing.get("home_id"),
            },
        )
    if (
        ref["home_kind"] == "project_agent"
        and existing.get("project_id") != ref["project_id"]
    ):
        raise AttentionServiceProblem(
            "attention_todo_project_mismatch",
            "TODO v3 project_id 与目标 Home 不一致；原文件未修改。",
            {
                "target_project_id": ref["project_id"],
                "todo_project_id": existing.get("project_id"),
            },
        )

    # 只用现有 renderer 校验“本次提交的字段值”（超长/类型/非法）。未提交的旧
    # 字段不参与校验（否则一个 parser 已接受的长旧值会挡住无关更新）；身份/必填
    # 与整体 Task 由现有 parser 检查（上面 parse + 未触碰 Tasks 区域）。缺
    # objective/next_action 未提交时沿用原值（parse 已保证其存在且合法）。
    base_current = dict(existing.get("current") or {})
    validation: dict[str, Any] = {
        key: ([] if key in TODO_V3_LIST_FIELDS else "")
        for key in TODO_V3_CURRENT_FIELDS
    }
    validation["objective"] = str(base_current.get("objective") or "")
    validation["next_action"] = str(base_current.get("next_action") or "")
    validation.update(updates)
    try:
        render_todo_v3(
            home_kind=str(existing.get("home_kind") or ""),
            home_id=str(existing.get("home_id") or ""),
            project_id=str(existing.get("project_id") or ""),
            objective=str(validation.get("objective") or ""),
            approved_scope=str(validation.get("approved_scope") or ""),
            stage=str(validation.get("stage") or ""),
            next_action=str(validation.get("next_action") or ""),
            waiting=str(validation.get("waiting") or ""),
            results=str(validation.get("results") or ""),
            result_refs=list(validation.get("result_refs") or []),
            context_refs=list(validation.get("context_refs") or []),
            legacy_source_ref=str(validation.get("legacy_source_ref") or ""),
            inflight=str(validation.get("inflight") or ""),
            alignment_ref=str(validation.get("alignment_ref") or ""),
            input_version=str(validation.get("input_version") or ""),
            delivery=str(validation.get("delivery") or ""),
            dependencies=str(validation.get("dependencies") or ""),
            continuation_to=str(validation.get("continuation_to") or ""),
            boundaries=str(validation.get("boundaries") or ""),
            history_ref=str(validation.get("history_ref") or ""),
            latest_readback=str(validation.get("latest_readback") or ""),
            updated_at=str(validation.get("updated_at") or ""),
            tasks=[],
        )
    except TodoV3Problem as problem:
        # 超长/非法值等：明确字段错误、失败不写。
        raise _map_problem(problem) from problem

    if dry_run:
        return {
            "schema": ATTENTION_SERVICE_SCHEMA,
            "home": ref,
            "current": dict(base_current),
            "tasks_count": len(existing.get("tasks") or []),
            "todo_path": str(path),
            "dry_run": True,
        }

    # 统一到公共合法写者：其内部持跨进程锁覆盖 read→validate→modify→replace、
    # 保持原 EOL、无变化不写；服务层不再保留第二份 competing surgical writer。
    try:
        # 公共写者在真实修改时刷新 updated_at；无变化不刷新。
        # 显式提交 updated_at 时保留调用方给定值。
        update_todo_v3_current(path, updates, expected_fingerprint=expected_fingerprint)
        actual = read_todo_v3(path)
    except TodoV3Problem as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "current": dict(actual.get("current") or {}),
        "tasks_count": len(actual.get("tasks") or []),
        "todo_path": str(path),
    }


def read_source_status(
    *,
    home_ref: dict[str, Any],
    source_kind: str,
    source_ref: str,
) -> dict[str, Any]:
    """Read one Notice by stable source identity; no transport/body duplication."""
    try:
        ref = _assert_home_v3(home_ref)
        identity = input_identity(
            home_kind=ref["home_kind"],
            home_id=ref["home_id"],
            project_id=ref["project_id"],
            source_kind=source_kind,
            source_ref=source_ref,
        )
        item = read_notice(
            Path(ref["home_path"]),
            notice_id_for(identity),
        )
    except (HomeProblem, TodoV3Problem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "notice": item,
    }


def register_direct_input(
    *,
    home_ref: dict[str, Any],
    source_ref: str,
    summary: str,
    request_activation: bool,
    activation_request_id: str = "",
) -> dict[str, Any]:
    """Register one caller-owned durable carrier by its existing locator.

    For source_kind=direct, source_ref is the body locator. PAOS stores it as
    input identity and never copies or dereferences the body here. To keep the
    Runtime prompt actionable across restarts, direct sources must use an
    explicit absolute path/UNC path or http(s) URL. Opaque ids must be resolved
    by the caller to their durable carrier before registration.
    """
    ref = _assert_home_v3(home_ref)
    source_ref = str(source_ref or "").strip()
    if not locator_like(source_ref):
        raise AttentionServiceProblem(
            "attention_direct_source_ref_invalid",
            (
                "direct source_ref 必须是已有 durable carrier 的绝对路径、UNC "
                "或 http(s) URL；PAOS 不根据 opaque id 猜正文位置。"
            ),
            {
                "source_ref": source_ref,
                "home_kind": ref["home_kind"],
                "home_id": ref["home_id"],
            },
        )
    request_id = activation_request_id.strip()
    if request_activation and not request_id:
        request_id = _stable_initial_activation_request_id(
            source_kind="direct",
            source_ref=source_ref,
            targets=[ref["home_id"]],
        )
    return register_source_input(
        home_ref=ref,
        source_kind="direct",
        source_ref=source_ref,
        summary=summary,
        request_activation=request_activation,
        activation_request_id=request_id,
    )
def _resolve_target_project_agent_home(
    *,
    project: dict[str, Any],
    agent_id: str,
    root_override: str,
    target_project_lookup: Callable[[str], dict[str, Any]] | None,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Resolved Home: invoked-project member first (unchanged strict path);
    on `home_agent_unknown` with a lookup available, resolve the target's OWN
    registered project (deterministic `<pid>-sxxx` convention — never a
    guess) and verify THAT exact Home exists.

    Lookup contract: the callable must already have verified that the target
    Agent is a registered member of that project and that the registered
    Home actually exists (the CLI/HTTP lookups both do); paos-todo/v3
    enforcement happens here via `_assert_home_v3`.  Returns the target
    project dict.  Returns (project, home_ref, cross)."""
    try:
        home_ref = _assert_home_v3(
            project_agent_home(
                project=project,
                agent_id=agent_id,
                root_override=root_override,
            )
        )
    except HomeProblem as direct:
        if direct.code != "home_agent_unknown" or target_project_lookup is None:
            raise direct
        target_project = target_project_lookup(agent_project_id(agent_id))
        home_ref = _assert_home_v3(
            project_agent_home(
                project=target_project,
                agent_id=agent_id,
            )
        )
        return target_project, home_ref, True
    return project, home_ref, False


def send_cat_source(
    *,
    root: Path,
    project: dict[str, Any],
    cat_base: str,
    room_id: str,
    target_agent_id: str,
    content: str,
    sender_agent_id: str = "",
    message_id: str = "",
    reply_to: str = "",
    request_activation: bool = True,
    target_project_lookup: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist verified CAT Exchange, then project it into one exact V1.3 Home."""
    root = _runtime_root(root)
    try:
        resolved_project, home_ref, cross_project = _resolve_target_project_agent_home(
            project=project,
            agent_id=target_agent_id,
            root_override=str(root),
            target_project_lookup=target_project_lookup,
        )
    except HomeProblem as problem:
        # Preserve the stable error code across CLI and HTTP callers
        # (home_agent_unknown / home_missing / home_* mismatch) instead of a
        # generic 500 on the HTTP path.
        raise _map_problem(problem) from problem
    try:
        persisted = persist_cat_agent_message(
            project_id=str(project.get("id") or ""),
            cat_base=cat_base,
            room_id=room_id,
            target_agent_id=target_agent_id,
            content=content,
            sender_agent_id=sender_agent_id,
            message_id=message_id,
            reply_to=reply_to,
            # Receiver exact Home already verified above (strict or cross
            # branch).  Approved contract §5.3: Room Project association is
            # business navigation, not ownership — the binding never gates a
            # verified exact-Home delivery, in either direction.
            allow_binding_navigation=True,
        )
        request_id = ""
        if request_activation:
            request_id = _stable_initial_activation_request_id(
                source_kind="cat",
                source_ref=str(persisted["source_ref"]),
                targets=[target_agent_id],
            )
        registered = register_source_input(
            home_ref=home_ref,
            source_kind="cat",
            source_ref=str(persisted["source_ref"]),
            summary=str(persisted["summary"]),
            request_activation=request_activation,
            activation_request_id=request_id,
        )
    except (CatActivationProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    output = {
        "schema": "paos-attention-cat-send/v1",
        "cat": persisted,
        "home": home_ref,
        "notice": registered["notice"],
        "activation_request_id": registered["activation_request_id"],
        "transport_state": persisted["transport_state"],
        "acknowledged": bool(persisted["acknowledged"]),
        "runtime_wake_performed": False,
    }
    if cross_project:
        output["cross_project"] = {
            "target_project_id": resolved_project.get("id"),
            "receiver_home": home_ref,
            "room_binding": persisted.get("project_binding"),
        }
    return output


def request_cat_activation(
    *,
    root: Path,
    project: dict[str, Any],
    cat_base: str,
    room_id: str,
    exchange_id: str,
    expected_agent_id: str = "",
    activation_request_id: str = "",
) -> dict[str, Any]:
    """Verify one durable CAT source, then request Notice activation only."""
    root = _runtime_root(root)
    project_id = str(project.get("id") or "").strip()
    try:
        verified = verify_cat_exchange_source(
            project_id=project_id,
            cat_base=cat_base,
            room_id=room_id,
            exchange_id=exchange_id,
            expected_agent_id=expected_agent_id,
        )
        target_agent = str(verified.get("agent_id") or "")
        home_ref = _assert_home_v3(
            project_agent_home(
                project=project,
                agent_id=target_agent,
                root_override=str(root),
            )
        )
        request_id = activation_request_id.strip() or new_activation_request_id()
        registered = register_source_input(
            home_ref=home_ref,
            source_kind="cat",
            source_ref=str(verified["source_ref"]),
            summary=str(verified["summary"]),
            request_activation=True,
            activation_request_id=request_id,
        )
    except (CatActivationProblem, HomeProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": "paos-attention-cat-activation-request/v1",
        "project_id": project_id,
        "home": home_ref,
        "source_kind": "cat",
        "source_ref": verified["source_ref"],
        "transport_state": verified["state"],
        "acknowledged": bool(verified["acknowledged"]),
        "notice": registered["notice"],
        "activation_request_id": request_id,
        "runtime_wake_performed": False,
        "notice_handled_inferred_from_cat_ack": False,
    }

def _mail_item_source_ref(item: dict[str, Any]) -> str:
    declared = str(item.get("declared_message_id") or "").strip()
    if declared and MAIL_ID_RE.fullmatch(declared):
        return declared
    filename = str(item.get("filename") or "").strip()
    if not filename:
        raise AttentionServiceProblem(
            "attention_mail_source_unmapped",
            "Mail 条目缺少可用于稳定 alias 的 filename。",
            {"item": item},
        )
    return f"legacy-mail-file:{filename}"


def _find_mail_item(
    *,
    root: Path,
    agent_id: str,
    lookup: str,
) -> dict[str, Any]:
    listing = list_mail(root, agent_id)
    lookup = str(lookup or "").strip()
    for item in listing.get("items") or []:
        if not isinstance(item, dict):
            continue
        candidates = {
            str(item.get("message_id") or ""),
            str(item.get("declared_message_id") or ""),
            Path(str(item.get("filename") or "")).stem,
            _mail_item_source_ref(item),
        }
        if lookup in candidates:
            return item
    raise AttentionServiceProblem(
        "attention_mail_missing",
        "目标 Mail 不在该 Home mailbox 中。",
        {"agent_id": agent_id, "lookup": lookup},
    )


def _read_mail_item_file(item: dict[str, Any], *, agent_id: str) -> dict[str, Any]:
    path = Path(str(item.get("path") or ""))
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AttentionServiceProblem(
            "attention_mail_unreadable",
            f"Mail 原件无法读取：{path}",
            {"agent_id": agent_id, "path": str(path)},
        ) from exc
    meta = parse_mail_frontmatter(text)
    recipient = str(meta.get("recipient_agent_id") or "").strip()
    if recipient and recipient != agent_id:
        raise AttentionServiceProblem(
            "attention_mail_recipient_mismatch",
            "Mail frontmatter recipient 与目标 Home 不一致。",
            {
                "agent_id": agent_id,
                "recipient_agent_id": recipient,
                "path": str(path),
            },
        )
    return {
        "schema": "paos-workstation-mail-read/v1",
        "agent_id": agent_id,
        "message_id": str(item.get("message_id") or path.stem),
        "path": str(path),
        "metadata": meta,
        "markdown": text,
    }

def _mail_notice_id(
    *,
    home_ref: dict[str, Any],
    source_ref: str,
) -> str:
    ref = normalize_home_ref(home_ref)
    return notice_id_for(
        input_identity(
            home_kind=ref["home_kind"],
            home_id=ref["home_id"],
            project_id=ref["project_id"],
            source_kind="mail",
            source_ref=source_ref,
        )
    )


def organize_input(
    *,
    home_ref: dict[str, Any],
    notice_id: str,
    summary: str | None = None,
    sort_order: int | None = None,
    archived: bool | None = None,
    operation_id: str = "",
) -> dict[str, Any]:
    """Edit Notice presentation metadata without changing handling or activation."""
    try:
        ref = _assert_home_v3(home_ref)
        item = organize_notice(
            home_path=Path(ref["home_path"]),
            notice_id=notice_id,
            summary=summary,
            sort_order=sort_order,
            archived=archived,
            operation_id=operation_id,
        )
    except (HomeProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "notice": item,
    }


def mark_input_read(
    *,
    home_ref: dict[str, Any],
    notice_id: str,
) -> dict[str, Any]:
    """Explicitly mark one Notice read using the exact owning Home identity."""
    try:
        ref = normalize_home_ref(home_ref)
        item = mark_notice_read(
            home_path=Path(ref["home_path"]),
            notice_id=notice_id,
            reader_home_kind=ref["home_kind"],
            reader_home_id=ref["home_id"],
            reader_project_id=ref["project_id"],
        )
    except (HomeProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "notice": item,
    }


def handle_input(
    *,
    home_ref: dict[str, Any],
    notice_id: str,
    resolution: str = "",
    action_ref: str = "",
) -> dict[str, Any]:
    try:
        ref = normalize_home_ref(home_ref)
        handled = handle_notice(
            home_path=Path(ref["home_path"]),
            notice_id=notice_id,
            resolution=resolution,
            action_ref=action_ref,
        )
    except (HomeProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "notice": handled,
    }


def handle_mail_input(
    *,
    root: Path,
    project: dict[str, Any],
    agent_id: str,
    message_id: str,
    resolution: str = "",
    action_ref: str = "",
) -> dict[str, Any]:
    """Handle one mapped Mail source through Notice only.

    message_id remains the CLI lookup token. Historical plain Markdown may
    use its filename stem for lookup while Notice keeps the explicit
    legacy-mail-file:<filename> source identity recorded by migration.
    """
    root = _runtime_root(root)
    try:
        ref = _assert_home_v3(
            project_agent_home(
                project=project,
                agent_id=agent_id,
                root_override=str(root),
            )
        )
        mail_item = _find_mail_item(root=root, agent_id=agent_id, lookup=message_id)
        source_ref = _mail_item_source_ref(mail_item)
        notice_id = _mail_notice_id(home_ref=ref, source_ref=source_ref)
        existing = read_notice(Path(ref["home_path"]), notice_id)
        _read_mail_item_file(mail_item, agent_id=agent_id)
    except (HomeProblem, MailProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    if existing.get("source_kind") != "mail" or existing.get("source_ref") != source_ref:
        raise AttentionServiceProblem(
            "attention_mail_notice_mismatch",
            "Mail source 与 Notice identity 不一致。",
            {
                "agent_id": agent_id,
                "message_id": message_id,
                "source_ref": source_ref,
            },
        )
    return handle_input(
        home_ref=ref,
        notice_id=notice_id,
        resolution=resolution,
        action_ref=action_ref,
    )

def read_project_mail_input(
    *,
    root: Path,
    project: dict[str, Any],
    agent_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Read immutable Mail body plus unified Notice handling projection."""
    root = _runtime_root(root)
    try:
        ref = _assert_home_v3(
            project_agent_home(
                project=project,
                agent_id=agent_id,
                root_override=str(root),
            )
        )
        mail_item = _find_mail_item(root=root, agent_id=agent_id, lookup=message_id)
        source_ref = _mail_item_source_ref(mail_item)
        mail = _read_mail_item_file(mail_item, agent_id=agent_id)
        notice_id = _mail_notice_id(home_ref=ref, source_ref=source_ref)
        item = read_notice(Path(ref["home_path"]), notice_id)
    except (HomeProblem, MailProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    mail["handling"] = {
        "handled": item.get("state") == "handled",
        "state": str(item.get("state") or "pending"),
        "reason": str(item.get("resolution") or ""),
        "handled_at": str(item.get("handled_at") or ""),
        "action_ref": str(item.get("action_ref") or ""),
        "notice_id": notice_id,
        "source": "notice",
        "source_ref": source_ref,
    }
    return {
        "schema": "paos-mail-attention-read/v1",
        "home": ref,
        "mail": mail,
        "notice": item,
    }

def list_project_mail_inputs(
    *,
    root: Path,
    project: dict[str, Any],
    agent_id: str,
) -> dict[str, Any]:
    """List Mail metadata with Notice as the only V1.3 handling authority.

    A truly unmapped legacy file remains visible as a derived unmapped row;
    that is not a second persisted handling state and must not be auto-handled.
    """
    root = _runtime_root(root)
    try:
        ref = _assert_home_v3(
            project_agent_home(
                project=project,
                agent_id=agent_id,
                root_override=str(root),
            )
        )
        mail = list_mail(root, agent_id)
        notices = list_notices(Path(ref["home_path"]))
    except (HomeProblem, MailProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    by_source = {
        (str(item.get("source_kind") or ""), str(item.get("source_ref") or "")): item
        for item in notices.get("items") or []
    }
    items: list[dict[str, Any]] = []
    pending_count = 0
    unmapped_count = 0
    for item in mail.get("items") or []:
        if not isinstance(item, dict):
            continue
        projected = dict(item)
        try:
            source_ref = _mail_item_source_ref(item)
        except AttentionServiceProblem as problem:
            projected["input_state"] = "unmapped"
            projected["mapping_error"] = problem.code
            projected["recovery"] = (
                "保留原件；通过转换 manifest 修复稳定 source mapping 后再处理。"
            )
            items.append(projected)
            unmapped_count += 1
            continue
        notice = by_source.get(("mail", source_ref))
        projected.pop("handled", None)
        projected.pop("handling_state", None)
        projected.pop("handling_reason", None)
        projected.pop("handling_error", None)
        projected["source_ref"] = source_ref
        if notice is None:
            projected["notice_id"] = ""
            projected["input_state"] = "unmapped"
            projected["resolution"] = ""
            projected["action_ref"] = ""
            projected["mapping_error"] = "attention_notice_missing_for_mail"
            projected["recovery"] = (
                "原件仍在 mailbox；按同一 migration manifest 补 Notice mapping，"
                "不得回退 legacy .handled 作为第二权威。"
            )
            items.append(projected)
            unmapped_count += 1
            continue
        if notice.get("state") == "pending":
            pending_count += 1
        projected["notice_id"] = notice.get("notice_id")
        projected["input_state"] = notice.get("state")
        projected["resolution"] = notice.get("resolution")
        projected["action_ref"] = notice.get("action_ref")
        items.append(projected)
    return {
        "schema": "paos-mail-attention-list/v1",
        "home": ref,
        "count": len(items),
        "pending_count": pending_count,
        "unmapped_count": unmapped_count,
        "unresolved_count": pending_count + unmapped_count,
        "items": items,
    }

def send_mail_source(
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
    request_activation: bool,
) -> dict[str, Any]:
    """Persist Mail, then Notice; optionally persist one activation intent.

    No Runtime wake occurs here.  P3 consumes the explicit activation intent.
    Retrying the same Mail message_id reuses immutable Mail and the same initial
    activation request identity.
    """
    root = _runtime_root(root)
    try:
        persisted = send_mail(
            root=root,
            project=project,
            subject=subject,
            body=body,
            recipients=recipients,
            broadcast=broadcast,
            sender_kind=sender_kind,
            sender_id=sender_id,
            message_id=message_id,
            registry_lookup=resolve_home_by_registry,
        )
        request_id = ""
        if request_activation:
            request_id = _stable_initial_activation_request_id(
                source_kind="mail",
                source_ref=str(persisted["message_id"]),
                targets=persisted.get("recipients") or [],
            )
        recipient_homes: dict[str, dict[str, Any]] = {}
        external_routes: list[dict[str, Any]] = []
        for agent_id in persisted.get("recipients") or []:
            agent_text = str(agent_id or "").strip()
            if not agent_text:
                continue
            try:
                home_ref = project_agent_home(
                    project=project,
                    agent_id=agent_text,
                    root_override=str(root),
                    require_existing=True,
                )
            except HomeProblem:
                home_ref = resolve_home_by_registry(agent_text)
            recipient_homes[agent_text] = _assert_home_v3(home_ref)
            if not _same_project_home(home_ref, project, root):
                external_routes.append(
                    _deliver_external_mail_copy(
                        home_ref=home_ref,
                        project=project,
                        envelope=persisted,
                        message_id=str(persisted.get("message_id") or ""),
                        request_activation=request_activation,
                        activation_request_id=request_id,
                    )
                )
        projected = persist_mail_dispatch_notices(
            root=root,
            dispatch={
                **persisted,
                "project_id": str(project.get("id") or ""),
            },
            recipient_homes=recipient_homes,
            request_activation=request_activation,
            activation_request_id=request_id,
            restrict_targets=[
                key
                for key, ref in recipient_homes.items()
                if str(ref.get("home_kind") or "") == "project_agent"
            ],
        )
        routes_by_agent = {
            str(route.get("recipient") or ""): route
            for route in external_routes
            if isinstance(route, dict)
        }
        # 外投回执回到同一 Mail 视图（仅返回面投影；immutable dispatch 不改写）:
        # 送达事实以本服务真实写入的 Home 副本为准，替换原按发送方 root 的
        # `workstation_missing` 行；notices 保持 paos-mail-notice-projection/v1
        # 的 dict schema（items/skipped/meta 正常），外投明细放 external_routes。
        mail_view = persisted
        if external_routes:
            merged: list[dict[str, Any]] = []
            for delivery in list(persisted.get("deliveries") or []):
                if not isinstance(delivery, dict):
                    merged.append(delivery)
                    continue
                agent_text = str(delivery.get("recipient_agent_id") or "")
                route = routes_by_agent.get(agent_text)
                if route is None:
                    merged.append(delivery)
                    continue
                merged.append(
                    {
                        "recipient_agent_id": agent_text,
                        "state": str(route.get("mail_state") or "delivered"),
                        "path": str(route.get("mail_path") or ""),
                    }
                )
            counts: dict[str, int] = {}
            for delivery in merged:
                state = str(delivery.get("state") or "unknown")
                counts[state] = counts.get(state, 0) + 1
            mail_view = {**persisted, "deliveries": merged, "counts": counts}
            skipped_view = [
                (
                    # skipped 同对象不再与 external_routes 自相矛盾：外投已由
                    # 真实 Home 副本承载（delivery_state 反映该外投事实）。
                    {**entry, "delivery_state": str(routes_by_agent[entry.get("agent_id")].get("mail_state")), "via": "external_route"}
                    if isinstance(entry, dict) and entry.get("agent_id") in routes_by_agent
                    else entry
                )
                for entry in projected.get("skipped") or []
            ]
            projected = {
                **projected,
                "skipped": skipped_view,
                "external_routes": [
                    route for route in external_routes if route
                ],
            }
    except (MailProblem, NoticeProblem, HomeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": "paos-attention-mail-send/v1",
        "mail": mail_view,
        "notices": projected,
        "activation_request_id": request_id,
        "runtime_wake_performed": False,
    }


def request_mail_activation(
    *,
    root: Path,
    project: dict[str, Any],
    message_id: str,
    agents: Iterable[str] | None = None,
    activation_request_id: str = "",
) -> dict[str, Any]:
    """Persist one activation intent for an existing durable Mail source (durable only; target Runtime wakes via an independent legitimate caller trigger)."""
    root = _runtime_root(root)
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        raise AttentionServiceProblem(
            "attention_project_id_missing",
            "Project 缺少 id。",
        )
    try:
        status = dispatch_status(root, message_id)
    except MailProblem as problem:
        raise _map_problem(problem) from problem
    if str(status.get("project_id") or "") != project_id:
        raise AttentionServiceProblem(
            "attention_source_project_mismatch",
            "Mail dispatch 不属于当前 Project。",
            {
                "project_id": project_id,
                "source_project_id": status.get("project_id"),
                "message_id": message_id,
            },
        )
    frozen = [str(value) for value in status.get("recipients") or []]
    requested = [str(value) for value in agents or [] if str(value)]
    selected = frozen if not requested else [value for value in frozen if value in set(requested)]
    unknown = [value for value in requested if value not in frozen]
    if unknown:
        raise AttentionServiceProblem(
            "attention_recipient_not_in_source",
            "指定 Home 不属于该 Mail 的冻结接收集合。",
            {"unknown_agents": unknown, "frozen_recipients": frozen},
        )
    request_id = activation_request_id.strip() or new_activation_request_id()
    # 冻结 recipients 仍按 immutable dispatch（原 dispatch 内容不变，读取作用面
    # 不受影响）；投递事实与 Notice 身份改沿真实收件 Home 层做，避免发送方
    # root 的 dispatch 投递投影误挡跨 Project 正常读取与 notify 同根：
    #   - 送达事实读收件 Home durable Mail（缺失/不可操作未按原 dispatch 误报）；
    #   - Notice 身份 isomorphic 于 send 正式 source-status（home_kind/home_id/
    #     project_id 按实际收件 Home，跨 Project 是收件方自己的 Project）。
    same_session_ids = {
        str((item or {}).get("id") or "")
        for item in project.get("sessions") or []
    }
    results: list[dict[str, Any]] = []
    subject = str(status.get("subject") or message_id)
    if not activation_request_id.strip():
        # 与 send --request-activation 的初始意图同 derivation（frozen 全集），
        # 同 mail notify 复用同一 activation_request_id，不派生新随机值。
        request_id = _stable_initial_activation_request_id(
            source_kind="mail",
            source_ref=message_id,
            targets=frozen,
        )
    for agent_id in selected:
        if agent_id in same_session_ids:
            try:
                ref = _assert_home_v3(
                    project_agent_home(
                        project=project,
                        agent_id=agent_id,
                        root_override=str(root),
                    )
                )
            except HomeProblem as problem:
                raise _map_problem(problem) from problem
        else:
            try:
                ref = _assert_home_v3(resolve_home_by_registry(agent_id))
            except (HomeProblem, AttentionServiceProblem) as problem:
                raise AttentionServiceProblem(
                    "attention_recipient_home_unresolved",
                    f"接收者 Home 无法按安装 registry 解析：{agent_id}",
                    {"agent_id": agent_id, "cause": str(problem)},
                ) from problem
        home_path = Path(str(ref["home_path"]))
        mail_path = home_path / "mailbox" / f"{message_id}.md"
        if not mail_path.is_file():
            results.append(
                {
                    "agent_id": agent_id,
                    "state": "blocked_source_not_delivered",
                    "delivery_state": "missing",
                }
            )
            continue
        try:
            mail_text = mail_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as problem:
            raise AttentionServiceProblem(
                "attention_source_mail_unreadable",
                f"收件 Home durable Mail 无法读取：{mail_path}",
                {"agent_id": agent_id, "message_id": message_id, "path": str(mail_path)},
            ) from problem
        meta = parse_mail_frontmatter(mail_text)
        if (
            str(meta.get("message_id") or "") != message_id
            or str(meta.get("recipient_agent_id") or "") != agent_id
        ):
            raise AttentionServiceProblem(
                "attention_source_mail_mismatch",
                "收件 Home durable Mail 与 message_id/recipient 不一致，拒绝登记激活 intent。",
                {
                    "agent_id": agent_id,
                    "message_id": message_id,
                    "mail_path": str(mail_path),
                },
            )
        # 内容级核验沿既有 Mail 合同（dispatch expected sha 唯一事实，二 ID 不足以证原件）：不一致=源被改，诚实拒绝。
        actual_sha = _sha256_text(mail_text)
        expected_sha = expected_mail_sha(root, message_id, agent_id)
        if expected_sha and actual_sha != expected_sha:
            raise AttentionServiceProblem(
                "attention_source_mail_content_conflict",
                "收件 Home durable Mail 正文与原 dispatch 不一致（内容被改），已拒绝。",
                {
                    "agent_id": agent_id,
                    "message_id": message_id,
                    "mail_path": str(mail_path),
                    "actual_sha256": actual_sha,
                    "expected_sha256": expected_sha,
                },
            )
        try:
            home_kind = str(ref.get("home_kind") or "project_agent")
            home_id = str(ref.get("home_id") or agent_id)
            ref_project_id = str(ref.get("project_id") or "")
            identity = input_identity(
                home_kind=home_kind,
                home_id=home_id,
                project_id=ref_project_id,
                source_kind="mail",
                source_ref=message_id,
            )
            nid = notice_id_for(identity)
            try:
                read_notice(home_path, nid)
            except NoticeProblem as problem:
                if problem.code != "notice_missing":
                    raise
                create_notice(
                    home_path=home_path,
                    home_kind=home_kind,
                    home_id=home_id,
                    project_id=ref_project_id,
                    source_kind="mail",
                    source_ref=message_id,
                    summary=subject,
                )
            requested_notice = request_notice_activation(
                home_path=home_path,
                notice_id=nid,
                activation_request_id=request_id,
            )
        except (HomeProblem, NoticeProblem) as problem:
            raise _map_problem(problem) from problem
        results.append(
            {
                "agent_id": agent_id,
                "home_kind": home_kind,
                "home_id": home_id,
                "home_project_id": ref_project_id,
                "state": "activation_requested",
                "notice_id": requested_notice.get("notice_id"),
                "activation_request_id": request_id,
            }
        )
    return {
        "schema": "paos-attention-activation-request/v1",
        "project_id": project_id,
        "source_kind": "mail",
        "source_ref": message_id,
        "activation_request_id": request_id,
        "results": results,
        "runtime_wake_performed": False,
    }


def register_source_input(
    *,
    home_ref: dict[str, Any],
    source_kind: str,
    source_ref: str,
    summary: str,
    request_activation: bool,
    activation_request_id: str = "",
) -> dict[str, Any]:
    """Register a verified CAT/direct source after its transport layer persists it."""
    try:
        ref = _assert_home_v3(home_ref)
        request_id = activation_request_id.strip()
        if request_activation and not request_id:
            request_id = new_activation_request_id()
        item = create_notice(
            home_path=Path(ref["home_path"]),
            home_kind=ref["home_kind"],
            home_id=ref["home_id"],
            project_id=ref["project_id"],
            source_kind=source_kind,
            source_ref=source_ref,
            summary=summary,
            activation_request_id=request_id if request_activation else "",
        )
    except (HomeProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "notice": item,
        "activation_request_id": request_id,
        "runtime_wake_performed": False,
    }


def activation_work(home_ref: dict[str, Any]) -> dict[str, Any]:
    """Read P3 work without performing any native side effect."""
    try:
        ref = normalize_home_ref(home_ref)
        items = activation_candidates(Path(ref["home_path"]))
    except (HomeProblem, NoticeProblem) as problem:
        raise _map_problem(problem) from problem
    return {
        "schema": "paos-attention-activation-work/v1",
        "home": ref,
        "items": items,
    }






def _takeover_mail_source(home_ref: dict[str, Any], source_ref: str) -> dict[str, Any]:
    home_path = Path(str(home_ref["home_path"]))
    try:
        if str(home_ref.get("home_kind") or "") == "project_agent":
            root = Path(str(home_ref.get("project_root") or ""))
            item = _find_mail_item(root=root, agent_id=str(home_ref["home_id"]), lookup=source_ref)
        else:
            filename = (
                source_ref[len("legacy-mail-file:"):]
                if source_ref.startswith("legacy-mail-file:")
                else f"{source_ref}.md"
            )
            path = home_path / "mailbox" / filename
            if not path.is_file():
                raise MailProblem(
                    "mail_message_missing",
                    f"Mail message 不存在：{path}",
                    {"agent_id": str(home_ref["home_id"]), "path": str(path)},
                )
            item = {"filename": path.name, "path": str(path), "message_id": path.stem}
        return _read_mail_item_file(item, agent_id=str(home_ref["home_id"]))
    except (MailProblem, AttentionServiceProblem) as problem:
        code = "attention_takeover_source_missing"
        if isinstance(problem, AttentionServiceProblem) and problem.code.endswith("recipient_mismatch"):
            code = problem.code
        raise AttentionServiceProblem(
            code,
            "Notice 的 Mail durable 来源无法读取；未标读、未写 Current。",
            {"source_ref": source_ref, "cause": str(problem)},
        ) from problem


def takeover_input(
    *,
    home_ref: dict[str, Any],
    notice_id: str,
    updates: dict[str, Any],
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Read one durable input, mark its Notice read, then switch this Home's Current."""
    try:
        ref = normalize_home_ref(home_ref)
    except HomeProblem as problem:
        raise _map_problem(problem) from problem
    if not updates:
        raise AttentionServiceProblem(
            "attention_takeover_current_empty",
            "接手必须明确提交本次 Current 字段（--set field=value）。",
            {"valid_fields": list(TODO_V3_CURRENT_FIELDS)},
        )
    unknown = sorted(k for k in updates if k not in TODO_V3_CURRENT_FIELDS)
    if unknown:
        raise AttentionServiceProblem(
            "attention_takeover_current_unknown",
            "存在未知 Current 字段；未读取、未标读、未写 Current。",
            {"unknown_fields": unknown, "valid_fields": list(TODO_V3_CURRENT_FIELDS)},
        )
    try:
        notice = read_notice(Path(str(ref["home_path"])), notice_id)
    except NoticeProblem as problem:
        raise _map_problem(problem) from problem
    if expected_fingerprint:
        current_fp = fingerprint_todo_v3(todo_path(ref))
        if current_fp != expected_fingerprint:
            raise AttentionServiceProblem(
                "attention_takeover_todo_changed",
                "TODO 指纹已变化；未读取、未标读、未写 Current。",
                {"expected": expected_fingerprint, "actual": current_fp},
            )
    source_kind = str(notice.get("source_kind") or "")
    source_ref = str(notice.get("source_ref") or "")
    if source_kind != "mail":
        raise AttentionServiceProblem(
            "attention_takeover_source_unsupported",
            "本入口目前只支持可读取的 Mail durable 来源；未标读、未写 Current。",
            {"source_kind": source_kind, "source_ref": source_ref},
        )
    try:
        update_home_todo_fields(
            home_ref=ref, updates=updates,
            expected_fingerprint=expected_fingerprint, dry_run=True,
        )
    except AttentionServiceProblem:
        raise
    source = _takeover_mail_source(ref, source_ref)
    stages = {"source": "read", "notice_read": False, "current": False}
    try:
        marked = mark_input_read(home_ref=ref, notice_id=notice_id)
        stages["notice_read"] = True
    except AttentionServiceProblem as problem:
        details = dict(getattr(problem, "details", {}) or {})
        details["stages"] = stages
        raise AttentionServiceProblem(
            "attention_takeover_notice_read_failed",
            "原输入已读取，但 Notice 标读失败；Current 未切换。",
            details,
        ) from problem
    try:
        updated = update_home_todo_fields(
            home_ref=ref, updates=updates, expected_fingerprint=expected_fingerprint,
        )
        stages["current"] = True
    except AttentionServiceProblem as problem:
        details = dict(getattr(problem, "details", {}) or {})
        details["stages"] = stages
        raise AttentionServiceProblem(
            "attention_takeover_current_failed",
            "原输入已读取且 Notice 已标读，但 Current 切换失败；请从这两步事实接续。",
            details,
        ) from problem
    return {
        "schema": ATTENTION_SERVICE_SCHEMA,
        "home": ref,
        "input": source,
        "notice": marked.get("notice") or notice,
        "current": updated.get("current") or {},
        "tasks_count": updated.get("tasks_count"),
        "stages": stages,
    }
