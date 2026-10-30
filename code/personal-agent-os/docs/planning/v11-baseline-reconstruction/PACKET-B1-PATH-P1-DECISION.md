# Packet B1 Path P1 Decision — Canonical Library Locator Across Windows + WSL

Decision owner: zrx  
Scope: Packet B1 only; no Workflow/Skill content migration

## Observed P1

Packet B1 created the versioned empty shared Library roots successfully.

The remaining failure was locator syntax:

```text
roots set with C:\... from WSL
→ library_root_not_found

roots set with /mnt/c/... from WSL
→ succeeds
→ registry stores /mnt/c/...
```

A registry containing only `/mnt/c/...` is not acceptable as the final
installation locator because the same installation is also consumed by
Windows-native PAOS/Codex tooling.

Rewriting the registry from Windows without changing the code is also
insufficient because WSL consumers would then fail to validate `C:/...`
through the current loader.

## Decision

The installation registry stores a **host-stable canonical locator**.

For this Windows-hosted installation:

```text
workflow_root = C:/Users/remo/Desktop/agent学习计划/PAOS-Libraries/workflow
skill_root    = C:/Users/remo/Desktop/agent学习计划/PAOS-Libraries/skill
```

Runtime-specific mount syntax is an access concern, not registry truth.

Therefore:

```text
registry truth          C:/...
Windows filesystem      C:/...
WSL filesystem access   /mnt/c/...
```

PAOS resolves the stored locator to the current runtime path only for
filesystem validation/access and returns the canonical stored locator to
callers/Workstation ENTRY.

This gives one registry to Windows-native and WSL Runtime carriers instead of
allowing the last writer's environment to redefine the canonical path.

## Narrow implementation

The fix is intentionally limited to Library roots:

1. `paos_library.register_library_roots()`
   - accepts Windows-drive locators when called from WSL;
   - maps them to `/mnt/<drive>/...` only for validation;
   - stores normalized `C:/...` locator bytes.

2. `paos_library.load_library_roots()`
   - reads the canonical locator;
   - resolves Windows-drive syntax to the runtime path for validation;
   - returns the canonical locator, not the temporary WSL mount path.

3. `paos library roots ... --config C:\...`
   - maps the explicit config locator under WSL so the real primary registry is
     still addressed;
   - does not create a runner-local second registry.

No schema bump is needed because `paos-library-roots/v1` already defines
root values as installation locators and its contract example uses Windows
drive paths.

## Backward behavior

- POSIX-native paths continue to store/return resolved POSIX paths.
- Existing `/mnt/c/...` registry values remain readable; Packet B1 will
  explicitly rewrite this installation to the canonical Windows locator only
  after the patch passes.
- Missing registry remains a valid unregistered state.
- Registry writes remain atomic and filesystem-only.
- Project governance is unchanged.

## Acceptance

Before Packet B1 may close:

1. focused A3b/cross-runtime tests pass;
2. full verifier passes;
3. WSL real root registration using **Windows-drive root arguments** succeeds;
4. registry bytes contain normalized `C:/...` roots, not `/mnt/c/...`;
5. WSL `roots show` validates the same registry and returns `C:/...`;
6. Windows-native `roots show` validates the same registry and returns the
   same `C:/...` values;
7. runner default registry remains absent/unregistered;
8. no Library content, Project governance, Workstation, Runtime owner, hook,
   binding, Room or Participant changes.

If Windows and WSL do not both validate the same registry, Packet B1 remains
blocked and M1 does not start.
