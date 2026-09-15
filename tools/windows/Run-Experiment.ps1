param(
    [ValidateSet('Api36','Api361','Api37','Play','Rooted')][string]$Profile = 'Api36',
    [string]$Package = 'com.nianticlabs.pokemongo',
    [string]$Config = '',
    [string]$Apk = '',
    [switch]$Launch,
    [switch]$Login
)
. "$PSScriptRoot/Android-Environment.ps1"
. "$PSScriptRoot/Emulator-Profiles.ps1"
$selected = Get-LabProfile $Profile
Assert-LabAvd $selected
if (-not $Config) {
    $Config = if ($Profile -eq 'Api36') { 'config/pokemongo.yaml' } elseif ($Profile -eq 'Api361') { 'config/pokemongo-api361.yaml' } elseif ($Profile -eq 'Api37') { 'config/pokemongo-api37.yaml' } else { 'config/default.yaml' }
}
$out = Join-Path $WorkspaceRoot ("artifacts/experiment-{0}-{1}" -f $selected.Avd, [guid]::NewGuid().ToString('N'))
$labArgs = @('--config', $Config, 'experiment', '--package', $Package, '--out', $out)
if ($Launch) { $labArgs += '--launch' }
if ($Login) { $labArgs += '--login' }
if ($Apk) { $labArgs += @('--apk', $Apk) }
Push-Location $WorkspaceRoot
try {
    uv run lab @labArgs
    if ($LASTEXITCODE -ne 0) { throw "lab experiment failed; inspect $out" }
} finally { Pop-Location }
Write-Host "Experiment artifacts: $out"
