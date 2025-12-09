"""Tests for debounce buffer service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from freezegun import freeze_time
from src.services.debounce_buffer import DebounceBuffer


@pytest.mark.unit
@pytest.mark.asyncio
async def test_debounce_buffer_enqueue_with_channel():
    """Test enqueuing message with channel ID."""
    buffer = DebounceBuffer(window_seconds=60)
    
    event = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C123456",
            "text": "Test message"
        }
    }
    
    await buffer.enqueue(event)
    
    assert "C123456" in buffer.buffer
    assert len(buffer.buffer["C123456"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_debounce_buffer_enqueue_without_channel():
    """Test enqueuing message without channel processes immediately."""
    buffer = DebounceBuffer(window_seconds=60)
    
    event = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": "Test message"
        }
    }
    
    with patch.object(buffer, '_process_event', new_callable=AsyncMock) as mock_process:
        await buffer.enqueue(event)
        mock_process.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
@freeze_time("2024-12-09 12:00:00")
async def test_debounce_buffer_time_window():
    """Test that messages are grouped within time window."""
    buffer = DebounceBuffer(window_seconds=300)  # 5 minutes
    
    event1 = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C123456",
            "text": "Message 1"
        }
    }
    
    event2 = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C123456",
            "text": "Message 2"
        }
    }
    
    await buffer.enqueue(event1)
    await buffer.enqueue(event2)
    
    assert len(buffer.buffer["C123456"]) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_debounce_buffer_multiple_channels():
    """Test that messages from different channels are buffered separately."""
    buffer = DebounceBuffer(window_seconds=60)
    
    event1 = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C123456",
            "text": "Message 1"
        }
    }
    
    event2 = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C789012",
            "text": "Message 2"
        }
    }
    
    await buffer.enqueue(event1)
    await buffer.enqueue(event2)
    
    assert "C123456" in buffer.buffer
    assert "C789012" in buffer.buffer
    assert len(buffer.buffer["C123456"]) == 1
    assert len(buffer.buffer["C789012"]) == 1

