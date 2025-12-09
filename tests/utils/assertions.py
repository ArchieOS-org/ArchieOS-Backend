"""Custom assertion helpers."""

from typing import Any, Dict
import json


def assert_valid_classification(classification: Any) -> None:
    """Assert that a classification object is valid."""
    assert classification is not None
    assert hasattr(classification, 'message_type')
    assert hasattr(classification, 'confidence')
    assert 0.0 <= classification.confidence <= 1.0


def assert_valid_realtor(realtor: Dict[str, Any]) -> None:
    """Assert that a realtor dict is valid."""
    assert 'realtor_id' in realtor
    assert 'slack_user_id' in realtor
    assert isinstance(realtor['realtor_id'], str)
    assert len(realtor['realtor_id']) > 0


def assert_valid_listing(listing: Dict[str, Any]) -> None:
    """Assert that a listing dict is valid."""
    assert 'listing_id' in listing
    assert 'type' in listing
    assert listing['type'] in ['SALE', 'LEASE']
    assert 'address' in listing


def assert_valid_response(response: Dict[str, Any], expected_status: int = 200) -> None:
    """Assert that a Vercel function response is valid."""
    assert 'statusCode' in response
    assert response['statusCode'] == expected_status
    assert 'headers' in response
    assert 'body' in response
    
    # Try to parse body as JSON if content-type is JSON
    if 'application/json' in response.get('headers', {}).get('Content-Type', ''):
        try:
            json.loads(response['body'])
        except json.JSONDecodeError:
            assert False, "Response body is not valid JSON"

