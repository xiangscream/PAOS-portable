"""CAT -> stable Agent activation for PAOS V1.1 B2c3.

CAT owns durable conversational Exchange/inbox/ACK facts.
PAOS owns Agent -> current Runtime activation through the generic Wake binding.

This module is intentionally Runtime/harness agnostic.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from paos_agent_activation import (
    AGENT_ACTIVATION_SCHEMA,
    AgentActivationProblem,
    activate_agent,
)


CAT_AGENT_MESSAGE_SCHEMA = "paos-agent-cat-message/v1"
CAT_EXCHANGE_ACTIVATION_SCHEMA = "paos-agent-cat-activation/v1"
DEFAULT_CAT_BASE = "http://127.0.0.1:8770"
DEFAULT_CAT_WAKE_PROMPT = "检查 CAT inbox，并从当前工位继续。"


class CatActivationProblem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def resolve_cat_base(value: str = "") -> str:
    raw = str(value or os.environ.get("CAT_BASE_URL") or DEFAULT_CAT_BASE).strip()
    raw = raw.rstrip("/")
    parsed = urllib.parse.urlsplit(raw)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise CatActivationProblem(
            "cat_base_invalid",
            "CAT base URL 必须是 http(s) origin。",
            {"cat_base": raw},
        )
    return f"{parsed.scheme}://{parsed.netloc}"


def new_cat_message_id() -> str:
    return f"catmsg-{uuid.uuid4().hex}"


def _cat_operation_id(message_id: str) -> str:
    digest = hashlib.sha256(message_id.encode("utf-8")).hexdigest()[:32]
    return f"op-paos-cat-{digest}"


def _cat_source_id(room_id: str, exchange_id: str) -> str:
    return f"{room_id}:{exchange_id}"


def _cat_exchange_summary(exchange: dict[str, Any]) -> str:
    content = " ".join(str(exchange.get("content") or "").split())
    if content:
        return content[:240]
    exchange_id = str(exchange.get("exchange_id") or "").strip()
    return f"CAT Exchange {exchange_id}" if exchange_id else "CAT Exchange"


class CatClient:
    def __init__(self, base_url: str, *, timeout: float = 8.0):
        self.base_url = resolve_cat_base(base_url)
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {}
            if not isinstance(body, dict):
                body = {}
            raise CatActivationProblem(
                str(body.get("error_code") or "cat_http_error"),
                str(body.get("error") or f"CAT HTTP {exc.code}"),
                {
                    "http_status": exc.code,
                    "path": path,
                },
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise CatActivationProblem(
                "cat_unreachable",
                f"CAT unreachable: {type(exc).__name__}: {exc}",
                {"path": path, "cat_base": self.base_url},
            ) from exc

        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CatActivationProblem(
                "cat_invalid_response",
                "CAT returned non-JSON response.",
                {"http_status": status, "path": path},
            ) from exc
        if not isinstance(body, dict):
            raise CatActivationProblem(
                "cat_invalid_response",
                "CAT returned a non-object JSON response.",
                {"http_status": status, "path": path},
            )
        if body.get("ok") is not True:
            raise CatActivationProblem(
                str(body.get("error_code") or "cat_error"),
                str(body.get("error") or "CAT request failed."),
                {"http_status": status, "path": path},
            )
        return body

    def room(self, room_id: str) -> dict[str, Any]:
        value = self.request(
            "GET",
            f"/api/rooms/{urllib.parse.quote(room_id, safe='')}",
        ).get("room")
        if not isinstance(value, dict):
            raise CatActivationProblem(
                "cat_room_invalid",
                "CAT room response missing room object.",
                {"room_id": room_id},
            )
        return value

    def exchanges(self, room_id: str) -> list[dict[str, Any]]:
        value = self.request(
            "GET",
            f"/api/rooms/{urllib.parse.quote(room_id, safe='')}/exchanges",
        ).get("exchanges")
        if not isinstance(value, list):
            raise CatActivationProblem(
                "cat_exchanges_invalid",
                "CAT exchanges response is invalid.",
                {"room_id": room_id},
            )
        return [item for item in value if isinstance(item, dict)]

    def inbox(self, room_id: str, participant_id: str) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"participant_id": participant_id})
        value = self.request(
            "GET",
            f"/api/rooms/{urllib.parse.quote(room_id, safe='')}/inbox?{query}",
        ).get("items")
        if not isinstance(value, list):
            raise CatActivationProblem(
                "cat_inbox_invalid",
                "CAT inbox response is invalid.",
                {
                    "room_id": room_id,
                    "participant_id": participant_id,
                },
            )
        return [item for item in value if isinstance(item, dict)]

    def send_exchange(
        self,
        room_id: str,
        *,
        operation_id: str,
        sender_id: str,
        target_id: str,
        content: str,
        reply_to: str = "",
        paos_refs: Iterable[Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operation_id": operation_id,
            "sender_id": sender_id,
            "target_id": target_id,
            "content": content,
            "paos_refs": list(paos_refs or []),
        }
        if reply_to:
            payload["reply_to"] = reply_to
        value = self.request(
            "POST",
            f"/api/rooms/{urllib.parse.quote(room_id, safe='')}/exchanges",
            payload,
        ).get("exchange")
        if not isinstance(value, dict):
            raise CatActivationProblem(
                "cat_exchange_invalid",
                "CAT exchange response missing exchange object.",
                {"room_id": room_id},
            )
        return value


def _validate_room(
    room: dict[str, Any],
    *,
    project_id: str,
    room_id: str,
    allow_binding_navigation: bool = False,
) -> dict[str, Any] | None:
    if str(room.get("room_id") or "") != room_id:
        raise CatActivationProblem(
            "cat_room_identity_mismatch",
            "CAT 返回的 Room identity 不匹配。",
            {"requested_room_id": room_id, "actual_room_id": room.get("room_id")},
        )
    if str(room.get("status") or "") != "open" or bool(room.get("expired")):
        raise CatActivationProblem(
            "cat_room_not_open",
            "CAT Room 当前不是可激活的 open 状态。",
            {
                "room_id": room_id,
                "status": room.get("status"),
                "expired": bool(room.get("expired")),
            },
        )
    if str(room.get("activation_owner") or "cat") != "paos":
        raise CatActivationProblem(
            "cat_activation_owner_conflict",
            "CAT Room 未把 activation ownership 交给 PAOS；拒绝创建第二条唤醒路径。",
            {
                "room_id": room_id,
                "activation_owner": room.get("activation_owner") or "cat",
            },
        )
    binding = room.get("paos_binding") or {}
    if isinstance(binding, dict) and str(binding.get("project_id") or "") == project_id:
        return None
    navigation = {
        "room_id": room_id,
        "requested_project_id": project_id,
        "bound_project_id": (
            binding.get("project_id") if isinstance(binding, dict) else None
        ),
        "navigation_only": True,
    }
    if allow_binding_navigation and isinstance(binding, dict) and navigation["bound_project_id"]:
        # 已批合同（§293）：Room Project 关联仅业务导航；跨 Project 定向
        # 消费者按精确 Home 验证（deliver 路径完成），binding 不作为阻断门。
        return navigation
    raise CatActivationProblem(
        "cat_project_binding_mismatch",
        "CAT Room 的 PAOS Project binding 与当前 Project 不一致。",
        {
            key: value
            for key, value in navigation.items()
            if key != "navigation_only"
        },
    )


def _participant_for_agent(
    room: dict[str, Any],
    *,
    agent_id: str,
) -> dict[str, Any]:
    matches = [
        item
        for item in (room.get("participants") or [])
        if isinstance(item, dict)
        and str(item.get("paos_session_id") or "") == agent_id
    ]
    if len(matches) != 1:
        raise CatActivationProblem(
            (
                "cat_agent_mapping_missing"
                if not matches
                else "cat_agent_mapping_ambiguous"
            ),
            "CAT Participant 到 stable Agent 的映射必须恰好唯一。",
            {
                "agent_id": agent_id,
                "match_count": len(matches),
            },
        )
    participant_id = str(matches[0].get("participant_id") or "").strip()
    if not participant_id:
        raise CatActivationProblem(
            "cat_participant_invalid",
            "CAT Participant 缺少 participant_id。",
            {"agent_id": agent_id},
        )
    return matches[0]


def _exchange_by_id(
    exchanges: list[dict[str, Any]],
    exchange_id: str,
) -> dict[str, Any]:
    matches = [
        item
        for item in exchanges
        if str(item.get("exchange_id") or "") == exchange_id
    ]
    if len(matches) != 1:
        raise CatActivationProblem(
            "cat_exchange_not_found",
            "CAT durable history 中无法唯一定位 Exchange。",
            {
                "exchange_id": exchange_id,
                "match_count": len(matches),
            },
        )
    return matches[0]


def verify_cat_exchange(
    *,
    client: CatClient,
    project_id: str,
    room_id: str,
    exchange_id: str,
    expected_agent_id: str = "",
    allow_binding_navigation: bool = False,
) -> dict[str, Any]:
    room = client.room(room_id)
    binding_navigation = _validate_room(
        room,
        project_id=project_id,
        room_id=room_id,
        allow_binding_navigation=allow_binding_navigation,
    )
    exchange = _exchange_by_id(
        client.exchanges(room_id),
        exchange_id,
    )
    target_participant_id = str(exchange.get("target_id") or "").strip()
    participant = next(
        (
            item
            for item in (room.get("participants") or [])
            if isinstance(item, dict)
            and str(item.get("participant_id") or "") == target_participant_id
        ),
        None,
    )
    if not isinstance(participant, dict):
        raise CatActivationProblem(
            "cat_target_participant_missing",
            "Exchange target 当前不在 CAT Room Participants 中。",
            {
                "room_id": room_id,
                "exchange_id": exchange_id,
                "target_id": target_participant_id,
            },
        )
    agent_id = str(participant.get("paos_session_id") or "").strip()
    if not agent_id:
        raise CatActivationProblem(
            "cat_target_agent_unmapped",
            "Exchange target Participant 未映射 stable PAOS Agent。",
            {
                "room_id": room_id,
                "exchange_id": exchange_id,
                "target_id": target_participant_id,
            },
        )
    if expected_agent_id and agent_id != expected_agent_id:
        raise CatActivationProblem(
            "cat_target_agent_mismatch",
            "CAT Exchange target 与请求的 stable Agent 不一致。",
            {
                "expected_agent_id": expected_agent_id,
                "actual_agent_id": agent_id,
                "exchange_id": exchange_id,
            },
        )

    acknowledged = bool(exchange.get("acknowledged"))
    inbox = client.inbox(room_id, target_participant_id)
    pending = any(
        str(item.get("exchange_id") or "") == exchange_id
        for item in inbox
    )
    if acknowledged:
        if pending:
            raise CatActivationProblem(
                "cat_exchange_state_conflict",
                "CAT Exchange 同时显示 acknowledged 与 pending。",
                {"exchange_id": exchange_id},
            )
        state = "already_consumed"
    else:
        if not pending:
            raise CatActivationProblem(
                "cat_exchange_state_unknown",
                "CAT Exchange 未 ACK，但也不在目标 Agent inbox；拒绝推断可唤醒。",
                {
                    "exchange_id": exchange_id,
                    "agent_id": agent_id,
                },
            )
        state = "pending"

    result = {
        "room_id": room_id,
        "exchange_id": exchange_id,
        "agent_id": agent_id,
        "state": state,
        "source_kind": "cat",
        "source_ref": _cat_source_id(room_id, exchange_id),
        "summary": _cat_exchange_summary(exchange),
        "source_verified": True,
        "acknowledged": acknowledged,
        "pending": pending,
    }
    if binding_navigation:
        result["project_binding"] = binding_navigation
    return result


def activate_cat_exchange(
    *,
    root: Path,
    project_id: str,
    cat_base: str,
    room_id: str,
    exchange_id: str,
    expected_agent_id: str = "",
    wake_prompt: str = DEFAULT_CAT_WAKE_PROMPT,
) -> dict[str, Any]:
    client = CatClient(cat_base)
    verified = verify_cat_exchange(
        client=client,
        project_id=project_id,
        room_id=room_id,
        exchange_id=exchange_id,
        expected_agent_id=expected_agent_id,
    )
    source_id = _cat_source_id(room_id, exchange_id)
    if verified["state"] == "already_consumed":
        return {
            "schema": CAT_EXCHANGE_ACTIVATION_SCHEMA,
            "project_id": project_id,
            "agent_id": verified["agent_id"],
            "source_kind": "cat",
            "source_id": source_id,
            "room_id": room_id,
            "exchange_id": exchange_id,
            "source_verified": True,
            "wake_requested": False,
            "state": "already_consumed",
            "replayed": True,
            "detail": "CAT Exchange 已 ACK；无需再次激活 Agent。",
        }

    try:
        activation = activate_agent(
            root=Path(root),
            project_id=project_id,
            agent_id=verified["agent_id"],
            source_kind="cat",
            source_id=source_id,
            wake_prompt=wake_prompt,
            source_verified=True,
        )
    except AgentActivationProblem as problem:
        raise CatActivationProblem(
            problem.code,
            str(problem),
            problem.details,
        ) from problem

    return {
        "schema": CAT_EXCHANGE_ACTIVATION_SCHEMA,
        "project_id": project_id,
        "agent_id": verified["agent_id"],
        "source_kind": "cat",
        "source_id": source_id,
        "room_id": room_id,
        "exchange_id": exchange_id,
        "source_verified": True,
        "wake_requested": bool(activation.get("wake_requested")),
        "state": activation.get("state"),
        "replayed": bool(activation.get("replayed")),
        "detail": activation.get("detail", ""),
        "activation": activation,
    }


def persist_cat_agent_message(
    *,
    project_id: str,
    cat_base: str,
    room_id: str,
    target_agent_id: str,
    content: str,
    sender_agent_id: str = "",
    message_id: str = "",
    reply_to: str = "",
    paos_refs: Iterable[Any] | None = None,
    allow_binding_navigation: bool = False,
) -> dict[str, Any]:
    """Persist and verify one CAT Exchange without performing Runtime activation."""
    project_id = str(project_id or "").strip()
    target_agent_id = str(target_agent_id or "").strip()
    sender_agent_id = str(sender_agent_id or "").strip()
    content = str(content or "")
    if not project_id or not target_agent_id or not room_id:
        raise CatActivationProblem(
            "cat_agent_message_invalid",
            "project_id / room_id / target Agent 均不能为空。",
        )
    if not content.strip():
        raise CatActivationProblem(
            "cat_agent_message_empty",
            "CAT Agent message 不能为空。",
        )

    client = CatClient(cat_base)
    room = client.room(room_id)
    _validate_room(
        room,
        project_id=project_id,
        room_id=room_id,
        allow_binding_navigation=allow_binding_navigation,
    )
    target = _participant_for_agent(
        room,
        agent_id=target_agent_id,
    )
    target_participant_id = str(target["participant_id"])

    if sender_agent_id:
        sender = _participant_for_agent(
            room,
            agent_id=sender_agent_id,
        )
        sender_participant_id = str(sender["participant_id"])
    else:
        sender_participant_id = "human"

    if sender_participant_id == target_participant_id:
        raise CatActivationProblem(
            "cat_sender_target_same_agent",
            "CAT sender 与 target 不能是同一个 stable Agent。",
            {"agent_id": target_agent_id},
        )

    effective_message_id = str(message_id or "").strip() or new_cat_message_id()
    operation_id = _cat_operation_id(effective_message_id)
    exchange = client.send_exchange(
        room_id,
        operation_id=operation_id,
        sender_id=sender_participant_id,
        target_id=target_participant_id,
        content=content,
        reply_to=str(reply_to or "").strip(),
        paos_refs=paos_refs,
    )
    exchange_id = str(exchange.get("exchange_id") or "").strip()
    if not exchange_id:
        raise CatActivationProblem(
            "cat_exchange_invalid",
            "CAT send succeeded without exchange_id.",
            {"room_id": room_id, "message_id": effective_message_id},
        )

    verified = verify_cat_exchange(
        client=client,
        project_id=project_id,
        room_id=room_id,
        exchange_id=exchange_id,
        expected_agent_id=target_agent_id,
        allow_binding_navigation=allow_binding_navigation,
    )
    return {
        "schema": "paos-cat-agent-message-source/v1",
        "project_id": project_id,
        "message_id": effective_message_id,
        "room_id": room_id,
        "exchange_id": exchange_id,
        "target_agent_id": target_agent_id,
        "sender_agent_id": sender_agent_id or "human",
        "durable_exchange_created": True,
        "source_kind": "cat",
        "source_ref": verified["source_ref"],
        "summary": verified["summary"],
        "transport_state": verified["state"],
        "acknowledged": verified["acknowledged"],
        "source_verified": True,
        "cat_base": client.base_url,
        **(
            {"project_binding": verified["project_binding"]}
            if verified.get("project_binding")
            else {}
        ),
        "meta": {
            "runtime_wake_performed": False,
            "cat_activation_owner_required": "paos",
            "retry_safe_with_same_message_id": True,
        },
    }


def verify_cat_exchange_source(
    *,
    project_id: str,
    cat_base: str,
    room_id: str,
    exchange_id: str,
    expected_agent_id: str = "",
    allow_binding_navigation: bool = False,
) -> dict[str, Any]:
    """Verify one durable CAT Exchange without performing Runtime activation."""
    client = CatClient(cat_base)
    return {
        "cat_base": client.base_url,
        **verify_cat_exchange(
            client=client,
            project_id=project_id,
            room_id=room_id,
            exchange_id=exchange_id,
            expected_agent_id=expected_agent_id,
            allow_binding_navigation=allow_binding_navigation,
        ),
    }


def send_cat_agent_message(
    *,
    root: Path,
    project_id: str,
    cat_base: str,
    room_id: str,
    target_agent_id: str,
    content: str,
    sender_agent_id: str = "",
    message_id: str = "",
    reply_to: str = "",
    paos_refs: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Legacy-compatible CAT send: persist first, then perform direct activation."""
    root = Path(root)
    persisted = persist_cat_agent_message(
        project_id=project_id,
        cat_base=cat_base,
        room_id=room_id,
        target_agent_id=target_agent_id,
        content=content,
        sender_agent_id=sender_agent_id,
        message_id=message_id,
        reply_to=reply_to,
        paos_refs=paos_refs,
    )
    activation = activate_cat_exchange(
        root=root,
        project_id=project_id,
        cat_base=str(persisted["cat_base"]),
        room_id=room_id,
        exchange_id=str(persisted["exchange_id"]),
        expected_agent_id=target_agent_id,
    )
    return {
        "schema": CAT_AGENT_MESSAGE_SCHEMA,
        "project_id": project_id,
        "message_id": persisted["message_id"],
        "room_id": room_id,
        "exchange_id": persisted["exchange_id"],
        "target_agent_id": target_agent_id,
        "sender_agent_id": sender_agent_id or "human",
        "durable_exchange_created": True,
        "activation": activation,
        "meta": {
            "agent_first": True,
            "runtime_harness_hidden": True,
            "cat_activation_owner_required": "paos",
            "two_phase_not_atomic": True,
            "retry_safe_with_same_message_id": True,
        },
    }
