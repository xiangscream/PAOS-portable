import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "attention-dashboard-v1-static")]

from install_homes import InstallHomesProblem, build_install_home_coverage  # noqa: E402


def todo_text(home_id: str, project_id: str, key: str = "ok") -> str:
    return (
        '---\nschema: "paos-todo/v3"\nhome_kind: "project_agent"\n'
        f'home_id: "{home_id}"\nproject_id: "{project_id}"\n---\n\n# Current\n\n'
        f'objective: "{key}"\nnext_action: "continue"\n'
    )


class Fixture:
    def __init__(self, tmp_path: Path):
        self.root = tmp_path
        self.source = tmp_path / "Source"
        self.projects = self.source / "private-data" / "project-registry" / "projects"
        self.projects.mkdir(parents=True)
        self.rooter_home = tmp_path / "RooterHome"
        self.rooter_home.mkdir()
        self.installation = tmp_path / "installation.json"
        self.installation.write_text(
            json.dumps({
                "schema": "paos-installation/v1",
                "source_root": str(self.source), "data_root": str(self.source / "private-data"),
                "library_roots_config": str(tmp_path / "library-roots.json"),
                "rooter_home": str(self.rooter_home),
            }),
            encoding="utf-8",
        )

    def project(self, pid: str, agents: list[tuple[str, str]], status: str = "active") -> Path:
        root = self.root / f"Project-{pid}"
        root.mkdir(exist_ok=True)
        sessions = [
            {"id": agent, "status": state, "mode": "managed"} for agent, state in agents
        ]
        (self.projects / f"{pid}.json").write_text(
            json.dumps({
                "schema": "paos-project/v1",
                "id": pid,
                "revision": 3,
                "status": status,
                "root_path": str(root),
                "sessions": sessions,
            }),
            encoding="utf-8",
        )
        return root

    def home(self, root: Path, agent: str, *, files: bool = True) -> Path:
        home = root / "Workstations" / agent
        home.mkdir(parents=True)
        if files:
            (home / "ENTRY.md").write_text("entry", encoding="utf-8")
            (home / "TODO.md").write_text(todo_text(agent, agent.split("-")[0]), encoding="utf-8")
        return home

    def contact(self, root: Path, targets: dict) -> None:
        store = root / "private-data" / "contact"
        store.mkdir(parents=True, exist_ok=True)
        (store / "native-targets.json").write_text(json.dumps(targets), encoding="utf-8")

    def run(self, **kwargs):
        return build_install_home_coverage(self.installation, **kwargs)


