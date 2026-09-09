param([ValidateSet('Api36','Play','Rooted')][string]$Profile = 'Api36')
. "$PSScriptRoot/Android-Environment.ps1"
. "$PSScriptRoot/Emulator-Profiles.ps1"
$selected = Get-LabProfile $Profile
Assert-LabAvd $selected
$report = [ordered]@{ Profile=$Profile; Serial=$selected.Serial; Avd=$selected.Avd; Root='not changed or inferred'; Authentication='unverified'; Certification='manual check required' }
foreach ($entry in @(@('Boot','sys.boot_completed'), @('Api','ro.build.version.sdk'), @('Release','ro.build.version.release'), @('Abi','ro.product.cpu.abilist'), @('Bridge','ro.dalvik.vm.native.bridge'))) {
    $report[$entry[0]] = Invoke-LabAdb @('-s',$selected.Serial,'shell','getprop',$entry[1])
}
if ($report.Boot -ne '1' -or $report.Api -ne $selected.Api -or $report.Release -ne $selected.Release) { throw "Expected booted Android $($selected.Release) / API $($selected.Api). Observed $($report | ConvertTo-Json -Compress)" }
if ($report.Abi -notmatch '(^|,)x86_64(,|$)') { throw 'Expected x86_64 ABI' }
$packages = @('android','com.google.android.gms')
if ($selected.PlayStore) { $packages += 'com.android.vending' }
foreach ($package in $packages) {
    $path = Invoke-LabAdb @('-s',$selected.Serial,'shell','pm','path',$package)
    if ($path -notmatch '^package:') { throw "Missing package or unavailable package manager: $package" }
}
$report.AdbUid = Invoke-LabAdb @('-s',$selected.Serial,'shell','id','-u')
if ($Profile -eq 'Api36' -and $report.AdbUid -eq '0') { throw 'Clean API 36 baseline unexpectedly has root ADB. Investigate without repatching.' }
$output = Join-Path $WorkspaceRoot 'artifacts'
New-Item -ItemType Directory $output -Force | Out-Null
$path = Join-Path $output ("profile-$Profile-$([guid]::NewGuid().ToString('N')).json")
$report | ConvertTo-Json | Set-Content -LiteralPath $path -Encoding UTF8
$report | Format-List
Write-Host "Diagnostic report: $path. ABI properties do not establish native ARM compatibility."
