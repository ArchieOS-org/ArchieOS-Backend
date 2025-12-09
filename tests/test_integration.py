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


@pytest.mark.integration
def test_generate_realtor_id():
    """Test realtor ID generation."""
    realtor_id = generate_realtor_id()
    assert isinstance(realtor_id, str)
    assert len(realtor_id) > 0


@pytest.mark.integration
def test_generate_listing_id():
    """Test listing ID generation."""
    from src.services.intake_ingestor import generate_listing_id
    listing_id = generate_listing_id()
    assert isinstance(listing_id, str)
    assert len(listing_id) > 0
