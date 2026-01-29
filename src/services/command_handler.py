"""Command handler for interactive Telegram bot commands."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..models.lesson import Lesson
from ..models.user_profile import UserProfile, UserSession
from ..models.admin_log import AdminActionLog
from .lesson_manager import LessonManager
from .quiz_generator import QuizGenerator
from .scheduler import SchedulerService
from .user_repository import UserRepository, create_user_repository
from .progress_tracker import ProgressTracker, create_progress_tracker


logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles interactive bot commands for users and admins."""
    
    def __init__(self, lesson_manager: LessonManager, scheduler_service: SchedulerService, admin_user_ids: List[int] = None):
        """Initialize command handler.
        
        Args:
            lesson_manager: Lesson management service
            scheduler_service: Scheduler service for manual triggers
            admin_user_ids: List of Telegram user IDs with admin privileges
        """
        from ..config import get_config
        config = get_config()
        
        self.lesson_manager = lesson_manager
        self.scheduler_service = scheduler_service
        self.quiz_generator = QuizGenerator()
        self.admin_user_ids = admin_user_ids or config.admin_user_ids
        
        # Initialize user repository and progress tracker
        try:
            from ..models.supabase_database import create_supabase_manager
            supabase_manager = create_supabase_manager()
            self.user_repo = create_user_repository(supabase_manager)
            self.progress_tracker = create_progress_tracker(self.user_repo)
            logger.info("User repository and progress tracker initialized")
        except Exception as e:
            logger.error(f"Failed to initialize user repository: {e}")
            self.user_repo = None
            self.progress_tracker = None
        
    def is_admin(self, user_id: int) -> bool:
        """Check if user has admin privileges."""
        return user_id in self.admin_user_ids
    
    async def _record_command_usage(self, command_name: str, update: Update, success: bool = True, 
                                  start_time: float = None, error_type: str = None) -> None:
        """Record command usage statistics.
        
        Args:
            command_name: Name of the command
            update: Telegram update object
            success: Whether command was successful
            start_time: Command start time for response time calculation
            error_type: Type of error if command failed
        """
        if not self.progress_tracker:
            return
        
        try:
            user_id = update.effective_user.id
            chat_type = update.effective_chat.type
            response_time_ms = int((time.time() - start_time) * 1000) if start_time else 0
            
            self.progress_tracker.record_command_usage(
                command_name=command_name,
                user_id=user_id,
                chat_type=chat_type,
                success=success,
                response_time_ms=response_time_ms,
                error_type=error_type
            )
        except Exception as e:
            logger.error(f"Error recording command usage: {e}")
    
    async def _ensure_user_profile(self, update: Update) -> Optional[UserProfile]:
        """Ensure user profile exists and return it.
        
        Args:
            update: Telegram update object
            
        Returns:
            UserProfile or None if failed
        """
        if not self.user_repo:
            return None
        
        try:
            user = update.effective_user
            chat = update.effective_chat
            
            return self.user_repo.get_or_create_user_profile(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                chat_id=chat.id
            )
        except Exception as e:
            logger.error(f"Error ensuring user profile: {e}")
            return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        start_time = time.time()
        
        try:
            user = update.effective_user
            
            # Ensure user profile exists
            await self._ensure_user_profile(update)
            
            welcome_text = f"""
🎓 **Welcome to Tutor.Me English Bot!**

Hello {user.first_name}! I'm your English learning companion.

📚 **What I do:**
• Daily English lessons at 21:00 EAT
• Interactive quizzes after each lesson
• Grammar, vocabulary, and common mistakes
• Track your learning progress

🔧 **Available Commands:**
/help - Show all commands
/latest - Get the latest lesson
/quiz - Practice with a quiz
/progress - Check your learning stats

Let's improve your English together! 🚀
            """
            
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
            logger.info(f"User {user.id} ({user.first_name}) started the bot")
            
            await self._record_command_usage("start", update, True, start_time)
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ Sorry, something went wrong. Please try again later.")
            await self._record_command_usage("start", update, False, start_time, str(e))
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = update.effective_user
        
        help_text = """
📖 **Available Commands:**

**For Everyone:**
/start - Welcome message and bot info
/help - Show this help message
/latest - Get the most recent lesson
/quiz - Get a practice quiz
/progress - View your learning progress
/subscribe - Get notified about new lessons

**Bot Info:**
• Lessons posted daily at 21:00 EAT
• Quizzes follow 5 minutes after lessons
• All lessons are stored and accessible anytime
        """
        
        # Add admin commands if user is admin
        if self.is_admin(user.id):
            help_text += """
**Admin Commands:**
/admin_post - Manually post next lesson
/admin_quiz - Post quiz for latest lesson
/admin_status - Check bot status
/admin_schedule - Change posting schedule
/admin_stats - View detailed statistics
            """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /latest command - get the most recent lesson."""
        start_time = time.time()
        
        try:
            # Ensure user profile exists
            await self._ensure_user_profile(update)
            
            # Get the last posted lesson
            lessons = self.lesson_manager.get_all_lessons()
            if not lessons:
                await update.message.reply_text("❌ No lessons available yet!")
                await self._record_command_usage("latest", update, False, start_time, "no_lessons")
                return
            
            # Find the most recent lesson (highest ID that was posted)
            latest_lesson = None
            for lesson in sorted(lessons, key=lambda x: x.id, reverse=True):
                if hasattr(lesson, 'posted') and lesson.posted:
                    latest_lesson = lesson
                    break
            
            if not latest_lesson:
                # If no lesson is marked as posted, get the first one
                latest_lesson = lessons[0]
            
            # Format and send the lesson
            lesson_text = f"""
