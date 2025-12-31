"""Database connection management and schema setup for SQLite."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime

from .lesson import Lesson
from .posting_history import PostingHistory
from .bot_config import BotConfig


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, db_path: str = "lessons.db"):
        """Initialize database manager with database path."""
        self.db_path = Path(db_path)
        self._ensure_database_directory()
        self._initialized = False
    
    def _ensure_database_directory(self) -> None:
        """Ensure the database directory exists."""
        if self.db_path.parent != Path('.'):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def initialize_database(self) -> bool:
        """Initialize database schema and perform integrity checks."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create lessons table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS lessons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        category TEXT NOT NULL CHECK (category IN ('grammar', 'vocabulary', 'common_mistakes')),
                        difficulty TEXT NOT NULL CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
                        created_at TEXT NOT NULL,
                        last_used TEXT,
                        usage_count INTEGER DEFAULT 0,
                        tags TEXT,  -- JSON array as string
                        source TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'imported', 'ai_generated')),
                        UNIQUE(title, content)  -- Prevent exact duplicates
                    )
                """)
                
                # Create posting_history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS posting_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lesson_id INTEGER NOT NULL,
                        posted_at TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        retry_count INTEGER DEFAULT 0,
                        FOREIGN KEY (lesson_id) REFERENCES lessons (id)
                    )
                """)
                
                # Create bot_config table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bot_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bot_token TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        posting_time TEXT DEFAULT '09:00',
                        timezone TEXT DEFAULT 'UTC',
                        retry_attempts INTEGER DEFAULT 3,
                        retry_delay INTEGER DEFAULT 60,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_last_used ON lessons(last_used)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_usage_count ON lessons(usage_count)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_history_lesson_id ON posting_history(lesson_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_history_posted_at ON posting_history(posted_at)")
                
                conn.commit()
                
                # Perform integrity check
                self._perform_integrity_check(cursor)
                
                self._initialized = True
                logger.info("Database initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _perform_integrity_check(self, cursor: sqlite3.Cursor) -> None:
        """Perform database integrity checks."""
        try:
            # Check database integrity
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result[0] != "ok":
                raise RuntimeError(f"Database integrity check failed: {result[0]}")
            
            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            if fk_violations:
                raise RuntimeError(f"Foreign key violations found: {fk_violations}")
            
            logger.info("Database integrity checks passed")
            
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            raise
    
    def check_lesson_count(self) -> int:
        """Check the number of lessons in the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM lessons")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Failed to check lesson count: {e}")
            return 0
    
    def is_initialized(self) -> bool:
        """Check if database is properly initialized."""
        if not self._initialized:
            return False
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if required tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('lessons', 'posting_history', 'bot_config')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = {'lessons', 'posting_history', 'bot_config'}
                return required_tables.issubset(set(tables))
                
        except Exception as e:
            logger.error(f"Failed to check database initialization: {e}")
            return False
    
    def validate_schema(self) -> bool:
        """Validate database schema matches expected structure."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check lessons table structure
                cursor.execute("PRAGMA table_info(lessons)")
                lessons_columns = {row[1]: row[2] for row in cursor.fetchall()}
                
                expected_lessons_columns = {
                    'id': 'INTEGER',
                    'title': 'TEXT',
                    'content': 'TEXT',
                    'category': 'TEXT',
                    'difficulty': 'TEXT',
                    'created_at': 'TEXT',
                    'last_used': 'TEXT',
                    'usage_count': 'INTEGER',
                    'tags': 'TEXT',
                    'source': 'TEXT'
                }
                
                for col_name, col_type in expected_lessons_columns.items():
                    if col_name not in lessons_columns:
                        logger.error(f"Missing column {col_name} in lessons table")
                        return False
                
                # Check posting_history table structure
                cursor.execute("PRAGMA table_info(posting_history)")
                history_columns = {row[1]: row[2] for row in cursor.fetchall()}
                
                expected_history_columns = {
                    'id': 'INTEGER',
                    'lesson_id': 'INTEGER',
                    'posted_at': 'TEXT',
                    'success': 'BOOLEAN',
                    'error_message': 'TEXT',
                    'retry_count': 'INTEGER'
                }
                
                for col_name, col_type in expected_history_columns.items():
                    if col_name not in history_columns:
                        logger.error(f"Missing column {col_name} in posting_history table")
                        return False
                
                # Check bot_config table structure
                cursor.execute("PRAGMA table_info(bot_config)")
                config_columns = {row[1]: row[2] for row in cursor.fetchall()}
                
                expected_config_columns = {
                    'id': 'INTEGER',
                    'bot_token': 'TEXT',
                    'channel_id': 'TEXT',
                    'posting_time': 'TEXT',
                    'timezone': 'TEXT',
                    'retry_attempts': 'INTEGER',
                    'retry_delay': 'INTEGER',
                    'created_at': 'TEXT',
                    'updated_at': 'TEXT'
                }
                
                for col_name, col_type in expected_config_columns.items():
                    if col_name not in config_columns:
                        logger.error(f"Missing column {col_name} in bot_config table")
                        return False
                
                logger.info("Database schema validation passed")
                return True
                
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            backup_path_obj = Path(backup_path)
            backup_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Use explicit connection management to ensure proper cleanup
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_path_obj))
            
            try:
                source_conn.backup(backup_conn)
                logger.info(f"Database backed up to {backup_path}")
                return True
            finally:
                backup_conn.close()
                source_conn.close()
            
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table counts
                cursor.execute("SELECT COUNT(*) FROM lessons")
                lesson_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM posting_history")
                history_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM bot_config")
                config_count = cursor.fetchone()[0]
                
                # Get database size
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                db_size = page_count * page_size
                
                # Get last posting
                cursor.execute("""
                    SELECT posted_at FROM posting_history 
                    WHERE success = 1 
                    ORDER BY posted_at DESC 
                    LIMIT 1
                """)
                last_success = cursor.fetchone()
                last_successful_post = last_success[0] if last_success else None
                
                return {
                    'lesson_count': lesson_count,
                    'history_count': history_count,
                    'config_count': config_count,
                    'database_size_bytes': db_size,
                    'last_successful_post': last_successful_post,
                    'database_path': str(self.db_path),
                    'initialized': self._initialized
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global database manager instance
_db_manager = None

def get_database_manager(db_path: str = "lessons.db") -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager