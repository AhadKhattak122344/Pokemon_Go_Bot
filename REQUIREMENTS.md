# Android Virtualization Fleet - Complete Requirements Specification

## Executive Summary

This document provides comprehensive technical requirements for deploying and managing an Android virtualization fleet on Proxmox VE. The design focuses on creating isolated, uniquely identifiable Android virtual machines that can be provisioned, controlled, and monitored through an automated orchestration layer.

---

## 1. Infrastructure Requirements

### 1.1 Hardware Specifications

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Processor | 8 cores x86_64 | 64+ cores (AMD EPYC/Intel Xeon) |
| RAM | 64GB | 256GB+ |
| Storage | 1TB NVMe | 4TB+ NVMe RAID10 |
| Network | 1Gbps | 10Gbps+ |

### 1.2 Software Requirements

| Component | Version |
|-----------|---------|
| Proxmox VE | 7.0+ |
| Virtualization | KVM |
| Storage Backend | LVM-Thin or ZFS |
| Network Bridge | Linux Bridge (vmbr0) |

---

## 2. Android VM Configuration Requirements

### 2.1 Template Specification

| Parameter | Required Value |
|-----------|---------------|
| OS | Bliss OS 16.9 x86_64 with GApps |
| Machine | q35 |
| BIOS | SeaBIOS |
| CPU Type | host |
| CPU Cores | 4 |
| RAM | 8192 MB |
| Disk Controller | sata |
| Disk Format | qcow2 |
| Disk Size | 64 GB |
| Network Model | virtio |
| Display | std |

### 2.2 Resource Scaling

| Instances | CPU Cores | RAM (GB) | Storage (GB) | Nodes |
|-----------|-----------|----------|--------------|-------|
| 10 | 40 | 80 | 640 | 1 |
| 25 | 100 | 200 | 1600 | 2 |
| 50 | 200 | 400 | 3200 | 4 |
| 100 | 400 | 800 | 6400 | 8 |

---

## 3. Root & System Modification Requirements

### 3.1 Magisk Requirements

| Requirement | Specification |
|-------------|---------------|
| Version | Magisk 26.3+ |
| Root Type | Systemless |
| Installation | Boot image patching |
| Zygisk | Enabled |
| DenyList | Enforced |

### 3.2 Required Magisk Modules

| Module | Purpose |
|--------|---------|
| Zygisk Next | Runtime process hooking |
| Shamiko | Root detection evasion |
| MagiskHide Props Config | Device fingerprint spoofing |
| Play Integrity Fix | Play Integrity API bypass |
| Universal SafetyNet Fix | SafetyNet bypass |
| libhoudini | ARM translation |

### 3.3 Magisk Installation Steps

**Step 1: Install Magisk APK**
```bash
adb install magisk.apk
```

**Step 2: Extract Boot Image**
```bash
adb shell dd if=/dev/block/by-name/boot of=/sdcard/boot.img
adb pull /sdcard/boot.img
```

**Step 3: Patch with Magisk**
- Open Magisk app
- Select "Install" → "Select and Patch a File"
- Choose boot.img
- Generate patched image

**Step 4: Flash Patched Image**
```bash
adb push magisk_patched_boot.img /sdcard/
adb shell dd if=/sdcard/magisk_patched_boot.img of=/dev/block/by-name/boot
adb reboot
```

**Step 5: Install Modules**
```bash
# Push modules
adb push module_name.zip /sdcard/

# Install each module via Magisk
adb shell su -c "magisk --install-module /sdcard/zygisk_next.zip"
adb shell su -c "magisk --install-module /sdcard/shamiko.zip"
adb shell su -c "magisk --install-module /sdcard/magiskhide_props_config.zip"
adb shell su -c "magisk --install-module /sdcard/play_integrity_fix.zip"
adb shell su -c "magisk --install-module /sdcard/libhoudini.zip"

# Reboot after all modules installed
adb reboot
```

### 3.4 Magisk Configuration Steps

```bash
# Enable Zygisk
adb shell su -c "magisk --enable-zygisk"

# Enable Magisk Hide
adb shell su -c "magiskhide enable"

# Add packages to DenyList
adb shell su -c "magiskhide add com.google.android.gms"
adb shell su -c "magiskhide add com.google.android.gms.persistent"
adb shell su -c "magiskhide add com.google.android.gms.unstable"
adb shell su -c "magiskhide add com.google.android.gsf"
adb shell su -c "magiskhide add com.android.vending"
```

