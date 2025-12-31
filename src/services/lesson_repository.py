"""Lesson repository for CRUD operations and data access."""

import json
import csv
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..models.lesson import Lesson
from ..models.database import DatabaseManager


logger = logging.getLogger(__name__)


class LessonRepository:
    """Repository for lesson data access and management."""
    
    def __init__(self, db_path: str = "lessons.db"):
        """Initialize lesson repository with database manager."""
        # Create a new database manager instance for each repository
        self.db_manager = DatabaseManager(db_path)
        if not self.db_manager.is_initialized():
            self.db_manager.initialize_database()
    
    def create_lesson(self, lesson: Lesson) -> Optional[int]:
        """Create a new lesson in the database."""
        try:
            # Validate lesson before saving
            lesson.validate()
            
            # Check for duplicates
            if self._is_duplicate(lesson):
                logger.warning(f"Duplicate lesson detected: {lesson.title}")
                return None
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO lessons (
                        title, content, category, difficulty, created_at,
                        last_used, usage_count, tags, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lesson.title,
                    lesson.content,
                    lesson.category,
                    lesson.difficulty,
                    lesson.created_at.isoformat() if lesson.created_at else datetime.utcnow().isoformat(),
                    lesson.last_used.isoformat() if lesson.last_used else None,
                    lesson.usage_count,
                    json.dumps(lesson.tags),
                    lesson.source
                ))
                
                lesson_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Created lesson with ID: {lesson_id}")
                return lesson_id
                
        except Exception as e:
            logger.error(f"Failed to create lesson: {e}")
            return None
    
    def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Retrieve a lesson by its ID."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_lesson(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get lesson by ID {lesson_id}: {e}")
            return None
    
    def get_lessons_by_category(self, category: str) -> List[Lesson]:
        """Retrieve all lessons in a specific category."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM lessons WHERE category = ? ORDER BY created_at",
                    (category,)
                )
                rows = cursor.fetchall()
                
                return [self._row_to_lesson(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get lessons by category {category}: {e}")
            return []
    
    def get_all_lessons(self) -> List[Lesson]:
        """Retrieve all lessons from the database."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM lessons ORDER BY created_at")
                rows = cursor.fetchall()
                
                return [self._row_to_lesson(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get all lessons: {e}")
            return []
    
    def update_lesson(self, lesson: Lesson) -> bool:
        """Update an existing lesson."""
        try:
            if not lesson.id:
                logger.error("Cannot update lesson without ID")
                return False
            
            # Validate lesson before updating
            lesson.validate()
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE lessons SET
                        title = ?, content = ?, category = ?, difficulty = ?,
                        last_used = ?, usage_count = ?, tags = ?, source = ?
                    WHERE id = ?
                """, (
                    lesson.title,
                    lesson.content,
                    lesson.category,
                    lesson.difficulty,
                    lesson.last_used.isoformat() if lesson.last_used else None,
                    lesson.usage_count,
                    json.dumps(lesson.tags),
                    lesson.source,
                    lesson.id
                ))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Updated lesson with ID: {lesson.id}")
                    return True
                else:
                    logger.warning(f"No lesson found with ID: {lesson.id}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to update lesson: {e}")
            return False
    
    def delete_lesson(self, lesson_id: int) -> bool:
        """Delete a lesson by its ID."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Deleted lesson with ID: {lesson_id}")
                    return True
                else:
                    logger.warning(f"No lesson found with ID: {lesson_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to delete lesson: {e}")
            return False
    
    def mark_lesson_used(self, lesson_id: int) -> bool:
        """Mark a lesson as used and update usage statistics."""
        try:
            lesson = self.get_lesson_by_id(lesson_id)
            if not lesson:
                logger.error(f"Lesson with ID {lesson_id} not found")
                return False
            
            lesson.mark_used()
            return self.update_lesson(lesson)
            
        except Exception as e:
            logger.error(f"Failed to mark lesson as used: {e}")
            return False
    
    def get_unused_lessons(self) -> List[Lesson]:
        """Get all lessons that have never been used."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM lessons 
                    WHERE last_used IS NULL 
                    ORDER BY created_at
                """)
                rows = cursor.fetchall()
                
                return [self._row_to_lesson(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get unused lessons: {e}")
            return []
    
    def get_least_recently_used_lesson(self) -> Optional[Lesson]:
        """Get the lesson that was used least recently."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM lessons 
                    WHERE last_used IS NOT NULL 
                    ORDER BY last_used ASC 
                    LIMIT 1
                """)
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_lesson(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get least recently used lesson: {e}")
            return None
    
    def reset_usage_cycle(self) -> bool:
        """Reset usage tracking for all lessons to start a new cycle."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE lessons SET 
                        last_used = NULL,
                        usage_count = 0
                """)
                conn.commit()
                
                logger.info(f"Reset usage cycle for {cursor.rowcount} lessons")
                return True
                
        except Exception as e:
            logger.error(f"Failed to reset usage cycle: {e}")
            return False
    
    def get_lesson_count(self) -> int:
        """Get the total number of lessons in the database."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM lessons")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get lesson count: {e}")
            return 0
    
    def import_lessons_from_json(self, file_path: str) -> Dict[str, Any]:
        """Import lessons from a JSON file."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both single lesson and array of lessons
            if isinstance(data, dict):
                lessons_data = [data]
            elif isinstance(data, list):
                lessons_data = data
            else:
                raise ValueError("JSON file must contain a lesson object or array of lessons")
            
            imported_count = 0
            skipped_count = 0
            errors = []
            
            for lesson_data in lessons_data:
                try:
                    lesson = Lesson.from_dict(lesson_data)
                    lesson.source = 'imported'
                    
                    lesson_id = self.create_lesson(lesson)
                    if lesson_id:
                        imported_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    errors.append(f"Error importing lesson '{lesson_data.get('title', 'Unknown')}': {e}")
                    skipped_count += 1
            
            result = {
                'imported': imported_count,
                'skipped': skipped_count,
                'errors': errors,
                'total_processed': len(lessons_data)
            }
            
            logger.info(f"JSON import completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to import lessons from JSON: {e}")
            return {
                'imported': 0,
                'skipped': 0,
                'errors': [str(e)],
                'total_processed': 0
            }
    
    def import_lessons_from_csv(self, file_path: str) -> Dict[str, Any]:
        """Import lessons from a CSV file."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            imported_count = 0
            skipped_count = 0
            errors = []
            
            with open(file_path_obj, 'r', encoding='utf-8', newline='') as f:
                # Try to detect delimiter, default to comma
                sample = f.read(1024)
                f.seek(0)
                
                delimiter = ','
                try:
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
                except Exception:
                    # If detection fails, use comma as default
                    delimiter = ','
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                    try:
                        # Map CSV columns to lesson fields
                        lesson_data = {
                            'title': row.get('title', '').strip(),
                            'content': row.get('content', '').strip(),
                            'category': row.get('category', '').strip().lower(),
                            'difficulty': row.get('difficulty', '').strip().lower(),
                            'tags': self._parse_csv_tags(row.get('tags', '')),
                            'source': 'imported'
                        }
                        
                        lesson = Lesson.from_dict(lesson_data)
                        
                        lesson_id = self.create_lesson(lesson)
                        if lesson_id:
                            imported_count += 1
                        else:
                            skipped_count += 1
                            
                    except Exception as e:
                        errors.append(f"Error importing row {row_num}: {e}")
                        skipped_count += 1
            
            result = {
                'imported': imported_count,
                'skipped': skipped_count,
                'errors': errors,
                'total_processed': imported_count + skipped_count
            }
            
            logger.info(f"CSV import completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to import lessons from CSV: {e}")
            return {
                'imported': 0,
                'skipped': 0,
                'errors': [str(e)],
                'total_processed': 0
            }
    
    def _row_to_lesson(self, row) -> Lesson:
        """Convert database row to Lesson object."""
        lesson = Lesson(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            category=row['category'],
            difficulty=row['difficulty'],
            usage_count=row['usage_count'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            source=row['source']
        )
        
        # Parse datetime fields
        if row['created_at']:
            lesson.created_at = datetime.fromisoformat(row['created_at'])
        if row['last_used']:
            lesson.last_used = datetime.fromisoformat(row['last_used'])
        
        return lesson
    
    def _is_duplicate(self, lesson: Lesson) -> bool:
        """Check if a lesson is a duplicate of existing content."""
        try:
            existing_lessons = self.get_all_lessons()
            
            for existing in existing_lessons:
                if lesson.is_similar_to(existing):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return False
    
    def _parse_csv_tags(self, tags_str: str) -> List[str]:
        """Parse tags from CSV string format."""
        if not tags_str or not tags_str.strip():
            return []
        
        # Handle different tag formats: "tag1,tag2,tag3" or "tag1;tag2;tag3" or JSON array
        tags_str = tags_str.strip()
        
        # Try JSON format first
        try:
            if tags_str.startswith('[') and tags_str.endswith(']'):
                return json.loads(tags_str)
        except json.JSONDecodeError:
            pass
        
        # Try comma or semicolon separated
        if ',' in tags_str:
            return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        elif ';' in tags_str:
            return [tag.strip() for tag in tags_str.split(';') if tag.strip()]
        else:
            # Single tag
            return [tags_str] if tags_str else []