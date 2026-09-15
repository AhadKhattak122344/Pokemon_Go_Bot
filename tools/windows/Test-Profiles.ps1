$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/Emulator-Profiles.ps1"
$clean = Get-LabProfile Api36
if ($clean.Avd -ne 'poke_api36_test' -or $clean.Port -ne 5556 -or $clean.Api -ne '36') { throw 'Clean profile mismatch' }
$api361 = Get-LabProfile Api361
if ($api361.Avd -ne 'poke_api361_test' -or $api361.Port -ne 5558 -or $api361.Api -ne '36' -or $api361.Minor -ne '1' -or $api361.ImageApi -ne '36.1' -or $api361.Release -ne '16') { throw 'API 36.1 profile mismatch' }
if ($api361.Serial -ne 'emulator-5558' -or $api361.Image -ne 'system-images;android-36.1;google_apis_playstore;x86_64') { throw 'API 36.1 image or serial mismatch' }
if ($api361.Port -eq $clean.Port -or $api361.Avd -eq $clean.Avd) { throw 'API 36.1 profile is not isolated from API 36' }
$api37 = Get-LabProfile Api37
if ($api37.Avd -ne 'poke_api37_test' -or $api37.Port -ne 5560 -or $api37.Api -ne '37' -or $api37.ImageApi -ne '37.0' -or $api37.Release -ne '17') { throw 'API 37 profile mismatch' }
if ($api37.Serial -ne 'emulator-5560' -or $api37.Image -ne 'system-images;android-37.0;google_apis_playstore;x86_64') { throw 'API 37 image or serial mismatch' }
if ($api37.Port -eq $clean.Port -or $api37.Port -eq $api361.Port -or $api37.Avd -eq $clean.Avd -or $api37.Avd -eq $api361.Avd) { throw 'API 37 profile is not isolated from clean profiles' }
$profileScripts = @('Start-Emulator.ps1', 'Stop-Emulator.ps1', 'Test-Emulator.ps1', 'Run-Experiment.ps1')
foreach ($script in $profileScripts) {
    $contents = Get-Content -LiteralPath (Join-Path $PSScriptRoot $script) -Raw
    if ($contents -notmatch "ValidateSet\('Api36','Api361','Api37','Play','Rooted'\)") { throw "$script does not accept Api37" }
}
$starter = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Start-Emulator.ps1') -Raw
if ($starter -notmatch 'function Update-LaunchedProcessTree' -or $starter -notmatch 'function Stop-LaunchedProcessTree') { throw 'Starter does not track its launched process tree' }
if ($starter -notmatch 'Get-CimInstance -ClassName Win32_Process' -or $starter -notmatch 'CreationDate') { throw 'Starter does not verify tracked process identity before cleanup' }
if ($starter -notmatch 'Stop-LaunchedProcessTree -RootProcess \$process -TrackedProcesses \$launchedProcesses') { throw 'Starter does not clean its tracked process tree on failure' }
if ($starter -match 'taskkill\.exe.*\/T' -or $starter -match 'Stop-Process -Id \$process\.Id') { throw 'Starter must not terminate unrecorded descendants or only the launcher' }
$starterAst = [Management.Automation.Language.Parser]::ParseInput($starter, [ref]$null, [ref]$null)
foreach ($functionAst in $starterAst.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in @('Test-ProcessCreationMatch','Update-LaunchedProcessTree','Stop-LaunchedProcessTree') }, $true)) {
    Invoke-Expression $functionAst.Extent.Text
}
$rootProcess = Microsoft.PowerShell.Management\Get-Process -Id $PID
$rootStartTime = $rootProcess.StartTime
$millisecondStartTime = $rootStartTime.AddTicks(-($rootStartTime.Ticks % [TimeSpan]::TicksPerMillisecond))
$subMillisecondRecord = [pscustomobject]@{ CreationDate = $millisecondStartTime.AddTicks(9) }
if (-not (Test-ProcessCreationMatch -ProcessRecord $subMillisecondRecord -StartTime $millisecondStartTime)) { throw 'Process identity rejected common-precision timestamps' }
$differentMillisecondRecord = [pscustomobject]@{ CreationDate = $millisecondStartTime.AddMilliseconds(1) }
if (Test-ProcessCreationMatch -ProcessRecord $differentMillisecondRecord -StartTime $millisecondStartTime) { throw 'Process identity accepted a different millisecond' }
$childProcessId = 42420
$childStartTime = $rootStartTime.AddSeconds(1)
$script:mockCimRows = @(
    [pscustomobject]@{ ProcessId = $PID; ParentProcessId = 0; CreationDate = $rootStartTime },
    [pscustomobject]@{ ProcessId = $childProcessId; ParentProcessId = $PID; CreationDate = $childStartTime }
)
function Get-CimInstance {
    param([string]$ClassName, [string]$Filter)
    if ($Filter -match 'ProcessId = (\d+)') { return $script:mockCimRows | Where-Object { $_.ProcessId -eq [int]$Matches[1] } }
    return $script:mockCimRows
}
$trackedProcesses = @{}
Update-LaunchedProcessTree -RootProcess $rootProcess -TrackedProcesses $trackedProcesses
if (-not @($trackedProcesses.Values | Where-Object { $_.ProcessId -eq $childProcessId -and $_.Depth -eq 1 })) { throw 'Process-tree tracking did not record the launched child' }
$script:mockCimRows[1].CreationDate = $rootStartTime.AddSeconds(-1)
$olderChild = @{}
Update-LaunchedProcessTree -RootProcess $rootProcess -TrackedProcesses $olderChild
if (@($olderChild.Values | Where-Object { $_.ProcessId -eq $childProcessId })) { throw 'Process-tree tracking accepted a child older than its parent' }
$script:mockCimRows[1].CreationDate = $childStartTime
$script:mockCimRows[0].CreationDate = $rootStartTime.AddSeconds(-1)
$reusedRoot = @{}
Update-LaunchedProcessTree -RootProcess $rootProcess -TrackedProcesses $reusedRoot
if ($reusedRoot.Count -ne 0) { throw 'Process-tree tracking trusted a reused launcher PID' }
$script:mockCimRows[0].CreationDate = $rootStartTime
$script:stoppedProcessIds = @()
function Get-Process { param([int]$Id) return $rootProcess }
function Stop-Process { param([System.Diagnostics.Process]$InputObject) $script:stoppedProcessIds += $InputObject.Id }
$cleanupProcesses = @{ child = [pscustomobject]@{ ProcessId = $PID; CreationDate = $rootStartTime; Depth = 1 } }
Stop-LaunchedProcessTree -RootProcess $rootProcess -TrackedProcesses $cleanupProcesses
if ($script:stoppedProcessIds.Count -ne 2) { throw 'Tracked child cleanup did not use validated process handles' }
$script:stoppedProcessIds = @()
$cleanupProcesses.child.CreationDate = $rootStartTime.AddSeconds(-1)
Stop-LaunchedProcessTree -RootProcess $rootProcess -TrackedProcesses $cleanupProcesses
if ($script:stoppedProcessIds.Count -ne 1) { throw 'Tracked child cleanup accepted a reused PID' }
Remove-Item function:Get-CimInstance, function:Get-Process, function:Stop-Process
$magisk = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Install-Magisk.ps1') -Raw
if ($magisk -notmatch 'Get-LabProfile Rooted' -or $magisk -notmatch 'Magisk setup is restricted to the owned rooted profile') { throw 'Magisk installer is not restricted to the rooted profile' }
$legacy = Get-LabProfile Play
if ($legacy.Avd -ne 'baseline' -or $legacy.Port -ne 5554) { throw 'Legacy profile mismatch' }
function Invoke-LabAdb { return "wrong-avd`nOK" }
$rejected = $false
try { Assert-LabAvd $clean } catch { $rejected = $true }
if (-not $rejected) { throw 'Wrong AVD was not rejected' }
function Invoke-LabAdb { return "poke_api36_test`nOK" }
Assert-LabAvd $clean
Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' | ForEach-Object {
    $tokens = $null; $errors = $null
    [void][Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
}
Write-Host 'PASS: profiles, stable ports, wrong-AVD protection, PowerShell syntax'
