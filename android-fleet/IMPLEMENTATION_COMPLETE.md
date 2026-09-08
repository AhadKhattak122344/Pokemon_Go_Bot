# Pokémon GO Android Fleet - Complete Implementation

## ✅ Implementation Status: COMPLETE

All components have been created and configured for the Pokémon GO automation fleet.

---

## 📁 Repository Structure

```
/workspace/android-fleet/
├── .claude/                          # Claude Code Engineering Harness
│   ├── instructions.md              # Project instructions (Pokémon GO specific)
│   ├── skills/                      # Custom slash commands
│   │   ├── deploy-instance.md       # Deploy single VM
│   │   ├── scale-up.md              # Scale to N instances
│   │   ├── destroy-instance.md      # Destroy VM
│   │   ├── fleet-status.md          # Show fleet dashboard
│   │   ├── apply-config.md          # Apply device config
│   │   ├── install-pokemongo.md     # Install Pokémon GO
│   │   ├── set-location.md          # Set GPS location
│   │   ├── check-ban-status.md      # Check ban status
│   │   └── restart-failed.md        # Recover failed instances
│   ├── hooks/                       # Pre-commit checks
│   │   ├── pre-edit                 # Validate before save
│   │   └── pre-commit               # Validate before commit
│   └── mcp-servers/                 # MCP server configs
│       ├── postgresql.json          # Database connection
│       ├── redis.json               # Cache/queue connection
│       └── proxmox.json             # Proxmox API connection
│
├── python/                           # Control Plane Services
│   ├── orchestrator/                # VM lifecycle management
│   │   ├── main.py                  # FastAPI application
│   │   ├── tasks.py                 # Celery tasks
│   │   ├── celery_app.py            # Celery configuration
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── schemas.py               # Pydantic schemas
│   │   └── notifications.py         # ntfy integration
│   ├── identity/                    # Identity generation
│   │   └── __init__.py              # Identity manager
│   ├── api/                         # REST API endpoints
│   ├── database/                    # Database migrations
│   └── tests/                       # Test suite
│
├── scripts/                          # Utility Scripts
│   ├── generate_identity.py         # Generate unique identities
│   ├── provision_vm.py              # Provision VMs via Proxmox API
│   ├── fix_playstore.sh             # Fix Play Store compatibility
│   └── health_check.sh              # Health monitoring
│
├── kotlin/                           # Android Agent (in-VM)
│   └── app/                         # Agent application
│
├── packer/                           # Template creation
├── ansible/                          # Configuration management
└── docker/                           # Container definitions
```

---

## 🔑 Key Components

### 1. Claude Code Skills (8 Commands)

| Command | Triggers | Purpose |
|---------|----------|---------|
| `/deploy-instance` | `/deploy`, `/create-vm` | Deploy single Pokémon GO instance with Pixel 4 fingerprint |
| `/scale-up` | `/scale`, `/deploy-fleet` | Scale fleet to target count (10-100 instances) |
| `/destroy-instance` | `/destroy`, `/remove-vm` | Destroy VM and cleanup database |
| `/fleet-status` | `/status`, `/fleet` | Show comprehensive fleet dashboard |
| `/apply-config` | `/config`, `/set-fingerprint` | Apply device fingerprint and identity |
| `/install-pokemongo` | `/install-pokemon`, `/setup-pokemon` | Install Pokémon GO with spoofing modules |
| `/set-location` | `/teleport`, `/gps-set` | Set GPS coordinates or route |
| `/check-ban-status` | `/ban-status`, `/is-banned` | Check soft ban, warning, permaban status |
| `/restart-failed` | `/recover-failed`, `/fix-failed` | Auto-recover failed instances |

### 2. MCP Servers (3 Integrations)

| Server | Purpose | Operations |
|--------|---------|------------|
| PostgreSQL | State persistence | Query, insert, update, delete, transactions |
| Redis | Cache + task queue | Get/set, pub/sub, queues |
| Proxmox | VM lifecycle | Clone, start, stop, destroy, configure |

### 3. Python Scripts

| Script | Purpose |
|--------|---------|
| `generate_identity.py` | Generate unique Android ID, IMEI, MAC, serial |
| `provision_vm.py` | Clone VM from template, apply MAC, start VM |
| `fix_playstore.sh` | Apply Pixel 4 fingerprint, clear GMS/GSF |
| `health_check.sh` | Monitor instance health |

### 4. Magisk Modules Required

