
## UXC-01 stacked contract delta

Branch target: `ux/tagline-contract` (stacked on `ux/foundation`).

Scope:
- add `generated.tagline` as a first-class Project read/default field;
- add coordinator-only `coordinator.project.tagline.update` authority;
- add one narrow `POST /api/projects/{project_id}/coordinator/tagline` action;
- one-line normalize and 240-character bound;
- receipt + Ledger event + idempotent replay;
- keep worker `project-progress-update` unable to write tagline;
- do not change Project Hero yet (UX-2 owns presentation).

Gate after UXC-01:
- Architecture: 9 boundaries PASS
- Python: 400 PASS
- Node UTC: 116 PASS
- Node Asia/Shanghai: 116 PASS
- Derived data: PASS
- compileall: PASS
- JS syntax: PASS
- Overall: 7/7 PASS
