# Do not repeat established dead ends

- Do not patch or root the clean API 36 baseline to guess at sign-in failure.
- Do not repatch API 34 merely because its known ARM translator hits SIGILL.
- Do not cycle accounts to diagnose an environment-wide failure.
- Do not retry this host's software-emulated Docker path without proof KVM is available.
- Do not restore the old ADB `-L tcp:0.0.0.0:5037` startup mistake.
- Do not infer native ARM execution from an advertised ABI/native-bridge property.
- Do not treat x86 Proxmox as a solution to arbitrary ARM64-only app requirements.
- Do not execute archived identity/concealment/integrity scripts or use them as acceptance evidence.
- Do not assume FastAPI or lifecycle commands exist: inspect `uv run lab --help`.
- Do not call an offline plan or mocked test a successful live deployment.
- Do not run the recovered Gradle skeleton as though the deleted app module exists.

## Investigation procedure

Use [the experiment log](../experiments/EXPERIMENT_LOG.md) before retrying. Capture diagnostics before clearing logcat or launching a smoke test. Record the selected AVD/serial, app version, exact symptom, timestamp, one changed variable, expected result and actual outcome. Separate install, launch, crash, authentication and certification. Keep private raw logs/screenshots in artifacts; link their paths from redacted notes. Missing evidence calls for capture, not a speculative root or image change.

# Android fleet handoff: verified corrections

Checked 2026-09-08 against project-maintained documentation and source. This reviews the pasted September 2026 handoff; it does not certify a running VM or a deployed fleet.

**The handoff is not an executable, production-ready recipe.** VM lifecycle automation is feasible, but successful Google Play installation, target-app operation, and integrity verdicts require separate testing on the exact guest image and app version. Nothing provided establishes that the user's existing emulator cannot work. Inspect it before replacing it.

## Compatibility claims that must change

