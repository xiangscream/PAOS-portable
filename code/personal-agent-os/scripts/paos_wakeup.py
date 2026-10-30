"""Workless Runtime contact surface（小薄面）。

旧的 Wake 驱动编排、attempt 状态机、重试轮询全部退役；本文件只承接：
- Contact native-target 配置（runtime/base_url/session_id/stop_file/…）的读写；
- `trigger_wake` 走独立原生注入工具（`runtime_injection.inject`）；
- `probe/recover/stop/test` 保留名字做显式退役响应，不再驱动业务状态。

历史 attempt/uncertain/binding 原件在磁盘保留，可读但不参与当前运行判断。
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

from paos_contact import load_native_targets, save_native_targets
from runtime_injection import InjectionError, inject as native_inject


WAKE_BINDING_SCHEMA = "paos-wake-binding/v1"
WAKE_STATUS_SCHEMA = "paos-wake-status/v1"
WAKE_ACTION_SCHEMA = "paos-wake-action/v1"
WAKE_SOURCE_KINDS = {"mail", "cat", "manual", "system"}
DEFAULT_WAKE_PROMPT = "检查 Workstation mailbox 或 CAT，并从当前工位继续。"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,159}$")


class WakeProblem(RuntimeError):
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


def _validate_id(value: str, *, label: str) -> str:
    cleaned = str(value or "").strip()
    if not _ID_RE.match(cleaned):
        raise WakeProblem(
            "wake_id_invalid",
            f"{label} 不符 {{committer-id}} 约定：{value!r}",
            {"value": value},
        )
    return cleaned


def native_target(root: Path, agent_id: str) -> dict[str, Any] | None:
    targets = load_native_targets(root)
    value = (targets or {}).get(_validate_id(agent_id, label="agent_id"))
    return value if isinstance(value, dict) else None


def load_binding(root: Path, agent_id: str, *, required: bool = True) -> dict[str, Any] | None:
    target = native_target(root, agent_id)
    if target is None:
        if required:
            raise WakeProblem(
                "wake_binding_missing",
                f"Agent 未配置 Contact 原生 target：{agent_id}",
                {"agent_id": agent_id},
            )
        return None
    record = {
        "schema": WAKE_BINDING_SCHEMA,
        "project_id": str(target.get("project_id") or "") or None,
        "agent_id": _validate_id(agent_id, label="agent_id"),
        "runtime_id": str(target.get("runtime_id") or "") or None,
        "native_session_id": str(target.get("session_id") or "").strip() or None,
        "driver": str(target.get("runtime") or "") or None,
        "driver_config": dict(target.get("target_details") or {}),
    }
    record["binding_fingerprint"] = _binding_fingerprint(record)
    return record


def _binding_fingerprint(candidate: dict[str, Any]) -> str:
    import hashlib

    payload = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bind_wakeup(
    *,
    root: Path,
    project_id: str | None,
    agent_id: str,
    runtime_id: str,
    native_session_id: str,
    driver_name: str,
    driver_config: dict[str, Any] | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Store the Contact native target entry (Contact 是唯一 target 事实源）。"""
    root = Path(root)
    if not root.is_dir():
        raise WakeProblem(
            "wake_project_root_missing",
            f"Project root 不存在：{root}",
            {"root_path": str(root)},
        )
    if project_id is not None:
        project_id = _validate_id(project_id, label="project_id")
    agent_id = _validate_id(agent_id, label="agent_id")
    native_session_id = str(native_session_id or "").strip()
    if not native_session_id:
        raise WakeProblem(
            "wake_native_session_missing",
            "bind 缺少 --native-session-id。",
            {"agent_id": agent_id},
        )
    target = dict(driver_config or {})
    target["runtime"] = str(driver_name or "").strip() or "unknown"
    target["session_id"] = native_session_id
    if project_id is not None:
        target.setdefault("project_id", project_id)
    if runtime_id:
        target.setdefault("runtime_id", runtime_id)
    targets = load_native_targets(root) or {}
    if target["runtime"] == "codex":
        previous = targets.get(agent_id) or {}
        extension = dict(previous.get("extension") or {}) if previous.get("session_id") == native_session_id else {}
        extension.update(target.get("extension") or {})
        default_home = Path.home() / ".paos/runtime-injection/codex-self" / agent_id
        if os.name == "nt":
            extension.setdefault("receiver_runtime_file", str(default_home / "runtime.json"))
            extension.setdefault("windows_python", sys.executable)
        if not all(isinstance(extension.get(key), str) and extension[key].strip()
                   for key in ("receiver_runtime_file", "windows_python")):
            raise WakeProblem("wake_codex_receiver_config_required",
                              "从正常Windows入口登记，或提供Windows receiver_runtime_file和windows_python；未保存不完整Contact。")
        if not all(PureWindowsPath(extension[key]).is_absolute()
                   for key in ("receiver_runtime_file", "windows_python")) or not extension["windows_python"].lower().endswith(".exe"):
            raise WakeProblem("wake_codex_receiver_config_invalid", "接收器和Python必须为绝对Windows路径，Python需为.exe；未保存Contact。")
        extension.setdefault("execution_environment", "windows")
        target["extension"] = extension
        target.setdefault("stop_file", previous.get("stop_file") or str(PureWindowsPath(extension["receiver_runtime_file"]).parent / "STOP"))
    targets[agent_id] = target
    store = save_native_targets(root, targets)
    return {
        "schema": WAKE_ACTION_SCHEMA,
        "action": "bind",
        "status": "stored",
        "agent_id": agent_id,
        "target": target,
        "store": str(store),
    }


