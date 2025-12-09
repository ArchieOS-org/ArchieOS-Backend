"""Tests for Realtor model."""

import pytest
from pydantic import ValidationError
from src.models.realtor import Realtor


@pytest.mark.unit
def test_realtor_valid():
    """Test valid realtor creation."""
    realtor = Realtor(
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        email="test@example.com",
        name="John Doe"
    )
    
    assert realtor.realtor_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert realtor.email == "test@example.com"
    assert realtor.name == "John Doe"
    assert realtor.status == "active"  # Default value


@pytest.mark.unit
def test_realtor_with_optional_fields():
    """Test realtor with all optional fields."""
    realtor = Realtor(
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        email="test@example.com",
        name="John Doe",
        phone="555-1234",
        license_number="RE12345",
        brokerage="Test Brokerage",
        slack_user_id="U123456",
        territories=["Manhattan", "Brooklyn"],
        status="active"
    )
    
    assert realtor.phone == "555-1234"
    assert realtor.license_number == "RE12345"
    assert realtor.brokerage == "Test Brokerage"
    assert realtor.slack_user_id == "U123456"
    assert len(realtor.territories) == 2


@pytest.mark.unit
def test_realtor_missing_required_fields():
    """Test that required fields are enforced."""
    with pytest.raises(ValidationError):
        Realtor(
            realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAV"
            # Missing email and name
        )


@pytest.mark.unit
def test_realtor_status_validation():
    """Test status field accepts valid values."""
    valid_statuses = ["active", "inactive", "suspended", "pending"]
    
    for status in valid_statuses:
        realtor = Realtor(
            realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
            name="John Doe",
            status=status
        )
        assert realtor.status == status


@pytest.mark.unit
def test_realtor_metadata_default():
    """Test that metadata defaults to empty dict."""
    realtor = Realtor(
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        email="test@example.com",
        name="John Doe"
    )
    
    assert realtor.metadata == {}


@pytest.mark.unit
def test_realtor_metadata_custom():
    """Test custom metadata."""
    realtor = Realtor(
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        email="test@example.com",
        name="John Doe",
        metadata={"custom_field": "value"}
    )
    
    assert realtor.metadata["custom_field"] == "value"

