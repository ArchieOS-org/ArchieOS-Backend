"""Health check endpoint."""

from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    """Health check handler for Vercel serverless function."""

    def do_GET(self):
        """Handle GET request."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = json.dumps({"status": "ok", "service": "archieos-backend"})
        self.wfile.write(response.encode('utf-8'))

    def do_POST(self):
        """Handle POST request (same as GET for health check)."""
        self.do_GET()
