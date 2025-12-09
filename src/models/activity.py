"""Activity model - represents listing tasks (tasks tied to listings)."""

from typing import Optional, Any
from datetime import date
from pydantic import BaseModel, Field


class Activity(BaseModel):
    """Activity model - listing-specific tasks."""
    task_id: str = Field(..., description="Task ID (text)")
    listing_id: str = Field(..., description="Listing ID (text FK)")
    realtor_id: Optional[str] = Field(None, description="Realtor ID (text FK)")
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    task_category: str = Field(
        ...,
        description="Task category: ADMIN, MARKETING, PHOTO, STAGING, INSPECTION, OTHER"
    )
    status: str = Field(
        default="OPEN",
        description="Status: OPEN, CLAIMED, IN_PROGRESS, DONE, FAILED, CANCELLED"
    )
    priority: int = Field(default=0, ge=0, le=10, description="Priority (0-10)")
    visibility_group: str = Field(
        default="BOTH",
        description="Visibility: BOTH, AGENT, MARKETING"
    )
    assigned_staff_id: Optional[str] = Field(None, description="Assigned staff ID (text FK)")
    due_date: Optional[date] = Field(None, description="Due date")
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict, description="Task inputs/metadata")
    outputs: dict[str, Any] = Field(default_factory=dict, description="Task outputs/results")

