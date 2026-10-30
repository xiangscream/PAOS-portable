#!/usr/bin/env python3
"""collab_run.py — T-MA-01 有界协作 Run 信封 CLI。

仅管理本地执行信封（run.json / STOP / marker.json / events.jsonl / 临时 hook 材料 / active-run 指针）。
不写 PAOS。运行环境：Windows 原生 Python 3.11（标准库）。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = "collab-run/v1"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
PACKAGE_DIR = Path(__file__).resolve().parent
ACTIVE_POINTER = Path(os.environ.get("TEMP", str(Path.home() / "AppData/Local/Temp"))) / "paos-collab-active-run.json"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def rfc3339(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def win_to_wsl(path_text: str) -> str:
    """把 Windows 路径转成 WSL 路径（DS-H 插件在 WSL 内用文件 API 时需要的形态）。"""
    p = path_text.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        return "/mnt/" + p[0].lower() + p[2:]
    return p


def parse_project_pair(session_id: str, request_id: str, project_id: str | None) -> str:
    if project_id:
        pid = project_id
    else:
        pid_s = session_id.rsplit("-s", 1)[0] if "-s" in session_id else ""
        pid_r = request_id.rsplit("-r", 1)[0] if "-r" in request_id else ""
        if not pid_s or not pid_r or pid_s != pid_r:
            sys.exit("[collab-run] session/request 必须同项目（形如 <pid>-s*/<pid>-r*），或用 --project-id 显式指定")
        pid = pid_s
    if not (session_id.startswith(pid + "-s") and request_id.startswith(pid + "-r")):
        sys.exit(f"[collab-run] session/request 与项目 {pid} 不匹配")
    return pid


def build_codex_hooks(command: str) -> str:
    cfg = {"hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", "command": command}]}]}}
    return json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"


def load_run(run_dir: Path) -> dict:
    if not run_dir.is_dir():
        sys.exit(f"[collab-run] 目录不存在: {run_dir}")
    f = run_dir / "run.json"
    if not f.is_file():
        sys.exit(f"[collab-run] 不是有效 run 目录（缺 run.json）: {run_dir}")
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"[collab-run] run.json 非法: {e}")
    if data.get("schema") != SCHEMA:
        sys.exit(f"[collab-run] schema 不匹配（期望 {SCHEMA}）: {data.get('schema')}")
    return data


def count_continues(run_dir: Path) -> int:
    f = run_dir / "events.jsonl"
    n = 0
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip().lstrip("\ufeff")
            if not line:
                continue
            try:
                if json.loads(line).get("event") == "continue":
                    n += 1
            except json.JSONDecodeError:
                pass  # 忽略半截审计行
    return n


def cmd_create(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    if run_dir.exists():
        sys.exit(f"[collab-run] run 目录已存在，拒绝覆盖: {run_dir}")
    if args.max_steps < 1:
        sys.exit("[collab-run] --max-steps 必须 >= 1")
    if args.ttl_minutes < 1:
        sys.exit("[collab-run] --ttl-minutes 必须 >= 1")
    project_id = parse_project_pair(args.session_id, args.request_id, args.project_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    now = utcnow()
    run = {
        "schema": SCHEMA,
        "run_id": f"run-{uuid.uuid4().hex[:12]}",
        "project_id": project_id,
        "session_id": args.session_id,
        "request_id": args.request_id,
        "max_steps": args.max_steps,
        "ttl_minutes": args.ttl_minutes,
        "created_at": rfc3339(now),
        "expires_at": rfc3339(now + timedelta(minutes=args.ttl_minutes)),
    }
    (run_dir / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    now = utcnow()
    expiry_error = False
    expired = None
    try:
        expires = datetime.fromisoformat(run["expires_at"].replace("Z", "+00:00"))
        expired = now > expires
    except (ValueError, KeyError, TypeError):
        expiry_error = True
    marker = None
    mp = run_dir / "marker.json"
    if mp.is_file():
        try:
            marker = json.loads(mp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            marker = {"_error": "marker.json 非法"}
    pointer = None
    pointer_present = ACTIVE_POINTER.is_file()
    if pointer_present:
        try:
            pointer = json.loads(ACTIVE_POINTER.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pointer = {"_error": "active-run 指针非法"}
    report = {
        "run_id": run["run_id"],
        "project_id": run.get("project_id"),
        "session_id": run["session_id"],
        "request_id": run["request_id"],
        "max_steps": run["max_steps"],
        "ttl_minutes": run["ttl_minutes"],
        "expires_at": run["expires_at"],
        "expired": expired,
        "expiry_parse_error": expiry_error,
        "stop_present": (run_dir / "STOP").is_file(),
        "marker_present": marker is not None,
        "marker": marker,
        "auto_steps_consumed": count_continues(run_dir),
        "active_pointer_present": pointer_present,
        "active_pointer": pointer,
        "hook_seen": (run_dir / "hook_seen").is_file(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_stop(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    _ = load_run(run_dir)
    (run_dir / "STOP").write_text(f"stopped_at={rfc3339(utcnow())}\n", encoding="utf-8")
    print(json.dumps({"ok": True, "stop": str(run_dir / "STOP")}, ensure_ascii=False))


def cmd_cleanup(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    if not args.yes:
        sys.exit(f"[collab-run] cleanup 会删除整个 run 目录；确认请加 --yes（run_id={run['run_id']}）")
    # 若 active 指针指向本 Run，先撤销，避免留下悬挂指针
    if ACTIVE_POINTER.is_file():
        try:
            ptr = json.loads(ACTIVE_POINTER.read_text(encoding="utf-8"))
            if Path(ptr.get("run_dir", "")).resolve() == run_dir.resolve():
                ACTIVE_POINTER.unlink()
        except (json.JSONDecodeError, OSError):
            pass
    shutil.rmtree(run_dir)
    print(json.dumps({"ok": True, "removed": str(run_dir)}, ensure_ascii=False))


def cmd_activate(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    target = str(run_dir.resolve())
    if ACTIVE_POINTER.is_file():
        try:
            prev = json.loads(ACTIVE_POINTER.read_text(encoding="utf-8"))
            prev_dir = prev.get("run_dir", "")
        except json.JSONDecodeError:
            prev_dir = ""
        if prev_dir and Path(prev_dir).resolve() != run_dir.resolve() and not args.force:
            sys.exit(f"[collab-run] 已有激活 Run：{prev_dir}。请先 deactivate，或加 --force 覆盖。")
    ACTIVE_POINTER.write_text(
        json.dumps({"run_dir": target, "active": True, "run_id": run["run_id"], "activated_at": rfc3339(utcnow())}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "pointer": str(ACTIVE_POINTER), "run_dir": target}, ensure_ascii=False))


def cmd_deactivate(args: argparse.Namespace) -> None:
    removed = ACTIVE_POINTER.is_file()
    if removed:
        ACTIVE_POINTER.unlink()
    print(json.dumps({"ok": True, "removed_pointer": removed, "pointer": str(ACTIVE_POINTER)}, ensure_ascii=False))


def fill(template: str, mapping: dict[str, str]) -> str:
    out = template
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _write_ps1_bom_crlf(dst: Path, text: str) -> None:
    normalized = "\r\n".join(text.lstrip("\ufeff").splitlines()) + "\r\n"
    dst.write_bytes(b"\xef\xbb\xbf" + normalized.encode("utf-8"))


def cmd_materialize(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    run = load_run(run_dir)
    runtime = args.runtime
    run_abs = str(run_dir.resolve())
    mapping = {
        "run_id": run["run_id"],
        "project_id": run.get("project_id", ""),
        "session_id": run["session_id"],
        "request_id": run["request_id"],
        "max_steps": str(run["max_steps"]),
        "ttl_minutes": str(run["ttl_minutes"]),
        "expires_at": run["expires_at"],
        "run_dir": run_abs,
        "wsl_run_dir": win_to_wsl(run_abs),
    }
    made: list[str] = []

    if runtime in ("codex", "all"):
        codex_dir = run_dir / "codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        ps1_dst = codex_dir / "stop_hook.ps1"
        _write_ps1_bom_crlf(ps1_dst, fill((TEMPLATE_DIR / "codex_stop_hook.ps1").read_text(encoding="utf-8"), mapping))

        # 临时 Codex 配置：用 JSON 序列化生成，避免 Windows 反斜杠破坏 JSON
        cmd_tmp = f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps1_dst.resolve()}"'
        (codex_dir / "hooks.json").write_text(build_codex_hooks(cmd_tmp), encoding="utf-8")

        # 稳定适配器说明（含正确转义的 JSON 配置）
        adapter = (PACKAGE_DIR / "codex_stop_adapter.ps1").resolve()
        adapter_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "{adapter}"'
        mapping["adapter_path"] = str(adapter)
        mapping["stable_hooks_json"] = build_codex_hooks(adapter_cmd).rstrip("\n")
        (run_dir / "STABLE_SETUP.md").write_text(
            fill((TEMPLATE_DIR / "stable_setup.md").read_text(encoding="utf-8"), mapping), encoding="utf-8"
        )
        made.extend(["codex/hooks.json", "codex/stop_hook.ps1", "STABLE_SETUP.md"])

    if runtime in ("dsh", "all"):
        dsh_dir = run_dir / "dsh"
        dsh_dir.mkdir(parents=True, exist_ok=True)
        (dsh_dir / "README.md").write_text(
            fill((TEMPLATE_DIR / "dsh_idle_hook.md").read_text(encoding="utf-8"), mapping), encoding="utf-8"
        )
        made.append("dsh/README.md")

    (run_dir / "WORKER_PROMPT.md").write_text(
        fill((TEMPLATE_DIR / "worker_prompt.md").read_text(encoding="utf-8"), mapping), encoding="utf-8"
    )
    made.append("WORKER_PROMPT.md")

    print(json.dumps({"ok": True, "runtime": runtime, "run_dir": run_abs, "generated": made}, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="collab_run.py", description="T-MA-01 有界协作 Run 信封 CLI（不写 PAOS）")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="创建 Run 信封")
    c.add_argument("run_dir")
    c.add_argument("--session-id", required=True)
    c.add_argument("--request-id", required=True)
    c.add_argument("--project-id", default=None, help="缺省从 session/request id 推导")
    c.add_argument("--max-steps", type=int, default=3)
    c.add_argument("--ttl-minutes", type=int, default=30)
    c.set_defaults(func=cmd_create)

    m = sub.add_parser("materialize", help="生成 Runtime 接入材料与 Worker Prompt")
    m.add_argument("run_dir")
    m.add_argument("--runtime", choices=["codex", "dsh", "all"], default="all")
    m.set_defaults(func=cmd_materialize)

    s = sub.add_parser("status", help="查看 run 状态")
    s.add_argument("run_dir")
    s.set_defaults(func=cmd_status)

    t = sub.add_parser("stop", help="写入 STOP 停止信号")
    t.add_argument("run_dir")
    t.set_defaults(func=cmd_stop)

    a = sub.add_parser("activate", help="激活本 Run（写 active-run 指针）")
    a.add_argument("run_dir")
    a.add_argument("--force", action="store_true", help="覆盖其它已激活 Run")
    a.set_defaults(func=cmd_activate)

    d = sub.add_parser("deactivate", help="撤销 active-run 指针")
    d.set_defaults(func=cmd_deactivate)

    x = sub.add_parser("cleanup", help="删除临时 hook / marker / 运行状态")
    x.add_argument("run_dir")
    x.add_argument("--yes", action="store_true")
    x.set_defaults(func=cmd_cleanup)
    return p


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()