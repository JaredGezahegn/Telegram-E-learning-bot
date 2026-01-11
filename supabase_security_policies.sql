-- Supabase Security Policies for Telegram English Bot
-- Copy and paste these commands into your Supabase SQL editor

-- First, ensure RLS is enabled on all tables
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_config ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON lessons;
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON posting_history;
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON bot_config;

-- LESSONS TABLE POLICIES
-- Allow public read access to lessons (for the bot to fetch lessons)
CREATE POLICY "Public read access to lessons" ON lessons
    FOR SELECT USING (true);

-- Allow service role to insert/update/delete lessons (for data management)
CREATE POLICY "Service role full access to lessons" ON lessons
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Allow authenticated users to update lesson usage statistics
CREATE POLICY "Authenticated users can update lesson usage" ON lessons
    FOR UPDATE USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- POSTING_HISTORY TABLE POLICIES
-- Allow public read access to posting history
CREATE POLICY "Public read access to posting history" ON posting_history
    FOR SELECT USING (true);

-- Allow service role full access to posting history
CREATE POLICY "Service role full access to posting history" ON posting_history
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Allow authenticated users to insert posting records
CREATE POLICY "Authenticated users can insert posting history" ON posting_history
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- BOT_CONFIG TABLE POLICIES
-- Allow public read access to bot config (for bot settings)
CREATE POLICY "Public read access to bot config" ON bot_config
    FOR SELECT USING (true);

-- Allow service role full access to bot config
CREATE POLICY "Service role full access to bot config" ON bot_config
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Allow authenticated users to update bot config
CREATE POLICY "Authenticated users can update bot config" ON bot_config
    FOR UPDATE USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- ALTERNATIVE: More restrictive policies (uncomment if you want stricter security)
-- These policies require authentication for all operations

/*
-- LESSONS TABLE - Authenticated only
CREATE POLICY "Authenticated read access to lessons" ON lessons
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated insert access to lessons" ON lessons
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated update access to lessons" ON lessons
    FOR UPDATE USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated delete access to lessons" ON lessons
    FOR DELETE USING (auth.role() = 'authenticated');

-- POSTING_HISTORY TABLE - Authenticated only
CREATE POLICY "Authenticated read access to posting history" ON posting_history
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated insert access to posting history" ON posting_history
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- BOT_CONFIG TABLE - Authenticated only
CREATE POLICY "Authenticated read access to bot config" ON bot_config
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated update access to bot config" ON bot_config
    FOR UPDATE USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');
*/

-- Grant necessary permissions to authenticated role
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant permissions to service role (for admin operations)
GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL sequences IN SCHEMA public TO service_role;

-- Create a function to check if user is service role (optional, for more complex policies)
CREATE OR REPLACE FUNCTION is_service_role()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN auth.jwt() ->> 'role' = 'service_role';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Verify the policies are created
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE schemaname = 'public' 
AND tablename IN ('lessons', 'posting_history', 'bot_config')
ORDER BY tablename, policyname;