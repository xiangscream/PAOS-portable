#!/usr/bin/env python3
"""一次性离线迁移：把 v2 项目状态迁到 workless 的 paos-project/v3。

这是**离线**工具：它不改运行中的服务、不发 HTTP、不自动启动任何 Harness。
它做且只做一件事——把每个真实项目文件从 v2 变成 v3，并保留全部历史事实。

迁移规则
--------
当前事实（按新 schema 重写）：
  - schema: paos-project/v2 -> paos-project/v3
  - sessions[]: 去掉 work_item_ids / current_work_item_id / work_released
  - requests[]: 去掉 target_work_item_id
  - artifacts[]: 去掉 work_item_ids

退役对象（原样搬运，不改写、不丢失）：
  - work_items[]           -> archived_work_items[]
  - work_suggestions[]     -> archived_work_suggestions[]
  旧 Work 对象里的每个字段逐字保留；归档只做"换位置"，不做"再解释"。

证据（只追加，绝不改写）：
  - ledger[]、operation_receipts{}、sessions[].close_result、
    cycles[].close_result / close_result_history 全部原样保留。
  - 只向 ledger **追加**一条 project.migrated 说明性事件；旧事件一条不动。
  - 历史 Cycle 里的 work_item_id 作为惰性历史字段留在原地，不删不改。

工位 Home（S032 的接口，直接 import，不私定第二份 TODO schema）
------------------------------------------------------------
  项目 JSON 之外，每个 Agent 的 Workstation Home 也要退 Work：Home 的 `TODO.md`
  当前事实里还有 `current_work`。这一步**不自己实现**，直接调用
  `paos_v13_convert.plan_v3_home_convergence` / `apply_v3_home_convergence`
  （面向已存在的 v3 Home，只摘 `current_work`，Notice／Mail 不重建）；回退用
  `--rollback-home`（吃 manifest，幂等 replay 由接口负责）。

  Home 按磁盘枚举（`Workstations/*` 加登记的 Rooter Home），逐个判成四态：
  `convertible`／`already_converged`／`absent`／`blocked_interface`；
  `blocked_interface` 具名报出，**不静默跳过**。

安全
----
  - 默认 dry-run；必须显式 --apply 才写盘。
  - **规划完成、首次写入之前**就判阻塞：只要规划期出现 `blocked_interface`，
    `--apply` 整体中止（退出码 3），Project／Current／Notice 一个都不动。
    先改治理事实、再发现 Home 收敛不了，不是"单次安装迁移"。
  - 写盘前：对**所有**目标文件先做一遍解析 + 转换 + 校验；任一文件有问题就
    整体中止，不写任何文件（不留半迁移状态）。
  - 写盘时：先把 before-state 原样备份到 <root>/backups/workless-migration-<ts>/，
    再用原子替换写新文件。
  - 幂等：已是 v3 的项目文件跳过；重复运行不产生第二次迁移事件。
  - Home 的回退：`--rollback-home <project-root>` 按 manifest 恢复（保留
    cutover 之后的业务事实，不删产物）。
  - `--skip-homes` 是**明确的"只迁项目文件"**选择，不是"自动跳过有问题的
    Home"：它让 Home 轴整体不参与本次运行。

用法
----
    python scripts/migrate_workless_installation.py --root <registry-root>                 # dry-run
    python scripts/migrate_workless_installation.py --root <registry-root> --apply         # 真正迁移
    python scripts/migrate_workless_installation.py --root <registry-root> --apply --only 3002
    python scripts/migrate_workless_installation.py --root <registry-root> --apply --skip-homes
    python scripts/migrate_workless_installation.py --rollback-home <project-root>
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE = REPO_ROOT / "attention-dashboard-v1-static"
SCRIPTS = REPO_ROOT / "scripts"
for _extra in (CORE, SCRIPTS):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from project_domain import (  # noqa: E402
    ARCHIVED_WORK_ITEMS_KEY,
    ARCHIVED_WORK_SUGGESTIONS_KEY,
    PROJECT_SCHEMA,
)
from project_schema import validate_project  # noqa: E402
from project_store import ProjectStore  # noqa: E402

# S032 交付的最终 Home 转换接口：同树同版直接 import，不另立第二份 TODO schema。
from paos_home import project_agent_home  # noqa: E402
from paos_installation import load_installation_descriptor, resolve_installation_path  # noqa: E402
from paos_mail import MailProblem  # noqa: E402
from paos_notice import NoticeProblem  # noqa: E402
from paos_todo_v3 import TodoV3Problem, parse_todo_v3  # noqa: E402
from paos_v13_convert import (  # noqa: E402
    V13ConversionProblem,
    apply_project_home_conversion,
    rollback_home_conversion,
)
from paos_workstation import WorkstationProblem, parse_todo_markdown  # noqa: E402

# S032 固定版（042e187 → b093436 → S010 9682544）才有的 v3 Home 收敛接口。本片与
# S032 按固定版本配对；名字不在就是这棵树还没配对，如实报阻塞——绝不自己写一个
# "看起来一样"的收敛器，那是静默的错误输出。
try:
    from paos_v13_convert import (  # noqa: E402
        apply_v3_home_convergence,
        plan_v3_home_convergence,
    )
except ImportError:  # pragma: no cover - 旧接口树
    apply_v3_home_convergence = None
    plan_v3_home_convergence = None

# Home 转换的失败类型：与 paos_v13_convert.converter_main 同一组，保证任何一类
# 都以可读的迁移错误结束，而不是裸抛堆栈。
HOME_PROBLEMS = (
    V13ConversionProblem,
    NoticeProblem,
    TodoV3Problem,
    WorkstationProblem,
    MailProblem,
)

LEGACY_SCHEMA = "paos-project/v2"
MIGRATION_EVENT = "project.migrated"
MIGRATION_OPERATION_PREFIX = "op-migrate-workless-"

# Home 转换的 manifest 名。必须**跨运行稳定**：paos_v13_convert 的幂等 replay 以
# manifest 路径为键，换名字就等于把已转换的 Home 当新活干。
HOME_MANIFEST_ID = "workless-migration"

# 每条记录里"当前事实"要摘掉的 Work 字段；证据字段不在此列。
SESSION_DROP = ("work_item_ids", "current_work_item_id", "work_released")
REQUEST_DROP = ("target_work_item_id",)
ARTIFACT_DROP = ("work_item_ids",)

# Home 的两条轴。真实安装的 Home 早已是 paos-todo/v3（10-06 那次 V1.3 发布转的），
# 所以现在的重点是 v3 收敛：只摘 current_work，Notice/Mail 不重建。
AXIS_V2 = "v2_entry"
AXIS_V3 = "v3_convergence"
V2_TODO_SCHEMA = "paos-todo/v2"
V3_TODO_SCHEMA = "paos-todo/v3"
V3_CONVERGE_DIR = "v3-converge"

HOME_CONVERTIBLE = "convertible"
HOME_ALREADY_CONVERGED = "already_converged"
HOME_ABSENT = "absent"
HOME_BLOCKED_INTERFACE = "blocked_interface"
HOME_STATES = (
    HOME_CONVERTIBLE,
    HOME_ALREADY_CONVERGED,
    HOME_ABSENT,
    HOME_BLOCKED_INTERFACE,
)


class MigrationError(RuntimeError):
    """迁移无法安全继续；消息面向人，指出文件与原因。"""


class MigrationBlocked(MigrationError):
    """规划期就已知某些 Home 收敛不了；在第一次写入之前整体中止。

    `blocked` 是逐个阻塞 Home 的判定（含 `home_kind`／`home_id`／`reason`），
    调用方可以直接把它回报给作者，不需要再从日志里猜是哪一个 Home。
    """

    def __init__(self, message: str, *, blocked: list[dict]):
        super().__init__(message)
        self.blocked = list(blocked)


def _blocked_message(blocked: list[dict]) -> str:
    parts = [
        f"{item.get('home_kind')}/{item.get('home_id') or '-'}：{item.get('reason', '')}"
        for item in blocked
    ]
    return (
        f"规划发现 {len(blocked)} 个 Home 无法收敛，已在写入前整体中止"
        f"（Project／Current／Notice 均未写）：" + "；".join(parts)
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".migrate-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _drop_keys(record: dict, keys) -> list[str]:
    removed = []
    for key in keys:
        if key in record:
            record.pop(key)
            removed.append(key)
    return removed


def plan_project(raw_text: str, path: Path) -> dict:
    """解析 + 转换 + 校验一个项目；返回计划（不改盘、不共享输入对象）。"""
    try:
        project = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise MigrationError(f"{path.name}: 不是合法 JSON：{error}") from error
    if not isinstance(project, dict):
        raise MigrationError(f"{path.name}: 顶层不是对象。")

    schema = project.get("schema")
    if schema == PROJECT_SCHEMA:
        # 计划里始终带上当前 project 字典：项目文件可以跳过，但 Workstation Home
        # 转换是另一条轴，重跑时仍要按当前状态推进。
        return {
            "path": path,
            "skip": True,
            "reason": "已是当前 schema",
            "project": project,
            "counts": {},
        }
    if schema != LEGACY_SCHEMA:
        raise MigrationError(
            f"{path.name}: schema 是 {schema!r}，既不是 {LEGACY_SCHEMA} 也不是 {PROJECT_SCHEMA}；"
            "拒绝猜测，请人工确认。"
        )

    updated = copy.deepcopy(project)
    project_id = str(updated.get("id") or "")
    counts = {"archived_work_items": 0, "archived_work_suggestions": 0, "sessions": 0, "requests": 0, "artifacts": 0}

    # 1) 退役对象：逐字搬到惰性归档键
    for src_key, dst_key in (
        ("work_items", ARCHIVED_WORK_ITEMS_KEY),
        ("work_suggestions", ARCHIVED_WORK_SUGGESTIONS_KEY),
    ):
        if src_key in updated:
            items = updated.pop(src_key)
            if not isinstance(items, list):
                raise MigrationError(f"{path.name}: {src_key} 不是数组，拒绝迁移。")
            existing = updated.get(dst_key)
            if isinstance(existing, list) and existing:
                raise MigrationError(
                    f"{path.name}: 已存在非空 {dst_key}，但仍有 {src_key}；状态矛盾，人工确认后再迁移。"
                )
            if items:
                updated[dst_key] = items
            counts[dst_key] = len(items)

    # 2) 当前事实：摘掉 Work 绑定
    for session in updated.get("sessions", []) or []:
        if isinstance(session, dict):
            if _drop_keys(session, SESSION_DROP):
                counts["sessions"] += 1
    for request in updated.get("requests", []) or []:
        if isinstance(request, dict):
            if _drop_keys(request, REQUEST_DROP):
                counts["requests"] += 1
    for artifact in updated.get("artifacts", []) or []:
        if isinstance(artifact, dict):
            if _drop_keys(artifact, ARTIFACT_DROP):
                counts["artifacts"] += 1

    # 3) 历史 Cycle 的 work_item_id 保持原样（惰性历史字段）。
    # 4) 证据集合原样；只追加一条说明性事件。
    ledger = updated.get("ledger")
    if not isinstance(ledger, list):
        raise MigrationError(f"{path.name}: ledger 不是数组，拒绝迁移。")
    receipts = updated.get("operation_receipts")
    if not isinstance(receipts, dict):
        raise MigrationError(f"{path.name}: operation_receipts 不是对象，拒绝迁移。")

    base_revision = int(updated.get("revision") or 0)
    operation_id = f"{MIGRATION_OPERATION_PREFIX}{uuid.uuid4().hex[:16]}"
    event_id = ProjectStore.allocate_id(updated, "e", None, project_id) if project_id else ""
    event = {
        "event_id": event_id,
        "event_type": MIGRATION_EVENT,
        "operation_id": operation_id,
        "base_revision": base_revision,
        "revision": base_revision + 1,
        "summary": (
            "一次离线迁移到 workless 状态：旧 Work 与 Work 建议转为只读历史归档，"
            "Session/Request/Artifact 的 Work 绑定移除；Ledger 与回执未改写。"
        ),
        "occurred_at": _now(),
        "allocated_ids": [event_id] if event_id else [],
        "changes": [
            {"path": "/schema", "before": LEGACY_SCHEMA, "after": PROJECT_SCHEMA},
            {"path": f"/{ARCHIVED_WORK_ITEMS_KEY}", "before": None, "after": "<moved>"},
        ],
        "details": {
            "migration": "workless",
            "counts": counts,
            "evidence_untouched": True,
        },
    }
    updated["ledger"] = list(ledger) + [event]
    updated["schema"] = PROJECT_SCHEMA
    updated["revision"] = base_revision + 1
    updated["updated_at"] = _now()

    # 5) 迁移结果必须过当前全量校验
    try:
        validate_project(updated)
    except Exception as error:  # ValidationError 及运行时错误都算计划失败
        raise MigrationError(f"{path.name}: 迁移结果未通过当前校验：{error}") from error

    return {
        "path": path,
        "skip": False,
        "project": updated,
        "before": project,
        "counts": counts,
        "project_id": project_id,
        "event_id": event_id,
    }


def _conservation(before: dict, after: dict) -> list[str]:
    """数量守恒与证据不变的自检；返回问题清单（空 = 通过）。"""
    problems = []
    if len(before.get("ledger", [])) + 1 != len(after.get("ledger", [])):
        problems.append("ledger 条数不等于原条数 + 1（只应追加一条）")
    if len(before.get("operation_receipts", {})) != len(after.get("operation_receipts", {})):
        problems.append("operation_receipts 条数发生变化（证据只能原样保留）")
    archived = len(after.get(ARCHIVED_WORK_ITEMS_KEY, []) or [])
    if archived != len(before.get("work_items", []) or []):
        problems.append(
            f"{ARCHIVED_WORK_ITEMS_KEY} 数量 {archived} != 原 work_items 数量 {len(before.get('work_items', []) or [])}"
        )
    b_sessions = {s.get("id"): s for s in before.get("sessions", []) or [] if isinstance(s, dict)}
    a_sessions = {s.get("id"): s for s in after.get("sessions", []) or [] if isinstance(s, dict)}
    if set(b_sessions) != set(a_sessions):
        problems.append("Session 集合发生变化")
    for sid, b_s in b_sessions.items():
        a_s = a_sessions.get(sid) or {}
        if b_s.get("close_result") != a_s.get("close_result"):
            problems.append(f"Session {sid} 的 close_result 被改写")
        b_cycles = b_s.get("cycles") or []
        a_cycles = a_s.get("cycles") or []
        if len(b_cycles) != len(a_cycles):
            problems.append(f"Session {sid} 的 Cycle 数量发生变化")
        for b_c, a_c in zip(b_cycles, a_cycles):
            if b_c.get("work_item_id") != a_c.get("work_item_id"):
                problems.append(f"Session {sid} 的历史 Cycle work_item_id 被改写")
            if b_c.get("close_result") != a_c.get("close_result"):
                problems.append(f"Session {sid} 的 Cycle close_result 被改写")
    return problems


def convert_interface_problem() -> str:
    """TODO 渲染器是否已经是退 Work 的那一版；返回原因，空串表示可用。

    v3 收敛会**重新渲染** TODO（去 `current_work`），所以渲染器还带这个字段时，
    收敛出来的结果仍会把它写回去——那是静默的错误输出，比不转换更糟。这里按接口
    契约做前置判断：不是退 Work 的那一版就拒绝转换。
    """
    import inspect

    from paos_todo_v3 import render_todo_v3

    parameters = inspect.signature(render_todo_v3).parameters
    if "current_work" in parameters:
        return "todo_renderer_still_writes_current_work"
    if "boundaries" not in parameters or "history_ref" not in parameters or "latest_readback" not in parameters:
        return "todo_renderer_missing_workless_optional_fields"
    return ""


def v3_converge_interface_problem() -> str:
    """v3 收敛接口是否可用；返回原因，空串表示可用。"""
    missing = [
        name
        for name, value in (
            ("plan_v3_home_convergence", plan_v3_home_convergence),
            ("apply_v3_home_convergence", apply_v3_home_convergence),
        )
        if value is None
    ]
    if missing:
        return "v3_converge_interface_missing:" + ",".join(missing)
    return ""


def _declared_schema(text: str) -> str:
    """用 S032 转换器同一个解析器读 TODO 声明的 schema（只为分类，不做转换）。"""
    parsed = parse_todo_markdown(text)
    return str(parsed.get("schema") or "").strip().strip('"')


def _dropped_current_values(
    source_text: str, candidate_text: str, fields_removed
) -> list[str]:
    """收敛后仍必须原地存活的 Current 值与 Task 行；返回会丢或被改形的字段名。

    接口自己声明它会摘掉 `fields_removed` 里的字段，其余字段的**值**必须不变。
    真实 Home 里确实存在渲染器不认识的 Current 字段（`boundaries` / `history_ref` /
    `latest_readback`），也存在把列表写成字符串的历史值（`result_refs`）。前者会被静默
    丢掉，后者会被逐字符拆成上百项 —— 两种都是删证据。宁可拒绝写入，也不产出这种
    结果，所以这里按值比对而不是只看"写没写成功"。
    """
    try:
        before = parse_todo_v3(source_text)
        after = parse_todo_v3(candidate_text)
    except Exception:
        return ["todo_unparsable"]
    allowed = set(fields_removed or ())
    lost = []
    before_current = before.get("current") or {}
    after_current = after.get("current") or {}
    for key, value in before_current.items():
        if key in allowed or str(value or "").strip() == "":
            continue
        if key not in after_current or after_current[key] != value:
            lost.append(key)
    if list(before.get("tasks") or []) != list(after.get("tasks") or []):
        lost.append("tasks")
    return sorted(lost)


def home_verdict(
    home_path: Path,
    *,
    home_kind: str,
    home_id: str,
    project_id: str,
    manifest_root: Path,
) -> dict:
    """判定一个 Home 能不能交给 S032 的接口收敛（只读，不改盘）。

    分类而不是自造转换：这里只挑出 `convertible` 的 Home，转换本身由
    `paos_v13_convert` 负责。已经是目标合同的 Home 归 `already_converged`——
    如实报告，不静默跳过、也不自行解析改写。
    """
    verdict = {
        "home_kind": home_kind,
        "home_id": home_id,
        "project_id": project_id,
        "home_path": str(home_path),
        "manifest_root": str(manifest_root),
    }
    todo_path = Path(home_path) / "TODO.md"
    if not todo_path.is_file():
        return {**verdict, "state": HOME_ABSENT, "reason": "todo_missing"}
    try:
        source_text = todo_path.read_text(encoding="utf-8")
        schema = _declared_schema(source_text)
    except Exception as problem:
        return {
            **verdict,
            "state": HOME_ABSENT,
            "reason": f"todo_unreadable:{getattr(problem, 'code', type(problem).__name__)}",
        }
    verdict["todo_schema"] = schema
    if schema not in (V2_TODO_SCHEMA, V3_TODO_SCHEMA):
        return {
            **verdict,
            "state": HOME_ABSENT,
            "reason": f"unsupported_input_schema:{schema}",
        }
    problem = convert_interface_problem() or v3_converge_interface_problem()
    if problem:
        return {**verdict, "state": HOME_BLOCKED_INTERFACE, "reason": problem}
    if schema == V2_TODO_SCHEMA:
        return {**verdict, "state": HOME_CONVERTIBLE, "axis": AXIS_V2}
    try:
        plan = plan_v3_home_convergence(
            home_path=Path(home_path),
            home_kind=home_kind,
            home_id=home_id,
            project_id=project_id,
        )
    except HOME_PROBLEMS as problem:
        return {
            **verdict,
            "state": HOME_BLOCKED_INTERFACE,
            "reason": f"v3_convergence_problem:{getattr(problem, 'code', type(problem).__name__)}",
            "detail": str(problem),
        }
    verdict["fields_removed"] = list(plan["fields_removed"])
    verdict["source_todo_sha256"] = plan["source_todo_sha256"]
    verdict["candidate_todo_sha256"] = plan["candidate_todo_sha256"]
    lost = _dropped_current_values(
        source_text, plan["candidate_todo_text"], plan["fields_removed"]
    )
    if lost:
        return {
            **verdict,
            "state": HOME_BLOCKED_INTERFACE,
            "reason": "convergence_would_not_preserve:" + ",".join(lost),
            "dropped": lost,
        }
    # 按内容判“已经到位”：行尾（CRLF/LF）差异不算需要收敛的差别，不为它改写文件。
    if plan["candidate_todo_text"] == source_text:
        return {**verdict, "state": HOME_ALREADY_CONVERGED, "reason": "todo_already_at_target"}
    return {**verdict, "state": HOME_CONVERTIBLE, "axis": AXIS_V3}


def plan_homes(project: dict) -> list[dict]:
    """按文件系统枚举一个项目下全部 Project Agent Home 的收敛判定（只读）。

    按目录枚举而不是按 sessions 枚举：Home 的存在与 Session 记录不是一回事
    （真实 3002 有 35 条 Session、磁盘上只有 8 个 Home），迁移范围以磁盘为准。
    """
    project_id = str(project.get("id") or "")
    root_raw = str(project.get("root_path") or "").strip()
    if not root_raw:
        return [
            {
                "home_kind": "project_agent",
                "home_id": "",
                "project_id": project_id,
                "state": HOME_ABSENT,
                "reason": "project_root_path_empty",
            }
        ]
    project_root = Path(root_raw)
    workstations = project_root / "Workstations"
    if not workstations.is_dir():
        return [
            {
                "home_kind": "project_agent",
                "home_id": "",
                "project_id": project_id,
                "state": HOME_ABSENT,
                "reason": "workstations_dir_missing",
                "workstations": str(workstations),
            }
        ]
    verdicts = []
    for path in sorted(item for item in workstations.iterdir() if item.is_dir()):
        try:
            canonical = project_agent_home(
                project=project,
                agent_id=path.name,
                root_override=root_raw,
                require_existing=False,
            )
        except Exception as problem:
            verdicts.append(
                {
                    "home_kind": "project_agent",
                    "home_id": path.name,
                    "project_id": project_id,
                    "home_path": str(path),
                    "state": HOME_ABSENT,
                    "reason": f"home_unresolved:{getattr(problem, 'code', type(problem).__name__)}",
                }
            )
            continue
        if Path(str(canonical["home_path"])) != path:
            verdicts.append(
                {
                    "home_kind": "project_agent",
                    "home_id": path.name,
                    "project_id": project_id,
                    "home_path": str(path),
                    "state": HOME_ABSENT,
                    "reason": "not_a_project_agent_home",
                }
            )
            continue
        verdicts.append(
            home_verdict(
                path,
                home_kind="project_agent",
                home_id=path.name,
                project_id=project_id,
                manifest_root=project_root,
            )
        )
    return verdicts


def plan_rooter_home(installation_path: Path) -> list[dict]:
    """登记的 Rooter Home：没有 Project、也没有 Project Session。

    身份一律用登记处记录的 Home 目录名；manifest 落在该 Home 的上一级目录下的
    `.paos/`——与 Project Agent Home 落在 `<project_root>/.paos/` 同一套布局。
    """
    verdict_base = {"home_kind": "rooter", "home_id": "", "project_id": ""}
    try:
        descriptor = load_installation_descriptor(Path(installation_path))
    except Exception as problem:
        return [
            {
                **verdict_base,
                "state": HOME_ABSENT,
                "reason": f"installation_unreadable:{type(problem).__name__}",
            }
        ]
    raw = str(descriptor.get("rooter_home") or "").strip()
    if not raw:
        return [{**verdict_base, "state": HOME_ABSENT, "reason": "rooter_home_not_registered"}]
    home_path = Path(raw)
    if not home_path.is_dir():
        return [
            {
                **verdict_base,
                "home_id": home_path.name,
                "state": HOME_ABSENT,
                "reason": "home_dir_missing",
                "home_path": str(home_path),
            }
        ]
    return [
        home_verdict(
            home_path,
            home_kind="rooter",
            home_id=home_path.name,
            project_id="",
            manifest_root=home_path.parent,
        )
    ]


def _home_manifest_path(verdict: dict) -> Path:
    """一个 Home 的收敛 manifest 路径（只用于报告；写入由 S032 的接口完成）。"""
    return (
        Path(str(verdict["manifest_root"]))
        / ".paos"
        / "v13-migration"
        / HOME_MANIFEST_ID
        / V3_CONVERGE_DIR
        / str(verdict["home_id"])
        / "manifest.json"
    )


def migrate(
    root: Path,
    *,
    apply: bool,
    only: str | None = None,
    homes: bool = True,
    installation_file: Path | None = None,
) -> dict:
    projects_dir = root / "projects"
    if not projects_dir.is_dir():
        raise MigrationError(f"{projects_dir} 不存在；--root 应指向 registry 根（其下有 projects/）。")

    paths = sorted(p for p in projects_dir.glob("*.json"))
    if only:
        paths = [p for p in paths if p.stem == only]
        if not paths:
            raise MigrationError(f"未找到项目 {only}（{projects_dir}）。")

    # 阶段一：全部先规划 + 校验，任何一个失败则整体中止（不写盘）
    plans = []
    for path in paths:
        raw = path.read_text(encoding="utf-8")
        plan = plan_project(raw, path)
        plan["before_sha256"] = _sha256(raw)
        if not plan["skip"]:
            problems = _conservation(plan["before"], plan["project"])
            if problems:
                raise MigrationError(f"{path.name}: 守恒自检失败：" + "；".join(problems))
        plan["homes"] = plan_homes(plan["project"]) if homes else []
        plans.append(plan)

    # 登记的 Rooter Home 不在任何 Project 下（无 Project Session），单独按登记处取。
    rooter_verdicts = []
    if homes:
        rooter_verdicts = plan_rooter_home(
            Path(installation_file) if installation_file else resolve_installation_path()
        )

    home_verdicts = [item for plan in plans for item in plan["homes"]] + rooter_verdicts
    home_summary = {
        state: sum(1 for item in home_verdicts if item["state"] == state)
        for state in HOME_STATES
    }

    report = {
        "root": str(root),
        "apply": bool(apply),
        "projects": len(plans),
        "migrated": 0,
        "skipped": 0,
        "counts": {},
        "backup_dir": "",
        "sha256": {},
        "homes": home_summary,
        "home_homes": len(home_verdicts),
        "home_details": home_verdicts,
        "home_converted": [],
        "home_blocked": [
            item for item in home_verdicts if item["state"] == HOME_BLOCKED_INTERFACE
        ],
    }

    if not apply:
        for plan in plans:
            if plan["skip"]:
                report["skipped"] += 1
            else:
                report["migrated"] += 1
                for key, value in plan["counts"].items():
                    report["counts"][key] = report["counts"].get(key, 0) + value
            report["sha256"][plan["path"].name] = plan["before_sha256"]
        return report

    # 规划已经做完、还没写任何东西：已知收敛不了的 Home 就在这里停。
    # 先备份并改 Project 的治理事实、再发现 Home 过不去，等于把"整次安装迁移"
    # 拆成一次半迁移——治理事实已经变了，而 Home 还是旧的。
    if report["home_blocked"]:
        raise MigrationBlocked(_blocked_message(report["home_blocked"]),
                               blocked=report["home_blocked"])

    # 阶段二：备份 before-state，然后原子写
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / "backups" / f"workless-migration-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    report["backup_dir"] = str(backup_dir)

    for plan in plans:
        path = plan["path"]
        if plan["skip"]:
            report["skipped"] += 1
            continue
        (backup_dir / path.name).write_text(
            json.dumps(plan["before"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _atomic_write(path, plan["project"])
        report["migrated"] += 1
        for key, value in plan["counts"].items():
            report["counts"][key] = report["counts"].get(key, 0) + value
        report["sha256"][path.name] = plan["before_sha256"]

    # 阶段三：回读核对
    for plan in plans:
        if plan["skip"]:
            continue
        text = plan["path"].read_text(encoding="utf-8")
        back = json.loads(text)
        if back.get("schema") != PROJECT_SCHEMA:
            raise MigrationError(f"{plan['path'].name}: 回读 schema 不是 {PROJECT_SCHEMA}。")
        validate_project(back)
        if len(back.get("ledger", [])) != len(plan["before"].get("ledger", [])) + 1:
            raise MigrationError(f"{plan['path'].name}: 回读 ledger 条数不符。")
    # 阶段四：Home 收敛（S032 的接口；每个 Home 独立 manifest + 幂等 replay）
    for plan in plans:
        for verdict in plan["homes"]:
            _apply_home(verdict, report, project=plan["project"])
    for verdict in rooter_verdicts:
        _apply_home(verdict, report, project=None)
    return report


def _apply_home(verdict: dict, report: dict, *, project: dict | None) -> None:
    """把一个 Home 交给对应的那条轴；任何失败都停在这里，不留半截状态。"""
    if verdict["state"] != HOME_CONVERTIBLE:
        return
    home_id = str(verdict["home_id"])
    try:
        if verdict.get("axis") == AXIS_V3:
            applied = apply_v3_home_convergence(
                project_root=Path(str(verdict["manifest_root"])),
                home_path=Path(str(verdict["home_path"])),
                home_kind=str(verdict["home_kind"]),
                home_id=home_id,
                project_id=str(verdict["project_id"]),
                manifest_id=HOME_MANIFEST_ID,
            )
        else:
            applied = apply_project_home_conversion(
                root=Path(str(verdict["manifest_root"])),
                project=project,
                agent_id=home_id,
                manifest_id=HOME_MANIFEST_ID,
            )
    except HOME_PROBLEMS as problem:
        raise MigrationError(
            f"Home 收敛失败：{home_id}"
            f"（{getattr(problem, 'code', 'v13_conversion_error')}）{problem}"
        ) from problem
    report["home_converted"].append(
        {
            "home_kind": verdict["home_kind"],
            "home_id": home_id,
            "axis": verdict.get("axis"),
            "replayed": bool(applied.get("replayed")),
            "fields_removed": list(applied.get("fields_removed") or []),
            "manifest": str(_home_manifest_path(verdict)),
        }
    )


def _rollback_v3_convergence(manifest_path: Path) -> dict:
    """按 manifest 把一次 v3 收敛逐字节还原。

    S032 的收敛接口把改动前的 TODO 原文留在 manifest 同级的 `TODO-before.md`，
    并记下 `source_todo_sha256`。回退只做这一件事：把那份原文放回去，并核对
    指纹——不重建 Notice/Mail，也不清 manifest。
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != "paos-v3-home-converge-manifest/v1":
        raise MigrationError(f"v3 收敛 manifest schema 无效：{manifest_path}")
    backup = Path(str(manifest.get("todo_backup_path") or ""))
    if not backup.is_file():
        backup = Path(manifest_path).parent / "TODO-before.md"
    if not backup.is_file():
        raise MigrationError(f"v3 收敛回退缺少原文备份：{backup}")
    original = backup.read_bytes()
    expected = str(manifest.get("source_todo_sha256") or "")
    actual = hashlib.sha256(original).hexdigest()
    if expected and actual != expected:
        raise MigrationError(f"v3 收敛回退原文指纹不符：{backup}")
    restored = Path(str(manifest.get("home_path") or ""))
    if not restored.name:
        raise MigrationError(f"v3 收敛 manifest 缺少 home_path：{manifest_path}")
    # 接口把 `home_path` 记成 TODO 文件的完整路径，不是 Home 目录。
    restored.write_bytes(original)
    return {
        "restored_todo_path": str(restored),
        "source_todo_sha256": actual,
        "manifest": str(manifest_path),
    }


