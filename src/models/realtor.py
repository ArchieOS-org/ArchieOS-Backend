"""Realtor model - represents people/agents (primary people table)."""

from typing import Optional
from pydantic import BaseModel, Field


class Realtor(BaseModel):
    """Realtor model - this is our primary Person/People model."""
    realtor_id: str = Field(..., description="Realtor ID (text)")
    email: str = Field(..., description="Email address")
    name: str = Field(..., description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    license_number: Optional[str] = Field(None, description="Real estate license number")
    brokerage: Optional[str] = Field(None, description="Brokerage name")
    slack_user_id: Optional[str] = Field(None, description="Slack user ID")
    territories: Optional[list[str]] = Field(None, description="Territory list")
    status: str = Field(default="active", description="Status: active, inactive, suspended, pending")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")


