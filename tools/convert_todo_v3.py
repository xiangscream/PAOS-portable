#!/usr/bin/env python3
"""One-shot offline TODO v3 -> v4 candidate conversion (NOT a runtime adapter).

No automatic discovery, migration or overwrite.  The original file remains the
source of historical evidence. An explicit --write creates a NEW candidate only.
Unrecognized v3 content is an error, never silently removed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from paos_todo import TodoProblem, parse_todo, render_todo, write_todo  # noqa: E402

OLD_SCHEMA = "paos-todo/v3"
TASK_SCHEMA = "paos-todo-task/v1"
# The original v3 writer's fields; do not make them live v4 state again.
V3_CURRENT_FIELDS = (
    "objective", "approved_scope", "stage", "next_action", "waiting", "results",
    "result_refs", "context_refs", "legacy_source_ref", "inflight", "alignment_ref",
    "input_version", "delivery", "dependencies", "continuation_to", "boundaries",
    "history_ref", "latest_readback", "updated_at",
)
V4_CURRENT_FIELDS = frozenset((
    "objective", "next_action", "waiting", "inflight", "context_refs", "result_refs", "updated_at",
))
V3_TASK_FIELDS = frozenset((
    "schema", "title", "state", "waiting", "result", "artifact_ref",
    "notify_after", "source_refs", "acceptance_refs",
))
_TASK_HEADER = re.compile(r"###\s+([A-Za-z0-9][A-Za-z0-9._-]*)\Z")
_FIELD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)\Z")


class ConversionError(ValueError):
    """A non-lossless conversion is explicitly refused."""


def fail(message: str, line: int | None = None) -> None:
    raise ConversionError(f"第 {line} 行：{message}" if line else message)


def _json_field(raw: str, lineno: int) -> tuple[str, Any]:
    match = _FIELD.fullmatch(raw)
    if not match:
        fail("无法识别的旧格式文本；为避免丢内容，拒绝自动转换", lineno)
    key, source = match.groups()
    try:
        return key, json.loads(source)
    except json.JSONDecodeError as exc:
        fail(f"旧格式字段 {key} 不是有效单行 JSON：{exc.msg}", lineno)
    raise AssertionError("unreachable")


def decode_v3(raw: bytes) -> dict[str, Any]:
    """Strictly decode the *known* v3 writer format, rather than its lax reader.

    The retired v3 reader ignored unrecognized lines and could silently lose
    handwritten notes. A one-time converter must instead stop on any such line.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConversionError("原件必须是 UTF-8；未修改文件") from exc
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        fail("不是可辨认的 v3 frontmatter；未修改文件", 1)
    meta: dict[str, Any] = {}
    at = 1
    for at in range(1, len(lines)):
        line = lines[at]
        if line == "---":
            break
        if not line.strip():
            continue
        key, value = _json_field(line, at + 1)
        if key not in {"schema", "home_kind", "home_id", "project_id"} or key in meta:
            fail(f"重复/未知 frontmatter 字段：{key}", at + 1)
        meta[key] = value
    else:
        fail("frontmatter 未闭合")
    if meta.get("schema") != OLD_SCHEMA:
        fail(f"输入必须是 {OLD_SCHEMA}，不接受混合/新版格式")
    if not isinstance(meta.get("home_kind"), str) or meta["home_kind"] not in {"rooter", "project_agent"}:
        fail("home_kind 无效")
    if not isinstance(meta.get("home_id"), str) or not meta["home_id"].strip():
        fail("home_id 缺失")
    project_id = meta.get("project_id", "")
    if not isinstance(project_id, str):
        fail("project_id 必须是文本")
    if (meta["home_kind"] == "rooter" and project_id) or (meta["home_kind"] == "project_agent" and not project_id):
        fail("Rooter/Project Home 身份与 project_id 不一致")

    current: dict[str, Any] = {}
    tasks: list[dict[str, Any]] = []
    task: dict[str, Any] | None = None
    mode = "start"
    saw_no_tasks = False
    for lineno in range(at + 2, len(lines) + 1):
        line = lines[lineno-1]
        if line == "# Current":
            if mode != "start":
                fail("重复/乱序的 Current 区段", lineno)
            mode = "current"
            continue
        if line == "# Tasks":
            if mode != "current":
                fail("重复/乱序的 Tasks 区段", lineno)
            mode = "tasks"
            continue
        if not line.strip():
            continue
        if mode == "tasks" and line == "_none_":
            if task is not None or tasks or saw_no_tasks:
                fail("_none_ 不能重复或和任务混用", lineno)
            saw_no_tasks = True
            continue
        if mode == "tasks" and (match := _TASK_HEADER.fullmatch(line)):
            if saw_no_tasks:
                fail("_none_ 后不能再添加任务", lineno)
            if task is not None:
                tasks.append(task)
            task = {"id": match.group(1)}
            continue
        key, value = _json_field(line, lineno)
        if mode == "current":
            if key not in V3_CURRENT_FIELDS or key in current:
                fail(f"未知/重复的 Current 字段：{key}", lineno)
            if key in {"result_refs", "context_refs"}:
                if value is not None and (not isinstance(value, list) or not all(isinstance(v, str) for v in value)):
                    fail(f"{key} 必须是字符串数组", lineno)
            elif not isinstance(value, str):
                fail(f"{key} 必须是文本", lineno)
            current[key] = value
        elif mode == "tasks" and task is not None:
            if key not in V3_TASK_FIELDS or key in task:
                fail(f"未知/重复的任务字段：{key}", lineno)
            task[key] = value
        else:
            fail("字段出现在不受支持的位置；防止丢失原始备注", lineno)
    if mode != "tasks":
        fail("缺少 # Current 或 # Tasks 区段")
    if task is not None:
        tasks.append(task)
    if len({t["id"] for t in tasks}) != len(tasks):
        fail("任务 ID 重复")
    for required in ("objective", "next_action"):
        if not isinstance(current.get(required), str) or not current[required].strip():
            fail(f"Current 缺少 {required}")
    if any(task.get("schema", TASK_SCHEMA) != TASK_SCHEMA for task in tasks):
        fail("任务 schema 不匹配")
    return {"home_kind": meta["home_kind"], "home_id": meta["home_id"],
            "project_id": project_id, "current": current, "tasks": tasks}


