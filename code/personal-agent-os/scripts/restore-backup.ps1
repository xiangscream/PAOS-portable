# Restore an installation-level PAOS backup into private-data/.
param(
    [Parameter(Mandatory = $true)]
    [string]$Archive,
    [string]$PreRestoreDestination = "",
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-PaosDataRoot {
    $installationFile = if ($env:PAOS_INSTALLATION_FILE) { $env:PAOS_INSTALLATION_FILE } else { Join-Path $HOME ".paos\installation.json" }
    if (-not (Test-Path -LiteralPath $installationFile)) { throw "安装描述不存在：$installationFile" }
    $descriptor = Get-Content -LiteralPath $installationFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($descriptor.schema -ne "paos-installation/v1") { throw "安装描述 schema 无效：$installationFile" }
    $raw = [string]$descriptor.data_root
    if (-not $raw) { throw "安装描述缺 data_root；请先运行 paos install configure --data-root。" }
    $driveAbsolute = $raw -match '^[A-Za-z]:[\\/]'
    $uncAbsolute = $raw.StartsWith('\\') -or $raw.StartsWith('//')
    if (-not ($driveAbsolute -or $uncAbsolute)) { throw "data_root 必须是真正绝对路径（盘符或 UNC），拒绝 drive-relative/根相对：$raw" }
    return [System.IO.Path]::GetFullPath($raw)
}

$Archive = [System.IO.Path]::GetFullPath($Archive)

function Resolve-PaosPython {
    if ($env:PAOS_PYTHON) { return $env:PAOS_PYTHON }
    foreach ($candidate in @("python", "python3", "py")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw "Python 3 未找到。请设置 PAOS_PYTHON 或安装 Python 3。"
}

if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) {
    Write-Host "[ERROR] 备份文件不存在：$Archive" -ForegroundColor Red
    exit 2
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "[ERROR] 端口 $Port 正在监听。请先运行 scripts\stop.ps1 -Port $Port，再恢复用户环境。" -ForegroundColor Red
    exit 2
}

$python = Resolve-PaosPython
$DataRoot = Resolve-PaosDataRoot
$privateRoot = $DataRoot
$currentFiles = @()
if (Test-Path -LiteralPath $privateRoot) {
    $currentFiles = @(Get-ChildItem -LiteralPath $privateRoot -Recurse -File -Force -ErrorAction SilentlyContinue | Select-Object -First 1)
}

if ($currentFiles.Count -gt 0) {
    if (-not $PreRestoreDestination) {
        $documents = [Environment]::GetFolderPath("MyDocuments")
        if (-not $documents) { $documents = $HOME }
        $PreRestoreDestination = Join-Path $documents "PAOS Backups"
    }
    $PreRestoreDestination = [System.IO.Path]::GetFullPath($PreRestoreDestination)
    New-Item -ItemType Directory -Force -Path $PreRestoreDestination | Out-Null
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
    $preRestoreArchive = Join-Path $PreRestoreDestination "paos-pre-restore-$timestamp.zip"

    Write-Host "[INFO] 先备份当前 private-data/：$preRestoreArchive"
    & $python (Join-Path $RepoRoot "scripts\paos_backup.py") backup --repo-root $RepoRoot --data-root $DataRoot --output $preRestoreArchive
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 恢复前备份失败；不会继续覆盖当前 private-data/。" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

& $python (Join-Path $RepoRoot "scripts\paos_backup.py") restore --repo-root $RepoRoot --data-root $DataRoot --archive $Archive --replace-existing
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] PAOS 用户环境已恢复。" -ForegroundColor Green
Write-Host "下一步：运行 scripts\start.ps1，然后 scripts\doctor.ps1。"
