# PAOS V1.1 — M3F-3002-E Production Cutover Decision

Decision owner: zrx  
Status: HUMAN-ONLY CUTOVER AUTHORIZED  
Date: 2026-09-22

## 1. Accepted candidate

The only authorized Project-3002 cutover source is:

```text
V11-M3G-3002-CUTOVER-INPUT-v4-S027.json
SHA-256 5314b3deaf87ec5581ff14cb84b7f9318f3f1cb5d269a852cb231680d18f87fd
base revision 654
```

Accepted evidence:

```text
86 Artifacts
0 MOVE
73 REBIND
13 stay_external
18 key_files_after
5 historical-source-absent locators excluded from current navigation
normalize PASS
disposable relocation 654 -> 655 PASS
idempotent replay PASS
s029 final delta review PASS
production mutation 0
```

The staged Project World and clean Source checkout are accepted.

Do not execute v1-v3.

Do not edit v4 during the production window.

The duplicate Source README entry in `key_files_after` and the legacy `DRAFT-v4` operation-id wording are non-blocking naming/navigation residue. They do not justify replacing the independently reviewed payload.

## 1.1 Source SHA freeze

The accepted production Source/runtime baseline for this cutover remains:

```text
3b86ac555a7526fcd5160fb7dd8404c98bad9733
```

This mainline authorization is documentation-only and may advance remote `main` after the v4 evidence was frozen.

Do not pull a newer main into the staged Source before E3 merely to match the newest remote commit. That would change the reviewed Source baseline for no runtime benefit.

After Project cutover and post-cutover acceptance, the new Source repository may fast-forward to the then-current main in a separate normal source update.

## 2. Revision rule

Project 3002 must remain revision `654` until the relocation operation begins.

Therefore:

- do not complete Work `3002-w057` before cutover;
- do not resolve or mutate any associated Project-3002 lifecycle object before cutover;
- do not perform any unrelated Project-3002 mutation during the execution window.

The production runtime/source handoff must preserve Project data without advancing the Project revision.

## 3. Production execution order

### E0 — freeze

Coordinator declares a short Project-3002 mutation freeze.

Confirm:

```text
revision = 654
root = C:\Users\remo\Desktop\agent学习计划\personal-agent-os
Artifacts = 86
key_files = 15
w057 = doing
```

Confirm the committed v4 SHA-256.

### E1 — production Runtime / installation-state handoff

Owner: s031.

```text
stop old writable runtime
-> snapshot/copy required canonical installation state
-> start exact main 3b86ac555a7526fcd5160fb7dd8404c98bad9733
   from staged Source/personal-agent-os
-> prove one service / one bridge / one writer
-> prove old writer remains stopped
```

This step must not call Project mutation APIs.

After the new runtime is live, re-read Project 3002 and require:

```text
revision = 654
old root unchanged
86 Artifacts
15 old key_files
```

Also verify registered Workflow/Skill roots and other installation facts required by the new runtime.

If revision is no longer `654`, STOP. Do not rewrite v4 inside the cutover window.

### E2 — final exact precondition read

Immediately before relocation:

- v4 SHA-256 still matches;
- live revision is `654`;
- `from_root_path` matches;
- ordered `key_files_before` matches;
- Artifact preconditions required by relocation-v2 still match.

No other Project mutation may occur between this read and E3.

### E3 — Human-only atomic Project relocation

Execute the v4 relocation-v2 payload once.

Expected live result:

```text
revision 654 -> 655
root -> C:\Users\remo\Desktop\agent学习计划\PAOS-Projects\3002-Personal-Agent-OS
key_files -> frozen 18-item key_files_after
Artifacts -> 73 REBIND + 13 retained
Ledger -> +1 project.root.relocated
receipt -> paos-project-root-relocate-receipt/v2
```

Replay the identical operation once only for idempotency verification. Revision must remain `655`.

### E4 — post-cutover acceptance

Before changing Work status, verify from the production runtime:

- new root is canonical;
- INDEX and current key files are readable;
- all non-historical current Artifact locators resolve;
- the 5 historical-source-absent locators are not exposed as current navigation;
- old root still exists;
- one writer remains active;
- Work / Session / Request / Decision collections were not rewritten by relocation.

s029 performs the independent post-cutover read-only review.

If this review fails, keep `w057` open and use the relocation receipt / rollback evidence.

### E5 — close the migration Work

Only after E4 PASS:

- complete `3002-w057`;
- resolve any remaining M3F execution Request/Assignment that is meant to close with that Work;
- accept the resulting Project revision advance as post-cutover lifecycle activity.

Do not expect Project revision to remain `655` after normal Work closeout.

### E6 — create fresh fixed Workstations

After `w057` is closed, create fresh homes under the new Project root for:

```text
s010  Project Lead / Coordinator
s027  Implementation / Integration
s029  Independent Reviewer / QA
s031  Runtime Reliability Specialist
```

Do not copy old ENTRY/TODO files.

Closing `w057` before Workstation provisioning prevents the migration Work from being seeded as the new baseline responsibility.

Then run fresh-Runtime cold-start acceptance.

## 4. Legacy root

Do not delete or archive the old root during E0-E6.

After fresh Workstations and normal work prove the new baseline:

- stop writing current outputs to the old root;
- retain it as legacy evidence;
- archive it in a separate later batch.

Compatibility with old daily-entry paths is not required.

## 5. WORKFLOW-PHILOSOPHY.md

`docs/WORKFLOW-PHILOSOPHY.md` in the old root does not block Project cutover.

Current disposition:

```text
legacy design source / historical reference
not canonical Source content
not a post-cutover key file
not current Project navigation
```

Artifact `3002-a073` may continue to point to the preserved old-root copy during the cutover.

Handle content in a separate post-cutover knowledge-consolidation batch before legacy-root archive:

1. compare the old document against:
   - `PRODUCT-AND-DESIGN-PHILOSOPHY.md`;
   - `wf-agent-work-cycle`;
   - `wf-coordinator-governance-cycle`;
   - `guide-project-work-world.md`;
2. identify only still-unique durable principles;
3. place surviving principles in the correct current authority:
   - Project/product philosophy -> current Source product/design philosophy;
   - universal working-method principle -> Workflow Library;
4. do not copy the old file wholesale into the new Source merely to preserve its filename;
5. if no unique current principle remains, retain the old file only as historical evidence.

This content review is independent of the production cutover.

## 6. Final authorization

The current mainline verdict is:

```text
AUTHORIZED-FOR-3002-PRODUCTION-CUTOVER
```

Execution must follow E0 -> E1 -> E2 -> E3 -> E4 -> E5 -> E6.

Any Project-3002 mutation before E3 invalidates the frozen revision-654 precondition and stops the run.
