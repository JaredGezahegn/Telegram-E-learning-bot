# Local Development Setup Script for Telegram English Bot (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🔧 Setting up Telegram English Bot for local development..." -ForegroundColor Green

# Check if Python 3.11+ is installed
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+\.\d+)") {
        $version = [version]$matches[1]
        $requiredVersion = [version]"3.11"
        
        if ($version -lt $requiredVersion) {
            Write-Host "❌ Python 3.11+ required. Found: $($matches[1])" -ForegroundColor Red
            exit 1
        }
    } else {
        throw "Python version not detected"
    }
} catch {
    Write-Host "❌ Python 3 not found. Please install Python 3.11 or later." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "🐍 Creating virtual environment..." -ForegroundColor Blue
    python -m venv venv
}

# Activate virtual environment
Write-Host "🔄 Activating virtual environment..." -ForegroundColor Blue
& "venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "⬆️  Upgrading pip..." -ForegroundColor Blue
python -m pip install --upgrade pip

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Blue
pip install -r requirements.txt

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Blue
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please edit .env file with your bot token and channel ID" -ForegroundColor Yellow
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "logs", "data" | Out-Null

# Initialize database with seed data
Write-Host "🗄️  Initializing database..." -ForegroundColor Blue
python data/load_seed_data.py

# Run tests to verify setup
Write-Host "🧪 Running tests to verify setup..." -ForegroundColor Blue
python -m pytest tests/ -v

Write-Host "✅ Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file with your bot token and channel ID" -ForegroundColor Yellow
Write-Host "2. Run the bot: python run_bot.py" -ForegroundColor Yellow
Write-Host "3. Or run tests: python -m pytest" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔗 Useful commands:" -ForegroundColor Cyan
Write-Host "  - Activate venv: venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  - Run bot: python run_bot.py" -ForegroundColor Yellow
Write-Host "  - Run tests: python -m pytest" -ForegroundColor Yellow
Write-Host "  - View logs: Get-Content logs/telegram_bot.log -Wait" -ForegroundColor Yellow