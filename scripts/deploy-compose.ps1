# Docker Compose Deployment Script for Telegram English Bot (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🐳 Deploying Telegram English Bot with Docker Compose..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker not found. Please install Docker first." -ForegroundColor Red
    exit 1
}

$composeCommand = $null
try {
    docker-compose --version | Out-Null
    $composeCommand = "docker-compose"
} catch {
    try {
        docker compose version | Out-Null
        $composeCommand = "docker compose"
    } catch {
        Write-Host "❌ Docker Compose not found. Please install Docker Compose first." -ForegroundColor Red
        exit 1
    }
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found. Please create it from .env.example" -ForegroundColor Red
    Write-Host "Copy-Item .env.example .env" -ForegroundColor Yellow
    Write-Host "Then edit .env with your bot token and channel ID" -ForegroundColor Yellow
    exit 1
}

# Check if environment variables are set in .env
$envContent = Get-Content ".env" -Raw
if (-not ($envContent -match "TELEGRAM_BOT_TOKEN=") -or -not ($envContent -match "TELEGRAM_CHANNEL_ID=")) {
    Write-Host "❌ Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID in .env file" -ForegroundColor Red
    exit 1
}

# Stop existing containers
Write-Host "🛑 Stopping existing containers..." -ForegroundColor Yellow
try {
    if ($composeCommand -eq "docker-compose") {
        docker-compose down
    } else {
        docker compose down
    }
} catch {
    # Ignore errors if no containers are running
}

# Build and start containers
Write-Host "🚀 Building and starting containers..." -ForegroundColor Blue
if ($composeCommand -eq "docker-compose") {
    docker-compose up -d --build
} else {
    docker compose up -d --build
}

Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
if ($composeCommand -eq "docker-compose") {
    Write-Host "  - View logs: docker-compose logs -f telegram-bot" -ForegroundColor Yellow
    Write-Host "  - Stop bot: docker-compose down" -ForegroundColor Yellow
    Write-Host "  - Restart bot: docker-compose restart telegram-bot" -ForegroundColor Yellow
    Write-Host "  - Check status: docker-compose ps" -ForegroundColor Yellow
} else {
    Write-Host "  - View logs: docker compose logs -f telegram-bot" -ForegroundColor Yellow
    Write-Host "  - Stop bot: docker compose down" -ForegroundColor Yellow
    Write-Host "  - Restart bot: docker compose restart telegram-bot" -ForegroundColor Yellow
    Write-Host "  - Check status: docker compose ps" -ForegroundColor Yellow
}

# Show container status
Write-Host ""
Write-Host "📊 Container Status:" -ForegroundColor Cyan
if ($composeCommand -eq "docker-compose") {
    docker-compose ps
} else {
    docker compose ps
}