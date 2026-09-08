param(
    [ValidateSet('Play','Rooted')]
    [string]$Profile = 'Play',
    [string]$Serial = 'emulator-5554'
)

. "$PSScriptRoot/Android-Environment.ps1"
$ErrorActionPreference = 'Stop'
$adb = "$env:ANDROID_HOME/platform-tools/adb.exe"

function Read-Device([string[]]$Arguments) {
    $value = & $adb -s $Serial @Arguments
    if ($LASTEXITCODE -ne 0) { throw "ADB command failed: $($Arguments -join ' ')" }
    return ($value | Out-String).Trim()
}

$report = [ordered]@{
    Serial = $Serial
    Profile = $Profile
    BootCompleted = Read-Device @('shell','getprop','sys.boot_completed')
    AndroidRelease = Read-Device @('shell','getprop','ro.build.version.release')
    Api = Read-Device @('shell','getprop','ro.build.version.sdk')
    AbiList = Read-Device @('shell','getprop','ro.product.cpu.abilist')
    PlayServices = Read-Device @('shell','pm','path','com.google.android.gms')
    PlayStore = Read-Device @('shell','pm','path','com.android.vending')
}

if ($report.BootCompleted -ne '1') { throw 'Android has not completed booting' }
if ($report.Api -ne '34' -or $report.AndroidRelease -notlike '14*') { throw 'The emulator is not Android 14 / API 34' }
if ($report.AbiList -notmatch '(^|,)x86_64(,|$)') { throw 'The emulator does not advertise x86_64' }
if ($report.PlayServices -notmatch '^package:') { throw 'Google Play services is missing' }

if ($Profile -eq 'Play') {
    if ($report.PlayStore -notmatch '^package:') { throw 'Google Play Store is missing' }
    $rootProbe = & $adb -s $Serial shell id -u
    if (($rootProbe | Out-String).Trim() -eq '0') { throw 'The Play profile unexpectedly has root ADB' }
    $report.Root = 'not available (expected for Google Play image)'
} else {
    $uid = Read-Device @('shell','id','-u')
    if ($uid -ne '0') { throw "Rooted profile ADB UID is $uid, expected 0" }
    $report.Root = "ADB UID $uid"
    $report.Magisk = Read-Device @('shell','/debug_ramdisk/magisk','-v')
    $report.MagiskManager = Read-Device @('shell','pm','path','com.topjohnwu.magisk')
    if ($report.MagiskManager -notmatch '^package:') { throw 'Magisk manager app is missing' }
}

$output = Join-Path $WorkspaceRoot 'artifacts/emulator-profile.json'
$report | ConvertTo-Json -Depth 3 | Set-Content $output -Encoding UTF8
$report | Format-List
Write-Host "Verification report: $output"
