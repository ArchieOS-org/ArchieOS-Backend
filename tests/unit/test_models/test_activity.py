"""Tests for Activity model."""

import pytest
from datetime import date
from pydantic import ValidationError
from src.models.activity import Activity


@pytest.mark.unit
def test_activity_valid():
    """Test valid activity creation."""
    activity = Activity(
        task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        listing_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
        name="Create listing photos",
        task_category="PHOTO"
    )
    
    assert activity.task_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert activity.listing_id == "01ARZ3NDEKTSV4RRFFQ69G5FAW"
    assert activity.name == "Create listing photos"
    assert activity.task_category == "PHOTO"
    assert activity.status == "OPEN"  # Default
    assert activity.priority == 0  # Default
    assert activity.visibility_group == "BOTH"  # Default


@pytest.mark.unit
def test_activity_with_all_fields():
    """Test activity with all fields."""
    due_date = date(2024, 12, 15)
    activity = Activity(
        task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        listing_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
        name="Create listing photos",
        description="Professional photos needed",
        task_category="PHOTO",
        status="IN_PROGRESS",
        priority=5,
        visibility_group="AGENT",
        assigned_staff_id="01ARZ3NDEKTSV4RRFFQ69G5FAY",
        due_date=due_date
    )
    
    assert activity.realtor_id == "01ARZ3NDEKTSV4RRFFQ69G5FAX"
    assert activity.description == "Professional photos needed"
    assert activity.status == "IN_PROGRESS"
    assert activity.priority == 5
    assert activity.due_date == due_date


@pytest.mark.unit
def test_activity_priority_bounds():
    """Test priority field bounds validation."""
    # Valid priorities
    for priority in [0, 5, 10]:
        activity = Activity(
            task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            listing_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            name="Test",
            task_category="OTHER",
            priority=priority
        )
        assert activity.priority == priority
    
    # Invalid priorities
    with pytest.raises(ValidationError):
        Activity(
            task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            listing_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            name="Test",
            task_category="OTHER",
            priority=11  # Too high
        )
    
    with pytest.raises(ValidationError):
        Activity(
            task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            listing_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            name="Test",
            task_category="OTHER",
            priority=-1  # Too low
        )


@pytest.mark.unit
def test_activity_inputs_outputs_default():
    """Test that inputs and outputs default to empty dict."""
    activity = Activity(
        task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        listing_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
        name="Test",
        task_category="OTHER"
    )
    
    assert activity.inputs == {}
    assert activity.outputs == {}


@pytest.mark.unit
@pytest.mark.parametrize("category", [
    "ADMIN", "MARKETING", "PHOTO", "STAGING", "INSPECTION", "OTHER"
])
def test_activity_task_categories(category):
    """Test all valid task categories."""
    activity = Activity(
        task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        listing_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
        name="Test",
        task_category=category
    )
    
    assert activity.task_category == category


