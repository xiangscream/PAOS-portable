# Upgrade Protocol

Use this reference when improving the skill from real user corrections.

## Goal

Upgrade by learning **transformations and decision rules**, not by accumulating banned words.

## Preferred correction record

For each meaningful correction, capture:

```markdown
### [Short category]

Context: [artifact type / audience]

Bad:
> [original text]

Good:
> [user-approved text]

Principle:
[semantic reason the good version is better]

Scope:
[when this rule applies and when it does not]
```

## Upgrade hierarchy

1. System/safety requirements
2. Explicit current user instruction
3. Project/organization local policy
4. User-approved correction examples
5. Universal Clean Writing rules
6. Generic style preference

## Add a universal rule only when

- the same failure recurs across different documents or domains;
- the rule can be stated semantically, not as a single-word ban;
- the rule has a clear exception boundary;
- the rule improves reader comprehension without deleting necessary truth.

## Keep a correction local when

- it reflects one organization's terminology;
- it depends on a specific audience or manager;
- it is domain-specific;
- it is a formatting preference rather than a general clarity principle.

## Do not overfit

Do not infer rules such as:

- "never use therefore";
- "never mention competitors";
- "never show evidence";
- "always use tables";
- "always be concise."

Instead capture the semantic condition:

- remove reasoning traces from publication-state text;
- show competitor evidence only when comparison/evidence is reader-relevant;
- use tables for genuinely parallel information;
- preserve detail when the reader must implement or verify it.

## Suggested local override files

Keep local calibration outside the universal skill bundle. A useful structure is:

```text
<local writing config>/
  clean-writing.local.md
  clean-writing.examples.local.md
```

`clean-writing.local.md` should contain stable organization/user rules.

`clean-writing.examples.local.md` should contain approved bad → good pairs from real edits.

When these files are available and authorized for the current task, load only the relevant parts and apply them after the universal rules.

## Periodic consolidation

After enough examples accumulate:

1. Group corrections by semantic failure.
2. Remove duplicate examples.
3. Promote recurring cross-domain principles to the universal rules.
4. Keep specific terminology and manager preferences local.
5. Retain a few strong examples per category rather than a huge corpus.
6. Re-test against older examples to prevent regressions.
