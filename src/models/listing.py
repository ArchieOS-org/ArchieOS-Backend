"""Listing models."""

from typing import Optional
from datetime import date
from pydantic import BaseModel, Field


class Listing(BaseModel):
    """Real estate listing."""
    listing_id: Optional[str] = Field(None, description="Listing ID (text)")
    type: Optional[str] = Field(None, description="SALE or LEASE")
    status: Optional[str] = Field(None, description="Listing status")
    address_string: Optional[str] = Field(None, description="Property address")
    agent_id: Optional[str] = Field(None, description="Assigned agent ID (text, legacy field)")
    realtor_id: Optional[str] = Field(None, description="Realtor ID (text FK)")
    assignee: Optional[str] = Field(None, description="Assignee name")
    due_date: Optional[date] = Field(None, description="Due date")
    notes: Optional[str] = Field(None, description="Listing notes")
    progress: Optional[float] = Field(None, description="Progress (0.0-1.0)")
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")

