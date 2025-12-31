"""PostingHistory data model for tracking lesson posting attempts."""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class PostingHistory:
    """Data model for tracking lesson posting history and attempts."""
    
    id: Optional[int] = None
    lesson_id: int = 0
    posted_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        """Initialize default values after object creation."""
        if self.posted_at is None:
            self.posted_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert posting history to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'success': self.success,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PostingHistory':
        """Create posting history from dictionary data."""
        history = cls(
            id=data.get('id'),
            lesson_id=data.get('lesson_id', 0),
            success=data.get('success', False),
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0)
        )
        
        # Parse datetime field
        if data.get('posted_at'):
            history.posted_at = datetime.fromisoformat(data['posted_at'])
            
        return history
    
    def validate(self) -> bool:
        """Validate posting history data."""
        if self.lesson_id <= 0:
            raise ValueError("Lesson ID must be positive")
        
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")
        
        if not isinstance(self.success, bool):
            raise ValueError("Success must be a boolean value")
        
        if self.error_message is not None and not isinstance(self.error_message, str):
            raise ValueError("Error message must be a string or None")
        
        return True
    
    def record_success(self) -> None:
        """Mark this posting attempt as successful."""
        self.success = True
        self.error_message = None
        self.posted_at = datetime.utcnow()
    
    def record_failure(self, error_message: str) -> None:
        """Mark this posting attempt as failed with error message."""
        self.success = False
        self.error_message = error_message
        self.posted_at = datetime.utcnow()
    
    def increment_retry(self) -> None:
        """Increment the retry count for this posting attempt."""
        self.retry_count += 1