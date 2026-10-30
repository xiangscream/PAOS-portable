"""Filesystem-only helper for the S3-1 Workstation commands.

This module is deliberately standalone: stdlib only, no PAOS Store / Workflow /
server imports, and it never reads or writes PAOS ``private-data``. It performs
runtime-local path checks and cycle-bound Workstation materialization; PAOS
facts and responsibility stay owned by the canonical REST surface.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Iterable

# 键值标记：PAOS key_files 现有格式 `说明：<absolute local path or URL>`（全角冒号）。
# ENTRY 必须同时保留 label（说明标记）与解析后的 locator，不得靠任意字符串猜路径。

_TODO_V3_PATH = Path(__file__).resolve().with_name("paos_todo_v3.py")
_TODO_V3_SPEC = importlib.util.spec_from_file_location(
    "paos_todo_v3_workstation_adapter",
    _TODO_V3_PATH,
)
if _TODO_V3_SPEC is None or _TODO_V3_SPEC.loader is None:
    raise RuntimeError(f"无法加载 TODO v3 helper：{_TODO_V3_PATH}")
_TODO_V3_HELPER = importlib.util.module_from_spec(_TODO_V3_SPEC)
_TODO_V3_SPEC.loader.exec_module(_TODO_V3_HELPER)


CANONICAL_GUIDE_TEMPLATE = """# Workflow Guide（项目工作方法副本）

- PAOS 保存正式事实；本文件是本地工作方法副本，不改变权限、责任或验收。
- 进入新 Cycle 前先读取当前事实：`paos session context <project> <agent>`。
- 在本 Cycle 目录内工作：`inputs/` 只读材料、`outputs/` 交付、`review/` 审查意见。
- 遇到 tenure 过期、责任冲突或材料不可达时停止，并把摩擦写回 Session Update 或 CAT。
- 本指南可被本工位编辑；`review/GUIDE-SEED.md` 保留本 Cycle 的精确 seed 基线。
- 改进是否晋升到 canonical Practice 必须经过 diff 审阅与显式 promotion。
"""


class WorkstationProblem(Exception):
    """A workstation failure with a stable error code for the CLI layer."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return root / path


# 显式 Windows 盘符绝对路径映射：仅在 POSIX/WSL 侧把 `C:\...`/`C://...`
# 转成 `/mnt/<drive>/...`，映射后仍按真实存在性检查。不做模糊搜索、
# 按文件名猜测或静默忽略。
_WINDOWS_DRIVE_RE = re.compile(r"^([A-Za-z]):[/\\](.*)$", re.DOTALL)
# wsl.localhost UNC：\\wsl.localhost\<distro>\... —— 仅当与本机 WSL_DISTRO_NAME
# 相同时明确映射到其后的 WSL 路径；不同 distro/其他 UNC 原样返回（真实失败）。
_WSL_UNC_RE = re.compile(
    r"^(?:\\\\wsl\.localhost\\|//wsl\.localhost/)([^\\/]+)[/\\](.*)$", re.IGNORECASE
)
# locator 判定：Windows 盘符绝对路径 / UNC / http(s) URL / POSIX 绝对路径。
_LOCATOR_LIKE_RE = re.compile(
    r"^(?:[A-Za-z]:[/\\]|\\\\|//|https?://|/[^/])", re.IGNORECASE
)


def locator_like(candidate: str) -> bool:
    """只认明确形态：Windows 盘符绝对路径 / UNC / http(s) URL。"""
    return bool(_LOCATOR_LIKE_RE.match(candidate.strip()))


def posix_windows_drive_locator(locator: str) -> str:
    """POSIX/WSL 下的显式路径映射：Windows 盘符 → /mnt/<drive>；
    wsl.localhost UNC 同 distro → 其后 WSL 路径；Windows 原生 UNC 原样；
    不同 distro/其他 UNC 原样返回（真实失败，不猜）。"""
    if os.name == "nt":
        return locator
    text = locator.strip()
    unc = _WSL_UNC_RE.match(text)
    if unc:
        distro = unc.group(1)
        if os.environ.get("WSL_DISTRO_NAME") == distro:
            rest = unc.group(2).replace("\\", "/")
            return "/" + rest
        return locator
    match = _WINDOWS_DRIVE_RE.match(text)
    if not match:
        return locator
    drive = match.group(1).lower()
    rest = match.group(2).replace("\\", "/")
    rest = re.sub(r"/{2,}", "/", rest).lstrip("/")
    return f"/mnt/{drive}/{rest}"


def parse_key_file_entry(raw: str) -> dict[str, str]:
    """`<label>：<locator>` 仅在 locator 明确像 locator（盘符/UNC/http(s)）
    时拆为 label+locator；否则整条按原 locator 处理并正常失败，不能猜。"""
    text = raw.strip()
    mark = text.find("：")
    if mark > 0:
        candidate = text[mark + 1 :].strip()
        if candidate and locator_like(candidate):
            return {"label": text[: mark + 1], "locator": candidate}
    return {"label": "", "locator": text}


def _readable_file_problem(path: Path) -> str:
    if not path.exists():
        return "not_found"
    if path.is_dir():
        return "is_directory"
    if not os.access(path, os.R_OK):
        return "not_readable"
    return ""


def _readable_entry_problem(path: Path) -> str:
    """key_file 引用定位符的检查：目录存在可读即通过。"""
    if not path.exists():
        return "not_found"
    if path.is_dir():
        if not os.access(path, os.R_OK):
            return "not_readable"
        return ""
    if not os.access(path, os.R_OK):
        return "not_readable"
    return ""


def preflight_workspace(
    root: Path,
    key_files: Iterable[str],
    materials: Iterable[str],
) -> dict[str, Any]:
    """Best-effort runtime checks for the selected Project workspace root.

    Project ``key_files`` are navigation references, not an implicit list of
    mandatory inputs for every Work. Their reachability is reported honestly
    but does not fail the Workstation preflight. Explicit ``materials`` are
    task-scoped inputs and remain fail-closed.
    """
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    def record(
        kind: str,
        raw: str,
        path: Path,
        problem: str,
        extra: dict[str, Any] | None = None,
        *,
        blocking: bool = True,
    ) -> None:
        entry = {
            "kind": kind,
            "raw": raw,
            "path": str(path),
            "ok": not problem,
            "reason": problem,
            "blocking": bool(problem and blocking),
        }
        if extra:
            entry.update(extra)
        checks.append(entry)
        if problem and blocking:
            issues.append(entry)

    root_problem = ""
    if not root.exists():
        root_problem = "not_found"
    elif not root.is_dir():
        root_problem = "not_a_directory"
    elif not os.access(root, os.R_OK):
        root_problem = "not_readable"
    elif not os.access(root, os.W_OK):
        root_problem = "not_writable"
    record("root", str(root), root, root_problem)

    for raw in key_files:
        entry = parse_key_file_entry(raw)
        locator = entry["locator"]
        if locator.lower().startswith(("http://", "https://")):
            # Remote reference：保留为引用、明确 not_checked，
            # 不宣称已访问，也不阻断本地材料化。
            checks.append(
                {
                    "kind": "key_file",
                    "raw": raw,
                    "label": entry["label"],
                    "locator": locator,
                    "type": "remote_reference",
                    "path": locator,
                    "ok": True,
                    "reason": "not_checked",
                    "blocking": False,
                }
            )
            continue
        mapped = posix_windows_drive_locator(locator)
        path = resolve_path(root, mapped)
        problem = _readable_entry_problem(path)
        record(
            "key_file",
            raw,
            path,
            problem,
            extra={
                "label": entry["label"],
                "locator": locator,
                "type": "directory" if path.is_dir() else "file",
            },
            blocking=False,
        )
    for raw in materials:
        path = resolve_path(root, raw)
        record("material", raw, path, _readable_file_problem(path))

    return {
        "ready": not issues,
        "root_path": str(root),
        "checks": checks,
        "issues": issues,
    }




