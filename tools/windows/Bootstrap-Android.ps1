param([switch]$WithEmulator)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$workspace = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$toolRoot = Join-Path $workspace '.tools'
New-Item -ItemType Directory $toolRoot -Force | Out-Null
if (!(Get-ChildItem "$toolRoot/jdk" -Directory -ErrorAction SilentlyContinue)) {
    $metadata = Invoke-RestMethod 'https://api.adoptium.net/v3/assets/latest/17/hotspot?architecture=x64&heap_size=normal&image_type=jdk&jvm_impl=hotspot&os=windows&vendor=eclipse'
    $package = $metadata[0].binary.package
    Invoke-WebRequest $package.link -OutFile "$toolRoot/jdk.zip"
    if ((Get-FileHash "$toolRoot/jdk.zip").Hash -ne $package.checksum) { throw 'JDK checksum mismatch' }
    Expand-Archive "$toolRoot/jdk.zip" "$toolRoot/jdk" -Force
}
if (!(Test-Path "$toolRoot/android-sdk/cmdline-tools/latest/bin/sdkmanager.bat")) {
    Invoke-WebRequest 'https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip' -OutFile "$toolRoot/android-tools.zip"
    Expand-Archive "$toolRoot/android-tools.zip" "$toolRoot/android-sdk/cmdline-tools" -Force
    Rename-Item "$toolRoot/android-sdk/cmdline-tools/cmdline-tools" latest
}
. "$PSScriptRoot/Android-Environment.ps1"
Write-Host 'Accepting Android SDK licenses for this build toolchain.'
$ErrorActionPreference = 'Continue'
1..80 | ForEach-Object { 'y' } | & "$env:ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager.bat" --licenses
if ($LASTEXITCODE -ne 0) { throw 'SDK license setup failed' }
$packages = @('platform-tools','platforms;android-35','build-tools;34.0.0')
if ($WithEmulator) {
    $packages += @(
        'emulator',
        'system-images;android-34;google_apis_playstore;x86_64',
        'system-images;android-36;google_apis_playstore;x86_64',
        'system-images;android-34;google_apis;x86_64'
    )
}
& "$env:ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager.bat" @packages
if ($LASTEXITCODE -ne 0) { throw 'SDK package installation failed' }
