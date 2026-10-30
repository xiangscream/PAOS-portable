# Start Windows-owned tasks, never services under this caller.
param([int]$Port = 8766, [string]$Entry = 'projects.html', [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
if ($Port -ne 8766) { throw 'The installed PAOS background service uses port 8766' }
& (Join-Path $PSScriptRoot 'windows-background.ps1') -Mode Start
for ($attempt = 0; $attempt -lt 10; $attempt++) {
    if (Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort $Port -ErrorAction SilentlyContinue) { break }
    Start-Sleep -Seconds 1
}
$health = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/api/health" -TimeoutSec 5
$commit = git -C (Split-Path $PSScriptRoot -Parent) rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or -not $health.ok -or $health.service -ne 'attention-dashboard-v1' -or
    $health.build.source_commit -ne $commit) { throw 'Running PAOS does not match installed Source' }
Write-Host '[OK] PAOS is running under Windows Task Scheduler.'
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:${Port}/attention-dashboard-v1-static/${Entry}" }
