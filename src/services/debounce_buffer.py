"""Debounce buffer service - group messages within time window."""

import os
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from src.services.supabase_client import SupabaseClient, enqueue_intake_message
from src.services.slack_classifier import classify_and_enqueue_slack_message, extract_links
from src.utils.logging import (
    get_structured_logger,
    log_timing,
    sanitize_message_text,
    mask_user_id,
    get_correlation_id,
)

logger = get_structured_logger(__name__)

# Default debounce window (seconds)
DEFAULT_DEBOUNCE_WINDOW = int(os.environ.get("DEBOUNCE_WINDOW_SECONDS", "300"))  # 5 minutes


class DebounceBuffer:
    """Buffer messages and process them in batches after a time window."""
    
    def __init__(self, window_seconds: int = DEFAULT_DEBOUNCE_WINDOW):
        self.window_seconds = window_seconds
        self.buffer: dict[str, list[dict]] = {}  # channel_id -> list of events
        self.timers: dict[str, asyncio.Task] = {}
        logger.info(
            "DebounceBuffer initialized",
            debounce_window_seconds=window_seconds
        )
    
    async def enqueue(self, body: dict) -> None:
        """
        Enqueue a Slack event to the debounce buffer.
        
        Groups events by channel and processes them after the debounce window.
        """
        correlation_id = get_correlation_id()
        
        # Extract channel ID for grouping
        channel_id = None
        if isinstance(body, dict):
            if body.get("type") == "event_callback" and body.get("event"):
                channel_id = body["event"].get("channel") or body["event"].get("channel_id")
            elif body.get("channel"):
                channel_id = body["channel"].get("id") if isinstance(body["channel"], dict) else body["channel"]
            elif body.get("channel_id"):
                channel_id = body["channel_id"]
        
        # Extract event details for logging
        event_id = None
        user_id = None
        message_text = None
        if isinstance(body, dict):
            if body.get("type") == "event_callback" and body.get("event"):
                event = body["event"]
                event_id = body.get("event_id", "")
                user_id = event.get("user", "")
                message_text = event.get("text", "")
        
        # If no channel, process immediately
        if not channel_id:
            logger.info(
                "Processing event immediately (no channel ID)",
                correlation_id=correlation_id,
                slack_event_id=event_id,
                slack_user_id=mask_user_id(user_id) if user_id else None
            )
            await self._process_event(body)
            return
        
        # Add to buffer
        if channel_id not in self.buffer:
            self.buffer[channel_id] = []
        
        buffer_size_before = len(self.buffer[channel_id])
        self.buffer[channel_id].append(body)
        buffer_size_after = len(self.buffer[channel_id])
        
        logger.info(
            "Message enqueued to debounce buffer",
            correlation_id=correlation_id,
            channel_id=channel_id,
            buffer_size_before=buffer_size_before,
            buffer_size_after=buffer_size_after,
            slack_event_id=event_id,
            slack_user_id=mask_user_id(user_id) if user_id else None,
            message_preview=sanitize_message_text(message_text, max_length=100) if message_text else None,
            debounce_window_seconds=self.window_seconds
        )
        
        # Reset timer for this channel
        if channel_id in self.timers:
            self.timers[channel_id].cancel()
            logger.debug(
                "Debounce timer reset for channel",
                correlation_id=correlation_id,
                channel_id=channel_id
            )
        
        # Schedule processing after debounce window
        self.timers[channel_id] = asyncio.create_task(
            self._process_channel_after_delay(channel_id)
        )
    
    async def _process_channel_after_delay(self, channel_id: str) -> None:
        """Process all buffered events for a channel after delay."""
        correlation_id = get_correlation_id()
        
        logger.info(
            "Debounce delay started for channel",
            correlation_id=correlation_id,
            channel_id=channel_id,
            debounce_window_seconds=self.window_seconds,
            messages_buffered=len(self.buffer.get(channel_id, []))
        )
        
        await asyncio.sleep(self.window_seconds)
        
        if channel_id in self.buffer:
            events = self.buffer.pop(channel_id)
            messages_count = len(events)
            
            if channel_id in self.timers:
                del self.timers[channel_id]
            
            logger.info(
                "Buffer flush started for channel",
                correlation_id=correlation_id,
                channel_id=channel_id,
                messages_processed=messages_count,
                debounce_window_seconds=self.window_seconds
            )
            
            # Process each event
            processed_count = 0
            failed_count = 0
            
            for idx, event in enumerate(events):
                try:
                    with log_timing(
                        "process_debounced_event",
                        logger=logger,
                        correlation_id=correlation_id,
                        channel_id=channel_id,
                        event_index=idx + 1,
                        total_events=messages_count
                    ):
                    await self._process_event(event)
                        processed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(
                        "Error processing debounced event",
                        correlation_id=correlation_id,
                        channel_id=channel_id,
                        event_index=idx + 1,
                        total_events=messages_count,
                        error=str(e),
                        exc_info=True
                    )
            
            logger.info(
                "Buffer flush completed for channel",
                correlation_id=correlation_id,
                channel_id=channel_id,
                messages_processed=messages_count,
                processed_successfully=processed_count,
                processed_failed=failed_count,
                debounce_window_seconds=self.window_seconds
                    )
    
    async def _process_event(self, body: dict) -> None:
        """Process a single event (classify and enqueue)."""
        correlation_id = get_correlation_id()
        
        # Extract event data
        event_data = self._extract_event_data(body)
        if not event_data:
            logger.debug(
                "Could not extract event data from body",
                correlation_id=correlation_id,
                body_type=type(body).__name__
            )
            return
        
        text = event_data.get("text", "")
        slack_user_id = event_data.get("user_id", "")
        channel_id = event_data.get("channel_id", "")
        ts = event_data.get("ts", "")
        
        logger.debug(
            "Event data extracted",
            correlation_id=correlation_id,
            channel_id=channel_id,
            slack_user_id=mask_user_id(slack_user_id) if slack_user_id else None,
            message_ts=ts,
            has_text=bool(text),
            text_length=len(text) if text else 0
        )
        
        if not text or not slack_user_id or not channel_id or not ts:
            logger.debug(
                "Missing required event fields",
                correlation_id=correlation_id,
                has_text=bool(text),
                has_user_id=bool(slack_user_id),
                has_channel_id=bool(channel_id),
                has_ts=bool(ts)
            )
            return
        
        # Extract links
        links = extract_links(text)
        attachments = event_data.get("attachments")
        
        logger.debug(
            "Processing event for classification",
            correlation_id=correlation_id,
            channel_id=channel_id,
            slack_user_id=mask_user_id(slack_user_id),
            message_ts=ts,
            message_preview=sanitize_message_text(text, max_length=100),
            links_count=len(links) if links else 0,
            has_attachments=bool(attachments)
        )
        
        # Classify and enqueue
        try:
            with log_timing(
                "classify_and_enqueue_message",
                logger=logger,
                correlation_id=correlation_id,
                channel_id=channel_id,
                slack_user_id=mask_user_id(slack_user_id)
            ):
            await classify_and_enqueue_slack_message(
                text=text,
                slack_user_id=slack_user_id,
                channel_id=channel_id,
                ts=ts,
                links=links,
                attachments=attachments
            )
                logger.debug(
                    "Event processed successfully",
                    correlation_id=correlation_id,
                    channel_id=channel_id,
                    slack_user_id=mask_user_id(slack_user_id)
                )
        except Exception as e:
            logger.error(
                "Error classifying message",
                correlation_id=correlation_id,
                channel_id=channel_id,
                slack_user_id=mask_user_id(slack_user_id),
                error=str(e),
                exc_info=True
            )
            raise
    
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
