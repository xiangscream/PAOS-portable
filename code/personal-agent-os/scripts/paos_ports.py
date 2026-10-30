"""Port/service view for the installed PAOS machine (w027 port slice).

Read-only derivation + real probes. Sources: installation descriptor, the
base URL the CLI actually resolved (``client.base_url`` — not a second
config fact), the CAT base URL (legacy scope marker only) and every
registered project's wake bindings on this machine. One per-service state
carries a *named* bind result (bindable / address_in_use / unbindable /
not_probed) plus a health/identity reading; TCP and UDP never merge; no
lock is held; cross-host (Windows vs WSL) boundaries are reported as
unknown when the probe cannot observe them."""

from __future__ import annotations

import json
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SCHEMA = "paos-ports-view/v1"

BINDABLE = "bindable"
ADDRESS_IN_USE = "address_in_use"
UNBINDABLE = "unbindable"
NOT_PROBED = "not_probed"


class PortsProblem(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def utc_now() -> int:
    return int(time.time())


def _split_base_url(raw: str | None, *, label: str, config_source: str) -> dict[str, Any] | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().rstrip("/")
    if "://" not in text:
        text = "http://" + text
    try:
        parsed = urllib.parse.urlsplit(text)
        scheme = parsed.scheme
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise PortsProblem(
            "ports_base_url_invalid",
            f"{label} base_url 无法用标准库解析：{raw}",
            {"raw": raw},
        ) from exc
    if scheme not in ("http", "https") or not host:
        raise PortsProblem(
            "ports_base_url_invalid",
            f"{label} base_url 需要 http/https scheme 与可用 host：{raw}",
            {"raw": raw},
        )
    if port is None:
        port = 80 if scheme == "http" else 443
    protocol = scheme
    url = text
    return {
        "service": label,
        "protocol": protocol,
        "listen_host": host,
        "port": port,
        "url": url,
        "config_source": config_source,
        "maintainer": "PAOS Core (local_server.py)",
        "health_path": "/api/health",
        "claimed_version": None,
        "shared_by_agents": [],
    }


def health_contract_for(service_name: str) -> tuple[str, str, str]:
    """(health path, healthy checker, source of the version string)."""
    if "opencode" in service_name.lower():
        return (
            "/global/health",
            "body.healthy == true",
            "body.version",
        )
    return (
        "/api/health",
        "body.ok == true",
        "body.build.source_commit",
    )


def collect_bindings(project_roots: list[tuple[str, Path]]) -> dict[str, Any]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    unreadable: list[dict[str, str]] = []
    for project_id, root in project_roots:
        d = Path(root) / ".paos" / "wakeup" / "bindings"
        if not d.is_dir():
            continue
        for binding_file in sorted(d.glob("*.json")):
            agent_id = binding_file.stem
            try:
                value = json.loads(binding_file.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                unreadable.append({"binding": str(binding_file), "error": str(exc)[:120]})
                continue
            driver = str(value.get("driver") or "")
            config = value.get("driver_config") or {}
            base_url = str(config.get("base_url") or "")
            if not driver or not base_url:
                continue
            key = (driver, base_url)
            row = rows.setdefault(
                key,
                {
                    "service": f"{driver} server",
                    "url": base_url,
                    "config_source": f"wake bindings ({driver})",
                    "maintainer": f"{driver} runtime",
                    "claimed_version": str(config.get("expected_version") or "") or None,
                    "shared_by_agents": [],
                    "drivers": {driver},
                },
            )
            row["drivers"].add(driver)
            if agent_id not in row["shared_by_agents"]:
                row["shared_by_agents"].append(agent_id)
    result = []
    for row in rows.values():
        row["service"] = f"{'+'.join(sorted(row['drivers']))} server"
        del row["drivers"]
        row["shared_by_agents"].sort()
        result.append(row)
    return {"services": result, "unreadable_bindings": unreadable}


def probe_tcp_bind(host: str, port: int, socket_factory: Any = socket.socket) -> dict[str, Any]:
    """One exclusive bind-and-close probe. No lock is kept. Named outcome:
    ``bindable`` (Idle port), ``address_in_use`` (occupied), ``unbindable``
    (permission/validation etc. — NOT a definite occupancy claim)."""
    sock = socket_factory(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            sock.bind((host, port))
            return {
                "state": BINDABLE,
                "errno": None,
                "reason": "端口当前空闲（可启动），非占用证明",
            }
        except OSError as exc:
            if exc.errno in (98, 10048):
                return {
                    "state": ADDRESS_IN_USE,
                    "errno": exc.errno,
                    "reason": f"端口已被占用（{exc.strerror or 'address in use'}）",
                }
            if exc.errno in (13, 10013):
                return {
                    "state": UNBINDABLE,
                    "errno": exc.errno,
                    "reason": f"不可绑定：权限/排除范围/错误地址（{exc.strerror or 'access denied'}）",
                }
            return {
                "state": UNBINDABLE,
                "errno": exc.errno,
                "reason": f"不可绑定：{exc}",
            }
    finally:
        try:
            sock.close()
        except OSError:
            pass


def read_health(url: str, path: str, timeout: float = 4.0) -> dict[str, Any]:
    """HTTP GET health; every failure keeps the exception type/reason.
    Never merges a transport error with 'service offline'."""
    full = url.rstrip("/") + path
    try:
        with urllib.request.urlopen(full, timeout=timeout) as response:
            body = json.load(response)
            return {
                "reachable": True,
                "http_status": response.status,
                "body": body if isinstance(body, dict) else {"raw": body},
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {"reachable": False, "http_status": exc.code, "body": None, "error": f"HTTPError {exc.code}"}
    except urllib.error.URLError as exc:
        return {"reachable": False, "http_status": None, "body": None, "error": f"URLError {exc.reason}"}
    except (OSError, ValueError) as exc:
        return {"reachable": False, "http_status": None, "body": None, "error": f"{type(exc).__name__} {exc}"}


def _parse_windows_netstat_line(line: str, port: int) -> str | None:
    """Windows `netstat -ano -p TCP` fields: Proto Local Foreign State PID.
    Return the row only when Proto==TCP, State==LISTENING and the *local
    address field* ends with the target port after the last colon."""
    tokens = line.split()
    if len(tokens) < 5 or tokens[0].upper() != "TCP" or tokens[3].upper() != "LISTENING":
        return None
    local = tokens[1]
    tail = local.rsplit(":", 1)
    if len(tail) == 2 and tail[1] == str(port):
        return line.strip()
    return None


def _parse_linux_ss_line(line: str, port: int) -> str | None:
    """Linux `ss -ltnp` fields: State Recv-Q Send-Q Local:Port Peer ..."""
    tokens = line.split()
    if len(tokens) < 4 or tokens[0].upper() != "LISTEN":
        return None
    local = tokens[3]
    host_part, sep, port_part = local.rpartition(":")
    if sep and port_part.isdigit() and int(port_part) == port:
        return line.strip()
    return None


def _listener_failure(port: int, reason: str) -> dict[str, Any]:
    return {"known": False, "note": reason, "pid": None, "program": None}


def _netstat_listeners_for_port(
    port: int,
    windows_lines: list[str] | None = None,
    linux_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Platform-native read of the *local* listener table. Accepts pre-captured
    lines for deterministic tests; otherwise runs the platform command.
    Only the host/namespace this probe runs on is observable — Windows/WSL
    cross-side stays unknown."""
    system = platform.system()
    if windows_lines is not None:
        rows = [r for line in windows_lines if (r := _parse_windows_netstat_line(line, port))]
        return _summarize_listener_rows("Windows", rows, pids_from_netstat=bool(rows))
    if linux_lines is not None:
        rows = [r for line in linux_lines if (r := _parse_linux_ss_line(line, port))]
        return _summarize_listener_rows("Linux", rows, pids_from_netstat=False)
    try:
        if system == "Windows":
            # netstat 本地化（Windows 中文环境为 CP936/mbcs）。严格解码：
            # 不静默替换非法字节；解码失败在下层 except 中以 known=false 具体
            # reason 可见，不伪装成成功监听。
            completed = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True,
                text=True,
                encoding="mbcs",
                timeout=10,
            )
        else:
            completed = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=10)
    except (subprocess.SubprocessError, OSError, UnicodeDecodeError) as exc:
        return _listener_failure(port, f"listener 读取失败：{type(exc).__name__} {exc}")
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()[:120]
        return _listener_failure(port, f"listener 命令退出码 {completed.returncode}：{stderr or '无 stderr'} 行")
    parse = _parse_windows_netstat_line if system == "Windows" else _parse_linux_ss_line
    rows = [r for line in completed.stdout.splitlines() if (r := parse(line, port))]
    return _summarize_listener_rows(system, rows, pids_from_netstat=(system == "Windows"))


def _summarize_listener_rows(
    system: str, rows: list[str], *, pids_from_netstat: bool
) -> dict[str, Any]:
    if not rows:
        return {
            "known": False,
            "note": f"{system} 标准字段未见本端口 LISTENING 监听（跨 host 边界可能不可见）",
            "pid": None,
            "program": None,
        }

    def _resolve(row: str) -> dict[str, Any]:
        tokens = row.split()
        pid = None
        program = None
        import re

        if pids_from_netstat and tokens and tokens[-1].isdigit():
            pid = tokens[-1]
        else:
            match = re.search(r'users:\(\((?:"([^"]*)"|\'([^\']*)\'),pid=(\d+)', row)
            if match:
                program = match.group(1) or match.group(2)
                pid = match.group(3)
            elif "pid=" in row:
                pid_match = re.search(r"pid=(\d+)", row)
                if pid_match:
                    pid = pid_match.group(1)
        return {"pid": pid, "program": program}

    first = _resolve(rows[0])
    return {
        "known": True,
        "note": f"{len(rows)} listening row(s)（{system} 本 host/namespace）",
        "pid": first["pid"],
        "program": first["program"],
    }


def build_ports_view(
    *,
    installation: dict[str, Any],
    core_base_url: str | None,
    cat_base_url: str | None,
    project_roots: list[tuple[str, Path]],
    probed: bool = True,
    probe_host: str | None = None,
) -> dict[str, Any]:
    services: list[dict[str, Any]] = []
    core = _split_base_url(
        core_base_url,
        label="PAOS Core (attention-dashboard-v1)",
        config_source="CLI resolved base_url (single source, no second fact)",
    )
    if core:
        services.append(core)
    cat = _split_base_url(
        cat_base_url,
        label="CAT (legacy; exit scope, not new mainline)",
        config_source="PAOS_CAT_BASE_URL env",
    )
    if cat:
        services.append(cat)
    binding_pack = collect_bindings(project_roots)
    for row in binding_pack["services"]:
        parsed = _split_base_url(
            row["url"], label=row["service"], config_source=row["config_source"]
        )
        if parsed:
            parsed["service"] = row["service"]
            parsed["maintainer"] = row["maintainer"]
            parsed["claimed_version"] = row["claimed_version"]
            parsed["shared_by_agents"] = row["shared_by_agents"]
            parsed["shared_count"] = len(row["shared_by_agents"])
            services.append(parsed)

    if probed:
        for row in services:
            listen_host = str(row["listen_host"] or "")
            bind_host = probe_host or listen_host or "127.0.0.1"
            proto_contract = health_contract_for(row["service"])
            bind_result = probe_tcp_bind(bind_host, int(row["port"]))
            observation: dict[str, Any] = {
                "bind": bind_result,
                "listener": _netstat_listeners_for_port(int(row["port"])),
                "cross_host_note": "bind/listener 只覆盖本 probe 运行的 host/namespace；Windows/WSL 另一侧不自动可见",
                "checked_at": utc_now(),
            }
            if row["protocol"] in ("http", "https"):
                health = read_health(row["url"], proto_contract[0])
                observation["health_path"] = proto_contract[0]
                observation["health_contract"] = proto_contract[1]
                observation["health_error"] = health.get("error")
                observation["http_status"] = health.get("http_status")
                body = health.get("body") or {}
                if health.get("reachable"):
                    if row["service"].startswith("opencode"):
                        observation["health_ok"] = body.get("healthy") is True
                        observation["observed_version"] = body.get("version")
                    else:
                        observation["health_ok"] = body.get("ok") is True
                        observation["observed_version"] = (body.get("build") or {}).get("source_commit")
                else:
                    observation["health_ok"] = False
                    observation["observed_version"] = None
            row["observation"] = observation
            row["started_confirmed"] = bool(observation.get("health_ok"))
    else:
        for row in services:
            row["observation"] = {
                "bind": {"state": NOT_PROBED, "reason": "未探测（本视图不可据 bind 给出空闲或占用）"},
                "health_detail": "not probed（本次未发起健康回读；不是未响应，也不是 false）",
                "checked_at": utc_now(),
            }
            row["started_confirmed"] = None

    return {
        "schema": SCHEMA,
        "read_only": True,
        "probe_uses_locks": False,
        "holds_no_locks": True,
        "registration_completeness_note": "只派生登记服务；未登记进程不在本视图（诚实全集范围）",
        "services": services,
        "unreadable_bindings": binding_pack.get("unreadable_bindings") or [],
        "references_only": {
            "note": "以下路径只是报告引用（历史/范围事实），不是本视图事实，也不写入每轮视图",
            "items": [
                "PAOS-Rooter/rooter-001/reports/R075-ADOPTION-20261009/WINDOWS-PORT-RESERVATION-READBACK-20261009.json",
                "PAOS-Rooter/rooter-001/reports/DOT-CONTACT-20261007/",
            ],
        },
        "product_decision": {
            "token_reservations": "not implemented (default); revisit only with real benefit/each-runtime-cost evidence",
        },
    }


def render_ports_markdown(view: dict[str, Any]) -> str:
    lines = []
    lines.append(f"### {view['schema']} · captured {utc_now()}")
    lines.append("")
    lines.append("| 服务 | protocol | host:port | 异常 | 正文 | 状态 | 核来源 | 复用共享 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in view.get("services") or []:
        obs = row.get("observation") or {}
        bind = obs.get("bind") or {}
        state = bind.get("state") or NOT_PROBED
        state_txt = {
            BINDABLE: "端口空闲(bindable)",
            ADDRESS_IN_USE: "端口被占(address_in_use)",
            UNBINDABLE: "不可绑定(unbindable)",
            NOT_PROBED: "未探测(not_probed)",
        }.get(state, state)
        health = obs.get("health_ok")
        if obs.get("health_detail") == "not probed（本次未发起健康回读；不是未响应，也不是 false）":
            identity = "健康回读未进行（--no-probe）；不是未响应，也不是 false"
        elif obs.get("health_error"):
            identity = f"{obs.get('health_path')} 读取失败({obs.get('health_error')}); health_ok=false"
        elif health is True:
            identity = f"{obs.get('health_path')} ok; observed={obs.get('observed_version')}"
        else:
            identity = f"{obs.get('health_path')} 未响应; health_ok=false"
        shared = row.get("shared_by_agents") or []
        shared_txt = f"{len(shared)} 位（共享 OpenCode 服务）" if shared else "—"
        listeners = obs.get("listener") or {}
        bind_txt = f"{state_txt}，PID: {listeners.get('pid')}" if listeners.get("known") else state_txt
        lines.append(
            f"| {row['service']} | {row['protocol']} | {row.get('listen_host')}:{row.get('port')} | {row.get('config_source')} | {row.get('maintainer')} | {bind_txt} | {identity} | {shared_txt} |"
        )
    lines.append("")
    lines.append("started 只在健康/身份回读 ok 时成立；bind=open 状态只表示端口空闲 (可能绑定)，bind=in_use 为占用，unbindable/no-probe 不产生空闲/占用信息。")
    lines.append("")
    return "\n".join(lines)
