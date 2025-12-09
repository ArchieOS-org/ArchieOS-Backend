"""Intake ingestor - process classified messages and create listings/tasks."""

import os
import json
import re
from typing import Optional
from datetime import date
from src.services.supabase_client import (
    get_intake_queue_batch,
    mark_queue_item_processed,
    check_intake_event_exists,
    insert_intake_event,
    create_listing,
    create_activity,
    create_agent_task,
    get_realtor_by_slack_id,
    create_realtor
)
from src.services.slack_users import resolve_slack_user, generate_realtor_id
from src.models.classification import ClassificationV1, MessageType, TaskKey
from src.utils.errors import IntakeError
from src.utils.logging import (
    get_structured_logger,
    log_timing,
    sanitize_message_text,
    mask_user_id,
    get_correlation_id,
)

logger = get_structured_logger(__name__)


def generate_listing_id() -> str:
    """Generate a text-based listing ID."""
    try:
        from ulid import ULID
        return str(ULID())
    except:
        import uuid
        return str(uuid.uuid4()).replace('-', '')


def generate_task_id() -> str:
    """Generate a text-based task ID."""
    try:
        from ulid import ULID
        return str(ULID())
    except:
        import uuid
        return str(uuid.uuid4()).replace('-', '')


def map_task_key_to_category(task_key: str) -> str:
    """Map task_key to task_category enum."""
    category_mapping = {
        TaskKey.SALE_ACTIVE_TASKS: "MARKETING",
        TaskKey.SALE_SOLD_TASKS: "MARKETING",
        TaskKey.SALE_CLOSING_TASKS: "ADMIN",
        TaskKey.LEASE_ACTIVE_TASKS: "MARKETING",
        TaskKey.LEASE_LEASED_TASKS: "MARKETING",
        TaskKey.LEASE_CLOSING_TASKS: "ADMIN",
        TaskKey.OPS_MISC_TASK: "OTHER",
    }
    
    try:
        task_key_enum = TaskKey(task_key)
        return category_mapping.get(task_key_enum, "OTHER")
    except ValueError:
        return "OTHER"


async def process_group_message(payload: dict, envelope: dict) -> None:
    """Process a GROUP message - create listing and create activities (listing tasks)."""
    correlation_id = get_correlation_id()
    
    logger.info(
        "Processing GROUP message",
        correlation_id=correlation_id,
        group_key=payload.get("group_key"),
        has_listing=bool(payload.get("listing")),
        has_assignee_hint=bool(payload.get("assignee_hint")),
        has_due_date=bool(payload.get("due_date")),
        confidence=payload.get("confidence")
    )
    
    # Extract Slack metadata
    slack_meta = {}
    if envelope.get("source"):
        slack_meta = {
            "userId": envelope["source"].get("slack_user_id"),
            "channelId": envelope["source"].get("channel_id"),
            "ts": envelope["source"].get("ts"),
        }
    else:
        # Legacy payload format
        slack_meta = {
            "userId": payload.get("user_id"),
            "channelId": payload.get("channel_id"),
            "ts": payload.get("ts"),
        }
    
    # Resolve Slack user to Realtor
    resolved_realtor = None
    if slack_meta.get("userId"):
        try:
            resolved_realtor = await resolve_slack_user(slack_meta["userId"])
            if resolved_realtor:
                logger.info(
                    "Resolved Slack user to realtor",
                        correlation_id=correlation_id,
                        slack_user_id=mask_user_id(slack_meta["userId"]),
                        realtor_id=resolved_realtor.get("realtor_id"),
                        name=resolved_realtor.get("name")
                )
        except Exception as e:
            logger.warning(
                "Failed to resolve Slack user",
                correlation_id=correlation_id,
                slack_user_id=mask_user_id(slack_meta["userId"]),
                error=str(e)
            )
    
    # Extract listing info
    listing_info = payload.get("listing", {})
    listing_type = listing_info.get("type") or "SALE"
    
    # Parse due date if present
    due_date = None
    if payload.get("due_date"):
        try:
            due_date_str = payload["due_date"]
            if "T" in due_date_str:
                due_date = date.fromisoformat(due_date_str.split("T")[0])
            else:
                due_date = date.fromisoformat(due_date_str)
        except (ValueError, AttributeError):
            pass
    
    # Generate listing ID
    listing_id = generate_listing_id()
    
    # Create listing
    listing_data = {
        "listing_id": listing_id,
        "type": listing_type,
        "status": "new",
        "address_string": listing_info.get("address") or "Unknown",
        "realtor_id": resolved_realtor.get("realtor_id") if resolved_realtor else None,
        "agent_id": resolved_realtor.get("realtor_id") if resolved_realtor else None,  # Legacy field
        "due_date": due_date.isoformat() if due_date else None,
    }
    
    listing = await create_listing(listing_data)
    
    logger.info(
        "Created listing from GROUP",
        correlation_id=correlation_id,
        listing_id=listing.get("listing_id"),
        address=listing.get("address_string"),
        listing_type=listing_type,
        realtor_id=listing.get("realtor_id"),
        group_key=payload.get("group_key"),
        due_date=due_date.isoformat() if due_date else None
    )
    
    # TODO: Seed default activities from templates based on group_key
    # For now, create a basic activity if group_key suggests one
    
    # Write to classifications table for audit
    try:
        from src.services.supabase_client import SupabaseClient
        async with SupabaseClient() as client:
            client.table("classifications").insert({
                "event_id": envelope.get("idempotency_key", ""),
                "user_id": slack_meta.get("userId", ""),
                "channel_id": slack_meta.get("channelId", ""),
                "message_ts": slack_meta.get("ts", ""),
                "message": envelope.get("source", {}).get("text", ""),
                "classification": payload,
                "message_type": "GROUP",
                "group_key": payload.get("group_key"),
                "assignee_hint": payload.get("assignee_hint"),
                "due_date": due_date.isoformat() if due_date else None,
                "confidence": payload.get("confidence", 0.0)
            }).execute()
        logger.debug(
            "Classification written to database",
            correlation_id=correlation_id,
            listing_id=listing_id
        )
    except Exception as e:
        logger.warning(
            "Failed to write classification",
            correlation_id=correlation_id,
            listing_id=listing_id,
            error=str(e)
        )


