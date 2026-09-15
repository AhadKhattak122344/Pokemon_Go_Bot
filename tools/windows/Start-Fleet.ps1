<#
.SYNOPSIS
  Boots fleet AVDs in parallel on their own console ports, waits for boot, enforces the PNG-screenshot
  display rule, captures getprop/crash/GMS/GSF evidence, and writes artifacts/fleet-latest.json.
#>
[CmdletBinding()]
param(
    [string]$Matrix,
    [string]$SummaryPath,
    [string[]]$Only,
    [ValidateRange(1,8)][int]$MaxParallel = 2,
    [ValidateRange(1,3600)][int]$TimeoutSeconds = 240,
    [ValidateRange(0,120)][int]$SettleSeconds = 25,
    [switch]$ColdBoot,
    [switch]$KeepOnFailure,
    [switch]$DryRun,
    [string]$SdkRoot, [string]$JavaHome, [string]$AvdHome
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Fleet-Common.ps1')
if (-not $Matrix) { $Matrix = Join-Path (Get-FleetRepoRoot) 'config/fleet-matrix.json' }
if (-not $SummaryPath) { $SummaryPath = Join-Path (Get-FleetRepoRoot) 'artifacts/fleet-latest.json' }
$targets = @(Select-FleetAvds -Matrix (Get-FleetMatrix -Path $Matrix) -Only $Only)
if ($DryRun) { [pscustomobject]@{ action='start'; matrix=$Matrix; names=@($targets.name) } | ConvertTo-Json -Depth 4; return }

$tools   = Get-FleetTools -SdkRoot $SdkRoot -JavaHome $JavaHome -AvdHome $AvdHome
$gpuHelp = Invoke-FleetNative -Exe $tools.Emulator -Arguments @('-help-gpu')
$supportedModes = @([regex]::Matches($gpuHelp.Output, '(?m)^\s+([a-z][a-z0-9_]*)\s+(?:\(default\)\s+)?->') | ForEach-Object { $_.Groups[1].Value })
if ($gpuHelp.ExitCode -ne 0 -or $supportedModes.Count -eq 0) { throw 'Could not read supported GPU modes from the installed emulator.' }
foreach ($target in $targets) { if ($target.gpu -notin $supportedModes) { throw "Unsupported GPU mode '$($target.gpu)' for $($target.name); supported: $($supportedModes -join ', ')" } }
$outDir  = New-FleetArtifactDir -Name 'fleet-start'
New-Item -ItemType Directory -Path (Split-Path -Parent ([IO.Path]::GetFullPath($SummaryPath))) -Force | Out-Null
ConvertTo-Json -InputObject @() | Set-Content -LiteralPath $SummaryPath
$adbStart = Invoke-FleetNative -Exe $tools.Adb -Arguments @('start-server')
if ($adbStart.ExitCode -ne 0) { throw "ADB startup failed: $($adbStart.Output)" }
Write-Host "Artifacts: $outDir"

foreach ($a in $targets) {
    if (@('device','offline','unauthorized') -contains (Get-FleetAdbState -Adb $tools.Adb -Serial $a.serial)) {
        $who = Get-FleetAvdName -Adb $tools.Adb -Serial $a.serial
        throw "Port $($a.port) already has an emulator ('$who'). Stop it first; this script never kills what it did not start."
    }
    if (-not (Test-Path (Join-Path $tools.AvdHome "$($a.name).avd"))) { throw "AVD $($a.name) missing. Run New-FleetAvds.ps1 first." }
    $listeners = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    if (@($listeners | Where-Object { $_.Port -in @([int]$a.port, ([int]$a.port + 1)) }).Count) {
        throw "Console/ADB port $($a.port) or $([int]$a.port + 1) is already in use."
    }
}

function Start-OneEmulator($a) {
    $dir = Join-Path $outDir $a.name
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $emuArgs = @('-avd', $a.name, '-port', "$($a.port)", '-gpu', $a.gpu, '-no-boot-anim', '-netdelay', 'none', '-netspeed', 'full', '-crash-report-mode', 'never')
    if ($ColdBoot) { $emuArgs += '-no-snapshot-load' }
    foreach ($f in @($a.features)) { if ($f) { $emuArgs += @('-feature', $f) } }
    foreach ($x in @($a.extraArgs)) { if ($x) { $emuArgs += $x } }
    Set-Content (Join-Path $dir 'command.txt') ("`"{0}`" {1}" -f $tools.Emulator, ($emuArgs -join ' '))
    $quotedArgs = ($emuArgs | ForEach-Object { ConvertTo-FleetNativeArgument ([string]$_) }) -join ' '
    $p = Start-Process -FilePath $tools.Emulator -ArgumentList $quotedArgs -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $dir 'emulator-stdout.log') `
            -RedirectStandardError  (Join-Path $dir 'emulator-stderr.log')
    $tracked = @{}
    Update-FleetTrackedProcessTree -OwnProcess $p -TrackedProcesses $tracked
    [pscustomobject]@{ avd = $a; dir = $dir; pid = $p.Id; process = $p; tracked = $tracked; started = (Get-Date) }
}

function Wait-OneEmulator($h) {
    $a = $h.avd; $dir = $h.dir; $adb = $tools.Adb
    $res = [ordered]@{
        name = $a.name; serial = $a.serial; port = $a.port; image = $a.image; gpu = $a.gpu
        features = @($a.features); pid = $h.pid; booted = $false; avdNameVerified = $false
        displayOk = $false; surfaceFlingerAssert = $false; gmsVersion = ''; gsfIdHex = ''
        fingerprint = ''; abilist = ''; status = 'unknown'; artifacts = $dir; stop = ''
    }
    $remaining = [Math]::Max(1, $TimeoutSeconds - [int]((Get-Date) - $h.started).TotalSeconds)
    $res.booted = Wait-FleetBoot -Adb $adb -Serial $a.serial -TimeoutSeconds $remaining -OwnProcess $h.process -TrackedProcesses $h.tracked
    if (-not $res.booted) {
        $res.status = 'boot_timeout'
        if ($h.process.HasExited) { $res.status = 'emulator_exited' }
        Save-FleetText -Adb $adb -Serial $a.serial -AdbArgs @('logcat','-b','crash','-d') -Path (Join-Path $dir 'crash.txt') | Out-Null
        return [pscustomobject]$res
    }
    $res.avdNameVerified = ((Get-FleetAvdName -Adb $adb -Serial $a.serial) -eq $a.name)
    if (-not $res.avdNameVerified) { $res.status = 'avd_name_mismatch'; return [pscustomobject]$res }
    Start-Sleep -Seconds $SettleSeconds

    $props = Save-FleetText -Adb $adb -Serial $a.serial -AdbArgs @('shell','getprop') -Path (Join-Path $dir 'getprop.txt')
    $res.fingerprint = [regex]::Match($props, '\[ro\.build\.fingerprint\]: \[(.*?)\]').Groups[1].Value
    $res.abilist     = [regex]::Match($props, '\[ro\.product\.cpu\.abilist\]: \[(.*?)\]').Groups[1].Value

    $crash = Save-FleetText -Adb $adb -Serial $a.serial -AdbArgs @('logcat','-b','crash','-d') -Path (Join-Path $dir 'crash.txt')
    $res.surfaceFlingerAssert = [bool]($crash -match 'hasReadColorBufferDma|GoldfishMapper::readFromHost')

    $gms = Save-FleetText -Adb $adb -Serial $a.serial -AdbArgs @('shell','dumpsys','package','com.google.android.gms') -Path (Join-Path $dir 'gms-dumpsys.txt')
    $res.gmsVersion = [regex]::Match($gms, 'versionName=(\S+)').Groups[1].Value

    # GSF Android ID (may be permission-denied on newer builds; recorded either way).
    $gsfCmd = "content query --uri content://com.google.android.gsf.gservices --projection value --where `"name='android_id'`"`nexit`n"
    $gsf = Invoke-FleetNative -Exe $adb -Arguments @('-s', $a.serial, 'shell') -StdIn $gsfCmd
    Set-Content (Join-Path $dir 'gsf-id.txt') $gsf.Output
    $m = [regex]::Match($gsf.Output, 'value=(\d+)')
    if ($m.Success) { $res.gsfIdHex = ([uint64]$m.Groups[1].Value).ToString('x') }

    $res.displayOk = Save-FleetScreenshot -Adb $adb -Serial $a.serial -Path (Join-Path $dir 'boot.png')
    $res.status = if ($res.displayOk -and -not $res.surfaceFlingerAssert) { 'display_ok' } else { 'display_failed' }
    return [pscustomobject]$res
}

$results = @()
for ($i = 0; $i -lt $targets.Count; $i += $MaxParallel) {
    $end   = [Math]::Min($i + $MaxParallel, $targets.Count) - 1
    $batch = @($targets[$i..$end])
    $handles = @()
    foreach ($a in $batch) {
        Write-Host ("starting {0} on {1} gpu={2} features=[{3}]" -f $a.name, $a.serial, $a.gpu, (@($a.features) -join ' '))
        try { $handles += Start-OneEmulator $a }
        catch {
            $results += [pscustomobject]@{ name=$a.name; serial=$a.serial; status='start_error'; error="$($_.Exception.Message)"; booted=$false; displayOk=$false }
        }
    }
    foreach ($h in $handles) {
        try { $r = Wait-OneEmulator $h }
        catch {
            $r = [pscustomobject]@{ name=$h.avd.name; serial=$h.avd.serial; pid=$h.pid; status='capture_error'; error="$($_.Exception.Message)"; booted=$false; displayOk=$false; stop=''; artifacts=$h.dir }
        }
        if ($r.status -ne 'display_ok' -and -not $KeepOnFailure) {
            $r.stop = Stop-FleetEmulator -Adb $tools.Adb -Serial $r.serial -ExpectedName $r.name -OwnProcess $h.process -TrackedProcesses $h.tracked
        }
        Write-Host ("{0}: {1}" -f $r.name, $r.status)
        $results += $r
        $r | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $h.dir 'result.json')
        ConvertTo-Json -InputObject @($results) -Depth 5 | Set-Content (Join-Path $outDir 'summary.json')
        ConvertTo-Json -InputObject @($results) -Depth 5 | Set-Content -LiteralPath $SummaryPath
    }
}

ConvertTo-Json -InputObject @($results) -Depth 5 | Set-Content (Join-Path $outDir 'summary.json')
ConvertTo-Json -InputObject @($results) -Depth 5 | Set-Content -LiteralPath $SummaryPath
$results | Select-Object name, serial, status, booted, displayOk, surfaceFlingerAssert, gmsVersion, abilist | Format-Table -AutoSize
Write-Host "`nRunning devices with display_ok stay up. Next: Install-FleetGame.ps1. Stop with Stop-Fleet.ps1."
if (@($results | Where-Object { $_.status -ne 'display_ok' }).Count -gt 0) { exit 1 }
