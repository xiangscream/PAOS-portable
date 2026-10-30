# Workstation materialization safety v1

Status: S3-1 implementation contract.

## Product result

An Agent / Runtime can verify that the local Project workspace and required materials are readable before dispatch, then materialize a lightweight Workstation for the **current execution Cycle** after canonical responsibility and `switch_work` have established that Cycle.

The Workstation is a replaceable local execution view. It is not a PAOS Project object, does not become a second source of truth, and never changes responsibility by itself.

S3-1 is the filesystem/cycle-safety foundation for V1-11, V1-13, FW-02 and FW-10. The full Coordinator dispatch preflight in FW-01, Reviewer responsibility in FW-05 and Coordinator organization loop are separate S3 packages.

## Why the old ordering changes

The older workstation addendum placed materialization before `switch_work`. V1-11 is stricter: a Workstation must not overwrite an old Runtime's entry material with a new tenure.

S3 therefore separates two operations:

1. **workspace preflight** may happen before a directed Assignment / Request and is read-only;
2. **materialization** happens only after the Agent has a canonical current Work/Cycle and the caller already possesses the Cycle / Context Pack coordinates issued for that tenure.

The resulting safe sequence is:

```text
workspace preflight
-> later Coordinator dispatch creates canonical responsibility
-> Agent reads Mailbox
-> canonical session switch-work creates the new Cycle
-> materialize that exact Cycle Workstation
-> Agent reads ENTRY / GUIDE and live PAOS context
-> Agent optionally self-reports its Runtime binding (Acknowledge)
```

S3-1 does not combine these steps into a new workflow transaction.

## Agent-facing command surface

Keep the Workstation discoverable from the existing Agent CLI so it reuses the same PAOS base-URL/config resolution and structured error behavior:

```text
paos workstation preflight PROJECT AGENT --work-id WORK [--root PATH] [--material PATH ...]
paos workstation prepare PROJECT AGENT --work-id WORK \
  --execution-cycle N --context-pack-id PACK \
  [--responsibility-id REQUEST ...] [--root PATH] [--material PATH ...]
```

`preflight` and `prepare` are local execution utilities. They may read PAOS through the existing REST client and inspect/write the selected Project workspace, but they must never read or write PAOS `private-data` directly.

They do not expose Human-only actions and do not create/resolve Work, Request, Decision, Review, Continue or Restore state.

## Root and path rules

The selected workspace root is:

1. explicit `--root`, when supplied;
2. otherwise the current Project `root_path` returned by PAOS.

No author path, Project ID or WSL address is a default.

Preflight checks the selected root, Project `key_files`, and each explicit `--material` in the **current Runtime process environment**. A path string is not evidence of reachability.

At minimum:

- root exists and is a directory;
- root can be read;
- materialization can create/write below `<root>/.paos`;
- relative key files/materials resolve from the selected root;
- required files exist and are readable;
- missing/unreadable paths are reported explicitly;
- a Windows-looking path that is not reachable in the current environment fails instead of being treated as valid metadata.

`preflight` is read-only: success or failure must not create `.paos`, mutate a Project, or issue a PAOS POST.

## V1.1 entry ownership

This S3 contract still governs Cycle-bound materialization safety. V1.1 supersedes one earlier navigation behavior: `materialize_cycle` no longer publishes or refreshes `.paos/agents/<agent>/ENTRY.md`.

The single stable Agent entry is now `<Project Root>/Workstations/<agent>/ENTRY.md`, created/migrated by `paos workstation init`. The existing `.paos/workstations/<work>/<agent>/cycle-N/` directory remains Cycle-bound evidence and keeps all non-overwrite guarantees below.

## Cycle-bound layout

Materialize into a tenure-specific directory:

```text
<root>/.paos/
├─ practice/
│  └─ WORKFLOW-GUIDE.md
└─ workstations/<work>/<agent>/cycle-<N>/
   ├─ ENTRY.md
   ├─ GUIDE.md
   ├─ inputs/
   ├─ outputs/
   └─ review/
```

A later Cycle always gets a new `cycle-<N>` directory. Preparing Cycle N+1 must not change any file or directory under Cycle N.

Re-running `prepare` for an already materialized Cycle must never overwrite an edited `ENTRY.md`, `GUIDE.md`, output or review material. An exact no-op may be accepted only when the implementation can prove the generated files are unchanged; otherwise fail with a clear conflict and leave existing bytes untouched.

## Execution-tenure input

`prepare` requires caller-supplied `--execution-cycle` and `--context-pack-id`.

These values are copied from the entry material issued to the current Runtime. The Workstation command must not select, refresh or silently replace them with the newest Cycle/Pack from PAOS.

It may read current Session Detail to **validate** the supplied coordinates. If they do not match the current Session Cycle/Context Pack, preparation fails before writing files.

This preserves the S2 rule that administrative tooling does not rescue a stale Runtime by silently acquiring a newer tenure.

## Responsibility and Work validation

`prepare` is post-claim materialization. It must verify:

- Project and Agent exist;
- supplied Work exists;
- the Agent's current Work equals the supplied Work;
- the supplied Cycle/Pack match the current Session entry;
- each supplied `--responsibility-id` exists in canonical Project responsibility history and refers to the relevant Agent/Work when those bindings are present.

A direct Human-created first Work may have no Request/Assignment ID; therefore `--responsibility-id` is optional. The Workstation must not invent one.

