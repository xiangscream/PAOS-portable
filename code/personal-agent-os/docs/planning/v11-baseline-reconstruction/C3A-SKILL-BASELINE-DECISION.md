# PAOS V1.1 — C3A Skill Baseline Decision

Decision owner: zrx  
Evidence baseline: C3A handoff commit `1a3c421`

## 1. C3A verdict

C3A is accepted.

The current canonical shared method baseline remains:

```text
Workflow Kernel
  wf-agent-work-cycle
  wf-coordinator-governance-cycle

Skill Library
  skill-engineering-change
  skill-independent-review
```

No Runtime/vendor/Project-local package is promoted merely because it exists.

## 2. clean-writing source decision

The exact original local source is accepted as:

```text
C:\Users\remo\.codex\skills\clean-writing\
```

with the package evidence recorded by C3A:

- `SKILL.md`
- `references/`
- `scripts/clean_lint.py`
- `agents/openai.yaml`
- `assets/icon.svg`

The Windows Codex root is the source-of-origin for C3B. Desktop mirror, zip, temp extraction and short test variants are not independent sources.

s029's initial SOURCE-MISSING result is preserved as an independent-search outcome, but it is superseded for source existence by the direct Windows-path evidence. The lesson is procedural: Windows and WSL user roots are not interchangeable search scopes.

## 3. Why clean-writing gets a C3B import packet

clean-writing is materially different from the other discovered packages:

- it was deliberately created as a reusable writing-quality Skill;
- its source package is exact and inspectable;
- it has a stable historical identity used by the user;
- it is not a vendor/system/runtime transport mechanism;
- it has no Project-governance ownership;
- it has substantial supporting references and a lint helper;
- it addresses a recurring quality problem across Projects.

However, exact source existence is not enough for direct activation.

It must be normalized and independently reviewed for:

- Codex-specific leakage;
- overly rigid style rules;
- overlap with Workflow Kernel;
- process-history / audit-language cleanup behavior;
- whether supporting references/scripts are actually reusable;
- whether the Skill still matches the user's current “clean, readable, high-quality” intent.

## 4. Stable identity

The canonical PAOS Skill ID remains:

```text
clean-writing
```

Do **not** rename it to `skill-clean-writing`.

Reason:

- `clean-writing` is the user's established reusable Skill identity;
- prior plans and usage references already use that name;
- the PAOS schema does not require a `skill-` prefix;
- renaming would create unnecessary alias/migration debt.

The package directory must therefore be:

```text
PAOS-Libraries/skill/clean-writing/
```

## 5. Normalization boundary

C3B may preserve execution content, but must not copy the Codex package wholesale.

### Candidate reusable content

Likely reusable:

- `SKILL.md` semantic method;
- `references/examples.md`;
- `references/language-modes.md`;
- `references/semantic-review.md`;
- `references/upgrade-protocol.md`;
- `scripts/clean_lint.py` if it is runtime-independent and reviewed.

### Runtime/UI-specific content

Do not import by default:

- `agents/openai.yaml`;
- `assets/icon.svg`;
- Codex-only tool declarations or invocation metadata;
- local absolute paths;
- Runtime-specific install/load instructions.

If a supporting file is retained, it must be because the Skill method needs it, not because it existed in the original package.

## 6. Governance boundary

clean-writing is execution technique only.

It must not own:

- Work status;
- TODO;
- review/acceptance authority;
- Project lifecycle;
- Coordinator authority;
- mandatory use on every artifact.

Expected usage boundary:

> Use when producing or revising reader-facing content where clarity, readability, semantic cleanliness and professional quality matter.

It should not automatically rewrite:

- raw evidence;
- logs;
- machine-generated contracts;
- code;
- exact quotations;
- preservation-required records.

## 7. Other discovered Skill packages

C3A found other potentially useful user packages, especially product/research/writing-oriented Codex user Skills.

They are **not** authorized for C3B.

Reason:

- content-level maturity/reuse evidence was not established one by one;
- many are Runtime-formatted;
- several overlap;
- mass-import would recreate the catalog-growth problem the two-layer design was meant to avoid.

They remain candidates for later promotion only when real work creates a need.

## 8. Usage-event / Catalog projection

The C3A usage event for `skill-independent-review` is valid:

```text
su-d8d9685039594198a9e5151158a2e24b
score = 0.5
```

C3B does not need a separate repair task for the stale generated Catalog.

If C3B reaches activation and rebuilds the Skill Catalog, the rebuilt projection should naturally include the existing usage event. That result should be verified as part of C3B acceptance.

Do not rewrite or duplicate the event.

## 9. Next gate

Authorize one bounded packet only:

```text
C3B
clean-writing normalize → independent review → activate if PASS → rebuild Skill Catalog
```

After C3B:

```text
STOP
```

Then Stage 1 proceeds to Project/Vault reconstruction unless C3B exposes a new blocking baseline problem.
