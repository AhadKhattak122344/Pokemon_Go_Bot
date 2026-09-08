# Android Virtualization Fleet on Proxmox VE - Technical Architecture

This document provides a comprehensive technical architecture for deploying and managing an Android virtualization fleet on Proxmox VE. The design focuses on creating isolated, uniquely identifiable Android virtual machines that can be provisioned, controlled, and monitored through an automated orchestration layer. This infrastructure is application-agnostic and designed for scalability, identity isolation, and operational efficiency.

## 1. Virtualization Platform Analysis

### 1.1 Hypervisor Foundation

Proxmox VE serves as the virtualization platform, providing KVM-based Type-1 hypervisor capabilities with enterprise management features.

**Core Capabilities:**

- Native KVM acceleration for near-bare-metal performance
- REST API for programmatic control of all operations
- Web-based management interface for manual administration
- Cluster support for horizontal scaling across physical hosts
- Built-in backup, snapshot, and restore functionality
- Storage management with support for multiple backends

### 1.2 Android Distribution Selection

| Distribution | Architecture | KVM Support | ARM Translation | Magisk Compatibility | Stability |
|-------------|-------------|-------------|-----------------|---------------------|-----------|
| Bliss OS | x86_64 | Native | libhoudini | Full | High |
| Android-x86 | x86_64 | Native | libndk_translation | Full | High |
| PrimeOS | x86_64 | Native | Proprietary | Limited | Medium |
| AOSP x86_64 | x86_64 | Native | Manual | Custom | Low |
| Android Cuttlefish | ARM64 | Nested | Native | Limited | Low |

**Recommended Distribution: Bliss OS 16.9**

**Justification:**

- Native x86_64 execution under KVM without nested virtualization overhead
- Built-in ARM translation layer (libhoudini) for app compatibility
- Full Magisk support for systemless root modifications
- Google Play Services integration with GApps build
- Active development community and regular updates
- Support for device fingerprint spoofing and hardware manipulation

### 1.3 Architecture Decision Points

**Path A: Nested ARM Emulation**

1. Create Linux VM in Proxmox
2. Run QEMU emulating ARM64 inside Linux VM
3. Run AOSP ARM64 image inside QEMU

**Result:** Genuine ARM architecture passes app compatibility checks

**Problem:** Severe performance penalty from nested virtualization (Proxmox → Linux VM → QEMU → ARM translation)

**Scalability:** Extremely poor, limited to 5-10 instances

**Path B: x86_64 with ARM Translation Layer**

1. Run Bliss OS/Android-x86 directly under KVM
2. Utilize built-in libhoudini/NDK translation
3. Spoof translation layer to appear as native ARM

**Result:** Native x86_64 performance with app compatibility

**Performance:** Near-bare-metal with KVM acceleration

**Scalability:** Excellent, limited only by hardware resources

**Selected Architecture: Path B**

This approach balances performance, compatibility, and scalability by leveraging:

- Native x86_64 execution with KVM acceleration
- ARM translation layer for application compatibility
- Device fingerprint spoofing for identity management
- Complete control over the virtualization stack

## 2. VM Template Creation Process

### 2.1 Base VM Configuration

**Hardware Specifications:**

| Component | Configuration | Technical Rationale |
|-----------|--------------|---------------------|
| Machine Type | q35 | Modern chipset with PCIe support, better device pass-through capabilities |
| BIOS | SeaBIOS | More reliable boot compatibility for Android-x86 family, GRUB compatibility |
| CPU Type | Host | Enables host CPU feature flags for ARM translation optimization |
| CPU Cores | 4 | Adequate for OS + Play Services + application workloads |
| RAM | 8GB | Sufficient for Android runtime, Google Play Services, and application memory requirements |
| Disk Controller | SATA | Compatible with Bliss OS driver availability, avoids VirtIO issues |
| Disk Size | 64GB | Adequate for OS, pre-installed applications, and runtime data |
| Network | VirtIO | Native virtualization performance with low overhead |
| Display | Standard VGA | Base compatibility, upgradeable to VirtIO-GPU for acceleration |

### 2.2 Installation Procedure

**Phase 1: Template Creation**

