$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/Emulator-Profiles.ps1"
$clean = Get-LabProfile Api36
if ($clean.Avd -ne 'poke_api36_test' -or $clean.Port -ne 5556 -or $clean.Api -ne '36') { throw 'Clean profile mismatch' }
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