def _read_or_seed_canonical_guide(canonical_guide: Path, guide_seed_text: str) -> bytes:
    """Return canonical Guide bytes, creating it atomically only when absent.

    A complete temporary file is hard-linked into place. ``os.link`` is an
    atomic create-if-absent operation on the supported Windows/WSL filesystems:
    if another Human/Runtime wins the race, FileExistsError leaves those bytes
    untouched and this attempt reads the winner instead. We fail closed on a
    filesystem that cannot provide this non-overwrite primitive rather than
    falling back to ``os.replace``.
    """
    try:
        return canonical_guide.read_bytes()
    except FileNotFoundError:
        pass

    canonical_guide.parent.mkdir(parents=True, exist_ok=True)
    staged = canonical_guide.parent / f".WORKFLOW-GUIDE.seed-{uuid.uuid4().hex}"
    try:
        staged.write_text(guide_seed_text, encoding="utf-8")
        try:
            os.link(staged, canonical_guide)
        except FileExistsError:
            pass
        except OSError as exc:
            raise WorkstationProblem(
                "canonical_guide_atomic_publish_failed",
                f"无法安全播种 canonical Guide：{canonical_guide}",
                {"canonical_guide_path": str(canonical_guide), "os_error": str(exc)},
            ) from exc
        return canonical_guide.read_bytes()
    finally:
        staged.unlink(missing_ok=True)