async def process_stray_message(payload: dict, envelope: dict) -> None:
    """Process a STRAY message - create agent task (not tied to a listing)."""
    correlation_id = get_correlation_id()
    
    logger.info(
        "Processing STRAY message",
        correlation_id=correlation_id,
        task_key=payload.get("task_key"),
        has_task_title=bool(payload.get("task_title")),
        has_assignee_hint=bool(payload.get("assignee_hint")),
        has_due_date=bool(payload.get("due_date")),
        confidence=payload.get("confidence")
    )
    
    # Check for promotion to listing (certain task_keys become listings)
    task_key = payload.get("task_key", "").upper()
    promote_to_listing = None
    
    if task_key in ("BUYER_DEAL", "BUYER_DEAL_CLOSING_TASKS"):
        promote_to_listing = {"dealType": "BUYER"}
    elif task_key in ("LEASE_TENANT_DEAL", "LEASE_TENANT_DEAL_CLOSING_TASKS"):
        promote_to_listing = {"dealType": "TENANT"}
    elif task_key in ("RELIST_LISTING_DEAL_SALE", "RELIST_LISTING_DEAL_LEASE", "RELIST_LISTING_DEAL"):
        promote_to_listing = {"dealType": "RELIST"}
    
    if promote_to_listing:
        logger.info(
            "Promoting STRAY to listing",
            correlation_id=correlation_id,
            task_key=task_key,
            promote_deal_type=promote_to_listing.get("dealType")
        )
        # Create listing instead of agent task
        listing_info = payload.get("listing", {})
        listing_type = listing_info.get("type") or "SALE"
        
        due_date = None
        if payload.get("due_date"):
            try:
                due_date_str = payload["due_date"]
                if "T" in due_date_str:
                    due_date = date.fromisoformat(due_date_str.split("T")[0])
                else:
                    due_date = date.fromisoformat(due_date_str)
            except (ValueError, AttributeError):
                pass
        
        listing_id = generate_listing_id()
        listing_data = {
            "listing_id": listing_id,
            "type": listing_type,
            "status": "new",
            "address_string": listing_info.get("address") or "Unknown",
            "due_date": due_date.isoformat() if due_date else None,
        }
        
        listing = await create_listing(listing_data)
        
        logger.info(
            "Promoted STRAY to listing",
            correlation_id=correlation_id,
            listing_id=listing.get("listing_id"),
            listing_type=listing_type,
            task_key=task_key
        )
        return
    
    # Extract Slack metadata
    slack_meta = {}
    if envelope.get("source"):
        slack_meta = {
            "text": envelope["source"].get("text"),
            "userId": envelope["source"].get("slack_user_id"),
            "channelId": envelope["source"].get("channel_id"),
            "ts": envelope["source"].get("ts"),
        }
    else:
        slack_meta = {
            "text": payload.get("text"),
            "userId": payload.get("user_id"),
            "channelId": payload.get("channel_id"),
            "ts": payload.get("ts"),
        }
    
    # Resolve Slack user to Realtor (required for agent_tasks)
    resolved_realtor = None
    if slack_meta.get("userId"):
        try:
            resolved_realtor = await resolve_slack_user(slack_meta["userId"])
            if not resolved_realtor:
                logger.error(
                        "Failed to resolve realtor for Slack user",
                        correlation_id=correlation_id,
                        slack_user_id=mask_user_id(slack_meta["userId"])
                    )
                return
        except Exception as e:
            logger.error(
                "Failed to resolve Slack user",
                correlation_id=correlation_id,
                slack_user_id=mask_user_id(slack_meta["userId"]),
                error=str(e),
                exc_info=True
            )
            return
    
    # Create friendly title from text
    friendly_title = None
    if slack_meta.get("text"):
        raw_text = slack_meta["text"].strip()
        if raw_text:
            first_line = raw_text.split("\n")[0]
            # Remove filler words
            first_line = re.sub(r'^\s*(please\s+)?', '', first_line, flags=re.IGNORECASE)
            first_line = " ".join(first_line.split())
            if len(first_line) > 80:
                first_line = first_line[:77] + "..."
            friendly_title = first_line[0].upper() + first_line[1:] if first_line else None
    
    # Use LLM-generated task_title if available, otherwise friendly_title
    task_title = payload.get("task_title") or friendly_title or "Task"
    
    # Map task_key to task_category
    task_category = map_task_key_to_category(task_key)
    
    # Parse due date
    due_date = None
    if payload.get("due_date"):
        try:
            due_date_str = payload["due_date"]
            if "T" in due_date_str:
                due_date = date.fromisoformat(due_date_str.split("T")[0])
            else:
                due_date = date.fromisoformat(due_date_str)
        except (ValueError, AttributeError):
            pass
    
    # Generate task ID
    task_id = generate_task_id()
    
    # Create agent task
    task_data = {
        "task_id": task_id,
        "realtor_id": resolved_realtor.get("realtor_id"),
        "task_key": task_key,  # Deprecated but required by schema
        "name": task_title,
        "description": slack_meta.get("text"),
        "status": "OPEN",
        "task_category": task_category,
        "priority": 0,
        "due_date": due_date.isoformat() if due_date else None,
        "inputs": {
            "slack": {
                "userId": slack_meta.get("userId"),
                "channelId": slack_meta.get("channelId"),
                "ts": slack_meta.get("ts")
            },
            "classification": payload
        }
    }
    
    task = await create_agent_task(task_data)
    
    logger.info(
        "Created agent task",
        correlation_id=correlation_id,
        task_id=task.get("task_id"),
        realtor_id=task.get("realtor_id"),
        name=task.get("name"),
        task_key=task_key,
        task_category=task_category,
        due_date=due_date.isoformat() if due_date else None
    )
    
    # Write to classifications table for audit
    try:
        from src.services.supabase_client import SupabaseClient
        async with SupabaseClient() as client:
            client.table("classifications").insert({
                "event_id": envelope.get("idempotency_key", ""),
                "user_id": slack_meta.get("userId", ""),
                "channel_id": slack_meta.get("channelId", ""),
                "message_ts": slack_meta.get("ts", ""),
                "message": slack_meta.get("text", ""),
                "classification": payload,
                "message_type": "STRAY",
                "task_key": task_key,
                "assignee_hint": payload.get("assignee_hint"),
                "due_date": due_date.isoformat() if due_date else None,
                "confidence": payload.get("confidence", 0.0)
            }).execute()
        logger.debug(
            "Classification written to database",
            correlation_id=correlation_id,
            task_id=task_id
        )
    except Exception as e:
        logger.warning(
            "Failed to write classification",
            correlation_id=correlation_id,
            task_id=task_id,
            error=str(e)
        )