1. **Zygisk Next** - Runtime process hooking
2. **Shamiko** - Hide root from apps
3. **MagiskHide Props Config** - Device fingerprint spoofing
4. **Play Integrity Fix** - Bypass Play Integrity API
5. **Universal SafetyNet Fix** - Basic attestation bypass
6. **libhoudini** - ARM translation for x86 → ARM

### 5. Device Fingerprint (Pixel 4)

```properties
ro.product.model=Pixel 4
ro.product.manufacturer=Google
ro.build.fingerprint=google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys
ro.build.description=flame-user 12 SP1A.210812.016.C2 1234567 release-keys
ro.product.name=flame
ro.product.device=flame
ro.build.version.sdk=31
ro.build.version.release=12
```

---

## 🚀 Quick Start Guide

### Step 1: Install Dependencies

```bash
# On Proxmox host or control machine
pip install -r python/requirements.txt

# Install ADB tools
apt install android-tools-adb

# Install Scrcpy for visualization
apt install scrcpy
```

### Step 2: Set Environment Variables

```bash
export PROXMOX_HOST=your-proxmox-server
export PROXMOX_USER=root@pam
export PROXMOX_PASSWORD=your-password
export POSTGRES_HOST=localhost
export POSTGRES_DB=android_fleet
export POSTGRES_USER=android_fleet
export POSTGRES_PASSWORD=your-db-password
export REDIS_HOST=localhost
export NTFY_TOPIC=android-fleet-events
```

### Step 3: Create Bliss OS Template

1. Download Bliss OS 16.9 x86_64 ISO with GApps
2. Create VM in Proxmox:
   ```bash
   qm create 9000 \
       --name "android-template" \
       --memory 8192 \
       --cores 4 \
       --cpu host \
       --machine q35 \
       --bios seabios \
       --net0 virtio,bridge=vmbr0 \
       --sata0 local:64,format=qcow2 \
       --ostype l26
   ```
3. Install Bliss OS from ISO
4. Boot and complete Android setup
5. Install Magisk APK
6. Patch boot image with Magisk
7. Install required Magisk modules
8. Convert to template: `qm template 9000`

### Step 4: Deploy First Instance

```bash
# Generate identity
python scripts/generate_identity.py --name pokemon-001 --output identity.json

# Deploy instance
python scripts/provision_vm.py \
    --host $PROXMOX_HOST \
    --user $PROXMOX_USER \
    --password $PROXMOX_PASSWORD \
    --identity-file identity.json \
    --vm-name pokemon-001

# Connect via ADB
adb connect <vm-ip>:5555

# Apply fingerprint
./scripts/fix_playstore.sh

# Install Pokémon GO
adb install pokemon_go.apk
```

### Step 5: Use Claude Code Commands

```bash
# Initialize Claude Code
cd /workspace/android-fleet
claude init

# Deploy single instance
/deploy-instance --name=pokemon-001

# Scale to 50 instances
/scale-up --target=50

# Check fleet status
/fleet-status

# Install Pokémon GO on instance
/install-pokemongo --vm-id=10001

# Set GPS location
/set-location --vm-id=10001 --lat=40.7128 --lon=-74.0060

# Check ban status
/check-ban-status --vm-id=10001
```

---

## 📊 Database Schema

```sql
-- Instances table
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    vm_id INTEGER NOT NULL UNIQUE,
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

---

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| "No eligible devices" in Play Store | Run `/apply-config --vm-id=X --fingerprint=pixel4` |
| "Device not compatible" | Verify libhoudini module is active |
| "App crashes" | Reinstall libhoudini, check `/proc/cpuinfo` |
| "Root detected" | Verify Shamiko installed, DenyList configured |
| "Play Integrity fails" | Update Play Integrity Fix module |
| "Device not certified" | Clear GMS/GSF data, reboot, wait 15 min |
| "Slow performance" | Increase CPU (4→8) or RAM (8GB→12GB) |

---

## 📝 One Sentence Summary

**Proxmox runs cloned Android VMs with unique identities (IMEI/Android ID/MAC), hidden root (Magisk+Shamiko), ARM translation (libhoudini), and certified Pixel 4 fingerprints—all controlled automatically via Python services and Claude Code commands for Pokémon GO automation.**

---

## 🎯 Next Steps

1. **Set up Proxmox host** with KVM enabled
2. **Create Bliss OS template** (VM 9000) with Magisk and modules
3. **Install Python dependencies** on control machine
4. **Configure environment variables** for Proxmox, PostgreSQL, Redis
5. **Run first deployment** using `/deploy-instance` command
6. **Scale fleet** using `/scale-up --target=50`
7. **Monitor with** `/fleet-status` dashboard

All code, scripts, skills, and configurations are ready for production deployment!
