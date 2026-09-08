$ErrorActionPreference = 'Stop'
$source = Split-Path $PSScriptRoot -Parent
$destination = Join-Path $source 'recovered'
if (Test-Path -LiteralPath $destination) { throw 'recovered already exists; recovery will not overwrite revisions.' }
$records = [Collections.Generic.List[object]]::new()
function Restore-File($name, $target) {
    $inputPath = Join-Path $source $name
    $outputPath = Join-Path $destination $target
    New-Item -ItemType Directory -Path (Split-Path $outputPath -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $inputPath -Destination $outputPath
    $records.Add([pscustomobject]@{ Source=$name; Target=$target; SHA256=(Get-FileHash -LiteralPath $inputPath).Hash })
}
# Infer Java names from declarations, never from the damaged export filename.
$classes = @{}
foreach ($file in Get-ChildItem -LiteralPath $source -File | Sort-Object Name) {
    $content = [IO.File]::ReadAllText($file.FullName)
    $package = [regex]::Match($content, '(?m)^package\s+([\w.]+);')
    $class = [regex]::Match($content, '(?m)^public\s+(?:final\s+|abstract\s+)?class\s+(\w+)')
    if (!$package.Success -or !$class.Success) { continue }
    $name = $class.Groups[1].Value
    $set = if ($name -eq 'ExampleInstrumentedTest') {'androidTest'} elseif ($name -eq 'ExampleUnitTest') {'test'} else {'main'}
    $target = "app/src/$set/java/$($package.Groups[1].Value.Replace('.', '/'))/$name.java"
    $hash = (Get-FileHash -LiteralPath $file.FullName).Hash
    if ($classes.ContainsKey($target)) {
        if ($classes[$target] -ne $hash) { throw "Conflicting source copies for $target" }
        continue
    }
    $classes[$target] = $hash
    Restore-File $file.Name $target
}
$mapping = @{
    'AndroidManifest.xml'='app/build.gradle'
    'RegibotApplication.java'='app/src/main/AndroidManifest.xml'
    'package-tree (29).html'='build.gradle'
    'package-summary (34).html'='settings.gradle'
    'package-tree (31).html'='gradle/libs.versions.toml'
    'ListSeparatorDecoration.html'='gradle.properties'
    'ParamsFragment.html'='gradle/wrapper/gradle-wrapper.properties'
    'MoreFragment.html'='gradle/wrapper/gradle-wrapper.jar'
    'package-summary (32).html'='gradlew'
    'package-tree (33).html'='gradlew.bat'
    'model_classifier_screen_v5.tflite'='app/proguard-rules.pro'
    'LICENSE'='.gitignore'
    'README.md'='LICENSE'
    'download (1)'='docs/ORIGINAL-README.md'
    'ActionService.html'='app/src/main/res/xml/backup_rules.xml'
    'FloatingMenuService.Callbacks.html'='app/src/main/res/xml/data_extraction_rules.xml'
    'FloatingMenuService.LocalBinder.html'='app/src/main/res/xml/global_action_bar_service.xml'
    'FloatingMenuService.html'='app/src/main/res/xml/parameters_preferences.xml'
    'parameters_preferences.xml'='app/src/main/res/menu/bottom_nav_menu.xml'
    'animation_lottie_happy.json'='app/src/main/res/layout/activity_navigation.xml'
    'animation_lottie_pikachu.json'='app/src/main/res/layout/activity_permission.xml'
    'ic_launcher_round (15).webp'='app/src/main/res/layout/activity_main.xml'
    'strings.xml'='app/src/main/res/layout/activity_webview.xml'
    'backup_rules.xml'='app/src/main/res/layout/recyclerview_menu_priority.xml'
    'data_extraction_rules.xml'='app/src/main/res/layout/widget_kofi.xml'
    'ic_launcher_background (16).xml'='app/src/main/res/layout/floating_menu.xml'
    'strings (17).xml'='app/src/main/res/layout/fragment_home.xml'
    'themes (18).xml'='app/src/main/res/layout/fragment_more.xml'
    'colors.xml'='app/src/main/res/layout/dialog_selector_theme.xml'
    'themes.xml'='app/src/main/res/layout/dialog_selector_language.xml'
    'dialog_selector_theme.xml'='app/src/main/res/drawable/shape_rounded_purple.xml'
    'ModelHandler.html'='app/src/main/res/values/colors.xml'
    'package-tree (23).html'='app/src/main/res/values/strings.xml'
    'package-tree (21).html'='app/src/main/res/values-es/strings.xml'
    'ModelHandler.Detector.html'='app/src/main/res/values/themes.xml'
    'package-summary (24).html'='app/src/main/res/values-night/themes.xml'
    'package-summary (22).html'='app/src/main/res/values/ic_launcher_background.xml'
    'ic_launcher (13).webp'='app/src/main/res/font/qrowdies.ttf'
    'package-tree.html'='app/src/main/res/raw/animation_lottie_happy.json'
    'ActionLooper.html'='app/src/main/res/raw/animation_lottie_pikachu.json'
}
foreach ($name in $mapping.Keys | Sort-Object) { Restore-File $name $mapping[$name] }
$records | Sort-Object Target | Export-Csv -LiteralPath (Join-Path $destination 'recovery-map.csv') -NoTypeInformation
Write-Output "Recovered $($records.Count) files; original files are untouched."
