#!/bin/bash

# Docker Deployment Script for Telegram English Bot

set -e

echo "🐳 Building and running Telegram English Bot with Docker..."

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker daemon not running. Please start Docker."
    exit 1
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

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t telegram-english-bot .

# Stop and remove existing container if it exists
if docker ps -a | grep -q "english-bot"; then
    echo "🛑 Stopping existing container..."
    docker stop english-bot || true
    docker rm english-bot || true
fi

# Create volume for persistent data
echo "💾 Creating data volume..."
docker volume create bot_data || true

# Prepare environment variables
ENV_VARS="-e TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN -e TELEGRAM_CHANNEL_ID=$TELEGRAM_CHANNEL_ID"

if [ ! -z "$POSTING_TIME" ]; then
    ENV_VARS="$ENV_VARS -e POSTING_TIME=$POSTING_TIME"
fi

if [ ! -z "$TIMEZONE" ]; then
    ENV_VARS="$ENV_VARS -e TIMEZONE=$TIMEZONE"
fi

if [ ! -z "$LOG_LEVEL" ]; then
    ENV_VARS="$ENV_VARS -e LOG_LEVEL=$LOG_LEVEL"
fi

if [ ! -z "$RETRY_ATTEMPTS" ]; then
    ENV_VARS="$ENV_VARS -e RETRY_ATTEMPTS=$RETRY_ATTEMPTS"
fi

if [ ! -z "$RETRY_DELAY" ]; then
    ENV_VARS="$ENV_VARS -e RETRY_DELAY=$RETRY_DELAY"
fi

# Run the container
echo "🚀 Starting container..."
docker run -d \
    --name english-bot \
    --restart unless-stopped \
    $ENV_VARS \
    -v bot_data:/app/data \
    telegram-english-bot

echo "✅ Container started successfully!"
echo "📊 Check logs with: docker logs english-bot"
echo "📱 Check status with: docker ps"
echo "🛑 Stop container with: docker stop english-bot"

# Show container status
echo ""
echo "📋 Container Status:"
docker ps --filter name=english-bot --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Show recent logs
echo ""
echo "📊 Recent Logs:"
docker logs --tail 20 english-bot