# Growing project-scoped IDs v1

Status: S1-1 implementation contract.

## Scope

PAOS Project IDs remain fixed four-digit IDs (`1xxx`, `2xxx`, `3xxx`). Only durable objects scoped inside a Project grow beyond the historical three-digit suffix ceiling:

- Work: `<project>-wNNN...`
- Agent/Session: `<project>-sNNN...`
- Artifact: `<project>-aNNN...`
- Request: `<project>-rNNN...`
- Decision: `<project>-dNNN...`
- Work Suggestion: `<project>-gNNN...`
- Ledger Event: `<project>-eNNN...`

The canonical suffix spelling is:

- exactly three decimal digits for historical values `000` through `999`;
- ordinary decimal spelling without a leading zero for `1000` and above.

Examples: `3002-w001`, `3002-w999`, `3002-w1000`, `3002-w10000` are canonical. `3002-w01` and `3002-w0001` are not.

## Allocation and high-water rule

New allocation is `max(all historically observed canonical suffixes) + 1` for that Project and kind. The allocator must observe IDs in the current business collection and in retained Ledger/operation-receipt evidence, including `allocated_ids` and touched paths.

Restore may roll back current business objects, but it preserves Ledger and operation receipts. Therefore an ID that existed before Restore remains above the historical high-water mark and is never reused for a different object.

There is no artificial `999` ceiling. Formatting keeps a minimum width of three digits so existing low-number projects retain their current spelling.

## Compatibility

The new reader accepts every previously valid three-digit scoped ID unchanged. No existing ID is rewritten and no data-schema migration is required merely to enable growth.

A pre-S1 binary/reader that validates scoped IDs with exactly three digits cannot understand a Project after that Project first contains a `1000+` scoped ID. This is an explicit downgrade boundary: once an extended ID has been committed, do not use a pre-S1 binary to read or write that Project. V1.0 install/upgrade and recovery guidance must surface this boundary rather than pretending old binaries are forward-compatible.

Projects that have not crossed the boundary keep their existing three-digit IDs and remain structurally unchanged by this feature.

## Non-goals

This change does not:

- change Project ID allocation;
- introduce a new durable ID object or database sequence;
- compact, renumber, or recycle historical IDs;
- alter Store single-writer semantics (S1-2);
- alter query snapshot semantics (S1-3);
- claim downgrade compatibility after an extended ID has been written.
