"""Integration tests for Supabase schema compatibility."""

import pytest
from src.services.slack_users import resolve_slack_user, generate_realtor_id
from src.services.supabase_client import (
    create_listing,
    create_activity,
    create_agent_task,
    get_realtor_by_slack_id
)
from src.models.realtor import Realtor
from src.models.activity import Activity
from src.models.agent_task import AgentTask


def test_generate_realtor_id():
    """Test realtor ID generation."""
    realtor_id = generate_realtor_id()
    assert isinstance(realtor_id, str)
    assert len(realtor_id) > 0


def test_generate_listing_id():
    """Test listing ID generation."""
    from src.services.intake_ingestor import generate_listing_id
    listing_id = generate_listing_id()
    assert isinstance(listing_id, str)
    assert len(listing_id) > 0


def test_generate_task_id():
    """Test task ID generation."""
    from src.services.intake_ingestor import generate_task_id
    task_id = generate_task_id()
    assert isinstance(task_id, str)
    assert len(task_id) > 0


@pytest.mark.asyncio
async def test_realtor_model():
    """Test Realtor model matches schema."""
    realtor = Realtor(
        realtor_id="test_realtor_123",
        email="test@example.com",
        name="Test Realtor",
        status="active"
    )
    assert realtor.realtor_id == "test_realtor_123"
    assert realtor.email == "test@example.com"
    assert realtor.status == "active"


@pytest.mark.asyncio
async def test_activity_model():
    """Test Activity model matches schema."""
    activity = Activity(
        task_id="test_task_123",
        listing_id="test_listing_123",
        name="Test Activity",
        task_category="MARKETING",
        status="OPEN"
    )
    assert activity.task_id == "test_task_123"
    assert activity.listing_id == "test_listing_123"
    assert activity.task_category == "MARKETING"


@pytest.mark.asyncio
async def test_agent_task_model():
    """Test AgentTask model matches schema."""
    agent_task = AgentTask(
        task_id="test_task_123",
        realtor_id="test_realtor_123",
        name="Test Agent Task",
        task_category="OTHER",
        status="OPEN"
    )
    assert agent_task.task_id == "test_task_123"
    assert agent_task.realtor_id == "test_realtor_123"
    assert agent_task.task_category == "OTHER"


def test_map_task_key_to_category():
    """Test task key to category mapping."""
    from src.services.intake_ingestor import map_task_key_to_category
    assert map_task_key_to_category("SALE_ACTIVE_TASKS") == "MARKETING"
    assert map_task_key_to_category("OPS_MISC_TASK") == "OTHER"
    assert map_task_key_to_category("UNKNOWN_KEY") == "OTHER"

