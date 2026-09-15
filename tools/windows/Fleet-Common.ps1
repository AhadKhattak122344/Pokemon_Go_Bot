# Shared helpers for the Fleet-*.ps1 scripts. Dot-source only; do not run directly.
Set-StrictMode -Version Latest

function Get-FleetRepoRoot { (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }

function Read-FleetJsonRows {
    param([Parameter(Mandatory)][string]$Path)
    # Windows PowerShell 5.1 emits a JSON array as one pipeline object.
    # Explicit iteration keeps zero/one/many reports consistently enumerable.
    $parsed = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
    foreach ($row in $parsed) { $row }
}

function ConvertTo-FleetNativeArgument {
    param([AllowEmptyString()][string]$Value)
    if ($Value.Length -eq 0) { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    $quoted = '"'; $slashes = 0
    foreach ($character in $Value.ToCharArray()) {
        if ($character -eq '\') { $slashes++; continue }
        if ($character -eq '"') { $quoted += ('\' * (($slashes * 2) + 1)) + '"'; $slashes = 0; continue }
        if ($slashes) { $quoted += '\' * $slashes; $slashes = 0 }
        $quoted += $character
    }
    if ($slashes) { $quoted += '\' * ($slashes * 2) }
    return $quoted + '"'
}

function Invoke-FleetNative {
    # No shell: arguments remain data, output is captured, and a hung adb/sdk call is bounded.
    param(
        [Parameter(Mandatory)][string]$Exe,
        [string[]]$Arguments = @(),
        [string]$StdIn,
        [ValidateRange(1, 3600)][int]$TimeoutSeconds = 60
    )
    $info = New-Object System.Diagnostics.ProcessStartInfo
    if ([IO.Path]::GetExtension($Exe) -eq '.bat') {
        $manager = [IO.Path]::GetFileNameWithoutExtension($Exe)
        if ($manager -notin @('sdkmanager','avdmanager')) { throw "Unsupported batch tool: $Exe" }
        $toolHome = Split-Path (Split-Path $Exe -Parent) -Parent
        $mainClass = if ($manager -eq 'avdmanager') { 'com.android.sdklib.tool.AvdManagerCli' } else { 'com.android.sdklib.tool.sdkmanager.SdkManagerCli' }
        $toolsProperty = if ($manager -eq 'avdmanager') { 'com.android.sdkmanager.toolsdir' } else { 'com.android.sdklib.toolsdir' }
        $Arguments = @("-D$toolsProperty=$toolHome", '-classpath', (Join-Path $toolHome "lib/$manager-classpath.jar"), $mainClass) + $Arguments
        $Exe = Join-Path $env:JAVA_HOME 'bin/java.exe'
    }
    $info.FileName = $Exe
    $info.Arguments = (($Arguments | ForEach-Object { ConvertTo-FleetNativeArgument ([string]$_) }) -join ' ')
    $info.UseShellExecute = $false; $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
    $info.RedirectStandardInput = $PSBoundParameters.ContainsKey('StdIn')
    $process = New-Object System.Diagnostics.Process; $process.StartInfo = $info
    try {
        if (-not $process.Start()) { throw "Could not start $Exe" }
        $stdout = $process.StandardOutput.ReadToEndAsync(); $stderr = $process.StandardError.ReadToEndAsync()
        if ($info.RedirectStandardInput) { $process.StandardInput.Write($StdIn); $process.StandardInput.Close() }
        $timedOut = -not $process.WaitForExit($TimeoutSeconds * 1000)
        if ($timedOut) { try { $process.Kill() } catch { }; [void]$process.WaitForExit(3000) }
        $outText = if ($stdout.Wait(3000)) { $stdout.Result } else { '[stdout capture incomplete]' }
        $errText = if ($stderr.Wait(3000)) { $stderr.Result } else { '[stderr capture incomplete]' }
        if ($timedOut) { $errText += "`nTimed out after $TimeoutSeconds seconds" }
        $nativeExit = if ($timedOut) { -1 } else { $process.ExitCode }
        [pscustomobject]@{ ExitCode=$nativeExit; Output=(($outText + "`n" + $errText).Trim()); TimedOut=$timedOut }
    } finally { $process.Dispose() }
}

function Find-FleetSdk {
    param([string]$SdkRoot)
    $candidates = @()
    foreach ($candidate in @($SdkRoot, $env:ANDROID_SDK_ROOT, $env:ANDROID_HOME)) { if ($candidate) { $candidates += $candidate } }
    $tools = Join-Path (Get-FleetRepoRoot) '.tools'
    if (Test-Path -LiteralPath $tools) {
        $candidates += $tools
        $candidates += (Get-ChildItem -LiteralPath $tools -Directory -Recurse -Depth 2 -ErrorAction SilentlyContinue | ForEach-Object FullName)
    }
    foreach ($candidate in $candidates) {
        if ((Test-Path -LiteralPath (Join-Path $candidate 'platform-tools\adb.exe')) -and (Test-Path -LiteralPath (Join-Path $candidate 'emulator\emulator.exe'))) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw 'Android SDK (platform-tools + emulator) not found. Pass -SdkRoot or set ANDROID_SDK_ROOT.'
}

function Get-FleetTools {
    param([string]$SdkRoot, [string]$JavaHome, [string]$AvdHome, [switch]$RequireManagers)
    $sdk = Find-FleetSdk -SdkRoot $SdkRoot
    $cmdline = Join-Path $sdk 'cmdline-tools'
    $avdmanager = Get-ChildItem -LiteralPath $cmdline -Recurse -Filter 'avdmanager.bat' -ErrorAction SilentlyContinue | Select-Object -First 1
    $sdkmanager = Get-ChildItem -LiteralPath $cmdline -Recurse -Filter 'sdkmanager.bat' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($RequireManagers -and (-not $avdmanager -or -not $sdkmanager)) { throw "cmdline-tools not found under $cmdline" }
    $java = $null
    foreach ($candidate in @($JavaHome, $env:JAVA_HOME)) { if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate 'bin\java.exe'))) { $java = $candidate; break } }
    if (-not $java) {
        $localTools = Join-Path (Get-FleetRepoRoot) '.tools'
        $foundJava = Get-ChildItem -LiteralPath $localTools -Recurse -Filter 'java.exe' -ErrorAction SilentlyContinue | Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
        if ($foundJava) { $java = $foundJava.Directory.Parent.FullName }
    }
    if ($RequireManagers -and -not $java) { throw 'JDK not found. Pass -JavaHome or set JAVA_HOME.' }
    $androidUserHome = Join-Path (Get-FleetRepoRoot) '.tools\android-user'
    $avdHomeResolved = if ($AvdHome) { $AvdHome } elseif ($env:ANDROID_AVD_HOME) { $env:ANDROID_AVD_HOME } else { Join-Path $androidUserHome 'avd' }
    New-Item -ItemType Directory -Path $androidUserHome -Force | Out-Null
    New-Item -ItemType Directory -Path $avdHomeResolved -Force | Out-Null
    $env:ANDROID_SDK_ROOT = $sdk; $env:ANDROID_HOME = $sdk
    if ($java) { $env:JAVA_HOME = $java }
    $env:ANDROID_USER_HOME = $androidUserHome; $env:ANDROID_AVD_HOME = $avdHomeResolved
    [pscustomobject]@{ Sdk=$sdk; Adb=(Join-Path $sdk 'platform-tools\adb.exe'); Emulator=(Join-Path $sdk 'emulator\emulator.exe'); AvdManager=$(if ($avdmanager) { $avdmanager.FullName } else { $null }); SdkManager=$(if ($sdkmanager) { $sdkmanager.FullName } else { $null }); JavaHome=$java; AndroidUserHome=$androidUserHome; AvdHome=$avdHomeResolved }
}

function Get-FleetMatrix {
    param([Parameter(Mandatory)][string]$Path)
    $raw = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
    if ($null -eq $raw.avds -or @($raw.avds).Count -eq 0) { throw 'Fleet matrix must contain a non-empty avds array.' }
    $defaults = @{}
    if ($raw.PSObject.Properties.Name -contains 'defaults') { foreach ($property in $raw.defaults.PSObject.Properties) { $defaults[$property.Name] = $property.Value } }
    $avds = @(); $names = @{}; $ports = @{}
    foreach ($avd in @($raw.avds)) {
        foreach ($key in $defaults.Keys) { if (-not ($avd.PSObject.Properties.Name -contains $key)) { $avd | Add-Member -NotePropertyName $key -NotePropertyValue $defaults[$key] } }
        foreach ($field in @('name','port','image','device','displayName')) { if (-not ($avd.PSObject.Properties.Name -contains $field) -or $null -eq $avd.$field -or [string]$avd.$field -eq '') { throw "Fleet matrix AVD is missing required '$field'." } }
        $name = [string]$avd.name
        if ($name -notmatch '^[A-Za-z0-9_.-]+$') { throw "Invalid AVD name '$name'." }
        if ($names.ContainsKey($name.ToLowerInvariant())) { throw "Duplicate AVD name '$name'." }; $names[$name.ToLowerInvariant()] = $true
        $port = 0
        if (-not [int]::TryParse(([string]$avd.port), [ref]$port) -or $port -lt 5554 -or $port -gt 5682 -or ($port % 2 -ne 0)) { throw "Invalid emulator console port '$($avd.port)' for '$name'." }
        if ($ports.ContainsKey($port)) { throw "Duplicate console port '$port'." }; $ports[$port] = $true
        if (@($avd.device).Count -eq 0) { throw "AVD '$name' needs at least one device profile." }
        $avd | Add-Member -NotePropertyName serial -NotePropertyValue ("emulator-{0}" -f $port) -Force
        $avds += $avd
    }
    [pscustomobject]@{ avds = $avds }
}

function Select-FleetAvds {
    param($Matrix, [string[]]$Only, [switch]$IncludeDisabled)
    $selected = @($Matrix.avds | Where-Object { ($IncludeDisabled -or $_.enabled) -and ((-not $Only) -or ($Only -contains $_.name)) })
    if ($selected.Count -eq 0) { throw 'No AVDs match the selection (check enabled or -Only names).' }
    return $selected
}

function Get-FleetAdbState {
    param([string]$Adb, [string]$Serial, [ValidateRange(1,300)][int]$TimeoutSeconds = 15)
    (Invoke-FleetNative -Exe $Adb -Arguments @('-s',$Serial,'get-state') -TimeoutSeconds $TimeoutSeconds).Output
}

function Get-FleetAvdName {
    param([string]$Adb, [string]$Serial, [ValidateRange(1,300)][int]$TimeoutSeconds = 15)
    $result = Invoke-FleetNative -Exe $Adb -Arguments @('-s',$Serial,'emu','avd','name') -TimeoutSeconds $TimeoutSeconds
    if ($result.ExitCode -ne 0) { return '' }
    $line = $result.Output -split "`n" | Where-Object { $_ -and $_ -notmatch '^OK$' } | Select-Object -First 1
    if ($line) { $line.Trim() } else { '' }
}

function Test-FleetProcessCreationMatch {
    param([object]$ProcessRecord, [datetime]$StartTime)
    # Win32_Process exposes microsecond-oriented CIM timestamps while
    # System.Diagnostics.Process exposes a .NET timestamp. Compare their common
    # millisecond precision rather than rejecting the same process over sub-ms
    # conversion noise.
    # Formatting truncates fractional seconds without converting large tick
    # counts to doubles (which can round across a millisecond boundary).
    $recordMilliseconds = $ProcessRecord.CreationDate.ToUniversalTime().ToString('yyyyMMddHHmmssfff')
    $startMilliseconds = $StartTime.ToUniversalTime().ToString('yyyyMMddHHmmssfff')
    return $recordMilliseconds -eq $startMilliseconds
}

function Update-FleetTrackedProcessTree {
    param(
        [System.Diagnostics.Process]$OwnProcess,
        [hashtable]$TrackedProcesses
    )

    # Record descendants while their parent relationship is still available. The
    # held launcher handle and its creation time must still identify the root
    # before any parent-PID edges are trusted.
    try {
        if ($OwnProcess.HasExited) { return }
        $rootStartTime = $OwnProcess.StartTime
    } catch { return }
    $allProcesses = @(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop)
    $rootRecord = $allProcesses | Where-Object { [int]$_.ProcessId -eq [int]$OwnProcess.Id } | Select-Object -First 1
    if ($null -eq $rootRecord -or -not (Test-FleetProcessCreationMatch -ProcessRecord $rootRecord -StartTime $rootStartTime)) { return }
    $key = "$($rootRecord.ProcessId):$($rootRecord.CreationDate.ToUniversalTime().Ticks)"
    $TrackedProcesses[$key] = [pscustomobject]@{ ProcessId = [int]$rootRecord.ProcessId; CreationDate = $rootRecord.CreationDate; Depth = 0 }
    $frontier = @($rootRecord)
    $seen = New-Object 'System.Collections.Generic.HashSet[int]'
    [void]$seen.Add([int]$OwnProcess.Id)
    $depth = 0
    while ($frontier.Count -gt 0) {
        $children = @(
            foreach ($parent in $frontier) {
                foreach ($candidate in $allProcesses) {
                    if ([int]$candidate.ParentProcessId -eq [int]$parent.ProcessId -and
                        $candidate.CreationDate -ge $parent.CreationDate -and
                        $seen.Add([int]$candidate.ProcessId)) {
                        $candidate
                    }
                }
            }
        )
        $depth++
        foreach ($child in $children) {
            $key = "$($child.ProcessId):$($child.CreationDate.ToUniversalTime().Ticks)"
            $TrackedProcesses[$key] = [pscustomobject]@{ ProcessId = [int]$child.ProcessId; CreationDate = $child.CreationDate; Depth = $depth }
        }
        $frontier = $children
    }
}

function Stop-FleetTrackedProcessTree {
    param(
        [System.Diagnostics.Process]$OwnProcess,
        [hashtable]$TrackedProcesses
    )

    try { Update-FleetTrackedProcessTree -OwnProcess $OwnProcess -TrackedProcesses $TrackedProcesses } catch { }
    foreach ($record in @($TrackedProcesses.Values | Where-Object { $_.Depth -gt 0 } | Sort-Object Depth -Descending)) {
        try {
            $current = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($record.ProcessId)" -ErrorAction Stop
            $currentProcess = Get-Process -Id $record.ProcessId -ErrorAction Stop
            if ($null -ne $current -and [int]$currentProcess.Id -eq [int]$record.ProcessId -and
                (Test-FleetProcessCreationMatch -ProcessRecord $current -StartTime $record.CreationDate) -and
                (Test-FleetProcessCreationMatch -ProcessRecord $record -StartTime $currentProcess.StartTime)) {
                Stop-Process -InputObject $currentProcess -Force -ErrorAction SilentlyContinue
            }
        } catch { }
    }
    try {
        if (-not $OwnProcess.HasExited) { Stop-Process -InputObject $OwnProcess -Force -ErrorAction SilentlyContinue }
    } catch { }
}

function Wait-FleetBoot {
    param([string]$Adb, [string]$Serial, [ValidateRange(1,3600)][int]$TimeoutSeconds, [System.Diagnostics.Process]$OwnProcess, [hashtable]$TrackedProcesses)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($null -ne $OwnProcess -and $null -ne $TrackedProcesses) {
            Update-FleetTrackedProcessTree -OwnProcess $OwnProcess -TrackedProcesses $TrackedProcesses
            if ($OwnProcess.HasExited -and $TrackedProcesses.Count -le 1) { return $false }
        }
        if ((Get-FleetAdbState -Adb $Adb -Serial $Serial) -ceq 'device') {
            if ((Invoke-FleetNative -Exe $Adb -Arguments @('-s',$Serial,'shell','getprop','sys.boot_completed') -TimeoutSeconds 15).Output -ceq '1') { return $true }
        }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Save-FleetScreenshot {
    # Binary adb stdout capture avoids cmd.exe injection and PowerShell text transcoding.
    param([string]$Adb, [string]$Serial, [string]$Path, [ValidateRange(1,300)][int]$TimeoutSeconds = 30)
    $parent = Split-Path -Parent $Path; if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    if (Test-Path -LiteralPath $Path) { Remove-Item -LiteralPath $Path -Force }
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Adb; $info.Arguments = ((@('-s',$Serial,'exec-out','screencap','-p') | ForEach-Object { ConvertTo-FleetNativeArgument ([string]$_) }) -join ' ')
    $info.UseShellExecute = $false; $info.CreateNoWindow = $true; $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process; $process.StartInfo = $info
    if (-not $process.Start()) { $process.Dispose(); return $false }
    $stderr = $process.StandardError.ReadToEndAsync()
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $copy = $process.StandardOutput.BaseStream.CopyToAsync($stream)
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) { try { $process.Kill() } catch { }; [void]$copy.Wait(3000); return $false }
        if (-not $copy.Wait(3000) -or $process.ExitCode -ne 0) { return $false }
        if ($stderr.Wait(3000) -and $stderr.Result) { Set-Content -LiteralPath ($Path + '.stderr.txt') -Value $stderr.Result }
    } finally { $stream.Dispose(); $process.Dispose() }
    if (-not (Test-Path -LiteralPath $Path) -or (Get-Item -LiteralPath $Path).Length -lt 8) { return $false }
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ([BitConverter]::ToString($bytes,0,8) -ne '89-50-4E-47-0D-0A-1A-0A') { return $false }
    try {
        Add-Type -AssemblyName System.Drawing
        $png = [Drawing.Image]::FromFile([IO.Path]::GetFullPath($Path))
        try { return ($png.Width -gt 0 -and $png.Height -gt 0) } finally { $png.Dispose() }
    } catch { return $false }
}

function Save-FleetText {
    param([string]$Adb, [string]$Serial, [string[]]$AdbArgs, [string]$Path, [ValidateRange(1,300)][int]$TimeoutSeconds = 30)
    $result = Invoke-FleetNative -Exe $Adb -Arguments (@('-s',$Serial) + $AdbArgs) -TimeoutSeconds $TimeoutSeconds
    Set-Content -LiteralPath $Path -Value $result.Output -Encoding UTF8
    return $result.Output
}

function New-FleetArtifactDir { param([string]$Name); $dir = Join-Path (Get-FleetRepoRoot) ("artifacts\{0}-{1}" -f $Name,(Get-Date -Format 'yyyyMMdd-HHmmss')); New-Item -ItemType Directory -Path $dir -Force | Out-Null; $dir }

function Stop-FleetEmulator {
    # Never use PID-only termination: console identity must match immediately before the stop request.
    param([string]$Adb, [string]$Serial, [string]$ExpectedName, [System.Diagnostics.Process]$OwnProcess, [hashtable]$TrackedProcesses)
    $state = Get-FleetAdbState -Adb $Adb -Serial $Serial
    $name = ''
    if (@('device','offline') -ccontains $state) {
        $name = Get-FleetAvdName -Adb $Adb -Serial $Serial
        if ($name -and $name -ne $ExpectedName) { return "left alone: port runs '$name', not '$ExpectedName'" }
        if ($name -eq $ExpectedName) {
            $result = Invoke-FleetNative -Exe $Adb -Arguments @('-s',$Serial,'emu','kill') -TimeoutSeconds 15
            if ($result.ExitCode -eq 0) { return "killed via console ($ExpectedName)" }
        }
    }
    if ($null -ne $OwnProcess -and $null -ne $TrackedProcesses) {
        Stop-FleetTrackedProcessTree -OwnProcess $OwnProcess -TrackedProcesses $TrackedProcesses
        return 'cleanup requested for verified owned process handles; verify serial disappearance'
    }
    if (@('device','offline') -ccontains $state) { return 'left alone: console identity/stop could not be verified' }
    return 'not running'
}
