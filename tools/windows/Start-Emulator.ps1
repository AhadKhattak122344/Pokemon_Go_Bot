param(
    [ValidateSet('Api36','Play','Rooted')][string]$Profile = 'Api36',
    [switch]$Headless,
    [ValidateRange(1,3600)][int]$TimeoutSeconds = 600
)
. "$PSScriptRoot/Android-Environment.ps1"
. "$PSScriptRoot/Emulator-Profiles.ps1"
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
$arguments = @('-avd',$selected.Avd,'-port',$selected.Port,'-no-audio','-gpu','auto','-memory','4096','-cores','4','-no-snapshot-load')
if ($Headless) { $arguments += '-no-window' }
$process = Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$log.log" -RedirectStandardError "$log.error.log"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
try {
    $lastError = 'Android has not booted'
    do {
        if ($process.HasExited) { throw "Emulator exited. Inspect $log.error.log" }
        try {
            $remaining = [Math]::Max(1, [Math]::Min(10, [Math]::Ceiling(($deadline - (Get-Date)).TotalSeconds)))
            $boot = Invoke-LabAdb @('-s',$selected.Serial,'shell','getprop','sys.boot_completed') -TimeoutSeconds $remaining
            if ($boot -eq '1') {
                Assert-LabAvd $selected
                & "$PSScriptRoot/Test-Emulator.ps1" -Profile $Profile
                Write-Host "$($selected.Avd) is ready on $($selected.Serial). No root or image patches were applied."
                return
            }
        } catch { $lastError = $_.Exception.Message }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Emulator boot timed out after $TimeoutSeconds seconds. $lastError. Inspect $log.error.log"
} catch {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    throw
}
