# CLI Installation Locator V1

The PAOS CLI keeps machine-local installation paths separate from its connection settings. The installation descriptor is `~/.paos/installation.json` and uses this schema:

```json
{
  "schema": "paos-installation/v1",
  "source_root": "C:/path/to/personal-agent-os",
  "library_roots_config": "C:/Users/<WindowsUser>/.paos/library-roots.json"
}
```

Both values are absolute path locators. On Windows, use native absolute paths; when Windows and WSL share one descriptor, store Windows-drive paths such as `C:/...`. WSL maps those locators to `/mnt/<drive>/...` at read time without rewriting the descriptor. The descriptor locates Source and the Library registry file; it does not configure the PAOS server URL, create the Library registry, or change PAOS Project data. Connection settings remain in `~/.paos/config.json` or `PAOS_BASE_URL`.

The descriptor path resolves in this order: global `--installation-file`, `PAOS_INSTALLATION_FILE`, then `~/.paos/installation.json`. The CLI flag must appear before the command.

## Configure from Windows PowerShell

Run from the PAOS Source repository root. This writes the descriptor under the current Windows user's `.paos` directory and points it at this checkout and the default user-level Library registry location:

```powershell
$paosHome = Join-Path $HOME ".paos"
$installationFile = Join-Path $paosHome "installation.json"
$libraryRegistry = Join-Path $paosHome "library-roots.json"
$sourceRoot = (Resolve-Path ".").Path

python -X utf8 scripts\paos.py --installation-file $installationFile install configure `
  --source-root $sourceRoot `
  --library-roots-config $libraryRegistry
python -X utf8 scripts\paos.py --installation-file $installationFile install show
python -X utf8 scripts\paos.py --base-url http://127.0.0.1:8766 orient 3002 3002-s031
```

`install configure` writes only the installation descriptor. Register or repair Library roots separately with the Library CLI.

## Read the same descriptor from WSL

Run from a WSL checkout or the mounted Source directory. Set the descriptor path to the same Windows file written above. For the normal Windows loopback bridge, set `PAOS_BASE_URL` to the Windows WSL-adapter address; [`WSL-ACCESS.md`](../WSL-ACCESS.md) describes the bridge and its address.

```bash
export PAOS_INSTALLATION_FILE='C:/Users/<WindowsUser>/.paos/installation.json'
PAOS_HOST="$(ip route show default | awk '{print $3; exit}')"
export PAOS_BASE_URL="http://${PAOS_HOST}:8766"

python3 scripts/paos.py --installation-file "$PAOS_INSTALLATION_FILE" install show
python3 scripts/paos.py --installation-file "$PAOS_INSTALLATION_FILE" orient 3002 3002-s031
```

Replace `<WindowsUser>` once with the Windows profile directory that owns the descriptor. Keep `source_root` and `library_roots_config` as Windows-drive locators in the shared file; do not rewrite them to WSL-only paths. If the bridge is unavailable, use the Windows-network fallback documented in `WSL-ACCESS.md`.

## TODO v2 is the normal recovery contract

`paos-todo/v2` is the trusted local recovery list. It must match the requested Project and Agent and contain one valid `## 当前` and `## 待办` section. If TODO is missing, unreadable, malformed, or belongs to another Agent, `orient` still shows the live PAOS Work and ENTRY, marks TODO untrusted, and reports the repair issue. It never derives the next action from TODO history.

Use the approved one-time V1.1→V1.2 converter before treating an old Workstation TODO as authoritative. The converter preserves old text as history and writes the trusted current section from confirmed state; the CLI does not infer current responsibility from historical sections.

### Apply and roll back the converter output

The converter output is an **incremental file set**, not a complete Project Vault or Workstation. First freeze and copy the complete target directory. Review the converter report, then overlay each output file onto that copy by its relative path; do not replace the full Vault/Workstation with the `--out` directory. If an output path would overwrite pre-existing data, stop and resolve the collision before applying it.

To roll back, restore each converted `TODO.md` byte-for-byte from its sibling `TODO.pre-v12.md`. Compare against the frozen copy and remove only backup/generated files that this conversion added and that were absent from the copy. Keep every pre-existing file; do not use a blanket delete or restore by re-rendering the TODO.

