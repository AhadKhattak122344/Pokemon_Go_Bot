param([switch]$Headless, [int]$TimeoutSeconds = 600)
. "$PSScriptRoot/Android-Environment.ps1"
# Android tools write diagnostics to stderr even on success. Check exit codes.
$ErrorActionPreference = 'Continue'
$avd = 'regibot_api30'
$emulator = "$env:ANDROID_HOME/emulator/emulator.exe"
$adb = "$env:ANDROID_HOME/platform-tools/adb.exe"
if (!(Test-Path $emulator)) { throw 'Run tools/Bootstrap-Android.ps1 -WithEmulator first.' }
if (!(Test-Path "$env:ANDROID_AVD_HOME/$avd.ini")) {
    'no' | & "$env:ANDROID_HOME/cmdline-tools/latest/bin/avdmanager.bat" create avd --force --name $avd --package 'system-images;android-30;google_apis;x86' --device pixel_4
    if ($LASTEXITCODE -ne 0) { throw 'AVD creation failed' }
}
& $adb start-server | Out-Null
$devices = & $adb devices
if ($devices -match 'emulator-5554\s') { throw 'Port 5554 is already occupied by an emulator. Stop it before launching this lab.' }
$output = Join-Path $WorkspaceRoot 'artifacts'
New-Item -ItemType Directory $output -Force | Out-Null
$arguments = @('-avd',$avd,'-port','5554','-no-snapshot','-no-audio','-gpu','swiftshader','-memory','4096','-cores','4')
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
    $apk = Join-Path $WorkspaceRoot 'recovered/app/build/outputs/apk/debug/app-debug.apk'
    if (!(Test-Path $apk)) { throw 'APK missing. Run tools/Build-App.ps1 first.' }
    & $adb -s emulator-5554 install -r $apk
    if ($LASTEXITCODE -ne 0) { throw 'APK installation failed' }
    & $adb -s emulator-5554 shell am start -W -n com.juancavr6.regibot/.MainActivity
    if ($LASTEXITCODE -ne 0) { throw 'App launch failed' }
    Write-Host 'RegiBot is running. Stop with tools/Stop-Emulator.ps1.'
} catch {
    if (!$process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    throw
}
