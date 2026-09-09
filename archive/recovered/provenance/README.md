# Recovery provenance only

The app module was removed in commit `cbc1d35`. The Gradle settings still mention
`:app`, but that directory and its Android sources are absent. Do not run this
skeleton as the current project or treat old successful build reports as current.

`HISTORICAL-README.md`, hashes, mappings and validation reports record the earlier
recovery effort. Its referenced paths are historical. The adjacent
`../migration-map.json` maps original flat files to the retained export.
