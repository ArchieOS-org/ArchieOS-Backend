# Deployment Checklist

## What's Complete ✅

- ✅ Code implementation complete
- ✅ Supabase migration applied (`intake_events`, `intake_queue` tables)
- ✅ Models updated to match existing schema
- ✅ Integration with existing Supabase project complete

## What's Needed from You

### 1. Supabase Credentials
You already have the Supabase project (`uhkrvxlclflgevocqtkh`). I need:

- **SUPABASE_URL**: Your Supabase project URL (e.g., `https://xxxxx.supabase.co`)
- **SUPABASE_SERVICE_ROLE_KEY**: Service role key (for backend operations)
- **SUPABASE_ANON_KEY**: Anon key (for reference, may not be needed for backend)

### 2. Slack App Credentials
- **SLACK_SIGNING_SECRET**: From your Slack app settings → Basic Information
- **SLACK_BOT_TOKEN** (optional): For user lookups via Slack API

### 3. LLM API Key
Choose one:
- **ANTHROPIC_API_KEY**: If using Claude (recommended)
- **OPENAI_API_KEY**: If using OpenAI GPT models

Also specify:
- **LLM_PROVIDER**: `anthropic` or `openai`
- **LLM_MODEL**: Model name (e.g., `claude-sonnet-4-20250514`)

### 4. Vercel Setup
I can create the Vercel project for you, but I need:
- **Team/Organization**: Which Vercel team/org should this be deployed to?
- Or I can deploy to your personal account

### 5. Slack Webhook Configuration
After deployment, you'll need to:
- Set Slack webhook URL to: `https://your-app.vercel.app/api/slack/events`
- Subscribe to events: `message.channels`, `message.groups`, `app_mention`

## Next Steps

Once you provide the credentials above, I can:
1. Create/configure the Vercel project
2. Set all environment variables
3. Deploy the backend
4. Test the Slack webhook endpoint
5. Verify the integration works end-to-end

## Quick Start (If You Want to Do It Manually)

```bash
# 1. Install Vercel CLI (if not already installed)
npm i -g vercel

# 2. Link to Vercel
cd /Users/noahdeskin/ArchieOS/ArchieOS-Backend
vercel link

# 3. Set environment variables
vercel env add SUPABASE_URL
vercel env add SUPABASE_SERVICE_ROLE_KEY
vercel env add SLACK_SIGNING_SECRET
vercel env add ANTHROPIC_API_KEY
# ... etc

# 4. Deploy
vercel --prod
```

## Testing After Deployment

1. Test health endpoint: `curl https://your-app.vercel.app/api/health`
2. Test Slack webhook (Slack will send a challenge on first setup)
3. Send a test message in Slack
4. Check Supabase `intake_queue` table for processed messages
5. Verify `listings` or `agent_tasks` tables have new records


