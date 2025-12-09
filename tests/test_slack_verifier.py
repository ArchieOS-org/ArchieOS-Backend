"""Tests for Slack signature verification."""

import os
import time
import hmac
import hashlib
import pytest
from src.services.slack_verifier import (
    verify_slack_signature,
    verify_slack_request,
    should_bypass_verification
)


def test_verify_slack_signature_valid():
    """Test valid signature verification."""
    secret = "test_secret"
    timestamp = str(int(time.time()))
    body = '{"type":"event_callback","event":{"type":"message"}}'
    
    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    signature = f"v0={expected_sig}"
    
    assert verify_slack_signature(secret, timestamp, body, signature) is True


def test_verify_slack_signature_invalid():
    """Test invalid signature verification."""
    secret = "test_secret"
    timestamp = str(int(time.time()))
    body = '{"type":"event_callback"}'
    signature = "v0=invalid_signature"
    
    assert verify_slack_signature(secret, timestamp, body, signature) is False


def test_verify_slack_signature_old_timestamp():
    """Test that old timestamps are rejected."""
    secret = "test_secret"
    timestamp = str(int(time.time()) - 400)  # 400 seconds ago (more than 5 min)
    body = '{"type":"event_callback"}'
    
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    signature = f"v0={expected_sig}"
    
    assert verify_slack_signature(secret, timestamp, body, signature) is False


def test_should_bypass_verification_dev():
    """Test bypass in development mode."""
    original_env = os.environ.get("NODE_ENV")
    try:
        os.environ["NODE_ENV"] = "development"
        assert should_bypass_verification() is True
    finally:
        if original_env:
            os.environ["NODE_ENV"] = original_env
        else:
            os.environ.pop("NODE_ENV", None)


def test_verify_slack_request_with_bypass():
    """Test request verification with bypass enabled."""
    original_env = os.environ.get("NODE_ENV")
    try:
        os.environ["NODE_ENV"] = "development"
        assert verify_slack_request("123", "invalid", "body") is True
    finally:
        if original_env:
            os.environ["NODE_ENV"] = original_env
        else:
            os.environ.pop("NODE_ENV", None)


