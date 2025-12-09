"""Slack event models."""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class SlackEventSource(BaseModel):
    """Source information extracted from Slack event."""
    text: str = Field(..., description="Message text")
    slack_user_id: str = Field(..., description="Slack user ID")
    channel_id: str = Field(..., description="Slack channel ID")
    ts: str = Field(..., description="Message timestamp")
    links: Optional[list[str]] = Field(None, description="URLs extracted from message")
    attachments: Optional[list[dict]] = Field(None, description="Slack attachments")


class SlackEventEnvelope(BaseModel):
    """Envelope for classified Slack events."""
    schema: Literal["classification_v1"] = "classification_v1"
    idempotency_key: str = Field(..., description="Deterministic key for deduplication")
    source: SlackEventSource = Field(..., description="Source event information")
    payload: dict = Field(..., description="Classification payload")
    links: Optional[list[str]] = None
    attachments: Optional[list[dict]] = None

