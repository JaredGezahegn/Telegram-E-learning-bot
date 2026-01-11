"""Services package for the Telegram English Bot."""

from .lesson_repository import LessonRepository
from .lesson_selector import LessonSelector, SelectionStrategy
from .lesson_manager import LessonManager

# Note: BotController and SchedulerService are imported dynamically to avoid dependency issues

__all__ = [
    'LessonRepository',
    'LessonSelector',
    'SelectionStrategy',
    'LessonManager'
]