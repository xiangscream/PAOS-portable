#!/usr/bin/env python3
"""Install the thin D1 Contact/Status package into one exact registered Home."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from paos_attention_service import resolve_home_by_registry
from paos_installation import resolve_installation_path
from paos_workstation import ensure_contact_package, refresh_generated_contact_py


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Install PAOS thin Contact/Status package into one exact registered Home.")
    parser.add_argument("agent_id", help="Exact registered Project Agent id or Rooter Home id")
    parser.add_argument("--installation-file", help="Existing PAOS installation descriptor path")
    parser.add_argument(
        "--refresh-generated",
        action="store_true",
        help="Update only an exact legacy-generated contact.py; keep manual edits",
    )
    args = parser.parse_args(argv)

    installation_path = resolve_installation_path(args.installation_file)
    home_ref = resolve_home_by_registry(
        args.agent_id,
        installation_file=str(installation_path),
    )
    if args.refresh_generated:
        result = refresh_generated_contact_py(
            home_path=Path(str(home_ref["home_path"])),
            home_kind=str(home_ref["home_kind"]),
            home_id=str(home_ref["home_id"]),
            project_id=str(home_ref.get("project_id") or ""),
            installation_file=str(installation_path),
        )
        print(json.dumps({
            "ok": True,
            "schema": "paos-contact-package-refresh/v1",
            "installation_file": str(installation_path),
            "home": home_ref,
            "package": result,
        }, ensure_ascii=False, indent=2))
        return 0

    result = ensure_contact_package(
        home_path=Path(str(home_ref["home_path"])),
        home_kind=str(home_ref["home_kind"]),
        home_id=str(home_ref["home_id"]),
        project_id=str(home_ref.get("project_id") or ""),
        installation_file=str(installation_path),
    )
    print(json.dumps({
        "ok": True,
        "schema": "paos-contact-package-install/v1",
        "installation_file": str(installation_path),
        "home": home_ref,
        "package": result,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
