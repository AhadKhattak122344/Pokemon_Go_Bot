# Android Fleet Setup Checklist

This file is the single source of truth for the repository's Android VM setup.
It was reconstructed from the requested Phase 0-5 requirements because the
referenced `CHECKLIST.md` was not present in the supplied workspace.

## Phase 0 - Prerequisites

- [x] Create `setup/`, `scripts/`, `docs/`, and `assets/` directories.
- [x] Check `adb`, `git`, and `python3` availability.
- [x] Support the repository-local Android SDK when `adb` is not on `PATH`.
- [ ] Install Python 3 if future tooling requires it (current scripts do not).

## Phase 1 - VM template preparation

- [x] Add a dynamic asset downloader for Magisk, Zygisk Next, Shamiko,
  Play Integrity Fix, Universal SafetyNet Fix, libhoudini, and the latest
  archived official Bliss OS x86_64 GApps ISO.
- [x] Download all resolved assets and record their URLs, sizes, and SHA-256
  hashes in `assets/manifest.json`.

  The original `chiteroman/PlayIntegrityFix` repository is no longer available.
  The downloader tries it first, then uses the maintained
  `KOWX712/PlayIntegrityFix` fork and emits an explicit warning.
  The legacy android-x86 libhoudini host currently fails TLS validation, so the
  downloader uses the current HTTPS source payload from
  `supremegamers/vendor_intel_proprietary_houdini`. It is a build/native-bridge
  payload, not a Magisk module; use Bliss OS's native-bridge integration.
- [x] Add a Proxmox VM preparation guide and fleet configuration template.
- [ ] Create and boot the Proxmox VM manually.
- [ ] Enable Android developer options, USB debugging, and TCP/IP ADB.
- [ ] Record the VM IP in a local fleet configuration.

## Phase 2 - Root

- [ ] Install the Magisk APK and complete the image/root setup on the template.
- [ ] Confirm `su -c id` returns `uid=0`.

## Phase 3 - Modules

- [ ] Install Zygisk Next and Shamiko.
- [ ] Install exactly one integrity compatibility module: Play Integrity Fix
  (default) or legacy Universal SafetyNet Fix.
- [ ] Reboot and verify all selected modules are enabled.

## Phase 4 - Lab device configuration

- [ ] Apply the Pixel 4 software profile through a Magisk property module.
- [ ] Configure the selected Zygisk implementation and DenyList packages.
- [ ] Generate per-VM Android ID and network identity values.
- [ ] Reboot the VM.

Hardware-backed identifiers may not be mutable from Android userspace. The
configuration script reports the values actually exposed after reboot rather
than claiming that an unsupported modem identifier change succeeded.

## Phase 5 - Verification

- [ ] Run `scripts/verify-installation.sh`.
- [ ] Confirm root, Magisk, Zygisk, module, ABI/native bridge, and Google Play
  services status.
- [ ] Perform any app-mediated Play Integrity test manually; SafetyNet is
  deprecated and there is no reliable generic ADB-only verdict API.
