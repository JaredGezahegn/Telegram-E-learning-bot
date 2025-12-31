"""Lesson selection service with duplication prevention and cycle management."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from ..models.lesson import Lesson
from .lesson_repository import LessonRepository


logger = logging.getLogger(__name__)


class SelectionStrategy(Enum):
    """Strategies for lesson selection."""
    UNUSED_FIRST = "unused_first"  # Prioritize unused lessons
    LEAST_RECENT = "least_recent"  # Select least recently used
    CATEGORY_ROTATION = "category_rotation"  # Rotate through categories


class LessonSelector:
    """Service for selecting lessons with duplication prevention."""
    
    def __init__(self, repository: Optional[LessonRepository] = None, 
                 cycle_days: int = 30):
        """
        Initialize lesson selector.
        
        Args:
            repository: Lesson repository instance
            cycle_days: Number of days before allowing lesson reuse
        """
        self.repository = repository or LessonRepository()
        self.cycle_days = cycle_days
        self._last_category = None
    
    def get_next_lesson(self, strategy: SelectionStrategy = SelectionStrategy.UNUSED_FIRST,
                       category_filter: Optional[str] = None) -> Optional[Lesson]:
        """
        Get the next lesson to post based on selection strategy.
        
        Args:
            strategy: Selection strategy to use
            category_filter: Optional category to filter by
            
        Returns:
            Next lesson to post or None if no lessons available
        """
        try:
            # Check if we have any lessons at all
            total_lessons = self.repository.get_lesson_count()
            if total_lessons == 0:
                logger.warning("No lessons available in database")
                return None
            
            # Apply selection strategy
            if strategy == SelectionStrategy.UNUSED_FIRST:
                lesson = self._select_unused_first(category_filter)
            elif strategy == SelectionStrategy.LEAST_RECENT:
                lesson = self._select_least_recent(category_filter)
            elif strategy == SelectionStrategy.CATEGORY_ROTATION:
                lesson = self._select_category_rotation(category_filter)
            else:
                logger.error(f"Unknown selection strategy: {strategy}")
                return None
            
            if lesson:
                logger.info(f"Selected lesson: {lesson.title} (ID: {lesson.id})")
            else:
                logger.warning("No suitable lesson found with current strategy")
            
            return lesson
            
        except Exception as e:
            logger.error(f"Failed to get next lesson: {e}")
            return None
    
    def mark_lesson_posted(self, lesson_id: int) -> bool:
        """
        Mark a lesson as posted and update usage statistics.
        
        Args:
            lesson_id: ID of the lesson that was posted
            
        Returns:
            True if successfully marked, False otherwise
        """
        try:
            success = self.repository.mark_lesson_used(lesson_id)
            if success:
                logger.info(f"Marked lesson {lesson_id} as posted")
            else:
                logger.error(f"Failed to mark lesson {lesson_id} as posted")
            return success
            
        except Exception as e:
            logger.error(f"Error marking lesson as posted: {e}")
            return False
    
    def check_cycle_reset_needed(self) -> bool:
        """
        Check if a usage cycle reset is needed.
        
        Returns:
            True if cycle reset is recommended
        """
        try:
            unused_lessons = self.repository.get_unused_lessons()
            
            # If no unused lessons, check if enough time has passed since last use
            if not unused_lessons:
                oldest_lesson = self.repository.get_least_recently_used_lesson()
                if oldest_lesson and oldest_lesson.last_used:
                    days_since_use = (datetime.utcnow() - oldest_lesson.last_used).days
                    return days_since_use >= self.cycle_days
                
                # If no lessons have been used yet, no reset needed
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking cycle reset: {e}")
            return False
    
    def reset_usage_cycle(self) -> bool:
        """
        Reset the usage cycle for all lessons.
        
        Returns:
            True if reset was successful
        """
        try:
            success = self.repository.reset_usage_cycle()
            if success:
                logger.info("Usage cycle reset completed")
                self._last_category = None  # Reset category rotation
            return success
            
        except Exception as e:
            logger.error(f"Error resetting usage cycle: {e}")
            return False
    
    def get_selection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about lesson selection and usage.
        
        Returns:
            Dictionary with selection statistics
        """
        try:
            total_lessons = self.repository.get_lesson_count()
            unused_lessons = len(self.repository.get_unused_lessons())
            
            # Get category distribution
            categories = ['grammar', 'vocabulary', 'common_mistakes']
            category_stats = {}
            
            for category in categories:
                lessons = self.repository.get_lessons_by_category(category)
                category_stats[category] = {
                    'total': len(lessons),
                    'unused': len([l for l in lessons if l.last_used is None])
                }
            
            # Check if cycle reset is recommended
            reset_needed = self.check_cycle_reset_needed()
            
            return {
                'total_lessons': total_lessons,
                'unused_lessons': unused_lessons,
                'used_lessons': total_lessons - unused_lessons,
                'category_stats': category_stats,
                'cycle_reset_needed': reset_needed,
                'cycle_days': self.cycle_days
            }
            
        except Exception as e:
            logger.error(f"Error getting selection stats: {e}")
            return {}
    
    def _select_unused_first(self, category_filter: Optional[str] = None) -> Optional[Lesson]:
        """Select from unused lessons first, then least recently used."""
        # Try unused lessons first
        unused_lessons = self.repository.get_unused_lessons()
        
        if category_filter:
            unused_lessons = [l for l in unused_lessons if l.category == category_filter]
        
        if unused_lessons:
            # Return first unused lesson (oldest by creation date)
            return unused_lessons[0]
        
        # If no unused lessons, fall back to least recently used
        return self._select_least_recent(category_filter)
    
    def _select_least_recent(self, category_filter: Optional[str] = None) -> Optional[Lesson]:
        """Select the least recently used lesson."""
        if category_filter:
            # Get all lessons in category and find least recently used
            category_lessons = self.repository.get_lessons_by_category(category_filter)
            if not category_lessons:
                return None
            
            # Sort by last_used (None values first, then oldest dates)
            category_lessons.sort(key=lambda x: x.last_used or datetime.min)
            return category_lessons[0]
        else:
            # Get globally least recently used lesson
            return self.repository.get_least_recently_used_lesson()
    
    def _select_category_rotation(self, category_filter: Optional[str] = None) -> Optional[Lesson]:
        """Select lesson using category rotation strategy."""
        categories = ['grammar', 'vocabulary', 'common_mistakes']
        
        if category_filter:
            # If category is specified, use it directly
            target_category = category_filter
        else:
            # Rotate through categories
            if self._last_category is None:
                target_category = categories[0]
            else:
                try:
                    current_index = categories.index(self._last_category)
                    next_index = (current_index + 1) % len(categories)
                    target_category = categories[next_index]
                except ValueError:
                    target_category = categories[0]
        
        # Get lesson from target category using unused_first strategy
        lesson = self._select_unused_first(target_category)
        
        if lesson:
            self._last_category = target_category
        else:
            # If no lesson in target category, try other categories
            for category in categories:
                if category != target_category:
                    lesson = self._select_unused_first(category)
                    if lesson:
                        self._last_category = category
                        break
        
        return lesson
    
    def validate_selection_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of lesson selection system.
        
        Returns:
            Dictionary with validation results
        """
        try:
            issues = []
            warnings = []
            
            # Check if database has sufficient lessons
            total_lessons = self.repository.get_lesson_count()
            if total_lessons < 30:
                warnings.append(f"Only {total_lessons} lessons available, recommended minimum is 30")
            
            # Check category distribution
            categories = ['grammar', 'vocabulary', 'common_mistakes']
            category_counts = {}
            
            for category in categories:
                count = len(self.repository.get_lessons_by_category(category))
                category_counts[category] = count
                
                if count == 0:
                    issues.append(f"No lessons found in category: {category}")
            
            # Check for lessons with invalid data
            all_lessons = self.repository.get_all_lessons()
            invalid_lessons = []
            
            for lesson in all_lessons:
                try:
                    lesson.validate()
                except ValueError as e:
                    invalid_lessons.append(f"Lesson {lesson.id}: {e}")
            
            if invalid_lessons:
                issues.extend(invalid_lessons)
            
            # Check usage distribution
            unused_count = len(self.repository.get_unused_lessons())
            usage_ratio = (total_lessons - unused_count) / total_lessons if total_lessons > 0 else 0
            
            if usage_ratio > 0.9:
                warnings.append("Over 90% of lessons have been used, consider cycle reset")
            
            return {
                'valid': len(issues) == 0,
                'total_lessons': total_lessons,
                'category_counts': category_counts,
                'unused_lessons': unused_count,
                'usage_ratio': usage_ratio,
                'issues': issues,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error validating selection integrity: {e}")
            return {
                'valid': False,
                'issues': [f"Validation error: {e}"],
                'warnings': []
            }