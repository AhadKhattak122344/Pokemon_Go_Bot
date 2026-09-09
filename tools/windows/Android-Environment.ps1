$ErrorActionPreference = 'Stop'
$WorkspaceRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$WorkspaceTools = Join-Path $WorkspaceRoot '.tools'
$portableJdk = Get-ChildItem (Join-Path $WorkspaceTools 'jdk') -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
if ($portableJdk) { $env:JAVA_HOME = $portableJdk.FullName }
if (!(Test-Path "$env:JAVA_HOME/bin/java.exe")) { throw 'JDK not found. Run tools/windows/Bootstrap-Android.ps1 first.' }
$env:ANDROID_HOME = Join-Path $WorkspaceTools 'android-sdk'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:ANDROID_USER_HOME = Join-Path $WorkspaceTools 'android-user'
$env:ANDROID_AVD_HOME = Join-Path $env:ANDROID_USER_HOME 'avd'
$env:GRADLE_USER_HOME = Join-Path $WorkspaceTools 'gradle-cache'
New-Item -ItemType Directory -Path $env:ANDROID_AVD_HOME -Force | Out-Null
$env:PATH = "$env:JAVA_HOME/bin;$env:ANDROID_HOME/platform-tools;$env:ANDROID_HOME/emulator;$env:PATH"
