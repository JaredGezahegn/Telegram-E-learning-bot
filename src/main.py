#!/usr/bin/env python3
"""
Simple main.py that directly starts the scheduler without complex system integration.
"""

import asyncio
import logging
import sys
import os
import signal

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global shutdown event
shutdown_event = asyncio.Event()

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log')
        ]
    )

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
        setup_logging()
        
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
        
        # Initialize lesson manager (uses database factory internally)
        from src.services.lesson_manager import LessonManager
        
        lesson_manager = LessonManager()
        logger.info("Lesson manager initialized")
        
        # Create bot controller
        from src.services.bot_controller import create_bot_controller
        bot_controller = await create_bot_controller()
        if not bot_controller:
            logger.error("Failed to create bot controller")
            return 1
        logger.info("Bot controller created successfully")
        
        # Set up application for interactive features
        try:
            bot_controller.setup_application()
            logger.info("Bot application setup completed")
        except Exception as setup_error:
            logger.error(f"Failed to setup bot application: {setup_error}")
            logger.info("Attempting to continue without full application setup...")
            # Continue execution - some features may be limited but basic functionality should work
        
        # Create and start scheduler
        from src.services.scheduler import create_scheduler_service
        scheduler_service = await create_scheduler_service(lesson_manager, bot_controller)
        if not scheduler_service:
            logger.error("Failed to create scheduler service")
            return 1
        logger.info("Scheduler service started successfully")
        
        # Create and register command handler for interactive features
        from src.services.command_handler import CommandHandler
        command_handler = CommandHandler(lesson_manager, scheduler_service)
        bot_controller.register_command_handlers(command_handler)
        logger.info("Interactive command handlers registered")
        
        # Start polling for interactive features
        await bot_controller.start_polling()
        logger.info("Bot polling started for interactive features")
        
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
            if 'bot_controller' in locals() and bot_controller:
                await bot_controller.stop_polling()
                logger.info("Bot polling stopped")
            
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