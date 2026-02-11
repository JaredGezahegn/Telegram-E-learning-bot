#!/usr/bin/env python3
"""
Diagnostic script to identify why the bot hangs during startup.
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def diagnose():
    """Run diagnostic checks."""
    try:
        logger.info("=== DIAGNOSTIC START ===")
        
        # Step 1: Check configuration
        logger.info("Step 1: Checking configuration...")
        from src.config import get_config
        config = get_config()
        config.validate()
        logger.info(f"✓ Configuration OK - Database: {config.database_type}")
        logger.info(f"  Posting time: {config.posting_time}")
        logger.info(f"  Timezone: {config.timezone}")
        logger.info(f"  Bot token: {config.bot_token[:20]}...")
        logger.info(f"  Channel ID: {config.channel_id}")
        
        # Step 2: Check lesson manager
        logger.info("\nStep 2: Checking lesson manager...")
        from src.services.lesson_manager import LessonManager
        lesson_manager = LessonManager()
        logger.info("✓ Lesson manager created")
        
        # Check if we have lessons
        lesson = lesson_manager.get_next_lesson_to_post()
        if lesson:
            logger.info(f"✓ Found lesson to post: {lesson.title}")
        else:
            logger.warning("⚠ No lessons available to post!")
        
        # Step 3: Check bot controller creation
        logger.info("\nStep 3: Checking bot controller creation...")
        logger.info("This is where the bot usually hangs...")
        
        from src.services.bot_controller import create_bot_controller
        logger.info("About to create bot controller...")
        
        bot_controller = await create_bot_controller()
        
        if bot_controller:
            logger.info("✓ Bot controller created successfully!")
        else:
            logger.error("✗ Bot controller creation failed!")
            return
        
        # Step 4: Check scheduler creation
        logger.info("\nStep 4: Checking scheduler creation...")
        from src.services.scheduler import create_scheduler_service
        
        scheduler_service = await create_scheduler_service(lesson_manager, bot_controller)
        
        if scheduler_service:
            logger.info("✓ Scheduler created successfully!")
            status = scheduler_service.get_scheduler_status()
            logger.info(f"  Running: {status.get('running')}")
            logger.info(f"  Next run: {status.get('next_run_time')}")
        else:
            logger.error("✗ Scheduler creation failed!")
        
        # Cleanup
        logger.info("\nCleaning up...")
        if scheduler_service:
            await scheduler_service.stop()
        if bot_controller:
            await bot_controller.close()
        
        logger.info("\n=== DIAGNOSTIC COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose())
