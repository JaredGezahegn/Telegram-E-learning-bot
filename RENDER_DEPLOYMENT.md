# Render Deployment Guide

This guide will help you deploy your Telegram English Bot to Render using Supabase as the database.

## Prerequisites

✅ **Completed Setup:**
- [x] Supabase database created and configured
- [x] Lessons loaded into Supabase (51 lessons)
- [x] Bot token from @BotFather
- [x] Telegram channel created

## Step 1: Prepare Your Repository

Make sure your repository is pushed to GitHub with the latest changes:

```bash
git add .
git commit -m "Configure for Render deployment with Supabase"
git push origin main
```

## Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Authorize Render to access your repositories

## Step 3: Deploy to Render

### Option A: Automatic Deployment (Recommended)

1. **Connect Repository**
   - In Render dashboard, click "New +"
   - Select "Web Service"
   - Connect your GitHub repository
   - Select the `telegram-english-bot` repository

2. **Configure Service**
   - **Name**: `telegram-english-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python src/main.py`
   - **Plan**: `Free` (sufficient for this bot)

3. **Set Environment Variables**
   Click "Environment" and add these variables:

   ```env
   # Bot Configuration
   BOT_TOKEN=your_telegram_bot_token_here
   CHANNEL_ID=your_channel_id_here

   # Database Configuration
   DATABASE_TYPE=supabase
   SUPABASE_URL=https://wdyhnatddirxgqtdazge.supabase.co
   SUPABASE_ANON_KEY=your_supabase_anon_key_here

   # Scheduling Configuration
   POSTING_TIME=09:00
   TIMEZONE=UTC

   # Quiz Configuration
   ENABLE_QUIZZES=true
   QUIZ_DELAY_MINUTES=5

   # Logging Configuration
   LOG_LEVEL=INFO

   # Python Configuration
   PYTHON_VERSION=3.11.0
   PYTHONPATH=/opt/render/project/src
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your bot
   - Wait for the build to complete (usually 2-3 minutes)

### Option B: Using render.yaml (Alternative)

If you prefer using the configuration file:

1. Your repository already has `render.yaml` configured
2. In Render dashboard, select "Blueprint"
3. Connect your repository
4. Render will read the `render.yaml` file automatically
5. Add the environment variables as shown above

## Step 4: Verify Deployment

### Check Build Logs

1. In Render dashboard, go to your service
2. Click on "Logs" tab
3. Look for successful startup messages:
   ```
   ✅ Connected to Supabase
   ✅ Bot started successfully
   📚 Loaded 51 lessons from database
   ⏰ Scheduler started
   ```

### Test Bot Functionality

1. **Manual Test**: Send a test message to your channel
2. **Check Logs**: Monitor logs for any errors
3. **Database Connection**: Verify Supabase connection in logs

## Step 5: Configure Auto-Deploy

1. In your service settings, enable "Auto-Deploy"
2. Select branch: `main`
3. Now every push to main will automatically redeploy

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | `1234567890:ABC...` |
| `CHANNEL_ID` | Your Telegram channel ID | `@your_channel` or `-1001234567890` |
| `SUPABASE_URL` | Your Supabase project URL | `https://abc.supabase.co` |
| `SUPABASE_ANON_KEY` | Your Supabase anon key | `eyJhbGciOiJIUzI1NiIs...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTING_TIME` | `09:00` | Daily posting time (24h format) |
| `TIMEZONE` | `UTC` | Timezone for scheduling |
| `ENABLE_QUIZZES` | `true` | Enable quiz generation |
| `QUIZ_DELAY_MINUTES` | `5` | Minutes between lesson and quiz |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Monitoring and Maintenance

### View Logs

1. Go to your service in Render dashboard
2. Click "Logs" tab
3. Use filters to find specific log levels or time ranges

### Health Monitoring

- Render automatically monitors your service health
- If the service crashes, Render will restart it automatically
- You'll receive email notifications for deployment failures

### Resource Usage

- **Free Tier Limits**: 750 hours/month (sufficient for 24/7 operation)
- **Memory**: 512MB (your bot uses ~50-100MB)
- **CPU**: Shared CPU (sufficient for scheduled posting)
- **Bandwidth**: 100GB/month (more than enough)

## Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check requirements.txt for correct versions
   # Ensure all dependencies are listed
   ```

2. **Environment Variable Issues**
   ```bash
   # Verify all required variables are set
   # Check for typos in variable names
   # Ensure no extra spaces in values
   ```

3. **Database Connection Issues**
   ```bash
   # Verify Supabase URL and key
   # Check Supabase service status
   # Review connection logs
   ```

4. **Bot Token Issues**
   ```bash
   # Verify token from @BotFather
   # Ensure bot is added to channel as admin
   # Check channel ID format
   ```

### Debug Mode

To enable debug logging, set:
```env
LOG_LEVEL=DEBUG
```

### Manual Restart

1. Go to your service in Render dashboard
2. Click "Manual Deploy" → "Deploy latest commit"
3. Or use the "Restart" button

## Cost and Scaling

### Free Tier Benefits

- **750 hours/month**: Enough for 24/7 operation
- **Automatic SSL**: HTTPS enabled by default
- **Custom domains**: Available on free tier
- **GitHub integration**: Auto-deploy on push

### Upgrading (If Needed)

- **Starter Plan ($7/month)**: More resources and priority support
- **Professional Plan ($25/month)**: Enhanced performance and features

## Security Best Practices

1. **Environment Variables**: Never commit secrets to Git
2. **Token Rotation**: Regularly rotate bot tokens
3. **Access Control**: Limit repository access
4. **Monitoring**: Enable deployment notifications

## Support and Resources

- **Render Documentation**: [docs.render.com](https://docs.render.com)
- **Render Community**: [community.render.com](https://community.render.com)
- **Status Page**: [status.render.com](https://status.render.com)

## Next Steps

After successful deployment:

1. **Test Daily Posting**: Wait for scheduled post time
2. **Monitor Performance**: Check logs regularly for first few days
3. **Set Up Alerts**: Configure email notifications
4. **Backup Strategy**: Consider periodic Supabase backups

Your Telegram English Bot is now running on Render with Supabase! 🎉

## Quick Commands

```bash
# View service status
curl https://your-service-name.onrender.com/health

# Check recent logs (if you have Render CLI)
render logs --service your-service-name

# Manual deploy
render deploy --service your-service-name
```