def wake_status(root: Path, agent_id: str) -> dict[str, Any]:
    root = Path(root)
    agent_id = _validate_id(agent_id, label="agent_id")
    target = native_target(root, agent_id)
    if target is None:
        return {
            "schema": WAKE_STATUS_SCHEMA,
            "agent_id": agent_id,
            "configured": False,
            "target_status": "unconfigured",
            "reachability": "unbound",
        }
    stop_file = str(target.get("stop_file") or "")
    return {
        "schema": WAKE_STATUS_SCHEMA,
        "agent_id": agent_id,
        "configured": True,
        "target_status": "configured",
        "runtime": str(target.get("runtime") or "") or None,
        "native_session_id": str(target.get("session_id") or "").strip() or None,
        "base_url": str(target.get("base_url") or "") or None,
        "stop_present": bool(stop_file and Path(stop_file).exists()),
        "reachability": "unknown",
        "activation": None,
        "native_turn": {"state": "not_observed"},
    }


def probe_wakeup(root: Path, agent_id: str) -> dict[str, Any]:
    """探测退役：不发测试请求，也不自动启动 Harness。"""
    root = Path(root)
    agent_id = _validate_id(agent_id, label="agent_id")
    return {
        "schema": WAKE_ACTION_SCHEMA,
        "action": "probe",
        "at": utc_now_iso(),
        "state": "retired",
        "result": {"state": "unknown", "note": "探测退役：状态保持 unknown（不自动启动 Harness）。"},
    }


