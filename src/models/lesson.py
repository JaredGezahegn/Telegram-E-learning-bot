"""Lesson data model for storing English lesson content."""

from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field
import json


@dataclass
class Lesson:
    """Data model for English lesson content."""
    
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    category: str = ""  # 'grammar', 'vocabulary', 'common_mistakes'
    difficulty: str = ""  # 'beginner', 'intermediate', 'advanced'
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    tags: List[str] = field(default_factory=list)
    source: str = "manual"  # 'manual', 'imported', 'ai_generated'
    
    def __post_init__(self):
        """Initialize default values after object creation."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert lesson to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'difficulty': self.difficulty,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count,
            'tags': self.tags,
            'source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Lesson':
        """Create lesson from dictionary data."""
        lesson = cls(
            id=data.get('id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            category=data.get('category', ''),
            difficulty=data.get('difficulty', ''),
            usage_count=data.get('usage_count', 0),
            tags=data.get('tags', []),
            source=data.get('source', 'manual')
        )
        
        # Parse datetime fields
        if data.get('created_at'):
            lesson.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('last_used'):
            lesson.last_used = datetime.fromisoformat(data['last_used'])
            
        return lesson
    
    def validate(self) -> bool:
        """Validate lesson content and metadata."""
        if not self.title or not self.title.strip():
            raise ValueError("Lesson title is required")
        
        if not self.content or not self.content.strip():
            raise ValueError("Lesson content is required")
        
        valid_categories = ['grammar', 'vocabulary', 'common_mistakes']
        if self.category not in valid_categories:
            raise ValueError(f"Category must be one of: {valid_categories}")
        
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        if self.difficulty not in valid_difficulties:
            raise ValueError(f"Difficulty must be one of: {valid_difficulties}")
        
        valid_sources = ['manual', 'imported', 'ai_generated']
        if self.source not in valid_sources:
            raise ValueError(f"Source must be one of: {valid_sources}")
        
        if not isinstance(self.tags, list):
            raise ValueError("Tags must be a list")
        
        if self.usage_count < 0:
            raise ValueError("Usage count cannot be negative")
        
        return True
    
    def mark_used(self) -> None:
        """Mark lesson as used and update usage statistics."""
        self.last_used = datetime.utcnow()
        self.usage_count += 1
    
    def is_similar_to(self, other: 'Lesson') -> bool:
        """Check if this lesson is similar to another lesson (for duplicate detection)."""
        if not isinstance(other, Lesson):
            return False
        
        # Check title similarity (case-insensitive)
        if self.title.lower().strip() == other.title.lower().strip():
            return True
        
        # Check content similarity (basic check for now)
        self_content = self.content.lower().strip()
        other_content = other.content.lower().strip()
        
        # If content is identical, it's a duplicate
        if self_content == other_content:
            return True
        
        # Check for substantial overlap (simple heuristic)
        if len(self_content) > 50 and len(other_content) > 50:
            # Check if one content contains most of the other
            shorter = min(self_content, other_content, key=len)
            longer = max(self_content, other_content, key=len)
            
            if len(shorter) > 0 and len(longer) > 0:
                overlap_ratio = len(shorter) / len(longer)
                if overlap_ratio > 0.8 and shorter in longer:
                    return True
        
        return False