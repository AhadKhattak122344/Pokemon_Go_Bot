"""
Android Fleet Orchestrator - FastAPI Application
Main entry point for the orchestration API.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import List, Optional
from pydantic import BaseModel

from .schemas import InstanceCreate, InstanceResponse, TaskResponse, CommandRequest, AppInstallRequest
from .tasks import deploy_instance_task, start_instance_task, stop_instance_task, destroy_instance_task
from .models import get_db
from .notifications import send_notification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Android Fleet Orchestrator")
    yield
    # Shutdown
    logger.info("Shutting down Android Fleet Orchestrator")


app = FastAPI(
    title="Android Fleet Orchestrator",
    description="API for managing Android VM instances on Proxmox",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "android-fleet-orchestrator"}


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    # TODO: Implement actual metrics collection
    return {
        "instances_total": 0,
        "instances_running": 0,
        "tasks_pending": 0
    }


@app.post("/instances", response_model=InstanceResponse)
async def create_instance(instance: InstanceCreate, background_tasks: BackgroundTasks):
    """Create a new Android VM instance."""
    db = next(get_db())
    
    try:
        # Generate identity
        from ..scripts.generate_identity import generate_identity
        identity = generate_identity(instance.name)
        
        # Create database record
        from .models import Instance
        db_instance = Instance(
            name=instance.name or identity["instance_name"],
            status="pending",
            identity=identity,
            config={"cpu_cores": instance.cpu_cores, "ram_mb": instance.ram_mb}
        )
        db.add(db_instance)
        db.commit()
        db.refresh(db_instance)
        
        # Queue deployment task
        task = deploy_instance_task.delay(
            instance_id=db_instance.id,
            template_id=instance.template_id or 9000,
            identity=identity
        )
        
        # Send notification
        send_notification(
            event_type="instance_deploying",
            instance_id=db_instance.id,
            title="Instance Deployment Started",
            message=f"Deploying {db_instance.name} (VM ID: pending)"
        )
        
        logger.info(f"Instance {db_instance.id} creation queued")
        return InstanceResponse.from_orm(db_instance)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/instances", response_model=List[InstanceResponse])
async def list_instances(status: Optional[str] = None):
    """List all instances with optional status filter."""
    db = next(get_db())
    
    from .models import Instance
    query = db.query(Instance)
    if status:
        query = query.filter(Instance.status == status)
    
    instances = query.all()
    return [InstanceResponse.from_orm(i) for i in instances]


@app.get("/instances/{instance_id}", response_model=InstanceResponse)
async def get_instance(instance_id: int):
    """Get instance details."""
    db = next(get_db())
    
    from .models import Instance
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    return InstanceResponse.from_orm(instance)


@app.delete("/instances/{instance_id}")
async def destroy_instance_endpoint(instance_id: int, background_tasks: BackgroundTasks):
    """Destroy an instance."""
    db = next(get_db())
    
    from .models import Instance
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Queue destruction task
    task = destroy_instance_task.delay(instance_id)
    
    send_notification(
        event_type="instance_destroying",
        instance_id=instance_id,
        title="Instance Destruction Started",
        message=f"Destroying {instance.name}"
    )
    
    return {"message": "Instance destruction queued", "task_id": task.id}


@app.post("/instances/{instance_id}/start")
async def start_instance_endpoint(instance_id: int, background_tasks: BackgroundTasks):
    """Start an instance."""
    db = next(get_db())
    
    from .models import Instance
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    task = start_instance_task.delay(instance_id)
    
    send_notification(
        event_type="instance_starting",
        instance_id=instance_id,
        title="Instance Starting",
        message=f"Starting {instance.name}"
    )
    
    return {"message": "Instance start queued", "task_id": task.id}


@app.post("/instances/{instance_id}/stop")
async def stop_instance_endpoint(instance_id: int, background_tasks: BackgroundTasks):
    """Stop an instance."""
    db = next(get_db())
    
    from .models import Instance
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    task = stop_instance_task.delay(instance_id)
    
    send_notification(
        event_type="instance_stopping",
        instance_id=instance_id,
        title="Instance Stopping",
        message=f"Stopping {instance.name}"
    )
    
    return {"message": "Instance stop queued", "task_id": task.id}


@app.post("/instances/{instance_id}/app")
async def install_app(instance_id: int, request: AppInstallRequest):
    """Install application on instance."""
    # TODO: Implement app installation
    return {"message": "App installation queued", "package": request.package_name}


@app.post("/instances/{instance_id}/command")
async def execute_command(instance_id: int, request: CommandRequest):
    """Execute ADB command on instance."""
    # TODO: Implement command execution
    return {"message": "Command queued", "command": request.command}


@app.get("/fleet/status")
async def fleet_status():
    """Get fleet-wide statistics."""
    db = next(get_db())
    
    from .models import Instance
    total = db.query(Instance).count()
    running = db.query(Instance).filter(Instance.status == "running").count()
    stopped = db.query(Instance).filter(Instance.status == "stopped").count()
    failed = db.query(Instance).filter(Instance.status == "failed").count()
    
    return {
        "total_instances": total,
        "running": running,
        "stopped": stopped,
        "failed": failed,
        "health_rate": (running / total * 100) if total > 0 else 0
    }


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(status: Optional[str] = None):
    """List all tasks."""
    db = next(get_db())
    
    from .models import TaskHistory
    query = db.query(TaskHistory)
    if status:
        query = query.filter(TaskHistory.status == status)
    
    tasks = query.order_by(TaskHistory.started_at.desc()).limit(100).all()
    return [TaskResponse.from_orm(t) for t in tasks]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Get task details."""
    db = next(get_db())
    
    from .models import TaskHistory
    task = db.query(TaskHistory).filter(TaskHistory.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse.from_orm(task)
