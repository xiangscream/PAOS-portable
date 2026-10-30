# Single-snapshot Session Detail v1

Status: S1-3 implementation contract.

## Required result

One Session Detail response must be built from exactly one current Project snapshot.

All fields derived from current Project state must describe the same captured revision, including:

- `project_revision`;
- the durable Agent / Session object;
- Mailbox;
- CAT binding facts stored in PAOS;
- current and historical Work projections;
- Cycle / Close projections;
- current timeline;
- current Artifacts and Requests;
- current Artifact lineage projection.

A writer may commit a newer Project revision after the query has loaded its snapshot. That does not invalidate the response: the response remains a coherent view of the revision it captured.

## What this does not mean

S1-3 does not hold a Store write mutex for the duration of an HTTP response and does not add a global read lock. The current Project JSON is loaded into one in-memory object and the composite query passes that object through pure projections.

The Context Pack body is different by design. A Context Pack is an immutable historical snapshot associated with a Cycle entry. Session Detail may separately read that Pack file and report its `available / missing / invalid` state. The Pack is not required to equal the current Project revision and must never be silently rebuilt from a later Project projection.

## Composition rule

A composite current-state query has one owner for loading current Project state. Downstream projection functions receive the captured Project object as an argument and must not call `ProjectStore.get_v2()` again.

In particular, Session Detail must not use an MRO decoration hook that calls `super().get_session_detail(...)` and then re-reads the Project to append another live field. Any live field that is purely derivable from Project state belongs in the same explicit projection composition.

S1-3 moves Artifact lineage into `session_projection.build_session_detail(project, session, ...)` and removes the `ArtifactRevisionHooksMixin.get_session_detail()` re-read. Artifact mutation and Context Pack hooks remain unchanged.

## Failure model

Before S1-3, this sequence is possible:

1. Session Detail reads Project revision N and builds `project_revision`, Session, Mailbox, timeline and current Artifact fields.
2. A writer commits revision N+1.
3. an outer query hook re-reads the Project and computes Artifact lineage from N+1.
4. the server returns one JSON object containing facts from N and N+1.

This is a correctness failure even though each individual read is valid.

After S1-3, step 3 has no second current-Project read. A concurrent writer can only affect the next request.

## Acceptance evidence

S1-3 is accepted only when all of the following are green on the exact candidate HEAD:

1. a deterministic sequenced-Store regression gives revision N on the first `get_v2()` call and N+1 on any illegal second call;
2. the real `WorkflowService.get_session_detail()` path performs exactly one `get_v2()` call;
3. `project_revision`, current `artifacts`, and `artifact_lineages` all come from revision N in that controlled test;
4. existing Session Detail, M5A Artifact lineage, Mailbox, CAT binding, Working Memory and typed-reference tests remain green;
5. a repository-wide query audit finds no remaining Session Detail decorator that re-reads current Project state;
6. `scripts/verify.py` and `git diff --check` are clean.

No browser behavior, CAT transport ownership, S1-2 writer locking, or S2 wholesale MRO refactor belongs in this package.
