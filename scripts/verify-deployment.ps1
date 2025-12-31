# Deployment Verification Script for Telegram English Bot (PowerShell)

$ErrorActionPreference = "Continue"

Write-Host "🔍 Verifying Telegram English Bot deployment..." -ForegroundColor Green

# Function to check environment variables
function Test-EnvironmentVariables {
    $missingVars = @()
    
    if (-not $env:TELEGRAM_BOT_TOKEN) {
        $missingVars += "TELEGRAM_BOT_TOKEN"
    }
    
    if (-not $env:TELEGRAM_CHANNEL_ID) {
        $missingVars += "TELEGRAM_CHANNEL_ID"
    }
    
    if ($missingVars.Count -eq 0) {
        Write-Host "✅ Required environment variables are set" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ Missing required environment variables: $($missingVars -join ', ')" -ForegroundColor Red
        return $false
    }
}

# Function to test bot token validity
function Test-BotToken {
    if (-not $env:TELEGRAM_BOT_TOKEN) {
        Write-Host "⚠️  Skipping bot token test (token not provided)" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "🤖 Testing bot token validity..." -ForegroundColor Blue
    
    try {
        $response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/getMe" -Method Get
        
        if ($response.ok) {
            Write-Host "✅ Bot token is valid (Bot: $($response.result.first_name))" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Bot token is invalid or bot is not accessible" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Error testing bot token: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to check database
function Test-Database {
    if (Test-Path "lessons.db") {
        try {
            $connection = New-Object System.Data.SQLite.SQLiteConnection("Data Source=lessons.db")
            $connection.Open()
            $command = $connection.CreateCommand()
            $command.CommandText = "SELECT COUNT(*) FROM lessons"
            $lessonCount = $command.ExecuteScalar()
            $connection.Close()
            
            if ($lessonCount -gt 0) {
                Write-Host "✅ Database exists with $lessonCount lessons" -ForegroundColor Green
                return $true
            } else {
                Write-Host "⚠️  Database exists but has no lessons" -ForegroundColor Yellow
                return $false
            }
        } catch {
            Write-Host "⚠️  Database file exists but cannot be read" -ForegroundColor Yellow
            return $false
        }
    } else {
        Write-Host "⚠️  Database file not found (will be created on first run)" -ForegroundColor Yellow
        return $true
    }
}

# Function to check Python dependencies
function Test-Dependencies {
    Write-Host "📦 Checking Python dependencies..." -ForegroundColor Blue
    
    try {
        $result = python -c "import telegram, apscheduler, sqlite3, hypothesis; print('OK')" 2>$null
        if ($result -eq "OK") {
            Write-Host "✅ All required Python packages are installed" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Some required Python packages are missing" -ForegroundColor Red
            Write-Host "Run: pip install -r requirements.txt" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "❌ Error checking dependencies: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to run basic tests
function Test-BasicTests {
    Write-Host "🧪 Running basic tests..." -ForegroundColor Blue
    
    try {
        $result = python -m pytest tests/ -x -q --tb=no 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Basic tests passed" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠️  Some tests failed (check with: python -m pytest tests/ -v)" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "⚠️  Error running tests: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

# Main verification process
function Main {
    $errors = 0
    
    Write-Host "🔍 Starting deployment verification..." -ForegroundColor Cyan
    Write-Host ""
    
    # Check environment variables
    if (-not (Test-EnvironmentVariables)) {
        $errors++
    }
    
    # Test bot token if available
    if (-not (Test-BotToken)) {
        $errors++
    }
    
    # Check dependencies
    if (-not (Test-Dependencies)) {
        $errors++
    }
    
    # Check database
    if (-not (Test-Database)) {
        $errors++
    }
    
    # Run tests
    if (-not (Test-BasicTests)) {
        $errors++
    }
    
    Write-Host ""
    
    if ($errors -eq 0) {
        Write-Host "🎉 Deployment verification completed successfully!" -ForegroundColor Green
        Write-Host "✅ Your bot should be ready to run" -ForegroundColor Green
        Write-Host ""
        Write-Host "📋 Next steps:" -ForegroundColor Cyan
        Write-Host "  - Start the bot: python run_bot.py" -ForegroundColor Yellow
        Write-Host "  - Monitor logs: Get-Content logs/telegram_bot.log -Wait" -ForegroundColor Yellow
        Write-Host "  - Check health: Invoke-RestMethod http://localhost:8000/health" -ForegroundColor Yellow
        return 0
    } else {
        Write-Host "⚠️  Deployment verification completed with $errors issue(s)" -ForegroundColor Yellow
        Write-Host "❌ Please fix the issues above before running the bot" -ForegroundColor Red
        return 1
    }
}

# Run main function
Main