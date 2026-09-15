<#
.SYNOPSIS
  Runs one recorded create/boot/display/game/stop pass for each selected fleet AVD.
  A failed case is recorded and testing continues to the next case. Login remains unverified.
#>
[CmdletBinding()]
param(
    [string]$Matrix,
    [string[]]$Only,
    [string]$ApkDir,
    [ValidateRange(1,3000)][int]$TimeoutSeconds = 180,
    [ValidateRange(1,600)][int]$ObserveSeconds = 30,
    [switch]$InstallImages,
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Fleet-Common.ps1')
$repo = Get-FleetRepoRoot
if (-not $Matrix) { $Matrix = Join-Path $repo 'config/fleet-matrix.json' }
if (-not $ApkDir) { $ApkDir = Join-Path $repo 'artifacts/pgo-apk' }
$Matrix = (Resolve-Path -LiteralPath $Matrix).Path
$targets = @(Select-FleetAvds -Matrix (Get-FleetMatrix -Path $Matrix) -Only $Only)
if ($DryRun) {
    [pscustomobject]@{ action='sweep'; matrix=$Matrix; apkDir=$ApkDir; names=@($targets.name); stages=@('create','boot/display','game observation','stop'); authentication='unverified' } | ConvertTo-Json -Depth 5
    return
}
if (-not (Test-Path -LiteralPath $ApkDir) -or -not @(Get-ChildItem -LiteralPath $ApkDir -Filter '*.apk').Count) { throw "APK set missing: $ApkDir" }
$ApkDir = (Resolve-Path -LiteralPath $ApkDir).Path
$outDir = New-FleetArtifactDir -Name 'fleet-sweep'
Copy-Item -LiteralPath $Matrix -Destination (Join-Path $outDir 'matrix.json')
$sdk = Get-FleetTools
$psExe = Join-Path $PSHOME 'powershell.exe'
$results = @()
Write-Host "Automated fleet pass: $outDir"

function Invoke-TestStage {
    param([string]$ScriptName, [string[]]$StageArgs, [string]$LogPath, [int]$Limit = 600)
    $commandArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot $ScriptName)) + $StageArgs
    $commandLine = ((@($psExe) + $commandArgs) | ForEach-Object { ConvertTo-FleetNativeArgument $_ }) -join ' '
    Set-Content -LiteralPath ($LogPath + '.command.txt') -Value $commandLine
    $stage = Invoke-FleetNative -Exe $psExe -Arguments $commandArgs -TimeoutSeconds $Limit
    Set-Content -LiteralPath $LogPath -Value $stage.Output
    Set-Content -LiteralPath ($LogPath + '.exit.txt') -Value $stage.ExitCode
    Write-Host "$ScriptName exited $($stage.ExitCode)"
    return $stage
}

foreach ($target in $targets) {
    $caseDir = Join-Path $outDir $target.name
    New-Item -ItemType Directory -Path $caseDir | Out-Null
    $bootSummary = Join-Path $caseDir 'boot.json'
    $case = [ordered]@{ name=$target.name; serial=$target.serial; image=$target.image; gpu=$target.gpu; features=@($target.features); status='pending'; createExit=$null; startExit=$null; gameExit=$null; stopExit=$null; boot=@(); game=@(); authentication='unverified'; artifacts=$caseDir; error='' }
    $ownsLaunch = $false
    try {
        Write-Host "Testing $($target.name)"
        $createArgs = @('-Matrix',$Matrix,'-Only',$target.name)
        if (-not $InstallImages) { $createArgs += '-SkipInstall' }
        $created = Invoke-TestStage 'New-FleetAvds.ps1' $createArgs (Join-Path $caseDir 'create.log') 3600
        $case.createExit = $created.ExitCode
        if ($created.ExitCode -ne 0) { $case.status='create_failed'; continue }
        $started = Invoke-TestStage 'Start-Fleet.ps1' @('-Matrix',$Matrix,'-Only',$target.name,'-SummaryPath',$bootSummary,'-MaxParallel','1','-ColdBoot','-TimeoutSeconds',"$TimeoutSeconds",'-SettleSeconds','15') (Join-Path $caseDir 'start.log') ($TimeoutSeconds + 300)
        $case.startExit = $started.ExitCode
        if (Test-Path -LiteralPath $bootSummary) {
            $case.boot = @(Read-FleetJsonRows -Path $bootSummary)
            $ownsLaunch = @($case.boot | Where-Object { $_.PSObject.Properties.Name -contains 'pid' -and $_.pid -gt 0 }).Count -gt 0
        }
        if ($started.ExitCode -ne 0 -or @($case.boot | Where-Object status -eq 'display_ok').Count -ne 1) { $case.status='display_not_ready'; continue }
        $latestGame = Join-Path $caseDir 'game.json'
        $game = Invoke-TestStage 'Install-FleetGame.ps1' @('-Summary',$bootSummary,'-ResultPath',$latestGame,'-ApkDir',$ApkDir,'-ObserveSeconds',"$ObserveSeconds",'-SampleSeconds','10') (Join-Path $caseDir 'game.log') ($ObserveSeconds + 600)
        $case.gameExit = $game.ExitCode
        if (Test-Path -LiteralPath $latestGame) {
            $case.game = @(Read-FleetJsonRows -Path $latestGame | Where-Object serial -eq $target.serial)
        }
        $case.status = if ($game.ExitCode -eq 0) { 'launch_observed' } else { 'game_test_failed' }
    } catch {
        $case.status='harness_error'; $case.error=$_.Exception.Message
    } finally {
        if ($ownsLaunch) {
            try {
                $stopped = Invoke-TestStage 'Stop-Fleet.ps1' @('-Matrix',$Matrix,'-Only',$target.name) (Join-Path $caseDir 'stop.log') 90
                $case.stopExit = $stopped.ExitCode
                $deadline = (Get-Date).AddSeconds(20)
                do {
                    $deviceState = Get-FleetAdbState -Adb $sdk.Adb -Serial $target.serial -TimeoutSeconds 5
                    if ($deviceState -notin @('device','offline','unauthorized')) { break }
                    Start-Sleep -Seconds 1
                } while ((Get-Date) -lt $deadline)
                if ($deviceState -in @('device','offline','unauthorized')) { $case.stopExit=1; $case.error += ' Emulator still attached after stop.'; $case.status='cleanup_failed' }
            } catch { $case.stopExit=1; $case.error += $_.Exception.Message; $case.status='cleanup_failed' }
        }
        $results += [pscustomobject]$case
        ConvertTo-Json -InputObject @($results) -Depth 12 | Set-Content (Join-Path $outDir 'summary.json')
        Write-Host "$($target.name): $($case.status)"
    }
}
ConvertTo-Json -InputObject @($results) -Depth 12 | Set-Content (Join-Path $repo 'artifacts/fleet-sweep-latest.json')
$results | Select-Object name,status,createExit,startExit,gameExit,stopExit | Format-Table -AutoSize
Write-Host "Evidence: $outDir"
if (@($results | Where-Object status -ne 'launch_observed').Count) { exit 1 }
