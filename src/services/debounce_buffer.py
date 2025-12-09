"""Debounce buffer service - group messages within time window."""

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from src.services.supabase_client import SupabaseClient, enqueue_intake_message
from src.services.slack_classifier import classify_and_enqueue_slack_message, extract_links

logger = logging.getLogger(__name__)

# Default debounce window (seconds)
DEFAULT_DEBOUNCE_WINDOW = int(os.environ.get("DEBOUNCE_WINDOW_SECONDS", "300"))  # 5 minutes


class DebounceBuffer:
    """Buffer messages and process them in batches after a time window."""
    
    def __init__(self, window_seconds: int = DEFAULT_DEBOUNCE_WINDOW):
        self.window_seconds = window_seconds
        self.buffer: dict[str, list[dict]] = {}  # channel_id -> list of events
        self.timers: dict[str, asyncio.Task] = {}
    
    async def enqueue(self, body: dict) -> None:
        """
        Enqueue a Slack event to the debounce buffer.
        
        Groups events by channel and processes them after the debounce window.
        """
        # Extract channel ID for grouping
        channel_id = None
        if isinstance(body, dict):
            if body.get("type") == "event_callback" and body.get("event"):
                channel_id = body["event"].get("channel") or body["event"].get("channel_id")
            elif body.get("channel"):
                channel_id = body["channel"].get("id") if isinstance(body["channel"], dict) else body["channel"]
            elif body.get("channel_id"):
                channel_id = body["channel_id"]
        
        # If no channel, process immediately
        if not channel_id:
            await self._process_event(body)
            return
        
        # Add to buffer
        if channel_id not in self.buffer:
            self.buffer[channel_id] = []
        
        self.buffer[channel_id].append(body)
        
        # Reset timer for this channel
        if channel_id in self.timers:
            self.timers[channel_id].cancel()
        
        # Schedule processing after debounce window
        self.timers[channel_id] = asyncio.create_task(
            self._process_channel_after_delay(channel_id)
        )
    
    async def _process_channel_after_delay(self, channel_id: str) -> None:
        """Process all buffered events for a channel after delay."""
        await asyncio.sleep(self.window_seconds)
        
        if channel_id in self.buffer:
            events = self.buffer.pop(channel_id)
            if channel_id in self.timers:
                del self.timers[channel_id]
            
            # Process each event
            for event in events:
                try:
                    await self._process_event(event)
                except Exception as e:
                    logger.error(
                        f"Error processing debounced event: {e}",
                        extra={"channel_id": channel_id, "error": str(e)}
                    )
    
    async def _process_event(self, body: dict) -> None:
        """Process a single event (classify and enqueue)."""
        # Extract event data
        event_data = self._extract_event_data(body)
        if not event_data:
            logger.debug("Could not extract event data from body")
            return
        
        text = event_data.get("text", "")
        slack_user_id = event_data.get("user_id", "")
        channel_id = event_data.get("channel_id", "")
        ts = event_data.get("ts", "")
        
        if not text or not slack_user_id or not channel_id or not ts:
            logger.debug("Missing required event fields")
            return
        
        # Extract links
        links = extract_links(text)
        attachments = event_data.get("attachments")
        
        # Classify and enqueue
        try:
            await classify_and_enqueue_slack_message(
                text=text,
                slack_user_id=slack_user_id,
                channel_id=channel_id,
                ts=ts,
                links=links,
                attachments=attachments
            )
        except Exception as e:
            logger.error(f"Error classifying message: {e}", exc_info=True)
    
    def _extract_event_data(self, body: dict) -> Optional[dict]:
        """Extract event data from Slack webhook body."""
        if not isinstance(body, dict):
            return None
        
        # Handle event_callback
        if body.get("type") == "event_callback" and body.get("event"):
            event = body["event"]
            return {
                "text": event.get("text", ""),
                "user_id": event.get("user") or event.get("user_id", ""),
                "channel_id": event.get("channel") or event.get("channel_id", ""),
                "ts": event.get("event_ts") or event.get("ts", ""),
                "attachments": event.get("attachments")
            }
        
        # Handle shortcut/message_action
        if body.get("type") in ("shortcut", "message_action"):
            return {
                "text": body.get("message", {}).get("text", "") if isinstance(body.get("message"), dict) else body.get("text", ""),
                "user_id": body.get("user", {}).get("id", "") if isinstance(body.get("user"), dict) else body.get("user_id", ""),
                "channel_id": body.get("channel", {}).get("id", "") if isinstance(body.get("channel"), dict) else body.get("channel_id", ""),
                "ts": body.get("action_ts") or body.get("message", {}).get("ts", "") if isinstance(body.get("message"), dict) else body.get("ts", ""),
                "attachments": body.get("attachments")
            }
        
        return None


# Global debounce buffer instance
_message_debounce_buffer: Optional[DebounceBuffer] = None


def get_message_debounce_buffer() -> DebounceBuffer:
    """Get or create global debounce buffer instance."""
    global _message_debounce_buffer
    if _message_debounce_buffer is None:
        window = int(os.environ.get("DEBOUNCE_WINDOW_SECONDS", "300"))
        _message_debounce_buffer = DebounceBuffer(window_seconds=window)
    return _message_debounce_buffer

