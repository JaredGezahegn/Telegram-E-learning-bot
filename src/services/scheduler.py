"""Scheduling service for automated daily lesson posting."""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, Callable
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from src.config import get_config
from src.models.lesson import Lesson
from src.models.posting_history import PostingHistory
from .lesson_manager import LessonManager
from .bot_controller import BotController
from .quiz_generator import QuizGenerator
from .resilience_service import get_resilience_service, ErrorSeverity


logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages automated daily lesson posting with APScheduler."""
    
    def __init__(self, lesson_manager: LessonManager, bot_controller: BotController):
        """
        Initialize scheduler service.
        
        Args:
            lesson_manager: Lesson management service
            bot_controller: Bot controller for sending messages
        """
        self.lesson_manager = lesson_manager
        self.bot_controller = bot_controller
        self.config = get_config()
        self.resilience_service = get_resilience_service()
        self.quiz_generator = QuizGenerator()
        
        # Quiz configuration
        self.enable_quizzes = self.config.enable_quizzes
        self.quiz_delay_minutes = self.config.quiz_delay_minutes
        
        # Initialize scheduler with async support
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of a job at a time
            'misfire_grace_time': 3600  # Allow 1 hour grace time for missed jobs
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone(self.config.timezone)
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        self.scheduler.add_listener(self._job_missed_listener, EVENT_JOB_MISSED)
        
        self._running = False
        self._daily_job_id = "daily_lesson_post"
        
    async def start(self) -> bool:
        """
        Start the scheduler service.
        
        Returns:
            True if started successfully, False otherwise.
        """
        try:
            if self._running:
                logger.warning("Scheduler is already running")
                return True
            
            # Validate configuration
            self._validate_config()
            
            # Schedule the daily posting job
            await self._schedule_daily_posting()
            
            # Start the scheduler
            self.scheduler.start()
            self._running = True
            
            logger.info(f"Scheduler started successfully. Daily posting at {self.config.posting_time} {self.config.timezone}")
            
            # Check for missed posts on startup
            await self._check_missed_posts()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the scheduler service."""
        try:
            if not self._running:
                logger.warning("Scheduler is not running")
                return
            
            self.scheduler.shutdown(wait=True)
            self._running = False
            
            logger.info("Scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def _validate_config(self) -> None:
        """Validate scheduler configuration."""
        try:
            # Validate posting time format
            time_parts = self.config.posting_time.split(":")
            if len(time_parts) != 2:
                raise ValueError("Invalid posting time format")
            
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Invalid posting time values")
            
            # Validate timezone
            try:
                pytz.timezone(self.config.timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f"Unknown timezone: {self.config.timezone}")
            
        except Exception as e:
            raise ValueError(f"Scheduler configuration validation failed: {e}")
    
    async def _schedule_daily_posting(self) -> None:
        """Schedule the daily lesson posting job."""
        try:
            # Parse posting time
            hour, minute = map(int, self.config.posting_time.split(":"))
            
            # Create cron trigger for daily execution
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.config.timezone
            )
            
            # Add the job
            self.scheduler.add_job(
                func=self._execute_daily_post,
                trigger=trigger,
                id=self._daily_job_id,
                name="Daily Lesson Posting",
                replace_existing=True
            )
            
            logger.info(f"Daily posting job scheduled for {hour:02d}:{minute:02d} {self.config.timezone}")
            
        except Exception as e:
            logger.error(f"Failed to schedule daily posting: {e}")
            raise
    
    async def _execute_daily_post(self) -> Dict[str, Any]:
        """
        Execute the daily lesson posting job with resilience support.
        
        Returns:
            Dictionary with execution results.
        """
        execution_start = datetime.utcnow()
        logger.info("Starting daily lesson posting job")
        
        try:
            async with self.resilience_service.resilient_operation("daily_post", "scheduler"):
                # Get next lesson to post
                lesson = self.lesson_manager.get_next_lesson_to_post()
                
                if not lesson:
                    error_msg = "No lessons available for posting"
                    logger.error(error_msg)
                    await self._record_posting_history(None, False, error_msg)
                    
                    # Handle as medium severity error
                    await self.resilience_service.handle_operation_failure(
                        "daily_post", Exception(error_msg), ErrorSeverity.MEDIUM,
                        {'reason': 'no_lessons_available'}
                    )
                    
                    return {
                        'success': False,
                        'error': error_msg,
                        'timestamp': execution_start
                    }
                
                logger.info(f"Selected lesson {lesson.id}: {lesson.title}")
                
                # Send the lesson
                send_result = await self.bot_controller.send_lesson(lesson)
                
                if send_result['success']:
                    # Mark lesson as posted
                    self.lesson_manager.mark_lesson_posted(lesson.id)
                    
                    # Record successful posting
                    await self._record_posting_history(
                        lesson.id, 
                        True, 
                        None, 
                        send_result.get('attempts', 1)
                    )
                    
                    logger.info(f"Daily lesson posted successfully: {lesson.title}")
                    
                    # Schedule quiz if enabled
                    if self.enable_quizzes:
                        quiz_run_time = datetime.now(pytz.timezone(self.config.timezone)) + timedelta(minutes=self.quiz_delay_minutes)
                        logger.info(f"Scheduling quiz for lesson {lesson.id} in {self.quiz_delay_minutes} minutes")
                        logger.info(f"Quiz will run at: {quiz_run_time}")
                        
                        try:
                            self.scheduler.add_job(
                                func=self._post_quiz_for_lesson_sync,
                                trigger='date',
                                run_date=quiz_run_time,
                                args=[lesson],
                                id=f"quiz_for_lesson_{lesson.id}",
                                name=f"Quiz for {lesson.title}",
                                replace_existing=True
                            )
                            logger.info(f"Quiz job successfully scheduled for lesson {lesson.id}")
                        except Exception as e:
                            logger.error(f"Failed to schedule quiz job for lesson {lesson.id}: {e}")
                    else:
                        logger.info("Quizzes are disabled - no quiz scheduled")
                    
                    return {
                        'success': True,
                        'lesson_id': lesson.id,
                        'lesson_title': lesson.title,
                        'message_id': send_result.get('message_id'),
                        'attempts': send_result.get('attempts', 1),
                        'quiz_scheduled': self.enable_quizzes,
                        'timestamp': execution_start
                    }
                else:
                    # Record failed posting
                    error_msg = send_result.get('error', 'Unknown error')
                    await self._record_posting_history(
                        lesson.id, 
                        False, 
                        error_msg, 
                        send_result.get('attempts', 1)
                    )
                    
                    logger.error(f"Failed to post daily lesson: {error_msg}")
                    
                    # Determine error severity based on error type
                    severity = ErrorSeverity.HIGH if send_result.get('permanent_error') else ErrorSeverity.MEDIUM
                    
                    # Handle posting failure
                    await self.resilience_service.handle_operation_failure(
                        "daily_post", Exception(error_msg), severity,
                        {
                            'lesson_id': lesson.id,
                            'attempts': send_result.get('attempts', 1),
                            'permanent_error': send_result.get('permanent_error', False),
                            'circuit_breaker_open': send_result.get('circuit_breaker_open', False)
                        }
                    )
                    
                    return {
                        'success': False,
                        'lesson_id': lesson.id,
                        'error': error_msg,
                        'attempts': send_result.get('attempts', 1),
                        'timestamp': execution_start
                    }
                    
        except Exception as e:
            error_msg = f"Unexpected error in daily posting job: {e}"
            logger.error(error_msg)
            
            await self._record_posting_history(None, False, error_msg)
            
            # Handle as critical error
            await self.resilience_service.handle_operation_failure(
                "daily_post", e, ErrorSeverity.CRITICAL,
                {'execution_start': execution_start.isoformat()}
            )
            
            return {
                'success': False,
                'error': error_msg,
                'timestamp': execution_start
            }
    
    async def _record_posting_history(self, lesson_id: Optional[int], success: bool, 
                                    error_message: Optional[str] = None, 
                                    retry_count: int = 1) -> None:
        """
        Record posting attempt in history.
        
        Args:
            lesson_id: ID of the lesson (None if no lesson selected)
            success: Whether posting was successful
            error_message: Error message if posting failed
            retry_count: Number of retry attempts made
        """
        try:
            history = PostingHistory(
                lesson_id=lesson_id,
                posted_at=datetime.utcnow(),
                success=success,
                error_message=error_message,
                retry_count=retry_count
            )
            
            # Store in database (assuming PostingHistory has a save method or repository)
            # For now, just log the history
            logger.info(f"Posting history recorded: lesson_id={lesson_id}, success={success}, retries={retry_count}")
            
        except Exception as e:
            logger.error(f"Failed to record posting history: {e}")
    
    async def _post_quiz_for_lesson(self, lesson: Lesson) -> Dict[str, Any]:
        """
        Post a quiz for the given lesson.
        
        Args:
            lesson: The lesson to generate a quiz for
            
        Returns:
            Dictionary with quiz posting results
        """
        try:
            logger.info(f"Starting quiz generation for lesson {lesson.id}: {lesson.title}")
            
            # Generate quiz from lesson content
            quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
            
            if not quiz:
                error_msg = f"Failed to generate quiz for lesson {lesson.id}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': 'Quiz generation failed',
                    'lesson_id': lesson.id
                }
            
            logger.info(f"Quiz generated successfully with {len(quiz.options)} options")
            logger.info(f"Quiz question: {quiz.question}")
            
            # Send quiz to channel
            logger.info(f"Attempting to send quiz poll for lesson {lesson.id}")
            send_result = await self.bot_controller.send_quiz_poll(quiz, delay_minutes=0)
            
            if send_result['success']:
                logger.info(f"Quiz posted successfully for lesson {lesson.id}")
                logger.info(f"Quiz message ID: {send_result.get('message_id')}")
                return {
                    'success': True,
                    'lesson_id': lesson.id,
                    'quiz_id': quiz.id,
                    'message_id': send_result.get('message_id')
                }
            else:
                error_msg = send_result.get('error', 'Unknown error')
                logger.error(f"Failed to post quiz for lesson {lesson.id}: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'lesson_id': lesson.id
                }
                
        except Exception as e:
            error_msg = f"Exception in quiz posting for lesson {lesson.id}: {e}"
            logger.error(error_msg)
            # Log full traceback for debugging
            import traceback
            logger.error(f"Quiz posting traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'lesson_id': lesson.id
            }
    
    def _post_quiz_for_lesson_sync(self, lesson: Lesson) -> None:
        """
        Synchronous wrapper for posting quiz (for APScheduler).
        
        Args:
            lesson: The lesson to generate a quiz for
        """
        import asyncio
        
        async def run_quiz_post():
            """Run the quiz posting in a proper async context."""
            try:
                result = await self._post_quiz_for_lesson(lesson)
                logger.info(f"Quiz posting completed for lesson {lesson.id}: {result}")
                return result
            except Exception as e:
                logger.error(f"Quiz posting failed for lesson {lesson.id}: {e}")
                return {'success': False, 'error': str(e)}
        
        try:
            # Always use asyncio.run to ensure proper execution
            result = asyncio.run(run_quiz_post())
            logger.info(f"Quiz sync wrapper completed for lesson {lesson.id}")
        except Exception as e:
            logger.error(f"Error in quiz sync wrapper for lesson {lesson.id}: {e}")
            # Log the full traceback for debugging
            import traceback
            logger.error(f"Quiz sync wrapper traceback: {traceback.format_exc()}")
    
    async def _check_missed_posts(self) -> None:
        """Check for and handle missed posts on startup."""
        try:
            # Get the last successful post time (this would need to be implemented in PostingHistory)
            # For now, we'll implement basic missed post detection
            
            current_time = datetime.now(pytz.timezone(self.config.timezone))
            posting_time_today = self._get_posting_time_for_date(current_time.date())
            
            # If current time is past today's posting time, check if we posted today
            if current_time > posting_time_today:
                # Check if we need to post today (this would require checking PostingHistory)
                logger.info("Checking for missed posts...")
                
                # For now, just log that we're checking
                # In a full implementation, this would:
                # 1. Check PostingHistory for today's posts
                # 2. If no successful post found, trigger immediate posting
                # 3. Handle catch-up logic for multiple missed days
                
        except Exception as e:
            logger.error(f"Error checking missed posts: {e}")
    
    def _get_posting_time_for_date(self, date) -> datetime:
        """
        Get the posting datetime for a specific date.
        
        Args:
            date: Date to get posting time for
            
        Returns:
            Datetime object for posting time on that date
        """
        hour, minute = map(int, self.config.posting_time.split(":"))
        tz = pytz.timezone(self.config.timezone)
        
        return tz.localize(datetime.combine(date, time(hour, minute)))
    
    async def trigger_immediate_post(self) -> Dict[str, Any]:
        """
        Trigger an immediate lesson post (for testing or catch-up).
        
        Returns:
            Dictionary with posting results.
        """
        logger.info("Triggering immediate lesson post")
        return await self._execute_daily_post()
    
    async def reschedule_daily_posting(self, new_time: str, new_timezone: Optional[str] = None) -> bool:
        """
        Reschedule the daily posting time.
        
        Args:
            new_time: New posting time in HH:MM format
            new_timezone: Optional new timezone
            
        Returns:
            True if rescheduled successfully, False otherwise.
        """
        try:
            # Validate new time format
            time_parts = new_time.split(":")
            if len(time_parts) != 2:
                raise ValueError("Invalid time format")
            
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Invalid time values")
            
            # Validate timezone if provided
            timezone = new_timezone or self.config.timezone
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f"Unknown timezone: {timezone}")
            
            # Remove existing job
            if self.scheduler.get_job(self._daily_job_id):
                self.scheduler.remove_job(self._daily_job_id)
            
            # Update config (this would need to be persisted in a real implementation)
            self.config.posting_time = new_time
            if new_timezone:
                self.config.timezone = new_timezone
            
            # Reschedule
            await self._schedule_daily_posting()
            
            logger.info(f"Daily posting rescheduled to {new_time} {timezone}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reschedule daily posting: {e}")
            return False
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get the next scheduled run time.
        
        Returns:
            Next run time or None if not scheduled.
        """
        try:
            job = self.scheduler.get_job(self._daily_job_id)
            if job:
                return job.next_run_time
            return None
        except Exception as e:
            logger.error(f"Error getting next run time: {e}")
            return None
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get scheduler status information.
        
        Returns:
            Dictionary with scheduler status.
        """
        try:
            next_run = self.get_next_run_time()
            
            return {
                'running': self._running,
                'next_run_time': next_run.isoformat() if next_run else None,
                'posting_time': self.config.posting_time,
                'timezone': self.config.timezone,
                'job_count': len(self.scheduler.get_jobs()),
                'scheduler_state': self.scheduler.state
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {
                'running': False,
                'error': str(e)
            }
    
    # Event listeners
    def _job_executed_listener(self, event) -> None:
        """Handle job execution events."""
        logger.info(f"Job {event.job_id} executed successfully")
    
    def _job_error_listener(self, event) -> None:
        """Handle job error events."""
        logger.error(f"Job {event.job_id} failed with error: {event.exception}")
    
    def _job_missed_listener(self, event) -> None:
        """Handle missed job events."""
        logger.warning(f"Job {event.job_id} was missed. Scheduled time: {event.scheduled_run_time}")
        
        # Trigger immediate execution for missed daily posts
        if event.job_id == self._daily_job_id:
            logger.info("Triggering immediate execution for missed daily post")
            # Schedule immediate execution
            asyncio.create_task(self.trigger_immediate_post())


# Convenience function for creating scheduler service
async def create_scheduler_service(lesson_manager: LessonManager, 
                                 bot_controller: BotController) -> Optional[SchedulerService]:
    """
    Create and start a scheduler service.
    
    Args:
        lesson_manager: Lesson management service
        bot_controller: Bot controller for sending messages
        
    Returns:
        Started SchedulerService instance or None if startup failed.
    """
    scheduler = SchedulerService(lesson_manager, bot_controller)
    
    if await scheduler.start():
        return scheduler
    else:
        await scheduler.stop()
        return None