#!/usr/bin/env python3
"""PAOS Collaboration Watcher —— T-CW-01 单次版。

这是 PAOS 主服务之外的轻量 Sidecar。职责只是“该不该唤醒”：
读 run.json → 检查 STOP / 过期 / 任务上限 → 读取 PAOS office 中指向
目标 Session 的 open Request → 决定是否调用 Runtime Adapter。

它不理解业务任务，不代替 Agent 领取 Work（不调用 switch_work）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

RUN_SCHEMA = "paos-collab-run/v0"
STATE_SCHEMA = "paos-collab-watcher-state/v0"
SUPPORTED_ADAPTERS = ("manual", "mock", "command", "self")
REQUEST_STATES = {
    "triggering",
    "woken",
    "failed",
    "uncertain",
    "cancelled",
    "resolved",
    "manual_notified",
    "delegated",
}

# Request 终态：本项目事实中的 status 映射
TERMINAL_REQUEST_STATES = ("resolved", "cancelled")


class WatcherError(Exception):
    """Watcher 运行错误；消息面向人类。"""


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_collab_root() -> Path:
    env = os.environ.get("PAOS_COLLAB_ROOT")
    return Path(env).resolve() if env else repo_root() / "private-data" / "collab"


def utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """写 JSON 用临时文件 + os.replace，避免半写状态。"""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(str(tmp), str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PAOS Collaboration Watcher (T-CW-01)")
    parser.add_argument("--run-id", required=True, help="private-data/collab 下的一次协作 Run ID")
    parser.add_argument("--once", action="store_true", default=True, help="单次扫描后退出（T-CW-01 默认）")
    args = parser.parse_args(argv)

    try:
        watcher = CollabWatcher(args.run_id)
        code = watcher.run_once()
    except WatcherError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("[INFO] 收到 Ctrl-C，退出。")
        return 130
    return code


class CollabWatcher:
    """读取一次协作 Run，单次处理一个可触发 Request（at-most-once）。"""

    def __init__(
        self,
        run_id: str,
        *,
        collab_root: Path | None = None,
        fetch_json: Any = None,
    ):
        self.run_id = run_id
        self.collab_root = collab_root or default_collab_root()
        self.run_dir = self.collab_root / run_id
        self.lock_path = self.run_dir / "WATCHER.lock"
        self.stop_path = self.run_dir / "STOP"
        self.events_path = self.run_dir / "events.jsonl"
        self.state_path = self.run_dir / "state.json"
        self.run: dict[str, Any] = {}
        self.state: dict[str, Any] = {
            "schema": STATE_SCHEMA,
            "run_id": run_id,
            "requests": {},
            "tasks_woken": 0,
            "updated_at": utc_now_iso(),
        }
        self._fetch_json = fetch_json or self._http_get_json
        self._lock_held = False

    # ─── 基本 IO ───

    def _http_get_json(self, url: str) -> Any:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _ensure_run_dir(self) -> None:
        if not self.run_dir.is_dir():
            raise WatcherError(f"协作 Run 目录不存在：{self.run_dir}")

    def _load_run(self) -> dict[str, Any]:
        self._ensure_run_dir()
        try:
            run = read_json(self.run_dir / "run.json")
        except FileNotFoundError as error:
            raise WatcherError(f"缺少 run.json：{self.run_dir / 'run.json'}") from error
        except (OSError, json.JSONDecodeError) as error:
            raise WatcherError(f"run.json 无法读取或不是合法 JSON：{error}") from error
        validate_run_json(run)
        return run

    def _repair_events_tail(self) -> None:
        """只截断 EOF 残行；完整中间行必须保持可审计。"""
        if not self.events_path.exists():
            return
        data = self.events_path.read_bytes()
        if not data or data.endswith(b"\n"):
            return
        last_newline = data.rfind(b"\n")
        self.events_path.write_bytes(data[: last_newline + 1] if last_newline >= 0 else b"")

    def _append_event(self, event: str, **fields: Any) -> None:
        self._repair_events_tail()
        line = {"ts": utc_now_iso(), "event": event, "run_id": self.run_id, **fields}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def read_events(self) -> list[dict[str, Any]]:
        """读取完整事件；只允许忽略 EOF 最后一条残行。"""
        if not self.events_path.exists():
            return []
        data = self.events_path.read_bytes()
        lines = data.splitlines(keepends=True)
        events: list[dict[str, Any]] = []
        for index, raw in enumerate(lines):
            complete = raw.endswith(b"\n")
            if not complete and index == len(lines) - 1:
                break
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise WatcherError(
                    f"events.jsonl 第 {index + 1} 行损坏：{self.events_path}"
                ) from error
            if not isinstance(value, dict):
                raise WatcherError(
                    f"events.jsonl 第 {index + 1} 行必须是对象：{self.events_path}"
                )
            events.append(value)
        return events

    def _save_state(self) -> None:
        self.state["updated_at"] = utc_now_iso()
        write_json_atomic(self.state_path, self.state)

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            self._save_state()
            return self.state
        try:
            state = read_json(self.state_path)
        except (OSError, json.JSONDecodeError) as error:
            raise WatcherError(
                f"state.json 损坏或不可读，拒绝按空状态重建：{self.state_path} —— {error}"
            ) from error
        if state.get("schema") != STATE_SCHEMA or state.get("run_id") != self.run_id:
            raise WatcherError(
                f"state.json 与当前 Run 不匹配：{self.state_path}"
            )
        requests = state.get("requests")
        if not isinstance(requests, dict):
            raise WatcherError(f"state.json 缺少 requests 对象：{self.state_path}")
        tasks_woken = state.get("tasks_woken")
        if (
            isinstance(tasks_woken, bool)
            or not isinstance(tasks_woken, int)
            or tasks_woken < 0
        ):
            raise WatcherError("state.json tasks_woken 必须是非负整数。")
        for request_id, entry in requests.items():
            if not isinstance(request_id, str) or not request_id:
                raise WatcherError("state.json requests 的键必须是 Request ID。")
            if not isinstance(entry, dict):
                raise WatcherError(f"state.json requests[{request_id}] 必须是对象。")
            if entry.get("state") not in REQUEST_STATES:
                raise WatcherError(
                    f"state.json requests[{request_id}].state 不合法：{entry.get('state')}"
                )
            if not isinstance(entry.get("session_id", ""), str):
                raise WatcherError(
                    f"state.json requests[{request_id}].session_id 必须是文本。"
                )
        return state

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            # os.kill(pid, 0) 在 Windows 上可能向目标进程发送控制事件，
            # 不能用作无副作用存活探测。Get-Process 只读查询 PID。
            import subprocess

            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return result.returncode == 0
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _read_lock(self) -> dict[str, Any]:
        try:
            value = read_json(self.lock_path)
        except (OSError, json.JSONDecodeError) as error:
            raise WatcherError(
                f"WATCHER.lock 无法读取；请人工确认后删除：{self.lock_path}"
            ) from error
        if not isinstance(value, dict) or isinstance(value.get("pid"), bool) or not isinstance(value.get("pid"), int):
            raise WatcherError(
                f"WATCHER.lock 缺少有效 PID；请人工确认后删除：{self.lock_path}"
            )
        return value

    def _acquire_lock(self) -> None:
        """Run 级生命周期锁：活进程拒绝，死亡 PID 安全接管。"""
        for _ in range(2):
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as error:
                lock = self._read_lock()
                if self._pid_alive(lock["pid"]):
                    raise WatcherError(
                        f"WATCHER.lock 已由 PID {lock['pid']} 持有，拒绝启动第二个 Watcher：{self.lock_path}"
                    ) from error
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    {"pid": os.getpid(), "started_at": utc_now_iso()},
                    handle,
                    ensure_ascii=False,
                )
                handle.flush()
                os.fsync(handle.fileno())
            self._lock_held = True
            return
        raise WatcherError(f"无法安全取得 WATCHER.lock：{self.lock_path}")

    def _release_lock(self) -> None:
        if not self._lock_held:
            return
        try:
            lock = self._read_lock()
            if lock.get("pid") == os.getpid():
                self.lock_path.unlink()
        except FileNotFoundError:
            pass
        finally:
            self._lock_held = False

    # ─── 状态机辅助 ───

    @staticmethod
    def reconcile_triggering(state: dict[str, Any]) -> bool:
        """启动时把崩溃遗留的 triggering 转成 uncertain。返回是否有变化。"""
        changed = False
        for request_id, entry in list(state.get("requests", {}).items()):
            if isinstance(entry, dict) and entry.get("state") == "triggering":
                entry["state"] = "uncertain"
                entry["reason"] = "recovered_on_start"
                entry["updated_at"] = utc_now_iso()
                changed = True
        return changed

    @staticmethod
    def reconcile_with_project(
        state: dict[str, Any], project_requests: dict[str, str]
    ) -> list[dict[str, str]]:
        """按 Project 权威事实收口 woken/uncertain，返回逐条状态变化。"""
        changes: list[dict[str, str]] = []
        for request_id, entry in list(state.get("requests", {}).items()):
            if not isinstance(entry, dict) or entry.get("state") not in {
                "woken",
                "uncertain",
                "manual_notified",
                "delegated",
            }:
                continue
            status = project_requests.get(request_id)
            if status not in TERMINAL_REQUEST_STATES:
                continue
            before = str(entry.get("state"))
            entry["state"] = status
            entry["updated_at"] = utc_now_iso()
            if status == "resolved":
                entry["resolved_at"] = utc_now_iso()
            else:
                entry["reason"] = "project_request_cancelled"
            changes.append(
                {"request_id": request_id, "before": before, "after": status}
            )
        return changes

    def _is_stopped(self) -> bool:
        return self.stop_path.exists()

    def _is_expired(self) -> bool:
        expires = self.run.get("expires_at", "")
        return bool(expires) and expires <= utc_now_iso()

    def _reached_task_limit(self) -> bool:
        max_tasks = int(self.run.get("limits", {}).get("max_tasks_per_run", 1))
        return int(self.state.get("tasks_woken", 0)) >= max_tasks

    # ─── 主流程 ───

    def run_once(self) -> int:
        self.run = self._load_run()
        self._acquire_lock()
        try:
            self.state = self._load_state()

            # 启动即修正崩溃遗留：triggering → uncertain。T-CW-01 无法确定
            # 外部 Runtime 是否已经启动，因此本轮只做权威对账，不再唤醒其他 Request。
            recovered_uncertain = self.reconcile_triggering(self.state)
            if recovered_uncertain:
                self._append_event("state.reconciled", detail="triggering -> uncertain")
                self._save_state()

            base_url = self.run["paos_base_url"].rstrip("/")
            project_id = self.run["project_id"]
            project_payload = self._fetch_json(f"{base_url}/api/projects/{project_id}")
            project_requests = parse_project_requests(project_payload)

            # 停止条件只阻止新唤醒，不能阻止已发生任务的状态对账。
            changes = self.reconcile_with_project(self.state, project_requests)
            if changes:
                for change in changes:
                    self._append_event("state.reconciled", **change)
                self._save_state()

            if recovered_uncertain:
                self._append_event("uncertain.requires_manual_review")
                return 0
            if self._is_stopped():
                self._append_event("stop.seen", stage="start", reason="STOP exists")
                return 0
            if self._is_expired():
                self._append_event("run.expired", expires_at=self.run.get("expires_at"))
                return 0
            if self._reached_task_limit():
                self._append_event("task_limit.reached", tasks_woken=self.state.get("tasks_woken"))
                return 0

            triggered_one = False
            handled_non_external = False
            for session_id, session_cfg in self.run.get("sessions", {}).items():
                office_payload = self._fetch_json(
                    f"{base_url}/api/projects/{project_id}/office?session_id={session_id}"
                )
                pending = parse_pending_requests(office_payload)
                for request in pending:
                    request_id = request.get("id")
                    if not request_id:
                        continue
                    if request_id in self.state.get("requests", {}):
                        continue
                    if self._reached_task_limit():
                        self._append_event("task_limit.reached", tasks_woken=self.state.get("tasks_woken"))
                        return 0

                    adapter = build_adapter(session_cfg, self.run_dir)
                    if getattr(adapter, "trigger_mode", "external") != "external":
                        delegated = getattr(adapter, "trigger_mode", "external") == "self"
                        state_name = "delegated" if delegated else "manual_notified"
                        event = "wake.delegated" if delegated else "wake.needs_manual"
                        self.state["requests"][request_id] = {
                            "state": state_name,
                            "session_id": session_id,
                            "work_item_id": request.get("target_work_item_id", ""),
                            "updated_at": utc_now_iso(),
                        }
                        self._save_state()
                        self._append_event(
                            event,
                            request_id=request_id,
                            session_id=session_id,
                            adapter=adapter.name,
                            reason=adapter.can_wake()[1],
                        )
                        handled_non_external = True
                        continue

                    # at-most-once：先原子写 triggering，再唤醒
                    self.state["requests"][request_id] = {
                        "state": "triggering",
                        "session_id": session_id,
                        "work_item_id": request.get("target_work_item_id", ""),
                        "updated_at": utc_now_iso(),
                    }
                    self._save_state()

                    can_wake, reason = adapter.can_wake()
                    self._append_event(
                        "request.triggering",
                        request_id=request_id,
                        session_id=session_id,
                        adapter=adapter.name,
                        can_wake=can_wake,
                        reason=reason,
                    )
                    if not can_wake:
                        self.state["requests"][request_id] = {
                            "state": "failed",
                            "session_id": session_id,
                            "reason": f"adapter_cannot_wake: {reason}",
                            "updated_at": utc_now_iso(),
                        }
                        self._save_state()
                        self._append_event(
                            "wake.failure",
                            request_id=request_id,
                            session_id=session_id,
                            reason=f"adapter_cannot_wake: {reason}",
                        )
                        triggered_one = True
                        break

                    # can_wake 可能访问磁盘；真正产生外部副作用前紧邻复查 STOP 与硬截止。
                    cancel_reason = ""
                    if self._is_stopped():
                        cancel_reason = "stopped_before_wake"
                    elif self._is_expired():
                        cancel_reason = "expired_before_wake"
                    if cancel_reason:
                        self.state["requests"][request_id] = {
                            "state": "cancelled",
                            "session_id": session_id,
                            "reason": cancel_reason,
                            "updated_at": utc_now_iso(),
                        }
                        self._save_state()
                        self._append_event(
                            "wake.cancelled",
                            request_id=request_id,
                            session_id=session_id,
                            reason=cancel_reason,
                        )
                        return 0

                    try:
                        result = adapter.wake(
                            target_session_id=session_id,
                            request_id=request_id,
                            wake_prompt=self.run.get("wake_prompt_template", "去 PAOS 领取新周期。"),
                        )
                    except OSError as error:
                        result = {
                            "ok": False,
                            "pid": None,
                            "detail": f"adapter_start_failed: {error}",
                        }
                    if result.get("ok"):
                        self.state["requests"][request_id] = {
                            "state": "woken",
                            "session_id": session_id,
                            "pid": result.get("pid"),
                            "updated_at": utc_now_iso(),
                        }
                        self.state["tasks_woken"] = int(self.state.get("tasks_woken", 0)) + 1
                        self._save_state()
                        self._append_event(
                            "wake.success",
                            request_id=request_id,
                            session_id=session_id,
                            detail=result.get("detail", ""),
                            pid=result.get("pid"),
                        )
                    else:
                        self.state["requests"][request_id] = {
                            "state": "failed",
                            "session_id": session_id,
                            "reason": result.get("detail", "adapter_wake_failed"),
                            "updated_at": utc_now_iso(),
                        }
                        self._save_state()
                        self._append_event(
                            "wake.failure",
                            request_id=request_id,
                            session_id=session_id,
                            reason=result.get("detail", "adapter_wake_failed"),
                        )
                    triggered_one = True
                    break
                if triggered_one:
                    break

            if not triggered_one and not handled_non_external:
                self._append_event(
                    "watcher.pass",
                    detail="no eligible pending request",
                )
            return 0
        finally:
            self._release_lock()


# ─── 解析辅助（测试固定 JSON fixture 用，保持层级真实） ───

def parse_pending_requests(office_payload: Any) -> list[dict[str, Any]]:
    """从真实 /office 响应中提取 pending_requests。

    真实层级：{"ok": true, "office": {"pending_requests": [...]}}
    """
    if not isinstance(office_payload, dict):
        return []
    office = office_payload.get("office")
    if not isinstance(office, dict):
        return []
    pending = office.get("pending_requests")
    return pending if isinstance(pending, list) else []


def parse_project_requests(project_payload: Any) -> dict[str, str]:
    """从真实 /api/projects/{id} 响应中提取 request id -> status。"""
    if not isinstance(project_payload, dict):
        return {}
    project = project_payload.get("project")
    if not isinstance(project, dict):
        return {}
    result: dict[str, str] = {}
    for request in project.get("requests", []):
        if isinstance(request, dict) and request.get("id"):
            result[request["id"]] = request.get("status", "")
    return result


# ─── run.json 校验 ───

def validate_run_json(run: Any) -> None:
    if not isinstance(run, dict):
        raise WatcherError("run.json 必须是 JSON 对象。")
    if run.get("schema") != RUN_SCHEMA:
        raise WatcherError(f"run.json schema 必须是 {RUN_SCHEMA}。")
    project_id = run.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise WatcherError("run.json 必须提供 project_id。")
    base_url = run.get("paos_base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise WatcherError("run.json 必须提供 paos_base_url。")
    sessions = run.get("sessions")
    if not isinstance(sessions, dict) or not sessions:
        raise WatcherError("run.json sessions 必须是非空对象。")
    for session_id, cfg in sessions.items():
        if not isinstance(session_id, str) or not session_id:
            raise WatcherError("run.json sessions 的键必须是 Session ID。")
        if not isinstance(cfg, dict):
            raise WatcherError(f"run.json sessions[{session_id}] 必须是对象。")
        adapter = cfg.get("adapter")
        if adapter not in SUPPORTED_ADAPTERS:
            raise WatcherError(
                f"run.json sessions[{session_id}].adapter 必须是 {SUPPORTED_ADAPTERS} 之一。"
            )
    limits = run.get("limits", {})
    if not isinstance(limits, dict):
        raise WatcherError("run.json limits 必须是对象。")
    for key in ("max_tasks_per_run", "max_concurrency_per_session"):
        value = limits.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value != 1:
            raise WatcherError(f"T-CW-01 要求 limits.{key} 必须严格为整数 1。")
    if limits.get("wake_once_per_request") is not True:
        raise WatcherError(
            "T-CW-01 要求 limits.wake_once_per_request 必须为 true。"
        )
    return None


# ─── Adapter ───

from collab_adapters import SUPPORTED_ADAPTERS_MAP  # noqa: E402


def build_adapter(session_cfg: dict[str, Any], run_dir: Path):
    adapter_name = session_cfg.get("adapter", "manual")
    adapter_cls = SUPPORTED_ADAPTERS_MAP.get(adapter_name)
    if adapter_cls is None:
        raise WatcherError(f"不支持的 adapter：{adapter_name}")
    return adapter_cls(session_cfg.get("adapter_config", {}), run_dir=run_dir)


if __name__ == "__main__":
    sys.exit(main())
