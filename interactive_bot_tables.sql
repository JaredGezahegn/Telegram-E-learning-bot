-- Interactive Telegram Bot Database Tables
-- Add these tables to your Supabase database for interactive features

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    chat_id BIGINT,
    registration_date TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    total_lessons_completed INTEGER DEFAULT 0,
    total_quizzes_taken INTEGER DEFAULT 0,
    average_quiz_score DECIMAL(5,2) DEFAULT 0.0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    preferred_difficulty TEXT,
    preferred_topics JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User progress tracking table
CREATE TABLE IF NOT EXISTS user_progress (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    activity_type TEXT NOT NULL, -- 'lesson', 'quiz', 'practice'
    content_id INTEGER NOT NULL,
    content_title TEXT NOT NULL,
    completion_timestamp TIMESTAMPTZ DEFAULT NOW(),
    score DECIMAL(5,2), -- For quizzes (0.0 to 100.0)
    time_spent INTEGER, -- In seconds
    difficulty_level TEXT,
    topic_category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

-- Quiz attempts table
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    quiz_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
    attempt_number INTEGER DEFAULT 1,
    score DECIMAL(5,2) DEFAULT 0.0,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    time_taken INTEGER DEFAULT 0, -- In seconds
    is_practice_mode BOOLEAN DEFAULT false,
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    answers JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- User sessions table for multi-step interactions
CREATE TABLE IF NOT EXISTS user_sessions (
    user_id BIGINT PRIMARY KEY,
    session_type TEXT NOT NULL, -- 'quiz', 'browse', 'practice'
    session_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 minutes'),
    is_active BOOLEAN DEFAULT true,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

-- Admin action logs table
CREATE TABLE IF NOT EXISTS admin_action_logs (
    id SERIAL PRIMARY KEY,
    admin_user_id BIGINT NOT NULL,
    admin_username TEXT,
    action_type TEXT NOT NULL,
    action_details TEXT NOT NULL,
    target_user_id BIGINT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (target_user_id) REFERENCES user_profiles(user_id) ON DELETE SET NULL
);

-- Command usage statistics table
CREATE TABLE IF NOT EXISTS command_usage_stats (
    id SERIAL PRIMARY KEY,
    command_name TEXT NOT NULL,
    user_id BIGINT NOT NULL,
    chat_type TEXT NOT NULL, -- 'private', 'group', 'channel'
    execution_time TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT true,
    response_time_ms INTEGER DEFAULT 0,
    error_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_activity_type ON user_progress(activity_type);
CREATE INDEX IF NOT EXISTS idx_user_progress_completion_timestamp ON user_progress(completion_timestamp);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_lesson_id ON quiz_attempts(lesson_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_completed_at ON quiz_attempts(completed_at);

CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active ON user_sessions(is_active);

CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_user_id ON admin_action_logs(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_timestamp ON admin_action_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action_type ON admin_action_logs(action_type);

CREATE INDEX IF NOT EXISTS idx_command_stats_command_name ON command_usage_stats(command_name);
CREATE INDEX IF NOT EXISTS idx_command_stats_user_id ON command_usage_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_command_stats_execution_time ON command_usage_stats(execution_time);

-- Create triggers to automatically update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at columns
CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add RLS (Row Level Security) policies if needed
-- These can be customized based on your security requirements

-- Enable RLS on tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_action_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE command_usage_stats ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (adjust as needed)
-- Allow users to read/write their own data
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can view own progress" ON user_progress
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can view own quiz attempts" ON quiz_attempts
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can view own sessions" ON user_sessions
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Allow service role to access all data (for bot operations)
CREATE POLICY "Service role full access user_profiles" ON user_profiles
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access user_progress" ON user_progress
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access quiz_attempts" ON quiz_attempts
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access user_sessions" ON user_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access admin_logs" ON admin_action_logs
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access command_stats" ON command_usage_stats
    FOR ALL USING (auth.role() = 'service_role');

-- Grant necessary permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Comments for documentation
COMMENT ON TABLE user_profiles IS 'User profiles for tracking learning progress and preferences';
COMMENT ON TABLE user_progress IS 'Individual user progress entries for tracking learning activities';
COMMENT ON TABLE quiz_attempts IS 'Detailed quiz attempt records with answers and performance';
COMMENT ON TABLE user_sessions IS 'Temporary sessions for multi-step user interactions';
COMMENT ON TABLE admin_action_logs IS 'Audit log for administrative actions';
COMMENT ON TABLE command_usage_stats IS 'Statistics for command usage and performance monitoring';