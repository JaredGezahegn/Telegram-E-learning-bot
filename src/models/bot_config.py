"""BotConfig data model for storing bot configuration settings."""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class BotConfig:
    """Data model for bot configuration settings stored in database."""
    
    id: Optional[int] = None
    bot_token: str = ""
    channel_id: str = ""
    posting_time: str = "09:00"  # HH:MM format
    timezone: str = "UTC"
    retry_attempts: int = 3
    retry_delay: int = 60  # seconds
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values after object creation."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert bot config to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'bot_token': self.bot_token,
            'channel_id': self.channel_id,
            'posting_time': self.posting_time,
            'timezone': self.timezone,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BotConfig':
        """Create bot config from dictionary data."""
        config = cls(
            id=data.get('id'),
            bot_token=data.get('bot_token', ''),
            channel_id=data.get('channel_id', ''),
            posting_time=data.get('posting_time', '09:00'),
            timezone=data.get('timezone', 'UTC'),
            retry_attempts=data.get('retry_attempts', 3),
            retry_delay=data.get('retry_delay', 60)
        )
        
        # Parse datetime fields
        if data.get('created_at'):
            config.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            config.updated_at = datetime.fromisoformat(data['updated_at'])
            
        return config
    
    def validate(self) -> bool:
        """Validate bot configuration settings."""
        if not self.bot_token or not self.bot_token.strip():
            raise ValueError("Bot token is required")
        
        # Validate bot token format (should contain colon)
        if ":" not in self.bot_token:
            raise ValueError("Invalid bot token format")
        
        if not self.channel_id or not self.channel_id.strip():
            raise ValueError("Channel ID is required")
        
        # Validate channel ID format
        if not (self.channel_id.startswith("@") or self.channel_id.startswith("-")):
            raise ValueError("Channel ID must start with @ or -")
        
        # Validate posting time format (HH:MM)
        try:
            time_parts = self.posting_time.split(":")
            if len(time_parts) != 2:
                raise ValueError("Posting time must be in HH:MM format")
            
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Invalid posting time values")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid posting time format: {e}")
        
        if not self.timezone or not self.timezone.strip():
            raise ValueError("Timezone is required")
        
        if self.retry_attempts < 0:
            raise ValueError("Retry attempts cannot be negative")
        
        if self.retry_delay < 0:
            raise ValueError("Retry delay cannot be negative")
        
        return True
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow()