"""Tests for Slack event deduplication."""

import pytest
from src.services.slack_dedup import generate_event_id


def test_generate_event_id_from_event_id():
    """Test event ID generation from body event_id."""
    body = {
        "event_id": "Ev123456"
    }
    headers = {}
    
    event_id = generate_event_id(body, headers)
    assert event_id == "Ev123456"


def test_generate_event_id_from_event_callback():
    """Test event ID generation from event_callback."""
    body = {
        "type": "event_callback",
        "event": {
            "event_ts": "1234567890.123456"
        }
    }
    headers = {}
    
    event_id = generate_event_id(body, headers)
    assert event_id == "slack_event_1234567890.123456"


def test_generate_event_id_fallback_hash():
    """Test fallback to hash when no event_id available."""
    body = {
        "type": "unknown",
        "data": "some data"
    }
    headers = {}
    
    event_id = generate_event_id(body, headers)
    assert event_id.startswith("slack_event_") or len(event_id) == 40  # SHA1 hex length

