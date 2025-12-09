"""Test helper functions."""

import json
import hmac
import hashlib
import time
from typing import Dict, Any


def generate_slack_signature(secret: str, timestamp: str, body: str) -> str:
    """Generate a valid Slack signature for testing."""
    sig_basestring = f"v0:{timestamp}:{body}"
    signature = hmac.new(
        secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"v0={signature}"


def create_slack_event(
    event_type: str = "message",
    text: str = "Test message",
    channel: str = "C123456",
    user: str = "U123456",
    event_id: str = None
) -> Dict[str, Any]:
    """Create a Slack event payload for testing."""
    if event_id is None:
        event_id = f"Ev{int(time.time())}"
    
    return {
        "type": "event_callback",
        "event_id": event_id,
        "event": {
            "type": event_type,
            "channel": channel,
            "user": user,
            "text": text,
            "ts": f"{int(time.time())}.123456"
        },
        "team_id": "T123456"
    }


def create_vercel_request(
    method: str = "POST",
    path: str = "/api/slack/events",
    body: Dict[str, Any] = None,
    headers: Dict[str, str] = None
) -> Dict[str, Any]:
    """Create a Vercel request object for testing."""
    if body is None:
        body = {"type": "event_callback"}
    
    if headers is None:
        headers = {
            "content-type": "application/json"
        }
    
    return {
        "method": method,
        "path": path,
        "headers": headers,
        "body": json.dumps(body) if isinstance(body, dict) else body,
        "query": {}
    }