```bash
# Create base VM with optimized settings
qm create 9000 \
    --name "android-template" \
    --memory 8192 \
    --cores 4 \
    --cpu host \
    --machine q35 \
    --bios seabios \
    --net0 virtio,bridge=vmbr0 \
    --scsihw virtio-scsi-single \
    --sata0 local:64,format=qcow2 \
    --ostype l26 \
    --boot order=sata0 \
    --vga std
```

**Phase 2: OS Installation**

1. **Download Bliss OS ISO**
   - Obtain Bliss OS 16.9 x86_64 with GApps from official repository
   - Verify checksum integrity

2. **Mount Installation Media**
   - Attach ISO to virtual CD-ROM via Proxmox interface or API
   - Configure boot order to prioritize CD-ROM

3. **Perform Installation**
   - Boot from ISO
   - Select full installation (not Live mode)
   - Partition virtual disk:
     - GPT partition table
     - system partition (ext4)
     - data partition (ext4, for user data)
     - cache partition (ext4)
   - Install GRUB bootloader to disk
   - Complete installation and remove installation media

4. **Initial Boot Configuration**
   - Boot into installed Android
   - Complete Android setup wizard
   - Sign into Google account (provisions Play Store)
   - Allow Play Store to update Google Play Services
   - Install core applications

**Phase 3: Post-Installation Cleanup**

- Remove temporary files
- Clear application cache
- Reset advertising ID
- Configure default settings
- Install management applications
- Perform final reboot

### 2.3 Root Configuration (Magisk)

**Root Setup Process:**

1. **Install Magisk APK**
   - Sideload Magisk APK (not available on Play Store)
   - Open Magisk application

2. **Extract Boot Image**
   - Identify boot partition location: `/dev/block/by-name/boot`
   - Extract current boot image:

```bash
adb shell dd if=/dev/block/by-name/boot of=/sdcard/boot.img
adb pull /sdcard/boot.img
```

3. **Patch Boot Image**
   - Transfer boot.img to device with Magisk app
   - Open Magisk → Install → Select and Patch a File
   - Select boot.img
   - Generate patched boot image (magisk_patched_boot.img)

4. **Flash Patched Image**
   - Transfer patched image back to device:

```bash
adb push magisk_patched_boot.img /sdcard/
```

   - Flash patched image:

```bash
adb shell dd if=/sdcard/magisk_patched_boot.img of=/dev/block/by-name/boot
```

5. **Reboot and Verify**
   - Reboot device
   - Open Magisk app to verify root access

**Required Magisk Modules:**

| Module | Purpose |
|--------|---------|
| Zygisk Next | Runtime process hooking framework |
| Shamiko | Root detection evasion |
| MagiskHide Props Config | Device fingerprint spoofing |
| Play Integrity Fix | Play Integrity API bypass |
| libhoudini | ARM translation layer |
| Universal SafetyNet Fix | Basic attestation bypass |

### 2.4 Device Compatibility Configuration

**Critical Configuration for App Installation:**

The VM must present as a recognized, certified Android device to Google Play Store.

**Device Fingerprint Configuration:**

```bash
# Apply validated fingerprint
ro.product.model=Pixel 4
ro.product.manufacturer=Google
ro.build.fingerprint=google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys
ro.build.description=flame-user 12 SP1A.210812.016.C2 1234567 release-keys
ro.product.name=flame
ro.product.device=flame
ro.build.version.sdk=31
ro.build.version.release=12
```

**ARM Translation Verification:**

```bash
# Verify ARM translation is active
adb shell cat /proc/cpuinfo | grep -i arm
# Should show ARMv7 or similar detection
```

### 2.5 Template Finalization

**Create Golden Image:**

```bash
# Stop VM
qm stop 9000

# Convert to template
qm template 9000

# Verify template status
qm list
```

**Template Properties:**

- ID: 9000 (standard convention)
- Type: Template (not directly runnable)
- Base Image: Clean Bliss OS with Magisk
- Preconfigured: Root access, ARM translation, Play Services

## 3. Proxmox REST API Integration

### 3.1 API Authentication Model

The Proxmox REST API requires ticket-based authentication:

**Authentication Process:**

1. POST credentials to `/access/ticket`
2. Receive ticket token and CSRF prevention token
3. Include both in subsequent requests
4. Token validity duration: 2 hours (configurable)

