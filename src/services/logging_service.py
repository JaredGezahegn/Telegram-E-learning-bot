"""Comprehensive logging service for the Telegram English Bot."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from enum import Enum

from src.config import get_config


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log category enumeration for better organization."""
    SYSTEM = "SYSTEM"
    BOT_CONTROLLER = "BOT_CONTROLLER"
    SCHEDULER = "SCHEDULER"
    LESSON_MANAGER = "LESSON_MANAGER"
    DATABASE = "DATABASE"
    POSTING = "POSTING"
    MONITORING = "MONITORING"
    ERROR_HANDLING = "ERROR_HANDLING"
    PERFORMANCE = "PERFORMANCE"
    NETWORK = "NETWORK"
    RECOVERY = "RECOVERY"


@dataclass
class LogEntry:
    """Structured log entry for consistent logging."""
    timestamp: datetime
    level: str
    category: str
    component: str
    message: str
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'category': self.category,
            'component': self.component,
            'message': self.message,
            'details': self.details,
            'correlation_id': self.correlation_id
        }
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict())


class LoggingService:
    """Comprehensive logging service with structured logging and monitoring."""
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize logging service.
        
        Args:
            log_dir: Directory to store log files
        """
        self.config = get_config()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Log retention settings
        self.max_log_files = 30  # Keep 30 days of logs
        self.max_file_size = 10 * 1024 * 1024  # 10MB per file
        
        # Statistics tracking
        self._log_stats = {
            'total_logs': 0,
            'logs_by_level': {level.value: 0 for level in LogLevel},
            'logs_by_category': {cat.value: 0 for cat in LogCategory},
            'session_start': datetime.utcnow()
        }
        
        # Initialize loggers
        self._setup_loggers()
        
        self.log_system_startup()
    
    def _setup_loggers(self) -> None:
        """Set up logging configuration with multiple handlers."""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
        
        # Main log file handler (rotating)
        main_log_file = self.log_dir / "telegram_bot.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.max_log_files
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Error log file handler
        error_log_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Posting activity log (separate file for posting history)
        posting_log_file = self.log_dir / "posting_activity.log"
        self.posting_logger = logging.getLogger("posting_activity")
        posting_handler = logging.handlers.RotatingFileHandler(
            posting_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.max_log_files
        )
        posting_handler.setFormatter(detailed_formatter)
        self.posting_logger.addHandler(posting_handler)
        self.posting_logger.setLevel(logging.INFO)
        
        # Structured log file (JSON format)
        structured_log_file = self.log_dir / "structured.jsonl"
        self.structured_handler = logging.FileHandler(structured_log_file)
        self.structured_logger = logging.getLogger("structured")
        self.structured_logger.addHandler(self.structured_handler)
        self.structured_logger.setLevel(logging.DEBUG)
    
    def log_system_startup(self) -> None:
        """Log system startup information."""
        startup_info = {
            'python_version': sys.version,
            'log_level': self.config.log_level,
            'log_directory': str(self.log_dir),
            'config_valid': True
        }
        
        try:
            self.config.validate()
        except Exception as e:
            startup_info['config_valid'] = False
            startup_info['config_error'] = str(e)
        
        self.log_structured(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            "system_startup",
            "System startup initiated",
            startup_info
        )
    
    def log_structured(self, level: LogLevel, category: LogCategory, 
                      component: str, message: str, 
                      details: Optional[Dict[str, Any]] = None,
                      correlation_id: Optional[str] = None) -> None:
        """
        Log a structured message.
        
        Args:
            level: Log level
            category: Log category
            component: Component name
            message: Log message
            details: Additional details dictionary
            correlation_id: Optional correlation ID for tracking related logs
        """
        # Update statistics
        self._log_stats['total_logs'] += 1
        self._log_stats['logs_by_level'][level.value] += 1
        self._log_stats['logs_by_category'][category.value] += 1
        
        # Create log entry
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level.value,
            category=category.value,
            component=component,
            message=message,
            details=details,
            correlation_id=correlation_id
        )
        
        # Log to structured file
        self.structured_logger.info(entry.to_json())
        
        # Log to standard logger
        logger = logging.getLogger(component)
        log_method = getattr(logger, level.value.lower())
        
        if details:
            log_method(f"{message} - Details: {details}")
        else:
            log_method(message)
    
    def log_posting_attempt(self, lesson_id: Optional[int], success: bool,
                           error_message: Optional[str] = None,
                           retry_count: int = 0,
                           message_id: Optional[int] = None,
                           correlation_id: Optional[str] = None) -> None:
        """
        Log a lesson posting attempt.
        
        Args:
            lesson_id: ID of the lesson being posted
            success: Whether posting was successful
            error_message: Error message if posting failed
            retry_count: Number of retry attempts
            message_id: Telegram message ID if successful
            correlation_id: Correlation ID for tracking
        """
        details = {
            'lesson_id': lesson_id,
            'success': success,
            'retry_count': retry_count,
            'message_id': message_id
        }
        
        if error_message:
            details['error_message'] = error_message
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Lesson posting {'succeeded' if success else 'failed'}"
        
        if lesson_id:
            message += f" for lesson {lesson_id}"
        
        if retry_count > 0:
            message += f" after {retry_count} retries"
        
        self.log_structured(
            level,
            LogCategory.POSTING,
            "posting_service",
            message,
            details,
            correlation_id
        )
        
        # Also log to posting activity logger
        self.posting_logger.info(f"{message} - {details}")
    
    def log_scheduler_event(self, event_type: str, details: Dict[str, Any],
                           correlation_id: Optional[str] = None) -> None:
        """
        Log scheduler-related events.
        
        Args:
            event_type: Type of scheduler event
            details: Event details
            correlation_id: Correlation ID for tracking
        """
        self.log_structured(
            LogLevel.INFO,
            LogCategory.SCHEDULER,
            "scheduler_service",
            f"Scheduler event: {event_type}",
            details,
            correlation_id
        )
    
    def log_database_operation(self, operation: str, success: bool,
                              details: Optional[Dict[str, Any]] = None,
                              error: Optional[str] = None) -> None:
        """
        Log database operations.
        
        Args:
            operation: Database operation name
            success: Whether operation was successful
            details: Operation details
            error: Error message if operation failed
        """
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Database operation '{operation}' {'succeeded' if success else 'failed'}"
        
        log_details = details or {}
        if error:
            log_details['error'] = error
        
        self.log_structured(
            level,
            LogCategory.DATABASE,
            "database_service",
            message,
            log_details
        )
    
    def log_bot_controller_event(self, event_type: str, success: bool,
                                details: Optional[Dict[str, Any]] = None,
                                error: Optional[str] = None) -> None:
        """
        Log bot controller events.
        
        Args:
            event_type: Type of bot controller event
            success: Whether event was successful
            details: Event details
            error: Error message if event failed
        """
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Bot controller event '{event_type}' {'succeeded' if success else 'failed'}"
        
        log_details = details or {}
        if error:
            log_details['error'] = error
        
        self.log_structured(
            level,
            LogCategory.BOT_CONTROLLER,
            "bot_controller",
            message,
            log_details
        )
    
    def log_system_health(self, health_status: str, metrics: Dict[str, Any]) -> None:
        """
        Log system health information.
        
        Args:
            health_status: Overall health status
            metrics: Health metrics
        """
        self.log_structured(
            LogLevel.INFO,
            LogCategory.MONITORING,
            "health_monitor",
            f"System health check: {health_status}",
            metrics
        )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any],
                              component: str = "unknown") -> None:
        """
        Log an error with full context information.
        
        Args:
            error: Exception that occurred
            context: Context information
            component: Component where error occurred
        """
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        
        # Add stack trace for debugging
        import traceback
        error_details['stack_trace'] = traceback.format_exc()
        
        self.log_structured(
            LogLevel.ERROR,
            LogCategory.ERROR_HANDLING,
            component,
            f"Error occurred in {component}",
            error_details
        )
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get logging statistics.
        
        Returns:
            Dictionary with logging statistics
        """
        uptime = datetime.utcnow() - self._log_stats['session_start']
        
        return {
            'session_start': self._log_stats['session_start'].isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'total_logs': self._log_stats['total_logs'],
            'logs_by_level': self._log_stats['logs_by_level'].copy(),
            'logs_by_category': self._log_stats['logs_by_category'].copy(),
            'log_files': self._get_log_file_info()
        }
    
    def _get_log_file_info(self) -> List[Dict[str, Any]]:
        """Get information about log files."""
        log_files = []
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                stat = log_file.stat()
                log_files.append({
                    'name': log_file.name,
                    'size_bytes': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                logging.error(f"Error getting info for log file {log_file}: {e}")
        
        return log_files
    
    def cleanup_old_logs(self) -> Dict[str, Any]:
        """
        Clean up old log files.
        
        Returns:
            Cleanup results
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.max_log_files)
        deleted_files = []
        errors = []
        
        try:
            for log_file in self.log_dir.glob("*.log*"):
                try:
                    file_modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_modified < cutoff_date:
                        log_file.unlink()
                        deleted_files.append(log_file.name)
                except Exception as e:
                    errors.append(f"Error deleting {log_file.name}: {e}")
            
            self.log_structured(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "log_cleanup",
                f"Log cleanup completed. Deleted {len(deleted_files)} files",
                {
                    'deleted_files': deleted_files,
                    'errors': errors
                }
            )
            
        except Exception as e:
            self.log_error_with_context(e, {'operation': 'log_cleanup'}, "log_cleanup")
            errors.append(str(e))
        
        return {
            'deleted_files': deleted_files,
            'errors': errors,
            'cleanup_date': cutoff_date.isoformat()
        }
    
    def export_logs(self, start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   level_filter: Optional[LogLevel] = None,
                   category_filter: Optional[LogCategory] = None) -> List[Dict[str, Any]]:
        """
        Export logs with optional filtering.
        
        Args:
            start_date: Start date for log export
            end_date: End date for log export
            level_filter: Filter by log level
            category_filter: Filter by log category
            
        Returns:
            List of log entries matching filters
        """
        exported_logs = []
        
        try:
            structured_log_file = self.log_dir / "structured.jsonl"
            
            if not structured_log_file.exists():
                return exported_logs
            
            with open(structured_log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Apply filters
                        log_timestamp = datetime.fromisoformat(log_entry['timestamp'])
                        
                        if start_date and log_timestamp < start_date:
                            continue
                        
                        if end_date and log_timestamp > end_date:
                            continue
                        
                        if level_filter and log_entry['level'] != level_filter.value:
                            continue
                        
                        if category_filter and log_entry['category'] != category_filter.value:
                            continue
                        
                        exported_logs.append(log_entry)
                        
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logging.warning(f"Error parsing log line: {e}")
                        continue
            
        except Exception as e:
            self.log_error_with_context(e, {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'level_filter': level_filter.value if level_filter else None,
                'category_filter': category_filter.value if category_filter else None
            }, "log_export")
        
        return exported_logs
    
    def shutdown(self) -> None:
        """Shutdown logging service and cleanup."""
        self.log_structured(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            "logging_service",
            "Logging service shutting down",
            self.get_log_statistics()
        )
        
        # Close all handlers
        for handler in logging.getLogger().handlers:
            handler.close()


# Global logging service instance
_logging_service = None

def get_logging_service() -> LoggingService:
    """Get the global logging service instance."""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service

def setup_logging(log_dir: str = "logs") -> LoggingService:
    """Set up and return logging service."""
    global _logging_service
    _logging_service = LoggingService(log_dir)
    return _logging_service