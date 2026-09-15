# Project map and preserved files

Open [Android-Lab.code-workspace](../Android-Lab.code-workspace) for separate
code/instruction, evidence, Android runtime, downloaded-component, and recovered
Android reference folders. Generated caches are hidden in that workspace view.
The sibling `deepseek-harness` project and parent workspace were left alone.

## Working project

| Folder | Purpose |
| --- | --- |
| [android_lab](../android_lab) | Active Python CLI, device diagnostics, app experiments, observation, location and Proxmox code |
| [tools/windows](../tools/windows) | Android SDK/AVD setup, baseline and fleet lifecycle scripts |
| [tools/linux](../tools/linux) | Docker emulator startup and ADB readiness |
| [config](../config) | App profiles, fleet matrix, Docker configuration and routes |
| [tests](../tests) | Maintained regression tests |
| [docs](.) | Architecture, commands, status, troubleshooting and handoff |
| [.codex](../.codex) | Project agent configuration and roles |

Start with [setup](../START-HERE.md), [commands](COMMANDS.md),
[fleet commands](FLEET.md), and [current state](STATE.md). The
[handoff](HANDOFF_2026-09-14.md) retains the earlier detailed project snapshot.
[AGENTS.md](../AGENTS.md), [DEBUGGING.md](DEBUGGING.md), [CODEX.md](CODEX.md),
[MODEL_STRATEGY.md](MODEL_STRATEGY.md), and [LOGIN_READ_FIRST.md](LOGIN_READ_FIRST.md)
remain at their established paths. No existing instruction Markdown was removed.

## Experiments and logs

| Location | Contents |
| --- | --- |
| [experiments/EXPERIMENT_LOG.md](../experiments/EXPERIMENT_LOG.md) | Dated actions, outcomes, evidence paths and next decisions |
| [experiments](../experiments) | Detailed experiment notes and reusable TEMPLATE |
| `artifacts/` | Original raw logs, screenshots, reports, APK captures and test output |
| `artifacts/INDEX.md` (local) | Navigable inventory of existing evidence directories and loose files |
| [knowledge_base](../knowledge_base) | Verified results, assumptions and known failed approaches |
| [codex_memory](../codex_memory) | Compact context, decisions and attempted-approach records |

Existing `artifacts/pgo-*`, `api361-test`, `api37-test`, `live-*`, `shungo-*`,
and the loose SDK/emulator/test logs remain at their original paths. Private
runtime evidence remains ignored by Git. The cleanup did not start an emulator,
perform a game login, or change an Android image.

## Android builds and components retained

| Location | Preserved material |
| --- | --- |
| `.tools/android-sdk/` | SDK tools, emulator, platform tools and installed system images |
| `.tools/android-user/avd/` | Existing named AVD configurations and virtual disks |
| `.tools/jdk/`, `.tools/gradle-cache/` | Java toolchain and Android build cache |
| `.tools/magisk-source/` | Existing downloaded Android component source |
| [assets](../assets) and [manifest](../assets/manifest.json) | ISO, APKs and downloaded component bundles with existing provenance |
| `artifacts/pgo-apk/`, `artifacts/api361-test/apks/` | Previously captured official game base/split APK sets |
| `artifacts/shungo-20260913/` | Existing Shungo APK and inspection evidence |
| `dist/`, `artifacts/dist/` | Existing Python distribution outputs, retained in place |
| [Android provenance](../archive/recovered/provenance) | Gradle skeleton, wrapper, original recovery/license/build metadata |

The active project is Python. The Android `app` module had already been removed
in commit `cbc1d35`; this cleanup neither removed nor restored that module. The
retained Gradle skeleton alone is not a currently buildable Android app.

## Pokemon/game-mechanics reference

All recovered source/resources/models and the original mapping remain under
[archive/recovered](../archive/recovered). The flat export has misleading
filenames: consult the [recovery map](../archive/recovered/provenance/recovery-map.csv)
and [migration map](../archive/recovered/migration-map.json) before identifying a
file by extension. These mappings locate the important historical roles:

| Historical role from recovery map | Retained file |
| --- | --- |
| ActionLooper / action execution | [image_logo.png](../archive/recovered/flat-export/image_logo.png) |
| ActionService | [shape_rounded_purple.xml](../archive/recovered/flat-export/shape_rounded_purple.xml) |
| ModelHandler | [logo_x.xml](../archive/recovered/flat-export/logo_x.xml) |
| SettingsController | [ic_launcher_foreground.xml](../archive/recovered/flat-export/ic_launcher_foreground.xml) |
| SettingsValuesProvider | [icon_accesibility.xml](../archive/recovered/flat-export/icon_accesibility.xml) |
| FloatingMenuService | [vector_arrow_back.xml](../archive/recovered/flat-export/vector_arrow_back.xml) |
| MainActivity | [MoreFragment.java](../archive/recovered/flat-export/MoreFragment.java) |
| Android app build configuration | [AndroidManifest.xml](../archive/recovered/flat-export/AndroidManifest.xml) |
| Android manifest | [RegibotApplication.java](../archive/recovered/flat-export/RegibotApplication.java) |

This is preserved reference material, not a claim of working gameplay automation.
The existing archive verifier checks all 280 historical mapping entries.

## Cleanup archive and restoration

On September 14, 2026, 969 files totaling 43,728,992 bytes were relocated without
deletion. Their SHA-256 hashes and timestamps were checked after the move.

| Former path | Current path |
| --- | --- |
| `.tmp/` | `artifacts/_archive/cleanup-20260914/.tmp/` |
| `android_cloud_lab.egg-info/` | `artifacts/_archive/cleanup-20260914/android_cloud_lab.egg-info/` |
| `experiments/config/` (nested duplicate Fleet script) | `artifacts/_archive/cleanup-20260914/experiments/config/` |

Exact per-file hashes and destinations are in the local
`artifacts/repo-cleanup-20260914/move-manifest.json`;
`artifacts/repo-cleanup-20260914/preservation-result.json` records verification.
Git status and both staged/unstaged patches were saved in
the same evidence directory before moving anything. Restoring a folder means
moving its listed destination back to its former path after checking that the
former path has not since been recreated. Python packaging may regenerate
`*.egg-info`; new scratch/output should go under `artifacts/tmp` or `artifacts/dist`.

The prior fleet run stopped at a host-side default-path error in New-FleetAvds;
creation exited 1 before a fleet AVD was created. Its scripts, input backups,
test logs, and downloaded API35 image remain available. Further fleet runtime
testing was paused when this cleanup was requested; no passing fleet run is claimed.