**API Endpoints for VM Lifecycle Management:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| List Templates | GET | `/nodes/{node}/storage/{storage}/content` |
| Clone VM | POST | `/nodes/{node}/qemu/{template_id}/clone` |
| Start VM | POST | `/nodes/{node}/qemu/{vmid}/status/start` |
| Stop VM | POST | `/nodes/{node}/qemu/{vmid}/status/stop` |
| Destroy VM | DELETE | `/nodes/{node}/qemu/{vmid}` |
| Modify Config | POST | `/nodes/{node}/qemu/{vmid}/config` |
| VM Status | GET | `/nodes/{node}/qemu/{vmid}/status/current` |

### 3.2 Automated Provisioning Workflow

**Clone and Configure Workflow:**

1. **Clone from Template**
   - POST to clone endpoint with new VM ID
   - Configure full clone (independent disk)
   - Set VM name

2. **Apply Unique Configuration**
   - Generate unique MAC address
   - Set MAC in VM configuration
   - Configure unique serial number
   - Apply custom CPU/memory if needed

3. **Start VM**
   - POST to start endpoint
   - Wait for boot completion

4. **Post-Boot Configuration**
   - Wait for ADB to become available
   - Push device identity configuration
   - Apply Android ID and IMEI
   - Configure system properties

5. **Verify Operation**
   - Check ADB connectivity
   - Verify Google Services registration
   - Confirm device certification

### 3.3 Resource Configuration Patterns

**Per-Instance Configuration:**

```yaml
# Unique identifiers generated per instance
identifiers:
  mac_address: "00:16:3E:XX:XX:XX"  # Unique per VM
  android_id: "XXXXXXXXXXXXXXXX"      # 16-digit hex
  imei: "35XXXXXXXXXXX"              # 15 digits
  serial: "XXXXXXXXXXXXXXXX"          # Random string
  
# Hardware fingerprint
fingerprint:
  model: "Pixel 4"
  manufacturer: "Google"
  fingerprint: "google/flame/flame:12/..."
  
# VM resources
resources:
  cpu_cores: 4
  ram_mb: 8192
  disk_gb: 64
  vlan_id: 100
```

## 4. Scaling & Resource Planning

### 4.1 Resource Requirements Matrix

**Per Instance Baseline:**

| Resource | Allocation | Notes |
|----------|------------|-------|
| CPU Cores | 4 | Moderate workload |
| RAM | 8GB | Android + Google Services |
| Storage | 64GB | OS + applications + data |
| Network | 10Mbps | Average usage |
| IOPS | 100-200 | Disk operations |

**Scale Projections:**

| Instances | Total CPU Cores | Total RAM (GB) | Total Storage (GB) | Host Nodes Recommended |
|-----------|----------------|----------------|-------------------|----------------------|
| 10 | 40 | 80 | 640 | 1 |
| 25 | 100 | 200 | 1600 | 2 |
| 50 | 200 | 400 | 3200 | 4 |
| 100 | 400 | 800 | 6400 | 8 |

### 4.2 Host Node Specifications

**Single Node (10-15 instances):**

- CPU: 64 cores @ 3.0GHz+
- RAM: 256GB DDR4
- Storage: 2TB NVMe RAID10
- Network: 10Gbps

**Medium Cluster (25-50 instances):**

- CPU: 128 cores @ 3.0GHz+
- RAM: 512GB DDR4
- Storage: 4TB NVMe RAID10
- Network: 25Gbps

**Large Cluster (100+ instances):**

- CPU: 256+ cores distributed
- RAM: 1TB+ distributed
- Storage: 8TB+ NVMe distributed
- Network: 40Gbps+

### 4.3 Resource Optimization Strategies

**CPU Oversubscription:**

- KVM allows CPU core oversubscription at 2:1 to 4:1 ratio
- Monitor CPU ready times to identify contention
- Adjust based on workload patterns

**Memory Overcommit:**

- KSM (Kernel Samepage Merging) for memory deduplication
- Balloon driver for dynamic memory adjustment
- Swap reservation for peak usage

**Storage Optimization:**

- Thin provisioning for disk images
- Storage deduplication where supported
- Tiered storage (SSD cache + HDD capacity)
- Regular cleanup and compaction

## 5. GPU Acceleration Options

### 5.1 GPU Virtualization Methods

