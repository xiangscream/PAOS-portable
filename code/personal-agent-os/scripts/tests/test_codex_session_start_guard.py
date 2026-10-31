import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_receiver_session_start as hook
import paos_wakeup as wake


class SessionStartGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.registry = self.source / "private-data/project-registry/projects"
        self.registry.mkdir(parents=True)
        self.descriptor = {
            "schema": "paos-installation/v1",
            "configured": True,
            "source_root": str(self.source),
            "data_root": str(self.source / "private-data"),
            "rooter_home": "",
            "library_roots_config": str(self.root / "library-roots.json"),
            "path": str(self.root / "installation.json"),
        }
        self.environment = {"CODEX_THREAD_ID": "own-thread", "CODEX_APP_TOOLS_PIPE_PATH": "own-fixture-pipe"}
        self.event = {"hook_event_name": "SessionStart", "source": "resume", "session_id": "own-thread"}
        self.target = self.register("3002", "3002-s031")

    def register(self, project_id, agent_id, thread="own-thread"):
        root = self.root / project_id
        (root / "Workstations" / agent_id).mkdir(parents=True)
        contact = root / "private-data/contact/native-targets.json"
        contact.parent.mkdir(parents=True, exist_ok=True)
        target = {"runtime": "codex", "session_id": thread, "stop_file": str(root / "STOP"),
                  "extension": {"receiver_runtime_file": str(root / "receiver/runtime.json"),
                                "windows_python": str(root / "registered-python.exe"),
                                "execution_environment": "windows"}}
        contact.write_text(json.dumps({agent_id: target}), encoding="utf-8")
        (self.registry / f"{project_id}.json").write_text(json.dumps({
            "schema": "paos-project-registry/v1", "id": project_id,
            "root_path": str(root), "homes": [agent_id],
            "coordinator_home_id": agent_id}), encoding="utf-8")
        Path(self.descriptor["path"]).write_text(json.dumps(self.descriptor), encoding="utf-8")
        return target

    def prepare(self, event=None, *, manual=False):
        Path(self.descriptor["path"]).write_text(json.dumps(self.descriptor), encoding="utf-8")
        with patch.object(hook, "os", SimpleNamespace(name="nt", environ=self.environment)), \
             patch.object(hook, "load_installation_descriptor", return_value=self.descriptor), \
             patch.object(hook.subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(hook.subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000, create=True), \
             patch.object(hook.subprocess, "Popen", return_value=SimpleNamespace(pid=123)) as launch:
            result = hook.prepare_current() if manual else hook.prepare(event or self.event)
            return result, launch

    def register_rooter(self, thread="rooter-thread", directory="rooter-001"):
        root = self.root / directory
        contact = root / "private-data/contact/native-targets.json"
        contact.parent.mkdir(parents=True)
        target = {"runtime": "codex", "session_id": thread, "stop_file": str(root / "STOP"),
                  "extension": {"receiver_runtime_file": str(root / "runtime.json"),
                                "windows_python": str(root / "python.exe"),
                                "execution_environment": "windows"}}
        contact.write_text(json.dumps({"rooter-001": target}), encoding="utf-8")
        self.descriptor["rooter_home"] = str(root)
        Path(self.descriptor["path"]).write_text(json.dumps(self.descriptor), encoding="utf-8")
        return target

    def test_rooter_identity_does_not_depend_on_directory_name(self):
        self.register_rooter(directory="中文 Rooter")
        self.environment["CODEX_THREAD_ID"] = "rooter-thread"
        result, launch = self.prepare(manual=True)
        self.assertIn("receiver_prepare_started: rooter-001", result)
        launch.assert_called_once()

    def test_rooter_prepares_without_a_project_registry_directory(self):
        self.register_rooter()
        (self.registry / "3002.json").unlink()
        self.registry.rmdir()
        self.environment["CODEX_THREAD_ID"] = "rooter-thread"
        result, launch = self.prepare(manual=True)
        self.assertIn("receiver_prepare_started: rooter-001", result)
        launch.assert_called_once()

    def test_registered_rooter_uses_own_home_contact_and_normal_prepare(self):
        target = self.register_rooter()
        self.environment["CODEX_THREAD_ID"] = "rooter-thread"
        with patch.object(hook, "rooter_home", wraps=hook.rooter_home) as validate:
            result, launch = self.prepare({**self.event, "session_id": "rooter-thread"})
        self.assertIn("receiver_prepare_started: rooter-001", result)
        validate.assert_called_once_with(home_path=self.root / "rooter-001", home_id="rooter-001")
        launch.assert_called_once()
        argv = launch.call_args.args[0]
        self.assertEqual(argv[0], target["extension"]["windows_python"])
        self.assertEqual(argv[-3:], [target["extension"]["receiver_runtime_file"], "--stop-file", target["stop_file"]])
        self.assertFalse((self.root / "rooter-001/Workstations").exists())

    def test_project_rooter_duplicate_thread_is_ambiguous(self):
        self.register_rooter("own-thread")
        with self.assertRaisesRegex(ValueError, "contact_thread_ambiguous"):
            self.prepare()

    @unittest.skipUnless(os.name == "nt", "Windows default Contact registration")
    def test_normal_bind_completes_contact_before_owner_prepare(self):
        contact = self.root / "3002/private-data/contact/native-targets.json"
        bare = {"runtime": "codex", "session_id": "own-thread", "stop_file": self.target["stop_file"]}
        colleague = {"runtime": "opencode", "session_id": "colleague-thread"}
        contact.write_text(json.dumps({"3002-s031": bare, "3002-s032": colleague}), encoding="utf-8")
        with patch.object(Path, "home", return_value=self.root), patch.object(wake, "os", SimpleNamespace(name="nt")):
            wake.bind_wakeup(root=self.root / "3002", project_id="3002", agent_id="3002-s031",
                             native_session_id="own-thread", runtime_id="codex-desktop", driver_name="codex")
        before = contact.read_bytes()
        result, launch = self.prepare(manual=True)
        value = json.loads(contact.read_text(encoding="utf-8"))
        self.assertIn("receiver_prepare_started: 3002-s031", result)
        self.assertEqual(value["3002-s032"], colleague)
        own = value["3002-s031"]
        self.assertEqual(own["session_id"], bare["session_id"])
        self.assertEqual(own["stop_file"], bare["stop_file"])
        self.assertEqual(own["extension"]["execution_environment"], "windows")
        self.assertEqual(own["extension"]["receiver_runtime_file"],
                         str(self.root / ".paos/runtime-injection/codex-self/3002-s031/runtime.json"))
        self.assertEqual(launch.call_args.args[0][0], sys.executable)
        self.assertEqual(contact.read_bytes(), before)

    def test_stopped_bare_contact_does_not_register_or_launch(self):
        contact = self.root / "3002/private-data/contact/native-targets.json"
        bare = {"runtime": "codex", "session_id": "own-thread", "stop_file": self.target["stop_file"]}
        contact.write_text(json.dumps({"3002-s031": bare}), encoding="utf-8")
        before = contact.read_bytes()
        Path(bare["stop_file"]).touch()
        with self.assertRaisesRegex(ValueError, "receiver_binding_incomplete"), patch.object(hook.subprocess, "Popen") as launch:
            self.prepare()
        self.assertEqual(contact.read_bytes(), before)
        launch.assert_not_called()

    def test_incomplete_rooter_is_not_silently_registered_during_resume(self):
        self.register_rooter("own-thread")
        contact = self.root / "rooter-001/private-data/contact/native-targets.json"
        contact.write_text(json.dumps({"rooter-001": {"runtime": "codex", "session_id": "own-thread"}}), encoding="utf-8")
        # This fixture must have only one matching Home, like the real Owner.
        self.environment["CODEX_THREAD_ID"] = "rooter-only"
        value = json.loads(contact.read_text(encoding="utf-8"))
        value["rooter-001"]["session_id"] = "rooter-only"
        contact.write_text(json.dumps(value), encoding="utf-8")
        before = contact.read_bytes()
        with self.assertRaisesRegex(ValueError, "receiver_binding_incomplete"):
            self.prepare({**self.event, "session_id": "rooter-only"})
        self.assertEqual(contact.read_bytes(), before)

    @unittest.skipUnless(os.name == "nt", "Windows default Contact registration")
    def test_two_registered_owners_resume_concurrently_without_contact_writes(self):
        project = self.root / "3002"
        (project / "Workstations/3002-s032").mkdir()
        registry = self.registry / "3002.json"
        value = json.loads(registry.read_text(encoding="utf-8"))
        value["homes"].append("3002-s032")
        registry.write_text(json.dumps(value), encoding="utf-8")
        with patch.object(Path, "home", return_value=self.root), patch.object(wake, "os", SimpleNamespace(name="nt")):
            for agent, thread in (("3002-s031", "own-thread"), ("3002-s032", "peer-thread")):
                wake.bind_wakeup(root=project, project_id="3002", agent_id=agent,
                                 native_session_id=thread, runtime_id="codex-desktop", driver_name="codex")
        contact = project / "private-data/contact/native-targets.json"
        original = contact.read_bytes()
        context = threading.local()
        barrier = threading.Barrier(2)
        class Environment:
            def get(self, key, default=None):
                return context.thread if key == "CODEX_THREAD_ID" else "fixture-pipe" if key == "CODEX_APP_TOOLS_PIPE_PATH" else default
        def launch(*args, **kwargs):
            barrier.wait(timeout=5)
            return SimpleNamespace(pid=123)
        def resume(thread):
            context.thread = thread
            return hook.prepare_current()
        with patch.object(hook, "os", SimpleNamespace(name="nt", environ=Environment())), \
             patch.object(hook, "load_installation_descriptor", return_value=self.descriptor), \
             patch.object(hook.subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(hook.subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000, create=True), \
             patch.object(hook.subprocess, "Popen", side_effect=launch) as launches, \
             ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(resume, ("own-thread", "peer-thread")))
        self.assertEqual(launches.call_count, 2)
        self.assertTrue(all("receiver_prepare_started" in result for result in results))
        self.assertEqual(contact.read_bytes(), original)

    def test_non_windows_bind_without_receiver_config_rejects_without_writing(self):
        contact = self.root / "3002/private-data/contact/native-targets.json"
        original = contact.read_bytes()
        with patch.object(wake, "os", SimpleNamespace(name="posix")), self.assertRaises(wake.WakeProblem):
            wake.bind_wakeup(root=self.root / "3002", project_id="3002", agent_id="3002-s099",
                             native_session_id="new-thread", runtime_id="codex-desktop", driver_name="codex")
        self.assertEqual(contact.read_bytes(), original)

    def test_non_windows_bind_uses_explicit_windows_configuration(self):
        config = {"extension": {"receiver_runtime_file": "C:/PAOS/receiver/runtime.json",
                                "windows_python": "C:/Python/python.exe"}}
        with patch.object(wake, "os", SimpleNamespace(name="posix")):
            result = wake.bind_wakeup(root=self.root / "3002", project_id="3002", agent_id="3002-s099",
                                      native_session_id="new-thread", runtime_id="codex-desktop", driver_name="codex",
                                      driver_config=config)
        self.assertEqual(result["target"]["extension"]["execution_environment"], "windows")
        self.assertEqual(result["target"]["stop_file"], "C:\\PAOS\\receiver\\STOP")

    def test_invalid_windows_receiver_config_does_not_write_contact(self):
        contact = self.root / "3002/private-data/contact/native-targets.json"
        original = contact.read_bytes()
        with patch.object(wake, "os", SimpleNamespace(name="posix")), self.assertRaises(wake.WakeProblem):
            wake.bind_wakeup(root=self.root / "3002", project_id="3002", agent_id="3002-s099",
                             native_session_id="new-thread", runtime_id="codex-desktop", driver_name="codex",
                             driver_config={"extension": {"receiver_runtime_file": "relative/runtime.json",
                                                          "windows_python": "C:/Python/python.exe"}})
        self.assertEqual(contact.read_bytes(), original)

    def test_unregistered_rooter_directory_is_not_discovered(self):
        self.register_rooter()
        del self.descriptor["rooter_home"]
        with self.assertRaisesRegex(ValueError, "contact_thread_not_registered"):
            hook.registered_target("rooter-thread", self.descriptor)

    def test_rooter_stop_and_environment_guards_prevent_launch(self):
        target = self.register_rooter()
        self.environment["CODEX_THREAD_ID"] = "rooter-thread"
        event = {**self.event, "session_id": "rooter-thread"}
        Path(target["stop_file"]).touch()
        result, launch = self.prepare(event)
        self.assertIn("original_STOP_present", result)
        launch.assert_not_called()
        self.environment.pop("CODEX_APP_TOOLS_PIPE_PATH")
        result, launch = self.prepare(event)
        self.assertIn("original_desktop_environment_missing", result)
        launch.assert_not_called()

    def test_rooter_different_event_thread_never_selects_registered_contact(self):
        self.register_rooter()
        with patch.object(hook, "registered_target") as lookup:
            result, launch = self.prepare({**self.event, "session_id": "rooter-thread"})
        self.assertIn("event_thread_mismatch", result)
        lookup.assert_not_called()
        launch.assert_not_called()

    def test_unique_registered_home_uses_original_locators_and_inherited_environment(self):
        runtime = Path(self.target["extension"]["receiver_runtime_file"])
        runtime.parent.mkdir()
        runtime.write_text("existing grant evidence", encoding="utf-8")
        result, launch = self.prepare()
        self.assertIn("receiver_prepare_started: 3002-s031 PID 123", result)
        launch.assert_called_once()
        args, kwargs = launch.call_args
        self.assertEqual(args[0], [self.target["extension"]["windows_python"], "-X", "utf8", "-B", "-m",
            "wakeup_native.codex_receiver", "--runtime-file", str(runtime), "--stop-file", self.target["stop_file"]])
        self.assertEqual(kwargs["cwd"], self.source / "scripts")
        self.assertEqual(kwargs["creationflags"], 0x09000000)
        self.assertNotIn("env", kwargs)
        self.assertNotIn("own-fixture-pipe", str(args))
        self.assertEqual(runtime.read_text(encoding="utf-8"), "existing grant evidence")

    def test_manual_and_session_start_use_the_same_owner_launch(self):
        with patch.object(hook, "registered_target", wraps=hook.registered_target) as lookup:
            automatic, automatic_launch = self.prepare()
            manual, manual_launch = self.prepare(manual=True)
        self.assertEqual(automatic, manual)
        self.assertEqual(automatic_launch.call_args.args, manual_launch.call_args.args)
        for launch in (automatic_launch, manual_launch):
            launch.assert_called_once()
            self.assertEqual(launch.call_args.kwargs["creationflags"], 0x09000000)
            self.assertEqual(launch.call_args.kwargs["cwd"], self.source / "scripts")
            self.assertEqual(launch.call_args.kwargs["stdin"], subprocess.DEVNULL)
            self.assertNotIn("env", launch.call_args.kwargs)
        self.assertEqual([call.args[0] for call in lookup.call_args_list], ["own-thread", "own-thread"])

    def test_manual_guards_environment_stop_and_ambiguous_owner(self):
        for field in self.environment.copy():
            with self.subTest(field=field):
                value = self.environment.pop(field)
                with patch.object(hook, "registered_target") as lookup:
                    result, launch = self.prepare(manual=True)
                self.assertIn("original_desktop_environment_missing", result)
                lookup.assert_not_called()
                launch.assert_not_called()
                self.environment[field] = value
        stop = Path(self.target["stop_file"])
        stop.touch()
        result, launch = self.prepare(manual=True)
        self.assertIn("original_STOP_present", result)
        launch.assert_not_called()
        stop.unlink()
        self.register_rooter("own-thread")
        with self.assertRaisesRegex(ValueError, "contact_thread_ambiguous"):
            self.prepare(manual=True)

    def test_manual_rooter_uses_its_original_registered_home(self):
        target = self.register_rooter()
        self.environment["CODEX_THREAD_ID"] = "rooter-thread"
        result, launch = self.prepare(manual=True)
        self.assertIn("receiver_prepare_started: rooter-001", result)
        self.assertEqual(launch.call_args.args[0][0], target["extension"]["windows_python"])
        self.assertEqual(launch.call_args.args[0][-3:],
                         [target["extension"]["receiver_runtime_file"], "--stop-file", target["stop_file"]])
        self.assertFalse((self.root / "rooter-001/Workstations").exists())

    def test_breakaway_denied_is_one_failure_without_relaunch_or_grant_change(self):
        runtime = Path(self.target["extension"]["receiver_runtime_file"])
        runtime.parent.mkdir()
        runtime.write_text("original grant", encoding="utf-8")
        for manual in (False, True):
            with self.subTest(manual=manual), \
                 patch.object(hook, "os", SimpleNamespace(name="nt", environ=self.environment)), \
                 patch.object(hook, "load_installation_descriptor", return_value=self.descriptor), \
                 patch.object(hook.subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
                 patch.object(hook.subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000, create=True), \
                 patch.object(hook.subprocess, "Popen", side_effect=PermissionError(5, "breakaway denied")) as launch:
                with self.assertRaisesRegex(PermissionError, "breakaway denied"):
                    hook.prepare_current() if manual else hook.prepare(self.event)
                launch.assert_called_once()
                self.assertEqual(runtime.read_text(encoding="utf-8"), "original grant")

    def test_manual_command_exposes_creation_failure_and_nonzero_exit(self):
        output = io.StringIO()
        with patch.object(sys, "argv", [str(Path(hook.__file__)), "--prepare-current"]), \
             patch.object(sys, "stdout", output), \
             patch.object(hook, "prepare_current", side_effect=PermissionError(5, "breakaway denied")) as prepare:
            self.assertEqual(hook.main(), 1)
        prepare.assert_called_once_with()
        self.assertIn("receiver_prepare_unavailable", json.loads(output.getvalue())["systemMessage"])
        self.assertIn("breakaway denied", output.getvalue())

    def test_session_start_without_session_id_does_not_become_manual_prepare(self):
        event = {key: value for key, value in self.event.items() if key != "session_id"}
        result, launch = self.prepare(event)
        self.assertIn("event_thread_mismatch", result)
        launch.assert_not_called()

    def test_stop_prevents_launch_and_log_creation(self):
        Path(self.target["stop_file"]).touch()
        result, launch = self.prepare()
        self.assertIn("original_STOP_present", result)
        launch.assert_not_called()
        self.assertFalse(Path(self.target["extension"]["receiver_runtime_file"]).parent.exists())

    def test_event_cannot_replace_native_thread(self):
        result, launch = self.prepare({**self.event, "session_id": "another-thread"})
        self.assertIn("event_thread_mismatch", result)
        launch.assert_not_called()

    def test_missing_environment_never_reads_registry(self):
        for field in self.environment.copy():
            with self.subTest(field=field):
                environment = self.environment.copy()
                self.environment.pop(field)
                with patch.object(hook, "registered_target") as lookup:
                    result, launch = self.prepare()
                self.assertIn("original_desktop_environment_missing", result)
                lookup.assert_not_called()
                launch.assert_not_called()
                self.environment = environment

    def test_only_startup_resume_are_processed(self):
        for source in ("compact", "clear", "fork"):
            result, launch = self.prepare({**self.event, "source": source})
            self.assertIn("unsupported_event", result)
            launch.assert_not_called()
        result, launch = self.prepare({**self.event, "source": "startup"})
        self.assertIn("receiver_prepare_started", result)
        launch.assert_called_once()

    def test_no_registration_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "contact_thread_not_registered"):
            hook.registered_target("unregistered", self.descriptor)

    def test_ambiguity_cannot_select_an_employee(self):
        self.register("3003", "3003-s009")
        with self.assertRaisesRegex(ValueError, "contact_thread_ambiguous"):
            self.prepare()

    def test_matching_contact_requires_existing_registered_home(self):
        (self.root / "3002/Workstations/3002-s031").rmdir()
        with self.assertRaises(hook.HomeProblem) as caught:
            self.prepare()
        self.assertEqual(caught.exception.code, "home_missing")
        (self.root / "3002/Workstations/3002-s031").mkdir()
        project_file = self.registry / "3002.json"
        value = json.loads(project_file.read_text(encoding="utf-8"))
        value["homes"] = ["3002-s099"]
        value["coordinator_home_id"] = "3002-s099"
        project_file.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(hook.HomeProblem) as caught:
            self.prepare()
        self.assertEqual(caught.exception.code, "home_agent_unknown")

    def test_new_employee_contact_needs_no_hook_change(self):
        self.register("3003", "3003-s099", "new-own-thread")
        self.environment["CODEX_THREAD_ID"] = "new-own-thread"
        result, launch = self.prepare({**self.event, "session_id": "new-own-thread"})
        self.assertIn("receiver_prepare_started: 3003-s099", result)
        launch.assert_called_once()

    def test_only_authoritative_registry_roots_are_read(self):
        unrelated = self.root / "unregistered/private-data/contact/native-targets.json"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("invalid unrelated data", encoding="utf-8")
        with patch.object(hook, "load_native_targets", wraps=hook.load_native_targets) as read:
            result, _ = self.prepare()
        self.assertIn("receiver_prepare_started", result)
        read.assert_called_once_with(self.root / "3002")

    def test_legacy_empty_roots_fail_without_reading_current_directory_contact(self):
        from paos_registry import RegistryProblem
        for project_id in ("1005", "2002", "2003"):
            (self.registry / f"{project_id}.json").write_text(json.dumps({
                "id": project_id, "root_path": "", "sessions": []}), encoding="utf-8")
        previous = Path.cwd()
        try:
            os.chdir(self.root / "3002")  # Has the real fixture's matching Contact.
            with patch.object(hook, "load_native_targets", wraps=hook.load_native_targets) as read:
                with self.assertRaises(RegistryProblem) as caught:
                    self.prepare()
            self.assertEqual(caught.exception.code, "project_schema_invalid")
            read.assert_not_called()
        finally:
            os.chdir(previous)

    def test_incomplete_binding_is_actionable_without_a_false_prepare_success(self):
        contact = self.root / "3002/private-data/contact/native-targets.json"
        del self.target["extension"]["windows_python"]
        contact.write_text(json.dumps({"3002-s031": self.target}), encoding="utf-8")
        before = contact.read_bytes()
        with self.assertRaisesRegex(ValueError, "receiver_binding_incomplete"):
            self.prepare()
        self.assertEqual(contact.read_bytes(), before)

    def test_stdin_command_reports_missing_environment(self):
        environment = {key: value for key, value in os.environ.items()
                       if key not in {"CODEX_THREAD_ID", "CODEX_APP_TOOLS_PIPE_PATH"}}
        result = subprocess.run([sys.executable, "-B", str(Path(hook.__file__))],
            input=json.dumps(self.event).encode("utf-8"), env=environment, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("original_desktop_environment_missing", json.loads(result.stdout)["systemMessage"])

    def test_manual_command_needs_original_environment_and_rejects_target_override(self):
        environment = {key: value for key, value in os.environ.items()
                       if key not in {"CODEX_THREAD_ID", "CODEX_APP_TOOLS_PIPE_PATH"}}
        for action in ("--prepare-current", "--update-current"):
            with self.subTest(action=action):
                command = [sys.executable, "-B", str(Path(hook.__file__)), action]
                result = subprocess.run(command, stdin=subprocess.DEVNULL, env=environment,
                                        capture_output=True, timeout=10)
                self.assertIn("original_desktop_environment_missing", json.loads(result.stdout)["systemMessage"])
                result = subprocess.run(command + ["--session-id", "another-thread"],
                                        stdin=subprocess.DEVNULL, env=environment, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertIn(b"unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
