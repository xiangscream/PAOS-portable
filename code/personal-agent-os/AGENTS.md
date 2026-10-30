# PAOS Agent Entry (development)

## What this repository is

Personal Agent OS is a local-only control plane for durable work facts — Projects, fixed Agent Homes, Current responsibilities, decisions, and Mail/Notice/activation evidence — stored as JSON by a transactional project store and served by a local HTTP service plus a CLI. Native runtimes (Codex, Claude Code, DeepSeek Harness, …) do the actual reasoning and execution; this repo keeps the state that survives them.

## Where business operating rules live (current entry)

Roles, work cycles, Notice/Mail handling, activation contracts, and write protocols are **not defined in this file**. They are maintained in the installation's shared workflow library (`PAOS-Libraries/workflow/`): read `CATALOG.md`, then `Guides/guide-work-method.md` (work cycle + recovery) and `Guides/ops-entry.md` (operations), reached through each fixed Agent Home's `ENTRY.md` and the Project-level `AGENTS.md`. Do not copy a second set of operating/entry rules into repository docs; if a doc claims business semantics, point it at the library entry instead.

## Architecture (current = v3 normal path; historical v2 chain marked)

**Current normal entry (v3)**: agents work through the CLI surface
(`scripts/paos.py` and its `paos_*` service modules) directly against fixed
Homes (`Workstations/<agent>/` holding ENTRY.md, TODO.md, mailbox/, notices/).
Durable state has two real writers: Project JSON is written only by
`ProjectStore` (`private-data/project-registry/projects/<id>.json`; sibling
focus.json, preferences.json, backups/, context-packs/), while Home files are
written by their respective `paos_*` writers (TODO via the `paos_todo_v3`
writer, mailbox mail files via the mail writer, Notice records via the
notice writer, activation sidecars via the attention/activation writers) —
there is no single unified store for both. Mail, Notice, activation, wake,
Property Contacts/Project Registry, step invocation and handoff all live on
this path; recovery/responsibility for agents restores from these facts.

Below is the historical HTTP + WorkflowService chain. It is **kept and
load-bearing for internal plumbing/compatibility**, but it is **not** the
current business entry nor the recovery/responsibility path — treat it as
v2-era internal legacy when reasoning about business semantics:

```text
scripts/start.ps1
  → attention-dashboard-v1-static/paos_server.py   (thin shell, sets X-PAOS-Runtime-Fingerprint)
  → attention-dashboard-v1-static/local_server.py  (HTTP routes GET/POST/PUT, error mapping, static fallback guard)
      → workflow_service.py  WorkflowService — thin facade over mixins; the authoritative
        mixin list is the `class WorkflowService(...)` declaration at the top of
        workflow_service.py: Session / Coordination / Decision workflow mixins,
        Agent-continuity workflow, and TypedReference / Coordinator-continuity /
        Agent-continuity / ArtifactRevision / WorkingMemory hook mixins.
      → contracts: project_contracts.py, session_contracts.py, coordination_contracts.py,
        agent_continuity_contracts.py, reference_contracts.py (+ project_schema.py) —
        payload normalization and validation only.
      → project_store.py  — the ONLY project-state disk writer.
          root: private-data/project-registry/
          files: projects/<id>.json (plus focus.json, preferences.json, backups/,
          context-packs/)
Read-only projections beside them (same directory, part of the historical
HTTP chain, not the v3 normal entry): context_compiler.py,
session_projection.py, office_projection.py, relations_projection.py,
lifecycle_projection.py, needs_me_projection.py, session_lifecycle.py.
CLI shared modules (the v3 normal path surface) live in scripts/: paos.py plus
paos_attention_service.py, paos_mail.py, paos_notice.py, paos_home.py,
paos_todo_v3.py, paos_installation.py, paos_contact.py and related paos_*
modules. local_server.py inserts scripts/ into sys.path, so the two trees are
one runtime; attention-dashboard-v1-static/ is not self-contained.
Frontend (attention-dashboard-v1-static/): ui-common.mjs, projects-model.mjs,
projects.mjs, ux-polish.mjs and HTML/CSS assets.
CAT boundary: CAT lives in the separate co-agent-2 repo; this repo only consumes CAT
through HTTP. No CAT runtime behavior belongs here.
```

## Store invariants (do not refactor for style)

`ProjectStore` keeps mutate_v2 / revision / Ledger / operation receipt / backup /
Restore / atomic write and the shared data-root lock. These are load-bearing; edit
only when a change's semantics genuinely require it, and keep receipts/revision
checks intact.

## Before editing

1. Read [`docs/DEVELOPMENT-PRINCIPLES.md`](docs/DEVELOPMENT-PRINCIPLES.md) (current
   principles). [`docs/CODE-MAP.md`](docs/CODE-MAP.md) is a **historical locating
   map** — use it only to find files; its Work-era business semantics are not the
   current business contract (current operating contract lives in the shared
   workflow library above), and it should not be treated as a mandatory read for
   business semantics.
2. Choose baseline checks proportional to the change: documentation-only edits need
   content/link review; localized code changes need affected checks; core state
   transitions, shared contracts, integration, and release need the full verifier
   below. Recorded results may substitute per its stated rule — re-run affected
   checks after changes, failures, or environment differences.
3. Never edit `private-data/` unless the task explicitly requires it.

## Verify

```bash
python scripts/verify.py
```

Seven gates: Architecture, Python tests, Derived data, Node UTC, Node Asia/Shanghai,
Python compileall, JS `node --check`.
