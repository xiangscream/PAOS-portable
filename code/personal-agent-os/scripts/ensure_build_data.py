#!/usr/bin/env python3
"""确保 build/dashboard-data.json 存在，且绝不覆盖任何已有派生产物。

`build/` 永不进入 Git（见 README「永不进入 Git」），所以任何干净检出都缺失
Dashboard 与其测试读取的 `build/dashboard-data.json`。补齐它需要两步，缺一不可：

    scan_vault.py        synthetic-vault        -> attention-state.json
    dashboard_adapter.py attention-state.json   -> dashboard-data.json

`verify.ps1` 在 Dashboard 套件前调用本脚本，让干净检出可以直接验证。

零覆盖规则（决定行为的唯一一条）：**只有 `build/` 整个目录不存在时才生成。**

`build/` 已存在意味着里面的东西是用户的派生状态 —— 可能来自真实来源而非
synthetic-vault。此时即使 `dashboard-data.json` 缺失也不自动生成：`scan_vault.py`
还会写 `attention-state.json`、`source-manifest.json`、`scan-report.md`，无法在
不可能覆盖其中任何一个的前提下推断用户意图。这种情况直接失败并提示显式重建。

生成本身也是全有或全无：两步都在临时目录完成，全部成功后才整体落盘。中途失败
不留下半个 `build/`，因此重试不会撞上"已存在但不完整"。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PIPELINE_DIRNAME = "attention-memory-pipeline-v0"

ALREADY_PRESENT = "already-present"
GENERATED = "generated"
REFUSED_EXISTING_BUILD = "refused-existing-build"
# 第二道防线：生成期间 build/ 才出现（竞态）。reason 与前置检查区分开，测试
# 才能判定究竟哪一层拦住了覆盖 —— 否则退回前置检查时后者顶上，制造假绿。
REFUSED_BUILD_APPEARED = "refused-build-appeared"
GENERATE_FAILED = "generate-failed"

REBUILD_HINT = (
    f"手动重建（会覆盖现有 build/，请自行确认）：\n"
    f"    cd {PIPELINE_DIRNAME}\n"
    f"    python scan_vault.py --source synthetic-vault\n"
    f"    python dashboard_adapter.py"
)


def ensure_build_data(
    pipeline_dir: Path,
    python: str | None = None,
) -> tuple[bool, str, str]:
    """返回 (ok, reason, message)。reason 取本模块的四个常量之一。

    不抛异常：调用方（verify.ps1）只需要退出码与一段可读提示。
    """
    python = python or sys.executable
    build_dir = pipeline_dir / "build"
    data_path = build_dir / "dashboard-data.json"

    if data_path.exists():
        return True, ALREADY_PRESENT, f"派生数据已存在，未改动：{data_path}"

    if build_dir.exists():
        # 零覆盖：build/ 里的产物属于用户，可能来自真实来源。
        return (
            False,
            REFUSED_EXISTING_BUILD,
            f"build/ 已存在但缺少 dashboard-data.json：{build_dir}\n"
            f"拒绝自动生成 —— 用 synthetic-vault 重跑会覆盖其中已有的派生产物。\n"
            f"{REBUILD_HINT}",
        )

    # build/ 整个不存在：没有用户数据可覆盖，生成是安全的。
    # 先在临时目录完成两步，全部成功后再整体落盘（失败不留半成品）。
    steps = (
        (
            "scan_vault.py",
            [
                "scan_vault.py",
                "--source",
                "synthetic-vault",
                "--output",
                "{tmp}/attention-state.json",
                "--manifest",
                "{tmp}/source-manifest.json",
                "--report",
                "{tmp}/scan-report.md",
            ],
        ),
        (
            "dashboard_adapter.py",
            [
                "dashboard_adapter.py",
                "--input",
                "{tmp}/attention-state.json",
                "--output",
                "{tmp}/dashboard-data.json",
            ],
        ),
    )

    # 暂存目录必须与 build/ 位于同一文件系统，最后才能用一次目录重命名完成
    # 原子落盘。若放在系统临时目录，只能逐文件搬运，中途失败会留下半个 build/。
    tmp_dir = Path(tempfile.mkdtemp(prefix=".paos-build-", dir=pipeline_dir))
    try:
        for label, argv in steps:
            resolved = [part.replace("{tmp}", str(tmp_dir)) for part in argv]
            completed = subprocess.run(
                [python, *resolved],
                cwd=pipeline_dir,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                return (
                    False,
                    GENERATE_FAILED,
                    f"{label} 失败（退出码 {completed.returncode}）：\n"
                    f"{completed.stdout}{completed.stderr}",
                )

        if not (tmp_dir / "dashboard-data.json").exists():
            return (
                False,
                GENERATE_FAILED,
                "两步都退出 0，但 dashboard-data.json 未落盘。",
            )

        # 落盘前重新确认 build/ 仍不存在：把上面这段时间里出现的 build/ 当作
        # 用户数据，宁可失败也不覆盖。
        if build_dir.exists():
            return (
                False,
                REFUSED_BUILD_APPEARED,
                f"生成期间 build/ 出现，放弃落盘以免覆盖：{build_dir}\n{REBUILD_HINT}",
            )

        try:
            _promote_build(tmp_dir, build_dir)
        except OSError as error:
            # 第二次 exists 检查与 rename 之间仍有极小竞态窗口。目的地若已
            # 出现，一律视为用户数据；否则是磁盘/权限类落盘失败。
            if build_dir.exists():
                return (
                    False,
                    REFUSED_BUILD_APPEARED,
                    f"落盘时 build/ 出现，放弃覆盖：{build_dir}\n{REBUILD_HINT}",
                )
            return (
                False,
                GENERATE_FAILED,
                f"派生数据原子落盘失败：{error}",
            )
    finally:
        # rename 成功后原路径已不存在；失败时清掉暂存目录，不留重试障碍。
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return (
        True,
        GENERATED,
        f"已从 synthetic-vault 生成派生数据：{build_dir}",
    )


def _promote_build(staging_dir: Path, build_dir: Path) -> None:
    """把完整暂存目录一次性提升为 build/；独立封装便于故障注入测试。"""
    staging_dir.rename(build_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--pipeline-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / PIPELINE_DIRNAME,
        help=f"{PIPELINE_DIRNAME} 目录（默认取仓库内的那个）",
    )
    args = parser.parse_args(argv)

    ok, reason, message = ensure_build_data(args.pipeline_dir)
    print(f"[{reason}] {message}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
