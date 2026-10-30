param([int]$Port = 8766, [string]$Entry = 'projects.html', [switch]$NoBrowser, [switch]$NoPause)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'stop.ps1') -Port $Port
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    if (-not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 250
}
& (Join-Path $PSScriptRoot 'start.ps1') -Port $Port -Entry $Entry -NoBrowser:$NoBrowser
