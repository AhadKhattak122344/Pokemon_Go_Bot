[CmdletBinding()]
param(
    [string]$Device,
    [string]$AssetsDirectory,
    [ValidateSet('PlayIntegrityFix','UniversalSafetyNetFix')]
    [string]$IntegrityModule = 'PlayIntegrityFix',
    [switch]$SkipMagiskApp,
    [switch]$NoReboot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'adb-common.ps1')

if (-not $AssetsDirectory) { $AssetsDirectory = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets' }
if (-not (Test-Path -LiteralPath $AssetsDirectory -PathType Container)) { throw "Assets directory not found: $AssetsDirectory" }

function Get-UniqueAsset {
    param([string]$Pattern)
    $found = @(Get-ChildItem -LiteralPath $AssetsDirectory -File -Filter $Pattern)
    if ($found.Count -ne 1) {
        throw "Expected exactly one asset matching '$Pattern', found $($found.Count). Use a dedicated assets directory with the intended versions."
    }
    if ($found[0].Name -notmatch '^[A-Za-z0-9._-]+$') { throw "Unsupported asset filename: $($found[0].Name)" }
    return $found[0]
}

# Preflight all local inputs before making changes to the device. Never install
# arbitrary ZIPs (including Houdini source bundles) from the assets directory.
$patterns = @('zygisk-next-*.zip', 'shamiko-*.zip')
$patterns += if ($IntegrityModule -eq 'PlayIntegrityFix') { 'play-integrity-fix-*.zip' } else { 'universal-safetynet-fix-*.zip' }
$modules = @($patterns | ForEach-Object { Get-UniqueAsset $_ })
$apk = if (-not $SkipMagiskApp) { Get-UniqueAsset 'magisk-*.apk' } else { $null }
$selectedAssets = @($modules)
if ($apk) { $selectedAssets += $apk }

$manifestPath = Join-Path $AssetsDirectory 'manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'manifest.json is missing. Run scripts/download-assets.ps1 to prepare and hash the selected assets.'
}
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
foreach ($asset in $selectedAssets) {
    $entry = @($manifest.assets | Where-Object { $_.file -ceq $asset.Name })
    if ($entry.Count -ne 1 -or $entry[0].sha256 -notmatch '^[0-9a-fA-F]{64}$') {
        throw "A unique SHA-256 manifest entry is required for $($asset.Name)."
    }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $asset.FullName).Hash -ine $entry[0].sha256) {
        throw "SHA-256 mismatch for $($asset.Name). Download the asset again."
    }
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($module in $modules) {
    $archive = [IO.Compression.ZipFile]::OpenRead($module.FullName)
    try {
        if (-not $archive.GetEntry('module.prop')) { throw "$($module.Name) is not a Magisk module ZIP (module.prop missing)." }
    } finally { $archive.Dispose() }
}

$adb = Resolve-FleetAdb
$target = @(Get-FleetAdbTarget -Adb $adb -Device $Device)
$rootCheck = Invoke-FleetRoot -Adb $adb -Target $target -Command 'id' -Description 'Root authorization check'
if ($rootCheck -notmatch 'uid=0\(root\)') { throw "Root is not authorized. Grant shell root in Magisk and retry. Output: $rootCheck" }
$version = Invoke-FleetRoot -Adb $adb -Target $target -Command 'magisk -v' -Description 'Magisk CLI check'
if (-not $version.Trim()) { throw 'Magisk CLI did not report a version. Installing the manager APK does not establish root.' }

if ($apk) {
    & $adb @target install -r $apk.FullName | Write-Host
    if ($LASTEXITCODE -ne 0) { throw 'Magisk APK installation failed.' }
}

foreach ($module in $modules) {
    $remote = "/data/local/tmp/fleet-$([guid]::NewGuid().ToString('N')).zip"
    Write-Host "Installing $($module.Name)"
    & $adb @target push $module.FullName $remote | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "ADB push failed for $($module.Name)." }
    try {
        $result = Invoke-FleetRoot -Adb $adb -Target $target -Command "magisk --install-module '$remote'" -Description "Installation of $($module.Name)"
        Write-Host $result
    } finally {
        & $adb @target shell rm -f $remote | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning "Unable to remove temporary device file: $remote" }
    }
}

Write-Host 'Module installation commands completed. Runtime compatibility and integrity verdicts remain unverified.'
if (-not $NoReboot) {
    Write-Host 'Rebooting device to activate modules.'
    & $adb @target reboot
    if ($LASTEXITCODE -ne 0) { throw 'ADB reboot failed.' }
} else { Write-Warning 'A reboot is required before checking module activation.' }
