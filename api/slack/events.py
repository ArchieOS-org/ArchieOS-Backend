"""Slack events webhook endpoint for Vercel."""

import json
import os
import asyncio
import time
from src.services.slack_verifier import verify_slack_request
from src.services.slack_dedup import is_duplicate_event, generate_event_id
from src.services.debounce_buffer import get_message_debounce_buffer
from src.services.supabase_client import insert_intake_event
from src.utils.logging_config import LoggingConfig, get_logger
from src.utils.logging import (
    get_structured_logger,
    correlation_context,
    log_timing,
    sanitize_message_text,
    mask_user_id,
    generate_correlation_id,
)

# Setup logging configuration (with error handling)
try:
    LoggingConfig.setup_logging()
    logger = get_structured_logger(__name__)
except Exception as e:
    # Fallback to basic logging if setup fails
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to setup structured logging: {e}")


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


async def ingest_minimal_event(payload: dict, correlation_id: str) -> None:
    """Persist minimal event state for audit."""
    try:
        with log_timing("ingest_minimal_event", logger=logger, correlation_id=correlation_id):
            event_id = generate_event_id(payload, {})
            await insert_intake_event(event_id)
            logger.debug(
                "Minimal event ingested",
                correlation_id=correlation_id,
                event_id=event_id
            )
    except Exception as e:
        logger.error(
            "Failed to ingest minimal event",
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True
        )


