# PAOS Authority Matrix

> Generated from `attention-dashboard-v1-static/authority_manifest.py`. Do not hand-edit the matrix rows.

The manifest describes product authority. Runtime Workflow/Store/Home-service validation remains the enforcement layer.
An HTTP route existing does **not** mean every actor may invoke it.

| Action | Human | Coordinator | Worker | HTTP | Contract | Side effect | Confirmation policy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `project.create` | YES | — | — | `POST /api/projects` | `—` | project-create | human-direct |
| `project.update` | YES | — | — | `PUT /api/projects/{project_id}` | `paos-project-manual-update/v1` | project-fields | human-direct |
| `project.root.relocate` | YES | — | — | `POST /api/projects/{project_id}/relocate-root` | `paos-project-root-relocate/v2` | project-root+key-files+artifact-paths | human-only |
| `project.restore` | YES | — | — | `POST /api/projects/{project_id}/restore-latest` | `—` | broad-restore | human-only |
| `session.open` | YES | — | — | `POST /api/projects/{project_id}/sessions` | `paos-session-open/v1` | none | human-direct |
| `session.continue` | YES | — | — | `POST /api/projects/{project_id}/sessions/{session_id}/continue` | `paos-session-continue/v1` | none | human-direct |
| `session.acknowledge` | — | YES | YES | `POST /api/projects/{project_id}/sessions/{session_id}/acknowledge` | `paos-session-ack/v1` | none | worker-self |
| `session.update` | — | YES | YES | `POST /api/projects/{project_id}/sessions/{session_id}/updates` | `paos-session-update/v1` | none | worker-self |
| `session.close` | — | YES | YES | `POST /api/projects/{project_id}/sessions/{session_id}/close` | `paos-session-close/v1` | none | worker-self |
| `session.abandon` | YES | — | — | `POST /api/projects/{project_id}/sessions/{session_id}/abandon` | `paos-session-abandon/v1` | none | human-direct |
| `session.reactivate` | YES | — | — | `POST /api/projects/{project_id}/sessions/{session_id}/reactivate` | `paos-session-reactivate/v1` | none | human-direct |
| `session.artifact.add` | — | YES | YES | `POST /api/projects/{project_id}/sessions/{session_id}/artifacts` | `paos-session-artifact-add/v1` | evidence-only | worker-self |
| `coordinator.grant` | YES | — | — | `POST /api/projects/{project_id}/sessions/{session_id}/grant-coordinator` | `paos-coordinator-grant/v1` | none | human-only |
| `coordinator.revoke` | YES | — | — | `POST /api/projects/{project_id}/sessions/{session_id}/revoke-coordinator` | `paos-coordinator-revoke/v1` | none | human-only |
| `coordinator.replace` | YES | — | — | `POST /api/projects/{project_id}/coordinator/replace` | `paos-coordinator-replace/v1` | none | human-only |
| `decision.review` | YES | — | — | `POST /api/projects/{project_id}/decisions/{decision_id}/review` | `paos-decision-review/v1` | decision-status | human-only |
| `coordinator.project.tagline.update` | — | YES | — | `POST /api/projects/{project_id}/coordinator/tagline` | `paos-coordinator-tagline-update/v1` | generated-tagline | coordinator-direct-receipt |
| `coordinator.request.create` | — | YES | — | `POST /api/projects/{project_id}/coordinator/requests` | `paos-coordinator-request-create/v1` | none | coordinator-direct-receipt |
| `coordinator.assignment.create` | — | YES | — | `POST /api/projects/{project_id}/coordinator/assignments` | `paos-coordinator-assignment/v1` | none | coordinator-direct-receipt |
| `coordinator.session.abandon` | — | YES | — | `POST /api/projects/{project_id}/coordinator/sessions/{session_id}/abandon` | `paos-coordinator-session-abandon/v1` | none | coordinator-direct-receipt |
| `agent.project.requirement_update` | — | YES | YES | `POST /api/agent/project-requirement-update` | `paos-agent-requirement-update/v1` | project-human-fields | explicit-human-authorization |
| `agent.project.list_update` | — | YES | YES | `POST /api/agent/project-list-update` | `paos-agent-project-list-update/v1` | project-lists | explicit-human-authorization |
| `agent.project.progress_update` | — | YES | YES | `POST /api/agent/project-progress-update` | `paos-agent-project-progress-update/v1` | generated-summary | explicit-human-authorization |
| `tips.correct` | YES | YES | YES | `POST /api/tips/corrections` | `paos-tip-correction/v1` | tips-inbox-file | explicit-source-action |
| `attention.todo.update` | — | YES | YES | `PUT /api/projects/{project_id}/agents/{session_id}/attention/todo` | `—` | home-todo | home-owner-self |
| `attention.notice.handle` | — | YES | YES | `POST /api/projects/{project_id}/agents/{session_id}/attention/notices/{notice_id}/handle` | `—` | notice-handling | home-owner-self |
| `attention.notice.organize` | — | YES | YES | `POST /api/projects/{project_id}/agents/{session_id}/attention/notices/{notice_id}/organize` | `—` | notice-organization | home-owner-self |
| `attention.source.register` | YES | YES | YES | `POST /api/projects/{project_id}/agents/{session_id}/attention/source` | `—` | notice-source | explicit-source-action |
| `attention.mail.send` | YES | YES | YES | `POST /api/projects/{project_id}/attention/mail` | `—` | mail+notice | explicit-source-action |
| `attention.mail.notify` | YES | YES | YES | `POST /api/projects/{project_id}/attention/mail/{message_id}/notify` | `—` | activation-intent | explicit-source-action |
| `attention.cat.send` | YES | YES | YES | `POST /api/projects/{project_id}/attention/cat` | `—` | cat+notice | explicit-source-action |
| `attention.cat.notify` | YES | YES | YES | `POST /api/projects/{project_id}/attention/cat/notify` | `—` | activation-intent | explicit-source-action |
| `rooter.todo.update` | YES | YES | — | `PUT /api/rooter/attention/todo` | `—` | home-todo | installation-home-self |
| `rooter.notice.handle` | YES | YES | — | `POST /api/rooter/attention/notices/{notice_id}/handle` | `—` | notice-handling | installation-home-self |
| `rooter.notice.organize` | YES | YES | — | `POST /api/rooter/attention/notices/{notice_id}/organize` | `—` | notice-organization | installation-home-self |
| `rooter.source.register` | YES | YES | — | `POST /api/rooter/attention/source` | `—` | notice-source | installation-home-self |

## Critical boundaries

- Decision accept/reject is Human-only. Coordinator may propose Decisions but cannot review them.
- Restore is Human-only.
- Opening a PAOS Session is Human-controlled and does not start an external Runtime.
- Continuing a PAOS Agent into a new native Runtime tenure is Human-controlled and keeps the same Agent ID.
- Agent `Close` is handoff testimony and never changes a responsibility status.
- Human/Coordinator `Abandon` is governance termination and never fabricates `close_result`.
- Coordinator Project writes use the explicit Coordinator endpoints and produce durable receipts.
- CAT transport remains a separate product boundary; this manifest classifies only PAOS-side CAT source send/notify projection, never CAT server governance or ACK authority.

## Generation / verification

```bash
python scripts/render_authority_matrix.py --check
python scripts/render_authority_matrix.py --write
```
