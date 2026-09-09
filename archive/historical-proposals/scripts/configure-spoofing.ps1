[CmdletBinding()]
param(
    [string]$Device,
    [switch]$UseZygiskNext,
    [switch]$EnforceDenyList,
    [string[]]$DenyListPackage = @('com.google.android.gms','com.android.vending','com.nianticlabs.pokemongo'),
    [switch]$NoReboot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'adb-common.ps1')

foreach ($package in $DenyListPackage) {
    if ($package -notmatch '^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$') { throw "Invalid package name: $package" }
}
$adb = Resolve-FleetAdb
$target = @(Get-FleetAdbTarget -Adb $adb -Device $Device)
$rootCheck = Invoke-FleetRoot -Adb $adb -Target $target -Command 'id' -Description 'Root authorization check'
if ($rootCheck -notmatch 'uid=0\(root\)') { throw "Root shell unavailable: $rootCheck" }

$nextCheck = 'for d in /data/adb/modules/zygisksu /data/adb/modules/zygisknext; do if [ -d "$d" ] && [ ! -e "$d/disable" ] && [ ! -e "$d/remove" ]; then echo enabled; fi; done'
$nextState = Invoke-FleetRoot -Adb $adb -Target $target -Command $nextCheck -Description 'Zygisk Next module check'
if ($UseZygiskNext -and $nextState -notmatch 'enabled') { throw 'Zygisk Next is not enabled in /data/adb/modules. Install it and reboot before using -UseZygiskNext.' }
if (-not $UseZygiskNext -and $nextState -match 'enabled') { throw 'Zygisk Next is installed. Use -UseZygiskNext or disable it and reboot before selecting built-in Zygisk.' }

$zygiskValue = if ($UseZygiskNext) { 0 } else { 1 }
$zygiskSql = "magisk --sqlite `"REPLACE INTO settings (key,value) VALUES ('zygisk',$zygiskValue);`""
Invoke-FleetRoot -Adb $adb -Target $target -Command $zygiskSql -Description 'Zygisk configuration' | Write-Host
$denyListMode = if ($EnforceDenyList) { 'enable' } else { 'disable' }
Invoke-FleetRoot -Adb $adb -Target $target -Command "magisk --denylist $denyListMode" -Description 'DenyList mode configuration' | Write-Host
$existingEntries = Invoke-FleetRoot -Adb $adb -Target $target -Command 'magisk --denylist ls' -Description 'DenyList lookup'
foreach ($package in ($DenyListPackage | Select-Object -Unique)) {
    if ($existingEntries -notmatch ("(?m)^" + [regex]::Escape($package) + "(?:[|\s]|$)")) {
        Invoke-FleetRoot -Adb $adb -Target $target -Command "magisk --denylist add '$package'" -Description "DenyList entry for $package" | Write-Host
    }
}

$androidId = -join (1..16 | ForEach-Object { '{0:x}' -f (Get-Random -Minimum 0 -Maximum 16) })
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$temp = Join-Path $tempRoot ("android-fleet-profile-" + [guid]::NewGuid().ToString('N'))
$remoteTemp = "/data/local/tmp/android-fleet-profile-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    Write-FleetUnixText -Path (Join-Path $temp 'module.prop') -Text @"
id=android_fleet_pixel4
name=Android Fleet Pixel 4 Lab Profile
version=1.1
versionCode=2
author=local-fleet
description=Lab build properties; does not provide certification or hardware identity
"@
    Write-FleetUnixText -Path (Join-Path $temp 'system.prop') -Text @"
ro.product.manufacturer=Google
ro.product.brand=google
ro.product.model=Pixel 4
ro.product.name=flame
ro.product.device=flame
ro.build.product=flame
ro.build.fingerprint=google/flame/flame:13/TP1A.221005.002/9012097:user/release-keys
ro.build.description=flame-user 13 TP1A.221005.002 9012097 release-keys
"@
    Write-FleetUnixText -Path (Join-Path $temp 'service.sh') -Text @"
#!/system/bin/sh
# Wait for the settings provider, which need not be ready at late_start.
attempt=0
while [ "`$(getprop sys.boot_completed)" != 1 ] && [ "`$attempt" -lt 120 ]; do
    sleep 2
    attempt=`$((attempt + 1))
done
[ "`$(getprop sys.boot_completed)" = 1 ] || exit 1
settings put secure android_id $androidId
"@
    # Push individual files into a unique existing directory; adb push of a
    # directory has different nesting semantics when the destination exists.
    & $adb @target shell mkdir -p $remoteTemp | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create device staging directory.' }
    foreach ($name in @('module.prop','system.prop','service.sh')) {
        & $adb @target push (Join-Path $temp $name) "$remoteTemp/$name" | Write-Host
        if ($LASTEXITCODE -ne 0) { throw "Unable to upload profile file: $name" }
    }
    $install = "mkdir -p /data/adb/modules/android_fleet_pixel4 && cp '$remoteTemp/module.prop' '$remoteTemp/system.prop' '$remoteTemp/service.sh' /data/adb/modules/android_fleet_pixel4/ && chown -R 0:0 /data/adb/modules/android_fleet_pixel4 && chmod 0755 /data/adb/modules/android_fleet_pixel4 /data/adb/modules/android_fleet_pixel4/service.sh && chmod 0644 /data/adb/modules/android_fleet_pixel4/module.prop /data/adb/modules/android_fleet_pixel4/system.prop"
    Invoke-FleetRoot -Adb $adb -Target $target -Command $install -Description 'Lab profile installation' | Write-Host
} finally {
    & $adb @target shell rm -f "$remoteTemp/module.prop" "$remoteTemp/system.prop" "$remoteTemp/service.sh" | Out-Null
    & $adb @target shell rmdir $remoteTemp 2>$null | Out-Null
    $resolvedTemp = [IO.Path]::GetFullPath($temp)
    if ($resolvedTemp.StartsWith($tempRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -and
        [IO.Path]::GetFileName($resolvedTemp) -like 'android-fleet-profile-*') {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Requested lab Android ID setting: $androidId"
Write-Warning 'Android 8+ app-scoped Android IDs and hardware-backed identifiers are not established by this setting. Assign the VM NIC MAC in Proxmox; this script does not change IMEI or network interfaces.'
Write-Host 'Profile configuration completed. Reboot and measure the effective properties and app behavior.'
if (-not $NoReboot) {
    & $adb @target reboot
    if ($LASTEXITCODE -ne 0) { throw 'ADB reboot failed.' }
}
