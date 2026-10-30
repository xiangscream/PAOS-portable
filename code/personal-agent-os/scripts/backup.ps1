# Create an installation-level PAOS backup of private-data/.
param(
    [string]$Destination = "",
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


function Resolve-PaosPython {
    if ($env:PAOS_PYTHON) { return $env:PAOS_PYTHON }
    foreach ($candidate in @("python", "python3", "py")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw "Python 3 未找到。请设置 PAOS_PYTHON 或安装 Python 3。"
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "[ERROR] 端口 $Port 正在监听。请先运行 scripts\stop.ps1 -Port $Port，再创建一致性备份。" -ForegroundColor Red
    exit 2
}

if (-not $Destination) {
    $documents = [Environment]::GetFolderPath("MyDocuments")
    if (-not $documents) { $documents = $HOME }
    $Destination = Join-Path $documents "PAOS Backups"
}
$Destination = [System.IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$DataRoot = Resolve-PaosDataRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
$archive = Join-Path $Destination "paos-backup-$timestamp.zip"
$python = Resolve-PaosPython

& $python (Join-Path $RepoRoot "scripts\paos_backup.py") backup --repo-root $RepoRoot --data-root $DataRoot --output $archive
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] 安装级备份：$archive" -ForegroundColor Green
Write-Host "范围：private-data/ 中实际存储的文件。外部引用目标、Secret Store、build/runtime 不复制进包。"
