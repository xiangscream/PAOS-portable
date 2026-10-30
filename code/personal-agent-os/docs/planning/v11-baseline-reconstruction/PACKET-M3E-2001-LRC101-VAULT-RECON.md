# PAOS V1.1 — Packet M3E-2001 LRC101 Independent Obsidian Vault Reconstruction

Decision owner: zrx
Mode: read-only discovery / no Project mutation
Target Project: `2001 LRC101`

## 0. Goal

Prepare LRC101 to become an independent Obsidian Vault and PAOS canonical Project root at:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
```

The packet does not yet create that root.

The purpose is to replace filename archaeology and monthly-workspace ambiguity with an exact migration manifest for the active Project.

## 1. Roles

### s027 — primary mapper

Update own TODO first.

Own the factual inventory:

- live PAOS 2001 registry/project state;
- both known legacy workspace families;
- current 2001 Artifact/key-file references;
- current Work/Session operational references;
- candidate current Project-owned files;
- exact writers/readers where determinable;
- proposed target mapping.

Do not mutate any 2001 source.

### s029 — independent reviewer

Update own TODO first.

Independently challenge:

- ownership assumptions;
- current-vs-historical classification;
- hidden shared consumers;
- hidden writers;
- proposed Project-vs-shared-material boundary;
- key_files atomicity;
- Human-DND boundary;
- Workstation/M4 interaction.

No mutation.

### s031 — runtime/path specialist, only if needed

Read-only support for:

- current Runtime-resolved 2001 paths;
- active Agent/Workstation path dependencies;
- process/writer evidence;
- Windows/WSL path reachability.

Do not restart or rebind anything merely for this packet unless Coordinator separately authorizes a diagnostic action.

### s010 — Coordinator

Maintain the accepted task boundary, collect reports, resolve obvious duplicates, and STOP for zrx after the final readback.

Do not turn local mapper proposals into mutation authority.

## 2. Baseline facts to capture first

Capture current Project 2001 through the real PAOS read path:

```text
revision
root_path
key_files
Artifacts: id/path/type/purpose/current relation
active/recent Work
active/recent Sessions
Requests/Decisions only where they carry operational paths
stable Workstation locators
```

Also capture the current deployed PAOS build SHA.

Do not infer current truth from old planning documents if live PAOS state differs.

## 3. Bounded source scope

Known legacy workspace families:

```text
C:\Users\remo\Desktop\OBSBOT-first-month-workspace
C:\Users\remo\Desktop\OBSBOT-workspace-M
```

Inventory only:

1. paths directly referenced by live 2001 governance/work/session/workstation facts;
2. clearly LRC101/2001-owned directories and files under the two roots;
3. immediate parent/sibling context needed to decide ownership;
4. known current Human LRC101 working material.

Do not broad-scan the entire disk.

Do not treat every occurrence of the string `LRC101` as Project ownership.

## 4. Artifact-family map

Group candidate material by semantic family before mapping individual files.

At minimum test for families such as:

```text
current product definition / PRD
strategy / positioning
research / evidence
meeting notes / Human working docs
current presentation/report outputs
Agent-produced current Work
Decision records
shared OBSBOT references
historical snapshots/packages
generated/rebuildable indexes
runtime / Session / Workstation evidence
```

These are categories to investigate, not assumptions that each exists.

For every file/directory candidate, record:

```text
source_path
source_family = FM | WORKSPACE-M | OTHER-KNOWN
owner = 2001 | SHARED | OTHER-PROJECT | UNKNOWN
truth_class = PROJECT-CURRENT | PROJECT-MATERIAL | SHARED-REFERENCE |
              HUMAN-DND | HISTORICAL | GENERATED-REBUILDABLE |
              RUNTIME-EVIDENCE | UNKNOWN
