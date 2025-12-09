"""Task models."""

from typing import Optional, Any
from datetime import date
from pydantic import BaseModel, Field
from uuid import UUID


class Task(BaseModel):
    """Task model."""
    task_id: Optional[UUID] = None
    listing_id: Optional[UUID] = Field(None, description="Associated listing ID (null for agent tasks)")
    name: str = Field(..., description="Task name/title")
    status: str = Field(default="OPEN", description="Task status")
    task_def_id: Optional[str] = Field(None, description="Task definition ID")
    is_stray: bool = Field(default=False, description="DEPRECATED: Use Activity/AgentTask models instead")
    task_category: Optional[str] = Field(None, description="Task category")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Task inputs/metadata")
    agent_id: Optional[UUID] = Field(None, description="Assigned agent person_id")
    agent: Optional[str] = Field(None, description="Assigned agent name")
    due_date: Optional[date] = Field(None, description="Due date")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

