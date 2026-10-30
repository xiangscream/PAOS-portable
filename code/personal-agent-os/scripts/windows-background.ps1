# Task Scheduler owns the long-running action, never the calling Harness.
param(
    [ValidateSet('Install', 'Switch', 'Start', 'Stop', 'Status')]
    [string]$Mode = 'Status',
    [string]$InstallationFile = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.paos\installation.json'),
    [string]$Python = 'python',
    [int]$CorePid,
    [int]$BridgePid
)
$ErrorActionPreference = 'Stop'
$installation = Get-Content -LiteralPath $InstallationFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($installation.schema -ne 'paos-installation/v1') { throw 'Invalid installation descriptor' }
$source = [string]$installation.source_root
$names = @('PAOS-Core', 'PAOS-WSL-Bridge')
$description = 'PAOS independent Windows background service'

function Read-OwnedTask([string]$Name) {
    $task = Get-ScheduledTask -TaskPath '\' -TaskName $Name -ErrorAction Stop
    if ($task.Description -ne $description) { throw "Unowned task: $Name" }
    return $task
}

if ($Mode -eq 'Install') {
    $pythonExe = (& $Python -c 'import sys; print(sys.executable)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Python resolution failed' }
    $pythonw = Join-Path (Split-Path $pythonExe -Parent) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonw)) { throw "pythonw missing: $pythonw" }
    if (-not (Test-Path -LiteralPath (Join-Path $source 'runtime_adapters\windows_paos_service.py'))) {
        throw 'Publish the background host before installing its tasks'
    }
    $user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    foreach ($index in 0..1) {
        $name = $names[$index]
        $role = @('core', 'bridge')[$index]
        $existing = Get-ScheduledTask -TaskPath '\' | Where-Object TaskName -eq $name
        if ($existing) {
            Read-OwnedTask $name | Out-Null
            if ($existing.State -eq 'Running') { throw "Stop owned task before changing its definition: $name" }
        }
        $arguments = '-X utf8 -u -m runtime_adapters.windows_paos_service --role ' + $role +
            ' --installation-file "' + $InstallationFile + '"'
        $action = New-ScheduledTaskAction -Execute $pythonw -Argument $arguments -WorkingDirectory $source
        Register-ScheduledTask -TaskPath '\' -TaskName $name -Description $description `
            -Action $action -Principal $principal -Settings $settings -Force | Out-Null
    }
    # Retire only the shortcut pointing to this installation's old VBS launcher.
    $startup = [Environment]::GetFolderPath('Startup')
    $oldTarget = Join-Path $source 'scripts\autostart\paos-autostart.vbs'
    foreach ($file in Get-ChildItem -LiteralPath $startup -Filter '*.lnk') {
        $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($file.FullName)
        if ($shortcut.TargetPath -eq $oldTarget) {
            $archive = Join-Path (Split-Path $InstallationFile -Parent) 'windows-services'
            New-Item -ItemType Directory -Path $archive -Force | Out-Null
            $destination = Join-Path $archive $file.Name
            if (Test-Path -LiteralPath $destination) { throw "Shortcut backup exists: $destination" }
            Move-Item -LiteralPath $file.FullName -Destination $destination
        }
    }
}

if ($Mode -eq 'Switch') {
    foreach ($name in $names) {
        if ((Read-OwnedTask $name).State -eq 'Running') { throw 'Switch is only for legacy processes, not already-running tasks' }
    }
    if (-not $CorePid -or -not $BridgePid) { throw 'Switch needs the exact existing CorePid and BridgePid' }
    $expected = @(@{pid=$CorePid;pattern='attention-dashboard-v1-static[/\\]paos_server\.py'},
        @{pid=$BridgePid;pattern='runtime_adapters[./\\]windows_wsl_paos_bridge'})
    # Validate both targets before stopping either; do not stop unknown listeners.
    foreach ($entry in $expected) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.pid)"
        if (-not $process -or $process.CommandLine -notmatch $entry.pattern) { throw 'Existing process identity mismatch' }
        $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8766 | Where-Object OwningProcess -eq $entry.pid)
        if ($listeners.Count -ne 1) { throw 'Existing listener identity mismatch' }
    }
    foreach ($entry in $expected) {
        Stop-Process -Id $entry.pid
        $process = Get-Process -Id $entry.pid -ErrorAction SilentlyContinue
        if ($process -and -not $process.WaitForExit(5000)) { throw 'Existing service did not exit' }
    }
}

if ($Mode -in @('Start', 'Switch')) {
    foreach ($name in $names) {
        $task = Read-OwnedTask $name
        if ($task.State -ne 'Running') {
            if ($name -eq 'PAOS-Core' -and (Get-NetTCPConnection -State Listen -LocalPort 8766 -ErrorAction SilentlyContinue |
                Where-Object LocalAddress -eq '127.0.0.1')) { throw 'Existing Core listener; use explicit Switch, not a second start' }
            if ($name -eq 'PAOS-WSL-Bridge' -and (Get-NetTCPConnection -State Listen -LocalPort 8766 -ErrorAction SilentlyContinue |
                Where-Object LocalAddress -notin @('127.0.0.1', '::1'))) { throw 'Existing bridge listener; use explicit Switch, not a second start' }
            Start-ScheduledTask -TaskPath '\' -TaskName $name
        }
    }
}
if ($Mode -eq 'Stop') {
    foreach ($name in $names) {
        Read-OwnedTask $name | Out-Null
        Stop-ScheduledTask -TaskPath '\' -TaskName $name
    }
}
function Get-RestartIntervalSeconds($Value) {
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) {
        return $null
    }
    if ($Value -is [TimeSpan]) {
        return [int][Math]::Round($Value.TotalSeconds)
    }
    try {
        return [int][Math]::Round(([System.Xml.XmlConvert]::ToTimeSpan([string]$Value)).TotalSeconds)
    } catch {
        try {
            return [int][Math]::Round(([TimeSpan]::Parse([string]$Value)).TotalSeconds)
        } catch {
            return $null
        }
    }
}
foreach ($name in $names) {
    $task = Read-OwnedTask $name
    $info = Get-ScheduledTaskInfo -TaskPath '\' -TaskName $name
    $restartInterval = $task.Settings.RestartInterval
    [pscustomobject]@{
        name=$name
        state=[string]$task.State
        user=$task.Principal.UserId
        logon=[string]$task.Principal.LogonType
        last_result=$info.LastTaskResult
        restart_count=[int]$task.Settings.RestartCount
        restart_interval=[string]$restartInterval
        restart_interval_seconds=Get-RestartIntervalSeconds $restartInterval
    }
}
