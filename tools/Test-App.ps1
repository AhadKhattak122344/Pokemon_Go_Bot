. "$PSScriptRoot/Android-Environment.ps1"
$ErrorActionPreference = 'Continue'
$project = Join-Path $WorkspaceRoot 'recovered'
& "$project/gradlew.bat" -p $project --no-daemon :app:connectedDebugAndroidTest
if ($LASTEXITCODE -ne 0) { throw 'Device tests failed. Check recovered/app/build/reports/androidTests/connected/debug.' }
# Gradle removes the app after instrumentation. Restore it for interactive testing.
& "$env:ANDROID_HOME/platform-tools/adb.exe" -s emulator-5554 install -r "$project/app/build/outputs/apk/debug/app-debug.apk"
if ($LASTEXITCODE -ne 0) { throw 'Could not reinstall the app after tests' }
& "$env:ANDROID_HOME/platform-tools/adb.exe" -s emulator-5554 shell am start -W -n com.juancavr6.regibot/.MainActivity
if ($LASTEXITCODE -ne 0) { throw 'Could not launch the app after tests' }
