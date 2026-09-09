[CmdletBinding()]
param(
    [string]$AssetsDirectory,
    [switch]$Force,
    [switch]$SkipBlissIso,
    [string]$GitHubToken = $env:GITHUB_TOKEN
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (-not $AssetsDirectory) { $AssetsDirectory = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets' }
New-Item -ItemType Directory -Path $AssetsDirectory -Force | Out-Null
$AssetsDirectory = (Resolve-Path -LiteralPath $AssetsDirectory).Path
$manifestEntries = [System.Collections.Generic.List[object]]::new()
$headers = @{ 'User-Agent' = 'android-fleet-asset-downloader/1.1' }
# Keep credentials on api.github.com. Downloads can redirect to third parties.
$apiHeaders = $headers.Clone()
$apiHeaders.Accept = 'application/vnd.github+json'
if ($GitHubToken) { $apiHeaders.Authorization = "Bearer $GitHubToken" }
$previousManifestPath = Join-Path $AssetsDirectory 'manifest.json'
$previousAssets = @()
if (Test-Path -LiteralPath $previousManifestPath -PathType Leaf) {
    $previousAssets = @((Get-Content -Raw -LiteralPath $previousManifestPath | ConvertFrom-Json).assets)
}

function Invoke-WithRetry {
    param([scriptblock]$Operation, [string]$Description)
    $lastError = $null
    foreach ($attempt in 1..3) {
        try { return & $Operation }
        catch {
            $lastError = $_
            if ($attempt -lt 3) {
                Write-Warning "$Description failed (attempt $attempt/3): $($_.Exception.Message)"
                Start-Sleep -Seconds ([math]::Pow(2, $attempt))
            }
        }
    }
    throw "$Description failed after 3 attempts: $($lastError.Exception.Message)"
}

function Save-Asset {
    param([string]$Name, [string]$Version, [string]$Url, [string]$FileName, [string]$ExpectedDigest = '')
    if ($FileName -ne [IO.Path]::GetFileName($FileName) -or $FileName -match '[\\/:]') { throw "Invalid asset filename: $FileName" }
    if (([Uri]$Url).Scheme -ne 'https') { throw "Asset URL must use HTTPS: $Url" }
    $expected = ''
    if ($ExpectedDigest) {
        if ($ExpectedDigest -notmatch '^sha256:[0-9a-fA-F]{64}$') { throw "Invalid or unsupported digest for $FileName" }
        $expected = $ExpectedDigest.Substring(7).ToLowerInvariant()
    }
    $destination = Join-Path $AssetsDirectory $FileName
    $partial = "$destination.partial"
    $previous = @($previousAssets | Where-Object { $_.file -ceq $FileName -and $_.url -ceq $Url -and $_.version -ceq $Version })
    $cachedHash = if ($previous.Count -eq 1 -and $previous[0].sha256 -match '^[0-9a-fA-F]{64}$') { $previous[0].sha256 } else { '' }
    if ((Test-Path -LiteralPath $destination -PathType Leaf) -and -not $Force -and ($expected -or $cachedHash)) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
        $referenceHash = if ($expected) { $expected } else { $cachedHash }
        if ($hash -ine $referenceHash) { throw "SHA-256 mismatch for cached $FileName. Use -Force to download a fresh copy." }
        Write-Host "Using existing $FileName (use -Force to replace it)."
    } else {
        Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
        Write-Host "Downloading $Name $Version -> $FileName"
        try {
            Invoke-WithRetry -Description "Download of $Name" -Operation {
                Invoke-WebRequest -UseBasicParsing -Headers $headers -Uri $Url -OutFile $partial -MaximumRedirection 10 | Out-Null
            }
            if (-not (Test-Path -LiteralPath $partial -PathType Leaf) -or (Get-Item -LiteralPath $partial).Length -eq 0) {
                throw "Downloaded file for $Name is empty."
            }
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $partial).Hash.ToLowerInvariant()
            if ($expected -and $hash -ne $expected) { throw "SHA-256 mismatch for $FileName" }
            # Never replace an existing good file with an unverified partial.
            Move-Item -LiteralPath $partial -Destination $destination -Force
        } finally {
            Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
        }
    }
    $manifestEntries.Add([pscustomobject]@{
        name = $Name; version = $Version; file = $FileName; url = $Url
        sha256 = $hash; size = (Get-Item -LiteralPath $destination).Length
        upstream_sha256_verified = [bool]$expected
        verified_at_utc = [DateTime]::UtcNow.ToString('o')
    })
}