| Method | Description | Performance | Compatibility | Setup Complexity |
|--------|-------------|-------------|---------------|------------------|
| VirtIO-GPU | Paravirtualized GPU | Good | High | Low |
| GPU Passthrough | Dedicated GPU per VM | Native | Limited | High |
| VirGL | OpenGL over VirtIO | Moderate | Moderate | Medium |
| QXL | Software rendering | Low | High | Low |

### 5.2 Recommended Approach: VirtIO-GPU

**Configuration:**

```bash
# Enable VirtIO-GPU
qm set <vmid> --vga virtio

# Allocate memory for GPU
qm set <vmid> --args "-device virtio-vga-gl,hostmem=512M"

# Enable SPICE enhancements
qm set <vmid> --spice_enhancements videostreaming
```

**Performance Considerations:**

- Good for UI rendering and basic graphics
- Moderate for 3D applications
- Shared GPU memory across instances
- Minimal setup complexity

### 5.3 GPU Passthrough (Performance Critical)

**Setup Process:**

1. **Identify GPU Devices:**

```bash
lspci -nn | grep -i nvidia
```

2. **Blacklist Host Drivers:**

```bash
echo "blacklist nvidiafb" >> /etc/modprobe.d/blacklist.conf
echo "blacklist nvidia" >> /etc/modprobe.d/blacklist.conf
```

3. **Bind to vfio-pci:**

```bash
echo "options vfio-pci ids=<vendor-id>:<device-id>" >> /etc/modprobe.d/vfio.conf
```

4. **Passthrough to VM:**

```bash
qm set <vmid> --hostpci0 01:00.0
```

**Limitations:**

- One GPU per VM
- Requires dedicated hardware
- Complex setup
- Limited scalability

## 6. ADB Integration & Control

### 6.1 ADB Network Configuration

**Enable ADB Over TCP/IP:**

```bash
# Set ADB port
adb shell setprop persist.adb.tcp.port 5555
adb shell setprop service.adb.tcp.port 5555

# Restart ADB daemon
adb shell stop adbd
adb shell start adbd
```

**ADB Connection Management:**

```python
# Connection patterns
adb connect <instance-ip>:5555
adb devices  # List connected devices
adb -s <device-id> shell <command>
adb disconnect <instance-ip>:5555
```

### 6.2 Management Control Interface

**ADB Commands for Instance Management:**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `adb shell getprop` | Retrieve system properties |
| System | `adb shell setprop` | Set system properties |
| Packages | `adb install [-r]` | Install/update APK |
| Packages | `adb uninstall` | Remove application |
| Packages | `adb shell pm list packages` | List installed apps |
| Activity | `adb shell am start` | Launch application |
| Activity | `adb shell am broadcast` | Send broadcast intent |
| Data | `adb push/pull` | Transfer files |
| Debug | `adb logcat` | View system logs |
| Screen | `adb screencap` | Capture screenshot |
| Input | `adb shell input tap` | Simulate touch |

### 6.3 Remote Visualization (Scrcpy)

**Setup:**

```bash
# Install scrcpy
apt install scrcpy

# Connect to instance
scrcpy -s <instance-ip>:5555

# Multiple instances
scrcpy -s <instance-ip>:5555 &
scrcpy -s <instance-ip>:5556 &
```

**Web-Based Dashboard Options:**

- QtScrcpy for desktop
- Web-Scrcpy for browser access
- Custom solution with noVNC + VNC server

## 7. Identity & State Isolation

### 7.1 Device Identity Management

**Identities to Spoof:**

| Identity Component | Purpose | Implementation Method |
|-------------------|---------|----------------------|
| Android ID | Unique device identifier | System property + database |
| IMEI | Hardware identifier | System property |
| MAC Address | Network identity | VM configuration |
| Serial Number | Device serial | Build.prop |
| Device Model | Hardware identity | Build.prop + Xposed |
| Manufacturer | Brand identity | Build.prop + Xposed |
| Build Fingerprint | OS version identity | Build.prop |
| Hardware Fingerprint | OpenGL/GPU identity | Xposed/LSPosed |

**Generation Strategy:**

```yaml
identity_generation:
  algorithm: "Random generation with validation"
  uniqueness: "Global uniqueness across fleet"
  persistence: "Stored in database for instance"
  rotation: "Manual rotation capability"
  validation: "Format and pattern verification"
```

