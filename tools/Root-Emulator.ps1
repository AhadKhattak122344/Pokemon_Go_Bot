param(
    [ValidateSet('status','enable','disable','self-test')]
    [string]$Action = 'status'
)
. "$PSScriptRoot/Android-Environment.ps1"
$python = Join-Path $WorkspaceTools 'python/python.exe'
if (!(Test-Path $python)) { $python = Join-Path $WorkspaceRoot '.venv/Scripts/python.exe' }
if (!(Test-Path $python)) { throw 'Python runtime missing. See tools/OPTIONAL-SETUP.md.' }
$report = Join-Path $WorkspaceRoot ("artifacts/root-{0}-{1}.json" -f $Action,[guid]::NewGuid().ToString('N'))
Push-Location $WorkspaceRoot
try {
    & $python -m orchestrator.cli --config cloud-lab/config/default.yaml root $Action --out $report
    if ($LASTEXITCODE -ne 0) { throw "Root command failed. See $report" }
} finally {
    Pop-Location
}

