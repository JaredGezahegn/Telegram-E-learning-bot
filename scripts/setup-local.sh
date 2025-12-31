#!/bin/bash

# Local Development Setup Script for Telegram English Bot

set -e

echo "🔧 Setting up Telegram English Bot for local development..."

# Check if Python 3.11+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your bot token and channel ID"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs data

# Initialize database with seed data
echo "🗄️  Initializing database..."
python data/load_seed_data.py

# Run tests to verify setup
echo "🧪 Running tests to verify setup..."
python -m pytest tests/ -v

echo "✅ Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your bot token and channel ID"
echo "2. Run the bot: python run_bot.py"
echo "3. Or run tests: python -m pytest"
echo ""
echo "🔗 Useful commands:"
echo "  - Activate venv: source venv/bin/activate"
echo "  - Run bot: python run_bot.py"
echo "  - Run tests: python -m pytest"
echo "  - View logs: tail -f logs/telegram_bot.log"