function Save-GitHubReleaseAsset {
    param([string]$Name, [string]$Repository, [string]$AssetPattern, [string]$OutputPrefix)
    $uri = "https://api.github.com/repos/$Repository/releases/latest"
    $release = Invoke-WithRetry -Description "GitHub release lookup for $Repository" -Operation {
        Invoke-RestMethod -Headers $apiHeaders -Uri $uri -TimeoutSec 60
    }
    if ($release.draft -or $release.prerelease) { throw "$Repository returned a non-stable release." }
    $matches = @($release.assets | Where-Object { $_.name -match $AssetPattern })
    if ($matches.Count -eq 0) {
        $names = ($release.assets.name -join ', ')
        throw "No $Name asset matched '$AssetPattern' in $($release.tag_name). Assets: $names"
    }
    if ($matches.Count -gt 1) {
        throw "Multiple $Name assets matched. Refine the asset pattern before selecting an architecture/version: $($matches.name -join ', ')"
    }
    $asset = $matches[0]
    $extension = [IO.Path]::GetExtension($asset.name)
    $safeVersion = ($release.tag_name -replace '[^0-9A-Za-z._-]', '_')
    $digest = if ($asset.PSObject.Properties['digest']) { [string]$asset.digest } else { '' }
    Save-Asset -Name $Name -Version $release.tag_name -Url $asset.browser_download_url `
        -FileName "$OutputPrefix-$safeVersion$extension" -ExpectedDigest $digest
}

function Save-GitHubReleaseAssetWithFallback {
    param([string]$Name, [string[]]$Repositories, [string]$AssetPattern, [string]$OutputPrefix)
    $lastError = $null
    foreach ($repository in $Repositories) {
        try {
            Save-GitHubReleaseAsset -Name $Name -Repository $repository -AssetPattern $AssetPattern -OutputPrefix $OutputPrefix
            if ($repository -ne $Repositories[0]) {
                Write-Warning "$($Repositories[0]) is unavailable; resolved $Name from configured fallback $repository."
            }
            return
        } catch {
            $lastError = $_
            Write-Warning "$Name source $repository was unavailable: $($_.Exception.Message)"
        }
    }
    throw "No configured source for $Name succeeded: $($lastError.Exception.Message)"
}

function Save-LibHoudini {
    # The legacy android-x86 SFS host currently has an invalid TLS chain. Use
    # the actively published HTTPS source bundle so certificate validation is
    # never disabled. Bliss may already contain a compatible native bridge.
    $repository = 'supremegamers/vendor_intel_proprietary_houdini'
    $repo = Invoke-WithRetry -Description 'libhoudini repository lookup' -Operation {
        Invoke-RestMethod -Headers $apiHeaders -Uri "https://api.github.com/repos/$repository" -TimeoutSec 60
    }
    $branch = Invoke-WithRetry -Description 'libhoudini branch lookup' -Operation {
        Invoke-RestMethod -Headers $apiHeaders -Uri "https://api.github.com/repos/$repository/branches/$([Uri]::EscapeDataString($repo.default_branch))" -TimeoutSec 60
    }
    $sha = [string]$branch.commit.sha
    if ($sha -notmatch '^[0-9a-fA-F]{40}$') { throw 'Unable to resolve the libhoudini source revision.' }
    $url = "https://api.github.com/repos/$repository/zipball/$sha"
    Save-Asset -Name 'libhoudini source payload' -Version "$($repo.default_branch)@$($sha.Substring(0,12))" `
        -Url $url -FileName "libhoudini-$($sha.Substring(0,12)).zip"
}

