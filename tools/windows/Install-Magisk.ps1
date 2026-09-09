param([string]$Serial = 'emulator-5554')

. "$PSScriptRoot/Android-Environment.ps1"
$python = Join-Path $WorkspaceTools 'python/python.exe'
if (!(Test-Path $python)) { $python = Join-Path $WorkspaceRoot '.venv/Scripts/python.exe' }
if (!(Test-Path $python)) {
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if ($systemPython) { $python = $systemPython.Source }
}
if (!(Test-Path $python)) { throw 'Python runtime missing. See tools/windows/OPTIONAL-SETUP.md.' }
& $python "$PSScriptRoot/install_magisk.py" --serial $Serial
if ($LASTEXITCODE -ne 0) { throw 'Magisk emulator setup failed. See the output above.' }
