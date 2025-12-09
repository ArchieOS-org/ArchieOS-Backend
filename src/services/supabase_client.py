"""Supabase client wrapper with async context manager support."""

import os
from typing import Optional
from supabase import create_client, Client
from supabase.client import ClientOptions
from src.utils.errors import SupabaseError
import logging

logger = logging.getLogger(__name__)

# Global client instance (singleton pattern)
_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton."""
    global _client
    
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise SupabaseError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        # Use transaction mode for serverless (port 6543)
        # Note: Supabase-py doesn't directly support port override, but connection pooling
        # is handled by Supabase's connection pooler
        options = ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        )
        
        _client = create_client(url, key, options)
        logger.info("Supabase client initialized", extra={"url": url})
    
    return _client


async def close_supabase_client() -> None:
    """Close Supabase client connections."""
    global _client
    if _client:
        # Supabase-py doesn't have explicit close, but we can clear the reference
        _client = None
        logger.info("Supabase client closed")


class SupabaseClient:
    """Async context manager for Supabase client."""
    
    def __init__(self):
        self.client: Optional[Client] = None
    
    async def __aenter__(self) -> Client:
        """Enter async context."""
        self.client = get_supabase_client()
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        # Supabase-py client doesn't need explicit cleanup
        # but we can log if needed
        if exc_type:
            logger.error(
                "Supabase operation error",
                extra={"error": str(exc_val), "type": exc_type.__name__}
            )
        return False


# Helper functions for common operations
async def insert_intake_event(event_id: str) -> None:
    """Insert an intake event for idempotency tracking."""
    async with SupabaseClient() as client:
        try:
            client.table("intake_events").insert({
                "event_id": event_id
            }).execute()
        except Exception as e:
            # Ignore duplicate key errors (idempotency)
            if "duplicate key" not in str(e).lower():
                raise SupabaseError(f"Failed to insert intake event: {e}")


async def check_intake_event_exists(event_id: str) -> bool:
    """Check if an intake event already exists."""
    async with SupabaseClient() as client:
        try:
            result = client.table("intake_events").select("event_id").eq("event_id", event_id).execute()
            return len(result.data) > 0
        except Exception as e:
            raise SupabaseError(f"Failed to check intake event: {e}")


async def enqueue_intake_message(envelope: dict, message_type: Optional[str] = None) -> str:
    """Enqueue a message to the intake queue."""
    async with SupabaseClient() as client:
        try:
            result = client.table("intake_queue").insert({
                "envelope": envelope,
                "message_type": message_type
            }).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]["id"]
            raise SupabaseError("Failed to enqueue message: no ID returned")
        except Exception as e:
            raise SupabaseError(f"Failed to enqueue intake message: {e}")


async def get_intake_queue_batch(batch_size: int = 5) -> list[dict]:
    """Get next batch of unprocessed queue items."""
    async with SupabaseClient() as client:
        try:
            # Use the database function for atomic batch retrieval
            result = client.rpc("get_intake_queue_batch", {"batch_size": batch_size}).execute()
            return result.data if result.data else []
        except Exception as e:
            # Fallback to direct query if function doesn't exist
            try:
                result = client.table("intake_queue").select("*").is_("processed_at", "null").order("created_at").limit(batch_size).execute()
                return result.data if result.data else []
            except Exception as fallback_error:
                raise SupabaseError(f"Failed to get intake queue batch: {e}, fallback: {fallback_error}")


async def mark_queue_item_processed(queue_id: str, error_message: Optional[str] = None) -> None:
    """Mark a queue item as processed."""
    async with SupabaseClient() as client:
        try:
            # Use the database function if available
            try:
                client.rpc("mark_intake_queue_processed", {
                    "queue_id": queue_id,
                    "error_msg": error_message
                }).execute()
            except Exception:
                # Fallback to direct update
                client.table("intake_queue").update({
                    "processed_at": "now()",
                    "error_message": error_message
                }).eq("id", queue_id).execute()
        except Exception as e:
            raise SupabaseError(f"Failed to mark queue item processed: {e}")


# Realtors table operations (primary people table)
async def get_realtor_by_slack_id(slack_user_id: str) -> Optional[dict]:
    """Get realtor by Slack user ID."""
    async with SupabaseClient() as client:
        try:
            result = client.table("realtors").select("*").eq("slack_user_id", slack_user_id).execute()
            return result.data[0] if result.data and len(result.data) > 0 else None
        except Exception as e:
            raise SupabaseError(f"Failed to get realtor by slack_id: {e}")


async def create_realtor(realtor_data: dict) -> dict:
    """Create a new realtor record."""
    async with SupabaseClient() as client:
        try:
            result = client.table("realtors").insert(realtor_data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError("Failed to create realtor: no data returned")
        except Exception as e:
            raise SupabaseError(f"Failed to create realtor: {e}")


async def update_realtor(realtor_id: str, updates: dict) -> dict:
    """Update a realtor record."""
    async with SupabaseClient() as client:
        try:
            result = client.table("realtors").update(updates).eq("realtor_id", realtor_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError(f"Failed to update realtor: {realtor_id}")
        except Exception as e:
            raise SupabaseError(f"Failed to update realtor: {e}")


# Activities table operations (listing tasks)
async def create_activity(activity_data: dict) -> dict:
    """Create a new activity (listing task)."""
    async with SupabaseClient() as client:
        try:
            result = client.table("activities").insert(activity_data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError("Failed to create activity: no data returned")
        except Exception as e:
            raise SupabaseError(f"Failed to create activity: {e}")


async def get_activities_by_listing(listing_id: str) -> list[dict]:
    """Get all activities for a listing."""
    async with SupabaseClient() as client:
        try:
            result = client.table("activities").select("*").eq("listing_id", listing_id).is_("deleted_at", "null").execute()
            return result.data if result.data else []
        except Exception as e:
            raise SupabaseError(f"Failed to get activities: {e}")


async def update_activity(task_id: str, updates: dict) -> dict:
    """Update an activity."""
    async with SupabaseClient() as client:
        try:
            result = client.table("activities").update(updates).eq("task_id", task_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError(f"Failed to update activity: {task_id}")
        except Exception as e:
            raise SupabaseError(f"Failed to update activity: {e}")


# AgentTasks table operations (tasks)
async def create_agent_task(task_data: dict) -> dict:
    """Create a new agent task."""
    async with SupabaseClient() as client:
        try:
            result = client.table("agent_tasks").insert(task_data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError("Failed to create agent task: no data returned")
        except Exception as e:
            raise SupabaseError(f"Failed to create agent task: {e}")


async def get_agent_tasks_by_realtor(realtor_id: str) -> list[dict]:
    """Get all agent tasks for a realtor."""
    async with SupabaseClient() as client:
        try:
            result = client.table("agent_tasks").select("*").eq("realtor_id", realtor_id).is_("deleted_at", "null").execute()
            return result.data if result.data else []
        except Exception as e:
            raise SupabaseError(f"Failed to get agent tasks: {e}")


async def update_agent_task(task_id: str, updates: dict) -> dict:
    """Update an agent task."""
    async with SupabaseClient() as client:
        try:
            result = client.table("agent_tasks").update(updates).eq("task_id", task_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError(f"Failed to update agent task: {task_id}")
        except Exception as e:
            raise SupabaseError(f"Failed to update agent task: {e}")


# Listings table operations
async def create_listing(listing_data: dict) -> dict:
    """Create a new listing."""
    async with SupabaseClient() as client:
        try:
            result = client.table("listings").insert(listing_data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError("Failed to create listing: no data returned")
        except Exception as e:
            raise SupabaseError(f"Failed to create listing: {e}")


async def get_listing_by_id(listing_id: str) -> Optional[dict]:
    """Get listing by ID."""
    async with SupabaseClient() as client:
        try:
            result = client.table("listings").select("*").eq("listing_id", listing_id).is_("deleted_at", "null").execute()
            return result.data[0] if result.data and len(result.data) > 0 else None
        except Exception as e:
            raise SupabaseError(f"Failed to get listing: {e}")


async def update_listing(listing_id: str, updates: dict) -> dict:
    """Update a listing."""
    async with SupabaseClient() as client:
        try:
            result = client.table("listings").update(updates).eq("listing_id", listing_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            raise SupabaseError(f"Failed to update listing: {listing_id}")
        except Exception as e:
            raise SupabaseError(f"Failed to update listing: {e}")

