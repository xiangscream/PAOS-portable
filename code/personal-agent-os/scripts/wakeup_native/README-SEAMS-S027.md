> **历史说明（非现行入口）**：本文件记录 S027 时期已删除 worker 的设计与证据。
> 当前正常使用与登记请读安装 OPS：`PAOS-Libraries/workflow/Guides/ops-entry.md`
> 不要启用本文件提到的 `opencode-worker@` 或旧 adapter 脚本；
> S027 暂停保持。历史原文保留，不重写证据。

# P3 seams — worker registration, five-unit re-wiring, CAT Room switch (s027)

## 1. Long-running service registration (s027 owner code)

- Unit template: `scripts/wakeup_native/opencode-worker@.service` (this dir).
- Per-participant env: `/home/remo/.config/opencode/worker/<participant>.env`
  (same layout as existing `cat-adapter` env: WORKER_SCRIPTS / WORKER_BINDING /
  WORKER_HOME_REF / WORKER_STATE / WORKER_POLL_SECONDS).
- Register: `systemctl --user daemon-reload && systemctl --user enable --now opencode-worker@p-3002-s027.service`.
- Runtime evidence: `${WORKER_STATE}/<participant>/runtime.json`; budget:
  `budget.json` (persists across restarts); attempts under state_root
  `<state>/<project>/<agent>/<fingerprint>/attempts/`. Service-mode has NO
  submission cap (new sources always processed); window passes an explicit
  `--max-submitted-batches` for test limits only.

## 2. Five existing units re-wiring (Rooter executes, one per window)

Current: `opencode-cat-adapter@p-<agent>.service`
(`/home/remo/.config/systemd/user/opencode-cat-adapter@.service`,
`ADAPTER_SCRIPT=.../opencode_cat_adapter.py`, `SCOPE=.../scope.json`,
`OPENCODE_BASE=http://127.0.0.1:4102`, `POLL_MS=3000`).

Switch per participant during its approved window:
1. `systemctl --user stop opencode-cat-adapter@p-<agent>.service`
   (marker/state untouched — no ACK, no marker deletion).
2. Create `/home/remo/.config/opencode/worker/p-<agent>.env` (same
   OPENCODE_BASE; binding/home-ref for that agent).
3. `systemctl --user enable --now opencode-worker@p-<agent>.service`.
4. Observe runtime/budget evidence; real business round proves reading
   originals + useful w071 output before any further switch.

Rollback: stop worker unit → `systemctl --user start opencode-cat-adapter@p-<agent>.service`.
Markers/Exchange/ACK state never deleted; accepted/uncertain attempts stay.

## 3. CAT source import seam (owner split)

- Web P2 owner: durable CAT Exchange → `register_source_input` → Notice with
  activation intent (`activate_cat_exchange` currently bypasses it — that seam
  is the web author's P2 file; s027 does not duplicate the polling here).
- s027 owner (this worker): consumes `activation_work(Home)` only; no CAT
  polling, no parallel submitter. The worker never ACKs an Exchange; CAT ACK
  transport semantics stay with the CAT surface.

## 4. Room activation-owner migration entry (one-time, per Room)

Read-only status: `scripts/wakeup_native/room_seam_status.py` (s027) prints
the un-ACK count / marker / ownership-generation facts for one participant
from the read-only metadata Rooter already captured
(`reports/V13-CAT-METADATA-PREPARE-20261005.json`: room-e7f0cfaa5c5f has 1492
exchanges / 41 un-ACK; room-f96fc33111b9 has 876 / 9).

Migration (Rooter, once per Room at the approved window): stop the old
adapter for the participant → web P2 registers un-ACKed Exchanges as
Notices (backfill WITHOUT ACK/force/state rewrite) → worker unit starts and
reconciles them like any Notice. Ownership generation stays as-is; no batch
ACK, no marker edits, no business-state rewrites.

Recovery: stop worker unit → old adapter unit back up (its markers intact) →
un-ACKed Exchanges that were already backfilled as Notices stay pending
(they are not lost and not double-consumed: CAT ACK was never faked).

## 5. What this seam does NOT do

- Does not stop any consumer outside an approved window.
- Does not touch co-agent-2 private-data files directly.
- Does not claim production adoption before P6's single switch.
