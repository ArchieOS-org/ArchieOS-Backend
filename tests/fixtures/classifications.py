"""Classification fixtures."""

from src.models.classification import ClassificationV1, MessageType, TaskKey, GroupKey


def classification_group_sale() -> ClassificationV1:
    """GROUP classification for sale listing."""
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


def classification_stray_followup() -> ClassificationV1:
    """STRAY classification for follow-up task."""
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


def classification_info_request() -> ClassificationV1:
    """INFO_REQUEST classification."""
    return ClassificationV1(
        schema_version=1,
        message_type=MessageType.INFO_REQUEST,
        task_key=None,
        group_key=None,
        listing=None,
        assignee_hint=None,
        due_date=None,
        task_title=None,
        confidence=0.7,
        explanations=None
    )


def classification_ignore() -> ClassificationV1:
    """IGNORE classification."""
    return ClassificationV1(
        schema_version=1,
        message_type=MessageType.IGNORE,
        task_key=None,
        group_key=None,
        listing=None,
        assignee_hint=None,
        due_date=None,
        task_title=None,
        confidence=0.95,
        explanations=None
    )