### 3.5 Configure MagiskHide Props Config

```bash
# Open props configuration
adb shell su -c "props"

# Menu navigation:
# 1 - Edit fingerprint
# 2 - Google
# 3 - Pixel 4 (or similar certified device)
# Confirm selection
# Reboot
```

---

## 4. Device Identity Requirements

### 4.1 Identity Components

| Component | Format | Uniqueness |
|-----------|--------|------------|
| Android ID | 16-char hex | Global |
| IMEI | 15 digits | Global |
| MAC Address | 6-byte hex | Global |
| Serial Number | 16-char alphanumeric | Global |
| Model | String | Rotating |
| Manufacturer | String | Rotating |

### 4.2 Device Fingerprint Requirements

| Property | Required Value |
|----------|---------------|
| ro.product.model | Pixel 4 |
| ro.product.manufacturer | Google |
| ro.build.fingerprint | google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys |
| ro.build.description | flame-user 12 SP1A.210812.016.C2 1234567 release-keys |
| ro.product.name | flame |
| ro.product.device | flame |
| ro.build.version.sdk | 31 |
| ro.build.version.release | 12 |

### 4.3 Apply Fingerprint

```bash
# Apply fingerprint
adb shell su -c "setprop ro.product.model Pixel 4"
adb shell su -c "setprop ro.product.manufacturer Google"
adb shell su -c "setprop ro.build.fingerprint google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys"
adb shell su -c "setprop ro.build.description flame-user 12 SP1A.210812.016.C2 1234567 release-keys"
adb shell su -c "setprop ro.product.name flame"
adb shell su -c "setprop ro.product.device flame"
adb shell su -c "setprop ro.build.version.sdk 31"
adb shell su -c "setprop ro.build.version.release 12"

# Make permanent via build.prop
adb shell su -c "sed -i 's/ro.product.model=.*/ro.product.model=Pixel 4/g' /system/build.prop"
adb shell su -c "sed -i 's/ro.product.manufacturer=.*/ro.product.manufacturer=Google/g' /system/build.prop"
adb shell su -c "echo 'ro.build.fingerprint=google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys' >> /system/build.prop"
```

### 4.4 LSPosed/Device Spoofing

```bash
# Install LSPosed via Magisk
adb shell su -c "magisk --install-module /sdcard/lsposed.zip"
adb reboot

# Install Device Emulator module
adb shell su -c "magisk --install-module /sdcard/device_emulator.zip"
adb reboot

# Push device configuration
cat > device_config.json << EOF
{
  "android_id": "1234567890abcdef",
  "imei": "352123456789012",
  "serial": "ABCDEF123456",
  "model": "Pixel 4",
  "manufacturer": "Google"
}
EOF

adb push device_config.json /sdcard/
adb shell su -c "cp /sdcard/device_config.json /data/data/com.device.emulator/config.json"
```

---

## 5. ARM Translation Requirements

### 5.1 Configuration Flags

```bash
# Enable ARM translation
adb shell su -c "setprop persist.sys.nativebridge 1"
adb shell su -c "setprop persist.sys.armv7a 1"
adb shell su -c "setprop persist.sys.armv8a 1"

# Set CPU ABI
adb shell su -c "setprop ro.product.cpu.abilist arm64-v8a,armeabi-v7a,armeabi"
adb shell su -c "setprop ro.product.cpu.abilist32 armeabi-v7a,armeabi"
```

### 5.2 Verification

```bash
# Verify ARM translation is working
adb shell "cat /proc/cpuinfo | grep -i arm"
# Should show ARMv7 or similar
```

---

## 6. ADB Control Requirements

### 6.1 ADB Configuration

```bash
# Enable ADB over TCP
adb shell su -c "setprop persist.adb.tcp.port 5555"
adb shell su -c "setprop service.adb.tcp.port 5555"

# Restart ADB daemon
adb shell su -c "stop adbd"
adb shell su -c "start adbd"

# Connect to instance
adb connect <instance-ip>:5555
```

