"""Slack user resolution service - map Slack user ID to realtors table (primary people table)."""

import logging
import os
from typing import Optional
try:
    from ulid import ULID
except ImportError:
    # Fallback: use uuid4 and convert to string if ulid not available
    import uuid
    class ULID:
        def __str__(self):
            return str(uuid.uuid4()).replace('-', '')[:26]
from src.services.supabase_client import SupabaseClient
from src.utils.errors import SupabaseError

logger = logging.getLogger(__name__)


def generate_realtor_id() -> str:
    """Generate a text-based realtor ID (ULID format)."""
    try:
        return str(ULID())
    except:
        # Fallback to UUID-based string if ULID fails
        import uuid
        return str(uuid.uuid4()).replace('-', '')


async def resolve_slack_user(slack_user_id: str) -> Optional[dict]:
    """
    Resolve Slack user ID to Realtor record (primary people table).
    
    Auto-creates Realtor record if it doesn't exist.
    Returns realtor record dict or None on error.
    """
    if not slack_user_id:
        return None
    
    async with SupabaseClient() as client:
        try:
            # Try to find existing realtor by slack_user_id
            result = client.table("realtors").select("*").eq("slack_user_id", slack_user_id).execute()
            
            if result.data and len(result.data) > 0:
                realtor = result.data[0]
                logger.info(
                    "Resolved Slack user to existing realtor",
                    extra={
                        "slack_user_id": slack_user_id,
                        "realtor_id": realtor.get("realtor_id"),
                        "name": realtor.get("name")
                    }
                )
                return realtor
            
            # Create new realtor record
            # Generate text-based ID (ULID format)
            realtor_id = generate_realtor_id()
            
            # Create fallback name from Slack user ID
            fallback_name = f"User_{slack_user_id[-8:]}"
            
            # Get email from Slack if available (via env or API)
            # For now, use a placeholder email format
            email = f"{slack_user_id}@slack.local"
            
            new_realtor = {
                "realtor_id": realtor_id,
                "slack_user_id": slack_user_id,
                "name": fallback_name,
                "email": email,
                "status": "active"
            }
            
            result = client.table("realtors").insert(new_realtor).execute()
            
            if result.data and len(result.data) > 0:
                realtor = result.data[0]
                logger.info(
                    "Created new realtor from Slack user",
                    extra={
                        "slack_user_id": slack_user_id,
                        "realtor_id": realtor.get("realtor_id"),
                        "name": realtor.get("name")
                    }
                )
                return realtor
            
            logger.warning(f"Failed to create realtor for Slack user: {slack_user_id}")
            return None
            
        except Exception as e:
            logger.error(
                f"Error resolving Slack user: {e}",
                extra={"slack_user_id": slack_user_id, "error": str(e)}
            )
            raise SupabaseError(f"Failed to resolve Slack user: {e}")


async def update_realtor_from_slack(
    realtor_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> dict:
    """Update realtor record with Slack information."""
    async with SupabaseClient() as client:
        try:
            updates = {}
            if name:
                updates["name"] = name
            if email:
                updates["email"] = email
            if phone:
                updates["phone"] = phone
            
            if not updates:
                # Return existing record
                result = client.table("realtors").select("*").eq("realtor_id", realtor_id).execute()
                if result.data and len(result.data) > 0:
                    return result.data[0]
                raise SupabaseError(f"Realtor not found: {realtor_id}")
            
            updates["updated_at"] = "now()"
            result = client.table("realtors").update(updates).eq("realtor_id", realtor_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            raise SupabaseError(f"Failed to update realtor: {realtor_id}")
            
        except Exception as e:
            logger.error(f"Error updating realtor: {e}")
            raise SupabaseError(f"Failed to update realtor: {e}")

