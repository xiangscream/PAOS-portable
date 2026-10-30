# G0 Governance Baseline — 2026-09-02

## Purpose

Freeze the evidence boundary before the G-round lifecycle-governance work. G0
changes no Project, Work, Session, Request, Decision, Ledger, receipt, or CAT
Room data.

## Source baseline

- Code source: `PAOS-HANDOFF-20260901.zip`
- Source SHA-256: `fc1670b1016c8e636d0e57e2e9bdbbe96776034411b6f8257a746055e1650638`
- Handoff states the source baseline is `main @ 6dff0b4`.
- The handoff intentionally contains no `.git` and no `private-data`; therefore
  this review workspace must not claim to be the user's live repository or the
  latest live Project data.

## Pre-change verification

```text
Architecture           PASS · 8 boundaries
Python                 346 PASS
Derived data           PASS
Node UTC               111 PASS
Node Asia/Shanghai     111 PASS
Python compileall      PASS
JS node --check        PASS
Overall                7/7 PASS
```

## Read-only regression evidence

The 2026-08-30 review package was used only as historical input. No file below
is copied into the product tree or written back to user data.

```text
2001 snapshot SHA-256  1fb937e591a69e0461d0707501be0e758e46c50ffbd766ff8e2b3b54dea459ee
3002 snapshot SHA-256  b5e9d266d2d73eb2b0476ed3386737735c0d75e0c62069d282df8093091770bf
CAT Room SHA-256       765552e4c0830fca0ee42a83cd453671b18326b104d348c0b437cafbc363efc6
```

The historical 2001 snapshot (revision 144) already contains six active
Sessions, including `s010→w005`, `s011→w018`, `s012→w016`, and `s013→w017`,
plus many `doing` Works with no active Session. This is sufficient to prove
that G1 must tolerate real historical data rather than only clean fixtures.

The operator later reported a newer live state (revision 157) and a subsequent
cleanup where a Work cancellation was used to clear stale Sessions. That newer
private data is **not present in this handoff**, so it is recorded as
operator-provided evidence rather than re-read or modified here.

## G-round safety locks

1. G1 is projection-only: no durable write path is added.
2. `doing + 0 active Agent` is a governance signal, not automatically Needs Me.
3. Existing Close evidence remains Agent voice and is not rewritten.
4. LRC101/Project 2001 is not mutated during G0/G1.
5. CAT is untouched in G1; G2b requires a fresh CAT source baseline before any write.
