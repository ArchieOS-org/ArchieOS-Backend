# Setup Required - Final Steps

## What I Can Do Automatically ✅

I can deploy to Vercel once you provide the credentials below. The Supabase project is already connected and migrations are applied.

## What I Need From You 🔑

### Required Environment Variables

1. **SUPABASE_SERVICE_ROLE_KEY**
   - Get from: Supabase Dashboard → Project Settings → API → `service_role` key (secret)
   - ⚠️ Keep this secret - it has admin access

2. **SLACK_SIGNING_SECRET**
   - Get from: Slack App Settings → Basic Information → App Credentials → Signing Secret

3. **LLM API Key** (choose one):
   - **ANTHROPIC_API_KEY**: Get from https://console.anthropic.com/
   - OR **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys

### Optional (but recommended):

4. **SLACK_BOT_TOKEN** (optional)
   - Get from: Slack App Settings → OAuth & Permissions → Bot User OAuth Token
   - Needed for: User lookups (auto-creating realtor records with names)

## Current Status

- ✅ Supabase Project: Connected (`uhkrvxlclflgevocqtkh`)
- ✅ Supabase URL: `https://kukmshbkzlskyuacgzbo.supabase.co`
- ✅ Migrations: Applied (`intake_events`, `intake_queue` tables exist)
- ✅ Vercel Team: Found (`nsd97's projects`)
- ⏳ Vercel Project: Ready to create/deploy
- ⏳ Environment Variables: Waiting for your credentials

## Once You Provide Credentials

I will:
1. Create the Vercel project
2. Set all environment variables
3. Deploy the backend
4. Provide you with the webhook URL for Slack

## Quick Test After Deployment

```bash
# Test health endpoint
curl https://your-app.vercel.app/api/health

# Should return: {"status": "ok", "service": "archieos-backend"}
```

Then configure Slack webhook URL in your Slack app settings.


