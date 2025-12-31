# Railway Deployment Script for Telegram English Bot (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Telegram English Bot to Railway..." -ForegroundColor Green

# Check if Railway CLI is installed
try {
    railway --version | Out-Null
} catch {
    Write-Host "❌ Railway CLI not found. Installing..." -ForegroundColor Red
    npm install -g @railway/cli
}

# Check if logged in
try {
    railway whoami | Out-Null
} catch {
    Write-Host "🔐 Please login to Railway..." -ForegroundColor Yellow
    railway login
}

# Deploy the application
Write-Host "📦 Deploying application..." -ForegroundColor Blue
railway up

Write-Host "⚙️  Setting up environment variables..." -ForegroundColor Blue

# Check if environment variables are provided
if (-not $env:TELEGRAM_BOT_TOKEN) {
    Write-Host "❌ TELEGRAM_BOT_TOKEN environment variable is required" -ForegroundColor Red
    Write-Host "Please set it before running this script:" -ForegroundColor Yellow
    Write-Host "`$env:TELEGRAM_BOT_TOKEN = 'your_token_here'" -ForegroundColor Yellow
    exit 1
}

if (-not $env:TELEGRAM_CHANNEL_ID) {
    Write-Host "❌ TELEGRAM_CHANNEL_ID environment variable is required" -ForegroundColor Red
    Write-Host "Please set it before running this script:" -ForegroundColor Yellow
    Write-Host "`$env:TELEGRAM_CHANNEL_ID = '@your_channel'" -ForegroundColor Yellow
    exit 1
}

# Set required environment variables
railway variables set TELEGRAM_BOT_TOKEN="$env:TELEGRAM_BOT_TOKEN"
railway variables set TELEGRAM_CHANNEL_ID="$env:TELEGRAM_CHANNEL_ID"

# Set optional environment variables if provided
if ($env:POSTING_TIME) {
    railway variables set POSTING_TIME="$env:POSTING_TIME"
}

if ($env:TIMEZONE) {
    railway variables set TIMEZONE="$env:TIMEZONE"
}

if ($env:LOG_LEVEL) {
    railway variables set LOG_LEVEL="$env:LOG_LEVEL"
}

Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host "🔗 Your bot should be running on Railway" -ForegroundColor Cyan
Write-Host "📊 Check logs with: railway logs" -ForegroundColor Yellow
Write-Host "⚙️  Manage variables with: railway variables" -ForegroundColor Yellow