"""scripts/ensure_build_data.py 的零覆盖保证。

verify.ps1 在 Dashboard 套件前调用该脚本补齐 build/dashboard-data.json，让干净
检出可以直接运行验证。这里测的是它必须绝不覆盖用户已有派生产物 —— 逻辑之所以
放在 Python 里而不是 verify.ps1 内联，就是为了能被本套件覆盖。
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ensure_build_data as ensure_build_data_module  # noqa: E402
from ensure_build_data import (  # noqa: E402
    ALREADY_PRESENT,
    GENERATE_FAILED,
    GENERATED,
    REFUSED_BUILD_APPEARED,
    REFUSED_EXISTING_BUILD,
    ensure_build_data,
)

PIPELINE_DIR = REPO_ROOT / "attention-memory-pipeline-v0"
MARKER = b'{"MARKER":"DO-NOT-OVERWRITE-EXISTING-BUILD"}\n'


class EnsureBuildDataTests(unittest.TestCase):
    """全部在临时副本上跑：真实 build/ 与 private-data/ 一概不碰。"""

    def _pipeline_copy(self, tmp: str) -> Path:
        """真实拷贝生成所需的最小集合：两个脚本 + synthetic-vault。

        必须是拷贝而非符号链接 —— 脚本以 cwd=pipeline 运行子进程，相对目标的
        链接解析不到，会让"生成失败"冒充"拒绝覆盖"，测试就成了假绿。
        """
        root = Path(tmp) / "pipeline"
        root.mkdir()
        shutil.copytree(PIPELINE_DIR / "synthetic-vault", root / "synthetic-vault")
        for script in ("scan_vault.py", "dashboard_adapter.py"):
            shutil.copy2(PIPELINE_DIR / script, root / script)
        # 自检：拷贝必须真的可执行，否则后续断言失去意义
        assert (root / "scan_vault.py").is_file()
        return root

    def test_generates_when_build_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self._pipeline_copy(tmp)

            ok, reason, _ = ensure_build_data(pipeline)

            self.assertTrue(ok)
            self.assertEqual(reason, GENERATED)
            data = json.loads(
                (pipeline / "build" / "dashboard-data.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["schema"], "attention-dashboard-data/v0")

    def test_existing_dashboard_data_is_never_touched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self._pipeline_copy(tmp)
            build = pipeline / "build"
            build.mkdir()
            target = build / "dashboard-data.json"
            target.write_bytes(MARKER)

            ok, reason, _ = ensure_build_data(pipeline)

            self.assertTrue(ok)
            self.assertEqual(reason, ALREADY_PRESENT)
            self.assertEqual(target.read_bytes(), MARKER)

    def test_partial_build_fails_without_overwriting_attention_state(self) -> None:
        """审计反例：build/ 有 attention-state 但缺 dashboard-data。

        此前只判断 dashboard-data.json，于是会用 synthetic-vault 重跑
        scan_vault.py，把用户可能来自真实来源的 attention-state 静默换掉 ——
        测试全绿而数据已丢。现在必须失败，且 marker 字节不变。
        """
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self._pipeline_copy(tmp)
            build = pipeline / "build"
            build.mkdir()
            state = build / "attention-state.json"
            state.write_bytes(MARKER)

            ok, reason, message = ensure_build_data(pipeline)

            self.assertFalse(ok)
            self.assertEqual(reason, REFUSED_EXISTING_BUILD)
            self.assertEqual(state.read_bytes(), MARKER)
            # 没有偷偷补上缺失的那个
            self.assertFalse((build / "dashboard-data.json").exists())
            # 也没顺手写入 scan_vault 的另外两个产物
            self.assertEqual(
                sorted(p.name for p in build.iterdir()), ["attention-state.json"]
            )
            self.assertIn("python scan_vault.py", message)

    def test_empty_build_dir_also_refuses(self) -> None:
        """空 build/ 同样算用户目录：宁可失败也不猜测意图。"""
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self._pipeline_copy(tmp)
            (pipeline / "build").mkdir()

            ok, reason, _ = ensure_build_data(pipeline)

            self.assertFalse(ok)
            self.assertEqual(reason, REFUSED_EXISTING_BUILD)

    def test_failed_generation_leaves_no_partial_build(self) -> None:
        """生成中途失败不得留下半个 build/，否则重试会撞上"已存在"而永久卡死。"""
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self._pipeline_copy(tmp)
            # 移除第二步的脚本：scan_vault 成功、dashboard_adapter 失败
            (pipeline / "dashboard_adapter.py").unlink()

            ok, _, _ = ensure_build_data(pipeline)

            self.assertFalse(ok)
            self.assertFalse((pipeline / "build").exists())

    def test_failed_atomic_landing_leaves_no_partial_build(self) -> None:
        """生成全成功但最终落盘失败，也不能遗留 build/ 或暂存目录。"""
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self._pipeline_copy(tmp)

            with patch.object(
                ensure_build_data_module,
                "_promote_build",
                side_effect=OSError("simulated landing failure"),
            ):
                ok, reason, _ = ensure_build_data(pipeline)

            self.assertFalse(ok)
            self.assertEqual(reason, GENERATE_FAILED)
            self.assertFalse((pipeline / "build").exists())
            self.assertEqual(list(pipeline.glob(".paos-build-*")), [])

    def test_build_appearing_during_atomic_landing_is_preserved(self) -> None:
        """竞态反例：最终 rename 前用户 build/ 出现，必须保留并放弃落盘。"""
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = self._pipeline_copy(tmp)
            marker_path = pipeline / "build" / "user-marker.json"

            def competing_writer(_: Path, build_dir: Path) -> None:
                build_dir.mkdir()
                marker_path.write_bytes(MARKER)
                raise FileExistsError("simulated competing build")

            with patch.object(
                ensure_build_data_module,
                "_promote_build",
                side_effect=competing_writer,
            ):
                ok, reason, _ = ensure_build_data(pipeline)

            self.assertFalse(ok)
            self.assertEqual(reason, REFUSED_BUILD_APPEARED)
            self.assertEqual(marker_path.read_bytes(), MARKER)
            self.assertEqual(
                sorted(path.name for path in marker_path.parent.iterdir()),
                ["user-marker.json"],
            )
            self.assertEqual(list(pipeline.glob(".paos-build-*")), [])

    def test_real_repo_build_is_not_modified(self) -> None:
        """真实 build/ 已完整时只做存在性判断，不重新生成。"""
        data_path = PIPELINE_DIR / "build" / "dashboard-data.json"
        if not data_path.exists():
            self.skipTest("真实 build/ 尚未生成，无可保护的产物")
        before = data_path.read_bytes()

        ok, reason, _ = ensure_build_data(PIPELINE_DIR)

        self.assertTrue(ok)
        self.assertEqual(reason, ALREADY_PRESENT)
        self.assertEqual(data_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
