#!/usr/bin/env python3
"""Render/check docs/AUTHORITY-MATRIX.md from the executable manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "attention-dashboard-v1-static"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from authority_manifest import render_authority_markdown  # noqa: E402

TARGET = ROOT / "docs" / "AUTHORITY-MATRIX.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rendered = render_authority_markdown()
    if args.write:
        TARGET.write_text(rendered, encoding="utf-8")
        print(f"wrote {TARGET.relative_to(ROOT)}")
        return 0
    current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if current != rendered:
        print("AUTHORITY-MATRIX.md is out of date; run --write", file=sys.stderr)
        return 1
    print("AUTHORITY-MATRIX.md is in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