def materialize_cycle(
    *,
    root: Path,
    work_id: str,
    agent_id: str,
    cycle: int,
    entry_text: str,
    guide_seed_text: str,
) -> Path:
    """Publish one new cycle directory atomically; never touch existing cycles.

    V1.1 keeps this directory as Cycle-bound execution evidence only. Stable
    Agent entry is owned by the visible Project Workstation and is not refreshed
    from Cycle materialization.
    """
    base = root / ".paos"
    canonical_guide = base / "practice" / "WORKFLOW-GUIDE.md"
    target = base / "workstations" / work_id / agent_id / f"cycle-{cycle}"
    if target.exists():
        raise WorkstationProblem(
            "workstation_exists",
            f"Workstation cycle 已存在，不覆盖：{target}",
            {"workstation_path": str(target)},
        )

    stage = target.parent / f".cycle-{cycle}.staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True)
        (stage / "ENTRY.md").write_text(entry_text, encoding="utf-8")
        guide_bytes = _read_or_seed_canonical_guide(canonical_guide, guide_seed_text)
        (stage / "GUIDE.md").write_bytes(guide_bytes)
        for name in ("inputs", "outputs", "review"):
            (stage / name).mkdir()
        (stage / "review" / "GUIDE-SEED.md").write_bytes(guide_bytes)
        os.rename(stage, target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    # V1.1: Cycle materialization publishes only Cycle-bound evidence.
    # The one normal Agent entry lives at <Project>/Workstations/<agent>/ENTRY.md.
    # Never recreate the retired .paos/agents/<agent>/ENTRY.md projection here.
    return target

# V1.1 fixed Agent Workstation foundation.
#
# Unlike the S3 cycle materialization above, this home is stable across Work,
# Cycle and Runtime changes. It lives in the visible Project Vault so humans and
# Agents can read the same Markdown directly in Obsidian.
V11_PROJECT_VAULT_DIRS = (
    "Inbox",
    "Materials",
    "Works",
    "Decisions",
    "Workstations",
    "Archive",
)
_TODO_ITEM_RE = re.compile(
    r"^- \[([ xX])\]\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s+(.+?)\s*$"
)


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def ensure_project_vault(root: Path) -> dict[str, Any]:
    """Ensure the minimal visible Project Vault layout without moving content.

    This is deliberately non-destructive. Existing directories are reused,
    existing files are never rewritten, and a conflicting file at one of the
    reserved directory paths fails before any new directory is created.
    """
    if not root.exists():
        raise WorkstationProblem(
            "project_vault_root_missing",
            f"Project Vault 根目录不存在：{root}",
            {"root_path": str(root)},
        )
    if not root.is_dir():
        raise WorkstationProblem(
            "project_vault_root_invalid",
            f"Project Vault 根路径不是目录：{root}",
            {"root_path": str(root)},
        )
    if not os.access(root, os.R_OK) or not os.access(root, os.W_OK):
        raise WorkstationProblem(
            "project_vault_root_unavailable",
            f"Project Vault 根目录不可读写：{root}",
            {"root_path": str(root)},
        )

    conflicts = [
        str(root / name)
        for name in V11_PROJECT_VAULT_DIRS
        if (root / name).exists() and not (root / name).is_dir()
    ]
    if conflicts:
        raise WorkstationProblem(
            "project_vault_layout_conflict",
            "Project Vault 标准目录与现有文件冲突，未执行初始化。",
            {"conflicts": conflicts, "root_path": str(root)},
        )

    created: list[str] = []
    for name in V11_PROJECT_VAULT_DIRS:
        path = root / name
        if not path.exists():
            path.mkdir()
            created.append(str(path))
    return {
        "root_path": str(root),
        "created_paths": created,
        "layout": {name: str(root / name) for name in V11_PROJECT_VAULT_DIRS},
    }


def _registered_body_ref(workflow_library: str) -> str:
    """正式安装登记（library-roots）下的唯一现行正文 canonical locator；未
    登记 → 空。显示保留 Windows canonical locator（如 library-roots 的
    `C:/…`），读取合同用同一 entry 源（磁盘 locator）。"""
    root_ref = _single_line(workflow_library)
    if not root_ref:
        return ""
    return str(Path(root_ref) / "Workflows" / "wf-agent-work-cycle.md")


def _readable_locator(path: str) -> tuple[bool, str]:
    """读取一个 canonical locator（Windows 盘符/UNC 或 POSIX 均可）。
    用 existing project helper `posix_windows_drive_locator` 做 host 侧
    实际磁盘路径：Windows locator 在 WSL 也能正确读（必须，否则显示时
    canonical 是 `C:/…` 但实际读的是相对文件路径，误报不可读）。返回
    (ok, problem) —— ok=False 时 problem 是如实的读取标签。"""
    from paos_workstation import posix_windows_drive_locator

    disk_path = Path(posix_windows_drive_locator(path.strip()))
    try:
        disk_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False, "（已登记但当前文件不可读）"
    return True, ""


def _library_locator_label(value: str, fallback: str) -> str:
    """登记了路径但文件当前不可读 / 未登记 分级标注（不猜）。走
    `_readable_locator` 保证 Windows canonical locator 的读取形态。"""
    text = _single_line(value)
    if not text:
        return fallback
    ok, problem = _readable_locator(text)
    if not ok:
        return f"{text}{problem}"
    return text


def render_fixed_entry(
    *,
    project: dict[str, Any],
    session: dict[str, Any],
    workstation_path: Path,
    workflow_library: str = "",
    skill_library: str = "",
    guide_ref: str = "",
    ops_ref: str = "",
    workflow_index_ref: str = "",
    skill_index_ref: str = "",
    tool_index_ref: str = "",
    staff_number: str = "",
) -> str:
    """Render the stable copy-paste entry for one long-lived Project Agent."""
    project_id = _single_line(project.get("id"))
    project_name = _single_line(project.get("name"))
    agent_id = _single_line(session.get("id"))
    identity_id = _single_line(session.get("identity_id"))
    workflow_root_ref = _single_line(workflow_library)
    skill_root_ref = _single_line(skill_library)
    workflow_ref = (
        _single_line(workflow_index_ref)
        or (str(Path(workflow_root_ref) / "CATALOG.md") if workflow_root_ref else "")
        or "（未登记；由 PAOS Library roots 提供）"
    )
    skill_ref = (
        _single_line(skill_index_ref)
        or (str(Path(skill_root_ref) / "CATALOG.md") if skill_root_ref else "")
        or "（未登记；由 PAOS Library roots 提供）"
    )
    guide_ref_default = (
        str(Path(workflow_root_ref) / "Guides" / "guide-work-method.md")
        if workflow_root_ref
        else ""
    )
    ops_ref_default = (
        str(Path(workflow_root_ref) / "Guides" / "ops-entry.md")
        if workflow_root_ref
        else ""
    )
    guide_locator = _library_locator_label(
        guide_ref or guide_ref_default,
        "（未登记；由 PAOS Library roots 提供）",
    )
    ops_locator = _library_locator_label(
        ops_ref or ops_ref_default,
        "（未登记；由 PAOS Library roots 提供）",
    )
    tool_locator = _library_locator_label(
        tool_index_ref,
        "（未登记；由共享 Tool Index 提供）",
    )
    body_ref = _registered_body_ref(workflow_root_ref)
    body_label = (
        _library_locator_label(body_ref, "（未登记；由 PAOS Library roots 提供）")
        if body_ref
        else "（未登记；由 PAOS Library roots 提供）"
    )
    # 规则 locator：工位 AGENTS 与 Project AGENTS 分别暴露；两者实际指向同一文件时共用；
    # 缺失如实标注（不伪称已生成，也不替现有员工写规则）。
    project_root = workstation_path.parent.parent
    workstation_rules = project_root / "Workstations" / agent_id / "AGENTS.md"
    project_rules = project_root / "AGENTS.md"
    ws_exists = workstation_rules.exists()
    pr_exists = project_rules.exists()
    if ws_exists and pr_exists and workstation_rules.resolve() == project_rules.resolve():
        rules_lines = [f"- 本人/项目规则：{workstation_rules}"]
    else:
        ws_label = str(workstation_rules) if ws_exists else f"{workstation_rules}（未登记）"
        pr_label = str(project_rules) if pr_exists else f"{project_rules}（未登记）"
        rules_lines = [
            f"- 本人规则（工位）：{ws_label}",
            f"- 项目规则：{pr_label}",
        ]
    restore_body_ref = (
        str(Path(workflow_root_ref) / "Workflows" / "wf-agent-work-cycle.md")
        + "#恢复"
        if workflow_root_ref
        else "（未登记；由 PAOS Library roots 提供）"
    )

    return "\n".join(
        [
            f"# Agent Workstation — {agent_id}"
            + (f" · 员工号 {staff_number}" if staff_number else ""),
            "",
            "## 身份",
            f"- Project：{project_id} · {project_name}",
            f"- Agent：{agent_id}" + (f"（员工号 {staff_number}）" if staff_number else ""),
            f"- Identity：{identity_id or '（未登记）'}",
            "- 本目录是该 Agent 在本 Project 中的固定工位；长期存在，不依赖 Work/Session 存续。",
            "",
            "## 固定入口",
            f"- 工位：{workstation_path}",
            f"- TODO：{workstation_path / 'TODO.md'}",
            f"- Notice：{workstation_path / 'notices'}",
            f"- Mailbox：{workstation_path / 'mailbox'}",
            *rules_lines,
            f"- 恢复正文：{restore_body_ref}",
            "- 恢复方式：从上方共享恢复正文开始（本页只给稳定入口，不复述步骤）。",
            f"- GUIDE：{guide_locator}",
            f"- OPS：{ops_locator}",
            f"- Workflow 唯一现行正文 = {body_label}（版本以该文件实际正文为准，本页不手抄）",
            f"- Workflow Index：{workflow_ref}",
            f"- Skill Index：{skill_ref}",
            f"- Tool Index：{tool_locator}",
            "",
            "## 工作约定",
            "- TODO.md 是本工位当前执行清单与简短状态的可读事实源；完成事项后补充完成方式和结果。",
            "- 正式成果直接写入 Project Vault 的 Works/ 或明确的项目文件位置，不把工位变成第二个项目库。",
            "- PAOS 继续负责身份、正式责任、验收和运行治理；ENTRY.md 不授予权限，也不承载当前授权事实。",
            "- Runtime 或唤醒器状态异常时保留工位文件，恢复后从同一工位继续。",
            "",
        ]
    )


def render_initial_todo(
    *,
    project: dict[str, Any],
    session: dict[str, Any],
    work: dict[str, Any] | None,
    objective: str = "",
) -> str:
    """Render the one normal new-Home TODO contract: paos-todo/v3."""
    project_id = _single_line(project.get("id"))
    agent_id = _single_line(session.get("id"))
    if not project_id or not agent_id:
        raise WorkstationProblem(
            "workstation_todo_identity_missing",
            "无法生成 TODO v3：Project/Agent identity 不完整。",
            {"project_id": project_id, "agent_id": agent_id},
        )

    work = work if isinstance(work, dict) else {}
    work_id = _single_line(work.get("id"))
    work_title = _single_line(work.get("title"))
    mission = session.get("mission") if isinstance(session.get("mission"), dict) else {}
    goal = (
        _single_line(objective)
        or _single_line(mission.get("objective"))
        or _single_line(work.get("objective"))
        or work_title
        or "核对当前责任与输入，维护 Current 后继续。"
    )
    next_action = (
        "读取 ENTRY / GUIDE / OPS，运行 orient 与 inbox 核对当前责任和输入，"
        f"然后开始执行：{goal}"
    )
    stage = _single_line(session.get("status")) or "not_started"
    input_version = (
        f"project-revision:{project.get('revision')}"
        if project.get("revision") is not None
        else ""
    )

    try:
        return _TODO_V3_HELPER.render_todo_v3(
            home_kind="project_agent",
            home_id=agent_id,
            project_id=project_id,
            objective=goal,
            approved_scope="",
            stage=stage,
            next_action=next_action,
            waiting="",
            results="",
            result_refs=(),
            context_refs=(),
            legacy_source_ref="",
            inflight="",
            alignment_ref="",
            input_version=input_version,
            delivery="",
            dependencies="",
            continuation_to="",
            tasks=[
                {
                    "id": "T-001",
                    "title": goal,
                    "state": "todo",
                    "waiting": "",
                    "result": "",
                    "artifact_ref": "",
                    "notify_after": [],
                }
            ],
        )
    except Exception as exc:
        code = str(getattr(exc, "code", "todo_v3_render_failed"))
        details = dict(getattr(exc, "details", {}) or {})
        raise WorkstationProblem(code, str(exc), details) from exc


def _publish_text_if_absent(path: Path, text: str) -> bool:
    """Atomically create one UTF-8 text file without overwriting an editor."""
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        staged.write_text(text, encoding="utf-8")
        try:
            os.link(staged, path)
            return True
        except FileExistsError:
            return False
        except OSError as exc:
            raise WorkstationProblem(
                "workstation_home_atomic_publish_failed",
                f"无法安全创建工位文件：{path}",
                {"path": str(path), "os_error": str(exc)},
            ) from exc
    finally:
        staged.unlink(missing_ok=True)


def _validate_existing_workstation_home(workstation: Path) -> None:
    conflicts: list[str] = []
    for name in ("ENTRY.md", "TODO.md"):
        path = workstation / name
        if path.exists() and not path.is_file():
            conflicts.append(str(path))
    mailbox = workstation / "mailbox"
    if mailbox.exists() and not mailbox.is_dir():
        conflicts.append(str(mailbox))
    notices = workstation / "notices"
    if notices.exists() and not notices.is_dir():
        conflicts.append(str(notices))
    if conflicts:
        raise WorkstationProblem(
            "workstation_home_layout_conflict",
            "固定工位中的保留路径与现有对象冲突。",
            {"workstation_path": str(workstation), "conflicts": conflicts},
        )


def _legacy_agent_entry_path(root: Path, agent_id: str) -> Path:
    return root / ".paos" / "agents" / agent_id / "ENTRY.md"


def _legacy_agent_entry_kind(path: Path, agent_id: str) -> str:
    """Classify the pre-V1.1 generated stable locator conservatively."""
    if not path.exists():
        return "absent"
    if not path.is_file():
        return "conflict"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "conflict"
    markers = (
        f"# Agent Workstation — {agent_id}",
        "这是生成的稳定入口，只做导航",
        "Latest materialized Work locator:",
        "Latest materialized Cycle locator:",
        "Latest materialized Cycle ENTRY:",
    )
    return "generated" if all(marker in text for marker in markers) else "conflict"


def _preflight_legacy_agent_entry(root: Path, agent_id: str) -> Path | None:
    """Allow automatic retirement only for the exact generated legacy locator."""
    path = _legacy_agent_entry_path(root, agent_id)
    kind = _legacy_agent_entry_kind(path, agent_id)
    if kind == "absent":
        return None
    if kind == "generated":
        return path
    raise WorkstationProblem(
        "legacy_agent_entry_conflict",
        "发现无法安全自动退役的旧 Agent ENTRY；未建立 V1.1 固定工位。",
        {
            "legacy_entry_path": str(path),
            "recovery": "先确认该文件是否有人为内容；保留需要的信息后移出 .paos/agents，再重试 workstation init。",
        },
    )


def _retire_generated_legacy_agent_entry(path: Path | None) -> str:
    """Retire one known generated legacy locator after the fixed home exists."""
    if path is None:
        return ""
    try:
        path.unlink()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise WorkstationProblem(
            "legacy_agent_entry_retire_failed_after_publish",
            "V1.1 固定工位已发布，但旧 Agent ENTRY 退役失败。",
            {
                "legacy_entry_path": str(path),
                "recovery": "保留新的 Workstations/<agent> 工位；只处理旧 .paos/agents/<agent>/ENTRY.md，不要重建工位。",
                "os_error": str(exc),
            },
        ) from exc

    # Clean only empty generated locator directories; never remove other content.
    for directory in (path.parent, path.parent.parent):
        try:
            directory.rmdir()
        except OSError:
            break
    return str(path)




CONTACT_PACKAGE_SCHEMA = "paos-contact-package/v1"

CONTACT_PY_TEMPLATE_V1 = r'''#!/usr/bin/env python3
"""Thin per-Home PAOS contact entry; all business logic stays in installed Source."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME_KIND = __HOME_KIND__
HOME_ID = __HOME_ID__
PROJECT_ID = __PROJECT_ID__


def _installation_file() -> Path:
    raw = os.environ.get("PAOS_INSTALLATION_FILE") or __INSTALL_FILE__ or str(
        Path.home() / ".paos" / "installation.json"
    )
    text = str(raw).strip()
    if os.name != "nt":
        match = re.match(r"^([A-Za-z]):[/\\](.*)$", text, re.DOTALL)
        if match:
            rest = re.sub(r"/{2,}", "/", match.group(2).replace("\\", "/")).lstrip("/")
            text = f"/mnt/{match.group(1).lower()}/{rest}"
    return Path(text).expanduser()


INSTALLATION_FILE = _installation_file()
DEFAULT_WAKE_MESSAGE = "检查 Workstation mailbox 或 CAT，并从当前工位继续。"


class ContactEntryError(Exception):
    pass


def _locator_for_platform(locator: str) -> str:
    if os.name == "nt":
        return locator
    text = str(locator or "").strip()
    match = re.match(r"^([A-Za-z]):[/\\](.*)$", text, re.DOTALL)
    if not match:
        return text
    rest = re.sub(r"/{2,}", "/", match.group(2).replace("\\", "/")).lstrip("/")
    return f"/mnt/{match.group(1).lower()}/{rest}"


def _source_scripts() -> Path:
    try:
        descriptor = json.loads(INSTALLATION_FILE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ContactEntryError(f"installation_descriptor_unavailable: {type(exc).__name__}") from exc
    source_root = str(descriptor.get("source_root") or "").strip()
    if not source_root:
        raise ContactEntryError("installation_source_root_missing")
    scripts = Path(_locator_for_platform(source_root)).expanduser() / "scripts"
    if not scripts.is_dir():
        raise ContactEntryError(f"installed_source_unreachable: {scripts}")
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    return scripts


def _resolve_home():
    _source_scripts()
    from paos_attention_service import resolve_home_by_registry
    try:
        ref = resolve_home_by_registry(HOME_ID, installation_file=str(INSTALLATION_FILE))
    except Exception as exc:
        raise ContactEntryError(f"home_unresolved: {type(exc).__name__}: {exc}") from exc
    local = Path(__file__).resolve().parent
    resolved = Path(str(ref["home_path"])).resolve()
    if os.path.normcase(str(local)) != os.path.normcase(str(resolved)):
        raise ContactEntryError("contact_home_locator_mismatch")
    if str(ref.get("home_kind") or "") != HOME_KIND:
        raise ContactEntryError("contact_home_kind_mismatch")
    return ref


def _load_read_services():
    _source_scripts()
    from paos_attention_service import read_home_state
    from paos_contact import runtime_contact
    return read_home_state, runtime_contact


def _contact_store_root(ref: dict) -> Path:
    """Existing install/Contact locator: Project native-target store lives at the
    Project root's private-data, not inside the Home directory; the Rooter Home's
    own Contact store root is the registered Rooter Home."""
    if HOME_KIND == "project_agent":
        root_text = str(ref.get("project_root") or "").strip()
        if not root_text:
            raise ContactEntryError("contact_project_root_missing")
        return Path(_locator_for_platform(root_text)).expanduser()
    return Path(str(ref["home_path"]))


def cmd_status():
    ref = _resolve_home()
    read_home_state, runtime_contact = _load_read_services()
    read_state = read_home_state(ref)
    runtime = runtime_contact(_contact_store_root(ref), HOME_ID)
    print(json.dumps({
        "schema": "paos-contact/v1",
        "action": "status",
        "home": ref,
        "read_model": read_state.get("read_model") or {},
        "runtime_contact": runtime,
        "capabilities": {
            "status": "supported_read_only",
            "wake": "supported_if_native_target_and_STOP_allow",
            "notify": "internal_project_agent_or_authorized_external_caller",
            "prepare": "manual_native_owner_only",
            "send": "authorized_external_caller_only",
        },
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_wake(message: str):
    ref = _resolve_home()
    _source_scripts()
    from paos_wakeup import trigger_wake
    try:
        result = trigger_wake(
            root=_contact_store_root(ref),
            agent_id=HOME_ID,
            wake_prompt=message or DEFAULT_WAKE_MESSAGE,
            source_kind="manual",
        )
    except Exception as exc:
        print(json.dumps({
            "schema": "paos-contact/v1",
            "action": "wake",
            "home": ref,
            "state": "error_or_uncertain",
            "error": type(exc).__name__,
            "detail": str(exc),
        }, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({
        "schema": "paos-contact/v1",
        "action": "wake",
        "home": ref,
        "result": result,
        "durable_input_created": False,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_notify(message_id: str, caller: str = "", token_stdin: bool = False, remind: bool = False):
    ref = _resolve_home()
    if not caller:
        return _cmd_notify_internal(ref, message_id)
    scripts = _source_scripts()
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from paos_external_contact import ExternalContactProblem, notify_external

    try:
        result = notify_external(
            installation_file=INSTALLATION_FILE, caller_id=caller,
            token=_external_token(token_stdin), home_ref=ref,
            external_id=message_id, remind=bool(remind),
        )
    except ExternalContactProblem as error:
        print(json.dumps({
            "schema": "paos-contact/v1", "action": "notify", "home": ref,
            "state": "rejected", "error_code": error.code, "error": str(error),
        }, ensure_ascii=False, indent=2))
        return 2
    if remind:
        result["remind"] = _external_remind(
            ref, str(result.get("message_id") or ""),
            f"外部通知 {message_id}: 请处理该既有输入",
        )
    print(json.dumps({"schema": "paos-contact/v1", "action": "notify", "home": ref, "result": result}, ensure_ascii=False, indent=2))
    return 0


def _cmd_notify_internal(ref, message_id: str):
    if HOME_KIND != "project_agent" or not PROJECT_ID:
        print(json.dumps({
            "schema": "paos-contact/v1", "action": "notify", "home": ref,
            "state": "unsupported", "reason": "rooter_notify_not_in_project_mail_contract",
        }, ensure_ascii=False, indent=2))
        return 2
    scripts = _source_scripts()
    command = [
        sys.executable, "-X", "utf8", "-B", str(scripts / "paos.py"),
        "--json", "attention", "notify", PROJECT_ID, message_id,
        "--agent", HOME_ID,
    ]
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def cmd_prepare():
    ref = _resolve_home()
    _, runtime_contact = _load_read_services()
    runtime = runtime_contact(_contact_store_root(ref), HOME_ID)
    receiver = runtime.get("receiver") if isinstance(runtime, dict) else None
    state = "already_prepared" if isinstance(receiver, dict) and receiver.get("prepared") is True else "manual_native_owner_required"
    print(json.dumps({
        "schema": "paos-contact/v1",
        "action": "prepare",
        "home": ref,
        "state": state,
        "performed": False,
        "reason": "contact entry never synthesizes SessionStart or copies native credentials",
        "runtime_contact": runtime,
    }, ensure_ascii=False, indent=2))
    return 0


def _external_token(token_stdin: bool) -> str:
    if token_stdin:
        return sys.stdin.read().strip()
    return os.environ.get("PAOS_EXTERNAL_TOKEN", "")


def _external_remind(ref, message_id: str, prompt: str):
    scripts = _source_scripts()
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from paos_external_contact import ensure_activation
    from paos_wakeup import trigger_wake

    created, _notice_id = ensure_activation(ref, message_id, "remind")
    if not created:
        return {"state": "already_attempted"}
    try:
        return trigger_wake(
            root=_contact_store_root(ref), agent_id=HOME_ID,
            wake_prompt=prompt, source_kind="mail",
        )
    except Exception as exc:
        return {"state": "error_or_uncertain", "error": type(exc).__name__}


def cmd_send(message_id: str, body_file: str, remind: bool, caller: str = "", token_stdin: bool = False):
    ref = _resolve_home()
    if not caller:
        print(json.dumps({
            "schema": "paos-contact/v1", "action": "send", "home": ref,
            "state": "unsupported",
            "reason": "external caller identity is required; internal callers continue to use agent send",
        }, ensure_ascii=False, indent=2))
        return 2
    scripts = _source_scripts()
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from paos_external_contact import ExternalContactProblem, send_external

    try:
        result = send_external(
            installation_file=INSTALLATION_FILE, caller_id=caller,
            token=_external_token(token_stdin), home_ref=ref,
            external_id=message_id, subject="External message", body_file=body_file,
            remind=bool(remind),
        )
    except ExternalContactProblem as error:
        print(json.dumps({
            "schema": "paos-contact/v1", "action": "send", "home": ref,
            "state": "rejected", "error_code": error.code, "error": str(error),
        }, ensure_ascii=False, indent=2))
        return 2
    if remind:
        result["remind"] = _external_remind(
            ref, str(result.get("message_id") or ""),
            f"外部消息 {message_id}: 请读取准确 Home 的该 Mail/Notice",
        )
    print(json.dumps({"schema": "paos-contact/v1", "action": "send", "home": ref, "result": result}, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="PAOS per-Home thin contact entry")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Read the exact Home and Runtime without writing")
    wake = sub.add_parser("wake", help="Explicit one-shot native wake; does not create durable Mail/Notice")
    wake.add_argument("--message", default=DEFAULT_WAKE_MESSAGE)
    notify = sub.add_parser("notify", help="Request activation for an existing durable Mail source")
    notify.add_argument("--caller", default="")
    notify.add_argument("--message-id", required=True)
    notify.add_argument("--token-stdin", action="store_true")
    notify.add_argument("--remind", action="store_true")
    sub.add_parser("prepare", help="Report whether native preparation is already present; never synthesizes a SessionStart event")
    send = sub.add_parser("send", help="Authorized external durable send through this exact Home")
    send.add_argument("--caller", default="")
    send.add_argument("--message-id", required=True)
    send.add_argument("--body-file", required=True)
    send.add_argument("--remind", action="store_true")
    send.add_argument("--token-stdin", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            return cmd_status()
        if args.command == "wake":
            return cmd_wake(args.message)
        if args.command == "notify":
            return cmd_notify(args.message_id, getattr(args, "caller", ""), bool(getattr(args, "token_stdin", False)), bool(getattr(args, "remind", False)))
        if args.command == "prepare":
            return cmd_prepare()
        return cmd_send(args.message_id, args.body_file, args.remind, getattr(args, "caller", ""), bool(getattr(args, "token_stdin", False)))
    except ContactEntryError as exc:
        print(json.dumps({
            "schema": "paos-contact/v1",
            "state": "unavailable",
            "error": str(exc),
        }, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _contact_template_v2(text: str) -> str:
    start = text.index("def cmd_status():")
    end = text.index("\n\ndef cmd_wake", start)
    status = """def cmd_status(full=False):
    ref = _resolve_home()
    read_home_state, runtime_contact = _load_read_services()
    runtime = runtime_contact(_contact_store_root(ref), HOME_ID)
    payload = {
        "schema": "paos-contact/v1",
        "action": "status",
        "mode": "full" if full else "compact",
        "home": ref,
        "runtime_contact": runtime,
        "capabilities": {
            "status": "supported_read_only",
            "full_status": "supported_read_only",
            "wake": "supported_if_native_target_and_STOP_allow",
            "notify": "internal_project_agent_or_authorized_external_caller",
            "prepare": "manual_native_owner_only",
            "send": "authorized_external_caller_only",
        },
    }
    if full:
        payload["read_model"] = read_home_state(ref).get("read_model") or {}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
"""
    text = text[:start] + status + text[end:]
    text = text.replace(
        '    sub.add_parser("status", help="Read the exact Home and Runtime without writing")',
        '    status = sub.add_parser("status", help="Read compact contact status; --full also reads Home/TODO/Notice history")\n'
        '    status.add_argument("--full", action="store_true", help="Read the complete Home read model (TODO/Tasks/Notice history)")',
        1,
    )
    text = text.replace(
        '        if args.command == "status":\n            return cmd_status()',
        '        if args.command == "status":\n            return cmd_status(bool(getattr(args, "full", False)))',
        1,
    )
    return text




def _with_utf8_stdout(template: str) -> str:
    bootstrap = (
        "def _configure_utf8_stdout():\n"
        "    for stream in (sys.stdout, sys.stderr):\n"
        "        reconfigure = getattr(stream, \"reconfigure\", None)\n"
        "        if reconfigure is not None:\n"
        "            reconfigure(encoding=\"utf-8\")\n"
        "\n\n"
    )
    return template.replace(
        "def main(argv=None):\n    import argparse",
        bootstrap + "def main(argv=None):\n    _configure_utf8_stdout()\n    import argparse",
        1,
    )





def _legacy_contact_markdown(text: str) -> str:
    return text.replace(
        "- python contact.py status — compact identity/config/STOP/receiver/contact status without reading TODO or Notice history. Read-only; bad TODO does not block it.\n"
        "- python contact.py status --full — also read the complete Home read model (Current, Tasks, Notice/recovery history, source fingerprints). Read-only; it does not mark Notice read.\n",
        "- python contact.py status — read the exact Home, current fields, source fingerprints, observed time, recovery counts, and Runtime contact. Read-only; it does not mark Notice read.\n",
    )


def _legacy_status_markdown(text: str) -> str:
    return text.replace(
        "4. Run python contact.py status for compact contact status; add --full for the live Home read model.\n",
        "4. Run python contact.py status for the live read model.\n",
    )


def render_contact_markdown_v1(*, home_kind: str, home_id: str, project_id: str) -> str:
    return _legacy_contact_markdown(
        render_contact_markdown(home_kind=home_kind, home_id=home_id, project_id=project_id)
    )


def render_status_markdown_v1(*, home_kind: str, home_id: str, project_id: str) -> str:
    return _legacy_status_markdown(
        render_status_markdown(home_kind=home_kind, home_id=home_id, project_id=project_id)
    )


def refresh_generated_contact_py(
    *, home_path: Path, home_kind: str, home_id: str, project_id: str,
    installation_file: str = "",
) -> dict[str, Any]:
    """Replace only exact legacy generated contact.py; keep manual edits."""
    home_path = Path(home_path)
    target = home_path / "contact.py"
    legacy = render_contact_py_v1(
        home_kind=home_kind, home_id=home_id, project_id=project_id,
        installation_file=installation_file,
    )
    current = render_contact_py(
        home_kind=home_kind, home_id=home_id, project_id=project_id,
        installation_file=installation_file,
    )
    try:
        text = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"status": "missing", "path": str(target)}
    except (OSError, UnicodeError):
        return {"status": "unreadable", "path": str(target)}
    if text not in {legacy, current}:
        return {"status": "modified", "path": str(target)}
    py_status = "current" if text == current else "updated"
    if py_status == "updated":
        temporary = target.with_name(f".{target.name}.staging-{__import__('uuid').uuid4().hex}")
        temporary.write_text(current, encoding="utf-8", newline="\n")
        temporary.replace(target)
    docs = {
        "contact_md": (
            home_path / "CONTACT.md",
            render_contact_markdown_v1(home_kind=home_kind, home_id=home_id, project_id=project_id),
            render_contact_markdown(home_kind=home_kind, home_id=home_id, project_id=project_id),
        ),
        "status_md": (
            home_path / "STATUS.md",
            render_status_markdown_v1(home_kind=home_kind, home_id=home_id, project_id=project_id),
            render_status_markdown(home_kind=home_kind, home_id=home_id, project_id=project_id),
        ),
    }
    files: dict[str, Any] = {"contact_py": {"status": py_status, "path": str(target)}}
    for label, (path, legacy_text, current_text) in docs.items():
        try:
            observed = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            files[label] = {"status": "missing", "path": str(path)}
            continue
        except (OSError, UnicodeError):
            files[label] = {"status": "unreadable", "path": str(path)}
            continue
        if observed == current_text:
            files[label] = {"status": "current", "path": str(path)}
        elif observed == legacy_text:
            temporary = path.with_name(f".{path.name}.staging-{__import__('uuid').uuid4().hex}")
            temporary.write_text(current_text, encoding="utf-8", newline="\n")
            temporary.replace(path)
            files[label] = {"status": "updated", "path": str(path)}
        else:
            files[label] = {"status": "modified", "path": str(path)}
    return {"status": py_status, "path": str(target), "files": files}


CONTACT_PY_TEMPLATE_V1 = _with_utf8_stdout(CONTACT_PY_TEMPLATE_V1)
CONTACT_PY_TEMPLATE = _contact_template_v2(CONTACT_PY_TEMPLATE_V1)


def render_contact_py_v1(
    *, home_kind: str, home_id: str, project_id: str, installation_file: str = ""
) -> str:
    return (
        CONTACT_PY_TEMPLATE_V1
        .replace("__HOME_KIND__", repr(home_kind))
        .replace("__HOME_ID__", repr(home_id))
        .replace("__PROJECT_ID__", repr(project_id))
        .replace("__INSTALL_FILE__", repr(str(installation_file or "")))
    )


def render_contact_py(
    *, home_kind: str, home_id: str, project_id: str, installation_file: str = ""
) -> str:
    return (
        CONTACT_PY_TEMPLATE
        .replace("__HOME_KIND__", repr(home_kind))
        .replace("__HOME_ID__", repr(home_id))
        .replace("__PROJECT_ID__", repr(project_id))
        .replace("__INSTALL_FILE__", repr(str(installation_file or "")))
    )


def render_contact_markdown(*, home_kind: str, home_id: str, project_id: str) -> str:
    project_line = f"- Project: {project_id}\n" if project_id else "- Project: none (installation-level Home)\n"
    return (
        "# PAOS Contact\n\n"
        f"- Home kind: {home_kind}\n"
        f"- Home id: {home_id}\n"
        f"{project_line}"
        "- Home resolution: the installed PAOS installation descriptor and its existing Project/Rooter resolver.\n"
        "- Shared implementation: installed Source; this file contains no driver, token, PID, or native credential.\n\n"
        "## Commands\n\n"
        "- python contact.py status — compact identity/config/STOP/receiver/contact status without reading TODO or Notice history. Read-only; bad TODO does not block it.\n"
        "- python contact.py status --full — also read the complete Home read model (Current, Tasks, Notice/recovery history, source fingerprints). Read-only; it does not mark Notice read.\n"
        "- python contact.py wake --message ... — one explicit native wake through the existing wake implementation. It does not create durable Mail/Notice and does not bypass STOP or an unconfigured target.\n"
        "- python contact.py notify --message-id <id> — internal Project Agent path; keeps the existing durable activation-intent behavior. Does not mark Notice read or directly wake the Runtime.\n"
        "- python contact.py notify --caller <id> --message-id <external-id> [--remind] [--token-stdin] — authorized external caller for this exact Home (Project or Rooter); persists/uses the existing Notice and wakes once only with remind permission.\n"
        "- python contact.py prepare — status/preflight only. It never fabricates a SessionStart event, copies native credentials, or claims a new receiver is prepared.\n"
        "- python contact.py send --caller <id> --message-id <external-id> --body-file <file> [--remind] [--token-stdin] — authorized external durable send to this exact Home; defaults to Mail/Notice without native remind.\n"
        "- Credentials come from the private `PAOS_EXTERNAL_TOKEN` environment or stdin (`--token-stdin`), never argv, Markdown or logs. Missing/revoked scope is rejected before delivery; no production grant is created here. Replaying the same caller/target/message with the same body is idempotent; different bytes are rejected. An uncertain native result is not resent automatically.\n\n"
        "## Read / recovery boundary\n\n"
        "- status uses the shared Home read service and exact Home resolver.\n"
        "- read_pending remains visible when a Notice is already read but still pending/unfinished.\n"
        "- Source fingerprints are raw-byte observations; the multi-file view is best-effort rather than an atomic global snapshot.\n"
        "- Missing, unreadable, filtered-out, or semantically unknown sources remain explicit; this page does not infer history or acceptance.\n"
    )


def render_status_markdown(*, home_kind: str, home_id: str, project_id: str) -> str:
    project_line = f"- Project: {project_id}\n" if project_id else "- Project: none (installation-level Home)\n"
    return (
        f"# PAOS Workstation Status — {home_id}\n\n"
        f"- Home kind: {home_kind}\n"
        f"- Home id: {home_id}\n"
        f"{project_line}"
        "- This is a stable navigation page, not a second source of truth.\n\n"
        "## Start here\n\n"
        "1. Read ENTRY.md.\n"
        "2. Read TODO.md and continue from its current section.\n"
        "3. Read CONTACT.md for the exact local contact entry.\n"
        "4. Run python contact.py status for compact contact status; add --full for the live Home read model.\n"
        "5. Inspect mailbox/ and notices/ only within this exact Home; do not scan guessed sibling directories.\n\n"
        "## Durable surfaces\n\n"
        "- ENTRY.md — navigation.\n"
        "- TODO.md — current work facts and task-level refs.\n"
        "- mailbox/ — durable inputs.\n"
        "- notices/ — Notice and read/handled sidecars.\n"
        "- CONTACT.md + contact.py — thin local contact/wake entry.\n\n"
        "The live read model reports observed_at, source fingerprints, current fields, read-pending recovery items, and explicit missing/filter scope. This page itself is not an acceptance receipt.\n"
    )


def ensure_contact_package(
    *,
    home_path: Path,
    home_kind: str,
    home_id: str,
    project_id: str = "",
    installation_file: str = "",
) -> dict[str, Any]:
    """Create the three thin Home files once; never overwrite an existing file."""
    home_path = Path(home_path)
    if not home_path.is_dir():
        raise WorkstationProblem(
            "contact_home_missing",
            f"Contact package Home 不存在：{home_path}",
            {"home_path": str(home_path), "home_id": home_id},
        )
    if home_kind not in {"project_agent", "rooter"}:
        raise WorkstationProblem(
            "contact_home_kind_invalid",
            f"不支持的 Home kind：{home_kind}",
            {"home_kind": home_kind},
        )
    home_id = _single_line(home_id)
    if not home_id:
        raise WorkstationProblem("contact_home_id_missing", "Contact package Home id 为空。")
    project_id = _single_line(project_id)
    if home_kind == "rooter" and project_id:
        raise WorkstationProblem(
            "contact_rooter_project_forbidden",
            "Rooter Contact package 不绑定 Project。",
            {"project_id": project_id},
        )
    if home_kind == "project_agent" and not project_id:
        raise WorkstationProblem(
            "contact_project_id_missing",
            "Project Agent Contact package 必须带 project_id。",
            {"home_id": home_id},
        )

    files = {
        "contact_py": home_path / "contact.py",
        "contact_md": home_path / "CONTACT.md",
        "status_md": home_path / "STATUS.md",
    }
    for label, path in files.items():
        if path.exists() and not path.is_file():
            raise WorkstationProblem(
                "contact_package_path_conflict",
                f"Contact package 路径不是普通文件：{path}",
                {"label": label, "path": str(path)},
            )

    contents = {
        files["contact_py"]: render_contact_py(
            home_kind=home_kind,
            home_id=home_id,
            project_id=project_id,
            installation_file=installation_file,
        ),
        files["contact_md"]: render_contact_markdown(
            home_kind=home_kind,
            home_id=home_id,
            project_id=project_id,
        ),
        files["status_md"]: render_status_markdown(
            home_kind=home_kind,
            home_id=home_id,
            project_id=project_id,
        ),
    }
    created: list[str] = []
    existing: list[str] = []
    for path, content in contents.items():
        if _publish_text_if_absent(path, content):
            created.append(str(path))
        else:
            existing.append(str(path))
    return {
        "schema": CONTACT_PACKAGE_SCHEMA,
        "home_kind": home_kind,
        "home_id": home_id,
        "project_id": project_id or None,
        "home_path": str(home_path),
        "paths": {key: str(value) for key, value in files.items()},
        "created_paths": created,
        "existing_paths": existing,
        "overwritten": False,
    }

def ensure_fixed_workstation(
    *,
    root: Path,
    project: dict[str, Any],
    session: dict[str, Any],
    work: dict[str, Any] | None = None,
    objective: str = "",
    workflow_library: str = "",
    skill_library: str = "",
    guide_ref: str = "",
    ops_ref: str = "",
    workflow_index_ref: str = "",
    skill_index_ref: str = "",
    tool_index_ref: str = "",
    staff_number: str = "",
) -> dict[str, Any]:
    """Create or repair one stable Project-local Agent Workstation.

    Existing ENTRY/TODO bytes are never replaced. Re-running this function is
    therefore safe after humans or Agents have edited the Markdown.
    """
    agent_id = _single_line(session.get("id"))
    if not agent_id:
        raise WorkstationProblem(
            "workstation_agent_id_missing",
            "无法建立固定工位：Session/Agent ID 为空。",
        )

    # P1 migration guard: do not create the V1.1 entry beside an unknown legacy
    # ENTRY. Only the exact generated pre-V1.1 locator may be retired.
    legacy_entry = _preflight_legacy_agent_entry(root, agent_id)
    vault = ensure_project_vault(root)
    workstation = root / "Workstations" / agent_id
    entry_text = render_fixed_entry(
        project=project,
        session=session,
        workstation_path=workstation,
        workflow_library=workflow_library,
        skill_library=skill_library,
        guide_ref=guide_ref,
        ops_ref=ops_ref,
        workflow_index_ref=workflow_index_ref,
        skill_index_ref=skill_index_ref,
        tool_index_ref=tool_index_ref,
        staff_number=staff_number,
    )
    todo_text = render_initial_todo(
        project=project,
        session=session,
        work=work,
        objective=objective,
    )

    created: list[str] = []
    if not workstation.exists():
        stage = workstation.parent / f".{agent_id}.staging-{uuid.uuid4().hex}"
        try:
            stage.mkdir()
            (stage / "ENTRY.md").write_text(entry_text, encoding="utf-8")
            (stage / "TODO.md").write_text(todo_text, encoding="utf-8")
            (stage / "mailbox").mkdir()
            (stage / "notices").mkdir()
            try:
                os.rename(stage, workstation)
                created.extend(
                    [
                        str(workstation),
                        str(workstation / "ENTRY.md"),
                        str(workstation / "TODO.md"),
                        str(workstation / "mailbox"),
                        str(workstation / "notices"),
                    ]
                )
            except FileExistsError:
                shutil.rmtree(stage, ignore_errors=True)
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            if isinstance(exc, WorkstationProblem):
                raise
            raise WorkstationProblem(
                "workstation_home_publish_failed",
                f"固定工位初始化失败：{workstation}",
                {"workstation_path": str(workstation), "cause": str(exc)},
            ) from exc

    if not workstation.exists() or not workstation.is_dir():
        raise WorkstationProblem(
            "workstation_home_invalid",
            f"固定工位路径不可用：{workstation}",
            {"workstation_path": str(workstation)},
        )

    _validate_existing_workstation_home(workstation)
    if _publish_text_if_absent(workstation / "ENTRY.md", entry_text):
        created.append(str(workstation / "ENTRY.md"))
    if _publish_text_if_absent(workstation / "TODO.md", todo_text):
        created.append(str(workstation / "TODO.md"))
    mailbox = workstation / "mailbox"
    if not mailbox.exists():
        mailbox.mkdir()
        created.append(str(mailbox))

    notices = workstation / "notices"
    active_todo = parse_workstation_todo(
        (workstation / "TODO.md").read_text(encoding="utf-8")
    )
    if active_todo.get("schema") == "paos-todo/v3" and not notices.exists():
        notices.mkdir()
        created.append(str(notices))

    retired_legacy_entry = _retire_generated_legacy_agent_entry(legacy_entry)
    return {
        "workstation_path": str(workstation),
        "entry_path": str(workstation / "ENTRY.md"),
        "todo_path": str(workstation / "TODO.md"),
        "mailbox_path": str(mailbox),
        "notice_path": str(notices),
        "created_paths": created,
        "retired_legacy_entry": retired_legacy_entry,
        "project_vault": vault,
    }


def parse_workstation_todo(text: str) -> dict[str, Any]:
    """Parse the active workstation TODO contract without guessing history.

    V1.3 converted Homes use paos-todo/v3.  The legacy v2 parser remains
    available only so the integration candidate can still inspect pre-cutover
    Homes and the one-time converter can read them.
    """
    head = "\n".join(text.splitlines()[:12])
    if "paos-todo/v3" not in head:
        return parse_todo_markdown(text)
    try:
        return _TODO_V3_HELPER.parse_todo_v3(text)
    except Exception as exc:  # stable WorkstationProblem contract for callers
        code = str(getattr(exc, "code", "todo_v3_invalid"))
        details = dict(getattr(exc, "details", {}) or {})
        raise WorkstationProblem(
            code,
            str(exc),
            details,
        ) from exc


def parse_todo_markdown(text: str) -> dict[str, Any]:
    """Parse v1.2 TODO current state only from explicit machine-readable sections."""
    lines = text.splitlines()
    meta: dict[str, str] = {}
    metadata_issues: list[str] = []
    if lines and lines[0].strip() == "---":
        metadata_closed = False
        for line in lines[1:]:
            if line.strip() == "---":
                metadata_closed = True
                break
            key, sep, value = line.partition(":")
            if sep:
                key = key.strip()
                if key in meta:
                    metadata_issues.append(f"duplicate_key:{key}")
                meta[key] = value.strip()
        if not metadata_closed:
            metadata_issues.append("front_matter_unterminated")
    else:
        metadata_issues.append("front_matter_missing")

    for key in ("schema", "project_id", "agent_id"):
        if not meta.get(key):
            metadata_issues.append(f"required_key_missing:{key}")

    sections: dict[str, list[str]] = {}
    section_counts: dict[str, int] = {}
    active: str | None = None
    for raw in lines:
        if raw.startswith("## "):
            active = raw[3:].strip()
            section_counts[active] = section_counts.get(active, 0) + 1
            sections.setdefault(active, [])
            continue
        if active is not None:
            sections[active].append(raw)

    current_section = sections.get("当前")
    task_section = sections.get("待办")
    missing_sections = []
    if current_section is None:
        missing_sections.append("当前")
    if task_section is None:
        missing_sections.append("待办")

    summary = {"stage": "", "progress": "", "blocked": "", "next": ""}
    labels = {
        "阶段：": "stage",
        "进展：": "progress",
        "阻塞：": "blocked",
        "下一步：": "next",
    }
    current = {
        "work": "",
        "objective": "",
        "stage": "",
        "next": "",
        "waiting": "",
        "results": "",
        "inflight": "",
    }
    current_labels = {
        "Work：": "work",
        "目标：": "objective",
        "阶段：": "stage",
        "下一步：": "next",
        "等待：": "waiting",
        "成果：": "results",
        "在途：": "inflight",
    }
    if current_section is not None:
        for raw in current_section:
            stripped = raw.strip()
            for label, key in labels.items():
                if stripped.startswith(label):
                    summary[key] = stripped[len(label) :].strip()
                    break
            for label, key in current_labels.items():
                if stripped.startswith(label):
                    current[key] = stripped[len(label) :].strip()
                    break

    detail_labels = {
        "完成方式：": "completion",
        "结果：": "result",
        "产出：": "artifact",
        "等待：": "waiting",
    }
    tasks: list[dict[str, Any]] = []
    malformed_tasks: list[str] = []
    if task_section is not None:
        task: dict[str, Any] | None = None
        for raw in task_section:
            stripped = raw.strip()
            match = _TODO_ITEM_RE.match(stripped)
            if match:
                task = {
                    "done": match.group(1).lower() == "x",
                    "id": match.group(2),
                    "title": match.group(3).strip(),
                    "details": {},
                }
                tasks.append(task)
                continue
            if stripped.startswith(("- [", "* [", "+ [")):
                malformed_tasks.append(stripped)
                task = None
                continue
            if task is not None and raw.startswith(("  ", "\t")):
                for label, key in detail_labels.items():
                    if stripped.startswith(label):
                        task["details"][key] = stripped[len(label) :].strip()
                        break

    done = sum(1 for item in tasks if item["done"])
    return {
        "schema": meta.get("schema") or "",
        "project_id": meta.get("project_id") or "",
        "agent_id": meta.get("agent_id") or "",
        "summary": summary,
        "current": current,
        "tasks": tasks,
        "counts": {
            "total": len(tasks),
            "done": done,
            "open": len(tasks) - done,
        },
        "missing_sections": missing_sections,
        "duplicate_sections": [
            name for name in ("当前", "待办") if section_counts.get(name, 0) > 1
        ],
        "metadata_issues": metadata_issues,
        "malformed_tasks": malformed_tasks,
    }


def read_fixed_workstation(
    root: Path,
    agent_id: str,
    *,
    tolerate_todo_errors: bool = False,
) -> dict[str, Any]:
    """Read the stable workstation without mutating Project or PAOS state."""
    legacy_entry = _legacy_agent_entry_path(root, agent_id)
    if legacy_entry.exists():
        raise WorkstationProblem(
            "workstation_dual_entry_detected",
            "同时发现 V1.1 固定工位与旧 .paos Agent ENTRY；拒绝静默选择入口。",
            {
                "legacy_entry_path": str(legacy_entry),
                "fixed_entry_path": str(root / "Workstations" / agent_id / "ENTRY.md"),
                "recovery": "运行 workstation init 完成旧生成入口退役；若旧文件含人为内容，先人工确认并移走。",
            },
        )
    workstation = root / "Workstations" / agent_id
    if not workstation.is_dir():
        raise WorkstationProblem(
            "workstation_home_missing",
            f"固定工位不存在：{workstation}",
            {"workstation_path": str(workstation)},
        )
    _validate_existing_workstation_home(workstation)
    todo_path = workstation / "TODO.md"
    todo_text: str | None = None
    todo_error: dict[str, Any] | None = None
    if not todo_path.is_file():
        problem = WorkstationProblem(
            "workstation_todo_missing",
            f"固定工位缺少 TODO.md：{todo_path}",
            {"todo_path": str(todo_path)},
        )
        if not tolerate_todo_errors:
            raise problem
        todo_error = {"code": problem.code, "detail": str(problem), **problem.details}
    else:
        try:
            todo_text = todo_path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            problem = WorkstationProblem(
                "workstation_todo_invalid_encoding",
                f"TODO.md 不是有效 UTF-8 文本：{todo_path}",
                {"todo_path": str(todo_path), "reason": str(exc)},
            )
            if not tolerate_todo_errors:
                raise problem from exc
            todo_error = {"code": problem.code, "detail": str(problem), **problem.details}
        except OSError as exc:
            problem = WorkstationProblem(
                "workstation_todo_unreadable",
                f"无法读取固定工位 TODO.md：{todo_path}",
                {"todo_path": str(todo_path), "reason": str(exc)},
            )
            if not tolerate_todo_errors:
                raise problem from exc
            todo_error = {"code": problem.code, "detail": str(problem), **problem.details}
    parsed_todo: dict[str, Any] = {}
    if todo_text is not None and todo_error is None:
        try:
            parsed_todo = parse_workstation_todo(todo_text)
        except WorkstationProblem as problem:
            if not tolerate_todo_errors:
                raise
            todo_error = {
                "code": problem.code,
                "detail": str(problem),
                **problem.details,
            }

    mailbox = workstation / "mailbox"
    messages = sorted(
        path.name for path in mailbox.glob("*.md")
    ) if mailbox.is_dir() else []
    notices = workstation / "notices"
    notice_files = sorted(
        path.name for path in notices.glob("notice-*.md")
    ) if notices.is_dir() else []
    return {
        "workstation_path": str(workstation),
        "entry_path": str(workstation / "ENTRY.md"),
        "entry_exists": (workstation / "ENTRY.md").is_file(),
        "todo_path": str(todo_path),
        "todo": parsed_todo,
        "todo_error": todo_error,
        "mailbox": {
            "path": str(mailbox),
            "ready": mailbox.is_dir(),
            "message_count": len(messages),
            "messages": messages,
        },
        "notices": {
            "path": str(notices),
            "ready": notices.is_dir(),
            "notice_count": len(notice_files),
            "notices": notice_files,
        },
    }
