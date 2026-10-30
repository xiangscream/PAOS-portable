#!/usr/bin/env python3
"""Read-only CAT Room seam status for one participant (s027, P3 window).

Reads the room metadata Rooter already captured (no HTTP, no writes) and
reports the facts a switch/rollback window needs: exchange/un-ACK counts,
participant ownership generation, marker file presence.  Never mutates
co-agent-2 private-data; never ACKs; never fakes consumption.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def room_facts(room_meta_file: Path, participant: str) -> dict[str, Any]:
    data = json.loads(room_meta_file.read_text(encoding="utf-8"))
    out: dict[str, Any] = {
        "schema": "paos-p3-room-seam-status/v1",
        "meta_file": str(room_meta_file),
        "observed_at": data.get("observed_at"),
        "http_reachability": data.get("http_reachability"),
        "rooms": [],
    }
    for room in data.get("rooms", []):
        state = room.get("room_state") or {}
        participants = room.get("participants") or []
        entry = next(
            (p for p in participants if str(p.get("identity", {}).get("participant_id") or "") == participant),
            None,
        )
        out["rooms"].append(
            {
                "room_id": room.get("room_id"),
                "room_source": room.get("room_source"),
                "events_source": room.get("events_source"),
                "status": state.get("status"),
                "wake_mode": state.get("wake_mode"),
                "paos_binding": state.get("paos_binding"),
                "exchange_count": room.get("exchange_count"),
                "unacked_count": room.get("unacked_count"),
                "participant_present": entry is not None,
                "ownership_generation": (entry or {}).get("identity", {}).get("ownership_generation"),
                "native_session_id": (entry or {}).get("identity", {}).get("native_session_id"),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta-file", required=True, help="Rooter read-only room metadata json")
    parser.add_argument("--participant", required=True, help="e.g. p-3002-s027")
    args = parser.parse_args()
    facts = room_facts(Path(args.meta_file), args.participant)
    print(json.dumps(facts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
