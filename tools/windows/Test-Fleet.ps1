$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Fleet-Common.ps1')
$repo = Get-FleetRepoRoot
$matrix = Get-FleetMatrix -Path (Join-Path $repo 'config/fleet-matrix.json')
$enabled = @(Select-FleetAvds -Matrix $matrix)
if ($enabled.Count -ne 3 -or $enabled[0] -is [array]) { throw 'Fleet selection is nested or has wrong enabled count' }
$one = @(Select-FleetAvds -Matrix $matrix -Only @('fleet_api35_pixel8'))
if ($one.Count -ne 1 -or $one[0].serial -ne 'emulator-5562') { throw 'Single selection failed' }
$all = @(Select-FleetAvds -Matrix $matrix -IncludeDisabled)
if ($all.Count -ne 4) { throw 'Disabled selection failed' }
$scratch = New-FleetArtifactDir -Name 'fleet-host-tests'
$rowsPath = Join-Path $scratch 'rows.json'
foreach ($json in @('[]','[{"pid":1}]','[{"pid":1},{"pid":2}]')) {
    Set-Content -LiteralPath $rowsPath -Value $json
    $rows = @(Read-FleetJsonRows -Path $rowsPath)
    $expectedCount = @([regex]::Matches($json,'"pid"')).Count
    if ($rows.Count -ne $expectedCount) { throw 'JSON report rows were nested or dropped' }
    if (@($rows | Where-Object { $_ -is [array] }).Count) { throw 'JSON report contains nested row arrays' }
}
$duplicate = Join-Path $scratch 'duplicate.json'
$matrix.avds[1].port = $matrix.avds[0].port
$matrix | ConvertTo-Json -Depth 8 | Set-Content $duplicate
$rejected = $false
try { Get-FleetMatrix -Path $duplicate | Out-Null } catch { $rejected = $true }
if (-not $rejected) { throw 'Duplicate port accepted' }

$psExe = Join-Path $PSHOME 'powershell.exe'
$native = Invoke-FleetNative -Exe $psExe -Arguments @('-NoProfile','-Command', "'hello'; [Console]::Error.WriteLine('diagnostic'); exit 7")
if ($native.ExitCode -ne 7 -or $native.Output -notmatch 'hello' -or $native.Output -notmatch 'diagnostic') { throw 'Native stream/exit capture failed' }
$timer = [Diagnostics.Stopwatch]::StartNew()
$timeout = Invoke-FleetNative -Exe $psExe -Arguments @('-NoProfile','-Command','Start-Sleep -Seconds 20') -TimeoutSeconds 1
if (-not $timeout.TimedOut -or $timeout.ExitCode -ne -1 -or $timer.Elapsed.TotalSeconds -gt 10) { throw 'Native timeout was not bounded' }
if ((ConvertTo-FleetNativeArgument '') -ne '""') { throw 'Empty native argument was dropped' }

# Exercise real -File parameter binding with defaults, outside the repository cwd.
Push-Location $scratch
try {
    foreach ($scriptName in @('New-FleetAvds.ps1','Start-Fleet.ps1','Stop-Fleet.ps1','Install-FleetGame.ps1','Run-FleetTests.ps1')) {
        $probe = Invoke-FleetNative -Exe $psExe -Arguments @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot $scriptName),'-DryRun')
        if ($probe.ExitCode -ne 0) { throw "Default path regression in ${scriptName}: $($probe.Output)" }
        $plan = $probe.Output | ConvertFrom-Json
        $resolved = if ($plan.action -eq 'game') { $plan.summary } else { $plan.matrix }
        if (-not $resolved.StartsWith($repo,[StringComparison]::OrdinalIgnoreCase)) { throw "Wrong default path in $scriptName" }
    }
} finally { Pop-Location }

function Get-FleetAdbState { return 'device' }
function Get-FleetAvdName { return 'unrelated-avd' }
function Invoke-FleetNative { throw 'Foreign AVD must never be killed' }
$stop = Stop-FleetEmulator -Adb unused -Serial emulator-5562 -ExpectedName fleet_api35_pixel8
if ($stop -notmatch '^left alone') { throw 'Foreign AVD protection failed' }

foreach ($file in Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*Fleet*.ps1') {
    $parseErrors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$null,[ref]$parseErrors)
    if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
    $badAssignments = $ast.FindAll({ param($node)
        $node -is [Management.Automation.Language.AssignmentStatementAst] -and
        $node.Left -is [Management.Automation.Language.VariableExpressionAst] -and
        $node.Left.VariablePath.UserPath -ieq 'pid'
    }, $true)
    if (@($badAssignments).Count) { throw "Reserved PID assignment in $($file.Name)" }
}
Write-Host 'PASS: fleet selection, duplicate-port rejection, native output/exit/timeout, foreign-AVD protection, reserved variables and syntax'
