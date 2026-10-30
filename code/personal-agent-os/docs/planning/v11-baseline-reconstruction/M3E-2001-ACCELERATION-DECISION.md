# PAOS V1.1 — M3E-2001 LRC101 Acceleration Decision

Decision owner: zrx
Human direction: prioritize migration of the two truly active Projects; start with LRC101
Prerequisite fact: M3C-1004 completed successfully on deployed main `5696ac877a550e06015ba491e983742713d2de27`

## 1. Decision

The previous preferred sequence:

```text
M3C-1004 -> M3D-1001/1002 -> M3E-2001
```

is superseded for execution priority by:

```text
M3C-1004 DONE
-> M3E-2001 LRC101 read-only reconstruction + migration design
-> bounded 2001 staged migration/cutover only after its own gate
-> M3D-1001/1002 later
```

Reason:

- 1004 has already proven the Project-first root and atomic governance-cutover pattern;
- 2001 LRC101 is one of the two genuinely active large Projects and benefits immediately from a stable canonical work world;
- 1001/1002 are thin routine Projects and are no longer a hard prerequisite for learning whether Project-first storage works;
- delaying 2001 would keep the highest-value active Project split across legacy monthly roots.

This changes priority, not safety discipline.

## 2. Frozen target

Future canonical root:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
```

This directory is intended to be both:

1. PAOS Project 2001 canonical root;
2. the independent Obsidian Vault opened by the Human for LRC101.

Do not create a nested `Vault/` layer.

Canonical additive Project layout remains:

```text
2001-LRC101/
├─ Inbox/
├─ Materials/
├─ Works/
├─ Decisions/
├─ Workstations/
└─ Archive/
```

An Obsidian `.obsidian/` directory is local UI/config state. It is not PAOS governance truth, is not required for migration correctness, and must not be copied wholesale from either legacy shared workspace.

## 3. What belongs in the Vault

The migration must classify material before copying it.

### PROJECT-CURRENT

Current LRC101 Project truth:

- current product-definition / PRD / strategy outputs;
- current research syntheses and evidence owned by 2001;
- current Decisions;
- current 2001 Work artifacts;
- Project-specific materials required to continue active work.

These are candidates for the new Vault.

### SHARED-REFERENCE

Cross-Project OBSBOT material is referenced, not duplicated merely to make the Vault self-contained.

Examples may include company-wide source material, common competitor/reference libraries, or evidence consumed by multiple Projects. Exact items must be proven by inventory.

### HUMAN-DND

Human-authored working material must be preserved byte-for-byte during staging unless the Human explicitly approves transformation.

No cleanup, renaming, semantic rewriting, Markdown normalization, frontmatter injection, or folder beautification is implied by migration.

### RUNTIME-EVIDENCE

Session logs, Cycle evidence, legacy Agent/runtime state, and runtime transport files are not automatically promoted into the Project Vault.

They stay in their existing evidence layer unless M4 explicitly migrates a stable Agent home or the read-only map proves a specific current Workstation dependency must move with Project root cutover.

### HISTORICAL / GENERATED

Historical snapshots and generated/rebuildable outputs are not automatically copied into the current Vault. Keep them where they are unless they are still current operational inputs or a later archive task accepts them.

## 4. Why 2001 needs its own reconstruction gate

Accepted M3 facts already show:

- `OBSBOT-first-month-workspace` and `OBSBOT-workspace-M` are both live lineages;
- 2001 consumes truth from both;
- 2001 is the highest-value/highest-risk Project in the shared OBSBOT cluster.

Therefore this is not a one-subtree copy like 1004.

Before any filesystem mutation, the system must identify:

```text
current canonical artifact families
+ exact source path(s)
+ current write authority
+ readers/consumers
+ registry Artifact pointers
+ key_files
+ Work/Session operational references
+ current stable Workstation dependencies
+ Human-DND material
```

## 5. Critical cutover questions

### 5.1 key_files

Project 2001 may have live `key_files` pointing to one or both legacy roots.

The current `project.root.relocate` contract atomically changes `root_path` plus Artifact pointers, not arbitrary `key_files`.

Therefore the read-only gate must classify every live `key_files` entry as:

```text
MOVE-WITH-PROJECT
KEEP-AS-SHARED-REFERENCE
HISTORICAL
STALE
UNKNOWN
```

If current Project truth requires an old-root key_file to move atomically with root cutover, return:

```text
NEED-CONTRACT-EXTENSION
```

Do not accept a transient split-truth sequence merely to avoid extending the contract.

### 5.2 Workstations

Do not bulk-move `.paos/agents`, `.paos/workstations`, or Session/Cycle evidence.

Inventory whether Project 2001 already has stable `Workstations/<agent-id>/` homes that are operationally tied to the current root. If cutover would strand a current Agent entry/TODO/mailbox, M3E must coordinate that exact stable-home move with M4 before root switch.

### 5.3 shared material

A self-contained-looking Vault is not the goal if it creates duplicate truth. Shared materials may remain external references until a canonical OBSBOT `Shared-Materials` location is separately accepted.

## 6. Authorization

Authorized now:

```text
M3E-2001-A = READ-ONLY RECONSTRUCTION
```

No 2001 filesystem copy/move, no new Vault creation, no registry mutation, no root relocation, no Workstation mutation, and no legacy-root archive is authorized by this decision alone.

The executable packet is:

`PACKET-M3E-2001-LRC101-VAULT-RECON.md`

## 7. Expected next decision

The read-only packet must return exactly one migration readiness verdict:

```text
READY-FOR-STAGED-MIGRATION
NEED-CONTRACT-EXTENSION
NEED-HUMAN-DND-DECISION
BLOCKED-UNKNOWN-WRITER
BLOCKED-OWNERSHIP
```

Only `READY-FOR-STAGED-MIGRATION` authorizes zrx to define the mutation packet.

1001/1002 remain valid later migrations, but they are no longer prerequisites for starting 2001 reconstruction.
