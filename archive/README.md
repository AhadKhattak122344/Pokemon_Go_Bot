# Archive

This directory is reference-only and excluded from Python packaging and Docker.

- `recovered/flat-export/`: original flattened source/resources/Javadoc with
  misleading filenames. No attempt was made to infer source roles from extensions.
- `recovered/provenance/`: metadata and Gradle skeleton left after the deliberate
  app removal in commit `cbc1d35`. It is not an active Android application.
- `recovered/migration-map.json`: original paths, destination paths, SHA-256 values,
  duplicate decisions and discovered references for the 280 relocated/deduplicated
  root export files. Every unique byte sequence remains available.
- `historical-proposals/`: superseded setup scripts, checklist and supplied handoff
  transcription. These contain unsupported assumptions and are not a deployment
  recipe. Do not run them as part of the current QA workflow.

139 `(1)` copies were removed only after exact byte comparison with their retained
counterparts and reference tracing. The two differing LICENSE/README variants are
preserved. Historical recovery-map paths describe the old export; use the migration
map to resolve them. Historical HTML was already flattened/incomplete and is not a
published documentation site.
