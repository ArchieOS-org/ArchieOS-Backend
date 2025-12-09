"""Shared pytest fixtures and configuration."""

import os
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Generator, AsyncGenerator
from datetime import datetime, timedelta
from freezegun import freeze_time

# Set test environment variables
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-secret")
os.environ.setdefault("LLM_PROVIDER", "anthropic")
os.environ.setdefault("LLM_MODEL", "claude-sonnet-4-20250514")
os.environ.setdefault("USE_LLM_CLASSIFIER", "true")
os.environ.setdefault("DEBOUNCE_WINDOW_SECONDS", "300")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = Mock()
    client.table = Mock(return_value=Mock())
    return client


@pytest.fixture
def mock_langchain_agent():
    """Mock LangChain agent for testing."""
    agent = AsyncMock()
    agent.invoke = AsyncMock()
    return agent


@pytest.fixture
def sample_slack_event():
    """Sample Slack event payload."""
    return {
        "type": "event_callback",
        "event_id": "Ev123456",
        "event": {
            "type": "message",
            "channel": "C123456",
            "user": "U123456",
            "text": "New listing at 123 Main St",
            "ts": "1234567890.123456"
        },
        "team_id": "T123456"
    }


@pytest.fixture
def sample_slack_event_group():
    """Sample Slack event for GROUP message."""
    return {
        "type": "event_callback",
        "event_id": "Ev789012",
        "event": {
            "type": "message",
            "channel": "C123456",
            "user": "U123456",
            "text": "New sale listing: 456 Oak Ave, asking $500k",
            "ts": "1234567890.123457"
        },
        "team_id": "T123456"
    }


@pytest.fixture
def sample_slack_event_stray():
    """Sample Slack event for STRAY message."""
    return {
        "type": "event_callback",
        "event_id": "Ev345678",
        "event": {
            "type": "message",
            "channel": "C123456",
            "user": "U123456",
            "text": "Follow up with client about viewing",
            "ts": "1234567890.123458"
        },
        "team_id": "T123456"
    }


@pytest.fixture
def sample_classification_group():
    """Sample GROUP classification."""
    from src.models.classification import ClassificationV1, MessageType, GroupKey
    
    return ClassificationV1(
        schema_version=1,
        message_type=MessageType.GROUP,
        task_key=None,
        group_key=GroupKey.SALE_LISTING,
        listing={"type": "SALE", "address": "123 Main St"},
        assignee_hint=None,
        due_date=None,
        task_title=None,
        confidence=0.9,
        explanations=None
    )


@pytest.fixture
def sample_classification_stray():
    """Sample STRAY classification."""
    from src.models.classification import ClassificationV1, MessageType, TaskKey
    
    return ClassificationV1(
        schema_version=1,
        message_type=MessageType.STRAY,
        task_key=TaskKey.GENERAL_FOLLOW_UP,
        group_key=None,
        listing=None,
        assignee_hint="U123456",
        due_date="2024-12-15",
        task_title="Follow up with client",
        confidence=0.85,
        explanations=None
    )


@pytest.fixture
def freeze_time_fixture():
    """Fixture for freezing time in tests."""
    with freeze_time("2024-12-09 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture
def mock_vercel_request():
    """Mock Vercel serverless function request."""
    return {
        "method": "POST",
        "path": "/api/slack/events",
        "headers": {
            "x-slack-signature": "v0=test-signature",
            "x-slack-request-timestamp": "1234567890",
            "content-type": "application/json"
        },
        "body": '{"type":"event_callback","event":{"type":"message"}}',
        "query": {}
    }


@pytest.fixture(scope="function")
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)

