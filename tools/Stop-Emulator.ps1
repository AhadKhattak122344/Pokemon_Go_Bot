. "$PSScriptRoot/Android-Environment.ps1"
$adb = "$env:ANDROID_HOME/platform-tools/adb.exe"
& $adb -s emulator-5554 emu kill
if ($LASTEXITCODE -ne 0) { throw 'Emulator did not accept the shutdown request' }
$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    $devices = & $adb devices
} while ($devices -match 'emulator-5554\s' -and (Get-Date) -lt $deadline)
if ($devices -match 'emulator-5554\s') { throw 'Emulator did not release port 5554 within 30 seconds' }