current_role
writer
consumer(s)
registry_artifact_id if any
key_file = yes/no
hash/size/mtime when file-based
proposed_target_or_reference
action = COPY | REFERENCE | RETAIN-IN-PLACE | DEFER | UNKNOWN
reason
```

## 5. Divergence analysis

Where the same logical document/family appears in both FM and workspace-M:

- do not select by filename alone;
- compare hashes/content/mtime/history where available;
- identify whether one is ancestor, duplicate, independently edited fork, generated copy, or different semantic artifact;
- identify which copy current Work/Session/Human practice actually uses.

Return unresolved forks explicitly.

Do not merge text during this packet.

## 6. Human-DND boundary

Produce a compact list of current Human-authored LRC101 material that must not be rewritten during migration.

Default:

```text
copy byte-for-byte
preserve filename
preserve relative grouping when it carries meaning
no semantic cleanup
no bulk rename
no frontmatter injection
no deletion
```

If a candidate destination requires reorganization that would alter Human working habits, flag it for Human decision rather than normalizing it automatically.

## 7. New Vault mapping

Propose a staged destination map under:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
```

Use the standard additive root:

```text
Inbox/
Materials/
Works/
Decisions/
Workstations/
Archive/
```

Rules:

- the root itself is the Obsidian Vault;
- no nested `Vault/`;
- do not copy a legacy shared `.obsidian/`;
- do not force every source document into one of the six folders if a reference is more correct;
- Project-current outputs belong under a clear current Work/Materials/Decision home;
- shared materials stay references;
- runtime evidence stays runtime evidence;
- historical bulk is not required for first cutover.

A proposed `INDEX.md`/home note may be recommended, but do not create it in this read-only packet.

## 8. Cutover-feasibility gates

### G1 — current truth completeness

Every active/current 2001 file family has one proposed canonical destination or explicit shared reference.

### G2 — writer map

No current 2001 write authority is hidden or UNKNOWN for a file that would move.

### G3 — key_files

Every live key_file is classified.

If a MOVE-WITH-PROJECT key_file needs atomic switch with root and Artifacts, verdict is `NEED-CONTRACT-EXTENSION` unless an equally safe contract already exists.

### G4 — Artifact pointers

Every current Artifact path that would become invalid after root switch is mapped to an exact destination.

### G5 — Workstation continuity

Root cutover cannot strand the active Agent's stable ENTRY/TODO/mailbox.

Legacy runtime/Cycle evidence is not a reason to copy it into the Vault.

### G6 — Human-DND

Human-created current material has an explicit no-rewrite staging rule.

### G7 — rollback

Old sources remain available and the proposed mutation can be copy-first, verify, cutover-last.

## 9. Required outputs

s027:

```text
s027/V11-M3E-2001-LIVE-TRUTH.md
s027/V11-M3E-2001-ARTIFACT-FAMILY-MAP.md
s027/V11-M3E-2001-VAULT-MAPPING.md
s027/V11-M3E-2001-WRITER-CONSUMER-MAP.md
```

s029:

```text
s029/V11-M3E-2001-INDEPENDENT-REVIEW.md
```

s031, only if used:

```text
s031/V11-M3E-2001-RUNTIME-PATH-READBACK.md
```

Coordinator:

```text
coordinator/V11-M3E-2001-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3E-2001-RECON.md
```

The Coordinator readback must end with exactly one readiness verdict:

```text
READY-FOR-STAGED-MIGRATION
NEED-CONTRACT-EXTENSION
NEED-HUMAN-DND-DECISION
BLOCKED-UNKNOWN-WRITER
BLOCKED-OWNERSHIP
```

## 10. Prohibited actions

This packet does not authorize:

- creating `2001-LRC101`;
- copying/moving/renaming LRC101 files;
- modifying either legacy monthly workspace;
- modifying Project 2001 registry/root/key_files/Artifacts;
- creating a migration Decision inside the future Vault;
- moving or rewriting stable Workstations;
- moving `.paos/agents` or `.paos/workstations`;
- importing a shared `.obsidian/`;
- archiving either monthly workspace;
- migrating 1001/1002;
- changing Workflow/Skill libraries.

## 11. Stop gate

After independent review and Coordinator readback:

```text
STOP
```

zrx decides the mutation packet from the evidence.
