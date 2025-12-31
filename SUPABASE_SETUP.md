# Supabase Setup Guide for Telegram English Bot

This guide will help you set up Supabase as your production database for the Telegram English Bot.

## Why Supabase?

- ✅ **PostgreSQL-based** - Robust and scalable
- ✅ **Free tier** - 500MB database, 2GB bandwidth
- ✅ **Real-time features** - Built-in subscriptions
- ✅ **Easy deployment** - No server management
- ✅ **Dashboard** - Visual database management

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up/Login with GitHub
3. Click "New Project"
4. Choose organization and project name
5. Set a strong database password
6. Select region (choose closest to your users)
7. Wait for project creation (~2 minutes)

## Step 2: Get Your Credentials

1. In your Supabase dashboard, go to **Settings > API**
2. Copy these values:
   - **Project URL** (e.g., `https://abcdefgh.supabase.co`)
   - **anon/public key** (starts with `eyJ...`)

## Step 3: Install Dependencies

```bash
pip install supabase==2.3.4
```

## Step 4: Set Environment Variables

Add to your `.env` file or deployment environment:

```env
# Database Configuration
DATABASE_TYPE=supabase

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Step 5: Create Database Tables

1. In Supabase dashboard, go to **SQL Editor**
2. Run the setup script to get the SQL commands:

```bash
python setup_supabase.py
```

3. Copy the generated SQL and paste it into the SQL Editor
4. Click "Run" to create all tables

### Manual Table Creation (Alternative)

If you prefer to create tables manually:

#### Lessons Table
```sql
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
```

#### Posting History Table
```sql
CREATE TABLE posting_history (
    id BIGSERIAL PRIMARY KEY,
    lesson_id BIGINT REFERENCES lessons(id) ON DELETE CASCADE,
    message_id BIGINT NOT NULL,
    channel_id TEXT,
    posted_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Step 6: Load Seed Data

Run the setup script to load your lessons:

```bash
# Set environment variables first
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"

# Run setup
python setup_supabase.py
```

## Step 7: Test Connection

Create a test script:

```python
import os
from src.services.database_factory import create_lesson_repository, get_database_info

# Set environment
os.environ['DATABASE_TYPE'] = 'supabase'
os.environ['SUPABASE_URL'] = 'your-url'
os.environ['SUPABASE_ANON_KEY'] = 'your-key'

# Test
repo = create_lesson_repository()
lessons = repo.get_all_lessons()
print(f"Found {len(lessons)} lessons in Supabase")

# Get database info
info = get_database_info()
print("Database info:", info)
```

## Deployment Configurations

### Railway
```env
DATABASE_TYPE=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
BOT_TOKEN=your-telegram-bot-token
CHANNEL_ID=your-channel-id
```

### Heroku
```bash
heroku config:set DATABASE_TYPE=supabase
heroku config:set SUPABASE_URL=https://your-project.supabase.co
heroku config:set SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Docker
```dockerfile
ENV DATABASE_TYPE=supabase
ENV SUPABASE_URL=https://your-project.supabase.co
ENV SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Security Considerations

### Row Level Security (RLS)
The setup script enables RLS by default. For production:

1. **Review policies** in Supabase dashboard under Authentication > Policies
2. **Customize access** based on your needs
3. **Use service role key** for server-side operations if needed

### API Keys
- **anon/public key**: Safe for client-side use
- **service_role key**: Server-side only, full database access

## Monitoring and Maintenance

### Dashboard Features
- **Table Editor**: View and edit data
- **SQL Editor**: Run custom queries  
- **Logs**: Monitor database activity
- **Usage**: Track storage and bandwidth

### Backup Strategy
- Supabase automatically backs up your database
- For additional safety, export data regularly:

```sql
-- Export lessons
SELECT * FROM lessons;

-- Export posting history  
SELECT * FROM posting_history;
```

## Troubleshooting

### Connection Issues
```python
# Test connection
from src.models.supabase_database import create_supabase_manager

db = create_supabase_manager()
if db.test_connection():
    print("✅ Connected to Supabase")
else:
    print("❌ Connection failed")
```

### Common Errors

1. **Invalid credentials**: Check URL and key
2. **Table not found**: Run the SQL setup commands
3. **Permission denied**: Check RLS policies
4. **Rate limiting**: Upgrade plan or optimize queries

### Migration from SQLite

```python
# Export from SQLite
from src.services.lesson_repository import LessonRepository
sqlite_repo = LessonRepository("lessons.db")
lessons = sqlite_repo.get_all_lessons()

# Import to Supabase
from src.services.supabase_lesson_repository import SupabaseLessonRepository
supabase_repo = SupabaseLessonRepository()
for lesson in lessons:
    supabase_repo.create_lesson(lesson)
```

## Cost Estimation

### Free Tier Limits
- **Database**: 500MB
- **Bandwidth**: 2GB/month
- **API requests**: 50,000/month

### Typical Usage (English Bot)
- **~50 lessons**: ~1MB storage
- **Daily posts**: ~30KB/day bandwidth
- **Monthly**: ~1MB bandwidth

**Result**: Free tier is more than sufficient! 🎉

## Support

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Discord](https://discord.supabase.com)
- [GitHub Issues](https://github.com/supabase/supabase/issues)