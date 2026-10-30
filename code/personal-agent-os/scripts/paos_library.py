"""Filesystem-only V1.1 Workflow / Skill Library helpers.

Source truth stays in human-readable Markdown plus append-only Skill usage
events. Generated catalogs are rebuildable views and never become a second
authority source.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable


WORKFLOW_SCHEMA = "paos-workflow/v1"
SKILL_SCHEMA = "paos-skill/v1"
CATALOG_SCHEMA = "paos-library-catalog/v1"
SKILL_USAGE_SCHEMA = "paos-skill-usage/v1"
from paos_home import posix_windows_drive_locator

LIBRARY_ROOTS_SCHEMA = "paos-library-roots/v1"
DEFAULT_LIBRARY_ROOTS_PATH = Path.home() / ".paos" / "library-roots.json"
GENERATED_MARKER = "<!-- PAOS GENERATED CATALOG: DO NOT EDIT -->"
SKILL_SCORE_VALUES = {0.0, 0.3, 0.5, 1.0}
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")
_WINDOWS_DRIVE_LOCATOR_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")


class LibraryProblem(RuntimeError):
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
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_id(value: str, *, label: str) -> str:
    text = str(value or "").strip()
    if not _ID_RE.fullmatch(text):
        raise LibraryProblem(
            "library_id_invalid",
            f"{label} 必须使用 2–80 位小写字母、数字、点、下划线或短横线。",
            {"value": text},
        )
    return text


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise LibraryProblem(
            "library_write_failed",
            f"无法写入 Library 文件：{path}",
            {"path": str(path), "os_error": str(exc)},
        ) from exc


def _write_if_absent(path: Path, text: str) -> bool:
    if path.exists():
        if not path.is_file():
            raise LibraryProblem(
                "library_layout_conflict",
                f"保留文件路径被非文件对象占用：{path}",
                {"path": str(path)},
            )
        return False
    _atomic_write_text(path, text)
    return True


def _ensure_dir(path: Path) -> bool:
    if path.exists():
        if not path.is_dir():
            raise LibraryProblem(
                "library_layout_conflict",
                f"保留目录路径被文件占用：{path}",
                {"path": str(path)},
            )
        return False
    path.mkdir(parents=True)
    return True


def _ensure_root(root: Path) -> bool:
    if root.exists():
        if not root.is_dir():
            raise LibraryProblem(
                "library_root_invalid",
                f"Library 根路径不是目录：{root}",
                {"root_path": str(root)},
            )
        return False
    root.mkdir(parents=True)
    return True


def workflow_readme() -> str:
    return """# Workflow Library

共享工作方法库。这里保存可复用的 Guide、Workflow 与 Template；Project 正文与 Agent 工位不放在这里。

- `Guides/`：跨项目工作原则与协作指南
- `Workflows/`：可执行的工作流程定义
- `Templates/`：Workflow 使用的可复用模板
- `CATALOG.md`：PAOS 根据 Markdown 元数据生成的目录，可重建

被 PAOS 识别的 Workflow 文档使用扁平 frontmatter：

```markdown
---
schema: paos-workflow/v1
id: example-workflow
title: Example Workflow
description: One-line purpose.
tags: planning, review
status: active
---
```
"""


def skill_readme() -> str:
    return """# Skill Library

共享 Agent Skill 库。每个 Skill 使用稳定目录名，并以 `SKILL.md` 作为入口；动态使用统计不写进文件名。

```text
<Skill Library>/
├─ <skill-id>/
│  └─ SKILL.md
├─ CATALOG.md
└─ .paos/
   ├─ catalog.json
   └─ usage-events/
```

被 PAOS 识别的 Skill 使用扁平 frontmatter：

```markdown
---
schema: paos-skill/v1
id: example-skill
title: Example Skill
description: What this skill helps an Agent do.
tags: writing, review
version: 1
status: active
---
```

