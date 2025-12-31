"""Telegram bot controller for managing API communication and message formatting."""

import asyncio
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime
import time

from telegram import Bot
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
        
        # Initialize bot instance
        self.bot = Bot(token=self.bot_token)
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
  
    async def close(self) -> None:
        """Close bot connection and cleanup resources."""
        try:
            await self.bot.close()
            logger.info("Bot controller closed successfully")
        except Exception as e:
            logger.error(f"Error closing bot controller: {e}")