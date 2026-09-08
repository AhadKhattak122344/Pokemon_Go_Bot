# Android Fleet - Pokémon GO Automation

## Architecture Overview
- **Python services**: Control plane (FastAPI + Proxmox API) for VM lifecycle management
- **Kotlin agent**: Android instance management for in-VM configuration
- **Proxmox VE**: Virtualization infrastructure running Bliss OS Android VMs
- **PostgreSQL**: State persistence for instances, identities, and task history
- **Redis**: Caching, task queues (Celery), and distributed locks

## Pokémon GO Specific Configuration

### Android Version
- **Target**: Android 12 (API 31) - Optimal for Pokémon GO compatibility
- **Distribution**: Bliss OS 16.9 x86_64 with GApps
- **ARM Translation**: libhoudini module for ARM app compatibility
- **Root**: Magisk 26.3+ with systemless root

### Device Fingerprint (Certified Device)
Each VM spoofs as Google Pixel 4 (flame):
```
ro.product.model=Pixel 4
ro.product.manufacturer=Google
ro.build.fingerprint=google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys
ro.build.description=flame-user 12 SP1A.210812.016.C2 1234567 release-keys
ro.product.name=flame
ro.product.device=flame
ro.build.version.sdk=31
ro.build.version.release=12
```

### Required Magisk Modules
1. **Zygisk Next** - Runtime process hooking framework
2. **Shamiko** - Root detection evasion (hides Magisk from apps)
3. **MagiskHide Props Config** - Device fingerprint spoofing
4. **Play Integrity Fix** - Play Integrity API bypass (MEETS_DEVICE_INTEGRITY)
5. **Universal SafetyNet Fix** - Basic attestation bypass
6. **libhoudini** - ARM translation layer for x86 → ARM

### Pokémon GO Evasion Strategy
| Check | Solution |
|-------|----------|
| ARM architecture | libhoudini translates ARM → x86 transparently |
| Device certification | Pixel 4 fingerprint makes Play Store think it's real |
| Root detection | Magisk Hide + Shamiko completely hide root |
| Play Integrity | Play Integrity Fix module spoofs attestation response |
| Unique device ID | Random IMEI/Android ID/MAC per VM |
| Location consistency | GPS spoofing via ADB location injection |

## Coding Standards
- **Python**: PEP8, type hints, docstrings, async/await patterns with aiohttp
- **Kotlin**: Android coding conventions, coroutines for async operations
- **API**: REST + JSON with proper error handling and validation
- **Logging**: Structured logging with context (JSON format)

## Proxmox API Patterns
- Use asynchronous requests with aiohttp
- Implement retry with exponential backoff (3 retries, 2x backoff)
- Handle token expiration (2-hour validity, auto-refresh)
- Rate limit operations (10 requests/second max)
- Always verify VM status after operations (start/stop/clone)

## Testing Strategy
- Unit tests for Python services (pytest + asyncio)
- Integration tests against staging Proxmox instance
- Acceptance tests for deployment workflows
- Performance benchmarks for scaling operations (10-100 instances)

## Deployment Process
1. Generate unique identity (Android ID, IMEI, MAC, serial)
2. Clone VM from template (ID 9000) via Proxmox API
3. Apply VM configuration (MAC address, CPU, RAM)
4. Start instance and wait for boot completion (target: 60-90 seconds)
5. Verify ADB connectivity on port 5555
6. Apply device fingerprint (Pixel 4) and configuration
7. Install Pokémon GO via ADB
8. Register instance in database
9. Send deployment notification via ntfy

## Repository Structure
```
android-fleet/
├── python/              # Control plane services
│   ├── orchestrator/    # VM lifecycle management (FastAPI)
│   ├── identity/        # Device identity generation
│   ├── api/             # FastAPI endpoints
│   └── tests/           # Test suite
├── kotlin/              # Android agent
│   ├── app/             # Agent application
│   └── build.gradle
├── packer/              # Template creation templates
├── ansible/             # Configuration management
├── docker/              # Container definitions
├── scripts/             # Utility scripts (generate_identity, provision_vm, etc.)
└── .claude/             # Claude Code configuration
    ├── instructions.md
    ├── skills/          # Custom slash commands
    ├── hooks/           # Pre-commit checks
    └── mcp-servers/     # MCP server configs
```

## Key Components
- **Orchestrator**: Manages VM lifecycle (create, start, stop, destroy)
- **Identity Manager**: Generates and validates unique device identities (IMEI, Android ID, MAC)
- **Task Queue**: Celery workers for async job processing (deploy, configure, install)
- **State Manager**: PostgreSQL + Redis for instance tracking
- **Android Agent**: In-VM service for configuration and health reporting

## Environment Variables Required
```bash
PROXMOX_HOST=proxmox.example.com
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=secret
POSTGRES_HOST=localhost
POSTGRES_DB=android_fleet
POSTGRES_USER=android_fleet
POSTGRES_PASSWORD=secret
REDIS_HOST=localhost
REDIS_PASSWORD=secret
NTFY_TOPIC=android-fleet-events
NTFY_SERVER=https://ntfy.sh
```

## Quick Start Commands
```bash
# Deploy single instance
/deploy-instance --name=pokemon-001 --template=pixel4

# Scale fleet to 100 instances
/scale-up --target=100 --template=pixel4

# Check fleet status
/fleet-status

# Destroy instance
/destroy-instance --vm-id=10001

# Apply configuration
/apply-config --vm-id=10001 --config=pokemon_config.json
```

## Troubleshooting
| Problem | Solution |
|---------|----------|
| "No eligible devices" in Play Store | Apply Pixel 4 fingerprint via MagiskHide Props Config |
| "Device not compatible" | Verify libhoudini module is installed and active |
| "App crashes" | Reinstall libhoudini module, check /proc/cpuinfo for ARM |
| "Root detected" | Verify Shamiko is installed and DenyList configured |
| "Play Integrity fails" | Update Play Integrity Fix module to latest version |
| "Device not certified" | Clear GMS/GSF data, reboot, wait 15 minutes for certification |
| "Slow performance" | Increase CPU cores (4→8) or RAM (8GB→12GB) per VM |

## One Sentence Summary
Proxmox runs cloned Android VMs with unique identities, hidden root (Magisk+Shamiko), ARM translation (libhoudini), and certified Pixel 4 fingerprints, all controlled automatically via Python services and Claude Code for Pokémon GO automation.
