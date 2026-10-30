from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


NOTE_SCHEMA = "attention-note/v0"
STATE_SCHEMA = "attention-state/v0"
MANIFEST_SCHEMA = "source-manifest/v0"
TASK_TYPES = {"thread_state", "commitment"}
DOMAIN_LABELS = {
    "work": "工作",
    "personal": "个人",
    "agent_ops": "Agent Ops",
}
SECRET_KEYS = {
    "token",
    "api_token",
    "access_token",
    "secret",
    "api_secret",
    "password",
    "api_key",
    "access_key",
    "private_key",
}
SECRET_BODY_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{12,}\b"),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
)


class ScanError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedNote:
    relative_path: str
    sha256: str
    size: int
    line_count: int
    metadata: dict[str, Any]
    title: str
    sections: dict[str, dict[str, Any]]

    @property
    def source_ref(self) -> dict[str, Any]:
        return {
            "path": self.relative_path,
            "sha256": self.sha256,
            "line_start": 1,
            "line_end": self.line_count,
        }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part) for part in inner.split(",")]
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_frontmatter(lines: list[str]) -> tuple[dict[str, Any], int]:
    if not lines or lines[0].strip() != "---":
        raise ScanError("缺少 YAML frontmatter")
    try:
        end_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ScanError("frontmatter 未闭合") from exc

    metadata: dict[str, Any] = {}
    for line_number, line in enumerate(lines[1:end_index], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():
            raise ScanError(f"第 {line_number} 行使用了嵌套 YAML；v0 只接受扁平字段")
        if ":" not in line:
            raise ScanError(f"第 {line_number} 行不是 key: value")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            raise ScanError(f"第 {line_number} 行字段名不合法")
        metadata[key] = parse_scalar(raw_value)
    return metadata, end_index


def extract_title(lines: list[str], body_start: int) -> str:
    for line in lines[body_start + 1 :]:
        if line.startswith("# "):
            return line[2:].strip()
    return "未命名笔记"


def extract_sections(lines: list[str], body_start: int) -> dict[str, dict[str, Any]]:
    headings: list[tuple[str, int]] = []
    for index, line in enumerate(lines[body_start + 1 :], start=body_start + 1):
        if line.startswith("## "):
            headings.append((line[3:].strip(), index))

    sections: dict[str, dict[str, Any]] = {}
    for position, (heading, index) in enumerate(headings):
        next_index = (
            headings[position + 1][1] if position + 1 < len(headings) else len(lines)
        )
        content_lines = lines[index + 1 : next_index]
        nonempty = [line.strip() for line in content_lines if line.strip()]
        bullets = [
            line[2:].strip()
            for line in nonempty
            if line.startswith("- ") and len(line) > 2
        ]
        paragraphs = [line for line in nonempty if not line.startswith("- ")]
        sections[heading] = {
            "text": " ".join(paragraphs).strip(),
            "bullets": bullets,
            "line_start": index + 1,
            "line_end": max(index + 1, next_index),
        }
    return sections


def contains_secret(metadata: dict[str, Any], text: str) -> bool:
    keys = {key.lower() for key in metadata}
    if keys.intersection(SECRET_KEYS):
        return True
    return any(pattern.search(text) for pattern in SECRET_BODY_PATTERNS)


def validate_metadata(metadata: dict[str, Any]) -> list[str]:
    required = {
        "schema",
        "id",
        "object_type",
        "domain",
        "project",
        "status",
        "review_state",
        "sensitivity",
        "updated",
    }
    errors = [f"缺少字段 {key}" for key in sorted(required - metadata.keys())]
    if metadata.get("schema") != NOTE_SCHEMA:
        errors.append(f"schema 必须是 {NOTE_SCHEMA}")
    if metadata.get("domain") not in DOMAIN_LABELS:
        errors.append("domain 必须是 work、personal 或 agent_ops")
    if metadata.get("review_state") not in {"candidate", "reviewed"}:
        errors.append("review_state 必须是 candidate 或 reviewed")
    return errors


def parse_note(path: Path, source_root: Path) -> ParsedNote:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    metadata, body_start = parse_frontmatter(lines)
    if contains_secret(metadata, text):
        raise ScanError("检测到密钥类字段或内容，整篇阻止摄取")
    validation_errors = validate_metadata(metadata)
    if validation_errors:
        raise ScanError("；".join(validation_errors))
    return ParsedNote(
        relative_path=path.relative_to(source_root).as_posix(),
        sha256=sha256_text(text),
        size=len(text.encode("utf-8")),
        line_count=max(1, len(lines)),
        metadata=metadata,
        title=extract_title(lines, body_start),
        sections=extract_sections(lines, body_start),
    )


def section_text(note: ParsedNote, name: str) -> str:
    return str(note.sections.get(name, {}).get("text", "")).strip()


def section_bullets(note: ParsedNote, name: str) -> list[str]:
    return list(note.sections.get(name, {}).get("bullets", []))


def normalized_base(note: ParsedNote) -> dict[str, Any]:
    metadata = note.metadata
    return {
        "id": metadata["id"],
        "object_type": metadata["object_type"],
        "scope": metadata.get("scope", "project"),
        "domain_code": metadata["domain"],
        "domain": DOMAIN_LABELS[metadata["domain"]],
        "project": metadata["project"],
        "thread": metadata.get("thread", ""),
        "status": metadata["status"],
        "review_state": metadata["review_state"],
        "sensitivity": metadata["sensitivity"],
        "updated": metadata["updated"],
        "title": note.title,
        "summary": section_text(note, "摘要"),
        "source_refs": [note.source_ref],
    }


def normalize_task(note: ParsedNote) -> dict[str, Any]:
    item = normalized_base(note)
    metadata = note.metadata
    item.update(
        {
            "kind": "task",
            "blocking": bool(metadata.get("blocking", False)),
            "external_commitment": bool(
                metadata.get("external_commitment", False)
            ),
            "long_term": bool(metadata.get("long_term", False)),
            "due_at": metadata.get("due_at"),
            "last_progress_at": metadata.get("last_progress_at"),
            "weekly_target": metadata.get("weekly_target"),
            "weekly_progress": metadata.get("weekly_progress"),
            "current_question": section_text(note, "当前唯一问题"),
            "deliverable": section_text(note, "阶段交付物"),
            "done_when": section_text(note, "完成定义"),
            "context": section_bullets(note, "上下文"),
        }
    )
    return item


def normalize_tip(note: ParsedNote) -> dict[str, Any]:
    item = normalized_base(note)
    item.update(
        {
            "kind": "tip",
            "why_keep": section_text(note, "为什么值得记"),
            "context": section_bullets(note, "上下文"),
        }
    )
    return item


def normalize_archive(note: ParsedNote) -> dict[str, Any]:
    item = normalized_base(note)
    item.update(
        {
            "epitaph": section_text(note, "项目墓志铭"),
            "why_stopped": section_text(note, "为什么停"),
            "reusable": section_bullets(note, "留下什么"),
            "restart_when": section_text(note, "值得重启的条件"),
            "first_hour": section_text(note, "第一小时"),
        }
    )
    return item


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def candidate_id(kind: str, seed: str) -> str:
    digest = hashlib.sha256(f"{kind}|{seed}".encode("utf-8")).hexdigest()[:12]
    return f"candidate-{kind}-{digest}"


def make_candidate(
    kind: str,
    reason: str,
    notes: list[ParsedNote],
    project: str,
    domain_code: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seed = "|".join(note.relative_path for note in notes)
    return {
        "id": candidate_id(kind, seed),
        "candidate_type": kind,
        "status": "candidate",
        "reason": reason,
        "project": project,
        "domain_code": domain_code,
        "domain": DOMAIN_LABELS.get(domain_code, domain_code),
        "details": details or {},
        "source_refs": [note.source_ref for note in notes],
    }


def build_rule_candidates(notes: list[ParsedNote], now: datetime) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for note in notes:
        metadata = note.metadata
        project = str(metadata.get("project", ""))
        domain_code = str(metadata.get("domain", ""))

        if project in {"", "unassigned", "未归类"}:
            candidates.append(
                make_candidate(
                    "scope_missing",
                    "对象尚未归属明确项目；不得进入项目默认上下文",
                    [note],
                    project or "unassigned",
                    domain_code,
                )
            )

        if metadata.get("review_state") == "candidate":
            candidates.append(
                make_candidate(
                    "source_declared_candidate",
                    "来源笔记自身标记为 candidate，需人工审核后才能升级",
                    [note],
                    project,
                    domain_code,
                    {"object_type": metadata.get("object_type")},
                )
            )

        if metadata.get("long_term"):
            last_progress = parse_datetime(metadata.get("last_progress_at"))
            weekly_target = int(metadata.get("weekly_target") or 0)
            weekly_progress = int(metadata.get("weekly_progress") or 0)
            debt_days = (now - last_progress).days if last_progress else 0
            if debt_days >= 7 or weekly_progress < weekly_target:
                candidates.append(
                    make_candidate(
                        "progress_debt",
                        "长期项目超过七天未推进或本周目标尚未完成",
                        [note],
                        project,
                        domain_code,
                        {
                            "debt_days": debt_days,
                            "weekly_progress": weekly_progress,
                            "weekly_target": weekly_target,
                        },
                    )
                )

        due_at = parse_datetime(metadata.get("due_at"))
        if due_at and due_at < now and metadata.get("status") == "active":
            candidates.append(
                make_candidate(
                    "overdue",
                    "活动任务已超过来源声明的截止时间",
                    [note],
                    project,
                    domain_code,
                    {"due_at": metadata.get("due_at")},
                )
            )

    decisions: dict[str, list[ParsedNote]] = {}
    for note in notes:
        if note.metadata.get("object_type") != "decision":
            continue
        key = str(note.metadata.get("decision_key", ""))
        if key:
            decisions.setdefault(key, []).append(note)

    for decision_key, grouped_notes in decisions.items():
        active_notes = [
            note
            for note in grouped_notes
            if note.metadata.get("status") not in {"superseded", "archived"}
        ]
        values = {
            str(note.metadata.get("decision_value", "")) for note in active_notes
        }
        if len(active_notes) > 1 and len(values) > 1:
            candidates.append(
                make_candidate(
                    "conflict",
                    "同一 decision_key 存在多个未失效且取值不同的对象",
                    active_notes,
                    str(active_notes[0].metadata.get("project", "")),
                    str(active_notes[0].metadata.get("domain", "")),
                    {
                        "decision_key": decision_key,
                        "values": sorted(values),
                    },
                )
            )

    dedupe_groups: dict[str, list[ParsedNote]] = {}
    for note in notes:
        dedupe_key = str(note.metadata.get("dedupe_key", ""))
        if dedupe_key:
            dedupe_groups.setdefault(dedupe_key, []).append(note)
    for dedupe_key, grouped_notes in dedupe_groups.items():
        if len(grouped_notes) > 1:
            candidates.append(
                make_candidate(
                    "duplicate",
                    "多个来源声明了相同 dedupe_key，建议人工合并或保留差异",
                    grouped_notes,
                    str(grouped_notes[0].metadata.get("project", "")),
                    str(grouped_notes[0].metadata.get("domain", "")),
                    {"dedupe_key": dedupe_key},
                )
            )

    return sorted(candidates, key=lambda item: (item["candidate_type"], item["id"]))


def manifest_from_source(source_root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(source_root.rglob("*.md")):
        if path.is_symlink():
            continue
        text = path.read_text(encoding="utf-8")
        files.append(
            {
                "path": path.relative_to(source_root).as_posix(),
                "sha256": sha256_text(text),
                "size": len(text.encode("utf-8")),
            }
        )
    return {"schema": MANIFEST_SCHEMA, "files": files}


def load_manifest(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {"schema": MANIFEST_SCHEMA, "files": []}
    return json.loads(path.read_text(encoding="utf-8"))


def compare_manifests(
    previous: dict[str, Any], current: dict[str, Any]
) -> dict[str, list[str]]:
    previous_files = {item["path"]: item["sha256"] for item in previous["files"]}
    current_files = {item["path"]: item["sha256"] for item in current["files"]}
    previous_paths = set(previous_files)
    current_paths = set(current_files)
    return {
        "added": sorted(current_paths - previous_paths),
        "modified": sorted(
            path
            for path in current_paths.intersection(previous_paths)
            if current_files[path] != previous_files[path]
        ),
        "deleted": sorted(previous_paths - current_paths),
        "unchanged": sorted(
            path
            for path in current_paths.intersection(previous_paths)
            if current_files[path] == previous_files[path]
        ),
    }


def scan_vault(
    source_root: Path,
    now: datetime,
    previous_manifest: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ScanError(f"来源目录不存在：{source_root}")

    current_manifest = manifest_from_source(source_root)
    changes = compare_manifests(
        previous_manifest or {"schema": MANIFEST_SCHEMA, "files": []},
        current_manifest,
    )

    notes: list[ParsedNote] = []
    source_index: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []

    for file_info in current_manifest["files"]:
        path = source_root / file_info["path"]
        try:
            note = parse_note(path, source_root)
        except (ScanError, UnicodeDecodeError) as exc:
            source_index.append(
                {
                    **file_info,
                    "ingest_status": "blocked",
                    "blocked_reason": str(exc),
                }
            )
            warnings.append({"path": file_info["path"], "warning": str(exc)})
            continue
        notes.append(note)
        source_index.append(
            {
                **file_info,
                "ingest_status": "indexed",
                "object_id": note.metadata["id"],
                "object_type": note.metadata["object_type"],
                "domain_code": note.metadata["domain"],
                "project": note.metadata["project"],
            }
        )

    tasks: list[dict[str, Any]] = []
    tips: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    archives: list[dict[str, Any]] = []
    source_objects: list[dict[str, Any]] = []

    for note in notes:
        object_type = str(note.metadata["object_type"])
        normalized = normalized_base(note)
        source_objects.append(normalized)
        if object_type in TASK_TYPES and note.metadata.get("attention", False):
            tasks.append(normalize_task(note))
        elif object_type == "tip":
            tips.append(normalize_tip(note))
        elif object_type == "project_profile":
            projects.append(
                {
                    **normalized,
                    "stage": note.metadata.get("stage", ""),
                    "first_task": section_text(note, "当前唯一任务"),
                    "constraints": section_bullets(note, "关键约束"),
                }
            )
        elif object_type == "archive_project":
            archives.append(normalize_archive(note))

    review_candidates = build_rule_candidates(notes, now)
    state = {
        "schema": STATE_SCHEMA,
        "generated_at": now.isoformat(),
        "data_scope": "synthetic-only",
        "source_root": source_root.as_posix(),
        "scan_summary": {
            "markdown_files": len(current_manifest["files"]),
            "indexed_files": sum(
                1 for item in source_index if item["ingest_status"] == "indexed"
            ),
            "blocked_files": sum(
                1 for item in source_index if item["ingest_status"] == "blocked"
            ),
            "tasks": len(tasks),
            "tips": len(tips),
            "projects": len(projects),
            "archives": len(archives),
            "review_candidates": len(review_candidates),
        },
        "changes": changes,
        "tasks": sorted(tasks, key=lambda item: item["id"]),
        "tips": sorted(tips, key=lambda item: item["id"]),
        "projects": sorted(projects, key=lambda item: item["id"]),
        "archives": sorted(archives, key=lambda item: item["id"]),
        "source_objects": sorted(source_objects, key=lambda item: item["id"]),
        "review_candidates": review_candidates,
        "source_index": sorted(source_index, key=lambda item: item["path"]),
        "warnings": warnings,
    }
    current_manifest["generated_at"] = now.isoformat()
    current_manifest["source_root"] = source_root.as_posix()
    return state, current_manifest


def ensure_output_outside_source(source_root: Path, target: Path) -> None:
    source = source_root.resolve()
    resolved_target = target.resolve()
    if resolved_target == source or source in resolved_target.parents:
        raise ScanError("输出位置不能位于来源 Vault 内，避免污染或递归摄取")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_report(state: dict[str, Any]) -> str:
    summary = state["scan_summary"]
    changes = state["changes"]
    lines = [
        "# Markdown 记忆管道扫描报告",
        "",
        f"- 生成时间：{state['generated_at']}",
        f"- 数据范围：{state['data_scope']}",
        f"- Markdown：{summary['markdown_files']} 个",
        f"- 已索引：{summary['indexed_files']} 个",
        f"- 阻止摄取：{summary['blocked_files']} 个",
        f"- 任务：{summary['tasks']} 个",
        f"- Tips：{summary['tips']} 个",
        f"- 审核候选：{summary['review_candidates']} 个",
        "",
        "## 变化",
        "",
        f"- 新增：{len(changes['added'])}",
        f"- 修改：{len(changes['modified'])}",
        f"- 删除：{len(changes['deleted'])}",
        f"- 未变化：{len(changes['unchanged'])}",
        "",
        "## 审核候选",
        "",
    ]
    for candidate in state["review_candidates"]:
        lines.append(
            f"- `{candidate['candidate_type']}` · {candidate['project']}："
            f"{candidate['reason']}（来源 {len(candidate['source_refs'])} 个）"
        )
    if not state["review_candidates"]:
        lines.append("- 无")
    lines.extend(["", "## 警告", ""])
    for warning in state["warnings"]:
        lines.append(f"- `{warning['path']}`：{warning['warning']}")
    if not state["warnings"]:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def run_scan(
    source: Path,
    output: Path,
    manifest_path: Path,
    report_path: Path,
    now: datetime,
    dry_run: bool,
    previous_path: Path | None = None,
) -> dict[str, Any]:
    ensure_output_outside_source(source, output)
    ensure_output_outside_source(source, manifest_path)
    ensure_output_outside_source(source, report_path)
    previous = load_manifest(previous_path or manifest_path)
    state, manifest = scan_vault(source, now, previous)
    if not dry_run:
        write_json(output, state)
        write_json(manifest_path, manifest)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(build_report(state), encoding="utf-8")
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只读扫描合成 Markdown Vault，生成带来源的候选对象。"
    )
    parser.add_argument("--source", type=Path, default=Path("synthetic-vault"))
    parser.add_argument(
        "--output", type=Path, default=Path("build/attention-state.json")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("build/source-manifest.json")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("build/scan-report.md")
    )
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--now",
        default="2026-07-29T09:00:00+08:00",
        help="实验参考时间，ISO 8601。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = parse_datetime(args.now)
    if now is None:
        raise ScanError("--now 必须是合法 ISO 8601 时间")
    state = run_scan(
        source=args.source,
        output=args.output,
        manifest_path=args.manifest,
        report_path=args.report,
        now=now,
        dry_run=args.dry_run,
        previous_path=args.previous,
    )
    print(json.dumps(state["scan_summary"], ensure_ascii=False, indent=2))
    print(json.dumps(state["changes"], ensure_ascii=False, indent=2))
    if args.dry_run:
        print("DRY RUN：未写入任何输出文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

