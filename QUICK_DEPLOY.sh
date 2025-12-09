#!/bin/bash
# Quick deployment script - Run this AFTER creating the project in Vercel dashboard

set -e

echo "🚀 ArchieOS Backend Deployment Script"
echo "========================================"
echo ""
echo "⚠️  IMPORTANT: Create the project 'archieos-backend' in Vercel dashboard first!"
echo "   Go to: https://vercel.com/nsd97s-projects"
echo ""
read -p "Press Enter once you've created the project in Vercel dashboard..."

# Link project
echo ""
echo "📎 Linking to Vercel project..."
vercel link --yes

# Set environment variables
echo ""
echo "🔐 Setting environment variables..."

# Load secrets from .env file or environment
if [ -f .env ]; then
    source .env
fi

echo "${SUPABASE_URL:-YOUR_SUPABASE_URL}" | vercel env add SUPABASE_URL production
echo "${SUPABASE_SERVICE_ROLE_KEY:-YOUR_SUPABASE_SERVICE_ROLE_KEY}" | vercel env add SUPABASE_SERVICE_ROLE_KEY production
echo "${SLACK_SIGNING_SECRET:-YOUR_SLACK_SIGNING_SECRET}" | vercel env add SLACK_SIGNING_SECRET production
echo "${SLACK_BOT_TOKEN:-YOUR_SLACK_BOT_TOKEN}" | vercel env add SLACK_BOT_TOKEN production
echo "${ANTHROPIC_API_KEY:-YOUR_ANTHROPIC_API_KEY}" | vercel env add ANTHROPIC_API_KEY production
echo "anthropic" | vercel env add LLM_PROVIDER production
echo "claude-sonnet-4-20250514" | vercel env add LLM_MODEL production
echo "0.6" | vercel env add LLM_CONFIDENCE_MIN production
echo "true" | vercel env add USE_LLM_CLASSIFIER production
echo "300" | vercel env add DEBOUNCE_WINDOW_SECONDS production
echo "production" | vercel env add ENVIRONMENT production

echo ""
echo "✅ Environment variables set!"
echo ""
echo "🚀 Deploying to production..."
vercel --prod --yes

echo ""
echo "✨ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Get your deployment URL from Vercel dashboard"
echo "2. Configure Slack webhook: https://your-app.vercel.app/api/slack/events"
echo "3. Test: curl https://your-app.vercel.app/api/health"

