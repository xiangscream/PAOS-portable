import json
import os
import subprocess
import time
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "attention-dashboard-v1-static")]

from install_homes import InstallHomesProblem, build_install_home_coverage  # noqa: E402
from paos_attention_service import AttentionServiceProblem, _registry_projects_root  # noqa: E402
from paos_backup import create_backup, restore_backup  # noqa: E402
from paos_installation import (  # noqa: E402
    InstallationProblem,
    effective_data_root,
    load_installation_descriptor,
)


def descriptor(tmp_path: Path, *, source: Path, data: str | None) -> Path:
    path = tmp_path / "installation.json"
    payload = {
        "schema": "paos-installation/v1",
        "source_root": str(source),
        "library_roots_config": str(tmp_path / "library-roots.json"),
        "rooter_home": str(tmp_path / "Rooter"),
        "agent_numbers_config": str(tmp_path / "numbers.json"),
    }
    if data is not None:
        payload["data_root"] = data
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def registry(data_root: Path, pid: str = "3002") -> Path:
    root = data_root / "project-registry" / "projects"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{pid}.json").write_text(json.dumps({
        "schema": "paos-project/v1", "id": pid, "revision": 1, "status": "active",
        "root_path": str(data_root.parent / f"Project-{pid}"),
        "sessions": [{"id": f"{pid}-s001", "status": "active", "mode": "managed"}],
    }), encoding="utf-8")
    return root


def test_missing_and_invalid_data_root_are_explicit(tmp_path):
    source = tmp_path / "Source"
    source.mkdir()
    path = descriptor(tmp_path, source=source, data=None)
    with pytest.raises(InstallationProblem) as error:
        load_installation_descriptor(path)
    assert error.value.code == "installation_data_root_missing"
    with pytest.raises(InstallHomesProblem) as error:
        build_install_home_coverage(path)
    assert error.value.status == 422
    absent = descriptor(tmp_path, source=source, data=str(tmp_path / "absent"))
    with pytest.raises(AttentionServiceProblem):
        _registry_projects_root(load_installation_descriptor(absent))


def test_query_does_not_create_missing_data_root(tmp_path):
    source = tmp_path / "Source"
    source.mkdir()
    missing = tmp_path / "not-created" / "data"
    path = descriptor(tmp_path, source=source, data=str(missing))
    with pytest.raises(InstallHomesProblem):
        build_install_home_coverage(path)
    assert not missing.exists()


def test_source_a_b_share_explicit_data_root(tmp_path):
    source_b = tmp_path / "SourceB"
    source_b.mkdir()
    (source_b / "private-data" / "project-registry" / "projects").mkdir(parents=True)
    decoy = source_b / "private-data" / "project-registry" / "projects" / "9999.json"
    decoy.write_text(json.dumps({"id": "9999", "sessions": []}), encoding="utf-8")
    data = tmp_path / "Data"
    registry(data)
    path = descriptor(tmp_path, source=source_b, data=str(data))
    result = build_install_home_coverage(path)
    assert result["scope"]["total"]["projects"] == 1
    assert result["homes"][0]["project_id"] == "3002"
    loaded = load_installation_descriptor(path)
    assert _registry_projects_root(loaded) == data / "project-registry" / "projects"


def _cli(tmp_path: Path, installation: Path, *args: str):
    env = dict(os.environ, PAOS_INSTALLATION_FILE=str(installation), PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "paos.py"), *args],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
    )


def test_configure_requires_and_preserves_data_root(tmp_path):
    from paos_installation import write_installation_descriptor

    installation = tmp_path / "installation.json"
    source = tmp_path / "Source"
    source.mkdir()
    with pytest.raises(InstallationProblem) as error:
        write_installation_descriptor(
            installation, source_root=str(source), library_roots_config=str(tmp_path / "l.json")
        )
    assert error.value.code == "installation_data_root_missing"
    data = tmp_path / "Data"
    write_installation_descriptor(
        installation, source_root=str(source),
        library_roots_config=str(tmp_path / "l.json"),
        rooter_home=str(tmp_path / "Rooter"), data_root=str(data),
    )
    # Update source only; data_root and other locators survive.
    write_installation_descriptor(
        installation, source_root=str(tmp_path / "Source2"),
        library_roots_config=str(tmp_path / "l.json"),
    )
    loaded = load_installation_descriptor(installation)
    assert loaded["data_root"] == str(data).replace("\\", "/") or Path(loaded["data_root"]) == data
    assert loaded["rooter_home"]
    with pytest.raises(InstallationProblem):
        write_installation_descriptor(
            installation, source_root=str(source),
            library_roots_config=str(tmp_path / "l.json"), data_root="",
        )


def test_install_show_reports_data_root_and_missing(tmp_path):
    source = tmp_path / "Source"
    source.mkdir()
    data = tmp_path / "Data"
    data.mkdir()
    path = descriptor(tmp_path, source=source, data=str(data))
    shown = _cli(tmp_path, path, "--json", "install", "show")
    assert shown.returncode == 0, shown.stderr
    payload = json.loads(shown.stdout)
    assert payload["data_root"] and payload["data_root_exists"] is True
    broken = descriptor(tmp_path / "broken", source=source, data=None) if False else None
    missing = tmp_path / "missing.json"
    missing.write_text(json.dumps({
        "schema": "paos-installation/v1", "source_root": str(source),
        "library_roots_config": str(tmp_path / "l.json"),
    }), encoding="utf-8")
    failed = _cli(tmp_path, missing, "--json", "install", "show")
    assert failed.returncode == 1
    assert json.loads(failed.stderr)["error_code"] == "installation_data_root_missing"


