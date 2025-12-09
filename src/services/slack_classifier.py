"""LLM classifier for Slack messages using LangChain with structured output."""

import os
import json
import time
import re
from typing import Optional
from datetime import datetime
# Note: LangChain structured output API may vary by version
# Using with_structured_output for Pydantic models
try:
    from langchain.agents import create_agent
    from langchain.agents.structured_output import ToolStrategy
except ImportError:
    # Fallback for different LangChain versions
    create_agent = None
    ToolStrategy = None
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from src.models.classification import ClassificationV1, MessageType
from src.services.supabase_client import enqueue_intake_message
from src.utils.errors import ClassificationError
from src.utils.logging import (
    get_structured_logger,
    log_timing,
    sanitize_message_text,
    mask_user_id,
    get_correlation_id,
)

logger = get_structured_logger(__name__)


def should_skip_prefilter(text: str) -> tuple[bool, Optional[str]]:
    """
    Pre-filter messages to skip obvious casual chat/noise before LLM classification.
    
    Reduces unnecessary API calls by ~70-80% based on CloudWatch data showing 90% IGNORE rate.
    
    Returns tuple of (should_skip, reason)
    """
    if not text or not isinstance(text, str):
        return False, None
    
    normalized = text.strip().lower()
    
    # Skip very short messages (< 10 chars, likely acknowledgments)
    if len(normalized) < 10:
        return True, "message_too_short"
    
    # Skip emoji-only or mostly emoji messages
    emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]', re.UNICODE)
    text_without_emoji = emoji_pattern.sub('', text).strip()
    if len(text_without_emoji) < 5:
        return True, "emoji_only"
    
    # Skip common greetings/acknowledgments
    casual_patterns = [
        (r'^(hi|hey|hello|thanks|thank you|thx|ty|ok|okay|sure|sounds good|perfect|great|awesome|nice|cool|lol|haha|yes|no|yep|nope|👍|👌)[\s!.]*$', "casual_greeting"),
        (r'^(good morning|good afternoon|good evening|gm|gn)[\s!.]*$', "greeting"),
        (r'^(congrats|congratulations|well done|good job)[\s!.]*$', "acknowledgment"),
    ]
    
    for pattern, reason in casual_patterns:
        if re.match(pattern, normalized, re.IGNORECASE):
            return True, reason
    
    # Skip pure emoji/reaction messages
    if re.match(r'^[\s\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF!.?]+$', text, re.UNICODE):
        return True, "emoji_reaction"
    
    return False, None


def redact_pii(text: str) -> str:
    """Redact PII from text (emails and phone numbers)."""
    if not text:
        return ""
    
    # Redact emails
    text = re.sub(
        r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',
        '[REDACTED_EMAIL]',
        text,
        flags=re.IGNORECASE
    )
    
    # Redact phone numbers
    text = re.sub(
        r'\b\+?\d[\d\s().-]{7,}\b',
        '[REDACTED_PHONE]',
        text
    )
    
    return text


