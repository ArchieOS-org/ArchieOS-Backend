"""Tests for Slack events endpoint."""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.utils.helpers import create_slack_event, generate_slack_signature, create_vercel_request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_slack_events_url_verification(mock_vercel_request):
    """Test URL verification challenge handling."""
    from api.slack.events import handler
    
    # Create URL verification request
    challenge_body = {
        "type": "url_verification",
        "challenge": "test-challenge-token"
    }
    
    request = create_vercel_request(
        body=challenge_body,
        headers={
            "content-type": "application/json"
        }
    )
    
    response = handler(request)
    
    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert response_body["challenge"] == "test-challenge-token"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_slack_events_invalid_signature(mock_vercel_request):
    """Test rejection of invalid signature."""
    from api.slack.events import handler
    
    request = create_vercel_request(
        body=create_slack_event(),
        headers={
            "x-slack-signature": "v0=invalid",
            "x-slack-request-timestamp": str(int(__import__('time').time())),
            "content-type": "application/json"
        }
    )
    
    with patch('api.slack.events.verify_slack_request', return_value=False):
        response = handler(request)
        
        assert response["statusCode"] == 401
        response_body = json.loads(response["body"])
        assert "error" in response_body


@pytest.mark.unit
def test_slack_events_duplicate_event(mock_vercel_request, sample_slack_event):
    """Test handling of duplicate events."""
    from api.slack.events import handler
    import asyncio
    
    request = create_vercel_request(
        body=sample_slack_event,
        headers={
            "x-slack-signature": "v0=valid",
            "x-slack-request-timestamp": str(int(__import__('time').time())),
            "content-type": "application/json"
        }
    )
    
    with patch('api.slack.events.verify_slack_request', return_value=True):
        with patch('api.slack.events.is_duplicate_event') as mock_dup:
            # Create a new event loop for this test
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Mock the async function to return immediately
            async def mock_dup_async(*args, **kwargs):
                return True
            mock_dup.side_effect = mock_dup_async
            
            # Use asyncio.run to handle the event loop properly
            def run_handler():
                # Create new event loop for handler
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return handler(request)
                finally:
                    new_loop.close()
            
            response = run_handler()
            
            assert response["statusCode"] == 200
            response_body = json.loads(response["body"])
            assert response_body["ok"] is True
            assert "X-Slack-Ignored-Retry" in response["headers"]


@pytest.mark.unit
def test_slack_events_valid_event(mock_vercel_request, sample_slack_event):
    """Test processing of valid event."""
    from api.slack.events import handler
    import asyncio
    
    request = create_vercel_request(
        body=sample_slack_event,
        headers={
            "x-slack-signature": "v0=valid",
            "x-slack-request-timestamp": str(int(__import__('time').time())),
            "content-type": "application/json"
        }
    )
    
    with patch('api.slack.events.verify_slack_request', return_value=True):
        with patch('api.slack.events.is_duplicate_event') as mock_dup:
            with patch('api.slack.events.ingest_minimal_event') as mock_ingest:
                with patch('api.slack.events.get_message_debounce_buffer') as mock_buffer:
                    # Mock async functions
                    async def mock_dup_async(*args, **kwargs):
                        return False
                    async def mock_ingest_async(*args, **kwargs):
                        return None
                    
                    mock_dup.side_effect = mock_dup_async
                    mock_ingest.side_effect = mock_ingest_async
                    
                    mock_buffer_instance = Mock()
                    mock_buffer_instance.enqueue = Mock()  # Don't await in handler
                    mock_buffer.return_value = mock_buffer_instance
                    
                    # Create new event loop for handler
                    def run_handler():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return handler(request)
                        finally:
                            new_loop.close()
                    
                    response = run_handler()
                    
                    assert response["statusCode"] == 200
                    response_body = json.loads(response["body"])
                    assert response_body["ok"] is True

