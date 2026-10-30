#!/usr/bin/env python3
"""PAOS V1.1 -> V1.2 one-time converter (Stage 1, isolated dry-run).

The output is an incremental patch, not a complete Project Vault or
Workstation. Freeze/copy the complete target first, then overlay the output
files by relative path onto that copy; never replace the target with the
output directory. For rollback, restore each original TODO byte-for-byte from
TODO.pre-v12.md, then remove only backup/generated files absent from the frozen
copy. Preserve all pre-existing data.

The converter reads a formal read-only Project snapshot (project JSON + Project
Vault Workstations) and writes an isolated output directory. It never mutates
the input snapshot and never touches the production Store, Runtime, Wake or CAT
binding.

Conservation:
- the project JSON is copied byte-for-byte (sha256 before == after);
- Work/Artifact/Request/Ledger/receipt/close evidence are preserved and
  reported by count, never rewritten;
- each agent's original TODO source is preserved next to the new current file.

Current responsibility comes only from live Project facts (the Agent's current
Work/mission), never from the historical TODO list. When no current Work exists
the current section says so explicitly.

TODO output matches the frozen V1.2 v2 contract (`paos-todo/v2`): exactly one
`## 当前` and one `## 待办`, with non-empty 目标/阶段/下一步. A file that is
already valid v2 is left untouched (idempotent).

Usage:
  python scripts/paos_v12_convert.py --project-json <snapshot>/project.json \
      --vault <snapshot/ProjectRoot> --out <isolated-dir> [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

V12_TODO_SCHEMA = "paos-todo/v2"
V12_CONVERT_SCHEMA = "paos-v12-convert-report/v1"
ORIGINAL_SUFFIX = "TODO.pre-v12.md"

FALLBACK_NEXT = "读取当前 Work 与 Mailbox，明确本轮下一步。"
UNSOURCED = "（原 TODO 未单独标注，见当前事实）"


class ConvertProblem(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _goal(project: dict[str, Any], session: dict[str, Any], work: dict[str, Any]) -> str:
    mission = session.get("mission") if isinstance(session.get("mission"), dict) else {}
    candidates = (
        _single_line(mission.get("objective")),
        _single_line(work.get("objective")),
        _single_line(work.get("title")),
    )
    for text in candidates:
        if text:
            return text
    return FALLBACK_NEXT


def _work_index(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["id"]: item
        for item in project.get("work_items", [])
        if isinstance(item, dict) and item.get("id")
    }


def render_v2_todo(
    *,
    project_id: str,
    agent_id: str,
    work_id: str,
    goal: str,
    stage: str = "未开始",
    next_text: str = "",
    waiting: str = "无",
    status_note: str = "",
    extra_current_lines: list[str] | None = None,
    open_tasks: list[dict[str, str]] | None = None,
) -> str:
    work_label = work_id or "（尚未绑定当前 Work）"
    goal = goal or FALLBACK_NEXT
    stage = stage or UNSOURCED
    next_text = next_text or goal
    waiting = waiting or UNSOURCED
    lines = [
        "---",
        f"schema: {V12_TODO_SCHEMA}",
        f"project_id: {project_id}",
        f"agent_id: {agent_id}",
        "---",
        "",
        "# 当前工作",
        "",
        "## 当前",
        f"Work：{work_label}",
        f"目标：{goal}",
        f"阶段：{stage}",
        f"下一步：{next_text}",
        f"等待：{waiting}",
        "成果：无",
        "在途：无",
    ]
    if status_note:
        lines.append(f"状态：{status_note}")
    if extra_current_lines:
        lines.append("")
        lines.append("### 当前事实（原 TODO 转换保留）")
        lines.extend(extra_current_lines)
    lines += ["", "## 待办", ""]
    # None -> default single task (standalone); [] -> intentionally empty.
    tasks = open_tasks if open_tasks is not None else [{"id": "T-001", "title": next_text}]
    for task in tasks:
        title = task["title"]
        if task.get("progress"):
            title = f"{title}（原为 [~]：需本人确认进行中或已撤销）"
        lines.append(f"- [ ] {task['id']} {title}")
        lines.append("  完成方式：（完成后填写）")
        lines.append("  结果：（完成后填写）")
    lines += ["", "## 继续阅读", "- ENTRY.md", "- mailbox/", ""]
    return "\n".join(lines)


_CURRENT_HEADING_PREFIXES = ("当前", "状态摘要")
# Checkbox: open [ ], done [x]/[X], ambiguous in-progress/retracted [~].
_TASK_RE = re.compile(
    r"^- \[([ xX~])\]\s+\**([A-Za-z0-9][A-Za-z0-9._-]*)\**\s+(.+?)\s*$"
)
# Retired credential formats named by the contract. Deliberately NOT the plain
# word "cycle": lifecycle/recycle/"release cycle"/"产品开发 cycle 评审" are
# business prose and must be left untouched.
RETIRED_MARKERS = (
    "execution claim",
    "execution_cycle",
    "context pack",
    "context-pack",
    "context_pack",
    "paos_runtime_instance_id",
    "write_owner",
)
_RETIRED_PAREN_RE = re.compile(
    r"[（(][^）)]*(?:"
    + "|".join(re.escape(m) for m in RETIRED_MARKERS)
    + r")[^）)]*[）)]",
    re.IGNORECASE,
)
_SEGMENT_SPLIT_RE = re.compile(r"(?<=[；;。，,])")


def _first_label(lines: list[str], label: str) -> str:
    """Read a ``label（optional annotation）：value`` from the current scope only."""
    word = label[:-1] if label.endswith("：") else label
    pattern = re.compile(r"^" + re.escape(word) + r"(?:（[^）]*）)?\s*：\s*(.*)$")
    for raw in lines:
        stripped = raw.strip().lstrip("-*").strip().replace("**", "")
        match = pattern.match(stripped)
        if match:
            return match.group(1).strip()
    return ""


def _section_lines(lines: list[str], index: int) -> list[str]:
    """Lines of one section, stopping at the next level-1/2 heading or a rule.

    Stopping at ``# `` / ``## `` / ``---`` keeps a following history section out
    of the current facts.
    """
    collected: list[str] = []
    for raw in lines[index:]:
        if raw.startswith("## ") or raw.startswith("# "):
            break
        if raw.strip() == "---":
            break
        # Any explicit history-intro line ends the current section, even with a
        # bullet/quote prefix.
        if "历史记录" in raw:
            break
        collected.append(raw.rstrip())
    return collected


def strip_retired_segments(line: str) -> str:
    """Remove retired claim/Cycle/Context-Pack clauses, keeping other clauses.

    Stage 2 removed execution claim / Context Pack / Cycle as normal entry or
    continuation steps. Only the retired clauses of a current-fact line are
    removed (the whole line is kept when it also carries business facts); the
    original line remains in the byte-exact ``TODO.pre-v12.md``.
    """
    low = line.lower()
    if not any(marker in low for marker in RETIRED_MARKERS):
        return line
    line = _RETIRED_PAREN_RE.sub("", line)
    kept = [
        segment
        for segment in _SEGMENT_SPLIT_RE.split(line)
        if not any(marker in segment.lower() for marker in RETIRED_MARKERS)
    ]
    return "".join(kept).strip()


def extract_current_facts(text: str) -> list[str]:
    """Return the original TODO's current-section facts (not history).

    Recognizes ``## 当前`` / ``## 当前区…`` / ``## 状态摘要``; falls back to the
    prose between the first ``# `` heading and the next ``## `` heading. Also
    appends an explicit ``## 等待`` section when present. Retired
    claim/Cycle/Context-Pack clauses are stripped clause-by-clause so business
    facts on the same line survive.
    """
    lines = text.splitlines()
    facts: list[str] = []
    start: int | None = None
    for i, raw in enumerate(lines):
        if raw.startswith("## ") and raw[3:].strip().startswith(_CURRENT_HEADING_PREFIXES):
            start = i + 1
            break
    if start is None:
        for i, raw in enumerate(lines):
            if raw.startswith("# "):
                start = i + 1
                break
    if start is not None:
        facts.extend(_section_lines(lines, start))
    for i, raw in enumerate(lines):
        if raw.startswith("## ") and raw[3:].strip() == "等待":
            facts.extend(_section_lines(lines, i + 1))
            break
    while facts and not facts[0].strip():
        facts.pop(0)
    while facts and not facts[-1].strip():
        facts.pop()
    cleaned = [strip_retired_segments(line) for line in facts]
    return [line for line in cleaned if line.strip()]


def extract_open_tasks(text: str) -> list[dict[str, Any]]:
    """Unchecked ``[ ]`` and ambiguous ``[~]`` tasks under ``## 待办``.

    ``[x]``/``[X]`` are completed and skipped. ``[~]`` is kept with
    ``progress=True`` because it can mean either in-progress or retracted; the
    caller must flag it for the person to calibrate rather than drop or invent.
    """
    lines = text.splitlines()
    tasks: list[dict[str, Any]] = []
    in_todo = False
    for raw in lines:
        if raw.startswith("## "):
            in_todo = raw[3:].strip().startswith("待办")
            continue
        if not in_todo:
            continue
        match = _TASK_RE.match(raw.strip())
        if not match:
            continue
        box, task_id, title = match.group(1), match.group(2), match.group(3).strip()
        if box.lower() == "x":
            continue
        tasks.append({"id": task_id, "title": title, "progress": box == "~"})
    return tasks


def front_matter_schema(text: str) -> str:
    """Return the declared ``schema:`` value from TODO front matter, else ''."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        if ":" in raw:
            key, value = raw.split(":", 1)
            if key.strip() == "schema":
                return value.strip()
    return ""


