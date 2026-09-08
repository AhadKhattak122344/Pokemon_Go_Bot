. "$PSScriptRoot/Android-Environment.ps1"
& "$env:ANDROID_HOME/platform-tools/adb.exe" -s emulator-5554 emu kill
if ($LASTEXITCODE -ne 0) { throw 'Emulator did not accept the shutdown request' }
