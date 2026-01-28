"""Configuration management using environment variables."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration class that loads settings from environment variables."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self.bot_token = self._get_required_env("BOT_TOKEN")
        self.channel_id = self._get_required_env("CHANNEL_ID")
        self.posting_time = os.getenv("POSTING_TIME", "09:00")
        self.timezone = os.getenv("TIMEZONE", "UTC")
        self.retry_attempts = int(os.getenv("RETRY_ATTEMPTS") or "3")
        self.retry_delay = int(os.getenv("RETRY_DELAY") or "60")
        self.database_path = os.getenv("DATABASE_PATH", "lessons.db")
        self.database_type = os.getenv("DATABASE_TYPE", "sqlite")  # sqlite or supabase
        
        # Admin Configuration
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        self.admin_user_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
        
        # Supabase Configuration (if using Supabase)
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        # Quiz Configuration
        self.enable_quizzes = os.getenv("ENABLE_QUIZZES", "true").lower() == "true"
        self.quiz_delay_minutes = int(os.getenv("QUIZ_DELAY_MINUTES") or "5")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Resource monitoring and resilience settings
        self.max_cpu_percent = float(os.getenv("MAX_CPU_PERCENT") or "85.0")
        self.max_memory_percent = float(os.getenv("MAX_MEMORY_PERCENT") or "85.0")
        self.max_disk_percent = float(os.getenv("MAX_DISK_PERCENT") or "90.0")
        self.circuit_breaker_threshold = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD") or "5")
        self.circuit_breaker_timeout = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT") or "300")
        self.enable_graceful_degradation = os.getenv("ENABLE_GRACEFUL_DEGRADATION", "true").lower() == "true"
        
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error if missing."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            # Validate bot token format (should start with number followed by colon)
            if not self.bot_token or ":" not in self.bot_token:
                raise ValueError("Invalid bot token format")
            
            # Validate channel ID format (should start with @ or -)
            if not self.channel_id or not (self.channel_id.startswith("@") or self.channel_id.startswith("-")):
                raise ValueError("Invalid channel ID format")
            
            # Validate posting time format (HH:MM)
            time_parts = self.posting_time.split(":")
            if len(time_parts) != 2 or not all(part.isdigit() for part in time_parts):
                raise ValueError("Invalid posting time format (use HH:MM)")
            
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Invalid posting time values")
            
            # Validate retry settings
            if self.retry_attempts < 0 or self.retry_delay < 0:
                raise ValueError("Retry settings must be non-negative")
            
            # Validate resource thresholds
            if not (0 <= self.max_cpu_percent <= 100):
                raise ValueError("CPU threshold must be between 0 and 100")
            
            if not (0 <= self.max_memory_percent <= 100):
                raise ValueError("Memory threshold must be between 0 and 100")
            
            if not (0 <= self.max_disk_percent <= 100):
                raise ValueError("Disk threshold must be between 0 and 100")
            
            if self.circuit_breaker_threshold < 1:
                raise ValueError("Circuit breaker threshold must be positive")
            
            if self.circuit_breaker_timeout < 0:
                raise ValueError("Circuit breaker timeout must be non-negative")
            
            return True
            
        except ValueError as e:
            raise ValueError(f"Configuration validation failed: {e}")


# Global configuration instance (lazy-loaded)
_config = None

def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config

# For backward compatibility
config = get_config