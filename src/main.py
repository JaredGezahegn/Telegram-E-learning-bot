"""Main application entry point for Telegram English Bot."""

import asyncio
import logging
import sys
import signal
from typing import Optional

from src.config import get_config
from src.services.system_integration_service import (
    get_system_integration_service, 
    initialize_system_services, 
    shutdown_system_services
)
from src.services.logging_service import get_logging_service, LogLevel, LogCategory
from src.services.health_service import start_health_service, stop_health_service


# Global references for graceful shutdown
integration_service: Optional[object] = None
shutdown_event = asyncio.Event()


def setup_logging():
    """Configure logging based on configuration."""
    config = get_config()
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
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
    """Main async application entry point."""
    global integration_service
    
    logger = logging.getLogger(__name__)
    logging_service = get_logging_service()
    
    try:
        # Validate configuration
        config = get_config()
        config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize system services
        logger.info("Initializing system services...")
        if not await initialize_system_services():
            logger.error("Failed to initialize system services")
            return 1
        
        # Start health check service for deployment platforms
        start_health_service(port=8000)
        
        integration_service = get_system_integration_service()
        
        # Log successful startup
        logging_service.log_structured(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            "application_startup",
            "Telegram English Bot started successfully",
            {
                'config_valid': True,
                'services_initialized': True,
                'graceful_degradation_enabled': config.enable_graceful_degradation
            }
        )
        
        logger.info("Telegram English Bot started successfully")
        logger.info("System is running with error handling and resilience features")
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        logging_service.log_error_with_context(
            e, {'operation': 'application_startup'}, 'main_application'
        )
        return 1
    
    finally:
        # Graceful shutdown
        logger.info("Shutting down system services...")
        try:
            # Stop health service first
            stop_health_service()
            
            await shutdown_system_services()
            logger.info("System services shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Starting Telegram English Bot with enhanced error handling...")
        
        # Run the async main function
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error(f"Critical error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()