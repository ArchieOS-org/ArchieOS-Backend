"""Intake queue processor endpoint (can be called via Vercel cron)."""

import json
import asyncio
import logging
from src.services.intake_ingestor import poll_and_ingest_once

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def handler(request):
    """
    Process intake queue.
    
    Can be called manually or via Vercel cron job.
    """
    try:
        # Get batch size from query params or default
        query_params = request.get("query", {}) or {}
        max_messages = int(query_params.get("max_messages", "5"))
        
        # Run async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        processed = loop.run_until_complete(poll_and_ingest_once(max_messages))
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "ok": True,
                "processed": processed,
                "max_messages": max_messages
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing intake queue: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }


