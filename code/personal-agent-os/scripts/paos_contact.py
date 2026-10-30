"""Team contact surface: build one read view over live PAOS, workstation TODOs
and Runtime Wake bindings. Reads only; missing data stays unknown."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from paos_workstation import (
    WorkstationProblem,
    posix_windows_drive_locator,
    read_fixed_workstation,
)

from paos_home import project_agent_home

CONTACT_SCHEMA = "paos-contact/v2"

TODO_FIELD_LABELS = ("work", "goal", "stage", "next", "waiting", "result", "wip")
TODO_LABEL_PREFIXES = {
    "work": "Work：",
    "goal": "目标：",
    "stage": "阶段：",
    "next": "下一步：",
    "waiting": "等待：",
    "result": "成果：",
    "wip": "在途：",
}
TODO_ANNOTATED_LABEL = re.compile(
    r"^(Work|目标|阶段|下一步|等待|成果|在途)（[^）]*）：(?P<value>.*)$"
)
TODO_SUB_HEADING = re.compile(r"^###\s*(?P<title>.+?)\s*$")
_H2_HEADING = re.compile(r"^## (?!#)")


def _current_section(text: str) -> str:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "## 当前":
            start = index + 1
            break
    if start is None:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        if _H2_HEADING.match(line):
            break
        collected.append(line)
    return "\n".join(collected)


def _parse_current_section(section: str, info: dict[str, Any]) -> None:
    fields: dict[str, str] = {}
    annotations: dict[str, list[str]] = {}
    facts: dict[str, list[str]] = {}
    pending_key: str | None = None
    pending_value: list[str] = []
    current_fact: str | None = None

    def flush_pending() -> None:
        nonlocal pending_key, pending_value
        if pending_key is not None:
            if pending_value:
                value = " ".join(part.strip() for part in pending_value if part.strip())
                existing = fields.get(pending_key) or ""
                fields[pending_key] = f"{existing} {value}".strip()
            pending_key = None
            pending_value = []

    def flush_fact() -> None:
        nonlocal current_fact
        current_fact = None

    for raw in section.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        sub = TODO_SUB_HEADING.match(raw)
        if sub:
            flush_pending()
            flush_fact()
            current_fact = sub.group("title")
            facts.setdefault(current_fact, [])
            continue
        annotated = TODO_ANNOTATED_LABEL.match(raw)
        if annotated:
            flush_pending()
            flush_fact()
            label = annotated.group(1)
            key = {"Work": "work", "目标": "goal", "阶段": "stage", "下一步": "next", "等待": "waiting", "成果": "result", "在途": "wip"}[label]
            value = annotated.group("value")
            parenthetical = raw[len(label) : len(raw) - len(value)].rstrip()
            annotations.setdefault(key, []).append(parenthetical)
            if fields.get(key):
                fields[key] += f" ；{value.strip()}"
            else:
                fields[key] = value.strip()
            continue
        matched = False
        for key, prefix in TODO_LABEL_PREFIXES.items():
            if raw.startswith(prefix):
                flush_pending()
                flush_fact()
                pending_key = key
                pending_value = [raw[len(prefix):]]
                matched = True
                break
        if matched:
            continue
        if raw.startswith("- "):
            if current_fact is not None:
                facts[current_fact].append(raw[2:].strip())
            elif pending_key is not None:
                pending_value.append(raw[2:])
            else:
                info.setdefault("extra_lines", []).append(raw[2:].strip())
            continue
        if current_fact is not None:
            facts[current_fact].append(stripped)
        else:
            info.setdefault("extra_lines", []).append(stripped)
    flush_pending()

    if facts:
        info["facts"] = {title: entries for title, entries in facts.items()}
    if annotations:
        info["annotations"] = annotations
    for key in TODO_FIELD_LABELS:
        fields.setdefault(key, "")
    info["current_section"] = fields


def read_team_todo(root: Path, agent_id: str, *, project_id: str | None = None) -> dict[str, Any]:
    """Read one Agent's workstation TODO through the trusted v2 contract.

    Trust gate (already-existing reader contract): frontmatter schema/identity,
    duplicate-current and section checks from `paos_workstation`; missing or
    corrupted facts render the todo unavailable with the exact reason, never
    silently. The annotations/facts/extra preservation stays as value-level
    enrichment over the same trusted file.
    """
    path = root / "Workstations" / agent_id / "TODO.md"
    info: dict[str, Any] = {"available": False, "path": str(path)}
    try:
        view = read_fixed_workstation(root, agent_id, tolerate_todo_errors=True)
    except WorkstationProblem as problem:
        info["reason"] = problem.code
        return info
    if not view.get("entry_exists"):
        info["reason"] = "workstation_entry_missing"
        return info
    todo_error = view.get("todo_error")
    if todo_error:
        info["reason"] = todo_error.get("code") or "todo_error"
        return info
    todo = view.get("todo") if isinstance(view.get("todo"), dict) else {}
    trust_issues: list[str] = []
    schema = str(todo.get("schema") or "")

    if schema == "paos-todo/v3":
        if todo.get("home_kind") != "project_agent":
            trust_issues.append(f"home_kind:{todo.get('home_kind') or 'missing'}")
        if project_id is not None and str(todo.get("project_id") or "") != str(project_id):
            trust_issues.append(f"project_id:{todo.get('project_id')}")
        if str(todo.get("home_id") or "") != str(agent_id):
            trust_issues.append(f"home_id:{todo.get('home_id') or 'missing'}")
        current = todo.get("current") if isinstance(todo.get("current"), dict) else {}
        if not str(current.get("objective") or "").strip():
            trust_issues.append("current:objective_missing")
        if not str(current.get("next_action") or "").strip():
            trust_issues.append("current:next_action_missing")
        if trust_issues:
            info["reason"] = "todo_untrusted"
            info["trust_issues"] = trust_issues
            return info
        info["current_section"] = {
            "goal": str(current.get("objective") or ""),
            "stage": str(current.get("stage") or ""),
            "next": str(current.get("next_action") or ""),
            "waiting": str(current.get("waiting") or ""),
            "result": str(current.get("results") or ""),
            "wip": str(current.get("inflight") or ""),
        }
        refs = [
            str(value)
            for value in (current.get("context_refs") or [])
            if str(value or "").strip()
        ]
        if refs:
            info["facts"] = {"Context refs": refs}
        info["available"] = True
        info["trusted"] = True
        info["todo_summary"] = {
            "stage": str(current.get("stage") or ""),
            "next": str(current.get("next_action") or ""),
        }
        info["counts"] = todo.get("counts") or {}
        return info

    if schema != "paos-todo/v2":
        trust_issues.append(f"schema:{schema or 'missing'}")
    if todo.get("project_id") and project_id is not None and str(todo.get("project_id")) != str(project_id):
        trust_issues.append(f"project_id:{todo.get('project_id')}")
    if todo.get("agent_id") and str(todo.get("agent_id")) != str(agent_id):
        trust_issues.append(f"agent_id:{todo.get('agent_id')}")
    if todo.get("duplicate_sections"):
        trust_issues.append("duplicate_sections:" + ",".join(todo["duplicate_sections"]))
    if todo.get("metadata_issues"):
        trust_issues.extend(f"front_matter:{item}" for item in todo["metadata_issues"])
    if todo.get("missing_sections"):
        trust_issues.append("missing_sections:" + ",".join(todo["missing_sections"]))
    if not trust_issues and not todo.get("agent_id"):
        trust_issues.append("agent_id_missing")
    if trust_issues:
        info["reason"] = "todo_untrusted"
        info["trust_issues"] = trust_issues
        return info
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        info["reason"] = f"todo_unreadable:{type(exc).__name__}"
        return info
    section = _current_section(text)
    if not section.strip():
        info["reason"] = "current_section_missing"
        return info
    _parse_current_section(section, info)
    info["available"] = True
    info["trusted"] = True
    info["todo_summary"] = todo.get("summary") or {}
    info["counts"] = todo.get("counts") or {}
    return info


def derive_attach(target: dict[str, Any]) -> dict[str, Any]:
    """Derive one copyable attach command from the current Contact native-target.

    Accepts both shapes: new (runtime/session_id/base_url/… 与 target_details)
    与 legacy (driver/native_session_id/driver_config)。只使用 target 内的事实；
    host wrappers（如 wsl --exec）不在 exact command 内，如实标注。
    """
    driver = str(target.get("driver") or target.get("runtime") or "")
    native_session_id = str(target.get("native_session_id") or target.get("session_id") or "").strip()
    base_url = str(target.get("base_url") or "").strip()
    if not base_url:
        cfg_fb = target.get("driver_config")
        if isinstance(cfg_fb, dict):
            base_url = str(cfg_fb.get("base_url") or "").strip()
    details: dict[str, Any] = {}
    source = target.get("driver_config")
    if isinstance(source, dict):
        details.update(source)
    extra = target.get("target_details")
    if isinstance(extra, dict):
        details.update(extra)
    explicit = str(details.get("attach_command") or "").strip()
    if explicit:
        return {"driver": driver, "session_id": native_session_id, "command": explicit, "source": "driver_config.attach_command"}
    if driver == "opencode":
        if base_url and native_session_id:
            command = (f"opencode --server {base_url} --session {native_session_id}"
                       if target.get("api_version") == 2
                       else f"opencode attach {base_url} --session {native_session_id}")
            return {"driver": driver, "session_id": native_session_id, "command": command, "source": "derived_from_native_target"}
        missing = "base_url" if not base_url else "native_session_id"
        return {"driver": driver, "session_id": native_session_id, "command": None, "reason": f"binding_missing_{missing}", "source": "derived_from_native_target"}
    explicit_manual = str(details.get("manual_open") or "").strip()
    if explicit_manual and driver == "codex":
        manual_open = {
            "native_thread": native_session_id,
            "co_agent_root": str(details.get("co_agent_root") or "") or None,
            "command": explicit_manual,
            "note": "target/DIP 配置 manual_open，按原文展示；本读面不编造命令。",
        }
        return {"driver": driver, "session_id": native_session_id, "command": None, "reason": "attach_undefined_for_driver:codex", "manual_open": manual_open, "source": "manual_open"}
    if explicit_manual:
        return {"driver": driver, "session_id": native_session_id, "command": explicit_manual, "source": "driver_config.manual_open"}
    if driver == "codex":
        manual_open: dict[str, Any] = {
            "native_thread": native_session_id,
            "co_agent_root": str(details.get("co_agent_root") or "") or None,
            "command": None,
            "note": ("codex 无外部 shell attach：人工在 Codex Desktop 定位绑定的原生会话，thread id 仅用于核对；"
                     "具备 mcp__codex_app__navigate_to_codex_page 工具的 Runtime 可用该导航"
                     "（threadId=native_session_id），不具备时即为人工路径；target/DIP 配置 manual_open 时按其原文展示。本读面不编造终端命令、不自动启动 Harness"),
        }
        return {"driver": driver, "session_id": native_session_id, "command": None, "reason": "attach_undefined_for_driver:codex", "manual_open": manual_open, "source": "derived_from_native_target"}
    return {
        "driver": driver, "session_id": native_session_id, "command": None,
        "reason": f"attach_undefined_for_driver:{driver or 'unknown'}",
        "note": "未核定该 Runtime 的 attach 入口；请使用其自身有依据的导航或人工路径，本读面不编造命令。",
        "source": "derived_from_native_target",
    }


def _local_pid_alive(pid: int) -> bool | None:
    """Read process existence only. Never use os.kill(pid, 0) on Windows."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return None
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (OSError, OverflowError):
        return None
    return True


def _codex_receiver_view(target: dict[str, Any]) -> dict[str, Any]:
    extension = target.get("extension")
    locator = str(extension.get("receiver_runtime_file") or "").strip() if isinstance(extension, dict) else ""
    view: dict[str, Any] = {
        "registered": bool(locator), "runtime_file": locator or None,
        "file_state": "not_registered", "state": "not_registered", "prepared": False,
        "pid": None, "pid_alive": None, "checked_at": datetime.now(timezone.utc).isoformat(),
        "reason": "receiver_runtime_file_not_registered", "blocking_reason": None,
        "repair_owner": "target_owner",
        "next_action": "原Owner从本人Desktop正常prepare，保持原locator/Thread/STOP；存活、未知或外Thread不覆盖。",
    }
    if not locator:
        view["next_action"] = "由正常Windows入职wake bind补齐接收配置，再由原Owner正常prepare；保留原Thread/STOP。"
        return view
    if os.name != "nt" and extension.get("execution_environment") == "windows":
        from runtime_injection import InjectionError, _windows_native
        try:
            return _windows_native(target, None, None, receiver_status=True)
        except (InjectionError, ValueError) as error:
            view.update(file_state="unknown", state="process_unknown", reason="windows_status_unavailable",
                        prepared=None, repair_owner="caller_installation_owner",
                        next_action="核正常Windows执行入口及安装配置；状态未确认，不按Linux PID判断或覆盖。")
            return view
    path = Path(posix_windows_drive_locator(locator)).expanduser()
    try:
        descriptor = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        view.update(file_state="missing", state="runtime_file_missing", reason="runtime_file_missing")
        return view
    except (OSError, UnicodeError) as error:
        view.update(file_state="unreadable", state="runtime_file_unreadable", reason=type(error).__name__)
        return view
    except json.JSONDecodeError:
        view.update(file_state="invalid", state="runtime_file_invalid", reason="invalid_json")
        return view
    if not isinstance(descriptor, dict) or descriptor.get("schema") != "paos-codex-self-reminder/v1":
        view.update(file_state="invalid", state="runtime_file_invalid", reason="invalid_schema")
        return view
    if descriptor.get("session_id") != target.get("session_id"):
        view.update(file_state="invalid", state="runtime_file_invalid", reason="target_session_mismatch")
        return view
    try:
        endpoint = urlsplit(str(descriptor.get("endpoint") or ""))
        valid_origin = (endpoint.scheme == "http" and endpoint.hostname == "127.0.0.1"
            and endpoint.port and not endpoint.username and not endpoint.password
            and not endpoint.path and not endpoint.query and not endpoint.fragment)
    except ValueError:
        valid_origin = False
    token = descriptor.get("token")
    if not valid_origin or not isinstance(token, str) or not token.strip():
        view.update(file_state="invalid", state="runtime_file_invalid", reason="invalid_receiver_grant")
        return view
    view.update(file_state="available", state="process_unknown", reason="pid_not_recorded")
    pid = descriptor.get("pid")
    if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
        return view
    view["pid"] = pid
    # A Windows descriptor read through WSL does not contain a Linux PID.
    foreign_process_host = (
        os.name != "nt" and (re.match(r"^[A-Za-z]:[\\/]", locator) or str(path).startswith("/mnt/"))
    ) or (os.name != "nt" and locator.startswith("\\\\"))
    if foreign_process_host:
        view["reason"] = "process_host_not_local"
        return view
    alive = _local_pid_alive(pid)
    view.update(pid_alive=alive, reason="process_check_unknown")
    if alive is False:
        view.update(state="process_not_running", reason="process_not_running")
    elif alive is True:
        from wakeup_native.process_identity import process_snapshot, valid_identity
        expected = descriptor.get("process_identity")
        snapshot = process_snapshot(pid, str(path) if "process_identity" not in descriptor else None,
                                    target.get("stop_file") if "process_identity" not in descriptor else None)
        view.update(pid_alive=snapshot["alive"], prepared=None, reason="process_identity_query_unavailable")
        if snapshot["alive"] is False:
            view.update(state="process_not_running", prepared=False, reason="process_not_running")
        elif snapshot["alive"] is True and "process_identity" not in descriptor:
            if snapshot.get("invocation_matches") is False:
                view.update(state="process_identity_mismatch", prepared=False, reason="receiver_invocation_mismatch")
            elif snapshot.get("invocation_matches") is True:
                view.update(reason="legacy_identity_unverified")
            else:
                view.update(reason="receiver_invocation_unavailable")
        elif snapshot["alive"] is True and valid_identity(expected) and valid_identity(snapshot.get("identity")):
            if expected.split(":", 1)[0] != snapshot["identity"].split(":", 1)[0]:
                view.update(reason="process_host_not_local")
            elif expected == snapshot["identity"]:
                view.update(state="prepared", prepared=True, reason=None, repair_owner=None, next_action=None,
                            receiver_behavior=descriptor.get("receiver_behavior"))
            else:
                view.update(state="process_identity_mismatch", prepared=False, reason="process_identity_mismatch")
    return view


def runtime_contact(root: Path, agent_id: str) -> dict[str, Any]:
    """Runtime contact facts for one Agent from its Contact native-target 项。

    Workless 语义：读面只反映已配置的本机原生 target（runtime/base_url/
    session_id/…）与显式 STOP 文件；不再报 attempt 状态，也不自动探测
    ——online/oracle 不由 PAOS 冒称， 失败与不可达如实返回。Codex接收入口
    只读运行文件/PID准备事实，不连接入口、不发送提醒。缺失与损坏
    的 target 配置保持可见区别。
    """
    root = Path(root)
    contact: dict[str, Any] = {
        "schema": CONTACT_SCHEMA,
        "configured": False,
        "target_status": "unconfigured",
        "binding_status": "unbound",
        "runtime": None,
        "driver": None,
        "native_session_id": None,
        "base_url": None,
        "stop_file": None,
        "stop_present": None,
        "state_basis": "native_target_absent",
        "online_state": "unknown",
        "checked_at": None,
        "attach": {},
        "inflight_attempts": [],
        "uncertain_attempts": [],
    }
    targets = load_native_targets(root)
    if targets is None:
        return contact
    target = targets.get(agent_id) if isinstance(targets.get(agent_id), dict) else None
    if not isinstance(target, dict) or not str(target.get("session_id") or "").strip():
        return contact
    contact["configured"] = True
    contact["binding_status"] = "configured"
    contact["target_status"] = "configured"
    contact["state_basis"] = "native_target_configured"
    contact["runtime"] = str(target.get("runtime") or "") or None
    contact["driver"] = contact["runtime"]
    contact["native_session_id"] = str(target.get("session_id") or "").strip()
    contact["base_url"] = str(target.get("base_url") or "") or None
    if contact["runtime"] == "opencode":
        contact["api_version"] = target.get("api_version", 1)
    contact["inflight_attempts"] = []
    contact["uncertain_attempts"] = []
    contact["stop_file"] = str(target.get("stop_file") or "") or None
    contact["stop_present"] = bool(contact["stop_file"] and Path(posix_windows_drive_locator(contact["stop_file"])).exists())
    if contact["runtime"] == "codex":
        contact["thread_registered"] = True
        contact["target_status"] = "thread_registered"
        contact["receiver"] = _codex_receiver_view(target)
        if contact["receiver"].get("repair_owner") == "target_owner":
            contact["receiver"]["repair_owner"] = agent_id
    contact["attach"] = derive_attach(contact)
    return contact


