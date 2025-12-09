"""Slack event fixtures."""

import time
from typing import Dict, Any


def slack_url_verification_challenge() -> Dict[str, Any]:
    """Slack URL verification challenge payload."""
    return {
        "type": "url_verification",
        "challenge": "test-challenge-token",
        "token": "test-token"
    }


def slack_app_mention_event(text: str = "Test mention") -> Dict[str, Any]:
    """Slack app_mention event."""
    return {
        "type": "event_callback",
        "event_id": f"Ev{int(time.time())}",
        "event": {
            "type": "app_mention",
            "channel": "C123456",
            "user": "U123456",
            "text": text,
            "ts": f"{int(time.time())}.123456"
        },
        "team_id": "T123456"
    }


def slack_message_event(text: str = "Test message", channel_type: str = "channel") -> Dict[str, Any]:
    """Slack message event."""
    return {
        "type": "event_callback",
        "event_id": f"Ev{int(time.time())}",
        "event": {
            "type": "message",
            "channel": "C123456",
            "channel_type": channel_type,
            "user": "U123456",
            "text": text,
            "ts": f"{int(time.time())}.123456"
        },
        "team_id": "T123456"
    }


