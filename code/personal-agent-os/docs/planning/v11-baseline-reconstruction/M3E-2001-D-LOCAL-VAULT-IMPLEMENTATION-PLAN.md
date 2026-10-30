# PAOS V1.1 — M3E-2001-D Local Vault Implementation Plan

Decision owner: zrx  
Local execution owner: s010  
Primary implementer: s027  
Independent reviewer: s029  
Runtime/deployment support: s031 when needed

## 1. Goal

Build a clean, practical, independent LRC101 Project Vault at:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
```

The Vault must be the normal working corpus for both Humans and Agents.

M3E-D ends the previous Web-led file-by-file archaeology phase. Local Agents now own the detailed implementation because they can inspect the real filesystem, current writers, duplicates, Obsidian behavior and PAOS state directly.

Web/mainline keeps only:

- Project/Vault architecture;
- content semantics;
- governance invariants;
- final merge/deploy/cutover gate.

## 2. Authority split

### zrx / Web mainline

Owns:

- target Project model;
- locality-first Vault principle;
- canonical vs reference vs runtime boundaries;
- minimum relocation contract invariants;
- final go/no-go for code merge, deployment and real Project-2001 governance cutover.

Does not own:

- exact folder placement for every file;
- exact duplicate-resolution algorithm;
- per-file hash bookkeeping;
- naming cleanup details;
- the last nine relative-path investigations;
- day-to-day copy tooling.

### s010 — local Coordinator

Owns the local implementation run.

Responsibilities:

- create bounded Work/Requests for M3E-D;
- let s027 make implementation decisions inside the frozen principles;
- request s031 only when runtime/deployment evidence is needed;
- reconcile only material blockers;
- return a concise mainline readback rather than another full migration diary.

### s027 — primary local implementer

Owns:

- detailed Vault information architecture;
- staged filesystem construction;
- source-to-Vault mapping;
- MOVE-CANONICAL / COPY-LOCAL / REFERENCE-ONLY classification refinement;
- provenance sidecar generation;
- practical duplicate/version cleanup;
- resolution of the remaining relative Artifact cases;
- relocation-v2 implementation branch/PR;
- local test and dry-run evidence.

s027 may use judgment. It does not need Web approval for ordinary file-placement decisions that do not change the frozen architecture.

### s029 — independent reviewer

Reviews outcomes, not paperwork volume.

Focus:

- does the Vault work as a Project workspace;
- are important current documents present and discoverable;
- is canonical/reference/runtime separation understandable;
- were current files lost or silently replaced;
- does relocation v2 preserve atomicity and rollback;
- are any unresolved current-content paths still capable of producing split truth.

s029 is not required to re-hash or manually re-audit every copied file.

### s031 — Runtime/deployment specialist

Use only for:

- deployed build verification;
- service restart/recovery;
- runtime path continuity;
- single-writer process evidence;
- post-merge deployment.

Do not use s031 as a general file-migration worker.

## 3. Frozen content semantics

Use these meanings throughout the implementation.

### MOVE-CANONICAL

LRC101-owned Project documents that should become normal/current inside the Vault.

Examples:

- current PRD/product-definition/strategy documents;
- Project process documents;
- reviews and handoffs;
- change notes and stage summaries;
- LRC101 meeting evidence owned by the Project;
- useful LRC101 deliverables.

Physical migration is still copy-first and rollback-safe. "MOVE" means canonical ownership after cutover, not an unsafe filesystem cut before verification.

### COPY-LOCAL

Related material that materially improves Project working locality.

Examples:

- downloaded meeting notes;
- research inputs;
- external review packs;
- relevant reference files;
- useful snapshots from runtime outputs or other locations.

The source remains intact. The Vault copy is a Project-local working/reference snapshot.

Record provenance in:

```text
Materials/_sources.jsonl
```

### REFERENCE-ONLY

Keep external when localization would be misleading or operationally wrong.

Typical cases:

- live Feishu/online documents;
- source repositories owned by another Project;
- centrally maintained shared systems;
- executable code that should stay with its owner.

### RUNTIME-EVIDENCE

Runtime machinery stays outside the Project content layer:

- ENTRY/TODO/mailbox;
- Session/Cycle metadata;
- runtime state;
- app state;
- legacy `.obsidian/` / `.workbuddy/`.

Useful LRC101 outputs produced inside runtime containers may still become COPY-LOCAL snapshots inside the Vault.

### HISTORICAL

Preserve but do not treat as current Project truth.

## 4. Local implementation freedom

Within the semantics above, local Agents may decide:

- exact subfolders below `Materials/`, `Works/` and `Archive/`;
- whether two equivalent files should be represented by one canonical copy plus provenance;
- whether a related external file is worth COPY-LOCAL;
- how to represent historical version families;
- how to resolve the remaining relative/no-root Artifact paths;
- whether a useful runtime output belongs in Reviews, Process, Deliveries or another sensible Project location;
- which file-copy tool to use;
- which integrity check is appropriate for each risk level.

The result should be clean and learnable. Do not preserve historical folder chaos merely because it existed.

Do not rewrite Human-authored document contents for tidiness unless a separate content-editing task authorizes it.

## 5. Vault structure

Required top-level shape:

```text
2001-LRC101/
├─ INDEX.md
├─ Inbox/
├─ Materials/
├─ Works/
├─ Decisions/
├─ Workstations/
└─ Archive/
```

This is the stable information contract.

Substructure is local-implementation judgment.

A sensible starting point may include:

```text
Materials/
  Research/
  Meetings/
  Reference-Snapshots/
  _sources.jsonl