### 6.2 Essential ADB Commands

| Category | Command | Purpose |
|----------|---------|---------|
| System | `adb shell getprop` | Retrieve properties |
| System | `adb shell setprop` | Set properties |
| Packages | `adb install app.apk` | Install application |
| Activity | `adb shell am start` | Launch app |
| Files | `adb push/pull` | Transfer files |
| Screen | `adb screencap` | Capture screen |
| Input | `adb shell input tap` | Simulate touch |

---

## 7. Python Control Plane Requirements

### 7.1 Required Services

| Service | Responsibility | Technology |
|---------|---------------|------------|
| Orchestrator | VM lifecycle management | FastAPI + Proxmox API |
| Identity Manager | Generate device identities | Python |
| Task Queue | Schedule jobs | Celery + Redis |
| State Manager | Track instances | PostgreSQL + Redis |

### 7.2 API Endpoints Required

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/instances` | POST | Create new instance |
| `/instances/{id}` | GET | Get instance status |
| `/instances/{id}` | DELETE | Destroy instance |
| `/instances/{id}/start` | POST | Start instance |
| `/instances/{id}/stop` | POST | Stop instance |
| `/instances/{id}/app` | POST | Install application |
| `/instances/{id}/command` | POST | Execute ADB command |

### 7.3 Proxmox API Integration

```python
# Authentication
POST /api2/json/access/ticket
Data: username, password

# Clone VM
POST /api2/json/nodes/{node}/qemu/{vmid}/clone
Data: newid, name, full=1

# Start VM
POST /api2/json/nodes/{node}/qemu/{vmid}/status/start

# Stop VM
POST /api2/json/nodes/{node}/qemu/{vmid}/status/stop

# Destroy VM
DELETE /api2/json/nodes/{node}/qemu/{vmid}
```

### 7.4 Database Schema

```sql
-- Instances table
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    vm_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    identity JSONB NOT NULL,
    config JSONB
);

-- Identity profiles
CREATE TABLE identity_profiles (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id),
    android_id VARCHAR(32) NOT NULL,
    imei VARCHAR(15) NOT NULL,
    mac_address VARCHAR(17) NOT NULL,
    serial VARCHAR(32) NOT NULL,
    model VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(50) NOT NULL,
    fingerprint TEXT NOT NULL
);

-- Task history
CREATE TABLE task_history (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id),
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    result JSONB
);
```

### 7.5 Redis Configuration

| Structure | Key Pattern | Purpose |
|-----------|-------------|---------|
| Hash | `instance:{id}:status` | Instance status |
| Set | `instances:running` | Active instances |
| List | `task:queue` | Task scheduling |
| List | `task:results` | Task results |
| Hash | `instance:{id}:config` | Configuration cache |

---

## 8. Notification Requirements

### 8.1 ntfy Integration

```bash
# Install ntfy client
pip install ntfy

# Send notification
ntfy publish android-fleet "Instance 42 deployed successfully"

# Subscribe to notifications
ntfy subscribe android-fleet
```

### 8.2 Event Types

| Event | Trigger |
|-------|---------|
| Instance Deployed | VM created and configured |
| Instance Started | VM booted |
| Instance Stopped | VM shutdown |
| Instance Failed | Error condition |
| Task Complete | Job finished |

---

## 9. Claude Code Engineering Harness Requirements

### 9.1 Installation

```bash
# Install Claude Code
npm install -g @anthropic/claude-code

# Navigate to repository
cd /path/to/repo

# Initialize Claude Code
claude init
```

### 9.2 Required Files

```
.claude/
├── instructions.md          # Project instructions
├── skills/                  # Custom slash commands
│   ├── deploy-instance.md
│   ├── scale-up.md
│   ├── destroy-instance.md
│   ├── fleet-status.md
│   └── apply-config.md
├── hooks/                   # Pre-commit hooks
│   ├── pre-edit
│   └── pre-commit
├── ignore                   # Excluded files
└── mcp-servers/            # MCP server configs
    ├── postgresql.json
    ├── redis.json
    └── proxmox.json
```

### 9.3 Project Instructions (CLAUDE.md)

```markdown
# Project Architecture
- Python services: Control plane (FastAPI + Proxmox API)
- Kotlin agent: Android instance management
- Proxmox: Virtualization infrastructure
- PostgreSQL: State persistence
- Redis: Caching and task queues