Agent 调用 Skill 后可记录 0 / 0.3 / 0.5 / 1 的价值分。PAOS 将使用次数、30 天热度、最近使用时间、跨 Project 数量与平均价值作为派生统计写入 Catalog。
"""


def ensure_workflow_library(root: Path) -> dict[str, Any]:
    root = Path(root)
    created: list[str] = []
    if _ensure_root(root):
        created.append(str(root))
    for name in ("Guides", "Workflows", "Templates", ".paos"):
        path = root / name
        if _ensure_dir(path):
            created.append(str(path))
    if _write_if_absent(root / "README.md", workflow_readme()):
        created.append(str(root / "README.md"))
    return {"kind": "workflow", "root_path": str(root), "created_paths": created}


def ensure_skill_library(root: Path) -> dict[str, Any]:
    root = Path(root)
    created: list[str] = []
    if _ensure_root(root):
        created.append(str(root))
    for path in (root / ".paos", root / ".paos" / "usage-events"):
        if _ensure_dir(path):
            created.append(str(path))
    if _write_if_absent(root / "README.md", skill_readme()):
        created.append(str(root / "README.md"))
    return {"kind": "skill", "root_path": str(root), "created_paths": created}


def _unquote_flat_value(value: str) -> str:
    """Read one flat frontmatter scalar without becoming a YAML parser.

    A complete pair of matching outer quotes is syntax, so remove it and
    decode only the escapes that YAML/JSON string values normally carry.
    Bare values are returned unchanged.
    """
    if len(value) < 2 or value[0] != value[-1] or value[0] not in {'"', "'"}:
        return value
    if value[0] == '"':
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        return decoded if isinstance(decoded, str) else value
    return value[1:-1].replace("''", "'")


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        key, sep, value = line.partition(":")
        if sep:
            result[key.strip()] = _unquote_flat_value(value.strip())
    return result if closed else {}


ABSORBED_NOTE_KEYS = {"tip_id", "source_sha256", "evidence_ref"}
_TIP_ID_RE = re.compile(r"^tip-[A-Za-z0-9_-]{1,120}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_absorbed_tips(raw_value: str, *, path: str = "") -> list[dict[str, str]]:
    """Shared strict parser for the optional absorbed_tips provenance note."""
    try:
        value = json.loads(raw_value)
    except (json.JSONDecodeError, TypeError) as error:
        raise LibraryProblem(
            "library_absorbed_tips_invalid", "absorbed_tips 不是合法 JSON。", {"path": path}
        ) from error
    if not isinstance(value, list) or not value:
        raise LibraryProblem(
            "library_absorbed_tips_invalid", "absorbed_tips 必须是非空 JSON 数组。", {"path": path}
        )
    notes: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != ABSORBED_NOTE_KEYS:
            raise LibraryProblem(
                "library_absorbed_tips_invalid", "absorbed_tips 对象字段不准确。", {"path": path}
            )
        tip_id = entry.get("tip_id")
        source_sha = entry.get("source_sha256")
        evidence = entry.get("evidence_ref")
        if not isinstance(tip_id, str) or not _TIP_ID_RE.fullmatch(tip_id):
            raise LibraryProblem("library_absorbed_tips_invalid", "absorbed_tips tip_id 无效。", {"path": path})
        if not isinstance(source_sha, str) or not _SHA256_RE.fullmatch(source_sha):
            raise LibraryProblem("library_absorbed_tips_invalid", "absorbed_tips source_sha256 无效。", {"path": path})
        if (
            not isinstance(evidence, str)
            or not evidence.strip()
            or len(evidence) > 1000
            or "\x00" in evidence
        ):
            raise LibraryProblem("library_absorbed_tips_invalid", "absorbed_tips evidence_ref 无效。", {"path": path})
        key = (tip_id, source_sha)
        if key in seen:
            raise LibraryProblem("library_absorbed_tips_invalid", "absorbed_tips 含重复来源。", {"path": path})
        seen.add(key)
        notes.append({"tip_id": tip_id, "source_sha256": source_sha, "evidence_ref": evidence.strip()})
    return notes


def _tags(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


_BLOCK_SCALAR_RE = re.compile(r"^[|>](?:[+-]?[1-9]?|[1-9]?[+-]?)$")


def _unsupported_block_scalar(text: str) -> tuple[str, str, int] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line_number, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return None
        key, sep, value = line.partition(":")
        raw_value = value.strip()
        header = re.split(r"\s+#", raw_value, maxsplit=1)[0].strip()
        if sep and _BLOCK_SCALAR_RE.fullmatch(header):
            return key.strip(), raw_value, line_number
    return None


def _record_skipped(
    skipped: list[dict[str, Any]] | None,
    *,
    path: Path,
    relative_path: str,
    reason: str,
    **details: Any,
) -> None:
    if skipped is None:
        return
    entry: dict[str, Any] = {
        "path": str(path),
        "relative_path": relative_path,
        "reason": reason,
    }
    entry.update(details)
    skipped.append(entry)


def _read_metadata(
    path: Path,
    expected_schema: str,
    *,
    skipped: list[dict[str, Any]] | None = None,
    relative_path: str = "",
) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LibraryProblem(
            "library_document_unreadable",
            f"Library 文档不可读取：{path}",
            {"path": str(path), "cause": str(exc)},
        ) from exc
    meta = parse_frontmatter(text)
    if not meta:
        _record_skipped(
            skipped,
            path=path,
            relative_path=relative_path,
            reason="missing_frontmatter",
        )
        return None
    if meta.get("schema") != expected_schema:
        _record_skipped(
            skipped,
            path=path,
            relative_path=relative_path,
            reason="schema_missing" if not meta.get("schema") else "schema_mismatch",
            expected_schema=expected_schema,
            actual_schema=str(meta.get("schema") or ""),
        )
        return None
    block_scalar = _unsupported_block_scalar(text)
    if block_scalar is not None:
        field, value, line_number = block_scalar
        raise LibraryProblem(
            "library_frontmatter_block_scalar_unsupported",
            f"Library frontmatter 使用不支持的裸块标量：{path} 字段 {field}",
            {
                "path": str(path),
                "relative_path": relative_path,
                "field": field,
                "value": value,
                "line": line_number,
            },
        )
    item_id = _validate_id(meta.get("id", ""), label="Library item id")
    title = meta.get("title", "").strip()
    if not title:
        raise LibraryProblem(
            "library_metadata_invalid",
            f"Library 文档缺少 title：{path}",
            {"path": str(path), "id": item_id},
        )
    item = {
        "id": item_id,
        "title": title,
        "description": meta.get("description", "").strip(),
        "tags": _tags(meta.get("tags", "")),
        "status": meta.get("status", "active").strip() or "active",
        "version": meta.get("version", "").strip(),
        "path": str(path),
    }
    if "absorbed_tips" in meta:
        if "status" not in meta:
            raise LibraryProblem(
                "library_absorbed_tips_invalid",
                "带 absorbed_tips 注记的正文必须显式声明 status。",
                {"path": str(path), "id": item_id},
            )
        item["absorbed_tips"] = validate_absorbed_tips(meta["absorbed_tips"], path=str(path))
    return item


def scan_workflows(
    root: Path,
    *,
    skipped: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root = Path(root)
    items: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for directory in ("Guides", "Workflows", "Templates"):
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            relative_path = str(path.relative_to(root))
            item = _read_metadata(
                path,
                WORKFLOW_SCHEMA,
                skipped=skipped,
                relative_path=relative_path,
            )
            if item is None:
                continue
            if item["id"] in seen:
                raise LibraryProblem(
                    "library_duplicate_id",
                    f"Workflow id 重复：{item['id']}",
                    {"first_path": seen[item["id"]], "second_path": str(path)},
                )
            seen[item["id"]] = str(path)
            item["section"] = directory
            item["relative_path"] = relative_path
            items.append(item)
    return sorted(items, key=lambda item: item["id"])


def scan_skills(
    root: Path,
    *,
    skipped: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root = Path(root)
    items: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for path in sorted(root.glob("*/SKILL.md")):
        relative_path = str(path.relative_to(root))
        item = _read_metadata(
            path,
            SKILL_SCHEMA,
            skipped=skipped,
            relative_path=relative_path,
        )
        if item is None:
            continue
        if path.parent.name != item["id"]:
            raise LibraryProblem(
                "skill_directory_id_mismatch",
                f"Skill 目录名必须与 id 一致：{item['id']}",
                {
                    "skill_id": item["id"],
                    "directory": path.parent.name,
                    "path": str(path),
                },
            )
        if item["id"] in seen:
            raise LibraryProblem(
                "library_duplicate_id",
                f"Skill id 重复：{item['id']}",
                {"first_path": seen[item["id"]], "second_path": str(path)},
            )
        seen[item["id"]] = str(path)
        item["relative_path"] = relative_path
        items.append(item)
    return sorted(items, key=lambda item: item["id"])


def _read_usage_events(root: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    event_root = Path(root) / ".paos" / "usage-events"
    if not event_root.is_dir():
        return events
    for path in sorted(event_root.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LibraryProblem(
                "skill_usage_event_invalid",
                f"Skill usage event 无法读取：{path}",
                {"path": str(path), "cause": str(exc)},
            ) from exc
        if not isinstance(value, dict) or value.get("schema") != SKILL_USAGE_SCHEMA:
            raise LibraryProblem(
                "skill_usage_event_invalid",
                f"Skill usage event schema 无效：{path}",
                {"path": str(path)},
            )
        events.append(value)
    return events


def _parse_iso(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_skill_stats(
    skills: Iterable[dict[str, Any]],
    events: Iterable[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=30)
    stats: dict[str, dict[str, Any]] = {
        item["id"]: {
            "uses": 0,
            "uses_30d": 0,
            "last_used_at": "",
            "usefulness_total": 0.0,
            "usefulness_avg": None,
            "project_count": 0,
            "agent_count": 0,
            "_projects": set(),
            "_agents": set(),
        }
        for item in skills
    }
    for event in events:
        skill_id = str(event.get("skill_id") or "")
        if skill_id not in stats:
            continue
        item = stats[skill_id]
        score = float(event.get("score") or 0.0)
        item["uses"] += 1
        item["usefulness_total"] += score
        used_at = str(event.get("used_at") or "")
        parsed = _parse_iso(used_at)
        if parsed is not None and parsed >= cutoff:
            item["uses_30d"] += 1
        if used_at and used_at > item["last_used_at"]:
            item["last_used_at"] = used_at
        project_id = str(event.get("project_id") or "").strip()
        agent_id = str(event.get("agent_id") or "").strip()
        if project_id:
            item["_projects"].add(project_id)
        if agent_id:
            item["_agents"].add(agent_id)
    for item in stats.values():
        item["project_count"] = len(item.pop("_projects"))
        item["agent_count"] = len(item.pop("_agents"))
        if item["uses"]:
            item["usefulness_avg"] = round(item["usefulness_total"] / item["uses"], 3)
        item["usefulness_total"] = round(item["usefulness_total"], 3)
    return stats


def _catalog_json(
    kind: str,
    root: Path,
    items: list[dict[str, Any]],
    skipped: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": CATALOG_SCHEMA,
        "kind": kind,
        "root_path": str(root),
        "generated_at": utc_now_iso(),
        "items": items,
        "skipped": list(skipped or []),
    }


def _safe_publish_generated(path: Path, text: str) -> None:
    if path.exists():
        if not path.is_file():
            raise LibraryProblem(
                "library_catalog_conflict",
                f"Catalog 路径被非文件占用：{path}",
                {"path": str(path)},
            )
        try:
            existing = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise LibraryProblem(
                "library_catalog_conflict",
                f"无法确认现有 Catalog 是否由 PAOS 生成：{path}",
                {"path": str(path), "cause": str(exc)},
            ) from exc
        if GENERATED_MARKER not in existing:
            raise LibraryProblem(
                "library_catalog_conflict",
                "现有 CATALOG.md 不是 PAOS 生成文件，拒绝覆盖。",
                {"path": str(path)},
            )
    _atomic_write_text(path, text)


def _md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_workflow_catalog(items: list[dict[str, Any]]) -> str:
    lines = [
        GENERATED_MARKER,
        "# Workflow Catalog",
        "",
        f"共 {len(items)} 项。源文件是权威；本页可随时重建。",
        "",
        "| ID | Title | Section | Status | Tags | Path |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| {id} | {title} | {section} | {status} | {tags} | {path} |".format(
                id=_md_escape(item["id"]),
                title=_md_escape(item["title"]),
                section=_md_escape(item.get("section", "")),
                status=_md_escape(item.get("status", "")),
                tags=_md_escape(", ".join(item.get("tags") or [])),
                path=_md_escape(item.get("relative_path", "")),
            )
        )
    return "\n".join(lines) + "\n"


def render_skill_catalog(items: list[dict[str, Any]]) -> str:
    lines = [
        GENERATED_MARKER,
        "# Skill Catalog",
        "",
        f"共 {len(items)} 项。Skill Markdown 与 usage event 是事实源；统计可重建。",
        "",
        "| Skill | Title | Status | Uses | 30d | Projects | Avg value | Last used | Path |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in items:
        avg = item.get("stats", {}).get("usefulness_avg")
        avg_text = "" if avg is None else str(avg)
        stats = item.get("stats") or {}
        lines.append(
            "| {id} | {title} | {status} | {uses} | {heat} | {projects} | {avg} | {last} | {path} |".format(
                id=_md_escape(item["id"]),
                title=_md_escape(item["title"]),
                status=_md_escape(item.get("status", "active")),
                uses=stats.get("uses", 0),
                heat=stats.get("uses_30d", 0),
                projects=stats.get("project_count", 0),
                avg=_md_escape(avg_text),
                last=_md_escape(stats.get("last_used_at", "")),
                path=_md_escape(item.get("relative_path", "")),
            )
        )
    return "\n".join(lines) + "\n"


def refresh_workflow_catalog(root: Path) -> dict[str, Any]:
    root = Path(root)
    ensure_workflow_library(root)
    skipped: list[dict[str, Any]] = []
    items = scan_workflows(root, skipped=skipped)
    payload = _catalog_json("workflow", root, items, skipped)
    _safe_publish_generated(root / "CATALOG.md", render_workflow_catalog(items))
    _atomic_write_text(
        root / ".paos" / "catalog.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return payload


def refresh_skill_catalog(root: Path) -> dict[str, Any]:
    root = Path(root)
    ensure_skill_library(root)
    skipped: list[dict[str, Any]] = []
    skills = scan_skills(root, skipped=skipped)
    events = _read_usage_events(root)
    stats = build_skill_stats(skills, events)
    enriched: list[dict[str, Any]] = []
    for item in skills:
        copy = dict(item)
        copy["stats"] = stats[item["id"]]
        enriched.append(copy)
    payload = _catalog_json("skill", root, enriched, skipped)
    _safe_publish_generated(root / "CATALOG.md", render_skill_catalog(enriched))
    _atomic_write_text(
        root / ".paos" / "catalog.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return payload


def record_skill_use(
    root: Path,
    *,
    skill_id: str,
    score: float,
    project_id: str = "",
    agent_id: str = "",
    work_id: str = "",
    note: str = "",
) -> dict[str, Any]:
    root = Path(root)
    ensure_skill_library(root)
    skill_id = _validate_id(skill_id, label="Skill id")
    score = float(score)
    if score not in SKILL_SCORE_VALUES:
        raise LibraryProblem(
            "skill_usage_score_invalid",
            "Skill 价值分只接受 0 / 0.3 / 0.5 / 1。",
            {"score": score},
        )
    skill_ids = {item["id"] for item in scan_skills(root)}
    if skill_id not in skill_ids:
        raise LibraryProblem(
            "skill_not_found",
            f"Skill 不存在：{skill_id}",
            {"skill_id": skill_id},
        )
    used_at = utc_now_iso()
    event = {
        "schema": SKILL_USAGE_SCHEMA,
        "event_id": "su-" + uuid.uuid4().hex,
        "skill_id": skill_id,
        "used_at": used_at,
        "score": score,
        "project_id": str(project_id or "").strip(),
        "agent_id": str(agent_id or "").strip(),
        "work_id": str(work_id or "").strip(),
        "note": str(note or "").strip(),
    }
    event_path = root / ".paos" / "usage-events" / f"{used_at.replace(':', '')}-{event['event_id']}.json"
    _atomic_write_text(
        event_path,
        json.dumps(event, ensure_ascii=False, indent=2) + "\n",
    )
    catalog = refresh_skill_catalog(root)
    return {
        "event": event,
        "event_path": str(event_path),
        "catalog": catalog,
    }


def _canonical_library_locator(value: str | Path) -> str:
    """Return a stable locator for registry storage.

    Windows drive paths are normalized to forward slashes so the same registry
    bytes can be read by native Windows and WSL. Other paths retain normal
    platform semantics and are resolved when validated.
    """
    text = str(value or "").strip()
    match = _WINDOWS_DRIVE_LOCATOR_RE.match(text)
    if not match:
        return text
    drive = match.group(1).upper()
    rest = re.sub(r"[\\/]+", "/", match.group(2)).strip("/")
    return f"{drive}:/{rest}" if rest else f"{drive}:/"


def _runtime_library_root_path(locator: str | Path) -> Path:
    """Resolve one stored locator to the path syntax of the current runtime.

    The registry remains host-stable. On POSIX/WSL, a Windows drive locator is
    mapped to /mnt/<drive>/... only for filesystem access/validation.
    """
    text = _canonical_library_locator(locator)
    match = _WINDOWS_DRIVE_LOCATOR_RE.match(text)
    if os.name != "nt" and match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/").lstrip("/")
        return Path(f"/mnt/{drive}/{rest}" if rest else f"/mnt/{drive}")
    return Path(text).expanduser()


def _validate_registered_library_root(root: Path, *, kind: str) -> Path:
    root = Path(root).expanduser()
    if not root.is_dir():
        raise LibraryProblem(
            "library_root_not_found",
            f"{kind} Library 根目录不存在：{root}",
            {"kind": kind, "root_path": str(root)},
        )
    required_files = ("README.md",)
    required_dirs = (
        ("Guides", "Workflows", "Templates", ".paos")
        if kind == "workflow"
        else (".paos", ".paos/usage-events")
    )
    missing = [
        name
        for name in required_files
        if not (root / name).is_file()
    ] + [
        name
        for name in required_dirs
        if not (root / name).is_dir()
    ]
    if missing:
        raise LibraryProblem(
            "library_root_not_initialized",
            f"{kind} Library 尚未完成初始化：{root}",
            {
                "kind": kind,
                "root_path": str(root),
                "missing_or_wrong_type": missing,
            },
        )
    return root.resolve()


def _validate_registered_library_locator(
    locator: str | Path,
    *,
    kind: str,
) -> tuple[str, Path]:
    canonical = _canonical_library_locator(locator)
    runtime_path = _runtime_library_root_path(canonical)
    resolved = _validate_registered_library_root(runtime_path, kind=kind)
    if _WINDOWS_DRIVE_LOCATOR_RE.match(canonical):
        return canonical, resolved
    return str(resolved), resolved


def load_library_roots(
    path: Path = DEFAULT_LIBRARY_ROOTS_PATH,
    *,
    validate_roots: bool = True,
) -> dict[str, Any]:
    """Load the installation-local canonical Workflow / Skill roots.

    A missing registry is a valid unregistered state. An existing but invalid
    registry fails visibly because silently dropping a configured library would
    produce misleading Workstation ENTRY files.
    """
    path = Path(path)
    if not path.exists():
        return {
            "schema": LIBRARY_ROOTS_SCHEMA,
            "registered": False,
            "config_path": str(path),
            "workflow_root": "",
            "skill_root": "",
            "tool_catalog": "",
        }
    if not path.is_file():
        raise LibraryProblem(
            "library_roots_config_invalid",
            f"Library roots 配置路径不是文件：{path}",
            {"config_path": str(path)},
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LibraryProblem(
            "library_roots_config_invalid",
            f"Library roots 配置无法读取：{path}",
            {"config_path": str(path), "cause": str(exc)},
        ) from exc
    if not isinstance(value, dict) or value.get("schema") != LIBRARY_ROOTS_SCHEMA:
        raise LibraryProblem(
            "library_roots_config_invalid",
            f"Library roots 配置 schema 无效：{path}",
            {"config_path": str(path)},
        )

    workflow_raw = str(value.get("workflow_root") or "").strip()
    skill_raw = str(value.get("skill_root") or "").strip()
    if not workflow_raw or not skill_raw:
        raise LibraryProblem(
            "library_roots_config_invalid",
            "Library roots 配置必须同时登记 Workflow 与 Skill 根目录。",
            {"config_path": str(path)},
        )

    workflow_locator = _canonical_library_locator(workflow_raw)
    skill_locator = _canonical_library_locator(skill_raw)
    if validate_roots:
        workflow_locator, _ = _validate_registered_library_locator(
            workflow_locator, kind="workflow"
        )
        skill_locator, _ = _validate_registered_library_locator(
            skill_locator, kind="skill"
        )
    else:
        if not _WINDOWS_DRIVE_LOCATOR_RE.match(workflow_locator):
            workflow_locator = str(Path(workflow_locator).expanduser())
        if not _WINDOWS_DRIVE_LOCATOR_RE.match(skill_locator):
            skill_locator = str(Path(skill_locator).expanduser())

    return {
        "schema": LIBRARY_ROOTS_SCHEMA,
        "registered": True,
        "config_path": str(path),
        "workflow_root": workflow_locator,
        "skill_root": skill_locator,
        "tool_catalog": str(value.get("tool_catalog") or "").strip(),
        "registered_at": str(value.get("registered_at") or ""),
    }


def tool_catalog_stored_locator(raw: str | Path) -> str:
    """Return the stable absolute locator used for registry storage.

    Rejects relative paths; converts /mnt/<drive>/... and Windows paths to the
    canonical C:/... form so one registry works from Windows and WSL.
    """
    text = str(raw or "").strip()
    if not text:
        raise LibraryProblem("tool_catalog_invalid", "Tool Catalog path 不能为空。")
    if _WINDOWS_DRIVE_LOCATOR_RE.match(text):
        return _canonical_library_locator(text)
    if text.startswith("/mnt/") and len(text) > 6 and text[5].isalpha() and text[6] == "/":
        return _canonical_library_locator(f"{text[5].upper()}:/{text[7:]}")
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        raise LibraryProblem("tool_catalog_invalid", "Tool Catalog 必须是绝对路径。", {"path": text})
    return _canonical_library_locator(str(candidate))


def _read_tool_catalog_schema(path: Path, *, label: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise LibraryProblem(
            "tool_catalog_unreadable", "Tool Catalog 原件无法读取。", {"path": label, "reason": type(error).__name__}
        ) from error
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LibraryProblem("tool_catalog_invalid", "Tool Catalog 不是有效 UTF-8。", {"path": label}) from error
    meta = parse_frontmatter(text.lstrip("\ufeff"))
    if meta.get("schema") != "paos-tool-catalog/v1":
        raise LibraryProblem(
            "tool_catalog_invalid", "Tool Catalog 的 schema 必须是 paos-tool-catalog/v1。", {"path": label}
        )
    return raw


def _validate_tool_catalog_file(locator: str | Path) -> str:
    """Validate an existing regular file and return its stable stored locator."""
    stored = tool_catalog_stored_locator(locator)
    runtime = _runtime_library_root_path(stored)
    if not runtime.exists():
        raise LibraryProblem("tool_catalog_missing", "Tool Catalog 原件不存在。", {"path": stored})
    if runtime.is_symlink() or not runtime.is_file():
        raise LibraryProblem("tool_catalog_conflict", "Tool Catalog 必须是普通文件。", {"path": stored})
    _read_tool_catalog_schema(runtime, label=stored)
    return stored


def register_library_roots(
    path: Path,
    *,
    workflow_root: Path | str,
    skill_root: Path | str,
    tool_catalog: str | None = None,
) -> dict[str, Any]:
    """Atomically register one canonical Workflow/Skill pair for this install.

    Registry bytes store stable locators; validation uses runtime-native paths.
    This lets a Windows-hosted installation keep one C:/... registry that is
    still verifiable from WSL via /mnt/<drive>/... access.
    """
    path = Path(path)
    workflow_locator, workflow_runtime = _validate_registered_library_locator(
        workflow_root, kind="workflow"
    )
    skill_locator, skill_runtime = _validate_registered_library_locator(
        skill_root, kind="skill"
    )
    if workflow_runtime == skill_runtime:
        raise LibraryProblem(
            "library_roots_same_path",
            "Workflow Library 与 Skill Library 必须使用两个独立根目录。",
            {"root_path": workflow_locator},
        )
    tool_locator = ""
    if tool_catalog is not None and str(tool_catalog).strip():
        tool_locator = _validate_tool_catalog_file(str(tool_catalog).strip())
    elif path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise LibraryProblem(
                "library_roots_config_invalid",
                f"Library roots 配置无法读取：{path}",
                {"config_path": str(path), "cause": type(error).__name__},
            ) from error
        if not isinstance(existing, dict):
            raise LibraryProblem(
                "library_roots_config_invalid",
                f"Library roots 配置必须是 JSON 对象：{path}",
                {"config_path": str(path)},
            )
        tool_locator = str(existing.get("tool_catalog") or "").strip()
    payload = {
        "schema": LIBRARY_ROOTS_SCHEMA,
        "workflow_root": workflow_locator,
        "skill_root": skill_locator,
        "tool_catalog": tool_locator,
        "registered_at": utc_now_iso(),
    }
    _atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return {
        **payload,
        "registered": True,
        "config_path": str(path),
    }


# ---- Registered Library resource search (D2.5) ----

_LIBRARY_SEARCH_FIELDS = (
    ("title", 10),
    ("id", 8),
    ("tags", 7),
    ("description", 5),
    ("headings", 3),
    ("body", 1),
)
_LIBRARY_SEARCH_MAX_QUERY_CHARS = 200
_LIBRARY_SEARCH_MAX_RESULTS = 50


def _read_library_search_document(
    path: Path,
    root: Path,
    *,
    kind: str,
    expected_schema: str,
) -> dict[str, Any] | None:
    """Read and hash one registered-library Markdown source exactly once."""
    root = Path(root).resolve()
    resolved = Path(path).resolve()
    try:
        relative_path = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise LibraryProblem(
            "library_search_path_escape",
            "Library 搜索遇到指向登记根目录之外的 Markdown 路径；已停止该次搜索。",
            {"library_kind": kind, "relative_path": Path(path).name},
        ) from exc
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise LibraryProblem(
            "library_search_source_unreadable",
            "登记 Library 中的资源无法读取；未返回不完整搜索结果。",
            {
                "library_kind": kind,
                "relative_path": relative_path,
                "cause": type(exc).__name__,
            },
        ) from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LibraryProblem(
            "library_search_source_unreadable",
            "登记 Library 资源不是合法 UTF-8；未返回不完整搜索结果。",
            {
                "library_kind": kind,
                "relative_path": relative_path,
                "cause": "UnicodeDecodeError",
            },
        ) from exc

    metadata = parse_frontmatter(text)
    if metadata.get("schema") != expected_schema:
        return None
    item_id = _validate_id(metadata.get("id", ""), label="Library item id")
    title = str(metadata.get("title") or "").strip()
    if not title:
        raise LibraryProblem(
            "library_metadata_invalid",
            "Library 搜索遇到缺少 title 的已声明资源。",
            {"library_kind": kind, "relative_path": relative_path, "id": item_id},
        )
    if kind == "skill" and Path(path).parent.name != item_id:
        raise LibraryProblem(
            "skill_directory_id_mismatch",
            "Skill 目录名与 frontmatter id 不一致；未将该项作为搜索结果。",
            {
                "skill_id": item_id,
                "directory": Path(path).parent.name,
                "relative_path": relative_path,
            },
        )

    lines = text.splitlines()
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    body_lines = lines[closing + 1:] if closing is not None else []
    body = "\n".join(body_lines).strip()
    headings = [
        match.group(1).strip()
        for line in body_lines
        if (match := re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line))
    ]
    tags = _tags(metadata.get("tags", ""))
    return {
        "id": item_id,
        "title": title,
        "description": str(metadata.get("description") or "").strip(),
        "tags": tags,
        "status": str(metadata.get("status") or "active").strip() or "active",
        "version": str(metadata.get("version") or "").strip(),
        "library_kind": kind,
        "relative_path": relative_path,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "headings": headings,
        "body": body,
    }


def search_library_resources(
    library_roots: dict[str, Any],
    query: str,
    *,
    kind: str = "all",
    limit: int = 20,
) -> dict[str, Any]:
    """Search active Markdown resources only under the registered Workflow/Skill roots.

    Matching is deterministic case-insensitive substring matching. Every distinct
    whitespace-separated query term must occur somewhere in a resource. The result
    contains explainable fields and exact relative locators, never source excerpts.
    """
    if not isinstance(library_roots, dict) or library_roots.get("schema") != LIBRARY_ROOTS_SCHEMA:
        raise LibraryProblem(
            "library_roots_config_invalid",
            "Library roots 配置 schema 无效。",
            {},
        )
    if not library_roots.get("registered"):
        raise LibraryProblem(
            "library_roots_not_registered",
            "当前安装未登记 Workflow/Skill Library；未回退到仓库、Inbox 或其他目录。",
            {},
        )
    if kind not in {"all", "workflow", "skill"}:
        raise LibraryProblem(
            "library_search_kind_invalid",
            "kind 只支持 all、workflow 或 skill。",
            {"kind": kind},
        )
    if type(limit) is not int or not 1 <= limit <= _LIBRARY_SEARCH_MAX_RESULTS:
        raise LibraryProblem(
            "library_search_limit_invalid",
            f"limit 必须是 1–{_LIBRARY_SEARCH_MAX_RESULTS} 的整数。",
            {"limit": limit},
        )
    if not isinstance(query, str):
        raise LibraryProblem("library_search_query_invalid", "q 必须是文本。", {})
    normalized_query = query.strip()
    if (
        not normalized_query
        or len(normalized_query) > _LIBRARY_SEARCH_MAX_QUERY_CHARS
        or "\x00" in normalized_query
    ):
        raise LibraryProblem(
            "library_search_query_invalid",
            f"q 必须是 1–{_LIBRARY_SEARCH_MAX_QUERY_CHARS} 个字符的非空文本。",
            {"max_chars": _LIBRARY_SEARCH_MAX_QUERY_CHARS},
        )
    terms: list[str] = []
    seen_terms: set[str] = set()
    for raw_term in normalized_query.split():
        folded = raw_term.casefold()
        if folded not in seen_terms:
            terms.append(raw_term)
            seen_terms.add(folded)
    if not terms:
        raise LibraryProblem("library_search_query_invalid", "q 不包含可检索词。", {})

    selected_kinds = ("workflow", "skill") if kind == "all" else (kind,)
    documents: list[dict[str, Any]] = []
    searched = {
        "workflow_active_documents": 0,
        "skill_active_documents": 0,
        "workflow_non_active_skipped": 0,
        "skill_non_active_skipped": 0,
    }
    seen_ids: dict[str, dict[str, str]] = {}
    for library_kind in selected_kinds:
        root_locator = str(library_roots.get(f"{library_kind}_root") or "").strip()
        if not root_locator:
            raise LibraryProblem(
                "library_roots_config_invalid",
                "登记的 Library 根目录缺失；未回退到其他来源。",
                {"library_kind": library_kind},
            )
        root = _validate_registered_library_root(
            _runtime_library_root_path(root_locator),
            kind=library_kind,
        )
        if library_kind == "workflow":
            paths = [
                path
                for directory in ("Guides", "Workflows", "Templates")
                for path in sorted((root / directory).rglob("*.md"))
            ]
            expected_schema = WORKFLOW_SCHEMA
        else:
            paths = sorted(root.glob("*/SKILL.md"))
            expected_schema = SKILL_SCHEMA

        for path in paths:
            document = _read_library_search_document(
                path,
                root,
                kind=library_kind,
                expected_schema=expected_schema,
            )
            if document is None:
                continue
            item_id = document["id"]
            prior = seen_ids.setdefault(library_kind, {})
            if item_id in prior:
                raise LibraryProblem(
                    "library_duplicate_id",
                    f"Library 资源 id 重复：{item_id}",
                    {
                        "library_kind": library_kind,
                        "first_path": prior[item_id],
                        "second_path": document["relative_path"],
                    },
                )
            prior[item_id] = document["relative_path"]
            if document["status"].casefold() != "active":
                searched[f"{library_kind}_non_active_skipped"] += 1
                continue
            searched[f"{library_kind}_active_documents"] += 1
            documents.append(document)

    weights = dict(_LIBRARY_SEARCH_FIELDS)
    matches: list[dict[str, Any]] = []
    for document in documents:
        field_values = {
            "title": document["title"],
            "id": document["id"],
            "tags": " ".join(document["tags"]),
            "description": document["description"],
            "headings": "\n".join(document["headings"]),
            "body": document["body"],
        }
        score = 0
        matched_fields: set[str] = set()
        term_matches: list[dict[str, Any]] = []
        every_term_matched = True
        for term in terms:
            folded = term.casefold()
            fields = [
                field
                for field, _weight in _LIBRARY_SEARCH_FIELDS
                if folded in str(field_values[field]).casefold()
            ]
            if not fields:
                every_term_matched = False
                break
            score += sum(weights[field] for field in fields)
            matched_fields.update(fields)
            term_matches.append({"term": term, "fields": fields})
        if not every_term_matched:
            continue
        matching_sections = [
            heading
            for heading in document["headings"]
            if any(term.casefold() in heading.casefold() for term in terms)
        ][:8]
        field_order = [field for field, _weight in _LIBRARY_SEARCH_FIELDS if field in matched_fields]
        strongest = ", ".join(field_order[:4])
        matches.append({
            "id": document["id"],
            "title": document["title"],
            "description": document["description"],
            "tags": document["tags"],
            "status": document["status"],
            "version": document["version"],
            "library_kind": document["library_kind"],
            "relative_path": document["relative_path"],
            "source_sha256": document["source_sha256"],
            "score": score,
            "matched_terms": terms,
            "matched_fields": field_order,
            "term_matches": term_matches,
            "matching_sections": matching_sections,
            "match_reason": (
                f"All {len(terms)} distinct query term(s) matched by "
                f"case-insensitive substring; matched fields: {strongest}."
            ),
        })

    matches.sort(
        key=lambda item: (
            -int(item["score"]),
            str(item["title"]).casefold(),
            str(item["library_kind"]),
            str(item["relative_path"]).casefold(),
        )
    )
    return {
        "schema": "paos-library-search/v1",
        "query": normalized_query,
        "query_terms": terms,
        "match_semantics": "case-insensitive substring; all distinct whitespace-separated terms must match",
        "kind": kind,
        "scope": {
            "basis": "installation-local registered Workflow/Skill Library roots only",
            "library_kinds_searched": list(selected_kinds),
            "reads": (
                ["Guides/*.md, Workflows/*.md, Templates/*.md with paos-workflow/v1 metadata"]
                if kind == "workflow"
                else ["<skill-id>/SKILL.md with paos-skill/v1 metadata"]
                if kind == "skill"
                else [
                    "Guides/*.md, Workflows/*.md, Templates/*.md with paos-workflow/v1 metadata",
                    "<skill-id>/SKILL.md with paos-skill/v1 metadata",
                ]
            ),
            "writes": [],
            "model_calls": 0,
            "source_excerpt_returned": False,
        },
        "searched": searched,
        "match_count": len(matches),
        "limit": limit,
        "truncated": len(matches) > limit,
        "items": matches[:limit],
    }