def handler(request):
    """
    Vercel serverless function handler for Slack events.
    
    Vercel Python runtime provides request as a dict with:
    - method: HTTP method
    - path: request path
    - headers: dict of headers
    - body: request body (string or bytes)
    """
    # Handle URL verification FIRST (before any complex setup)
    # This is critical for Slack's webhook verification
    try:
        body_data = request.get("body", "")
        if isinstance(body_data, bytes):
            raw_body = body_data.decode("utf-8")
        else:
            raw_body = str(body_data)
        
        # Try to parse JSON to check for URL verification
        try:
            body = json.loads(raw_body)
            if body.get("type") == "url_verification":
                challenge = body.get("challenge")
                if challenge:
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"challenge": challenge})
                    }
        except (json.JSONDecodeError, AttributeError):
            pass  # Continue to normal processing
    except Exception:
        pass  # Continue to normal processing if verification check fails
    
    # Now proceed with normal request processing
    request_start_time = time.time()
    
    # Extract or generate correlation ID
    headers = request.get("headers", {})
    try:
        correlation_id = headers.get(
            LoggingConfig.LOG_CORRELATION_ID_HEADER,
            generate_correlation_id()
        )
    except:
        correlation_id = generate_correlation_id()
    
    # Get Vercel request ID if available
    vercel_request_id = headers.get("x-vercel-id") or headers.get("x-request-id")
    
    with correlation_context(correlation_id):
        try:
            # Log request received
            method = request.get("method", "POST")
            path = request.get("path", "/api/slack/events")
            body_data = request.get("body", "")
            body_size = len(body_data) if body_data else 0
            
            logger.info(
                "Slack webhook request received",
                correlation_id=correlation_id,
                vercel_request_id=vercel_request_id,
                method=method,
                path=path,
                body_size_bytes=body_size,
                has_body=bool(body_data)
            )
            
            # Get raw body
            if isinstance(body_data, bytes):
                raw_body = body_data.decode("utf-8")
            else:
                raw_body = str(body_data)
            
            # Parse JSON body
            try:
                body = json.loads(raw_body)
                logger.debug(
                    "Parsed JSON body",
                    correlation_id=correlation_id,
                    body_type=type(body).__name__
                )
            except json.JSONDecodeError:
                # Try form-urlencoded format
                if raw_body.startswith("payload="):
                    import urllib.parse
                    payload_str = urllib.parse.unquote(raw_body[8:].replace("+", "%20"))
                    body = json.loads(payload_str)
                    logger.debug(
                        "Parsed form-urlencoded body",
                        correlation_id=correlation_id
                    )
                else:
                    body = {}
                    logger.warning(
                        "Failed to parse request body",
                        correlation_id=correlation_id,
                        body_preview=raw_body[:100] if raw_body else None
                    )
            
            # Detect event type
            event_type = body.get("type", "unknown")
            logger.info(
                "Event type detected",
                correlation_id=correlation_id,
                event_type=event_type
            )
            
            # Get Slack headers
            timestamp = headers.get("x-slack-request-timestamp", "")
            signature = headers.get("x-slack-signature", "")
            
            # Verify signature with timing
            verification_start = time.time()
            is_valid = verify_slack_request(timestamp, signature, raw_body)
            verification_time_ms = (time.time() - verification_start) * 1000
            
            if not is_valid:
                logger.warning(
                    "Slack signature verification failed",
                    correlation_id=correlation_id,
                    verification_time_ms=round(verification_time_ms, 2),
                    has_timestamp=bool(timestamp),
                    has_signature=bool(signature)
                )
                return {
                    "statusCode": 401,
                    "headers": {
                        "Content-Type": "application/json",
                        LoggingConfig.LOG_CORRELATION_ID_HEADER: correlation_id
                    },
                    "body": json.dumps({"error": "invalid signature"})
                }
            
            logger.info(
                "Slack signature verified",
                correlation_id=correlation_id,
                verification_time_ms=round(verification_time_ms, 2)
            )
            
            # Extract message details for logging
            slack_event_id = body.get("event_id", "")
            slack_user_id = None
            slack_channel_id = None
            slack_message_ts = None
            message_text = None
            
            if body.get("type") == "event_callback" and body.get("event"):
                event = body["event"]
                slack_user_id = event.get("user", "")
                slack_channel_id = event.get("channel", "")
                slack_message_ts = event.get("event_ts") or event.get("ts", "")
                message_text = event.get("text", "")
            
            # Log message received with details
            if message_text or slack_user_id:
                logger.info(
                    "Slack message received",
                    correlation_id=correlation_id,
                    event_type=event_type,
                    slack_event_id=slack_event_id,
                    slack_user_id=mask_user_id(slack_user_id) if slack_user_id else None,
                    slack_channel_id=slack_channel_id,
                    slack_message_ts=slack_message_ts,
                    message_text=sanitize_message_text(message_text) if message_text else None,
                    message_length=len(message_text) if message_text else 0
                )
            
            # Check for duplicates (synchronous check)
            dedup_start = time.time()
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            is_dup = loop.run_until_complete(is_duplicate_event(body, headers))
            dedup_time_ms = (time.time() - dedup_start) * 1000
            
            if is_dup:
                logger.info(
                    "Duplicate event detected, ignoring",
                    correlation_id=correlation_id,
                    slack_event_id=slack_event_id,
                    deduplication_time_ms=round(dedup_time_ms, 2)
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Slack-Ignored-Retry": "true",
                        LoggingConfig.LOG_CORRELATION_ID_HEADER: correlation_id
                    },
                    "body": json.dumps({"ok": True})
                }
            
            logger.debug(
                "Event is not duplicate",
                correlation_id=correlation_id,
                slack_event_id=slack_event_id,
                deduplication_time_ms=round(dedup_time_ms, 2)
            )
            
            # Normalize event
            normalized = normalize_event(body)
            if normalized:
                logger.info(
                    "Event normalized",
                    correlation_id=correlation_id,
                    normalized_type=normalized.get("type"),
                    normalized_user=mask_user_id(normalized.get("user", "")),
                    normalized_channel=normalized.get("channel", "")
                )
            else:
                logger.debug(
                    "Event could not be normalized",
                    correlation_id=correlation_id,
                    event_type=event_type
                )
            
            # Normalize event and persist minimal state before ACK
            if normalized:
                try:
                    loop.run_until_complete(ingest_minimal_event(body, correlation_id))
                    logger.info(
                        "Ingested minimal event before ACK",
                        correlation_id=correlation_id,
                        normalized_type=normalized.get("type")
                    )
                except Exception as e:
                    logger.error(
                        "Pre-ACK ingest error",
                        correlation_id=correlation_id,
                        error=str(e),
                        exc_info=True
                    )
            
            # ACK immediately (200 OK)
            response = {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    LoggingConfig.LOG_CORRELATION_ID_HEADER: correlation_id
                },
                "body": json.dumps({"ok": True})
            }
            
            # Fire-and-forget background processing with debounce buffer
            try:
                debounce_buffer = get_message_debounce_buffer()
                # Schedule async task (will run in background if event loop allows)
                task = asyncio.create_task(debounce_buffer.enqueue(body))
                # Don't await - let it run in background
                
                buffer_size = len(debounce_buffer.buffer.get(normalized.get("channel", ""), [])) if normalized else 0
                logger.info(
                    "Message enqueued to debounce buffer",
                    correlation_id=correlation_id,
                    event_type=normalized.get("type") if normalized else "unknown",
                    channel_id=normalized.get("channel") if normalized else None,
                    buffer_size=buffer_size
                )
            except Exception as e:
                logger.error(
                    "Debounce buffer enqueue error",
                    correlation_id=correlation_id,
                    error=str(e),
                    exc_info=True
                )
            
            # Log response with total processing time
            total_time_ms = (time.time() - request_start_time) * 1000
            logger.info(
                "Slack webhook request completed",
                correlation_id=correlation_id,
                status_code=response["statusCode"],
                total_processing_time_ms=round(total_time_ms, 2)
            )
            
            return response
            
        except Exception as e:
            total_time_ms = (time.time() - request_start_time) * 1000
            logger.error(
                "Error processing Slack event",
                correlation_id=correlation_id,
                error=str(e),
                total_processing_time_ms=round(total_time_ms, 2),
                exc_info=True
            )
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    LoggingConfig.LOG_CORRELATION_ID_HEADER: correlation_id
                },
                "body": json.dumps({"error": "internal server error"})
            }
