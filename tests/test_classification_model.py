"""Tests for ClassificationV1 Pydantic model."""

import pytest
from src.models.classification import (
    ClassificationV1,
    MessageType,
    TaskKey,
    GroupKey
)


def test_classification_group_valid():
    """Test valid GROUP classification."""
    classification = ClassificationV1(
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
    
    assert classification.message_type == MessageType.GROUP
    assert classification.group_key == GroupKey.SALE_LISTING
    assert classification.task_key is None


def test_classification_stray_valid():
    """Test valid STRAY classification."""
    classification = ClassificationV1(
        schema_version=1,
        message_type=MessageType.STRAY,
        task_key=TaskKey.OPS_MISC_TASK,
        group_key=None,
        listing={"type": None, "address": None},
        assignee_hint=None,
        due_date=None,
        task_title="Update brochure copy",
        confidence=0.8,
        explanations=None
    )
    
    assert classification.message_type == MessageType.STRAY
    assert classification.task_key == TaskKey.OPS_MISC_TASK
    assert classification.group_key is None


def test_classification_info_request_valid():
    """Test valid INFO_REQUEST classification."""
    classification = ClassificationV1(
        schema_version=1,
        message_type=MessageType.INFO_REQUEST,
        task_key=None,
        group_key=None,
        listing={"type": None, "address": None},
        assignee_hint=None,
        due_date=None,
        task_title=None,
        confidence=0.7,
        explanations=["Missing listing type", "Missing address"]
    )
    
    assert classification.message_type == MessageType.INFO_REQUEST
    assert classification.task_key is None
    assert classification.group_key is None


def test_classification_invalid_both_keys():
    """Test that both keys cannot be set."""
    with pytest.raises(ValueError, match="Exactly one of group_key or task_key"):
        ClassificationV1(
            schema_version=1,
            message_type=MessageType.GROUP,
            task_key=TaskKey.OPS_MISC_TASK,  # Should be None for GROUP
            group_key=GroupKey.SALE_LISTING,
            listing={"type": "SALE", "address": "123 Main St"},
            assignee_hint=None,
            due_date=None,
            task_title=None,
            confidence=0.9,
            explanations=None
        )


def test_classification_invalid_info_request_with_keys():
    """Test that INFO_REQUEST cannot have keys."""
    with pytest.raises(ValueError, match="group_key and task_key must both be null"):
        ClassificationV1(
            schema_version=1,
            message_type=MessageType.INFO_REQUEST,
            task_key=TaskKey.OPS_MISC_TASK,  # Should be None
            group_key=None,
            listing={"type": None, "address": None},
            assignee_hint=None,
            due_date=None,
            task_title=None,
            confidence=0.7,
            explanations=None
        )


