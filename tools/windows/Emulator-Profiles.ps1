function Get-LabProfile {
    param([ValidateSet('Api36','Play','Rooted')][string]$Profile = 'Api36')
    $profiles = @{
        Api36 = @{ Avd='poke_api36_test'; Api='36'; Release='16'; Port=5556; Variant='google_apis_playstore'; PlayStore=$true }
        Play = @{ Avd='baseline'; Api='34'; Release='14'; Port=5554; Variant='google_apis_playstore'; PlayStore=$true }
        Rooted = @{ Avd='baseline-rooted'; Api='34'; Release='14'; Port=5554; Variant='google_apis'; PlayStore=$false }
    }
    $result = $profiles[$Profile].Clone()
    $result.Serial = "emulator-$($result.Port)"
    $result.Image = "system-images;android-$($result.Api);$($result.Variant);x86_64"
    return $result
}

function Invoke-LabAdb {
    param([string[]]$Arguments, [ValidateRange(1,600)][int]$TimeoutSeconds = 30)
    $adbPath = Join-Path $env:ANDROID_HOME 'platform-tools/adb.exe'
    if (-not (Test-Path -LiteralPath $adbPath)) { throw 'ADB is missing. Run tools/windows/Bootstrap-Android.ps1 -WithEmulator.' }
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $adbPath
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.Arguments = ($Arguments | ForEach-Object { '"' + ($_ -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"' }) -join ' '
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            throw "ADB timed out after $TimeoutSeconds seconds. Check the device and debugging authorization."
        }
        $output = $stdout.GetAwaiter().GetResult()
        $errorOutput = $stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw "ADB failed: $errorOutput $output" }
        return $output.Trim()
    } finally { $process.Dispose() }
}

function Assert-LabAvd {
    param([hashtable]$Selected)
    $name = Invoke-LabAdb @('-s',$Selected.Serial,'emu','avd','name')
    if (($name -split '\r?\n')[0].Trim() -ne $Selected.Avd) {
        throw "Port $($Selected.Port) belongs to another AVD. Expected $($Selected.Avd); no changes made."
    }
}
