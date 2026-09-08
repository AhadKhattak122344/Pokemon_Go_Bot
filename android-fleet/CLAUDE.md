# Project Instructions

## Architecture Overview
- Python services for control plane (FastAPI + Proxmox API)
- Kotlin agents inside Android instances
- Proxmox for virtualization infrastructure
- PostgreSQL for state persistence
- Redis for caching and task queues

## Coding Standards
- Python: PEP8, type hints, docstrings, async/await patterns
- Kotlin: Android coding conventions, coroutines for async operations
- API: REST + JSON with proper error handling
- Logging: Structured logging with context (JSON format)

## Proxmox API Patterns
- Use asynchronous requests with aiohttp
- Implement retry with exponential backoff (3 retries, 2x backoff)
- Handle token expiration (2-hour validity)
- Rate limit operations (10 requests/second max)
- Always verify VM status after operations

## Testing Strategy
- Unit tests for Python services (pytest + asyncio)
- Integration tests against staging Proxmox instance
- Acceptance tests for deployment workflows
- Performance benchmarks for scaling operations

## Deployment Process
1. Generate unique identity (Android ID, IMEI, MAC, serial)
2. Clone VM from template (ID 9000) via Proxmox API
3. Apply VM configuration (MAC address, CPU, RAM)
4. Start instance and wait for boot completion
5. Verify ADB connectivity
6. Apply device fingerprint and configuration
7. Register instance in database
8. Send deployment notification via ntfy

## Repository Structure
```
android-fleet/
├── python/          # Control plane services
│   ├── orchestrator/    # VM lifecycle management
│   ├── identity/        # Device identity generation
│   ├── api/            # FastAPI endpoints
│   └── tests/          # Test suite
├── kotlin/          # Android agent
│   ├── app/          # Agent application
│   └── build.gradle
├── packer/          # Template creation templates
├── ansible/         # Configuration management
├── docker/          # Container definitions
├── scripts/         # Utility scripts
└── .claude/         # Claude Code configuration
```

## Key Components
- **Orchestrator**: Manages VM lifecycle (create, start, stop, destroy)
- **Identity Manager**: Generates and validates unique device identities
- **Task Queue**: Celery workers for async job processing
- **State Manager**: PostgreSQL + Redis for instance tracking
- **Android Agent**: In-VM service for configuration and health reporting

## Environment Variables Required
```bash
PROXMOX_HOST=proxmox.example.com
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=secret
POSTGRES_HOST=localhost
POSTGRES_DB=android_fleet
REDIS_HOST=localhost
NTFY_TOPIC=android-fleet-events
```
