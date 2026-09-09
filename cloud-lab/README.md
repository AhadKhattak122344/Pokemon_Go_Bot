# Android Virtualization Lab

**Production-ready Android virtualization fleet on Proxmox with Android 16 support.**

This system provides automated provisioning, management, and orchestration of Android VMs
on Proxmox/KVM hypervisors. It supports both the official Android emulator (API 34) and
Bliss OS 16.x for full Android 16 virtualization with Google Play Services compatibility.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PHYSICAL SERVER (Proxmox Host)                 │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Proxmox VE (Hypervisor)                    │ │
│  │                        KVM + QEMU                             │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                     │
│  ┌───────────────────────────┼───────────────────────────────────┐ │
│  │                           ▼                                   │ │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │   │ Template │  │Instance 1│  │Instance 2│  │Instance N│   │ │
│  │   │ (ID 9000)│  │ (10001)  │  │ (10002)  │  │ (1000N)  │   │ │
│  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  │        │             │             │             │           │ │
│  │        └─────────────┼─────────────┼─────────────┘           │ │
│  │                      │             │                         │ │
│  │                 ADB over TCP/IP (Port 5555)                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                     │
│                              ▼                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │          CONTROL PLANE (Python Services + PostgreSQL)        │ │
│  │  • Orchestrator (FastAPI + Proxmox API)                     │ │
│  │  • Identity Manager (Random IMEI/Android ID/MAC)            │ │
│  │  • Task Queue (Celery + Redis)                              │ │
│  │  • State Manager (PostgreSQL)                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

### Core Functionality
- **Proxmox Integration**: Full VM lifecycle management (create, clone, start, stop, reboot, delete)
- **Android 16 Support**: Bliss OS 16.9.7 GApps with Google Play Services
- **ADB Management**: Automatic device detection, connection, and command execution
- **Boot Detection**: Waits for Android `boot_completed` state
- **Health Checks**: VM status, Android boot completion, ADB connectivity

### Android VM Features
- **Google Play Services**: Certified device with Play Store access
- **Magisk Root**: Systemless root with Zygisk, Shamiko, and Play Integrity Fix
- **ARM Translation**: libhoudini for running ARM-native apps on x86_64
- **Device Identity**: Unique IMEI, Android ID, MAC address per instance
- **Device Spoofing**: Pixel 4 fingerprint for Play Store compatibility

## Quick Start

### Prerequisites
- Proxmox VE 7.0+ server with KVM support
- Linux x86_64 Ubuntu 22.04/24.04 host (for emulator mode)
- Docker Engine, Docker Compose v2, GNU Make
- Minimum: 4 vCPU, 8 GB RAM, 20 GB free SSD per Android instance

### Installation

```sh
cd cloud-lab
make build
make up
make smoke
make down
```

### CLI Usage

```sh
# Install Python CLI
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'

# Manage Android instances
lab up                              # Start emulator/VM
lab status                          # Check boot state
lab install --apk apks/your-app.apk # Install application
lab smoke                           # Run launch test
lab down                            # Stop instance

# Location testing
lab location set --lat 40.758 --lon -73.985
lab location follow --gpx config/routes/sample_city_walk.gpx --speed-mps 1.4

# Root management (emulator only)
lab root status
lab root enable
lab root disable
lab root self-test
```

### Configuration

Set `LAB_PROFILE=nested-virt` for KVM acceleration. Configuration defaults to
`config/default.yaml`; `--config` accepts another file.

Environment variable overrides:
- `ADB_SERVER_SOCKET`: ADB server connection
- `LAB_SERIAL`: Device serial number
- `LAB_ARTIFACTS`: Output directory

## Proxmox VM Management

The system includes a complete Proxmox client for Android VM operations:

