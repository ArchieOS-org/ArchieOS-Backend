"""Test data factories using Faker."""

from faker import Faker
from typing import Optional
from datetime import date, timedelta

fake = Faker()


def create_realtor_data(slack_user_id: Optional[str] = None) -> dict:
    """Create test realtor data."""
    return {
        "realtor_id": fake.uuid4().replace('-', '')[:26],  # ULID-like format
        "slack_user_id": slack_user_id or f"U{fake.random_int(min=100000, max=999999)}",
        "name": fake.name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
    }


def create_listing_data(realtor_id: Optional[str] = None, listing_type: str = "SALE") -> dict:
    """Create test listing data."""
    return {
        "listing_id": fake.uuid4().replace('-', '')[:26],
        "realtor_id": realtor_id or fake.uuid4().replace('-', '')[:26],
        "type": listing_type,
        "address": fake.address(),
        "price": fake.random_int(min=100000, max=2000000),
        "status": "ACTIVE",
    }


def create_activity_data(listing_id: str, task_category: str = "MARKETING") -> dict:
    """Create test activity data."""
    return {
        "activity_id": fake.uuid4().replace('-', '')[:26],
        "listing_id": listing_id,
        "task_category": task_category,
        "title": fake.sentence(nb_words=4),
        "description": fake.text(),
        "due_date": (date.today() + timedelta(days=fake.random_int(min=1, max=30))).isoformat(),
        "status": "PENDING",
    }


def create_agent_task_data(realtor_id: Optional[str] = None) -> dict:
    """Create test agent task data."""
    return {
        "agent_task_id": fake.uuid4().replace('-', '')[:26],
        "realtor_id": realtor_id or fake.uuid4().replace('-', '')[:26],
        "title": fake.sentence(nb_words=4),
        "description": fake.text(),
        "due_date": (date.today() + timedelta(days=fake.random_int(min=1, max=30))).isoformat(),
        "status": "PENDING",
    }

