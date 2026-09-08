param([switch]$SkipChecks)
. "$PSScriptRoot/Android-Environment.ps1"
$project = Join-Path $WorkspaceRoot 'recovered'
[IO.File]::WriteAllText((Join-Path $project 'local.properties'), "sdk.dir=$($env:ANDROID_HOME.Replace('\','/'))`n")
$tasks = @(':app:assembleDebug')
if (!$SkipChecks) { $tasks += @(':app:testDebugUnitTest', ':app:lintDebug') }
& "$project/gradlew.bat" -p $project --no-daemon @tasks
if ($LASTEXITCODE -ne 0) { throw "Gradle failed with exit code $LASTEXITCODE" }
$output = Join-Path $WorkspaceRoot 'artifacts'
New-Item -ItemType Directory $output -Force | Out-Null
Copy-Item "$project/app/build/outputs/apk/debug/app-debug.apk" "$output/RegiBot-debug.apk"
Get-FileHash "$output/RegiBot-debug.apk" -Algorithm SHA256