def is_valid_v2(text: str) -> bool:
    """Minimal fail-closed check matching the frozen v2 parser contract."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    meta: dict[str, str] = {}
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        if ":" in raw:
            key, value = raw.split(":", 1)
            meta[key.strip()] = value.strip()
    if meta.get("schema") != V12_TODO_SCHEMA:
        return False
    sections: dict[str, list[str]] = {}
    active: str | None = None
    for raw in lines:
        if raw.startswith("## "):
            active = raw[3:].strip()
            sections.setdefault(active, [])
            continue
        if active is not None:
            sections[active].append(raw)
    if len(sections.get("当前", [])) == 0 or "当前" not in sections:
        return False
    if "待办" not in sections:
        return False
    # exactly one of each heading
    headings = [raw[3:].strip() for raw in lines if raw.startswith("## ")]
    if headings.count("当前") != 1 or headings.count("待办") != 1:
        return False
    current = sections["当前"]
    required = {"目标：": False, "阶段：": False, "下一步：": False}
    for raw in current:
        for label in required:
            if raw.strip().startswith(label) and raw.strip()[len(label):].strip():
                required[label] = True
    return all(required.values())


PENDING_ACK_WAITING = "本人完成首次入场 Ack（未完成前不开始实质工作）"
PENDING_ACK_FACT = (
    "本人首次 Ack 未完成：先由本人完成入场；原 TODO 中依赖旧运行凭据 / "
    "Cycle 的历史步骤在 Stage 2 不再适用（原文见 TODO.pre-v12.md）。"
)
PENDING_ACK_TASK = (
    "本人完成首次入场 Ack（pending_ack → active）；入口不再需要旧运行凭据或 Cycle。"
)
CALIBRATE_NEXT = (
    "需本人校准：对照 live PAOS Work 明确当前下一步（旧 TODO 当前片段缺失或与 live 不一致）"
)


def _header_lines(text: str) -> list[str]:
    """Lines between the first ``# `` heading and the next ``## `` heading."""
    lines = text.splitlines()
    start: int | None = None
    for i, raw in enumerate(lines):
        if raw.startswith("# "):
            start = i + 1
            break
    if start is None:
        return []
    collected: list[str] = []
    for raw in lines[start:]:
        if raw.startswith("## "):
            break
        collected.append(raw.rstrip())
    return collected


