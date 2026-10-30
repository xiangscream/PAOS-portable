# PAOS V1.1 — Packet M3E-2001-C Root-Sensitive Artifact Closure

Decision owner: zrx
Mode: read-only
Project: 2001 LRC101

## 0. Goal

Close the root-sensitive Artifact facts that still block relocation-v2 implementation.

The scope is deliberately narrower than M3E-B.

Do not attempt another full LRC101 content inventory.

## 1. Baseline

Read live Project 2001 through PAOS first and record:

```text
deployed build SHA
revision
root_path
key_files
Artifact count
relative/no-root Artifact count
absolute external / WSL / cross-Project bucket counts
```

If counts differ from M3E-B, save the exact live snapshot used for this packet and explain the delta.

## 2. s027 — primary resolver

Update own TODO first.

### C-001 Freeze one Artifact snapshot

Save one machine-readable snapshot for this packet.

Output:

```text
s027/V11-M3E-2001-C-LIVE-ARTIFACT-SNAPSHOT.json
```

The snapshot must include enough provenance for every Artifact:

```text
id
path
type
purpose
source_session_id
work_item_ids
replaces / version metadata when present
```

Do not mutate registry data.

### C-002 Correct the easy false-unresolved buckets

Re-evaluate the M3E-B UNRESOLVED rows using exact live paths.

Expected first-pass semantics:

- `/mnt/c/.../FM/.paos/**` runtime machinery -> RUNTIME-EVIDENCE / RETAIN, but inspect whether a useful LRC101 output inside the container should be promoted into the Vault;
- 3002 repo source/code -> REFERENCE-ONLY / RETAIN unless the item is a static reference snapshot that materially improves LRC101 locality;
- Downloads/Desktop LRC101 material -> evaluate for COPY-LOCAL by default rather than automatic RETAIN;
- `/tmp` absolute historical/temporary path -> HISTORICAL / RETAIN for cutover purposes, even if the target is missing;
- live external URLs -> REFERENCE-ONLY / RETAIN unless an explicit exported snapshot is useful.

For any COPY-LOCAL candidate, record the proposed Vault path and source provenance. Do not copy it during M3E-C.

### C-003 Resolve every relative/no-root Artifact

For each live relative Artifact, record:

```text
id
raw_path
source_session_id
work_item_ids
candidate_roots_checked
resolved_absolute_path
exists
semantic_class
content_semantics = MOVE-CANONICAL | COPY-LOCAL | REFERENCE-ONLY | RUNTIME-EVIDENCE | HISTORICAL | UNRESOLVED
future_action = MOVE | RETAIN | REBIND | UNRESOLVED
proposed_pointer
proposed_vault_path
source_provenance
evidence
```

Resolution ladder:

1. If raw path begins `.paos/`, resolve against the legacy FM root.
2. If raw path begins `第二个月/`, resolve against `OBSBOT-workspace-M`.
3. For `outputs/`, bare filenames, and version folders:
   - use source Session and linked Work first;
   - enumerate only that Session/Work's known Agent, Workstation, Cycle, review-workstation, delivery, and current Project output roots;
   - test the exact relative path, then exact basename only inside those bounded roots.
4. Use content hash only to distinguish same-name candidates after provenance narrowing.
5. Do not choose a candidate solely because it has the newest mtime.

If exactly one provenance-compatible candidate exists, resolve it.

If multiple byte-identical candidates exist, record the duplicate set and choose the provenance-primary locator.

If multiple distinct candidates or no credible candidate exists, keep UNRESOLVED.

### C-004 Classify broken relative references

A missing relative Artifact must not automatically block the whole migration forever.

Use its Work/Session provenance and purpose to classify:

```text
HISTORICAL-BROKEN
CURRENT-BROKEN
UNKNOWN
```

- HISTORICAL-BROKEN may be eligible for a stable legacy/historical pointer treatment in relocation v2;
- CURRENT-BROKEN remains P1;
- UNKNOWN remains unresolved.

Do not delete or hide the Artifact.

