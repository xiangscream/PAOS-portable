"""Agent-first activation orchestration for PAOS V1.1 B2c.

Callers target stable PAOS Agent identities. Runtime / harness details stay
behind the existing Wake binding and Wake driver contract.

B2c does not create another truth source. Durable source facts remain in
Workstation Mail / CAT, and Runtime delivery facts remain in Wake attempts.
This module only verifies source delivery, derives stable per-Agent Wake
attempt identities, and invokes the Wake controller.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from paos_mail import MailProblem, dispatch_status, send_mail
from paos_contact import load_native_targets
from paos_wakeup import DEFAULT_WAKE_PROMPT
from runtime_injection import InjectionError, inject as native_inject


AGENT_ACTIVATION_SCHEMA = "paos-agent-activation/v1"
AGENT_ACTIVATION_BATCH_SCHEMA = "paos-agent-activation-batch/v1"
AGENT_MESSAGE_SCHEMA = "paos-agent-message/v1"
SUPPORTED_SOURCE_KINDS = {"mail", "cat", "system"}


class AgentActivationProblem(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _clean_id(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AgentActivationProblem(
            "agent_activation_id_missing",
            f"{label} 不能为空。",
            {"label": label},
        )
    return text


def stable_activation_attempt_id(
    *,
    project_id: str,
    agent_id: str,
    source_kind: str,
    source_id: str,
) -> str:
    """Derive one stable Wake attempt identity for one Agent + source fact.

    Harness/runtime/binding is intentionally absent. If an activation was
    already attempted under an older binding, a later binding mismatch fails
    closed in B2a rather than silently producing a second model turn.
    """
    project_id = _clean_id(project_id, "project_id")
    agent_id = _clean_id(agent_id, "agent_id")
    source_kind = _clean_id(source_kind, "source_kind")
    source_id = _clean_id(source_id, "source_id")
    if source_kind not in SUPPORTED_SOURCE_KINDS:
        raise AgentActivationProblem(
            "agent_activation_source_kind_invalid",
            "不支持的 Agent activation source kind。",
            {"source_kind": source_kind},
        )
    digest = hashlib.sha256(
        "\0".join(
            [project_id, agent_id, source_kind, source_id]
        ).encode("utf-8")
    ).hexdigest()[:32]
    return f"agent-{source_kind}-{digest}"


def activate_agent(
    *,
    root: Path,
    project_id: str,
    agent_id: str,
    source_kind: str,
    source_id: str,
    wake_prompt: str = DEFAULT_WAKE_PROMPT,
    attempt_id: str = "",
    source_verified: bool = False,
) -> dict[str, Any]:
    """Request continuation for one stable Agent identity.

    This surface intentionally does not expose runtime_id, native session id,
    driver name, or harness-specific details.
    """
    root = Path(root)
    project_id = _clean_id(project_id, "project_id")
    agent_id = _clean_id(agent_id, "agent_id")
    source_kind = _clean_id(source_kind, "source_kind")
    source_id = _clean_id(source_id, "source_id")
    if source_kind not in SUPPORTED_SOURCE_KINDS:
        raise AgentActivationProblem(
            "agent_activation_source_kind_invalid",
            "不支持的 Agent activation source kind。",
            {"source_kind": source_kind},
        )
    if source_kind in {"mail", "cat"} and not source_verified:
        raise AgentActivationProblem(
            "agent_activation_source_unverified",
            "Durable communication source 尚未验证；拒绝先唤醒后补事实。",
            {
                "source_kind": source_kind,
                "source_id": source_id,
                "agent_id": agent_id,
            },
        )

    targets = load_native_targets(root)
    target = (targets or {}).get(agent_id) if isinstance(targets, dict) else None
    if not isinstance(target, dict) or not str(target.get("session_id") or "").strip():
        return {
            "schema": AGENT_ACTIVATION_SCHEMA,
            "project_id": project_id,
            "agent_id": agent_id,
            "source_kind": source_kind,
            "source_id": source_id,
            "source_verified": bool(source_verified),
            "target_configured": False,
            "wake_requested": False,
            "state": "native_target_not_configured",
            "replayed": False,
            "detail": "Agent 未配置 Contact native target；durable source 已保留，将由本人读取或用独立注入工具显式提醒。",
        }
    if str(target.get("project_id") or "") not in {"", project_id}:
        # Project 归属不匹配必须在读面可见：不冒称本地 target 属该项目。
        return {
            "schema": AGENT_ACTIVATION_SCHEMA,
            "project_id": project_id,
            "agent_id": agent_id,
            "source_kind": source_kind,
            "source_id": source_id,
            "source_verified": bool(source_verified),
            "target_configured": True,
            "wake_requested": False,
            "state": "native_target_project_mismatch",
            "replayed": False,
            "detail": "Contact native target 属其他 Project；拒绝跨 Project 注入。",
        }

    try:
        result = native_inject(target=target, message=str(wake_prompt or DEFAULT_WAKE_PROMPT))
    except (InjectionError, ValueError) as problem:
        return {
            "schema": AGENT_ACTIVATION_SCHEMA,
            "project_id": project_id,
            "agent_id": agent_id,
            "source_kind": source_kind,
            "source_id": source_id,
            "source_verified": bool(source_verified),
            "target_configured": True,
            "wake_requested": False,
            "state": "native_rejected",
            "replayed": False,
            "error": str(problem),
            "error_type": type(problem).__name__,
            "detail": "原生注入被拒绝或不可达；durable source 仍在工位。",
        }

    return {
        "schema": AGENT_ACTIVATION_SCHEMA,
        "project_id": project_id,
        "agent_id": agent_id,
        "source_kind": source_kind,
        "source_id": source_id,
        "source_verified": bool(source_verified),
        "target_configured": True,
        "wake_requested": True,
        "state": "native_accepted",
        "replayed": False,
        "receipt": result,
    }

def _selected_frozen_recipients(
    *,
    frozen_recipients: list[str],
    requested_agents: Iterable[str] | None,
) -> list[str]:
    requested = []
    for value in requested_agents or []:
        agent_id = str(value or "").strip()
        if agent_id and agent_id not in requested:
            requested.append(agent_id)
    if not requested:
        return list(frozen_recipients)

    unknown = [
        agent_id
        for agent_id in requested
        if agent_id not in frozen_recipients
    ]
    if unknown:
        raise AgentActivationProblem(
            "agent_activation_recipient_not_in_source",
            "指定 Agent 不属于该 durable source 的冻结 recipient 集合。",
            {
                "unknown_agents": unknown,
                "frozen_recipients": frozen_recipients,
            },
        )

    # Preserve the source's frozen ordering rather than caller ordering.
    requested_set = set(requested)
    return [
        agent_id
        for agent_id in frozen_recipients
        if agent_id in requested_set
    ]


def send_agent_mail(
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
) -> dict[str, Any]:
    """Persist durable Workstation Mail first, then activate its Agents.

    This is the normal Agent-first collaboration path. The operation is
    intentionally two-phase rather than pretending Mail filesystem state and
    Runtime Wake side effects are atomic. Retrying the same message_id is safe:
    B1 reuses the dispatch and B2c reuses stable per-Agent Wake attempt ids.
    """
    root = Path(root)
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
        )
    except MailProblem as problem:
        raise AgentActivationProblem(
            problem.code,
            str(problem),
            problem.details,
        ) from problem

    project_id = _clean_id(project.get("id"), "project_id")
    activation = activate_mail_dispatch(
        root=root,
        project_id=project_id,
        message_id=str(persisted["message_id"]),
    )
    return {
        "schema": AGENT_MESSAGE_SCHEMA,
        "project_id": project_id,
        "message_id": persisted["message_id"],
        "mail": persisted,
        "activation": activation,
        "meta": {
            "durable_source_persisted_before_activation": True,
            "two_phase_not_atomic": True,
            "retry_safe_with_same_message_id": True,
            "agent_first": True,
            "runtime_harness_hidden": True,
        },
    }


def activate_mail_dispatch(
    *,
    root: Path,
    project_id: str,
    message_id: str,
    agents: Iterable[str] | None = None,
    wake_prompt: str = "检查 Workstation mailbox，并从当前工位继续。",
) -> dict[str, Any]:
    """Activate frozen recipients of one already-persisted Workstation Mail.

    Mail delivery is verified first. A recipient is never woken when its
    immutable mailbox copy is missing, unreadable or conflicted.
    """
    root = Path(root)
    project_id = _clean_id(project_id, "project_id")
    message_id = _clean_id(message_id, "message_id")

    try:
        mail = dispatch_status(root, message_id)
    except MailProblem as problem:
        raise AgentActivationProblem(
            problem.code,
            str(problem),
            problem.details,
        ) from problem

    source_project = str(mail.get("project_id") or "")
    if source_project != project_id:
        raise AgentActivationProblem(
            "agent_activation_source_project_mismatch",
            "Workstation Mail dispatch 不属于当前 Project。",
            {
                "requested_project_id": project_id,
                "source_project_id": source_project,
                "message_id": message_id,
            },
        )

    frozen_recipients = [
        str(value)
        for value in (mail.get("recipients") or [])
        if str(value or "").strip()
    ]
    selected = _selected_frozen_recipients(
        frozen_recipients=frozen_recipients,
        requested_agents=agents,
    )
    delivery_by_agent = {
        str(item.get("recipient_agent_id") or ""): str(
            item.get("state") or "unknown"
        )
        for item in (mail.get("deliveries") or [])
        if isinstance(item, dict)
    }

    activations: list[dict[str, Any]] = []
    for agent_id in selected:
        delivery_state = delivery_by_agent.get(agent_id, "missing")
        if delivery_state != "delivered":
            activations.append(
                {
                    "schema": AGENT_ACTIVATION_SCHEMA,
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "source_kind": "mail",
                    "source_id": message_id,
                    "attempt_id": stable_activation_attempt_id(
                        project_id=project_id,
                        agent_id=agent_id,
                        source_kind="mail",
                        source_id=message_id,
                    ),
                    "source_verified": False,
                    "mail_delivery_state": delivery_state,
                    "binding_present": None,
                    "wake_requested": False,
                    "state": "blocked_source_not_delivered",
                    "replayed": False,
                    "detail": (
                        "Durable Workstation Mail 尚未完整交付给该 Agent；"
                        "拒绝先唤醒后补消息。"
                    ),
                }
            )
            continue

        item = activate_agent(
            root=root,
            project_id=project_id,
            agent_id=agent_id,
            source_kind="mail",
            source_id=message_id,
            wake_prompt=wake_prompt,
            source_verified=True,
        )
        item["mail_delivery_state"] = delivery_state
        activations.append(item)

    counts: dict[str, int] = {}
    for item in activations:
        state = str(item.get("state") or "unknown")
        counts[state] = counts.get(state, 0) + 1

    return {
        "schema": AGENT_ACTIVATION_BATCH_SCHEMA,
        "project_id": project_id,
        "source_kind": "mail",
        "source_id": message_id,
        "audience": mail.get("audience"),
        "frozen_recipients": frozen_recipients,
        "selected_agents": selected,
        "mail_delivery": {
            "schema": mail.get("schema"),
            "subject": mail.get("subject"),
            "deliveries": mail.get("deliveries") or [],
        },
        "activations": activations,
        "counts": counts,
        "meta": {
            "agent_first": True,
            "runtime_harness_hidden": True,
            "new_orchestration_truth_source": False,
            "mail_delivery_and_wake_state_remain_separate": True,
        },
    }
