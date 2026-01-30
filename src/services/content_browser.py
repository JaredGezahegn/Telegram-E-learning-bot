"""Content browsing service for searching and filtering lessons."""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from ..models.lesson import Lesson
from .lesson_manager import LessonManager

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result of a content search operation."""
    lessons: List[Lesson]
    total_count: int
    search_terms: List[str]
    filters_applied: Dict[str, Any]
    suggestions: List[str] = None


@dataclass
class ContentStats:
    """Statistics about available content."""
    total_lessons: int
    categories: List[str]
    difficulties: List[str]
    popular_tags: List[str]
    category_counts: Dict[str, int]
    difficulty_counts: Dict[str, int]


class ContentBrowser:
    """Service for browsing, searching, and filtering lesson content."""
    
    def __init__(self, lesson_manager: LessonManager):
        """Initialize content browser with lesson manager."""
        self.lesson_manager = lesson_manager
        self._content_stats = None
        logger.info("Content browser initialized")
    
    def get_content_stats(self) -> ContentStats:
        """Get comprehensive statistics about available content."""
        if self._content_stats is None:
            self._refresh_content_stats()
        return self._content_stats
    
    def _refresh_content_stats(self) -> None:
        """Refresh cached content statistics."""
        try:
            lessons = self.lesson_manager.get_all_lessons()
            
            categories = set()
            difficulties = set()
            tags = set()
            category_counts = {}
            difficulty_counts = {}
            
            for lesson in lessons:
                if lesson.category:
                    categories.add(lesson.category)
                    category_counts[lesson.category] = category_counts.get(lesson.category, 0) + 1
                
                if lesson.difficulty:
                    difficulties.add(lesson.difficulty)
                    difficulty_counts[lesson.difficulty] = difficulty_counts.get(lesson.difficulty, 0) + 1
                
                if lesson.tags:
                    tags.update(lesson.tags)
            
            # Get most popular tags (by frequency in lessons)
            tag_counts = {}
            for lesson in lessons:
                for tag in lesson.tags or []:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            popular_tags = sorted(tag_counts.keys(), key=lambda x: tag_counts[x], reverse=True)[:20]
            
            self._content_stats = ContentStats(
                total_lessons=len(lessons),
                categories=sorted(categories),
                difficulties=sorted(difficulties),
                popular_tags=popular_tags,
                category_counts=category_counts,
                difficulty_counts=difficulty_counts
            )
            
            logger.info(f"Content stats refreshed: {len(lessons)} lessons, {len(categories)} categories")
            
        except Exception as e:
            logger.error(f"Error refreshing content stats: {e}")
            # Fallback to empty stats
            self._content_stats = ContentStats(
                total_lessons=0,
                categories=[],
                difficulties=[],
                popular_tags=[],
                category_counts={},
                difficulty_counts={}
            )
    
    def search_by_category(self, category: str, limit: int = 10) -> SearchResult:
        """Search lessons by category."""
        try:
            # Normalize category name
            category = category.lower().strip()
            
            # Get all lessons in category
            lessons = self.lesson_manager.get_lessons_by_category(category)
            
            # Sort by usage count (least used first) and limit results
            lessons.sort(key=lambda x: (x.usage_count, x.id))
            limited_lessons = lessons[:limit] if limit > 0 else lessons
            
            # Generate suggestions if no results
            suggestions = []
            if not lessons:
                stats = self.get_content_stats()
                suggestions = [cat for cat in stats.categories if category in cat.lower()][:3]
            
            return SearchResult(
                lessons=limited_lessons,
                total_count=len(lessons),
                search_terms=[category],
                filters_applied={'category': category, 'limit': limit},
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error searching by category '{category}': {e}")
            return SearchResult(
                lessons=[],
                total_count=0,
                search_terms=[category],
                filters_applied={'category': category, 'limit': limit},
                suggestions=[]
            )
    
    def search_by_difficulty(self, difficulty: str, limit: int = 10) -> SearchResult:
        """Search lessons by difficulty level."""
        try:
            # Normalize difficulty
            difficulty = difficulty.lower().strip()
            
            # Get all lessons
            all_lessons = self.lesson_manager.get_all_lessons()
            
            # Filter by difficulty
            lessons = [lesson for lesson in all_lessons if lesson.difficulty.lower() == difficulty]
            
            # Sort by usage count and limit
            lessons.sort(key=lambda x: (x.usage_count, x.id))
            limited_lessons = lessons[:limit] if limit > 0 else lessons
            
            # Generate suggestions if no results
            suggestions = []
            if not lessons:
                stats = self.get_content_stats()
                suggestions = [diff for diff in stats.difficulties if difficulty in diff.lower()][:3]
            
            return SearchResult(
                lessons=limited_lessons,
                total_count=len(lessons),
                search_terms=[difficulty],
                filters_applied={'difficulty': difficulty, 'limit': limit},
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error searching by difficulty '{difficulty}': {e}")
            return SearchResult(
                lessons=[],
                total_count=0,
                search_terms=[difficulty],
                filters_applied={'difficulty': difficulty, 'limit': limit},
                suggestions=[]
            )
    
    def search_by_tag(self, tag: str, limit: int = 10) -> SearchResult:
        """Search lessons by tag."""
        try:
            # Normalize tag
            tag = tag.lower().strip()
            
            # Get all lessons
            all_lessons = self.lesson_manager.get_all_lessons()
            
            # Filter by tag
            lessons = []
            for lesson in all_lessons:
                if lesson.tags and any(tag in lesson_tag.lower() for lesson_tag in lesson.tags):
                    lessons.append(lesson)
            
            # Sort by usage count and limit
            lessons.sort(key=lambda x: (x.usage_count, x.id))
            limited_lessons = lessons[:limit] if limit > 0 else lessons
            
            # Generate suggestions if no results
            suggestions = []
            if not lessons:
                stats = self.get_content_stats()
                suggestions = [t for t in stats.popular_tags if tag in t.lower()][:3]
            
            return SearchResult(
                lessons=limited_lessons,
                total_count=len(lessons),
                search_terms=[tag],
                filters_applied={'tag': tag, 'limit': limit},
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error searching by tag '{tag}': {e}")
            return SearchResult(
                lessons=[],
                total_count=0,
                search_terms=[tag],
                filters_applied={'tag': tag, 'limit': limit},
                suggestions=[]
            )
    
    def search_by_title(self, query: str, limit: int = 10) -> SearchResult:
        """Search lessons by title keywords."""
        try:
            # Normalize query
            query = query.lower().strip()
            query_words = query.split()
            
            # Get all lessons
            all_lessons = self.lesson_manager.get_all_lessons()
            
            # Filter by title match
            lessons = []
            for lesson in all_lessons:
                title_lower = lesson.title.lower()
                if any(word in title_lower for word in query_words):
                    lessons.append(lesson)
            
            # Sort by relevance (more matches first), then by usage count
            def relevance_score(lesson):
                title_lower = lesson.title.lower()
                matches = sum(1 for word in query_words if word in title_lower)
                return (-matches, lesson.usage_count, lesson.id)
            
            lessons.sort(key=relevance_score)
            limited_lessons = lessons[:limit] if limit > 0 else lessons
            
            return SearchResult(
                lessons=limited_lessons,
                total_count=len(lessons),
                search_terms=query_words,
                filters_applied={'title_query': query, 'limit': limit},
                suggestions=[]
            )
            
        except Exception as e:
            logger.error(f"Error searching by title '{query}': {e}")
            return SearchResult(
                lessons=[],
                total_count=0,
                search_terms=[query],
                filters_applied={'title_query': query, 'limit': limit},
                suggestions=[]
            )
    
    def get_popular_content(self, limit: int = 10) -> SearchResult:
        """Get most popular (frequently used) lessons."""
        try:
            all_lessons = self.lesson_manager.get_all_lessons()
            
            # Sort by usage count (descending) and recency
            lessons = sorted(all_lessons, key=lambda x: (-x.usage_count, x.id))
            limited_lessons = lessons[:limit] if limit > 0 else lessons
            
            return SearchResult(
                lessons=limited_lessons,
                total_count=len(all_lessons),
                search_terms=['popular'],
                filters_applied={'type': 'popular', 'limit': limit},
                suggestions=[]
            )
            
        except Exception as e:
            logger.error(f"Error getting popular content: {e}")
            return SearchResult(
                lessons=[],
                total_count=0,
                search_terms=['popular'],
                filters_applied={'type': 'popular', 'limit': limit},
                suggestions=[]
            )
    
    def get_recent_content(self, limit: int = 10) -> SearchResult:
        """Get most recently added lessons."""
        try:
            all_lessons = self.lesson_manager.get_all_lessons()
            
            # Sort by ID (assuming higher ID = more recent)
            lessons = sorted(all_lessons, key=lambda x: x.id or 0, reverse=True)
            limited_lessons = lessons[:limit] if limit > 0 else lessons
            
            return SearchResult(
                lessons=limited_lessons,
                total_count=len(all_lessons),
                search_terms=['recent'],
                filters_applied={'type': 'recent', 'limit': limit},
                suggestions=[]
            )
            
        except Exception as e:
            logger.error(f"Error getting recent content: {e}")
            return SearchResult(
                lessons=[],
                total_count=0,
                search_terms=['recent'],
                filters_applied={'type': 'recent', 'limit': limit},
                suggestions=[]
            )
    
    def get_lesson_preview(self, lesson_id: int) -> Optional[Dict[str, Any]]:
        """Get a preview of a lesson with metadata."""
        try:
            lesson = self.lesson_manager.get_lesson(lesson_id)
            if not lesson:
                return None
            
            # Create preview with truncated content
            preview_content = lesson.content[:200] + "..." if len(lesson.content) > 200 else lesson.content
            
            return {
                'id': lesson.id,
                'title': lesson.title,
                'preview_content': preview_content,
                'full_content_length': len(lesson.content),
                'category': lesson.category,
                'difficulty': lesson.difficulty,
                'tags': lesson.tags or [],
                'usage_count': lesson.usage_count,
                'created_at': lesson.created_at.isoformat() if lesson.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting lesson preview for ID {lesson_id}: {e}")
            return None
    
    def get_category_overview(self) -> Dict[str, Any]:
        """Get overview of all categories with counts and examples."""
        try:
            stats = self.get_content_stats()
            
            overview = {}
            for category in stats.categories:
                # Get a few example lessons from this category
                examples = self.search_by_category(category, limit=3)
                
                overview[category] = {
                    'count': stats.category_counts.get(category, 0),
                    'examples': [
                        {'id': lesson.id, 'title': lesson.title}
                        for lesson in examples.lessons
                    ]
                }
            
            return {
                'total_categories': len(stats.categories),
                'total_lessons': stats.total_lessons,
                'categories': overview
            }
            
        except Exception as e:
            logger.error(f"Error getting category overview: {e}")
            return {'total_categories': 0, 'total_lessons': 0, 'categories': {}}


def create_content_browser(lesson_manager: LessonManager) -> ContentBrowser:
    """Factory function to create a content browser."""
    return ContentBrowser(lesson_manager)