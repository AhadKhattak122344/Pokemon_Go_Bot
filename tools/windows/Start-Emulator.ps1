param(
    [ValidateSet('Api36','Api361','Api37','Play','Rooted')][string]$Profile = 'Api36',
    [switch]$Headless,
    [ValidateSet('auto','host','software','lavapipe','swiftshader','swangle')][string]$Gpu = 'auto',
    [switch]$DisableSharedSlots,
    [ValidateRange(1,3600)][int]$TimeoutSeconds = 600
)
. "$PSScriptRoot/Android-Environment.ps1"
. "$PSScriptRoot/Emulator-Profiles.ps1"

function Test-ProcessCreationMatch {
    param([object]$ProcessRecord, [datetime]$StartTime)
    # Win32_Process exposes microsecond-oriented CIM timestamps while
    # System.Diagnostics.Process exposes a .NET timestamp. Compare their common
    # millisecond precision rather than rejecting the same process over sub-ms
    # conversion noise.
    # Formatting truncates fractional seconds without converting large tick
    # counts to doubles (which can round across a millisecond boundary).
    $recordMilliseconds = $ProcessRecord.CreationDate.ToUniversalTime().ToString('yyyyMMddHHmmssfff')
    $startMilliseconds = $StartTime.ToUniversalTime().ToString('yyyyMMddHHmmssfff')
    return $recordMilliseconds -eq $startMilliseconds
}

function Update-LaunchedProcessTree {
    param(
        [System.Diagnostics.Process]$RootProcess,
        [hashtable]$TrackedProcesses
    )

    # Record descendants while their parent relationship is still available. The
    # held launcher handle and its creation time must still identify the root
    # before any parent-PID edges are trusted.
    try {
        if ($RootProcess.HasExited) { return }
        $rootStartTime = $RootProcess.StartTime
    } catch { return }
    $allProcesses = @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)
    $rootRecord = $allProcesses | Where-Object { [int]$_.ProcessId -eq [int]$RootProcess.Id } | Select-Object -First 1
    if ($null -eq $rootRecord -or -not (Test-ProcessCreationMatch -ProcessRecord $rootRecord -StartTime $rootStartTime)) { return }
    $key = "$($rootRecord.ProcessId):$($rootRecord.CreationDate.ToUniversalTime().Ticks)"
    $TrackedProcesses[$key] = [pscustomobject]@{ ProcessId = [int]$rootRecord.ProcessId; CreationDate = $rootRecord.CreationDate; Depth = 0 }
    $frontier = @($rootRecord)
    $seen = New-Object 'System.Collections.Generic.HashSet[int]'
    [void]$seen.Add([int]$RootProcess.Id)
    $depth = 0
    while ($frontier.Count -gt 0) {
        $children = @(
            foreach ($parent in $frontier) {
                foreach ($candidate in $allProcesses) {
                    if ([int]$candidate.ParentProcessId -eq [int]$parent.ProcessId -and
                        $candidate.CreationDate -ge $parent.CreationDate -and
                        $seen.Add([int]$candidate.ProcessId)) {
                        $candidate
                    }
                }
            }
        )
        $depth++
        foreach ($child in $children) {
            $key = "$($child.ProcessId):$($child.CreationDate.ToUniversalTime().Ticks)"
            $TrackedProcesses[$key] = [pscustomobject]@{ ProcessId = [int]$child.ProcessId; CreationDate = $child.CreationDate; Depth = $depth }
        }
        $frontier = $children
    }
}

