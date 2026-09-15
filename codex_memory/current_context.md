# Current Context

Last updated: 2026-09-14

Latest user direction: repository cleanup, superseding active fleet execution.
Read docs/PROJECT_MAP.md for the organized layout and preserved Android/game
reference. Generated .tmp, root egg-info and misplaced experiments/config files
are retained under artifacts/_archive/cleanup-20260914, with 969 file hashes in
artifacts/repo-cleanup-20260914/move-manifest.json. No logs/components were deleted.
Fleet scripts are restored but New-FleetAvds -SkipInstall exited1 at its default
Matrix path (empty PSScriptRoot). API35 image download succeeded; no fleet AVD was
created by that failed command. Resume from F01 evidence, not a claimed boot pass.

The active project is the `android-cloud-lab` CLI, not a FastAPI service. The
repo already contains a cautious Proxmox planner/deployer, diagnostics, observer,
root controls, location helpers, and Pokemon GO experiment harness.

Current verified baseline:

- Native API36 AVD `poke_api36_test` boots and launches Pokemon GO.
- Pokemon GO login remains unresolved on the emulator with the designated account.
- API36.1 display stability failed.
- API37 auto/host boot failed. Software GPU and software with GLDirectMem disabled
  both reached the boot marker but failed display capture with SurfaceFlinger
  SIGABRT (L23/L24). Guest stopped; no API37 login attempted.
- Proxmox is plan/preflight/deploy code with mocked tests and no live host proof.

Before suggesting a path, run:

```powershell
uv run python tools/validate_against_history.py "short suggestion text"
```

Then read the matched source entry before recommending or executing anything.
