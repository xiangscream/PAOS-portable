"""Prepare the caller's registered receiver, manually or from SessionStart."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

from paos_attention_service import AttentionServiceProblem, _registry_projects_root
from paos_contact import load_native_targets
from paos_home import HomeProblem, project_agent_home, rooter_home
from paos_installation import InstallationProblem, load_installation_descriptor, resolve_installation_path
from paos_workstation import WorkstationProblem, posix_windows_drive_locator
from runtime_injection import InjectionError
from wakeup_native.codex_receiver import ReceiverError, retire_owned_runtime


def registered_target(thread_id, descriptor):
    """Read registered Project/Rooter Contacts, then validate the matching Home."""
    registry = _registry_projects_root(descriptor)
    if not registry.is_dir():
        raise ValueError("project_registry_missing")
    matches = []
    for project_file in sorted(registry.glob("*.json")):
        project = json.loads(project_file.read_text(encoding="utf-8"))
        root_locator = project.get("root_path")
        if not root_locator:
            continue  # Unhoused projects have no Project Home or Contact root.
        root = Path(posix_windows_drive_locator(root_locator))
        targets = load_native_targets(root) or {}
        for agent_id, target in targets.items():
            if target.get("runtime") == "codex" and target.get("session_id") == thread_id:
                home = project_agent_home(project=project, agent_id=agent_id)
                matches.append((home, target))
    rooter_locator = descriptor.get("rooter_home")
    if rooter_locator:
        root = Path(posix_windows_drive_locator(rooter_locator)).expanduser()
        # Same Home id/root contract as the public Rooter Contact route.
        target = (load_native_targets(root) or {}).get(root.name)
        if target and target.get("runtime") == "codex" and target.get("session_id") == thread_id:
            home = rooter_home(home_path=root, home_id=root.name)
            matches.append((home, target))
    if len(matches) != 1:
        raise ValueError("contact_thread_not_registered" if not matches else "contact_thread_ambiguous")
    return matches[0]


def prepare(event):
    if event.get("hook_event_name") != "SessionStart" or event.get("source") not in {"startup", "resume"}:
        return "receiver_prepare_skipped: unsupported_event"
    return prepare_current(event=event)


def prepare_current(*, event=None, update=False):
    """Resolve only the current Desktop Owner; never accept a target override."""
    thread_id = os.environ.get("CODEX_THREAD_ID", "")
    if not thread_id or not os.environ.get("CODEX_APP_TOOLS_PIPE_PATH"):
        return "receiver_prepare_skipped: original_desktop_environment_missing"
    if event is not None and event.get("session_id") != thread_id:
        return "receiver_prepare_skipped: event_thread_mismatch"
    if os.name != "nt":
        return "receiver_prepare_skipped: windows_desktop_required"

    descriptor = load_installation_descriptor(resolve_installation_path())
    home, target = registered_target(thread_id, descriptor)
    # Bind establishes Contact configuration; concurrent Owner resumes are readers.
    extension = target.get("extension") or {}
    locators = [extension.get("receiver_runtime_file"), target.get("stop_file"), extension.get("windows_python")]
    if not all(isinstance(item, str) and item.strip() for item in locators):
        raise ValueError("receiver_binding_incomplete: complete the original Home's receiver registration, then --prepare-current")
    runtime, stop, python = [Path(posix_windows_drive_locator(item)) for item in locators]
    if not all(item.is_absolute() for item in (runtime, stop, python)):
        return "receiver_prepare_skipped: registered_receiver_locators_not_absolute"
    if stop.exists():
        return "receiver_prepare_skipped: original_STOP_present"
    if update:
        retire_owned_runtime(runtime, stop)
    scripts = Path(posix_windows_drive_locator(descriptor["source_root"])) / "scripts"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with Path(f"{runtime}.prepare-{stamp}.stdout.log").open("wb") as stdout, Path(f"{runtime}.prepare-{stamp}.stderr.log").open("wb") as stderr:
        process = subprocess.Popen(
            [str(python), "-X", "utf8", "-B", "-m", "wakeup_native.codex_receiver",
             "--runtime-file", str(runtime), "--stop-file", str(stop)],
            cwd=scripts, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_BREAKAWAY_FROM_JOB,
        )
    action = "update" if update else "prepare"
    return f"receiver_{action}_started: {home['home_id']} PID {process.pid}; read readiness through wake status."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument("--prepare-current", action="store_true",
                        help="Prepare only this Desktop caller's registered receiver; no hook event required.")
    commands.add_argument("--update-current", action="store_true",
                          help="Update only this Desktop Owner's verified receiver; keep STOP and unknown instances.")
    args = parser.parse_args()
    exit_code = 0
    try:
        if args.update_current:
            message = prepare_current(update=True)
        elif args.prepare_current:
            message = prepare_current()
        else:
            event = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
            message = prepare(event)
    except (OSError, UnicodeError, ValueError, KeyError, HomeProblem, InstallationProblem,
            AttentionServiceProblem, WorkstationProblem, ReceiverError, InjectionError) as exc:
        message = f"receiver_prepare_unavailable: {exc}"
        exit_code = 1 if args.prepare_current or args.update_current else 0
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
