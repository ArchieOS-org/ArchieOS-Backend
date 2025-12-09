"""AgentTask model - represents tasks not tied to listings."""

from typing import Optional, Any
from datetime import date
from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    """AgentTask model - tasks not tied to specific listings."""
    task_id: str = Field(..., description="Task ID (text)")
    realtor_id: str = Field(..., description="Realtor ID (text FK, required)")
    task_key: Optional[str] = Field(None, description="Task key (deprecated, use task_category)")
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    status: str = Field(
        default="OPEN",
        description="Status: OPEN, CLAIMED, IN_PROGRESS, DONE, FAILED, CANCELLED"
    )
    priority: int = Field(default=0, ge=0, le=10, description="Priority (0-10)")
    assigned_staff_id: Optional[str] = Field(None, description="Assigned staff ID (text FK)")
    due_date: Optional[date] = Field(None, description="Due date")
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None
    notes: Optional[str] = Field(None, description="Task notes")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Task inputs/metadata")
    outputs: dict[str, Any] = Field(default_factory=dict, description="Task outputs/results")
    task_category: str = Field(
        default="OTHER",
        description="Task category: ADMIN, MARKETING, PHOTO, STAGING, INSPECTION, OTHER"
    )