def test_denominator_dedupes_sessions_and_keeps_history(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("1001", [("1001-s001", "historical"), ("1001-s001", "active"), ("1001-s002", "active")], status="closed")
    fx.home(root, "1001-s001")
    result = fx.run()
    assert result["scope"]["total"] == {"projects": 1, "project_agents": 2, "rooter": 1, "identities": 3}
    rows = {row["home_id"]: row for row in result["homes"]}
    assert rows["1001-s002"]["home"]["exists"] is False
    assert rows["1001-s002"]["lifecycle"]["session_status"] == "active"
    assert rows["1001-s001"]["lifecycle"]["project_status"] == "closed"


def test_rooter_row_and_unregistered_rooter(tmp_path):
    fx = Fixture(tmp_path)
    fx.project("3002", [("3002-s001", "active")])
    result = fx.run()
    rooter = [r for r in result["homes"] if r["home_kind"] == "rooter"]
    assert len(rooter) == 1 and rooter[0]["project_id"] == ""
    assert result["scope"]["total"]["rooter"] == 1
    fx.installation.write_text(json.dumps({
        "schema": "paos-installation/v1", "source_root": str(fx.source), "data_root": str(fx.source / "private-data"),
        "library_roots_config": str(tmp_path / "lib.json"), "rooter_home": "",
    }), encoding="utf-8")
    result = fx.run()
    assert result["scope"]["total"]["rooter"] == 0
    assert any(i["code"] == "rooter_home_unregistered" for i in result["issues"])


def test_filters_and_404(tmp_path):
    fx = Fixture(tmp_path)
    a = fx.project("3002", [("3002-s001", "active")])
    fx.project("1001", [("1001-s001", "active")])
    fx.home(a, "3002-s001")
    result = fx.run(project="3002")
    assert [r["home_id"] for r in result["homes"]] == ["3002-s001"]
    assert result["scope"]["filter"] == {"project": "3002", "home": None}
    assert fx.run(home="rooter-001")["homes"][0]["home_kind"] == "rooter"
    for kwargs in ({"project": "9999"}, {"home": "nope"}):
        with pytest.raises(InstallHomesProblem) as error:
            fx.run(**kwargs)
        assert error.value.code == "installation_filter_not_found" and error.value.status == 404


def test_contact_package_absent_partial_matching_modified_conflict(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("3002", [(f"3002-s00{i}", "active") for i in range(1, 6)])
    for i in range(1, 6):
        fx.home(root, f"3002-s00{i}")
    from paos_workstation import render_contact_markdown, render_contact_py, render_status_markdown
    for i, mode in enumerate(("absent", "partial", "matching", "modified", "conflict"), start=1):
        home = root / "Workstations" / f"3002-s00{i}"
        if mode == "partial":
            (home / "CONTACT.md").write_text("x", encoding="utf-8")
        elif mode in ("matching", "modified"):
            texts = {
                "contact.py": render_contact_py(
                    home_kind="project_agent", home_id=f"3002-s00{i}", project_id="3002",
                    installation_file=str(fx.installation),
                ),
                "CONTACT.md": render_contact_markdown(home_kind="project_agent", home_id=f"3002-s00{i}", project_id="3002"),
                "STATUS.md": render_status_markdown(home_kind="project_agent", home_id=f"3002-s00{i}", project_id="3002"),
            }
            for name, text in texts.items():
                (home / name).write_text(text + ("# edited" if mode == "modified" else ""), encoding="utf-8")
        elif mode == "conflict":
            (home / "contact.py").mkdir()
    result = fx.run()
    statuses = {r["home_id"]: r["contact_package"]["status"] for r in result["homes"] if r["home_kind"] == "project_agent"}
    assert statuses == {
        "3002-s001": "absent", "3002-s002": "partial", "3002-s003": "matching",
        "3002-s004": "modified", "3002-s005": "unavailable",
    }
    assert result["summary"]["contact_status"]["matching"] == 1


def test_support_classification_and_whitelist(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("3002", [("3002-s001", "active"), ("3002-s002", "active"), ("3002-s003", "active"), ("3002-s004", "active"), ("3002-s005", "active")])
    for i in range(1, 6):
        fx.home(root, f"3002-s00{i}")
    fx.contact(root, {
        "3002-s001": {"runtime": "codex", "runtime_id": "r1", "session_id": "s1", "stop_file": str(tmp_path / "missing.stop")},
        "3002-s002": {"runtime": "some-future-runtime", "runtime_id": "r2", "session_id": "s2"},
        "3002-s003": {"runtime": "opencode", "runtime_id": "r3"},
        "3002-s004": {"runtime": "opencode", "runtime_id": "r4", "session_id": "s4", "token": "SECRET-TOKEN", "pipe": "\\\\.\\pipe\\x"},
        "3002-s005": {"runtime": "workbuddy", "runtime_id": "r5", "session_id": "s5", "stop_file": str(tmp_path / "stop")},
    })
    (tmp_path / "stop").write_text("", encoding="utf-8")
    result = fx.run()
    rows = {r["home_id"]: r for r in result["homes"]}
    assert rows["3002-s001"]["contact"]["classification"] == "conditional"
    assert rows["3002-s001"]["contact"]["stop"] == "missing"
    assert rows["3002-s002"]["contact"]["classification"] == "unsupported"
    assert rows["3002-s003"]["contact"]["classification"] is None
    assert rows["3002-s004"]["contact"]["classification"] == "conditional"
    assert rows["3002-s005"]["contact"]["stop"] == "present"
    assert result["summary"]["support"]["automatic"] == 0
    assert result["summary"]["unclassified"] == 1
    blob = json.dumps(result, ensure_ascii=False)
    assert "SECRET-TOKEN" not in blob and "pipe" not in blob
    assert all(r["native_reachability"] == "not_observed" for r in result["homes"])


def test_no_writes_and_no_execution(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("3002", [("3002-s001", "active")])
    home = fx.home(root, "3002-s001")
    marker = tmp_path / "executed"
    (home / "contact.py").write_text(f"open({str(marker)!r}, 'w').write('x')\n", encoding="utf-8")
    before = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*") if p.is_file()}
    time.sleep(0.01)
    result = fx.run()
    after = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after and not marker.exists()
    assert result["read_only"] is True and result["business_acceptance"] == "not_determined"


def test_registry_corruption_is_global_503(tmp_path):
    fx = Fixture(tmp_path)
    fx.project("3002", [("3002-s001", "active")])
    (fx.projects / "1001.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(InstallHomesProblem) as error:
        fx.run()
    assert error.value.code == "installation_registry_unreadable" and error.value.status == 503


def test_missing_installation_and_root(tmp_path):
    missing = tmp_path / "none.json"
    with pytest.raises(InstallHomesProblem) as error:
        build_install_home_coverage(missing)
    assert error.value.code == "installation_not_registered" and error.value.status == 404
    fx = Fixture(tmp_path)
    fx.projects.rmdir()
    with pytest.raises(InstallHomesProblem) as error:
        fx.run()
    assert error.value.code == "installation_registry_root_missing" and error.value.status == 404


def _run_cli(fx, *args):
    import os
    import subprocess
    env = dict(
        os.environ,
        PAOS_INSTALLATION_FILE=str(fx.installation),
        PYTHONIOENCODING="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "paos.py"), *args],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
    )


def test_cli_json_and_short_table_share_service_without_core(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("3002", [("3002-s001", "active")])
    fx.home(root, "3002-s001")
    json_run = _run_cli(fx, "--json", "install", "homes")
    assert json_run.returncode == 0, json_run.stderr
    payload = json.loads(json_run.stdout)
    assert payload["schema"] == "paos-installation-home-coverage/v1"
    assert payload["scope"]["total"]["identities"] == 2
    plain = _run_cli(fx, "install", "homes", "--project", "3002")
    assert plain.returncode == 0, plain.stderr
    assert "安装登记" in plain.stdout and "3002-s001" in plain.stdout and not plain.stdout.lstrip().startswith("{")


def test_cli_filter_404_and_bad_descriptor_422(tmp_path):
    fx = Fixture(tmp_path)
    fx.project("3002", [("3002-s001", "active")])
    missing = _run_cli(fx, "--json", "install", "homes", "--project", "9999")
    assert missing.returncode == 1
    error = json.loads(missing.stderr)
    assert error["error_code"] == "installation_filter_not_found"
    fx.installation.write_text('{"schema": "wrong"}', encoding="utf-8")
    bad = _run_cli(fx, "--json", "install", "homes")
    assert bad.returncode != 0
    assert json.loads(bad.stderr)["error_code"] == "installation_descriptor_invalid"


def test_complete_reflects_missing_home_and_row_issues(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("1001", [("1001-s001", "active")])
    fx.home(root, "1001-s001")
    assert fx.run()["complete"] is True
    (root / "Workstations" / "1001-s001" / "TODO.md").unlink()
    fx.project("1002", [("1002-s001", "active")])
    result = fx.run()
    assert result["complete"] is False
    rows = {r["home_id"]: r for r in result["homes"]}
    assert any(i["code"] == "home_missing" for i in rows["1002-s001"]["issues"])
    assert result["summary"]["home_present"] + result["summary"]["home_missing"] + result["summary"]["home_unlocatable"] == result["summary"]["rows"]


def test_conditional_requires_resolvable_home(tmp_path):
    fx = Fixture(tmp_path)
    fx.project("3002", [("3002-s001", "active")])
    root = tmp_path / "Project-3002"
    fx.contact(root, {"3002-s001": {"runtime": "codex", "runtime_id": "r", "session_id": "s"}})
    result = fx.run()
    row = next(r for r in result["homes"] if r["home_id"] == "3002-s001")
    assert row["home"]["state"] == "missing"
    assert row["contact"]["classification"] is None
    assert result["summary"]["unclassified"] == 1


def test_registered_empty_project_filter_returns_empty(tmp_path):
    fx = Fixture(tmp_path)
    fx.project("1002", [])
    result = fx.run(project="1002")
    assert result["homes"] == []
    assert result["scope"]["filter"]["project"] == "1002"
    with pytest.raises(InstallHomesProblem) as error:
        fx.run(project="9999")
    assert error.value.code == "installation_filter_not_found"


def test_stop_unreadable_is_explicit(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("3002", [("3002-s001", "active")])
    fx.home(root, "3002-s001")
    stop = tmp_path / "stop-dir"
    stop.mkdir()
    fx.contact(root, {"3002-s001": {"runtime": "codex", "runtime_id": "r", "session_id": "s", "stop_file": str(stop)}})
    row = next(r for r in fx.run()["homes"] if r["home_id"] == "3002-s001")
    assert row["contact"]["stop"] == "unreadable"


def test_complete_false_when_target_config_invalid_or_package_modified(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("3002", [("3002-s001", "active"), ("3002-s002", "active")])
    fx.home(root, "3002-s001")
    fx.home(root, "3002-s002")
    fx.contact(root, {"3002-s001": ["not", "a", "target"], "3002-s002": None})
    result = fx.run()
    rows = {r["home_id"]: r for r in result["homes"]}
    assert rows["3002-s001"]["contact"]["classification"] is None
    assert rows["3002-s001"]["contact"]["config_source"] == "native_targets_unreadable"
    assert any(i["code"] == "contact_config_unreadable" for i in rows["3002-s001"]["issues"])
    assert result["complete"] is False

    from paos_workstation import render_contact_markdown, render_contact_py, render_status_markdown
    home = root / "Workstations" / "3002-s002"
    for name, text in {
        "contact.py": render_contact_py(home_kind="project_agent", home_id="3002-s002", project_id="3002"),
        "CONTACT.md": render_contact_markdown(home_kind="project_agent", home_id="3002-s002", project_id="3002"),
        "STATUS.md": render_status_markdown(home_kind="project_agent", home_id="3002-s002", project_id="3002"),
    }.items():
        (home / name).write_text(text + "# edited\n", encoding="utf-8")
    result = fx.run()
    rows = {r["home_id"]: r for r in result["homes"]}
    assert rows["3002-s002"]["contact_package"]["status"] == "modified"
    assert any(i["code"] == "contact_package_modified" for i in rows["3002-s002"]["issues"])
    assert result["complete"] is False
    assert (home / "CONTACT.md").read_text(encoding="utf-8").endswith("# edited\n")


def test_generated_package_matching_uses_registered_installation(tmp_path):
    from paos_workstation import ensure_contact_package

    fx = Fixture(tmp_path)
    root = fx.project("3002", [("3002-s001", "active")])
    home = fx.home(root, "3002-s001")
    ensure_contact_package(
        home_path=home, home_kind="project_agent", home_id="3002-s001",
        project_id="3002", installation_file=str(fx.installation),
    )
    row = next(r for r in fx.run()["homes"] if r["home_id"] == "3002-s001")
    assert row["contact_package"]["status"] == "matching"
    (home / "CONTACT.md").write_text((home / "CONTACT.md").read_text(encoding="utf-8") + "manual\n", encoding="utf-8")
    row = next(r for r in fx.run()["homes"] if r["home_id"] == "3002-s001")
    assert row["contact_package"]["status"] == "modified"


def test_windows_locator_variant_is_same_installation():
    from install_homes import _installation_locator_variants

    variants = _installation_locator_variants("/mnt/c/Users/remo/.paos/installation.json")
    assert "C:\\Users\\remo\\.paos\\installation.json" in variants


def test_forward_slash_windows_locator_is_same_installation(tmp_path):
    from install_homes import _installation_locator_variants

    variants = _installation_locator_variants("C:/Users/remo/.paos/installation.json")
    assert "C:/Users/remo/.paos/installation.json" in variants
    assert "C:\\Users\\remo\\.paos\\installation.json" in variants


def test_wsl_compares_forward_slash_windows_generated_package(tmp_path):
    from install_homes import _contact_package
    from paos_workstation import (
        render_contact_markdown, render_contact_py, render_status_markdown,
    )

    home = tmp_path / "home"
    home.mkdir()
    windows = "C:/Users/remo/.paos/installation.json"
    (home / "contact.py").write_text(
        render_contact_py(home_kind="project_agent", home_id="3002-s001", project_id="3002", installation_file=windows),
        encoding="utf-8",
    )
    (home / "CONTACT.md").write_text(
        render_contact_markdown(home_kind="project_agent", home_id="3002-s001", project_id="3002"),
        encoding="utf-8",
    )
    (home / "STATUS.md").write_text(
        render_status_markdown(home_kind="project_agent", home_id="3002-s001", project_id="3002"),
        encoding="utf-8",
    )
    result = _contact_package(home, "project_agent", "3002-s001", "3002", "/mnt/c/Users/remo/.paos/installation.json")
    assert result["status"] == "matching"


def test_windows_check_sees_posix_generated_package(tmp_path):
    from install_homes import _contact_package, _installation_locator_variants
    from paos_workstation import (
        render_contact_markdown, render_contact_py, render_status_markdown,
    )

    variants = _installation_locator_variants("C:/Users/remo/.paos/installation.json")
    assert "/mnt/c/Users/remo/.paos/installation.json" in variants
    home = tmp_path / "home"
    home.mkdir()
    posix = "/mnt/c/Users/remo/.paos/installation.json"
    (home / "contact.py").write_text(
        render_contact_py(home_kind="project_agent", home_id="3002-s001", project_id="3002", installation_file=posix),
        encoding="utf-8",
    )
    (home / "CONTACT.md").write_text(
        render_contact_markdown(home_kind="project_agent", home_id="3002-s001", project_id="3002"),
        encoding="utf-8",
    )
    (home / "STATUS.md").write_text(
        render_status_markdown(home_kind="project_agent", home_id="3002-s001", project_id="3002"),
        encoding="utf-8",
    )
    result = _contact_package(home, "project_agent", "3002-s001", "3002", "C:/Users/remo/.paos/installation.json")
    assert result["status"] == "matching"


def test_configured_target_without_runtime_id_is_complete(tmp_path):
    fx = Fixture(tmp_path)
    root = fx.project("3002", [("3002-s001", "active")])
    fx.home(root, "3002-s001")
    fx.contact(root, {"3002-s001": {"runtime": "codex", "session_id": "thread"}})
    row = next(r for r in fx.run()["homes"] if r["home_id"] == "3002-s001")
    assert row["contact"]["target_complete"] is True
    assert row["contact"]["classification"] == "conditional"
