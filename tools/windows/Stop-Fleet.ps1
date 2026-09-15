<#
.SYNOPSIS
  Stops fleet emulators by console port, only after confirming the running AVD name matches the matrix.
#>
[CmdletBinding()]
param(
    [string]$Matrix,
    [string[]]$Only,
    [switch]$DryRun,
    [string]$SdkRoot, [string]$JavaHome, [string]$AvdHome
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Fleet-Common.ps1')
if (-not $Matrix) { $Matrix = Join-Path (Get-FleetRepoRoot) 'config/fleet-matrix.json' }
$targets = @(Select-FleetAvds -Matrix (Get-FleetMatrix -Path $Matrix) -Only $Only -IncludeDisabled)
if ($DryRun) { [pscustomobject]@{ action='stop'; matrix=$Matrix; names=@($targets.name) } | ConvertTo-Json -Depth 4; return }

$tools   = Get-FleetTools -SdkRoot $SdkRoot -JavaHome $JavaHome -AvdHome $AvdHome

foreach ($a in $targets) {
    $msg = Stop-FleetEmulator -Adb $tools.Adb -Serial $a.serial -ExpectedName $a.name
    Write-Host ("{0} ({1}): {2}" -f $a.name, $a.serial, $msg)
}
