# Access PAOS from WSL2

PAOS intentionally keeps its HTTP server on Windows loopback (`127.0.0.1`).
WSL2 NAT mode uses a separate network namespace, so WSL's own
`127.0.0.1:8766` is not the Windows loopback service.

## Normal path

On Windows, start PAOS as usual:

```powershell
.\scripts\start.ps1
```

When a Windows network adapter whose interface name contains `WSL` exists,
`start.ps1` starts a small TCP bridge:

```text
<Windows WSL adapter IPv4>:8766 -> 127.0.0.1:8766
```

The PAOS server itself still binds only `127.0.0.1`; the bridge does not change
any HTTP route or domain contract. The bridge requires an explicit IPv4 listen
address and rejects wildcard (`0.0.0.0`) binding.

From WSL, the Windows-side WSL adapter is normally the default-route gateway:

```bash
PAOS_HOST="$(ip route show default | awk '{print $3; exit}')"
curl "http://${PAOS_HOST}:8766/api/health"
```

Expected response includes:

```json
{"ok": true, "service": "attention-dashboard-v1"}
```

## Fallbacks when the bridge is unavailable

Both of these have the important property that they use the **Windows network
stack**, even though the command is launched from WSL.

### Windows curl.exe

```bash
/mnt/c/Windows/System32/curl.exe -s \
  'http://127.0.0.1:8766/api/health'
```

The same method works for JSON writes; use `--data-binary` and the normal PAOS
HTTP contract.

### Windows PowerShell

```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -NoProfile -Command \
  "Invoke-RestMethod -Uri 'http://127.0.0.1:8766/api/health' -Method Get"
```

`powershell.exe` is not guaranteed to be on the WSL `PATH`, so use the full
path when needed.

Avoid relying on `cmd.exe` while the WSL process is in a Linux/UNC working
directory; Windows `cmd.exe` may reject that current directory. Prefer
`curl.exe` or full-path PowerShell for PAOS access.

## Security boundary

Do not change `local_server.py` to listen on `0.0.0.0` merely to make WSL work.
The adapter exists specifically so PAOS can remain loopback-only on Windows
while exposing one explicit WSL virtual-adapter endpoint.
