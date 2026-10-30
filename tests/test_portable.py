"""Bootstrap contract tests using synthetic packages, not production Homes.

These tests do not stand in for the core verifier or native-runtime testing.
"""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import portable


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Windows may return an 8.3 TEMP alias; production canonicalizes paths.
        self.root = (Path(self.temp.name) / "中文 portable package").resolve()
        self.root.mkdir()
        (self.root / "config").mkdir()
        for name in portable.SCHEMAS:
            shutil.copyfile(portable.ROOT / "config" / f"{name}.example.json",
                            self.root / "config" / f"{name}.example.json")
        for name in ("code/personal-agent-os/scripts/paos.py", "libraries/tool-catalog.md",
                     "libraries/workflow/README.md", "libraries/workflow/CATALOG.md",
                     "libraries/skill/README.md", "libraries/skill/CATALOG.md"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic fixture; never executed\n", encoding="utf-8")
        for name in ("Guides", "Workflows", "Templates"):
            (self.root / "libraries/workflow" / name).mkdir()

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def change_template(self, name="installation", **fields):
        path = self.root / "config" / f"{name}.example.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value.update(fields)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_plan_is_read_only(self):
        before = self.snapshot()
        configs = portable.expected_configs(self.root)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / "data").exists())
        self.assertEqual(configs["installation"]["source_root"], str(self.root / "code/personal-agent-os"))

    def test_plan_uses_checkout_not_cwd(self):
        cwd = Path.cwd()
        try:
            os.chdir(self.temp.name)
            self.assertEqual(portable.expected_configs(self.root)["installation"]["data_root"], str(self.root / "data"))
        finally:
            os.chdir(cwd)

    def test_init_creates_pair_and_metadata_not_homes(self):
        result = portable.initialize(self.root)
        self.assertTrue(result["created"])
        configs = portable.configured_pair(self.root, portable.expected_configs(self.root))
        self.assertEqual(configs["installation"]["rooter_home"], "")
        self.assertEqual(configs["installation"]["agent_numbers_config"], "")
        self.assertTrue(configs["library-roots"]["registered_at"])
        self.assertFalse((self.root / "libraries/Rooter").exists())
        self.assertEqual(list((self.root / "data").iterdir()), [])
        for path in portable.metadata_dirs(configs):
            self.assertTrue(path.is_dir())

    def test_init_idempotent_bytes(self):
        portable.initialize(self.root)
        before = self.snapshot()
        self.assertFalse(portable.initialize(self.root)["created"])
        self.assertEqual(before, self.snapshot())

    def test_init_preserves_business_bytes(self):
        path = self.root / "data/keep-evidence.json"
        path.parent.mkdir()
        path.write_bytes(b'{"receipt":"do not rewrite"}\n')
        portable.initialize(self.root)
        self.assertEqual(path.read_bytes(), b'{"receipt":"do not rewrite"}\n')

    def test_existing_mismatched_config_not_overwritten(self):
        portable.initialize(self.root)
        path = portable.local_dir(self.root) / "installation.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["data_root"] = str(self.root / "elsewhere")
        path.write_text(json.dumps(value), encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertEqual(before, self.snapshot())

    def test_equivalent_absolute_locator_not_rewritten(self):
        portable.initialize(self.root)
        path = portable.local_dir(self.root) / "installation.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["data_root"] = str(self.root / "data" / ".." / "data")
        path.write_text(json.dumps(value), encoding="utf-8")
        before = self.snapshot()
        self.assertFalse(portable.initialize(self.root)["created"])
        self.assertEqual(before, self.snapshot())

    def test_relative_current_locator_is_rejected(self):
        portable.initialize(self.root)
        path = portable.local_dir(self.root) / "installation.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["data_root"] = "data"
        path.write_text(json.dumps(value), encoding="utf-8")
        self.assertFalse(portable.doctor(self.root)["configuration_ok"])

    def test_existing_invalid_json_not_overwritten(self):
        portable.initialize(self.root)
        path = portable.local_dir(self.root) / "installation.json"
        path.write_text("broken", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertEqual(before, self.snapshot())

    def test_existing_legacy_installation_refuses_second_install(self):
        path = self.root / "config/installation.json"
        path.write_text("original", encoding="utf-8")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertFalse(portable.local_dir(self.root).exists())
        self.assertEqual(path.read_text(encoding="utf-8"), "original")

    def test_wrong_schema_is_rejected_before_writes(self):
        self.change_template(schema="wrong")
        before = self.snapshot()
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / "data").exists())

    def test_unknown_template_field_is_rejected(self):
        self.change_template(runtime_id="not allowed")
        with self.assertRaises(portable.PortableError):
            portable.expected_configs(self.root)

    def test_blank_required_path_is_rejected(self):
        self.change_template(data_root="")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)

    def test_relative_path_is_rejected(self):
        self.change_template(data_root="relative")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)

    def test_unknown_placeholder_is_rejected(self):
        self.change_template(data_root="<OTHER>/data")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)

    def test_template_traversal_is_rejected(self):
        self.change_template(data_root="<PAOS_ROOT>/../outside")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)

    def test_library_config_pointer_must_match_pair(self):
        self.change_template(library_roots_config="<PAOS_ROOT>/config/wrong.json")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)

    def test_missing_package_file_fails_before_writes(self):
        (self.root / "libraries/tool-catalog.md").unlink()
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertFalse(portable.local_dir(self.root).exists())

    def test_rooter_must_exist_and_is_not_created(self):
        path = self.root / "missing-home"
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root, str(path))
        self.assertFalse(path.exists())

    def test_explicit_rooter_preserved_on_repeat(self):
        home = self.root / "private-home"
        home.mkdir()
        (home / "TODO.md").write_text("unchanged", encoding="utf-8")
        portable.initialize(self.root, str(home))
        portable.initialize(self.root)
        value = json.loads((portable.local_dir(self.root) / "installation.json").read_text(encoding="utf-8"))
        self.assertEqual(value["rooter_home"], str(home))
        self.assertEqual((home / "TODO.md").read_text(encoding="utf-8"), "unchanged")

    def test_rooter_relative_path_refused(self):
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root, "relative-home")

    def test_existing_binding_cannot_be_replaced_by_init(self):
        home, another = self.root / "home", self.root / "another"
        home.mkdir()
        another.mkdir()
        portable.initialize(self.root, str(home))
        before = self.snapshot()
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root, str(another))
        self.assertEqual(before, self.snapshot())

    def test_agent_numbers_not_reset(self):
        path = self.root / "config/AGENT-NUMBERS.json"
        path.write_text('{"existing":99}', encoding="utf-8")
        portable.initialize(self.root, agent_numbers=str(path))
        self.assertEqual(path.read_text(encoding="utf-8"), '{"existing":99}')

    def test_partial_existing_pair_is_not_overwritten(self):
        portable.local_dir(self.root).mkdir()
        (portable.local_dir(self.root) / "library-roots.json").write_text("{}", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertEqual(before, self.snapshot())

    def test_metadata_file_conflict_is_rejected(self):
        (self.root / "libraries/workflow/.paos").write_text("not a directory", encoding="utf-8")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertFalse(portable.local_dir(self.root).exists())

    def test_external_symlink_is_rejected(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        try:
            (self.root / "data").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks not available: {exc}")
        with self.assertRaises(portable.PortableError):
            portable.initialize(self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_doctor_unconfigured_is_read_only(self):
        before = self.snapshot()
        result = portable.doctor(self.root)
        self.assertFalse(result["configuration_ok"])
        self.assertEqual(before, self.snapshot())
        self.assertFalse(portable.local_dir(self.root).exists())

    def test_doctor_does_not_claim_business_or_runtime_verification(self):
        portable.initialize(self.root)
        before = self.snapshot()
        result = portable.doctor(self.root)
        self.assertTrue(result["configuration_ok"], result)
        for key in ("cli_verified", "business_verified", "runtime_verified"):
            self.assertFalse(result[key])
        self.assertEqual(before, self.snapshot())

    def test_relocated_config_is_diagnosed_not_rewritten(self):
        portable.initialize(self.root)
        new = Path(self.temp.name) / "moved"
        shutil.copytree(self.root, new)
        original = (portable.local_dir(new) / "installation.json").read_bytes()
        result = portable.doctor(new)
        self.assertFalse(result["configuration_ok"])
        self.assertEqual(original, (portable.local_dir(new) / "installation.json").read_bytes())

    def test_new_checkout_plan_tracks_new_location(self):
        new = Path(self.temp.name) / "second checkout"
        shutil.copytree(self.root, new)
        portable.initialize(new)
        result = json.loads((portable.local_dir(new) / "installation.json").read_text(encoding="utf-8"))
        self.assertEqual(result["source_root"], str((new / "code/personal-agent-os").resolve()))

    def test_staging_failure_leaves_no_published_pair(self):
        real_dump = json.dump
        count = 0
        def fail_second(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("injected IO failure")
            return real_dump(*args, **kwargs)
        with patch.object(portable.json, "dump", side_effect=fail_second):
            with self.assertRaises(OSError):
                portable.initialize(self.root)
        self.assertFalse(portable.local_dir(self.root).exists())
        self.assertEqual(list((self.root / "config").glob(".portable-*")), [])

    def test_rename_failure_cleans_staging(self):
        with patch.object(Path, "rename", side_effect=OSError("injected rename failure")):
            with self.assertRaises(OSError):
                portable.initialize(self.root)
        self.assertFalse(portable.local_dir(self.root).exists())
        self.assertEqual(list((self.root / "config").glob(".portable-*")), [])

    def test_missing_metadata_is_reported_then_recreated(self):
        portable.initialize(self.root)
        path = self.root / "libraries/skill/.paos"
        shutil.rmtree(path)
        before = self.snapshot()
        self.assertFalse(portable.doctor(self.root)["configuration_ok"])
        portable.initialize(self.root)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(portable.doctor(self.root)["configuration_ok"])

    def test_environment_override_warning(self):
        portable.initialize(self.root)
        with patch.dict(os.environ, {"PAOS_INSTALLATION_FILE": "elsewhere", "PAOS_LIBRARY_ROOTS_CONFIG": "elsewhere"}):
            result = portable.doctor(self.root)
        self.assertGreaterEqual(len(result["warnings"]), 2)

    def test_doctor_reports_missing_bound_rooter(self):
        home = self.root / "home"
        home.mkdir()
        portable.initialize(self.root, str(home))
        home.rmdir()
        self.assertFalse(portable.doctor(self.root)["configuration_ok"])

    def test_doctor_detects_two_descriptors(self):
        portable.initialize(self.root)
        (self.root / "config/installation.json").write_text("{}", encoding="utf-8")
        self.assertFalse(portable.doctor(self.root)["configuration_ok"])

    def test_cli_exit_codes(self):
        with patch.object(portable, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(portable.main(["plan"]), 0)
            self.assertEqual(portable.main(["doctor"]), 1)
            self.assertEqual(portable.main(["init"]), 0)
            self.assertEqual(portable.main(["doctor"]), 0)
        self.change_template(schema="wrong")
        with patch.object(portable, "ROOT", self.root), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(portable.main(["plan"]), 2)


if __name__ == "__main__":
    unittest.main()
