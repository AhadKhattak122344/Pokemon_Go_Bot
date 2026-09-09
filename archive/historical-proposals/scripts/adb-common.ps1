# Shared ADB helpers. Dot-source from the installation/configuration scripts.
function Resolve-FleetAdb {
    $command = Get-Command adb -CommandType Application -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $local = Join-Path (Split-Path $PSScriptRoot -Parent) '.tools\android-sdk\platform-tools\adb.exe'
    if (Test-Path -LiteralPath $local -PathType Leaf) { return $local }
    throw 'adb was not found on PATH or in .tools/android-sdk/platform-tools. Run tools/Bootstrap-Android.ps1.'
}

function Get-FleetAdbTarget {
    param([string]$Adb, [string]$Device)
    if ($Device) {
        if ($Device -match '^(?:[^:]+|\[[^\]]+\]):\d+$') {
            $connection = (& $Adb connect $Device 2>&1) -join "`n"
            if ($LASTEXITCODE -ne 0 -or $connection -match '(?i)failed|unable|cannot') {
                throw "ADB connection to $Device failed: $connection"
            }
        }
    } else {
        $listing = @(& $Adb devices)
        if ($LASTEXITCODE -ne 0) { throw 'Unable to list ADB devices.' }
        $connected = @($listing | Select-String "`tdevice\s*$" | ForEach-Object { ($_.Line -split "`t")[0] })
        if ($connected.Count -ne 1) {
            throw "Specify -Device. Expected exactly one authorized ADB device, found $($connected.Count)."
        }
        $Device = $connected[0]
    }
    $state = (& $Adb -s $Device get-state 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0 -or $state.Trim() -ne 'device') {
        throw "The selected ADB device is not ready or authorized: $state"
    }
    return @('-s', $Device)
}

function Invoke-FleetRoot {
    param([string]$Adb, [string[]]$Target, [string]$Command, [string]$Description = 'Root command')
    # ADB joins shell arguments, and Windows PowerShell also parses native quotes.
    # Transport a UTF-8/LF script as base64 so neither layer can reinterpret it.
    $scriptText = "set -e`n" + $Command.Replace("`r`n", "`n") + "`n"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($scriptText))
    $output = (& $Adb @Target shell "printf %s $encoded | base64 -d | su -c sh" 2>&1) -join "`n"
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "$Description failed (exit $exitCode): $output" }
    return $output
}

function Write-FleetUnixText {
    param([string]$Path, [string]$Text)
    $unixText = $Text.Replace("`r`n", "`n").TrimEnd("`r", "`n") + "`n"
    [IO.File]::WriteAllText($Path, $unixText, [Text.UTF8Encoding]::new($false))
}
