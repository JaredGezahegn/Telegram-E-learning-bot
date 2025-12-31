#!/bin/bash

# Railway Deployment Script for Telegram English Bot

set -e

echo "🚀 Deploying Telegram English Bot to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway..."
    railway login
fi

# Deploy the application
echo "📦 Deploying application..."
railway up

echo "⚙️  Setting up environment variables..."

# Check if environment variables are provided
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN environment variable is required"
    echo "Please set it before running this script:"
    echo "export TELEGRAM_BOT_TOKEN=your_token_here"
    exit 1
fi

if [ -z "$TELEGRAM_CHANNEL_ID" ]; then
    echo "❌ TELEGRAM_CHANNEL_ID environment variable is required"
    echo "Please set it before running this script:"
    echo "export TELEGRAM_CHANNEL_ID=@your_channel"
    exit 1
fi

# Set required environment variables
railway variables set TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
railway variables set TELEGRAM_CHANNEL_ID="$TELEGRAM_CHANNEL_ID"

# Set optional environment variables if provided
if [ ! -z "$POSTING_TIME" ]; then
    railway variables set POSTING_TIME="$POSTING_TIME"
fi

if [ ! -z "$TIMEZONE" ]; then
    railway variables set TIMEZONE="$TIMEZONE"
fi

if [ ! -z "$LOG_LEVEL" ]; then
    railway variables set LOG_LEVEL="$LOG_LEVEL"
fi

echo "✅ Deployment completed successfully!"
echo "🔗 Your bot should be running on Railway"
echo "📊 Check logs with: railway logs"
echo "⚙️  Manage variables with: railway variables"