### 7.2 Networking Isolation

**Network Topology:**

```
Proxmox Node
    ├── vmbr0 (Main Bridge)
    │   └── VLAN 100-199 (Instance VLANs)
    ├── NAT/Masquerade (Outbound)
    └── Firewall (Inbound Control)
```

**Isolation Strategy:**

| Layer | Configuration | Purpose |
|-------|--------------|---------|
| VLAN | Separate VLAN per instance | Network segmentation |
| MAC | Unique MAC per instance | Network identity |
| IP | Unique IP per instance | Addressability |
| Firewall | Restrictive rules | Traffic control |
| NAT | Masquerade outbound | Internet access |

### 7.3 Storage Isolation

**Storage Model:**

```
Storage Hierarchy:
├── Template Storage (Read-Only)
│   └── Base VM image (shared across clones)
├── Instance Storage (Per VM)
│   ├── Disk image (qcow2)
│   ├── Configuration (VM config)
│   └── State (Runtime data)
└── Data Volume (Optional)
    └── Persistent application data
```

**Storage Configuration:**

| Component | Location | Format | Purpose |
|-----------|----------|--------|---------|
| Template | local | qcow2 | Base image |
| Clone Storage | local-lvm | qcow2 | Instance disk |
| Config File | /etc/pve/qemu-server | .conf | VM configuration |
| Data Backup | NFS/remote | qcow2 | Disaster recovery |

### 7.4 State Management

**State Components to Track:**

| State Element | Storage Location | Update Frequency |
|--------------|------------------|------------------|
| VM Status | Proxmox API | Real-time |
| Instance Identity | Database | On creation |
| Application State | Database | Periodic |
| Running Tasks | Redis/Queue | Per operation |
| Logs | Centralized logging | Continuous |

## 8. Control Plane Architecture

### 8.1 Python Services (Control Plane)

**Recommended Service Architecture:**

| Service | Purpose | Technology |
|---------|---------|------------|
| Orchestrator | VM lifecycle management | FastAPI + Proxmox API |
| Identity Manager | Unique device identity generation | Python + random generation |
| Task Queue | Job scheduling and execution | Celery + Redis |
| State Manager | Instance state tracking | PostgreSQL + Redis |
| API Gateway | External interface | FastAPI |
| Log Aggregator | Centralized logging | Python logging + ELK |
| Metrics Collector | Performance monitoring | Prometheus + Python |

**Service Responsibilities:**

**Orchestrator Service:**

- Clone VMs from template
- Start/stop/destroy instances
- Apply VM configuration
- Manage VM lifecycles
- Handle API requests

**Identity Manager:**

- Generate unique device identities
- Validate identity formats
- Store identities in database
- Prevent identity collisions

**Task Queue:**

- Schedule batch operations
- Process jobs asynchronously
- Handle retries and failures
- Monitor job completion

**State Manager:**

- Track instance status
- Record operational history
- Store configuration states
- Provide state queries

### 8.2 Kotlin Services (Android Agent)

**Recommended Agent Architecture:**

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| Identity Agent | Manage device identity | System service |
| Configuration Agent | Apply runtime config | Content provider |
| Health Reporter | Report instance status | Scheduled task |
| Command Listener | Receive control commands | Broadcast receiver |
| App Installer | Manage application lifecycle | Package manager |

**Agent Capabilities:**

**Identity Agent:**

- Set Android ID, IMEI, serial
- Apply device fingerprint
- Modify build properties
- Persist identity across reboots

**Configuration Agent:**

- Accept configuration JSON via ADB
- Apply configuration immediately
- Validate configuration format
- Report configuration status

**Health Reporter:**

- Report CPU, memory, disk usage
- Report application status
- Report network connectivity
- Send heartbeat to control plane

**Command Listener:**

- Receive intents from ADB
- Execute commands securely
- Return command results
- Support script execution

### 8.3 Database & State Management

**PostgreSQL Schema:**

