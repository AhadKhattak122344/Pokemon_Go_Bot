# Android Fleet for Pokémon GO

Automated Android VM fleet management on Proxmox VE with unique device identities, root hiding, ARM translation, and Play Store compatibility.

## Quick Start

### Prerequisites
- Proxmox VE 7.0+ server
- Bliss OS 16.9 x86_64 ISO with GApps
- Python 3.9+
- PostgreSQL 13+
- Redis 6+

### Installation

1. **Create Base Template** (VM ID 9000):
   - Install Bliss OS 16.9 with GApps
   - Root with Magisk 26.3+
   - Install modules: Zygisk Next, Shamiko, MagiskHide Props Config, Play Integrity Fix, libhoudini
   - Apply Pixel 4 fingerprint
   - Convert to template: `qm template 9000`

2. **Install Dependencies**:
```bash
cd /workspace/android-fleet
pip install -r python/requirements.txt
```

3. **Setup Database**:
```bash
psql -U postgres -f python/database/schema.sql
```

4. **Start Services**:
```bash
# Start Redis
redis-server

# Start API
cd python && uvicorn api.main:app --host 0.0.0.0 --port 8000

# Start Celery worker
celery -A orchestrator.celery_app worker --loglevel=info
```

## Claude Code Commands

Available slash commands in `.claude/skills/`:

- `/deploy-instance` - Deploy new Android VM with unique identity
- `/scale-up <count>` - Scale fleet to target size
- `/destroy-instance <vm_id>` - Remove instance
- `/fleet-status` - Show all instances and health
- `/apply-config <vm_id>` - Apply configuration via ADB
- `/install-pokemongo <vm_id>` - Install Pokémon GO
- `/set-location <vm_id> <lat> <lng>` - Set GPS location
- `/check-ban-status <vm_id>` - Check if account banned
- `/restart-failed` - Restart failed instances

## Architecture

```
android-fleet/
├── .claude/              # Claude Code engineering harness
│   ├── skills/           # Custom slash commands
│   ├── hooks/            # Pre-commit checks
│   └── mcp-servers/      # MCP configurations
├── python/               # Control plane services
│   ├── api/              # FastAPI REST API
│   ├── orchestrator/     # VM lifecycle management
│   ├── identity/         # Device identity generation
│   ├── database/         # PostgreSQL schema
│   └── tests/            # Unit tests
├── scripts/              # Deployment scripts
│   ├── generate_identity.py
│   ├── provision_vm.py
│   ├── fix_playstore.sh
│   └── health_check.sh
├── kotlin/               # Android agent (optional)
├── ansible/              # Configuration management
├── packer/               # Template building
└── docker/               # Container definitions
```

## Key Features

### Device Spoofing
Each VM gets unique:
- Android ID (16-char hex)
- IMEI (15 digits, Luhn validated)
- MAC address (Proxmox OUI)
- Serial number (16-char alphanumeric)
- Pixel 4 fingerprint (Android 12)

### Anti-Detection
- **Magisk**: Systemless root
- **Zygisk**: Runtime hooking
- **Shamiko**: Hide root from apps
- **Play Integrity Fix**: Pass attestation
- **libhoudini**: ARM translation for x86

### Automation
- Clone VMs via Proxmox API
- Apply unique identities automatically
- Install/configure apps via ADB
- Health monitoring and auto-restart
- ntfy notifications for events

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/instances` | Create new instance |
| GET | `/instances` | List all instances |
| GET | `/instances/{id}` | Get instance status |
| POST | `/instances/{id}/start` | Start instance |
| POST | `/instances/{id}/stop` | Stop instance |
| DELETE | `/instances/{id}` | Destroy instance |
| POST | `/instances/{id}/app` | Install app |
| POST | `/instances/{id}/command` | Execute ADB command |

## Scaling Guide

| Instances | CPU Cores | RAM (GB) | Storage (GB) | Nodes |
|-----------|-----------|----------|--------------|-------|
| 10 | 40 | 80 | 640 | 1 |
| 25 | 100 | 200 | 1600 | 2 |
| 50 | 200 | 400 | 3200 | 4 |
| 100 | 400 | 800 | 6400 | 8 |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No eligible devices" | Apply Pixel 4 fingerprint |
| "Device not compatible" | Verify libhoudini installed |
| "Root detected" | Check Shamiko module active |
| "Play Integrity fails" | Update Play Integrity Fix |
| "Device not certified" | Clear GMS/GSF data, wait 15 min |

## Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Full technical architecture
- [REQUIREMENTS.md](../REQUIREMENTS.md) - Complete requirements specification
- [START-HERE.md](../START-HERE.md) - Getting started guide

## License

MIT License
