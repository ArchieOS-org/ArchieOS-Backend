"""Slack events webhook endpoint for Vercel."""

import json
import os
import asyncio
import logging
from src.services.slack_verifier import verify_slack_request
from src.services.slack_dedup import is_duplicate_event, generate_event_id
from src.services.debounce_buffer import get_message_debounce_buffer
from src.services.supabase_client import insert_intake_event

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def normalize_event(body: dict) -> dict | None:
    """
    Normalize Slack event to standard format.
    
    Returns dict with type, text, user, channel, event_id or None.
    """
    if not isinstance(body, dict):
        return None
    
    # Handle event_callback
    if body.get("type") == "event_callback" and body.get("event"):
        event = body["event"]
        event_type = event.get("type")
        
        if event_type == "app_mention":
            return {
                "type": "app_mention",
                "text": event.get("text", ""),
                "user": event.get("user", ""),
                "channel": event.get("channel", ""),
                "event_id": body.get("event_id", "")
            }
        
        if event_type == "message":
            channel_type = event.get("channel_type")
            if channel_type in ("channel", "group"):
                type_label = "message.groups" if channel_type == "group" else "message.channels"
                return {
                    "type": type_label,
                    "text": event.get("text", ""),
                    "user": event.get("user", ""),
                    "channel": event.get("channel", ""),
                    "event_id": body.get("event_id", "")
                }
    
    # Handle shortcut
    if body.get("type") == "shortcut":
        user_obj = body.get("user", {})
        user_id = user_obj.get("id") if isinstance(user_obj, dict) else body.get("user_id", "")
        return {
            "type": "shortcut",
            "text": body.get("callback_id", ""),
            "user": user_id
        }
    
    return None


async def ingest_minimal_event(payload: dict) -> None:
    """Persist minimal event state for audit."""
    try:
        event_id = generate_event_id(payload, {})
        await insert_intake_event(event_id)
    except Exception as e:
        logger.error(f"Failed to ingest minimal event: {e}")


def handler(request):
    """
    Vercel serverless function handler for Slack events.
    
    Vercel Python runtime provides request as a dict with:
    - method: HTTP method
    - path: request path
    - headers: dict of headers
    - body: request body (string or bytes)
    """
    try:
        # Get raw body
        body_data = request.get("body", "")
        if isinstance(body_data, bytes):
            raw_body = body_data.decode("utf-8")
        else:
            raw_body = str(body_data)
        
        # Parse JSON body
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            # Try form-urlencoded format
            if raw_body.startswith("payload="):
                import urllib.parse
                payload_str = urllib.parse.unquote(raw_body[8:].replace("+", "%20"))
                body = json.loads(payload_str)
            else:
                body = {}
        
        # Handle URL verification challenge
        if body.get("type") == "url_verification":
            challenge = body.get("challenge")
            if challenge:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"challenge": challenge})
                }
        
        # Get headers
        headers = request.get("headers", {})
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        
        # Verify signature
        if not verify_slack_request(timestamp, signature, raw_body):
            logger.warning("Slack signature verification failed")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "invalid signature"})
            }
        
        # Check for duplicates (synchronous check)
        # Note: In serverless, we need to handle async carefully
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        is_dup = loop.run_until_complete(is_duplicate_event(body, headers))
        if is_dup:
            logger.info("Duplicate event detected, ignoring")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "X-Slack-Ignored-Retry": "true"
                },
                "body": json.dumps({"ok": True})
            }
        
        # Normalize event and persist minimal state before ACK
        normalized = normalize_event(body)
        if normalized:
            try:
                loop.run_until_complete(ingest_minimal_event(body))
                logger.info("Ingested minimal event before ACK", extra={"type": normalized.get("type")})
            except Exception as e:
                logger.error(f"Pre-ack ingest error: {e}")
        
        # ACK immediately (200 OK)
        response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": True})
        }
        
        # Fire-and-forget background processing with debounce buffer
        # In serverless, we'll process synchronously but quickly
        try:
            debounce_buffer = get_message_debounce_buffer()
            # Schedule async task (will run in background if event loop allows)
            task = asyncio.create_task(debounce_buffer.enqueue(body))
            # Don't await - let it run in background
            logger.info("Message enqueued to debounce buffer", extra={"event_type": normalized.get("type") if normalized else "unknown"})
        except Exception as e:
            logger.error(f"Debounce buffer enqueue error: {e}", exc_info=True)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "internal server error"})
        }