def load_native_targets(root: Path) -> dict[str, Any] | None:
    """Read the workless Contact native-target store (`contact/native-targets.json`).

    Returns None when the file is absent; raises TaskProblem on corrupt JSON so
    callers can visibly distinguish missing from broken.
    """
    store = Path(root) / "private-data" / "contact" / "native-targets.json"
    if not store.is_file():
        return None
    try:
        return json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkstationProblem(
            "native_targets_unreadable",
            f"原生 target 配置无法读取：{exc}",
            {"path": str(store)},
        ) from exc


def save_native_targets(root: Path, targets: dict[str, Any]) -> Path:
    store = Path(root) / "private-data" / "contact" / "native-targets.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(targets, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return store




def _read_project_home_state(
    project: dict[str, Any],
    root: Path,
    agent_id: str,
) -> dict[str, Any]:
    """Read the exact fixed Home through the shared Home/read service."""
    try:
        from paos_attention_service import read_home_state

        home_ref = project_agent_home(
            project=project,
            agent_id=agent_id,
            root_override=str(root),
            require_existing=True,
        )
        state = read_home_state(home_ref)
        return {
            "available": True,
            "read_model": state.get("read_model") or {},
        }
    except Exception as exc:
        return {
            "available": False,
            "status_basis": "read_error",
            "error": type(exc).__name__,
            "detail": str(exc)[:240],
        }


