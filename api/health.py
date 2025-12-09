"""Health check endpoint."""

import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """Health check handler."""
    
    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = json.dumps({"status": "ok", "service": "archieos-backend"})
        self.wfile.write(response.encode('utf-8'))
        return
    
    def do_POST(self):
        """Handle POST requests."""
        self.do_GET()

