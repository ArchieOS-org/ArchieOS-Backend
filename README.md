# ArchieOS Backend

Python backend for ArchieOS, built with LangChain, Supabase, and Vercel Serverless Functions.

## Overview

This backend implements a two-stage architecture:

- **Stage 1**: Slack intake pipeline - replicates mogadishu-v1 functionality for ingesting and classifying Slack messages
- **Stage 2**: LangChain agent system - voice memo processing, document generation, and advanced orchestration (coming soon)

## Architecture

### Stage 1: Slack Intake Pipeline

```
Slack Webhook → Events Endpoint → Signature Verification → Deduplication → 
Debounce Buffer → LLM Classification → Intake Queue → Intake Ingestor → 
Database (Listings/Tasks)
```

**Key Components:**

1. **Slack Events Endpoint** (`api/slack/events.py`)
   - Receives Slack webhook events
   - Verifies HMAC-SHA256 signatures
   - Deduplicates events using Supabase `intake_events` table
   - ACKs immediately (< 3s) to avoid Slack retries
   - Enqueues to debounce buffer for background processing

2. **Debounce Buffer** (`src/services/debounce_buffer.py`)
   - Groups rapid messages from same channel within time window (default: 5 minutes)
   - Reduces LLM API calls by batching related messages

3. **LLM Classifier** (`src/services/slack_classifier.py`)
   - Uses LangChain with structured output (Pydantic)
   - Pre-filters casual chat (~70-80% reduction)
   - Classifies messages into: GROUP, STRAY, INFO_REQUEST, IGNORE
   - Extracts: listing type, address, assignee, due date, task title

4. **Intake Ingestor** (`src/services/intake_ingestor.py`)
   - Polls `intake_queue` table
   - Processes GROUP messages → creates listings + seeds default tasks
   - Processes STRAY messages → creates stray tasks
   - Resolves Slack users to `people` table (auto-creates if needed)

5. **Supabase Client** (`src/services/supabase_client.py`)
   - Async wrapper with connection pooling
   - Uses transaction mode (port 6543) for serverless efficiency

## Prerequisites

- Python 3.11+
- Supabase project (Postgres database)
- Vercel account (for deployment)
- Slack app with webhook URL configured
- LLM API key (Anthropic Claude or OpenAI)

## Setup

### 1. Clone Repository

```bash
git clone https://github.com/Archieos-org/ArchieOS-Backend.git
cd ArchieOS-Backend
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (optional)
pip install -e ".[dev]"
```

### 3. Configure Environment Variables

Create `.env` file:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# Slack
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_BOT_TOKEN=your-slack-bot-token  # Optional, for user lookups

# LLM
LLM_PROVIDER=anthropic  # or "openai"
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key  # if using OpenAI
LLM_MODEL=claude-sonnet-4-20250514  # or gpt-4o-mini, etc.
LLM_CONFIDENCE_MIN=0.6

# Feature Flags
USE_LLM_CLASSIFIER=true
DEBOUNCE_WINDOW_SECONDS=300  # 5 minutes

# Environment
NODE_ENV=development  # Set to "production" in production
```

### 4. Run Supabase Migrations

```bash
# Install Supabase CLI (if not already installed)
npm install -g supabase

# Link to your project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push
```

Or manually run SQL files from `supabase/migrations/` in Supabase dashboard.

### 5. Local Development

```bash
# Run tests
pytest

# Run linting
ruff check src/

# Type checking
mypy src/
```

## API Endpoints

### `POST /api/slack/events`

Slack webhook endpoint for receiving events.

**Request:**
- Headers: `X-Slack-Signature`, `X-Slack-Request-Timestamp`
- Body: Slack event JSON

**Response:**
- `200 OK`: Event processed (or duplicate)
- `401 Unauthorized`: Invalid signature
- `500 Internal Server Error`: Processing error

**Example:**
```bash
curl -X POST https://your-app.vercel.app/api/slack/events \
  -H "X-Slack-Signature: v0=..." \
  -H "X-Slack-Request-Timestamp: 1234567890" \
  -d '{"type":"event_callback","event":{"type":"message"}}'
```

### `GET /api/health`

Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "archieos-backend"}
```

