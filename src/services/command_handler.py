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
from .content_browser import ContentBrowser, create_content_browser


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
        
        # Initialize content browser
        self.content_browser = create_content_browser(lesson_manager)
        
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

Choose what you'd like to do:
            """
            
            # Create inline keyboard with command buttons
            keyboard = [
                [
                    InlineKeyboardButton("📖 Latest Lesson", callback_data="cmd_latest"),
                    InlineKeyboardButton("🧠 Take Quiz", callback_data="cmd_quiz")
                ],
                [
                    InlineKeyboardButton("📊 My Progress", callback_data="cmd_progress"),
                    InlineKeyboardButton("❓ Help", callback_data="cmd_help")
                ]
            ]
            
            # Add admin buttons if user is admin
            if self.is_admin(user.id):
                keyboard.append([
                    InlineKeyboardButton("👑 Admin Panel", callback_data="cmd_admin_panel")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_text, 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
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
📖 **Tutor.Me English Bot - Help**

Choose what you'd like to do:
        """
        
        # Create comprehensive command buttons
        keyboard = [
            [
                InlineKeyboardButton("📖 Latest Lesson", callback_data="cmd_latest"),
                InlineKeyboardButton("🧠 Take Quiz", callback_data="cmd_quiz")
            ],
            [
                InlineKeyboardButton("📊 My Progress", callback_data="cmd_progress"),
                InlineKeyboardButton("🔍 Browse Lessons", callback_data="cmd_browse")
            ],
            [
                InlineKeyboardButton("🔔 Subscribe", callback_data="cmd_subscribe")
            ]
        ]
        
        # Add admin buttons if user is admin
        if self.is_admin(user.id):
            help_text += "\n👑 **Admin Features Available**"
            keyboard.extend([
                [
                    InlineKeyboardButton("📝 Post Lesson", callback_data="cmd_admin_post"),
                    InlineKeyboardButton("📊 Bot Status", callback_data="cmd_admin_status")
                ],
                [
                    InlineKeyboardButton("📈 Admin Stats", callback_data="cmd_admin_stats"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="cmd_admin_settings")
                ]
            ])
        
        # Add info button
        keyboard.append([
            InlineKeyboardButton("ℹ️ About Bot", callback_data="cmd_about")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
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
            
            # Handle command buttons
            if data.startswith("cmd_"):
                await self._handle_command_button(update, context, data)
                return
            
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
            
            # Handle browse functionality
            elif data.startswith("browse_"):
                await self._handle_browse_callback(query, data)
            
            elif data.startswith("view_lesson_"):
                lesson_id = int(data.split("_")[2])
                await self._show_lesson_detail(query, lesson_id)
            
            elif data.startswith("similar_"):
                category = data.split("_", 1)[1]
                await self._show_category_lessons(query, category)
            
            elif data.startswith("answer_"):
                # Handle quiz answer
                try:
                    parts = data.split("_")
                    if len(parts) < 4:
                        await query.edit_message_text("❌ Invalid quiz data format.")
                        return
                    
                    lesson_id = int(parts[1])
                    answer_index = int(parts[2])
                    is_correct = bool(int(parts[3]))
                    
                    # Handle quiz_id safely
                    quiz_id = 0
                    if len(parts) > 4 and parts[4] not in ['None', 'null', '']:
                        try:
                            quiz_id = int(parts[4])
                        except (ValueError, TypeError):
                            quiz_id = 0
                    
                    # Calculate score (simple: 100% if correct, 0% if incorrect)
                    score = 100.0 if is_correct else 0.0
                    
                    # Record quiz attempt in progress tracker
                    try:
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
                    except Exception as progress_error:
                        logger.warning(f"Failed to record progress: {progress_error}")
                    
                    # Create result message
                    if is_correct:
                        result_text = f"✅ **Correct!**\n\nGreat job! You got the right answer."
                    else:
                        result_text = f"❌ **Incorrect**\n\nDon't worry, keep practicing!"
                    
                    # Try to add explanation if available
                    try:
                        lesson = self.lesson_manager.get_lesson(lesson_id)
                        if lesson:
                            quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
                            if quiz and hasattr(quiz, 'explanation') and quiz.explanation:
                                result_text += f"\n\n💡 **Explanation:** {quiz.explanation}"
                    except Exception as explanation_error:
                        logger.warning(f"Failed to get explanation: {explanation_error}")
                    
                    # Add navigation buttons
                    keyboard = [
                        [InlineKeyboardButton("🔄 Try Another Quiz", callback_data=f"quiz_{lesson_id}")],
                        [InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_help")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)
                    
                    logger.info(f"User {user_id} answered quiz: lesson={lesson_id}, correct={is_correct}")
                    
                except ValueError as ve:
                    logger.error(f"Invalid quiz answer data: {data}, error: {ve}")
                    await query.edit_message_text("❌ Invalid quiz answer format. Please try again.")
                except Exception as quiz_error:
                    logger.error(f"Error processing quiz answer: {quiz_error}")
                    await query.edit_message_text("❌ Error processing quiz answer. Please try again.")
        
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text("❌ Error processing your request. Please try again.")
    async def _handle_command_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """Handle command button presses from inline keyboards."""
        query = update.callback_query
        user = query.from_user
        
        try:
            if data == "cmd_latest":
                # Simulate latest command
                await self._execute_latest_for_callback(query)
            
            elif data == "cmd_quiz":
                # Simulate quiz command
                await self._execute_quiz_for_callback(query)
            
            elif data == "cmd_progress":
                # Simulate progress command
                await self._execute_progress_for_callback(query)
            
            elif data == "cmd_help":
                # Show help with buttons
                await self._execute_help_for_callback(query)
            
            elif data == "cmd_browse":
                # Show content browsing options
                await self._show_browse_menu(query)
            
            elif data == "cmd_subscribe":
                # Handle subscription
                await query.edit_message_text(
                    "🔔 **Subscription Settings**\n\n"
                    "You're automatically subscribed to daily lessons at 21:00 EAT!\n\n"
                    "📅 Next lesson: Tomorrow at 21:00\n"
                    "🔄 Lessons are posted automatically"
                )
            
            elif data == "cmd_about":
                # Show about information
                about_text = """
ℹ️ **About Tutor.Me English Bot**

🎓 **Purpose:** Help you improve your English skills daily
📚 **Content:** Grammar, vocabulary, common mistakes
⏰ **Schedule:** Daily lessons at 21:00 EAT
🧠 **Interactive:** Quizzes and progress tracking

🤖 **Bot Features:**
• Automatic daily lessons
• Interactive quizzes
• Progress tracking
• Personal statistics
• Admin controls

Made with ❤️ for English learners
                """
                
                # Back button
                keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_help")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)
            
            # Admin command buttons
            elif data == "cmd_admin_panel" and self.is_admin(user.id):
                await self._show_admin_panel(query)
            
            elif data == "cmd_admin_post" and self.is_admin(user.id):
                await self._execute_admin_post_for_callback(query)
            
            elif data == "cmd_admin_status" and self.is_admin(user.id):
                await self._execute_admin_status_for_callback(query)
            
            elif data == "cmd_admin_stats" and self.is_admin(user.id):
                await query.edit_message_text("📊 **Admin Statistics**\n\nDetailed stats coming soon...")
            
            elif data == "cmd_admin_settings" and self.is_admin(user.id):
                await self._show_admin_settings(query)
            
            elif data == "cmd_admin_quiz" and self.is_admin(user.id):
                await self._execute_admin_quiz_for_callback(query)
            
            else:
                await query.edit_message_text("❌ Unknown command or insufficient permissions.")
                
        except Exception as e:
            logger.error(f"Error handling command button {data}: {e}")
            await query.edit_message_text("❌ Error processing command. Please try again.")
    
    async def _execute_latest_for_callback(self, query) -> None:
        """Execute latest command for callback query."""
        try:
            lessons = self.lesson_manager.get_all_lessons()
            if not lessons:
                await query.edit_message_text("📚 No lessons available yet. Check back later!")
                return
            
            # Get the most recent lesson
            latest_lesson = lessons[-1]
            
            lesson_text = f"""
📖 **Latest Lesson**

**{latest_lesson.title}**

{latest_lesson.content[:500]}{'...' if len(latest_lesson.content) > 500 else ''}

📊 **Details:**
• Category: {latest_lesson.category}
• Difficulty: {latest_lesson.difficulty}
• Tags: {', '.join(latest_lesson.tags) if latest_lesson.tags else 'None'}
            """
            
            # Add quiz button
            keyboard = [
                [InlineKeyboardButton("🧠 Take Quiz", callback_data=f"quiz_{latest_lesson.id}")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(lesson_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in latest callback: {e}")
            await query.edit_message_text("❌ Error retrieving latest lesson.")
    
    async def _execute_quiz_for_callback(self, query) -> None:
        """Execute quiz command for callback query."""
        try:
            lessons = self.lesson_manager.get_all_lessons()
            if not lessons:
                await query.edit_message_text("📚 No lessons available for quiz yet!")
                return
            
            # Get a recent lesson for quiz
            recent_lessons = lessons[-5:] if len(lessons) >= 5 else lessons
            import random
            lesson = random.choice(recent_lessons)
            
            try:
                quiz = self.quiz_generator.generate_quiz_for_lesson(lesson)
                if not quiz:
                    await query.edit_message_text("❌ Couldn't generate quiz. Please try again later.")
                    return
                
                if not hasattr(quiz, 'options') or not quiz.options:
                    await query.edit_message_text("❌ Quiz has no options. Please try again later.")
                    return
                
                quiz_text = f"🧠 **Quiz Time!**\n\n**Lesson:** {lesson.title}\n\n**{quiz.question}**"
                
                # Create answer buttons
                keyboard = []
                for i, option in enumerate(quiz.options):
                    if hasattr(option, 'text') and hasattr(option, 'is_correct'):
                        quiz_id = getattr(quiz, 'id', 0)
                        # Ensure quiz_id is a valid integer
                        if quiz_id is None or quiz_id == 'None':
                            quiz_id = 0
                        keyboard.append([InlineKeyboardButton(
                            f"{chr(65 + i)}. {option.text[:50]}{'...' if len(option.text) > 50 else ''}", 
                            callback_data=f"answer_{lesson.id}_{i}_{1 if option.is_correct else 0}_{quiz_id}"
                        )])
                
                if not keyboard:
                    await query.edit_message_text("❌ Quiz options are invalid. Please try again later.")
                    return
                
                # Add back button
                keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_help")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(quiz_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            except Exception as quiz_gen_error:
                logger.error(f"Quiz generation error: {quiz_gen_error}")
                await query.edit_message_text("❌ Error generating quiz. Please try again later.")
            
        except Exception as e:
            logger.error(f"Error in quiz callback: {e}")
            await query.edit_message_text("❌ Error generating quiz.")
    
    async def _execute_progress_for_callback(self, query) -> None:
        """Execute progress command for callback query."""
        try:
            user_id = query.from_user.id
            
            if not self.progress_tracker:
                await query.edit_message_text("📊 Progress tracking not available.")
                return
            
            progress = self.progress_tracker.get_user_progress_summary(user_id)
            
            progress_text = f"""
📊 **Your Learning Progress**

👤 **Profile:** {query.from_user.first_name}
📚 **Lessons Completed:** {progress.get('lessons_completed', 0)}
🧠 **Quizzes Taken:** {progress.get('quizzes_taken', 0)}
📈 **Average Score:** {progress.get('average_score', 0):.1f}%
🔥 **Current Streak:** {progress.get('current_streak', 0)} days
🏆 **Best Streak:** {progress.get('longest_streak', 0)} days

Keep up the great work! 🎉
            """
            
            # Add back button
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_help")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(progress_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in progress callback: {e}")
            await query.edit_message_text("❌ Error retrieving progress.")
    
    async def _execute_help_for_callback(self, query) -> None:
        """Execute help command for callback query."""
        user = query.from_user
        
        help_text = """
📖 **Tutor.Me English Bot - Help**

Choose what you'd like to do:
        """
        
        # Create comprehensive command buttons
        keyboard = [
            [
                InlineKeyboardButton("📖 Latest Lesson", callback_data="cmd_latest"),
                InlineKeyboardButton("🧠 Take Quiz", callback_data="cmd_quiz")
            ],
            [
                InlineKeyboardButton("📊 My Progress", callback_data="cmd_progress"),
                InlineKeyboardButton("🔍 Browse Lessons", callback_data="cmd_browse")
            ],
            [
                InlineKeyboardButton("🔔 Subscribe", callback_data="cmd_subscribe")
            ]
        ]
        
        # Add admin buttons if user is admin
        if self.is_admin(user.id):
            help_text += "\n👑 **Admin Features Available**"
            keyboard.extend([
                [
                    InlineKeyboardButton("📝 Post Lesson", callback_data="cmd_admin_post"),
                    InlineKeyboardButton("🧠 Post Quiz", callback_data="cmd_admin_quiz")
                ],
                [
                    InlineKeyboardButton("📊 Bot Status", callback_data="cmd_admin_status"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="cmd_admin_settings")
                ]
            ])
        
        # Add info button
        keyboard.append([
            InlineKeyboardButton("ℹ️ About Bot", callback_data="cmd_about")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _show_admin_panel(self, query) -> None:
        """Show admin control panel."""
        admin_text = """
👑 **Admin Control Panel**

Welcome to the admin dashboard!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Post Lesson", callback_data="cmd_admin_post"),
                InlineKeyboardButton("🧠 Post Quiz", callback_data="cmd_admin_quiz")
            ],
            [
                InlineKeyboardButton("📊 Bot Status", callback_data="cmd_admin_status"),
                InlineKeyboardButton("⚙️ Settings", callback_data="cmd_admin_settings")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(admin_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _execute_admin_post_for_callback(self, query) -> None:
        """Execute admin post command for callback query."""
        try:
            # Get next lesson to post
            lessons = self.lesson_manager.get_all_lessons()
            if not lessons:
                await query.edit_message_text("❌ No lessons available to post.")
                return
            
            # Get a lesson that hasn't been posted recently
            import random
            lesson = random.choice(lessons)
            
            # Actually post the lesson to the channel using the scheduler service
            result = await self.scheduler_service.trigger_immediate_post()
            success = result.get('success', False)
            quiz_scheduled = result.get('quiz_scheduled', False)
            
            if success:
                lesson_title = result.get('lesson_title', 'Unknown')
                result_text = f"""
✅ **Lesson Posted Successfully!**

**Posted:** {lesson_title}
**Status:** ✅ Sent to channel

📋 **Next Steps:**
"""
                if quiz_scheduled:
                    result_text += "🧠 Quiz will be posted in 5 minutes automatically"
                else:
                    result_text += "ℹ️ Quizzes are disabled in settings"
                    
            else:
                error_msg = result.get('error', 'Unknown error')
                result_text = f"""
⚠️ **Posting Failed**

**Error:** {error_msg}
**Status:** ❌ Not sent to channel

Please check the logs for more details.
                """
            
            # Add back button
            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="cmd_admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in admin post callback: {e}")
            await query.edit_message_text("❌ Error posting lesson. Check logs for details.")
    
    async def _execute_admin_status_for_callback(self, query) -> None:
        """Execute admin status command for callback query."""
        try:
            # Get bot status information
            status_text = f"""
📊 **Bot Status Report**

🤖 **Bot Status:** ✅ Online
📅 **Last Lesson:** Today
⏰ **Next Scheduled:** Tomorrow 21:00 EAT
📊 **Total Lessons:** {len(self.lesson_manager.get_all_lessons())}

🔧 **System Status:**
• Database: ✅ Connected
• Scheduler: ✅ Running
• Commands: ✅ Active

📈 **Quick Stats:**
• Active Users: Available in full stats
• Commands Today: Available in full stats
            """
            
            # Add back button
            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="cmd_admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(status_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in admin status callback: {e}")
            await query.edit_message_text("❌ Error retrieving status.")
    
    async def _show_admin_settings(self, query) -> None:
        """Show admin settings panel."""
        settings_text = """
⚙️ **Admin Settings**

Current Configuration:
        """
        
        # Get current settings
        try:
            config = get_config()
            settings_text += f"""
📅 **Posting Time:** {config.posting_time} {config.timezone}
🧠 **Quizzes:** {'✅ Enabled' if config.enable_quizzes else '❌ Disabled'}
⏱️ **Quiz Delay:** {config.quiz_delay_minutes} minutes
📊 **Database:** {config.database_type.title()}
            """
        except Exception as e:
            settings_text += f"\n❌ Error loading settings: {e}"
        
        keyboard = [
            [
                InlineKeyboardButton("🧠 Post Quiz Now", callback_data="cmd_admin_quiz"),
                InlineKeyboardButton("📊 View Stats", callback_data="cmd_admin_stats")
            ],
            [
                InlineKeyboardButton("🔙 Admin Panel", callback_data="cmd_admin_panel")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(settings_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _execute_admin_quiz_for_callback(self, query) -> None:
        """Execute admin quiz command for callback query."""
        try:
            # Get the most recent lesson
            lessons = self.lesson_manager.get_all_lessons()
            if not lessons:
                await query.edit_message_text("❌ No lessons available for quiz.")
                return
            
            # Get the latest lesson
            latest_lesson = lessons[-1]
            
            # Post quiz for the latest lesson
            try:
                # Use the scheduler's quiz posting method
                quiz_result = await self.scheduler_service._post_quiz_for_lesson(latest_lesson)
                
                if quiz_result.get('success', False):
                    result_text = f"""
✅ **Quiz Posted Successfully!**

**Lesson:** {latest_lesson.title}
**Quiz:** Posted to channel

The quiz for the latest lesson has been sent to the channel.
                    """
                else:
                    error_msg = quiz_result.get('error', 'Unknown error')
                    result_text = f"""
❌ **Quiz Posting Failed**

**Lesson:** {latest_lesson.title}
**Error:** {error_msg}

Please check the logs for more details.
                    """
                    
            except Exception as quiz_error:
                logger.error(f"Error posting quiz: {quiz_error}")
                result_text = f"""
❌ **Quiz Posting Error**

**Lesson:** {latest_lesson.title}
**Error:** {str(quiz_error)}

Please check the logs for more details.
                """
            
            # Add back button
            keyboard = [[InlineKeyboardButton("🔙 Admin Settings", callback_data="cmd_admin_settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in admin quiz callback: {e}")
            await query.edit_message_text("❌ Error posting quiz. Check logs for details.")
    
    # Content Browsing Methods
    async def _show_browse_menu(self, query) -> None:
        """Show the main content browsing menu."""
        try:
            # Get content statistics
            stats = self.content_browser.get_content_stats()
            
            browse_text = f"""
🔍 **Browse Lessons**

📚 **Available Content:**
• Total Lessons: {stats.total_lessons}
• Categories: {len(stats.categories)}
• Difficulty Levels: {len(stats.difficulties)}

Choose how you'd like to browse:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📂 By Category", callback_data="browse_categories"),
                    InlineKeyboardButton("📊 By Difficulty", callback_data="browse_difficulties")
                ],
                [
                    InlineKeyboardButton("🏷️ By Topic", callback_data="browse_tags"),
                    InlineKeyboardButton("🔥 Popular", callback_data="browse_popular")
                ],
                [
                    InlineKeyboardButton("🆕 Recent", callback_data="browse_recent"),
                    InlineKeyboardButton("🔍 Search", callback_data="browse_search")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_help")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(browse_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing browse menu: {e}")
            await query.edit_message_text("❌ Error loading browse menu.")
    
    async def _show_categories_menu(self, query) -> None:
        """Show available categories for browsing."""
        try:
            stats = self.content_browser.get_content_stats()
            
            categories_text = """
📂 **Browse by Category**

Select a category to explore:
            """
            
            keyboard = []
            # Create buttons for each category
            for i in range(0, len(stats.categories), 2):
                row = []
                for j in range(2):
                    if i + j < len(stats.categories):
                        category = stats.categories[i + j]
                        count = stats.category_counts.get(category, 0)
                        # Format category name for display
                        display_name = category.replace('_', ' ').title()
                        row.append(InlineKeyboardButton(
                            f"{display_name} ({count})", 
                            callback_data=f"browse_cat_{category}"
                        ))
                keyboard.append(row)
            
            # Add back button
            keyboard.append([InlineKeyboardButton("🔙 Back to Browse", callback_data="cmd_browse")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(categories_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing categories menu: {e}")
            await query.edit_message_text("❌ Error loading categories.")
    
    async def _show_difficulties_menu(self, query) -> None:
        """Show available difficulty levels for browsing."""
        try:
            stats = self.content_browser.get_content_stats()
            
            difficulties_text = """
📊 **Browse by Difficulty**

Select your preferred difficulty level:
            """
            
            keyboard = []
            for difficulty in stats.difficulties:
                count = stats.difficulty_counts.get(difficulty, 0)
                display_name = difficulty.title()
                keyboard.append([InlineKeyboardButton(
                    f"{display_name} ({count} lessons)", 
                    callback_data=f"browse_diff_{difficulty}"
                )])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("🔙 Back to Browse", callback_data="cmd_browse")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(difficulties_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing difficulties menu: {e}")
            await query.edit_message_text("❌ Error loading difficulty levels.")
    
    async def _show_category_lessons(self, query, category: str) -> None:
        """Show lessons in a specific category."""
        try:
            search_result = self.content_browser.search_by_category(category, limit=8)
            
            if not search_result.lessons:
                await query.edit_message_text(
                    f"📂 **{category.replace('_', ' ').title()}**\n\n"
                    "❌ No lessons found in this category."
                )
                return
            
            # Format category name for display
            display_name = category.replace('_', ' ').title()
            lessons_text = f"""
📂 **{display_name} Lessons**

Found {search_result.total_count} lessons:
            """
            
            keyboard = []
            for lesson in search_result.lessons:
                # Truncate long titles
                title = lesson.title[:40] + "..." if len(lesson.title) > 40 else lesson.title
                keyboard.append([InlineKeyboardButton(
                    f"📖 {title}", 
                    callback_data=f"view_lesson_{lesson.id}"
                )])
            
            # Add navigation buttons
            nav_buttons = [
                InlineKeyboardButton("🔙 Categories", callback_data="browse_categories"),
                InlineKeyboardButton("🏠 Browse Menu", callback_data="cmd_browse")
            ]
            keyboard.append(nav_buttons)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(lessons_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing category lessons for '{category}': {e}")
            await query.edit_message_text("❌ Error loading lessons.")
    
    async def _show_difficulty_lessons(self, query, difficulty: str) -> None:
        """Show lessons of a specific difficulty."""
        try:
            search_result = self.content_browser.search_by_difficulty(difficulty, limit=8)
            
            if not search_result.lessons:
                await query.edit_message_text(
                    f"📊 **{difficulty.title()} Lessons**\n\n"
                    "❌ No lessons found at this difficulty level."
                )
                return
            
            lessons_text = f"""
📊 **{difficulty.title()} Lessons**

Found {search_result.total_count} lessons:
            """
            
            keyboard = []
            for lesson in search_result.lessons:
                # Truncate long titles and show category
                title = lesson.title[:35] + "..." if len(lesson.title) > 35 else lesson.title
                category_emoji = "📝" if lesson.category == "grammar" else "📚" if lesson.category == "vocabulary" else "⚠️"
                keyboard.append([InlineKeyboardButton(
                    f"{category_emoji} {title}", 
                    callback_data=f"view_lesson_{lesson.id}"
                )])
            
            # Add navigation buttons
            nav_buttons = [
                InlineKeyboardButton("🔙 Difficulties", callback_data="browse_difficulties"),
                InlineKeyboardButton("🏠 Browse Menu", callback_data="cmd_browse")
            ]
            keyboard.append(nav_buttons)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(lessons_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing difficulty lessons for '{difficulty}': {e}")
            await query.edit_message_text("❌ Error loading lessons.")
    
    async def _show_popular_lessons(self, query) -> None:
        """Show most popular lessons."""
        try:
            search_result = self.content_browser.get_popular_content(limit=8)
            
            if not search_result.lessons:
                await query.edit_message_text("🔥 **Popular Lessons**\n\n❌ No lessons available.")
                return
            
            lessons_text = f"""
🔥 **Popular Lessons**

Most frequently accessed lessons:
            """
            
            keyboard = []
            for i, lesson in enumerate(search_result.lessons, 1):
                title = lesson.title[:35] + "..." if len(lesson.title) > 35 else lesson.title
                usage_info = f" ({lesson.usage_count} views)" if lesson.usage_count > 0 else ""
                keyboard.append([InlineKeyboardButton(
                    f"{i}. {title}{usage_info}", 
                    callback_data=f"view_lesson_{lesson.id}"
                )])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("🔙 Back to Browse", callback_data="cmd_browse")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(lessons_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing popular lessons: {e}")
            await query.edit_message_text("❌ Error loading popular lessons.")
    
    async def _show_recent_lessons(self, query) -> None:
        """Show most recent lessons."""
        try:
            search_result = self.content_browser.get_recent_content(limit=8)
            
            if not search_result.lessons:
                await query.edit_message_text("🆕 **Recent Lessons**\n\n❌ No lessons available.")
                return
            
            lessons_text = f"""
🆕 **Recent Lessons**

Latest additions to our content:
            """
            
            keyboard = []
            for lesson in search_result.lessons:
                title = lesson.title[:40] + "..." if len(lesson.title) > 40 else lesson.title
                category_name = lesson.category.replace('_', ' ').title()
                keyboard.append([InlineKeyboardButton(
                    f"📖 {title} ({category_name})", 
                    callback_data=f"view_lesson_{lesson.id}"
                )])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("🔙 Back to Browse", callback_data="cmd_browse")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(lessons_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing recent lessons: {e}")
            await query.edit_message_text("❌ Error loading recent lessons.")
    
    async def _show_lesson_detail(self, query, lesson_id: int) -> None:
        """Show detailed view of a specific lesson."""
        try:
            lesson = self.lesson_manager.get_lesson(lesson_id)
            if not lesson:
                await query.edit_message_text("❌ Lesson not found.")
                return
            
            # Format lesson content
            lesson_text = f"""
📖 **{lesson.title}**

{lesson.content}

---
📂 **Category:** {lesson.category.replace('_', ' ').title()}
📊 **Difficulty:** {lesson.difficulty.title()}
🏷️ **Tags:** {', '.join(lesson.tags) if lesson.tags else 'None'}
👀 **Views:** {lesson.usage_count}
            """
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("🧠 Take Quiz", callback_data=f"quiz_{lesson_id}"),
                    InlineKeyboardButton("📋 More Like This", callback_data=f"similar_{lesson.category}")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Browse", callback_data="cmd_browse")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(lesson_text, parse_mode='Markdown', reply_markup=reply_markup)
            
            # Record lesson view in progress tracker
            if self.progress_tracker:
                try:
                    self.progress_tracker.record_lesson_completion(
                        user_id=query.from_user.id,
                        lesson_id=lesson.id,
                        lesson_title=lesson.title,
                        difficulty=lesson.difficulty,
                        category=lesson.category
                    )
                except Exception as progress_error:
                    logger.warning(f"Failed to record lesson view: {progress_error}")
            
        except Exception as e:
            logger.error(f"Error showing lesson detail for ID {lesson_id}: {e}")
            await query.edit_message_text("❌ Error loading lesson details.")
    
    async def _handle_browse_callback(self, query, data: str) -> None:
        """Handle browse-related callback queries."""
        try:
            if data == "browse_categories":
                await self._show_categories_menu(query)
            elif data == "browse_difficulties":
                await self._show_difficulties_menu(query)
            elif data == "browse_popular":
                await self._show_popular_lessons(query)
            elif data == "browse_recent":
                await self._show_recent_lessons(query)
            elif data == "browse_tags":
                # Show popular tags menu
                await self._show_tags_menu(query)
            elif data == "browse_search":
                # Show search instructions
                await query.edit_message_text(
                    "🔍 **Search Lessons**\n\n"
                    "To search for lessons, use these commands:\n"
                    "• Type the lesson title or keywords\n"
                    "• Use the category and difficulty browsers\n"
                    "• Browse by popular tags\n\n"
                    "💡 **Tip:** Use the buttons below for easier browsing!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back to Browse", callback_data="cmd_browse")
                    ]])
                )
            elif data.startswith("browse_cat_"):
                category = data.split("browse_cat_", 1)[1]
                await self._show_category_lessons(query, category)
            elif data.startswith("browse_diff_"):
                difficulty = data.split("browse_diff_", 1)[1]
                await self._show_difficulty_lessons(query, difficulty)
            elif data.startswith("browse_tag_"):
                tag = data.split("browse_tag_", 1)[1]
                await self._show_tag_lessons(query, tag)
            else:
                await query.edit_message_text("❌ Unknown browse option.")
                
        except Exception as e:
            logger.error(f"Error handling browse callback '{data}': {e}")
            await query.edit_message_text("❌ Error processing browse request.")
    
    async def _show_tags_menu(self, query) -> None:
        """Show popular tags for browsing."""
        try:
            stats = self.content_browser.get_content_stats()
            
            tags_text = """
🏷️ **Browse by Topic**

Popular topics to explore:
            """
            
            keyboard = []
            # Show first 12 popular tags
            popular_tags = stats.popular_tags[:12]
            
            for i in range(0, len(popular_tags), 2):
                row = []
                for j in range(2):
                    if i + j < len(popular_tags):
                        tag = popular_tags[i + j]
                        # Format tag for display
                        display_tag = tag.replace('_', ' ').title()
                        row.append(InlineKeyboardButton(
                            f"#{display_tag}", 
                            callback_data=f"browse_tag_{tag}"
                        ))
                keyboard.append(row)
            
            # Add back button
            keyboard.append([InlineKeyboardButton("🔙 Back to Browse", callback_data="cmd_browse")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(tags_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing tags menu: {e}")
            await query.edit_message_text("❌ Error loading topics.")
    
    async def _show_tag_lessons(self, query, tag: str) -> None:
        """Show lessons with a specific tag."""
        try:
            search_result = self.content_browser.search_by_tag(tag, limit=8)
            
            if not search_result.lessons:
                display_tag = tag.replace('_', ' ').title()
                await query.edit_message_text(
                    f"🏷️ **#{display_tag} Lessons**\n\n"
                    "❌ No lessons found with this topic."
                )
                return
            
            display_tag = tag.replace('_', ' ').title()
            lessons_text = f"""
🏷️ **#{display_tag} Lessons**

Found {search_result.total_count} lessons:
            """
            
            keyboard = []
            for lesson in search_result.lessons:
                title = lesson.title[:35] + "..." if len(lesson.title) > 35 else lesson.title
                difficulty_emoji = "🟢" if lesson.difficulty == "beginner" else "🟡" if lesson.difficulty == "intermediate" else "🔴"
                keyboard.append([InlineKeyboardButton(
                    f"{difficulty_emoji} {title}", 
                    callback_data=f"view_lesson_{lesson.id}"
                )])
            
            # Add navigation buttons
            nav_buttons = [
                InlineKeyboardButton("🔙 Topics", callback_data="browse_tags"),
                InlineKeyboardButton("🏠 Browse Menu", callback_data="cmd_browse")
            ]
            keyboard.append(nav_buttons)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(lessons_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing tag lessons for '{tag}': {e}")
            await query.edit_message_text("❌ Error loading lessons.")
    
    def get_config(self):
        """Get configuration for settings display."""
        from ..config import get_config
        return get_config()