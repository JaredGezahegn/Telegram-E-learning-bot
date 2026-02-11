#!/usr/bin/env python3
"""
Post a lesson immediately to test the bot.
This bypasses the scheduler and posts right away.
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def post_now():
    """Post a lesson immediately."""
    try:
        logger.info("=" * 60)
        logger.info("IMMEDIATE LESSON POST TEST")
        logger.info("=" * 60)
        
        # Initialize components
        from src.config import get_config
        from src.services.lesson_manager import LessonManager
        from src.services.bot_controller import create_bot_controller
        
        config = get_config()
        config.validate()
        logger.info("Configuration validated")
        
        lesson_manager = LessonManager()
        logger.info("Lesson manager initialized")
        
        bot_controller = await create_bot_controller()
        if not bot_controller:
            logger.error("Failed to create bot controller")
            return False
        logger.info("Bot controller created")
        
        # Get next lesson
        lesson = lesson_manager.get_next_lesson_to_post()
        if not lesson:
            logger.error("No lessons available!")
            return False
        
        logger.info(f"Selected lesson: {lesson.title}")
        logger.info(f"Category: {lesson.category}")
        logger.info(f"Difficulty: {lesson.difficulty}")
        
        # Post the lesson
        logger.info("\nPosting lesson to channel...")
        result = await bot_controller.send_lesson(lesson)
        
        if result['success']:
            logger.info("SUCCESS! Lesson posted to channel")
            logger.info(f"Message ID: {result.get('message_id')}")
            
            # Mark as posted
            lesson_manager.mark_lesson_posted(lesson.id)
            logger.info("Lesson marked as posted in database")
            
            # Post quiz if enabled
            if config.enable_quizzes:
                logger.info("\nGenerating and posting quiz...")
                from src.services.quiz_generator import QuizGenerator
                quiz_gen = QuizGenerator()
                quiz = quiz_gen.generate_quiz_for_lesson(lesson)
                
                if quiz:
                    quiz_result = await bot_controller.send_quiz_poll(quiz, delay_minutes=0)
                    if quiz_result['success']:
                        logger.info("SUCCESS! Quiz posted to channel")
                        logger.info(f"Quiz message ID: {quiz_result.get('message_id')}")
                    else:
                        logger.warning(f"Quiz posting failed: {quiz_result.get('error')}")
                else:
                    logger.warning("Quiz generation failed")
            
            logger.info("\n" + "=" * 60)
            logger.info("TEST COMPLETE - Check your Telegram channel!")
            logger.info("=" * 60)
            return True
        else:
            logger.error(f"FAILED to post lesson: {result.get('error')}")
            return False
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'bot_controller' in locals() and bot_controller:
            await bot_controller.close()

if __name__ == "__main__":
    success = asyncio.run(post_now())
    sys.exit(0 if success else 1)
