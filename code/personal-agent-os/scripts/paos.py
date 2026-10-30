#!/usr/bin/env python3
"""Agent-first PAOS localhost REST CLI.

Durable state is accessed only through HTTP. The CLI intentionally exposes
Agent/Runtime actions and supported Coordinator governance commands. Human-only
governance remains on its approved Human surface.
"""
from __future__ import annotations

import argparse
import socket
import json
import locale
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from paos_workstation import (  # noqa: E402
    posix_windows_drive_locator,
    WorkstationProblem,
    ensure_fixed_workstation,
    read_fixed_workstation,
    resolve_path,
)
from paos_coordinator import session_from_project  # noqa: E402
from paos_guide import (  # noqa: E402
    GuideProblem,
    build_guide_diff,
    promote_guide_candidate,
    validate_current_coordinator,
)
from paos_mail import (  # noqa: E402
    MailProblem,
    dispatch_status,
    list_mail,
    mark_mail_handled,
    read_mail,
    resolve_recipients,
    send_mail,
)
from paos_agent_activation import (  # noqa: E402
    AgentActivationProblem,
    activate_mail_dispatch,
    send_agent_mail,
)
from paos_home import HomeProblem, agent_project_id, project_agent_home
from paos_attention_service import (  # noqa: E402
    resolve_home_by_registry,
    AttentionServiceProblem,
    read_source_status as attention_read_source_status,
    register_direct_input as attention_register_direct_input,
    request_cat_activation as attention_request_cat_activation,
    send_cat_source as attention_send_cat_source,
    write_home_todo as attention_write_home_todo,
    update_home_todo_fields as attention_update_home_todo_fields,
    TODO_V3_LIST_FIELDS as attention_todo_list_fields,
    handle_input as attention_handle_input,
    takeover_input as attention_takeover_input,
    mark_input_read as attention_mark_input_read,
    organize_input as attention_organize_input,
    handle_mail_input as attention_handle_mail_input,
    list_project_mail_inputs as attention_list_project_mail_inputs,
    read_project_mail_input as attention_read_project_mail_input,
    read_home_state as attention_read_home_state,
    request_mail_activation as attention_request_mail_activation,
    resolve_project_home as attention_resolve_project_home,
    resolve_rooter_home as attention_resolve_rooter_home,
    resolve_home_by_registry,
    send_mail_source as attention_send_mail_source,
)
from paos_cat_activation import (  # noqa: E402
    CatActivationProblem,
    activate_cat_exchange,
    send_cat_agent_message,
    verify_cat_exchange_source,
)
from runtime_injection import (  # noqa: E402
    InjectionError,
    InjectionUncertain,
    inject as native_inject,
)
from paos_wakeup import WakeProblem, bind_wakeup  # noqa: E402
from paos_contact import (  # noqa: E402
    load_native_targets,
    save_native_targets,
)
from paos_library import (  # noqa: E402
    LibraryProblem,
    ensure_skill_library,
    ensure_workflow_library,
    load_library_roots,
    record_skill_use,
    refresh_skill_catalog,
    refresh_workflow_catalog,
    register_library_roots,
)
from paos_installation import (
    effective_data_root,  # noqa: E402
    InstallationProblem,
    load_installation_descriptor,
    resolve_installation_path,
    resolve_library_roots_path,
    write_installation_descriptor,
)
DEFAULT_BASE_URL = "http://127.0.0.1:8766"
CLI_CONFIG_SCHEMA = "paos-cli-config/v1"
AGENT_CONTEXT_SCHEMA = "paos-cli-agent-context/v1"
AGENT_MAILBOX_SCHEMA = "paos-cli-agent-mailbox/v1"
ORIENT_SCHEMA = "paos-orient/v1"
INBOX_SCHEMA = "paos-inbox/v1"
from paos_agent_numbers import (
    NumbersProblem,
    agent_id_for_staff_number,
    allocate_number,
    resolve_numbers_path,
    staff_number as agent_staff_number,
)
from paos_contact import (  # noqa: E402
    CONTACT_SCHEMA,
    build_team_rows,
    parse_team_payload,
    runtime_contact,
)
from paos_cat_cli import add_cat_parser, execute_cat  # noqa: E402
PEERS_SCHEMA = "paos-peers/v2"
COORDINATOR_CONTROL_SCHEMA = "paos-cli-coordinator-control/v1"
CONTROL_LIST_LIMIT = 6
CONTROL_DELTA_LIMIT = 8
CONTROL_TEXT_MAX_CHARS = 320
REQUEST_TYPES = (
    "information",
    "artifact",
    "review",
    "decision",
    "coordination",
    "resource",
    "clarification",
    "assignment",
    "integration",
)
PROTECTED_BODY_FIELDS = {
    "schema",
    "operation_id",
    "revision",
    "base_revision",
    "session_id",
    "coordinator_session_id",
    "execution_cycle",
    "context_pack_id",
    "runtime_id",
    "model_id",
    "write_owner_id",
    "write_owner_generation",
}


from paos_render import (
    render_workbench,
    render_program_rollback,
    render_install_plan,
    render_install_homes,
    render_authority,
)


from paos_orient import (
    _orient_source_root, _orient_library_roots, _orient_next_action,
    _todo_current_view, _todo_open_tasks, _orient_todo_contract_issues, render_orient,
)
from paos_compact import (
    _bounded_compact_text, compact_request_ref, compact_mailbox, compact_work, compact_action,
)


class CliError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        error_code: str = "",
        hint: str = "",
        details: dict[str, Any] | None = None,
        operation_id: str | None = None,
        revision: int | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.hint = hint
        self.details = dict(details or {})
        self.operation_id = operation_id
        self.revision = revision

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "ok": False,
            "error": str(self),
            "error_code": self.error_code or "cli_error",
            "hint": self.hint,
            "details": self.details,
        }
        if self.status is not None:
            result["status"] = self.status
        if self.operation_id:
            result["operation_id"] = self.operation_id
        if self.revision is not None:
            result["revision"] = self.revision
        return result


class RestClient:
    def __init__(self, base_url: str, timeout: float = 8.0, *, service: str = "PAOS"):
        self.base_url = normalize_base_url(base_url, "base URL")
        self.timeout = timeout
        self.service = service

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            body: dict[str, Any] = {}
            try:
                candidate = json.loads(raw)
                if isinstance(candidate, dict):
                    body = candidate
            except json.JSONDecodeError:
                pass
            error = body.get("error")
            message = str(error.get("message") if isinstance(error, dict) else error or raw or exc)
            details = body.get("details")
            if not isinstance(details, dict):
                details = {}
            raise CliError(
                message,
                status=exc.code,
                error_code=str(error.get("code") if isinstance(error, dict) else body.get("error_code") or "http_error"),
                hint=str(body.get("hint") or ""),
                details=details,
            ) from exc
        except URLError as exc:
            raise CliError(
                f"{self.service} unreachable: {exc.reason}",
                error_code="unreachable",
                hint=f"Check that {self.service} is running and that the configured base URL is reachable.",
            ) from exc
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CliError(
                f"{self.service} returned non-JSON response",
                error_code="invalid_response",
            ) from exc
        if not isinstance(body, dict):
            raise CliError(
                f"{self.service} returned a non-object JSON response",
                error_code="invalid_response",
            )
        return body


def new_operation_id() -> str:
    return "op-cli-" + uuid.uuid4().hex


def new_project_update_id() -> str:
    """Generate an ID for the existing authorized Project Agent write contract."""
    return "up-cli-" + uuid.uuid4().hex


def normalize_base_url(value: str, label: str) -> str:
    text = str(value or "").strip().rstrip("/")
    parsed = urlsplit(text)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise CliError(
            f"{label} must be an http(s) origin such as http://127.0.0.1:8766",
            error_code="invalid_base_url",
        )
    return f"{parsed.scheme}://{parsed.netloc}"


def resolve_config_path(explicit: str | None = None) -> Path:
    raw = explicit or os.environ.get("PAOS_CONFIG_PATH")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".paos" / "config.json"


def load_cli_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(
            f"Cannot read PAOS CLI config: {path}",
            error_code="config_error",
            hint="Fix or remove the local config file, or select another one with --config-file.",
        ) from exc
    if not isinstance(value, dict):
        raise CliError(
            f"PAOS CLI config must contain one JSON object: {path}",
            error_code="config_error",
        )
    schema = value.get("schema")
    if schema not in (None, CLI_CONFIG_SCHEMA):
        raise CliError(
            f"Unsupported PAOS CLI config schema: {schema}",
            error_code="config_error",
        )
    result: dict[str, Any] = {}
    if "base_url" in value:
        result["base_url"] = normalize_base_url(str(value["base_url"]), "config base_url")
    return result


def write_cli_config(path: Path, *, base_url: str) -> dict[str, Any]:
    normalized = normalize_base_url(base_url, "base URL")
    payload = {"schema": CLI_CONFIG_SCHEMA, "base_url": normalized}
    temporary = path.with_name(f"{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise CliError(
            f"Cannot write PAOS CLI config: {path}",
            error_code="config_error",
        ) from exc
    return payload


def resolve_base_url(explicit: str | None, config_path: Path) -> str:
    if explicit:
        return normalize_base_url(explicit, "--base-url")
    env_value = os.environ.get("PAOS_BASE_URL")
    if env_value:
        return normalize_base_url(env_value, "PAOS_BASE_URL")
    config = load_cli_config(config_path)
    if config.get("base_url"):
        return str(config["base_url"])
    return DEFAULT_BASE_URL


def _decode_stdin_bytes(data: bytes, label: str) -> str:
    """Decode native CLI stdin without inheriting surrogateescape artifacts.

    UTF-8 is the PAOS interchange default. Common Windows native-pipe
    encodings are accepted only as strict fallbacks when the bytes are not
    valid UTF-8.
    """
    if not data:
        return ""

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass

    candidates: list[str] = ["utf-8"]
    stream_encoding = str(getattr(sys.stdin, "encoding", "") or "").strip()
    if stream_encoding:
        candidates.append(stream_encoding)
    try:
        preferred = locale.getpreferredencoding(False)
    except Exception:
        preferred = ""
    if preferred:
        candidates.append(preferred)
    if os.name == "nt":
        candidates.append("mbcs")

    seen: set[str] = set()
    for encoding in candidates:
        key = encoding.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        try:
            return data.decode(encoding, errors="strict")
        except (LookupError, UnicodeDecodeError):
            continue

    raise CliError(
        f"Cannot decode {label} from stdin as UTF-8/native Windows text",
        error_code="text_input_encoding_error",
        hint="Pipe UTF-8 text or use @FILE with a UTF-8 file.",
    )


def _read_stdin_text(label: str) -> str:
    stream = sys.stdin
    binary = getattr(stream, "buffer", None)
    if binary is not None:
        try:
            data = binary.read()
        except OSError as exc:
            raise CliError(
                f"Cannot read {label} from stdin",
                error_code="text_input_error",
            ) from exc
        return _decode_stdin_bytes(data, label)

    # StringIO/test/custom streams have no binary buffer. If a text wrapper
    # already produced surrogateescape code points, recover the original
    # bytes and run them through the same strict decoder.
    text = stream.read()
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
        encoding = str(getattr(stream, "encoding", "") or "utf-8")
        try:
            data = text.encode(encoding, errors="surrogateescape")
        except (LookupError, UnicodeEncodeError) as exc:
            raise CliError(
                f"Cannot recover {label} stdin bytes",
                error_code="text_input_encoding_error",
            ) from exc
        return _decode_stdin_bytes(data, label)
    return text


def text_arg(value: str | None, label: str, *, required: bool = False) -> str:
    """Resolve one text argument from literal text, @FILE, or '-' stdin."""
    if value is None:
        text = ""
    else:
        raw = str(value)
        if raw == "-":
            text = _read_stdin_text(label)
        elif raw.startswith("@@"):
            text = raw[1:]
        elif raw.startswith("@"):
            path = Path(raw[1:]).expanduser()
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise CliError(
                    f"Cannot read {label} from {path}",
                    error_code="text_input_error",
                ) from exc
        else:
            text = raw
    text = text.strip()
    if required and not text:
        raise CliError(
            f"{label} cannot be empty",
            error_code="text_input_error",
        )
    return text


def todo_text_arg(value: str | None, label: str, *, required: bool = False) -> str:
    """Resolve TODO payload without normalizing line endings or outer whitespace."""
    if value is None:
        text = ""
    else:
        raw = str(value)
        if raw == "-":
            text = _read_stdin_text(label)
        elif raw.startswith("@@"):
            text = raw[1:]
        elif raw.startswith("@"):
            path = Path(raw[1:]).expanduser()
            try:
                text = path.read_bytes().decode("utf-8")
            except OSError as exc:
                raise CliError(
                    f"Cannot read {label} from {path}",
                    error_code="text_input_error",
                ) from exc
            except UnicodeError as exc:
                raise CliError(
                    f"Cannot decode {label} from {path} as UTF-8",
                    error_code="text_input_encoding_error",
                ) from exc
        else:
            text = raw
    if required and not text.strip():
        raise CliError(
            f"{label} cannot be empty",
            error_code="text_input_error",
        )
    return text


def text_list(values: list[str] | None, label: str) -> list[str]:
    return [
        item
        for index, value in enumerate(values or [], start=1)
        if (item := text_arg(value, f"{label}[{index}]"))
    ]


