"""Slack signature verification matching mogadishu-v1 logic."""

import os
import hmac
import hashlib
import time
import logging
from typing import Optional
from src.utils.errors import SlackVerificationError

logger = logging.getLogger(__name__)


def should_bypass_verification() -> bool:
    """Check if signature verification should be bypassed (dev mode)."""
    env = os.environ.get("NODE_ENV", "").lower()
    if env in ("development", "local"):
        return True
    
    bypass_flag = os.environ.get("SLACK_BYPASS_VERIFY", "").lower()
    return bypass_flag == "true"


def get_signing_secret() -> str:
    """Get Slack signing secret from environment."""
    # In test mode, use test secret if provided
    if os.environ.get("NODE_ENV", "").lower() == "test":
        test_secret = os.environ.get("SLACK_SIGNING_SECRET_TEST")
        if test_secret:
            return test_secret
    
    # Otherwise use production secret (strip to remove any trailing newlines from env var)
    secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
    if not secret:
        raise SlackVerificationError("SLACK_SIGNING_SECRET not set")
    return secret


def verify_slack_signature(
    secret: str,
    timestamp: str,
    body: str,
    signature: str
) -> bool:
    """
    Verify Slack request signature using HMAC-SHA256.
    
    Matches mogadishu-v1 slackVerify.ts logic.
    """
    if not secret or not timestamp or not signature:
        return False
    
    # Check timestamp to prevent replay attacks (5 minute window)
    try:
        ts = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - ts) > 300:  # 5 minutes
            logger.warning("Slack request timestamp too old or too far in future")
            return False
    except ValueError:
        return False
    
    # Create signature base string
    sig_basestring = f"v0:{timestamp}:{body}"
    
    # Compute expected signature
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures using constant-time comparison
    expected_signature = f"v0={expected_sig}"
    
    return hmac.compare_digest(expected_signature, signature)


def verify_slack_request(
    timestamp: str,
    signature: str,
    raw_body: str
) -> bool:
    """
    Verify a Slack request.
    
    Returns True if verification passes or is bypassed, False otherwise.
    """
    if should_bypass_verification():
        logger.debug("Slack signature verification bypassed (dev mode)")
        return True
    
    try:
        secret = get_signing_secret()
        logger.info(f"Verifying signature - secret_length={len(secret)}, timestamp={timestamp}, signature_preview={signature[:30] if signature else 'NONE'}...")
        result = verify_slack_signature(secret, timestamp, raw_body, signature)
        if not result:
            logger.warning(f"Signature mismatch - timestamp_valid={bool(timestamp)}, body_length={len(raw_body)}")
        return result
    except Exception as e:
        logger.error(f"Slack verification error: {e}")
        return False

