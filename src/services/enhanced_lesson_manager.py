"""Enhanced lesson manager that handles both lessons and quizzes."""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .lesson_manager import LessonManager
from .lesson_selector import LessonSelector
from .quiz_generator import QuizGenerator
from .bot_controller import BotController
from ..models.lesson import Lesson
from ..models.quiz import Quiz


logger = logging.getLogger(__name__)


class EnhancedLessonManager(LessonManager):
    """Enhanced lesson manager with quiz functionality."""
    
    def __init__(self, lesson_repository=None, bot_controller: Optional[BotController] = None, db_path: str = "lessons.db"):
        """Initialize enhanced lesson manager."""
        if lesson_repository:
            # If a repository is provided, create a custom initialization
            self.repository = lesson_repository
            self.selector = LessonSelector(lesson_repository, cycle_days=30)
        else:
            # Use default initialization from parent
            super().__init__(db_path)
        
        self.bot_controller = bot_controller
        self.quiz_generator = QuizGenerator()
        self.quiz_delay_minutes = 5  # Wait 5 minutes after lesson before posting quiz
    
    async def post_lesson_with_quiz(self, lesson: Optional[Lesson] = None) -> Dict[str, Any]:
        """Post a lesson and follow up with a quiz.
        
        Args:
            lesson: Specific lesson to post, or None to select automatically.
            
        Returns:
            Dictionary with results of both lesson and quiz posting.
        """
        if not self.bot_controller:
            raise RuntimeError("Bot controller not initialized")
        
        result = {
            'lesson_posted': False,
            'quiz_posted': False,
            'lesson_result': None,
            'quiz_result': None,
            'lesson': None,
            'quiz': None,
            'timestamp': datetime.utcnow()
        }
        
        try:
            # Get lesson to post
            if not lesson:
                lesson = self.get_next_lesson()
            
            if not lesson:
                logger.warning("No lesson available to post")
                result['error'] = "No lesson available"
                return result
            
            result['lesson'] = lesson
            logger.info(f"Posting lesson: {lesson.title} (ID: {lesson.id})")
            
            # Post the lesson
            lesson_result = await self.bot_controller.send_lesson(lesson)
            result['lesson_result'] = lesson_result
            result['lesson_posted'] = lesson_result.get('success', False)
            
            if not result['lesson_posted']:
                logger.error(f"Failed to post lesson: {lesson_result.get('error')}")
                return result
            
            # Update lesson usage
            if hasattr(self, 'repository') and hasattr(self.repository, 'update_lesson_usage'):
                self.repository.update_lesson_usage(lesson.id)
            else:
                logger.warning("Could not update lesson usage - method not available")
            
            # Generate quiz for the lesson
            logger.info(f"Generating quiz for lesson: {lesson.title}")
            quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
            
            if not quiz:
                logger.warning(f"Could not generate quiz for lesson {lesson.id}")
                result['quiz_error'] = "Quiz generation failed"
                return result
            
            result['quiz'] = quiz
            logger.info(f"Generated quiz: {quiz.question[:50]}...")
            
            # Post the quiz after delay
            logger.info(f"Scheduling quiz to post in {self.quiz_delay_minutes} minutes")
            quiz_result = await self.bot_controller.send_quiz_poll(quiz, self.quiz_delay_minutes)
            result['quiz_result'] = quiz_result
            result['quiz_posted'] = quiz_result.get('success', False)
            
            if result['quiz_posted']:
                logger.info(f"Successfully posted lesson and quiz for: {lesson.title}")
            else:
                logger.warning(f"Lesson posted but quiz failed: {quiz_result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in post_lesson_with_quiz: {e}")
            result['error'] = str(e)
            return result
    
    async def post_daily_lesson_with_quiz(self) -> Dict[str, Any]:
        """Post the daily lesson with quiz (scheduled method)."""
        logger.info("Starting daily lesson and quiz posting")
        
        try:
            result = await self.post_lesson_with_quiz()
            
            # Log summary
            if result['lesson_posted'] and result['quiz_posted']:
                logger.info("✅ Daily lesson and quiz posted successfully")
            elif result['lesson_posted']:
                logger.warning("⚠️ Daily lesson posted, but quiz failed")
            else:
                logger.error("❌ Daily lesson posting failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in daily lesson posting: {e}")
            return {
                'lesson_posted': False,
                'quiz_posted': False,
                'error': str(e),
                'timestamp': datetime.utcnow()
            }
    
    def set_quiz_delay(self, minutes: int) -> None:
        """Set the delay between lesson and quiz posting.
        
        Args:
            minutes: Minutes to wait between lesson and quiz.
        """
        if minutes < 0:
            raise ValueError("Quiz delay cannot be negative")
        
        self.quiz_delay_minutes = minutes
        logger.info(f"Quiz delay set to {minutes} minutes")
    
    def get_quiz_delay(self) -> int:
        """Get current quiz delay in minutes."""
        return self.quiz_delay_minutes
    
    async def test_quiz_generation(self, lesson_id: int) -> Optional[Quiz]:
        """Test quiz generation for a specific lesson.
        
        Args:
            lesson_id: ID of lesson to generate quiz for.
            
        Returns:
            Generated quiz or None if failed.
        """
        try:
            lesson = self.lesson_repository.get_lesson_by_id(lesson_id)
            if not lesson:
                logger.error(f"Lesson {lesson_id} not found")
                return None
            
            quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
            
            if quiz:
                logger.info(f"Test quiz generated for lesson {lesson_id}")
                logger.info(f"Question: {quiz.question}")
                logger.info(f"Options: {[opt.text for opt in quiz.options]}")
                logger.info(f"Correct: {quiz.get_correct_option().text}")
            else:
                logger.warning(f"Failed to generate test quiz for lesson {lesson_id}")
            
            return quiz
            
        except Exception as e:
            logger.error(f"Error testing quiz generation: {e}")
            return None