def build_candidate(original: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    current = original["current"]
    # Any retained v3 field becomes visibly historical, not another live plan.
    extra = {key: current[key] for key in V3_CURRENT_FIELDS
             if key not in V4_CURRENT_FIELDS and current.get(key)}
    pinned = ""
    if extra:
        pinned = "## v3 遗留 Current（待核现行性）\n\n" + "\n".join(
            f"- **{key}:** {value}" for key, value in extra.items())
    mapped_tasks = []
    for task in original["tasks"]:
        mapped_tasks.append({key: value for key, value in task.items() if key != "schema"})
    args: dict[str, Any] = {
        "home_kind": original["home_kind"], "home_id": original["home_id"],
        "project_id": original["project_id"], "pinned": pinned,
        "objective": current["objective"], "next_action": current["next_action"],
        "waiting": current.get("waiting", ""), "inflight": current.get("inflight", ""),
        "context_refs": current.get("context_refs") or [],
        "result_refs": current.get("result_refs") or [],
        "updated_at": current.get("updated_at", ""), "tasks": mapped_tasks,
    }
    try:
        text = render_todo(**args)
        parsed = parse_todo(text)
    except TodoProblem as exc:
        raise ConversionError(f"v4 表达不了该旧工位：{exc}；未写入任何原件") from exc
    for key in V4_CURRENT_FIELDS:
        actual = parsed["current"].get(key)
        before = current.get(key, [] if key in {"result_refs", "context_refs"} else "")
        if before is None and key in {"result_refs", "context_refs"}:
            before = []
        if actual != before:
            fail(f"Current.{key} 转换不完全一致，要求人工核对")
    for key, value in extra.items():
        if f"- **{key}:** {value}" not in parsed["pinned"]:
            fail(f"原 Current.{key} 遗留文字未保留")
    if len(parsed["tasks"]) != len(mapped_tasks):
        fail("任务数量转换后不一致")
    for old, new in zip(mapped_tasks, parsed["tasks"]):
        for key in ("id", "title", "state", "waiting", "result", "artifact_ref",
                    "source_refs", "acceptance_refs", "notify_after"):
            before = old.get(key, [] if key in {"source_refs", "acceptance_refs", "notify_after"} else
                             "todo" if key == "state" else "")
            if before is None and key in {"source_refs", "acceptance_refs", "notify_after"}:
                before = []
            if key == "notify_after":
                before = [{"to": n["to"], "when": n["when"], "source_ref": n.get("source_ref", "")}
                          for n in before]
            if before != new.get(key):
                fail(f"任务 {old['id']} 的 {key} 无法无损转换")
    return text, {"retained_extra_fields": list(extra), "tasks": len(mapped_tasks)}


def prepare(source: Path, output: Path, *, expected_hash: str = "",
            expect_home_id: str = "") -> tuple[bytes, bytes, dict[str, Any]]:
    if source.resolve() == output.resolve():
        fail("输出不能覆盖旧 TODO；请指定单独的候选文件")
    if not source.is_file() or source.is_symlink():
        fail(f"原件不存在或不是普通文件：{source}")
    raw = source.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    if expected_hash and source_sha != expected_hash:
        fail("原件 SHA-256 不匹配，停止转换，重新核对来源")
    old = decode_v3(raw)
    if expect_home_id and old["home_id"] != expect_home_id:
        fail(f"工位身份不匹配：预期 {expect_home_id}，实际 {old['home_id']}")
    candidate, meta = build_candidate(old)
    data = candidate.encode("utf-8")
    result = {"source": str(source), "candidate": str(output), "home_kind": old["home_kind"],
              "home_id": old["home_id"], "project_id": old["project_id"],
              "source_sha256": source_sha, "candidate_sha256": hashlib.sha256(data).hexdigest(),
              **meta, "source_unchanged": True}
    return raw, data, result


def execute(source: Path, output: Path, *, write: bool = False, expected_hash: str = "",
            expect_home_id: str = "") -> dict[str, Any]:
    source, output = Path(source).expanduser().absolute(), Path(output).expanduser().absolute()
    raw, candidate, report = prepare(source, output, expected_hash=expected_hash,
                                     expect_home_id=expect_home_id)
    if write:
        if output.exists() or output.is_symlink():
            fail(f"候选目标已存在，拒绝覆盖：{output}")
        if source.read_bytes() != raw:
            fail("转换期间旧 TODO 有变化，停止写候选")
        try:
            write_todo(output, candidate.decode("utf-8"), create_only=True)
        except TodoProblem as exc:
            raise ConversionError(f"候选写入失败：{exc}") from exc
        if output.read_bytes() != candidate or source.read_bytes() != raw:
            fail("回读内容发生变化，请保留原件并人工核查")
    return {"ok": True, "mode": "candidate_written" if write else "plan_only", **report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="准确的现存 TODO v3 原件")
    parser.add_argument("--output", type=Path, required=True, help="另一个、尚不存在的 v4 候选路径")
    parser.add_argument("--expect-home-id", default="", help="预期的精确 Home ID")
    parser.add_argument("--expected-source-sha256", default="", help="先前回读确认的原件 SHA-256")
    parser.add_argument("--write", action="store_true", help="显式创建候选；不写时只做规划")
    args = parser.parse_args(argv)
    try:
        result = execute(args.source, args.output, write=args.write,
                         expected_hash=args.expected_source_sha256,
                         expect_home_id=args.expect_home_id)
    except (ConversionError, OSError, UnicodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
