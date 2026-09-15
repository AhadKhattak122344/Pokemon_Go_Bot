# Current Working Assumptions

Last updated: 2026-09-14

## Device And Runtime

- A boot marker is not display readiness.
- A resumed activity is not authentication success.
- A native-bridge property is not proof that the target ARM or ARM64 code works.
- Google packages or a Play Store listing are not Play Protect certification.

## Proxmox

- Template clones should start from an account-free Android guest.
- Locally administered MACs and SMBIOS UUIDs are VM inventory identities only.
- A running QEMU VM is still `android_unverified` until cold boot, networking,
  ADB, app install, app launch, login, and representative behavior are tested.

## Pokemon GO Investigation

- The designated account works on a physical iPhone, so the emulator path remains
  the investigated variable.
- The API 36 emulator's uncertified Play Store state is relevant but not proven
  to be the sole private-backend rejection reason.
- Further unchanged login attempts on the same emulator add little evidence.

## Untested

- Certified physical Android comparison with the designated Google account.
- Real Proxmox clone boot, ADB persistence, and two-instance data isolation.
- API37 software-rendered boot/display result from the planned L23 test.
