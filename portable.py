#!/usr/bin/env python3
"""PAOS Portable 的安装定位助手（仅标准库；不管理业务状态）。

plan/doctor 只读；init 只创建新配置和可重建目录，不覆盖现有安装。
配置沿用核心的两个 v1 schema。没有新增 Project/Home/Runtime 状态库。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCHEMAS = {"installation": "paos-installation/v1", "library-roots": "paos-library-roots/v1"}
PATH_FIELDS = {
    "installation": {"source_root", "data_root", "library_roots_config", "rooter_home", "agent_numbers_config"},
    "library-roots": {"workflow_root", "skill_root", "tool_catalog"},
}


class PortableError(ValueError):
    """带具体路径的可恢复配置错误；不将错误解释为未配置。"""


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise PortableError(f"无法读取 JSON 对象：{path} ({exc})") from exc
    if not isinstance(value, dict):
        raise PortableError(f"配置必须是 JSON 对象：{path}")
    return value


def local_dir(root: Path) -> Path:
    return root / "config" / "local"


def expected_configs(root: Path) -> dict[str, dict[str, Any]]:
    """只展开版本化模板；所有相对定位锚定仓库，而非当前工作目录。"""
    root = root.resolve()
    result = {}
    for name, schema in SCHEMAS.items():
        path = root / "config" / f"{name}.example.json"
        value = read_object(path)
        if value.get("schema") != schema:
            raise PortableError(f"模板 schema 不符：{path}，应为 {schema}")
        if set(value) - (PATH_FIELDS[name] | {"schema", "registered_at"}):
            raise PortableError(f"模板有未支持字段，停止而不是猜测：{path}")
        for field in PATH_FIELDS[name]:
            raw = value.get(field)
            if not isinstance(raw, str) or (not raw and field not in {"rooter_home", "agent_numbers_config"}):
                raise PortableError(f"{path}: {field} 必须是有效路径字符串")
            if raw.startswith("<PAOS_ROOT>/"):
                candidate = (root / raw[len("<PAOS_ROOT>/"):]).resolve()
                if not candidate.is_relative_to(root):
                    raise PortableError(f"模板路径越出仓库：{path}: {field}")
                value[field] = str(candidate)
            elif raw and ("<" in raw or not Path(raw).is_absolute()):
                raise PortableError(f"模板路径未解析：{path}: {field}={raw}")
        result[name] = value
    # 安装文件必须引用同一个将被发布的配置对，不能回指旧机器。
    wanted = local_dir(root) / "library-roots.json"
    if result["installation"]["library_roots_config"] != str(wanted):
        raise PortableError(f"模板 library_roots_config 必须指向 {wanted}")
    return result


def package_problems(root: Path, configs: dict[str, dict[str, Any]]) -> list[str]:
    install, libraries = configs["installation"], configs["library-roots"]
    files = [Path(install["source_root"]) / "scripts" / "paos.py", Path(libraries["tool_catalog"])]
    dirs = []
    for kind in ("workflow", "skill"):
        base = Path(libraries[f"{kind}_root"])
        files.extend([base / "README.md", base / "CATALOG.md"])
        dirs.append(base)
    dirs.extend(Path(libraries["workflow_root"]) / p for p in ("Guides", "Workflows", "Templates"))
    return ([f"缺少文件：{p}" for p in files if not p.is_file()]
            + [f"缺少目录：{p}" for p in dirs if not p.is_dir()])


def metadata_dirs(configs: dict[str, dict[str, Any]]) -> list[Path]:
    """核心 loader 要求这些目录存在；这里只建空目录，不重建历史使用事件。"""
    return [Path(configs["installation"]["data_root"]),
            Path(configs["library-roots"]["workflow_root"]) / ".paos",
            Path(configs["library-roots"]["skill_root"]) / ".paos" / "usage-events"]


def validate_write_paths(root: Path, paths: list[Path]) -> None:
    """拒绝跨出包根的链接和文件占位；不替用户修理或删除它们。"""
    for path in paths:
        if not path.resolve().is_relative_to(root):
            raise PortableError(f"写入路径越出仓库：{path}")
        for part in (path, *path.parents):
            if part == root:
                break
            if part.is_symlink() or (part.exists() and not part.is_dir()):
                raise PortableError(f"目录路径被链接或文件占用：{part}")


def configured_pair(root: Path, expected: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    pair = {}
    for name in SCHEMAS:
        path = local_dir(root) / f"{name}.json"
        if path.is_symlink():
            raise PortableError(f"配置文件不能是链接：{path}")
        actual = read_object(path)
        for key, value in expected[name].items():
            # 工位/编号是显式的本机绑定，不是可从源码推断的业务身份。
            if key in {"rooter_home", "agent_numbers_config", "registered_at"}:
                continue
            current = actual.get(key)
            matches = (isinstance(current, str) and bool(current)
                       and Path(current).is_absolute()
                       and Path(current).resolve() == Path(value).resolve()) if key in PATH_FIELDS[name] else current == value
            if not matches:
                raise PortableError(f"配置与当前位置不符：{path}: {key}；拒绝自动覆盖，请使用核心安装配置入口重新登记")
        for key in ("rooter_home", "agent_numbers_config") if name == "installation" else ():
            value = actual.get(key, "")
            if not isinstance(value, str) or (value and not Path(value).is_absolute()):
                raise PortableError(f"配置路径无效：{path}: {key}")
        pair[name] = actual
    return pair


def prepare(root: Path, rooter_home: str = "", agent_numbers: str = "") -> dict[str, dict[str, Any]]:
    configs = expected_configs(root)
    problems = package_problems(root, configs)
    if problems:
        raise PortableError("\n".join(problems))
    for key, value, directory in (("rooter_home", rooter_home, True), ("agent_numbers_config", agent_numbers, False)):
        if value:
            path = Path(value).expanduser()
            if not path.is_absolute() or not (path.is_dir() if directory else path.is_file()):
                raise PortableError(f"{key} 必须显式指向已有的绝对{'目录' if directory else '文件'}：{value}")
            configs["installation"][key] = str(path.resolve())
    return configs


def initialize(root: Path, rooter_home: str = "", agent_numbers: str = "") -> dict[str, Any]:
    root = root.resolve()
    configs = prepare(root, rooter_home, agent_numbers)
    target = local_dir(root)
    paths = [root / "config", target, *metadata_dirs(configs)]
    validate_write_paths(root, paths)
    # 不悄悄创建第二份安装；已有手工配置应继续走原配置入口。
    legacy = root / "config" / "installation.json"
    if legacy.exists() or legacy.is_symlink():
        raise PortableError(f"已有安装配置：{legacy}；未建立第二份安装")
    if target.exists():
        actual = configured_pair(root, configs)
        for key, requested in (("rooter_home", rooter_home), ("agent_numbers_config", agent_numbers)):
            if requested and (not actual["installation"].get(key) or
                              Path(actual["installation"][key]).resolve() != Path(configs["installation"][key]).resolve()):
                raise PortableError(f"已有 {key} 与请求不同；init 不覆盖绑定")
        for path in metadata_dirs(configs):
            path.mkdir(parents=True, exist_ok=True)
        return {"created": False, "installation_file": str(target / "installation.json")}

    # 两个配置文件先在同一文件系统的暂存目录写完，再一次 rename 发布。
    # 不为旧配置提供 force；IO 失败时不留下半对“有效安装”。
    stage = Path(tempfile.mkdtemp(prefix=".portable-", dir=root / "config"))
    try:
        configs["library-roots"]["registered_at"] = datetime.now(timezone.utc).isoformat()
        for name, value in configs.items():
            with (stage / f"{name}.json").open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
        for path in metadata_dirs(configs):
            path.mkdir(parents=True, exist_ok=True)
        # 已有完整目录不可被 rename 覆盖；再次检测也拒绝空目录占位。
        if target.exists() or target.is_symlink():
            raise PortableError(f"配置目录已出现，停止发布：{target}")
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {"created": True, "installation_file": str(target / "installation.json")}


def doctor(root: Path) -> dict[str, Any]:
    """只检查安装定位，不将静态检查冒充 CLI/工位/唤醒闭环验收。"""
    root = root.resolve()
    expected = expected_configs(root)
    problems = package_problems(root, expected)
    warnings = ["空 usage-events 目录不代表历史使用事件已迁入；Catalog 统计尚未复核"]
    legacy = root / "config" / "installation.json"
    if legacy.exists() or legacy.is_symlink():
        problems.append(f"发现另一安装描述：{legacy}；请明确使用哪一份配置")
    pair = None
    try:
        validate_write_paths(root, [local_dir(root), *metadata_dirs(expected)])
        pair = configured_pair(root, expected)
    except PortableError as exc:
        problems.append(str(exc))
    for path in metadata_dirs(expected):
        if not path.is_dir():
            problems.append(f"缺少本机目录：{path}；请执行 init")
    selected = os.environ.get("PAOS_INSTALLATION_FILE")
    if selected and Path(selected).resolve() != (local_dir(root) / "installation.json"):
        warnings.append("当前 PAOS_INSTALLATION_FILE 指向别处；本检查未改动环境变量")
    if os.environ.get("PAOS_LIBRARY_ROOTS_CONFIG"):
        warnings.append("存在 PAOS_LIBRARY_ROOTS_CONFIG 环境覆盖；运行前应核对或清除")
    if pair:
        for field, directory in (("rooter_home", True), ("agent_numbers_config", False)):
            raw = pair["installation"].get(field, "")
            if not raw:
                warnings.append(f"{field} 未绑定；未创建身份或重置编号")
            elif not (Path(raw).is_dir() if directory else Path(raw).is_file()):
                problems.append(f"已绑定的 {field} 不存在：{raw}")
    return {"configuration_ok": not problems, "problems": problems, "warnings": warnings,
            "cli_verified": False, "business_verified": False, "runtime_verified": False,
            "installation_file": str(local_dir(root) / "installation.json")}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="只读：显示按仓库位置展开的两个配置")
    init = sub.add_parser("init", help="创建本机配置；不覆盖现有安装，不创建工位")
    init.add_argument("--rooter-home", default="", help="已迁入的 Rooter 工位绝对路径")
    init.add_argument("--agent-numbers-config", default="", help="已迁入的编号登记文件绝对路径")
    sub.add_parser("doctor", help="只读：检查定位；不是业务或唤醒验收")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = expected_configs(ROOT)
        elif args.command == "init":
            result = initialize(ROOT, args.rooter_home, args.agent_numbers_config)
        else:
            result = doctor(ROOT)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("configuration_ok") is False else 0
    except (PortableError, OSError) as exc:
        print(json.dumps({"configuration_ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
