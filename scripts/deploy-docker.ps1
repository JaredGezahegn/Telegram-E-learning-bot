# Docker Deployment Script for Telegram English Bot (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🐳 Building and running Telegram English Bot with Docker..." -ForegroundColor Green

# Check if Docker is installed and running
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker not found. Please install Docker first." -ForegroundColor Red
    exit 1
}

try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker daemon not running. Please start Docker." -ForegroundColor Red
    exit 1
}

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

# Build the Docker image
Write-Host "🔨 Building Docker image..." -ForegroundColor Blue
docker build -t telegram-english-bot .

# Stop and remove existing container if it exists
$existingContainer = docker ps -a --filter name=english-bot --format "{{.Names}}"
if ($existingContainer -eq "english-bot") {
    Write-Host "🛑 Stopping existing container..." -ForegroundColor Yellow
    docker stop english-bot
    docker rm english-bot
}

# Create volume for persistent data
Write-Host "💾 Creating data volume..." -ForegroundColor Blue
docker volume create bot_data

# Prepare environment variables
$envVars = @(
    "-e", "TELEGRAM_BOT_TOKEN=$env:TELEGRAM_BOT_TOKEN",
    "-e", "TELEGRAM_CHANNEL_ID=$env:TELEGRAM_CHANNEL_ID"
)

if ($env:POSTING_TIME) {
    $envVars += "-e", "POSTING_TIME=$env:POSTING_TIME"
}

if ($env:TIMEZONE) {
    $envVars += "-e", "TIMEZONE=$env:TIMEZONE"
}

if ($env:LOG_LEVEL) {
    $envVars += "-e", "LOG_LEVEL=$env:LOG_LEVEL"
}

if ($env:RETRY_ATTEMPTS) {
    $envVars += "-e", "RETRY_ATTEMPTS=$env:RETRY_ATTEMPTS"
}

if ($env:RETRY_DELAY) {
    $envVars += "-e", "RETRY_DELAY=$env:RETRY_DELAY"
}

# Run the container
Write-Host "🚀 Starting container..." -ForegroundColor Blue
$dockerArgs = @(
    "run", "-d",
    "--name", "english-bot",
    "--restart", "unless-stopped"
) + $envVars + @(
    "-v", "bot_data:/app/data",
    "telegram-english-bot"
)

& docker @dockerArgs

Write-Host "✅ Container started successfully!" -ForegroundColor Green
Write-Host "📊 Check logs with: docker logs english-bot" -ForegroundColor Yellow
Write-Host "📱 Check status with: docker ps" -ForegroundColor Yellow
Write-Host "🛑 Stop container with: docker stop english-bot" -ForegroundColor Yellow

# Show container status
Write-Host ""
Write-Host "📋 Container Status:" -ForegroundColor Cyan
docker ps --filter name=english-bot --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"

# Show recent logs
Write-Host ""
Write-Host "📊 Recent Logs:" -ForegroundColor Cyan
docker logs --tail 20 english-bot