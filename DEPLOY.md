# Deployment Guide

## Issue
Vercel CLI is trying to use the directory name "ArchieOS-Backend" as the project name, but project names must be lowercase. We need to create the project manually or via the web interface first.

## Option 1: Create Project via Vercel Dashboard (Recommended)

1. **Go to Vercel Dashboard**: https://vercel.com/nsd97s-projects
2. **Click "Add New..." → "Project"**
3. **Import Git Repository**: Select `Archieos-org/ArchieOS-Backend` (or create without Git first)
4. **Project Name**: Use `archieos-backend` (lowercase)
5. **Framework Preset**: Other (or leave as default)
6. **Root Directory**: Leave as `.` (root)
7. **Build Command**: Leave empty (Python functions don't need build)
8. **Output Directory**: Leave empty
9. **Install Command**: Leave empty
10. **Click "Deploy"**

After deployment, you can set environment variables via the dashboard or CLI.

## Option 2: Use Vercel CLI After Manual Project Creation

Once the project exists in Vercel (created via dashboard), link it:

```bash
cd /Users/noahdeskin/ArchieOS/ArchieOS-Backend
vercel link
# Select: nsd97s-projects
# Select: archieos-backend (or the project you created)
```

Then set environment variables:

```bash
# Supabase
echo "YOUR_SUPABASE_URL" | vercel env add SUPABASE_URL production
echo "YOUR_SUPABASE_SERVICE_ROLE_KEY" | vercel env add SUPABASE_SERVICE_ROLE_KEY production

# Slack
echo "YOUR_SLACK_SIGNING_SECRET" | vercel env add SLACK_SIGNING_SECRET production
echo "YOUR_SLACK_BOT_TOKEN" | vercel env add SLACK_BOT_TOKEN production

# LLM
echo "YOUR_ANTHROPIC_API_KEY" | vercel env add ANTHROPIC_API_KEY production
echo "anthropic" | vercel env add LLM_PROVIDER production
echo "claude-sonnet-4-20250514" | vercel env add LLM_MODEL production
echo "0.6" | vercel env add LLM_CONFIDENCE_MIN production
echo "true" | vercel env add USE_LLM_CLASSIFIER production
echo "300" | vercel env add DEBOUNCE_WINDOW_SECONDS production
echo "production" | vercel env add ENVIRONMENT production

# Deploy
vercel --prod
```

## Option 3: Set Environment Variables via Dashboard

1. Go to your project in Vercel Dashboard
2. Settings → Environment Variables
3. Add each variable:
   - `SUPABASE_URL`: `YOUR_SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`: `YOUR_SUPABASE_SERVICE_ROLE_KEY`
   - `SLACK_SIGNING_SECRET`: `YOUR_SLACK_SIGNING_SECRET`
   - `SLACK_BOT_TOKEN`: `YOUR_SLACK_BOT_TOKEN`
   - `ANTHROPIC_API_KEY`: `YOUR_ANTHROPIC_API_KEY`
   - `LLM_PROVIDER`: `anthropic`
   - `LLM_MODEL`: `claude-sonnet-4-20250514`
   - `LLM_CONFIDENCE_MIN`: `0.6`
   - `USE_LLM_CLASSIFIER`: `true`
   - `DEBOUNCE_WINDOW_SECONDS`: `300`
   - `ENVIRONMENT`: `production`

4. Redeploy after setting variables

## After Deployment

1. **Get your deployment URL** from Vercel (e.g., `https://archieos-backend-xxxxx.vercel.app`)

2. **Configure Slack Webhook**:
   - Go to https://api.slack.com/apps → Your App → Event Subscriptions
   - Set Request URL: `https://your-app.vercel.app/api/slack/events`
   - Subscribe to events:
     - `message.channels`
     - `message.groups`  
     - `app_mention`

3. **Test Health Endpoint**:
   ```bash
   curl https://your-app.vercel.app/api/health
   # Should return: {"status": "ok", "service": "archieos-backend"}
   ```

4. **Test Slack Integration**:
   - Send a message in Slack
   - Check Supabase `intake_queue` table
   - Check `classifications` table for results
   - Check `listings` or `agent_tasks` tables

## Troubleshooting

- **Project name error**: Create project via dashboard first with lowercase name
- **Environment variables not working**: Ensure they're set for "Production" environment
- **Function timeout**: Check `vercel.json` - maxDuration is set to 60s
- **Import errors**: Ensure `src/**` is included in `includeFiles` in `vercel.json`

