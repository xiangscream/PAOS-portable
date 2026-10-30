# Personal Agent OS clean-install preparation. No administrator rights required.
param()

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

Set-Location $RepoRoot

function Resolve-PaosPython {
    if ($env:PAOS_PYTHON) { return $env:PAOS_PYTHON }
    foreach ($candidate in @("python", "python3", "py")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw "Python 3 未找到。请安装 Python，或设置 PAOS_PYTHON 指向 Python 3 解释器。"
}

$python = Resolve-PaosPython
Write-Host "=== PAOS 安装准备 ===" -ForegroundColor Cyan
Write-Host "仓库：$RepoRoot"
Write-Host "Python：$python"

$DataRoot = Resolve-PaosDataRoot
$requiredDirs = @(
    "project-registry\projects",
    "inbox\tips",
    "environment",
    "logs",
    "plugin-registry"
)
foreach ($relative in $requiredDirs) {
    $path = Join-Path $DataRoot $relative
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}
Write-Host "[OK] PAOS 用户数据目录已准备。" -ForegroundColor Green

& $python (Join-Path $RepoRoot "scripts\ensure_build_data.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] 派生数据准备失败。未覆盖现有 build/；请按上方提示处理。" -ForegroundColor Red
    exit $LASTEXITCODE
}

# ASCII cmd locates its sibling script; the UTF-8-BOM script carries Unicode.
function Install-CatRelayEntry {
    param([string]$Bin, [string]$SourceRoot, [string]$PythonCommand)

    $relayLaunch = Join-Path $Bin "paos-cat-relay-launch.ps1"
    $relayCmd = Join-Path $Bin "paos-cat-relay.cmd"
    $rootLiteral = $SourceRoot.Replace("'", "''")
    $pythonLiteral = $PythonCommand.Replace("'", "''")
    $launch = @"
param([int]`$ListenPort = 8870, [int]`$ServicePort = 8870, [string]`$WslUser = 'remo')
`$ErrorActionPreference = 'Stop'
& '$pythonLiteral' -X utf8 -B '$rootLiteral\scripts\paos_cat_relay_windows.py' --listen-port `$ListenPort --service-port `$ServicePort --wsl-user `$WslUser @args
exit `$LASTEXITCODE
"@
    $cmd = '@echo off' + "`r`n" + 'powershell.exe -NoProfile -File "%~dp0paos-cat-relay-launch.ps1" %*' + "`r`n"
    if (-not (Test-Path -LiteralPath $relayLaunch)) {
        [System.IO.File]::WriteAllText($relayLaunch, $launch, [System.Text.UTF8Encoding]::new($true))
    }
    if (-not (Test-Path -LiteralPath $relayCmd)) {
        [System.IO.File]::WriteAllText($relayCmd, $cmd, [System.Text.Encoding]::ASCII)
    }
}

$catBin = Join-Path $env:USERPROFILE ".paos\bin"
if (Test-Path -LiteralPath $catBin) {
    Install-CatRelayEntry -Bin $catBin -SourceRoot $RepoRoot -PythonCommand $python
    Write-Host "[OK] CAT relay entry prepared (manual start)." -ForegroundColor Green
}

Write-Host "[OK] 安装准备完成。" -ForegroundColor Green
Write-Host "下一步："
