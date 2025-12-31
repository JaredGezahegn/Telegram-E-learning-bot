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
        
        if not self.db_manager.is_initialized():
            # Initialize in sync context - you may want to handle this differently
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.db_manager.initialize_database())
            except RuntimeError:
                # If no event loop is running, create one
                asyncio.run(self.db_manager.initialize_database())
    
    def create_lesson(self, lesson: Lesson) -> Optional[int]:
        """Create a new lesson in Supabase."""
        return self.db_manager.create_lesson(lesson)
    
    def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by ID from Supabase."""
        return self.db_manager.get_lesson_by_id(lesson_id)
    
    def get_all_lessons(self) -> List[Lesson]:
        """Get all lessons from Supabase."""
        return self.db_manager.get_all_lessons()
    
    def get_lessons_by_category(self, category: str) -> List[Lesson]:
        """Get lessons by category from Supabase."""
        return self.db_manager.get_lessons_by_category(category)
    
    def get_lessons_by_difficulty(self, difficulty: str) -> List[Lesson]:
        """Get lessons by difficulty from Supabase."""
        try:
            result = self.db_manager.client.table('lessons').select('*').eq('difficulty', difficulty).execute()
            return [self.db_manager._row_to_lesson(row) for row in result.data]
        except Exception as e:
            logger.error(f"Failed to get lessons by difficulty {difficulty}: {e}")
            return []
    
    def get_unused_lessons(self, days: int = 30) -> List[Lesson]:
        """Get lessons not used in the specified number of days."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get lessons that haven't been used recently or never used
            result = self.db_manager.client.table('lessons').select('*').or_(
                f'last_used.is.null,last_used.lt.{cutoff_date}'
            ).execute()
            
            return [self.db_manager._row_to_lesson(row) for row in result.data]
            
        except Exception as e:
            logger.error(f"Failed to get unused lessons: {e}")
            return []
    
    def get_least_used_lessons(self, limit: int = 10) -> List[Lesson]:
        """Get the least used lessons."""
        try:
            result = self.db_manager.client.table('lessons').select('*').order('usage_count').limit(limit).execute()
            return [self.db_manager._row_to_lesson(row) for row in result.data]
        except Exception as e:
            logger.error(f"Failed to get least used lessons: {e}")
            return []
    
    def update_lesson_usage(self, lesson_id: int) -> bool:
        """Update lesson usage statistics."""
        return self.db_manager.update_lesson_usage(lesson_id)
    
    def search_lessons(self, query: str) -> List[Lesson]:
        """Search lessons by title or content."""
        try:
            # Use Supabase text search
            result = self.db_manager.client.table('lessons').select('*').or_(
                f'title.ilike.%{query}%,content.ilike.%{query}%'
            ).execute()
            
            return [self.db_manager._row_to_lesson(row) for row in result.data]
            
        except Exception as e:
            logger.error(f"Failed to search lessons with query '{query}': {e}")
            return []
    
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
        try:
            # Get total count
            total_result = self.db_manager.client.table('lessons').select('id', count='exact').execute()
            total_count = total_result.count
            
            # Get category distribution
            categories_result = self.db_manager.client.table('lessons').select('category').execute()
            categories = {}
            for row in categories_result.data:
                cat = row['category']
                categories[cat] = categories.get(cat, 0) + 1
            
            # Get difficulty distribution
            difficulties_result = self.db_manager.client.table('lessons').select('difficulty').execute()
            difficulties = {}
            for row in difficulties_result.data:
                diff = row['difficulty']
                difficulties[diff] = difficulties.get(diff, 0) + 1
            
            return {
                'total_lessons': total_count,
                'categories': categories,
                'difficulties': difficulties,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get lesson statistics: {e}")
            return {
                'total_lessons': 0,
                'categories': {},
                'difficulties': {},
                'error': str(e)
            }
    
    def delete_lesson(self, lesson_id: int) -> bool:
        """Delete a lesson (use with caution)."""
        try:
            result = self.db_manager.client.table('lessons').delete().eq('id', lesson_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to delete lesson {lesson_id}: {e}")
            return False
    
    def update_lesson(self, lesson: Lesson) -> bool:
        """Update an existing lesson."""
        try:
            if not lesson.id:
                logger.error("Cannot update lesson without ID")
                return False
            
            lesson_data = {
                'title': lesson.title,
                'content': lesson.content,
                'category': lesson.category,
                'difficulty': lesson.difficulty,
                'tags': lesson.tags,
                'source': getattr(lesson, 'source', None)
            }
            
            result = self.db_manager.client.table('lessons').update(lesson_data).eq('id', lesson.id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update lesson {lesson.id}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test repository connection."""
        return self.db_manager.test_connection()