```sql
-- Instances table
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    vm_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    machine_type VARCHAR(50),
    identity JSONB NOT NULL,
    config JSONB,
    metadata JSONB
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
    fingerprint TEXT NOT NULL,
    assigned_at TIMESTAMP NOT NULL
);

-- Task history
CREATE TABLE task_history (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id),
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    result JSONB,
    error TEXT
);

-- Account vault
CREATE TABLE account_vault (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id),
    account_id VARCHAR(100) NOT NULL,
    encrypted_data BYTEA NOT NULL,
    created_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_instances_status ON instances(status);
CREATE INDEX idx_instances_vm_id ON instances(vm_id);
CREATE INDEX idx_tasks_instance ON task_history(instance_id);
CREATE INDEX idx_accounts_instance ON account_vault(instance_id);
```

**Redis Usage:**

| Redis Structure | Key Pattern | Purpose |
|----------------|-------------|---------|
| Hash | `instance:{id}:status` | Current instance status |
| Set | `instances:running` | Active instances |
| Queue | `task:queue` | Task scheduling |
| Queue | `task:results` | Task results |
| Hash | `instance:{id}:config` | Configuration cache |
| String | `instance:{id}:lock` | Distributed locks |

### 8.4 Task Queue Architecture

**Task Types:**

| Task | Description | Priority |
|------|-------------|----------|
| DEPLOY | Create and start new instance | High |
| STOP | Stop running instance | Medium |
| START | Start stopped instance | Medium |
| DESTROY | Remove instance | Low |
| RESTART | Restart instance | Medium |
| UPDATE_APP | Install/update application | Medium |
| APPLY_CONFIG | Apply runtime configuration | Low |
| EXECUTE_CMD | Execute custom command | Variable |

**Queue Workflow:**

1. Producer: API endpoint receives request
2. Queue: Task added to Redis queue with priority
3. Worker: Celery worker picks up task
4. Execution: Worker performs operations
5. Result: Task result stored in Redis
6. Callback: Notification sent to ntfy/webhook

## 9. Notification & Event System

### 9.1 ntfy Integration

**Event Types to Publish:**

| Event | Trigger | Payload |
|-------|---------|---------|
| Instance Deployed | VM provisioning complete | VM ID, status, config |
| Instance Started | VM started | VM ID, start time |
| Instance Stopped | VM stopped | VM ID, stop time |
| Instance Failed | Error condition | VM ID, error details |
| App Installed | Installation complete | Package, version, result |
| Task Complete | Task finished | Task ID, result |
| Identity Generated | New identity created | Identity details |

**ntfy Configuration:**

```yaml
topic: "android-fleet-events"
server: "https://ntfy.sh"
auth: "username:password"
templates:
  - "Instance {{ vm_id }} deployed"
  - "Status changed to {{ status }}"
  - "Error: {{ error_message }}"
```

**Notification Flow:**

```
Action → Orchestrator → ntfy → Subscribers
           ↓
      Database
           ↓
    Logging System
```

### 9.2 Logging Architecture

**Log Levels:**

| Level | Purpose |
|-------|---------|
| DEBUG | Detailed debugging information |
| INFO | Normal operations and state changes |
| WARNING | Non-critical issues |
| ERROR | Critical failures requiring attention |
| CRITICAL | System-level failures |

**Log Aggregation:**

- Centralized log collection
- Structured logging (JSON format)
- Log rotation and retention policies
- Search and filtering capabilities

## 10. Claude Code Engineering Harness

### 10.1 Project Setup

**Initial Configuration:**

1. Install Claude Code
   - Install via CLI tool
   - Configure authentication
   - Set up repository access

2. Initialize Project
   - Run `claude init` in repository
   - Configure MCP servers for services:
     - PostgreSQL: Database access
     - Redis: Cache and queue management
     - Proxmox: VM lifecycle control

### 10.2 Project Instructions (CLAUDE.md)

**Template Structure:**

```markdown
# Project Instructions

## Architecture Overview
- Python services for control plane
- Kotlin agents inside Android instances
- Proxmox for virtualization
- PostgreSQL for persistence
- Redis for caching and queues

## Coding Standards
- Python: PEP8, type hints, docstrings
- Kotlin: Android coding conventions
- API: REST + JSON
- Logging: Structured logging with context

## Proxmox API Patterns
- Use asynchronous requests
- Implement retry with exponential backoff
- Handle token expiration
- Rate limit operations

## Testing Strategy
- Unit tests for Python services
- Integration tests against staging Proxmox
- Acceptance tests for deployment
- Performance benchmarks

## Deployment Process
- Clone from template
- Apply configuration
- Start instance
- Verify operation
- Register in database

## Repository Structure
├── python/          # Control plane services
├── kotlin/          # Android agent
├── packer/          # Template creation
├── ansible/         # Configuration management
├── docker/          # Container definitions
└── scripts/         # Utility scripts
```