### `POST /api/intake/process`

Process intake queue (can be called manually or via cron).

**Query Parameters:**
- `max_messages` (optional): Batch size (default: 5)

**Response:**
```json
{"ok": true, "processed": 3, "max_messages": 5}
```

## Database Schema

### Core Tables

- **`people`**: Slack user resolution
- **`listings`**: Real estate listings (SALE/LEASE)
- **`tasks`**: Tasks associated with listings or stray tasks
- **`audit_log`**: Event audit trail

### Intake Tables

- **`intake_events`**: Deduplication tracking
- **`intake_queue`**: Queue for classified messages

See `supabase/migrations/` for full schema.

## Deployment

> **⚠️ Important**: Due to Vercel CLI project naming constraints, you must create the project via the Vercel dashboard first. See [DEPLOY.md](./DEPLOY.md) for detailed instructions.

### Quick Deploy

**Option 1: Use the deployment script** (after creating project in dashboard):
```bash
./QUICK_DEPLOY.sh
```

**Option 2: Manual deployment**:

1. **Create Project in Vercel Dashboard**
   - Go to https://vercel.com/nsd97s-projects
   - Click "Add New..." → "Project"
   - Import `Archieos-org/ArchieOS-Backend` or create manually
   - **Project Name**: `archieos-backend` (lowercase required)
   - Framework: Other
   - Click "Deploy"

2. **Link Project**
   ```bash
   vercel link
   # Select: nsd97s-projects
   # Select: archieos-backend
   ```

3. **Set Environment Variables**
   ```bash
   # See DEPLOY.md for full list, or use:
   ./QUICK_DEPLOY.sh
   ```

4. **Deploy**
   ```bash
   vercel --prod
   ```

For complete deployment instructions with all environment variables, see [DEPLOY.md](./DEPLOY.md).

### Configure Slack Webhook

1. Go to Slack App settings → Event Subscriptions
2. Set Request URL to: `https://your-app.vercel.app/api/slack/events`
3. Subscribe to events:
   - `message.channels`
   - `message.groups`
   - `app_mention`

### Set Up Cron Job (Optional)

Configure Vercel cron to process intake queue periodically:

```json
// vercel.json
{
  "crons": [{
    "path": "/api/intake/process",
    "schedule": "*/5 * * * *"
  }]
}
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_slack_verifier.py

# Run with verbose output
pytest -v
```

## Project Structure

```
.
├── api/                    # Vercel serverless functions
│   ├── slack/
│   │   └── events.py       # Slack webhook endpoint
│   ├── intake/
│   │   └── process.py      # Queue processor
│   └── health.py           # Health check
├── src/
│   ├── models/             # Pydantic models
│   │   ├── classification.py
│   │   ├── listing.py
│   │   └── task.py
│   ├── services/           # Business logic
│   │   ├── slack_verifier.py
│   │   ├── slack_dedup.py
│   │   ├── slack_classifier.py
│   │   ├── slack_users.py
│   │   ├── debounce_buffer.py
│   │   ├── intake_ingestor.py
│   │   └── supabase_client.py
│   └── utils/              # Utilities
│       ├── errors.py
│       └── logging.py
├── supabase/
│   └── migrations/         # Database migrations
├── tests/                  # Test suite
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Project metadata
├── vercel.json            # Vercel configuration
└── README.md              # This file
```

## Troubleshooting

### Signature Verification Fails

- Check `SLACK_SIGNING_SECRET` matches Slack app settings
- Verify timestamp is within 5-minute window
- In development, set `NODE_ENV=development` to bypass verification

### Classification Not Working

- Verify LLM API keys are set correctly
- Check `USE_LLM_CLASSIFIER=true` in environment
- Review logs for LLM API errors
- Ensure `LLM_CONFIDENCE_MIN` threshold is appropriate

### Database Connection Issues

- Verify Supabase URL and keys
- Check network connectivity
- Ensure migrations have been run
- Review Supabase dashboard for connection limits

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Stage 2 (Coming Soon)

Stage 2 will add:
- LangChain supervisor agent pattern
- Voice memo transcription and processing
- Document generation agents (listings, contracts)
- Advanced task orchestration
- Multi-agent workflows