def trigger_wake(
    *,
    root: Path,
    agent_id: str,
    wake_prompt: str = "检查 Workstation mailbox 或 CAT，并从当前工位继续。",
    source_kind: str = "manual",
    attempt_id: str = "",
) -> dict[str, Any]:
    """一次原生注入：只受 configured target 与明确 STOP 影响；失败如实暴露。"""
    root = Path(root)
    agent_id = _validate_id(agent_id, label="agent_id")
    if str(source_kind or "").strip() not in WAKE_SOURCE_KINDS:
        raise WakeProblem(
            "wake_source_kind_invalid",
            f"不支持的 source kind：{source_kind}",
            {"source_kind": source_kind},
        )
    target = native_target(root, agent_id)
    if target is None:
        raise WakeProblem(
            "wake_binding_missing",
            f"Agent 未配置 Contact 原生 target：{agent_id}",
            {"agent_id": agent_id},
        )
    if str(source_kind or "").strip() in {"manual", "system"} and not str(attempt_id or "").strip():
        stable_key = new_attempt_id()
        try:
            result = native_inject(target=target, message=str(wake_prompt or DEFAULT_WAKE_PROMPT), model=None)
        except (InjectionError, ValueError) as exc:
            raise WakeProblem(
                "wake_native_rejected",
                f"原生注入被拒绝：{exc}",
                {"agent_id": agent_id, "error_type": type(exc).__name__},
            ) from exc
        return {"schema": WAKE_ACTION_SCHEMA, "action": "trigger", "at": utc_now_iso(), "attempt_id": stable_key, "state": "native_accepted", "receipt": result}
    raise WakeProblem("wake_source_kind_irrelevant", f"不支持的 source kind：{source_kind}", {"source_kind": source_kind})


def new_attempt_id() -> str:
    import uuid

    return uuid.uuid4().hex


def recover_wakeup(root: Path, agent_id: str) -> dict[str, Any]:
    """恢复退役：不重放旧 uncertain/timeout attempt；如需提醒，请用一次显式 trigger。"""
    root = Path(root)
    agent_id = _validate_id(agent_id, label="agent_id")
    return {
        "schema": WAKE_ACTION_SCHEMA,
        "action": "recover",
        "at": utc_now_iso(),
        "state": "retired",
        "result": {"state": "unknown", "note": "恢复重试退役；如需提醒请走独立注入工具."},
    }


def stop_wakeup(root: Path, agent_id: str) -> dict[str, Any]:
    """停止提醒注入：只写 Contact 配置里登记的 stop_file 标记（若未配置则为 no-op）。"""
    root = Path(root)
    agent_id = _validate_id(agent_id, label="agent_id")
    target = native_target(root, agent_id)
    stop_file = str((target or {}).get("stop_file") or "").strip()
    if not stop_file:
        return {
            "schema": WAKE_ACTION_SCHEMA,
            "action": "stop",
            "at": utc_now_iso(),
            "state": "no_stop_file",
            "result": {"state": "no_stop_file", "agent_id": agent_id},
        }
    stop_path = Path(stop_file)
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text("PAOS explicit stop marker\n", encoding="utf-8")
    return {
        "schema": WAKE_ACTION_SCHEMA,
        "action": "stop",
        "at": utc_now_iso(),
        "state": "stopped",
        "result": {"state": "stopped", "agent_id": agent_id, "stop_file": str(stop_path)},
    }


def unbind_wakeup(root: Path, agent_id: str, *, force: bool = False) -> dict[str, Any]:
    """移除 Contact native-target 配置项（对历史 binding 文件不动）。"""
    root = Path(root)
    agent_id = _validate_id(agent_id, label="agent_id")
    targets = load_native_targets(root) or {}
    if agent_id not in targets:
        return {
            "schema": WAKE_ACTION_SCHEMA,
            "action": "unbind",
            "at": utc_now_iso(),
            "status": "not_configured",
            "result": {"state": "not_configured", "agent_id": agent_id},
        }
    targets.pop(agent_id, None)
    store = save_native_targets(root, targets)
    return {
        "schema": WAKE_ACTION_SCHEMA,
        "action": "unbind",
        "at": utc_now_iso(),
        "status": "cleared",
        "result": {"state": "cleared", "agent_id": agent_id, "store": str(store)},
    }


def test_wakeup(root: Path, agent_id: str) -> dict[str, Any]:
    """试唤醒退役：不额外发模型测试请求。"""
    root = Path(root)
    agent_id = _validate_id(agent_id, label="agent_id")
    return {
        "schema": WAKE_ACTION_SCHEMA,
        "action": "test",
        "at": utc_now_iso(),
        "state": "retired",
        "result": {"state": "unknown", "note": "试唤醒退役；不额外发模型测试请求。"},
    }