# Coding Standards
- Python: PEP8, type hints, docstrings
- Kotlin: Android coding conventions

# Deployment Process
1. Generate identity
2. Clone VM from template
3. Apply configuration
4. Start instance
5. Verify operation
6. Register in database
```

### 9.4 Required Skills

**/deploy-instance**
- Generate unique identity
- Clone VM via Proxmox API
- Apply fingerprint
- Start instance
- Verify operation
- Send notification

**/scale-up**
- Check current instance count
- Deploy new instances in parallel
- Verify all instances healthy
- Report deployment status

**/destroy-instance**
- Stop VM
- Destroy VM
- Remove from database
- Cleanup storage

**/fleet-status**
- Query all instances
- Show resource usage
- Identify failed instances
- Show pending tasks

**/apply-config**
- Validate configuration
- Push via ADB
- Verify application
- Confirm success

---

## 10. Deployment Script Requirements

### 10.1 Identity Generation Script

```bash
#!/bin/bash
# generate_identity.sh

# Generate Android ID (16-char hex)
ANDROID_ID=$(openssl rand -hex 8)

# Generate IMEI (15 digits)
TAC=$(printf "%06d" $((RANDOM % 1000000)))
FAC=$(printf "%02d" $((RANDOM % 100)))
SNR=$(printf "%06d" $((RANDOM % 1000000)))
IMEI="${TAC}${FAC}${SNR}"

# Generate MAC Address
MAC="00:16:3E:$(openssl rand -hex 3 | sed 's/\(..\)/\1:/g' | sed 's/:$//')"

# Generate Serial Number
SERIAL=$(openssl rand -hex 8 | tr 'a-z' 'A-Z')

# Output JSON
cat << EOF
{
  "android_id": "$ANDROID_ID",
  "imei": "$IMEI",
  "mac_address": "$MAC",
  "serial": "$SERIAL",
  "model": "Pixel 4",
  "manufacturer": "Google"
}
EOF
```

### 10.2 VM Provisioning Script

```python
#!/usr/bin/env python3
# provision_vm.py

import requests
import json
import secrets
import subprocess

class ProxmoxClient:
    def __init__(self, host, username, password):
        self.host = host
        self.base_url = f"https://{host}:8006/api2/json"
        self.session = requests.Session()
        self.session.verify = False
        self.authenticate(username, password)
    
    def authenticate(self, username, password):
        response = self.session.post(
            f"{self.base_url}/access/ticket",
            data={"username": username, "password": password}
        )
        data = response.json()["data"]
        self.token = data["ticket"]
        self.csrf_token = data["CSRFPreventionToken"]
        self.session.headers.update({
            "Authorization": f"PVEAPITicket={self.token}",
            "CSRFPreventionToken": self.csrf_token
        })
    
    def clone_vm(self, template_id, new_id, name):
        response = self.session.post(
            f"{self.base_url}/nodes/proxmox/qemu/{template_id}/clone",
            data={"newid": new_id, "name": name, "full": 1}
        )
        return response.json()
    
    def start_vm(self, vm_id):
        response = self.session.post(
            f"{self.base_url}/nodes/proxmox/qemu/{vm_id}/status/start"
        )
        return response.json()
    
    def stop_vm(self, vm_id):
        response = self.session.post(
            f"{self.base_url}/nodes/proxmox/qemu/{vm_id}/status/stop"
        )
        return response.json()
    
    def destroy_vm(self, vm_id):
        response = self.session.delete(
            f"{self.base_url}/nodes/proxmox/qemu/{vm_id}"
        )
        return response.json()

def deploy_instance(identity, vm_name):
    # Generate unique VM ID
    vm_id = 10000 + int(secrets.randbits(16) % 1000)
    
    # Clone from template
    client = ProxmoxClient("proxmox-host", "root", "password")
    client.clone_vm(9000, vm_id, vm_name)
    
    # Apply MAC address
    mac = identity["mac_address"]
    client.session.post(
        f"{client.base_url}/nodes/proxmox/qemu/{vm_id}/config",
        data={"net0": f"virtio,macaddr={mac},bridge=vmbr0"}
    )
    
    # Start VM
    client.start_vm(vm_id)
    
    # Wait for ADB
    import time
    time.sleep(30)
    
    # Apply fingerprint via ADB
    ip = get_vm_ip(vm_id)
    apply_fingerprint(ip, identity)
    
    return vm_id