```python
from orchestrator.proxmox import ProxmoxClient, VmConfig

# Initialize client
client = ProxmoxClient(
    host="proxmox.example.com",
    username="root@pam",
    password="secret",
)

# Clone Android template
config = VmConfig(
    vm_id=10001,
    name="android-1",
    cores=4,
    memory_mb=8192,
    disk_size_gb=64,
)

result = client.clone_vm(template_id=9000, config=config)
client.start_vm(10001)
```

### Supported Operations
- `clone_vm()` - Clone from template
- `start_vm()` / `stop_vm()` / `reboot_vm()` - Lifecycle control
- `get_vm_status()` - Query running state
- `get_vm_config()` - Get VM configuration
- `delete_vm()` - Remove VM
- `convert_to_template()` - Create template from VM
- `list_vms()` - List all VMs

## Android 16 Setup (Bliss OS)

### Critical Notes

**Bliss OS Status**: The official project has stopped publishing new public images.
Existing builds (16.9.7) are available and stable, but monitor the Bliss OS status
page for updates.

### Required Components
1. **Bliss OS 16.9.7 GApps** - Must use GApps version (includes Google Play Services)
2. **Magisk 30.7** - Systemless root management
3. **Zygisk Next 1.5.0+** - Runtime hooking
4. **Shamiko 0.7.0+** - Root hiding
5. **Play Integrity Fix v18.2+** - Attestation spoofing
6. **libhoudini** - ARM translation for x86_64
7. **LSPosed** - Xposed framework replacement
8. **Device Emulator** - Identity spoofing module

### VM Creation Steps

1. Download Bliss OS ISO:
```sh
wget https://sourceforge.net/projects/blissos-x86/files/Official/BlissOS16/Gapps/Generic/Bliss-v16.9.7-x86_64-OFFICIAL-gapps-20241011.iso
```

2. Upload to Proxmox and create template VM (ID 9000)

3. Install Magisk and modules via ADB

4. Configure device fingerprint (Pixel 4 recommended)

5. Convert to template for cloning

See the handoff document for detailed setup instructions.

## Testing

The smoke test launches the configured app, waits for its ready activity, checks
the crash buffer, and writes artifacts (screenshot, logcat, dumpsys, metadata, JUnit XML).

```sh
make smoke
# or
lab smoke
```

Artifacts are written to `artifacts/<timestamp>-<uuid>/`:
- `launch.png` - Screenshot
- `logcat.txt` - System logs
- `dumpsys_location.txt` - Location service state
- `meta.json` - Test metadata
- `junit.xml` - Test results

## Build Reproducibility

Command-line-tools build 11076708 and direct Python dependencies are pinned. SDK
manager's emulator, platform-tools, Android 14 image revisions, and OS package
updates may change upstream; archive built image digests for reproducible CI.

## Scope Limitations

The following are **not** implemented in this repository:
- noVNC web console
- Infrastructure provisioning scripts
- Managed PaaS integration
- Identity spoofing automation (manual Magisk module installation)
- Attestation bypass automation
- External backend automation

## Official References

- [Emulator architecture and acceleration](https://developer.android.com/studio/run/emulator-acceleration)
- [Emulator CLI](https://developer.android.com/studio/run/emulator-commandline)
- [SDK manager](https://developer.android.com/tools/sdkmanager)
- [ROOT-CONTROLS.md](docs/ROOT-CONTROLS.md) - Debug root operations

## Troubleshooting

### Common Issues

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| "No eligible devices" | Missing device fingerprint | Apply Pixel 4 fingerprint via MagiskHide Props Config |
| "Device not compatible" | ARM translation not working | Verify `ro.dalvik.vm.native.bridge=houdini` |
| "App crashes" | libhoudini not installed | Reinstall magisk_libhoudini module |
| "Root detected" | Shamiko not configured | Enable DenyList, add target app |
| "Play Integrity fails" | Outdated PIF module | Update Play Integrity Fix |
| "Device not certified" | GSF data needs reset | Clear GMS/GSF, wait 15 min |
| "Slow performance" | Insufficient resources | Increase CPU/RAM allocation |

## License

MIT License
