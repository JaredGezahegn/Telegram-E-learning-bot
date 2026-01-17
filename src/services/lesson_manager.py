"""Lesson management service that combines repository and selection functionality."""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..models.lesson import Lesson
from .database_factory import create_lesson_repository
from .lesson_selector import LessonSelector, SelectionStrategy


logger = logging.getLogger(__name__)


class LessonManager:
    """High-level service for managing lesson content and selection."""
    
    def __init__(self, db_path: str = "lessons.db", cycle_days: int = 30):
        """
        Initialize lesson manager.
        
        Args:
            db_path: Path to SQLite database (ignored if using Supabase)
            cycle_days: Number of days before allowing lesson reuse
        """
        # Use database factory to create appropriate repository
        self.repository = create_lesson_repository()
        self.selector = LessonSelector(self.repository, cycle_days)
    
    # Repository operations
    def add_lesson(self, lesson: Lesson) -> Optional[int]:
        """Add a new lesson to the system."""
        return self.repository.create_lesson(lesson)
    
    def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        """Get a lesson by ID."""
        return self.repository.get_lesson_by_id(lesson_id)
    
    def update_lesson(self, lesson: Lesson) -> bool:
        """Update an existing lesson."""
        return self.repository.update_lesson(lesson)
    
    def delete_lesson(self, lesson_id: int) -> bool:
        """Delete a lesson by ID."""
        return self.repository.delete_lesson(lesson_id)
    
    def get_lessons_by_category(self, category: str) -> List[Lesson]:
        """Get all lessons in a specific category."""
        return self.repository.get_lessons_by_category(category)
    
    def get_all_lessons(self) -> List[Lesson]:
        """Get all lessons."""
        return self.repository.get_all_lessons()
    
    # Selection operations
    def get_next_lesson_to_post(self, strategy: SelectionStrategy = SelectionStrategy.UNUSED_FIRST,
                               category: Optional[str] = None) -> Optional[Lesson]:
        """
        Get the next lesson to post.
        
        Args:
            strategy: Selection strategy to use
            category: Optional category filter
            
        Returns:
            Next lesson to post or None if no lessons available
        """
        return self.selector.get_next_lesson(strategy, category)
    
    def mark_lesson_posted(self, lesson_id: int) -> bool:
        """Mark a lesson as posted."""
        return self.selector.mark_lesson_posted(lesson_id)
    
    def reset_usage_cycle(self) -> bool:
        """Reset usage cycle for all lessons."""
        return self.selector.reset_usage_cycle()
    
    def is_cycle_reset_needed(self) -> bool:
        """Check if usage cycle reset is needed."""
        return self.selector.check_cycle_reset_needed()
    
    # Import operations
    def import_from_json(self, file_path: str) -> Dict[str, Any]:
        """Import lessons from JSON file."""
        return self.repository.import_lessons_from_json(file_path)
    
    def import_from_csv(self, file_path: str) -> Dict[str, Any]:
        """Import lessons from CSV file."""
        return self.repository.import_lessons_from_csv(file_path)
    
    def bulk_import(self, file_path: str) -> Dict[str, Any]:
        """
        Import lessons from file (auto-detect format).
        
        Args:
            file_path: Path to the file to import
            
        Returns:
            Import results dictionary
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return {
                    'imported': 0,
                    'skipped': 0,
                    'errors': [f"File not found: {file_path}"],
                    'total_processed': 0
                }
            
            # Auto-detect file format
            file_extension = file_path_obj.suffix.lower()
            
            if file_extension == '.json':
                return self.import_from_json(file_path)
            elif file_extension in ['.csv', '.tsv']:
                return self.import_from_csv(file_path)
            else:
                return {
                    'imported': 0,
                    'skipped': 0,
                    'errors': [f"Unsupported file format: {file_extension}"],
                    'total_processed': 0
                }
                
        except Exception as e:
            logger.error(f"Error in bulk import: {e}")
            return {
                'imported': 0,
                'skipped': 0,
                'errors': [str(e)],
                'total_processed': 0
            }
    
    # Statistics and monitoring
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            selection_stats = self.selector.get_selection_stats()
            db_stats = self.repository.db_manager.get_database_stats()
            
            return {
                'lesson_stats': selection_stats,
                'database_stats': db_stats,
                'system_health': self._check_system_health()
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def validate_system(self) -> Dict[str, Any]:
        """Validate the entire lesson management system."""
        try:
            # Validate selection integrity
            selection_validation = self.selector.validate_selection_integrity()
            
            # Validate database
            db_initialized = self.repository.db_manager.is_initialized()
            schema_valid = self.repository.db_manager.validate_schema()
            
            # Check minimum lesson requirements
            lesson_count = self.repository.get_lesson_count()
            min_lessons_met = lesson_count >= 30
            
            # Combine all validation results
            all_issues = selection_validation.get('issues', [])
            all_warnings = selection_validation.get('warnings', [])
            
            if not db_initialized:
                all_issues.append("Database is not properly initialized")
            
            if not schema_valid:
                all_issues.append("Database schema validation failed")
            
            if not min_lessons_met:
                all_warnings.append(f"Only {lesson_count} lessons available, minimum 30 recommended")
            
            return {
                'valid': len(all_issues) == 0,
                'database_initialized': db_initialized,
                'schema_valid': schema_valid,
                'minimum_lessons_met': min_lessons_met,
                'lesson_count': lesson_count,
                'selection_valid': selection_validation.get('valid', False),
                'issues': all_issues,
                'warnings': all_warnings
            }
            
        except Exception as e:
            logger.error(f"Error validating system: {e}")
            return {
                'valid': False,
                'issues': [f"System validation error: {e}"],
                'warnings': []
            }
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        try:
            health_status = "healthy"
            issues = []
            
            # Check database connectivity
            try:
                lesson_count = self.repository.get_lesson_count()
            except Exception as e:
                health_status = "unhealthy"
                issues.append(f"Database connectivity issue: {e}")
                lesson_count = 0
            
            # Check if we have lessons
            if lesson_count == 0:
                health_status = "degraded"
                issues.append("No lessons available in database")
            
            # Check if cycle reset is overdue
            if self.selector.check_cycle_reset_needed():
                if health_status == "healthy":
                    health_status = "attention_needed"
                issues.append("Usage cycle reset is recommended")
            
            return {
                'status': health_status,
                'lesson_count': lesson_count,
                'issues': issues,
                'last_check': self._get_current_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                'status': 'error',
                'issues': [f"Health check failed: {e}"],
                'last_check': self._get_current_timestamp()
            }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    # Convenience methods for common operations
    def setup_initial_lessons(self, seed_data_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Set up initial lessons from seed data.
        
        Args:
            seed_data_path: Optional path to seed data file
            
        Returns:
            Setup results
        """
        try:
            if seed_data_path and Path(seed_data_path).exists():
                # Import from provided seed data
                return self.bulk_import(seed_data_path)
            else:
                # Create minimal default lessons if no seed data
                return self._create_default_lessons()
                
        except Exception as e:
            logger.error(f"Error setting up initial lessons: {e}")
            return {
                'imported': 0,
                'skipped': 0,
                'errors': [str(e)],
                'total_processed': 0
            }
    
    def _create_default_lessons(self) -> Dict[str, Any]:
        """Create a minimal set of default lessons."""
        default_lessons = [
            {
                'title': 'Present Simple vs Present Continuous',
                'content': '🎯 **Grammar Lesson: Present Simple vs Present Continuous**\n\n📝 **Rule**: Use Present Simple for habits, Present Continuous for actions happening now\n\n✅ **Correct**: I work every day (habit) / I am working now (current action)\n❌ **Wrong**: I am working every day / I work now\n\n💡 **Tip**: Look for time markers like "always", "now", "at the moment"',
                'category': 'grammar',
                'difficulty': 'beginner',
                'tags': ['present_simple', 'present_continuous', 'tenses']
            },
            {
                'title': 'Common Vocabulary: Business Terms',
                'content': '📚 **Vocabulary Lesson: Essential Business Terms**\n\n💼 **Key Words**:\n• Meeting - formal discussion\n• Deadline - time limit for completion\n• Budget - planned spending\n• Revenue - income from sales\n\n📝 **Example**: "We have a meeting to discuss the budget before the deadline."\n\n💡 **Practice**: Use these words in your daily conversations!',
                'category': 'vocabulary',
                'difficulty': 'intermediate',
                'tags': ['business', 'workplace', 'professional']
            },
            {
                'title': 'Common Mistake: Its vs It\'s',
                'content': '⚠️ **Common Mistake: Its vs It\'s**\n\n📝 **Rule**: \n• Its = possessive (belonging to it)\n• It\'s = contraction (it is/it has)\n\n✅ **Correct**: The dog wagged its tail. It\'s a friendly dog.\n❌ **Wrong**: The dog wagged it\'s tail. Its a friendly dog.\n\n💡 **Memory Tip**: If you can say "it is", use "it\'s"',
                'category': 'common_mistakes',
                'difficulty': 'beginner',
                'tags': ['grammar', 'possessive', 'contractions']
            }
        ]
        
        imported_count = 0
        errors = []
        
        for lesson_data in default_lessons:
            try:
                lesson = Lesson.from_dict(lesson_data)
                lesson_id = self.add_lesson(lesson)
                if lesson_id:
                    imported_count += 1
                else:
                    errors.append(f"Failed to create lesson: {lesson_data['title']}")
            except Exception as e:
                errors.append(f"Error creating lesson '{lesson_data['title']}': {e}")
        
        return {
            'imported': imported_count,
            'skipped': 0,
            'errors': errors,
            'total_processed': len(default_lessons)
        }