def extract_links(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = r'https?://\S+'
    raw_urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    cleaned = []
    for url in raw_urls:
        # Remove common trailing punctuation
        url = re.sub(r'[&gt;>)\],.]+$', '', url)
        # Strip HTML-escaped angle brackets
        url = re.sub(r'^&lt;|&gt;$', '', url)
        # Strip literal angle brackets
        url = re.sub(r'^<|>$', '', url)
        # Keep URL before Slack's "|label" form
        url = url.split('|')[0]
        cleaned.append(url)
    
    return cleaned


def build_classification_prompt(
    text: str,
    slack_user_id: str,
    channel_id: str,
    ts: str,
    links: Optional[list[str]] = None,
    attachments: Optional[list[dict]] = None
) -> dict:
    """
    Build the classification prompt matching mogadishu-v1 logic.
    
    Returns dict with system, developer, user, and fewShot prompts.
    """
    sanitized_text = redact_pii(text)
    
    # Parse timestamp
    try:
        ts_number = float(ts)
        ref_iso = datetime.fromtimestamp(ts_number).isoformat() if ts_number > 0 else datetime.now().isoformat()
    except (ValueError, OSError):
        ref_iso = datetime.now().isoformat()
    
    links_section = ""
    if links and len(links) > 0:
        links_section = "\n\nLinks (verbatim):\n" + "\n".join(links)
    
    system_prompt = """System (ultra-brief, non-negotiable)
You transform real-estate operations Slack messages into JSON only that conforms to the developer instructions and schema.
Never fabricate fields. If irrelevant to ops, return IGNORE. If operational but incomplete, return INFO_REQUEST with brief explanations.
Do not output prose or code fences—JSON only."""
    
    developer_prompt = """Developer (full behavior spec)
Objective
Classify a Slack message and extract fields into a strict JSON object that matches the schema. Return only valid JSON.

Message types
• GROUP — The message declares or updates a listing container (i.e., "this is a listing entity").
Allowed group_key values:
• SALE_LISTING
• LEASE_LISTING
• SALE_LEASE_LISTING
• SOLD_SALE_LEASE_LISTING
• RELIST_LISTING
• RELIST_LISTING_DEAL_SALE_OR_LEASE
• BUY_OR_LEASED
• MARKETING_AGENDA_TEMPLATE
• STRAY — A single actionable task that does not declare/update a listing group (creates an agent task). Pick exactly one task_key: prefer the catalog below; otherwise use OPS_MISC_TASK for any clear request.
• INFO_REQUEST — Operational/real-estate content but missing specifics to proceed. Explain what's missing in explanations.
• IGNORE — Chit-chat, reactions, or content unrelated to operations.

Decision rules & tie-breaks
• Choose exactly one message_type.
• Prefer GROUP if a message both declares/updates a listing and requests tasks.
• GROUP ⇒ set group_key (one of the allowed values) and task_key:null.
• STRAY ⇒ set exactly one task_key (from taxonomy) and group_key:null. Creates an agent task (not tied to a listing).
• If multiple task candidates appear, choose the most specific (e.g., *_CLOSING_* over *_ACTIVE_*). If ambiguity remains, use INFO_REQUEST and explain briefly.

Listing types (for listing.type)
• Only set "SALE" or "LEASE" if explicit OR unambiguously implied by the hints below. Otherwise null.
  Hints for SALE (non-exhaustive): sold, conditional, firm, purchase agreement/APS, buyer deal, closing date (sale), MLS #, open house, staging, deposit (sale), conditions removal.
  Hints for LEASE (non-exhaustive): lease/leased, tenant/landlord, showings schedule, OTL/offer to lease, LOI, rent/TMI/NNN, possession date (lease), renewal, term/rate per month.

Assignees & addresses
• assignee_hint → Person explicitly named or @-mentioned. If only pronouns ("he/she/they") or only a team ("Marketing"), set null.
• listing.address → Extract only if explicitly present in text OR clearly present within provided links/attachment titles.

Dates & timezone policy
• Timezone: America/Toronto. Current reference time: """ + ref_iso + """
• CRITICAL: Use message_timestamp_iso as YOUR reference for "today" when parsing relative dates.

• Output format rules:
  - Date-only (no time mentioned): Use yyyy-MM-dd format
  - Date AND time mentioned: Use yyyy-MM-ddTHH:mm format (24-hour)
  - NEVER add a default time if time was not mentioned in the message

• Date parsing examples (assume message_timestamp_iso = """ + ref_iso + """):
  - "tomorrow" → 1 day after message timestamp → "2025-11-03"
  - "in 2 days" / "in two days" → 2 days after message timestamp → "2025-11-04"
  - "by Friday" / "this Friday" → next Friday occurrence after message timestamp → "2025-11-08"
  - "next week" → 7 days after message timestamp → "2025-11-09"
  - "Oct 15" → abbreviated month, infer year → "2025-10-15"
  - "November 10" → full month name, infer year → "2025-11-10"
  - "December 1" → full month name, infer year → "2025-12-01"
  - "due November 7" → extract date from phrase → "2025-11-07"
  - "tomorrow at 3pm" → includes time → "2025-11-03T15:00"
  - "Friday at 5pm" → includes time → "2025-11-08T17:00"

• If ambiguous or contradictory, set null and add brief explanation.

Best-effort vs nulls
• Prefer best-effort fills with a short explanation when reasonable (e.g., listing.type from strong hints, relative dates).
• Never fabricate addresses or names.

Task taxonomy (valid task_key values for STRAY - creates agent tasks)
Sale Listings
• SALE_ACTIVE_TASKS, SALE_SOLD_TASKS, SALE_CLOSING_TASKS

Lease Listings
• LEASE_ACTIVE_TASKS, LEASE_LEASED_TASKS, LEASE_CLOSING_TASKS, LEASE_ACTIVE_TASKS_ARLYN (special case)

Re-List Listings
• RELIST_LISTING_DEAL_SALE, RELIST_LISTING_DEAL_LEASE

Buyer Deals
• BUYER_DEAL, BUYER_DEAL_CLOSING_TASKS

Lease Tenant Deals
• LEASE_TENANT_DEAL, LEASE_TENANT_DEAL_CLOSING_TASKS

Pre-Con Deals
• PRECON_DEAL

Mutual Release
• MUTUAL_RELEASE_STEPS

General Ops
• OPS_MISC_TASK (any actionable request without a specific template)

Task Titles (for STRAY only)
• For STRAY messages, generate a concise task_title (5-10 words max, 80 chars max) summarizing the actionable request (used as agent task name)
• Remove filler words ("please", "can you", "could you")
• Capitalize first word
• Examples:
  - "can you bring a small stack of your business cards to the office tomorrow?" → "Bring business cards to office"
  - "Please update the brochure copy and send draft by Friday" → "Update brochure copy and send draft"
  - "need help setting up the new listing photos" → "Set up new listing photos"
• Set task_title:null for GROUP, INFO_REQUEST, IGNORE

Extraction rules
• listing.address → Street/building/unit only if explicit in text or provided links; otherwise null.
• assignee_hint → name/@mention only; pronouns/teams => null.
• due_date → resolve per rules above; if not resolvable, null with a brief explanation.
• task_title → concise summary (5-10 words) for STRAY only (becomes agent task name); null for GROUP/INFO_REQUEST/IGNORE.
• confidence ∈ [0,1] reflects certainty of classification and extracted fields.
• explanations → brief bullets for assumptions, heuristics, or missing info; null if not needed."""
    
    few_shot_examples = [
        {
            "role": "user",
            "content": 'Input: "Create a new lease listing for 22 King St W unit 1402."'
        },
        {
            "role": "assistant",
            "content": json.dumps({
                "schema_version": 1,
                "message_type": "GROUP",
                "task_key": None,
                "group_key": "LEASE_LISTING",
                "listing": {"type": "LEASE", "address": "22 King St W unit 1402"},
                "assignee_hint": None,
                "due_date": None,
                "task_title": None,
                "confidence": 0.94,
                "explanations": ["Due date not present"]
            })
        },
        {
            "role": "user",
            "content": 'Input: "For 18 Oak Ave, start closing checklist; target Oct 3 17:00."'
        },
        {
            "role": "assistant",
            "content": json.dumps({
                "schema_version": 1,
                "message_type": "STRAY",
                "task_key": "SALE_CLOSING_TASKS",
                "group_key": None,
                "listing": {"type": "SALE", "address": "18 Oak Ave"},
                "assignee_hint": None,
                "due_date": "2025-10-03T17:00",
                "task_title": "Start closing checklist for 18 Oak Ave",
                "confidence": 0.91,
                "explanations": None
            })
        },
        {
            "role": "user",
            "content": 'Input: "Please start active tasks for the new listing."'
        },
        {
            "role": "assistant",
            "content": json.dumps({
                "schema_version": 1,
                "message_type": "INFO_REQUEST",
                "task_key": None,
                "group_key": None,
                "listing": {"type": None, "address": None},
                "assignee_hint": None,
                "due_date": None,
                "task_title": None,
                "confidence": 0.72,
                "explanations": ["Missing listing type (SALE/LEASE)", "Missing address", "Due date not present"]
            })
        },
        {
            "role": "user",
            "content": 'Input: "Great job team! 🎉"'
        },
        {
            "role": "assistant",
            "content": json.dumps({
                "schema_version": 1,
                "message_type": "IGNORE",
                "task_key": None,
                "group_key": None,
                "listing": {"type": None, "address": None},
                "assignee_hint": None,
                "due_date": None,
                "task_title": None,
                "confidence": 0.99,
                "explanations": ["Irrelevant to operations"]
            })
        },
        {
            "role": "user",
            "content": 'Input: "Please update the brochure copy and send draft by Friday."'
        },
        {
            "role": "assistant",
            "content": json.dumps({
                "schema_version": 1,
                "message_type": "STRAY",
                "task_key": "OPS_MISC_TASK",
                "group_key": None,
                "listing": {"type": None, "address": None},
                "assignee_hint": None,
                "due_date": None,
                "task_title": "Update brochure copy and send draft",
                "confidence": 0.74,
                "explanations": ["Generic operations request without a specific template"]
            })
        }
    ]
    
    user_prompt = f"""Return ONLY JSON per the schema.

Context: timezone=America/Toronto; message_timestamp_iso={ref_iso}

Message:
{sanitized_text}{links_section}"""
    
    return {
        "system": system_prompt,
        "developer": developer_prompt,
        "user": user_prompt,
        "fewShot": few_shot_examples
    }


def get_llm_model():
    """Get configured LLM model."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    model_name = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
    
    logger.debug(
        "Getting LLM model",
        llm_provider=provider,
        llm_model=model_name
    )
    
    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ClassificationError("ANTHROPIC_API_KEY not set")
        return ChatAnthropic(model=model_name, api_key=api_key)
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ClassificationError("OPENAI_API_KEY not set")
        return ChatOpenAI(model=model_name, api_key=api_key)
    else:
        raise ClassificationError(f"Unsupported LLM provider: {provider}")


async def classify_and_enqueue_slack_message(
    text: str,
    slack_user_id: str,
    channel_id: str,
    ts: str,
    links: Optional[list[str]] = None,
    attachments: Optional[list[dict]] = None
) -> dict:
    """
    Classify a Slack message and enqueue to intake queue.
    
    Returns dict with 'ok' or 'skipped' key.
    """
    correlation_id = get_correlation_id()
    
    logger.info(
        "Classification started",
        correlation_id=correlation_id,
        channel_id=channel_id,
        slack_user_id=mask_user_id(slack_user_id),
        message_ts=ts,
        message_preview=sanitize_message_text(text, max_length=100),
        message_length=len(text) if text else 0,
        links_count=len(links) if links else 0,
        has_attachments=bool(attachments)
    )
    
    # Check feature flag
    use_classifier = os.environ.get("USE_LLM_CLASSIFIER", "true").lower() == "true"
    if not use_classifier:
        logger.debug(
            "Classifier disabled via feature flag",
            correlation_id=correlation_id,
            channel_id=channel_id
        )
        return {"skipped": True}
    
    # Pre-filter casual chat
    should_skip, skip_reason = should_skip_prefilter(text)
    if should_skip:
        logger.info(
            "Message skipped by pre-filter",
            correlation_id=correlation_id,
            channel_id=channel_id,
            skip_reason=skip_reason,
            message_preview=sanitize_message_text(text, max_length=50)
        )
        return {"skipped": True}
    
    try:
        # Build prompt
        with log_timing("build_classification_prompt", logger=logger, correlation_id=correlation_id):
        prompt_data = build_classification_prompt(text, slack_user_id, channel_id, ts, links, attachments)
        
        # Build full prompt
        full_prompt = f"""{prompt_data['system']}

{prompt_data['developer']}

{prompt_data['user']}"""
        
        prompt_size = len(full_prompt)
        logger.debug(
            "Classification prompt built",
            correlation_id=correlation_id,
            prompt_size_chars=prompt_size,
            prompt_size_kb=round(prompt_size / 1024, 2)
        )
        
        # Use LLM with structured output
        model = get_llm_model()
        provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
        model_name = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
        
        logger.info(
            "LLM classification request started",
            correlation_id=correlation_id,
            llm_provider=provider,
            llm_model=model_name,
            prompt_size_chars=prompt_size
        )
        
        llm_start_time = time.time()
        
        # Use with_structured_output for Pydantic models
        try:
            structured_llm = model.with_structured_output(ClassificationV1)
            classification = structured_llm.invoke(full_prompt)
        except AttributeError:
            # Fallback: use regular invoke and parse JSON
            response = model.invoke(full_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from response
            try:
                # Look for JSON in the response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    classification_dict = json.loads(json_str)
                    classification = ClassificationV1(**classification_dict)
                else:
                    raise ClassificationError("No JSON found in LLM response")
            except (json.JSONDecodeError, ValueError) as e:
                raise ClassificationError(f"Failed to parse LLM response: {e}")
        
        llm_latency_ms = (time.time() - llm_start_time) * 1000
        
        logger.info(
            "LLM classification response received",
            correlation_id=correlation_id,
            llm_provider=provider,
            llm_model=model_name,
            llm_latency_ms=round(llm_latency_ms, 2),
            message_type=classification.message_type.value if classification.message_type else None,
            confidence=classification.confidence,
            group_key=classification.group_key,
            task_key=classification.task_key,
            has_listing_address=bool(classification.listing and classification.listing.get("address")),
            has_assignee_hint=bool(classification.assignee_hint),
            has_due_date=bool(classification.due_date),
            has_task_title=bool(classification.task_title)
        )
        
        # Check confidence threshold
        confidence_min = float(os.environ.get("LLM_CONFIDENCE_MIN", "0.6"))
        if classification.confidence < confidence_min:
            logger.info(
                "Classification below confidence threshold",
                correlation_id=correlation_id,
                confidence=classification.confidence,
                confidence_threshold=confidence_min,
                message_type=classification.message_type.value if classification.message_type else None
            )
            return {"skipped": True}
        
        # Skip IGNORE messages
        if classification.message_type == MessageType.IGNORE:
            logger.info(
                "Message classified as IGNORE, skipping",
                correlation_id=correlation_id,
                confidence=classification.confidence
            )
            return {"skipped": True}
        
        # Enqueue to intake queue
        idempotency_key = f"{channel_id}:{ts}"
        envelope = {
            "schema": "classification_v1",
            "idempotency_key": idempotency_key,
            "source": {
                "slack_user_id": slack_user_id,
                "channel_id": channel_id,
                "ts": ts,
                "text": text
            },
            "payload": classification.model_dump(),
            "links": links or [],
            "attachments": attachments or []
        }
        
        with log_timing("enqueue_intake_message", logger=logger, correlation_id=correlation_id):
        await enqueue_intake_message(envelope, classification.message_type.value)
        
        logger.info(
            "Message classified and enqueued",
            correlation_id=correlation_id,
            message_type=classification.message_type.value,
            channel_id=channel_id,
            slack_user_id=mask_user_id(slack_user_id),
            confidence=classification.confidence,
            group_key=classification.group_key,
            task_key=classification.task_key,
            listing_address=classification.listing.get("address") if classification.listing else None,
            assignee_hint=classification.assignee_hint,
            due_date=classification.due_date,
            task_title=classification.task_title,
            idempotency_key=idempotency_key
        )
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(
            "Classification error",
            correlation_id=correlation_id,
            channel_id=channel_id,
            slack_user_id=mask_user_id(slack_user_id),
            error=str(e),
            exc_info=True
        )
        return {"skipped": True}