async def process_info_request(payload: dict) -> None:
    """Process an INFO_REQUEST message - log for admin review."""
    correlation_id = get_correlation_id()
    
    logger.info(
        "Processing INFO_REQUEST",
        correlation_id=correlation_id,
        confidence=payload.get("confidence", 0.0),
        has_explanations=bool(payload.get("explanations"))
    )
    
    # Write to classifications table for audit
    try:
        from src.services.supabase_client import SupabaseClient
        async with SupabaseClient() as client:
            client.table("classifications").insert({
                "event_id": "",
                "user_id": "",
                "channel_id": "",
                "message_ts": "",
                "message": "",
                "classification": payload,
                "message_type": "INFO_REQUEST",
                "confidence": payload.get("confidence", 0.0)
            }).execute()
        logger.debug(
            "INFO_REQUEST classification written to database",
            correlation_id=correlation_id
        )
    except Exception as e:
        logger.warning(
            "Failed to write classification",
            correlation_id=correlation_id,
            error=str(e)
        )


async def poll_and_ingest_once(max_messages: int = 5) -> int:
    """
    Poll intake queue and process messages.
    
    Returns number of messages processed.
    """
    correlation_id = get_correlation_id()
    
    logger.info(
        "Polling intake queue",
        correlation_id=correlation_id,
        max_messages=max_messages
    )
    
    try:
        # Get batch of unprocessed messages
        batch = await get_intake_queue_batch(max_messages)
        
        if not batch:
            logger.debug(
                "No messages in queue",
                correlation_id=correlation_id
            )
            return 0
        
        logger.info(
            "Retrieved batch from intake queue",
            correlation_id=correlation_id,
            batch_size=len(batch),
            max_messages=max_messages
        )
        
        processed = 0
        failed = 0
        
        for idx, item in enumerate(batch):
            queue_id = item.get("id")
            envelope = item.get("envelope", {})
            
            try:
                # Check if already processed (idempotency)
                event_id = envelope.get("idempotency_key") or str(queue_id)
                if await check_intake_event_exists(str(event_id)):
                    logger.info(
                        "Skipping duplicate event",
                        correlation_id=correlation_id,
                        event_id=event_id,
                        queue_id=str(queue_id)
                    )
                    await mark_queue_item_processed(str(queue_id))
                    processed += 1
                    continue
                
                # Extract payload
                payload = envelope.get("payload", {})
                message_type = payload.get("message_type")
                
                logger.info(
                    "Processing queue item",
                    correlation_id=correlation_id,
                    queue_id=str(queue_id),
                    event_id=event_id,
                    message_type=message_type,
                    item_index=idx + 1,
                    total_items=len(batch)
                )
                
                # Process based on message type
                if message_type == "GROUP":
                    await process_group_message(payload, envelope)
                elif message_type == "STRAY":
                    await process_stray_message(payload, envelope)
                elif message_type == "INFO_REQUEST":
                    await process_info_request(payload)
                else:
                    logger.warning(
                            "Unknown message type",
                            correlation_id=correlation_id,
                            queue_id=str(queue_id),
                            message_type=message_type
                        )
                
                # Mark as processed
                await insert_intake_event(str(event_id))
                await mark_queue_item_processed(str(queue_id))
                processed += 1
                
                logger.debug(
                    "Queue item processed successfully",
                    correlation_id=correlation_id,
                    queue_id=str(queue_id),
                    message_type=message_type
                )
                
            except Exception as e:
                failed += 1
                logger.error(
                    "Error processing queue item",
                    correlation_id=correlation_id,
                    queue_id=str(queue_id),
                    item_index=idx + 1,
                    total_items=len(batch),
                    error=str(e),
                    exc_info=True
                )
                # Don't mark as processed on error - let it retry
                # Could increment retry_count here
        
        logger.info(
            "Intake queue poll completed",
            correlation_id=correlation_id,
            batch_size=len(batch),
            processed_successfully=processed,
            processed_failed=failed
        )
        
        return processed
        
    except Exception as e:
        logger.error(
            "Error polling intake queue",
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True
        )
        return 0
