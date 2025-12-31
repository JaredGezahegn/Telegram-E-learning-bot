# Deployment Guide

This document provides comprehensive instructions for deploying the Telegram English Bot on various platforms.

## Environment Variables

### Required Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` | Yes |
| `TELEGRAM_CHANNEL_ID` | Channel ID (with @) or numeric ID | `@english_learning_daily` or `-1001234567890` | Yes |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `POSTING_TIME` | Daily posting time (24h format) | `09:00` | `14:30` |
| `TIMEZONE` | Timezone for posting schedule | `UTC` | `America/New_York` |
| `DATABASE_PATH` | Path to SQLite database file | `lessons.db` | `/data/lessons.db` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `RETRY_ATTEMPTS` | Max retry attempts for failed posts | `3` | `5` |
| `RETRY_DELAY` | Initial retry delay in seconds | `60` | `120` |
| `RESOURCE_CHECK_INTERVAL` | Resource monitoring interval (seconds) | `300` | `600` |

### Platform-Specific Variables

#### Railway
- No additional variables required
- Uses automatic port detection

#### Render
- `PYTHON_VERSION`: Set to `3.11.0`
- `PYTHONPATH`: Set to `/opt/render/project/src`

#### Fly.io
- `PYTHONPATH`: Set to `/app`
- Uses internal networking

## Deployment Instructions

### Quick Start with Docker Compose

For the fastest local deployment:

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd telegram-english-bot

# 2. Configure environment
cp .env.example .env
# Edit .env with your bot token and channel ID

# 3. Deploy
./scripts/deploy-compose.sh  # Linux/macOS
# or
.\scripts\deploy-compose.ps1  # Windows PowerShell
```

### 1. Railway Deployment

1. **Prerequisites**
   - Railway account
   - GitHub repository with your bot code

2. **Deploy Steps**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login to Railway
   railway login
   
   # Deploy from current directory
   railway up
   
   # Set environment variables
   railway variables set TELEGRAM_BOT_TOKEN=your_token_here
   railway variables set TELEGRAM_CHANNEL_ID=@your_channel
   ```

3. **Configuration**
   - Railway automatically detects the `railway.toml` file
   - Uses Dockerfile for containerized deployment
   - Persistent storage included in free tier

### 2. Render Deployment

1. **Prerequisites**
   - Render account
   - GitHub repository connected to Render

2. **Deploy Steps**
   - Connect your GitHub repository to Render
   - Render will automatically detect `render.yaml`
   - Set environment variables in Render dashboard:
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHANNEL_ID`

3. **Configuration**
   - Uses web service type for persistent running
   - 1GB disk storage for database
   - Auto-deploy on git push

### 3. Fly.io Deployment

1. **Prerequisites**
   - Fly.io account
   - Fly CLI installed

2. **Deploy Steps**
   ```bash
   # Install Fly CLI
   curl -L https://fly.io/install.sh | sh
   
   # Login to Fly.io
   fly auth login
   
   # Launch app (uses fly.toml)
   fly launch
   
   # Set secrets
   fly secrets set TELEGRAM_BOT_TOKEN=your_token_here
   fly secrets set TELEGRAM_CHANNEL_ID=@your_channel
   
   # Deploy
   fly deploy
   ```

3. **Configuration**
   - Uses persistent volume for data storage
   - Auto-scaling with min 0 machines (cost-effective)
   - Health checks included

### 4. Docker Deployment (Self-hosted)

#### Option A: Docker Compose (Recommended)

1. **Setup Environment**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your bot credentials
   nano .env  # or use your preferred editor
   ```

2. **Deploy with Script**
   ```bash
   # Linux/macOS
   ./scripts/deploy-compose.sh
   
   # Windows PowerShell
   .\scripts\deploy-compose.ps1
   ```

3. **Manual Deployment**
   ```bash
   # Build and start
   docker-compose up -d --build
   
   # View logs
   docker-compose logs -f telegram-bot
   
   # Stop
   docker-compose down
   ```

#### Option B: Direct Docker

1. **Build Image**
   ```bash
   docker build -t telegram-english-bot .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     --name english-bot \
     --restart unless-stopped \
     -e TELEGRAM_BOT_TOKEN=your_token_here \
     -e TELEGRAM_CHANNEL_ID=@your_channel \
     -v bot_data:/app/data \
     telegram-english-bot
   ```

## Resource Requirements

### Free Tier Compatibility

| Platform | CPU | Memory | Storage | Network |
|----------|-----|--------|---------|---------|
| Railway | 0.5 vCPU | 512MB | 1GB | 100GB/month |
| Render | 0.1 CPU | 512MB | 1GB SSD | 100GB/month |
| Fly.io | 1 shared CPU | 256MB | 3GB volume | 160GB/month |

### Bot Resource Usage

- **CPU**: Very low, mostly idle except during daily posting
- **Memory**: ~50-100MB typical usage
- **Storage**: ~10-50MB for database and logs
- **Network**: Minimal, only Telegram API calls

## Monitoring and Maintenance

### Health Checks

All platforms include health check endpoints:
- **Path**: `/health` (if web server enabled)
- **Database**: SQLite connection test
- **Interval**: 30 seconds
- **Timeout**: 10 seconds

### Logs Access

#### Railway
```bash
railway logs
```

#### Render
- View logs in Render dashboard
- Real-time log streaming available

#### Fly.io
```bash
fly logs
```

### Database Backup

For production deployments, consider periodic database backups:

```bash
# Create backup
sqlite3 lessons.db ".backup backup_$(date +%Y%m%d).db"

# Restore backup
sqlite3 lessons.db ".restore backup_20231201.db"
```

## Troubleshooting

### Common Issues

1. **Bot Token Invalid**
   - Verify token from @BotFather
   - Ensure no extra spaces in environment variable

2. **Channel Access Denied**
   - Add bot as admin to channel
   - Verify channel ID format (@channel or -1001234567890)

3. **Database Locked**
   - Restart the application
   - Check file permissions in container

4. **Memory Limits**
   - Monitor resource usage
   - Consider upgrading to paid tier if needed

### Debug Mode

Enable debug logging:
```bash
# Set environment variable
LOG_LEVEL=DEBUG
```

### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f telegram-bot

# Stop services
docker-compose down

# Restart specific service
docker-compose restart telegram-bot

# Check service status
docker-compose ps

# Rebuild and restart
docker-compose up -d --build
```

### Support

For deployment issues:
1. Check platform-specific documentation
2. Review application logs
3. Verify environment variables
4. Test bot token with Telegram API directly

## Security Considerations

1. **Environment Variables**
   - Never commit tokens to version control
   - Use platform secret management
   - Rotate tokens periodically

2. **Container Security**
   - Runs as non-root user
   - Minimal base image
   - No unnecessary packages

3. **Network Security**
   - HTTPS-only communication
   - No exposed ports except health checks
   - Telegram API over TLS

## Cost Optimization

1. **Free Tier Usage**
   - All platforms offer sufficient free tier resources
   - Monitor usage to stay within limits
   - Use auto-scaling features

2. **Resource Efficiency**
   - Bot sleeps between scheduled posts
   - Minimal memory footprint
   - Efficient database queries

3. **Scaling Considerations**
   - Single instance sufficient for most use cases
   - Database can handle thousands of lessons
   - Network usage minimal