Works/
  Current/
  Process/
  Reviews/
  Deliveries/
```

Do not treat this suggestion as a mandatory taxonomy if the real corpus suggests a cleaner structure.

## 6. Integrity policy

M3E-D does **not** require full SHA-256 auditing of every migrated file.

Use risk-proportionate verification.

### Tier A — cutover-critical canonical files

Examples:

- current main PRD/product-definition documents;
- key Decisions;
- files directly referenced by key_files;
- files whose identity is ambiguous because duplicates exist;
- small files that form the governance/cutover boundary.

Verify strongly when useful:

- byte-for-byte comparison;
- SHA-256;
- or an equivalent deterministic content comparison.

The tool may generate hashes automatically, but the handoff does not need to list hundreds of hashes.

### Tier B — ordinary MOVE-CANONICAL / COPY-LOCAL bulk material

Normally sufficient:

- source exists;
- destination exists;
- copy command succeeded;
- file count/size are plausible;
- files are readable;
- targeted spot checks for suspicious or duplicate families.

Use hash only when ambiguity, copy failure or rollback risk justifies it.

### Tier C — references/runtime/historical retained outside

No copy integrity check is needed if the item is not copied.

### Final integrity requirement

Before cutover:

- no known current canonical document selected for migration is missing;
- no obvious zero-byte/truncated copy exists;
- high-value duplicates have an explicit chosen current/canonical treatment;
- rollback source remains available.

## 7. Remaining relative Artifact cases

The remaining relative/no-root Artifact cases are no longer a separate Web-led migration phase.

s027 resolves them during local implementation using provenance and the real filesystem.

Rules:

- historical/generated missing references may be classified HISTORICAL-BROKEN and do not automatically block Project migration;
- runtime-relative references may be REBIND candidates;
- current Project-content references must resolve to one safe current destination before final cutover;
- if a current-content Artifact remains genuinely ambiguous after bounded local investigation, it is a cutover blocker and should be escalated.

Do not block Vault construction merely because historical registry rows are imperfect.

## 8. Relocation v2 implementation

Local Agents are authorized to implement and review the next relocation contract in a code branch/PR using disposable data only.

The exact request schema and internal code structure are local implementation decisions, but the semantic invariants are frozen.

One Human-only operation must be able to atomically change:

```text
Project root
+ exact ordered key_files before/after
+ Artifact pointers that move into the new Vault
+ Artifact pointers that stay external
+ relative Artifact pointers that must be rebound to stable locators
```

Required invariants:

- exact base revision;
- identical replay is idempotent;
- changed replay conflicts;
- old root matches the request;
- current key_files exactly match the declared before-state;
- affected Artifact current paths are explicit preconditions;
- root/key_files/Artifact pointer changes commit in one Project revision;
- one Ledger event / durable receipt;
- rollback contains the complete before-state needed to recover;
- generic `project.update(root_path)` remains forbidden;
- v1/simple migrations remain compatible;
- Work/Sessions/Requests/Decisions are not silently rewritten.

The contract must not become a general Artifact-cleanup endpoint.

No real Project-2001 relocation may run during M3E-D.

## 9. Local execution sequence

### D1 — create staged working Vault

s010 opens the implementation Work. s027 creates the target Vault structure and begins staging content.

The new root may physically exist before governance cutover, but it is labeled staged/non-canonical until the final transaction succeeds.

Legacy sources remain intact.

### D2 — organize the working corpus

s027 performs the practical migration:

- MOVE-CANONICAL candidates staged into the Vault;
- COPY-LOCAL material staged with provenance;
- INDEX/navigation created;
- runtime/application state excluded;
- duplicates/version families handled with local judgment;
- remaining relative Artifact cases resolved as part of the work.

### D3 — implement relocation v2 in parallel

s027 creates the implementation PR.

s029 independently reviews contract semantics and executable tests.

No production 2001 mutation.

### D4 — local usability review

s029 performs a Project-level review.

At minimum, starting from the staged Vault only, verify that a fresh Agent or reviewer can locate:

- the current/main PRD or product-definition document;
- recent relevant meeting material;
- important research/evidence;
- recent review/handoff/process output;
- current Decisions;
- where ongoing work should continue.

The purpose is to prove the Vault works without legacy-folder archaeology.

### D5 — mainline handoff

s010 returns a concise handoff.

Required outputs:

```text
coordinator/V11-M3E-2001-D-COORDINATOR-READBACK.md
s027/V11-M3E-2001-D-VAULT-READBACK.md
s027/V11-M3E-2001-D-CONTRACT-READBACK.md
s029/V11-M3E-2001-D-INDEPENDENT-REVIEW.md
```

Working manifests may remain in the local Project/Vault and do not need to be duplicated into a giant handoff report.

## 10. What the handoff must answer

Mainline needs only these decisions:

### Vault

- Does the staged Vault exist and open normally in Obsidian?
- Can Human/Agent normal work stay inside it most of the time?
- Are current Project docs/process docs/materials discoverable?
- Are COPY-LOCAL sources traceable?
- Is runtime/app state kept out of Project content?

### Current-content safety

- Are there any unresolved **current** Project documents that would become invalid at cutover?
- If yes, list only those blockers.
- Historical/broken registry residue should be reported separately, not inflated into a current-content blocker.

### Contract

- Is relocation v2 PR ready for mainline merge review?
- Does it provide the required atomic semantics?
- Did focused/full local verification pass?
- Are there new P0/P1 issues?

### Cutover readiness

Return one final status:

```text
READY-FOR-MAINLINE-MERGE-AND-CUTOVER-GATE
BLOCKED-CURRENT-CONTENT-AMBIGUITY
BLOCKED-CONTRACT
BLOCKED-VAULT-USABILITY
```

Then STOP.

## 11. Not authorized yet

M3E-D does not authorize:

- real Project-2001 root/key_files/Artifact mutation;
- deletion of legacy LRC101 content;
- archiving the monthly workspaces;
- moving stable Workstations/runtime state into the Vault;
- production deployment of relocation v2 before mainline review/merge;
- declaring the staged Vault canonical before the governance cutover.

The final cutover remains a mainline decision after local implementation evidence is available.