function Stop-LaunchedProcessTree {
    param(
        [System.Diagnostics.Process]$RootProcess,
        [hashtable]$TrackedProcesses
    )

    try { Update-LaunchedProcessTree -RootProcess $RootProcess -TrackedProcesses $TrackedProcesses } catch { }
    foreach ($record in @($TrackedProcesses.Values | Where-Object { $_.Depth -gt 0 } | Sort-Object Depth -Descending)) {
        try {
            $current = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($record.ProcessId)" -ErrorAction Stop
            $currentProcess = Get-Process -Id $record.ProcessId -ErrorAction Stop
            if ($null -ne $current -and [int]$currentProcess.Id -eq [int]$record.ProcessId -and
                (Test-ProcessCreationMatch -ProcessRecord $current -StartTime $record.CreationDate) -and
                (Test-ProcessCreationMatch -ProcessRecord $record -StartTime $currentProcess.StartTime)) {
                Stop-Process -InputObject $currentProcess -Force -ErrorAction SilentlyContinue
            }
        } catch { }
    }
    try {
        if (-not $RootProcess.HasExited) { Stop-Process -InputObject $RootProcess -Force -ErrorAction SilentlyContinue }
    } catch { }
}

$selected = Get-LabProfile $Profile
$emulator = Join-Path $env:ANDROID_HOME 'emulator/emulator.exe'
if (-not (Test-Path -LiteralPath $emulator)) { throw 'Run tools/windows/Bootstrap-Android.ps1 -WithEmulator first.' }
if (-not (Test-Path -LiteralPath "$env:ANDROID_AVD_HOME/$($selected.Avd).ini")) {
    $imagePath = Join-Path $env:ANDROID_HOME ($selected.Image.Replace(';','/'))
    if (-not (Test-Path -LiteralPath $imagePath)) { throw "System image missing: $($selected.Image). Run tools/windows/Bootstrap-Android.ps1 -WithEmulator." }
    'no' | & "$env:ANDROID_HOME/cmdline-tools/latest/bin/avdmanager.bat" create avd --name $selected.Avd --package $selected.Image --device pixel_7
    if ($LASTEXITCODE -ne 0) { throw 'AVD creation failed; existing AVDs were not overwritten.' }
}
$devices = Invoke-LabAdb @('devices')
if ($devices -match "(?m)^$($selected.Serial)\s") { throw "$($selected.Serial) is occupied. Select the correct profile or stop its AVD first." }
$output = Join-Path $WorkspaceRoot 'artifacts'
New-Item -ItemType Directory $output -Force | Out-Null
$log = "$output/emulator-$($selected.Avd)-$([guid]::NewGuid().ToString('N'))"
$arguments = @('-avd',$selected.Avd,'-port',$selected.Port,'-no-audio','-gpu',$Gpu,'-memory','4096','-cores','4','-no-snapshot-load')
if ($Headless) { $arguments += '-no-window' }
if ($DisableSharedSlots) { $arguments += @('-feature','-HasSharedSlotsHostMemoryAllocator') }
$process = Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.error.log"
$launchedProcesses = @{}
try { Update-LaunchedProcessTree -RootProcess $process -TrackedProcesses $launchedProcesses } catch { }
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
try {
    $lastError = 'Android has not booted'
    do {
        try { Update-LaunchedProcessTree -RootProcess $process -TrackedProcesses $launchedProcesses } catch { }
        if ($process.HasExited) { throw "Emulator exited. Inspect $log.error.log" }
        try {
            $remaining = [Math]::Max(1, [Math]::Min(10, [Math]::Ceiling(($deadline - (Get-Date)).TotalSeconds)))
            $boot = Invoke-LabAdb @('-s',$selected.Serial,'shell','getprop','sys.boot_completed') -TimeoutSeconds $remaining
            if ($boot -eq '1') {
                Assert-LabAvd $selected
                & "$PSScriptRoot/Test-Emulator.ps1" -Profile $Profile
                Write-Host "$($selected.Avd) boot/version checks passed on $($selected.Serial); display and app readiness require separate observation. No root or image patches were applied."
                return
            }
        } catch { $lastError = $_.Exception.Message }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Emulator boot timed out after $TimeoutSeconds seconds. $lastError. Inspect $log.error.log"
} catch {
    Stop-LaunchedProcessTree -RootProcess $process -TrackedProcesses $launchedProcesses
    throw
}
