"""Supabase database connection management and operations."""

import os
import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .lesson import Lesson
from .posting_history import PostingHistory


logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manages Supabase database connections and operations using HTTP requests."""
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize Supabase manager."""
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_ANON_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be provided")
        
        self.base_url = f"{self.url}/rest/v1"
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        self._initialized = False
    
    def is_initialized(self) -> bool:
        """Check if database is properly initialized."""
        return self._initialized
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?select=id&limit=1",
                headers=self.headers,
                timeout=10
            )
            logger.info("Supabase connection test successful")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return False
    
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
            
            response = requests.post(
                f"{self.base_url}/lessons",
                headers=self.headers,
                json=lesson_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result:
                    lesson_id = result[0]['id']
                    logger.info(f"Created lesson with ID: {lesson_id}")
                    return lesson_id
            
            logger.error(f"Failed to create lesson: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to create lesson: {e}")
            return None
    
    def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by ID."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?id=eq.{lesson_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return self._row_to_lesson(data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get lesson {lesson_id}: {e}")
            return None
    
    def get_all_lessons(self) -> List[Lesson]:
        """Get all lessons."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?order=created_at",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [self._row_to_lesson(row) for row in data]
            
            logger.error(f"Failed to get lessons: {response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get all lessons: {e}")
            return []
    
    def get_lessons_by_category(self, category: str) -> List[Lesson]:
        """Get lessons by category."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?category=eq.{category}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [self._row_to_lesson(row) for row in data]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get lessons by category {category}: {e}")
            return []
    
    def update_lesson_usage(self, lesson_id: int) -> bool:
        """Update lesson usage statistics."""
        try:
            # Get current usage count
            response = requests.get(
                f"{self.base_url}/lessons?id=eq.{lesson_id}&select=usage_count",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200 or not response.json():
                return False
            
            current_count = response.json()[0].get('usage_count', 0)
            
            # Update usage
            update_data = {
                'usage_count': current_count + 1,
                'last_used': datetime.utcnow().isoformat()
            }
            
            update_response = requests.patch(
                f"{self.base_url}/lessons?id=eq.{lesson_id}",
                headers=self.headers,
                json=update_data,
                timeout=10
            )
            
            return update_response.status_code in [200, 204]
            
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
            
            response = requests.post(
                f"{self.base_url}/posting_history",
                headers=self.headers,
                json=posting_data,
                timeout=10
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"Failed to record posting: {e}")
            return False
    
    def get_posting_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get posting history."""
        try:
            response = requests.get(
                f"{self.base_url}/posting_history?order=posted_at.desc&limit={limit}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get posting history: {e}")
            return []
    
    def get_lessons_by_difficulty(self, difficulty: str) -> List[Lesson]:
        """Get lessons by difficulty."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?difficulty=eq.{difficulty}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [self._row_to_lesson(row) for row in data]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get lessons by difficulty {difficulty}: {e}")
            return []
    
    def get_unused_lessons_by_days(self, days: int = 30) -> List[Lesson]:
        """Get lessons not used in the specified number of days."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            response = requests.get(
                f"{self.base_url}/lessons?or=(last_used.is.null,last_used.lt.{cutoff_date})",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [self._row_to_lesson(row) for row in data]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get unused lessons: {e}")
            return []
    
    def get_least_used_lessons(self, limit: int = 10) -> List[Lesson]:
        """Get the least used lessons."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?order=usage_count.asc&limit={limit}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [self._row_to_lesson(row) for row in data]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get least used lessons: {e}")
            return []
    
    def search_lessons(self, query: str) -> List[Lesson]:
        """Search lessons by title or content."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?or=(title.ilike.*{query}*,content.ilike.*{query}*)",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [self._row_to_lesson(row) for row in data]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to search lessons with query '{query}': {e}")
            return []
    
    def get_lesson_statistics(self) -> Dict[str, Any]:
        """Get lesson statistics."""
        try:
            response = requests.get(
                f"{self.base_url}/lessons?select=category,difficulty",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                total_count = len(data)
                
                # Calculate category distribution
                categories = {}
                difficulties = {}
                for row in data:
                    cat = row['category']
                    categories[cat] = categories.get(cat, 0) + 1
                    
                    diff = row['difficulty']
                    difficulties[diff] = difficulties.get(diff, 0) + 1
                
                return {
                    'total_lessons': total_count,
                    'categories': categories,
                    'difficulties': difficulties,
                    'last_updated': datetime.utcnow().isoformat()
                }
            
            return {
                'total_lessons': 0,
                'categories': {},
                'difficulties': {},
                'error': 'Failed to fetch data'
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
            response = requests.delete(
                f"{self.base_url}/lessons?id=eq.{lesson_id}",
                headers=self.headers,
                timeout=10
            )
            
            return response.status_code in [200, 204]
            
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
            
            response = requests.patch(
                f"{self.base_url}/lessons?id=eq.{lesson.id}",
                headers=self.headers,
                json=lesson_data,
                timeout=10
            )
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            logger.error(f"Failed to update lesson {lesson.id}: {e}")
            return False


# Convenience function
def create_supabase_manager(url: Optional[str] = None, key: Optional[str] = None) -> SupabaseManager:
    """Create and return a Supabase manager instance."""
    return SupabaseManager(url, key)