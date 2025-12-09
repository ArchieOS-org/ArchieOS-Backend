"""Slack events webhook endpoint for Vercel."""

from http.server import BaseHTTPRequestHandler
import json
import os
import asyncio
import time
import logging

# Setup basic logging first
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Lazy imports to avoid initialization errors
_services_loaded = False
_verify_slack_request = None
_is_duplicate_event = None
_generate_event_id = None
_get_message_debounce_buffer = None
_insert_intake_event = None


def _load_services():
    """Lazy load services to avoid import errors."""
    global _services_loaded, _verify_slack_request, _is_duplicate_event
    global _generate_event_id, _get_message_debounce_buffer, _insert_intake_event
    
    if _services_loaded:
        return True
    
    try:
        from src.services.slack_verifier import verify_slack_request
        from src.services.slack_dedup import is_duplicate_event, generate_event_id
        from src.services.debounce_buffer import get_message_debounce_buffer
        from src.services.supabase_client import insert_intake_event
        
        _verify_slack_request = verify_slack_request
        _is_duplicate_event = is_duplicate_event
        _generate_event_id = generate_event_id
        _get_message_debounce_buffer = get_message_debounce_buffer
        _insert_intake_event = insert_intake_event
        _services_loaded = True
        return True
    except Exception as e:
        _logger.error(f"Failed to load services: {e}")
        return False


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


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler for Slack events."""

    def do_POST(self):
        """Handle POST request from Slack."""
        try:
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""
            
            # Parse JSON
            try:
                body = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                body = {}
            
            # Handle URL verification FIRST (before any other processing)
            if body.get("type") == "url_verification":
                challenge = body.get("challenge", "")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({"challenge": challenge})
                self.wfile.write(response.encode('utf-8'))
                _logger.info(f"URL verification successful, challenge: {challenge[:20]}...")
                return
            
            # Load services for event processing
            if not _load_services():
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "service initialization failed"}).encode('utf-8'))
                return
            
            # Get Slack headers (case-insensitive)
            timestamp = self.headers.get("X-Slack-Request-Timestamp") or self.headers.get("x-slack-request-timestamp", "")
            signature = self.headers.get("X-Slack-Signature") or self.headers.get("x-slack-signature", "")
            
            # Debug logging
            _logger.info(f"Slack headers - timestamp: {timestamp[:10] if timestamp else 'MISSING'}..., signature: {signature[:20] if signature else 'MISSING'}...")
            _logger.info(f"Body length: {len(raw_body)}, body preview: {raw_body[:100] if raw_body else 'EMPTY'}...")
            
            # Verify signature
            is_valid = _verify_slack_request(timestamp, signature, raw_body)
            if not is_valid:
                _logger.warning(f"Slack signature verification failed - has_timestamp={bool(timestamp)}, has_signature={bool(signature)}")
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "invalid signature"}).encode('utf-8'))
                return
            
            _logger.info("Slack signature verified")
            
            # Check for duplicates
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            is_dup = loop.run_until_complete(_is_duplicate_event(body, dict(self.headers)))
            if is_dup:
                _logger.info("Duplicate event detected, ignoring")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('X-Slack-Ignored-Retry', 'true')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode('utf-8'))
                return
            
            # Normalize event
            normalized = normalize_event(body)
            if normalized:
                _logger.info(f"Event normalized: type={normalized.get('type')}, channel={normalized.get('channel')}")
                
                # Persist minimal state
                try:
                    event_id = _generate_event_id(body, {})
                    loop.run_until_complete(_insert_intake_event(event_id))
                    _logger.info(f"Ingested event: {event_id}")
                except Exception as e:
                    _logger.error(f"Pre-ACK ingest error: {e}")
                
                # Enqueue to debounce buffer
                try:
                    debounce_buffer = _get_message_debounce_buffer()
                    loop.run_until_complete(debounce_buffer.enqueue(body))
                    _logger.info("Message enqueued to debounce buffer")
                except Exception as e:
                    _logger.error(f"Debounce buffer enqueue error: {e}")
            
            # ACK immediately (200 OK)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode('utf-8'))
            _logger.info("Slack event processed successfully")
            
        except Exception as e:
            _logger.error(f"Error processing Slack event: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "internal server error"}).encode('utf-8'))

    def do_GET(self):
        """Handle GET request (health check)."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "endpoint": "slack/events"}).encode('utf-8'))
