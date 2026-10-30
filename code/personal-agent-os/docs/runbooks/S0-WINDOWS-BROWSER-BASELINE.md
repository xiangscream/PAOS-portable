# S0 Windows browser baseline

Purpose: collect the missing **real Windows/browser baseline evidence** for PAOS V1.0 S0 without changing business data or pretending that source/HTTP inspection equals a browser walkthrough.

This is an evidence runbook, not a product requirement or a PASS report. Record what actually happens.

## 1. Scope and starting point

Use a real Windows user environment with Chrome or Edge and a real repository checkout.

For the initial S0 baseline, record the exact checkout SHA. The review baseline is:

```text
PAOS main 1eb9ae0bd50f5bcb09789b9c74a5739075376a38
CAT  master aa4380b9c5bbf3355486505d515ee8901de31dcb
```

If main/master has moved before execution, do not silently substitute it. Record the actual SHA and state whether the evidence is for the original S0 baseline or for a later candidate.

Do not execute Continue, Close, Restore, Work Review, Decision acceptance, destructive file operations, or real business mutations merely to collect this baseline. Use an isolated synthetic/test project for actions that require writes. Existing real projects may be inspected read-only when necessary, with sensitive content excluded from screenshots and logs.

## 2. Checkout and runtime truth

From the PAOS repository root, record:

```powershell
git rev-parse HEAD
git status --short
git diff --check
.\scripts\verify.ps1
.\scripts\doctor.ps1
```

Expected evidence is not a prewritten PASS string. Save the actual command outputs or a concise transcript containing:

- exact HEAD;
- whether the worktree was clean before the walkthrough;
- `git diff --check` result;
- verifier 7-gate result and actual test counts;
- Doctor result;
- any warning/error that required recovery.

Start PAOS through the canonical path:

```powershell
.\scripts\start.ps1
```

Confirm that `/api/health` reports `paos-build-identity/v1` and that the running/static identity corresponds to the checkout being tested. If `start.ps1` or Doctor detects an old process/static mismatch, record the mismatch and recovery instead of restarting until the evidence disappears.

## 3. Browser baseline

Use the same browser window for the walkthrough. Record browser name/version and Windows version.

Capture the current product before V1.0 UI restructuring. The purpose is to preserve an honest before-state for S2/S4 comparison.

### Home / Projects

Record:

- what the first screen says is important;
- whether recent/pinned/current work is discoverable without understanding internal protocol terms;
- how a user reaches a Project;
- visible stale/historical/maintenance surfaces that compete with the main task;
- empty/loading/error behavior if naturally encountered.

### Project

Open a representative Project and record whether the page answers, without hunting:

1. What is being done now?
2. Who is responsible?
3. What needs Human attention?
4. What current results/artifacts exist?
5. What is the next normal action?

Also record where History, Suggestions/Office/Admin, raw requirements, and technical diagnostics appear relative to the normal path.

### Work

Open one Work without changing it. Record:

- objective / Done When visibility;
- owner/Agent relationship;
- blockers/status;
- current result visibility;
- whether a normal Human can tell how work will reach review;
- whether the UI pushes the user toward Admin/Correct State for a normal lifecycle action.

PR #35 Ready-for-Review backend is not part of main until Human merge approval. Do not treat a candidate API as a released UI feature.

### Agent

Open an Agent detail page and record:

- stable Agent identity versus Runtime binding;
- current Work and mission;
- current-cycle progress and actionable Mailbox;
- whether historical Ack/Close/cycles are visibly historical;
- whether Continue/current-runtime messaging/History are distinguishable;
- any place where a Human is asked to provide Runtime-internal fields.

Do not create a new Agent on real business data solely for this baseline.

### Artifacts / documents

Record how the user finds the current output and its source/version information. For visible paths, note whether the UI distinguishes a registered string from a path that is actually reachable on this machine. Do not open private paths outside the explicitly selected test scope.

### CAT, if installed for this evidence run

Record PAOS-offline and CAT-offline states separately where practical. In the Room, inspect without sending business messages:

- sender -> target clarity;
- stable participant identity;
- Reply preview/clear behavior;
- long-message and long-history readability;
- participant/text filtering if currently available;
- Runtime/connection diagnostics relative to the main conversation surface.

CAT is optional for base PAOS. Failure or absence of CAT must not be relabeled as a base PAOS failure unless the product incorrectly makes it mandatory.

## 4. Viewports and interaction evidence

For S0, collect at least the current desktop baseline at the actual user viewport. If convenient, also record 1440x900 and 1280x720. The mandatory three-size acceptance including 390 px belongs to S4, not S0.

For each page visited, note concrete friction rather than aesthetic preference:

- click/page transitions to reach the target;
- repeated input or repeated confirmation;
- internal concepts the Human must understand;
- competing equivalent entry points;
- clipped/overflowing controls or long text;
- loading/empty/error ambiguity;
- keyboard/focus/dialog failure if encountered.

Screenshots are useful only when they do not expose private project content, credentials, local private paths, tokens, or personal messages. Prefer a synthetic fixture for shareable evidence.

## 5. Evidence record

Use this minimal record for the walkthrough result:

```text
Date/time:
Operator:
Windows version:
Browser/version:
PAOS HEAD:
CAT HEAD (if used):
Worktree clean before:
git diff --check:
verify.ps1:
doctor.ps1:
health/build identity:
Data source: synthetic / read-only real project

Pages actually clicked:
- Home:
- Project:
- Work:
- Agent:
- Artifacts/docs:
- CAT (optional):

Observed blockers:
Observed non-blocking friction:
Evidence files/screenshots:
Worktree clean after:
```

A missing page or blocked environment is recorded as **not executed**, not PASS.

## 6. S0 interpretation

This walkthrough closes only the S0 baseline-evidence gap. It does not certify the future V1.0 UI.

Use the result as the before-state for S2/S4. S4 must repeat the relevant flows after implementation and show that the normal path no longer requires Admin correction, stale history is not presented as current work, and the declared viewport/keyboard/error-state acceptance actually passes.