def load_body(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        raw = _read_stdin_text("JSON body") if path == "-" else Path(path).read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(
            f"Cannot read --body JSON: {path}",
            error_code="invalid_body_file",
        ) from exc
    if not isinstance(value, dict):
        raise CliError("--body must contain one JSON object", error_code="invalid_body_file")
    conflict = sorted(PROTECTED_BODY_FIELDS.intersection(value))
    if conflict:
        raise CliError(
            f"--body cannot override protected field: {conflict[0]}",
            error_code="protected_field",
        )
    return value


def build_project_progress_update_payload(args: argparse.Namespace) -> dict[str, Any]:
    """Build only the existing Session-authorized generated-summary patch."""
    project_id = str(getattr(args, "project_id", "") or "").strip()
    if not re.fullmatch(r"[123]\d{3}", project_id):
        raise CliError("Project ID 必须符合现有四位编号合同。", error_code="invalid_project_id")

    expected_revision = getattr(args, "expected_revision", None)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
        raise CliError("必须提供正整数 --expected-revision。", error_code="invalid_revision")

    update_id = str(getattr(args, "update_id", None) or new_project_update_id()).strip()
    if not re.fullmatch(r"up-[A-Za-z0-9._:-]{4,120}", update_id):
        raise CliError("update_id 必须符合现有 up- ID 合同。", error_code="invalid_update_id")

    session_id = str(getattr(args, "session_id", None) or "").strip()
    handshake_id = str(getattr(args, "handshake_id", None) or "").strip()
    if bool(session_id) == bool(handshake_id):
        raise CliError("必须且只能提供一个 --session-id 或 --handshake-id。", error_code="invalid_session_ref")
    if any(value.startswith("<") and value.endswith(">") for value in (session_id, handshake_id) if value):
        raise CliError("不能使用占位符作为受管 Session 引用。", error_code="invalid_session_ref")

    reason = text_arg(getattr(args, "reason", None), "reason", required=True).strip()
    if not reason or len(reason) > 8000:
        raise CliError("reason 必须是 1–8000 个字符的非空文本。", error_code="invalid_reason")

    fields = (
        ("stage", "stage"),
        ("progress_and_results", "progress_and_results"),
        ("recent_change", "recent_change"),
        ("current_gap", "current_gap"),
    )
    generated_patch: dict[str, str] = {}
    for argument, field in fields:
        value = getattr(args, argument, None)
        if value is not None:
            generated_patch[field] = text_arg(value, field)

    if not generated_patch:
        raise CliError(
            "至少提供一个进度字段：--stage、--progress-and-results、--recent-change 或 --current-gap。",
            error_code="empty_generated_patch",
        )

    return {
        "schema": "paos-agent-project-progress-update/v1",
        "update_id": update_id,
        "project_id": project_id,
        "expected_revision": expected_revision,
        "session_ref": {
            "handshake_id": handshake_id,
            "session_id": session_id,
        },
        "generated_patch": generated_patch,
        "reason": reason,
    }


def project_revision(client: RestClient, project_id: str) -> int:
    response = client.request("GET", f"/api/projects/{project_id}")
    return int(response["project"]["revision"])


def get_session_detail(
    client: RestClient, project_id: str, session_id: str
) -> dict[str, Any]:
    return client.request(
        "GET", f"/api/projects/{project_id}/sessions/{session_id}"
    )


def mutation_meta(
    client: RestClient,
    project_id: str,
    args: argparse.Namespace,
) -> tuple[str, int]:
    op = args.operation_id or new_operation_id()
    revision = (
        args.revision
        if args.revision is not None
        else project_revision(client, project_id)
    )
    return op, revision


def session_mutation_meta(
    client: RestClient,
    project_id: str,
    session_id: str,
    args: argparse.Namespace,
    detail: dict[str, Any] | None = None,
) -> tuple[str, int, dict[str, Any] | None]:
    op = args.operation_id or new_operation_id()
    if args.revision is not None:
        return op, args.revision, detail
    current = detail or get_session_detail(client, project_id, session_id)
    try:
        revision = int(current["project_revision"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CliError(
            "Session Detail is missing project_revision",
            error_code="invalid_response",
        ) from exc
    return op, revision, current


def post_mutation(
    client: RestClient,
    path: str,
    payload: dict[str, Any],
    op: str,
    revision: int,
    *,
    unknown_message: str | None = None,
    unknown_hint: str | None = None,
) -> dict[str, Any]:
    try:
        return client.request("POST", path, payload)
    except CliError as exc:
        exc.operation_id = op
        exc.revision = revision
        raise
    except (TimeoutError, socket.timeout) as exc:
        raise CliError(
            unknown_message
            or "请求超时，服务端可能已提交，结果未知。保留原 update_id，不要自动重发或更换 ID。",
            error_code="commit_result_unknown",
            hint=unknown_hint
            or "用同一 update_id 与 expected_revision 重新读取最新 revision 后再决定；不要自动重发。",
            operation_id=op,
            revision=revision,
        ) from exc


def find_by_id(
    items: list[dict[str, Any]], object_id: str, label: str
) -> dict[str, Any]:
    for item in items:
        if item.get("id") == object_id:
            return item
    raise CliError(
        f"{label} not found: {object_id}",
        error_code="not_found",
    )


def _prepare_session_handoff(
    args: argparse.Namespace,
    client: RestClient,
    *,
    operation_id: str,
) -> dict[str, Any] | None:
    recipient_id = str(getattr(args, "handoff_to", None) or "").strip()
    if not recipient_id:
        if any(
            str(getattr(args, field, None) or "").strip()
            for field in ("handoff_subject", "handoff_body", "handoff_message_id")
        ):
            raise CliError("--handoff-subject/body/message-id require --handoff-to", error_code="invalid_handoff")
        return None
    subject = text_arg(args.handoff_subject, "handoff subject", required=True)
    body = text_arg(args.handoff_body, "handoff body", required=True)
    message_id = str(getattr(args, "handoff_message_id", None) or operation_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,119}", message_id):
        raise CliError(
            "handoff message_id 必须为 3–120 位字母、数字、点、下划线或短横线。",
            error_code="mail_message_id_invalid",
        )
    response = client.request("GET", f"/api/projects/{args.project_id}")
    project = response.get("project")
    if not isinstance(project, dict):
        raise CliError("Project response is missing project", error_code="invalid_response")
    if recipient_id == args.session_id:
        raise CliError("handoff recipient must be another Project Agent", error_code="mail_recipient_self")
    find_by_id(project.get("sessions", []), recipient_id, "handoff Agent")
    root_raw = str(project.get("root_path") or "").strip()
    if not root_raw:
        raise CliError(
            "Project 没有 root_path，无法保存 durable handoff Mail。",
            error_code="mail_project_root_missing",
        )
    root = Path(posix_windows_drive_locator(root_raw)).expanduser()
    if not root.is_dir():
        raise CliError(
            f"Project root 不可用，未提交本次责任更新：{root}",
            error_code="mail_project_root_missing",
        )
    return {
        "project": project,
        "root": root,
        "recipient_id": recipient_id,
        "subject": subject,
        "body": body,
        "message_id": message_id,
    }


def _deliver_session_handoff(
    result: dict[str, Any],
    *,
    handoff: dict[str, Any] | None,
    project_id: str,
    sender_id: str,
    operation_id: str,
) -> dict[str, Any]:
    if handoff is None:
        return result
    try:
        persisted = send_mail(
            root=handoff["root"],
            project=handoff["project"],
            subject=handoff["subject"],
            body=handoff["body"],
            recipients=[handoff["recipient_id"]],
            sender_kind="agent",
            sender_id=sender_id,
            message_id=handoff["message_id"],
        )
    except MailProblem as problem:
        return {
            **result,
            "handoff": {
                "state": "not_persisted",
                "operation_id": operation_id,
                "message_id": handoff["message_id"],
                "recipient_id": handoff["recipient_id"],
                "error_code": problem.code,
                "detail": str(problem),
                "details": problem.details,
            },
        }
    try:
        activation = activate_mail_dispatch(
            root=handoff["root"],
            project_id=project_id,
            message_id=handoff["message_id"],
        )
    except AgentActivationProblem as problem:
        activation = {
            "state": "activation_error",
            "error_code": problem.code,
            "detail": str(problem),
        }
    return {
        **result,
        "handoff": {
            "state": "persisted",
            "operation_id": operation_id,
            "message_id": handoff["message_id"],
            "recipient_id": handoff["recipient_id"],
            "mail": persisted,
            "activation": activation,
        },
    }


def validate_guide_candidate_binding(
    project: dict[str, Any], *, work_id: str, session_id: str, cycle: int
) -> None:
    """Bind one local Guide path to the canonical Session Cycle that created it."""
    find_by_id(project.get("work_items") or [], work_id, "Guide candidate Work")
    session = find_by_id(
        project.get("sessions") or [], session_id, "Guide candidate Session"
    )
    if isinstance(cycle, bool) or not isinstance(cycle, int) or cycle < 1:
        raise CliError(
            "Guide candidate Cycle 必须是正整数。",
            error_code="guide_candidate_cycle_invalid",
            details={"cycle": cycle},
        )
    cycle_record = next(
        (
            item
            for item in (session.get("cycles") or [])
            if isinstance(item, dict) and int(item.get("number") or 0) == cycle
        ),
        None,
    )
    if cycle_record is None:
        raise CliError(
            f"Session {session_id} 没有 Cycle {cycle}；不能把该目录作为 canonical Guide 候选。",
            error_code="guide_candidate_cycle_missing",
            details={"session_id": session_id, "cycle": cycle},
        )
    cycle_work_id = str(cycle_record.get("work_item_id") or "")
    if cycle_work_id != work_id:
        raise CliError(
            "Guide candidate Work 与该 Session Cycle 的 canonical Work 不一致。",
            error_code="guide_candidate_work_mismatch",
            details={
                "session_id": session_id,
                "cycle": cycle,
                "supplied_work_item_id": work_id,
                "cycle_work_item_id": cycle_work_id,
            },
        )












def session_actor(project_id: str, session: dict[str, Any]) -> str:
    coordinator = session.get("coordinator") or {}
    if (
        coordinator.get("level") == "coordinator"
        and not coordinator.get("revoked_at")
        and coordinator.get("project_id") == project_id
        and session.get("status") == "active"
        and session.get("acknowledgement") is not None
    ):
        return "coordinator"
    return "worker"












def _control_item(item: dict[str, Any]) -> dict[str, Any]:
    """Compact one stewardship/office item without copying long bodies."""
    keep = (
        "id",
        "event_id",
        "type",
        "kind",
        "request_id",
        "request_type",
        "decision_id",
        "work_item_id",
        "session_id",
        "target_session_id",
        "target_identity_id",
        "binding_state",
        "status",
        "waiting_on",
        "requires_human",
        "cycle_number",
        "revision",
        "event_type",
        "operation_id",
    )
    result = {key: item.get(key) for key in keep if key in item}
    for field in ("title", "description", "detail", "reason", "waiting_reason", "summary"):
        if field not in item:
            continue
        value, omitted = _bounded_compact_text(item.get(field), CONTROL_TEXT_MAX_CHARS)
        result[field] = value
        if omitted:
            result[f"{field}_omitted"] = True
    return result


def _control_list(items: Any, *, limit: int = CONTROL_LIST_LIMIT) -> dict[str, Any]:
    values = [item for item in (items or []) if isinstance(item, dict)]
    shown = [_control_item(item) for item in values[:limit]]
    return {
        "items": shown,
        "omitted": max(0, len(values) - len(shown)),
        "total": len(values),
    }


def build_coordinator_control(
    *,
    project_id: str,
    stewardship: dict[str, Any],
    office: dict[str, Any],
    delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a thin Coordinator control view from existing read projections.

    This is not a new durable state model. It keeps unresolved responsibilities
    visible while exposing new ledger events only when the caller supplies a
    since_revision cursor.
    """
    coordinator = stewardship.get("coordinator")
    if not isinstance(coordinator, dict):
        coordinator = {}

    lifecycle = stewardship.get("lifecycle_findings")
    lifecycle_items = lifecycle.get("items") if isinstance(lifecycle, dict) else []

    attention = {
        "needs_human": _control_list(
            (stewardship.get("needs_me") or {}).get("items")
            if isinstance(stewardship.get("needs_me"), dict)
            else []
        ),
        "responsibility_gaps": _control_list(stewardship.get("responsibility_gaps")),
        "pending_integration": _control_list(office.get("pending_integration")),
        "review_work": _control_list(stewardship.get("review_work")),
        "lifecycle_findings": _control_list(lifecycle_items),
        "coordinator_pending_requests": _control_list(office.get("pending_requests")),
    }

    delta_view: dict[str, Any] = {
        "requested": False,
        "since_revision": None,
        "current_revision": stewardship.get("revision"),
        "events": [],
        "omitted": 0,
    }
    if isinstance(delta, dict):
        raw_events = [item for item in (delta.get("events") or []) if isinstance(item, dict)]
        shown = [_control_item(item) for item in raw_events[-CONTROL_DELTA_LIMIT:]]
        delta_view = {
            "requested": True,
            "since_revision": delta.get("since_revision"),
            "current_revision": delta.get("current_revision"),
            "events": shown,
            "omitted": max(0, len(raw_events) - len(shown)),
        }

    session_id = str(coordinator.get("session_id") or "")
    revision = int(stewardship.get("revision") or 0)
    next_revision = int(delta_view.get("current_revision") or revision)
    expand = {
        "full_stewardship": f"paos project inspect {project_id}",
        "needs_human": f"paos needs-me {project_id}",
        "project": f"paos project show {project_id}",
        "next_delta": (
            f"paos coordinator control {project_id} --since-revision {next_revision}"
        ),
    }
    if session_id:
        expand["coordinator_context"] = f"paos session context {project_id} {session_id}"
        expand["coordinator_mailbox"] = f"paos session mailbox {project_id} {session_id}"

    counts = dict(stewardship.get("counts") or {})
    counts.update(
        {
            "pending_integration": len(office.get("pending_integration") or []),
            "blocked_work_items": len(office.get("blocked_work_items") or []),
            "coordinator_pending_requests": len(office.get("pending_requests") or []),
            "active_sessions": len(office.get("active_sessions") or []),
        }
    )

    return {
        "ok": True,
        "schema": COORDINATOR_CONTROL_SCHEMA,
        "project_id": project_id,
        "revision": revision,
        "coordinator": {
            key: coordinator.get(key)
            for key in (
                "session_id",
                "status",
                "acknowledged",
                "active",
                "identity_id",
                "agent_label",
            )
            if key in coordinator
        },
        "counts": counts,
        "attention": attention,
        "delta": delta_view,
        "meta": {
            "atomic_snapshot": False,
            "revision_source": "stewardship",
            "sources": [
                "stewardship",
                "office",
                *(["delta"] if isinstance(delta, dict) else []),
            ],
        },
        "expand": expand,
    }


def coordinator_control(
    client: RestClient,
    project_id: str,
    *,
    since_revision: int | None = None,
) -> dict[str, Any]:
    stewardship_response = client.request(
        "GET", f"/api/projects/{project_id}/stewardship"
    )
    stewardship = stewardship_response.get("stewardship")
    if not isinstance(stewardship, dict):
        raise CliError(
            "Stewardship response is missing stewardship",
            error_code="invalid_response",
        )

    coordinator = stewardship.get("coordinator")
    session_id = (
        str(coordinator.get("session_id") or "")
        if isinstance(coordinator, dict)
        else ""
    )
    office_path = f"/api/projects/{project_id}/office"
    if session_id:
        office_path += "?" + urlencode({"session_id": session_id})
    office_response = client.request("GET", office_path)
    office = office_response.get("office")
    if not isinstance(office, dict):
        raise CliError(
            "Office response is missing office",
            error_code="invalid_response",
        )

    delta = None
    if since_revision is not None:
        delta_response = client.request(
            "GET",
            f"/api/projects/{project_id}/delta?"
            + urlencode({"since_revision": since_revision}),
        )
        delta = delta_response.get("delta")
        if not isinstance(delta, dict):
            raise CliError(
                "Delta response is missing delta",
                error_code="invalid_response",
            )

    return build_coordinator_control(
        project_id=project_id,
        stewardship=stewardship,
        office=office,
        delta=delta,
    )


def build_agent_context(
    detail: dict[str, Any],
    authority: dict[str, Any],
    *,
    project_id: str,
    session_id: str,
) -> dict[str, Any]:
    session = detail.get("session")
    if not isinstance(session, dict):
        raise CliError(
            "Session Detail is missing session",
            error_code="invalid_response",
        )
    mailbox = detail.get("mailbox")
    if not isinstance(mailbox, dict):
        mailbox = {}
    context_pack = detail.get("context_pack")
    if not isinstance(context_pack, dict):
        context_pack = {}
    pack_content = context_pack.get("content")
    if not isinstance(pack_content, dict):
        pack_content = {}
    actor = str(authority.get("actor") or session_actor(project_id, session))
    allowed_actions = [
        compact_action(action)
        for action in authority.get("actions", [])
        if isinstance(action, dict) and bool(action.get("allowed", True))
    ]
    entry = session.get("entry") or {}
    return {
        "ok": True,
        "schema": AGENT_CONTEXT_SCHEMA,
        "project_id": project_id,
        "live": {
            "project_revision": detail.get("project_revision"),
            "agent": {
                "id": session_id,
                "status": session.get("status"),
                "current_cycle": session.get("current_cycle"),
                "identity_id": session.get("identity_id"),
                "agent_label": session.get("agent_label"),
                "runtime_id": session.get("runtime_id"),
                "model_id": session.get("model_id"),
            },
            "mission": session.get("mission") or {},
            "current_work": compact_work(detail.get("current_work_item")),
            "progress": session.get("progress") or {},
            "mailbox": compact_mailbox(mailbox),
            "working_memory": detail.get("working_memory") or {},
            "artifact_lineages": detail.get("artifact_lineages") or {},
            "typed_references": detail.get("typed_references") or {},
            "authority": {
                "actor": actor,
                "available_actions": allowed_actions,
            },
        },
        "entry_snapshot": {
            "status": context_pack.get("status"),
            "path": context_pack.get("path"),
            "project_revision_at_entry": pack_content.get("project_revision"),
            "context_pack_id": (
                pack_content.get("context_pack_id")
                or (entry.get("context_pack_id") if isinstance(entry, dict) else None)
            ),
            "context_level": pack_content.get("context_level"),
            "execution": pack_content.get("execution") or {},
            "working_memory_at_entry": pack_content.get("working_memory") or {},
            "materials": pack_content.get("materials") or [],
            "project_location": pack_content.get("project_location") or {},
            "boundaries": pack_content.get("boundaries") or [],
        },
        "expand": {
            "mailbox": f"paos session mailbox {project_id} {session_id}",
            "session": f"paos session show {project_id} {session_id}",
            "project": f"paos project show {project_id}",
            "authority": f"paos authority --actor {actor} --allowed-only",
        },
    }


def session_context(
    client: RestClient,
    project_id: str,
    session_id: str,
) -> dict[str, Any]:
    detail = get_session_detail(client, project_id, session_id)
    session = detail.get("session")
    if not isinstance(session, dict):
        raise CliError(
            "Session Detail is missing session",
            error_code="invalid_response",
        )
    actor = str(detail.get("authority_actor") or session_actor(project_id, session))
    authority_response = client.request(
        "GET", "/api/authority?" + urlencode({"actor": actor})
    )
    authority = authority_response.get("authority")
    if not isinstance(authority, dict):
        raise CliError(
            "Authority response is missing authority",
            error_code="invalid_response",
        )
    return build_agent_context(
        detail,
        authority,
        project_id=project_id,
        session_id=session_id,
    )


def session_mailbox(
    client: RestClient,
    project_id: str,
    session_id: str,
) -> dict[str, Any]:
    detail = get_session_detail(client, project_id, session_id)
    mailbox = detail.get("mailbox")
    if not isinstance(mailbox, dict):
        raise CliError(
            "Session Detail is missing mailbox",
            error_code="invalid_response",
        )
    return {
        "ok": True,
        "schema": AGENT_MAILBOX_SCHEMA,
        "project_id": project_id,
        "session_id": session_id,
        "project_revision": detail.get("project_revision"),
        "mailbox": mailbox,
    }














def _read_orient_inputs(
    client: RestClient,
    project_id: str,
    agent_id: str,
    *,
    root_override: str | None,
    installation_path: Path,
) -> dict[str, Any]:
    project_response = client.request("GET", f"/api/projects/{project_id}")
    project = project_response.get("project")
    if not isinstance(project, dict):
        raise CliError("Project response is missing project", error_code="invalid_response")
    detail = get_session_detail(client, project_id, agent_id)
    session = detail.get("session")
    if not isinstance(session, dict):
        raise CliError("Session Detail is missing session", error_code="invalid_response")
    mailbox = detail.get("mailbox")
    if not isinstance(mailbox, dict):
        raise CliError("Session Detail is missing mailbox", error_code="invalid_response")

    root_raw = str(root_override or project.get("root_path") or "").strip()
    root = (
        Path(posix_windows_drive_locator(root_raw)).expanduser()
        if root_raw
        else None
    )
    issues: list[dict[str, str]] = []
    workstation_view: dict[str, Any] = {}
    if root is None:
        issues.append(
            {
                "kind": "project_root_missing",
                "detail": "Project 未登记 root_path，且未提供 --root；固定工位不可读。",
            }
        )
    else:
        try:
            workstation_view = read_fixed_workstation(
                root, agent_id, tolerate_todo_errors=True
            )
        except WorkstationProblem as problem:
            issues.append(
                {
                    "kind": "workstation",
                    "code": str(problem.code),
                    "detail": f"固定工位不可读（{problem.code}）：{problem}",
                }
            )
            workstation = root / "Workstations" / agent_id
            workstation_view = {
                "workstation_path": str(workstation),
                "entry_path": str(workstation / "ENTRY.md"),
                "entry_exists": (workstation / "ENTRY.md").is_file(),
                "todo_path": str(workstation / "TODO.md"),
                "todo": {},
                "todo_error": {"code": problem.code, "detail": str(problem)},
                "mailbox": {},
            }

    todo = workstation_view.get("todo") if isinstance(workstation_view.get("todo"), dict) else {}
    todo_error = workstation_view.get("todo_error")
    contract_issues = (
        _orient_todo_contract_issues(todo, project_id, agent_id)
        if workstation_view and not todo_error
        else []
    )
    todo_trusted = bool(workstation_view) and not bool(todo_error) and not contract_issues
    current = _todo_current_view(todo) if todo_trusted else {}
    open_tasks = _todo_open_tasks(todo) if todo_trusted else []
    if todo_error:
        issues.append(
            {
                "kind": "todo_read",
                "code": str(todo_error.get("code") or "todo_unavailable"),
                "detail": str(todo_error.get("detail") or "固定工位 TODO 不可读取。"),
            }
        )
    if contract_issues:
        issues.append(
            {
                "kind": "todo_contract",
                "code": "todo_contract_invalid",
                "detail": "TODO 当前区格式或身份不完整；仍显示固定工位 ENTRY，不从 TODO 历史推断下一步。",
            }
        )

    try:
        installation = load_installation_descriptor(installation_path)
    except InstallationProblem as problem:
        installation = None
        issues.append(
            {
                "kind": "installation_descriptor_invalid",
                "code": problem.code,
                "detail": str(problem),
            }
        )
    installation_roots = _orient_library_roots(installation, issues)
    source_root = _orient_source_root(installation, issues)
    counts = mailbox.get("counts") or {}
    request_inbox_count = int(counts.get("inbox") or 0)
    workstation_mailbox = workstation_view.get("mailbox") or {}
    mail_count = int(workstation_mailbox.get("message_count") or 0)
    unhandled_mail_count = 0
    if root is not None and workstation_mailbox.get("ready"):
        try:
            if todo.get("schema") == "paos-todo/v3":
                mail_listing = attention_list_project_mail_inputs(
                    root=root,
                    project=project,
                    agent_id=agent_id,
                )
                mail_count = int(mail_listing.get("count") or 0)
                unhandled_mail_count = int(
                    mail_listing.get("unresolved_count")
                    if mail_listing.get("unresolved_count") is not None
                    else mail_listing.get("pending_count") or 0
                )
            else:
                mail_listing = list_mail(root, agent_id)
                mail_count = int(mail_listing.get("count") or 0)
                unhandled_mail_count = int(mail_listing.get("unhandled_count") or 0)
                for item in mail_listing.get("items") or []:
                    if isinstance(item, dict) and item.get("handling_error"):
                        issues.append(
                            {
                                "kind": "mail_handling_record",
                                "detail": str((item.get("handling_error") or {}).get("detail") or "Mail handled 记录无效。"),
                            }
                        )
        except (MailProblem, AttentionServiceProblem) as problem:
            issues.append(
                {
                    "kind": "durable_mail",
                    "code": str(getattr(problem, "code", "mail_unavailable")),
                    "detail": str(problem),
                }
            )
            unhandled_mail_count = mail_count
    project_root = str(root) if root is not None else ""
    payload = {
        "ok": True,
        "schema": ORIENT_SCHEMA,
        "project_revision": detail.get("project_revision"),
        "identity": {
            "project_id": project_id,
            "project_name": project.get("name"),
            "agent_id": agent_id,
            "identity_id": session.get("identity_id"),
            "agent_label": session.get("agent_label"),
            "status": session.get("status"),
        },
        "project": {
            "root_path": project_root,
            "source_root": source_root,
            "library_roots": installation_roots,
        },
        "entry": {
            "path": workstation_view.get("entry_path", ""),
            "available": bool(workstation_view.get("entry_exists")),
        },
        "todo": {
            "workstation_path": workstation_view.get("workstation_path", ""),
            "path": workstation_view.get("todo_path", ""),
            "schema": todo.get("schema", ""),
            "trusted": todo_trusted,
            "current": current,
            "open_tasks": open_tasks,
            "counts": todo.get("counts") or {},
            "missing_sections": todo.get("missing_sections") or [],
            "issues": contract_issues,
            "read_error": todo_error,
        },
        "communication": {
            "durable_mail": {
                "state": "ready" if workstation_mailbox.get("ready") else "unavailable",
                "count": mail_count,
                "unhandled_count": unhandled_mail_count,
                "path": workstation_mailbox.get("path", ""),
            },
            "formal_requests": compact_mailbox(mailbox),
        },
        "runtime_reachability": "unknown",
        "inconsistencies": issues,
        "next_action": _orient_next_action(
            request_inbox_count,
            unhandled_mail_count,
            current,
            open_tasks,
            todo_trusted,
        ),
        "expand": {
            "inbox": f"paos inbox {project_id} {agent_id}",
            "session": f"paos session show {project_id} {agent_id}",
            "project": f"paos project show {project_id}",
        },
    }
    return payload




def execute_orient(
    args: argparse.Namespace,
    client: RestClient,
    installation_path: Path,
) -> Any:
    payload = _read_orient_inputs(
        client,
        args.project_id,
        args.agent_id,
        root_override=args.root,
        installation_path=installation_path,
    )
    label = agent_staff_number(
        args.agent_id,
        explicit_path=str(getattr(args, 'agent_numbers_file', None) or ''),
        installation_path=installation_path,
    )
    if label:
        payload["identity"]["staff_number"] = label
        payload["staff_number"] = label
    return payload if args.json_output else render_orient(payload)


def _git_source_revision(root: Path) -> str | None:
    if not root.is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    revision = result.stdout.strip()
    return revision or None


def execute_status(
    args: argparse.Namespace,
    client: RestClient,
    installation_path: Path,
) -> dict[str, Any]:
    project_response = client.request("GET", f"/api/projects/{args.project_id}")
    project = project_response.get("project")
    if not isinstance(project, dict):
        raise CliError("Project response is missing project", error_code="invalid_response")
    detail = get_session_detail(client, args.project_id, args.agent_id)
    session = detail.get("session")
    if not isinstance(session, dict):
        raise CliError("Session Detail is missing session", error_code="invalid_response")

    blockers: list[dict[str, str]] = []
    try:
        installation = load_installation_descriptor(installation_path)
    except InstallationProblem as problem:
        installation = {"configured": False, "source_root": "", "data_root": "", "path": str(installation_path)}
        blockers.append({"kind": "installation", "action": str(problem)})
    try:
        effective_data_root(installation)
    except InstallationProblem as problem:
        blockers.append({"kind": "installation_data_root", "action": str(problem)})

    running_cli_path = Path(__file__).resolve()
    running_source_root = running_cli_path.parent.parent
    configured_source_root = str(installation.get("source_root") or "")
    configured_source_path = (
        Path(posix_windows_drive_locator(configured_source_root)).expanduser()
        if configured_source_root
        else None
    )
    same_source = None
    if configured_source_path is not None:
        same_source = os.path.normcase(str(configured_source_path.resolve())) == os.path.normcase(
            str(running_source_root.resolve())
        )
        if not same_source:
            blockers.append(
                {
                    "kind": "installation_source_mismatch",
                    "action": "安装 descriptor 指向的 Source 与当前运行 CLI 不同；核对安装路径和版本后再判断运行态。",
                }
            )

    server_build: dict[str, Any] = {"state": "unknown"}
    try:
        health = client.request("GET", "/api/health")
        build = health.get("build")
        server_build = {
            "state": "available",
            "service": health.get("service"),
            "source_commit": (build or {}).get("source_commit") if isinstance(build, dict) else None,
            "release_tag": (build or {}).get("release_tag") if isinstance(build, dict) else None,
            "runtime_fingerprint": (build or {}).get("runtime_fingerprint") if isinstance(build, dict) else None,
            "static_fingerprint": (build or {}).get("static_fingerprint") if isinstance(build, dict) else None,
        }
    except CliError as problem:
        server_build["error_code"] = problem.error_code or "health_unavailable"

    root_raw = str(getattr(args, "root", None) or project.get("root_path") or "").strip()
    root = Path(posix_windows_drive_locator(root_raw)).expanduser() if root_raw else None
    workstation: dict[str, Any] = {}
    if root is None:
        blockers.append({"kind": "project_root", "action": "为 Project 配置 root_path，或在本命令提供 --root。"})
    else:
        try:
            workstation = read_fixed_workstation(root, args.agent_id, tolerate_todo_errors=True)
        except WorkstationProblem as problem:
            blockers.append({"kind": "workstation", "action": f"修复固定工位：{problem}"})
        if workstation.get("todo_error"):
            blockers.append(
                {
                    "kind": "todo_unavailable",
                    "action": "修复当前 TODO.md；orient/status 仍以 live PAOS Work 为准，不从历史 TODO 推断下一步。",
                }
            )
        todo = workstation.get("todo") if isinstance(workstation.get("todo"), dict) else {}
        todo_issues = (
            _orient_todo_contract_issues(todo, args.project_id, args.agent_id)
            if workstation and not workstation.get("todo_error")
            else []
        )
        if todo_issues:
            blockers.append(
                {
                    "kind": "todo_contract",
                    "action": "修复 TODO 当前区的身份或字段；从正式 Mail/Notice 恢复真实责任，不回退到历史 Cycle。",
                }
            )

    mail_state: dict[str, Any] = {"available": False, "count": 0, "unhandled_count": 0, "latest_received": None}
    if root is not None:
        try:
            todo_view = workstation.get("todo") if isinstance(workstation.get("todo"), dict) else {}
            if todo_view.get("schema") == "paos-todo/v3":
                mail_listing = attention_list_project_mail_inputs(
                    root=root,
                    project=project,
                    agent_id=args.agent_id,
                )
                pending_count = int(
                    mail_listing.get("unresolved_count")
                    if mail_listing.get("unresolved_count") is not None
                    else mail_listing.get("pending_count") or 0
                )
            else:
                mail_listing = list_mail(root, args.agent_id)
                pending_count = int(mail_listing.get("unhandled_count") or 0)
            items = mail_listing.get("items") or []
            latest = max(
                (item for item in items if isinstance(item, dict)),
                key=lambda item: str(item.get("created_at") or ""),
                default=None,
            )
            latest_received = None
            if latest is not None:
                if str(latest.get("input_state") or ""):
                    latest_received = {
                        "message_id": latest.get("message_id"),
                        "subject": latest.get("subject"),
                        "sender_id": latest.get("sender_id"),
                        "persisted": True,
                        "input_state": latest.get("input_state"),
                        "resolution": latest.get("resolution"),
                        "action_ref": latest.get("action_ref"),
                        "handling_source": "notice",
                    }
                else:
                    latest_received = {
                        "message_id": latest.get("message_id"),
                        "subject": latest.get("subject"),
                        "sender_id": latest.get("sender_id"),
                        "persisted": True,
                        "handled_marker": bool(latest.get("handled")),
                        "handling_state": latest.get("handling_state"),
                        "handling_reason": latest.get("handling_reason"),
                        "replied": latest.get("handling_state") == "replied",
                        "handling_error": latest.get("handling_error"),
                    }
            mail_state = {
                "available": True,
                "count": int(mail_listing.get("count") or 0),
                "unhandled_count": pending_count,
                "latest_received": latest_received,
            }
        except (MailProblem, AttentionServiceProblem) as problem:
            mail_state.update(
                {
                    "error_code": str(getattr(problem, "code", "mail_unavailable")),
                    "detail": str(problem),
                    "details": getattr(problem, "details", {}),
                }
            )
            blockers.append({"kind": "mailbox", "action": f"恢复 Workstation Mailbox：{problem}"})

    wake_view: dict[str, Any] = {
        "configured": False,
        "target_status": "unconfigured",
        "runtime": None,
        "native_session_id": None,
        "stop_present": None,
        "activation": None,
        "native_turn": {"state": "not_observed"},
    }
    if root is not None:
        wake_view = {
            **runtime_contact(root, args.agent_id),
            "activation": None,
            "native_turn": {"state": "not_observed"},
        }

    if args.message_id:
        if root is None:
            outgoing = {"state": "unavailable", "detail": "Project root is not available."}
        else:
            try:
                dispatch = dispatch_status(root, args.message_id, registry_lookup=_registry_authoritative_or_none(getattr(args, "installation_file", None)))
                deliveries = [
                    {
                        "agent_id": item.get("recipient_agent_id"),
                        "state": item.get("state"),
                    }
                    for item in dispatch.get("deliveries", [])
                    if isinstance(item, dict)
                ]
                outgoing = {
                    "state": "persisted",
                    "message_id": dispatch.get("message_id"),
                    "deliveries": deliveries,
                }
            except (MailProblem, AttentionServiceProblem) as problem:
                outgoing = {
                    "state": "unavailable",
                    "error_code": problem.code,
                    "detail": str(problem),
                    "details": problem.details,
                }
        mail_state["outgoing_message"] = outgoing

    progress = session.get("progress") if isinstance(session.get("progress"), dict) else {}
    for blocker in progress.get("blockers") or []:
        if str(blocker or "").strip():
            blockers.append({"kind": "session_progress", "action": str(blocker)})
    current_work = detail.get("current_work_item")
    work_id = str((current_work or {}).get("id") or "") if isinstance(current_work, dict) else ""
    artifacts = [
        item
        for item in detail.get("artifacts", []) or []
        if isinstance(item, dict) and (not work_id or work_id in (item.get("work_item_ids") or []))
    ]
    latest_artifact = max(
        artifacts,
        key=lambda item: str(item.get("created_at") or ""),
        default=None,
    )
    todo = workstation.get("todo") if isinstance(workstation.get("todo"), dict) else {}
    todo_trusted = bool(workstation) and not bool(workstation.get("todo_error")) and not bool(
        _orient_todo_contract_issues(todo, args.project_id, args.agent_id) if todo else ["missing"]
    )
    payload = {
        "ok": True,
        "schema": "paos-status/v1",
        "project_id": args.project_id,
        "agent_id": args.agent_id,
        "runtime": {
            "cli_path": str(running_cli_path),
            "cli_source_root": str(running_source_root),
            "cli_source_revision": _git_source_revision(running_source_root),
            "installation": {
                "descriptor_path": str(installation_path),
                "configured": bool(installation.get("configured")),
                "source_root": configured_source_root,
                "data_root": str(installation.get("data_root") or ""),
                "source_revision": _git_source_revision(configured_source_path) if configured_source_path else None,
                "matches_running_cli": same_source,
            },
            "paos_server": server_build,
        },
        "responsibility": {
            "session_status": session.get("status"),
            "todo": {
                "path": workstation.get("todo_path", ""),
                "trusted": todo_trusted,
                "current": _todo_current_view(todo) if todo_trusted else None,
                "error": workstation.get("todo_error"),
            },
            "formal_request_counts": (detail.get("mailbox") or {}).get("counts") or {},
            "next_action": _orient_next_action(
                int(((detail.get("mailbox") or {}).get("counts") or {}).get("inbox") or 0),
                int(mail_state.get("unhandled_count") or 0),
                _todo_current_view(todo) if todo_trusted else {},
                _todo_open_tasks(todo) if todo_trusted else [],
                todo_trusted,
            ),
        },
        "contact": {"workstation_mail": mail_state, "native_wake": wake_view},
        "artifact_evidence": (
            {
                "state": "registered",
                "artifact_id": latest_artifact.get("id"),
                "path": latest_artifact.get("path"),
                "purpose": latest_artifact.get("purpose"),
            }
            if latest_artifact
            else {"state": "none_registered_for_current_work"}
        ),
        "blockers": blockers,
    }
    return payload


MUTATION_RECEIPT_FIELDS = (
    "schema",
    "ok",
    "operation_id",
    "project_id",
    "session_id",
    "revision",
    "base_revision",
    "event_type",
    "event_id",
    "created_at",
    "state",
    "request_hash",
    "touched_paths",
    "allocated_ids",
    "summary",
)


def _remind_via_native(
    *,
    root: Path,
    project: dict[str, Any],
    agent_id: str,
    message_id: str,
    sender_id: str,
    subject: str,
    installation_path: Path | None = None,
) -> dict[str, Any]:
    """既有 Contact native-target → 一次 runtime_inject 的显式去点。

    Contact 目录取值使用 registry 解析（resolve_home_by_registry）所以跨
    Project Home 的 Contact 原件在**接收者自己的 Project root**；不能让发信
    方造另一份或误报未绑定；未解析 → manual_required 诚实。
    本安装登记的 Rooter Home 按 Home 类型路由到本人正式 native-target store；
    未登记的 Rooter Home → manual_required 诚实（不伪造 cross-Installation 目标）。
    Prompt 由调用方（即本 CLI）拼好，注入失败/STOP/类别错误如实返回。"""
    installation_path = installation_path or resolve_installation_path(None)
    route = _rooter_home_root(installation_path)
    if route and agent_id == route[0]:
        # Rooter Home 是本安装登记的 installation Home：只取本人正式 Home 的
        # native-target store（不查/建 Project Session，不借同事环境）。
        return _inject_from_contact_store(
            route[1],
            agent_id=agent_id,
            message_id=message_id,
            sender_id=sender_id,
            subject=subject,
        )
    if agent_id == "rooter-001":
        return {
            "agent_id": agent_id,
            "state": "manual_required",
            "reason": (
                "Rooter Home 未在本安装登记（installation descriptor 无 "
                "rooter_home）；不伪造 cross-Installation 目标。"
            ),
        }
    invoked_members = {
        str(s.get("id") or "")
        for s in (project.get("sessions") or [])
        if isinstance(s, dict)
    }
    is_cross_project = agent_id not in invoked_members
    contact_home_root = None
    if is_cross_project:
        # 跨 Project Home 的 Contact 原件在**接收者自己的 Project root**。
        # registry Home 提供真实 project_root（Windows C:/ 形态），按现有
        # posix_windows_drive_locator 转换为实际可读取的真实磁盘定位。
        try:
            home_ref = resolve_home_by_registry(agent_id)
            project_root_text = str(home_ref.get("project_root") or "").strip()
            contact_home_root = (
                Path(posix_windows_drive_locator(project_root_text))
                if project_root_text else None
            )
        except AttentionServiceProblem as problem:
            return {
                "agent_id": agent_id,
                "state": "manual_required",
                "reason": f"跨 Project Home 未能按 registry 解析：{problem}",
            }
        if contact_home_root is None or not contact_home_root.is_dir():
            return {
                "agent_id": agent_id,
                "state": "manual_required",
                "reason": "跨 Project Home 的 Contact 文件目录真实不存在。",
            }
    else:
        # 本 Project：execute_agent 已经拿到真实 root；无需读全局 registry。
        contact_home_root = Path(root)
    return _inject_from_contact_store(
        contact_home_root,
        agent_id=agent_id,
        message_id=message_id,
        sender_id=sender_id,
        subject=subject,
    )


def _inject_from_contact_store(
    contact_home_root: Path,
    *,
    agent_id: str,
    message_id: str,
    sender_id: str,
    subject: str,
) -> dict[str, Any]:
    """One-shot native reminder from a Home's own Contact native-target store.

    Shared by Project Agents and the installation-registered Rooter Home so the
    same official target drives record, status and reminder. Missing target,
    STOP, uncertain/network/rejected outcomes stay honest; nothing is resent.
    """
    target_map = load_native_targets(contact_home_root) or {}
    target = target_map.get(agent_id)
    if not isinstance(target, dict):
        return {
            "agent_id": agent_id,
            "state": "manual_required",
            "reason": f"Contact native-target 未登记在 {contact_home_root}；请正常调用 wake bind",
        }
    stop_file = str((target or {}).get("stop_file") or "")
    if stop_file and Path(posix_windows_drive_locator(stop_file)).exists():
        return {
            "agent_id": agent_id,
            "state": "native_stopped",
            "error_code": "native_stopped",
            "accepted": False,
            "retry": False,
            "repair_owner": agent_id,
            "next_action": "尊重原STOP；只有原授权主体可解除，不自动重投。",
            "reason": "STOP file present; owner explicitly paused",
        }
    message = (
        f"mail message_id {message_id} 已由 {sender_id} 持久投递到 "
        f"{agent_id} 工位 mailbox；主题为 {subject}。请实读该 durable mail，"
        "先走 Current 后原输入合同，再由本人决定下一步；本提醒只是一个"
        "原生跟进，不做业务解析。"
    )
    try:
        receipt = native_inject(target=target, message=message)
    except InjectionUncertain as problem:
        return {
            "agent_id": agent_id,
            "state": "delivery_uncertain",
            "accepted": None,
            "retry": False,
            "reason": str(problem),
            "error_type": type(problem).__name__,
            **problem.details(),
            "repair_owner": agent_id,
        }
    except (OSError, URLError, socket.timeout) as problem:
        # 保留已落 mail；网络未确认与系统真实错误不冒称 native_rejected。
        return {
            "agent_id": agent_id,
            "state": "network_unconfirmed",
            "accepted": None,
            "retry": False,
            "reason": str(problem),
            "error_type": type(problem).__name__,
        }
    except (InjectionError, ValueError) as problem:
        return {
            "agent_id": agent_id,
            "state": "native_rejected",
            "accepted": False,
            "reason": str(problem),
            "error_type": type(problem).__name__,
            **(problem.details() if isinstance(problem, InjectionError) else {}),
            "repair_owner": (agent_id if problem.repair_owner == "target_owner" else problem.repair_owner) if isinstance(problem, InjectionError) else "sender",
        }
    if not isinstance(receipt, dict) or receipt.get("accepted") is not True:
        # A call returned without its success contract; delivery is not known.
        return {
            "agent_id": agent_id,
            "state": "delivery_uncertain",
            "accepted": None,
            "retry": False,
            "reason": "native_inject returned no confirmed acceptance; do not resend",
            "error_type": "receipt_shape_unexpected",
        }
    normalized = {
        "agent_id": agent_id,
        "state": "native_accepted",
        "accepted": True,
        "runtime": receipt.get("runtime"),
        "session_id": receipt.get("session_id"),
        "http_status": receipt.get("http_status"),
        "native_state": receipt.get("native_state"),
    }
    for key in ("request_id", "reason", "error_type", "native_status_before_submit"):
        if receipt.get(key):
            normalized[key] = receipt.get(key)
    return normalized


def _compact_mutation_receipt(result: dict[str, Any]) -> dict[str, Any]:
    """Compact default mutation receipt; the full payload only via --full-result.

    Compact output keeps provenance fields (operation/revision/event/receipt,
    progress summary, replay state, handoff/activation outcome when present)
    and a small session summary; bulky history such as cycles/project history
    is dropped from this view and never re-hid under a nested "full" key.
    Failure information is never dropped, and "ok" is only reported when the
    mutation actually returned it - it is never synthesized here.
    """

    if not isinstance(result, dict):
        raise TypeError("mutation receipt must be a dict")

    def _blocked() -> bool:
        handoff = result.get("handoff")
        if isinstance(handoff, dict) and handoff.get("state") == "not_persisted":
            return True
        activation = result.get("activation")
        if isinstance(activation, dict) and (
            activation.get("error") or activation.get("uncertain")
        ):
            return True
        return (
            result.get("ok") is False
            or bool(result.get("error") or result.get("error_code"))
        )

    if result.get("full") is None and not _blocked():
        receipt = result.get("receipt") if isinstance(result.get("receipt"), dict) else {}
        compacted = {
            field: result[field]
            for field in MUTATION_RECEIPT_FIELDS
            if field in result
        }
        for field in MUTATION_RECEIPT_FIELDS:
            if field not in compacted and field in receipt:
                compacted[field] = receipt[field]
        for field in ("replayed", "handoff", "activation", "request_updates"):
            if field in result:
                compacted[field] = result[field]
        session = result.get("session") if isinstance(result.get("session"), dict) else None
        if session:
            compacted["session"] = {
                key: session[key]
                for key in ("id", "status", "current_work_item_id", "project_revision")
                if key in session
            }
            progress = session.get("progress") if isinstance(session.get("progress"), dict) else None
            if progress:
                compacted["session"]["progress"] = {
                    key: progress[key]
                    for key in ("status", "summary", "blockers", "next_actions")
                    if key in progress
                }
        if receipt:
            compacted["receipt_keys"] = sorted(receipt.keys())
        return compacted
    return result


def _compact_top(marker: dict[str, Any]) -> dict[str, Any]:
    return {field: marker[field] for field in MUTATION_RECEIPT_FIELDS if field in marker}


def _mail_item_pending(item: dict[str, Any]) -> bool:
    if str(item.get("input_state") or "") in {"pending", "handled"}:
        return str(item.get("input_state")) == "pending"
    return not bool(item.get("handled"))


def _rank_inbox_mail_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pending input first, both groups newest-first by created_at."""

    def newest_first(item: dict[str, Any]) -> str:
        return str(item.get("created_at") or "")

    pending = sorted(
        (item for item in items if _mail_item_pending(item)),
        key=newest_first,
        reverse=True,
    )
    handled = sorted(
        (item for item in items if not _mail_item_pending(item)),
        key=newest_first,
        reverse=True,
    )
    return pending + handled


def execute_inbox(
    args: argparse.Namespace,
    client: RestClient,
) -> Any:
    project_response = client.request("GET", f"/api/projects/{args.project_id}")
    project = project_response.get("project")
    if not isinstance(project, dict):
        raise CliError("Project response is missing project", error_code="invalid_response")
    detail = get_session_detail(client, args.project_id, args.agent_id)
    mailbox = detail.get("mailbox")
    if not isinstance(mailbox, dict):
        raise CliError("Session Detail is missing mailbox", error_code="invalid_response")
    root_raw = str(args.root or project.get("root_path") or "").strip()
    durable_mail: dict[str, Any] = {
        "state": "unavailable",
        "path": "",
        "count": 0,
        "items": [],
    }
    if root_raw:
        root = Path(posix_windows_drive_locator(root_raw)).expanduser()
        try:
            workstation = read_fixed_workstation(
                root,
                args.agent_id,
                tolerate_todo_errors=True,
            )
            todo_schema = str((workstation.get("todo") or {}).get("schema") or "")
            if todo_schema == "paos-todo/v3":
                listed = attention_list_project_mail_inputs(
                    root=root,
                    project=project,
                    agent_id=args.agent_id,
                )
                pending_count = int(
                    listed.get("unresolved_count")
                    if listed.get("unresolved_count") is not None
                    else listed.get("pending_count") or 0
                )
                path_value = str(root / "Workstations" / args.agent_id / "mailbox")
            else:
                listed = list_mail(root, args.agent_id)
                pending_count = int(listed.get("unhandled_count") or 0)
                path_value = str(listed.get("mailbox_path") or "")
            ranked = _rank_inbox_mail_items(listed.get("items", []) or [])
            shown = ranked[:6]
            pending_shown = sum(1 for item in shown if _mail_item_pending(item))
            durable_mail = {
                "state": "ready",
                "path": path_value,
                "count": listed.get("count", 0),
                "unhandled_count": pending_count,
                "items": shown,
                "items_shown": len(shown),
                "unhandled_hidden": max(0, pending_count - pending_shown),
                "omitted": max(0, int(listed.get("count", 0)) - 6),
                "ordering": "pending first, then by created_at descending",
                "expand_with": f"paos mail list {args.project_id} {args.agent_id}",
            }
        except (MailProblem, AttentionServiceProblem, WorkstationProblem) as problem:
            durable_mail.update(
                {
                    "state": "missing" if problem.code == "mailbox_missing" else "unreadable",
                    "error_code": problem.code,
                    "detail": str(problem),
                    "path": (problem.details or {}).get("path", ""),
                }
            )
    else:
        durable_mail["detail"] = "Project 未登记 root_path，且未提供 --root。"

    payload = {
        "ok": True,
        "schema": INBOX_SCHEMA,
        "project_id": args.project_id,
        "agent_id": args.agent_id,
        "project_revision": detail.get("project_revision"),
        "durable_mail": durable_mail,
        "formal_requests": compact_mailbox(mailbox),
        "runtime_reachability": {"state": "unknown", "checked": False},
        "message_consumption": {"state": "not_observed", "source": "inbox read does not inspect CAT Exchanges or native Runtime turns"},
        "business_result_delivery": {"state": "not_inferred"},
        "business_acceptance": {"state": "not_inferred"},
        "expand": {
            "request_details": f"paos session mailbox {args.project_id} {args.agent_id}",
            "mail_list": f"paos mail list {args.project_id} {args.agent_id}",
            "project": f"paos project show {args.project_id}",
        },
    }
    if args.json_output:
        return payload
    lines = [
        f"PAOS inbox — {args.agent_id} @ {args.project_id}",
        f"Durable Workstation Mail: {durable_mail.get('state')} ({durable_mail.get('count', 0)})；未处理 {durable_mail.get('unhandled_count', 0)}；其余用 {durable_mail.get('expand_with', 'paos mail list …')} 查看",
        f"Formal Request inbox/waiting: {(payload['formal_requests'].get('counts') or {}).get('inbox', 0)}/{(payload['formal_requests'].get('counts') or {}).get('waiting', 0)}",
        "Runtime reachability: unknown (not probed)",
        "Message consumption/reply: not observed by this read",
        "Business result delivery/acceptance: not inferred from Mail or Request presence",
    ]
    for item in durable_mail.get("items") or []:
        marker = " [未处理]" if _mail_item_pending(item) else ""
        lines.append(f"  Mail{marker} · {item.get('message_id')}: {item.get('subject') or ''}")
    if durable_mail.get("omitted"):
        lines.append(
            f"  …其余 {durable_mail['omitted']} 封用 {durable_mail.get('expand_with', 'paos mail list …')} 查看"
            f"（未处理隐藏 {durable_mail.get('unhandled_hidden', 0)} 封）"
        )
    for item in (payload["formal_requests"].get("inbox") or []):
        lines.append(f"  Request · {item.get('request_id')} [{item.get('status')}] {item.get('description') or ''}")
    return "\n".join(lines)


def _roster_root(
    args: argparse.Namespace,
    client: RestClient,
) -> tuple[Path, dict[str, Any]]:
    project = client.request("GET", f"/api/projects/{args.project_id}")["project"]
    root_raw = str(getattr(args, "root", None) or project.get("root_path") or "").strip()
    if not root_raw:
        raise CliError(
            "未提供 --root，且 Project 没有 root_path；无法定位 Workstations。",
            error_code="contact_project_root_missing",
        )
    root = Path(posix_windows_drive_locator(root_raw)).expanduser()
    return root, project


def _apply_fresh_probe(root: Path, entry: dict[str, Any]) -> None:
    """Workless: no automatic probing；状态保持 never probed。"""
    runtime = entry["runtime_contact"]
    runtime.update({"state_basis": "probe_never_run", "checked_at": None})


def execute_ports(args: argparse.Namespace, client: RestClient) -> Any:
    project_roots = []
    items = (client.request("GET", "/api/projects") or {}).get("items") or []
    for project in items:
        raw_root = str(project.get("root_path") or "").strip()
        if raw_root:
            project_roots.append(
                (str(project.get("id")), Path(posix_windows_drive_locator(raw_root)).expanduser())
            )
    from paos_ports import build_ports_view, PortsProblem, render_ports_markdown  # noqa: PLC0415

    view = build_ports_view(
        installation=load_installation_descriptor(resolve_installation_path()),
        core_base_url=client.base_url,
        cat_base_url=os.environ.get("PAOS_CAT_BASE_URL") or None,
        project_roots=project_roots,
        probed=bool(getattr(args, "probe", True)),
        probe_host=getattr(args, "probe_host", None) or None,
    )
    if getattr(args, "json_output", False):
        return view
    print(render_ports_markdown(view))
    return None


def execute_home(args: argparse.Namespace, client: RestClient) -> Any:
    """Read-only same-source home view; optional PAOS-HOME.md region write."""
    data = client.request("GET", "/api/home") or {}
    markdown = str(data.get("markdown") or "")
    if getattr(args, "write", None):
        home_module_dir = Path(__file__).resolve().parents[1] / "attention-dashboard-v1-static"
        if str(home_module_dir) not in sys.path:
            sys.path.insert(0, str(home_module_dir))
        from home_readmodel import (  # noqa: PLC0415
            HomeWriteProblem,
            apply_generated_region_bytes,
        )

        target = Path(posix_windows_drive_locator(str(args.write))).expanduser()
        if not target.is_file():
            raise CliError(
                f"目标文件不存在：{target}",
                error_code="home_target_missing",
                hint="PAOS-HOME.md 由入口 owner 维护；生成区标记需在既有文件内预先明确。",
            )
        existing = target.read_bytes()
        new_bytes = apply_generated_region_bytes(existing, markdown.encode("utf-8"))
        target.write_bytes(new_bytes)
        return {
            "ok": True,
            "written": str(target),
            "captured_at": (data.get("view") or {}).get("captured_at"),
            "note": "仅替换 PAOS-HOME:GENERATED 生成区；生成区外字节原样保留（换行风格按标记间原字节）",
        }
    if getattr(args, "json_output", False):
        return data.get("view") or data
    print(markdown.rstrip())
    return None


def execute_team(
    args: argparse.Namespace,
    client: RestClient,
) -> Any:
    root, project = _roster_root(args, client)
    numbers_map = _staff_numbers_map(args)
    agents = build_team_rows(project, root, numbers_map=numbers_map)["agents"]
    for entry in agents:
        if bool(getattr(args, "probe", False)):
            _apply_fresh_probe(root, entry)
    installation = load_installation_descriptor(resolve_installation_path())
    payload = {
        "ok": True,
        "schema": CONTACT_SCHEMA,
        "project_id": args.project_id,
        "agent_id": args.agent_id,
        "roster_filter": "fixed_workstation",
        "agents": agents,
        "meta": {
            "base_url": client.base_url,
            "installation": installation,
            "note": (
                "TEAM=长期固定工位名册，与 Session 状态分离；历史 probe 不声称现在在线；"
                "只有 --probe 的 fresh 结果或 last_probe 附检查时间。在线 attach 与离线人工启动分开；本命令不启动 Harness。"
            ),
        },
    }
    if args.json_output:
        return payload
    return render_contact(payload, include_self=True)


def execute_peers(args: argparse.Namespace, client: RestClient) -> Any:
    root, project = _roster_root(args, client)
    numbers_map = _staff_numbers_map(args)
    # peers 与 team 共用 TEAM 长期固定工位名册（fixed_workstation 接线），
    # 排除请求本人；既有 JSON 读面键保留。Session 状态退为历史事实
    # （completed/abandoned 但正式 Home 在 → 仍列出）；名册在场不冒称在线
    # （无 --probe 不探测/启动模型、online 状态保持未知）。读面不写数据。
    roster = build_team_rows(project, root, numbers_map=numbers_map)["agents"]
    peers: list[dict[str, Any]] = [
        entry
        for entry in roster
        if str(entry.get("agent_id") or "") != str(args.agent_id)
    ]
    if bool(getattr(args, "probe", False)):
        for entry in peers:
            _apply_fresh_probe(root, entry)
    payload = {
        "ok": True,
        "schema": PEERS_SCHEMA,
        "project_id": args.project_id,
        "agent_id": args.agent_id,
        "roster_filter": "fixed_workstation",
        "peers": peers,
    }
    if args.json_output:
        return payload
    return render_contact(payload, include_self=False)



def _staff_numbers_map(args: argparse.Namespace) -> dict[str, str]:
    """Read-only staff-number lookup for contact rows; unknown agents stay blank."""
    try:
        resolved_installation_path = resolve_installation_path(
            getattr(args, "installation_file", None)
        )
        numbers_path = resolve_numbers_path(
            getattr(args, "agent_numbers_file", None),
            resolved_installation_path,
        )
        from paos_agent_numbers import load_numbers

        return load_numbers(numbers_path)
    except Exception:
        return {}


def render_contact(payload: dict[str, Any], *, include_self: bool) -> str:
    label = "team" if (payload.get("schema") or "") == CONTACT_SCHEMA else "peers"
    agents = payload.get("agents") if include_self else (payload.get("peers") or [])
    body = dict(payload)
    body["agents"] = agents
    body["agent_id"] = payload.get("agent_id")
    filter_note = payload.get("roster_filter") or "unknown"
    lines = [
        f"PAOS {label} — {payload.get('agent_id')} @ {payload.get('project_id')}",
        f"Roster ({filter_note}): {len(agents)}",
    ]
    parse_team_payload(body, lines)
    meta = payload.get("meta") or {}
    installation = meta.get("installation") or {}
    if isinstance(installation, dict) and installation:
        lines.append(f"Installation locator: {installation.get('path') or 'not configured'}")
        if installation.get("source_root"):
            lines.append(f"Source root: {installation.get('source_root')}")
    if isinstance(meta.get("base_url"), str):
        lines.append(f"base_url: {meta['base_url']}")
    note = str(meta.get("note") or "")
    if note:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def build_session_update_payload(
    *,
    op: str,
    revision: int,
    session_id: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "paos-session-update/v1",
        "operation_id": op,
        "base_revision": revision,
        "session_id": session_id,
        **fields,
    }


def complete_version_ref(args: argparse.Namespace) -> dict[str, str] | None:
    values = {
        "provider": getattr(args, "version_provider", None),
        "revision": getattr(args, "version_revision", None),
        "path": getattr(args, "version_path", None),
    }
    present = [bool(str(value or "").strip()) for value in values.values()]
    if any(present) and not all(present):
        raise CliError(
            "--version-provider, --version-revision and --version-path must be provided together",
            error_code="incomplete_version_ref",
        )
    if not all(present):
        return None
    return {key: str(value).strip() for key, value in values.items()}




def _allocate_staff_number(args: argparse.Namespace, installation_path: Path) -> str:
    try:
        return allocate_number(
            resolve_numbers_path(
                getattr(args, "agent_numbers_file", None),
                installation_path,
            ),
            args.session_id,
        )
    except NumbersProblem as exc:
        if getattr(exc, "code", None) == "agent_numbers_not_configured":
            return ""
        raise


def execute_workstation(
    args: argparse.Namespace,
    client: RestClient,
    installation_path: Path,
) -> dict[str, Any]:
    """Runtime-local workspace preflight / cycle-bound materialization."""
    project = client.request("GET", f"/api/projects/{args.project_id}")["project"]
    root_raw = args.root or str(project.get("root_path") or "").strip()
    if not root_raw:
        raise CliError(
            "未提供 --root，且 Project 没有 root_path；无法选择工作区。",
            error_code="workstation_root_missing",
            hint="请显式传入 --root，或在 Project 中登记 root_path。",
        )
    root_raw = posix_windows_drive_locator(root_raw)
    root = Path(root_raw).expanduser()

    if args.workstation_command == "init":
        detail = get_session_detail(client, args.project_id, args.session_id)
        session = detail.get("session") or {}
        workflow_library = str(getattr(args, "workflow_library", None) or "")
        skill_library = str(getattr(args, "skill_library", None) or "")
        try:
            if not workflow_library or not skill_library:
                installation = load_installation_descriptor(installation_path)
                roots_path = resolve_library_roots_path(installation=installation)
                roots = load_library_roots(roots_path)
                if not workflow_library:
                    workflow_library = str(roots.get("workflow_root") or "")
                if not skill_library:
                    skill_library = str(roots.get("skill_root") or "")
            staff = _allocate_staff_number(args, installation_path)
            result = ensure_fixed_workstation(
                root=root,
                project=project,
                session=session,
                objective=str(getattr(args, "objective", None) or ""),
                workflow_library=workflow_library,
                skill_library=skill_library,
                staff_number=staff,
            )
        except (WorkstationProblem, LibraryProblem, InstallationProblem) as problem:
            raise CliError(
                str(problem),
                error_code=getattr(problem, "code", "workstation_error"),
                details=problem.details,
            ) from None
        return {
            "ok": True,
            "schema": "paos-workstation-home/v1",
            **result,
        }

    if args.workstation_command == "show":
        try:
            result = read_fixed_workstation(root, args.session_id)
        except WorkstationProblem as problem:
            raise CliError(
                str(problem),
                error_code=problem.code,
                details=problem.details,
            ) from None
        return {
            "ok": True,
            "schema": "paos-workstation-home-view/v1",
            "project_id": args.project_id,
            "agent_id": args.session_id,
            **result,
        }

    if args.workstation_command == "guide-diff":
        try:
            result = build_guide_diff(
                Path(posix_windows_drive_locator(str(args.candidate))).expanduser(),
                canonical_src=Path(
                    posix_windows_drive_locator(str(args.canonical))
                ).expanduser(),
            )
        except GuideProblem as problem:
            raise CliError(
                str(problem), error_code=problem.code, details=problem.details
            ) from None
        return {"ok": True, **result}

def _home_uses_todo_v3(root: Path, agent_id: str) -> bool:
    """Home 合同只按固定工位 TODO frontmatter schema 判定，与公开服务的
    `_assert_home_v3` 实时口径一致（TODO.md 存在且标识 `schema: paos-todo/v3`）。

    Current 正文（字段/区段）解析失败——例如 todo_v3_notify_after_invalid
    ——不把 V3 Home 误判为 legacy：解析错误由 Home 状态视图如实呈现并保留
    可定位错误码；send/notify 仍走持久 Mail + Notice/intent，与原生注入分离。
    真实结构/读取错误（工位双入口、TODO.md 读失败）以可定位异常拒绝，不用
    False 掩盖成 legacy；TODO 缺失=未被迁移的 V1.2 Home 按现存明确 legacy
    合同路由。不制造新兼容框架。"""

    def _frontmatter_schema(raw: bytes) -> str:
        for line in raw.splitlines():
            text = line.decode("utf-8", "replace").strip()
            if text.startswith("schema:"):
                return text.split(":", 1)[1].strip().strip('"')
        return ""

    legacy_entry = root / ".paos" / "agents" / agent_id / "ENTRY.md"
    if legacy_entry.exists():
        raise WorkstationProblem(
            "workstation_dual_entry_detected",
            "同时发现 V1.1 固定工位与旧 .paos Agent ENTRY；拒绝静默选择入口。",
            {
                "legacy_entry_path": str(legacy_entry),
                "fixed_entry_path": str(root / "Workstations" / agent_id / "ENTRY.md"),
                "recovery": "运行 workstation init 完成旧生成入口退役；若旧文件含人为内容，先人工确认并移走。",
            },
        )
    todo_file = root / "Workstations" / agent_id / "TODO.md"
    if todo_file.is_symlink() or (not todo_file.is_file() and todo_file.exists()):
        raise WorkstationProblem(
            "workstation_todo_unreadable",
            f"固定工位 TODO.md 定位异常（符号链接/目录冲突），拒绝解读合同：{todo_file}",
            {"todo_path": str(todo_file)},
        )
    if not todo_file.is_file():
        # TODO 缺失=未被迁移的 V1.2 Home；按现存明确 legacy 合同路由。
        return False
    try:
        raw = todo_file.read_bytes()[:4096]
    except OSError as exc:
        # 真实读取失败必须可定位拒绝，不得用 False 掩盖成 legacy。
        raise WorkstationProblem(
            "workstation_todo_unreadable",
            f"无法读取固定工位 TODO.md：{todo_file}",
            {"todo_path": str(todo_file), "reason": str(exc)},
        ) from exc
    return _frontmatter_schema(raw) == "paos-todo/v3"



def _resolve_staff_number_recipients(args: argparse.Namespace) -> list[str]:
    """Human 统一 S 号寻址：`--to`/`--agents` 中的 `Sxxx`（列表或单字符串，
    如 chat --to S032 / mail --to S032）经真实注册登记反查为完整 Agent ID，
    再进入原路由；未注册/歧义/形态错误直接报错，不按目录后缀猜。
    CLI `--agent-numbers-file` 与 `--installation-file` 是同一登记事实源。"""
    registry_path = getattr(args, "agent_numbers_file", None)
    installation_path = getattr(args, "installation_file", None) or resolve_installation_path()
    resolved: list[str] = []

    def _swap(token: str) -> str:
        token = str(token).strip()
        if token.upper().startswith("S") and token[1:].isdigit():
            return agent_id_for_staff_number(token, explicit_path=registry_path, installation_path=installation_path)
        return token

    to_value = getattr(args, "to", None)
    if isinstance(to_value, list):
        args.to = [_swap(raw) for raw in list(to_value)]
        resolved = list(args.to)
    elif isinstance(to_value, (str, bytes)) and str(to_value or "").strip():
        args.to = _swap(str(to_value))
    agents = getattr(args, "agents", None)
    if isinstance(agents, list):
        args.agents = [_swap(raw) for raw in list(agents)]
    return resolved


def _cross_project_target_lookup(
    client: RestClient,
    root: Path,
    target_agent_id: str,
) -> Callable[[str], dict[str, Any]] | None:
    """Cross-project targeted CAT lookup: routes only when the recipient is
    a PRECISE registered member of its own project (deterministic `<pid>-sxxx`
    convention) whose registered Home actually exists — never a guessed
    home/participant.  paos-todo/v3 enforcement is done by the service
    (`_assert_home_v3` → `attention_home_not_v3`), so callers verify
    membership + house existence only.  Returns a lookup callable or None
    (None => keep the invoked-project path unchanged)."""
    try:
        project_id = agent_project_id(target_agent_id)
        project = client.request("GET", f"/api/projects/{project_id}").get("project")
    except (CliError, AgentActivationProblem, HomeProblem):
        # Non-convention ids (rooter-001 etc.) never enter the cross-project
        # branch: keep the invoked-project path unchanged instead of leaking.
        return None
    if not isinstance(project, dict):
        return None
    sessions = [i for i in (project.get("sessions") or []) if isinstance(i, dict)]
    if not any(str(i.get("id") or "") == target_agent_id for i in sessions):
        return None
    # NOTE: v3 enforcement happens in the service (`_assert_home_v3` raises
    # `attention_home_not_v3`), so non-v3 targets get the precise error code
    # instead of a misleading home_agent_unknown.
    return lambda _pid: project

def _recipient_contract(
    *,
    root: Path,
    recipients: list[str],
) -> str:
    if not recipients:
        return "empty"
    v3 = [
        agent_id
        for agent_id in recipients
        if _home_uses_todo_v3(root, agent_id)
    ]
    if not v3:
        return "legacy"
    if len(v3) == len(recipients):
        return "v3"
    raise CliError(
        "接收者同时存在 v2/v3 Home；切换窗口内拒绝混用两套输入/activation 路径。",
        error_code="v13_mixed_home_contract",
        details={
            "v3_agents": v3,
            "legacy_agents": [
                agent_id for agent_id in recipients if agent_id not in v3
            ],
        },
    )


def _registered_rooter_home(
    installation_path: Path,
    *,
    home_id: str = "rooter-001",
    require_todo_v3: bool = True,
) -> dict[str, Any]:
    try:
        descriptor = load_installation_descriptor(installation_path)
    except InstallationProblem as problem:
        raise CliError(
            str(problem),
            error_code=problem.code,
            details=problem.details,
        ) from None
    rooter_home = str(descriptor.get("rooter_home") or "").strip()
    if not descriptor.get("configured") or not rooter_home:
        raise CliError(
            "installation descriptor 未登记 Rooter Home。",
            error_code="rooter_home_not_registered",
            hint="先用 paos install configure --rooter-home <absolute-path> 登记。",
        )
    try:
        return attention_resolve_rooter_home(
            home_path=rooter_home,
            home_id=home_id,
            require_todo_v3=require_todo_v3,
        )
    except AttentionServiceProblem as problem:
        raise CliError(
            str(problem),
            error_code=problem.code,
            details=problem.details,
        ) from None


def _rooter_home_root(installation_path: Path) -> tuple[str, Path] | None:
    """Resolve the installation-registered Rooter Home as (home_id, real root).

    Returns None when the descriptor is unconfigured or has no rooter_home.
    Callers route wake/reminder by Home type instead of assuming a Project
    Session; this never fabricates a Rooter Home or its native-target store.
    """
    try:
        descriptor = load_installation_descriptor(installation_path)
    except InstallationProblem:
        return None
    if not descriptor.get("configured"):
        return None
    rooter_home = str(descriptor.get("rooter_home") or "").strip()
    if not rooter_home:
        return None
    root = Path(posix_windows_drive_locator(rooter_home)).expanduser()
    return (root.name, root)


def _registry_authoritative_or_none(explicit_installation_file: str | None = None):
    """安装配置缺席（无描述文件）时返回 None：显式走既有桌面同 Project 合同。
    配置存在 → 返回 registry resolver；登记失败如实传播（不静默降级）。
    路径解析全部沿 paos_installation 既有服务工具，不在 CLI 里自建第二份
    安装/registry 目录判断。"""
    installation_path = resolve_installation_path(explicit_installation_file)
    if not installation_path.is_file():
        return None
    return lambda agent_id: resolve_home_by_registry(
        agent_id, installation_file=str(installation_path)
    )


def _parse_todo_update_sets(sets: list[str]) -> dict[str, Any]:
    """Parse repeatable `--set FIELD=VALUE` into a Current-field update dict.

    List fields (result_refs/context_refs) collect each value in order. A pair
    without `=` or an empty field name is an explicit usage error, not a guess.
    """
    updates: dict[str, Any] = {}
    for raw in sets or []:
        text = str(raw)
        if "=" not in text:
            raise CliError(
                f"--set 需要 FIELD=VALUE 形态：{text!r}",
                error_code="attention_todo_update_bad_pair",
            )
        name, value = text.split("=", 1)
        name = name.strip()
        if not name:
            raise CliError(
                f"--set 字段名不能为空：{text!r}",
                error_code="attention_todo_update_bad_pair",
            )
        if name in attention_todo_list_fields:
            updates.setdefault(name, []).append(value)
        else:
            updates[name] = value
    return updates


def _todo_write_receipt(write_result: dict[str, Any]) -> dict[str, Any]:
    """写回执精简（T-053 延续）：成功/错误仍如实，Home/路径/当前动作/任务计数
    可定位；完整 TODO 与任务正文仍由 show/orient 读，不把任务正文/历史当回执。
    服务层 write_home_todo 合同完整保留（全文仍真实写入）；不吞错误、不改
    写入事实、无新框架。"""
    todo = write_result.get("todo") or {}
    current = todo.get("current") or {}
    receipt = {
        "schema": write_result.get("schema"),
        "home": write_result.get("home"),
        "todo": {
            "schema": todo.get("schema"),
            "home_kind": todo.get("home_kind"),
            "home_id": todo.get("home_id"),
            "project_id": todo.get("project_id"),
            "current": {
                "stage": current.get("stage"),
                "next_action": current.get("next_action"),
            },
            "counts": todo.get("counts") or {},
        },
        "written_sha_tier": write_result.get("written_sha_tier"),
    }
    if "projection" in write_result:
        receipt["projection"] = write_result["projection"]
    return receipt


def execute_agent(
    args: argparse.Namespace,
    client: RestClient,
    installation_path: Path | None = None,
) -> dict[str, Any]:
    """Agent-first durable communication (durable delivery + persisted intent only); an independent wake trigger is executed once by a legitimate native caller."""
    project = client.request("GET", f"/api/projects/{args.project_id}")["project"]
    root_raw = str(getattr(args, "root", None) or project.get("root_path") or "").strip()
    if not root_raw:
        raise CliError(
            "未提供 --root，且 Project 没有 root_path；无法定位 Agent activation state。",
            error_code="agent_activation_project_root_missing",
        )
    root = Path(posix_windows_drive_locator(root_raw)).expanduser()
    _resolve_staff_number_recipients(args)

    try:
        if args.agent_command == "send":
            frozen = resolve_recipients(
                project,
                recipients=list(args.to or []),
                broadcast=bool(args.broadcast),
                registry_lookup=resolve_home_by_registry,
            )
            invoked_members = {
                str(item.get("id") or "")
                for item in (project.get("sessions") or [])
                if isinstance(item, dict)
            }
            local_recipients = [value for value in frozen if value in invoked_members]
            cross_present = len(local_recipients) < len(frozen)
            # 统一 S 号/跨 Project 合同：任一 recipient 经 registry 定位出
            # 对方真实 Home 时走 Home 轴服务路径（逐 recipient 分流：本 Project
            # 工位直接投递+Notice，跨 Project/Rooter 走 registry 外投）；纯本
            # Project 维持原 v3/legacy 合同判断。
            send_remind = bool(getattr(args, "remind", False))
            mail_sender_id = str(args.sender_id or "")
            mail_subject = text_arg(args.subject, "mail subject", required=True)
            normal_delivered = set()
            if cross_present or _recipient_contract(root=root, recipients=local_recipients or frozen) == "v3":
                send_result = {
                    "ok": True,
                    **attention_send_mail_source(
                        root=root,
                        project=project,
                        subject=mail_subject,
                        body=text_arg(args.body, "mail body"),
                        recipients=list(args.to or []),
                        broadcast=bool(args.broadcast),
                        sender_kind=str(args.sender_kind or "human"),
                        sender_id=mail_sender_id,
                        message_id=str(args.message_id or ""),
                        request_activation=True,
                    ),
                }
            else:
                send_result = {
                    "ok": True,
                    **send_agent_mail(
                        root=root,
                        project=project,
                        subject=mail_subject,
                        body=text_arg(args.body, "mail body"),
                        recipients=list(args.to or []),
                        broadcast=bool(args.broadcast),
                        sender_kind=str(args.sender_kind or "human"),
                        sender_id=mail_sender_id,
                        message_id=str(args.message_id or ""),
                    ),
                }
            message_id_used = str((send_result.get("mail") or {}).get("message_id") or "")
            # **本次真实新投递集合**（S010 窄修 #2）：external_routes 中
            # `already_delivered` 是已收件的同 ID replay 件不进入再提醒集合。
            normal_delivered: set[str] = set()
            for entry in (send_result.get("mail") or {}).get("deliveries") or []:
                if isinstance(entry, dict):
                    agent_id = str(entry.get("recipient_agent_id") or "")
                    state_field = str(entry.get("state") or entry.get("delivery_state") or "")
                    if agent_id and state_field in {"delivered"}:
                        normal_delivered.add(agent_id)
            for route in (send_result.get("notices") or {}).get("external_routes") or []:
                if isinstance(route, dict):
                    mail_state = str(route.get("mail_state") or "")
                    if mail_state == "delivered":
                        normal_delivered.add(str(route.get("recipient") or ""))
                    # already_delivered → 已投递的 replay 件仅报告，不注入
            reminders: list[dict[str, Any]] = []
            if send_remind:
                reminders.extend(
                    _remind_via_native(
                        root=root,
                        project=project,
                        agent_id=agent_id,
                        message_id=message_id_used,
                        sender_id=mail_sender_id,
                        subject=mail_subject,
                        installation_path=installation_path,
                    )
                    for agent_id in sorted(normal_delivered)
                )
            confirmed_wake = any(r.get("accepted") is True for r in reminders)
            unknown_wake = any(r.get("state") in {"delivery_uncertain", "network_unconfirmed"} for r in reminders)
            send_result = {
                **send_result,
                "reminders": reminders,
                "runtime_wake_performed": True if confirmed_wake else None if unknown_wake else False,
            }
            # Short output semantics per S010（round-3）：
            #   - 普通 default agent send → 全部短回执（含已读取的 Notice 真实
            #     状态；无读端事实时是 not_observed），不把值硬编为 true。
            #   - --json: 完整机器字段（原 full 原件）。
            #   - --full-result: 原 full 原件。
            home_deliveries_list = sorted(
                normal_delivered
            )
            send_result.setdefault("home_deliveries", home_deliveries_list)
            projected = send_result.get("notices") or {}
            # Real Notice states only, from the two places the send actually
            # wrote them: same-Project dispatch items and cross-Project
            # external_routes (each route reports the state that its own
            # create_notice persisted). No guessing from Mail delivery and no
            # scanning other Homes.
            actual_notice_states = [
                str(item.get("state") or "")
                for item in projected.get("items") or []
                if isinstance(item, dict)
            ]
            actual_notice_states.extend(
                str(route.get("notice_state") or "")
                for route in projected.get("external_routes") or []
                if isinstance(route, dict)
            )
            if "pending" in actual_notice_states:
                pending_notice = "pending"
            elif "handled" in actual_notice_states:
                pending_notice = "handled"
            else:
                # replay 可能已 handled；未读到消费事实则 not_observed，不冒充。
                pending_notice = "not_observed"
            short_view = {
                "ok": send_result.get("ok"),
                "message_id": message_id_used,
                "home_deliveries": home_deliveries_list,
                "pending_notice": pending_notice,
                "reminders": reminders,
                "runtime_wake_performed": send_result["runtime_wake_performed"],
                "next_action": (
                    "native accepted → 等本人真实消费 Orientation/Current；"
                    "delivery_uncertain / network_unconfirmed → Mail 已落盘，原生未确认，不得重发或换路；"
                    "manual_required / native_rejected → 显式一次提醒未真实到达，"
                    "按 Contact 正常入口手动以同一 message_id 真实对接。"
                ),
            }
            argjson = bool(getattr(args, "json_output", False))
            fullresult = bool(getattr(args, "full_result", False))
            if fullresult or argjson:
                return send_result
            return {"ok": send_result.get("ok"), **short_view}

        if args.agent_command == "chat":
            target = str(args.to)
            cross_lookup = None
            if _recipient_contract(root=root, recipients=[target]) != "v3":
                # Same-project targets (legacy or not) keep the ORIGINAL
                # legacy path: only a genuinely cross-project recipient (not
                # a member of the invoked project) may attempt the lookup.
                invoked_members = {
                    str(i.get("id") or "")
                    for i in (project.get("sessions") or [])
                    if isinstance(i, dict)
                }
                if target not in invoked_members:
                    cross_lookup = _cross_project_target_lookup(
                        client, root, target
                    )
            if cross_lookup is not None or _recipient_contract(root=root, recipients=[target]) == "v3":
                return {
                    "ok": True,
                    **attention_send_cat_source(
                        root=root,
                        project=project,
                        cat_base=str(args.cat_base or ""),
                        room_id=str(args.room),
                        target_agent_id=target,
                        content=text_arg(args.body, "CAT message body", required=True),
                        sender_agent_id=str(args.from_agent or ""),
                        message_id=str(args.message_id or ""),
                        reply_to=str(args.reply_to or ""),
                        request_activation=True,
                        target_project_lookup=cross_lookup,
                    ),
                }
            return {
                "ok": True,
                **send_cat_agent_message(
                    root=root,
                    project_id=args.project_id,
                    cat_base=str(args.cat_base or ""),
                    room_id=str(args.room),
                    target_agent_id=target,
                    content=text_arg(args.body, "CAT message body", required=True),
                    sender_agent_id=str(args.from_agent or ""),
                    message_id=str(args.message_id or ""),
                    reply_to=str(args.reply_to or ""),
                ),
            }

        if args.agent_command == "notify":
            if args.mail_message_id:
                source = dispatch_status(root, str(args.mail_message_id), registry_lookup=_registry_authoritative_or_none(getattr(args, "installation_file", None)))
                frozen = [
                    str(value)
                    for value in (source.get("recipients") or [])
                    if str(value or "").strip()
                ]
                selected = list(args.agents or []) or frozen
                if _recipient_contract(root=root, recipients=selected) == "v3":
                    return {
                        "ok": True,
                        **attention_request_mail_activation(
                            root=root,
                            project=project,
                            message_id=str(args.mail_message_id),
                            agents=list(args.agents or []),
                            activation_request_id=str(
                                getattr(args, "activation_request_id", None) or ""
                            ),
                        ),
                    }
                return {
                    "ok": True,
                    **activate_mail_dispatch(
                        root=root,
                        project_id=args.project_id,
                        message_id=str(args.mail_message_id),
                        agents=list(args.agents or []),
                    ),
                }

            if args.cat_exchange_ref:
                room_id, sep, exchange_id = str(args.cat_exchange_ref).partition(":")
                if not sep or not room_id or not exchange_id:
                    raise CliError(
                        "--cat-exchange 必须使用 <room-id>:<exchange-id>。",
                        error_code="cat_exchange_ref_invalid",
                    )
                selected = list(args.agents or [])
                if len(selected) > 1:
                    raise CliError(
                        "CAT Exchange 只能映射一个 target Agent；--agent 最多指定一次。",
                        error_code="cat_agent_selector_invalid",
                    )
                expected = selected[0] if selected else ""
                verified = verify_cat_exchange_source(
                    project_id=args.project_id,
                    cat_base=str(args.cat_base or ""),
                    room_id=room_id,
                    exchange_id=exchange_id,
                    expected_agent_id=expected,
                )
                target = str(verified.get("agent_id") or "")
                if _recipient_contract(root=root, recipients=[target]) == "v3":
                    return {
                        "ok": True,
                        **attention_request_cat_activation(
                            root=root,
                            project=project,
                            cat_base=str(args.cat_base or ""),
                            room_id=room_id,
                            exchange_id=exchange_id,
                            expected_agent_id=expected,
                            activation_request_id=str(
                                getattr(args, "activation_request_id", None) or ""
                            ),
                        ),
                    }
                return {
                    "ok": True,
                    **activate_cat_exchange(
                        root=root,
                        project_id=args.project_id,
                        cat_base=str(args.cat_base or ""),
                        room_id=room_id,
                        exchange_id=exchange_id,
                        expected_agent_id=expected,
                    ),
                }
    except (
        AgentActivationProblem,
        CatActivationProblem,
        AttentionServiceProblem,
        MailProblem,
        WorkstationProblem,
    ) as problem:
        raise CliError(
            str(problem),
            error_code=getattr(problem, "code", "agent_activation_error"),
            details=getattr(problem, "details", {}),
        ) from None

    raise CliError(
        f"Unsupported agent command: {args.agent_command}",
        error_code="unsupported_command",
    )

def _refresh_workbench_notice(
    installation_path: Path, home_ref: dict[str, Any], result: dict[str, Any],
    notice_id: str,
) -> dict[str, Any]:
    try:
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "attention-dashboard-v1-static"))
        from workbench_markdown import refresh_home_after_notice

        notice = result.get("notice") if isinstance(result.get("notice"), dict) else result
        page = refresh_home_after_notice(
            installation_path, home_ref, notice_id=notice_id,
            state=str(notice.get("state") or "pending"),
            read=bool(notice.get("read")),
        )
    except Exception as error:  # noqa: BLE001 - business write already committed
        result["projection"] = {"ok": False, "error_code": "workbench_projection_failed", "error": type(error).__name__}
        return result
    if page.get("status") == "conflict":
        result["projection"] = {"ok": False, "error_code": "workbench_projection_conflict", "page": page.get("page")}
    else:
        result["projection"] = {"ok": True, "page": page.get("page"), "status": page.get("status")}
    return result


def _refresh_workbench_fast(installation_path: Path, home_ref: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    try:
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "attention-dashboard-v1-static"))
        from workbench_markdown import refresh_home_after_todo

        page = refresh_home_after_todo(installation_path, home_ref)
    except Exception as error:  # noqa: BLE001 - business write already committed
        result["projection"] = {"ok": False, "error_code": "workbench_projection_failed", "error": type(error).__name__}
        return result
    if page.get("status") == "conflict":
        result["projection"] = {"ok": False, "error_code": "workbench_projection_conflict", "page": page.get("page")}
    else:
        result["projection"] = {"ok": True, "page": page.get("page"), "status": page.get("status")}
    return result


def execute_attention(
    args: argparse.Namespace,
    client: RestClient,
    installation_path: Path,
) -> dict[str, Any]:
    """V1.3 Home service; public paths persist facts but never submit native turns."""
    _resolve_staff_number_recipients(args)
    try:
        if args.attention_command.startswith("rooter-"):
            home_ref = _registered_rooter_home(
                installation_path,
                home_id=str(getattr(args, "home_id", None) or "rooter-001"),
                require_todo_v3=(args.attention_command != "rooter-todo-write"),
            )
            if args.attention_command == "rooter-show":
                return {"ok": True, **attention_read_home_state(home_ref)}
            if args.attention_command == "rooter-read":
                return {
                    "ok": True,
                    **attention_mark_input_read(
                        home_ref=home_ref,
                        notice_id=str(args.notice_id),
                    ),
                }
            if args.attention_command == "rooter-handle":
                return {
                    "ok": True,
                    **attention_handle_input(
                        home_ref=home_ref,
                        notice_id=str(args.notice_id),
                        resolution=text_arg(args.resolution, "resolution"),
                        action_ref=text_arg(args.action_ref, "action ref"),
                    ),
                }
            if args.attention_command == "rooter-notice-update":
                return {
                    "ok": True,
                    **attention_organize_input(
                        home_ref=home_ref,
                        notice_id=str(args.notice_id),
                        summary=(
                            text_arg(args.summary, "notice summary", required=True)
                            if args.summary is not None
                            else None
                        ),
                        sort_order=args.sort_order,
                        archived=(
                            True if args.archive
                            else (False if args.restore else None)
                        ),
                        operation_id=str(args.operation_id or ""),
                    ),
                }
            if args.attention_command == "rooter-takeover":
                return {
                    "ok": True,
                    **attention_takeover_input(
                        home_ref=home_ref,
                        notice_id=str(args.notice_id),
                        updates=_parse_todo_update_sets(args.sets),
                        expected_fingerprint=getattr(args, "expected_fingerprint", None),
                    ),
                }
            if args.attention_command == "rooter-todo-update":
                return {
                    "ok": True,
                    **attention_update_home_todo_fields(
                        home_ref=home_ref,
                        updates=_parse_todo_update_sets(args.sets),
                        expected_fingerprint=getattr(
                            args, "expected_fingerprint", None
                        ),
                    ),
                }
            if args.attention_command == "rooter-todo-write":
                return {
                    "ok": True,
                    **_todo_write_receipt(
                        attention_write_home_todo(
                            home_ref=home_ref,
                            text=todo_text_arg(
                                args.body,
                                "TODO markdown",
                                required=True,
                            ),
                            expected_fingerprint=getattr(
                                args, "expected_fingerprint", None
                            ),
                        )
                    ),
                }
            if args.attention_command == "rooter-source-register":
                return {
                    "ok": True,
                    **attention_register_direct_input(
                        home_ref=home_ref,
                        source_ref=str(args.source_ref),
                        summary=text_arg(args.summary, "source summary", required=True),
                        request_activation=bool(args.activate),
                        activation_request_id=str(args.activation_request_id or ""),
                    ),
                }
            if args.attention_command == "rooter-source-status":
                return {
                    "ok": True,
                    **attention_read_source_status(
                        home_ref=home_ref,
                        source_kind=str(args.source_kind),
                        source_ref=str(args.source_ref),
                    ),
                }

        project = client.request("GET", f"/api/projects/{args.project_id}")["project"]
        root_raw = str(
            getattr(args, "root", None)
            or project.get("root_path")
            or ""
        ).strip()
        if not root_raw:
            raise CliError(
                "未提供 --root，且 Project 没有 root_path；无法定位 V1.3 Home。",
                error_code="attention_project_root_missing",
            )
        root = Path(posix_windows_drive_locator(root_raw)).expanduser()

        if args.attention_command in {
            "show",
            "handle",
            "read",
            "takeover",
            "notice-update",
            "todo-write",
            "todo-update",
            "source-register",
            "source-status",
        }:
            home_ref = attention_resolve_project_home(
                project=project,
                agent_id=args.agent_id,
                root_override=str(root),
                # 写口修复：旧 TODO 破损不能挡合法 v3 恢复载荷（真实 Home 定位
                # 保留，新载荷合同在 write_home_todo 校验）。todo-update 同理由
                # update_home_todo_fields 对坏/旧 TODO 给明确恢复写口引导。
                require_todo_v3=(args.attention_command not in {"todo-write", "todo-update"}),
            )
            if args.attention_command == "show":
                return {"ok": True, **attention_read_home_state(home_ref)}
            if args.attention_command == "handle":
                handled = {"ok": True, **attention_handle_input(
                    home_ref=home_ref,
                    notice_id=str(args.notice_id),
                    resolution=text_arg(args.resolution, "resolution"),
                    action_ref=text_arg(args.action_ref, "action ref"),
                )}
                return _refresh_workbench_notice(installation_path, home_ref, handled, str(args.notice_id))
            if args.attention_command == "read":
                marked = {"ok": True, **attention_mark_input_read(
                    home_ref=home_ref,
                    notice_id=str(args.notice_id),
                )}
                return _refresh_workbench_notice(installation_path, home_ref, marked, str(args.notice_id))
            if args.attention_command == "notice-update":
                return {
                    "ok": True,
                    **attention_organize_input(
                        home_ref=home_ref,
                        notice_id=str(args.notice_id),
                        summary=(
                            text_arg(args.summary, "notice summary", required=True)
                            if args.summary is not None
                            else None
                        ),
                        sort_order=args.sort_order,
                        archived=(
                            True if args.archive
                            else (False if args.restore else None)
                        ),
                        operation_id=str(args.operation_id or ""),
                    ),
                }
            if args.attention_command == "todo-write":
                return _refresh_workbench_fast(installation_path, home_ref, {
                    "ok": True,
                    **_todo_write_receipt(
                        attention_write_home_todo(
                            home_ref=home_ref,
                            text=todo_text_arg(
                                args.body,
                                "TODO markdown",
                                required=True,
                            ),
                            expected_fingerprint=getattr(
                                args, "expected_fingerprint", None
                            ),
                        )
                    ),
                })
            if args.attention_command == "takeover":
                return _refresh_workbench_fast(installation_path, home_ref, {
                    "ok": True,
                    **attention_takeover_input(
                        home_ref=home_ref,
                        notice_id=str(args.notice_id),
                        updates=_parse_todo_update_sets(args.sets),
                        expected_fingerprint=getattr(args, "expected_fingerprint", None),
                    ),
                })
            if args.attention_command == "todo-update":
                return _refresh_workbench_fast(installation_path, home_ref, {
                    "ok": True,
                    **attention_update_home_todo_fields(
                        home_ref=home_ref,
                        updates=_parse_todo_update_sets(args.sets),
                        expected_fingerprint=getattr(
                            args, "expected_fingerprint", None
                        ),
                    ),
                })
            if args.attention_command == "source-register":
                return {
                    "ok": True,
                    **attention_register_direct_input(
                        home_ref=home_ref,
                        source_ref=str(args.source_ref),
                        summary=text_arg(args.summary, "source summary", required=True),
                        request_activation=bool(args.activate),
                        activation_request_id=str(args.activation_request_id or ""),
                    ),
                }
            return {
                "ok": True,
                **attention_read_source_status(
                    home_ref=home_ref,
                    source_kind=str(args.source_kind),
                    source_ref=str(args.source_ref),
                ),
            }

        if args.attention_command == "send":
            return {
                "ok": True,
                **attention_send_mail_source(
                    root=root,
                    project=project,
                    subject=text_arg(args.subject, "mail subject", required=True),
                    body=text_arg(args.body, "mail body"),
                    recipients=list(args.to or []),
                    broadcast=bool(args.broadcast),
                    sender_kind=str(args.sender_kind or "human"),
                    sender_id=str(args.sender_id or ""),
                    message_id=str(args.message_id or ""),
                    request_activation=bool(args.activate),
                ),
            }

        if args.attention_command == "notify":
            return {
                "ok": True,
                **attention_request_mail_activation(
                    root=root,
                    project=project,
                    message_id=str(args.message_id),
                    agents=list(args.agents or []),
                    activation_request_id=str(args.activation_request_id or ""),
                ),
            }
    except AttentionServiceProblem as problem:
        raise CliError(
            str(problem),
            error_code=problem.code,
            details=problem.details,
        ) from None

    raise CliError(
        f"Unsupported attention command: {args.attention_command}",
        error_code="unsupported_command",
    )

DEFAULT_WAKE_PROMPT = "检查 Workstation mailbox 或 CAT，并从当前工位继续。"


def load_driver_config(path: str | None) -> dict[str, Any]:
    """Load an optional UTF-8 JSON config file used as native target details."""
    p_path = str(path or "").strip()
    if not p_path:
        return {}
    with open(p_path, "r", encoding="utf-8") as file_handle:
        data = json.loads(file_handle.read())
    if not isinstance(data, dict):
        raise CliError("driver-config JSON 必须是 object。", error_code="wake_driver_config_invalid")
    return data


def execute_wake(
    args: argparse.Namespace,
    client: RestClient,
    installation_path: Path | None = None,
) -> dict[str, Any]:
    """Workless wake surface: native-target config + one-shot injection only.

    bind/unbind/status operate the Contact native-target store (no attempt
    machine); trigger calls the standalone native injection tool; probe/
    recover/stop/test are explicitly retired. The original reasons stay
    visible instead of silently becoming empty lists.

    Home-type routing: the installation-registered Rooter Home reads/writes
    only its own native-target store (no Project Session lookup or creation);
    Project Agents keep the existing path.
    """
    installation_path = installation_path or resolve_installation_path(
        getattr(args, "installation_file", None)
    )
    route = _rooter_home_root(installation_path)
    is_rooter_home = bool(route and args.agent_id == route[0])
    if is_rooter_home:
        root = route[1]
    else:
        project = client.request("GET", f"/api/projects/{args.project_id}")["project"]
        root_raw = str(getattr(args, "root", None) or project.get("root_path") or "").strip()
        if not root_raw:
            raise CliError(
                "未提供 --root，且 Project 没有 root_path；无法定位 Contact native-target。",
                error_code="wake_project_root_missing",
            )
        root = Path(posix_windows_drive_locator(root_raw)).expanduser()
    try:
        if args.wake_command == "bind":
            if is_rooter_home:
                # Rooter Home 不是 Project Session：只从 argv 取原生目标，不查/建 Session。
                native_session_id = str(getattr(args, "native_session_id", None) or "").strip()
                if not native_session_id:
                    raise CliError(
                        "Rooter Home bind 需要 --native-session-id（不读 Project Session）。",
                        error_code="wake_native_session_missing",
                    )
                runtime_id = str(getattr(args, "runtime_id", None) or "").strip() or None
            else:
                detail = get_session_detail(client, args.project_id, args.agent_id)
                session = detail.get("session") or {}
                runtime_session = (
                    session.get("runtime_session")
                    if isinstance(session.get("runtime_session"), dict)
                    else {}
                )
                runtime_id = str(args.runtime_id or session.get("runtime_id") or "").strip() or None
                native_session_id = str(args.native_session_id or runtime_session.get("session_id") or "").strip()
                if not native_session_id:
                    raise CliError(
                        "bind 需要 --native-session-id 或 Session 已登记 runtime_session。",
                        error_code="wake_native_session_missing",
                    )
            driver_config = load_driver_config(args.driver_config)
            return {
                "ok": True,
                **bind_wakeup(root=root, project_id=None if is_rooter_home else args.project_id,
                              agent_id=args.agent_id, runtime_id=runtime_id,
                              native_session_id=native_session_id, driver_name=args.driver,
                              driver_config=driver_config),
            }
        if args.wake_command == "unbind":
            targets = load_native_targets(root) or {}
            if args.agent_id not in targets:
                return {
                    "ok": True,
                    "schema": "paos-wake-action/v1",
                    "action": "unbind",
                    "status": "not_configured",
                    "agent_id": args.agent_id,
                }
            targets.pop(args.agent_id, None)
            store_path = save_native_targets(root, targets)
            return {
                "ok": True,
                "schema": "paos-wake-action/v1",
                "action": "unbind",
                "status": "cleared",
                "agent_id": args.agent_id,
                "store": str(store_path),
            }
        if args.wake_command == "status":
            return {
                **runtime_contact(root, args.agent_id),
                "ok": True,
                "schema": "paos-wake-status/v1",
                "agent_id": args.agent_id,
                "activation": None,
                "native_turn": {"state": "not_observed"},
            }
        if args.wake_command == "probe":
            return {"ok": True, "schema": "paos-wake-action/v1", "action": "probe", "state": "retired", "note": "探测退役：不自动启动/探测 Harness，状态保持 unknown。"}
        if args.wake_command == "recover":
            return {"ok": True, "schema": "paos-wake-action/v1", "action": "recover", "state": "retired", "note": "恢复重试退役；如需提醒请走独立注入工具。"}
        if args.wake_command == "stop":
            targets = load_native_targets(root) or {}
            target = targets.get(args.agent_id) if isinstance(targets.get(args.agent_id), dict) else None
            if not target:
                return {"ok": True, "schema": "paos-wake-action/v1", "action": "stop", "state": "not_configured", "agent_id": args.agent_id}
            stop_file = str(target.get("stop_file") or "").strip()
            if not stop_file:
                return {"ok": True, "schema": "paos-wake-action/v1", "action": "stop", "state": "no_stop_file", "agent_id": args.agent_id}
            Path(stop_file).parent.mkdir(parents=True, exist_ok=True)
            Path(stop_file).write_text("PAOS explicit stop marker\n", encoding="utf-8")
            return {"ok": True, "schema": "paos-wake-action/v1", "action": "stop", "state": "stopped", "agent_id": args.agent_id, "stop_file": stop_file}
        if args.wake_command == "test":
            return {"ok": True, "schema": "paos-wake-action/v1", "action": "test", "state": "retired", "note": "试唤醒退役；不额外发模型测试请求。"}
        if args.wake_command == "trigger":
            message = text_arg(args.prompt, "wake prompt") or DEFAULT_WAKE_PROMPT
            native_model = None
            if getattr(args, "model", None):
                raw_model = str(args.model).strip()
                try:
                    parsed = json.loads(raw_model)
                except ValueError:
                    parsed = raw_model
                native_model = parsed  # opencode expects dict(providerID/modelID); others expect str
            target = (load_native_targets(root) or {}).get(args.agent_id)
            if not isinstance(target, dict):
                return {
                    "ok": True,
                    "schema": "paos-wake-action/v1",
                    "action": "trigger",
                    "state": "not_configured",
                    "agent_id": args.agent_id,
                    "note": "未配置原生 target；原提醒不入注入通道。请用 paos wake bind 存储 Contact 还 native-targets.json 配置。",
                }
            try:
                receipt = native_inject(target=target, message=message, model=native_model)
            except InjectionUncertain as exc:
                return {
                    "ok": True,
                    "schema": "paos-wake-action/v1",
                    "action": "trigger",
                    "state": "delivery_uncertain",
                    "agent_id": args.agent_id,
                    "accepted": None,
                    "retry": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    **exc.details(),
                    "repair_owner": args.agent_id,
                }
            except (InjectionError, ValueError) as exc:
                return {
                    "ok": True,
                    "schema": "paos-wake-action/v1",
                    "action": "trigger",
                    "state": "native_rejected",
                    "agent_id": args.agent_id,
                    "accepted": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    **(exc.details() if isinstance(exc, InjectionError) else {}),
                    "repair_owner": (args.agent_id if exc.repair_owner == "target_owner" else exc.repair_owner) if isinstance(exc, InjectionError) else "sender",
                }
            return {
                "ok": True,
                "schema": "paos-wake-action/v1",
                "action": "trigger",
                "state": "accepted",
                "agent_id": args.agent_id,
                **receipt,
            }
    except CliError:
        raise
    except (InjectionError, WakeProblem, ValueError, OSError) as problem:
        raise CliError(
            f"Wake 命令失败：{problem}",
            error_code=getattr(problem, "code", "wake_operation_failed"),
            details={"detail": str(problem)},
        ) from None

    raise CliError(
        f"Unsupported wake command: {args.wake_command}",
        error_code="unsupported_command",
    )


def execute_mail(
    args: argparse.Namespace,
    client: RestClient,
) -> dict[str, Any]:
    """V1.3 Mail UX backed by immutable Mail + unified Notice handling."""
    project = client.request("GET", f"/api/projects/{args.project_id}")["project"]
    root_raw = str(
        getattr(args, "root", None)
        or project.get("root_path")
        or ""
    ).strip()
    if not root_raw:
        raise CliError(
            "未提供 --root，且 Project 没有 root_path；无法定位 Workstation Mail。",
            error_code="mail_project_root_missing",
        )
    root = Path(posix_windows_drive_locator(root_raw)).expanduser()
    try:
        if args.mail_command == "send":
            frozen = resolve_recipients(
                project,
                recipients=list(args.to or []),
                broadcast=bool(args.broadcast),
            )
            if _recipient_contract(root=root, recipients=frozen) == "v3":
                return {
                    "ok": True,
                    **attention_send_mail_source(
                        root=root,
                        project=project,
                        subject=text_arg(args.subject, "mail subject", required=True),
                        body=text_arg(args.body, "mail body"),
                        recipients=list(args.to or []),
                        broadcast=bool(args.broadcast),
                        sender_kind=str(args.sender_kind or "human"),
                        sender_id=str(args.sender_id or ""),
                        message_id=str(args.message_id or ""),
                        request_activation=False,
                    ),
                }
            return {
                "ok": True,
                **send_mail(
                    root=root,
                    project=project,
                    subject=text_arg(args.subject, "mail subject", required=True),
                    body=text_arg(args.body, "mail body"),
                    recipients=list(args.to or []),
                    broadcast=bool(args.broadcast),
                    sender_kind=str(args.sender_kind or "human"),
                    sender_id=str(args.sender_id or ""),
                    message_id=str(args.message_id or ""),
                ),
            }

        if args.mail_command == "reply":
            find_by_id(project.get("sessions", []), args.agent_id, "Agent")
            if not _home_uses_todo_v3(root, args.agent_id):
                original = read_mail(root, args.agent_id, args.in_reply_to)
                metadata = original.get("metadata")
                if (
                    not isinstance(metadata, dict)
                    or metadata.get("recipient_agent_id") != args.agent_id
                ):
                    raise CliError(
                        "被回复的 Mail 不属于该 Agent 的收件箱。",
                        error_code="mail_reply_source_mismatch",
                    )
                recipient_id = str(metadata.get("sender_id") or "").strip()
                if metadata.get("sender_kind") != "agent" or not recipient_id:
                    raise CliError(
                        "原 Mail 不是由 Project Agent 发送，无法通过 Agent Mail 回复。",
                        error_code="mail_reply_target_unavailable",
                        hint="对 Human 的正式请求请使用 paos session request-create。",
                    )
                original_subject = str(metadata.get("subject") or "").strip()
                subject = text_arg(args.subject, "mail subject") or f"Re: {original_subject}"
                body = (
                    f"In reply to: `{args.in_reply_to}`\n\n"
                    + text_arg(args.body, "mail body", required=True)
                )
                reply = send_mail(
                    root=root,
                    project=project,
                    subject=subject,
                    body=body,
                    recipients=[recipient_id],
                    sender_kind="agent",
                    sender_id=args.agent_id,
                    message_id=str(args.message_id or ""),
                )
                handling = mark_mail_handled(
                    root,
                    args.agent_id,
                    args.in_reply_to,
                    state="replied",
                    reason=f"Reply persisted as {reply['message_id']}",
                )
                try:
                    activation = activate_mail_dispatch(
                        root=root,
                        project_id=args.project_id,
                        message_id=str(reply["message_id"]),
                    )
                except AgentActivationProblem as problem:
                    activation = {
                        "state": "activation_error",
                        "error_code": problem.code,
                        "detail": str(problem),
                    }
                return {
                    "ok": True,
                    **reply,
                    "handling": handling,
                    "activation": activation,
                }

            original = attention_read_project_mail_input(
                root=root,
                project=project,
                agent_id=args.agent_id,
                message_id=args.in_reply_to,
            )
            original_mail = original.get("mail") or {}
            metadata = original_mail.get("metadata")
            if (
                not isinstance(metadata, dict)
                or metadata.get("recipient_agent_id") != args.agent_id
            ):
                raise CliError(
                    "被回复的 Mail 不属于该 Agent 的收件箱。",
                    error_code="mail_reply_source_mismatch",
                )
            recipient_id = str(metadata.get("sender_id") or "").strip()
            if metadata.get("sender_kind") != "agent" or not recipient_id:
                raise CliError(
                    "原 Mail 不是由 Project Agent 发送，无法通过 Agent Mail 回复。",
                    error_code="mail_reply_target_unavailable",
                    hint="对 Human 的正式请求请使用 paos session request-create。",
                )
            if _recipient_contract(root=root, recipients=[recipient_id]) != "v3":
                raise CliError(
                    "当前 Home 已采用 V1.3，但回复目标仍是 legacy Home；切换窗口内拒绝跨合同发送。",
                    error_code="v13_target_not_converted",
                    details={"recipient_agent_id": recipient_id},
                )
            original_subject = str(metadata.get("subject") or "").strip()
            subject = text_arg(args.subject, "mail subject") or f"Re: {original_subject}"
            body = (
                f"In reply to: `{args.in_reply_to}`\n\n"
                + text_arg(args.body, "mail body", required=True)
            )
            reply = attention_send_mail_source(
                root=root,
                project=project,
                subject=subject,
                body=body,
                recipients=[recipient_id],
                sender_kind="agent",
                sender_id=args.agent_id,
                message_id=str(args.message_id or ""),
                request_activation=True,
            )
            handling = attention_handle_mail_input(
                root=root,
                project=project,
                agent_id=args.agent_id,
                message_id=args.in_reply_to,
                resolution="replied",
                action_ref=str((reply.get("mail") or {}).get("message_id") or ""),
            )
            return {"ok": True, **reply, "handling": handling}

        if args.mail_command == "list":
            if _home_uses_todo_v3(root, args.agent_id):
                return {
                    "ok": True,
                    **attention_list_project_mail_inputs(
                        root=root,
                        project=project,
                        agent_id=args.agent_id,
                    ),
                }
            return {"ok": True, **list_mail(root, args.agent_id)}

        if args.mail_command == "read":
            if _home_uses_todo_v3(root, args.agent_id):
                result = attention_read_project_mail_input(
                    root=root,
                    project=project,
                    agent_id=args.agent_id,
                    message_id=args.message_id,
                )
                return {
                    "ok": True,
                    **(result.get("mail") or {}),
                    "notice": result.get("notice"),
                    "home": result.get("home"),
                }
            return {"ok": True, **read_mail(root, args.agent_id, args.message_id)}

        if args.mail_command == "handle":
            find_by_id(project.get("sessions", []), args.agent_id, "Agent")
            reason = text_arg(args.reason, "handling reason")
            if _home_uses_todo_v3(root, args.agent_id):
                resolution = str(args.state or "handled")
                if reason:
                    resolution = f"{resolution}: {reason}"
                return {
                    "ok": True,
                    **attention_handle_mail_input(
                        root=root,
                        project=project,
                        agent_id=args.agent_id,
                        message_id=args.message_id,
                        resolution=resolution,
                        action_ref="",
                    ),
                }
            return {
                "ok": True,
                **mark_mail_handled(
                    root,
                    args.agent_id,
                    args.message_id,
                    state=args.state,
                    reason=reason,
                ),
            }

        if args.mail_command == "status":
            return {
                "ok": True,
                **dispatch_status(root, args.message_id, registry_lookup=_registry_authoritative_or_none(getattr(args, "installation_file", None))),
            }
    except (MailProblem, AttentionServiceProblem) as problem:
        raise CliError(
            str(problem),
            error_code=getattr(problem, "code", "mail_error"),
            details=getattr(problem, "details", {}),
        ) from None
    raise CliError(
        f"Unsupported mail command: {args.mail_command}",
        error_code="unsupported_command",
    )

def execute_library(
    args: argparse.Namespace,
    installation_path: Path,
    client: RestClient,
) -> dict[str, Any]:
    """Workflow / Skill Library operations (catalog/usage on disk; search via the local HTTP read face)."""
    try:
        if args.library_command == "search":
            query = urlencode({
                "q": args.query,
                "kind": args.kind,
                "limit": args.limit,
            })
            return client.request("GET", "/api/library/search?" + query)

        if args.library_command == "tools":
            return client.request("GET", "/api/library/tools")
        if args.library_command == "roots":
            installation = load_installation_descriptor(installation_path)
            config_path = resolve_library_roots_path(
                installation=installation,
                explicit=args.roots_config,
            )
            if args.roots_command == "show":
                return {
                    "ok": True,
                    **load_library_roots(config_path),
                }
            result = register_library_roots(
                config_path,
                workflow_root=Path(str(args.workflow_root)).expanduser(),
                skill_root=Path(str(args.skill_root)).expanduser(),
                tool_catalog=getattr(args, "tool_catalog", None),
            )
            return {
                "ok": True,
                **result,
            }

        root = Path(posix_windows_drive_locator(str(args.root))).expanduser()
        if args.library_command == "init":
            result = (
                ensure_workflow_library(root)
                if args.kind == "workflow"
                else ensure_skill_library(root)
            )
            catalog = (
                refresh_workflow_catalog(root)
                if args.kind == "workflow"
                else refresh_skill_catalog(root)
            )
            return {
                "ok": True,
                "schema": "paos-library-init/v1",
                **result,
                "catalog": catalog,
            }

        if args.library_command == "catalog":
            catalog = (
                refresh_workflow_catalog(root)
                if args.kind == "workflow"
                else refresh_skill_catalog(root)
            )
            return {"ok": True, **catalog}

        if args.library_command == "skill-use":
            result = record_skill_use(
                root,
                skill_id=args.skill_id,
                score=float(args.score),
                project_id=str(args.project_id or ""),
                agent_id=str(args.agent_id or ""),
                work_id=str(args.work_id or ""),
                note=str(args.note or ""),
            )
            return {
                "ok": True,
                "schema": "paos-skill-use-recorded/v1",
                **result,
            }
    except (LibraryProblem, InstallationProblem) as problem:
        raise CliError(
            str(problem),
            error_code=getattr(problem, "code", "library_error"),
            details=problem.details,
        ) from None

    raise CliError(
        f"Unsupported library command: {args.library_command}",
        error_code="unsupported_command",
    )

def execute(
    args: argparse.Namespace,
    client: RestClient,
    *,
    config_path: Path | None = None,
    installation_path: Path | None = None,
) -> Any:
    if args.command == "cat":
        return execute_cat(args, client, text_arg)
    resolved_installation_path = installation_path or resolve_installation_path(
        getattr(args, "installation_file", None)
    )

    if args.command == "workbench":
        import sys as _sys
        from pathlib import Path as _Path

        _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "attention-dashboard-v1-static"))
        from workbench_markdown import WorkbenchProblem, build_workbench

        if args.workbench_command in {"scan", "watch"}:
            import time as _time
            from workbench_refresh import scan_dirty

            limit = int(getattr(args, "limit", 32) or 32)
            while True:
                result = scan_dirty(resolved_installation_path, limit=limit)
                if args.json_output and args.workbench_command == "scan":
                    return result
                if args.workbench_command == "scan":
                    return f"工作台补扫：处理 {result['processed']} 个标记；ok={result['ok']}"
                if bool(getattr(args, "once", False)):
                    return result
                _time.sleep(max(1, int(getattr(args, "interval", 60))))

        try:
            result = build_workbench(
                resolved_installation_path,
                home_ids=list(getattr(args, "home", None) or []),
                project_ids=list(getattr(args, "project", None) or []),
                changed_only=bool(getattr(args, "changed_only", False)),
            )
        except WorkbenchProblem as error:
            raise CliError(
                str(error), status=error.status, error_code=error.code,
                details=error.details,
            ) from error
        if args.json_output:
            return result
        return render_workbench(result)

    if args.command == "install":
        try:
            if args.install_command == "rollback":
                import sys as _sys
                from pathlib import Path as _Path

                _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "attention-dashboard-v1-static"))
                from paos_program_rollback import RollbackProblem, apply_program_rollback, plan_program_rollback

                try:
                    if getattr(args, "apply", False):
                        if not args.compatibility_file:
                            raise RollbackProblem("rollback_compatibility_missing", "执行回退必须提供 --compatibility-file。")
                        result = apply_program_rollback(
                            resolved_installation_path, args.target_source, args.compatibility_file,
                        )
                    else:
                        result = plan_program_rollback(resolved_installation_path, args.target_source)
                        if args.compatibility_file:
                            from paos_program_rollback import _load_compat, validate_compatibility
                            compat = _load_compat(Path(args.compatibility_file))
                            validate_compatibility(result, compat)
                            result["compatibility"] = compat
                            result["ready"] = True
                            result["reason"] = None
                except RollbackProblem as error:
                    raise CliError(
                        str(error), status=409 if error.code == "rollback_writer_active" else 422,
                        error_code=error.code, details=error.details,
                    ) from error
                return result if args.json_output else render_program_rollback(result)
            if args.install_command == "plan":
                import sys as _sys
                from pathlib import Path as _Path

                _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "attention-dashboard-v1-static"))
                from install_plan import InstallPlanProblem, build_install_plan

                try:
                    plan = build_install_plan(
                        resolved_installation_path,
                        target_source=getattr(args, "target_source", None),
                        retire=bool(getattr(args, "retire", False)),
                    )
                except InstallPlanProblem as error:
                    raise CliError(
                        str(error), status=error.status, error_code=error.code,
                        details=error.details,
                    ) from error
                if args.json_output:
                    return plan
                return render_install_plan(plan)
            if args.install_command == "homes":
                import sys as _sys
                from pathlib import Path as _Path

                _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "attention-dashboard-v1-static"))
                from install_homes import InstallHomesProblem, build_install_home_coverage

                try:
                    coverage = build_install_home_coverage(
                        resolved_installation_path,
                        project=getattr(args, "project", None),
                        home=getattr(args, "home", None),
                    )
                except InstallHomesProblem as error:
                    raise CliError(
                        str(error), status=error.status, error_code=error.code,
                        details=error.details,
                    ) from error
                if args.json_output:
                    return coverage
                return render_install_homes(coverage)
            if args.install_command == "configure":
                return {
                    "ok": True,
                    **write_installation_descriptor(
                        resolved_installation_path,
                        source_root=args.source_root,
                        library_roots_config=args.library_roots_config,
                        rooter_home=args.rooter_home,
                        data_root=args.data_root,
                    ),
                }
            descriptor = load_installation_descriptor(resolved_installation_path)
            if not descriptor["configured"]:
                return {"ok": True, **descriptor}
            source_runtime_path = Path(
                posix_windows_drive_locator(descriptor["source_root"])
            ).expanduser()
            try:
                data_root_path = effective_data_root(descriptor)
                if not data_root_path.is_dir():
                    raise InstallationProblem(
                        "installation_data_root_unavailable",
                        "登记的数据根不存在。",
                        {"data_root": str(data_root_path)},
                    )
            except InstallationProblem as problem:
                raise CliError(
                    str(problem), status=422, error_code=problem.code,
                    details=problem.details,
                ) from problem
            roots_path = resolve_library_roots_path(installation=descriptor)
            roots = load_library_roots(roots_path)
            rooter_home_raw = str(descriptor.get("rooter_home") or "").strip()
            rooter_home_path = (
                Path(posix_windows_drive_locator(rooter_home_raw)).expanduser()
                if rooter_home_raw
                else None
            )
            return {
                "ok": True,
                **descriptor,
                "source_root_exists": source_runtime_path.is_dir(),
                "data_root_exists": data_root_path.is_dir(),
                "rooter_home_exists": (
                    rooter_home_path.is_dir()
                    if rooter_home_path is not None
                    else False
                ),
                "library_roots": roots,
            }
        except (InstallationProblem, LibraryProblem) as problem:
            raise CliError(
                str(problem),
                error_code=getattr(problem, "code", "installation_error"),
                details=problem.details,
            ) from None

    if args.command == "workstation":
        return execute_workstation(args, client, resolved_installation_path)

    if args.command == "orient":
        return execute_orient(args, client, resolved_installation_path)

    if args.command == "status":
        return execute_status(args, client, resolved_installation_path)

    if args.command == "inbox":
        return execute_inbox(args, client)

    if args.command == "peers":
        return execute_peers(args, client)

    if args.command == "team":
        return execute_team(args, client)

    if args.command == "home":
        return execute_home(args, client)

    if args.command == "ports":
        return execute_ports(args, client)

    if args.command == "library":
        return execute_library(args, resolved_installation_path, client)

    if args.command == "tips":
        if args.tips_command == "search":
            project_values = args.project or []
            if len(project_values) > 1:
                raise CliError(
                    "--project 只能指定一次。",
                    error_code="tips_search_project_invalid",
                )
            params = {"q": args.query, "limit": args.limit}
            if project_values:
                project_value = project_values[0]
                if (
                    not isinstance(project_value, str)
                    or not project_value.strip()
                    or len(project_value.strip()) > 200
                    or "\x00" in project_value
                ):
                    raise CliError(
                        "--project 去除首尾空白后长度必须为 1–200 个字符，且不能包含 NUL。",
                        error_code="tips_search_project_invalid",
                    )
                params["project"] = project_value
            return client.request("GET", "/api/tips/search?" + urlencode(params))
        if args.tips_command == "read":
            if not isinstance(args.tip_id, str) or not re.fullmatch(r"tip-[A-Za-z0-9_-]{1,120}", args.tip_id):
                raise CliError(
                    "Tip ID 无效；只接受 tip-[A-Za-z0-9_-]{1,120}。",
                    error_code="tips_id_invalid",
                )
            encoded_tip_id = quote(args.tip_id, safe="")
            return client.request("GET", "/api/tips/" + encoded_tip_id)
        if args.tips_command == "correct":
            raw_text = text_arg(args.body, "correction request", required=True)
            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise CliError("correction request 不是合法 JSON。", error_code="tips_correction_invalid") from exc
            if not isinstance(payload, dict):
                raise CliError("correction request 必须是 JSON 对象。", error_code="tips_correction_invalid")
            if payload.get("schema") != "paos-tip-correction/v1":
                raise CliError("schema 必须是 paos-tip-correction/v1。", error_code="tips_correction_invalid")
            required = ("id", "base_tip_id", "base_source_sha256", "title", "project", "reason", "actor")
            missing = [name for name in required if name not in payload]
            if missing:
                raise CliError("correction request 缺少字段：" + "、".join(missing), error_code="tips_correction_invalid")
            for key in ("id", "base_tip_id"):
                if not re.fullmatch(r"tip-[A-Za-z0-9_-]{1,120}", str(payload[key])):
                    raise CliError(f"{key} 无效。", error_code="tips_correction_invalid")
            if payload["id"] == payload["base_tip_id"]:
                raise CliError("新旧 ID 必须不同。", error_code="tips_correction_invalid")
            if not re.fullmatch(r"[0-9a-f]{64}", str(payload["base_source_sha256"])):
                raise CliError("base_source_sha256 必须是 64 位小写十六进制。", error_code="tips_correction_invalid")
            return post_mutation(
                client, "/api/tips/corrections", payload, str(payload["id"]), 0,
                unknown_message="请求超时，服务端可能已提交，结果未知。保留原 Tip ID，按该新 ID 核查后再决定；不要自动重发。",
                unknown_hint="按新 Tip ID 读取或搜索确认是否已提交；不要自动重发或更换 ID。",
            )
        if args.tips_command == "absorptions":
            if not isinstance(args.tip_id, str) or not re.fullmatch(r"tip-[A-Za-z0-9_-]{1,120}", args.tip_id):
                raise CliError("Tip ID 无效；只接受 tip-[A-Za-z0-9_-]{1,120}。", error_code="tips_id_invalid")
            if not re.fullmatch(r"[0-9a-f]{64}", str(args.source_sha256 or "")):
                raise CliError("--source-sha256 必须是 64 位小写十六进制。", error_code="tips_absorption_query_invalid")
            return client.request(
                "GET",
                "/api/tips/" + quote(args.tip_id, safe="") + "/absorptions?source_sha256=" + args.source_sha256,
            )
        if args.tips_command == "history":
            if not isinstance(args.tip_id, str) or not re.fullmatch(r"tip-[A-Za-z0-9_-]{1,120}", args.tip_id):
                raise CliError(
                    "Tip ID 无效；只接受 tip-[A-Za-z0-9_-]{1,120}。",
                    error_code="tips_id_invalid",
                )
            return client.request("GET", "/api/tips/" + quote(args.tip_id, safe="") + "/history")
        raise CliError("Unsupported Tips command", error_code="unsupported_command")

    if args.command == "attention":
        return execute_attention(args, client, resolved_installation_path)

    if args.command == "mail":
        return execute_mail(args, client)

    if args.command == "agent":
        return execute_agent(args, client, resolved_installation_path)

    if args.command == "wake":
        return execute_wake(args, client, resolved_installation_path)

    if args.command == "config":
        path = config_path or resolve_config_path(getattr(args, "config_file", None))
        if args.config_command == "set-base-url":
            config = write_cli_config(path, base_url=args.value)
            return {
                "ok": True,
                "schema": CLI_CONFIG_SCHEMA,
                "path": str(path),
                **config,
            }
        config = load_cli_config(path)
        return {
            "ok": True,
            "schema": CLI_CONFIG_SCHEMA,
            "path": str(path),
            "configured_base_url": config.get("base_url", ""),
            "effective_base_url": resolve_base_url(args.base_url, path),
        }

    if args.command == "health":
        return client.request("GET", "/api/health")

    if args.command == "authority":
        q = "?" + urlencode({"actor": args.actor}) if args.actor else ""
        response = client.request("GET", "/api/authority" + q)
        if args.json_output:
            return response
        return render_authority(response["authority"], args.allowed_only)

    if args.command == "relations":
        return client.request("GET", f"/api/projects/{args.project_id}/relations")

    if args.command == "needs-me":
        return client.request("GET", f"/api/projects/{args.project_id}/needs-me")

    if args.command == "project":
        if args.project_command == "experience":
            return client.request("GET", f"/api/projects/{quote(args.project_id, safe='')}/experience")
        if args.project_command == "acceptance-check":
            if not isinstance(args.home, str) or not args.home.strip() or not isinstance(args.task, str) or not args.task.strip():
                raise CliError("--home 与 --task 不能为空。", error_code="acceptance_check_query_invalid")
            if args.ref_index < 0:
                raise CliError("--ref-index 必须是非负整数。", error_code="acceptance_check_query_invalid")
            if not re.fullmatch(r"[0-9a-f]{64}", str(args.todo_sha256 or "")):
                raise CliError("--todo-sha256 必须是 64 位小写十六进制。", error_code="acceptance_check_query_invalid")
            params = urlencode({
                "home_id": args.home.strip(),
                "task_id": args.task.strip(),
                "ref_index": args.ref_index,
                "todo_sha256": args.todo_sha256,
            })
            return client.request(
                "GET",
                f"/api/projects/{quote(args.project_id, safe='')}/acceptance-ref/verify?" + params,
            )
        if args.project_command == "outcomes":
            view = "full" if args.full else "summary"
            return client.request(
                "GET",
                f"/api/projects/{args.project_id}/outcomes?view={view}",
            )
        if args.project_command == "progress-update":
            payload = build_project_progress_update_payload(args)
            return post_mutation(
                client,
                "/api/agent/project-progress-update",
                payload,
                payload["update_id"],
                payload["expected_revision"],
            )
        if args.project_command == "show":
            return client.request("GET", f"/api/projects/{args.project_id}")
        return client.request("GET", f"/api/projects/{args.project_id}/stewardship")

    if args.command == "session":
        if args.session_command == "show":
            return get_session_detail(client, args.project_id, args.session_id)
        if args.session_command == "context":
            return session_context(client, args.project_id, args.session_id)
        if args.session_command == "mailbox":
            return session_mailbox(client, args.project_id, args.session_id)

        base_path = (
            f"/api/projects/{args.project_id}/sessions/{args.session_id}"
        )
        detail: dict[str, Any] | None = None
        if args.session_command == "artifact-add" and args.revision is not None:
            detail = get_session_detail(client, args.project_id, args.session_id)
        op, rev, detail = session_mutation_meta(
            client,
            args.project_id,
            args.session_id,
            args,
            detail,
        )
        if args.session_command == "ack":
            contact_args = []
            if args.environment is not None:
                contact_args.append(("environment", args.environment))
            if args.runtime_title is not None:
                contact_args.append(("title", args.runtime_title))
            if args.native_session_id is not None:
                contact_args.append(("session_id", args.native_session_id))
            if args.source_path is not None:
                contact_args.append(("source_path", args.source_path))
            runtime_contact = dict(contact_args)
            payload = {
                "schema": "paos-session-ack/v1",
                "operation_id": op,
                "base_revision": rev,
                "session_id": args.session_id,
                "agent_label": args.agent_label or "",
                "runtime_session": runtime_contact,
                "understood_objective": text_arg(
                    args.understood_objective, "understood objective", required=True
                ),
                "understood_boundaries": text_list(args.boundary, "boundary"),
                "proposed_first_steps": text_list(args.first_step, "first step"),
                "detected_risks": text_list(args.risk, "risk"),
            }
            if args.runtime_id:
                payload["runtime_id"] = args.runtime_id
                payload["model_id"] = args.model_id or ""
            elif args.model_id:
                raise CliError(
                    "--model-id requires --runtime-id",
                    error_code="invalid_runtime_binding",
                )
            return post_mutation(
                client,
                base_path + "/acknowledge",
                payload,
                op,
                rev,
            )

        if args.session_command in {"update", "report"}:
            handoff = _prepare_session_handoff(args, client, operation_id=op)
            payload = build_session_update_payload(
                op=op,
                revision=rev,
                session_id=args.session_id,
                fields={
                    "progress": {
                        "status": args.status,
                        "summary": text_arg(args.summary, "summary"),
                        "percent": None,
                        "blockers": text_list(args.blocker, "blocker"),
                        "next_actions": text_list(args.next_action, "next action"),
                    }
                },
            )
            payload.update(load_body(args.body))
            result = post_mutation(
                client,
                base_path + "/updates",
                payload,
                op,
                rev,
            )
            compact = True if args.full_result is None else not args.full_result
            result = _deliver_session_handoff(
                result,
                handoff=handoff,
                project_id=args.project_id,
                sender_id=args.session_id,
                operation_id=op,
            )
            if compact:
                return _compact_mutation_receipt(result)
            return result

        if args.session_command == "artifact-add":
            purpose = text_arg(args.purpose, "purpose")
            change_summary = text_arg(args.change_summary, "change summary")
            if args.replaces and not change_summary:
                raise CliError(
                    "--change-summary is required when --replaces is used",
                    error_code="missing_change_summary",
                )
            payload = {
                "schema": "paos-session-artifact-add/v1",
                "operation_id": op,
                "base_revision": rev,
                "session_id": args.session_id,
                "path": args.path,
                "type": args.type,
                "purpose": purpose,
                "replaces": args.replaces or "",
            }
            if change_summary:
                payload["change_summary"] = change_summary
            version_ref = complete_version_ref(args)
            if version_ref is not None:
                payload["version_ref"] = version_ref
            return post_mutation(
                client,
                base_path + "/artifacts",
                payload,
                op,
                rev,
            )

        if args.session_command == "request-create":
            request = {
                "request_type": args.request_type,
                "requires_human": args.requires_human,
                "target_identity_id": args.target_identity_id or "",
                "target_session_id": args.target_session_id or "",
                "description": text_arg(args.description, "request description", required=True),
            }
            payload = build_session_update_payload(
                op=op,
                revision=rev,
                session_id=args.session_id,
                fields={"requests": [request]},
            )
            return post_mutation(
                client,
                base_path + "/updates",
                payload,
                op,
                rev,
            )

        if args.session_command == "request-resolve":
            payload = build_session_update_payload(
                op=op,
                revision=rev,
                session_id=args.session_id,
                fields={
                    "request_updates": [
                        {
                            "request_id": args.request_id,
                            "status": args.status,
                            "resolution": text_arg(args.resolution, "request resolution"),
                        }
                    ]
                },
            )
            result = post_mutation(
                client,
                base_path + "/updates",
                payload,
                op,
                rev,
            )
            return result if args.full_result else _compact_mutation_receipt(result)

        if args.session_command in {"close", "submit"}:
            handoff = _prepare_session_handoff(args, client, operation_id=op)
            payload = {
                "schema": "paos-session-close/v1",
                "operation_id": op,
                "base_revision": rev,
                "session_id": args.session_id,
                "result": args.result,
                "result_summary": text_arg(args.summary, "result summary"),
                "remaining_work": text_list(args.remaining, "remaining work"),
                "recommended_next_identity_id": args.recommended_next or "",
            }
            payload.update(load_body(args.body))
            result = post_mutation(
                client,
                base_path + "/close",
                payload,
                op,
                rev,
            )
            return _deliver_session_handoff(
                result,
                handoff=handoff,
                project_id=args.project_id,
                sender_id=args.session_id,
                operation_id=op,
            )

        raise CliError(
            f"unsupported session command: {args.session_command}",
            error_code="unsupported_command",
        )

    if args.command == "coordinator":
        if args.coordinator_command == "control":
            return coordinator_control(
                client,
                args.project_id,
                since_revision=args.since_revision,
            )

        if args.coordinator_command == "guide-promote":
            project = client.request(
                "GET", f"/api/projects/{args.project_id}"
            )["project"]
            try:
                validate_current_coordinator(
                    project,
                    coordinator_session_id=args.coordinator_session_id,
                )
                candidate = Path(
                    posix_windows_drive_locator(str(args.candidate))
                ).expanduser()
                result = promote_guide_candidate(
                    candidate,
                    canonical_src=Path(
                        posix_windows_drive_locator(str(args.canonical))
                    ).expanduser(),
                    expected_candidate_sha256=args.expected_candidate_sha256,
                    change_summary=text_arg(
                        args.change_summary, "change summary", required=True
                    ),
                )
            except GuideProblem as problem:
                raise CliError(
                    str(problem), error_code=problem.code, details=problem.details
                ) from None
            return {
                "ok": True,
                "project_id": args.project_id,
                "coordinator_session_id": args.coordinator_session_id,
                "candidate": str(candidate),
                **result,
            }

        op, rev = mutation_meta(client, args.project_id, args)
        root = f"/api/projects/{args.project_id}/coordinator"
        common = {
            "operation_id": op,
            "revision": rev,
            "coordinator_session_id": args.coordinator_session_id,
        }
        if args.coordinator_command == "request":
            payload = {
                "schema": "paos-coordinator-request-create/v1",
                "operation_id": op,
                "expected_revision": rev,
                "session_id": args.coordinator_session_id,
                "requests": [
                    {
                        "request_type": args.request_type,
                        "target_session_id": args.target_session_id,
                        "target_identity_id": args.target_identity_id or "",
                        "description": text_arg(args.description, "description", required=True),
                    }
                ],
            }
            path = root + "/requests"
        return post_mutation(client, path, payload, op, rev)

    raise CliError("unsupported command", error_code="unsupported_command")