### C-005 Produce the corrected transaction map

Output:

```text
s027/V11-M3E-2001-C-TRANSACTION-MAP.jsonl
s027/V11-M3E-2001-C-RESOLUTION-REPORT.md
```

Each current Artifact must receive both a content semantic and a transaction pointer action.

Content semantics:

```text
MOVE-CANONICAL
COPY-LOCAL
REFERENCE-ONLY
RUNTIME-EVIDENCE
HISTORICAL
UNRESOLVED
```

Pointer actions:

```text
MOVE
RETAIN
REBIND
UNRESOLVED
```

Definitions:

- MOVE-CANONICAL: LRC101-owned current/process content becomes canonical in the Vault;
- COPY-LOCAL: source remains authoritative elsewhere, but a Project-local reference snapshot should be staged into the Vault with provenance;
- REFERENCE-ONLY: locator stays external;
- RUNTIME-EVIDENCE: runtime state stays outside the Vault;
- HISTORICAL: preserve, but do not make current Project content;
- MOVE(pointer): future PAOS pointer targets a staged Vault file, including COPY-LOCAL snapshots when the Project should discover the local copy first;
- RETAIN: pointer stays at an absolute/cutover-stable external location;
- REBIND: physical content stays outside the new Vault, but a relative pointer becomes a stable absolute locator atomically with root cutover;
- UNRESOLVED: cannot yet produce one safe post-cutover treatment.

Do not implement any transaction.

## 3. s029 — independent review

Update own TODO first.

Required output:

```text
s029/V11-M3E-2001-C-INDEPENDENT-REVIEW.md
```

Independently check:

- snapshot counts;
- whether the 42 WSL runtime rows were correctly recognized rather than silently normalized;
- all 45 relative/no-root rows from the accepted M3E-B baseline, adjusted only if live facts changed;
- at least every REBIND and UNRESOLVED row;
- whether Downloads/Desktop/legacy-workspace inputs should become COPY-LOCAL reference snapshots so normal LRC101 work stays inside the Vault;
- whether any external item is actually a live canonical input that must move;
- whether missing relative rows are truly historical rather than current broken outputs;
- whether the proposed v2 contract needs REBIND in addition to MOVE/RETAIN.

No mutation.

## 4. s031 — only if provenance needs Runtime evidence

s010 may request read-only support for a bounded list of Artifact IDs.

s031 may inspect Session/Cycle/runtime locator evidence only for those IDs.

No restart, rebind or state transition is authorized.

## 5. Coordinator

Return:

```text
coordinator/V11-M3E-2001-C-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3E-2001-C.md
```

Include:

- live Project revision/root;
- corrected bucket counts;
- content-semantics counts and MOVE / RETAIN / REBIND / UNRESOLVED pointer-action counts;
- exact unresolved IDs;
- exact REBIND IDs;
- Human ownership decisions still needed, if any;
- smallest relocation-v2 semantic set required.

End with exactly one:

```text
READY-FOR-CONTRACT-IMPLEMENTATION
NEED-HUMAN-OWNERSHIP-DECISION
BLOCKED-UNRESOLVED-RELATIVE-ARTIFACT
```

Then STOP.

## 6. Vault-locality acceptance check

Before returning READY-FOR-CONTRACT-IMPLEMENTATION, confirm that the proposed map would allow a future staged Vault to contain:

- current LRC101 mainline documents;
- useful Project process/review/handoff outputs;
- commonly needed related inputs as COPY-LOCAL snapshots where practical;
- source provenance for copied material;
- no runtime/application-state bulk import.

This is still a read-only design check.

## 7. Prohibited actions

M3E-C does not authorize:

- creating the LRC101 Vault;
- copying/moving/renaming LRC101 content;
- editing Project 2001;
- changing root/key_files/Artifact pointers;
- path-normalization writes;
- Artifact deletion/retirement;
- implementing relocation v2;
- Workstation migration;
- monthly-workspace archive.

Normal bounded Work/Request/Session lifecycle updates for executing this read-only packet are allowed.
