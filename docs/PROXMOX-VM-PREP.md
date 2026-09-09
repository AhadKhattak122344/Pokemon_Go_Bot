# Proxmox deployment preparation

The maintained implementation is `cloud-lab/orchestrator/proxmox.py`, registered
as `lab proxmox`. Its unit tests use fake API responses. No real Proxmox host was
contacted during this change. Keep one host and one guest image as the pilot.

## Prepare a template on the intended host

1. Install Proxmox using its current official installer or the instructions for
   the exact Debian/PVE version. Do not run the old generic Ubuntu repository recipe.
2. Choose an Android guest image appropriate for the workload. Archived Bliss OS
   images are experiments, not a maintained or certified compatibility guarantee.
   Check the image's actual Android API and architecture; Bliss version numbers
   are not Android version numbers.
3. Upload the ISO through the Proxmox ISO-storage UI. Select actual disk storage,
   bridge, graphics and CPU options supported by the host. Start with 4 vCPU,
   8 GiB RAM and a 64 GiB disk as a pilot allocation, not a capacity benchmark.
4. Use a consistent BIOS/bootloader installation: OVMF with an EFI disk and UEFI
   installer, or SeaBIOS with the matching legacy bootloader. Include the optical
   drive in installation boot order; detach it and boot the installed disk afterward.
5. Validate cold boot, graphics, networking and authorized ADB. Enable the guest's
   debugging listener through its supported UI/console before `adb connect`.
   Keep ADB on an isolated management network or tunnel.
6. Test a disposable instance with the exact target APK and required native ABIs.
   Capture diagnostics and any legitimate app/backend integrity result separately.
   Root and a bridge property are not app acceptance tests.
7. Prepare an account-free template: do not clone signed-in Google sessions or
   test-account data. Shut it down cleanly and convert it to a Proxmox template.
   Record its VMID, image checksum, Android API and validation evidence.

The CLI deliberately supports a stopped, unlocked, single-NIC QEMU template on
one node, with ordinary sized virtual disks. Templates with passthrough/shared
host devices, hooks or custom topology require manual review. It does not create
an OS installation or generalize Android user data automatically.

## Configure and review offline

From the repository root:

```powershell
Copy-Item cloud-lab/config/proxmox.example.json cloud-lab/config/proxmox.json
uv run python -c "import uuid; print(uuid.uuid4())"
```

Edit `proxmox.json`: replace host/node/storage/bridge/template VMID, set a **fresh
namespace UUID** from the command above, and choose unused instance VMIDs/names.
The example points at a reserved example hostname and cannot deploy as-is.

```powershell
uv run lab proxmox plan --config cloud-lab/config/proxmox.json --out artifacts/proxmox-plan.json
```

`plan` is offline, validates the configuration, and deterministically derives
locally administered MACs and SMBIOS UUIDs. These are VM inventory identities,
not Android IDs, IMEIs or certified handset identities. Run one deployment
process at a time; the API remains the authority for VMID allocation.

## Connect and preflight later

Set `PVE_TOKEN_ID` to `USER@REALM!TOKENID` and `PVE_TOKEN_SECRET` to its secret in the
process environment using your secret manager. Never put secrets in JSON or Git.
Use a trusted server certificate. For a private CA add `ca_file` to the config;
relative paths resolve beside that JSON file. TLS checks and redirect protection
remain enabled.

Give the user and privilege-separated token permission to inspect cluster VM
inventory, node status/network/storage and the source template. Deployment also
requires clone, VM allocation/configuration/power, datastore allocation and
bridge access permissions for the selected resources. Read preflight cannot
prove write permissions; inspect effective token ACLs in Proxmox before deploying.
See the [official token and privilege guide](https://github.com/proxmox/pve-docs/blob/master/pveum.adoc).

```powershell
uv run lab proxmox preflight --config cloud-lab/config/proxmox.json --out artifacts/proxmox-preflight.json
```

Preflight rejects occupied IDs/names, unavailable templates/bridges/storage,
unsupported inherited settings, and insufficient RAM/disk plus configured reserves.
It counts all cloned virtual disks, including EFI/TPM state. This is a conservative
allocation check, not a performance or overcommit model. Missing visibility or
host changes can still make a later API write fail.

## Deploy only after pilot acceptance

```powershell
uv run lab proxmox deploy --config cloud-lab/config/proxmox.json --out artifacts/proxmox-deploy.json
```

A fresh output path is required. The tool rechecks preflight, full-clones each VM,
waits for the clone UPID, configures the stopped VM, then starts it and waits for
the start UPID. Existing VLAN/firewall/MTU NIC options are preserved. It records
intent before writes and task IDs before waiting. Auto-start on host boot is off.
Success is `provisioned_android_unverified`: running QEMU is not booted Android.

On task failure, warning, timeout or uncertain network write, inspect the journal
and Proxmox task log before taking further action. There is no automatic delete,
adoption, retry, or rollback of a partially created VM. A timeout may leave an
operation running. Resolve it explicitly, then use a new output path and unused
VMIDs for any new deployment.

## Guest acceptance

With the actual guest debugging address in `adb.serial` of a local Android YAML
scenario, and ADB available in the current environment:

```powershell
uv run lab --config cloud-lab/config/local-guest.yaml connect
uv run lab --config cloud-lab/config/local-guest.yaml status
uv run lab --config cloud-lab/config/local-guest.yaml diagnostics
```

Demonstrate cold-reboot persistence, a real ARM/ARM64 native test for each required
ABI, app install/launch/login and representative behavior, and isolated data for
two clones. Check Play Store certification in the UI; do not infer it from timestamps.
Only then benchmark concurrency, CPU, memory, graphics and storage at the intended
fleet size. Do not report unseen guest capabilities as passed.

Protocol sources and the rejected handoff claims are recorded in
[HANDOFF-FACT-CHECK.md](HANDOFF-FACT-CHECK.md).
