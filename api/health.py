"""Health check endpoint."""

import json


def handler(request):
    """
    Health check handler for Vercel serverless function.
    
    Vercel Python runtime provides request as a dict with:
    - method: HTTP method
    - path: request path
    - headers: dict of headers
    - body: request body (string or bytes)
    """
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "service": "archieos-backend"})
    }

