#!/usr/bin/env python3
"""Setup script for Supabase integration."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()


def create_supabase_tables_sql():
    """Generate SQL for creating Supabase tables."""
    
    sql_commands = """
-- Create lessons table
CREATE TABLE IF NOT EXISTS lessons (
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

-- Create indexes for lessons
CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category);
CREATE INDEX IF NOT EXISTS idx_lessons_difficulty ON lessons(difficulty);
CREATE INDEX IF NOT EXISTS idx_lessons_last_used ON lessons(last_used);
CREATE INDEX IF NOT EXISTS idx_lessons_usage_count ON lessons(usage_count);
CREATE INDEX IF NOT EXISTS idx_lessons_tags ON lessons USING GIN(tags);

-- Create posting_history table
CREATE TABLE IF NOT EXISTS posting_history (
    id BIGSERIAL PRIMARY KEY,
    lesson_id BIGINT REFERENCES lessons(id) ON DELETE CASCADE,
    message_id BIGINT NOT NULL,
    channel_id TEXT,
    posted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for posting_history
CREATE INDEX IF NOT EXISTS idx_posting_history_lesson_id ON posting_history(lesson_id);
CREATE INDEX IF NOT EXISTS idx_posting_history_posted_at ON posting_history(posted_at);
CREATE INDEX IF NOT EXISTS idx_posting_history_channel_id ON posting_history(channel_id);

-- Create bot_config table
CREATE TABLE IF NOT EXISTS bot_config (
    id BIGSERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for bot_config
CREATE INDEX IF NOT EXISTS idx_bot_config_key ON bot_config(key);

-- Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_config ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your security needs)
-- These policies allow all operations for authenticated users
CREATE POLICY IF NOT EXISTS "Allow all operations for authenticated users" ON lessons
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY IF NOT EXISTS "Allow all operations for authenticated users" ON posting_history
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY IF NOT EXISTS "Allow all operations for authenticated users" ON bot_config
    FOR ALL USING (auth.role() = 'authenticated');
"""
    
    return sql_commands


def load_lessons_to_supabase():
    """Load seed lessons into Supabase."""
    try:
        from models.supabase_database import create_supabase_manager
        from data.load_seed_data import load_seed_lessons
        
        print("🔄 Loading lessons into Supabase...")
        
        # Create Supabase manager
        db_manager = create_supabase_manager()
        
        # Test connection
        if not db_manager.test_connection():
            print("❌ Failed to connect to Supabase")
            return False
        
        print("✅ Connected to Supabase")
        
        # Load lessons from JSON
        lessons = load_seed_lessons()
        print(f"📚 Loaded {len(lessons)} lessons from JSON")
        
        # Insert lessons
        success_count = 0
        for lesson in lessons:
            lesson_id = db_manager.create_lesson(lesson)
            if lesson_id:
                success_count += 1
            else:
                print(f"⚠️  Failed to insert lesson: {lesson.title}")
        
        print(f"✅ Successfully inserted {success_count}/{len(lessons)} lessons")
        
        # Verify
        all_lessons = db_manager.get_all_lessons()
        print(f"✅ Supabase now contains {len(all_lessons)} lessons")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading lessons to Supabase: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Supabase Setup for Telegram English Bot")
    print("=" * 50)
    
    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials!")
        print("\nPlease set the following environment variables:")
        print("- SUPABASE_URL: Your Supabase project URL")
        print("- SUPABASE_ANON_KEY: Your Supabase anon/public key")
        print("\nYou can find these in your Supabase project dashboard under Settings > API")
        return 1
    
    print("✅ Supabase credentials found")
    print(f"   URL: {supabase_url}")
    print(f"   Key: {supabase_key[:20]}...")
    
    # Generate SQL
    print("\n📝 SQL Commands for Supabase:")
    print("Copy and paste these commands into your Supabase SQL editor:")
    print("-" * 60)
    print(create_supabase_tables_sql())
    print("-" * 60)
    
    # Ask if user wants to load data
    print("\n📊 After creating the tables in Supabase, you can load the seed data.")
    response = input("Do you want to load seed lessons into Supabase now? (y/N): ").strip().lower()
    
    if response == 'y':
        if load_lessons_to_supabase():
            print("\n🎉 Supabase setup completed successfully!")
            print("\nTo use Supabase in production, set:")
            print("DATABASE_TYPE=supabase")
        else:
            print("\n❌ Failed to load lessons. Please check your Supabase setup.")
            return 1
    else:
        print("\n✅ Setup completed. Remember to:")
        print("1. Create the tables in Supabase using the SQL above")
        print("2. Load your lesson data")
        print("3. Set DATABASE_TYPE=supabase in your environment")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())