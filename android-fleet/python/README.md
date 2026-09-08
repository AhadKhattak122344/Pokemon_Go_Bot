# Android Fleet Control Plane - Python Services

FastAPI-based orchestration system for managing Android VM fleets on Proxmox.

## Installation

```bash
pip install -r requirements.txt
```

## Requirements

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Proxmox VE 7.0+

## Configuration

Create `.env` file:

```bash
PROXMOX_HOST=proxmox.example.com
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your_password
PROXMOX_NODE=proxmox
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=android_fleet
POSTGRES_USER=android_fleet
POSTGRES_PASSWORD=your_password
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=android-fleet-events
```

## Running Services

### Orchestrator API
```bash
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000
```

### Celery Worker
```bash
celery -A orchestrator.celery_app worker --loglevel=info
```

### Celery Beat (Scheduler)
```bash
celery -A orchestrator.celery_app beat --loglevel=info
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/instances` | POST | Create new instance |
| `/instances` | GET | List all instances |
| `/instances/{id}` | GET | Get instance details |
| `/instances/{id}` | DELETE | Destroy instance |
| `/instances/{id}/start` | POST | Start instance |
| `/instances/{id}/stop` | POST | Stop instance |
| `/instances/{id}/restart` | POST | Restart instance |
| `/instances/{id}/app` | POST | Install application |
| `/instances/{id}/command` | POST | Execute ADB command |
| `/fleet/status` | GET | Get fleet statistics |
| `/tasks` | GET | List tasks |
| `/tasks/{id}` | GET | Get task status |

## Example Usage

### Deploy Instance
```bash
curl -X POST http://localhost:8000/instances \
  -H "Content-Type: application/json" \
  -d '{
    "name": "android-001",
    "template_id": 9000,
    "cpu_cores": 4,
    "ram_mb": 8192
  }'
```

### List Instances
```bash
curl http://localhost:8000/instances
```

### Start Instance
```bash
curl -X POST http://localhost:8000/instances/1/start
```

### Install App
```bash
curl -X POST http://localhost:8000/instances/1/app \
  -H "Content-Type: application/json" \
  -d '{
    "apk_url": "https://example.com/app.apk",
    "package_name": "com.example.app"
  }'
```

## Architecture

```
python/
├── orchestrator/
│   ├── main.py              # FastAPI application
│   ├── celery_app.py        # Celery configuration
│   ├── tasks.py             # Celery tasks
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── proxmox_client.py    # Proxmox API client
│   ├── adb_client.py        # ADB management
│   └── notifications.py     # ntfy integration
├── identity/
│   ├── generator.py         # Identity generation
│   └── validator.py         # Identity validation
├── database/
│   ├── schema.sql           # Database schema
│   └── connection.py        # DB connection
└── tests/
    ├── test_orchestrator.py
    └── test_identity.py
```

## Testing

```bash
pytest tests/ -v
```

## Monitoring

- Health check: `GET /health`
- Metrics: `GET /metrics` (Prometheus format)
- Logs: Structured JSON logging to stdout
