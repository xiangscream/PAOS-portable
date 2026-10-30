# PAOS V1.1 — M3E-2001-E Pre-Cutover Completion

Decision owner: zrx  
Local execution owner: s010  
Primary implementer: s027  
Reviewer: s029 as needed

## 1. Current state

Accepted baseline:

```text
Project 2001 revision = 1068
root_path = C:\Users\remo\Desktop\OBSBOT-first-month-workspace
Artifacts = 377
live key_files = 10
staged Vault = C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
relocation v2 = merged and deployment-gated
production cutover = NOT AUTHORIZED
```

The latest narrow correction proved that the prepared `key_files_after` no longer contains stale Project-owned legacy locators, but two accepted MOVE-CANONICAL key files are not yet staged in the Vault.

Those two files are the only known content prerequisite before the final T1 / Human-only cutover gate.

## 2. Authorized local action

Stage these two accepted MOVE-CANONICAL files into sensible Vault-local canonical locations:

```text
LRC101-完整PRD调研总计划表-v0.1-2026-08-11.md
LRC101-场景环境标准与宠物速度检索-2026-08-13.md
```

Local Agents own the exact subfolder placement under the frozen Vault information architecture.

Requirements:

- preserve the source files until after successful governance cutover;
- do not rewrite their contents as part of migration;
- use a deterministic content comparison appropriate for these key-file-level documents;
- SHA-256 is allowed but not required if an equivalent byte/content comparison is used;
- do not reopen the 377-Artifact classification.

## 3. Rebuild the final cutover input

After both files exist in the staged Vault:

1. re-read live Project 2001;
2. require revision still equals `1068`;
3. keep `key_files_before` exactly equal to the live ordered 10-item list;
4. regenerate `key_files_after` from the staged Vault and accepted external/shared references;
5. replace the two excluded legacy entries with their Vault-local locators;
6. do not restore the old FM root or workspace-M paths;
7. do not preserve the old count merely for symmetry.

The final `key_files_after` must describe the Project surface Humans and Agents should actually use after cutover.

## 4. Narrow T1

Run one final no-new-writes checkpoint after the two files are staged and the payload is rebuilt.

T1 is not a whole-workspace freeze.

Scope only the current content sources whose state matters to the pending cutover, including:

- the two newly staged source files;
- other selected MOVE-CANONICAL source families that could still change between staging and cutover;
- Human-editable workspace-M current-content paths represented by the final transaction.

Explicitly exclude ongoing runtime-only writes such as:

```text
FM\.paos\**
```

unless a specific current-content file inside that tree is directly part of the cutover source set.

T1 should answer one question:

> Is the staged/current Project content still a faithful cutover candidate right now?

Do not turn T1 into another full migration audit.

## 5. Verification

Required before returning to mainline:

- both newly staged Vault files exist and are readable;
- their content matches the intended source;
- final `key_files_after` contains only readable Vault-local entries plus accepted live external/shared references;
- no stale Project-owned FM/workspace-M locator remains in `key_files_after`;
- relocation-v2 normalizer accepts the final payload;
- one disposable-store dry-run passes;
- idempotent replay passes;
- T1 passes;
- live Project 2001 remains revision 1068 with zero governance mutation.

No need to re-run:

- 377-Artifact inventory;
- full Vault archaeology;
- full-corpus hashes;
- relocation-v2 implementation review already accepted.

## 6. Local lifecycle

s010 should open one bounded pre-cutover Work.

s027 performs the two-file staging, payload rebuild and T1 evidence.

s029 may do a narrow independent check of the final payload/T1 result if s010 judges it useful. Do not require a full Vault re-review.

## 7. Handoff to mainline

Return one concise readback containing:

```text
live revision
two staged destination paths
content comparison = PASS/FAIL
final key_files_before count
final key_files_after count + values
stale Project-owned legacy key_files remaining
v2 normalize = PASS/FAIL
dry-run = PASS/FAIL
idempotent replay = PASS/FAIL
T1 = PASS/FAIL
production mutation = 0
```

Final verdict:

```text
READY-FOR-HUMAN-ONLY-CUTOVER-AUTHORIZATION
BLOCKED-STAGING
BLOCKED-T1
BLOCKED-CUTOVER-INPUT
```

Then STOP.

## 8. Still not authorized

M3E-2001-E does not authorize:

- invoking relocation v2 against real Project 2001;
- changing live root/key_files/Artifact pointers;
- deleting source files;
- archiving either legacy monthly workspace;
- migrating stable Workstations;
- declaring the staged Vault canonical.

The next production mutation requires a new explicit Human-only authorization from mainline.