📚 **Latest Lesson: {latest_lesson.title}**

{latest_lesson.content}

---
🏷️ Category: {latest_lesson.category.title()}
📊 Difficulty: {latest_lesson.difficulty.title()}
🆔 Lesson #{latest_lesson.id}
            """
            
            # Add quiz button
            keyboard = [[InlineKeyboardButton("🧠 Take Quiz", callback_data=f"quiz_{latest_lesson.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(lesson_text, parse_mode='Markdown', reply_markup=reply_markup)
            
            # Record lesson completion in progress tracker
            if self.progress_tracker:
                self.progress_tracker.record_lesson_completion(
                    user_id=update.effective_user.id,
                    lesson_id=latest_lesson.id,
                    lesson_title=latest_lesson.title,
                    difficulty=latest_lesson.difficulty,
                    category=latest_lesson.category
                )
            
            logger.info(f"User {update.effective_user.id} requested latest lesson: {latest_lesson.id}")
            await self._record_command_usage("latest", update, True, start_time)
            
        except Exception as e:
            logger.error(f"Error in latest_command: {e}")
            await update.message.reply_text("❌ Sorry, couldn't retrieve the latest lesson. Please try again later.")
            await self._record_command_usage("latest", update, False, start_time, str(e))
    
    async def quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /quiz command - get a practice quiz."""
        try:
            # Get a random lesson for quiz
            lessons = self.lesson_manager.get_all_lessons()
            if not lessons:
                await update.message.reply_text("❌ No lessons available for quiz!")
                return
            
            import random
            lesson = random.choice(lessons)
            
            # Generate quiz
            quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
            if not quiz:
                await update.message.reply_text("❌ Couldn't generate quiz. Please try again!")
                return
            
            # Format quiz as message with inline buttons
            quiz_text = f"🧠 **Quiz Time!**\n\n**{quiz.question}**"
            
            # Create inline keyboard with options
            keyboard = []
            for i, option in enumerate(quiz.options):
                keyboard.append([InlineKeyboardButton(
                    f"{chr(65 + i)}. {option.text[:50]}{'...' if len(option.text) > 50 else ''}", 
                    callback_data=f"answer_{lesson.id}_{i}_{1 if option.is_correct else 0}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(quiz_text, parse_mode='Markdown', reply_markup=reply_markup)
            logger.info(f"User {update.effective_user.id} requested quiz for lesson {lesson.id}")
            
        except Exception as e:
            logger.error(f"Error in quiz_command: {e}")
            await update.message.reply_text("❌ Sorry, couldn't generate quiz. Please try again later.")
    
    async def progress_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /progress command - show user progress."""
        start_time = time.time()
        
        try:
            user = update.effective_user
            
            # Ensure user profile exists
            profile = await self._ensure_user_profile(update)
            
            if self.progress_tracker and profile:
                # Get comprehensive progress data
                progress_report = self.progress_tracker.generate_progress_report(user.id)
                
                if progress_report:
                    await update.message.reply_text(progress_report, parse_mode='Markdown')
                else:
                    # Fallback to basic progress
                    basic_progress = f"""
📊 **Your Learning Progress**

👤 **User:** {user.first_name}
🆔 **User ID:** {user.id}

📚 **Your Stats:**
• Lessons completed: {profile.total_lessons_completed}
• Quizzes taken: {profile.total_quizzes_taken}
• Average quiz score: {profile.average_quiz_score:.1f}%
• Current streak: {profile.current_streak} days
• Longest streak: {profile.longest_streak} days

🎯 **Keep Learning!**
Use /latest to catch up on recent lessons
Use /quiz to practice anytime
                    """
                    await update.message.reply_text(basic_progress, parse_mode='Markdown')
            else:
                # Fallback to system stats if user tracking unavailable
                lessons = self.lesson_manager.get_all_lessons()
                total_lessons = len(lessons)
                
                stats = self.lesson_manager.get_system_stats()
                
                progress_text = f"""
📊 **Learning Progress**

👤 **User:** {user.first_name}
🆔 **User ID:** {user.id}

📚 **System Stats:**
• Total lessons available: {total_lessons}
• Lessons posted: {stats.get('total_posted', 0)}
• Success rate: {stats.get('success_rate', 0):.1f}%

🎯 **Keep Learning!**
Use /latest to catch up on recent lessons
Use /quiz to practice anytime

💡 **Tip:** Your personal progress tracking will be available soon!
                """
                
                await update.message.reply_text(progress_text, parse_mode='Markdown')
            
            logger.info(f"User {user.id} checked progress")
            await self._record_command_usage("progress", update, True, start_time)
            
        except Exception as e:
            logger.error(f"Error in progress_command: {e}")
            await update.message.reply_text("❌ Sorry, couldn't retrieve progress. Please try again later.")
            await self._record_command_usage("progress", update, False, start_time, str(e))
    
    # Admin Commands
    async def admin_post_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin_post command - manually trigger lesson posting."""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ You don't have admin privileges.")
            return
        
        try:
            await update.message.reply_text("🔄 Triggering manual lesson post...")
            
            # Trigger immediate post
            result = await self.scheduler_service.trigger_immediate_post()
            
            if result['success']:
                success_text = f"""
✅ **Lesson Posted Successfully!**

📚 **Lesson:** {result.get('lesson_title', 'Unknown')}
🆔 **Lesson ID:** {result.get('lesson_id', 'Unknown')}
📱 **Message ID:** {result.get('message_id', 'Unknown')}
🧠 **Quiz Scheduled:** {result.get('quiz_scheduled', False)}
⏰ **Posted at:** {result.get('timestamp', datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S')}
                """
                await update.message.reply_text(success_text, parse_mode='Markdown')
            else:
                error_text = f"❌ **Failed to post lesson:**\n{result.get('error', 'Unknown error')}"
                await update.message.reply_text(error_text, parse_mode='Markdown')
            
            logger.info(f"Admin {user.id} triggered manual post: {result}")
            
        except Exception as e:
            logger.error(f"Error in admin_post_command: {e}")
            await update.message.reply_text("❌ Error triggering manual post. Check logs for details.")
    
    async def admin_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin_status command - show bot status."""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ You don't have admin privileges.")
            return
        
        try:
            # Get scheduler status
            scheduler_status = self.scheduler_service.get_scheduler_status()
            
            # Get system stats
            system_stats = self.lesson_manager.get_system_stats()
            
            status_text = f"""
🤖 **Bot Status Report**

**Scheduler:**
• Running: {'✅' if scheduler_status.get('running') else '❌'}
• Next run: {scheduler_status.get('next_run_time', 'Not scheduled')}
• Posting time: {scheduler_status.get('posting_time', 'Unknown')}
• Timezone: {scheduler_status.get('timezone', 'Unknown')}
• Active jobs: {scheduler_status.get('job_count', 0)}

**System:**
• Total lessons: {system_stats.get('total_lessons', 0)}
• Posted lessons: {system_stats.get('total_posted', 0)}
• Success rate: {system_stats.get('success_rate', 0):.1f}%
• Last error: {system_stats.get('last_error', 'None')}

**Database:**
• Status: {'✅ Connected' if system_stats.get('database_connected') else '❌ Disconnected'}
• Type: {system_stats.get('database_type', 'Unknown')}
            """
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            logger.info(f"Admin {user.id} checked bot status")
            
        except Exception as e:
            logger.error(f"Error in admin_status_command: {e}")
            await update.message.reply_text("❌ Error retrieving bot status. Check logs for details.")
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard button presses."""
        query = update.callback_query
        await query.answer()
        
        start_time = time.time()
        
        try:
            data = query.data
            user_id = query.from_user.id
            
            # Ensure user profile exists
            await self._ensure_user_profile(update)
            
            if data.startswith("quiz_"):
                # Handle quiz request from lesson
                lesson_id = int(data.split("_")[1])
                lesson = self.lesson_manager.get_lesson(lesson_id)
                
                if lesson:
                    quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
                    if quiz:
                        # Format quiz
                        quiz_text = f"🧠 **Quiz for: {lesson.title}**\n\n**{quiz.question}**"
                        
                        # Create answer buttons
                        keyboard = []
                        for i, option in enumerate(quiz.options):
                            keyboard.append([InlineKeyboardButton(
                                f"{chr(65 + i)}. {option.text[:50]}{'...' if len(option.text) > 50 else ''}", 
                                callback_data=f"answer_{lesson_id}_{i}_{1 if option.is_correct else 0}_{quiz.id if hasattr(quiz, 'id') else 0}"
                            )])
                        
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(quiz_text, parse_mode='Markdown', reply_markup=reply_markup)
                    else:
                        await query.edit_message_text("❌ Couldn't generate quiz for this lesson.")
                else:
                    await query.edit_message_text("❌ Lesson not found.")
            
            elif data.startswith("answer_"):
                # Handle quiz answer
                parts = data.split("_")
                lesson_id = int(parts[1])
                answer_index = int(parts[2])
                is_correct = bool(int(parts[3]))
                quiz_id = int(parts[4]) if len(parts) > 4 else 0
                
                # Calculate score (simple: 100% if correct, 0% if incorrect)
                score = 100.0 if is_correct else 0.0
                
                # Record quiz attempt in progress tracker
                if self.progress_tracker:
                    self.progress_tracker.record_quiz_attempt(
                        user_id=user_id,
                        quiz_id=quiz_id,
                        lesson_id=lesson_id,
                        score=score,
                        total_questions=1,
                        correct_answers=1 if is_correct else 0,
                        time_taken=int((time.time() - start_time) * 1000),  # Convert to ms
                        is_practice=False,
                        answers=[{
                            'question_index': 0,
                            'user_answer_index': answer_index,
                            'is_correct': is_correct,
                            'timestamp': datetime.utcnow().isoformat()
                        }]
                    )
                
                if is_correct:
                    result_text = f"✅ **Correct!**\n\nGreat job! You got the right answer."
                else:
                    result_text = f"❌ **Incorrect**\n\nDon't worry, keep practicing!"
                
                # Add explanation if available
                lesson = self.lesson_manager.get_lesson(lesson_id)
                if lesson:
                    quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
                    if quiz and quiz.explanation:
                        result_text += f"\n\n💡 **Explanation:** {quiz.explanation}"
                
                # Add retry button
                keyboard = [[InlineKeyboardButton("🔄 Try Another Quiz", callback_data=f"quiz_{lesson_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)
                
                logger.info(f"User {user_id} answered quiz: lesson={lesson_id}, correct={is_correct}")
        
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text("❌ Error processing your request. Please try again.")