def rollback_homes(project_root: Path) -> dict:
    """按 manifest 回退一个 root 下的全部 Home 转换（v2 入口轴 + v3 收敛轴）。"""
    base = Path(project_root) / ".paos" / "v13-migration" / HOME_MANIFEST_ID
    converge = sorted(base.glob(f"{V3_CONVERGE_DIR}/*/manifest.json"))
    entry = [item for item in sorted(base.glob("*/manifest.json")) if item not in converge]
    if not converge and not entry:
        raise MigrationError(f"未找到 Home 转换 manifest：{base}")
    rollbacks = []
    for manifest in entry:
        try:
            rollbacks.append(rollback_home_conversion(manifest))
        except HOME_PROBLEMS as problem:
            raise MigrationError(
                f"Home 回退失败：{manifest}"
                f"（{getattr(problem, 'code', 'v13_conversion_error')}）{problem}"
            ) from problem
    for manifest in converge:
        rollbacks.append(_rollback_v3_convergence(manifest))
    return {
        "project_root": str(project_root),
        "manifests": len(rollbacks),
        "converge_manifests": len(converge),
        "rollbacks": rollbacks,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="一次性离线迁移到 workless（paos-project/v3）")
    parser.add_argument("--root", default=None, help="registry 根目录（其下有 projects/）")
    parser.add_argument("--apply", action="store_true", help="真正写盘；缺省只做 dry-run")
    parser.add_argument("--only", default=None, help="只迁移一个项目 ID")
    parser.add_argument(
        "--skip-homes",
        action="store_true",
        help="只迁移项目文件，不做 Workstation Home 收敛",
    )
    parser.add_argument(
        "--installation-file",
        default=None,
        metavar="PATH",
        help="登记 Rooter Home 的安装描述符；缺省用本机标准位置",
    )
    parser.add_argument(
        "--rollback-home",
        default=None,
        metavar="PROJECT_ROOT",
        help="按 manifest 回退该 root 下的 Home 收敛",
    )
    args = parser.parse_args(argv)

    if args.rollback_home:
        try:
            result = rollback_homes(Path(args.rollback_home))
        except MigrationError as error:
            print(f"回退中止：{error}", file=sys.stderr)
            return 2
        print(
            f"[ROLLBACK-HOME] root={result['project_root']} "
            f"manifests={result['manifests']}"
        )
        for item in result["rollbacks"]:
            print(f"  restored: {item['restored_todo_path']}")
        return 0

    if not args.root:
        print("迁移中止：需要 --root（或使用 --rollback-home）。", file=sys.stderr)
        return 2

    try:
        report = migrate(
            Path(args.root),
            apply=args.apply,
            only=args.only,
            homes=not args.skip_homes,
            installation_file=Path(args.installation_file) if args.installation_file else None,
        )
    except MigrationBlocked as error:
        print(f"迁移未开始：{error}", file=sys.stderr)
        return 3
    except MigrationError as error:
        print(f"迁移中止：{error}", file=sys.stderr)
        return 2
    mode = "APPLY" if report["apply"] else "DRY-RUN"
    print(f"[{mode}] projects={report['projects']} migrated={report['migrated']} skipped={report['skipped']}")
    if report["counts"]:
        print("counts:", json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))
    if report["backup_dir"]:
        print("before-state backup:", report["backup_dir"])
    if report["home_homes"]:
        print(
            "homes:"
            f" convertible={report['homes'][HOME_CONVERTIBLE]}"
            f" already_converged={report['homes'][HOME_ALREADY_CONVERGED]}"
            f" absent={report['homes'][HOME_ABSENT]}"
            f" blocked_interface={report['homes'][HOME_BLOCKED_INTERFACE]}"
        )
    for item in report["home_details"]:
        if item["state"] not in (HOME_CONVERTIBLE, HOME_ALREADY_CONVERGED):
            print(
                f"  {item['state'].upper()} {item['home_kind']}/{item['home_id'] or '-'}:"
                f" {item.get('reason', '')}"
            )
    if report["home_converted"]:
        replayed = sum(1 for item in report["home_converted"] if item["replayed"])
        print(f"home converged: {len(report['home_converted']) - replayed} applied, {replayed} replayed")
    if not report["apply"]:
        print("（dry-run：未写盘。加 --apply 才执行迁移。）")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
