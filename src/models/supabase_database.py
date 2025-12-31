"""Supabase database connection management and operations."""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from .lesson import Lesson
from .posting_history import PostingHistory


logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manages Supabase database connections and operations."""
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize Supabase manager."""
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase client not installed. Run: pip install supabase")
        
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_ANON_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be provided")
        
        self.client: Client = create_client(self.url, self.key)
        self._initialized = False
    
    async def initialize_database(self) -> bool:
        """Initialize database schema."""
        try:
            # Create lessons table
            await self._create_lessons_table()
            
            # Create posting history table
            await self._create_posting_history_table()
            
            # Create bot config table
            await self._create_bot_config_table()
            
            self._initialized = True
            logger.info("Supabase database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase database: {e}")
            return False
    
    async def _create_lessons_table(self):
        """Create lessons table if it doesn't exist."""
        # Note: In Supabase, you typically create tables via the dashboard
        # This method can be used to verify table exists or create via SQL
        try:
            # Test if table exists by trying to select from it
            result = self.client.table('lessons').select('id').limit(1).execute()
            logger.info("Lessons table exists")
        except Exception:
            logger.warning("Lessons table may not exist. Please create it in Supabase dashboard.")
            # You could also create it programmatically:
            # self.client.rpc('create_lessons_table').execute()
    
    async def _create_posting_history_table(self):
        """Create posting history table if it doesn't exist."""
        try:
            result = self.client.table('posting_history').select('id').limit(1).execute()
            logger.info("Posting history table exists")
        except Exception:
            logger.warning("Posting history table may not exist. Please create it in Supabase dashboard.")
    
    async def _create_bot_config_table(self):
        """Create bot config table if it doesn't exist."""
        try:
            result = self.client.table('bot_config').select('id').limit(1).execute()
            logger.info("Bot config table exists")
        except Exception:
            logger.warning("Bot config table may not exist. Please create it in Supabase dashboard.")
    
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized
    
    # Lesson operations
    def create_lesson(self, lesson: Lesson) -> Optional[int]:
        """Create a new lesson."""
        try:
            lesson_data = {
                'title': lesson.title,
                'content': lesson.content,
                'category': lesson.category,
                'difficulty': lesson.difficulty,
                'tags': lesson.tags,
                'source': getattr(lesson, 'source', None),
                'created_at': lesson.created_at.isoformat() if lesson.created_at else datetime.utcnow().isoformat(),
                'last_used': lesson.last_used.isoformat() if lesson.last_used else None,
                'usage_count': lesson.usage_count or 0
            }
            
            result = self.client.table('lessons').insert(lesson_data).execute()
            
            if result.data:
                lesson_id = result.data[0]['id']
                logger.info(f"Created lesson with ID: {lesson_id}")
                return lesson_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create lesson: {e}")
            return None
    
    def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by ID."""
        try:
            result = self.client.table('lessons').select('*').eq('id', lesson_id).execute()
            
            if result.data:
                return self._row_to_lesson(result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get lesson {lesson_id}: {e}")
            return None
    
    def get_all_lessons(self) -> List[Lesson]:
        """Get all lessons."""
        try:
            result = self.client.table('lessons').select('*').order('created_at').execute()
            
            return [self._row_to_lesson(row) for row in result.data]
            
        except Exception as e:
            logger.error(f"Failed to get all lessons: {e}")
            return []
    
    def get_lessons_by_category(self, category: str) -> List[Lesson]:
        """Get lessons by category."""
        try:
            result = self.client.table('lessons').select('*').eq('category', category).execute()
            
            return [self._row_to_lesson(row) for row in result.data]
            
        except Exception as e:
            logger.error(f"Failed to get lessons by category {category}: {e}")
            return []
    
    def update_lesson_usage(self, lesson_id: int) -> bool:
        """Update lesson usage statistics."""
        try:
            # Get current usage count
            result = self.client.table('lessons').select('usage_count').eq('id', lesson_id).execute()
            
            if not result.data:
                return False
            
            current_count = result.data[0].get('usage_count', 0)
            
            # Update usage
            update_result = self.client.table('lessons').update({
                'usage_count': current_count + 1,
                'last_used': datetime.utcnow().isoformat()
            }).eq('id', lesson_id).execute()
            
            return len(update_result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update lesson usage for {lesson_id}: {e}")
            return False
    
    def _row_to_lesson(self, row: Dict[str, Any]) -> Lesson:
        """Convert database row to Lesson object."""
        return Lesson(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            category=row['category'],
            difficulty=row['difficulty'],
            tags=row.get('tags', []),
            source=row.get('source'),
            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else None,
            last_used=datetime.fromisoformat(row['last_used'].replace('Z', '+00:00')) if row.get('last_used') else None,
            usage_count=row.get('usage_count', 0)
        )
    
    # Posting history operations
    def record_posting(self, lesson_id: int, message_id: int, channel_id: str = None) -> bool:
        """Record a lesson posting."""
        try:
            posting_data = {
                'lesson_id': lesson_id,
                'message_id': message_id,
                'channel_id': channel_id,
                'posted_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table('posting_history').insert(posting_data).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to record posting: {e}")
            return False
    
    def get_posting_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get posting history."""
        try:
            result = self.client.table('posting_history').select('*').order('posted_at', desc=True).limit(limit).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to get posting history: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            # Try to select from lessons table
            result = self.client.table('lessons').select('id').limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return False


# Convenience function
def create_supabase_manager(url: Optional[str] = None, key: Optional[str] = None) -> SupabaseManager:
    """Create and return a Supabase manager instance."""
    return SupabaseManager(url, key)