def build_team_rows(
    project: dict[str, Any],
    data_root: Path,
    *,
    numbers_map: dict[str, str] | None = None,
    agent_ids: set[str] | None = None,
) -> dict[str, Any]:
    """TEAM rows over fixed workstations; optional agent_ids narrows Home reads."""
    root = Path(posix_windows_drive_locator(str(data_root))).expanduser()
    sessions_by_agent: dict[str, list[dict[str, Any]]] = {}
    for session in project.get("sessions") or []:
        if isinstance(session, dict) and str(session.get("id") or ""):
            sessions_by_agent.setdefault(str(session.get("id")), []).append(session)
    agents: list[dict[str, Any]] = []
    workstation_root = root / "Workstations"
    if workstation_root.is_dir():
        for workstation in sorted(workstation_root.iterdir()):
            if not workstation.is_dir():
                continue
            agent_id = workstation.name
            if agent_ids is not None and agent_id not in agent_ids:
                continue
            active = [
                session
                for session in sessions_by_agent.get(agent_id, [])
                if str(session.get("status") or "") == "active"
            ]
            session = active[0] if active else None
            entry: dict[str, Any] = {
                "agent_id": agent_id,
                "identity_id": (session or {}).get("identity_id"),
                "staff_number": (numbers_map or {}).get(agent_id),
                "agent_label": (session or {}).get("agent_label"),
                "membership_basis": "fixed_workstation",
                "session_status": (session or {}).get("status") or "no_active_session",
                "workstation_todo": read_team_todo(root, agent_id),
                "runtime_contact": runtime_contact(root, agent_id),
                "home_read": _read_project_home_state(project, root, agent_id),
            }
            agents.append(entry)
    return {
        "schema": CONTACT_SCHEMA,
        "roster_filter": "fixed_workstation",
        "agents": agents,
    }


