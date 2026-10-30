# Canonical Library Roots V1.1

## Purpose

A PAOS installation may register one canonical Workflow Library and one canonical Skill Library.

The registry is local installation configuration, not Project governance state and not a second copy of Library content.

Default location:

```text
private-data/environment/library-roots.json
```

Schema:

```json
{
  "schema": "paos-library-roots/v1",
  "workflow_root": "C:/.../PAOS Workflow Library",
  "skill_root": "C:/.../PAOS Skill Library",
  "registered_at": "..."
}
```

The two roots must be distinct, existing, initialized A3 libraries.

### Cross-runtime locator rule

The registry stores a **stable installation locator**, not a runtime-specific
mount path.

For a Windows-hosted installation the canonical locator is Windows drive form,
normalized with forward slashes:

```text
C:/Users/.../PAOS-Libraries/workflow
C:/Users/.../PAOS-Libraries/skill
```

Native Windows validates these paths directly.

When the same installation is accessed from WSL/POSIX, PAOS maps a Windows
drive locator to its runtime filesystem path (for example
`C:/Users/... -> /mnt/c/Users/...`) only for access and validation. The
registry bytes are not rewritten to `/mnt/c/...`.

This keeps one installation registry usable by Windows-native and WSL Runtime
carriers and prevents whichever Runtime wrote the registry last from changing
the canonical locator syntax.

## CLI

Register once:

```text
paos library roots set \
  --workflow-root <workflow-library> \
  --skill-root <skill-library>
```

Inspect:

```text
paos library roots show
```

`--config <path>` is available for tests and explicit alternate installations.

When invoked from WSL, both root arguments and an explicit Windows-drive
`--config` locator are resolved to the corresponding `/mnt/<drive>/...`
path for filesystem access while preserving the Windows root locators in the
registry.

These commands are filesystem-only. They do not call PAOS HTTP and do not change Project revision, Session, Ledger or Work.

## Session Open integration

The A2 order remains unchanged:

```text
commit canonical PAOS Session
→ load installation library roots
→ provision Project-local Workstation
→ return Session + Workstation result
```

When a valid roots registry exists, a newly created Workstation receives:

```text
Workflow Library：<canonical workflow root>
Skill Library：<canonical skill root>
```

The same paths appear in the Workstation provisioning response.

If the registry file does not exist, A2 remains backward compatible: Workstation creation succeeds and ENTRY records both libraries as unregistered.

If a registry exists but is invalid, unreadable, points to missing/uninitialized roots, or otherwise cannot be trusted, Session creation remains committed but Workstation provisioning returns explicit `repair_required`. It never silently drops a configured root.

## Recovery

`paos workstation init <project> <agent>` inherits the canonical registered roots when explicit `--workflow-library` / `--skill-library` overrides are not supplied.

This keeps the A2 repair command semantically aligned with normal Session Open provisioning.

Explicit CLI library path arguments remain valid recovery overrides.

## Existing Workstations

A1 established that existing `ENTRY.md` and `TODO.md` bytes are never overwritten during repair.

A3b preserves that rule.

If a Workstation was created before library registration, or the installation later changes canonical roots:

- provisioning does not rewrite the existing ENTRY;
- it returns `entry_matches_registration=false`;
- it returns `entry_migration_required=true`.

Migration of existing ENTRY files belongs to the explicit V1.1 migration/R1 path, where edits can be inspected rather than silently replaced.

## Truth and ownership

- Workflow/Skill Markdown: Library content source truth.
- Skill usage events: usage source events.
- Library catalogs: derived indexes.
- `library-roots.json`: installation-local locator config.
- Project Workstation ENTRY: stable Agent entry document.
- PAOS ProjectStore: governance facts only.

The roots registry is deliberately outside Project JSON and never advances Project revision.

## Acceptance

1. Canonical roots registration is atomic and validates both libraries before replacing the registry.
2. Workflow and Skill roots cannot be the same directory.
3. Windows-drive root locators remain canonical Windows locators in registry
   bytes even when registration/validation runs from WSL.
4. Windows-drive `--config` locators are usable from WSL without creating a
   runner-local second registry.
5. Missing registry is a valid unregistered state.
6. Existing invalid registry fails visibly.
7. New Session Open injects registered roots into a newly created Workstation ENTRY.
8. Returned `entry_markdown` exactly matches disk and contains both registered roots.
9. Registry reads/writes do not mutate PAOS governance state.
10. Manual `workstation init` inherits registered roots by default.
11. Existing ENTRY bytes are not rewritten when registration appears or changes later.
12. Drift is surfaced as `entry_migration_required` for R1.
13. A1/A2/A3a regressions, full verifier and diff hygiene pass.
