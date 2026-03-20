from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

TaskStatus = Literal["planned", "inprogress", "completed", "pending"]
TaskPriority = Literal["low", "medium", "high", "urgent"]


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = "planned"
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    source_name: Optional[str] = None
    source_logo: Optional[str] = None
    position: int = 0


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    source_name: Optional[str] = None
    source_logo: Optional[str] = None
    position: Optional[int] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    position: Optional[int] = None


class TaskResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    status: str
    priority: Optional[str]
    due_date: Optional[datetime]
    reminder_at: Optional[datetime]
    source_name: Optional[str]
    source_logo: Optional[str]
    external_ref: Optional[str]
    position: int
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
