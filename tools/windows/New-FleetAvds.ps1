<#
.SYNOPSIS
  Installs system images and creates the fleet AVDs from config/fleet-matrix.json.
  Creates NEW AVD names only. No root, no image edits. Realism = Pixel hardware profile,
  RAM/screen/sensors, PlayStore.enabled, no hardware keyboard/nav keys.
#>
[CmdletBinding()]
param(
    [string]$Matrix,
    [string[]]$Only,
    [switch]$SkipInstall,
    [switch]$Force,
    [switch]$DryRun,
    [string]$SdkRoot,
    [string]$JavaHome,
    [string]$AvdHome
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Fleet-Common.ps1')
if (-not $Matrix) { $Matrix = Join-Path (Get-FleetRepoRoot) 'config/fleet-matrix.json' }
$targets = @(Select-FleetAvds -Matrix (Get-FleetMatrix -Path $Matrix) -Only $Only)
if ($DryRun) { [pscustomobject]@{ action='create'; matrix=$Matrix; names=@($targets.name) } | ConvertTo-Json -Depth 4; return }

$tools   = Get-FleetTools -SdkRoot $SdkRoot -JavaHome $JavaHome -AvdHome $AvdHome -RequireManagers
$outDir  = New-FleetArtifactDir -Name 'fleet-create'
Write-Host "SDK: $($tools.Sdk)`nJDK: $($tools.JavaHome)`nAVD home: $($tools.AvdHome)`nArtifacts: $outDir"

$protected = @('poke_api36_test','poke_api361_test','poke_api37_test','baseline','baseline-rooted')
foreach ($a in $targets) { if ($protected -contains $a.name) { throw "Refusing to touch protected AVD $($a.name)" } }

# 1. System images
if (-not $SkipInstall) {
    $images  = @($targets | ForEach-Object image | Sort-Object -Unique)
    $missing = @($images | Where-Object { -not (Test-Path (Join-Path $tools.Sdk (($_ -replace ';','\') + '\source.properties'))) })
    if ($missing.Count -gt 0) {
        Write-Host 'Accepting SDK licenses...'
        $lic = Invoke-FleetNative -Exe $tools.SdkManager -Arguments @('--licenses') -StdIn ("y`n" * 40)
        Set-Content (Join-Path $outDir 'sdkmanager-licenses.log') $lic.Output
        if ($lic.ExitCode -ne 0) { throw "SDK license check failed; see $outDir" }
        foreach ($img in $missing) {
            Write-Host "Installing $img (this downloads ~1-3 GB) ..."
            $r = Invoke-FleetNative -Exe $tools.SdkManager -Arguments @('--channel=0', $img) -StdIn "y`n" -TimeoutSeconds 3600
            Add-Content (Join-Path $outDir 'sdkmanager-install.log') "== $img (exit $($r.ExitCode))`n$($r.Output)`n"
            if ($r.ExitCode -ne 0) { throw "sdkmanager failed for $img (exit $($r.ExitCode)); see $outDir" }
        }
    } else { Write-Host 'All system images already present.' }
}

# 2. Device profiles this SDK knows
$deviceList = Invoke-FleetNative -Exe $tools.AvdManager -Arguments @('list','device','-c')
Set-Content -LiteralPath (Join-Path $outDir 'device-profiles.txt') -Value $deviceList.Output
if ($deviceList.ExitCode -ne 0) { throw "Cannot list device profiles: $($deviceList.Output)" }
$knownDevices = @($deviceList.Output -split "`n" | ForEach-Object { $_.Trim() })

# 3. Create + shape AVDs
$summary = @()
foreach ($a in $targets) {
    $device = @($a.device) | Where-Object { $knownDevices -contains $_ } | Select-Object -First 1
    if (-not $device) { throw "No device profile from [$($a.device -join ', ')] exists in this SDK. Run: avdmanager list device -c" }

    $avdDir  = Join-Path $tools.AvdHome ("{0}.avd" -f $a.name)
    $created = $false
    if ((Test-Path $avdDir) -and -not $Force) {
        Write-Host "exists: $($a.name) (preserving existing configuration and data)"
        $summary += [pscustomobject]@{ name=$a.name; image=$a.image; device=$device; port=$a.port; serial=$a.serial; created=$false; configIni=(Join-Path $avdDir 'config.ini') }
        ConvertTo-Json -InputObject @($summary) -Depth 4 | Set-Content (Join-Path $outDir 'summary.json')
        continue
    } else {
        $createArgs = @('create','avd','--name',$a.name,'--package',$a.image,'--device',$device,'--sdcard',"$($a.sdcardMb)M")
        if ($Force) { $createArgs += '--force' }
        $r = Invoke-FleetNative -Exe $tools.AvdManager -Arguments $createArgs -StdIn "no`n" -TimeoutSeconds 180
        Add-Content (Join-Path $outDir 'avdmanager.log') "== $($a.name) (exit $($r.ExitCode))`n$($r.Output)`n"
        if ($r.ExitCode -ne 0 -or -not (Test-Path $avdDir)) { throw "avdmanager create failed for $($a.name); see $outDir\avdmanager.log" }
        $created = $true
    }

    $cfg = Join-Path $avdDir 'config.ini'
    $ini = [ordered]@{}
    foreach ($line in (Get-Content $cfg)) {
        if ($line -match '^\s*([^#=]+?)\s*=\s*(.*)$') { $ini[$Matches[1]] = $Matches[2] }
    }
    $set = @{
        'avd.ini.displayname'       = $a.displayName
        'hw.device.name'            = $device
        'hw.device.manufacturer'    = 'Google'
        'hw.ramSize'                = "$($a.ramMb)"
        'vm.heapSize'               = "$($a.heapMb)"
        'disk.dataPartition.size'   = "$($a.internalStorageMb)M"
        'hw.gpu.enabled'            = 'yes'
        'hw.gpu.mode'               = $a.gpu
        'hw.keyboard'               = 'no'
        'hw.mainKeys'               = 'no'
        'hw.dPad'                   = 'no'
        'hw.trackBall'              = 'no'
        'hw.camera.back'            = 'virtualscene'
        'hw.camera.front'           = 'emulated'
        'hw.gps'                    = 'yes'
        'hw.accelerometer'          = 'yes'
        'hw.gyroscope'              = 'yes'
        'hw.sensors.orientation'    = 'yes'
        'hw.sensors.proximity'      = 'yes'
        'hw.sensors.light'          = 'yes'
        'hw.sensors.pressure'       = 'yes'
        'hw.sensors.magnetic_field' = 'yes'
        'hw.battery'                = 'yes'
        'hw.audioInput'             = 'yes'
        'hw.audioOutput'            = 'yes'
        'PlayStore.enabled'         = 'true'
        'fastboot.forceColdBoot'    = 'no'
        'showDeviceFrame'           = 'no'
    }
    foreach ($k in $set.Keys) { $ini[$k] = $set[$k] }
    @($ini.Keys | ForEach-Object { "{0}={1}" -f $_, $ini[$_] }) | Set-Content -Path $cfg -Encoding ASCII
    Copy-Item $cfg (Join-Path $outDir ("{0}-config.ini" -f $a.name))

    Write-Host ("ready: {0}  image={1}  device={2}  serial={3}" -f $a.name, $a.image, $device, $a.serial)
    $summary += [pscustomobject]@{ name=$a.name; image=$a.image; device=$device; port=$a.port; serial=$a.serial; created=$created; configIni=$cfg }
    ConvertTo-Json -InputObject @($summary) -Depth 4 | Set-Content (Join-Path $outDir 'summary.json')
}
ConvertTo-Json -InputObject @($summary) -Depth 4 | Set-Content (Join-Path $outDir 'summary.json')
$summary | Format-Table -AutoSize
