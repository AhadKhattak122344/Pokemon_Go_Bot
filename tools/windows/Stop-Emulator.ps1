param([ValidateSet('Api36','Play','Rooted')][string]$Profile = 'Api36')
. "$PSScriptRoot/Android-Environment.ps1"
. "$PSScriptRoot/Emulator-Profiles.ps1"
$selected = Get-LabProfile $Profile
$devices = Invoke-LabAdb @('devices')
if ($devices -notmatch "(?m)^$($selected.Serial)\s") { Write-Host "$($selected.Avd) is already stopped."; return }
Assert-LabAvd $selected
Invoke-LabAdb @('-s',$selected.Serial,'emu','kill') | Write-Host
$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    $devices = Invoke-LabAdb @('devices')
} while ($devices -match "(?m)^$($selected.Serial)\s" -and (Get-Date) -lt $deadline)
if ($devices -match "(?m)^$($selected.Serial)\s") { throw 'The selected emulator did not disconnect within 30 seconds.' }
