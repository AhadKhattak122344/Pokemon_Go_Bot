<#
.SYNOPSIS
  Installs the Pokemon GO split APKs on every fleet device that passed display_ok, launches once,
  observes, and classifies: install_failed / launch_error / native_crash / process_exited / process_running.
  process_running means a numeric PID was observed. Foreground UI and login are separate evidence.
#>
[CmdletBinding()]
param(
    [string]$Summary,
    [string]$ResultPath,
    [string[]]$Serials,
    [string]$ApkDir,
    [string]$PullFromSerial,
    [ValidatePattern('^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$')][string]$Package = 'com.nianticlabs.pokemongo',
    [ValidateRange(1,3600)][int]$ObserveSeconds = 60,
    [ValidateRange(1,60)][int]$SampleSeconds = 10,
    [switch]$Reinstall,
    [switch]$DryRun,
    [string]$SdkRoot, [string]$JavaHome, [string]$AvdHome
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Fleet-Common.ps1')
if (-not $Summary) { $Summary = Join-Path (Get-FleetRepoRoot) 'artifacts/fleet-latest.json' }
if (-not $ResultPath) { $ResultPath = Join-Path (Get-FleetRepoRoot) 'artifacts/fleet-game-latest.json' }
if ($DryRun) { [pscustomobject]@{ action='game'; summary=$Summary; package=$Package } | ConvertTo-Json -Depth 4; return }
New-Item -ItemType Directory -Path (Split-Path -Parent ([IO.Path]::GetFullPath($ResultPath))) -Force | Out-Null
ConvertTo-Json -InputObject @() | Set-Content -LiteralPath $ResultPath

$tools  = Get-FleetTools -SdkRoot $SdkRoot -JavaHome $JavaHome -AvdHome $AvdHome
$adb    = $tools.Adb
$outDir = New-FleetArtifactDir -Name 'fleet-game'
Write-Host "Artifacts: $outDir"

# Devices
$expectedNames = @{}
if (Test-Path -LiteralPath $Summary) {
    foreach ($entry in @(Read-FleetJsonRows -Path $Summary)) {
        if ($entry.status -eq 'display_ok') { $expectedNames[$entry.serial] = $entry.name }
    }
}
if (-not $Serials) {
    if (-not (Test-Path $Summary)) { throw "No -Serials given and $Summary not found. Run Start-Fleet.ps1 first." }
    $Serials = @(Read-FleetJsonRows -Path $Summary | Where-Object { $_.status -eq 'display_ok' } | ForEach-Object serial)
}
$Serials = @($Serials)
if ($Serials.Count -eq 0) { throw 'No display_ok devices to test.' }

# APKs
$apkDirResolved = $ApkDir
if ($PullFromSerial) {
    if ((Get-FleetAdbState -Adb $adb -Serial $PullFromSerial) -ne 'device') { throw "$PullFromSerial is not online." }
    $apkDirResolved = Join-Path $outDir 'apk'
    New-Item -ItemType Directory -Path $apkDirResolved -Force | Out-Null
    $paths = @((Invoke-FleetNative -Exe $adb -Arguments @('-s', $PullFromSerial, 'shell', 'pm', 'path', $Package)).Output -split "`n" |
               Where-Object { $_ -match '^package:' } | ForEach-Object { ($_ -replace '^package:', '').Trim() })
    if ($paths.Count -eq 0) { throw "$Package is not installed on $PullFromSerial." }
    foreach ($p in $paths) {
        Write-Host "pulling $p"
        $r = Invoke-FleetNative -Exe $adb -Arguments @('-s', $PullFromSerial, 'pull', $p, $apkDirResolved)
        if ($r.ExitCode -ne 0) { throw "pull failed: $($r.Output)" }
    }
}
if (-not $apkDirResolved -or -not (Test-Path $apkDirResolved)) { throw 'Provide -ApkDir <folder with base.apk + splits> or -PullFromSerial emulator-5556.' }
$apks = @(Get-ChildItem $apkDirResolved -Filter '*.apk' | ForEach-Object FullName)
if ($apks.Count -eq 0) { throw "No .apk files in $apkDirResolved" }
if (-not ($apks -match 'arm64')) { Write-Warning 'No arm64 split found in APK set; the game may fail with missing native libs.' }
Write-Host ("APK set ({0}): {1}" -f $apks.Count, (($apks | Split-Path -Leaf) -join ', '))

$results = @()
foreach ($serial in $Serials) {
    $avdName = Get-FleetAvdName -Adb $adb -Serial $serial
    if (-not $expectedNames.ContainsKey($serial) -or $avdName -ne $expectedNames[$serial]) {
        throw "No current name-matched display_ok result for $serial. Run Start-Fleet.ps1 first."
    }
    $dir = Join-Path $outDir ($(if ($avdName) { $avdName } else { $serial }))
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $res = [ordered]@{
        serial = $serial; avd = $avdName; package = $Package; abilist = ''; installed = $false
        installOutput = ''; component = ''; startOutput = ''; newFatalSignals = @(); sigill = $false
        pidAtEnd = ''; focusAtEnd = ''; screenshotsOk = 0; status = 'unknown'; artifacts = $dir
        authentication = 'unverified'; foregroundAtEnd = $false; observedPids = @(); probeErrors = @(); samplesTaken = 0
    }
    Write-Host "`n== $serial ($avdName)"

    if ((Get-FleetAdbState -Adb $adb -Serial $serial) -ne 'device') { $res.status = 'device_offline'; $results += [pscustomobject]$res; continue }

    $res.abilist = (Invoke-FleetNative -Exe $adb -Arguments @('-s', $serial, 'shell', 'getprop', 'ro.product.cpu.abilist')).Output
    if ($res.abilist -notmatch 'arm64-v8a') { $res.status = 'no_arm64_abi'; $results += [pscustomobject]$res; continue }

    # Pre-capture before any change (never clear buffers first).
    $preCrash = Save-FleetText -Adb $adb -Serial $serial -AdbArgs @('logcat','-b','crash','-d') -Path (Join-Path $dir 'crash-before.txt')
    Save-FleetScreenshot -Adb $adb -Serial $serial -Path (Join-Path $dir 'before.png') | Out-Null

    $already = (Invoke-FleetNative -Exe $adb -Arguments @('-s', $serial, 'shell', 'pm', 'path', $Package)).Output -match '^package:'
    if ($already -and -not $Reinstall) {
        $res.installed = $true; $res.installOutput = 'already installed'
    } else {
        Write-Host 'installing...'
        $r = Invoke-FleetNative -Exe $adb -Arguments (@('-s', $serial, 'install-multiple', '-r', '-g') + $apks) -TimeoutSeconds 180
        $res.installOutput = $r.Output
        Set-Content (Join-Path $dir 'install.txt') $r.Output
        $res.installed = ($r.ExitCode -eq 0 -and $r.Output -match 'Success')
        if (-not $res.installed) { $res.status = 'install_failed'; Write-Host "install failed: $($r.Output)"; $results += [pscustomobject]$res; continue }
    }

    Save-FleetText -Adb $adb -Serial $serial -AdbArgs @('shell','dumpsys','package',$Package) -Path (Join-Path $dir 'package.txt') | Out-Null
    $resolve = (Invoke-FleetNative -Exe $adb -Arguments @('-s', $serial, 'shell', 'cmd', 'package', 'resolve-activity', '--brief', '-c', 'android.intent.category.LAUNCHER', $Package)).Output
    $res.component = ([string]($resolve -split "`n" | Where-Object { $_ -match ('^' + [regex]::Escape($Package) + '/[A-Za-z0-9_.$]+$') } | Select-Object -Last 1)).Trim()
    if (-not $res.component) { $res.status = 'launch_error'; $res.startOutput = $resolve; $results += [pscustomobject]$res; continue }

    Write-Host "launching $($res.component)"
    $start = Invoke-FleetNative -Exe $adb -Arguments @('-s', $serial, 'shell', 'am', 'start', '-W', '-n', $res.component)
    $res.startOutput = $start.Output
    Set-Content (Join-Path $dir 'am-start.txt') $start.Output
    if ($start.ExitCode -ne 0 -or $start.Output -match 'Error|Exception') { $res.status = 'launch_error'; $results += [pscustomobject]$res; continue }

    $samples = [Math]::Max(1, [int][Math]::Ceiling($ObserveSeconds / $SampleSeconds))
    for ($s = 1; $s -le $samples; $s++) {
        Start-Sleep -Seconds ([Math]::Min($SampleSeconds, $ObserveSeconds - (($s - 1) * $SampleSeconds)))
        $res.samplesTaken++
        $pidProbe = Invoke-FleetNative -Exe $adb -Arguments @('-s', $serial, 'shell', 'pidof', $Package)
        $appPid = if ($pidProbe.ExitCode -eq 0 -and $pidProbe.Output -match '^\d+(\s+\d+)*$') { $pidProbe.Output } else { '' }
        if ($pidProbe.ExitCode -ne 0 -and $pidProbe.Output) { $res.probeErrors += $pidProbe.Output }
        if ($appPid) { $res.observedPids += @($appPid -split '\s+') }
        $windowProbe = Invoke-FleetNative -Exe $adb -Arguments @('-s', $serial, 'shell', 'dumpsys', 'window')
        $focus = (($windowProbe.Output -split "`n") | Where-Object { $_ -match 'mCurrentFocus|mFocusedApp' }) -join "`n"
        if ($windowProbe.ExitCode -ne 0) { $res.probeErrors += $windowProbe.Output }
        $ok    = Save-FleetScreenshot -Adb $adb -Serial $serial -Path (Join-Path $dir ("sample-{0:D2}.png" -f $s))
        if ($ok) { $res.screenshotsOk++ }
        Add-Content (Join-Path $dir 'observe.txt') ("[{0}] sample={1} pid={2} png={3}`n{4}`n" -f (Get-Date -Format 'o'), $s, $appPid, $ok, $focus)
        Write-Host ("  sample={0} pid={1} png={2}" -f $s, $(if ($appPid) { $appPid } else { '-' }), $ok)
        $res.pidAtEnd = $appPid; $res.focusAtEnd = $focus
        $res.foregroundAtEnd = [bool]($focus -match [regex]::Escape($Package))
        if (-not $appPid) { break }
    }

    $postCrash = Save-FleetText -Adb $adb -Serial $serial -AdbArgs @('logcat','-b','crash','-d') -Path (Join-Path $dir 'crash-after.txt')
    Save-FleetText -Adb $adb -Serial $serial -AdbArgs @('logcat','-d','-t','1500') -Path (Join-Path $dir 'logcat-tail.txt') | Out-Null
    $preLines = @($preCrash -split "`n")
    $newCrashLines = @(($postCrash -split "`n") | Where-Object { $preLines -notcontains $_ })
    $targetPids = @($res.observedPids)
    foreach ($line in $newCrashLines) {
        if ($line -match ('pid:\s*(\d+).*>>>\s*' + [regex]::Escape($Package) + '\s*<<<')) { $targetPids += $Matches[1] }
    }
    $res.newFatalSignals = @($newCrashLines | Where-Object {
        $_ -match 'Fatal signal.*pid\s+(\d+)\s*\(' -and $targetPids -contains $Matches[1]
    })
    $res.sigill = [bool](($res.newFatalSignals -join "`n") -match 'signal 4 \(SIGILL\)')

    if ($res.newFatalSignals.Count -gt 0) { $res.status = 'native_crash' }
    elseif ($res.probeErrors.Count -gt 0 -or $res.screenshotsOk -lt $res.samplesTaken) { $res.status = 'observation_partial' }
    elseif (-not $res.pidAtEnd)          { $res.status = 'process_exited' }
    else                                  { $res.status = 'process_running' }

    Write-Host ("result: {0}{1}" -f $res.status, $(if ($res.sigill) { ' (SIGILL)' } else { '' }))
    [pscustomobject]$res | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $dir 'result.json')
    $results += [pscustomobject]$res
}

ConvertTo-Json -InputObject @($results) -Depth 5 | Set-Content (Join-Path $outDir 'summary.json')
ConvertTo-Json -InputObject @($results) -Depth 5 | Set-Content -LiteralPath $ResultPath
$results | Select-Object avd, serial, status, sigill, pidAtEnd, screenshotsOk | Format-Table -AutoSize
Write-Host "`nprocess_running = observed process; authentication remains unverified. Evidence: $outDir"
if (@($results | Where-Object { $_.status -ne 'process_running' }).Count -gt 0) { exit 1 }
