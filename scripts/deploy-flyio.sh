#!/bin/bash

# Fly.io Deployment Script for Telegram English Bot

set -e

echo "🚀 Deploying Telegram English Bot to Fly.io..."

# Check if Fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Installing..."
    curl -L https://fly.io/install.sh | sh
    echo "Please add Fly CLI to your PATH and run this script again"
    exit 1
fi

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo "🔐 Please login to Fly.io..."
    fly auth login
fi

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

# Launch app (creates app if doesn't exist)
echo "📦 Launching application..."
if [ ! -f "fly.toml" ]; then
    echo "❌ fly.toml not found. Please run from project root directory."
    exit 1
fi

# Create app if it doesn't exist
if ! fly status &> /dev/null; then
    echo "🆕 Creating new Fly.io app..."
    fly launch --no-deploy
fi

# Create volume for persistent data if it doesn't exist
echo "💾 Setting up persistent storage..."
if ! fly volumes list | grep -q "bot_data"; then
    fly volumes create bot_data --region iad --size 1
fi

# Set secrets
echo "🔐 Setting up secrets..."
fly secrets set TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
fly secrets set TELEGRAM_CHANNEL_ID="$TELEGRAM_CHANNEL_ID"

# Set optional secrets if provided
if [ ! -z "$POSTING_TIME" ]; then
    fly secrets set POSTING_TIME="$POSTING_TIME"
fi

if [ ! -z "$TIMEZONE" ]; then
    fly secrets set TIMEZONE="$TIMEZONE"
fi

if [ ! -z "$LOG_LEVEL" ]; then
    fly secrets set LOG_LEVEL="$LOG_LEVEL"
fi

# Deploy the application
echo "🚀 Deploying application..."
fly deploy

echo "✅ Deployment completed successfully!"
echo "🔗 Your bot should be running on Fly.io"
echo "📊 Check logs with: fly logs"
echo "📱 Check status with: fly status"
echo "⚙️  Manage secrets with: fly secrets list"