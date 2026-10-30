# PAOS V1.1 — M3E-2001-C Decision

Decision owner: zrx
Evidence baseline: M3E-2001-B handoff `0431aea649f8e727e7d237d6552ccefe435ac62d`

## 1. Verdict

M3E-2001-B is accepted as:

```text
BLOCKED-UNRESOLVED-ARTIFACT
```

The next packet is:

```text
M3E-2001-C = ROOT-SENSITIVE ARTIFACT FACT CLOSURE
```

It remains read-only.

Project 2001 is not authorized to create a new Vault, stage content, implement relocation v2, or mutate root/key_files/Artifacts.

## 2. Mainline interpretation of the 106 unresolved rows

The 106 rows are not one uniform blocker class.

Current evidence supports the following default dispositions, subject to exact live recheck:

- WSL-form paths under `/mnt/c/.../OBSBOT-first-month-workspace/.paos/**` are runtime evidence and should be reclassified from UNRESOLVED to RETAIN;
- pointers into Project 3002 are CROSS_PROJECT_REFERENCE and should RETAIN;
- absolute Downloads/Desktop package paths are cutover-stable external references by default and should RETAIN unless current evidence proves they are canonical LRC101 content selected for the new Vault;
- absolute temporary/missing paths such as `/tmp/cat-unverified` are historical/data-quality facts, but do not become root-cutover blockers merely because the target is missing;
- the remaining root-sensitive blocker is the set of relative/no-root Artifact paths whose meaning may change when Project `root_path` changes.

Therefore M3E-C focuses on the live relative/no-root set, currently observed as 45 rows.

Do not ask the Human to classify the whole 106-row set before machine-resolvable facts are closed.

## 3. Project locality / ownership policy

Human decision: the LRC101 Vault must contain the practical working corpus, not merely an index of external locations.

Use two independent classifications:

```text
content_semantics:
  MOVE-CANONICAL
  COPY-LOCAL
  REFERENCE-ONLY
  RUNTIME-EVIDENCE
  HISTORICAL
  UNRESOLVED

transaction_pointer_action:
  MOVE
  RETAIN
  REBIND
  UNRESOLVED
```

Default intent:

- LRC101-owned current/process documents -> MOVE-CANONICAL;
- related inputs, meeting notes, research material and useful external packages -> COPY-LOCAL when a local copy improves normal Project work;
- live Feishu sources, other-Project executable/source repositories, runtime/application state -> REFERENCE-ONLY or RUNTIME-EVIDENCE;
- useful LRC101 outputs found inside runtime containers must be promoted into the Vault even though the runtime container itself stays outside.

A COPY-LOCAL file keeps its original source authoritative and records provenance in `Materials/_sources.jsonl`.

See `M3E-2001-VAULT-LOCALITY-DECISION.md`.

Human ownership decision is required only where evidence cannot determine whether an item is LRC101-owned, a useful Project-local reference copy, or truly outside Project scope.

## 4. Relative Artifact rule

A relative Artifact path is not safe to carry unchanged across Project root relocation unless its resolution base is explicitly independent of Project `root_path`.

Each relative Artifact must resolve to one of:

```text
PROJECT-CONTENT
RUNTIME-EVIDENCE
EXTERNAL/SHARED-REFERENCE
HISTORICAL-BROKEN
UNRESOLVED
```

Resolution must use provenance before filename guessing:

1. Artifact `source_session_id`;
2. linked `work_item_ids`;
3. Session/Cycle/Workstation output locations;
4. known workspace-M Project-content locations;
5. exact bounded basename/path search inside those provenance-derived roots.

No whole-disk search.

If multiple candidates exist:

- identical candidates may be recorded as duplicates, but one provenance-backed locator must be selected for the Artifact pointer plan;
- distinct candidates remain UNRESOLVED until provenance or Human evidence chooses one.

## 5. Contract refinement to test

M3E-B proposed `artifact_retains[]` with unchanged paths.

M3E-C must determine whether that is sufficient for relative runtime/historical references.

If a relative Artifact resolves to a physical file that should remain in the legacy location, relocation v2 may need an explicit pointer-rebind semantic:

```text
physical file: retain in legacy location
Artifact pointer: relative old value -> absolute stable legacy locator
```

This rebind, if needed, must occur in the same root-relocation transaction. It must not be a separate pre-cleanup mutation.

M3E-C does not implement this. It only proves whether the semantic is required and returns the exact rows that need it.

## 6. Exit condition

M3E-C must return:

- exact live Artifact snapshot and bucket counts;
- all relative/no-root Artifact rows resolved or explicitly unresolved;
- corrected content-semantics counts plus MOVE / RETAIN / REBIND / UNRESOLVED pointer-action counts;
- list of rows requiring pointer rebind;
- list of truly Human-dependent ownership decisions, if any;
- smallest relocation-v2 contract delta required by the real data.

Coordinator verdict must be exactly one:

```text
READY-FOR-CONTRACT-IMPLEMENTATION
NEED-HUMAN-OWNERSHIP-DECISION
BLOCKED-UNRESOLVED-RELATIVE-ARTIFACT
```

Only the first authorizes a later implementation packet.
