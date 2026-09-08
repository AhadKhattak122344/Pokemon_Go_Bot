"""
Pydantic schemas for Android Fleet Orchestrator API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class InstanceCreate(BaseModel):
    """Schema for creating a new instance."""
    name: Optional[str] = None
    template_id: Optional[int] = 9000
    cpu_cores: int = 4
    ram_mb: int = 8192


class InstanceResponse(BaseModel):
    """Schema for instance response."""
    id: int
    vm_id: Optional[int] = None
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    ip_address: Optional[str] = None
    adb_port: int = 5555
    
    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """Schema for task response."""
    id: int
    instance_id: Optional[int]
    task_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True


class CommandRequest(BaseModel):
    """Schema for ADB command request."""
    command: str
    timeout: int = 30


class AppInstallRequest(BaseModel):
    """Schema for app installation request."""
    apk_url: str
    package_name: str