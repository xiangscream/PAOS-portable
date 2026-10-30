"""A14 external (non-member) send/notify authorization and idempotency."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_BODY = 64 * 1024
DEFAULT_RATE = (10, 60)
SCHEMA = "paos-external-grants/v1"


class ExternalContactProblem(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _grants_path(data_root: Path) -> Path:
    return Path(data_root) / "contact" / "external-callers.json"


def load_grants(data_root: Path) -> list[dict[str, Any]]:
    path = _grants_path(data_root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as error:
        raise ExternalContactProblem("external_grants_unreadable", "外部调用授权配置不可读。", {"path": str(path)}) from error
    if not isinstance(value, dict) or value.get("schema") != SCHEMA or not isinstance(value.get("grants"), list):
        raise ExternalContactProblem("external_grants_invalid", "外部调用授权配置结构无效。", {"path": str(path)})
    return [item for item in value["grants"] if isinstance(item, dict)]


def _target_key(home_ref: dict[str, Any]) -> str:
    if home_ref.get("home_kind") == "rooter":
        return "rooter:" + str(home_ref.get("home_id"))
    return f"project:{home_ref.get('project_id')}/{home_ref.get('home_id')}"


def _rate_path(data_root: Path) -> Path:
    return Path(data_root) / "contact" / "external-rate.json"


def _acquire_rate_guard(path: Path, timeout: float = 10.0) -> Path:
    """Cross-OS mutual exclusion via atomic directory creation.

    msvcrt/flock do not interoperate on the same DrvFs path; mkdir is atomic
    on both Windows and WSL. Stale lock directories older than 60s are removed.
    """
    lock = path.with_name(path.name + ".lockdir")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    while True:
        try:
            os.mkdir(lock)
            return lock
        except FileExistsError:
            if time.time() >= deadline:
                raise ExternalContactProblem("external_rate_busy", "外部限流锁等待超时。", {"path": str(lock)})
            time.sleep(0.05)


def _release_rate_guard(lock: Path) -> None:
    try:
        os.rmdir(lock)
    except OSError:
        pass


def _check_rate(data_root: Path, caller_id: str, limit: tuple[int, int]) -> float:
    path = _rate_path(data_root)
    _lock = _acquire_rate_guard(path)
    try:
        if path.exists():
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ExternalContactProblem("external_rate_state_invalid", "外部限流状态损坏，拒绝投递。", {"path": str(path)}) from error
            if not isinstance(state, dict):
                raise ExternalContactProblem("external_rate_state_invalid", "外部限流状态损坏，拒绝投递。", {"path": str(path)})
        else:
            state = {}
        now = time.time()
        count, window = limit
        entries = [float(item) for item in (state.get(caller_id) or []) if isinstance(item, (int, float))]
        entries = [item for item in entries if now - item < window]
        if len(entries) >= count:
            raise ExternalContactProblem("external_rate_limited", "外部调用超过授权限额。", {"caller_id": caller_id})
        entries.append(now)
        state[caller_id] = entries
        temporary = path.with_name(f".{path.name}.staging-{os.getpid()}")
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
        return now
    finally:
        _release_rate_guard(_lock)


def _release_rate(data_root: Path, caller_id: str, token: float) -> None:
    path = _rate_path(data_root)
    _lock = _acquire_rate_guard(path)
    try:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        entries = [float(item) for item in (state.get(caller_id) or []) if isinstance(item, (int, float))]
        if token in entries:
            entries.remove(token)
        state[caller_id] = entries
        temporary = path.with_name(f".{path.name}.staging-{os.getpid()}")
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        _release_rate_guard(_lock)


def verify_grant(
    *, installation_file: str | Path, caller_id: str, token: str,
    home_ref: dict[str, Any], action: str,
) -> dict[str, Any]:
    from paos_installation import effective_data_root, load_installation_descriptor, resolve_installation_path

    descriptor = load_installation_descriptor(resolve_installation_path(str(installation_file)))
    data_root = effective_data_root(descriptor)
    token_hash = _sha256(token.encode("utf-8")) if token else ""
    target = _target_key(home_ref)
    for grant in load_grants(data_root):
        if str(grant.get("caller_id") or "") != caller_id:
            continue
        if bool(grant.get("revoked")):
            raise ExternalContactProblem("external_grant_revoked", "外部调用授权已撤销。", {"caller_id": caller_id})
        if not token_hash or str(grant.get("token_sha256") or "") != token_hash:
            raise ExternalContactProblem("external_token_invalid", "外部调用凭据无效。", {"caller_id": caller_id})
        targets = grant.get("targets")
        if not isinstance(targets, list) or not targets or not all(isinstance(item, str) and item for item in targets):
            raise ExternalContactProblem("external_grant_invalid", "授权 targets 必须是准确字符串列表。", {"grant_id": grant.get("grant_id")})
        if target not in targets:
            raise ExternalContactProblem("external_target_forbidden", "目标不在授权范围。", {"target": target})
        actions = grant.get("actions")
        if not isinstance(actions, list) or not actions or not all(isinstance(item, str) and item for item in actions):
            raise ExternalContactProblem("external_grant_invalid", "授权 actions 必须是准确字符串列表。", {"grant_id": grant.get("grant_id")})
        if action not in actions:
            raise ExternalContactProblem("external_action_forbidden", "动作不在授权范围。", {"action": action})
        limits = grant.get("limits") or {}
        return {
            "caller_id": caller_id,
            "grant_id": str(grant.get("grant_id") or ""),
            "target": target,
            "max_bytes": int(limits.get("max_bytes") or MAX_BODY),
            "rate": (
                int(limits.get("rate_count") or DEFAULT_RATE[0]),
                int(limits.get("rate_seconds") or DEFAULT_RATE[1]),
            ),
            "data_root": data_root,
        }
    raise ExternalContactProblem("external_grant_missing", "外部调用方未登记或凭据不符。", {"caller_id": caller_id})


def external_message_id(caller_id: str, home_ref: dict[str, Any], external_id: str) -> str:
    key = f"{caller_id}\0{_target_key(home_ref)}\0{external_id}".encode("utf-8")
    return "ext-" + _sha256(key)[:40]


def _cli() -> list[str]:
    return [sys.executable, "-X", "utf8", "-B", str(Path(__file__).with_name("paos.py"))]



def find_external_notice(home_ref: dict[str, Any], message_id: str) -> dict[str, Any] | None:
    from paos_notice import list_notices

    try:
        listing = list_notices(Path(str(home_ref["home_path"])))
    except Exception:
        return None
    for item in listing.get("items") or []:
        if str(item.get("source_kind") or "") == "mail" and str(item.get("source_ref") or "") == message_id:
            return item
    return None


def ensure_activation(home_ref: dict[str, Any], message_id: str, purpose: str) -> tuple[bool, str]:
    """Create one stable activation intent if absent; returns (created, notice_id)."""
    from paos_notice import request_notice_activation

    notice = find_external_notice(home_ref, message_id)
    if notice is None:
        raise ExternalContactProblem("external_message_missing", "该调用方在此目标没有对应外部消息。")
    notice_id = str(notice.get("notice_id") or "")
    request_id = f"external-{purpose}-{message_id}"
    activation_dir = Path(str(home_ref["home_path"])) / "notices" / ".activation" / notice_id
    if (activation_dir / f"{request_id}.json").is_file():
        return False, notice_id
    result = request_notice_activation(
        home_path=Path(str(home_ref["home_path"])),
        notice_id=notice_id,
        activation_request_id=request_id,
    )
    return bool(result.get("activation_request_created")), notice_id

def _mail_path(home_ref: dict[str, Any], message_id: str) -> Path:
    return Path(str(home_ref["home_path"])) / "mailbox" / f"{message_id}.md"


def send_external(
    *, installation_file: str | Path, caller_id: str, token: str,
    home_ref: dict[str, Any], external_id: str, subject: str, body_file: str,
    remind: bool,
) -> dict[str, Any]:
    grant = verify_grant(
        installation_file=installation_file, caller_id=caller_id, token=token,
        home_ref=home_ref, action="send",
    )
    if remind:
        verify_grant(
            installation_file=installation_file, caller_id=caller_id, token=token,
            home_ref=home_ref, action="remind",
        )
    body_path = Path(body_file)
    try:
        raw = body_path.read_bytes()
    except OSError as error:
        raise ExternalContactProblem("external_body_unreadable", "正文文件不可读。") from error
    if len(raw) > grant["max_bytes"]:
        raise ExternalContactProblem("external_body_too_large", "正文超过授权限额。")
    if len(raw) > MAX_BODY:
        raise ExternalContactProblem("external_body_too_large", "正文超过 64 KiB。")
    try:
        body = raw.decode("utf-8")
    except UnicodeError as error:
        raise ExternalContactProblem("external_body_invalid_utf8", "正文必须是 UTF-8。") from error
    message_id = external_message_id(caller_id, home_ref, external_id)
    mail_path = _mail_path(home_ref, message_id)
    rate_token = None
    if not mail_path.exists():
        rate_token = _check_rate(grant["data_root"], caller_id, grant["rate"])

    from paos_attention_service import _deliver_external_mail_copy

    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if mail_path.is_file():
        try:
            for line in mail_path.read_text(encoding="utf-8").splitlines()[:20]:
                if line.lower().startswith("created_at:"):
                    candidate = line.split(":", 1)[1].strip().strip('"')
                    if candidate:
                        created_at = candidate
                    break
        except OSError:
            pass
    project = {"id": str(home_ref.get("project_id") or "")}
    try:
        delivered = _deliver_external_mail_copy(
            home_ref=home_ref, project=project,
            envelope={
                "created_at": created_at, "sender_kind": "external",
                "sender_id": caller_id, "subject": subject, "body": body,
                "audience": "targeted",
            },
            message_id=message_id, request_activation=False,
            activation_request_id="",
        )
    except Exception as error:  # noqa: BLE001 - map shared conflict
        code = str(getattr(error, "code", "external_send_failed"))
        if code == "attention_external_mail_conflict" and mail_path.is_file():
            try:
                existing = mail_path.read_text(encoding="utf-8")
            except OSError:
                existing = ""
            winner_created_at = None
            for line in existing.splitlines()[:20]:
                if line.lower().startswith("created_at:"):
                    winner_created_at = line.split(":", 1)[1].strip().strip('"') or None
                    break
            same = False
            if winner_created_at:
                from paos_attention_service import _render_mail

                expected = _render_mail(
                    message_id=message_id,
                    project_id=str(home_ref.get("project_id") or ""),
                    recipient_id=str(home_ref.get("home_id") or ""),
                    created_at=winner_created_at,
                    sender_kind="external",
                    sender_id=caller_id,
                    subject=subject,
                    body=body,
                    audience="targeted",
                )
                same = expected == existing
            if same:
                if rate_token is not None:
                    _release_rate(grant["data_root"], caller_id, rate_token)
                return {"schema": "paos-external-contact/v1", "action": "send",
                        "home": home_ref, "message_id": message_id,
                        "mail_state": "already_delivered"}
        raise ExternalContactProblem(code, str(error)) from error
    result = {"schema": "paos-external-contact/v1", "action": "send", "home": home_ref, "message_id": message_id, **delivered}
    if remind:
        result["remind"] = {"state": "not_implemented_in_direct_path"}
    return result


def notify_external(
    *, installation_file: str | Path, caller_id: str, token: str,
    home_ref: dict[str, Any], external_id: str, remind: bool,
) -> dict[str, Any]:
    grant = verify_grant(
        installation_file=installation_file, caller_id=caller_id, token=token,
        home_ref=home_ref, action="notify",
    )
    if remind:
        verify_grant(
            installation_file=installation_file, caller_id=caller_id, token=token,
            home_ref=home_ref, action="remind",
        )
    message_id = external_message_id(caller_id, home_ref, external_id)
    mail_path = _mail_path(home_ref, message_id)
    if not mail_path.is_file():
        raise ExternalContactProblem("external_message_missing", "该调用方在此目标没有对应外部消息。")
    subject = external_id
    try:
        for line in mail_path.read_text(encoding="utf-8").splitlines()[:30]:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip().strip('"') or external_id
                break
    except OSError as error:
        raise ExternalContactProblem("external_message_unreadable", "外部消息不可读。") from error
    existing_notice = find_external_notice(home_ref, message_id)
    from paos_notice import create_notice

    request_id = f"external-notify-{message_id}"
    has_intent = False
    if existing_notice:
        activation_dir = (Path(str(home_ref["home_path"])) / "notices" / ".activation"
                          / str(existing_notice.get("notice_id") or ""))
        has_intent = (activation_dir / f"{request_id}.json").is_file()
    rate_token = None
    if not has_intent:
        rate_token = _check_rate(grant["data_root"], caller_id, grant["rate"])
    if existing_notice is None:
        try:
            create_notice(
                home_path=Path(str(home_ref["home_path"])),
                home_kind=str(home_ref["home_kind"]), home_id=str(home_ref["home_id"]),
                project_id=str(home_ref.get("project_id") or ""),
                source_kind="mail", source_ref=message_id, summary=subject,
            )
        except Exception as error:  # noqa: BLE001
            if rate_token is not None:
                _release_rate(grant["data_root"], caller_id, rate_token)
            raise ExternalContactProblem("external_notify_failed", str(error)) from error
    created, notice_id = ensure_activation(home_ref, message_id, "notify")
    if created and rate_token is None:
        # An older notice carried a different intent; reserve for this one.
        try:
            _check_rate(grant["data_root"], caller_id, grant["rate"])
        except ExternalContactProblem:
            raise
    notice = find_external_notice(home_ref, message_id) or {}
    return {
        "schema": "paos-external-contact/v1", "action": "notify",
        "home": home_ref, "message_id": message_id, "notice": notice,
        "remind": {"state": "not_implemented_in_direct_path"} if remind else None,
    }
