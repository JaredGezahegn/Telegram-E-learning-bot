"""Supabase-based lesson repository for CRUD operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..models.lesson import Lesson
from ..models.supabase_database import SupabaseManager


logger = logging.getLogger(__name__)


class SupabaseLessonRepository:
    """Repository for lesson data access using Supabase."""
    
    def __init__(self, supabase_manager: Optional[SupabaseManager] = None):
        """Initialize repository with Supabase manager."""
        if supabase_manager:
            self.db_manager = supabase_manager
        else:
            from ..models.supabase_database import create_supabase_manager
            self.db_manager = create_supabase_manager()
    
    def create_lesson(self, lesson: Lesson) -> Optional[int]:
        """Create a new lesson in Supabase."""
        return self.db_manager.create_lesson(lesson)
    
    def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by ID from Supabase."""
        return self.db_manager.get_lesson_by_id(lesson_id)
    
    def get_all_lessons(self) -> List[Lesson]:
        """Get all lessons from Supabase."""
        return self.db_manager.get_all_lessons()
    
    def get_lesson_count(self) -> int:
        """Get total count of lessons."""
        try:
            lessons = self.get_all_lessons()
            return len(lessons)
        except Exception as e:
            logger.error(f"Failed to get lesson count: {e}")
            return 0
    
    def get_lessons_by_category(self, category: str) -> List[Lesson]:
        """Get lessons by category from Supabase."""
        return self.db_manager.get_lessons_by_category(category)
    
    def get_lessons_by_difficulty(self, difficulty: str) -> List[Lesson]:
        """Get lessons by difficulty from Supabase."""
        return self.db_manager.get_lessons_by_difficulty(difficulty)
    
    def get_unused_lessons(self, days: int = None) -> List[Lesson]:
        """Get lessons not used in the specified number of days, or never used if days is None."""
        if days is None:
            return self.db_manager.get_unused_lessons()
        else:
            return self.db_manager.get_unused_lessons_by_days(days)
    
    def get_least_used_lessons(self, limit: int = 10) -> List[Lesson]:
        """Get the least used lessons."""
        return self.db_manager.get_least_used_lessons(limit)
    
    def get_least_recently_used_lesson(self) -> Optional[Lesson]:
        """Get the least recently used lesson."""
        return self.db_manager.get_least_recently_used_lesson()
    
    def update_lesson_usage(self, lesson_id: int) -> bool:
        """Update lesson usage statistics."""
        return self.db_manager.update_lesson_usage(lesson_id)
    
    def mark_lesson_used(self, lesson_id: int) -> bool:
        """Mark a lesson as used and update usage statistics."""
        return self.update_lesson_usage(lesson_id)
    
    def search_lessons(self, query: str) -> List[Lesson]:
        """Search lessons by title or content."""
        return self.db_manager.search_lessons(query)
    
    def get_lessons_by_tags(self, tags: List[str]) -> List[Lesson]:
        """Get lessons that contain any of the specified tags."""
        try:
            # Note: This requires proper JSON array handling in Supabase
            # You might need to adjust based on how tags are stored
            lessons = self.get_all_lessons()
            
            # Filter in Python for now (could be optimized with proper Supabase queries)
            matching_lessons = []
            for lesson in lessons:
                if lesson.tags and any(tag in lesson.tags for tag in tags):
                    matching_lessons.append(lesson)
            
            return matching_lessons
            
        except Exception as e:
            logger.error(f"Failed to get lessons by tags {tags}: {e}")
            return []
    
    def get_lesson_statistics(self) -> Dict[str, Any]:
        """Get lesson statistics."""
        return self.db_manager.get_lesson_statistics()
    
    def delete_lesson(self, lesson_id: int) -> bool:
        """Delete a lesson (use with caution)."""
        return self.db_manager.delete_lesson(lesson_id)
    
    def update_lesson(self, lesson: Lesson) -> bool:
        """Update an existing lesson."""
        return self.db_manager.update_lesson(lesson)
    
    def test_connection(self) -> bool:
        """Test repository connection."""
        return self.db_manager.test_connection()