def apply_fingerprint(ip, identity):
    # Connect via ADB
    subprocess.run(["adb", "connect", f"{ip}:5555"])
    
    # Apply properties
    props = {
        "ro.product.model": identity["model"],
        "ro.product.manufacturer": identity["manufacturer"],
        "ro.build.fingerprint": identity["fingerprint"]
    }
    
    for key, value in props.items():
        subprocess.run(["adb", "shell", "su", "-c", f"setprop {key} '{value}'"])
    
    # Clear Google Services
    subprocess.run(["adb", "shell", "pm", "clear", "com.google.android.gms"])
    subprocess.run(["adb", "shell", "pm", "clear", "com.google.android.gsf"])
    subprocess.run(["adb", "shell", "pm", "clear", "com.android.vending"])
```

### 10.3 Play Store Fix Script

```bash
#!/bin/bash
# fix_playstore.sh

echo "Fixing Play Store compatibility..."

# Apply Pixel fingerprint
adb shell su -c "setprop ro.product.model Pixel 4"
adb shell su -c "setprop ro.product.manufacturer Google"
adb shell su -c "setprop ro.build.fingerprint google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys"

# Clear Google services
adb shell pm clear com.google.android.gms
adb shell pm clear com.google.android.gsf
adb shell pm clear com.android.vending

# Clear cache
adb shell su -c "rm -rf /data/data/com.google.android.gms/cache/*"
adb shell su -c "rm -rf /data/data/com.google.android.gsf/cache/*"

# Reboot
adb reboot

echo "Waiting for reboot..."
adb wait-for-device
sleep 30

echo "Verifying..."
adb shell "getprop ro.product.model"
adb shell "getprop ro.build.fingerprint"

echo "✓ Device compatibility fixes applied!"
echo "✓ Wait 5-15 minutes for Play Store certification"
```

---

## 11. Monitoring Requirements

### 11.1 Health Check Script

```bash
#!/bin/bash
# health_check.sh

check_instance() {
    local ip=$1
    
    # Check ADB connectivity
    if ! adb connect "$ip:5555" 2>/dev/null; then
        echo "ERROR: ADB connection failed"
        return 1
    fi
    
    # Check system properties
    model=$(adb shell getprop ro.product.model 2>/dev/null)
    if [ "$model" != "Pixel 4" ]; then
        echo "ERROR: Device model mismatch"
        return 1
    fi
    
    # Check Google Services
    gms=$(adb shell pm path com.google.android.gms 2>/dev/null)
    if [[ ! "$gms" =~ "package:" ]]; then
        echo "ERROR: Google Play Services missing"
        return 1
    fi
    
    echo "OK: Instance $ip healthy"
    return 0
}

# Usage
for ip in $(cat /etc/hosts | grep android | awk '{print $1}'); do
    check_instance "$ip"
done
```

### 11.2 Metrics Collection

```bash
# Collect VM metrics via Proxmox API
curl -s -k -H "Authorization: PVEAPITicket=$TOKEN" \
  "https://proxmox:8006/api2/json/nodes/proxmox/qemu/$VM_ID/status/current" \
  | jq '.data | {cpu: .cpu, memory: .mem, disk: .disk}'
