# PAOS V1.1 — M3F-3002-R1 Artifact Locator Closure

Status: authorized narrow blocker closure  
Scope: 9 invalid Artifact rebind targets only

## Goal

M3F staging, clean Source checkout and runtime handoff rehearsal are accepted.

The only current blocker is that 9 proposed Artifact rebinds point to files that do not exist. They cannot be treated as stable post-cutover locators.

Do not reopen the full 3002 migration.

## Rule

For each of the 9 Artifacts, answer one question first:

> Does this Artifact still represent current Project truth or a current working entry?

### A. Current and source exists somewhere

Use the real existing source.

- Project-owned current content -> place/reuse it in the staged Project world and REBIND/MOVE to that real path.
- Repo-owned current content -> point to the real path under `Source/personal-agent-os`.
- External current source -> keep a stable external locator.

No placeholder files.

### B. Historical / superseded / old Runtime evidence

Do not recreate missing content.

Classify it as historical and remove it from normal current navigation.

If its original meaning must survive root relocation, use a stable absolute legacy locator only when that locator accurately records the historical location. A historical locator may describe missing historical evidence, but it must not be presented as a readable current entry.

It must not appear in post-cutover `key_files`, INDEX current links, or current Workstation navigation.

### C. Current but source does not exist

This remains:

```text
BLOCKED-CURRENT-TRUTH
```

Do not manufacture content from filenames, neighboring versions, summaries or memory.

Escalate only those Artifacts.

## Local evidence

For each of the 9, return:

```text
artifact_id
declared/current locator
owner/work/source if known
current_status = CURRENT | HISTORICAL | RUNTIME-EVIDENCE | EXTERNAL
source_exists = yes/no
final_action = MOVE | REBIND | RETAIN-HISTORICAL
final_locator
reason
```

Keep the reasoning short. This is a disposition table, not another migration report.

## Verification

After reclassification:

1. every current Artifact locator in the cutover payload resolves to an existing source;
2. no historical-broken Artifact is exposed as a current/key entry;
3. root-relative paths cannot silently change meaning after root cutover;
4. staged Vault and Source are otherwise unchanged;
5. rerun relocation-v2 normalizer;
6. rerun one disposable-store dry-run + idempotent replay;
7. s029 reviews only these 9 rows and their resulting payload delta.

No full Artifact re-audit.

## Stop point

Return:

```text
READY-FOR-3002-CLEAN-CUTOVER
BLOCKED-CURRENT-TRUTH
```

Real Project-3002 relocation remains Human-gated.
