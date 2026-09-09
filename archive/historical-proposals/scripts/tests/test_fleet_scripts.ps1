[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$scriptDirectory = Split-Path $PSScriptRoot -Parent
. (Join-Path $scriptDirectory 'adb-common.ps1')
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('fleet-script-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$passed = 0
function Assert-True { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message }; $script:passed++; Write-Output "PASS: $Message" }
function Assert-Throws {
    param([scriptblock]$Operation, [string]$Pattern, [string]$Message)
    $caught = $false
    try { & $Operation | Out-Null } catch { if ($_.Exception.Message -notmatch $Pattern) { throw }; $caught = $true }
    Assert-True $caught $Message
}
try {
    $tokens = $null
    $errors = $null
    $downloadAst = [Management.Automation.Language.Parser]::ParseFile((Join-Path $scriptDirectory 'download-assets.ps1'), [ref]$tokens, [ref]$errors)
    Assert-True ($errors.Count -eq 0) 'Downloader parses in Windows PowerShell'
    foreach ($functionAst in $downloadAst.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
        . ([scriptblock]::Create($functionAst.Extent.Text))
    }
    $AssetsDirectory = $testRoot
    $Force = $false
    $previousAssets = @()
    $manifestEntries = [Collections.Generic.List[object]]::new()
    $headers = @{ 'User-Agent' = 'test' }
    $apiHeaders = @{ 'User-Agent' = 'test'; Authorization = 'Bearer TEST_ONLY' }
    $script:fixturePayload = 'new-download'
    $script:seenDownloadHeaders = $null
    function Invoke-WebRequest {
        param([switch]$UseBasicParsing, $Headers, $Uri, $OutFile, $MaximumRedirection)
        $script:seenDownloadHeaders = $Headers
        [IO.File]::WriteAllText($OutFile, $script:fixturePayload, [Text.UTF8Encoding]::new($false))
    }
    function Invoke-RestMethod {
        param($Headers, $Uri, $TimeoutSec)
        # Older release payloads omit digest entirely.
        [pscustomobject]@{ draft = $false; prerelease = $false; tag_name = 'v1'; assets = @(
            [pscustomobject]@{ name = 'test-v1.zip'; browser_download_url = 'https://example.test/test.zip' }
        ) }
    }
    Save-GitHubReleaseAsset -Name test -Repository example/test -AssetPattern '^test.*\.zip$' -OutputPrefix test
    Assert-True (Test-Path -LiteralPath (Join-Path $testRoot 'test-v1.zip')) 'GitHub asset without digest is handled under StrictMode'
    Assert-True (-not $script:seenDownloadHeaders.ContainsKey('Authorization')) 'Download request receives no GitHub bearer token'
    Assert-True (-not $manifestEntries[0].upstream_sha256_verified) 'Local-only hashes are labeled as not verified upstream'
    $cachedPath = Join-Path $testRoot 'cached.zip'
    [IO.File]::WriteAllText($cachedPath, 'old-good-bytes')
    $oldHash = (Get-FileHash -LiteralPath $cachedPath).Hash
    $Force = $true
    Assert-Throws { Save-Asset -Name cached -Version v1 -Url https://example.test/cached.zip -FileName cached.zip -ExpectedDigest ('sha256:' + $oldHash) } 'SHA-256 mismatch' 'Failed download hash stops replacement'
    Assert-True ((Get-FileHash -LiteralPath $cachedPath).Hash -eq $oldHash) 'Existing good asset survives a bad replacement download'
    Assert-True (-not (Test-Path -LiteralPath ($cachedPath + '.partial'))) 'Failed download partial is removed'
    $Force = $false
    $previousAssets = @([pscustomobject]@{ file = 'cached.zip'; url = 'https://example.test/cached.zip'; version = 'v1'; sha256 = $oldHash })
    [IO.File]::WriteAllText($cachedPath, 'tampered')
    Assert-Throws { Save-Asset -Name cached -Version v1 -Url https://example.test/cached.zip -FileName cached.zip } 'SHA-256 mismatch for cached' 'Cached bytes are checked against their previous manifest'
    Assert-Throws { Save-Asset -Name escape -Version v1 -Url https://example.test/test.zip -FileName '../escape.zip' } 'Invalid asset filename' 'Downloader rejects a path outside its asset directory'

    $script:adbMode = 'ok'
    $script:rootCommand = ''
    $script:installCount = 0
    $script:pushes = @()
    function Mock-Adb {
        $global:LASTEXITCODE = 0
        if ($args[0] -eq 'devices') {
            "List of devices attached"
            "fixture-a`tdevice"
            if ($script:adbMode -eq 'multiple') { "fixture-b`tdevice" }
        } elseif ($args[0] -eq 'connect') {
            if ($script:adbMode -eq 'connection_failure') { 'failed to connect' } else { 'connected' }
        } elseif ($args[2] -eq 'get-state') { 'device' }
        elseif ($args[2] -eq 'push') { $script:pushes += [string]$args[3]; 'pushed' }
        elseif ($args[2] -eq 'shell' -and $args[3] -match '^printf %s ([A-Za-z0-9+/=]+) \| base64 -d \| su -c sh$') {
            $script:rootCommand = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Matches[1]))
            if ($script:adbMode -eq 'root_failure') { $global:LASTEXITCODE = 17; 'benign-looking output'; return }
            if ($script:rootCommand -match 'magisk --install-module') {
                $script:installCount++
                if ($script:adbMode -eq 'install_failure') { $global:LASTEXITCODE = 23; 'installation rejected'; return }
                'module staged'
            } elseif ($script:rootCommand -match 'magisk -v') { '30.0:fixture' }
            else { 'uid=0(root) gid=0(root)' }
        }
    }
    $probeCommand = 'magisk --sqlite "SELECT value FROM settings WHERE key=''zygisk'';"'
    Invoke-FleetRoot -Adb Mock-Adb -Target @('-s','fixture-a') -Command $probeCommand | Out-Null
    Assert-True ($script:rootCommand -eq ("set -e`n" + $probeCommand + "`n")) 'Root transport preserves nested SQL quotes and LF boundaries'
    $script:adbMode = 'root_failure'
    Assert-Throws { Invoke-FleetRoot -Adb Mock-Adb -Target @('-s','fixture-a') -Command id } 'exit 17' 'Root command nonzero status is not hidden by output'
    $script:adbMode = 'multiple'
    Assert-Throws { Get-FleetAdbTarget -Adb Mock-Adb } 'found 2' 'Multiple connected devices require an explicit serial'
    $script:adbMode = 'connection_failure'
    Assert-Throws { Get-FleetAdbTarget -Adb Mock-Adb -Device fixture:5555 } 'connection.*failed' 'ADB textual connection failures fail even with exit code zero'

    $unixPath = Join-Path $testRoot 'service.sh'
    Write-FleetUnixText -Path $unixPath -Text "#!/system/bin/sh`r`necho test`r`n"
    $unixBytes = [IO.File]::ReadAllBytes($unixPath)
    Assert-True (-not ($unixBytes -contains 13) -and $unixBytes[0] -eq 35) 'Android scripts use LF and have no UTF-8 BOM'

    $moduleDirectory = Join-Path $testRoot 'modules'
    New-Item -ItemType Directory -Path $moduleDirectory | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $moduleManifest = @()
    foreach ($name in @('zygisk-next-v1.zip','shamiko-v1.zip','play-integrity-fix-v1.zip')) {
        $modulePath = Join-Path $moduleDirectory $name
        $zip = [IO.Compression.ZipFile]::Open($modulePath, [IO.Compression.ZipArchiveMode]::Create)
        $writer = [IO.StreamWriter]::new($zip.CreateEntry('module.prop').Open())
        $writer.Write("id=fixture`n"); $writer.Dispose(); $zip.Dispose()
        $moduleManifest += [pscustomobject]@{ file = $name; sha256 = (Get-FileHash -LiteralPath $modulePath).Hash }
    }
    [IO.File]::WriteAllText((Join-Path $moduleDirectory 'unrelated.zip'), 'not a module')
    @{ assets = $moduleManifest } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $moduleDirectory 'manifest.json')
    $installText = Get-Content -Raw -LiteralPath (Join-Path $scriptDirectory 'install-magisk-modules.ps1')
    $installText = $installText.Replace(". (Join-Path `$PSScriptRoot 'adb-common.ps1')", '')
    $installer = [scriptblock]::Create($installText)
    function Resolve-FleetAdb { 'Mock-Adb' }
    $script:adbMode = 'install_failure'
    Assert-Throws { & $installer -Device fixture-a -AssetsDirectory $moduleDirectory -SkipMagiskApp -NoReboot } 'exit 23' 'Module installer preserves installation failure through cleanup'
    Assert-True ($script:installCount -eq 1) 'Installer stops after the first rejected module'
    $script:adbMode = 'ok'
    $script:installCount = 0
    $script:pushes = @()
    & $installer -Device fixture-a -AssetsDirectory $moduleDirectory -SkipMagiskApp -NoReboot
    Assert-True ($script:installCount -eq 3 -and $script:pushes.Count -eq 3) 'Installer selects only the three required module ZIPs'
    $script:pushes = @()
    [IO.File]::WriteAllText((Join-Path $moduleDirectory 'shamiko-v1.zip'), 'tampered')
    Assert-Throws { & $installer -Device fixture-a -AssetsDirectory $moduleDirectory -SkipMagiskApp -NoReboot } 'SHA-256 mismatch' 'Installer rejects tampered module assets'
    Assert-True ($script:pushes.Count -eq 0) 'Asset preflight finishes before any device upload'
    Write-Output "$passed script regression checks passed. All downloads and device commands were mocked."
} finally {
    $absoluteTestRoot = [IO.Path]::GetFullPath($testRoot)
    $absoluteTempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($absoluteTestRoot.StartsWith($absoluteTempRoot, [StringComparison]::OrdinalIgnoreCase) -and
        [IO.Path]::GetFileName($absoluteTestRoot) -like 'fleet-script-tests-*') {
        Remove-Item -LiteralPath $absoluteTestRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
