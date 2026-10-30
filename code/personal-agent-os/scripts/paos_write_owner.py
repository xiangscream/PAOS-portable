"""Runtime-instance-local PAOS write-owner credentials for the Agent CLI."""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

WRITE_OWNER_LOCAL_SCHEMA = "paos-write-owner-local/v1"
_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class WriteOwnerProblem(RuntimeError):
    def __init__(self, code: str, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.hint = hint


def resolve_runtime_instance_id(explicit: str | None = None, *, required: bool) -> str:
    value = str(explicit or os.environ.get("PAOS_RUNTIME_INSTANCE_ID") or "").strip()
    if not value:
        if required:
            raise WriteOwnerProblem(
                "runtime_instance_id_required",
                "enter 必须绑定明确的 Runtime 实例。",
                "为当前 Runtime 生成一个稳定且唯一的 PAOS_RUNTIME_INSTANCE_ID；同一 Runtime 后续命令复用它，另一个进程使用新值。",
            )
        return ""
    if not _PATH_SEGMENT_RE.fullmatch(value):
        raise WriteOwnerProblem(
            "runtime_instance_id_invalid",
            "PAOS_RUNTIME_INSTANCE_ID 只能含字母、数字、点、下划线或短横线，且不能以标点开头。",
        )
    return value


def _path_segment(value: str, field: str) -> str:
    text = str(value or "").strip()
    if not _PATH_SEGMENT_RE.fullmatch(text):
        raise WriteOwnerProblem(
            "write_owner_identity_invalid",
            f"{field} 不能作为本机 write-owner 文件路径段。",
        )
    return text


def write_owner_path(project_id: str, agent_id: str, instance_id: str) -> Path:
    project = _path_segment(project_id, "project_id")
    agent = _path_segment(agent_id, "agent_id")
    instance = _path_segment(instance_id, "instance_id")
    return (
        Path.home()
        / ".paos"
        / "write-owners"
        / project
        / agent
        / f"{instance}.json"
    )


def load_write_owner(
    project_id: str, agent_id: str, instance_id: str
) -> dict[str, Any] | None:
    path = write_owner_path(project_id, agent_id, instance_id)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WriteOwnerProblem(
            "write_owner_local_record_invalid",
            f"Runtime 本机 write-owner 记录无法读取：{path}",
            "修复或移走该 Runtime 实例自己的记录后，重新执行 enter；不会从其他实例恢复 owner。",
        ) from exc
    if not isinstance(value, dict) or value.get("schema") != WRITE_OWNER_LOCAL_SCHEMA:
        raise WriteOwnerProblem(
            "write_owner_local_record_invalid",
            f"Runtime 本机 write-owner 记录 schema 无效：{path}",
        )
    expected = {
        "project_id": str(project_id),
        "agent_id": str(agent_id),
        "instance_id": str(instance_id),
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise WriteOwnerProblem(
            "write_owner_local_record_invalid",
            f"Runtime 本机 write-owner 记录身份不匹配：{path}",
        )
    owner_id = value.get("owner_id")
    generation = value.get("generation")
    if (
        not isinstance(owner_id, str)
        or not owner_id.strip()
        or isinstance(generation, bool)
        or not isinstance(generation, int)
        or generation < 1
    ):
        raise WriteOwnerProblem(
            "write_owner_local_record_invalid",
            f"Runtime 本机 write-owner 记录缺少有效 owner_id/generation：{path}",
        )
    return {"owner_id": owner_id.strip(), "generation": generation}


def save_write_owner(
    project_id: str,
    agent_id: str,
    instance_id: str,
    owner_id: str,
    generation: int,
) -> Path:
    path = write_owner_path(project_id, agent_id, instance_id)
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise WriteOwnerProblem(
            "write_owner_response_invalid", "enter 回执缺少有效 write_owner.owner_id。"
        )
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise WriteOwnerProblem(
            "write_owner_response_invalid", "enter 回执缺少有效 write_owner.generation。"
        )
    payload = {
        "schema": WRITE_OWNER_LOCAL_SCHEMA,
        "project_id": str(project_id),
        "agent_id": str(agent_id),
        "instance_id": str(instance_id),
        "owner_id": owner_id.strip(),
        "generation": generation,
    }
    temporary = path.with_name(f"{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise WriteOwnerProblem(
            "write_owner_local_store_failed",
            f"enter 成功，但 Runtime 本机 owner 凭据无法保存：{path}",
            "修复本机目录权限后，在同一 Runtime instance 再次执行 session enter；CLI 会绑定并保存新的当前 owner。",
        ) from exc
    return path


def _generation_override(explicit: int | None) -> int | None:
    value: Any = explicit
    if value is None:
        raw = os.environ.get("PAOS_WRITE_OWNER_GENERATION", "").strip()
        if raw:
            try:
                value = int(raw)
            except ValueError as exc:
                raise WriteOwnerProblem(
                    "write_owner_generation_invalid",
                    "PAOS_WRITE_OWNER_GENERATION 必须是正整数。",
                ) from exc
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise WriteOwnerProblem(
            "write_owner_generation_invalid",
            "write_owner_generation 必须是正整数。",
        )
    return value


def resolve_write_owner(
    project_id: str,
    agent_id: str,
    *,
    instance_id: str = "",
    explicit_owner_id: str | None = None,
    explicit_generation: int | None = None,
) -> dict[str, Any] | None:
    owner_id = str(explicit_owner_id or os.environ.get("PAOS_WRITE_OWNER_ID") or "").strip()
    generation = _generation_override(explicit_generation)
    local: dict[str, Any] | None = None
    if instance_id and (not owner_id or generation is None):
        local = load_write_owner(project_id, agent_id, instance_id)
    if owner_id:
        if generation is None and local and local["owner_id"] == owner_id:
            generation = local["generation"]
        if generation is None:
            raise WriteOwnerProblem(
                "write_owner_generation_required",
                "显式 write_owner_id 覆盖必须同时提供 generation，或匹配当前 Runtime 实例的本机记录。",
                "使用 --owner-generation/PAOS_WRITE_OWNER_GENERATION 配对显式 owner_id。",
            )
        return {"owner_id": owner_id, "generation": generation}
    if generation is not None:
        raise WriteOwnerProblem(
            "write_owner_id_required", "write_owner_generation 不能脱离 write_owner_id 使用。"
        )
    return local
