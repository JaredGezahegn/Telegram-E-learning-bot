#!/bin/bash

# Docker Compose Deployment Script for Telegram English Bot

set -e

echo "🐳 Deploying Telegram English Bot with Docker Compose..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    echo "cp .env.example .env"
    echo "Then edit .env with your bot token and channel ID"
    exit 1
fi

# Check if environment variables are set in .env
if ! grep -q "TELEGRAM_BOT_TOKEN=" .env || ! grep -q "TELEGRAM_CHANNEL_ID=" .env; then
    echo "❌ Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID in .env file"
    exit 1
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down || docker compose down || true

# Build and start containers
echo "🚀 Building and starting containers..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
else
    docker compose up -d --build
fi

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker-compose logs -f telegram-bot"
echo "  - Stop bot: docker-compose down"
echo "  - Restart bot: docker-compose restart telegram-bot"
echo "  - Check status: docker-compose ps"

# Show container status
echo ""
echo "📊 Container Status:"
if command -v docker-compose &> /dev/null; then
    docker-compose ps
else
    docker compose ps
fi