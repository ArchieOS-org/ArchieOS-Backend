"""Tests for health check endpoint."""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from http.server import BaseHTTPRequestHandler
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api.health import handler


@pytest.mark.unit
def test_health_handler_class():
    """Test that handler is a BaseHTTPRequestHandler subclass."""
    assert issubclass(handler, BaseHTTPRequestHandler)


@pytest.mark.unit
def test_health_get_request():
    """Test GET request to health endpoint."""
    from io import BytesIO
    
    # Create minimal mock socket
    class MockSocket:
        def makefile(self, *args, **kwargs):
            return BytesIO(b"GET /api/health HTTP/1.1\r\n\r\n")
        def sendall(self, data):
            pass
        def close(self):
            pass
    
    # Create handler instance
    h = handler(MockSocket(), ("127.0.0.1", 8000), None)
    
    # Mock wfile
    h.wfile = BytesIO()
    
    # Mock send_response and send_header
    h.send_response = Mock()
    h.send_header = Mock()
    h.end_headers = Mock()
    
    # Call do_GET
    h.do_GET()
    
    # Verify response
    assert h.send_response.called
    assert h.send_response.call_args[0][0] == 200
    assert h.send_header.called
    
    # Get written data
    h.wfile.seek(0)
    response_json = h.wfile.read().decode('utf-8')
    response_data = json.loads(response_json)
    
    assert response_data["status"] == "ok"
    assert response_data["service"] == "archieos-backend"


@pytest.mark.unit
def test_health_post_request():
    """Test POST request to health endpoint."""
    from io import BytesIO
    
    class MockSocket:
        def makefile(self, *args, **kwargs):
            return BytesIO(b"POST /api/health HTTP/1.1\r\n\r\n")
        def sendall(self, data):
            pass
        def close(self):
            pass
    
    h = handler(MockSocket(), ("127.0.0.1", 8000), None)
    h.wfile = BytesIO()
    h.send_response = Mock()
    h.send_header = Mock()
    h.end_headers = Mock()
    
    h.do_POST()
    
    assert h.send_response.called
    h.wfile.seek(0)
    response_json = h.wfile.read().decode('utf-8')
    response_data = json.loads(response_json)
    
    assert response_data["status"] == "ok"

