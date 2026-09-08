param(
    [ValidateSet('Play','Rooted')]
    [string]$Profile = 'Play',
    [switch]$Headless,
    [int]$TimeoutSeconds = 600
)
. "$PSScriptRoot/Android-Environment.ps1"
# Android tools write diagnostics to stderr even on success. Check exit codes.
$ErrorActionPreference = 'Continue'
$profiles = @{
    Play = @{
        Avd = 'baseline'
        Image = 'system-images;android-34;google_apis_playstore;x86_64'
        InstallMagisk = $false
    }
    Rooted = @{
        Avd = 'baseline-rooted'
        Image = 'system-images;android-34;google_apis;x86_64'
        InstallMagisk = $true
    }
}
$selected = $profiles[$Profile]
$avd = $selected.Avd
$emulator = "$env:ANDROID_HOME/emulator/emulator.exe"
$adb = "$env:ANDROID_HOME/platform-tools/adb.exe"
if (!(Test-Path $emulator)) { throw 'Run tools/Bootstrap-Android.ps1 -WithEmulator first.' }
if (!(Test-Path "$env:ANDROID_AVD_HOME/$avd.ini")) {
    'no' | & "$env:ANDROID_HOME/cmdline-tools/latest/bin/avdmanager.bat" create avd --force --name $avd --package $selected.Image --device pixel_7
    if ($LASTEXITCODE -ne 0) { throw 'AVD creation failed' }
}
& $adb start-server | Out-Null
$devices = & $adb devices
if ($devices -match 'emulator-5554\s') { throw 'Port 5554 is already occupied by an emulator. Stop it before launching this lab.' }
$output = Join-Path $WorkspaceRoot 'artifacts'
New-Item -ItemType Directory $output -Force | Out-Null
$arguments = @('-avd',$avd,'-port','5554','-no-audio','-gpu','auto','-memory','4096','-cores','4')
if ($Headless) { $arguments += '-no-window' }
$windowStyle = if ($Headless) { 'Hidden' } else { 'Normal' }
$process = Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle $windowStyle -PassThru -RedirectStandardOutput "$output/emulator.log" -RedirectStandardError "$output/emulator-error.log"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
try {
    do {
        if ($process.HasExited) { throw 'Emulator exited. See artifacts/emulator-error.log.' }
        $boot = & $adb -s emulator-5554 shell getprop sys.boot_completed 2>$null
        if ($boot -eq '1') { break }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    if ($boot -ne '1') { throw "Emulator boot timed out after $TimeoutSeconds seconds" }
    $sdk = (& $adb -s emulator-5554 shell getprop ro.build.version.sdk).Trim()
    $release = (& $adb -s emulator-5554 shell getprop ro.build.version.release).Trim()
    $abiList = (& $adb -s emulator-5554 shell getprop ro.product.cpu.abilist).Trim()
    if ($sdk -ne '34' -or $release -notlike '14*') { throw "Expected Android 14 / API 34, got Android $release / API $sdk" }
    if ($abiList -notmatch '(^|,)x86_64(,|$)') { throw "Expected x86_64 support, got $abiList" }

    if ($selected.InstallMagisk) {
        & "$PSScriptRoot/Install-Magisk.ps1" -Serial emulator-5554
        if ($LASTEXITCODE -ne 0) { throw 'Magisk setup failed' }
    } else {
        $playStore = & $adb -s emulator-5554 shell pm path com.android.vending
        if ($LASTEXITCODE -ne 0 -or $playStore -notmatch '^package:') { throw 'Google Play Store is missing from baseline' }
    }

    Write-Host "$avd is running (Android $release, $abiList) on emulator-5554. Stop with tools/Stop-Emulator.ps1."
} catch {
    if (!$process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    throw
}
