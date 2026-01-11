#!/usr/bin/env python3
"""
Simple main.py that directly starts the scheduler without complex system integration.
"""

import asyncio
import logging
import sys
import os
import signal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Global shutdown event
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

async def main_async():
    """Simple main async function."""
    logger = logging.getLogger(__name__)
    
    try:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('bot.log')
            ]
        )
        
        logger.info("Starting Telegram English Bot (Simple Version)")
        
        # Validate configuration
        from src.config import get_config
        config = get_config()
        config.validate()
        logger.info(f"Configuration validated - Database: {config.database_type}")
        
        # Start health service
        from src.services.health_service import start_health_service, stop_health_service
        start_health_service(port=8000)
        logger.info("Health service started on port 8000")
        
        # Initialize lesson manager
        from src.services.lesson_manager import LessonManager
        
        lesson_manager = LessonManager(config.database_path)
        logger.info("Lesson manager initialized")
        
        # Create bot controller
        from src.services.bot_controller import create_bot_controller
        bot_controller = await create_bot_controller()
        if not bot_controller:
            logger.error("Failed to create bot controller")
            return 1
        logger.info("Bot controller created successfully")
        
        # Create and start scheduler
        from src.services.scheduler import create_scheduler_service
        scheduler_service = await create_scheduler_service(lesson_manager, bot_controller)
        if not scheduler_service:
            logger.error("Failed to create scheduler service")
            return 1
        logger.info("Scheduler service started successfully")
        
        # Log scheduler status
        status = scheduler_service.get_scheduler_status()
        logger.info(f"Scheduler running: {status.get('running', False)}")
        logger.info(f"Next run time: {status.get('next_run_time', 'Not scheduled')}")
        logger.info(f"Posting time: {status.get('posting_time', 'Unknown')} {status.get('timezone', '')}")
        
        logger.info("🎉 Telegram English Bot started successfully!")
        logger.info("📅 Daily lessons will be posted automatically")
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Graceful shutdown
        logger.info("Shutting down...")
        try:
            if 'scheduler_service' in locals() and scheduler_service:
                await scheduler_service.stop()
                logger.info("Scheduler stopped")
            
            if 'bot_controller' in locals() and bot_controller:
                await bot_controller.close()
                logger.info("Bot controller closed")
            
            stop_health_service()
            logger.info("Health service stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

def main():
    """Main entry point."""
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the async main function
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error(f"Critical error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()