```

---

## 12. Quick Start Checklist

### 12.1 Infrastructure Setup
- [ ] Install Proxmox VE
- [ ] Configure network bridge (vmbr0)
- [ ] Create storage pool (local-lvm)
- [ ] Verify KVM acceleration

### 12.2 Android Template
- [ ] Download Bliss OS 16.9 ISO
- [ ] Create VM with correct hardware
- [ ] Install Bliss OS
- [ ] Configure Google Play Services
- [ ] Install Magisk
- [ ] Install required modules
- [ ] Apply device fingerprint
- [ ] Enable ARM translation
- [ ] Convert to template

### 12.3 Control Plane
- [ ] Install Python 3.9+
- [ ] Install PostgreSQL
- [ ] Install Redis
- [ ] Deploy Python services
- [ ] Configure database schema
- [ ] Setup task queue (Celery + Redis)

### 12.4 Automation
- [ ] Write identity generation script
- [ ] Write VM provisioning script
- [ ] Configure Proxmox API client
- [ ] Test ADB connectivity
- [ ] Verify fingerprint application
- [ ] Test Play Store compatibility

### 12.5 Claude Code
- [ ] Install Claude Code
- [ ] Create CLAUDE.md
- [ ] Setup MCP servers
- [ ] Create skills
- [ ] Configure hooks

---

## 13. Troubleshooting Quick Reference

| Problem | Check | Solution |
|---------|-------|----------|
| Play Store no eligible devices | Device fingerprint | Apply Pixel fingerprint |
| App not compatible | ARM translation | Verify /proc/cpuinfo shows ARM |
| Device not certified | GSF registration | Clear GMS/GSF data, reboot, wait 15 min |
| ADB connection refused | ADB port | Set persist.adb.tcp.port=5555 |
| App crashes | ARM translation | Reinstall libhoudini module |
| Identity not unique | Check generation script | Ensure random generation works |
| VM won't start | Proxmox API | Check logs: qm status <vmid> |

---

## 14. Summary

This system enables:

- **Hundreds of Android VMs** running on Proxmox servers
- **Unique device identities** per instance (Android ID, IMEI, MAC, serial)
- **Full Play Store compatibility** with certified device fingerprint
- **Complete remote control** via ADB and Scrcpy
- **Automated deployment** via Python services + Proxmox API
- **AI-assisted development** with Claude Code engineering harness
- **Scalability** from 10 to 100+ instances with horizontal scaling

---

## Appendix A: Docker Emulator Lab (Current Implementation)

### Current Build Status: ✅ VERIFIED

| Component | Android Version | Image Type | AVD Name | ADB Port | Device |
|-----------|----------------|------------|----------|----------|--------|
| Dockerfile.emulator | API 34 (Android 14) | google_apis_playstore x86_64 | baseline | 5554 | Pixel 6 |
| start_emulator.sh | - | - | baseline | 5554→5555 relay | - |
| docker-compose.yml | - | - | baseline | 5554:5554 | - |
| config/default.yaml | API 34 | - | baseline | - | - |
| README.md | API 34 | google_apis_playstore | baseline | 5554 | Pixel 6 |

### How It Works Now

#### Part 1: Docker Emulator Lab (Ready to Run)

```bash
cd cloud-lab
make build    # Builds SDK, downloads API 34 Google Play image, creates 'baseline' AVD, compiles app
make up       # Starts emulator on port 5554, waits 900s for boot, installs APK, launches app
make smoke    # Verifies boot, launches activity, captures screenshot/logs, generates JUnit XML
make down     # Cleans up containers
```

**Build Flow:**
1. Downloads Android SDK command-line tools (build 11076708)
2. Installs `system-images;android-34;google_apis_playstore;x86_64`
3. Creates AVD named `baseline` with Pixel 6 device profile
4. Builds RegiBot app from `/workspace/recovered/`
5. Bundles APK into emulator image

**Runtime Flow:**
1. Emulator starts on port 5554 with software rendering (or KVM with `PROFILE=nested-virt`)
2. socat relays host:5554 → emulator:5555 (ADB)
3. ADB server runs on port 5037
4. Waits up to 900 seconds for `sys.boot_completed=1`
5. Auto-installs `/opt/regibot.apk`
6. Launches `com.juancavr6.regibot/.MainActivity`

#### Part 2: Proxmox VE Fleet Architecture (Documented)

Complete technical architecture for scalable Android VM deployment:
- **Platform:** Proxmox VE with KVM
- **OS:** Bliss OS 16.9 x86_64 (native KVM, libhoudini ARM translation, Magisk root)
- **Scaling:** 10-100 instances across 1-8 host nodes
- **Control Plane:** Python FastAPI + PostgreSQL + Redis + Celery
- **Identity:** Unique Android ID, IMEI, MAC, serial per instance
- **Provisioning:** Automated via Proxmox REST API

---

## Document Version

- **Version:** 1.0
- **Last Updated:** 2024
- **Status:** Complete Requirements Specification
