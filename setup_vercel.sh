#!/bin/bash
# Setup script for Vercel deployment with environment variables

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Vercel project...${NC}"

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo -e "${YELLOW}Vercel CLI not found. Installing...${NC}"
    npm install -g vercel
fi

# Link project (if not already linked)
if [ ! -f ".vercel/project.json" ]; then
    echo "Linking to Vercel..."
    vercel link --yes --scope=nsd97s-projects
fi

# Set environment variables
echo -e "${GREEN}Setting environment variables...${NC}"

# Load secrets from .env file if it exists
if [ -f .env ]; then
    source .env
fi

# Supabase
vercel env add SUPABASE_URL production <<< "${SUPABASE_URL:-YOUR_SUPABASE_URL}"
vercel env add SUPABASE_SERVICE_ROLE_KEY production <<< "${SUPABASE_SERVICE_ROLE_KEY:-YOUR_SUPABASE_SERVICE_ROLE_KEY}"
vercel env add SUPABASE_ANON_KEY production <<< "${SUPABASE_ANON_KEY:-YOUR_SUPABASE_ANON_KEY}"

# Slack
vercel env add SLACK_SIGNING_SECRET production <<< "${SLACK_SIGNING_SECRET:-YOUR_SLACK_SIGNING_SECRET}"
vercel env add SLACK_BOT_TOKEN production <<< "${SLACK_BOT_TOKEN:-YOUR_SLACK_BOT_TOKEN}"

# LLM
vercel env add ANTHROPIC_API_KEY production <<< "${ANTHROPIC_API_KEY:-YOUR_ANTHROPIC_API_KEY}"
vercel env add LLM_PROVIDER production <<< "anthropic"
vercel env add LLM_MODEL production <<< "claude-sonnet-4-20250514"
vercel env add LLM_CONFIDENCE_MIN production <<< "0.6"

# Feature flags
vercel env add USE_LLM_CLASSIFIER production <<< "true"
vercel env add DEBOUNCE_WINDOW_SECONDS production <<< "300"
vercel env add ENVIRONMENT production <<< "production"
vercel env add NODE_ENV production <<< "production"

echo -e "${GREEN}Environment variables set!${NC}"
echo -e "${YELLOW}Deploying to production...${NC}"
vercel --prod

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Get your deployment URL from Vercel dashboard"
echo "2. Configure Slack webhook: https://your-app.vercel.app/api/slack/events"
echo "3. Subscribe to events: message.channels, message.groups, app_mention"