def convert_todo(
    text: str,
    *,
    project_id: str,
    agent_id: str,
    work_id: str,
    goal: str,
    status_note: str = "",
    pending_ack: bool = False,
) -> tuple[str, str | None, bool]:
    """Return ``(status, new_text)``.

    status:
    - ``already_v2``: a valid v2 TODO; caller preserves its bytes unchanged.
    - ``converted``:   a v1/unknown TODO converted to a fresh v2 current section.
    - ``invalid_v2``:  declares ``paos-todo/v2`` but is structurally invalid.
      It must fail closed and be preserved, never silently rebuilt as v1.
    """
    if is_valid_v2(text):
        return "already_v2", text, False
    if front_matter_schema(text) == V12_TODO_SCHEMA:
        return "invalid_v2", None, False
    header = _header_lines(text)
    facts = extract_current_facts(text)
    open_tasks = extract_open_tasks(text)
    # Read current labels ONLY from the header goal block and the current
    # section. Never scan the whole file: a v1 TODO often mixes old
    # "当前/下一步" fragments into history, which would leak a stale
    # "Session closed / waiting for reassignment" into the fresh current.
    scope = [*header, *facts]
    doc_goal = _first_label(scope, "目标：") or goal
    src_stage = _first_label(scope, "阶段：")
    src_next = _first_label(scope, "下一步：")
    src_wait = _first_label(scope, "等待：")
    # Calibration is required when the next action cannot be trusted. A missing
    # stage is only marked unsourced, not a stop.
    needs_calibration = not src_next
    stage = src_stage or UNSOURCED
    next_text = src_next or (CALIBRATE_NEXT if needs_calibration else doc_goal)
    waiting = src_wait or UNSOURCED
    definite = [t for t in open_tasks if not t.get("progress")]
    ambiguous = [t for t in open_tasks if t.get("progress")]
    if ambiguous:
        # [~] can mean in-progress or retracted. Keep the real ids/titles, but
        # put them in a non-actionable calibration area (not `## 待办`) so a
        # retracted item never re-becomes a current task.
        needs_calibration = True
        facts = [
            *facts,
            "",
            "需本人校准（[~] 非当前指令；进行中/已撤销无法可靠区分，原文见 TODO.pre-v12.md）：",
        ]
        for item in ambiguous:
            facts.append(f"- [~] {item['id']} {item['title']}")
    elif needs_calibration:
        facts = [*facts, "", f"校准提示：{CALIBRATE_NEXT}"]
    # Do NOT synthesize an open task from the 下一步 prose. `## 待办` lists only
    # real definite unfinished items and may stay empty.
    open_tasks = definite
    if pending_ack:
        # The Agent has not legally entered yet. Do not carry old claim/Cycle
        # instructions forward as active tasks; require the person's first Ack.
        waiting = PENDING_ACK_WAITING
        open_tasks = [{"id": "T-001", "title": PENDING_ACK_TASK, "progress": False}]
        facts = [*facts, "", PENDING_ACK_FACT]
        needs_calibration = False
    return "converted", render_v2_todo(
        project_id=project_id,
        agent_id=agent_id,
        work_id=work_id,
        goal=doc_goal,
        stage=stage,
        next_text=next_text,
        waiting=waiting,
        status_note=status_note,
        extra_current_lines=facts,
        open_tasks=open_tasks,
    ), needs_calibration