def add_mutation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--operation-id",
        help="Optional idempotency key; generated when omitted",
    )
    parser.add_argument(
        "--revision",
        type=int,
        help="Optimistic-lock revision; current revision is read when omitted",
    )


def add_session_write_args(parser: argparse.ArgumentParser) -> None:
    add_mutation_args(parser)


def add_session_handoff_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--handoff-to", help="Target Agent for a durable post-report handoff")
    parser.add_argument("--handoff-subject", help="Required durable handoff Mail subject")
    parser.add_argument("--handoff-body", help="Required durable handoff Mail body, @FILE or '-' for stdin")
    parser.add_argument("--handoff-message-id", help="Stable Mail id; defaults to this Session operation-id")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="paos",
        description=(
            "PAOS Agent/Runtime workflows and supported Coordinator governance. "
            "Actions that remain explicitly Human-owned stay on the approved Human "
            "surface. Text values accept "
            "literal text, @FILE, or '-' for UTF-8 stdin (use @@... for a literal leading @)."
        ),
    )
    p.add_argument(
        "--base-url",
        help=(
            "PAOS origin. Resolution: --base-url > PAOS_BASE_URL > local config "
            "> http://127.0.0.1:8766"
        ),
    )
    p.add_argument(
        "--config-file",
        help="Override the user config path (default ~/.paos/config.json)",
    )
    p.add_argument(
        "--installation-file",
        help="Override the installation descriptor path (default ~/.paos/installation.json)",
    )
    p.add_argument(
        "--agent-numbers-file",
        help=(
            "Override the unique staff-number registry path (default: AgentNumBers locator from installation descriptor)"
        ),
    )
    p.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit machine-readable JSON, including structured errors",
    )
    p.add_argument(
        "--full-result",
        dest="full_result",
        action="store_true",
        default=None,
        help=(
            "For mutating commands (session update/report, request-resolve): "
            "emit the original full receipt (session history etc.) instead of "
            "the compact default. Failures always print failure fields."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)
    add_cat_parser(sub)

    sub.add_parser("health", help="Check PAOS reachability")

    home = sub.add_parser("home", help="Read-only same-source status view")
    home.add_argument(
        "--write",
        dest="write",
        metavar="PATH",
        help="Write the generated region of the given PAOS-HOME.md; markers required",
    )

    ports = sub.add_parser("ports", help="Derived service/port view with real bind+health probes")
    ports.add_argument("--no-probe", dest="probe", action="store_false", help="Derive rows only")
    ports.add_argument("--probe-host", dest="probe_host", default="127.0.0.1", help="Bind probe host")

    orient = sub.add_parser(
        "orient",
        help="Recover identity, current TODO, Mail and entry points",
    )
    orient.add_argument("project_id")
    orient.add_argument("agent_id")
    orient.add_argument("--root", help="Override Project root when root_path is missing")

    status = sub.add_parser(
        "status",
        help="Show installation, current responsibility, contact and handoff evidence",
    )
    status.add_argument("project_id")
    status.add_argument("agent_id")
    status.add_argument("--root", help="Override Project root when root_path is missing")
    status.add_argument("--message-id", help="Inspect one outgoing durable Mail dispatch")

    inbox = sub.add_parser(
        "inbox",
        help="Read durable Workstation Mail separately from formal PAOS Requests",
    )
    inbox.add_argument("project_id")
    inbox.add_argument("agent_id")
    inbox.add_argument("--root", help="Override Project root when root_path is missing")

    attention = sub.add_parser(
        "attention",
        help="V1.3 Home TODO/NOTICE/source service; never submits native turns inline",
    )
    attention_sub = attention.add_subparsers(dest="attention_command", required=True)

    x = attention_sub.add_parser("show", help="Read one Project Agent Home TODO/NOTICE state")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--root")

    x = attention_sub.add_parser("handle", help="Handle one Notice through the unified input state")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("notice_id")
    x.add_argument("--resolution")
    x.add_argument("--action-ref")
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "read",
        help="Explicitly mark one Notice read; reading/listing alone never changes read state",
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("notice_id")
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "takeover",
        help=(
            "Read one Notice source, explicitly mark it read, then switch only "
            "the submitted Current fields of this exact Home"
        ),
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("notice_id")
    x.add_argument(
        "--set",
        dest="sets",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="Repeatable Current field update; at least one is required",
    )
    x.add_argument("--expected-fingerprint", help="Refuse if the TODO changed since this sha256")
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "notice-update",
        help="Edit Notice summary/order/archive metadata without changing source or handling",
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("notice_id")
    x.add_argument("--summary", help="Edit Notice attention summary only; source body is unchanged")
    x.add_argument("--sort-order", type=int, help="Manual display order; lower values sort first")
    view = x.add_mutually_exclusive_group()
    view.add_argument(
        "--archive",
        action="store_true",
        help="Presentation-only archive; does not handle/cancel or clear activation intent",
    )
    view.add_argument(
        "--restore",
        action="store_true",
        help="Restore an archived Notice to the active presentation group",
    )
    x.add_argument("--operation-id", help="Stable idempotency key for this organize update")
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "todo-write",
        help="Replace this exact Project Agent Home TODO v3 after identity validation",
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--body", required=True, help="TODO Markdown, @FILE, or '-' for stdin")
    x.add_argument(
        "--expected-fingerprint",
        help="Optimistic lock: only write if the current TODO sha256 matches this value",
    )
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "todo-update",
        help=(
            "Update only the named Current fields of this Home's one TODO v3; "
            "metadata, unmentioned Current fields and the whole Task body are kept"
        ),
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument(
        "--set",
        dest="sets",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help=(
            "Repeatable Current field update (e.g. --set stage='...' "
            "--set next_action='...'). Fields: objective, approved_scope, stage, "
            "next_action, waiting, results, inflight, alignment_ref, input_version, "
            "delivery, dependencies, continuation_to, boundaries, history_ref, "
            "latest_readback, updated_at, legacy_source_ref, result_refs, context_refs "
            "(list fields collect each --set value in order)"
        ),
    )
    x.add_argument(
        "--expected-fingerprint",
        help="Optimistic lock: only write if the current TODO sha256 matches this value",
    )
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "source-register",
        help="Register one already-durable direct source for an exact Project Agent Home",
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument(
        "--source-ref",
        required=True,
        help="Existing durable carrier locator: absolute/UNC path or http(s) URL",
    )
    x.add_argument("--summary", required=True, help="Short attention summary; not the body")
    x.add_argument("--activate", action="store_true")
    x.add_argument("--activation-request-id")
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "source-status",
        help="Read Notice progress by stable source identity",
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--source-kind", required=True, choices=["mail", "cat", "direct", "system"])
    x.add_argument("--source-ref", required=True)
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "send",
        help="Persist Mail + Notice; optionally request activation without waking inline",
    )
    x.add_argument("project_id")
    recipients = x.add_mutually_exclusive_group(required=True)
    recipients.add_argument("--to", action="append", help="Exact target Agent id; repeatable")
    recipients.add_argument("--broadcast", action="store_true")
    x.add_argument("--subject", required=True)
    x.add_argument("--body", required=True, help="Markdown body, @FILE, or '-' for stdin")
    x.add_argument(
        "--sender-kind",
        default="human",
        choices=["human", "system", "coordinator", "agent", "external"],
    )
    x.add_argument("--sender-id")
    x.add_argument("--message-id")
    x.add_argument(
        "--activate",
        action="store_true",
        help="Persist one activation intent (durable, no inline wake); a separate wake by a legitimate caller wakes the Runtime once",
    )
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "notify",
        help="Persist one activation intent for an existing Mail source (durable; no inline wake — a separate legitimate caller trigger wakes the Runtime once)",
    )
    x.add_argument("project_id")
    x.add_argument("message_id")
    x.add_argument("--agent", dest="agents", action="append")
    x.add_argument("--activation-request-id")
    x.add_argument("--root")

    x = attention_sub.add_parser(
        "rooter-show",
        help="Read the registered Rooter Home without creating a Project Session",
    )
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-read",
        help="Explicitly mark one Notice read in the registered Rooter Home",
    )
    x.add_argument("notice_id")
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-handle",
        help="Handle one Notice in the registered Rooter Home",
    )
    x.add_argument("notice_id")
    x.add_argument("--resolution")
    x.add_argument("--action-ref")
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-notice-update",
        help="Edit registered Rooter Notice summary/order/archive metadata",
    )
    x.add_argument("notice_id")
    x.add_argument("--summary", help="Edit Notice attention summary only; source body is unchanged")
    x.add_argument("--sort-order", type=int, help="Manual display order; lower values sort first")
    view = x.add_mutually_exclusive_group()
    view.add_argument(
        "--archive",
        action="store_true",
        help="Presentation-only archive; does not handle/cancel or clear activation intent",
    )
    view.add_argument(
        "--restore",
        action="store_true",
        help="Restore an archived Notice to the active presentation group",
    )
    x.add_argument("--operation-id", help="Stable idempotency key for this organize update")
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-takeover",
        help="Take over one registered Rooter Notice and switch only submitted Current fields",
    )
    x.add_argument("notice_id")
    x.add_argument("--set", dest="sets", action="append", default=[], metavar="FIELD=VALUE")
    x.add_argument("--expected-fingerprint")
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-todo-update",
        help=(
            "Update only the named Current fields of the registered Rooter Home's "
            "one TODO v3; metadata, unmentioned Current fields and the whole Task body are kept"
        ),
    )
    x.add_argument(
        "--set",
        dest="sets",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help=(
            "Repeatable Current field update (e.g. --set stage='...' "
            "--set next_action='...'). Fields: objective, approved_scope, stage, "
            "next_action, waiting, results, inflight, alignment_ref, input_version, "
            "delivery, dependencies, continuation_to, boundaries, history_ref, "
            "latest_readback, updated_at, legacy_source_ref, result_refs, context_refs "
            "(list fields collect each --set value in order)"
        ),
    )
    x.add_argument(
        "--expected-fingerprint",
        help="Optimistic lock: only write if the current TODO sha256 matches this value",
    )
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-todo-write",
        help="Replace registered Rooter TODO v3 after identity validation",
    )
    x.add_argument("--body", required=True, help="TODO Markdown, @FILE, or '-' for stdin")
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-source-register",
        help="Register one already-durable direct source in the registered Rooter Home",
    )
    x.add_argument(
        "--source-ref",
        required=True,
        help="Existing durable carrier locator: absolute/UNC path or http(s) URL",
    )
    x.add_argument("--summary", required=True, help="Short attention summary; not the body")
    x.add_argument("--activate", action="store_true")
    x.add_argument("--activation-request-id")
    x.add_argument("--home-id", default="rooter-001")

    x = attention_sub.add_parser(
        "rooter-source-status",
        help="Read registered Rooter Notice progress by stable source identity",
    )
    x.add_argument("--source-kind", required=True, choices=["mail", "cat", "direct", "system"])
    x.add_argument("--source-ref", required=True)
    x.add_argument("--home-id", default="rooter-001")

    peers = sub.add_parser(
        "peers",
        help="List durable Project Agents with TODO and Runtime contact",
    )
    peers.add_argument("project_id")
    peers.add_argument("agent_id")
    peers.add_argument("--root", help="Override Project root when root_path is missing")
    peers.add_argument("--probe", action="store_true", help="Fresh-probe each bound peer Runtime now")

    team = sub.add_parser(
        "team",
        help="Stable team entry: long-term Agents, TODO links and Runtime attach",
    )
    team.add_argument("project_id")
    team.add_argument("agent_id")
    team.add_argument("--root", help="Override Project root when root_path is missing")
    team.add_argument("--probe", action="store_true", help="Fresh-probe each bound Runtime now")

    agent = sub.add_parser(
        "agent",
        help=(
            "Agent durable communication: Mail/CAT persists and records an activation intent; "
            "an explicit one-shot native reminder uses --remind"
        ),
    )
    agents = agent.add_subparsers(dest="agent_command", required=True)

    x = agents.add_parser(
        "send",
        help=(
            "Persist Workstation Mail to stable Agent(s). Default: durable delivery + activation "
            "intent only (no inline wake). With --remind: also send one native reminder via Contact/"
            "runtime_injection; no polling or retry."
        ),
    )
    x.add_argument("project_id")
    recipients = x.add_mutually_exclusive_group(required=True)
    recipients.add_argument(
        "--to",
        action="append",
        help="Exact stable Agent id; repeatable",
    )
    recipients.add_argument(
        "--broadcast",
        action="store_true",
        help="Freeze all non-historical Project Agents as the durable recipient set",
    )
    x.add_argument("--subject", required=True)
    x.add_argument(
        "--body",
        required=True,
        help="Markdown body, @FILE, or '-' for stdin",
    )
    x.add_argument(
        "--sender-kind",
        default="human",
        choices=["human", "system", "coordinator", "agent", "external"],
    )
    x.add_argument("--sender-id")
    x.add_argument("--message-id", help="Stable idempotency key for the whole Agent message")
    x.add_argument(
        "--remind",
        action="store_true",
        help="显式一次原生提醒：Mail 持久投递后，按 Contact 与 runtime_injection 对每个正常投递 Home 一次性注入；不能注入如实 manual_required / native_rejected；不做后台轮询与重试器。",
    )
    x.add_argument("--root")

    x = agents.add_parser(
        "chat",
        help="Persist CAT Exchange and register a Notice activation intent; whether the target Runtime turns is decided by its own native loop",
    )
    x.add_argument("project_id")
    x.add_argument("--room", required=True, help="CAT Room id with activation_owner=paos")
    x.add_argument("--to", required=True, help="Exact stable target Agent id")
    x.add_argument("--body", required=True, help="CAT message body, @FILE, or '-' for stdin")
    x.add_argument("--from-agent", help="Stable sender Agent id; omit for human")
    x.add_argument("--message-id", help="Stable idempotency key for CAT send + Agent activation")
    x.add_argument("--reply-to", help="Optional exact CAT Exchange id being replied to")
    x.add_argument(
        "--cat-base",
        help="CAT origin; default CAT_BASE_URL or http://127.0.0.1:8770",
    )
    x.add_argument("--root")

    x = agents.add_parser(
        "notify",
        help="Notify stable Agent recipients from one already-persisted durable source",
    )
    x.add_argument("project_id")
    source = x.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--mail",
        dest="mail_message_id",
        help="Existing Workstation Mail message id; frozen recipients are reused",
    )
    source.add_argument(
        "--cat-exchange",
        dest="cat_exchange_ref",
        help="Existing CAT source as <room-id>:<exchange-id>",
    )
    x.add_argument(
        "--agent",
        dest="agents",
        action="append",
        help=(
            "Optional exact stable Agent expected from the durable source. "
            "Repeatable for Mail; CAT accepts at most one."
        ),
    )
    x.add_argument(
        "--cat-base",
        help="CAT origin for --cat-exchange; default CAT_BASE_URL or http://127.0.0.1:8770",
    )
    x.add_argument(
        "--activation-request-id",
        help="Stable V1.3 activation intent id for safe retry; omit for a new explicit cycle",
    )
    x.add_argument("--root")

    wake = sub.add_parser(
        "wake",
        help="Workless contact surface: native-target bind/status/unbind + one-shot trigger; probe/recover/stop/test retired (not on help)",
    )
    wakes = wake.add_subparsers(dest="wake_command", required=True)

    x = wakes.add_parser(
        "bind",
        help="Store the Contact native target (runtime/session/… from --driver-config) for one Agent",
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--driver", required=True, help="原生 runtime 名（codex / opencode / workbuddy）")
    x.add_argument("--runtime-id")
    x.add_argument("--native-session-id")
    x.add_argument(
        "--driver-config",
        help="Optional UTF-8 JSON file containing native target config (base_url/…)",
    )
    x.add_argument("--root")

    x = wakes.add_parser("status")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--root")

    x = wakes.add_parser(
        "trigger",
        help="Send one reminder through the standalone native injection tool (no attempt machine)",
    )
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--prompt", help="Literal, @FILE or '-' inject message")
    x.add_argument("--source-kind", default="manual", choices=["manual", "system"])
    x.add_argument("--source-id")
    x.add_argument(
        "--model",
        help='Human-specified model only; omit to inherit the target model. OpenCode: JSON '
             '{"providerID":"opencode","modelID":"MODEL_ID"}; '
             'Codex/WorkBuddy: native model string.',
    )
    x.add_argument("--root")

    x = wakes.add_parser("unbind", help="Drop the Contact native target for one Agent")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--root")

    mail = sub.add_parser(
        "mail",
        help="Durable Markdown mail in Project-local Agent Workstations",
    )
    mails = mail.add_subparsers(dest="mail_command", required=True)

    x = mails.add_parser("send", help="Persist targeted or broadcast Workstation Mail")
    x.add_argument("project_id")
    recipients = x.add_mutually_exclusive_group(required=True)
    recipients.add_argument("--to", action="append", help="Exact Agent ID; repeatable")
    recipients.add_argument(
        "--broadcast",
        action="store_true",
        help="Freeze all non-historical Project Agents as the recipient set",
    )
    x.add_argument("--subject", required=True)
    x.add_argument(
        "--body",
        required=True,
        help="Markdown body, @FILE, or '-' for stdin",
    )
    x.add_argument(
        "--sender-kind",
        default="human",
        choices=["human", "system", "coordinator", "agent", "external"],
    )
    x.add_argument("--sender-id")
    x.add_argument("--message-id", help="Stable idempotency key for retry")
    x.add_argument("--root")

    x = mails.add_parser("reply", help="Reply to an Agent Mail in this Agent's inbox")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("in_reply_to")
    x.add_argument("--body", required=True, help="Markdown body, @FILE, or '-' for stdin")
    x.add_argument("--subject", help="Override the default Re: subject")
    x.add_argument("--message-id", help="Stable idempotency key for retry")
    x.add_argument("--root")

    x = mails.add_parser("list", help="List durable Markdown mail for one Agent")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("--root")

    x = mails.add_parser("read", help="Read one durable Markdown mail file")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("message_id")
    x.add_argument("--root")

    x = mails.add_parser("handle", help="Record that one received Mail was handled")
    x.add_argument("project_id")
    x.add_argument("agent_id")
    x.add_argument("message_id")
    x.add_argument("--state", choices=["handled", "incorporated"], default="handled")
    x.add_argument("--reason", help="Short reason for the handling marker")
    x.add_argument("--root")

    x = mails.add_parser(
        "status",
        help="Check immutable dispatch recipient delivery state",
    )
    x.add_argument("project_id")
    x.add_argument("message_id")
    x.add_argument("--root")

    lib = sub.add_parser(
        "library",
        help="Manage filesystem-only Workflow / Skill libraries",
    )
    libs = lib.add_subparsers(dest="library_command", required=True)

    for name in ("init", "catalog"):
        x = libs.add_parser(name)
        x.add_argument("kind", choices=["workflow", "skill"])
        x.add_argument("--root", required=True)

    x = libs.add_parser("tools", help="Read the registered local Tool Catalog (read-only)")

    x = libs.add_parser(
        "search",
        help="Search active resources in the installation-registered Workflow/Skill Libraries",
    )
    x.add_argument("query", help="1–200 character query; all distinct whitespace-separated terms must match")
    x.add_argument("--kind", choices=["all", "workflow", "skill"], default="all")
    x.add_argument("--limit", type=int, choices=range(1, 51), default=20)

    x = libs.add_parser(
        "skill-use",
        help="Record one Skill use and rebuild derived Skill catalog stats",
    )
    x.add_argument("--root", required=True)
    x.add_argument("--skill-id", required=True)
    x.add_argument("--score", required=True, choices=["0", "0.3", "0.5", "1"])
    x.add_argument("--project-id")
    x.add_argument("--agent-id")
    x.add_argument("--work-id")
    x.add_argument("--note")


    roots = libs.add_parser(
        "roots",
        help="Register/show canonical machine-local Workflow and Skill roots",
    )
    roots_sub = roots.add_subparsers(dest="roots_command", required=True)

    x = roots_sub.add_parser("show")
    x.add_argument("--config", dest="roots_config")

    x = roots_sub.add_parser("set")
    x.add_argument("--workflow-root", required=True)
    x.add_argument("--skill-root", required=True)
    x.add_argument("--tool-catalog", help="Absolute path to the registered paos-tool-catalog/v1 file")
    x.add_argument("--config", dest="roots_config")

    tips = sub.add_parser("tips", help="Search and read the current Core-resolved Tips Inbox")
    tips_sub = tips.add_subparsers(dest="tips_command", required=True)
    x = tips_sub.add_parser("search", help="Deterministic all-term search of current Inbox Tips")
    x.add_argument("query")
    x.add_argument("--project", action="append", help="Exact captured project-text filter; repeat is rejected")
    x.add_argument("--limit", type=int, choices=range(1, 51), default=20)
    x = tips_sub.add_parser("read", help="Read one Tip by stable ID from the current Inbox")
    x.add_argument("tip_id")
    x = tips_sub.add_parser("correct", help="Append one immutable Tip correction version")
    x.add_argument("--body", required=True, help="Correction request JSON, @FILE, or '-' for stdin")
    x = tips_sub.add_parser("history", help="Derive the linear version chain for a Tip")
    x.add_argument("tip_id")
    x = tips_sub.add_parser("absorptions", help="Where registered Workflow methods absorbed this Tip version")
    x.add_argument("tip_id")
    x.add_argument("--source-sha256", required=True, help="Exact original-byte SHA from tips read")

    cfg = sub.add_parser("config", help="Inspect or persist CLI connection config")
    cfgs = cfg.add_subparsers(dest="config_command", required=True)
    cfgs.add_parser("show", help="Show configured/effective PAOS base URL")
    x = cfgs.add_parser("set-base-url", help="Persist the PAOS base URL for this user")
    x.add_argument("value")

    workbench = sub.add_parser("workbench", help="Rebuild Markdown workbench pages")
    workbenches = workbench.add_subparsers(dest="workbench_command", required=True)
    wb = workbenches.add_parser("build", help="Rebuild install/project/home/resource Markdown pages")
    wb.add_argument("--home", action="append", help="Exact Home id to include (repeatable)")
    wb.add_argument("--project", action="append", help="Project id to include (repeatable)")
    wb.add_argument("--changed-only", action="store_true", help="Skip pages whose source signature is unchanged")
    scan = workbenches.add_parser("scan", help="Process dirty Home markers once (host maintenance/cron)")
    scan.add_argument("--limit", type=int, default=32)
    watch = workbenches.add_parser("watch", help="Host maintenance loop: scan dirty markers every interval")
    watch.add_argument("--interval", type=int, default=60)
    watch.add_argument("--once", action="store_true")

    install = sub.add_parser(
        "install",
        help="Inspect or configure machine-local PAOS installation locators",
    )
    installs = install.add_subparsers(dest="install_command", required=True)
    installs.add_parser("show", help="Show the installation descriptor and Library registry state")
    x = installs.add_parser(
        "rollback", help="Preview or apply an explicit program rollback preserving data_root"
    )
    x.add_argument("--target-source", required=True)
    x.add_argument("--compatibility-file")
    x.add_argument("--apply", action="store_true")
    x = installs.add_parser(
        "plan", help="Read-only upgrade diff and retire preview for this installation"
    )
    x.add_argument("--target-source", help="Explicit target Source tree for upgrade diff")
    x.add_argument("--retire", action="store_true", help="Include retire preview")
    x = installs.add_parser(
        "homes", help="Read-only coverage of every registered Project Agent and Rooter Home"
    )
    x.add_argument("--project", help="Exact Project ID filter")
    x.add_argument("--home", help="Exact Home ID filter")
    x = installs.add_parser("configure", help="Write the machine-local installation descriptor")
    x.add_argument("--source-root", required=True)
    x.add_argument(
        "--data-root",
        help="Absolute installation data root; omit only to keep an existing registered value",
    )
    x.add_argument("--library-roots-config", required=True)
    x.add_argument(
        "--rooter-home",
        help="Optional absolute path of the registered installation-level Rooter Home",
    )

    a = sub.add_parser("authority", help="Inspect current action authority")
    a.add_argument("--actor", choices=["human", "coordinator", "worker"])
    a.add_argument("--allowed-only", action="store_true")

    for name in ("relations", "needs-me"):
        x = sub.add_parser(name)
        x.add_argument("project_id")

    pr = sub.add_parser("project", help="Inspect Project facts and authorized Agent progress")
    prs = pr.add_subparsers(dest="project_command", required=True)
    x = prs.add_parser(
        "progress-update",
        help="Update only generated Project progress fields through a matching managed Session",
    )
    x.add_argument("project_id")
    session_ref_group = x.add_mutually_exclusive_group(required=True)
    session_ref_group.add_argument("--session-id", help="Managed PAOS Session ID")
    session_ref_group.add_argument("--handshake-id", help="Existing managed handshake ID")
    x.add_argument("--expected-revision", type=int, required=True)
    x.add_argument("--update-id", help="Stable up- ID; reuse unchanged after an uncertain result")
    x.add_argument("--reason", required=True)
    x.add_argument("--stage", help="Patch generated.stage")
    x.add_argument("--progress-and-results", help="Patch generated.progress_and_results")
    x.add_argument("--recent-change", help="Patch generated.recent_change")
    x.add_argument("--current-gap", help="Patch generated.current_gap")

    x = prs.add_parser("experience", help="Read the registered Project's Materials/TIPS.md (read-only)")
    x.add_argument("project_id")
    x = prs.add_parser(
        "acceptance-check",
        help="Verify one acceptance_refs entry's local registered bytes (read-only)",
    )
    x.add_argument("project_id")
    x.add_argument("--home", required=True, help="Registered Project Agent Home ID")
    x.add_argument("--task", required=True, help="TODO Task ID")
    x.add_argument("--ref-index", type=int, required=True, help="Zero-based acceptance_refs index")
    x.add_argument("--todo-sha256", required=True, help="TODO fingerprint_sha256 from the Home work read")
    x = prs.add_parser(
        "outcomes",
        help="Read Project Artifact, Decision and recorded Close history (summary by default)",
    )
    x.add_argument("project_id")
    x.add_argument("--full", action="store_true", help="Return the complete outcomes projection")

    for name in ("show", "inspect"):
        x = prs.add_parser(name)
        x.add_argument("project_id")

    s = sub.add_parser(
        "session",
        help="Inspect and manage the current Agent execution Session",
    )
    ss = s.add_subparsers(dest="session_command", required=True)

    for name in ("show", "context", "mailbox"):
        x = ss.add_parser(name)
        x.add_argument("project_id")
        x.add_argument("session_id")

    x = ss.add_parser("ack", help="Record an explicit Session acknowledgement")
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument("--understood-objective", required=True)
    x.add_argument("--agent-label")
    x.add_argument("--environment")
    x.add_argument("--runtime-title")
    x.add_argument("--native-session-id")
    x.add_argument("--source-path")
    x.add_argument("--runtime-id")
    x.add_argument("--model-id")
    x.add_argument("--boundary", action="append")
    x.add_argument("--first-step", action="append")
    x.add_argument("--risk", action="append")
    add_session_write_args(x)

    x = ss.add_parser("update", aliases=["report"], help="Write current progress")
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument(
        "--status",
        default="working",
        choices=["not_started", "working", "blocked", "done", "review"],
    )
    x.add_argument("--summary")
    x.add_argument("--blocker", action="append")
    x.add_argument("--next-action", action="append")
    x.add_argument(
        "--body",
        help="Optional extra Session Update JSON file, or '-' for stdin; protected protocol fields cannot be overridden",
    )
    add_session_write_args(x)
    add_session_handoff_args(x)

    x = ss.add_parser(
        "artifact-add",
        help="Register a durable Artifact",
    )
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument("--path", required=True)
    x.add_argument("--type", default="session_archive")
    x.add_argument("--purpose")
    x.add_argument(
        "--work-id",
        help="Related Work id; optional",
    )
    x.add_argument("--replaces")
    x.add_argument("--change-summary")
    x.add_argument("--version-provider")
    x.add_argument("--version-revision")
    x.add_argument("--version-path")
    add_session_write_args(x)

    x = ss.add_parser("request-create", help="Create a Request through Session Update")
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument("--request-type", required=True, choices=REQUEST_TYPES)
    x.add_argument("--description", required=True)
    x.add_argument("--requires-human", action="store_true")
    x.add_argument("--target-identity-id")
    x.add_argument("--target-session-id")
    add_session_write_args(x)

    x = ss.add_parser("request-resolve", help="Resolve/cancel a Request through Session Update")
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument("request_id")
    x.add_argument("--status", required=True, choices=["resolved", "cancelled"])
    x.add_argument("--resolution")
    add_session_write_args(x)

    x = ss.add_parser(
        "close",
        aliases=["submit"],
        help="Close this Agent execution Session and record handoff evidence",
    )
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument(
        "--result",
        required=True,
        choices=["completed", "partial", "blocked", "abandoned"],
    )
    x.add_argument("--summary")
    x.add_argument("--remaining", action="append")
    x.add_argument("--recommended-next")
    x.add_argument(
        "--body",
        help="Optional extra Close JSON file, or '-' for stdin; protected protocol fields cannot be overridden",
    )
    add_session_write_args(x)
    add_session_handoff_args(x)

    c = sub.add_parser("coordinator", help="Dedicated Coordinator governance commands")
    cs = c.add_subparsers(dest="coordinator_command", required=True)

    x = cs.add_parser(
        "control",
        help="Thin read-only Coordinator control view over existing projections",
    )
    x.add_argument("project_id")
    x.add_argument(
        "--since-revision",
        type=int,
        help="Optional previous Project revision; include only newer ledger events",
    )

    x = cs.add_parser(
        "guide-promote",
        help="Promote one exactly reviewed canonical Guide candidate (real file input)",
    )
    x.add_argument("project_id")
    x.add_argument("--coordinator-session-id", required=True)
    x.add_argument("--candidate", required=True, help="Reviewed candidate GUIDE.md path")
    x.add_argument("--canonical", required=True, help="Canonical GUIDE.md path")
    x.add_argument("--expected-candidate-sha256", required=True)
    x.add_argument("--change-summary")
    add_mutation_args(x)

    for name in ("request",):
        x = cs.add_parser(name)
        x.add_argument("project_id")
        x.add_argument("--coordinator-session-id", required=True)
        add_mutation_args(x)
        x.add_argument("--request-type", required=True, choices=REQUEST_TYPES)
        x.add_argument("--target-session-id")
        x.add_argument("--target-identity-id")
        x.add_argument("--description", required=True)

    w = sub.add_parser(
        "workstation",
        help="Create, inspect and prepare the stable Agent Workstation",
    )
    ws = w.add_subparsers(dest="workstation_command", required=True)

    x = ws.add_parser(
        "init",
        help="Create or repair the stable Project-local Agent Workstation",
    )
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument("--root")
    x.add_argument("--objective")
    x.add_argument("--workflow-library")
    x.add_argument("--skill-library")

    x = ws.add_parser(
        "show",
        help="Read the stable Agent Workstation TODO and mailbox state",
    )
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument("--root")

    x = ws.add_parser(
        "guide-diff",
        help="Compare one reviewed candidate GUIDE file against its canonical source",
    )
    x.add_argument("project_id")
    x.add_argument("session_id")
    x.add_argument("--candidate", required=True, help="Candidate GUIDE.md path")
    x.add_argument("--canonical", required=True, help="Canonical GUIDE.md path")
    x.add_argument("--root")
    return p


def render_plain_error(exc: CliError) -> str:
    lines = [f"ERROR [{exc.error_code or 'cli_error'}]: {exc}"]
    os_error = (exc.details or {}).get("os_error")
    if os_error:
        lines.append(f"CAUSE: {os_error}")
    for issue in (exc.details or {}).get("issues") or []:
        locator = issue.get("locator") or issue.get("path") or ""
        lines.append(
            f"- [{issue.get('kind') or 'item'}] {issue.get('raw') or locator}"
            f" -> {issue.get('reason') or 'unknown'}"
        )
    if exc.hint:
        lines.append(f"HINT: {exc.hint}")
    if exc.operation_id:
        lines.append(f"operation: {exc.operation_id}")
    if exc.revision is not None:
        lines.append(f"revision: {exc.revision}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = resolve_config_path(args.config_file)
    installation_path = resolve_installation_path(args.installation_file)
    try:
        if args.command == "cat":
            base_url = args.url
        elif args.command == "install":
            base_url = DEFAULT_BASE_URL
        elif args.command == "config" and args.config_command == "set-base-url":
            # Config repair must not depend on the previously configured/env origin.
            # RestClient validates the new value, but this command performs no HTTP.
            base_url = args.value
        else:
            base_url = resolve_base_url(args.base_url, config_path)
        client = RestClient(base_url, service="CAT" if args.command == "cat" else "PAOS")
        result = execute(
            args,
            client,
            config_path=config_path,
            installation_path=installation_path,
        )
    except CliError as exc:
        if args.json_output:
            print(
                json.dumps(exc.as_dict(), ensure_ascii=False, indent=2),
                file=sys.stderr,
            )
        else:
            print(render_plain_error(exc), file=sys.stderr)
        return 1
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
