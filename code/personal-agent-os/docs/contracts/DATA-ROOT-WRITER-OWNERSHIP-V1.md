# Data-root writer ownership v1

Status: S1-2 implementation contract.

## Required result

For one canonical PAOS project-registry data root:

- all `ProjectStore` instances inside one process serialize mutations through the same root-scoped mutex;
- only one PAOS executable may hold writer ownership for that root at a time;
- a second executable must fail immediately and clearly instead of becoming another writer;
- if the owner process exits or crashes, the operating system releases ownership so a replacement process can start without deleting a stale PID/lock file;
- revision, Ledger, receipt, backup, Restore and atomic-replace semantics stay unchanged.

This package fixes V1-02. It does not implement S1-3 single-snapshot reads or S5 Runtime/CAT ownership fencing.

## Canonical root identity

Root identity is derived from the resolved absolute path with platform case normalization. Different path spellings that resolve to the same data root must converge on one in-process mutex and one cross-process lease identity.

## Store-level serialization

`ProjectStore` remains the only project-state persistence layer. Its existing transaction critical sections continue to use `self._lock`, but that lock is no longer private to one Store object. Stores pointing at the same canonical root receive the same process-wide mutex.

The behavioral requirement is stronger than checking object identity: if Store A pauses after reading revision N, Store B for the same root cannot enter a competing mutation and commit another revision N+1 underneath it. After A commits, B must re-read the new state and follow the existing conflict/rebase rules.

Stores pointing at different roots do not block one another.

## Executable writer lease

The canonical PAOS server process must acquire a non-blocking OS file lock before serving the writable data root and hold it for the server lifetime.

The lock file is only a rendezvous point and diagnostic record. The kernel lock is the ownership truth. Therefore:

- an existing lock file does not by itself mean the root is busy;
- PID/timestamp metadata may be stale and must never be used as the authority for takeover;
- normal exit releases the kernel lock;
- process termination/crash also releases the kernel lock;
- a replacement process may reuse the same lock file immediately after the old kernel ownership disappears.

The rendezvous file lives under the system temporary directory rather than inside project business data. This avoids treating operational lock metadata as backup/project content and avoids keeping a Windows temporary project root undeletable merely because a lock handle is open.

## Failure contract

Writer-lease acquisition is fail-fast. Contention raises `DataRootInUseError` with stable code `data_root_in_use` and a recovery hint telling the operator to stop the other PAOS instance.

The server entrypoint should surface this as a concise startup failure, not continue in a degraded multi-writer mode.

## Supported implementation path

The lease uses standard-library OS primitives:

- Windows: `msvcrt.locking(..., LK_NBLCK, 1)` on a reserved byte;
- POSIX: `fcntl.flock(..., LOCK_EX | LOCK_NB)`.

Unsupported operating systems must fail closed rather than silently run without writer ownership.

## Acceptance evidence

S1-2 is accepted only when all of the following are green on the exact candidate HEAD:

1. deterministic same-process two-Store contention test proves only one mutation can commit from the same starting revision;
2. second process holding the same root is rejected with `data_root_in_use`;
3. kill/crash of the owner is followed by successful reacquisition without deleting the rendezvous file;
4. existing Store/Restore/transaction suites remain green;
5. `scripts/verify.py` and `git diff --check` are clean;
6. supported Windows execution repeats contention + crash/restart against the real checkout/server entrypoint.

No test may mark a stale metadata file itself as ownership evidence; only the OS lock decides ownership.