def convert_standalone(
    *,
    workstation: Path,
    out: Path,
    agent_id: str,
    project_id: str = "",
    objective: str = "",
    stage: str = "",
    next_text: str = "",
) -> dict[str, Any]:
    """Convert one installation-level workstation with no PAOS Project/Session.

    Current responsibility must be supplied explicitly (Human/Rooter). Nothing
    is inferred from the historical TODO list.
    """
    if not agent_id:
        raise ConvertProblem("standalone_agent_required", "standalone 模式需要 --agent-id。")
    if not objective:
        raise ConvertProblem(
            "standalone_objective_required",
            "standalone 模式需要显式 --objective（不从历史推断当前责任）。",
        )
    src_todo = workstation / "TODO.md"
    if not src_todo.is_file():
        raise ConvertProblem("standalone_todo_missing", f"工位缺少 TODO.md：{src_todo}")
    text = src_todo.read_text(encoding="utf-8")
    status, _new_text, _needs_calibration = convert_todo(
        text, project_id=project_id, agent_id=agent_id, work_id="", goal=objective
    )
    out.mkdir(parents=True, exist_ok=True)
    agent_report: dict[str, Any] = {
        "agent_id": agent_id,
        "project_id": project_id,
        "standalone": True,
        "todo_status": status,
    }
    errors: list[dict[str, Any]] = []
    if status == "converted":
        shutil.copyfile(src_todo, out / ORIGINAL_SUFFIX)  # byte-exact
        (out / "TODO.md").write_text(
            render_v2_todo(
                project_id=project_id,
                agent_id=agent_id,
                work_id="",
                goal=objective,
                stage=stage,
                next_text=next_text,
                extra_current_lines=extract_current_facts(text),
                open_tasks=extract_open_tasks(text),
            ),
            encoding="utf-8",
        )
        agent_report["original_saved_as"] = str(out / ORIGINAL_SUFFIX)
    elif status == "already_v2":
        (out / "TODO.md").write_bytes(src_todo.read_bytes())
    else:
        shutil.copyfile(src_todo, out / ORIGINAL_SUFFIX)
        agent_report["original_saved_as"] = str(out / ORIGINAL_SUFFIX)
        agent_report["error"] = "声明 paos-todo/v2 但结构无效；保留原文，不重建。"
        errors.append({"agent_id": agent_id, "error_code": "todo_v2_invalid", "detail": agent_report["error"]})
    dst_todo = out / "TODO.md"
    agent_report["todo_output_sha256"] = _sha256(dst_todo) if dst_todo.is_file() else ""
    return {
        "schema": V12_CONVERT_SCHEMA,
        "project_id": project_id,
        "mode": "standalone",
        "conservation": {"project_json_unchanged": None, "counts": {}},
        "agents": [agent_report],
        "errors": errors,
        "retired_working_memory_artifacts": [],
        "notes": [
            "Standalone workstation: original TODO preserved as TODO.pre-v12.md.",
            "Current responsibility was supplied explicitly, not inferred from history.",
        ],
    }


