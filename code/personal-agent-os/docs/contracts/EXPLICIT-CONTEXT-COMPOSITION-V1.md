# Explicit Context Pack composition v1

Status: S2-4 implementation contract.

## Product result

PAOS builds one Agent Context Pack through one named composition path. The result no longer depends on the order of Context-related mixins in `WorkflowService`.

S2-4 changes composition structure, not product meaning. Existing Context Pack fields, Prompt instructions, bounded projections, Runtime-tenure rules, CAT binding semantics, Artifact/Working Memory semantics and typed-reference semantics remain unchanged unless an existing test proves a correction is required.

## Composition boundary

`WorkflowService._compile_context_pack(project, session)` is the single service entry. It delegates to one explicit Context Pack composer.

The composer receives the already loaded Project and Session plus the Identity registry and environment-capabilities reference. It is a pure read/projection path: it does not read Project state again, write durable state, call HTTP/CAT, or resolve Artifact file bodies.

Context-only mixins must not own `_compile_context_pack`. In particular, the production result must no longer depend on a `super()._compile_context_pack(...)` chain across:

- Agent continuity;
- Mailbox;
- CAT binding;
- Artifact revision context;
- Working Memory context/safety;
- typed references.

Mutation hooks remain out of scope for S2-4.

## Explicit data composition

The composer builds current Context data from the single Project object supplied by the caller.

The stages are explicit and ordered by dependency:

1. derive the bounded Mailbox from canonical Project responsibility;
2. build the base Context Pack from a Context-only Project view that suppresses the legacy broad Request projection;
3. project current Working Memory, bounded Artifact index and related recent delta;
4. sanitize malformed/conflicting Working Memory for Context output;
5. project Artifact revision lineages;
6. project CAT binding without network access;
7. attach the bounded Mailbox;
8. project typed references;
9. attach the guarded execution claim when the current Cycle requires one.

The saved Context Pack remains a snapshot. This composition path never turns it into current Project truth.

## Prompt composition

The base Prompt is rendered exactly once after the Context data used by the base renderer has been assembled.

Feature-specific Prompt sections are then applied in one explicit order. Each section injector remains a pure string transformation over already projected data.

S2-4 must preserve the current externally visible Prompt meaning and section content. Existing golden and feature-specific Prompt tests remain the compatibility gate; no fixture change is accepted merely to make the refactor easier.

## Working Memory wrapper retirement

`BoundedWorkingMemoryHooksMixin` exists only to alter Context composition. After Context composition becomes explicit, `WorkflowService` uses the ordinary `WorkingMemoryHooksMixin` for Working Memory mutation semantics, while the existing sanitizer is called directly by the composer.

This must not change Working Memory append, lineage, Restore, conflict or exact-head behavior.

## Invariants

- One current Project snapshot enters Context composition; no stage calls `store.get_v2()`.
- `ProjectStore` remains the only persistence owner.
- Context composition performs no durable mutation and no CAT/network call.
- Mailbox remains a projection of canonical Requests/Assignments, not a second state store.
- Working Memory remains a special Artifact type with its existing write and Restore rules.
- Typed references do not gain new authority or persistence paths.
- Runtime execution claims are carried from the issued Cycle/Context Pack and are never refreshed by the composer.
- Human/Coordinator/Worker authority boundaries do not change.

## Acceptance

S2-4 is accepted only when the exact candidate HEAD satisfies all of the following:

1. `WorkflowService` directly owns the single `_compile_context_pack` service entry;
2. the former Context hook classes no longer define `_compile_context_pack`;
3. Context-only Mailbox/CAT/bounded-memory wrapper mixins leave the `WorkflowService` MRO, while ordinary Working Memory mutation semantics remain present;
4. the explicit composer contains exactly one base `build_prompt_markdown(...)` render;
5. feature-specific Context/Prompt suites for Mailbox, CAT binding, Working Memory safety, Artifact revision, typed references and Agent continuity remain green without weakening expectations;
6. Session Open, Continue, Reactivate and missing-Pack replay continue to produce valid Context Packs from the same existing workflow contracts;
7. `python scripts/verify.py`, Python compile checks and `git diff --check` pass;
8. an exact-checkout smoke compares representative pre/post Context Pack and Prompt output and explains every intentional difference; the default expectation is no product-content difference.

## Not in S2-4

- mutation-hook/MRO refactoring;
- new Session/Work/Request/Artifact business actions;
- CAT ownership fencing or recovery;
- Human UI changes;
- broader payload-size policy beyond preserving existing bounded Context projections;
- Workstation/Guide/Coordinator organization-loop work;
- install, backup or release packaging.
