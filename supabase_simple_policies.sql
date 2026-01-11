-- Simple Supabase Security Policies for Telegram English Bot
-- Use this if you want simpler, more open access for your bot

-- Enable RLS on all tables
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_config ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON lessons;
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON posting_history;
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON bot_config;

-- Simple policies: Allow all operations for anyone with a valid API key
-- This is suitable for a bot application where you control all access

-- LESSONS TABLE - Allow all operations
CREATE POLICY "Allow all operations on lessons" ON lessons
    FOR ALL USING (true)
    WITH CHECK (true);

-- POSTING_HISTORY TABLE - Allow all operations  
CREATE POLICY "Allow all operations on posting_history" ON posting_history
    FOR ALL USING (true)
    WITH CHECK (true);

-- BOT_CONFIG TABLE - Allow all operations
CREATE POLICY "Allow all operations on bot_config" ON bot_config
    FOR ALL USING (true)
    WITH CHECK (true);

-- Grant permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- Verify policies
SELECT tablename, policyname, cmd 
FROM pg_policies 
WHERE schemaname = 'public' 
AND tablename IN ('lessons', 'posting_history', 'bot_config');