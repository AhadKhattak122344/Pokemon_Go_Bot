$ErrorActionPreference = 'Stop'
$root = Join-Path (Split-Path $PSScriptRoot -Parent) 'recovered'
$main = Join-Path $root 'app/src/main'
$failures = [Collections.Generic.List[string]]::new()
$resources = @{}
foreach ($file in Get-ChildItem (Join-Path $main 'res') -File -Recurse) {
    $type = ($file.Directory.Name -split '-')[0]
    if ($type -ne 'values') { $resources["$type/$($file.BaseName)"] = $true }
    if ($file.Extension -eq '.xml') {
        try { $xml = [xml][IO.File]::ReadAllText($file.FullName) }
        catch { $failures.Add("Invalid XML: $($file.FullName)"); continue }
        if ($type -eq 'values') {
            foreach ($node in $xml.resources.ChildNodes) {
                if ($node.name) { $resources["$($node.LocalName)/$($node.name)"] = $true }
            }
        }
    }
}
$missing = @{}
foreach ($file in Get-ChildItem $main -File -Recurse) {
    if ($file.Extension -notin '.xml','.java') { continue }
    $content = [IO.File]::ReadAllText($file.FullName)
    foreach ($match in [regex]::Matches($content, '@(drawable|layout|mipmap|xml|raw|font|string|color|style)/([\w.]+)|(?<!android\.)\bR\.(drawable|layout|mipmap|xml|raw|font|string|color|style)\.([\w]+)')) {
        $key = if ($match.Groups[1].Success) { "$($match.Groups[1])/$($match.Groups[2])" } else { "$($match.Groups[3])/$($match.Groups[4])" }
        if (!$resources.ContainsKey($key)) { $missing[$key] = $true }
    }
    if ($file.Extension -eq '.java') {
        $class = [regex]::Match($content, '(?m)^public\s+(?:final\s+|abstract\s+)?class\s+(\w+)')
        if (!$class.Success -or $class.Groups[1].Value -ne $file.BaseName) { $failures.Add("Java filename mismatch: $($file.Name)") }
    }
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$jar = [IO.Compression.ZipFile]::OpenRead((Join-Path $root 'gradle/wrapper/gradle-wrapper.jar'))
try {
    if (!$jar.GetEntry('org/gradle/wrapper/GradleWrapperMain.class')) { $failures.Add('Wrapper JAR has no entry point') }
} finally { $jar.Dispose() }
$models = @('model_detector_map_v2.tflite','model_detector_encounter.tflite','model_detector_clickable_v2.tflite','model_classifier_screen_v5.tflite','predictor.tflite')
$missingModels = @($models | Where-Object { !(Test-Path -LiteralPath (Join-Path $main "assets/$_")) })
$report = [ordered]@{
    StructuralErrors = @($failures)
    UnresolvedResourceReferences = @($missing.Keys | Sort-Object)
    MissingModelAssets = $missingModels
    Note = 'Static recovery audit, not an Android compile or runtime test. Framework/library references may need manual review.'
}
$report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $root 'validation-report.json') -Encoding UTF8
$report | ConvertTo-Json -Depth 4
if ($failures.Count -or $missing.Count -or $missingModels.Count) { exit 1 }
