# Personal Agent OS 一键验证（wrapper：实际逻辑在 scripts/verify.py）

# 找到 Python 后调用 verify.py，避免 Windows / Linux / WSL 各写一套测试入口。
# PAOS_PYTHON / PAOS_NODE 环境变量可覆盖解释器选择（与旧版一致）。

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$python = $null
if ($env:PAOS_PYTHON) {
    $python = $env:PAOS_PYTHON
    if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
        Write-Host "FAIL: PAOS_PYTHON 指定的解释器不可用：$python" -ForegroundColor Red
        exit 1
    }
} else {
    foreach ($c in @("python", "python3", "py")) {
        $f = Get-Command $c -ErrorAction SilentlyContinue
        if ($f) { $python = $c; break }
    }
}

if (-not $python) {
    Write-Host "FAIL: Python 未找到。设置 PAOS_PYTHON 环境变量。" -ForegroundColor Red
    exit 1
}

$global:LASTEXITCODE = $null
& $python (Join-Path $PSScriptRoot "verify.py")

if ($null -eq $global:LASTEXITCODE) {
    Write-Host "FAIL: scripts/verify.py 未能执行（Python 启动失败）。" -ForegroundColor Red
    exit 1
}
exit $global:LASTEXITCODE
