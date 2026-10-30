# Personal Agent OS 一键诊断
# 五层定位：服务 → 端口 → 数据 → 来源 → 浏览器
# 2026-07-31

param([int]$Port = 8766)

$ErrorActionPreference = "Continue"
$identityMismatch = $false
# Navigate to repo root (supports any launch directory)
Set-Location (Split-Path -Parent $PSScriptRoot)

# Use the same Python resolution rule as start.ps1 so Doctor diagnoses the
# checkout with the interpreter PAOS itself would use.
$python = $null
if ($env:PAOS_PYTHON) {
    $python = $env:PAOS_PYTHON
} else {
    foreach ($candidate in @("python", "python3", "py")) {
        $found = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($found) { $python = $candidate; break }
    }
}
if (-not $python) {
    Write-Host "[FAIL] Python 未找到；无法计算当前 checkout build identity。" -ForegroundColor Red
    exit 1
}
Write-Host "=== Personal Agent OS Doctor ===" -ForegroundColor Cyan
Write-Host ""

# L1: 服务是否在监听
Write-Host "[L1] 服务监听状态..."
$listener = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
if ($listener) {
    Write-Host "  OK: 端口 ${Port} 正在监听" -ForegroundColor Green
} else {
    Write-Host "  FAIL: 端口 ${Port} 未监听。请先运行 start.ps1" -ForegroundColor Red
    exit 1
}

# L2: /api/health
Write-Host "[L2] 健康接口..."
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/api/health" -Method Get -TimeoutSec 3
    if ($health.ok) {
        Write-Host "  OK: health={ok: true}, service=$($health.service)" -ForegroundColor Green
        if ($health.build -and $health.build.schema -eq "paos-build-identity/v1") {
            $commit = if ($health.build.source_commit) { $health.build.source_commit } else { "unavailable" }
            $tag = if ($health.build.release_tag) { $health.build.release_tag } else { "unreleased" }
            Write-Host "  BUILD: commit=$commit tag=$tag"
        } else {
            Write-Host "  FAIL: 运行中的 PAOS 未报告 build identity；它可能是旧进程/旧版本。" -ForegroundColor Red
            $identityMismatch = $true
        }
    } else {
        Write-Host "  FAIL: health 返回异常" -ForegroundColor Red
    }
} catch {
    Write-Host "  FAIL: 无法连接 /api/health — $_" -ForegroundColor Red
    exit 2
}

# L2.5: 当前 checkout 与运行实例是否一致（E13）
Write-Host "[L2.5] Build identity..."
try {
    $identityJson = & $python "attention-dashboard-v1-static/release_identity.py" --repo-root "." --json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $identityJson) { throw "release_identity.py failed" }
    $localIdentity = $identityJson | ConvertFrom-Json
    if (-not $health.build) {
        Write-Host "  FAIL: 无法与旧版运行实例比较。请重启 PAOS 后再诊断。" -ForegroundColor Red
        $identityMismatch = $true
    } else {
        $runtimeMatches = $health.build.runtime_fingerprint -eq $localIdentity.runtime_fingerprint
        $staticMatches = $health.build.static_fingerprint -eq $localIdentity.static_fingerprint
        $commitMatches = (-not $health.build.source_commit) -or (-not $localIdentity.source_commit) -or ($health.build.source_commit -eq $localIdentity.source_commit)
        if ($runtimeMatches -and $staticMatches -and $commitMatches) {
            Write-Host "  OK: 运行实例与当前 checkout 的 runtime/static identity 一致" -ForegroundColor Green
        } else {
            Write-Host "  FAIL: 运行实例与当前 checkout 不一致。" -ForegroundColor Red
            if (-not $runtimeMatches) { Write-Host "    runtime fingerprint mismatch" }
            if (-not $staticMatches) { Write-Host "    static fingerprint mismatch" }
            if (-not $commitMatches) { Write-Host "    source commit mismatch" }
            Write-Host "  ACTION: 运行 .\scripts\restart.ps1，再重新执行 doctor.ps1" -ForegroundColor Yellow
            $identityMismatch = $true
        }
    }
} catch {
    Write-Host "  FAIL: 无法计算当前 checkout build identity — $_" -ForegroundColor Red
    $identityMismatch = $true
}

# L3: 页面入口
Write-Host "[L3] 页面 HTTP 状态..."
try {
    $page = Invoke-WebRequest -Uri "http://127.0.0.1:${Port}/attention-dashboard-v1-static/" -Method Get -TimeoutSec 5 -UseBasicParsing
    Write-Host "  OK: HTTP $($page.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  FAIL: 页面无法访问 — $_" -ForegroundColor Red
}

# L4: 数据
Write-Host "[L4] Dashboard 数据..."
try {
    $data = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/attention-memory-pipeline-v0/build/dashboard-data.json" -Method Get -TimeoutSec 3
    if ($data) {
        Write-Host "  OK: 数据可读" -ForegroundColor Green
    } else {
        Write-Host "  WARN: 数据为空" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARN: 数据不可用（可能需要先运行 Pipeline）" -ForegroundColor Yellow
}

# L5: 来源
Write-Host "[L5] 合成数据目录..."
$syntheticDir = "attention-memory-pipeline-v0/synthetic-vault"
if (Test-Path $syntheticDir) {
    $count = (Get-ChildItem -Path $syntheticDir -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' }).Count
    Write-Host "  OK: synthetic-vault 存在（$count 个文件）" -ForegroundColor Green
} else {
    Write-Host "  WARN: synthetic-vault 未找到" -ForegroundColor Yellow
}

Write-Host ""
if ($identityMismatch) {
    Write-Host "=== 诊断完成：发现版本/资源不一致 ===" -ForegroundColor Red
    exit 4
}
Write-Host "=== 诊断完成 ===" -ForegroundColor Cyan