function Save-BlissIso {
    $folder = 'https://sourceforge.net/projects/blissos-x86/files/Official/BlissOS16/Gapps/Generic/'
    $page = Invoke-WithRetry -Description 'Bliss OS archive lookup' -Operation { Invoke-WebRequest -UseBasicParsing -Uri $folder -Headers $headers }
    $matches = [regex]::Matches($page.Content, '(?<name>Bliss-[^"''<>/]*x86_64[^"''<>/]*gapps[^"''<>/]*\.iso)') |
        ForEach-Object { $_.Groups['name'].Value } | Sort-Object -Unique
    if (-not $matches) { throw 'No x86_64 GApps ISO was found in the official Bliss OS archive.' }
    $selected = $matches | Sort-Object {
        if ($_ -match '(?<date>20\d{6})') { [int64]$Matches.date } else { 0 }
    } -Descending | Select-Object -First 1
    $encoded = [Uri]::EscapeDataString($selected).Replace('%2F','/')
    $url = "$folder$encoded/download"
    $checksumUrl = "https://downloads.sourceforge.net/project/blissos-x86/Official/BlissOS16/Gapps/Generic/$encoded.sha256"
    $checksumTemp = Join-Path ([IO.Path]::GetTempPath()) ("bliss-" + [guid]::NewGuid().ToString('N') + '.sha256')
    try {
        Invoke-WithRetry -Description 'Bliss OS checksum lookup' -Operation {
            Invoke-WebRequest -UseBasicParsing -Uri $checksumUrl -Headers $headers -OutFile $checksumTemp -MaximumRedirection 10
        }
        $checksumText = Get-Content -Raw -LiteralPath $checksumTemp
    } finally {
        Remove-Item -LiteralPath $checksumTemp -Force -ErrorAction SilentlyContinue
    }
    if ($checksumText -notmatch '(?i)(?<hash>[0-9a-f]{64})') { throw 'The Bliss OS SHA-256 file did not contain a valid hash.' }
    Save-Asset -Name 'Bliss OS x86_64 GApps (archived)' -Version ($selected -replace '\.iso$','') -Url $url -FileName $selected -ExpectedDigest "sha256:$($Matches.hash)"
}

Save-GitHubReleaseAsset -Name 'Magisk' -Repository 'topjohnwu/Magisk' -AssetPattern '^Magisk-v.*\.apk$' -OutputPrefix 'magisk'
Save-GitHubReleaseAsset -Name 'Zygisk Next' -Repository 'Dr-TSNG/ZygiskNext' -AssetPattern '(?i)^Zygisk[-_ ]?Next.*\.zip$' -OutputPrefix 'zygisk-next'
Save-GitHubReleaseAsset -Name 'Shamiko' -Repository 'LSPosed/LSPosed.github.io' -AssetPattern '(?i)^Shamiko.*\.zip$' -OutputPrefix 'shamiko'
Save-GitHubReleaseAssetWithFallback -Name 'Play Integrity Fix' -Repositories @('chiteroman/PlayIntegrityFix','KOWX712/PlayIntegrityFix') -AssetPattern '(?i)^(PlayIntegrityFix|PIF).*\.zip$' -OutputPrefix 'play-integrity-fix'
Save-GitHubReleaseAsset -Name 'Universal SafetyNet Fix' -Repository 'kdrag0n/safetynet-fix' -AssetPattern '(?i).*\.zip$' -OutputPrefix 'universal-safetynet-fix'
Save-LibHoudini
if (-not $SkipBlissIso) { Save-BlissIso } else { Write-Warning 'Bliss OS ISO download skipped by request.' }

$manifest = [pscustomobject]@{
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    warning = 'A local SHA-256 records bytes, not publisher authenticity. Check upstream_sha256_verified for each asset. A Houdini source ZIP is not an installable module or proof of working ARM translation. Review version compatibility before deployment.'
    assets = $manifestEntries
}
$manifestTemporaryPath = Join-Path $AssetsDirectory 'manifest.json.partial'
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestTemporaryPath -Encoding utf8
Move-Item -LiteralPath $manifestTemporaryPath -Destination $previousManifestPath -Force
Write-Host "Asset preparation complete: $AssetsDirectory"
