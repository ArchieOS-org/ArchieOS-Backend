# Schema Mapping Document

## Overview
Mapping between our new backend code and existing Supabase schema.

## Table Mappings

### People/Users
- **Our Code**: `people` table (UUID-based)
- **Existing DB**: `realtors` table (text-based `realtor_id`)
- **Action**: Use `realtors` as primary people table
- **Key Fields**: `realtor_id` (text), `slack_user_id` (text), `name`, `email`, `status`

### Listings
- **Our Code**: `listings` table (UUID-based)
- **Existing DB**: `listings` table (text-based `listing_id`)
- **Action**: Use existing table, convert IDs to text
- **Key Fields**: `listing_id` (text), `realtor_id` (text FK), `type`, `status`, `address_string`

### Tasks
- **Our Code**: Unified `tasks` table with `is_stray` flag
- **Existing DB**: 
  - `activities` table (listing tasks) - has `listing_id` FK
  - `agent_tasks` table (tasks) - has `realtor_id` FK
- **Action**: Use both tables, no unified table
- **Key Fields**:
  - `activities`: `task_id` (text), `listing_id` (text FK), `realtor_id` (text FK), `assigned_staff_id` (text FK)
  - `agent_tasks`: `task_id` (text), `realtor_id` (text FK), `assigned_staff_id` (text FK)

### Infrastructure (New)
- **intake_events**: New table for idempotency
- **intake_queue**: New table for processing queue
- **audit_log**: Check if exists, create if missing

## ID Format
- Existing tables use `text` for IDs (likely ULID format)
- Our code uses UUID - need to convert to text IDs
- Generate IDs using ULID or similar text-based format

## Field Mappings

### Listing Creation
- `listing_id`: Generate text ID (ULID)
- `realtor_id`: From resolved Slack user
- `type`: From classification (`SALE` or `LEASE`)
- `status`: Default to `'new'`
- `address_string`: From classification `listing.address`

### Activity Creation (Listing Tasks)
- `task_id`: Generate text ID
- `listing_id`: From created listing
- `realtor_id`: From resolved user (if applicable)
- `assigned_staff_id`: From resolved user (if staff)
- `name`: From task template or classification
- `status`: Default to `'OPEN'`
- `task_category`: Map from classification `task_key`

### AgentTask Creation (Tasks)
- `task_id`: Generate text ID
- `realtor_id`: From resolved user (required)
- `name`: From classification `task_title` or message text
- `status`: Default to `'OPEN'`
- `task_category`: Map from classification `task_key`

## User Resolution Flow
1. Check `realtors` table by `slack_user_id`
2. If not found, create new record in `realtors`
3. Return `realtor_id` (text)
4. Optionally check `staff` table for internal operations

## Terminology Changes
- Remove all "stray task" references
- Use "agent_tasks" or just "tasks" instead
- `agent_tasks` table = tasks not tied to listings

