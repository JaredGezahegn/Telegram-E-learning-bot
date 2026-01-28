# 🚀 Quick Deployment Guide - Go Live in 15 Minutes

## Step 1: Set Up Supabase (5 minutes)

1. **Create account**: Go to [supabase.com](https://supabase.com) → Sign up with GitHub
2. **New project**: Click "New Project" → Choose name → Set password → Select region
3. **Get credentials**: Settings → API → Copy:
   - Project URL: `https://xxx.supabase.co`
   - anon/public key: `eyJhbGciOiJIUertyuizI1NiIsInR5cCI6IkpXVCJ9...`

4. **Create tables**: Go to SQL Editor → Paste this:

```sql
-- Create lessons table
CREATE TABLE lessons (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ,
    usage_count INTEGER DEFAULT 0
);

-- Create posting history table
CREATE TABLE posting_history (
    id BIGSERIAL PRIMARY KEY,
    lesson_id BIGINT REFERENCES lessons(id),
    message_id BIGINT NOT NULL,
    channel_id TEXT,
    posted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_lessons_category ON lessons(category);
CREATE INDEX idx_lessons_difficulty ON lessons(difficulty);
CREATE INDEX idx_lessons_usage_count ON lessons(usage_count);
```

5. **Load data**: Run locally:
```bash
export SUPABASE_URL="your-url"
export SUPABASE_ANON_KEY="your-key"
python setup_supabase.py
```

## Step 2: Deploy to Railway (10 minutes)

### Option A: Railway (Recommended)

1. **Connect GitHub**: [railway.app](https://railway.app) → Login → New Project → Deploy from GitHub
2. **Select repo**: Choose your bot repository
3. **Set environment variables**:
   ```
   BOT_TOKEN=8171475486:your bot token 
   CHANNEL_ID= your channel id
   DATABASE_TYPE=supabase
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_ANON_KEY= your supabase anon key...
   POSTING_TIME=any time you wanna
   TIMEZONE=UTC
   ```

4. **Deploy**: Railway will automatically build and deploy
5. **Check logs**: Ensure bot starts successfully

### Option B: Render

1. **New Web Service**: [render.com](https://render.com) → New → Web Service
2. **Connect repo**: Link your GitHub repository
3. **Settings**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python -m src.main`
4. **Environment Variables**: Same as Railway above

## Step 3: Verify Deployment

1. **Check logs**: Look for "Telegram English Bot started successfully"
2. **Test posting**: Bot should post at scheduled time (09:00 UTC)
3. **Monitor**: Check Supabase dashboard for data

## 🎉 You're Live!

Your bot is now running 24/7 with:
- ✅ Persistent Supabase database
- ✅ Automatic daily lesson posting
- ✅ Error handling and monitoring
- ✅ Clean message formatting

## Troubleshooting

**Bot not starting?**
- Check environment variables are set correctly
- Verify Supabase credentials
- Check Railway/Render logs

**No lessons posting?**
- Ensure lessons are loaded in Supabase
- Check timezone settings
- Verify bot permissions in Telegram channel

**Database errors?**
- Confirm tables were created in Supabase
- Check connection with test script
