#!/bin/bash

# Deployment Verification Script for Telegram English Bot

set -e

echo "🔍 Verifying Telegram English Bot deployment..."

# Function to check if a URL is accessible
check_url() {
    local url=$1
    local name=$2
    
    if curl -s -f "$url" > /dev/null; then
        echo "✅ $name is accessible"
        return 0
    else
        echo "❌ $name is not accessible"
        return 1
    fi
}

# Function to check environment variables
check_env_vars() {
    local missing_vars=()
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        missing_vars+=("TELEGRAM_BOT_TOKEN")
    fi
    
    if [ -z "$TELEGRAM_CHANNEL_ID" ]; then
        missing_vars+=("TELEGRAM_CHANNEL_ID")
    fi
    
    if [ ${#missing_vars[@]} -eq 0 ]; then
        echo "✅ Required environment variables are set"
        return 0
    else
        echo "❌ Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
}

# Function to test bot token validity
test_bot_token() {
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo "⚠️  Skipping bot token test (token not provided)"
        return 0
    fi
    
    echo "🤖 Testing bot token validity..."
    
    local response=$(curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe")
    
    if echo "$response" | grep -q '"ok":true'; then
        local bot_name=$(echo "$response" | grep -o '"first_name":"[^"]*"' | cut -d'"' -f4)
        echo "✅ Bot token is valid (Bot: $bot_name)"
        return 0
    else
        echo "❌ Bot token is invalid or bot is not accessible"
        echo "Response: $response"
        return 1
    fi
}

# Function to check database
check_database() {
    if [ -f "lessons.db" ]; then
        local lesson_count=$(sqlite3 lessons.db "SELECT COUNT(*) FROM lessons;" 2>/dev/null || echo "0")
        if [ "$lesson_count" -gt 0 ]; then
            echo "✅ Database exists with $lesson_count lessons"
            return 0
        else
            echo "⚠️  Database exists but has no lessons"
            return 1
        fi
    else
        echo "⚠️  Database file not found (will be created on first run)"
        return 0
    fi
}

# Function to check Python dependencies
check_dependencies() {
    echo "📦 Checking Python dependencies..."
    
    if python -c "import telegram, apscheduler, sqlite3, hypothesis" 2>/dev/null; then
        echo "✅ All required Python packages are installed"
        return 0
    else
        echo "❌ Some required Python packages are missing"
        echo "Run: pip install -r requirements.txt"
        return 1
    fi
}

# Function to run basic tests
run_tests() {
    echo "🧪 Running basic tests..."
    
    if python -m pytest tests/ -x -q --tb=no 2>/dev/null; then
        echo "✅ Basic tests passed"
        return 0
    else
        echo "⚠️  Some tests failed (check with: python -m pytest tests/ -v)"
        return 1
    fi
}

# Main verification process
main() {
    local errors=0
    
    echo "🔍 Starting deployment verification..."
    echo ""
    
    # Check environment variables
    if ! check_env_vars; then
        ((errors++))
    fi
    
    # Test bot token if available
    if ! test_bot_token; then
        ((errors++))
    fi
    
    # Check dependencies
    if ! check_dependencies; then
        ((errors++))
    fi
    
    # Check database
    if ! check_database; then
        ((errors++))
    fi
    
    # Run tests
    if ! run_tests; then
        ((errors++))
    fi
    
    echo ""
    
    if [ $errors -eq 0 ]; then
        echo "🎉 Deployment verification completed successfully!"
        echo "✅ Your bot should be ready to run"
        echo ""
        echo "📋 Next steps:"
        echo "  - Start the bot: python run_bot.py"
        echo "  - Monitor logs: tail -f logs/telegram_bot.log"
        echo "  - Check health: curl http://localhost:8000/health"
        return 0
    else
        echo "⚠️  Deployment verification completed with $errors issue(s)"
        echo "❌ Please fix the issues above before running the bot"
        return 1
    fi
}

# Run main function
main "$@"