def contact_entry(
    root: Path,
    agent_id: str,
    session: dict[str, Any],
    numbers_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One peers row from the live active session + workstation facts."""
    entry: dict[str, Any] = {
        "agent_id": agent_id,
        "identity_id": session.get("identity_id"),
        "agent_label": session.get("agent_label"),
        "staff_number": (numbers_map or {}).get(agent_id),
        "membership_basis": "active_session",
        "session_status": session.get("status"),
        "workstation_todo": read_team_todo(root, agent_id),
        "runtime_contact": runtime_contact(root, agent_id),
    }
    return entry


def parse_team_payload(payload: dict[str, Any], lines: list[str]) -> None:
    for agent in payload["agents"]:
        todo = agent.get("workstation_todo") or {}
        runtime = agent.get("runtime_contact") or {}
        staff = agent.get('staff_number')
        lines.append(
            f"- {agent['agent_id']} ({agent.get('identity_id') or 'unregistered'})"
            + (f" [员工号={staff}]" if staff else "")
            + f"[session={agent.get('session_status') or 'unknown'}]"
        )
        home_read = agent.get("home_read") or {}
        if home_read.get("available"):
            model = home_read.get("read_model") or {}
            recovery = model.get("recovery") or {}
            counts = recovery.get("counts") or {}
            source = (model.get("sources") or {}).get("todo") or {}
            lines.append(
                f"  Home read: observed_at={model.get('observed_at') or 'unknown'} "
                f"unread_pending={counts.get('unread_pending', 0)} "
                f"read_pending={counts.get('read_pending', 0)} "
                f"handled_unread={counts.get('handled_unread', 0)}"
            )
            lines.append(
                f"  TODO source: {source.get('path') or 'unknown'} "
                f"fingerprint={source.get('fingerprint_sha256') or 'unknown'} "
                f"updated_at={source.get('semantic_updated_at') or 'unknown'}"
            )
        else:
            lines.append(
                f"  Home read: unavailable ({home_read.get('status_basis') or home_read.get('error') or 'unknown'})"
            )
        if todo.get("available"):
            fields = todo.get("current_section") or {}
            lines.append(f"  TODO: {todo.get('path')}")
            for label, key in (
                ("next", "next"),
                ("waiting", "waiting"),
                ("stage", "stage"),
            ):
                value = str(fields.get(key) or "").strip()
                if value:
                    lines.append(f"  {label}: {value}")
            for key, values in (todo.get("annotations") or {}).items():
                if values:
                    lines.append(f"  annotations.{key}: {' / '.join(str(v) for v in values)}")
            for title, entries in (todo.get("facts") or {}).items():
                lines.append(f"  facts[{title}]: {' | '.join(str(e) for e in entries[:3])}")
        else:
            lines.append(f"  TODO: unknown ({todo.get('reason') or 'unavailable'}) {todo.get('path')}")
        if runtime.get("configured"):
            attach = runtime.get("attach") or {}
            lines.append(
                f"  Runtime: driver={runtime.get('driver') or 'unknown'} "
                f"session={runtime.get('native_session_id') or 'unknown'} "
                f"online_state={runtime.get('online_state') or 'unknown'}"
                f" (basis={runtime.get('state_basis')}, checked_at={runtime.get('checked_at') or 'never'})"
            )
            receiver = runtime.get("receiver")
            if isinstance(receiver, dict):
                lines.append(
                    f"  Receiver: {receiver['state']} (registered={receiver['registered']}, "
                    f"file={receiver['file_state']}, pid_alive={receiver['pid_alive']}, "
                    f"checked_at={receiver['checked_at']}); wakeability=unknown, consumption=not_observed"
                )
            command = attach.get("command")
            if command:
                lines.append(f"  Attach: {command}")
            elif attach.get("manual_open"):
                manual = attach["manual_open"]
                lines.append(
                    f"  Attach: undefined for {attach.get('driver')}; manual open:"
                    f" thread={manual.get('native_thread') or 'unknown'}"
                    f" co_agent_root={manual.get('co_agent_root') or 'not configured'}"
                )
                if manual.get("command"):
                    lines.append(f"  Manual open command: {manual['command']}")
            else:
                lines.append(
                    f"  Attach: unavailable ({attach.get('reason') or 'undefined'}); manual start only"
                )
            inflight = runtime.get("inflight_attempts") or []
            for attempt_id in inflight[:3]:
                lines.append(f"  Inflight attempt: {attempt_id} (triggering, not observed)")
            if len(inflight) > 3:
                lines.append(f"  Inflight attempt: …and {len(inflight) - 3} more (explicit recover required)")
            uncertain = runtime.get("uncertain_attempts") or []
            for attempt_id in uncertain[:3]:
                lines.append(f"  Uncertain attempt: {attempt_id} (needs explicit recover)")
            if len(uncertain) > 3:
                lines.append(f"  Uncertain attempt: …and {len(uncertain) - 3} more (explicit recover required)")
        else:
            lines.append(f"  Runtime: unbound ({runtime.get('reason') or 'no wake binding'}); offline/manual start")


def render_team(payload: dict[str, Any]) -> str:
    lines = [
        f"PAOS team — {payload['agent_id']} @ {payload['project_id']}",
        f"Long-term Agents (status=active): {len(payload['agents'])}",
    ]
    parse_team_payload(payload, lines)
    meta = payload.get("meta") or {}
    lines.append(f"  base_url: {meta.get('base_url') or 'unknown'}")
    installation = meta.get("installation") or {}
    lines.append(
        f" installation locator: {installation.get('path') or 'not configured'}"
    )
    return "\n".join(lines)