def test_backup_and_restore_use_registered_data_root(tmp_path):
    source = tmp_path / "Source"
    source.mkdir()
    data = tmp_path / "Data"
    (data / "project-registry" / "projects").mkdir(parents=True)
    (data / "project-registry" / "projects" / "3002.json").write_text("{}", encoding="utf-8")
    archive = tmp_path / "backup.zip"
    manifest = create_backup(source, archive, data_root=data)
    assert manifest["file_count"] == 1
    target = tmp_path / "Restored"
    restored = restore_backup(source, archive, data_root=target)
    assert restored["schema"] == "paos-install-backup/v1"
    assert (target / "project-registry" / "projects" / "3002.json").is_file()
    assert not (source / "private-data").exists()


def test_build_server_uses_data_root_and_explicit_library_registry(tmp_path):
    import local_server

    source = tmp_path / "Source"
    source.mkdir()
    data = tmp_path / "Data"
    (data / "project-registry" / "projects").mkdir(parents=True)
    explicit = tmp_path / "Explicit Library" / "roots.json"
    explicit.parent.mkdir()
    explicit.write_text("{}", encoding="utf-8")
    path = descriptor(tmp_path, source=source, data=str(data))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["library_roots_config"] = str(explicit)
    path.write_text(json.dumps(payload), encoding="utf-8")
    from project_store import ProjectStore
    server = local_server.build_server(
        "127.0.0.1", 0, data / "inbox" / "tips",
        ProjectStore(data / "project-registry"), installation_path=path,
    )
    try:
        assert server.data_root == data
        assert server.library_roots_path == explicit
        assert server.project_store.root == data / "project-registry"
    finally:
        server.server_close()
        local_server.close_logging()


def test_core_main_entry_starts_with_data_root(tmp_path):
    source = tmp_path / "Source"
    source.mkdir()
    data = tmp_path / "Data"
    (data / "project-registry" / "projects").mkdir(parents=True)
    path = descriptor(tmp_path, source=source, data=str(data))
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "attention-dashboard-v1-static" / "local_server.py"),
         "--port", "0", "--installation-file", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
    )
    try:
        time.sleep(1.5)
        assert proc.poll() is None, proc.stderr.read()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_backup_cli_defaults_to_registered_data_root(tmp_path):
    source_b = tmp_path / "SourceB"
    (source_b / "private-data").mkdir(parents=True)
    (source_b / "private-data" / "wrong-source.txt").write_text("decoy", encoding="utf-8")
    data = tmp_path / "Data"
    (data / "project-registry").mkdir(parents=True)
    (data / "canonical.txt").write_text("canonical", encoding="utf-8")
    path = descriptor(tmp_path, source=source_b, data=str(data))
    archive = tmp_path / "backup.zip"
    env = dict(os.environ, PAOS_INSTALLATION_FILE=str(path), PYTHONIOENCODING="utf-8")
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "paos_backup.py"), "backup",
         "--repo-root", str(source_b), "--output", str(archive)],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    import zipfile
    names = zipfile.ZipFile(archive).namelist()
    assert "private-data/canonical.txt" in names
    assert all("wrong-source" not in name for name in names)


def test_core_refuses_missing_data_root_without_creating_it(tmp_path):
    import local_server
    from paos_installation import InstallationProblem

    source = tmp_path / "Source"
    source.mkdir()
    missing = tmp_path / "absent" / "data"
    path = descriptor(tmp_path, source=source, data=str(missing))
    with pytest.raises(InstallationProblem) as error:
        local_server.build_server("127.0.0.1", 0, None, installation_path=path)
    assert error.value.code == "installation_data_root_unavailable"
    assert not missing.exists()


def test_corrupt_existing_descriptor_is_not_overwritten(tmp_path):
    from paos_installation import write_installation_descriptor

    installation = tmp_path / "installation.json"
    original = "{broken-json"
    installation.write_text(original, encoding="utf-8")
    with pytest.raises(InstallationProblem) as error:
        write_installation_descriptor(
            installation, source_root=str(tmp_path / "Source"),
            library_roots_config=str(tmp_path / "l.json"),
            data_root=str(tmp_path / "Data"),
        )
    assert error.value.code == "installation_descriptor_invalid"
    assert installation.read_text(encoding="utf-8") == original


def test_powershell_locators_strict_and_utf8():
    for name in ("install.ps1", "backup.ps1", "restore-backup.ps1"):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "-Encoding UTF8" in text
        assert r"$driveAbsolute = $raw -match '^[A-Za-z]:[\\/]'" in text
        assert r"StartsWith('\\')" in text
        assert "StartsWith('//')" in text
        assert r"StartsWith('\\\\')" not in text
        assert "if (-not [System.IO.Path]::IsPathRooted($raw))" not in text