### 10.3 Custom Skills (Slash Commands)

**Skill: /deploy-instance**

```yaml
name: deploy-instance
description: Deploy new Android VM instance
triggers:
  - /deploy
  - /create-instance
actions:
  - Generate unique identity
  - Clone from template
  - Apply configuration
  - Start instance
  - Verify operation
  - Register in database
  - Send ntfy notification
output: Instance ID and status
```

**Skill: /scale-up**

```yaml
name: scale-up
description: Scale fleet to target size
triggers:
  - /scale
  - /scale-up
actions:
  - Current instance count
  - Target instance count
  - Parallel deployment
  - Status verification
  - Capacity check
output: Deployment summary
```

**Skill: /destroy-instance**

```yaml
name: destroy-instance
description: Destroy VM instance
triggers:
  - /destroy
  - /remove-instance
actions:
  - Stop VM
  - Destroy VM
  - Remove from database
  - Cleanup storage
  - Send notification
output: Confirmation of destruction
```

**Skill: /fleet-status**

```yaml
name: fleet-status
description: Show fleet status
triggers:
  - /status
  - /fleet-status
actions:
  - Query all instances
  - Show resource usage
  - Identify failed instances
  - Show pending tasks
output: Fleet status dashboard
```

**Skill: /apply-config**

```yaml
name: apply-config
description: Apply configuration to instance
triggers:
  - /config
  - /apply-config
actions:
  - Validate configuration
  - Push via ADB
  - Verify application
  - Restart if needed
  - Confirm success
output: Configuration status
```

### 10.4 Hooks Implementation

**Pre-Edit Hook (.claude/hooks/pre-edit):**

```yaml
name: pre-edit
triggers:
  - file-save
  - commit
check:
  - lint:python
  - lint:kotlin
  - type-check:python
  - type-check:kotlin
  - format:python
  - format:kotlin
  - test:unit
  - security:scan
```

**Pre-Commit Hook:**

```yaml
name: pre-commit
triggers:
  - git-commit
check:
  - run:python tests/
  - run:kotlin tests/
  - run:integration-tests
  - run:proxmox-check
```

### 10.5 MCP Server Configuration

**PostgreSQL MCP Server:**

```yaml
name: postgresql-mcp
type: database
connection:
  host: "localhost"
  port: 5432
  database: "android_fleet"
  user: "${POSTGRES_USER}"
  password: "${POSTGRES_PASSWORD}"
operations:
  - query
  - insert
  - update
  - delete
  - transaction
```

**Redis MCP Server:**

```yaml
name: redis-mcp
type: cache
connection:
  host: "localhost"
  port: 6379
  password: "${REDIS_PASSWORD}"
operations:
  - get
  - set
  - delete
  - queue
  - pubsub
```

**Proxmox MCP Server:**

```yaml
name: proxmox-mcp
type: api
connection:
  host: "${PROXMOX_HOST}"
  port: 8006
  user: "${PROXMOX_USER}"
  password: "${PROXMOX_PASSWORD}"
operations:
  - clone_vm
  - start_vm
  - stop_vm
  - destroy_vm
  - get_status
  - list_vms
  - get_config
  - set_config
```

### 10.6 Repository Access & Indexing

**Indexed Files:**

- Python services and modules
- Kotlin agent code
- Ansible playbooks
- Packer templates
- Docker configurations
- Shell scripts
- Configuration files

**Cross-File Operations:**

- Search across entire repository
- Make changes across files
- Refactor across boundaries
- Generate documentation
- Create new components

**CLAUDE.ignore File:**

```yaml
# Binaries
*.pyc
*.class
*.jar
*.apk

# Generated files
__pycache__/
build/
dist/
target/

# Secrets
*.key
*.pem
*.crt
.env
secrets.yaml

# Large files
*.iso
*.qcow2
*.vmdk
*.img

# IDE files
.idea/
.vscode/
*.swp
```