## Continue work and communicate

Normal Session and Coordinator writes do not require a Runtime owner token, instance ID, `session enter`, or Cycle/Context Pack claim. They still carry the Project/Agent or Coordinator business identity, operation ID, and expected revision, and PAOS validates the action against current responsibility and domain rules. A native Runtime ID or session ID supplied on `session ack` is descriptive metadata.

Write a normal progress update from Windows PowerShell:

```powershell
python -X utf8 scripts\paos.py session report 3002 3002-s031 `
  --summary "当前进度摘要" `
  --operation-id "op-s031-progress-001"
```

Close the Agent Session and hand off one durable, targeted Mail in the same operation:

```powershell
python -X utf8 scripts\paos.py session submit 3002 3002-s031 `
  --result partial --summary "执行交接摘要" `
  --operation-id "op-s031-handoff-001" `
  --handoff-to 3002-s010 `
  --handoff-subject "请接续当前 Work" `
  --handoff-body "结果已持久化；请从当前 Work 和 TODO 继续。"
```

The business result is persisted first; the durable Mail uses the operation ID by default, then the existing activation path is requested. Reuse the same operation ID and content when recovering a delivery. A persisted result remains visible if Mail persistence or activation fails.

The WSL command needs the same PAOS base URL and installation descriptor described above; it uses the same no-credential Session contract:

```bash
python3 scripts/paos.py session report 3002 3002-s031 \
  --summary "当前进度摘要" \
  --operation-id "op-s031-progress-001"
```

Read and mark durable Mail only after it has been handled or incorporated. A reply marks its source Mail as replied only after the reply itself is persisted:

```powershell
python -X utf8 scripts\paos.py mail list 3002 3002-s031
python -X utf8 scripts\paos.py mail read 3002 3002-s031 '<received_message_id>'
python -X utf8 scripts\paos.py mail handle 3002 3002-s031 '<received_message_id>' --state incorporated --reason "Added to current plan"
python -X utf8 scripts\paos.py mail reply 3002 3002-s031 '<received_message_id>' --body "已完成核对。"
```

Use `status` to compare the running CLI and installation descriptor, current PAOS Work, TODO trust, durable Mail delivery/handling, and the last recorded Wake facts:

```powershell
python -X utf8 scripts\paos.py --json status 3002 3002-s031 --message-id "op-s031-handoff-001"
```

`status` is read-only: it does not probe Wake or infer that an accepted activation became a visible native turn. It reports the native turn as `not_observed` unless separate evidence establishes it.

### Verify a configured CAT route

Use the existing read and activation surfaces as one check path:

```powershell
python -X utf8 scripts\paos.py orient 3002 3002-s031
python -X utf8 scripts\paos.py workstation show 3002 3002-s031
python -X utf8 scripts\paos.py wake status 3002 3002-s031
$exchange = "<room-id>:<exchange-id>"
python -X utf8 scripts\paos.py agent notify 3002 --cat-exchange $exchange --agent 3002-s031
```

Match the fixed ENTRY/Project path with the PAOS Wake binding's Project, Agent, Runtime, native session and binding fingerprint. Match the CAT Room's Project binding and Participant→Agent mapping; the Participant's Runtime/native session and `ownership_generation` must agree with the same binding and the current Runtime's existing scope file. Do not refresh the scope or follow a newer generation during readback. `agent notify` validates the Room/Project and Exchange target and reports whether that exact Exchange is pending or already acknowledged. It requests Wake when the Exchange is pending, so run it only as part of an authorized activation check. An `already_consumed` result confirms ACK; `woken` alone does not confirm consumption.

`report` aliases `session update`; `submit` aliases `session close` and records execution handoff by closing the Agent Session/Cycle only. It does not submit the Work for review or change the Work's Human review or completion state; Work review/acceptance is a separate Coordinator/Human action. `mail send` and `mail reply` create durable Workstation Mail without mutating the Agent Session. Normal Session/Coordinator writes do not carry Runtime owner credentials or execution-cycle claims.
