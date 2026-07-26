import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    assigned_to: uuid.UUID
    due_date: date
    priority: str = Field("MEDIUM", description="LOW, MEDIUM, or HIGH")

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None  # "PENDING", "IN_PROGRESS", "COMPLETED"
    manager_remarks: Optional[str] = None

class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    assigned_to: uuid.UUID
    assigned_by: uuid.UUID
    due_date: date
    priority: str
    status: str
    manager_remarks: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