## 11. Implementation Roadmap

### 11.1 Phase 1: Foundation (Week 1-2)

| Task | Description | Deliverable |
|------|-------------|-------------|
| Setup Proxmox | Install and configure | Working Proxmox node |
| Create Template | Install Bliss OS + Magisk | Base template |
| Configure Root | Install required modules | Rooted template |
| Test Template | Verify functionality | Validated template |

### 11.2 Phase 2: Automation (Week 3-4)

| Task | Description | Deliverable |
|------|-------------|-------------|
| API Integration | Proxmox REST API | Working API client |
| Provisioning Script | Clone and configure | Deployment script |
| Identity Generation | Unique IDs | Identity manager |
| ADB Integration | Remote control | ADB controller |

### 11.3 Phase 3: Control Plane (Week 5-6)

| Task | Description | Deliverable |
|------|-------------|-------------|
| Python Services | Orchestration API | Working services |
| Database Setup | PostgreSQL schema | Database ready |
| Task Queue | Celery + Redis | Queue system |
| Notification | ntfy integration | Event system |

### 11.4 Phase 4: Scaling & Optimization (Week 7-8)

| Task | Description | Deliverable |
|------|-------------|-------------|
| Multi-node Setup | Proxmox cluster | Scalable infrastructure |
| Resource Planning | Capacity planning | Scaling guidelines |
| GPU Acceleration | VirtIO-GPU | Enhanced performance |
| Performance Testing | Benchmark | Performance metrics |

### 11.5 Phase 5: Engineering Harness (Week 9-10)

| Task | Description | Deliverable |
|------|-------------|-------------|
| Claude Code Setup | Configuration | MCP servers |
| Skills Creation | Custom commands | Slash commands |
| Hooks Implementation | Pre-commit checks | Automated checks |
| Documentation | Complete guide | Final documentation |

## 12. Operational Considerations

### 12.1 Maintenance Tasks

| Task | Frequency | Criticality |
|------|-----------|-------------|
| Template Updates | Monthly | High |
| Module Updates | Weekly | High |
| Security Patches | As needed | Critical |
| Storage Cleanup | Weekly | Medium |
| Performance Review | Monthly | Medium |
| Backup Verification | Weekly | High |

### 12.2 Monitoring Requirements

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU Usage | > 80% | Scale out or upgrade hardware |
| Memory Usage | > 85% | Increase RAM or optimize |
| Disk Usage | > 80% | Clean up or expand |
| Network Latency | > 100ms | Investigate network |
| Instance Count | Near capacity | Deploy new nodes |
| Task Queue Length | > 1000 | Scale workers |

### 12.3 Failure Scenarios

| Scenario | Impact | Recovery |
|----------|--------|----------|
| Node Failure | Instances lost | Failover to backup |
| Template Corruption | New instances fail | Rebuild template |
| Network Outage | Instances unreachable | Check networking |
| Database Failure | State unknown | Restore from backup |
| API Rate Limit | Slow deployment | Implement backoff |
| Storage Full | Cannot deploy | Clean up or expand |

### 12.4 Backup Strategy

| Component | Backup Frequency | Retention |
|-----------|-----------------|-----------|
| Template | Monthly | 3 months |
| Instance Data | Daily | 7 days |
| Database | Daily | 30 days |
| Configuration | Daily | 30 days |
| Logs | Weekly | 90 days |

## 13. Key Design Decisions Summary

| Decision Area | Chosen Approach | Rationale |
|--------------|-----------------|-----------|
| Android Distribution | Bliss OS 16.9 | Best KVM support, Magisk compatibility |
| Root Method | Magisk | Systemless root, active development |
| ARM Translation | libhoudini | Built-in, Magisk module support |
| Device Identity | Random generation | Unique per instance |
| Scaling Approach | KVM VMs | Full isolation, complete control |
| Control Interface | ADB + Scrcpy | Native Android debugging tools |
| Resource Management | Proxmox API | Native integration |
| State Management | PostgreSQL + Redis | Persistent + fast access |
| Orchestration | Python services | Rich ecosystem, libraries |
| Agent Framework | Kotlin + Android APIs | Native Android development |
| Engineering Harness | Claude Code | AI-assisted development |
| CI/CD Integration | Packer + Ansible | Infrastructure as Code |
