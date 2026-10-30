# PAOS V1.1 — LRC101 Vault Locality Decision

Decision owner: zrx
Human direction: LRC101 Project Vault must contain the working corpus, not merely an index of external locations.

## 1. Product goal

The LRC101 Vault must be the default place where a Human or Agent enters the Project and can normally continue work without manually searching legacy monthly workspaces, Downloads, runtime folders, or unrelated Project roots.

Target root:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
```

The Vault optimizes **Project working locality**, not global deduplication.

A global authoritative source may remain unique while the LRC101 Vault keeps a Project-local reference copy with provenance.

## 2. Three content semantics

### 2.1 MOVE-CANONICAL — LRC101-owned Project documents

Project-owned documents move into the Vault as canonical Project truth.

Examples:

- current product definition / PRD / strategy documents;
- LRC101-specific meeting outputs and decision support;
- Project reviews, handoffs, change notes and phase summaries;
- Agent-produced LRC101 process documents that are useful to future work;
- current Project-owned evidence syntheses;
- LRC101-specific deliverables.

After cutover, Humans and Agents should use the Vault copy as the normal/current document.

Migration execution remains safe:

```text
stage copy
-> risk-proportionate integrity verification
-> governance cutover
-> old working copy becomes legacy/archive/non-current
```

"Move" describes canonical ownership. It does not authorize a risky filesystem cut before verification.

### 2.2 COPY-LOCAL — related material needed for normal Project work

Related input/reference material should be copied into the Vault when having a local copy materially improves normal discovery and work continuity.

Examples:

- downloaded meeting notes/transcripts used by LRC101;
- research inputs and evidence files used repeatedly by the Project;
- external review packs / GPT-Pro packages used as Project inputs;
- relevant company/reference documents that are practical to keep locally;
- useful source files currently scattered in Downloads/Desktop or legacy monthly workspaces.

The original source remains intact.

The Vault copy is a **Project-local reference snapshot**, not automatically the authoritative source of the external material.

Every copied reference must preserve provenance in a sidecar/source manifest rather than rewriting the source file.

Minimum provenance:

```text
local_path
source_path_or_url
source_owner
copied_at
hash_or_version_when useful
source_authority = external | shared | other-project | human-source
update_policy
```

Recommended manifest:

```text
Materials/_sources.jsonl
```

### 2.3 REFERENCE-ONLY — do not localize

Keep only a locator when copying would be wrong or misleading.

Default cases:

- live Feishu/online documents where the live service is the meaningful source;
- executable/source repositories owned by another Project;
- PAOS runtime / Session / Cycle state;
- large generated/rebuildable caches;
- application state such as legacy `.obsidian/` and `.workbuddy/`;
- shared systems whose meaning depends on remaining live and centrally maintained.

A small exported snapshot may still be copied when it is explicitly useful as evidence, but it must be labeled as a snapshot.

## 3. Runtime container vs Project output

Do not classify everything under `.paos/**` as one thing.

Separate:

```text
runtime container/state
vs
Project-useful output produced inside that runtime container
```

Runtime state stays outside the Vault.

A useful LRC101 output currently living inside a Session/Workstation output directory should be promoted into the Vault.

Default:

- runtime metadata / ENTRY / TODO / mailbox / Cycle machinery -> RETAIN;
- LRC101 review, handoff, summary, draft, analysis, index, change note, delivery artifact -> MOVE-CANONICAL or COPY-LOCAL depending on ownership.

The runtime original may remain as immutable evidence after promotion. It must not remain the normal working location.

## 4. Vault information architecture

The standard Project root remains:

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

Suggested LRC101 substructure:

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

This is a semantic target, not permission to reorganize files during the current read-only packet.

`INDEX.md` should point first to the current mainline documents and then explain where Project materials, process records, Decisions and historical work live.

## 5. Split-truth rule

A copied related file does not become a second authoritative external source merely because it lives in the Vault.

Use one of these labels:

```text
CANONICAL-PROJECT
PROJECT-REFERENCE-SNAPSHOT
EXTERNAL-LIVE-REFERENCE
RUNTIME-EVIDENCE
HISTORICAL
```

Rules:

- CANONICAL-PROJECT: Vault is the normal editable/current location after cutover.
- PROJECT-REFERENCE-SNAPSHOT: Vault copy is optimized for locality; provenance points to the external/shared source.
- EXTERNAL-LIVE-REFERENCE: locator only.
- RUNTIME-EVIDENCE: not Project content.
- HISTORICAL: preserved but not current.

## 6. Effect on M3E-C

M3E-C must no longer default all Downloads/Desktop/related external files to RETAIN merely because their absolute paths survive root relocation.

For each resolved item, classify both:

```text
content_semantics =
  MOVE-CANONICAL
  COPY-LOCAL
  REFERENCE-ONLY
  RUNTIME-EVIDENCE
  HISTORICAL
  UNRESOLVED

transaction_pointer_action =
  MOVE
  RETAIN
  REBIND
  UNRESOLVED
```

Examples:

- downloaded meeting note actively used by LRC101:
  `COPY-LOCAL + MOVE(pointer to Vault copy)`;
- LRC101 process note inside runtime output:
  `MOVE-CANONICAL + MOVE(pointer to Vault)`, while runtime evidence may preserve the old file;
- PAOS source file:
  `REFERENCE-ONLY + RETAIN`;
- relative runtime path:
  `RUNTIME-EVIDENCE + REBIND`;
- live Feishu URL:
  `REFERENCE-ONLY + RETAIN`.

## 7. Migration acceptance

A future LRC101 cutover is not complete merely because all Artifact pointers are technically valid.

The Vault must also satisfy:

- current LRC101 mainline documents are inside the Vault;
- useful Project process documents are discoverable inside the Vault;
- commonly needed related inputs are locally available where practical;
- reference snapshots carry provenance;
- Runtime/application state is not mixed into Project content;
- a Human or fresh Agent can start from the Vault and locate the normal working corpus without legacy-folder archaeology.

This decision supersedes the conservative external-retain default in the earlier M3E-C planning where it conflicts with Project locality.


## 8. Implementation ownership

Detailed file organization is delegated to the local PAOS Agents under `M3E-2001-D-LOCAL-VAULT-IMPLEMENTATION-PLAN.md`.

The Web/mainline layer does not prescribe per-file placement or require full-corpus hashing. Local implementation should optimize Project usability and preserve the architectural boundaries in this document.
