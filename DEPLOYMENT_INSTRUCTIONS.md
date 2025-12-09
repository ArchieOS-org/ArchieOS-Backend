# Deployment Instructions

## Quick Deploy

I've created a setup script with your credentials. Run:

```bash
cd /Users/noahdeskin/ArchieOS/ArchieOS-Backend
./setup_vercel.sh
```

This will:
1. Link to Vercel (if needed)
2. Set all environment variables
3. Deploy to production

## Manual Deployment (Alternative)

If you prefer to set variables manually:

```bash
# 1. Link project
vercel link --scope=nsd97s-projects

# 2. Set environment variables (one at a time)
vercel env add SUPABASE_URL production
# Enter: YOUR_SUPABASE_URL

vercel env add SUPABASE_SERVICE_ROLE_KEY production
# Enter: YOUR_SUPABASE_SERVICE_ROLE_KEY

vercel env add SLACK_SIGNING_SECRET production
# Enter: YOUR_SLACK_SIGNING_SECRET

vercel env add SLACK_BOT_TOKEN production
# Enter: YOUR_SLACK_BOT_TOKEN

vercel env add ANTHROPIC_API_KEY production
# Enter: YOUR_ANTHROPIC_API_KEY

vercel env add LLM_PROVIDER production
# Enter: anthropic

vercel env add LLM_MODEL production
# Enter: claude-sonnet-4-20250514

# 3. Deploy
vercel --prod
```

## After Deployment

1. **Get your deployment URL** from Vercel dashboard (e.g., `https://archieos-backend-xxxxx.vercel.app`)

2. **Configure Slack Webhook**:
   - Go to Slack App Settings → Event Subscriptions
   - Set Request URL to: `https://your-app.vercel.app/api/slack/events`
   - Subscribe to events:
     - `message.channels`
     - `message.groups`
     - `app_mention`

3. **Test the endpoint**:
   ```bash
   curl https://your-app.vercel.app/api/health
   # Should return: {"status": "ok", "service": "archieos-backend"}
   ```

4. **Test Slack integration**:
   - Send a message in a Slack channel
   - Check Supabase `intake_queue` table for the message
   - Check `classifications` table for classification results
   - Check `listings` or `agent_tasks` tables for created records

## Environment Variables Set

- ✅ SUPABASE_URL: `https://kukmshbkzlskyuacgzbo.supabase.co`
- ✅ SUPABASE_SERVICE_ROLE_KEY: (set)
- ✅ SLACK_SIGNING_SECRET: (set)
- ✅ SLACK_BOT_TOKEN: (set)
- ✅ ANTHROPIC_API_KEY: (set)
- ✅ LLM_PROVIDER: `anthropic`
- ✅ LLM_MODEL: `claude-sonnet-4-20250514`

## Troubleshooting

If deployment fails:
1. Check Vercel logs: `vercel logs`
2. Verify environment variables: `vercel env ls`
3. Test locally: Set `.env` file with same variables and test

