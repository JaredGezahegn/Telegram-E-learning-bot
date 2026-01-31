"""Telegram bot controller for managing API communication and message formatting."""

import asyncio
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
import time

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler as TelegramCommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError, BadRequest, Forbidden
from telegram.constants import ParseMode

from src.config import get_config
from src.models.lesson import Lesson
from src.models.quiz import Quiz
from .resilience_service import get_resilience_service, ErrorSeverity


logger = logging.getLogger(__name__)


class BotController:
    """Manages Telegram API communication and message formatting."""
    
    def __init__(self, bot_token: Optional[str] = None):
        """Initialize bot controller with token validation.
        
        Args:
            bot_token: Optional bot token. If not provided, uses config.
        """
        config = get_config()
        self.bot_token = bot_token or config.bot_token
        self.channel_id = config.channel_id
        self.retry_attempts = config.retry_attempts
        self.retry_delay = config.retry_delay
        
        # Initialize bot instance and application
        self.bot = Bot(token=self.bot_token)
        self.application = None
        self._validated = False
        
        # Initialize resilience service
        self.resilience_service = get_resilience_service()
        
    async def initialize(self) -> bool:
        """Initialize bot and validate token and permissions.
        
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            # Validate bot token by getting bot info
            await self._validate_token()
            
            # Verify channel permissions
            await self._verify_permissions()
            
            self._validated = True
            logger.info("Bot controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Bot initialization failed: {e}")
            return False
    
    async def _validate_token(self) -> None:
        """Validate bot token by attempting to get bot information."""
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Bot token validated. Bot username: @{bot_info.username}")
        except TelegramError as e:
            raise ValueError(f"Invalid bot token: {e}")
    
    async def _verify_permissions(self) -> None:
        """Verify bot has necessary permissions in the target channel."""
        try:
            # Get chat information to verify access
            chat = await self.bot.get_chat(self.channel_id)
            logger.info(f"Channel access verified: {chat.title}")
            
            # Get bot's member status in the channel
            bot_member = await self.bot.get_chat_member(self.channel_id, self.bot.id)
            
            # Check if bot is admin or has posting permissions
            if bot_member.status not in ['administrator', 'creator']:
                # For channels, bot needs to be admin to post
                if chat.type == 'channel':
                    raise PermissionError("Bot must be an administrator in the channel to post messages")
            
            logger.info(f"Bot permissions verified. Status: {bot_member.status}")
            
        except Forbidden as e:
            raise PermissionError(f"Bot lacks permissions for channel {self.channel_id}: {e}")
        except BadRequest as e:
            if "chat not found" in str(e).lower():
                raise ValueError(f"Channel {self.channel_id} not found or bot not added to channel")
            raise PermissionError(f"Permission error: {e}")
    
    def format_lesson_message(self, lesson: Lesson) -> str:
        """Format lesson content for Telegram with proper markup.
        
        Args:
            lesson: Lesson object to format.
            
        Returns:
            Formatted message string with Telegram HTML markup.
        """
        if not lesson or not lesson.content:
            raise ValueError("Invalid lesson content")
        
        # Convert markdown-style content to clean Telegram HTML
        message = self._convert_to_telegram_format(lesson.content)
        
        # Add footer with lesson metadata
        footer_parts = []
        if lesson.tags:
            tags_str = " ".join([f"#{tag}" for tag in lesson.tags[:3]])  # Limit to 3 tags
            footer_parts.append(f"\n\n🏷️ {tags_str}")
        
        # Add lesson ID for tracking (hidden in small text)
        footer_parts.append(f"\n\n<i>Lesson #{lesson.id}</i>")
        
        message += "".join(footer_parts)
        
        return message
    
    def _convert_to_telegram_format(self, content: str) -> str:
        """Convert markdown-style content to clean Telegram HTML format.
        
        Args:
            content: Raw lesson content with markdown formatting.
            
        Returns:
            Clean HTML formatted for Telegram.
        """
        # Start with the original content
        text = content
        
        # Convert **bold** to <b>bold</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Convert *italic* to <i>italic</i> (but not if it's part of **)
        text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
        
        # Escape HTML characters that aren't our tags
        text = self._escape_html_selective(text)
        
        # Clean up excessive whitespace while preserving intentional line breaks
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove trailing whitespace but keep the line structure
            cleaned_line = line.rstrip()
            cleaned_lines.append(cleaned_line)
        
        # Join lines back together
        text = '\n'.join(cleaned_lines)
        
        # Remove excessive empty lines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _escape_html_selective(self, text: str) -> str:
        """Escape HTML characters but preserve our formatting tags.
        
        Args:
            text: Text that may contain HTML tags we want to keep.
            
        Returns:
            Text with selective HTML escaping.
        """
        # First, protect our HTML tags
        protected_tags = []
        tag_pattern = r'<(/?)([bi])>'
        
        def protect_tag(match):
            tag = match.group(0)
            placeholder = f"__PROTECTED_TAG_{len(protected_tags)}__"
            protected_tags.append(tag)
            return placeholder
        
        text = re.sub(tag_pattern, protect_tag, text)
        
        # Now escape HTML characters
        text = self._escape_html(text)
        
        # Restore protected tags
        for i, tag in enumerate(protected_tags):
            text = text.replace(f"__PROTECTED_TAG_{i}__", tag)
        
        return text
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters for Telegram HTML parsing.
        
        Args:
            text: Text to escape.
            
        Returns:
            HTML-escaped text.
        """
        if not text:
            return ""
        
        # Replace HTML special characters (but keep quotes readable)
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            # Don't escape quotes for better readability in Telegram
            # '"': '&quot;',
            # "'": '&#x27;'
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
    
    async def send_lesson(self, lesson: Lesson) -> Dict[str, Any]:
        """Send formatted lesson to the channel with retry logic.
        
        Args:
            lesson: Lesson to send.
            
        Returns:
            Dictionary with success status and message details.
        """
        if not self._validated:
            raise RuntimeError("Bot controller not initialized. Call initialize() first.")
        
        if not lesson:
            raise ValueError("Lesson cannot be None")
        
        # Format the message
        try:
            message_text = self.format_lesson_message(lesson)
        except Exception as e:
            logger.error(f"Failed to format lesson {lesson.id}: {e}")
            return {
                'success': False,
                'error': f"Message formatting failed: {e}",
                'lesson_id': lesson.id,
                'timestamp': datetime.utcnow()
            }
        
        # Send with retry logic
        return await self._send_with_retry(message_text, lesson.id)
    
    async def _send_with_retry(self, message_text: str, lesson_id: int) -> Dict[str, Any]:
        """Send message with exponential backoff retry logic and resilience support.
        
        Args:
            message_text: Formatted message to send.
            lesson_id: ID of the lesson being sent.
            
        Returns:
            Dictionary with send result details.
        """
        last_error = None
        
        # Check circuit breaker state
        breaker_state = self.resilience_service.get_circuit_breaker_state("telegram_api")
        if breaker_state == "open":
            logger.error(f"Telegram API circuit breaker is open, skipping send attempt for lesson {lesson_id}")
            return {
                'success': False,
                'error': "Telegram API circuit breaker is open",
                'lesson_id': lesson_id,
                'timestamp': datetime.utcnow(),
                'attempts': 0,
                'circuit_breaker_open': True
            }
        
        for attempt in range(self.retry_attempts + 1):  # +1 for initial attempt
            try:
                # Use resilient operation context
                async with self.resilience_service.resilient_operation(
                    f"send_lesson_{lesson_id}", "telegram_api"
                ):
                    # Send the message
                    message = await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=message_text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                
                logger.info(f"Lesson {lesson_id} sent successfully (attempt {attempt + 1})")
                
                return {
                    'success': True,
                    'message_id': message.message_id,
                    'lesson_id': lesson_id,
                    'timestamp': datetime.utcnow(),
                    'attempts': attempt + 1
                }
                
            except (BadRequest, Forbidden) as e:
                # These errors won't be fixed by retrying - handle first before TelegramError
                logger.error(f"Permanent error sending lesson {lesson_id}: {e}")
                
                # Record failure for circuit breaker
                self.resilience_service.record_circuit_breaker_failure("telegram_api")
                
                # Handle as high severity error
                await self.resilience_service.handle_operation_failure(
                    f"send_lesson_{lesson_id}", e, ErrorSeverity.HIGH,
                    {'lesson_id': lesson_id, 'attempt': attempt + 1, 'error_type': 'permanent'}
                )
                
                return {
                    'success': False,
                    'error': str(e),
                    'lesson_id': lesson_id,
                    'timestamp': datetime.utcnow(),
                    'attempts': attempt + 1,
                    'permanent_error': True
                }
                
            except RetryAfter as e:
                # Telegram rate limiting - wait the specified time
                wait_time = e.retry_after
                logger.warning(f"Rate limited, waiting {wait_time} seconds (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                last_error = e
                
            except (TimedOut, NetworkError) as e:
                # Network-related errors - use exponential backoff and resilience handling
                if attempt < self.retry_attempts:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Network error, retrying in {wait_time} seconds (attempt {attempt + 1}): {e}")
                    
                    # Handle network error through resilience service
                    await self.resilience_service.handle_network_error(
                        e, f"send_lesson_{lesson_id}",
                        {'lesson_id': lesson_id, 'attempt': attempt + 1}
                    )
                    
                    await asyncio.sleep(wait_time)
                last_error = e
                
            except TelegramError as e:
                # Other Telegram errors - retry with backoff
                if attempt < self.retry_attempts:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Telegram error, retrying in {wait_time} seconds (attempt {attempt + 1}): {e}")
                    
                    # Handle as medium severity error
                    await self.resilience_service.handle_operation_failure(
                        f"send_lesson_{lesson_id}", e, ErrorSeverity.MEDIUM,
                        {'lesson_id': lesson_id, 'attempt': attempt + 1, 'error_type': 'telegram_api'}
                    )
                    
                    await asyncio.sleep(wait_time)
                last_error = e
                
            except Exception as e:
                # Unexpected errors
                logger.error(f"Unexpected error sending lesson {lesson_id}: {e}")
                
                # Handle as critical error
                await self.resilience_service.handle_operation_failure(
                    f"send_lesson_{lesson_id}", e, ErrorSeverity.CRITICAL,
                    {'lesson_id': lesson_id, 'attempt': attempt + 1, 'error_type': 'unexpected'}
                )
                
                return {
                    'success': False,
                    'error': f"Unexpected error: {e}",
                    'lesson_id': lesson_id,
                    'timestamp': datetime.utcnow(),
                    'attempts': attempt + 1
                }
        
        # All retry attempts failed
        logger.error(f"Failed to send lesson {lesson_id} after {self.retry_attempts + 1} attempts. Last error: {last_error}")
        
        # Record final failure for circuit breaker
        self.resilience_service.record_circuit_breaker_failure("telegram_api")
        
        # Handle final failure
        await self.resilience_service.handle_operation_failure(
            f"send_lesson_{lesson_id}", last_error or Exception("All retries exhausted"),
            ErrorSeverity.HIGH,
            {'lesson_id': lesson_id, 'total_attempts': self.retry_attempts + 1, 'final_failure': True}
        )
        
        return {
            'success': False,
            'error': str(last_error) if last_error else "Unknown error",
            'lesson_id': lesson_id,
            'timestamp': datetime.utcnow(),
            'attempts': self.retry_attempts + 1
        }
    
    async def test_connection(self) -> bool:
        """Test bot connection and permissions with resilience support.
        
        Returns:
            True if connection test successful, False otherwise.
        """
        try:
            async with self.resilience_service.resilient_operation("test_connection", "telegram_api"):
                # Test bot token
                await self._validate_token()
                
                # Test channel access
                await self._verify_permissions()
                
                # Send a test message (optional - could be used for health checks)
                # For now, just verify we can access the chat
                chat = await self.bot.get_chat(self.channel_id)
                logger.info(f"Connection test successful for channel: {chat.title}")
                
                return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            
            # Handle connection test failure
            await self.resilience_service.handle_operation_failure(
                "test_connection", e, ErrorSeverity.MEDIUM,
                {'operation': 'connection_test'}
            )
            
            return False
    
    async def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """Get bot information for monitoring and debugging.
        
        Returns:
            Dictionary with bot information or None if error.
        """
        try:
            bot_info = await self.bot.get_me()
            return {
                'id': bot_info.id,
                'username': bot_info.username,
                'first_name': bot_info.first_name,
                'can_join_groups': bot_info.can_join_groups,
                'can_read_all_group_messages': bot_info.can_read_all_group_messages,
                'supports_inline_queries': bot_info.supports_inline_queries
            }
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return None
    
    async def send_quiz_poll(self, quiz: Quiz, delay_minutes: int = 5) -> Dict[str, Any]:
        """Send a quiz as a Telegram poll after a delay.
        
        Args:
            quiz: Quiz to send as a poll.
            delay_minutes: Minutes to wait before sending the poll.
            
        Returns:
            Dictionary with success status and poll details.
        """
        if not self._validated:
            raise RuntimeError("Bot controller not initialized. Call initialize() first.")
        
        if not quiz:
            raise ValueError("Quiz cannot be None")
        
        try:
            # Validate quiz
            quiz.validate()
        except Exception as e:
            logger.error(f"Invalid quiz: {e}")
            return {
                'success': False,
                'error': f"Quiz validation failed: {e}",
                'quiz_id': quiz.id,
                'timestamp': datetime.utcnow()
            }
        
        # Wait for the specified delay
        if delay_minutes > 0:
            logger.info(f"Waiting {delay_minutes} minutes before posting quiz...")
            await asyncio.sleep(delay_minutes * 60)
        
        # Prepare poll options (Telegram polls support up to 10 options)
        poll_options = [option.text for option in quiz.options[:10]]
        correct_option_id = quiz.get_correct_option_index()
        
        if correct_option_id is None:
            logger.error(f"Quiz {quiz.id} has no correct answer")
            return {
                'success': False,
                'error': "Quiz has no correct answer",
                'quiz_id': quiz.id,
                'timestamp': datetime.utcnow()
            }
        
        # Format quiz question
        question_text = f"🧠 Quiz Time!\n\n{quiz.question}"
        
        # Send with retry logic
        return await self._send_poll_with_retry(
            question=question_text,
            options=poll_options,
            correct_option_id=correct_option_id,
            explanation=quiz.explanation,
            quiz_id=quiz.id
        )
    
    async def _send_poll_with_retry(self, question: str, options: list, correct_option_id: int, 
                                   explanation: str, quiz_id: int) -> Dict[str, Any]:
        """Send poll with retry logic."""
        last_error = None
        
        # Check circuit breaker state
        breaker_state = self.resilience_service.get_circuit_breaker_state("telegram_api")
        if breaker_state == "open":
            logger.error(f"Telegram API circuit breaker is open, skipping poll send for quiz {quiz_id}")
            return {
                'success': False,
                'error': "Telegram API circuit breaker is open",
                'quiz_id': quiz_id,
                'timestamp': datetime.utcnow(),
                'attempts': 0,
                'circuit_breaker_open': True
            }
        
        for attempt in range(self.retry_attempts + 1):
            try:
                async with self.resilience_service.resilient_operation(
                    f"send_quiz_{quiz_id}", "telegram_api"
                ):
                    # Send the poll
                    poll_message = await self.bot.send_poll(
                        chat_id=self.channel_id,
                        question=question,
                        options=options,
                        type='quiz',  # This makes it a quiz with correct answer
                        correct_option_id=correct_option_id,
                        explanation=explanation,
                        is_anonymous=True,  # Must be anonymous for channels
                        allows_multiple_answers=False
                    )
                
                logger.info(f"Quiz {quiz_id} sent successfully (attempt {attempt + 1})")
                
                return {
                    'success': True,
                    'poll_id': poll_message.poll.id,
                    'message_id': poll_message.message_id,
                    'quiz_id': quiz_id,
                    'timestamp': datetime.utcnow(),
                    'attempts': attempt + 1
                }
                
            except (BadRequest, Forbidden) as e:
                logger.error(f"Permanent error sending quiz {quiz_id}: {e}")
                self.resilience_service.record_circuit_breaker_failure("telegram_api")
                
                await self.resilience_service.handle_operation_failure(
                    f"send_quiz_{quiz_id}", e, ErrorSeverity.HIGH,
                    {'quiz_id': quiz_id, 'attempt': attempt + 1, 'error_type': 'permanent'}
                )
                
                return {
                    'success': False,
                    'error': str(e),
                    'quiz_id': quiz_id,
                    'timestamp': datetime.utcnow(),
                    'attempts': attempt + 1,
                    'permanent_error': True
                }
                
            except RetryAfter as e:
                wait_time = e.retry_after
                logger.warning(f"Rate limited, waiting {wait_time} seconds (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                last_error = e
                
            except (TimedOut, NetworkError) as e:
                if attempt < self.retry_attempts:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Network error, retrying in {wait_time} seconds (attempt {attempt + 1}): {e}")
                    
                    await self.resilience_service.handle_network_error(
                        e, f"send_quiz_{quiz_id}",
                        {'quiz_id': quiz_id, 'attempt': attempt + 1}
                    )
                    
                    await asyncio.sleep(wait_time)
                last_error = e
                
            except TelegramError as e:
                if attempt < self.retry_attempts:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Telegram error, retrying in {wait_time} seconds (attempt {attempt + 1}): {e}")
                    
                    await self.resilience_service.handle_operation_failure(
                        f"send_quiz_{quiz_id}", e, ErrorSeverity.MEDIUM,
                        {'quiz_id': quiz_id, 'attempt': attempt + 1, 'error_type': 'telegram_api'}
                    )
                    
                    await asyncio.sleep(wait_time)
                last_error = e
                
            except Exception as e:
                logger.error(f"Unexpected error sending quiz {quiz_id}: {e}")
                
                await self.resilience_service.handle_operation_failure(
                    f"send_quiz_{quiz_id}", e, ErrorSeverity.CRITICAL,
                    {'quiz_id': quiz_id, 'attempt': attempt + 1, 'error_type': 'unexpected'}
                )
                
                return {
                    'success': False,
                    'error': f"Unexpected error: {e}",
                    'quiz_id': quiz_id,
                    'timestamp': datetime.utcnow(),
                    'attempts': attempt + 1
                }
        
        # All retry attempts failed
        logger.error(f"Failed to send quiz {quiz_id} after {self.retry_attempts + 1} attempts. Last error: {last_error}")
        
        self.resilience_service.record_circuit_breaker_failure("telegram_api")
        
        await self.resilience_service.handle_operation_failure(
            f"send_quiz_{quiz_id}", last_error or Exception("All retries exhausted"),
            ErrorSeverity.HIGH,
            {'quiz_id': quiz_id, 'total_attempts': self.retry_attempts + 1, 'final_failure': True}
        )
        
        return {
            'success': False,
            'error': str(last_error) if last_error else "Unknown error",
            'quiz_id': quiz_id,
            'timestamp': datetime.utcnow(),
            'attempts': self.retry_attempts + 1
        }


    async def close(self) -> None:
        """Close bot connection and cleanup resources."""
        try:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
        except Exception as e:
            logger.error(f"Error closing application: {e}")
        
        try:
            await self.bot.close()
            logger.info("Bot controller closed successfully")
        except Exception as e:
            logger.error(f"Error closing bot controller: {e}")
    
    def setup_application(self) -> None:
        """Set up the Telegram application for handling updates."""
        if not self.application:
            try:
                # Import at the top of the method to avoid scope issues
                from telegram.ext import Application, ApplicationBuilder
                from telegram import Bot
                
                # Try the standard approach first
                self.application = Application.builder().token(self.bot_token).build()
                logger.info("Successfully created application with standard approach")
                
            except AttributeError as e:
                if "_Updater__polling_cleanup_cb" in str(e):
                    # Handle compatibility issue with newer Python versions
                    logger.warning(f"Telegram bot library compatibility issue detected: {e}")
                    logger.info("Attempting compatibility workaround...")
                    
                    try:
                        # Alternative approach for compatibility - use ApplicationBuilder directly
                        from telegram.ext import ApplicationBuilder
                        builder = ApplicationBuilder()
                        builder.token(self.bot_token)
                        
                        # Try to build with minimal configuration
                        self.application = builder.build()
                        logger.info("Successfully created application with compatibility workaround")
                        
                    except Exception as fallback_error:
                        logger.error(f"ApplicationBuilder approach failed: {fallback_error}")
                        
                        try:
                            # Last resort: create application with pre-built bot
                            from telegram.ext import Application
                            from telegram import Bot
                            bot = Bot(token=self.bot_token)
                            self.application = Application.builder().bot(bot).build()
                            logger.info("Created application with pre-built bot as last resort")
                            
                        except Exception as final_error:
                            logger.error(f"All application setup methods failed: {final_error}")
                            # Create a minimal mock application to prevent complete failure
                            self.application = None
                            logger.warning("Could not create application - interactive features will be disabled")
                            return
                else:
                    # Re-raise if it's a different AttributeError
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error setting up application: {e}")
                try:
                    # Try basic fallback with explicit imports
                    from telegram.ext import Application
                    from telegram import Bot
                    bot = Bot(token=self.bot_token)
                    self.application = Application.builder().bot(bot).build()
                    logger.info("Created application with basic fallback")
                    
                except Exception as final_error:
                    logger.error(f"All application setup methods failed: {final_error}")
                    # Set to None to prevent further errors
                    self.application = None
                    logger.warning("Could not create application - interactive features will be disabled")
                    return
    
    def register_command_handlers(self, command_handler_instance) -> None:
        """Register command handlers with the bot application.
        
        Args:
            command_handler_instance: Instance of CommandHandler class with command methods
        """
        if not self.application:
            self.setup_application()
        
        # If application setup failed, skip handler registration
        if not self.application:
            logger.warning("Application not available - skipping command handler registration")
            return
        
        # Register user commands
        self.application.add_handler(TelegramCommandHandler("start", command_handler_instance.start_command))
        self.application.add_handler(TelegramCommandHandler("help", command_handler_instance.help_command))
        self.application.add_handler(TelegramCommandHandler("latest", command_handler_instance.latest_command))
        self.application.add_handler(TelegramCommandHandler("quiz", command_handler_instance.quiz_command))
        self.application.add_handler(TelegramCommandHandler("progress", command_handler_instance.progress_command))
        
        # Register additional user commands (if implemented)
        if hasattr(command_handler_instance, 'subscribe_command'):
            self.application.add_handler(TelegramCommandHandler("subscribe", command_handler_instance.subscribe_command))
        
        # Register admin commands
        self.application.add_handler(TelegramCommandHandler("admin_post", command_handler_instance.admin_post_command))
        self.application.add_handler(TelegramCommandHandler("admin_status", command_handler_instance.admin_status_command))
        
        # Register additional admin commands (if implemented)
        if hasattr(command_handler_instance, 'admin_quiz_command'):
            self.application.add_handler(TelegramCommandHandler("admin_quiz", command_handler_instance.admin_quiz_command))
        if hasattr(command_handler_instance, 'admin_schedule_command'):
            self.application.add_handler(TelegramCommandHandler("admin_schedule", command_handler_instance.admin_schedule_command))
        if hasattr(command_handler_instance, 'admin_stats_command'):
            self.application.add_handler(TelegramCommandHandler("admin_stats", command_handler_instance.admin_stats_command))
        
        # Register callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(command_handler_instance.handle_callback_query))
        
        logger.info("Command handlers registered successfully")
    
    def register_message_handlers(self, command_handler_instance) -> None:
        """Register message handlers for non-command messages.
        
        Args:
            command_handler_instance: Instance of CommandHandler class with message handler methods
        """
        if not self.application:
            self.setup_application()
        
        # Register text message handler for general messages (if implemented)
        if hasattr(command_handler_instance, 'handle_text_message'):
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                command_handler_instance.handle_text_message
            ))
        
        # Register photo message handler (if implemented)
        if hasattr(command_handler_instance, 'handle_photo_message'):
            self.application.add_handler(MessageHandler(
                filters.PHOTO, 
                command_handler_instance.handle_photo_message
            ))
        
        # Register document message handler (if implemented)
        if hasattr(command_handler_instance, 'handle_document_message'):
            self.application.add_handler(MessageHandler(
                filters.Document.ALL, 
                command_handler_instance.handle_document_message
            ))
        
        logger.info("Message handlers registered successfully")
    
    def register_callback_query_handlers(self, command_handler_instance) -> None:
        """Register callback query handlers for inline keyboard interactions.
        
        Args:
            command_handler_instance: Instance of CommandHandler class with callback handler methods
        """
        if not self.application:
            self.setup_application()
        
        # Register main callback query handler
        self.application.add_handler(CallbackQueryHandler(command_handler_instance.handle_callback_query))
        
        # Register specific callback patterns (if implemented)
        if hasattr(command_handler_instance, 'handle_quiz_callback'):
            self.application.add_handler(CallbackQueryHandler(
                command_handler_instance.handle_quiz_callback, 
                pattern=r'^(quiz_|answer_)'
            ))
        
        if hasattr(command_handler_instance, 'handle_lesson_callback'):
            self.application.add_handler(CallbackQueryHandler(
                command_handler_instance.handle_lesson_callback, 
                pattern=r'^lesson_'
            ))
        
        if hasattr(command_handler_instance, 'handle_admin_callback'):
            self.application.add_handler(CallbackQueryHandler(
                command_handler_instance.handle_admin_callback, 
                pattern=r'^admin_'
            ))
        
        logger.info("Callback query handlers registered successfully")
    
    def register_all_handlers(self, command_handler_instance) -> None:
        """Register all handlers (commands, messages, callbacks) in one call.
        
        Args:
            command_handler_instance: Instance of CommandHandler class with all handler methods
        """
        self.register_command_handlers(command_handler_instance)
        self.register_message_handlers(command_handler_instance)
        self.register_callback_query_handlers(command_handler_instance)
        
        logger.info("All handlers registered successfully")
    
    def get_registered_handlers_info(self) -> Dict[str, Any]:
        """Get information about registered handlers for monitoring and debugging.
        
        Returns:
            Dictionary with handler information
        """
        if not self.application:
            return {'error': 'Application not initialized'}
        
        handler_info = {
            'total_handlers': len(self.application.handlers[0]) if self.application.handlers else 0,
            'command_handlers': [],
            'message_handlers': [],
            'callback_handlers': [],
            'other_handlers': []
        }
        
        # Keep track of registered commands manually since telegram library doesn't expose them easily
        registered_commands = [
            'start', 'help', 'latest', 'quiz', 'progress',  # User commands
            'admin_post', 'admin_status'  # Admin commands (always registered)
        ]
        
        # Add optional commands if they exist
        optional_commands = [
            ('subscribe', 'subscribe_command'),
            ('admin_quiz', 'admin_quiz_command'),
            ('admin_schedule', 'admin_schedule_command'),
            ('admin_stats', 'admin_stats_command')
        ]
        
        if self.application.handlers:
            command_count = 0
            for handler in self.application.handlers[0]:
                handler_type = type(handler).__name__
                
                if handler_type == 'TelegramCommandHandler':
                    # Use our known command list since telegram doesn't expose command names easily
                    command_name = 'unknown'
                    callback_name = getattr(handler.callback, '__name__', 'unknown') if handler.callback else 'unknown'
                    
                    # Try to match by callback name
                    if callback_name.endswith('_command'):
                        potential_command = callback_name.replace('_command', '')
                        if potential_command in registered_commands:
                            command_name = potential_command
                        else:
                            # Check optional commands
                            for opt_cmd, opt_callback in optional_commands:
                                if callback_name == opt_callback:
                                    command_name = opt_cmd
                                    break
                    
                    # If still unknown, use the index to map to our known commands
                    if command_name == 'unknown' and command_count < len(registered_commands):
                        command_name = registered_commands[command_count]
                    
                    handler_info['command_handlers'].append({
                        'command': command_name,
                        'callback': callback_name
                    })
                    command_count += 1
                    
                elif handler_type == 'MessageHandler':
                    handler_info['message_handlers'].append({
                        'filters': str(handler.filters) if hasattr(handler, 'filters') else 'unknown',
                        'callback': getattr(handler.callback, '__name__', 'unknown') if handler.callback else 'unknown'
                    })
                elif handler_type == 'CallbackQueryHandler':
                    pattern_info = 'no pattern'
                    if hasattr(handler, 'pattern') and handler.pattern:
                        pattern_info = str(handler.pattern)
                    
                    handler_info['callback_handlers'].append({
                        'pattern': pattern_info,
                        'callback': getattr(handler.callback, '__name__', 'unknown') if handler.callback else 'unknown'
                    })
                else:
                    handler_info['other_handlers'].append({
                        'type': handler_type,
                        'callback': getattr(handler.callback, '__name__', 'unknown') if handler.callback else 'unknown'
                    })
        
        return handler_info
    
    async def handle_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route user commands to appropriate handlers with validation.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        if not update.message or not update.message.text:
            return
        
        command_text = update.message.text
        if not command_text.startswith('/'):
            return
        
        # Extract command and arguments
        parts = command_text.split()
        command = parts[0][1:]  # Remove the '/' prefix
        args = parts[1:] if len(parts) > 1 else []
        
        user_id = update.effective_user.id
        
        # Log command usage
        logger.info(f"User {user_id} executed command: /{command} with args: {args}")
        
        # Validate command exists (this is handled by the telegram library's dispatcher)
        # The actual command execution is handled by the registered CommandHandler instances
        
    async def handle_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route admin commands with authorization check.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        if not update.message or not update.message.text:
            return
        
        command_text = update.message.text
        if not command_text.startswith('/admin_'):
            return
        
        user_id = update.effective_user.id
        
        # This method can be used for additional admin command validation
        # The actual authorization is handled in the CommandHandler class
        logger.info(f"Admin command attempt by user {user_id}: {command_text}")
    
    async def send_interactive_response(self, chat_id: int, message: str, 
                                     parse_mode: str = ParseMode.MARKDOWN,
                                     reply_markup=None) -> Dict[str, Any]:
        """Send formatted interactive response to users.
        
        Args:
            chat_id: Target chat ID
            message: Message text to send
            parse_mode: Telegram parse mode (HTML or Markdown)
            reply_markup: Optional inline keyboard markup
            
        Returns:
            Dictionary with send result
        """
        if not self._validated:
            raise RuntimeError("Bot controller not initialized. Call initialize() first.")
        
        try:
            sent_message = await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
            return {
                'success': True,
                'message_id': sent_message.message_id,
                'chat_id': chat_id,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to send interactive response to {chat_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'chat_id': chat_id,
                'timestamp': datetime.utcnow()
            }
    
    async def start_polling(self) -> None:
        """Start polling for updates (for interactive features)."""
        if not self.application:
            logger.warning("Application not available - cannot start polling. Interactive features will be disabled.")
            return
        
        try:
            logger.info("Starting bot polling for interactive features...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
        except Exception as e:
            logger.error(f"Failed to start polling: {e}")
            logger.warning("Interactive features will be disabled")
    
    async def stop_polling(self) -> None:
        """Stop polling for updates."""
        if self.application and self.application.updater:
            try:
                await self.application.updater.stop()
                logger.info("Bot polling stopped")
            except Exception as e:
                logger.error(f"Error stopping polling: {e}")
            logger.info("Bot polling stopped")


# Convenience function for creating and initializing bot controller
async def create_bot_controller(bot_token: Optional[str] = None) -> Optional[BotController]:
    """Create and initialize a bot controller.
    
    Args:
        bot_token: Optional bot token. If not provided, uses config.
        
    Returns:
        Initialized BotController instance or None if initialization failed.
    """
    controller = BotController(bot_token)
    
    if await controller.initialize():
        return controller
    else:
        await controller.close()
        return None