| Handoff claim | Verified correction |
| --- | --- |
| Bliss OS 16.9.7 is a stable production baseline with only a temporary project risk. | Bliss's August 2026 status says old SourceForge images are frozen archives without updates or official support. The next tree requires a clean install; there is no release ETA. Treat an archived image as a compatibility experiment, not a maintained production baseline. [Bliss status](https://blissos.org/status.html) |
| A GApps image ensures full Play Store compatibility. | GApps/GMS identifies included Google services. It does not establish device certification, a particular store listing's availability, or app login compatibility. FOSS is a different services variant; it is not automatically unusable for all Android apps. [Bliss build variants](https://docs.blissos.org/knowledgebase/frequently-asked-questions/build-filenames/), [Google certification](https://support.google.com/android/answer/7165974?hl=en) |
| Bliss 16 needs a libhoudini Magisk module. | The previous-generation Bliss docs identify libhoudini for Bliss 14/15 and **libndk_translation for Bliss 16/17**. Inspect the actual image before adding or replacing a native bridge. A bridge's presence alone does not prove compatibility with every ARM library. [Bliss hardware/native-bridge documentation](https://docs.blissos.org/knowledgebase/frequently-asked-questions/hardware-compatibility/) |
| Root, a Pixel fingerprint, and random IDs make a VM a real/certified device. | Google's Android 13+ device-integrity definition includes hardware-backed evidence of a locked bootloader and certified manufacturer image. Changing strings cannot establish that evidence. The conditional virtual-integrity label is documented for Google Play Games for PC; it is not a promise for arbitrary Proxmox guests. [Google integrity verdicts](https://developer.android.com/google/play/integrity/verdicts) |
| A Play Store package timestamp proves certification; clearing Google data and waiting guarantees certification. | A package timestamp measures package state, not certification. Read **Play Store → profile → Settings → About → Play Protect certification**. Google lists rooting, custom OS images, and unlocked bootloaders among failure causes. Do not clear service/account data as an automatic certification step. [Google's verification and repair instructions](https://support.google.com/android/answer/7165974?hl=en) |
| Magisk is required for the target application. | Installing the Magisk APK is not the same as installing root. Root is not a generic Android application prerequisite. If the target is Pokémon GO, its publisher explicitly says rooted devices are unsupported and does not guarantee every nominally qualifying configuration. [Magisk installation](https://topjohnwu.github.io/Magisk/install.html), [Pokémon GO supported devices](https://niantic.helpshift.com/hc/en/6-pokemon-go/faq/92-supported-devices/) |
| All listed component versions form a supported stack. | Magisk's latest release resolved to **v30.7** during this check. That confirms this version only, not the compatibility of the combined module stack. Zygisk Next explicitly requires Magisk's built-in Zygisk to be **off**, contradicting the handoff. [Magisk release](https://github.com/topjohnwu/Magisk/releases/tag/v30.7), [Zygisk Next requirements](https://github.com/Dr-TSNG/ZygiskNext#requirements) |

For a commercial fleet, the image's availability also is not a redistribution license: Bliss's published terms distinguish open-source code from bundled GApps, native bridge, Widevine, and other proprietary components. Establish the applicable image/component permissions before distributing a template. [Bliss licensing](https://blissos.org/licensing.html)

## Commands and implementation errors

| Area | Correction required before execution |
| --- | --- |
| Host installation | Do not execute the generic “Debian/Ubuntu” host setup. Select the official installer or instructions for the installed Debian/PVE generation. The pasted enterprise repository is missing `/pve` in its URL and requires a subscription. Current project repository examples use Trixie and a scoped archive keyring; their legacy table maps Bookworm to PVE 8 and Bullseye to PVE 7. [Official installation source](https://raw.githubusercontent.com/proxmox/pve-docs/master/pve-installation.adoc), [official repository definitions](https://raw.githubusercontent.com/proxmox/pve-docs/master/pve-package-repos.adoc) |
| `pvesm upload` | No such command appears in the official `pvesm` command table. Use the storage's ISO upload UI/API, or copy an ISO into the verified ISO directory for an appropriate directory storage. Do not assume all stores accept ISO files or VM disk images. [Official CLI source](https://raw.githubusercontent.com/proxmox/pve-storage/master/src/PVE/CLI/pvesm.pm) |
| Installer boot | `--boot order=sata0` excludes the installation CD-ROM. Include the actual CD-ROM device while installing, then switch to the installed disk. The handoff also mixes SeaBIOS with an EFI partition recipe: choose a consistent legacy-BIOS or OVMF/UEFI installation and matching bootloader. Storage names and qcow2 support must match the selected storage. [Official QEMU VM guide source](https://raw.githubusercontent.com/proxmox/pve-docs/master/qm.adoc) |
| Initial ADB connection | `adb connect IP:5555` cannot enable a listener that is not running. Establish guest debugging through the guest's supported UI/console or existing authorized ADB transport first. Android's standard TCP workflow starts with an established connection before `adb tcpip 5555`; wireless pairing is another supported workflow on suitable builds. Use `adb -s SERIAL ...` on every fleet operation, with bounded connection/boot timeouts. [Android ADB documentation](https://developer.android.com/tools/adb) |
| Magisk boot patch | The proposed first-install procedure assumes `su` already works and `/dev/block/by-name/boot` exists. Those are unverified assumptions for a PC-style Android installation. Inspect the actual boot layout and use its documented installation method; never blindly `dd` into a guessed partition. Patched filenames include a generated suffix. [Magisk installation](https://topjohnwu.github.io/Magisk/install.html) |
| Magisk CLI | `magisk --enable-zygisk` and `magiskhide add ...` are absent from the current documented CLI. Do not build automation around them. The documented denylist CLI is a different interface; a configured denylist does not prove app compatibility. [Magisk tools](https://topjohnwu.github.io/Magisk/tools.html) |
| Module downloads | The handoff downloads `shamiko-1.0.1-304-release.zip` but later pushes `shamiko.zip`; no rename connects those steps. Several other URLs guess a generic asset name beneath `releases/latest/download`. Inspect each actual release, pin the exact asset and checksum, and validate HTTP success and archive format. This review has not validated every pasted asset URL. |
| `setprop ro.*` | Android defines `ro` properties as set once. Ordinary runtime `setprop` is not a valid general way to rewrite already-set build, ABI, or serial properties. Appending duplicate `build.prop` entries is not a reliable fix. Changing SDK/version strings does not change the installed framework and may break compatibility. [AOSP property rules](https://source.android.com/docs/core/architecture/configuration/add-system-properties) |
| ARM test | `/proc/cpuinfo` describes the kernel's exposed CPU; successful user-space ARM translation need not put `ARMv7` there. Record ABI/native-bridge properties, then run a known ARM-native test APK of each required bitness and inspect its result/logs. Confirm the real target separately. This is a test-design correction, not evidence that translation works on this VM. |
| Identity script | `generate_imei` is undefined, the generated MAC is never applied, and the purported module package/config path has no supporting interface specification in the handoff. On Android 8+, `ANDROID_ID` is scoped to app-signing key, user, and device; a single random JSON value does not demonstrate what every app observes. Use unique VM IDs, network MACs, and isolated guest data for fleet inventory; do not claim they produce certified handset identity. [Android ID behavior](https://developer.android.com/about/versions/oreo/android-8.0-changes) |
| Proxmox authentication | `Authorization: PVEAPITicket=...` is wrong. Ticket sessions use the `PVEAuthCookie` cookie with the appropriate CSRF header for writes; API tokens use `Authorization: PVEAPIToken=USER@REALM!TOKENID=SECRET`. Keep TLS verification enabled with the deployment CA. [Official HTTP server source](https://raw.githubusercontent.com/proxmox/pve-http-server/master/src/PVE/APIServer/AnyEvent.pm), [official token documentation source](https://raw.githubusercontent.com/proxmox/pve-docs/master/pveum.adoc) |
| Provisioning and capacity | The snippet hard-codes a node and VMID, ignores HTTP errors, and starts configuring a clone before checking task completion. Add allocated IDs, task polling, failure recovery, and bounded waits. Four vCPUs/8 GiB/64 GiB is a starting allocation, not a benchmark or physical-core requirement. Measure graphics, translation, storage latency, boot concurrency, and application workload before selecting fleet size. These are implementation findings from the pasted code. |

## Verified Proxmox API details for implementation

All paths below are relative to `/api2/json`. These are source-verified interfaces; no live Proxmox node was contacted for this review.

| Operation | Interface and result |
| --- | --- |
| Clone | `POST /nodes/{node}/qemu/{template}/clone`; response data is a task UPID. Set `full=1` when requesting a full clone. |
| Configure a stopped clone | `PUT /nodes/{node}/qemu/{vmid}/config`; synchronous, response data is null. `POST` is also valid, but asynchronous: poll its UPID when returned. |
| Start | `POST /nodes/{node}/qemu/{vmid}/status/start`; response data is a task UPID. Hypervisor task completion is not Android boot completion. |

These operations and their permission requirements are defined in [Proxmox's QEMU API source](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/API2/Qemu.pm). The repository's current path includes `src/`.

Poll `GET /nodes/{node}/tasks/{upid}/status` until `status` is `stopped`, then inspect `exitstatus`; a stopped task is not automatically successful. `exitstatus` is absent while running. Preserve the UPID and task log on failures or timeout. [Proxmox task API source](https://raw.githubusercontent.com/proxmox/pve-manager/master/PVE/API2/Tasks.pm)

`GET /nodes/{node}/network` returns an array with `iface`, `type`, and optional `active` state. Conventional bridges use `bridge` or `OVSBridge`; other network types also exist. `GET /nodes/{node}/storage/{storage}/status` returns an object whose `content` is a content-type list string; `enabled`, `active`, and byte-valued `total`, `used`, and `avail` fields are optional. Missing values must not be interpreted as demonstrated availability. [Network API source](https://raw.githubusercontent.com/proxmox/pve-manager/master/PVE/API2/Network.pm), [storage status API source](https://raw.githubusercontent.com/proxmox/pve-storage/master/src/PVE/API2/Storage/Status.pm)

## Evidence required before calling it working

1. Capture the existing guest's exact image/build, Android SDK, CPU ABIs, native bridge, rendering path, available Google packages, and current target package/version.
2. Prove the guest boots, obtains networking, and reconnects through authorized ADB after a cold reboot.
3. Record Play Store certification separately from store listing availability, install completion, foreground launch, login, and a representative in-app session. Preserve relevant crash logs. Report integrity verdicts only when a legitimate app/server test actually returns them.
4. Run one clone from an account-free template and demonstrate separate guest data and network identity. Do not bake personal Google sessions into a shared template.
5. Exercise provisioning failure, retry, stop/start, and two concurrent instances. Scale only after measuring the actual workload.

**Remaining limitation:** source review can disprove faulty instructions, but cannot replace these device tests or guarantee future app acceptance. “Runs without detection” is not a supportable fleet success criterion. If the app requires device properties this guest cannot provide, use a supported device platform rather than marking a bypass module as proof of readiness.

## Historical sources

The supplied Project_Handoff.docx transcript is retained in [the archive](../archive/historical-proposals/PROJECT_HANDOFF_SOURCE.md). The newly pasted recipe is retained as an [unexecuted proposal](../experiments/2026-09-09-user-proposal.md). These sources are historical material, not authority to execute their commands.