The command performs no `switch_work` and no Request mutation. Responsibility changes remain owned by existing canonical PAOS actions.

## ENTRY.md

`ENTRY.md` is a locator for this exact Cycle, not a frozen Project dump. It contains only what is needed to enter safely:

- Project ID/name;
- stable Agent ID and Identity;
- current Work ID/title;
- current Cycle and Context Pack ID;
- supplied canonical responsibility references, if any;
- Mission / Done When;
- required material paths and reachability result;
- local `inputs/`, `outputs/` and `review/` locations;
- current Human-only boundary;
- stop conditions for stale tenure or unreachable material;
- the command to read live facts, for example `paos session context PROJECT AGENT`;
- the local GUIDE and canonical Practice Guide paths.

It must not embed the full Project JSON, full Session Detail, historical Context Pack, CAT transcript, REST schema tutorial, or Artifact body content.

## GUIDE.md and canonical Practice seed

The Project-level canonical Practice path is:

`<root>/.paos/practice/WORKFLOW-GUIDE.md`

First-use materialization may seed this file from one repository-shipped minimal template when it does not exist. Once present, the canonical file is never automatically overwritten.

Each cycle's `GUIDE.md` is a private editable copy seeded from the canonical Practice file and records its seed source. Editing a cycle GUIDE never automatically changes the canonical guide. Review/promotion of Guide improvements is handled by a later S3 package using existing Artifact lineage rather than a new database.

## Failure behavior

All validation happens before writing the cycle directory.

On failure:

- no PAOS business mutation occurs;
- no new cycle directory is left partially materialized;
- an existing cycle directory is unchanged;
- CLI structured-error output retains a stable error code and useful details, including failed paths or stale Cycle/Pack coordinates.

If filesystem creation fails after validation, clean up only files/directories created by that failed attempt. Never delete or repair pre-existing user material.

## Boundaries

S3-1 does not implement:

- Coordinator creation of Assignment / Request;
- the complete FW-01 semantic preflight (Coordinator validity, orphaned doing Work, Reviewer readiness, CAT/Adapter ownership);
- Reviewer Work/Request setup;
- Mailbox wake or adapter fencing;
- automatic `switch_work`, Ack, Continue, Runtime launch or claim refresh;
- canonical Guide review/promotion;
- Project browser UX or local URI opening;
- backup/export of Workstation bodies;
- a new Workstation/Practice PAOS persistence object.

## key_file reference vs required --material（S7 修订，2026-09）

Project `key_files` 的产品语义是**引用定位符**，与 `--material`（必需逐个材料化）不同：

- key_file 每条按引用预检，分类进 ENTRY：
  - 普通本地文件：必须存在可读；
  - 本地目录：存在可读即通过，记录 type=directory；
  - http/https URL：保留为 remote reference，明确 reason=not_checked，
    不宣称已访问、不阻断本地材料化；
  - `说明：<locator>`／任意 `<标签>：<locator>`（全角冒号）：仅当冒号后缀明确像
    Windows 盘符绝对路径 / UNC / http(s) URL / POSIX 绝对路径时拆为 label+locator；
    否则整条按原 locator 处理并真实失败——不做模糊搜索、按文件名猜测或静默忽略。
- POSIX/WSL 下显式映射 Windows 盘符绝对路径到 `/mnt/<drive>/...`；
  `wsl.localhost` UNC 仅当与本机 WSL_DISTRO_NAME 相同时映射为其后的 WSL 路径；
  不同 distro / 其他 UNC 原样返回并真实失败。
- 确实不可达的本地 key_file 仍 fail closed，并逐项进入 JSON diagnostics；
  非 JSON CLI 错误输出逐项列出 issue。
- required `--material` 维持严格语义：必须存在、可读、是普通文件；
  缺失/目录继续 fail closed。
- 本节不改变 PAOS/CAT/tenure/Store 行为，不新增 PAOS API。

## Acceptance

S3-1 is accepted only when the exact candidate HEAD proves:

1. `paos --help` exposes `workstation preflight` and `workstation prepare` without exposing new Human-only mutations;
2. preflight succeeds for a readable workspace containing required key files/materials and performs GET-only/no-write behavior;
3. missing/unreadable root, key file or explicit material fails closed with structured diagnostics and leaves no `.paos` side effect;
4. `prepare` requires explicit Cycle/Context-Pack coordinates and rejects stale/mismatched values before filesystem writes;
5. materialization creates the cycle-bound `ENTRY.md / GUIDE.md / inputs / outputs / review` layout under a path containing spaces and non-ASCII characters;
6. a new Cycle creates a distinct directory and leaves the previous Cycle byte-for-byte unchanged;
7. re-preparing an edited existing Cycle cannot overwrite its ENTRY/GUIDE/output/review material;
8. `prepare` issues no PAOS POST and does not call `switch_work` or refresh an execution claim;
9. ENTRY stays locator-sized and contains current IDs/mission/material references/live-context command without dumping full Project/Prompt/history;
10. existing S2 Agent CLI, tenure, Continue, Working Memory and authority tests remain green;
11. `python scripts/verify.py` and `git diff --check` pass;
12. a real Windows or WSL smoke proves a root containing spaces/Chinese characters, one reachable file, one deliberately unreachable path, and Cycle N -> N+1 non-overwrite behavior.
