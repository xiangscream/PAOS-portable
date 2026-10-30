$ErrorActionPreference = 'Continue'
# T-MA-01 临时 Codex Stop-hook（一次续步；block = stdout JSON + exit 0）
$runDir = Split-Path -Parent $PSScriptRoot
$stopFile = Join-Path $runDir 'STOP'
$runFile = Join-Path $runDir 'run.json'
$markerFile = Join-Path $runDir 'marker.json'
$eventsFile = Join-Path $runDir 'events.jsonl'
$seenFile = Join-Path $runDir 'hook_seen'

function Log-Cont-Ok {
    param([string]$Message)
    try {
        Add-Content -LiteralPath $eventsFile -Value $Message -Encoding utf8 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# 非关键审计：最佳努力写，不 gate 决策
function Log-Cont {
    param([string]$Message)
    $null = Log-Cont-Ok -Message $Message
}

# 硬停：STOP
if (Test-Path -LiteralPath $stopFile) { exit 0 }

# 硬停：run.json 非法/过期
if (-not (Test-Path -LiteralPath $runFile)) { exit 0 }
try { $run = Get-Content -LiteralPath $runFile -Raw | ConvertFrom-Json -ErrorAction Stop } catch { exit 0 }
try { if ([DateTime]::UtcNow -gt [DateTime]::Parse($run.expires_at)) { exit 0 } } catch { exit 0 }

# 硬停：max_steps（只统计已发生的 continue）
$consumed = 0
if (Test-Path -LiteralPath $eventsFile) {
    foreach ($line in Get-Content -LiteralPath $eventsFile) {
        $t = $line.TrimStart([char]0xFEFF).Trim()
        if ($t) {
            try { $o = $t | ConvertFrom-Json -ErrorAction Stop; if ($o.event -eq 'continue') { $consumed += 1 } } catch {}
        }
    }
}
if ($consumed -ge [int]$run.max_steps) { exit 0 }

# hook_seen 探针（第一次看到本 Run 时写）
if (-not (Test-Path -LiteralPath $seenFile)) {
    New-Item -ItemType File -Path $seenFile -Force | Out-Null
    Log-Cont -Message ('{"ts":"' + [DateTime]::UtcNow.ToString('o') + '","event":"hook_seen","run_id":"' + $run.run_id + '"}')
}

# 无 marker = 不续步
if (-not (Test-Path -LiteralPath $markerFile)) { exit 0 }

# 原子抢占 marker（rename 成功才算抢到；重叠 hook 只有一个能成功）
$claimed = $markerFile + '.claimed.' + [DateTime]::UtcNow.Ticks
try { Move-Item -LiteralPath $markerFile -Destination $claimed -ErrorAction Stop } catch { exit 0 }

# 严格解析 + 身份校验；失败时保留错误信号、不续步
try { $marker = Get-Content -LiteralPath $claimed -Raw | ConvertFrom-Json -ErrorAction Stop } catch {
    Log-Cont -Message ('{"ts":"' + [DateTime]::UtcNow.ToString('o') + '","event":"marker_invalid"}')
    Remove-Item -LiteralPath $claimed -Force -ErrorAction SilentlyContinue
    exit 0
}
$identityOk = ($marker.run_id -eq $run.run_id) -and ($marker.session_id -eq $run.session_id) -and ($marker.request_id -eq $run.request_id)
if (-not $identityOk) {
    Log-Cont -Message ('{"ts":"' + [DateTime]::UtcNow.ToString('o') + '","event":"marker_identity_mismatch"}')
    Remove-Item -LiteralPath $claimed -Force -ErrorAction SilentlyContinue
    exit 0
}

# step_no 严格校验：缺失 → 自动计算；存在 → 必须可解析为正整数
$step = $null
if ($null -ne $marker.step_no) {
    $okStep = $false
    try {
        $v = [int]$marker.step_no
        if ($v -ge 1) { $step = $v; $okStep = $true }
    } catch {}
    if (-not $okStep) {
        Log-Cont -Message ('{"ts":"' + [DateTime]::UtcNow.ToString('o') + '","event":"marker_invalid_step"}')
        Remove-Item -LiteralPath $claimed -Force -ErrorAction SilentlyContinue
        exit 0
    }
} else {
    $step = $consumed + 1
}

# 有界硬停的持久化 gate：continue 计数必须先成功落盘，才能 block
$continueMsg = '{"ts":"' + [DateTime]::UtcNow.ToString('o') + '","event":"continue","step":' + $step + '}'
if (-not (Log-Cont-Ok -Message $continueMsg)) {
    # 落盘失败：不续步；把 claimed marker 放回原位（未解决，保留状态）
    try { Move-Item -LiteralPath $claimed -Destination $markerFile -Force -ErrorAction Stop } catch {}
    exit 0
}

# 计数已持久化，才允许消费 claimed 并续一步
Remove-Item -LiteralPath $claimed -Force -ErrorAction SilentlyContinue

'{"decision":"block","reason":"continue-one-step"}'
exit 0
