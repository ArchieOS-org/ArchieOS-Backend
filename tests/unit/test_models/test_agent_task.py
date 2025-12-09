"""Tests for AgentTask model."""

import pytest
from datetime import date
from pydantic import ValidationError
from src.models.agent_task import AgentTask


@pytest.mark.unit
def test_agent_task_valid():
    """Test valid agent task creation."""
    task = AgentTask(
        task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
        name="Follow up with client"
    )
    
    assert task.task_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert task.realtor_id == "01ARZ3NDEKTSV4RRFFQ69G5FAX"
    assert task.name == "Follow up with client"
    assert task.status == "OPEN"  # Default
    assert task.priority == 0  # Default
    assert task.task_category == "OTHER"  # Default


@pytest.mark.unit
def test_agent_task_with_all_fields():
    """Test agent task with all fields."""
    due_date = date(2024, 12, 15)
    task = AgentTask(
        task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
        name="Follow up with client",
        description="Call about viewing",
        status="IN_PROGRESS",
        priority=7,
        assigned_staff_id="01ARZ3NDEKTSV4RRFFQ69G5FAY",
        due_date=due_date,
        notes="Client prefers morning calls",
        task_category="ADMIN"
    )
    
    assert task.description == "Call about viewing"
    assert task.status == "IN_PROGRESS"
    assert task.priority == 7
    assert task.due_date == due_date
    assert task.notes == "Client prefers morning calls"
    assert task.task_category == "ADMIN"


@pytest.mark.unit
def test_agent_task_realtor_id_required():
    """Test that realtor_id is required."""
    with pytest.raises(ValidationError):
        AgentTask(
            task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            name="Test"
            # Missing realtor_id
        )


@pytest.mark.unit
def test_agent_task_priority_bounds():
    """Test priority field bounds validation."""
    # Valid priorities
    for priority in [0, 5, 10]:
        task = AgentTask(
            task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
            name="Test",
            priority=priority
        )
        assert task.priority == priority
    
    # Invalid priorities
    with pytest.raises(ValidationError):
        AgentTask(
            task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
            name="Test",
            priority=11  # Too high
        )


@pytest.mark.unit
def test_agent_task_inputs_outputs_default():
    """Test that inputs and outputs default to empty dict."""
    task = AgentTask(
        task_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        realtor_id="01ARZ3NDEKTSV4RRFFQ69G5FAX",
        name="Test"
    )
    
    assert task.inputs == {}
    assert task.outputs == {}

