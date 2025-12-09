"""Tests for Slack user resolution service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.services.slack_users import resolve_slack_user, generate_realtor_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_slack_user_existing(mock_supabase_client):
    """Test resolving existing Slack user."""
    from src.services.supabase_client import SupabaseClient
    
    # Mock existing realtor
    mock_realtor = {
        "realtor_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "slack_user_id": "U123456",
        "name": "John Doe",
        "email": "john@example.com"
    }
    
    # Mock SupabaseClient context manager
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_query = MagicMock()
    
    mock_query.eq.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[mock_realtor])
    mock_table.select.return_value = mock_query
    mock_client.table.return_value = mock_table
    
    with patch('src.services.slack_users.SupabaseClient') as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        result = await resolve_slack_user("U123456")
        
        assert result is not None
        assert result["realtor_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_table.select.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_slack_user_auto_create(mock_supabase_client):
    """Test auto-creating realtor for new Slack user."""
    from src.services.supabase_client import SupabaseClient
    
    # Mock SupabaseClient - first query returns empty, insert succeeds
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_select_query = MagicMock()
    mock_insert_query = MagicMock()
    
    # First call (select) returns empty
    mock_select_query.eq.return_value = mock_select_query
    mock_select_query.select.return_value = mock_select_query
    mock_select_query.execute.return_value = MagicMock(data=[])
    
    # Second call (insert) succeeds
    new_realtor = {
        "realtor_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "slack_user_id": "U789012",
        "name": "User_789012",
        "email": "U789012@slack.local"
    }
    mock_insert_query.execute.return_value = MagicMock(data=[new_realtor])
    mock_table.insert.return_value = mock_insert_query
    mock_table.select.return_value = mock_select_query
    
    mock_client.table.return_value = mock_table
    
    with patch('src.services.slack_users.SupabaseClient') as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        result = await resolve_slack_user("U789012")
        
        assert result is not None
        assert result["realtor_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_table.insert.assert_called_once()


@pytest.mark.unit
def test_generate_realtor_id():
    """Test realtor ID generation."""
    realtor_id = generate_realtor_id()
    
    assert isinstance(realtor_id, str)
    assert len(realtor_id) > 0
    # ULID format: 26 characters
    assert len(realtor_id) == 26

