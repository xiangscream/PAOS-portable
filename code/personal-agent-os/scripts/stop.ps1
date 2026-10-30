param([int]$Port = 8766)
$ErrorActionPreference = 'Stop'
if ($Port -ne 8766) { throw 'The installed PAOS background service uses port 8766' }
& (Join-Path $PSScriptRoot 'windows-background.ps1') -Mode Stop
