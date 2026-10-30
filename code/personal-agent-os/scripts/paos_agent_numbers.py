"""Staff-number registry: one installation-wide unique long-term agent number.
Reads and writes the single `AGENT-NUMBERS.json` registry; no second registry,
no auto-interpretation of project suffixes. Missing file is a real error; write
failures fail closed.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

_LOCK_TIMEOUT_SECS = 30.0

try:
    import fcntl
except ImportError:
    fcntl = None

from paos_installation import InstallationProblem, load_installation_descriptor
from paos_workstation import posix_windows_drive_locator

SCHEMA = "paos-agent-numbers/v1"
NUM_RE = re.compile(r"^S(\d+)$")


class NumbersProblem(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def resolve_numbers_path(
    explicit: str | None,
    installation_path: Path,
    installation: dict[str, Any] | None = None,
) -> Path:
    """Single registry locator: explicit --agent-numbers-file wins, then
    installation descriptor field `agent_numbers_config`, then a
    `AGENT-NUMBERS.json` sitting beside the installation descriptor."""
    if explicit:
        return Path(explicit).expanduser()
    if installation is None:
        try:
            installation = load_installation_descriptor(installation_path)
        except InstallationProblem:
            installation = {}
    configured = str((installation or {}).get("agent_numbers_config") or "").strip()
    if configured:
        return Path(configured).expanduser()
    neighbour = Path(installation_path).expanduser().parent / "AGENT-NUMBERS.json"
    if neighbour.is_file():
        return neighbour
    raise NumbersProblem(
        "agent_numbers_not_configured",
        "未配置唯一员工号登记：安装描述缺 `agent_numbers_config`，且安装描述旁没有 AGENT-NUMBERS.json。",
        {"installation_path": str(installation_path)},
    )


def load_numbers(path: Path) -> dict[str, str]:
    path = Path(posix_windows_drive_locator(str(path))).expanduser()
    if not path.is_file():
        raise NumbersProblem(
            "agent_numbers_registry_missing",
            f"员工号登记文件不存在：{path}",
            {"path": str(path)},
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NumbersProblem(
            "agent_numbers_registry_invalid",
            f"员工号登记无法读取：{exc}",
            {"path": str(path)},
        ) from exc
    if not isinstance(data, dict):
        raise NumbersProblem(
            "agent_numbers_registry_invalid",
            "员工号登记必须是整对象（agent_id → S 号）。",
            {"path": str(path)},
        )
    numbers: dict[str, str] = {}
    for key, value in data.items():
        agent_id = str(key or "").strip()
        label = str(value or "").strip()
        if not agent_id or not NUM_RE.match(label):
            raise NumbersProblem(
                "agent_numbers_registry_invalid",
                f"员工号登记包含非法条目：{key!r} → {value!r}",
                {"path": str(path)},
            )
        numbers[agent_id] = label
    return numbers


def save_numbers(path: Path, numbers: dict[str, str]) -> None:
    path = Path(posix_windows_drive_locator(str(path))).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.parent / f".{path.name}.staging-{os.getpid()}"
    try:
        stage.write_text(
            json.dumps(numbers, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(stage, path)
    except Exception as exc:
        try:
            stage.unlink(missing_ok=True)
        except OSError:
            pass
        raise NumbersProblem(
            "agent_numbers_write_failed",
            f"员工号登记写入失败：{exc}",
            {"path": str(path)},
        ) from exc


@contextlib.contextmanager
def _registry_lock(path: Path, timeout_secs: float | None = None):
    """Exclusive cross-runtime lock over the whole read-modify-write critical
    section. fcntl/msvcrt advisory locks do not exclude each other across
    WSL/drvfs (verified), so exclusivity uses one atomic create-exclusive
    claim file (O_CREAT|O_EXCL is honored by both runtimes on the same Windows
    volume). No stealing: a leftover lock (e.g. after a crashed holder) blocks
    every waiter until the wait times out with a real error; the explicit
    owner must then be verified and the lock removed by installation
    governance, never silently taken over."""
    path = Path(posix_windows_drive_locator(str(path))).expanduser()
    lock_path = path.parent / f".{path.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + (timeout_secs if timeout_secs is not None else _LOCK_TIMEOUT_SECS)
    fd = None
    while True:
        try:
            fd = os.open(
                lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC
            )
            os.write(fd, f"holder pid={os.getpid()}".encode("utf-8"))
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise NumbersProblem(
                    "agent_numbers_lock_timeout",
                    (
                        f"员工号登记锁等待超时：{lock_path} 已被其他持有者占用"
                        "；若确认持有者已终止，由安装治理明确核实例后移除该锁文件，"
                        f"本机制绝不静默接管。"
                    ),
                    {"path": str(lock_path)},
                )
            time.sleep(0.01)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
            try:
                lock_path.unlink()
            except OSError:
                pass


def _max_used(numbers: dict[str, str]) -> int:
    used = 0
    for label in numbers.values():
        match = NUM_RE.match(label)
        if match:
            used = max(used, int(match.group(1)))
    return used


def allocate_number(
    path: Path,
    agent_id: str,
    *,
    explicit_label: str | None = None,
    extra_forbidden: dict[str, str] | None = None,
    timeout_secs: float | None = None,
) -> str:
    """Assign one unique number to this agent, replay-safe.
    Caller passes numbers already merged from extra sources (e.g. an offline
    migration inventory) so nothing silently duplicates."""
    agent_id = agent_id.strip()
    with _registry_lock(path, timeout_secs=timeout_secs):
        numbers = load_numbers(path)
        for source in (extra_forbidden or {}):
            numbers.setdefault(source, extra_forbidden[source])  # type: ignore[index]
        existing = numbers.get(agent_id)
        if existing:
            return existing  # replay/reopen: keep the same number
        if explicit_label:
            if not NUM_RE.match(explicit_label):
                raise NumbersProblem(
                    "agent_numbers_label_invalid",
                    f"指定的员工号不符合 S+数字 格式：{explicit_label!r}",
                    {"agent_id": agent_id},
                )
            label = explicit_label
        else:
            candidate = _max_used(numbers) + 1
            while f"S{candidate:03d}" in numbers.values():
                candidate += 1
            label = f"S{candidate:03d}"
        if any(
            value == label and key != agent_id for key, value in numbers.items()
        ):
            raise NumbersProblem(
                "agent_numbers_conflict",
                f"员工号 {label} 已被其他长期 Agent 登记，不能静默重复。",
                {"agent_id": agent_id, "label": label},
            )
        numbers[agent_id] = label
        save_numbers(path, numbers)
        return label


def agent_id_for_staff_number(
    staff_number_value: str,
    *,
    explicit_path: str | None = None,
    path: Path | None = None,
    installation_path: Path | None = None,
    installation: dict[str, Any] | None = None,
) -> str:
    """Staff-number addressing (Human-approved unified delivery): real registry
    reverse lookup only — never guess by suffix or shadow another agent. The
    registry values look like S036; the caller normalizes the input only by
    trimming and case-folding the leading S.  Raises NumbersProblem on
    unknown/duplicate mapping so CLI callers can surface precise errors."""
    want = str(staff_number_value or "").strip().upper()
    if not want.startswith("S") or len(want) < 2 or not want[1:].isdigit():
        raise NumbersProblem(
            "staff_number_invalid",
            f"无效员工号：{staff_number_value!r}（正确形态如 S036）",
            {"staff_number": staff_number_value},
        )
    registry_path = path
    if registry_path is None:
        registry_path = resolve_numbers_path(
            explicit_path, installation_path or Path(__file__).parent, installation
        )
    numbers = load_numbers(registry_path)
    matches = sorted(k for k, v in numbers.items() if str(v).strip().upper() == want)
    if not matches:
        raise NumbersProblem(
            "staff_number_unknown",
            f"员工号未在注册登记中找到：{want}",
            {"staff_number": want, "registry": str(registry_path)},
        )
    if len(matches) > 1:
        raise NumbersProblem(
            "staff_number_ambiguous",
            f"员工号映射到多个 Agent，需要先在登记中澄清：{want} -> {matches}",
            {"staff_number": want, "matches": matches},
        )
    return matches[0]


def staff_number(
    agent_id: str,
    *,
    explicit_path: str | None = None,
    path: Path | None = None,
    installation_path: Path | None = None,
    installation: dict[str, Any] | None = None,
) -> str | None:
    """Display-only lookup. Unknown agent → None (never guess by suffix)."""
    try:
        registry_path = path
        if registry_path is None:
            if installation_path is None and not explicit_path:
                return None
            registry_path = resolve_numbers_path(
                explicit_path, installation_path or Path(__file__).parent, installation
            )
        return load_numbers(registry_path).get(agent_id.strip())
    except NumbersProblem:
        return None
