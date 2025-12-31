"""Database factory for creating appropriate repository instances."""

import logging
from typing import Union

from ..config import get_config
from .lesson_repository import LessonRepository
from .supabase_lesson_repository import SupabaseLessonRepository
from ..models.database import DatabaseManager
from ..models.supabase_database import create_supabase_manager


logger = logging.getLogger(__name__)


def create_lesson_repository() -> Union[LessonRepository, SupabaseLessonRepository]:
    """Create appropriate lesson repository based on configuration."""
    config = get_config()
    
    if config.database_type.lower() == "supabase":
        logger.info("Using Supabase lesson repository")
        try:
            return SupabaseLessonRepository()
        except Exception as e:
            logger.error(f"Failed to create Supabase repository: {e}")
            logger.info("Falling back to SQLite repository")
            return LessonRepository(config.database_path)
    else:
        logger.info("Using SQLite lesson repository")
        return LessonRepository(config.database_path)


def create_database_manager():
    """Create appropriate database manager based on configuration."""
    config = get_config()
    
    if config.database_type.lower() == "supabase":
        logger.info("Using Supabase database manager")
        try:
            return create_supabase_manager()
        except Exception as e:
            logger.error(f"Failed to create Supabase manager: {e}")
            logger.info("Falling back to SQLite database manager")
            return DatabaseManager(config.database_path)
    else:
        logger.info("Using SQLite database manager")
        return DatabaseManager(config.database_path)


def create_lesson_repository() -> Union[LessonRepository, SupabaseLessonRepository]:
    """Create appropriate lesson repository based on configuration."""
    config = get_config()
    
    if config.database_type.lower() == "supabase":
        logger.info("Using Supabase lesson repository")
        try:
            return SupabaseLessonRepository()
        except Exception as e:
            logger.error(f"Failed to create Supabase repository: {e}")
            logger.info("Falling back to SQLite repository")
            return LessonRepository(config.database_path)
    else:
        logger.info("Using SQLite lesson repository")
        return LessonRepository(config.database_path)


def get_database_info() -> dict:
    """Get information about the current database configuration."""
    config = get_config()
    
    info = {
        'type': config.database_type,
        'path': config.database_path if config.database_type == 'sqlite' else None,
        'supabase_url': config.supabase_url if config.database_type == 'supabase' else None,
        'configured': True
    }
    
    # Test connection
    try:
        repo = create_lesson_repository()
        info['connection_test'] = repo.test_connection()
    except Exception as e:
        info['connection_test'] = False
        info['error'] = str(e)
    
    return info