def load_project(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConvertProblem("project_snapshot_missing", f"Project 快照不存在：{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConvertProblem(
            "project_snapshot_invalid", f"Project 快照无法解析：{path}", {"cause": str(exc)}
        ) from exc
    if not isinstance(value, dict) or not value.get("id"):
        raise ConvertProblem("project_snapshot_invalid", f"Project 快照缺少 id：{path}")
    return value


def convert_snapshot(
    *,
    project_json: Path,
    vault: Path,
    out: Path,
) -> dict[str, Any]:
    project = load_project(project_json)
    project_id = str(project.get("id"))
    out.mkdir(parents=True, exist_ok=True)

    # Conservation: copy the project snapshot unchanged.
    out_project = out / "project.json"
    shutil.copyfile(project_json, out_project)
    before_sha = _sha256(project_json)
    after_sha = _sha256(out_project)

    works = _work_index(project)
    sessions = [s for s in project.get("sessions", []) if isinstance(s, dict)]
    agents: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for session in sessions:
        agent_id = str(session.get("id") or "")
        if not agent_id:
            continue
        work_id = str(session.get("current_work_item_id") or "")
        work = works.get(work_id, {})
        goal = _goal(project, session, work)
        src_dir = vault / "Workstations" / agent_id
        src_todo = src_dir / "TODO.md"
        agent_report: dict[str, Any] = {
            "agent_id": agent_id,
            "work_id": work_id,
            "todo_present": src_todo.is_file(),
        }
        if src_todo.is_file():
            text = src_todo.read_text(encoding="utf-8")
            session_status = str(session.get("status") or "")
            if session_status == "pending_ack":
                status_note = (
                    "pending_ack（尚未完成合法入场；需本人首次 Ack，转换结果不能替代）"
                )
            elif session_status:
                status_note = f"{session_status}（PAOS 当前状态）"
            else:
                status_note = ""
            status, new_text, needs_calibration = convert_todo(
                text,
                project_id=project_id,
                agent_id=agent_id,
                work_id=work_id,
                goal=goal,
                status_note=status_note,
                pending_ack=session_status == "pending_ack",
            )
            agent_report["todo_status"] = status
            if needs_calibration:
                agent_report["needs_calibration"] = True
            dst_dir = out / "Workstations" / agent_id
            dst_dir.mkdir(parents=True, exist_ok=True)
            if status == "converted":
                shutil.copyfile(src_todo, dst_dir / ORIGINAL_SUFFIX)  # byte-exact
                (dst_dir / "TODO.md").write_text(new_text, encoding="utf-8")
                agent_report["original_saved_as"] = str(dst_dir / ORIGINAL_SUFFIX)
            elif status == "already_v2":
                # Preserve the valid v2 bytes into the isolated target verbatim.
                (dst_dir / "TODO.md").write_bytes(src_todo.read_bytes())
            else:  # invalid_v2: fail closed, keep the original, never rebuild.
                shutil.copyfile(src_todo, dst_dir / ORIGINAL_SUFFIX)
                agent_report["original_saved_as"] = str(dst_dir / ORIGINAL_SUFFIX)
                agent_report["error"] = (
                    "声明 paos-todo/v2 但结构无效；保留原文，不按 v1 重建当前区。"
                )
                errors.append(
                    {
                        "agent_id": agent_id,
                        "error_code": "todo_v2_invalid",
                        "detail": agent_report["error"],
                    }
                )
            dst_todo = dst_dir / "TODO.md"
            agent_report["todo_output_sha256"] = (
                _sha256(dst_todo) if dst_todo.is_file() else ""
            )
            agent_report["todo_output_bytes_exact"] = (
                dst_todo.is_file() and dst_todo.read_bytes() == src_todo.read_bytes()
            )
        agents.append(agent_report)

    wm_artifacts = [
        {"id": a.get("id"), "path": a.get("path"), "source_session_id": a.get("source_session_id")}
        for a in project.get("artifacts", [])
        if isinstance(a, dict) and a.get("type") == "agent_working_memory"
    ]

    return {
        "schema": V12_CONVERT_SCHEMA,
        "project_id": project_id,
        "conservation": {
            "project_json_sha256_before": before_sha,
            "project_json_sha256_after": after_sha,
            "project_json_unchanged": before_sha == after_sha,
            "counts": {
                "work_items": len(project.get("work_items", [])),
                "sessions": len(sessions),
                "artifacts": len(project.get("artifacts", [])),
                "requests": len(project.get("requests", [])),
                "ledger_events": len(project.get("ledger", [])),
                "operation_receipts": len(project.get("operation_receipts", {})),
            },
        },
        "agents": agents,
        "errors": errors,
        "needs_calibration": [
            a["agent_id"] for a in agents if a.get("needs_calibration")
        ],
        "retired_working_memory_artifacts": wm_artifacts,
        "notes": [
            "Current stage/next come only from the header goal block and the current section; history is never scanned.",
            "If the source lacks a trustworthy stage/next, the Agent is listed in needs_calibration and the item says 需本人校准.",
            "Project JSON is copied unchanged; IDs, Ledger, receipts and close evidence are preserved.",
            "Each converted Agent keeps its original TODO as TODO.pre-v12.md next to the new v2 TODO.",
            "Historical agent_working_memory artifacts stay read-only; if a body matters, save it as an ordinary Project file.",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "PAOS V1.1->V1.2 one-time converter. Writes an isolated incremental "
            "patch, not a complete Vault or Workstation; overlay by relative paths onto a full frozen copy."
        )
    )
    p.add_argument("--project-json", help="Read-only Project snapshot JSON (project mode)")
    p.add_argument("--vault", help="Read-only Project Vault root, contains Workstations/ (project mode)")
    p.add_argument(
        "--out",
        required=True,
        help=(
            "Incremental patch directory, not a complete Vault or Workstation. Overlay onto a full frozen copy; "
            "rollback restores original TODO bytes from TODO.pre-v12.md and removes only files created here."
        ),
    )
    p.add_argument("--standalone", action="store_true", help="Convert one installation-level workstation with no PAOS Project")
    p.add_argument("--workstation", help="Standalone workstation dir containing TODO.md")
    p.add_argument("--agent-id", default="", help="Standalone Agent id")
    p.add_argument("--project-id", default="", help="Standalone project/sentinel id (front matter)")
    p.add_argument("--objective", default="", help="Standalone current objective (Human-provided)")
    p.add_argument("--stage", default="", help="Standalone current stage (Human-provided)")
    p.add_argument("--next", dest="next_text", default="", help="Standalone next action (Human-provided)")
    p.add_argument("--json", action="store_true", help="Emit the report as JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.standalone:
            if not args.workstation:
                raise ConvertProblem(
                    "standalone_workstation_required", "standalone 模式需要 --workstation。"
                )
            report = convert_standalone(
                workstation=Path(args.workstation).expanduser(),
                out=Path(args.out).expanduser(),
                agent_id=args.agent_id,
                project_id=args.project_id,
                objective=args.objective,
                stage=args.stage,
                next_text=args.next_text,
            )
        else:
            if not args.project_json or not args.vault:
                raise ConvertProblem(
                    "project_inputs_required",
                    "项目模式需要 --project-json 与 --vault（或用 --standalone）。",
                )
            report = convert_snapshot(
                project_json=Path(args.project_json).expanduser(),
                vault=Path(args.vault).expanduser(),
                out=Path(args.out).expanduser(),
            )
    except ConvertProblem as problem:
        print(json.dumps({"ok": False, "error_code": problem.code, "error": str(problem), "details": problem.details}, ensure_ascii=False))
        return 2
    ok = not report["errors"]
    if args.json:
        print(json.dumps({"ok": ok, **report}, ensure_ascii=False, indent=2))
    else:
        cons = report["conservation"]
        print(f"PAOS V1.2 convert — project {report['project_id']}")
        print(f"  project JSON unchanged: {cons['project_json_unchanged']}")
        for agent in report["agents"]:
            print(f"  {agent['agent_id']}: TODO {agent.get('todo_status', 'absent')}")
        for error in report["errors"]:
            print(f"  ERROR {error['error_code']}: {error['agent_id']} — {error['detail']}")
        if report["retired_working_memory_artifacts"]:
            print(f"  retired Working Memory artifacts: {len(report['retired_working_memory_artifacts'])}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
