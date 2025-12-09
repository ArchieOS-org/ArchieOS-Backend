"""Slack event deduplication using Supabase intake_events table."""

import hashlib
import json
import logging
from typing import Optional
from src.services.supabase_client import check_intake_event_exists, insert_intake_event

logger = logging.getLogger(__name__)


def generate_event_id(body: dict, headers: dict) -> str:
    """
    Generate deterministic event ID for deduplication.
    
    Uses event_id from body if available, otherwise generates from body content.
    """
    # Try to use Slack's event_id if available
    if isinstance(body, dict):
        event_id = body.get("event_id")
        if event_id:
            return str(event_id)
        
        # For event_callback, use the event's event_ts
        if body.get("type") == "event_callback" and body.get("event"):
            event_ts = body["event"].get("event_ts") or body["event"].get("ts")
            if event_ts:
                return f"slack_event_{event_ts}"
        
        # Fallback: hash the body content
        body_str = json.dumps(body, sort_keys=True)
        return hashlib.sha1(body_str.encode()).hexdigest()
    
    # Last resort: hash the string representation
    body_str = str(body)
    return hashlib.sha1(body_str.encode()).hexdigest()


async def is_duplicate_event(body: dict, headers: dict) -> bool:
    """
    Check if an event is a duplicate.
    
    Returns True if event already processed, False otherwise.
    """
    try:
        event_id = generate_event_id(body, headers)
        exists = await check_intake_event_exists(event_id)
        
        if exists:
            logger.info(f"Duplicate event detected: {event_id}")
            return True
        
        # Mark as seen (fire and forget)
        try:
            await insert_intake_event(event_id)
        except Exception as e:
            logger.warning(f"Failed to insert intake event (non-fatal): {e}")
        
        return False
    except Exception as e:
        logger.error(f"Error checking duplicate event: {e}")
        # On error, don't treat as duplicate (allow processing)
        return False

