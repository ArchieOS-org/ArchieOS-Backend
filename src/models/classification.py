"""Classification models matching mogadishu-v1 TypeScript schema."""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message classification types."""
    GROUP = "GROUP"
    STRAY = "STRAY"
    INFO_REQUEST = "INFO_REQUEST"
    IGNORE = "IGNORE"


class TaskKey(str, Enum):
    """Valid task_key values for STRAY messages."""
    # Sale Listings
    SALE_ACTIVE_TASKS = "SALE_ACTIVE_TASKS"
    SALE_SOLD_TASKS = "SALE_SOLD_TASKS"
    SALE_CLOSING_TASKS = "SALE_CLOSING_TASKS"
    # Lease Listings
    LEASE_ACTIVE_TASKS = "LEASE_ACTIVE_TASKS"
    LEASE_LEASED_TASKS = "LEASE_LEASED_TASKS"
    LEASE_CLOSING_TASKS = "LEASE_CLOSING_TASKS"
    LEASE_ACTIVE_TASKS_ARLYN = "LEASE_ACTIVE_TASKS_ARLYN"
    # Re-List Listings
    RELIST_LISTING_DEAL_SALE = "RELIST_LISTING_DEAL_SALE"
    RELIST_LISTING_DEAL_LEASE = "RELIST_LISTING_DEAL_LEASE"
    # Buyer Deals
    BUYER_DEAL = "BUYER_DEAL"
    BUYER_DEAL_CLOSING_TASKS = "BUYER_DEAL_CLOSING_TASKS"
    # Lease Tenant Deals
    LEASE_TENANT_DEAL = "LEASE_TENANT_DEAL"
    LEASE_TENANT_DEAL_CLOSING_TASKS = "LEASE_TENANT_DEAL_CLOSING_TASKS"
    # Pre-Con Deals
    PRECON_DEAL = "PRECON_DEAL"
    # Mutual Release
    MUTUAL_RELEASE_STEPS = "MUTUAL_RELEASE_STEPS"
    # General Ops
    OPS_MISC_TASK = "OPS_MISC_TASK"


class GroupKey(str, Enum):
    """Valid group_key values for GROUP messages."""
    SALE_LISTING = "SALE_LISTING"
    LEASE_LISTING = "LEASE_LISTING"
    SALE_LEASE_LISTING = "SALE_LEASE_LISTING"
    SOLD_SALE_LEASE_LISTING = "SOLD_SALE_LEASE_LISTING"
    RELIST_LISTING = "RELIST_LISTING"
    RELIST_LISTING_DEAL_SALE_OR_LEASE = "RELIST_LISTING_DEAL_SALE_OR_LEASE"
    BUY_OR_LEASED = "BUY_OR_LEASED"
    MARKETING_AGENDA_TEMPLATE = "MARKETING_AGENDA_TEMPLATE"


class ListingType(str, Enum):
    """Listing type values."""
    SALE = "SALE"
    LEASE = "LEASE"


class ListingInfo(BaseModel):
    """Listing information extracted from message."""
    type: Optional[Literal["SALE", "LEASE"]] = Field(
        None,
        description="Listing type: SALE or LEASE if explicit or unambiguously implied, otherwise null"
    )
    address: Optional[str] = Field(
        None,
        description="Street/building/unit address if explicit in text or provided links, otherwise null"
    )


class ClassificationV1(BaseModel):
    """Classification schema matching TypeScript ClassificationV1."""
    schema_version: Literal[1] = Field(
        1,
        description="Schema version"
    )
    message_type: MessageType = Field(
        ...,
        description="Message classification type: GROUP, STRAY, INFO_REQUEST, or IGNORE"
    )
    task_key: Optional[TaskKey] = Field(
        None,
        description="Task key for STRAY messages, null for GROUP/INFO_REQUEST/IGNORE"
    )
    group_key: Optional[GroupKey] = Field(
        None,
        description="Group key for GROUP messages, null for STRAY/INFO_REQUEST/IGNORE"
    )
    listing: ListingInfo = Field(
        ...,
        description="Listing information extracted from message"
    )
    assignee_hint: Optional[str] = Field(
        None,
        description="Person explicitly named or @-mentioned, null if only pronouns or team name"
    )
    due_date: Optional[str] = Field(
        None,
        description="Due date in ISO format (yyyy-MM-dd or yyyy-MM-ddTHH:mm), null if not resolvable"
    )
    task_title: Optional[str] = Field(
        None,
        max_length=80,
        description="Concise task title (5-10 words) for STRAY messages only, null for GROUP/INFO_REQUEST/IGNORE"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    explanations: Optional[list[str]] = Field(
        None,
        description="Brief explanations for assumptions, heuristics, or missing info, null if not needed"
    )

    def model_post_init(self, __context: any) -> None:
        """Validate that exactly one of group_key or task_key is non-null (unless INFO_REQUEST/IGNORE)."""
        message_type = self.message_type
        group_present = self.group_key is not None
        task_present = self.task_key is not None

        if message_type in (MessageType.INFO_REQUEST, MessageType.IGNORE):
            if group_present or task_present:
                raise ValueError("group_key and task_key must both be null for INFO_REQUEST/IGNORE")
        else:
            if group_present == task_present:
                raise ValueError("Exactly one of group_key or task_key must be non-null")

